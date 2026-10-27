"""Partial finals, explicit nonparticipation and versioned cohort reconciliation."""

import json
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import psycopg

from hoop.domains.nba.collection import accepted_request
from hoop.domains.nba.outcomes.operations import reconcile
from hoop.domains.nba.outcomes.parsing import PARSER
from hoop.domains.nba.outcomes.persistence import pending_work
from hoop.domains.nba.sources.policy import ProbeRunner
from hoop.platform.artifacts import PrivateArtifacts
from hoop.platform.evidence import EvidenceError
from hoop.platform.prepared import encoded
from hoop.platform.provenance import parse_time


def main() -> int:
    import argparse

    from hoop.domains.nba.sources.policy import HTTPTransport, Policy, SystemClock
    from hoop.platform.artifacts import ArtifactError, Session, Settings
    from hoop.platform.database import DatabaseError, connection, health
    from hoop.platform.local_artifacts import atomic_json
    from hoop.platform.provenance import Archive

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=["work", "reconcile"])
    parser.add_argument("--config", type=Path, default=Path("configs/outcomes.json"))
    parser.add_argument("--environment", choices=["local", "github-actions"], required=True)
    parser.add_argument("--event", type=UUID, action="append")
    parser.add_argument("--from-time", type=parse_time)
    parser.add_argument("--to-time", type=parse_time)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--confirm-source-gates", action="store_true")
    args = parser.parse_args()
    result: dict[str, Any]
    try:
        config = json.loads(args.config.read_text())
        if (
            config.get("schema_version") != 1
            or config.get("parser_version") != PARSER
            or config.get("automatic_recheck_days") != 7
        ):
            raise EvidenceError("Reviewed outcome policy required")
        if args.operation == "reconcile":
            if not args.confirm_source_gates or not config["routes"]:
                raise EvidenceError("Accepted final routes and source gates required")
            for route in config["routes"]:
                accepted_request(route, args.environment, rehearsal=False, parser_version=PARSER)
        with connection() as conn:
            if health(conn)["role"] != "baseline_runtime":
                raise EvidenceError("Restricted runtime required")
            clock = SystemClock()
            if args.operation == "work":
                result = {
                    "work": pending_work(
                        conn,
                        clock.now(),
                        event_ids=args.event,
                        date_from=args.from_time,
                        date_to=args.to_time,
                    )
                }
            else:
                runner = ProbeRunner(
                    Archive(args.output / "source"),
                    HTTPTransport(),
                    clock,
                    Policy(**config["policy"]),
                    str(uuid4()),
                )
                result = reconcile(
                    conn,
                    PrivateArtifacts(Session(Settings.from_env())),
                    runner,
                    config,
                    args.environment,
                    event_ids=args.event,
                    date_from=args.from_time,
                    date_to=args.to_time,
                )
        atomic_json(args.output / "outcome-report.json", json.loads(encoded(result)))
        print(json.dumps(result, default=str, sort_keys=True))
        return 0 if result.get("state", "succeeded") == "succeeded" else 1
    except (
        EvidenceError,
        ArtifactError,
        DatabaseError,
        psycopg.Error,
        ValueError,
        KeyError,
        OSError,
    ):
        result = {
            "state": "blocked",
            "reason_code": "reconciliation_failed",
            "durable_audit_confirmed": False,
        }
        atomic_json(args.output / "outcome-failure.json", result)
        print(json.dumps(result))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
