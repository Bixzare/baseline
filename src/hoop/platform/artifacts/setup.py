"""Controlled setup only. Never import administrator credentials into a job."""

import json
import re
from dataclasses import replace
from typing import Any
from uuid import UUID

import psycopg
from psycopg.pq import TransactionStatus

from hoop.platform.artifacts import (
    ArtifactError,
    HTTPTransport,
    Session,
    Settings,
    Transport,
    is_storage_error,
)


def provision(
    conn: psycopg.Connection[Any],
    settings: Settings,
    admin_key: str,
    *,
    transport: Transport | None = None,
    unrelated_bucket: str = "baseline-denied-rehearsal",
) -> dict[str, Any]:
    if not admin_key or admin_key == settings.key:
        raise ArtifactError("separate_setup_credential_required")
    if not conn.autocommit or conn.info.transaction_status != TransactionStatus.IDLE:
        raise ArtifactError("network_requires_no_database_transaction")
    if (
        not re.fullmatch(r"[a-z0-9-]{1,63}", unrelated_bucket)
        or unrelated_bucket == settings.bucket
    ):
        raise ArtifactError("invalid_negative_test_bucket")
    client = transport or HTTPTransport()
    headers = {
        "apikey": admin_key,
        "Content-Type": "application/json",
    }

    if not admin_key.startswith("sb_secret_"):
        # Legacy service JWT compatibility only. Modern keys are not JWTs.
        headers["Authorization"] = "Bearer " + admin_key

    def call(method: str, path: str, value: Any = None) -> Any:
        result = client.request(
            method,
            settings.url + path,
            headers,
            None if value is None else json.dumps(value).encode(),
        )
        # A canonical missing-bucket error is not a generic bad request or denial.
        if (
            method == "GET"
            and path.startswith("/storage/v1/bucket/")
            and is_storage_error(result, code="NoSuchBucket", status=404)
        ):
            return None
        if result.status not in {200, 201, 404}:
            raise ArtifactError("controlled_setup_refused")
        if result.status == 404:
            return None
        try:
            return json.loads(result.body)
        except ValueError:
            raise ArtifactError("invalid_setup_response") from None

    identity = None
    # Bounded, repeatable lookup also recovers a lost user-creation response.
    for page in range(1, 5):
        listing = call("GET", f"/auth/v1/admin/users?page={page}&per_page=50")
        if not isinstance(listing, dict) or not isinstance(listing.get("users"), list):
            raise ArtifactError("invalid_setup_user_listing")
        if any(not isinstance(user, dict) for user in listing["users"]):
            raise ArtifactError("invalid_setup_user_listing")
        matches = [user for user in listing["users"] if user.get("email") == settings.email]
        if matches:
            if len(matches) != 1:
                raise ArtifactError("ambiguous_backend_identity")
            identity = matches[0]
            break
        if len(listing["users"]) < 50:
            break
    else:
        raise ArtifactError("setup_user_inventory_exceeds_budget")
    if identity is None:
        identity = call(
            "POST",
            "/auth/v1/admin/users",
            {
                "email": settings.email,
                "password": settings.password,
                "email_confirm": True,
            },
        )
    try:
        user_id = str(UUID(identity["id"]))
    except (KeyError, TypeError, ValueError):
        raise ArtifactError("invalid_setup_identity") from None
    if settings.user_id != str(UUID(int=0)) and user_id != settings.user_id:
        raise ArtifactError("setup_identity_mismatch")
    bucket = call("GET", f"/storage/v1/bucket/{settings.bucket}")
    if bucket is None:
        call(
            "POST",
            "/storage/v1/bucket",
            {"id": settings.bucket, "name": settings.bucket, "public": False},
        )
        bucket = call("GET", f"/storage/v1/bucket/{settings.bucket}")
    if (
        not isinstance(bucket, dict)
        or bucket.get("id") != settings.bucket
        or bucket.get("public") is not False
    ):
        raise ArtifactError("private_bucket_verification_failed")
    negative = call("GET", f"/storage/v1/bucket/{unrelated_bucket}")
    if negative is None:
        call(
            "POST",
            "/storage/v1/bucket",
            {"id": unrelated_bucket, "name": unrelated_bucket, "public": False},
        )
        negative = call("GET", f"/storage/v1/bucket/{unrelated_bucket}")
    if (
        not isinstance(negative, dict)
        or negative.get("id") != unrelated_bucket
        or negative.get("public") is not False
    ):
        raise ArtifactError("negative_bucket_verification_failed")
    Session(replace(settings, user_id=user_id), client).authenticate()
    # Configuration is data, not manual schema DDL. Append settings only after
    # provider APIs verify the user and private bucket. No privileged fallback.
    with conn.transaction():
        conn.execute("SET LOCAL ROLE baseline_owner")
        current = conn.execute(
            "SELECT backend_user_id,bucket_id FROM platform.artifact_storage_bindings "
            "ORDER BY binding_id DESC LIMIT 1"
        ).fetchone()
        if current != (UUID(user_id), settings.bucket):
            conn.execute(
                "INSERT INTO platform.artifact_storage_bindings(backend_user_id,bucket_id) "
                "VALUES (%s,%s)",
                (user_id, settings.bucket),
            )
    return {
        "backend_user_id": user_id,
        "bucket": settings.bucket,
        "public": False,
        "unrelated_private_bucket": unrelated_bucket,
        "hosted_permissions_verified": False,
    }
