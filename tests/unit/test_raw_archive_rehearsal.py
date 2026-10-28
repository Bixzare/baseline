"""Default-off and explicit confirmation are independent of private credentials."""

import json

from scripts.rehearse_raw_archives import main


def test_default_plan_never_loads_hosted_credentials(monkeypatch, capsys) -> None:
    def forbidden(*args, **kwargs):
        raise AssertionError("No connection permitted in default plan")

    monkeypatch.setattr("scripts.rehearse_raw_archives.connection", forbidden)
    monkeypatch.setattr("sys.argv", ["raw-rehearsal"])
    assert main() == 0
    assert json.loads(capsys.readouterr().out) == {
        "operation": "plan",
        "network_access": False,
        "database_writes": False,
        "production_enabled": False,
    }


def test_explicit_confirmation_required_before_connection(monkeypatch, capsys) -> None:
    def forbidden(*args, **kwargs):
        raise AssertionError("No connection permitted without confirmation")

    monkeypatch.setattr("scripts.rehearse_raw_archives.connection", forbidden)
    monkeypatch.setattr("sys.argv", ["raw-rehearsal", "check"])
    assert main() == 1
    assert json.loads(capsys.readouterr().out)["reason_code"] == "raw_archive_rehearsal_failed"
