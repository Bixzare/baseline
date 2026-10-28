"""Actual catalog evidence cannot pass after a broader policy or RLS change."""

from typing import Any

import pytest

from hoop.platform.artifacts import ArtifactError
from hoop.platform.artifacts.policies import policy_evidence

pytestmark = pytest.mark.postgres


def read_as_runtime(conn: Any) -> dict[str, Any]:
    conn.execute("SET ROLE baseline_runtime")
    try:
        return policy_evidence(conn)
    finally:
        conn.execute("RESET ROLE")


def test_actual_catalog_boundary_is_stable_and_requires_runtime(migrated: Any) -> None:
    _, conn = migrated
    with pytest.raises(ArtifactError, match="restricted_runtime"):
        policy_evidence(conn)
    first = read_as_runtime(conn)
    assert first["verified"] and first == read_as_runtime(conn)
    assert first["object_mutation_policy_count"] == 0


@pytest.mark.parametrize(
    "change", ["broader_policy", "rls_disabled", "bucket_policy", "api_owns_objects", "api_bypass"]
)
def test_unexpected_storage_policy_boundary_is_refused(migrated: Any, change: str) -> None:
    _, conn = migrated
    if change == "broader_policy":
        conn.execute(
            "CREATE POLICY bad_update ON storage.objects FOR UPDATE TO authenticated USING(true)"
        )
    elif change == "rls_disabled":
        conn.execute("ALTER TABLE storage.objects DISABLE ROW LEVEL SECURITY")
    elif change == "bucket_policy":
        conn.execute(
            "CREATE POLICY bad_bucket ON storage.buckets FOR SELECT TO authenticated USING(true)"
        )
    elif change == "api_owns_objects":
        conn.execute("ALTER TABLE storage.objects OWNER TO authenticated")
    else:
        conn.execute("ALTER ROLE authenticated BYPASSRLS")
    try:
        with pytest.raises(ArtifactError, match="storage_policy_boundary_not_verified"):
            read_as_runtime(conn)
    finally:
        if change == "api_bypass":
            conn.execute("ALTER ROLE authenticated NOBYPASSRLS")
