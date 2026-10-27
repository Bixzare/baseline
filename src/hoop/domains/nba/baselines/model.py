"""Freeze a verified roster and common appearance window before calculating rates."""

import json
import math
from datetime import date, datetime
from pathlib import Path
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo

from hoop.domains.nba.history.readers import eligible_latest
from hoop.platform.evidence import EvidenceError, known_by
from hoop.platform.prepared import encoded, validate_entries
from hoop.platform.provenance import digest, parse_time

POLICY_PATH = Path(__file__).parents[5] / "configs/baseline.json"
TARGETS = ("minutes", "points", "rebounds", "assists", "threes_made")


def descriptor(policy: dict[str, Any]) -> dict[str, Any]:
    if (
        policy.get("window") != 10
        or set(policy.get("targets", {})) != set(TARGETS)
        or policy.get("domain") != "nba"
        or policy.get("schema_version") != 1
    ):
        raise EvidenceError("Unsupported baseline policy")
    if (
        policy.get("schedule_max_age_seconds") != 1800
        or policy.get("roster_max_age_seconds") != 86400
        or policy.get("calendar_timezone") != "America/New_York"
    ):
        raise EvidenceError("Baseline freshness/calendar policy requires reviewed values")
    return {
        "schema_version": 1,
        "domain": "nba",
        "family": policy["family"],
        "version": policy["version"],
        "targets": policy["targets"],
        "code_version": digest(Path(__file__).read_text().encode()),
        "config_hash": digest(encoded(policy)),
        "configuration": policy,
        "dependency_lock_hash": digest(
            (Path(__file__).parents[5] / "uv.lock").read_text().encode()
        ),
        "learned_artifact_id": None,
        "training_cutoff": None,
    }


def fresh(evidence: dict[str, Any], cutoff: datetime, seconds: int) -> bool:
    try:
        if not known_by(evidence, cutoff):
            return False
        times = [parse_time(evidence["received_at"])]
        for field in ["source_published_at", "source_generated_at"]:
            if evidence.get(field):
                times.append(parse_time(evidence[field]))
        for container in ["details", "source_summary"]:
            generation = evidence.get(container, {}).get("source_generated_at")
            if generation:
                times.append(parse_time(generation))
        return all(0 <= (cutoff - value).total_seconds() <= seconds for value in times)
    except (ValueError, TypeError, KeyError, AttributeError):
        return False


def required_time(record: dict[str, Any], field: str) -> datetime:
    try:
        return parse_time(record[field])
    except (ValueError, TypeError, KeyError, AttributeError):
        raise EvidenceError("Required timezone-aware source time is unknown") from None


def order_key(row: dict[str, Any]) -> tuple[str, float]:
    return (
        row["game_date"],
        parse_time(str(row["actual_start"])).timestamp()
        if row.get("actual_start")
        else float("-inf"),
    )


def ambiguous_order(rows: list[dict[str, Any]]) -> bool:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(row["game_date"], []).append(row)
    return any(
        len(group) > 1
        and (
            any(not row.get("actual_start") for row in group)
            or len({order_key(row)[1] for row in group}) != len(group)
        )
        for group in grouped.values()
    )


def affects_window(row: dict[str, Any], oldest: str | None, count: int) -> bool:
    return not oldest or count < 10 or not row.get("game_date") or row["game_date"] >= oldest


def count_value(value: Any) -> float | None:
    if type(value) not in {int, float}:
        return None
    try:
        result = float(value)
        return result if math.isfinite(result) and result >= 0 and result.is_integer() else None
    except (ValueError, OverflowError):
        return None


def freeze_evidence(value: Any) -> Any:
    if isinstance(value, float) and not math.isfinite(value):
        return {"invalid_numeric": str(value)}
    if isinstance(value, dict):
        return {key: freeze_evidence(item) for key, item in value.items()}
    if isinstance(value, list):
        return [freeze_evidence(item) for item in value]
    return value


