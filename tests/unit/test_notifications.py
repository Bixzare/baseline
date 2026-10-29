"""Validate the subprocess boundary without opening desktop UI in routine tests."""

import json
import subprocess
from types import SimpleNamespace

import pytest

from hoop.platform import notifications


@pytest.mark.parametrize("shown", [True, False])
def test_shell_acknowledgment_never_claims_visible_delivery(monkeypatch, shown):
    monkeypatch.setattr(notifications.sys, "platform", "win32")
    monkeypatch.setenv("BASELINE_RUNTIME_DSN", "private-fixture-database")
    monkeypatch.setenv("BASELINE_ARTIFACT_PASSWORD", "private-fixture-secret")
    monkeypatch.setenv("PGPASSWORD", "private-fixture-password")
    calls = []

    def run(command, **kwargs):
        calls.append((command, kwargs))
        return SimpleNamespace(
            returncode=0, stdout=json.dumps({"queued": True, "shell_shown_event": shown})
        )

    monkeypatch.setattr(subprocess, "run", run)
    result = notifications.notify(rehearsal=True)
    assert result == {
        "attempted": True,
        "queued": True,
        "shell_shown_event": shown,
        "delivery": "unverified",
    }
    command, options = calls[0]
    assert options["env"]["BASELINE_NOTIFICATION_REHEARSAL"] == "1"
    assert (
        not {"BASELINE_RUNTIME_DSN", "BASELINE_ARTIFACT_PASSWORD", "PGPASSWORD"}
        & options["env"].keys()
    )
    assert options["timeout"] == 20 and "-STA" in command
    assert "private-fixture" not in json.dumps(command)


@pytest.mark.parametrize(
    "payload,code",
    [
        ("not-json", 0),
        ('{"queued":true}', 0),
        ('{"queued":true,"shell_shown_event":"true"}', 0),
        ("{}", 1),
        ("[]", 0),
    ],
)
def test_missing_or_malformed_shell_acknowledgment_fails_closed(monkeypatch, payload, code):
    monkeypatch.setattr(notifications.sys, "platform", "win32")
    monkeypatch.setattr(
        subprocess, "run", lambda *a, **k: SimpleNamespace(returncode=code, stdout=payload)
    )
    assert notifications.notify() == {"attempted": True, "queued": False, "delivery": "unverified"}


def test_non_windows_notice_opens_no_subprocess(monkeypatch):
    monkeypatch.setattr(notifications.sys, "platform", "linux")

    def forbidden(*args, **kwargs):
        raise AssertionError("No desktop subprocess on this platform")

    monkeypatch.setattr(subprocess, "run", forbidden)
    assert notifications.notify() == {"attempted": False, "delivery": "unverified"}
