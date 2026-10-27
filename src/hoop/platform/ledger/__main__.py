"""Controlled setup only. It cannot publish a forecast or create a receipt."""

import argparse
import json
from pathlib import Path

from hoop.platform.artifacts import ArtifactError, PrivateArtifacts, Session, Settings
from hoop.platform.database import DatabaseError, connection, health
from hoop.platform.evidence import EvidenceError
from hoop.platform.ledger.bootstrap import bootstrap
from hoop.platform.ledger.registry import active_bundle


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=["bootstrap", "inspect"])
    parser.add_argument("--descriptor", type=Path)
    parser.add_argument("--domain")
    parser.add_argument("--family")
    parser.add_argument("--confirm-hosted-gates", action="store_true")
    args = parser.parse_args()
    try:
        if args.operation == "inspect":
            if not args.domain or not args.family:
                raise EvidenceError("Domain/family required")
            with connection() as conn:
                if health(conn)["role"] != "baseline_runtime":
                    raise EvidenceError("Inspection must verify the restricted runtime role")
                result = active_bundle(conn, args.domain, args.family)
        else:
            if not args.confirm_hosted_gates or args.descriptor is None:
                raise EvidenceError("Reviewed hosted gates and descriptor required")
            descriptor = json.loads(args.descriptor.read_text())
            with connection("BASELINE_MIGRATION_DSN") as conn:
                result = bootstrap(
                    conn,
                    PrivateArtifacts(Session(Settings.from_env())),
                    descriptor,
                    environment="production",
                )
        print(json.dumps(result, sort_keys=True, default=str))
        return 0
    except (DatabaseError, EvidenceError, ArtifactError, ValueError, KeyError, OSError):
        print(json.dumps({"status": "blocked", "reason_code": "baseline_bootstrap_failed"}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