def prepare(
    inputs: dict[str, Any], *, policy: dict[str, Any] | None = None, generated_at: datetime
) -> dict[str, Any]:
    policy = policy or json.loads(POLICY_PATH.read_text())
    version = descriptor(policy)
    cutoff = parse_time(inputs["feature_cutoff"])
    if generated_at.tzinfo is None or generated_at < cutoff:
        raise EvidenceError("Generation must be aware and follow the feature cutoff")
    event = inputs["event"]
    schedule = inputs["schedule"]
    UUID(inputs["run_id"])
    if inputs.get("environment") not in {"rehearsal", "production"}:
        raise EvidenceError("Explicit preparation environment required")
    if (
        schedule["event_id"] != event["event_id"]
        or schedule["source_event_id"] != event["source_event_id"]
        or schedule.get("event_state") != "scheduled"
        or schedule.get("actual_start") is not None
        or required_time(schedule, "scheduled_start") <= generated_at
        or not fresh(schedule, cutoff, policy["schedule_max_age_seconds"])
    ):
        raise EvidenceError("Essential schedule/status evidence is invalid, stale or started")
    teams = event["team_ids"]
    if len(teams) != 2 or len(set(teams)) != 2:
        raise EvidenceError("Two distinct game teams required")
    cohort = []
    roster_sources = []
    all_ids = set()
    rosters = inputs["rosters"]
    if len(rosters) != 2 or {row["team_id"] for row in rosters} != set(teams):
        raise EvidenceError("Both saved team rosters are required")
    for roster in rosters:
        if roster["season"] != event["season"] or not fresh(
            roster, cutoff, policy["roster_max_age_seconds"]
        ):
            raise EvidenceError("Essential roster evidence is invalid or stale")
        body = roster["artifact_body"].encode()
        artifact = roster["artifact"]
        if digest(body) != artifact["sha256"] or len(body) != artifact["byte_count"]:
            raise EvidenceError("Roster artifact hash/size mismatch")
        members = json.loads(body)
        if (
            members.get("schema_version") != 1
            or members.get("team_id") != roster["team_id"]
            or members.get("season") != roster["season"]
            or not members.get("players")
        ):
            raise EvidenceError("Roster artifact identity/schema mismatch")
        for member in members["players"]:
            player = member["player_id"]
            if (
                not isinstance(player, str)
                or not player.isdigit()
                or int(player) <= 0
                or player in all_ids
            ):
                raise EvidenceError("Invalid or conflicting roster membership")
            all_ids.add(player)
            cohort.append(
                {
                    "player_id": player,
                    "team_id": roster["team_id"],
                    "availability": member.get("availability", "unknown"),
                    "roster_id": roster["roster_id"],
                }
            )
        roster_sources.append(
            {key: roster[key] for key in ["roster_id", "team_id", "source_check_id", "artifact"]}
        )
    latest = eligible_latest(
        inputs["history"],
        cutoff,
        ("event_id", "player_id"),
        (
            "team_id",
            "participation",
            "minutes_seconds",
            "points",
            "rebounds",
            "assists",
            "threes_made",
            "started",
        ),
    )
    local_date = cutoff.astimezone(ZoneInfo(policy["calendar_timezone"])).date()
    entries = []
    features = []
    reconciliation = []
    for member in sorted(cohort, key=lambda row: row["player_id"]):
        player = member["player_id"]
        appearances = []
        unresolved = []
        for row in latest:
            if (
                row["player_id"] != player
                or row["event_id"] == event["event_id"]
                or row["source_event_id"] == event["source_event_id"]
                or row["competition"] != "regular"
            ):
                continue
            try:
                actual = required_time(row, "actual_start") if row.get("actual_start") else None
                if actual is not None and actual >= cutoff:
                    continue
                day = (
                    actual.astimezone(ZoneInfo(policy["calendar_timezone"])).date()
                    if actual
                    else (date.fromisoformat(row["game_date"]) if row.get("game_date") else None)
                )
            except (ValueError, EvidenceError):
                day = None
                actual = None
            if actual:
                row = {
                    **row,
                    "game_date": day.isoformat() if day else None,
                    "date_convention": "derived_from_verified_actual_start",
                }
            if day is not None and day > local_date:
                continue
            if (
                row.get("ambiguous_revision")
                or row.get("event_state") != "final"
                or row.get("participation") not in {"played", "did_not_play"}
                or day is None
                or row.get("date_convention")
                not in {"source_calendar_verified", "derived_from_verified_actual_start"}
            ):
                unresolved.append({**row, "game_date": None} if day is None else row)
            elif row["participation"] == "played":
                appearances.append(row)
        appearances.sort(key=order_key, reverse=True)
        window = appearances[: policy["window"]]
        oldest = window[-1]["game_date"] if window else None
        gaps = [
            gap
            for gap in inputs.get("gaps", [])
            if gap["player_id"] == player
            and parse_time(gap["observed_at"]) <= cutoff
            and affects_window(gap, oldest, len(window))
        ]
        uncertain = any(affects_window(row, oldest, len(window)) for row in unresolved) or bool(
            gaps
        )
        ambiguous = ambiguous_order(window)
        if len(appearances) > 10 and appearances[9]["game_date"] == appearances[10]["game_date"]:
            ambiguous = ambiguous or ambiguous_order([appearances[9], appearances[10]])
        reason = (
            "unresolved_history"
            if uncertain
            else (
                "ambiguous_history_order" if ambiguous else ("no_history" if not window else None)
            )
        )
        seconds = []
        for row in window:
            try:
                seconds_value = float(row["minutes_seconds"])
            except (ValueError, TypeError):
                seconds_value = float("nan")
            seconds.append(seconds_value)
        try:
            denominator = (
                math.fsum(seconds) / 60
                if seconds and all(math.isfinite(x) and x > 0 for x in seconds)
                else 0
            )
        except OverflowError:
            denominator = 0
        if reason is None and (denominator <= 0 or not math.isfinite(denominator)):
            reason = "invalid_minutes"
        minutes = denominator / len(window) if window and denominator > 0 else None
        if uncertain:
            reconciliation.append(player)
        feature = {
            "player_id": player,
            "history_count": len(window),
            "short_history": len(window) < 10,
            "last_appearance_date": window[0]["game_date"] if window else None,
            "history": window,
            "unresolved": unresolved if uncertain else [],
            "gaps": gaps,
            "target_completeness": {},
        }
        for target in TARGETS:
            value: float | None = None
            rate: float | None = None
            target_reason = reason
            if target_reason is None:
                if target == "minutes":
                    value = minutes
                else:
                    values = [count_value(row.get(target)) for row in window]
                    if any(x is None for x in values):
                        target_reason = "invalid_stat"
                    else:
                        rate = math.fsum(x for x in values if x is not None) / denominator
                        value = minutes * rate if minutes is not None else None
                if value is not None and (not math.isfinite(value) or value < 0):
                    value = None
                    target_reason = "invalid_stat"
            feature["target_completeness"][target] = target_reason is None
            entries.append(
                {
                    "subject_type": "player",
                    "subject_id": player,
                    "target": target,
                    "value": value,
                    "unit": policy["targets"][target],
                    "reason_code": target_reason,
                    "rate": rate,
                }
            )
        features.append(freeze_evidence(feature))
    validate_entries(entries)
    # Hash only cutoff-eligible selected inputs, so appended future data cannot
    # alter an earlier snapshot's identity.
    frozen = {
        "event": event,
        "schedule": schedule,
        "roster_sources": roster_sources,
        "cohort": cohort,
        "features": features,
        "config_hash": version["config_hash"],
    }
    return {
        "schema_version": 1,
        "environment": inputs["environment"],
        "event": event,
        "run_id": inputs["run_id"],
        "feature_cutoff": cutoff.isoformat(),
        "generated_at": generated_at.isoformat(),
        "input_hash": digest(encoded(frozen)),
        "descriptor": version,
        "cohort": cohort,
        "features": features,
        "schedule": schedule,
        "roster_sources": roster_sources,
        "entries": entries,
        "reconciliation_requested": sorted(reconciliation),
        "coverage": {
            "players": len(cohort),
            "entries": len(entries),
            "numeric_entries": sum(row["value"] is not None for row in entries),
        },
        "official_publication": False,
        "publication_receipt": None,
    }
