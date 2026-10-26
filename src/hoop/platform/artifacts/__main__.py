"""Explicit controlled setup and manual hosted permission rehearsal."""

import argparse
import json
import os
from dataclasses import replace
from uuid import UUID

from hoop.platform.artifacts import ArtifactError, Session, Settings
from hoop.platform.artifacts.verify import verify
from hoop.platform.database import DatabaseError, connection


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=["setup", "verify"])
    args = parser.parse_args()
    try:
        if args.operation == "setup":
            # Zero is only an unbound first-setup placeholder, never a verified
            # runtime identity. Setup returns the actual UUID to configure.
            settings = Settings(
                os.environ["BASELINE_SUPABASE_URL"].rstrip("/"),
                os.environ["BASELINE_SUPABASE_PUBLISHABLE_KEY"],
                os.environ["BASELINE_ARTIFACT_EMAIL"],
                os.environ["BASELINE_ARTIFACT_PASSWORD"],
                os.environ.get("BASELINE_ARTIFACT_USER_ID", str(UUID(int=0))),
                os.environ.get("BASELINE_ARTIFACT_BUCKET", "baseline-artifacts"),
            )
            from hoop.platform.artifacts.setup import provision

            with connection("BASELINE_MIGRATION_DSN") as conn:
                result = provision(
                    conn,
                    settings,
                    os.environ["BASELINE_SUPABASE_ADMIN_KEY"],
                    unrelated_bucket=os.environ.get(
                        "BASELINE_OTHER_ARTIFACT_BUCKET", "baseline-denied-rehearsal"
                    ),
                )
        else:
            settings = Settings.from_env()
            other = replace(
                settings,
                email=os.environ["BASELINE_OTHER_ARTIFACT_EMAIL"],
                password=os.environ["BASELINE_OTHER_ARTIFACT_PASSWORD"],
                user_id=os.environ["BASELINE_OTHER_ARTIFACT_USER_ID"],
            )
            result = verify(
                Session(settings), Session(other), os.environ["BASELINE_OTHER_ARTIFACT_BUCKET"]
            )
        print(json.dumps(result, sort_keys=True))
        return 0 if result.get("verified", args.operation == "setup") else 1
    except (ArtifactError, DatabaseError, KeyError, ValueError):
        print(json.dumps({"verified": False, "reason_code": "artifact_setup_or_check_failed"}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
