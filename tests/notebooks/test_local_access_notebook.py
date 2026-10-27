"""Verify the history notebook offline, including a fresh project kernel."""

import json
import os
import socket
import sys
from datetime import UTC, datetime
from ipaddress import ip_address
from pathlib import Path
from time import monotonic
from typing import Any

import pytest
from jupyter_client import BlockingKernelClient, KernelManager
from jupyter_client.kernelspec import KernelSpecManager

from hoop.domains.nba.sources.policy import Response

ROOT = Path(__file__).resolve().parents[2]
NOTEBOOK = ROOT / "test.ipynb"
SOCKET_CONNECT = socket.socket.connect


def code_cells(path: Path = NOTEBOOK) -> list[dict[str, Any]]:
    notebook = json.loads(path.read_text(encoding="utf-8"))
    return [cell for cell in notebook["cells"] if cell["cell_type"] == "code"]


def cell_source(tag: str) -> str:
    return next(
        "".join(cell["source"]) for cell in code_cells() if tag in cell["metadata"].get("tags", [])
    )


def namespace() -> dict[str, Any]:
    result: dict[str, Any] = {}
    for tag in ["environment", "parameters"]:
        exec(compile(cell_source(tag), str(NOTEBOOK), "exec"), result)
    return result


def test_notebook_is_clean_and_live_access_is_disabled() -> None:
    notebook = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
    assert notebook["nbformat"] == 4
    assert notebook["metadata"]["kernelspec"]["name"] == "baseline"
    assert len({cell["id"] for cell in notebook["cells"]}) == len(notebook["cells"])
    for cell in code_cells():
        assert cell["execution_count"] is None
        assert cell["outputs"] == []
    state = namespace()
    assert state["RUN_LIVE"] is False
    assert state["CONFIRM_LOCAL_MACHINE"] is False
    exec(compile(cell_source("stock-parameters"), str(NOTEBOOK), "exec"), state)
    assert state["RUN_STOCK_DEFAULTS"] is False
    assert state["STOCK_LOCAL_CONFIRMED"] is False


def execute(client: BlockingKernelClient, source: str) -> None:
    message_id = client.execute(source)
    deadline = monotonic() + 30
    while True:
        remaining = deadline - monotonic()
        if remaining <= 0:
            raise TimeoutError("Notebook cell did not finish in 30 seconds")
        message = client.get_iopub_msg(timeout=remaining)
        if message["parent_header"].get("msg_id") != message_id:
            continue
        if message["msg_type"] == "error":
            raise AssertionError(message["content"]["evalue"])
        if message["msg_type"] == "status" and message["content"]["execution_state"] == "idle":
            return


