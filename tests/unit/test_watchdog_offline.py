import json
import sys
from pathlib import Path
from typing import Any

from hoop.domains.nba.watchdog import main


def test_offline_checker_keeps_corrupt_cache_unknown_and_never_attempts_recovery(
    tmp_path: Path, monkeypatch: Any
) -> None:
    monkeypatch.delenv("BASELINE_RUNTIME_DSN", raising=False)
    (tmp_path / "cached-health.json").write_text("corrupt")
    monkeypatch.setattr(sys, "argv", ["watchdog", "--output", str(tmp_path)])
    assert main() == 1
    result = json.loads((tmp_path / "latest-health.json").read_text())
    assert result["state"] == "unverified" and not result["recovery_attempted"]
    assert result["local_incident_saved"]
    assert result["cache_reason"] == "unavailable_or_invalid"


def test_fixture_task_mode_is_explicit_and_never_opens_a_database(
    tmp_path: Path, monkeypatch: Any
) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "watchdog",
            "--mode",
            "rehearsal",
            "--fixture-state",
            "tests/fixtures/ops/health.json",
            "--output",
            str(tmp_path),
        ],
    )
    assert main() == 0
    result = json.loads((tmp_path / "latest-health.json").read_text())
    assert result["state"] == "rehearsal" and not result["recovery_attempted"]
    assert result["assessment"]["state"] == "degraded"


def test_notification_timeout_retains_unverified_delivery(monkeypatch: Any) -> None:
    import subprocess

    from hoop.domains.nba.watchdog import notify

    def failed(*args: Any, **kwargs: Any) -> None:
        raise subprocess.TimeoutExpired("fixture", 15)

    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(subprocess, "CREATE_NO_WINDOW", 0, raising=False)
    monkeypatch.setattr(subprocess, "run", failed)
    assert notify() == {"attempted": True, "queued": False, "delivery": "unverified"}


def test_unchanged_offline_alert_notifies_once(tmp_path: Path, monkeypatch: Any) -> None:
    from hoop.domains.nba import watchdog

    root = tmp_path / "root"
    (root / "configs").mkdir(parents=True)
    config = json.loads(Path("configs/health.json").read_text())
    config["desktop_notifications_enabled"] = True
    (root / "configs/health.json").write_text(json.dumps(config))
    (root / "configs/operations.json").write_text(Path("configs/operations.json").read_text())
    attempts = []
    monkeypatch.setattr(watchdog, "ROOT", root)
    monkeypatch.setattr(
        watchdog, "notify", lambda **kwargs: attempts.append(True) or {"queued": True}
    )
    monkeypatch.delenv("BASELINE_RUNTIME_DSN", raising=False)
    monkeypatch.setattr(sys, "argv", ["watchdog", "--output", str(tmp_path / "reports")])
    assert main() == 1
    assert main() == 1
    assert main() == 1
    assert attempts == [True]
