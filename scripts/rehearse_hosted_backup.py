"""Manual current-state export/restore rehearsal; never a launch-complete backup."""

import argparse
import hashlib
import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any
from uuid import uuid4

import psycopg
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict, make_conninfo

from hoop.platform.artifacts import ArtifactError, PrivateArtifacts, Session, Settings
from hoop.platform.backup import (
    ArchiveArtifacts,
    BackupError,
    finalize,
    remote_readback,
    verify_set,
)
from hoop.platform.backup.database import Tools, export, restore, retain_inputs
from hoop.platform.backup.onedrive import OneDrive
from hoop.platform.database import DatabaseError, connection


def local_restore_admin(dsn: str) -> None:
    options = {key: str(value) for key, value in conninfo_to_dict(dsn).items() if value is not None}
    if options.get("host") not in {"localhost", "127.0.0.1", "::1"} or not options.get(
        "dbname", ""
    ).startswith("baseline_test"):
        raise BackupError("rehearsal_restore_requires_explicit_local_test_admin")


def project(*, require_source_dsn: bool = False) -> str:
    value = os.environ["BASELINE_BACKUP_PROJECT_ID"]
    if os.environ["BASELINE_SUPABASE_URL"].rstrip("/") != f"https://{value}.supabase.co":
        raise BackupError("rehearsal_project_mismatch")
    if not require_source_dsn:
        return value
    options = {
        key: str(item)
        for key, item in conninfo_to_dict(os.environ["BASELINE_MIGRATION_DSN"]).items()
        if item is not None
    }
    if options.get("sslmode") != "verify-full" or not (
        options.get("user") == "postgres." + value
        and options.get("host", "").endswith(".pooler.supabase.com")
        or options.get("user") == "postgres"
        and options.get("host") == f"db.{value}.supabase.co"
    ):
        raise BackupError("rehearsal_source_identity_mismatch")
    return value


