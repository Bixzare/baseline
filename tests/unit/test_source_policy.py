"""Failure policies use deterministic mocked transport and clocks, never live NBA."""

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from hoop.domains.nba.sources.policy import Policy, ProbeRequest, ProbeRunner, Response
from hoop.domains.nba.sources.validate import validate
from hoop.platform.provenance import Archive

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "nba"


class FakeClock:
    def __init__(self) -> None:
        self.elapsed = 0.0
        self.sleeps: list[float] = []

    def monotonic(self) -> float:
        return self.elapsed

    def now(self) -> datetime:
        return datetime(2026, 10, 14, 23, 30, tzinfo=UTC) + timedelta(seconds=self.elapsed)

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.elapsed += seconds


class FakeTransport:
    def __init__(self, responses: list[Response | Exception]) -> None:
        self.responses = responses
        self.calls: list[tuple[str, float]] = []

    def get(self, url: str, timeout: float) -> Response:
        self.calls.append((url, timeout))
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def request() -> ProbeRequest:
    return ProbeRequest(
        "status", "https://cdn.nba.com/status.json", "github-actions", {"season": "2026-27"}
    )


def valid_response() -> Response:
    return Response(200, (FIXTURES / "scoreboard.json").read_bytes(), {})


def runner(
    tmp_path: Path, responses: list[Response | Exception], **policy: float | int
) -> ProbeRunner:
    return ProbeRunner(
        Archive(tmp_path), FakeTransport(responses), FakeClock(), Policy(**policy), "test-run"
    )


@pytest.mark.parametrize("failure", [TimeoutError(), OSError(), Response(503, b"{}", {})])
def test_temporary_failure_then_success_is_retained(
    tmp_path: Path, failure: Response | Exception
) -> None:
    probe = runner(tmp_path, [failure, valid_response()])
    result = probe.fetch(request(), validate)
    assert result["outcome"] == "verified_sample"
    assert probe.requests == 2
    assert probe.observations[0]["outcome"] == "failed"
    assert probe.observations[0]["retry_scheduled"] is True
    assert probe.archive.verify() == 2
    assert probe.clock.monotonic() == 3


def test_retries_are_exhausted_after_three_attempts(tmp_path: Path) -> None:
    probe = runner(tmp_path, [TimeoutError(), TimeoutError(), TimeoutError()])
    assert probe.fetch(request(), validate)["outcome"] == "failed"
    assert probe.requests == 3
    assert probe.observations[-1]["retry_scheduled"] is False


@pytest.mark.parametrize(
    "status,body", [(403, b"{}"), (401, b"{}"), (200, b"<html>captcha</html>")]
)
def test_denial_stops_source_without_retry_or_another_endpoint(
    tmp_path: Path, status: int, body: bytes
) -> None:
    probe = runner(tmp_path, [Response(status, body, {})])
    assert probe.fetch(request(), validate)["reason"] == "access_denied_or_html_challenge"
    other = ProbeRequest("schedule", "https://cdn.nba.com/schedule.json", "github-actions", {})
    assert probe.fetch(other, validate)["reason"] == "source_stopped_after_access_denial"
    assert probe.requests == 1
    assert probe.archive.verify() == 2


@pytest.mark.parametrize("header", ["10", "Wed, 14 Oct 2026 23:30:10 GMT"])
def test_retry_after_is_honored(tmp_path: Path, header: str) -> None:
    probe = runner(tmp_path, [Response(429, b"{}", {"retry-after": header}), valid_response()])
    assert probe.fetch(request(), validate)["outcome"] == "verified_sample"
    assert probe.clock.monotonic() == 10


def test_retry_after_exceeds_budget_stops_without_sleep(tmp_path: Path) -> None:
    probe = runner(tmp_path, [Response(429, b"{}", {"retry-after": "181"})])
    assert probe.fetch(request(), validate)["reason"] == "retry_after_exceeds_run_budget"
    assert probe.requests == 1
    assert probe.clock.monotonic() == 0


def test_malformed_retry_after_cannot_trigger_unbounded_sleep(tmp_path: Path) -> None:
    probe = runner(tmp_path, [Response(429, b"{}", {"retry-after": "later"})])
    assert (
        probe.fetch(request(), validate)["reason"] == "invalid_retry_after; stopping_without_retry"
    )
    assert probe.requests == 1


