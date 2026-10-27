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


@pytest.mark.parametrize("claim_kind", ["legacy", "json"])
def test_identity_gate_needs_no_auth_schema_access(migrated, claim_kind: str) -> None:
    from uuid import uuid4

    _, conn = migrated
    identity, outsider = str(uuid4()), str(uuid4())
    conn.execute("REVOKE USAGE ON SCHEMA auth FROM PUBLIC,baseline_owner")
    conn.execute(
        "INSERT INTO platform.artifact_storage_bindings(backend_user_id,bucket_id) "
        "VALUES(%s,'baseline-artifacts')",
        (identity,),
    )
    conn.execute("SET ROLE authenticated")
    conn.execute("SELECT set_config('request.jwt.claim.sub','',false)")
    conn.execute("SELECT set_config('request.jwt.claims','',false)")
    assert conn.execute(
        "SELECT platform.artifact_identity_allowed('baseline-artifacts')"
    ).fetchone() == (False,)
    if claim_kind == "legacy":
        conn.execute("SELECT set_config('request.jwt.claim.sub',%s,false)", (identity,))
    else:
        import json

        conn.execute(
            "SELECT set_config('request.jwt.claims',%s,false)",
            (json.dumps({"sub": identity, "role": "authenticated"}),),
        )
    assert conn.execute(
        "SELECT platform.artifact_identity_allowed('baseline-artifacts')"
    ).fetchone() == (True,)
    assert conn.execute(
        "SELECT platform.artifact_identity_allowed('another-bucket')"
    ).fetchone() == (False,)
    conn.execute("SELECT set_config('request.jwt.claim.sub',%s,false)", (outsider,))
    assert conn.execute(
        "SELECT platform.artifact_identity_allowed('baseline-artifacts')"
    ).fetchone() == (False,)
    conn.execute("RESET ROLE")
    assert not conn.execute(
        "SELECT has_schema_privilege('baseline_owner','auth','USAGE')"
    ).fetchone()[0]
    assert not conn.execute(
        "SELECT pg_has_role('baseline_owner','authenticated','MEMBER')"
    ).fetchone()[0]

    assert not conn.execute(
        "SELECT has_function_privilege('baseline_runtime',"
        "'platform.artifact_identity_allowed(text)','EXECUTE')"
    ).fetchone()[0]
