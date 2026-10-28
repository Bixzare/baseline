"""Actual shared snapshots and restoration preserve original ledger evidence."""

import json
import os
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import psycopg
import pytest
from psycopg import sql
from psycopg.conninfo import make_conninfo

from hoop.domains.nba.publication import publish_player
from hoop.platform.backup import (
    ArchiveArtifacts,
    BackupError,
    finalize,
    remote_readback,
    verify_set,
)
from hoop.platform.backup.database import Tools, export, inventory, restore, retain_inputs
from hoop.platform.local_artifacts import checksum
from tests.fixtures.publication import publication_fixture

pytestmark = pytest.mark.postgres


@pytest.fixture
def restore_target() -> Iterator[str]:
    base = os.environ["BASELINE_TEST_DSN"]
    name = "baseline_restore_" + uuid4().hex
    with psycopg.connect(base, autocommit=True) as admin:
        admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
        try:
            target = make_conninfo(base, dbname=name)
            with psycopg.connect(target, autocommit=True) as provider:
                provider.execute(
                    (ROOT / "tests/fixtures/postgres/provider.sql").read_text(), prepare=False
                )
            yield target
        finally:
            assert name.startswith("baseline_restore_") and len(name) == 49
            admin.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(name)))


ROOT = Path(__file__).resolve().parents[2]


class FixtureRemote:
    evidence_kind = "synthetic_remote_fixture"

    def __init__(self, root: Path):
        self.root = root

    def download(self, relative: str, destination: Path, limit: int) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        with (self.root / relative).open("rb") as source, destination.open("xb") as output:
            output.write(source.read(limit))


def tools() -> Tools:
    container = os.environ.get("BASELINE_PG_TOOL_CONTAINER")
    directory = os.environ.get("BASELINE_PG_BIN")
    return Tools(directory=Path(directory) if directory else None, rehearsal_container=container)


def test_snapshot_restore_keeps_ledger_ids_times_and_concurrent_writes_outside_snapshot(
    migrated: Any, restore_target: str, tmp_path: Path
) -> None:
    started = time.monotonic()
    source_dsn, conn = migrated
    p = publication_fixture(conn, tmp_path / "source")
    publish_player(conn, p["store"], p["retained"], UUID(p["bundle"]))
    source_rows = conn.execute(
        "SELECT prediction_id,value FROM platform.predictions ORDER BY prediction_id"
    ).fetchall()
    receipt_rows = conn.execute("TABLE platform.publication_receipts").fetchall()
    archive = tmp_path / "history.csv"
    archive.write_bytes(b"accepted-history-fixture\n")
    files = [
        {
            "label": "history.csv",
            "source": str(archive),
            "sha256": checksum(archive),
            "byte_count": archive.stat().st_size,
        }
    ]
    concurrent_id = str(uuid4())

    def concurrent() -> None:
        with psycopg.connect(source_dsn, autocommit=True) as writer:
            writer.execute(
                "INSERT INTO platform.runs VALUES(%s,'later','synthetic','rehearsal',"
                "'fixture',%s,DEFAULT)",
                (concurrent_id, "a" * 64),
            )

    stage, sync = tmp_path / "stage", tmp_path / "sync"
    manifest = export(
        conn,
        source_dsn,
        tools(),
        stage,
        source_project="fixture_source",
        migration_dir=ROOT / "migrations",
        code_hash="a" * 64,
        lock_hash="b" * 64,
        archive_files=files,
        schemas=["platform", "nba", "api"],
        after_snapshot=concurrent,
    )
    retain_inputs(manifest, stage, p["store"], files)
    sha = finalize(stage, sync, manifest)
    assert finalize(stage, sync, manifest) == sha
    assert len(list((sync / "objects").rglob("*"))) < len(manifest["files"]) * 2 + 5
    receipt = remote_readback(
        FixtureRemote(sync),
        tmp_path / "remote-download",
        backup_id=manifest["backup_id"],
        expected_hash=sha,
        source_project="fixture_source",
        forbidden_roots=[stage, sync],
    )
    assert not receipt["off_device_verified"]
    with psycopg.connect(restore_target, autocommit=True) as target:
        result = restore(
            target,
            restore_target,
            tools(),
            tmp_path / "remote-download",
            manifest["backup_id"],
            sha,
            expected_project="fixture_source",
        )
        assert result["original_rows_preserved"] and not result["automation_enabled"]
        recovered_store = ArchiveArtifacts(tmp_path / "remote-download", manifest["backup_id"], sha)
        for descriptor in manifest["artifact_inventory"]:
            assert recovered_store.read(descriptor) == p["store"].read(descriptor)
        target.execute("SET ROLE baseline_runtime")
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            target.execute("UPDATE platform.predictions SET value=0")
        target.execute("RESET ROLE")
        assert (
            target.execute(
                "SELECT prediction_id,value FROM platform.predictions ORDER BY prediction_id"
            ).fetchall()
            == source_rows
        )
        assert target.execute("TABLE platform.publication_receipts").fetchall() == receipt_rows
        assert (
            target.execute(
                "SELECT 1 FROM platform.runs WHERE run_id=%s", (concurrent_id,)
            ).fetchone()
            is None
        )
        with pytest.raises(BackupError, match="application_schemas"):
            restore(
                target,
                restore_target,
                tools(),
                sync,
                manifest["backup_id"],
                sha,
                expected_project="fixture_source",
            )
        with target.transaction():
            target.execute("SET LOCAL TIME ZONE 'UTC'")
            assert inventory(target, tuple(manifest["schemas"])) == manifest["snapshot_inventory"]
    (tmp_path / "backup-rehearsal.json").write_text(
        json.dumps(
            {
                "evidence": "synthetic_local_postgres",
                "backup_id": manifest["backup_id"],
                "manifest_sha256": sha,
                "represented_cutoff": manifest["represented_cutoff"],
                "tables_verified": result["tables_verified"],
                "predictions_preserved": len(source_rows),
                "receipts_preserved": len(receipt_rows),
                "off_device_verified": False,
                "elapsed_seconds": round(time.monotonic() - started, 3),
                "total_logical_bytes": receipt["bytes_verified"],
                "automation_enabled": False,
            },
            sort_keys=True,
        )
    )
    blob = next(f for f in manifest["files"] if f["label"].startswith("artifact:"))
    (sync / blob["path"]).write_bytes(b"corruption")
    with pytest.raises(BackupError, match="missing_or_corrupt"):
        verify_set(sync, manifest["backup_id"], sha)


def test_missing_artifact_cannot_finalize_a_complete_backup(migrated: Any, tmp_path: Path) -> None:
    dsn, conn = migrated
    publication_fixture(conn, tmp_path / "source")
    manifest = export(
        conn,
        dsn,
        tools(),
        tmp_path / "stage",
        source_project="fixture_source",
        migration_dir=ROOT / "migrations",
        code_hash="a" * 64,
        lock_hash="b" * 64,
        archive_files=[],
        schemas=["platform", "nba", "api"],
    )
    with pytest.raises(BackupError, match="artifact_not_in_complete"):
        finalize(tmp_path / "stage", tmp_path / "sync", manifest)
    assert not (tmp_path / "sync").exists()