def export_current(output: Path, *, archive_inventory: Path | None = None) -> dict[str, Any]:
    archives = json.loads(archive_inventory.read_text()) if archive_inventory else []
    if not isinstance(archives, list) or archive_inventory is not None and not archives:
        raise BackupError("nonempty_reviewed_archive_inventory_required")
    labels = set()
    for item in archives:
        if (
            not isinstance(item, dict)
            or set(item) != {"label", "source", "sha256", "byte_count"}
            or not all(isinstance(item[k], str) for k in ["label", "source", "sha256"])
            or type(item["byte_count"]) is not int
            or item["byte_count"] < 0
            or item["label"] in labels
        ):
            raise BackupError("invalid_reviewed_archive_inventory")
        labels.add(item["label"])
    implementation = subprocess.run(
        [
            "git",
            "diff",
            "--quiet",
            "HEAD",
            "--",
            "scripts/rehearse_hosted_backup.py",
            "src/hoop/platform/backup",
        ],
        capture_output=True,
        timeout=10,
    )
    if implementation.returncode:
        raise BackupError("backup_implementation_must_be_committed")
    source = project(require_source_dsn=True)
    stage = Path(os.environ["BASELINE_BACKUP_STAGING_DIR"]) / ("prelaunch-" + uuid4().hex)
    with connection("BASELINE_MIGRATION_DSN") as conn:
        manifest = export(
            conn,
            os.environ["BASELINE_MIGRATION_DSN"],
            Tools(directory=Path(os.environ["BASELINE_PG_BIN"])),
            stage,
            source_project=source,
            migration_dir=Path("migrations"),
            code_hash=subprocess.run(
                ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True
            ).stdout.strip(),
            lock_hash=hashlib.sha256(Path("uv.lock").read_bytes()).hexdigest(),
            archive_files=archives,
            schemas=["platform", "nba", "api"],
        )
    retain_inputs(manifest, stage, PrivateArtifacts(Session(Settings.from_env())), archives)
    manifest.update(
        scope=(
            "hosted-prelaunch-application-and-reviewed-history"
            if archives
            else "hosted-prelaunch-application-export-only"
        ),
        launch_backup_gate_satisfied=False,
    )
    sha = finalize(stage, Path(os.environ["BASELINE_BACKUP_SYNC_DIR"]), manifest)
    result = {
        "backup_id": manifest["backup_id"],
        "manifest_sha256": sha,
        "project": source,
        "represented_cutoff": manifest["represented_cutoff"],
        "scope": manifest["scope"],
        "archive_count": manifest["archive_count"],
        "launch_backup_gate_satisfied": False,
    }
    output.mkdir(parents=True, exist_ok=True)
    (output / "hosted-export.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def restore_downloaded(output: Path, *, readback_seconds: int = 180) -> dict[str, Any]:
    if type(readback_seconds) is not int or not 1 <= readback_seconds <= 1800:
        raise BackupError("bounded_readback_budget_required")
    reference = json.loads((output / "hosted-export.json").read_text())
    source = project()
    if reference["project"] != source:
        raise BackupError("rehearsal_reference_project_mismatch")
    base = os.environ["BASELINE_RESTORE_ADMIN_DSN"]
    local_restore_admin(base)
    target_name = "baseline_restore_" + uuid4().hex
    readback = Path(os.environ["BASELINE_BACKUP_READBACK_DIR"]) / ("rehearsal-" + uuid4().hex)
    remote = OneDrive(
        Path(os.environ["BASELINE_RCLONE_BIN"]),
        os.environ["BASELINE_BACKUP_REMOTE"],
        os.environ["BASELINE_RCLONE_VERSION"],
    )
    started = time.monotonic()
    receipt = remote_readback(
        remote,
        readback,
        backup_id=reference["backup_id"],
        expected_hash=reference["manifest_sha256"],
        source_project=source,
        forbidden_roots=[
            Path(os.environ["BASELINE_BACKUP_SYNC_DIR"]),
            Path(os.environ["BASELINE_BACKUP_STAGING_DIR"]),
        ],
        max_seconds=readback_seconds,
    )
    manifest = verify_set(readback, reference["backup_id"], reference["manifest_sha256"])
    with psycopg.connect(base, autocommit=True, connect_timeout=5) as admin:
        admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(target_name)))
        try:
            target = make_conninfo(base, dbname=target_name)
            with psycopg.connect(target, autocommit=True, connect_timeout=5) as conn:
                conn.execute(
                    Path("tests/fixtures/postgres/provider.sql").read_text(), prepare=False
                )
                result = restore(
                    conn,
                    target,
                    Tools(directory=Path(os.environ["BASELINE_PG_BIN"])),
                    readback,
                    reference["backup_id"],
                    reference["manifest_sha256"],
                    expected_project=source,
                )
                archive = ArchiveArtifacts(
                    readback, reference["backup_id"], reference["manifest_sha256"]
                )
                for item in manifest["artifact_inventory"]:
                    if hashlib.sha256(archive.read(item)).hexdigest() != item["sha256"]:
                        raise BackupError("restored_artifact_mismatch")
                conn.execute("SET ROLE baseline_runtime")
                try:
                    conn.execute("UPDATE platform.predictions SET value=0")
                except psycopg.errors.InsufficientPrivilege:
                    denied = True
                else:
                    raise BackupError("restored_runtime_mutation_not_denied")
        finally:
            if not target_name.startswith("baseline_restore_") or len(target_name) != 49:
                raise BackupError("rehearsal_cleanup_identity_mismatch")
            admin.execute(
                sql.SQL("DROP DATABASE {} WITH(FORCE)").format(sql.Identifier(target_name))
            )
    result.update(receipt)
    result.update(
        scope=manifest["scope"],
        required_artifacts_verified=len(manifest["artifact_inventory"]),
        runtime_mutation_denied=denied,
        isolated_target_removed=True,
        elapsed_seconds=round(time.monotonic() - started, 3),
        readback_budget_seconds=readback_seconds,
        launch_backup_gate_satisfied=False,
        archive_count=manifest["archive_count"],
    )
    (output / "hosted-restore.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "operation", choices=["plan", "export", "restore"], nargs="?", default="plan"
    )
    parser.add_argument("--output", type=Path, default=Path("artifacts/hosted-backup-rehearsal"))
    parser.add_argument("--readback-seconds", type=int, default=180)
    parser.add_argument("--archive-inventory", type=Path)
    args = parser.parse_args()
    try:
        result = (
            {"mode": "plan", "automation_enabled": False, "launch_backup_gate_satisfied": False}
            if args.operation == "plan"
            else export_current(args.output, archive_inventory=args.archive_inventory)
            if args.operation == "export"
            else restore_downloaded(args.output, readback_seconds=args.readback_seconds)
        )
        print(json.dumps(result, sort_keys=True))
        return 0
    except (
        BackupError,
        DatabaseError,
        ArtifactError,
        OSError,
        ValueError,
        KeyError,
        psycopg.Error,
    ) as error:
        failure = {
            "verified": False,
            "reason_code": "hosted_backup_rehearsal_failed",
            "failure_type": type(error).__name__,
        }
        safe_reasons = {
            "remote_readback_budget_exhausted",
            "onedrive_remote_readback_failed",
            "onedrive_remote_readback_unavailable",
            "onedrive_batch_readback_failed",
            "onedrive_batch_readback_unavailable",
            "backup_implementation_must_be_committed",
        }
        if isinstance(error, BackupError) and str(error) in safe_reasons:
            failure["failure_detail"] = str(error)
        print(json.dumps(failure))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
