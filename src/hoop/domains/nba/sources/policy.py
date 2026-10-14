"""Sequential requests, bounded retries, raw retention, and truthful failures."""

import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

from hoop.platform.provenance import Archive, utc

USER_AGENT = "Baseline-source-probe/0.1 (NBA capability verification)"


@dataclass(frozen=True)
class Policy:
    min_gap: float = 3
    timeout: float = 30
    retries: int = 2
    max_requests: int = 16
    max_seconds: float = 180

    def __post_init__(self) -> None:
        if not (3 <= self.min_gap <= 60 and 0 < self.timeout <= 30 and 0 <= self.retries <= 2):
            raise ValueError("Policy requires gap >=3s, timeout <=30s, and at most two retries")
        if not (1 <= self.max_requests <= 100 and 0 < self.max_seconds <= 600):
            raise ValueError("Invalid request/time budget")


@dataclass(frozen=True)
class ProbeRequest:
    capability: str
    url: str
    environment: str
    context: dict[str, Any]

    def __post_init__(self) -> None:
        parsed = urlparse(self.url)
        if parsed.scheme != "https" or parsed.username or parsed.password or parsed.fragment:
            raise ValueError("Request must use credential-free HTTPS")
        if parsed.hostname not in {"cdn.nba.com", "stats.nba.com"}:
            raise ValueError("Unsupported source hostname")
        if any(
            k.lower() in {"token", "key", "api_key", "authorization"}
            for k in parse_qs(parsed.query)
        ):
            raise ValueError("Credential query parameters are forbidden")
        if self.environment not in {"local", "github-actions", "cloud-development"}:
            raise ValueError("Unknown execution environment")
        if parsed.hostname == "stats.nba.com" and self.environment != "local":
            raise ValueError("stats.nba.com requests are local-machine only")


@dataclass(frozen=True)
class Response:
    status: int
    body: bytes
    headers: dict[str, str]
    complete: bool = True


class Transport(Protocol):
    def get(self, url: str, timeout: float) -> Response: ...


class Clock(Protocol):
    def now(self) -> datetime: ...
    def monotonic(self) -> float: ...
    def sleep(self, seconds: float) -> None: ...


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(UTC)

    def monotonic(self) -> float:
        return time.monotonic()

    def sleep(self, seconds: float) -> None:
        time.sleep(seconds)


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(
        self, req: Any, fp: Any, code: int, msg: str, headers: Any, newurl: str
    ) -> None:
        # A redirect must not silently change source, request identity, or cloud routing.
        return None


class HTTPTransport:
    def get(self, url: str, timeout: float) -> Response:
        request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
        opener = build_opener(NoRedirect())
        try:
            response = opener.open(request, timeout=timeout)
        except HTTPError as error:
            response = error
        with response:
            body = response.read(8 * 1024 * 1024 + 1)
            return Response(
                response.code,
                body,
                {key.lower(): value for key, value in response.headers.items()},
                len(body) <= 8 * 1024 * 1024,
            )


class Validator(Protocol):
    def __call__(self, body: bytes, request: ProbeRequest, now: datetime) -> dict[str, Any]: ...


