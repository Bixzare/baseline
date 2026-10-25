"""In-memory HTTP boundary. It is not a Supabase emulator or hosted proof."""

import json
from dataclasses import replace
from urllib.parse import urlsplit

from hoop.platform.artifacts import ArtifactError, Response, Settings

USER = "11111111-1111-4111-8111-111111111111"
OTHER = "22222222-2222-4222-8222-222222222222"
SETTINGS = Settings(
    "https://fixture.supabase.co",
    "sb_publishable_fixture",
    "fixture@example.test",
    "not_real",
    USER,
)


class MemoryStorage:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}
        self.calls: list[tuple[str, str]] = []
        self.lost_upload = False
        self.corrupt = False
        self.upload_status = 200
        self.auth_statuses: list[int] = []
        self.renewal_refused = False
        self.force_401 = False
        self.auth_count = 0

    def request(
        self, method: str, url: str, headers: dict[str, str], body: bytes | None
    ) -> Response:
        path = urlsplit(url).path
        self.calls.append((method, path))
        if path == "/auth/v1/token":
            if "refresh_token" in url and self.renewal_refused:
                return Response(400, b"{}")
            if self.auth_statuses:
                status = self.auth_statuses.pop(0)
                if status != 200:
                    return Response(status, b'{"error":"do not retain upstream credentials"}')
            self.auth_count += 1
            payload = json.loads(body or b"{}")
            identity = OTHER if payload.get("email") == "other@example.test" else USER
            return Response(
                200,
                json.dumps(
                    {
                        "access_token": f"access-{self.auth_count}",
                        "refresh_token": f"refresh-{self.auth_count}",
                        "expires_in": 3600,
                        "user": {"id": identity},
                    }
                ).encode(),
            )
        if self.force_401:
            self.force_401 = False
            return Response(401, b"{}")
        key = path.removeprefix("/storage/v1/object/authenticated/").removeprefix(
            "/storage/v1/object/"
        )
        if method == "GET":
            if key not in self.objects:
                return Response(404, b"{}")
            return Response(200, b"corrupt" if self.corrupt else self.objects[key])
        if method == "POST":
            assert headers["x-upsert"] == "false"
            if key in self.objects:
                return Response(409, b"{}")
            if self.upload_status != 200:
                return Response(self.upload_status, b"{}")
            assert body is not None
            self.objects[key] = body
            if self.lost_upload:
                self.lost_upload = False
                raise ArtifactError("transport_failure")
            return Response(200, b"{}")
        raise AssertionError((method, path))


def other_settings() -> Settings:
    return replace(SETTINGS, email="other@example.test", user_id=OTHER)
