"""Fixture preparation is local and cannot publish or activate a model."""

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from hoop.domains.nba.baselines.model import prepare
from hoop.platform.artifacts import ArtifactError, PrivateArtifacts, Session, Settings
from hoop.platform.database import DatabaseError, connection
from hoop.platform.evidence import EvidenceError
from hoop.platform.local_artifacts import atomic_json
from hoop.platform.prepared import retain_prepared, save_local
from hoop.platform.provenance import parse_time


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=["fixture", "prepare"])
    parser.add_argument("--input", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--event")
    parser.add_argument("--cutoff")
    parser.add_argument("--confirm-hosted-gates", action="store_true")
    args = parser.parse_args()
    try:
        retained = None
        if args.operation == "fixture":
            if args.input is None:
                raise EvidenceError("Fixture input required")
            inputs = json.loads(args.input.read_text())
            if inputs.get("environment") != "rehearsal":
                raise EvidenceError("Fixture input must be rehearsal")
            result = prepare(inputs, generated_at=parse_time(inputs["fixture_generated_at"]))
        else:
            if not args.event or not args.cutoff or not args.confirm_hosted_gates:
                raise EvidenceError(
                    "Real preparation requires event, cutoff and confirmed hosted gates"
                )
            from hoop.domains.nba.baselines.capture import capture_game

            with connection() as conn:
                store = PrivateArtifacts(Session(Settings.from_env()))
                inputs = capture_game(
                    conn, store, UUID(args.event), parse_time(args.cutoff), environment="production"
                )
                result = prepare(inputs, generated_at=datetime.now(UTC))
                retained = retain_prepared(conn, store, result)
        saved = save_local(result, args.output)
        if retained is not None:
            atomic_json(args.output / "registration-descriptor.json", retained["descriptor"])
            atomic_json(args.output / "retained.json", retained)
        print(json.dumps({**saved, "coverage": result["coverage"], "retained": retained}))
        return 0
    except (EvidenceError, ArtifactError, DatabaseError, KeyError, ValueError, OSError):
        print(
            json.dumps({"status": "blocked", "reason_code": "baseline_fixture_preparation_failed"})
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
