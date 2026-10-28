"""Default planning is local; apply needs reviewed source and hosted gates."""

import argparse
import json
from pathlib import Path

from hoop.domains.nba.history.raw import stage_raw_archives
from hoop.domains.nba.history.seed import apply_seed, plan_seed
from hoop.platform.artifacts import ArtifactError, PrivateArtifacts, Session, Settings
from hoop.platform.database import DatabaseError, connection
from hoop.platform.evidence import EvidenceError
from hoop.platform.local_artifacts import LocalArtifacts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=["plan", "stage-raw", "apply"])
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--downloads", type=Path)
    parser.add_argument("--acceptance", type=Path)
    parser.add_argument("--raw-archives", type=Path)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--confirm-hosted-gates", action="store_true")
    args = parser.parse_args()
    try:
        store = LocalArtifacts(args.archive)
        pointer = json.loads((args.archive / "candidate-current.json").read_text())
        descriptor = pointer["manifest_artifact"]
        report = {
            **json.loads(store.verify(descriptor).read_text()),
            "manifest_artifact": descriptor,
        }
        if args.operation == "stage-raw":
            staged = stage_raw_archives(report, args.archive)
            args.report.parent.mkdir(parents=True, exist_ok=True)
            args.report.write_text(json.dumps(staged, sort_keys=True))
            print(
                json.dumps(
                    {
                        "operation": "stage-raw",
                        "source_accepted": False,
                        "encoded_bytes": sum(
                            a["encoded_byte_count"] for a in staged["files"].values()
                        ),
                        "part_count": sum(len(a["parts"]) for a in staged["files"].values()),
                    }
                )
            )
            return 0
        observations = None
        if args.downloads:
            observations = {
                row["file"]: {
                    "requested_at": row["started_at"],
                    "received_at": row["finished_at"],
                    "sha256": row["sha256"],
                }
                for row in json.loads(args.downloads.read_text())
            }
        plan = plan_seed(
            report,
            args.archive,
            json.loads(args.source_manifest.read_text()),
            json.loads(args.acceptance.read_text()) if args.acceptance else None,
            observations,
            json.loads(args.raw_archives.read_text()) if args.raw_archives else None,
        )
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(plan, sort_keys=True))
        if args.operation == "apply":
            if not args.confirm_hosted_gates:
                raise EvidenceError("Apply requires confirmed hosted/source gates")
            with connection() as conn:
                result = apply_seed(
                    conn,
                    PrivateArtifacts(Session(Settings.from_env())),
                    plan,
                    args.archive,
                    args.report.with_suffix(".checkpoint.json"),
                    environment="production",
                )
        else:
            result = {
                key: plan[key]
                for key in ["counts", "blockers", "required_raw_bytes", "plan_sha256"]
            }
        print(json.dumps(result))
        return 1 if plan["blockers"] else 0
    except (EvidenceError, ArtifactError, DatabaseError, ValueError, KeyError, OSError):
        print(json.dumps({"status": "blocked", "reason_code": "seed_plan_or_import_failed"}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
