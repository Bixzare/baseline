"""The optimized provider boundary stays exact, bounded and remote-to-local."""

import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from hoop.platform.backup import BackupError
from hoop.platform.backup.onedrive import OneDrive


def remote():
    result = OneDrive.__new__(OneDrive)
    result.binary = Path("rclone")
    result.remote = "fixture:BaselineBackups"
    result.env = {"SystemRoot": "fixture-system"}
    return result


def test_batch_uses_only_listed_objects_with_hard_caps_and_two_workers(tmp_path, monkeypatch):
    keys = {"objects/aa/" + "a" * 64: 5, "objects/bb/" + "b" * 64: 8}
    calls = []

    def run(command, **kwargs):
        calls.append((command, kwargs))
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(subprocess, "run", run)
    remote().download_many(keys, tmp_path, max_seconds=60)
    command, options = calls[0]
    assert command[1:4] == ["copy", "fixture:BaselineBackups", str(tmp_path.resolve())]
    assert command[command.index("--max-transfer") + 1] == "13"
    assert command[command.index("--cutoff-mode") + 1] == "hard"
    assert command[command.index("--transfers") + 1] == "2"
    assert command[command.index("--multi-thread-streams") + 1] == "0"
    assert options["timeout"] == 60 and options["env"] == {"SystemRoot": "fixture-system"}
    assert (tmp_path / "requested-objects.txt").read_text().splitlines() == sorted(keys)
    assert "delete" not in command and "sync" not in command


@pytest.mark.parametrize(
    "mode", ["unsafe_path", "bad_limit", "empty", "used_directory", "bad_budget"]
)
def test_batch_refuses_unsafe_or_reused_inputs_before_subprocess(tmp_path, monkeypatch, mode):
    files = {"objects/aa/" + "a" * 64: 2}
    budget = 60
    if mode == "unsafe_path":
        files = {"../outside": 2}
    elif mode == "bad_limit":
        files = {next(iter(files)): True}
    elif mode == "empty":
        files = {}
    elif mode == "used_directory":
        (tmp_path / "objects").mkdir()
    else:
        budget = float("nan")

    def forbidden(*args, **kwargs):
        raise AssertionError("Unsafe batch opened subprocess")

    monkeypatch.setattr(subprocess, "run", forbidden)
    with pytest.raises(BackupError):
        remote().download_many(files, tmp_path, max_seconds=budget)


@pytest.mark.parametrize("mode", ["failed", "timeout"])
def test_batch_failure_never_exposes_provider_stderr(tmp_path, monkeypatch, mode):
    def run(*args, **kwargs):
        if mode == "timeout":
            raise subprocess.TimeoutExpired("fixture", 60)
        return SimpleNamespace(returncode=1, stderr=b"private token must not escape")

    monkeypatch.setattr(subprocess, "run", run)
    with pytest.raises(BackupError) as error:
        remote().download_many({"objects/aa/" + "a" * 64: 2}, tmp_path, max_seconds=60)
    assert "private" not in str(error.value) and "token" not in str(error.value)