@pytest.mark.parametrize(
    "notebook_path",
    [
        NOTEBOOK,
        ROOT / "notebooks/01_sources_and_backfill.ipynb",
        ROOT / "notebooks/02_baseline_and_ledger.ipynb",
    ],
)
def test_fixture_run_in_fresh_kernel_cannot_access_network(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    notebook_path: Path,
) -> None:
    # Jupyter needs local IPC; Windows asyncio also creates a loopback socket pair.
    # Keep external connections forbidden in the parent as well as in the kernel.
    def loopback_only(sock: socket.socket, address: Any) -> Any:
        try:
            permitted = isinstance(address, tuple) and ip_address(address[0]).is_loopback
        except ValueError:
            permitted = False
        if not permitted:
            raise AssertionError("Kernel test cannot open external network connections")
        return SOCKET_CONNECT(sock, address)

    monkeypatch.setattr(socket.socket, "connect", loopback_only)
    with socket.socket() as connection:
        with pytest.raises(AssertionError, match="external network"):
            connection.connect(("203.0.113.1", 443))

    kernel_root = tmp_path / "kernels"
    spec_dir = kernel_root / "baseline_test"
    spec_dir.mkdir(parents=True)
    (spec_dir / "kernel.json").write_text(
        json.dumps(
            {
                "argv": [sys.executable, "-m", "ipykernel_launcher", "-f", "{connection_file}"],
                "display_name": "Baseline notebook test",
                "language": "python",
            }
        ),
        encoding="utf-8",
    )
    manager = KernelManager(
        kernel_name="baseline_test",
        kernel_spec_manager=KernelSpecManager(kernel_dirs=[str(kernel_root)]),
    )
    client = None
    try:
        manager.start_kernel(
            cwd=str(ROOT),
            env={**os.environ, "IPYTHONDIR": str(tmp_path), "JUPYTER_RUNTIME_DIR": str(tmp_path)},
        )
        client = manager.blocking_client()
        client.start_channels()
        client.wait_for_ready(timeout=30)
        execute(
            client,
            "import socket\n"
            "def reject_network(*args, **kwargs):\n"
            "    raise AssertionError('Notebook fixture run attempted network access')\n"
            "socket.socket.connect = reject_network\n"
            "import psycopg\n"
            "psycopg.connect = reject_network\n",
        )
        for cell in code_cells(notebook_path):
            assert cell["execution_count"] is None and not cell["outputs"]
            execute(client, "".join(cell["source"]))
        if notebook_path.name == "02_baseline_and_ledger.ipynb":
            execute(
                client,
                "assert result['coverage'] == {'players':3,'entries':15,'numeric_entries':10}\n"
                "assert not result['official_publication'] and replay['reused']",
            )
            return
        if notebook_path != NOTEBOOK:
            execute(
                client,
                "assert replay_report['reused']\n"
                "assert not seed_report['source_accepted']\n"
                "assert seed_report['row_counts'] == {'players': 2, 'teams': 2}\n"
                "assert not import_plan['blockers'] and not import_plan['hosted_ready']",
            )
            return
        execute(
            client,
            "assert RUN_LIVE is False\n"
            "assert CONFIRM_LOCAL_MACHINE is False\n"
            "assert live_runner is None and archive_path is None\n"
            "assert live_access_passed is False\n"
            "assert set(fixture_summary['history']) == {'player', 'team'}\n"
            "assert fixture_summary['evidence'].eq('synthetic fixture').all()\n"
            "assert fixture_summary['rows'].gt(0).all()\n",
        )
        execute(
            client,
            "assert not RUN_STOCK_DEFAULTS and not stock_access_passed\n"
            "assert stock_archive is None\n"
            "assert dataset_summary['evidence_kind'] == 'synthetic_fixture'\n"
            "assert dataset_summary['source_accepted'] is False\n"
            "assert dataset_summary['valid_game_count'] == 1",
        )
    finally:
        if client is not None:
            client.stop_channels()
        if manager.has_kernel:
            manager.shutdown_kernel(now=True)


def test_live_probe_requires_local_confirmation() -> None:
    state = namespace()
    state["RUN_LIVE"] = True
    with pytest.raises(RuntimeError, match="Confirm this is your own local computer"):
        exec(compile(cell_source("live-probe"), str(NOTEBOOK), "exec"), state)
    assert state["archive_path"] is None


@pytest.mark.parametrize("marker", ["GITHUB_ACTIONS", "CI", "CODEX_PROXY_CERT"])
def test_live_probe_rejects_cloud_and_ci(monkeypatch: pytest.MonkeyPatch, marker: str) -> None:
    state = namespace()
    state.update(RUN_LIVE=True, CONFIRM_LOCAL_MACHINE=True)
    monkeypatch.setenv(marker, "true")
    with pytest.raises(RuntimeError, match="forbidden from cloud/CI"):
        exec(compile(cell_source("live-probe"), str(NOTEBOOK), "exec"), state)
    assert state["archive_path"] is None


def test_team_success_cannot_hide_player_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    state = namespace()
    for marker in ["GITHUB_ACTIONS", "CI", "CODEX_PROXY_CERT"]:
        monkeypatch.delenv(marker, raising=False)
    for name in ["test.ipynb", "uv.lock"]:
        (tmp_path / name).write_bytes((ROOT / name).read_bytes())
    helper_path = Path("src/hoop/domains/nba/sources/native_history.py")
    (tmp_path / helper_path).parent.mkdir(parents=True)
    (tmp_path / helper_path).write_bytes((ROOT / helper_path).read_bytes())
    state.update(RUN_LIVE=True, CONFIRM_LOCAL_MACHINE=True, ROOT=tmp_path)
    monkeypatch.setattr(state["subprocess"], "check_output", lambda *a, **k: "synthetic-test")
    team_body = (ROOT / "tests/fixtures/nba/history-team.json").read_bytes()

    class FixtureTransport:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            self.validate = state["validate"]

        def get(self, url: str, timeout: float) -> Response:
            return Response(200, b"{}" if "PlayerOrTeam=P" in url else team_body, {})

    class FixtureClock:
        elapsed = 0.0

        def now(self) -> datetime:
            return datetime(2026, 10, 15, tzinfo=UTC)

        def monotonic(self) -> float:
            return self.elapsed

        def sleep(self, seconds: float) -> None:
            self.elapsed += seconds

    state.update(NBAApiHistoryTransport=FixtureTransport, SystemClock=FixtureClock)
    exec(compile(cell_source("live-probe"), str(NOTEBOOK), "exec"), state)
    exec(compile(cell_source("inspect"), str(NOTEBOOK), "exec"), state)
    assert state["live_runner"].requests == 2
    assert state["live_access_passed"] is False
    outcomes = dict(
        zip(state["live_summary"]["history"], state["live_summary"]["outcome"], strict=True)
    )
    assert outcomes == {"player": "failed", "team": "verified_sample"}
    assert state["live_runner"].archive.verify() == 2