class ProbeRunner:
    def __init__(
        self, archive: Archive, transport: Transport, clock: Clock, policy: Policy, run_id: str
    ) -> None:
        self.archive = archive
        self.transport = transport
        self.clock = clock
        self.policy = policy
        self.run_id = run_id
        self.started = clock.monotonic()
        self.last_end: float | None = None
        self.requests = 0
        self.blocked: set[str] = set()
        self.observations: list[dict[str, Any]] = []

    def remaining(self) -> float:
        return self.policy.max_seconds - (self.clock.monotonic() - self.started)

    def save(self, request: ProbeRequest, **fields: Any) -> dict[str, Any]:
        result = self.archive.observation(
            {
                "run_id": self.run_id,
                "capability": request.capability,
                "source": urlparse(request.url).hostname,
                "environment": request.environment,
                "request_url": request.url,
                "request_context": request.context,
                "parser_version": "nba-source-probe-v1",
                "policy": asdict(self.policy),
                "requested_at": None,
                "received_at": None,
                "validated_at": None,
                "completed_at": utc(self.clock.now()),
                "source_publication_time": None,
                "http_status": None,
                "raw_sha256": None,
                "raw_path": None,
                "record_count": None,
                **fields,
            }
        )
        self.observations.append(result)
        return result

    def fetch(self, request: ProbeRequest, validate: Validator) -> dict[str, Any]:
        source = str(urlparse(request.url).hostname)
        if source in self.blocked:
            return self.save(
                request, outcome="unverified", reason="source_stopped_after_access_denial"
            )
        for attempt in range(self.policy.retries + 1):
            gap = (
                0
                if self.last_end is None
                else max(0, self.policy.min_gap - (self.clock.monotonic() - self.last_end))
            )
            if self.requests >= self.policy.max_requests or self.remaining() <= gap:
                return self.save(
                    request, outcome="unverified", reason="request_or_time_budget_exhausted"
                )
            self.clock.sleep(gap)
            requested = utc(self.clock.now())
            self.requests += 1
            response: Response | None = None
            failure = ""
            try:
                response = self.transport.get(
                    request.url, min(self.policy.timeout, self.remaining())
                )
            except (TimeoutError, OSError, URLError) as error:
                failure = f"temporary_network_failure: {type(error).__name__}"
            received = utc(self.clock.now()) if response is not None else None
            self.last_end = self.clock.monotonic()
            fields: dict[str, Any] = {
                "attempt": attempt + 1,
                "requested_at": requested,
                "received_at": received,
            }
            retry = response is None
            if response is not None:
                checksum, path = self.archive.raw(response.body)  # Always before parsing.
                fields.update(
                    http_status=response.status,
                    raw_sha256=checksum,
                    raw_path=path,
                    raw_complete=response.complete,
                )
                stripped = response.body.lstrip().lower()
                denied = response.status in {401, 403} or stripped.startswith(
                    (b"<!doctype html", b"<html")
                )
                if denied:
                    self.blocked.add(source)
                    return self.save(
                        request,
                        **fields,
                        outcome="failed",
                        reason="access_denied_or_html_challenge",
                    )
                retry = response.status == 429 or response.status in {500, 502, 503, 504}
                failure = f"http_{response.status}"
                if response.status == 200 and response.complete:
                    try:
                        summary = validate(response.body, request, self.clock.now())
                    except (ValueError, KeyError, TypeError) as error:
                        return self.save(
                            request, **fields, outcome="failed", reason=f"invalid_payload: {error}"
                        )
                    return self.save(
                        request,
                        **fields,
                        outcome="verified_sample",
                        reason=None,
                        validated_at=utc(self.clock.now()),
                        record_count=summary["record_count"],
                        summary=summary,
                    )
                if not response.complete:
                    retry = False
                    failure = "body_exceeds_8MiB_limit; archived_prefix_only"
            delay = self.policy.min_gap
            if response is not None and "retry-after" in response.headers:
                try:
                    value = response.headers["retry-after"]
                    try:
                        delay = max(delay, float(value))
                    except ValueError:
                        delay = max(
                            delay, (parsedate_to_datetime(value) - self.clock.now()).total_seconds()
                        )
                except (ValueError, TypeError, OverflowError):
                    retry = False
                    failure = "invalid_retry_after; stopping_without_retry"
            if retry and delay >= self.remaining():
                retry = False
                failure = "retry_after_exceeds_run_budget"
            result = self.save(
                request,
                **fields,
                outcome="failed",
                reason=failure,
                retry_scheduled=retry and attempt < self.policy.retries,
            )
            if not retry or attempt == self.policy.retries:
                return result
            self.clock.sleep(delay)
        raise AssertionError("Unreachable retry state")
