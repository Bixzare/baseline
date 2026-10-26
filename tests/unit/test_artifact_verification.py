"""The manual rehearsal fails if a forbidden API operation succeeds."""

import json
from urllib.parse import urlsplit

import pytest

from hoop.platform.artifacts import Response, Session
from hoop.platform.artifacts.verify import verify
from tests.fixtures.storage_client import SETTINGS, MemoryStorage, other_settings


class RehearsalTransport(MemoryStorage):
    def __init__(self, *, broken: bool = False) -> None:
        super().__init__()
        self.broken = broken
        self.tokens: dict[str, str] = {}

    def request(
        self, method: str, url: str, headers: dict[str, str], body: bytes | None
    ) -> Response:
        path = urlsplit(url).path
        if path == "/auth/v1/token":
            result = super().request(method, url, headers, body)
            payload = json.loads(result.body)
            self.tokens[payload["access_token"]] = json.loads(body or b"{}").get(
                "email", SETTINGS.email
            )
            return result
        token = headers.get("Authorization", "").removeprefix("Bearer ")
        if self.tokens.get(token) != SETTINGS.email:
            return Response(403, b"{}")
        if path.startswith("/rest/v1/"):
            return Response(406, b"{}")
        if method == "PUT":
            return Response(200 if self.broken else 403, b"{}")
        if method in {"DELETE"} or path.endswith("/move") or "negative-bucket" in path:
            return Response(403, b"{}")
        if headers.get("x-upsert") == "true":
            return Response(403, b"{}")
        return super().request(method, url, headers, body)


@pytest.mark.parametrize("broken", [False, True])
def test_rehearsal_is_not_green_after_an_unexpected_permission(broken: bool) -> None:
    transport = RehearsalTransport(broken=broken)
    report = verify(
        Session(SETTINGS, transport), Session(other_settings(), transport), "negative-bucket"
    )
    assert report["verified"] is not broken
    assert report["checks"]["original_bytes_preserved"]
    assert "Bearer" not in json.dumps(report)


def test_existing_concurrent_creation_is_hash_verified_after_conflict() -> None:
    from hoop.platform.artifacts import PrivateArtifacts

    class Race(MemoryStorage):
        raced = False

        def request(
            self, method: str, url: str, headers: dict[str, str], body: bytes | None
        ) -> Response:
            if method == "POST" and "/storage/" in url and not self.raced:
                self.raced = True
                key = urlsplit(url).path.removeprefix("/storage/v1/object/")
                assert body is not None
                self.objects[key] = body
                return Response(409, b"{}")
            return super().request(method, url, headers, body)

    transport = Race()
    assert (
        PrivateArtifacts(Session(SETTINGS, transport)).put(b"hi", kind="raw", format="txt")[
            "byte_count"
        ]
        == 2
    )
    assert len(transport.objects) == 1
