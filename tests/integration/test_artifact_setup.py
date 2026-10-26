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
