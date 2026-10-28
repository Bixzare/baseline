"""NBA operational thresholds, coverage and guarded recovery eligibility."""

from datetime import UTC, datetime, timedelta
from typing import Any

from hoop.platform.evidence import EvidenceError
from hoop.platform.provenance import parse_time


def assess(now: datetime, snapshot: dict[str, Any]) -> dict[str, Any]:
    if now.tzinfo is None:
        raise EvidenceError("Aware health clock required")
    now = now.astimezone(UTC)
    conditions = []
    recovery = []
    pause_optional = False

    def check(key: str, bad: bool, reason: str, *, critical: bool = False, **details: Any) -> None:
        conditions.append(
            {
                "alert_key": key,
                "severity": "critical" if critical else "warning",
                "state": "open" if bad else "resolved",
                "reason_code": reason,
                "observed_at": now,
                "details": details,
            }
        )

    active = snapshot.get("production_active", False)
    events = snapshot.get("events", [])
    in_window = any(
        e.get("start")
        and parse_time(e["start"]) - timedelta(minutes=120)
        <= now
        < parse_time(e["start"]) - timedelta(minutes=15)
        for e in events
        if e["state"] == "scheduled"
    )
    runs = snapshot.get("runs", {})
    if active and in_window:
        dispatcher = runs.get("dispatcher", {})
        for field in ["started", "succeeded"]:
            value = dispatcher.get(field)
            bad = value is None or not 0 <= (now - parse_time(value)).total_seconds() < 45 * 60
            check(
                "nba:dispatcher:" + field,
                bad,
                "dispatcher_heartbeat_missing" if field == "started" else "dispatcher_incomplete",
                last=value,
            )
    if active and now.time() >= datetime(2000, 1, 1, 9, 17, tzinfo=UTC).time():
        nightly = runs.get("nightly", {}).get("succeeded")
        bad = (
            nightly is None or parse_time(nightly).date() != now.date() or parse_time(nightly) > now
        )
        check("nba:nightly:completion", bad, "nightly_not_successful", last=nightly)
    activation = parse_time(snapshot["activation_at"]) if snapshot.get("activation_at") else None
    for event in events:
        start = parse_time(event["start"]) if event.get("start") else None
        if start is None:
            check("nba:event:" + event["event_id"], True, "unknown_start")
            continue
        if activation and start < activation:
            continue
        if event["state"] in {"postponed", "cancelled"}:
            continue
        if event["state"] == "unknown":
            check("nba:event:" + event["event_id"], True, "unresolved_occurrence")
            continue
        if not active or now < start - timedelta(minutes=120):
            continue
        key = "nba:event:" + event["event_id"]
        if event.get("valid_forecast"):
            check(key, False, "forecast_verified")
            continue
        if now >= start - timedelta(minutes=15) or event["state"] in {"in_progress", "final"}:
            check(key, True, "missed_or_unverified_forecast", critical=True)
            continue
        if not event.get("essential_fresh", False):
            check(key, True, "essential_input_stale")
            continue
        if now >= start - timedelta(minutes=90):
            check(key, True, "forecast_missing_recovery_due")
            if snapshot.get("fallback_enabled"):
                recovery.append(event["event_id"])
    if not snapshot.get("schedule_known", False):
        check("nba:schedule:unknown", True, "inventory_unverified")
    else:
        check("nba:schedule:unknown", False, "inventory_verified")
    for source in snapshot.get("sources", []):
        bad = source.get("state") != "accepted" or source.get("environment") == "unverified"
        times = [source.get("received_at"), source.get("generated_at")]
        age = source.get("max_age_seconds")
        if age is not None:
            bad = (
                bad
                or source.get("received_at") is None
                or any(t and not 0 <= (now - parse_time(t)).total_seconds() <= age for t in times)
            )
        check(
            source["alert_key"],
            bool(bad),
            "source_unavailable" if bad else "source_verified",
            capability=source["capability"],
            environment=source["environment"],
            source_id=source["source_id"],
        )
    for expected in snapshot.get("missing_capabilities", []):
        check("nba:capability:" + expected, True, "capability_unverified")
    for outcome in snapshot.get("pending_outcomes", []):
        if outcome["state"] == "final":
            check(
                "nba:outcome:" + str(outcome["event_id"]),
                True,
                "final_outcome_unresolved",
                outcome_state=outcome.get("outcome_state"),
            )
    backup = snapshot.get("backup", {})
    cutoff = backup.get("cutoff")
    backup_bad = (
        not backup.get("verified")
        or not cutoff
        or not 0 <= (now - parse_time(cutoff)).total_seconds() <= 24 * 3600
    )
    check("nba:backup:age", bool(backup_bad), "backup_stale_or_unverified", backup_cutoff=cutoff)
    for name in ["database", "objects"]:
        metric = snapshot.get("capacity", {}).get(name, {})
        used, limit = metric.get("used_bytes"), metric.get("limit_bytes")
        known = (
            metric.get("limit_verified")
            and isinstance(limit, int)
            and limit > 0
            and isinstance(used, int)
            and used >= 0
        )
        if not known:
            check(
                "nba:capacity:" + name,
                True,
                "capacity_unverified",
                measurement=metric.get("measurement"),
            )
            continue
        ratio = used / limit
        if name == "objects" and not metric.get("provider_usage_known", False):
            check(
                "nba:capacity:objects_provider",
                True,
                "provider_usage_unverified",
                measurement="registered objects exclude possible orphans",
            )
        projected = metric.get("projected_season_bytes")
        overflow = isinstance(projected, int) and projected > limit
        check(
            "nba:capacity:" + name,
            ratio >= 0.6 or overflow,
            "capacity_threshold" if ratio >= 0.6 or overflow else "capacity_below_threshold",
            critical=ratio >= 0.8,
            ratio=ratio,
            measurement=metric.get("measurement"),
            provider_usage_known=metric.get("provider_usage_known", False),
        )
        pause_optional = pause_optional or ratio >= 0.8
    return {
        "state": "degraded" if any(c["state"] == "open" for c in conditions) else "healthy",
        "conditions": conditions,
        "recovery_event_ids": recovery,
        "pause_optional": pause_optional,
        "source_snapshot": snapshot,
        "observed_at": now,
    }
