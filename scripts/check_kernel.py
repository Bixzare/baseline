"""Check registered Baseline kernel identity and imports in a fresh kernel."""

import json
import os
import sys
from pathlib import Path
from queue import Empty
from tempfile import TemporaryDirectory
from time import monotonic

from jupyter_client import KernelManager
from jupyter_client.kernelspec import KernelSpecManager

import hoop


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    executable = Path(sys.executable).absolute()
    assert sys.version_info[:2] == (3, 12), sys.version
    assert sys.prefix != sys.base_prefix, "Use the project virtual environment"
    assert Path(hoop.__file__).resolve() == root / "src" / "hoop" / "__init__.py"
    specs = KernelSpecManager(kernel_dirs=[str(Path(sys.prefix) / "share/jupyter/kernels")])
    spec = specs.get_kernel_spec("baseline")
    # Do not resolve symlinks here: two venvs may share the same base interpreter.
    assert Path(spec.argv[0]).absolute() == executable, spec.argv[0]
    with TemporaryDirectory(prefix="baseline-kernel-") as runtime:
        manager = KernelManager(kernel_name="baseline", kernel_spec_manager=specs)
        client = None
        try:
            manager.start_kernel(
                cwd=str(root),
                env={**os.environ, "JUPYTER_RUNTIME_DIR": runtime, "IPYTHONDIR": runtime},
            )
            client = manager.blocking_client()
            client.start_channels()
            client.wait_for_ready(timeout=30)
            message_id = client.execute(
                "import json, sys, hoop, hoop.platform, hoop.domains.nba; "
                "print(json.dumps({'executable': sys.executable, 'package': hoop.__file__}))"
            )
            output = ""
            deadline = monotonic() + 30
            while True:
                remaining = deadline - monotonic()
                if remaining <= 0:
                    raise TimeoutError("Kernel execution did not finish within 30 seconds")
                try:
                    message = client.get_iopub_msg(timeout=remaining)
                except Empty as error:
                    raise TimeoutError("Kernel produced no completion message") from error
                if message["parent_header"].get("msg_id") != message_id:
                    continue
                if message["msg_type"] == "error":
                    raise RuntimeError(message["content"]["evalue"])
                if message["msg_type"] == "stream":
                    output += message["content"]["text"]
                if (
                    message["msg_type"] == "status"
                    and message["content"]["execution_state"] == "idle"
                ):
                    break
            identity = json.loads(output.strip())
            assert Path(identity["executable"]).absolute() == executable, identity
            assert Path(identity["package"]).resolve() == root / "src/hoop/__init__.py", identity
            print(f"Baseline kernel: OK ({identity['executable']})")
            print(f"Package imports and paths: OK ({identity['package']})")
        finally:
            if client is not None:
                client.stop_channels()
            if manager.has_kernel:
                manager.shutdown_kernel(now=True)


if __name__ == "__main__":
    main()
