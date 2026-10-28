"""Controlled API setup and idempotent database binding on disposable fixtures."""

import json
from dataclasses import replace
from typing import Any
from uuid import UUID

import pytest

from hoop.platform.artifacts import ArtifactError, Response
from hoop.platform.artifacts.setup import provision
from tests.fixtures.storage_client import SETTINGS, USER, MemoryStorage

pytestmark = pytest.mark.postgres


class SetupTransport(MemoryStorage):
    def __init__(self) -> None:
        super().__init__()
        self.users: list[dict[str, str]] = []
        self.buckets: dict[str, Any] = {}

    def request(
        self, method: str, url: str, headers: dict[str, str], body: bytes | None
    ) -> Response:
        if "/auth/v1/token" in url:
            assert headers["apikey"] == SETTINGS.key
            return super().request(method, url, headers, body)
        assert headers["apikey"] == "setup-only-fixture-key"
        if "/admin/users" in url:
            if method == "GET":
                return Response(200, json.dumps({"users": self.users}).encode())
            self.users.append({"id": USER, "email": SETTINGS.email})
            return Response(201, json.dumps(self.users[-1]).encode())
        if method == "GET":
            bucket = self.buckets.get(url.rsplit("/", 1)[-1])
            return (
                Response(404, b"{}")
                if bucket is None
                else Response(200, json.dumps(bucket).encode())
            )
        value = json.loads(body or b"{}")
        assert value["public"] is False
        self.buckets[value["id"]] = value
        return Response(200, b"{}")


def test_repeat_setup_keeps_identity_and_one_binding(migrated: Any) -> None:
    _, conn = migrated
    transport = SetupTransport()
    unbound = replace(SETTINGS, user_id=str(UUID(int=0)))
    first = provision(conn, unbound, "setup-only-fixture-key", transport=transport)
    assert first["backend_user_id"] == USER
    assert not first["hosted_permissions_verified"]
    assert provision(conn, SETTINGS, "setup-only-fixture-key", transport=transport) == first
    assert len(transport.users) == 1 and len(transport.buckets) == 2
    assert conn.execute("SELECT count(*) FROM platform.artifact_storage_bindings").fetchone() == (
        1,
    )


def test_existing_public_bucket_is_refused_without_binding(migrated: Any) -> None:
    _, conn = migrated
    transport = SetupTransport()
    transport.buckets[SETTINGS.bucket] = {"id": SETTINGS.bucket, "public": True}
    with pytest.raises(ArtifactError, match="private_bucket"):
        provision(conn, SETTINGS, "setup-only-fixture-key", transport=transport)
    assert conn.execute("SELECT count(*) FROM platform.artifact_storage_bindings").fetchone() == (
        0,
    )


def test_modern_setup_key_uses_apikey_without_invalid_bearer(migrated: Any) -> None:
    _, conn = migrated

    class ModernTransport(SetupTransport):
        def request(
            self, method: str, url: str, headers: dict[str, str], body: bytes | None
        ) -> Response:
            if "/auth/v1/token" not in url:
                assert headers["apikey"] == "sb_secret_synthetic_fixture_only"
                assert "Authorization" not in headers
                headers = {**headers, "apikey": "setup-only-fixture-key"}
            return super().request(method, url, headers, body)

    report = provision(
        conn,
        replace(SETTINGS, user_id=str(UUID(int=0))),
        "sb_secret_synthetic_fixture_only",
        transport=ModernTransport(),
    )
    assert report["backend_user_id"] == USER


class WrappedMissingBucketTransport(SetupTransport):
    missing_response = Response(
        400, b'{"statusCode":"404","code":"NoSuchBucket","error":"Bucket not found"}'
    )

    def request(
        self, method: str, url: str, headers: dict[str, str], body: bytes | None
    ) -> Response:
        if method == "GET" and "/storage/v1/bucket/" in url:
            if url.rsplit("/", 1)[-1] not in self.buckets:
                return self.missing_response
        return super().request(method, url, headers, body)


def test_hosted_wrapped_missing_bucket_is_created_and_verified(migrated: Any) -> None:
    _, conn = migrated
    transport = WrappedMissingBucketTransport()
    report = provision(conn, SETTINGS, "setup-only-fixture-key", transport=transport)
    assert report["public"] is False and len(transport.buckets) == 2
    assert conn.execute("SELECT count(*) FROM platform.artifact_storage_bindings").fetchone() == (
        1,
    )


@pytest.mark.parametrize(
    "body",
    [
        b'{"statusCode":"403","code":"NoSuchBucket"}',
        b'{"statusCode":"404","code":"AccessDenied"}',
        b'{"statusCode":"404","code":"InvalidRequest"}',
        b'{"code":"NoSuchBucket"}',
        b"invalid-json",
        b"[]",
    ],
)
def test_unrecognized_bucket_errors_do_not_create_or_bind(migrated: Any, body: bytes) -> None:
    _, conn = migrated
    transport = WrappedMissingBucketTransport()
    transport.missing_response = Response(400, body)
    with pytest.raises(ArtifactError, match="controlled_setup_refused"):
        provision(conn, SETTINGS, "setup-only-fixture-key", transport=transport)
    assert not transport.buckets
    assert conn.execute("SELECT count(*) FROM platform.artifact_storage_bindings").fetchone() == (
        0,
    )
