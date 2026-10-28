"""Controlled local backup job. Production is off until reviewed setup is verified."""

import argparse
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit
from uuid import uuid4

from psycopg.conninfo import conninfo_to_dict

from hoop.platform.artifacts import ArtifactError, PrivateArtifacts, Session, Settings, retain
from hoop.platform.backup import BackupError, finalize, remote_readback
from hoop.platform.backup.database import Tools, export, restore, retain_inputs
from hoop.platform.backup.onedrive import OneDrive
from hoop.platform.database import DatabaseError, connection
from hoop.platform.evidence import register
from hoop.platform.local_artifacts import atomic_json
from hoop.platform.prepared import encoded
from hoop.platform.provenance import digest

ROOT = Path(__file__).resolve().parents[4]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=["run", "verify", "restore"])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--backup-id")
    parser.add_argument("--manifest-hash")
    args = parser.parse_args()
    config = json.loads((ROOT / "configs/backup.json").read_text())
    if not config["enabled"] or os.environ.get("BASELINE_BACKUP_ENABLE") != "true":
        print(json.dumps({"state": "disabled", "off_device_verified": False}))
        return 0
    run_id = str(uuid4())
    result = {"state": "unverified", "off_device_verified": False, "run_id": run_id}
    try:
        sync = Path(os.environ["BASELINE_BACKUP_SYNC_DIR"]).resolve()
        staging_root = Path(os.environ["BASELINE_BACKUP_STAGING_DIR"]).resolve()
        readback_root = Path(os.environ["BASELINE_BACKUP_READBACK_DIR"]).resolve()
        if any(
            a == b or a.is_relative_to(b) or b.is_relative_to(a)
            for a, b in [(sync, staging_root), (sync, readback_root), (staging_root, readback_root)]
        ):
            raise BackupError("backup_directories_must_be_separate")
        if not sync.is_dir():
            raise BackupError("owner_configured_sync_folder_required")
        project = os.environ["BASELINE_BACKUP_PROJECT_ID"]
        settings = Settings.from_env()
        if urlsplit(settings.url).hostname != project + ".supabase.co":
            raise BackupError("backup_project_api_identity_mismatch")
        if args.operation == "run":
            options = conninfo_to_dict(os.environ["BASELINE_MIGRATION_DSN"])
            direct = options.get("host") == "db." + project + ".supabase.co"
            pooled = (
                str(options.get("host", "")).endswith(".pooler.supabase.com")
                and options.get("user") == "postgres." + project
            )
            if not direct and not pooled:
                raise BackupError("backup_database_project_identity_mismatch")
        tools = Tools(directory=Path(os.environ["BASELINE_PG_BIN"]))
        remote = OneDrive(
            Path(os.environ["BASELINE_RCLONE_BIN"]),
            os.environ["BASELINE_BACKUP_REMOTE"],
            os.environ["BASELINE_RCLONE_VERSION"],
        )
        store = PrivateArtifacts(Session(settings))
        if args.operation == "run":
            archive_files = json.loads(
                Path(os.environ["BASELINE_BACKUP_ARCHIVE_INVENTORY"]).read_text()
            )
            if not isinstance(archive_files, list) or not archive_files:
                raise BackupError("reviewed_historical_archive_inventory_required")
            with connection("BASELINE_MIGRATION_DSN") as conn:
                register(
                    conn,
                    "runs",
                    {
                        "run_id": run_id,
                        "operation": "backup",
                        "domain": config["domain"],
                        "environment": "production",
                        "code_version": digest(
                            encoded(
                                {
                                    p.name: digest(p.read_bytes())
                                    for p in sorted(Path(__file__).parent.glob("*.py"))
                                }
                            )
                        ),
                        "config_hash": digest((ROOT / "configs/backup.json").read_bytes()),
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
                        "details": {"backup_id": run_id},
                    },
                )
                stage = staging_root / run_id
                manifest = export(
                    conn,
                    os.environ["BASELINE_MIGRATION_DSN"],
                    tools,
                    stage,
                    source_project=project,
                    migration_dir=ROOT / "migrations",
                    code_hash=digest(
                        encoded(
                            {
                                p.name: digest(p.read_bytes())
                                for p in sorted(Path(__file__).parent.glob("*.py"))
                            }
                        )
                    ),
                    lock_hash=digest((ROOT / "uv.lock").read_bytes()),
                    archive_files=archive_files,
                    schemas=config["schemas"],
                )
            retain_inputs(manifest, stage, store, archive_files)
            sha = finalize(stage, sync, manifest)
            identity = manifest["backup_id"]
        else:
            identity, sha = args.backup_id, args.manifest_hash
            if not identity or not sha:
                raise BackupError("explicit_backup_identity_required")
        fetched = readback_root / str(uuid4())
        receipt = remote_readback(
            remote,
            fetched,
            backup_id=identity,
            expected_hash=sha,
            source_project=project,
            forbidden_roots=[sync, staging_root],
        )
        if args.operation == "restore":
            with connection("BASELINE_RESTORE_DSN") as conn:
                result.update(
                    restore(
                        conn,
                        os.environ["BASELINE_RESTORE_DSN"],
                        tools,
                        fetched,
                        identity,
                        sha,
                        expected_project=project,
                    )
                )
        if args.operation == "run":
            body = (fetched / "sets" / identity / "manifest.json").read_bytes()
            with connection("BASELINE_MIGRATION_DSN") as conn:
                artifact = retain(
                    conn,
                    store,
                    body,
                    kind="reports",
                    format="json",
                    manifest={"backup_id": identity},
                )
                register(
                    conn,
                    "run_events",
                    {
                        "run_event_id": str(uuid4()),
                        "run_id": run_id,
                        "state": "succeeded",
                        "reason_code": "backup_remote_verified",
                        "details": {
                            "backup_manifest_id": artifact["artifact_id"],
                            "backup_id": identity,
                            "remote_readback_sha256": sha,
                            "backup_cutoff": receipt["represented_cutoff"],
                            "off_device_verified": True,
                            "verified_at": datetime.now(UTC).isoformat(),
                            "files_verified": receipt["files_verified"],
                            "bytes_verified": receipt["bytes_verified"],
                        },
                    },
                )
        result.update(state="verified", **receipt)
    except (BackupError, ArtifactError, DatabaseError, OSError, ValueError, KeyError, TypeError):
        result.update(state="incomplete", reason_code="backup_or_remote_verification_failed")
        if args.operation == "run":
            try:
                with connection("BASELINE_MIGRATION_DSN") as conn:
                    register(
                        conn,
                        "run_events",
                        {
                            "run_event_id": str(uuid4()),
                            "run_id": run_id,
                            "state": "incomplete",
                            "reason_code": "backup_verification_failed",
                            "details": {"off_device_verified": False},
                        },
                    )
            except (DatabaseError, ValueError):
                result["durable_recording_confirmed"] = False
    atomic_json(args.output / "latest-backup.json", result)
    print(json.dumps({k: result[k] for k in ["state", "run_id", "off_device_verified"]}))
    return 0 if result["state"] == "verified" else 1


if __name__ == "__main__":
    raise SystemExit(main())
