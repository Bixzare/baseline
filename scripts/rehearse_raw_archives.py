"""Manual archive retention/readback. No source acceptance or production activation."""

import argparse
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import psycopg
from psycopg.rows import dict_row

from hoop.platform.artifacts import ArtifactError, PrivateArtifacts, Session, Settings
from hoop.platform.database import DatabaseError, connection, health
from hoop.platform.evidence import EvidenceError, register
from hoop.platform.local_artifacts import LocalArtifacts, atomic_json, checksum
from hoop.platform.provenance import digest
from hoop.platform.raw_archives import REPRESENTATION, retain_archive, verify_archive, verify_raw


def check_roots(
    conn: psycopg.Connection[Any], store: PrivateArtifacts, ids: list[str]
) -> dict[str, Any]:
    if not 1 <= len(ids) <= 16 or len(set(ids)) != len(ids):
        raise ValueError("Bounded distinct root identities required")
    identities = [str(UUID(value)) for value in ids]
    with conn.transaction(), conn.cursor(row_factory=dict_row) as cursor:
        cursor.execute("SET TRANSACTION READ ONLY")
        roots = cursor.execute(
            "SELECT * FROM platform.artifacts WHERE artifact_id=ANY(%s::uuid[])", (identities,)
        ).fetchall()
    if len(roots) != len(ids) or any(
        r["manifest"].get("representation") != REPRESENTATION for r in roots
    ):
        raise ValueError("Registered archive roots required")
    # The database snapshot closes before authentication or object requests.
    originals = {str(root["artifact_id"]): verify_raw(root, store.read) for root in roots}
    return {
        "archive_root_ids": identities,
        "originals": originals,
        "logical_bytes_verified": sum(row["byte_count"] for row in originals.values()),
        "source_accepted": False,
        "publication_enabled": False,
        "verified_at": datetime.now(UTC).isoformat(),
        "readback_verified": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", nargs="?", choices=["plan", "retain", "check"], default="plan")
    parser.add_argument("--archive", type=Path)
    parser.add_argument("--staged", type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--confirm-rehearsal", action="store_true")
    args = parser.parse_args()
    if args.operation == "plan":
        print(
            json.dumps(
                {
                    "operation": "plan",
                    "network_access": False,
                    "database_writes": False,
                    "production_enabled": False,
                }
            )
        )
        return 0
    run_id = None
    try:
        if not args.confirm_rehearsal or args.report is None:
            raise ValueError("Explicit rehearsal confirmation and report required")
        staged = None
        if args.operation == "retain":
            if args.archive is None or args.staged is None:
                raise ValueError("Verified local archive and staged set required")
            staged = json.loads(args.staged.read_text())
            if not 1 <= len(staged["files"]) <= 16:
                raise ValueError("Bounded archive set required")
            local = LocalArtifacts(args.archive)
            for archive in staged["files"].values():
                verify_archive(archive, lambda part: local.verify(part).read_bytes())
        with connection() as conn:
            if health(conn)["role"] != "baseline_runtime":
                raise ValueError("Restricted runtime identity required")
            store = PrivateArtifacts(Session(Settings.from_env()))
            if staged is not None:
                run_id = str(uuid4())
                register(
                    conn,
                    "runs",
                    {
                        "run_id": run_id,
                        "operation": "raw_archive_rehearsal",
                        "domain": "platform",
                        "environment": "rehearsal",
                        "code_version": checksum(Path(__file__)),
                        "config_hash": digest(json.dumps(staged, sort_keys=True).encode()),
                    },
                )
                register(
                    conn,
                    "run_events",
                    {
                        "run_event_id": str(uuid4()),
                        "run_id": run_id,
                        "state": "started",
                        "reason_code": None,
                        "details": {},
                    },
                )
                try:
                    roots = [
                        retain_archive(conn, store, local, archive)
                        for archive in staged["files"].values()
                    ]
                    result = check_roots(conn, store, [str(root["artifact_id"]) for root in roots])
                    register(
                        conn,
                        "run_events",
                        {
                            "run_event_id": str(uuid4()),
                            "run_id": run_id,
                            "state": "succeeded",
                            "reason_code": None,
                            "details": {"archive_count": len(roots), "source_accepted": False},
                        },
                    )
                except Exception:
                    register(
                        conn,
                        "run_events",
                        {
                            "run_event_id": str(uuid4()),
                            "run_id": run_id,
                            "state": "failed",
                            "reason_code": "raw_archive_rehearsal_failed",
                            "details": {},
                        },
                    )
                    raise
            else:
                ids = os.environ.get("BASELINE_RAW_ARCHIVE_ROOT_IDS", "").split(",")
                result = check_roots(conn, store, ids)
        result.update(
            operation=args.operation,
            environment="rehearsal",
            run_id=run_id,
            hosted_writes_performed=args.operation == "retain",
        )
        atomic_json(args.report, result)
        print(json.dumps(result))
        return 0
    except (
        ArtifactError,
        DatabaseError,
        EvidenceError,
        ValueError,
        KeyError,
        OSError,
        psycopg.Error,
    ):
        failure = {
            "status": "blocked",
            "reason_code": "raw_archive_rehearsal_failed",
            "operation": args.operation,
            "run_id": run_id,
        }
        if args.report is not None:
            atomic_json(args.report, failure)
        print(json.dumps(failure))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
