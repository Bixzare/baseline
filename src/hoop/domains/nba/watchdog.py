"""Independent local assessment and guarded recovery; offline mode never publishes."""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import psycopg

from hoop.domains.nba.health import snapshot
from hoop.domains.nba.health_policy import assess
from hoop.domains.nba.operations import ROOT, SourceBudget, stages
from hoop.platform.artifacts import ArtifactError, PrivateArtifacts, Session, Settings
from hoop.platform.database import DatabaseError, connection, health
from hoop.platform.evidence import EvidenceError
from hoop.platform.local_artifacts import atomic_json
from hoop.platform.monitoring import reconcile_conditions
from hoop.platform.notifications import notify
from hoop.platform.operations import production_enabled, run_pipeline
from hoop.platform.prepared import encoded
from hoop.platform.provenance import parse_time


def local_incident(directory: Path, reason: str, now: datetime) -> bool:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / (now.astimezone(UTC).strftime("%Y-%m-%d") + ".jsonl")
    record = (
        encoded(
            {
                "observed_at": now.isoformat(),
                "reason_code": reason,
                "durable_database_recording": False,
                "blind_recovery_attempted": False,
            }
        )
        + b"\n"
    )
    if path.exists() and path.stat().st_size + len(record) > 1048576:
        return False
    with path.open("ab") as stream:
        stream.write(record)
    return True


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mode", choices=["read-only", "production", "rehearsal"], default="read-only"
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--fixture-state", type=Path)
    parser.add_argument("--notify", action="store_true")
    parser.add_argument("--invocation", type=UUID)
    args = parser.parse_args()
    config = json.loads((ROOT / "configs/health.json").read_text())
    operations = json.loads((ROOT / "configs/operations.json").read_text())
    actual_now = datetime.now(UTC)
    result: dict[str, Any] = {
        "invocation_id": str(args.invocation or uuid4()),
        "checked_at_actual_utc": actual_now.isoformat(),
        "recovery_attempted": False,
        "durable_alerts": 0,
    }
    cache = args.output / "cached-health.json"
    try:
        if args.mode == "rehearsal":
            if (
                not args.fixture_state
                or args.fixture_state.stat().st_size > config["cache_max_bytes"]
            ):
                raise EvidenceError("Bounded explicit fixture input required")
            fixture = json.loads(args.fixture_state.read_text())
            if fixture.get("evidence") != "synthetic_fixture":
                raise EvidenceError("Fixture evidence required")
            result.update(
                state="rehearsal",
                assessment=assess(parse_time(fixture["fixture_now"]), fixture["snapshot"]),
                production_heartbeat=False,
            )
        elif args.mode == "production" and not production_enabled(operations):
            result.update(state="disabled", production_heartbeat=False)
        else:
            with connection() as conn:
                if health(conn)["role"] != "baseline_runtime":
                    raise EvidenceError("Restricted watchdog role required")
                captured = snapshot(conn, config, operations)
                result.update(
                    state=captured["assessment"]["state"],
                    assessment=captured["assessment"],
                    production_heartbeat=False,
                )
                if len(encoded(captured)) <= config["cache_max_bytes"]:
                    atomic_json(cache, json.loads(encoded(captured)))
                if args.mode == "production":
                    result["durable_alerts"] = reconcile_conditions(
                        conn, captured["assessment"]["conditions"], captured["now"], namespace="nba"
                    )
                    if config["local_fallback_enabled"]:
                        store = PrivateArtifacts(Session(Settings.from_env()))
                        budget = SourceBudget(
                            args.output / "sources", "local", operations, conn=conn
                        )
                        recover = captured["assessment"]["recovery_event_ids"]
                        if recover:
                            result["recovery_attempted"] = True
                            result["recovery"] = run_pipeline(
                                conn,
                                "dispatcher",
                                stages(
                                    conn,
                                    store,
                                    budget,
                                    "dispatcher",
                                    selected_event_ids={UUID(i) for i in recover},
                                ),
                                operations,
                            )
                        nightly = any(
                            c["alert_key"] == "nba:nightly:completion" and c["state"] == "open"
                            for c in captured["assessment"]["conditions"]
                        )
                        if nightly:
                            remaining = operations["max_seconds"] - (
                                budget.clock.monotonic() - budget.started
                            )
                            if remaining > 0:
                                result["recovery_attempted"] = True
                                result["nightly_recovery"] = run_pipeline(
                                    conn,
                                    "nightly",
                                    stages(conn, store, budget, "nightly"),
                                    {**operations, "max_seconds": remaining},
                                )
                            else:
                                result["nightly_recovery"] = {"state": "budget_exhausted"}
    except (
        EvidenceError,
        ArtifactError,
        DatabaseError,
        psycopg.Error,
        OSError,
        ValueError,
        KeyError,
    ):
        result.update(
            state="unverified",
            reason_code="database_or_evidence_unavailable",
            durable_database_recording=False,
        )
        result["local_incident_saved"] = local_incident(
            args.output / "incidents", "database_or_evidence_unavailable", actual_now
        )
        if cache.exists() and cache.stat().st_size <= config["cache_max_bytes"]:
            try:
                previous = json.loads(cache.read_text())
                result["cache_observed_at"] = previous.get("now")
                age = (actual_now - parse_time(previous["now"])).total_seconds()
                result["cache_age_seconds"] = age
                result["cache_stale"] = age > 1800 or age < 0
                result["cache_is_deadline_authority"] = False
            except (OSError, ValueError, KeyError):
                result["cache_reason"] = "unavailable_or_invalid"
    conditions = result.get("assessment", {}).get("conditions", [])
    keys = sorted(
        c["alert_key"] + ":" + c["severity"] + ":" + c["reason_code"]
        for c in conditions
        if c["state"] == "open"
    )
    if result["state"] == "unverified":
        keys = ["offline:" + result["reason_code"]]
    result["open_condition_keys"] = keys
    old_keys = []
    previously_queued = False
    previous_report = args.output / "latest-health.json"
    if previous_report.exists() and previous_report.stat().st_size <= config["cache_max_bytes"]:
        try:
            saved_report = json.loads(previous_report.read_text())
            old_keys = saved_report.get("open_condition_keys", [])
            previously_queued = saved_report.get("notice_queued_for_open_keys", False)
        except (OSError, ValueError):
            pass
    result["notice_queued_for_open_keys"] = previously_queued and keys == old_keys
    if (
        args.notify
        or config["desktop_notifications_enabled"]
        and keys
        and (keys != old_keys or not previously_queued)
    ):
        result["notification"] = notify(rehearsal=args.mode == "rehearsal")
        result["notice_queued_for_open_keys"] = result["notification"].get("queued", False)
    atomic_json(args.output / "latest-health.json", json.loads(encoded(result)))
    print(
        json.dumps(
            {
                k: result[k]
                for k in ["state", "invocation_id", "recovery_attempted", "durable_alerts"]
            },
            sort_keys=True,
        )
    )
    return 0 if result["state"] in {"healthy", "disabled", "rehearsal"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
