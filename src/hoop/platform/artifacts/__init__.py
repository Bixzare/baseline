"""Bounded Supabase Auth/Storage REST client. Sessions stay in job memory."""

import json
import os
import re
import time
from dataclasses import dataclass, field
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
from uuid import UUID, uuid4

import psycopg
from psycopg.pq import TransactionStatus

from hoop.platform.evidence import register, safe_summary
from hoop.platform.provenance import digest

MAX_BYTES = 16 * 1024 * 1024
KINDS = {"raw", "history", "features", "models", "reports"}


class ArtifactError(RuntimeError):
    """Only stable sanitized reason codes cross the client boundary."""


@dataclass(frozen=True)
class Response:
    status: int
    body: bytes


class Transport(Protocol):
    def request(
        self, method: str, url: str, headers: dict[str, str], body: bytes | None
    ) -> Response: ...


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args: Any, **kwargs: Any) -> None:
        return None


class HTTPTransport:
    def request(
        self, method: str, url: str, headers: dict[str, str], body: bytes | None
    ) -> Response:
        request = Request(url, data=body, headers=headers, method=method)
        try:
            response = build_opener(NoRedirect()).open(request, timeout=15)
        except HTTPError as error:
            response = error
        except (URLError, TimeoutError, OSError):
            raise ArtifactError("transport_failure") from None
        try:
            with response:
                content = response.read(MAX_BYTES + 1)
                if len(content) > MAX_BYTES:
                    raise ArtifactError("response_too_large")
                return Response(response.code, content)
        except (TimeoutError, OSError):
            raise ArtifactError("transport_failure") from None


@dataclass(frozen=True)
class Settings:
    url: str
    key: str = field(repr=False)
    email: str = field(repr=False)
    password: str = field(repr=False)
    user_id: str
    bucket: str = "baseline-artifacts"

    def __post_init__(self) -> None:
        parsed = urlsplit(self.url)
        if not (
            parsed.scheme == "https"
            and parsed.hostname
            and re.fullmatch(r"[a-z0-9-]+\.supabase\.co", parsed.hostname)
            and not parsed.username
            and not parsed.password
            and not parsed.port
            and parsed.path in {"", "/"}
            and not parsed.query
            and not parsed.fragment
        ):
            raise ArtifactError("invalid_project_url")
        if not re.fullmatch(r"sb_publishable_[A-Za-z0-9_-]{1,256}", self.key):
            # Current setup uses an explicit publishable key, never a secret or
            # legacy service JWT. Supporting other key forms needs verification.
            raise ArtifactError("publishable_key_required")
        if not self.email or not self.password:
            raise ArtifactError("backend_credentials_missing")
        try:
            UUID(self.user_id)
        except ValueError:
            raise ArtifactError("invalid_backend_identity") from None
        if not re.fullmatch(r"[a-z0-9-]{1,63}", self.bucket):
            raise ArtifactError("unsafe_bucket")

    @classmethod
    def from_env(cls) -> "Settings":
        try:
            return cls(
                os.environ["BASELINE_SUPABASE_URL"].rstrip("/"),
                os.environ["BASELINE_SUPABASE_PUBLISHABLE_KEY"],
                os.environ["BASELINE_ARTIFACT_EMAIL"],
                os.environ["BASELINE_ARTIFACT_PASSWORD"],
                os.environ["BASELINE_ARTIFACT_USER_ID"],
                os.environ.get("BASELINE_ARTIFACT_BUCKET", "baseline-artifacts"),
            )
        except KeyError:
            raise ArtifactError("artifact_environment_missing") from None


