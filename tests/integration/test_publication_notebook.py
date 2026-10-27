"""Execute the opt-in Postgres walkthrough in an isolated fresh Jupyter kernel."""

import json
import os
import socket
import sys
from ipaddress import ip_address
from pathlib import Path
from typing import Any

import pytest
from jupyter_client import KernelManager
from jupyter_client.kernelspec import KernelSpecManager

from tests.notebooks.test_local_access_notebook import SOCKET_CONNECT, execute

pytestmark = pytest.mark.postgres


def test_optional_postgres_walkthrough_uses_only_local_fixture_database(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def loopback(sock: socket.socket, address: Any) -> Any:
        assert isinstance(address, tuple) and ip_address(address[0]).is_loopback
        return SOCKET_CONNECT(sock, address)

    monkeypatch.setattr(socket.socket, "connect", loopback)
    root = Path(__file__).resolve().parents[2]
    kernels = tmp_path / "kernels/baseline"
    kernels.mkdir(parents=True)
    (kernels / "kernel.json").write_text(
        json.dumps(
            {
                "argv": [sys.executable, "-m", "ipykernel_launcher", "-f", "{connection_file}"],
                "display_name": "Baseline isolated Postgres",
                "language": "python",
            }
        )
    )
    manager = KernelManager(
        kernel_name="baseline",
        kernel_spec_manager=KernelSpecManager(kernel_dirs=[str(kernels.parent)]),
    )
    client = None
    try:
        manager.start_kernel(
            cwd=str(root),
            env={**os.environ, "IPYTHONDIR": str(tmp_path), "JUPYTER_RUNTIME_DIR": str(tmp_path)},
            extra_arguments=["--HistoryManager.enabled=False"],
        )
        client = manager.blocking_client()
        client.start_channels()
        client.wait_for_ready(timeout=30)
        execute(
            client,
            "import socket, psycopg\n"
            "from psycopg.conninfo import conninfo_to_dict\n"
            "real_connect = psycopg.connect\n"
            "def local_only(dsn='', *args, **kwargs):\n"
            "    allowed = {'localhost','127.0.0.1','::1','postgres'}\n"
            "    assert conninfo_to_dict(dsn).get('host') in allowed\n"
            "    return real_connect(dsn, *args, **kwargs)\n"
            "psycopg.connect = local_only\n"
            "def no_network(*args, **kwargs):\n"
            "    raise AssertionError('External network disabled')\n"
            "socket.socket.connect = no_network\n",
        )
        notebook = json.loads((root / "notebooks/02_baseline_and_ledger.ipynb").read_text())
        for cell in notebook["cells"]:
            if cell["cell_type"] == "code":
                source = "".join(cell["source"])
                if cell["id"] == "publication-inputs":
                    source = "RUN_POSTGRES_REHEARSAL = True"
                execute(client, source)
        execute(
            client,
            "assert publication_report['state']=='timely_confirmed'\n"
            "assert publication_report['insertion_transaction_id'] != "
            "publication_report['confirming_transaction_id']\n"
            "assert publication_report['production_ready'] is False\n",
        )
    finally:
        if client is not None:
            client.stop_channels()
        if manager.has_kernel:
            manager.shutdown_kernel(now=False)