@pytest.mark.parametrize("failure", [None, "timeout", "denial", "empty"])
def test_stock_client_at_network_boundary(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, failure: str | None
) -> None:
    import requests
    from nba_api.stats.library.http import NBAStatsHTTP

    state = namespace()
    exec(compile(cell_source("stock-parameters"), str(NOTEBOOK), "exec"), state)
    state.update(RUN_STOCK_DEFAULTS=True, STOCK_LOCAL_CONFIRMED=True, ROOT=tmp_path)
    for name in ["test.ipynb", "uv.lock"]:
        (tmp_path / name).write_bytes((ROOT / name).read_bytes())
    for marker in ["GITHUB_ACTIONS", "CI", "CODEX_PROXY_CERT"]:
        monkeypatch.delenv(marker, raising=False)
    monkeypatch.setattr(NBAStatsHTTP, "_session", None)
    monkeypatch.setattr(requests.utils, "get_environ_proxies", lambda url: {})
    monkeypatch.setattr(state["subprocess"], "check_output", lambda *a, **k: "synthetic-test")
    monkeypatch.setattr("time.sleep", lambda seconds: None)
    calls = []

    def send(adapter: Any, request: Any, **kwargs: Any) -> requests.Response:
        calls.append(request)
        for key, value in NBAStatsHTTP.headers.items():
            assert request.headers[key] == value
        assert "Cookie" not in request.headers
        assert kwargs["verify"] is True
        assert kwargs["timeout"] == 20
        if failure == "timeout":
            raise requests.exceptions.ReadTimeout("synthetic timeout")
        side = "player" if "PlayerOrTeam=P" in request.url else "team"
        response = requests.Response()
        response.status_code = 403 if failure == "denial" else 200
        response._content = (
            b"<html>Denied</html>"
            if failure == "denial"
            else b"{}"
            if failure == "empty"
            else (ROOT / f"tests/fixtures/nba/history-{side}.json").read_bytes()
        )
        response.url = request.url
        return response

    monkeypatch.setattr(requests.adapters.HTTPAdapter, "send", send)
    exec(compile(cell_source("stock-run"), str(NOTEBOOK), "exec"), state)
    exec(compile(cell_source("stock-inspect"), str(NOTEBOOK), "exec"), state)
    assert len(calls) == (2 if failure is None else 1)
    assert state["stock_access_passed"] is (failure is None)
    rows = json.loads((state["stock_archive"] / "results.json").read_text())
    assert len(rows) == len(calls)
    if failure == "timeout":
        assert rows[0]["error"] == "ReadTimeout"
        assert rows[0]["http_status"] is None
        assert "response_file" not in rows[0]
    elif failure == "denial":
        assert rows[0]["http_status"] == 403
        assert (
            state["stock_archive"] / rows[0]["response_file"]
        ).read_bytes() == b"<html>Denied</html>"


@pytest.mark.parametrize("marker", [None, "CI", "GITHUB_ACTIONS", "CODEX_PROXY_CERT"])
def test_stock_guards_precede_requests(monkeypatch: pytest.MonkeyPatch, marker: str | None) -> None:
    state = namespace()
    exec(compile(cell_source("stock-parameters"), str(NOTEBOOK), "exec"), state)
    state.update(RUN_STOCK_DEFAULTS=True, STOCK_LOCAL_CONFIRMED=marker is not None)
    if marker:
        monkeypatch.setenv(marker, "true")
    with pytest.raises(RuntimeError, match="local computer|forbidden from cloud/CI"):
        exec(compile(cell_source("stock-run"), str(NOTEBOOK), "exec"), state)
    assert state["stock_archive"] is None