class Session:
    def __init__(self, settings: Settings, transport: Transport | None = None) -> None:
        self.settings = settings
        self.transport = transport or HTTPTransport()
        self.access = ""
        self.refresh = ""
        self.expires_at = 0.0

    def authenticate(self, *, renewal: bool = False) -> None:
        data = (
            {"refresh_token": self.refresh}
            if renewal
            else {
                "email": self.settings.email,
                "password": self.settings.password,
            }
        )
        grant = "refresh_token" if renewal else "password"
        for attempt in range(2):
            response = self.transport.request(
                "POST",
                f"{self.settings.url}/auth/v1/token?grant_type={grant}",
                {"apikey": self.settings.key, "Content-Type": "application/json"},
                json.dumps(data).encode(),
            )
            if response.status == 429 or response.status >= 500:
                if attempt == 0:
                    time.sleep(0.1)
                    continue
            break
        if response.status != 200:
            raise ArtifactError("session_renewal_refused" if renewal else "authentication_refused")
        try:
            result = json.loads(response.body)
            if result["user"]["id"] != self.settings.user_id:
                raise ArtifactError("authenticated_identity_mismatch")
            access, refresh = result["access_token"], result["refresh_token"]
            lifetime = float(result["expires_in"])
            if (
                not isinstance(access, str)
                or not access
                or re.fullmatch(r"[A-Za-z0-9_.-]{1,8192}", access) is None
                or not isinstance(refresh, str)
                or not refresh
                or not 30 < lifetime <= 86400
            ):
                raise ValueError
        except (ValueError, KeyError, TypeError):
            raise ArtifactError("invalid_auth_response") from None
        self.access, self.refresh, self.expires_at = access, refresh, time.monotonic() + lifetime

    def request(
        self,
        method: str,
        path: str,
        body: bytes | None = None,
        *,
        headers: dict[str, str] | None = None,
    ) -> Response:
        if not path.startswith("/") or path.startswith("//"):
            raise ArtifactError("unsafe_request_path")
        if not self.access:
            self.authenticate()
        elif time.monotonic() >= self.expires_at - 30:
            self.authenticate(renewal=True)
        for attempt in range(2):
            response = self.transport.request(
                method,
                self.settings.url + path,
                {
                    "apikey": self.settings.key,
                    "Authorization": "Bearer " + self.access,
                    **(headers or {}),
                },
                body,
            )
            if response.status != 401 or attempt == 1:
                return response
            self.authenticate(renewal=True)
        raise ArtifactError("session_request_failed")


class PrivateArtifacts:
    def __init__(self, session: Session) -> None:
        self.session = session

    def put(
        self, body: bytes, *, kind: str, format: str, schema_version: int = 1
    ) -> dict[str, Any]:
        if (
            kind not in KINDS
            or not re.fullmatch(r"[a-z0-9_-]{1,32}", format)
            or type(schema_version) is not int
            or schema_version < 1
        ):
            raise ArtifactError("invalid_artifact_descriptor")
        if len(body) > MAX_BYTES:
            raise ArtifactError("artifact_too_large")
        sha = digest(body)
        key = f"{kind}/{sha[:2]}/{sha}"
        bucket = self.session.settings.bucket
        path = f"/storage/v1/object/{bucket}/{key}"
        download = f"/storage/v1/object/authenticated/{bucket}/{key}"
        response = self.session.request("GET", download)
        if response.status == 404:
            try:
                upload = self.session.request(
                    "POST",
                    path,
                    body,
                    headers={
                        "Content-Type": "application/octet-stream",
                        "x-upsert": "false",
                    },
                )
            except ArtifactError:
                # Lost upload response: verification can recover an existing
                # object. Never resubmit with replacement enabled.
                upload = None
            if upload is not None and upload.status not in {200, 201, 400, 409}:
                raise ArtifactError("upload_refused")
            response = self.session.request("GET", download)
        if response.status != 200:
            raise ArtifactError("artifact_read_failed")
        if len(response.body) != len(body) or digest(response.body) != sha:
            raise ArtifactError("artifact_readback_mismatch")
        project = str(urlsplit(self.session.settings.url).hostname).split(".")[0]
        return {
            "sha256": sha,
            "kind": kind,
            "format": format,
            "schema_version": schema_version,
            "byte_count": len(body),
            "storage_uri": f"supabase://{project}/{bucket}/{key}",
        }


def retain(
    conn: psycopg.Connection[Any],
    store: PrivateArtifacts,
    body: bytes,
    *,
    kind: str,
    format: str,
    manifest: dict[str, Any],
    artifact_id: str | None = None,
) -> dict[str, Any]:
    if not conn.autocommit or conn.info.transaction_status != TransactionStatus.IDLE:
        raise ArtifactError("network_requires_no_database_transaction")
    safe_summary(manifest)
    descriptor = store.put(body, kind=kind, format=format)
    return register(
        conn,
        "artifacts",
        {
            "artifact_id": artifact_id or str(uuid4()),
            **descriptor,
            "manifest": manifest,
        },
    )