def test_request_budget_records_incomplete_assessment(tmp_path: Path) -> None:
    probe = runner(tmp_path, [valid_response()], max_requests=1)
    probe.fetch(request(), validate)
    result = probe.fetch(request(), validate)
    assert result["outcome"] == "unverified"
    assert result["reason"] == "request_or_time_budget_exhausted"
    assert result["http_status"] is None and result["received_at"] is None


def test_time_budget_prevents_next_gap_and_caps_timeout(tmp_path: Path) -> None:
    probe = runner(tmp_path, [valid_response()], max_seconds=2)
    probe.fetch(request(), validate)
    transport = probe.transport
    assert isinstance(transport, FakeTransport)
    assert transport.calls[0][1] == 2
    assert probe.fetch(request(), validate)["outcome"] == "unverified"
    assert probe.requests == 1


def test_raw_bytes_exist_before_parser_runs(tmp_path: Path) -> None:
    probe = runner(tmp_path, [valid_response()])

    def parser(body: bytes, item: ProbeRequest, now: datetime) -> dict[str, int]:
        assert list((tmp_path / "raw").glob("*.bin"))[0].read_bytes() == body
        return {"record_count": 1}

    assert probe.fetch(request(), parser)["outcome"] == "verified_sample"


@pytest.mark.parametrize("body", [b"{broken", b"[]", b"{}", b'{"scoreboard":{"games":[]}}'])
def test_http_200_invalid_payload_never_passes(tmp_path: Path, body: bytes) -> None:
    probe = runner(tmp_path, [Response(200, body, {})])
    result = probe.fetch(request(), validate)
    assert result["outcome"] == "failed"
    assert result["reason"].startswith("invalid_payload")
    assert result["validated_at"] is None
    assert probe.requests == 1


def test_truncated_body_is_retained_but_cannot_validate(tmp_path: Path) -> None:
    probe = runner(tmp_path, [Response(200, b"{}", {}, complete=False)])
    result = probe.fetch(request(), validate)
    assert result["outcome"] == "failed"
    assert result["raw_complete"] is False


def test_new_versions_and_identical_repeats_preserve_observations(tmp_path: Path) -> None:
    original = valid_response()
    payload = json.loads(original.body)
    payload["scoreboard"]["games"][0]["gameStatusText"] = "Later revised status"
    revised = Response(200, json.dumps(payload).encode(), {})
    probe = runner(tmp_path, [original, original, revised])
    versions = [probe.fetch(request(), validate) for _ in range(3)]
    assert len({item["observation_id"] for item in versions}) == 3
    assert versions[0]["raw_path"] == versions[1]["raw_path"]
    assert versions[0]["raw_path"] != versions[2]["raw_path"]
    assert len(list((tmp_path / "raw").glob("*.bin"))) == 2
    assert probe.archive.verify() == 3
    (tmp_path / versions[0]["raw_path"]).write_bytes(b"changed")
    with pytest.raises(ValueError, match="Checksum mismatch"):
        probe.archive.verify()


@pytest.mark.parametrize("environment", ["github-actions", "cloud-development"])
def test_cloud_stats_requests_are_rejected_before_transport(environment: str) -> None:
    with pytest.raises(ValueError, match="local-machine only"):
        ProbeRequest("history", "https://stats.nba.com/stats/leaguegamelog", environment, {})


@pytest.mark.parametrize(
    "url",
    [
        "http://cdn.nba.com/a",
        "https://user:secret@cdn.nba.com/a",
        "https://cdn.nba.com/a?token=x",
        "https://example.com/a",
    ],
)
def test_unsafe_requests_are_rejected(url: str) -> None:
    with pytest.raises(ValueError):
        ProbeRequest("status", url, "local", {})


@pytest.mark.parametrize(
    "values",
    [{"retries": 3}, {"min_gap": 2}, {"timeout": 31}, {"max_requests": 0}, {"max_seconds": 601}],
)
def test_policy_cannot_exceed_contract(values: dict[str, int]) -> None:
    with pytest.raises(ValueError):
        Policy(**values)
