"""Do not silently combine Baseline permissions with preexisting allow policies."""

import shutil
from pathlib import Path

import psycopg
import pytest

from hoop.platform.database import DatabaseError, apply

pytestmark = pytest.mark.postgres


def test_existing_storage_policy_requires_review(database: str, tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[2]
    files = tmp_path / "migrations"
    files.mkdir()
    for name in ["0001_foundation.sql", "0002_evidence.sql"]:
        shutil.copy(root / "migrations" / name, files / name)
    with psycopg.connect(database, autocommit=True) as conn:
        apply(conn, files)
        conn.execute("CREATE POLICY existing_policy ON storage.objects FOR SELECT USING (true)")
        shutil.copy(
            root / "migrations/0003_artifact_policies.sql", files / "0003_artifact_policies.sql"
        )
        with pytest.raises(DatabaseError, match="rolled back"):
            apply(conn, files)
        assert conn.execute(
            "SELECT to_regclass('platform.artifact_storage_bindings')"
        ).fetchone() == (None,)
        assert conn.execute("SELECT count(*) FROM platform.schema_migrations").fetchone() == (2,)
