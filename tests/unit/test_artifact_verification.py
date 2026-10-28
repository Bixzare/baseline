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


@pytest.mark.parametrize("inconclusive", [None, "concealed_mutation", "empty_delete"])
def test_wrapped_denials_preserve_strict_mutation_checks(inconclusive: str | None) -> None:
    class WrappedDenials(RehearsalTransport):
        def request(self, method, url, headers, body):
            if inconclusive == "concealed_mutation" and method == "PUT":
                return Response(400, b'{"code":"NoSuchKey","statusCode":"404"}')
            if inconclusive == "empty_delete" and method == "DELETE":
                return Response(200, b"[]")
            result = super().request(method, url, headers, body)
            if result.status == 403:
                return Response(400, b'{"code":"AccessDenied","statusCode":"403"}')
            return result

    transport = WrappedDenials()
    report = verify(
        Session(SETTINGS, transport), Session(other_settings(), transport), "negative-bucket"
    )
    assert report["verified"] is (inconclusive is None)
    assert report["checks"]["original_bytes_preserved"]
    if inconclusive == "concealed_mutation":
        assert not report["checks"]["replacement"]["denied"]
    elif inconclusive == "empty_delete":
        assert not report["checks"]["delete"]["denied"]


@pytest.mark.parametrize(
    "failure",
    [
        None,
        "generic_move",
        "destination_created",
        "changed_bytes",
        "policy_changed",
        "invalid_claim",
        "delete_nonempty",
    ],
)
def test_policy_evidence_requires_corroborated_unchanged_resources(failure: str | None) -> None:
    import base64

    class HostedShapes(RehearsalTransport):
        def request(self, method, url, headers, body):
            path = urlsplit(url).path
            if path == "/auth/v1/token":
                response = super().request(method, url, headers, body)
                payload = json.loads(response.body)
                email = json.loads(body or b"{}").get("email", SETTINGS.email)
                claims = {
                    "role": "service_role" if failure == "invalid_claim" else "authenticated",
                    "sub": payload["user"]["id"],
                }
                token = (
                    "fixture."
                    + base64.urlsafe_b64encode(json.dumps(claims).encode()).decode().rstrip("=")
                    + ".signature"
                )
                self.tokens[token] = email
                payload["access_token"] = token
                return Response(200, json.dumps(payload).encode())
            token = headers.get("Authorization", "").removeprefix("Bearer ")
            backend = self.tokens.get(token) == SETTINGS.email
            if backend and method == "DELETE":
                if failure == "changed_bytes":
                    self.objects.clear()
                return Response(200, b'["unexpected"]' if failure == "delete_nonempty" else b"[]")
            if backend and path.endswith("/move"):
                data = json.loads(body)
                if failure == "destination_created":
                    self.objects[data["bucketId"] + "/" + data["destinationKey"]] = b"unexpected"
                return (
                    Response(404, b"{}")
                    if failure == "generic_move"
                    else Response(400, b'{"code":"NoSuchKey","statusCode":"404"}')
                )
            if backend and method == "PUT" and "/bucket/" in path:
                return Response(400, b'{"code":"NoSuchBucket","statusCode":"404"}')
            return super().request(method, url, headers, body)

    calls = []

    def policies():
        calls.append(True)
        return {
            "verified": True,
            "fingerprint": "changed" if failure == "policy_changed" and len(calls) > 1 else "same",
        }

    transport = HostedShapes()
    if failure == "invalid_claim":
        from hoop.platform.artifacts import ArtifactError

        with pytest.raises(ArtifactError, match="api_role_claim"):
            verify(
                Session(SETTINGS, transport),
                Session(other_settings(), transport),
                "negative-bucket",
                policies=policies,
            )
        assert not transport.objects
        return
    report = verify(
        Session(SETTINGS, transport),
        Session(other_settings(), transport),
        "negative-bucket",
        policies=policies,
    )
    assert report["verified"] is (failure is None)
    if failure is None:
        assert report["checks"]["delete"]["prevention_verified"]
        assert not report["checks"]["delete"]["denied"]
        assert report["checks"]["move"]["prevention_verified"]
        assert report["checks"]["bucket_admin"]["prevention_verified"]
