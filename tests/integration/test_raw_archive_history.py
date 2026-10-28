"""Restricted-role seed provenance survives encoded storage and exact reruns."""

import json
from pathlib import Path
from typing import Any

import psycopg
import pytest
from psycopg.conninfo import make_conninfo
from psycopg.rows import dict_row

from hoop.domains.nba.history.raw import stage_raw_archives
from hoop.domains.nba.history.seed import apply_seed, plan_seed
from hoop.platform.artifacts import ArtifactError, PrivateArtifacts, Session
from hoop.platform.database import provision_runtime
from hoop.platform.local_artifacts import LocalArtifacts
from hoop.platform.raw_archives import materialize_raw
from tests.fixtures.history_seed import fixture_seed
from tests.fixtures.storage_client import SETTINGS, MemoryStorage

pytestmark = pytest.mark.postgres


def test_encoded_seed_preserves_original_source_and_all_registered_parts(
    migrated: Any, tmp_path: Path
) -> None:
    dsn, owner = migrated
    provision_runtime(owner, "synthetic_fixture_password_only")
    local_root = tmp_path / "archive"
    report, manifest, direct = fixture_seed(local_root)
    staged = stage_raw_archives(report, local_root)
    plan = plan_seed(
        report, local_root, manifest, direct["acceptance"], direct["observations"], staged
    )
    assert not plan["blockers"]
    transport = MemoryStorage()
    store = PrivateArtifacts(Session(SETTINGS, transport))
    with psycopg.connect(
        make_conninfo(dsn, user="baseline_runtime", password="synthetic_fixture_password_only"),
        autocommit=True,
    ) as conn:
        first = apply_seed(conn, store, plan, local_root, tmp_path / "checkpoint.json")
        artifact_count = conn.execute("SELECT count(*) FROM platform.artifacts").fetchone()[0]
        assert apply_seed(conn, store, plan, local_root, tmp_path / "checkpoint.json") == first
        assert (
            conn.execute("SELECT count(*) FROM platform.artifacts").fetchone()[0] == artifact_count
        )
        with conn.cursor(row_factory=dict_row) as cursor:
            checks = cursor.execute("SELECT * FROM platform.source_checks").fetchall()
            artifacts = cursor.execute("SELECT * FROM platform.artifacts").fetchall()
        by_id = {str(a["artifact_id"]): a for a in artifacts}
        payloads = {a["sha256"]: store.read(a) for a in artifacts}
        originals = set(manifest["files"].values())
        assert len(checks) == 4
        for check in checks:
            raw = by_id[str(check["raw_artifact_id"])]
            assert raw["format"] == "json" and raw["sha256"] not in originals
            summary = check["validation_summary"]
            assert summary["raw_representation"] == "gzip_parts_v1"
            assert summary["original_raw_sha256"] in originals
            encoded = json.loads(store.read(raw))
            for part in encoded["parts"]:
                assert by_id[part["artifact_id"]]["sha256"] == part["sha256"]
            restored = materialize_raw(raw, store.read, tmp_path / "restored" / raw["sha256"])
            source = next(
                a for a in report["artifacts"] if a["sha256"] == summary["original_raw_sha256"]
            )
            assert restored.read_bytes() == LocalArtifacts(local_root).verify(source).read_bytes()
            # Backup readers can use saved physical objects without the provider.
            assert (
                materialize_raw(
                    raw,
                    lambda part: payloads[part["sha256"]],
                    tmp_path / "off-provider" / raw["sha256"],
                ).read_bytes()
                == restored.read_bytes()
            )
        assert conn.execute("SELECT count(*) FROM platform.predictions").fetchone() == (0,)
        assert conn.execute("SELECT count(*) FROM nba.roster_snapshots").fetchone() == (0,)
        transport.corrupt = True
        with pytest.raises(ArtifactError):
            materialize_raw(raw, store.read, tmp_path / "must-not-finalize")
        assert not (tmp_path / "must-not-finalize").exists()
