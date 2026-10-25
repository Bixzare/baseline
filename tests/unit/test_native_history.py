"""Exercise the real nba_api client with deterministic HTTP adapter responses."""

import json
from pathlib import Path
from typing import Any

import pytest
import requests
from nba_api.stats.endpoints.leaguegamelog import LeagueGameLog
from nba_api.stats.library.http import NBAStatsHTTP

from hoop.domains.nba.sources.native_history import HEADERS, NBAApiHistoryTransport
from hoop.domains.nba.sources.policy import Policy, ProbeRunner, SystemClock
from hoop.domains.nba.sources.probe import local_requests
from hoop.platform.provenance import Archive

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def local_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for marker in ["GITHUB_ACTIONS", "CI", "CODEX_PROXY_CERT"]:
        monkeypatch.delenv(marker, raising=False)


def make_probe(tmp_path: Path) -> tuple[NBAApiHistoryTransport, ProbeRunner]:
    transport = NBAApiHistoryTransport(Archive(tmp_path), confirm_local_machine=True)
    runner = ProbeRunner(
        transport.archive, transport, SystemClock(), Policy(retries=0), "synthetic-native"
    )
    return transport, runner


def history_requests() -> Any:
    config = json.loads((ROOT / "configs/sources/local.json").read_text())
    return local_requests({**config, "team_ids": []})


def mock_http(
    monkeypatch: pytest.MonkeyPatch, status: int, body: bytes, **headers: str
) -> list[Any]:
    calls = []

    def send(adapter: Any, request: Any, **kwargs: Any) -> requests.Response:
        calls.append((request, kwargs))
        response = requests.Response()
        response.status_code = status
        response._content = body
        response.url = request.url
        response.request = request
        response.headers.update(headers)
        return response

    monkeypatch.setattr(requests.adapters.HTTPAdapter, "send", send)
    return calls


@pytest.mark.usefixtures("local_environment")
@pytest.mark.parametrize(("index", "kind"), [(0, "player"), (1, "team")])
def test_native_endpoint_parses_fixture_after_raw_retention(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, index: int, kind: str
) -> None:
    body = (ROOT / f"tests/fixtures/nba/history-{kind}.json").read_bytes()
    calls = mock_http(monkeypatch, 200, body)
    previous_session = object()
    monkeypatch.setattr(NBAStatsHTTP, "_session", previous_session)
    original_parser = LeagueGameLog.load_response

    def inspect_before_parse(endpoint: Any) -> None:
        assert list((tmp_path / "raw").glob("*.bin"))[0].read_bytes() == body
        original_parser(endpoint)

    monkeypatch.setattr(LeagueGameLog, "load_response", inspect_before_parse)
    transport, runner = make_probe(tmp_path)
    result = runner.fetch(history_requests()[index], transport.validate)
    assert result["outcome"] == "verified_sample"
    assert result["http_status"] == 200
    assert result["record_count"] == transport.frame_rows == 1
    assert transport.archive.verify() == 1
    assert NBAStatsHTTP._session is previous_session
    assert len(calls) == 1
    request, options = calls[0]
    assert "PlayerOrTeam=" + ("P" if index == 0 else "T") in request.url
    assert request.headers["User-Agent"] == HEADERS["User-Agent"]
    assert "Referer" not in request.headers and "Sec-Ch-Ua" not in request.headers
    assert options["timeout"] == 30
    assert options["verify"] is True


@pytest.mark.usefixtures("local_environment")
@pytest.mark.parametrize("status", [200, 403])
def test_html_stops_native_source_without_a_second_request(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, status: int
) -> None:
    calls = mock_http(monkeypatch, status, b"<html>Access denied</html>")
    transport, runner = make_probe(tmp_path)
    first, second = history_requests()
    result = runner.fetch(first, transport.validate)
    assert result["reason"] == "access_denied_or_html_challenge"
    assert result["http_status"] == status
    assert runner.fetch(second, transport.validate)["outcome"] == "unverified"
    assert len(calls) == runner.requests == 1
    assert transport.archive.verify() == 2


@pytest.mark.usefixtures("local_environment")
def test_native_timeout_retains_failure_and_restores_session(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    previous_session = object()
    monkeypatch.setattr(NBAStatsHTTP, "_session", previous_session)

    def timeout(*args: Any, **kwargs: Any) -> None:
        raise requests.exceptions.ReadTimeout("synthetic timeout")

    monkeypatch.setattr(requests.adapters.HTTPAdapter, "send", timeout)
    transport, runner = make_probe(tmp_path)
    result = runner.fetch(history_requests()[0], transport.validate)
    assert result["outcome"] == "failed"
    assert result["reason"] == "temporary_network_failure: ReadTimeout"
    assert result["http_status"] is None and result["raw_path"] is None
    assert NBAStatsHTTP._session is previous_session
    assert runner.requests == 1
    assert transport.archive.verify() == 1


@pytest.mark.usefixtures("local_environment")
def test_native_parse_failure_cannot_pass_shared_validation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    mock_http(monkeypatch, 200, b"{}")
    transport, runner = make_probe(tmp_path)
    result = runner.fetch(history_requests()[0], transport.validate)
    assert result["outcome"] == "failed"
    assert result["http_status"] == 200
    assert "native_client_parse_failed" in result["reason"]
    assert (tmp_path / result["raw_path"]).read_bytes() == b"{}"


@pytest.mark.usefixtures("local_environment")
def test_redirect_is_retained_without_following(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = mock_http(monkeypatch, 302, b"redirect", Location="https://stats.nba.com/other")
    transport, runner = make_probe(tmp_path)
    result = runner.fetch(history_requests()[0], transport.validate)
    assert result["outcome"] == "failed"
    assert result["http_status"] == 302
    assert len(calls) == 1


@pytest.mark.parametrize("marker", ["GITHUB_ACTIONS", "CI", "CODEX_PROXY_CERT"])
def test_native_access_is_local_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, marker: str
) -> None:
    monkeypatch.setenv(marker, "true")
    with pytest.raises(ValueError, match="forbidden from cloud/CI"):
        make_probe(tmp_path)
