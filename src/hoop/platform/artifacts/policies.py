"""Read-only corroboration of the actual API role and Storage policy boundary."""

import hashlib
import json
from typing import Any

import psycopg
from psycopg.pq import TransactionStatus

from hoop.platform.artifacts import ArtifactError


def policy_evidence(conn: psycopg.Connection[Any]) -> dict[str, Any]:
    if not conn.autocommit or conn.info.transaction_status != TransactionStatus.IDLE:
        raise ArtifactError("policy_evidence_requires_idle_runtime_connection")
    with conn.transaction():
        conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
        identity = conn.execute("SELECT current_user").fetchone()
        if identity != ("baseline_runtime",):
            raise ArtifactError("policy_evidence_requires_restricted_runtime")
        tables = conn.execute(
            "SELECT c.relname,c.relrowsecurity,pg_has_role('authenticated',c.relowner,'MEMBER') "
            "FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace "
            "WHERE n.nspname='storage' AND c.relname IN('objects','buckets') ORDER BY c.relname"
        ).fetchall()
        privileged = conn.execute(
            "SELECT EXISTS(SELECT FROM pg_roles WHERE (rolsuper OR rolbypassrls) "
            "AND pg_has_role('authenticated',oid,'MEMBER'))"
        ).fetchone()
        rows = conn.execute(
            "SELECT tablename,policyname,roles,cmd,permissive,qual,with_check FROM pg_policies "
            "WHERE schemaname='storage' AND tablename IN('objects','buckets') "
            "ORDER BY tablename,policyname"
        ).fetchall()
    expected = [
        ("objects", "baseline_artifact_create", ["authenticated"], "INSERT"),
        ("objects", "baseline_artifact_read", ["authenticated"], "SELECT"),
    ]
    if (
        tables != [("buckets", True, False), ("objects", True, False)]
        or privileged != (False,)
        or [tuple(row[:4]) for row in rows] != expected
    ):
        raise ArtifactError("storage_policy_boundary_not_verified")
    encoded = json.dumps({"tables": tables, "policies": rows}, sort_keys=True).encode()
    return {
        "verified": True,
        "fingerprint": hashlib.sha256(encoded).hexdigest(),
        "api_role": "authenticated",
        "object_mutation_policy_count": 0,
        "bucket_policy_count": 0,
    }
