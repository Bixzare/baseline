import json

from hoop.domains.nba.history.lineage import main


def test_default_plan_has_no_credentials_or_network(monkeypatch, capsys) -> None:
    def forbidden(*args, **kwargs):
        raise AssertionError("Connection forbidden")

    monkeypatch.setattr("hoop.domains.nba.history.lineage.connection", forbidden)
    monkeypatch.setattr("sys.argv", ["lineage"])
    assert main() == 0
    assert json.loads(capsys.readouterr().out) == {
        "operation": "plan",
        "network_access": False,
        "seed_accepted": False,
    }


def test_invalid_cloud_input_fails_before_credentials_or_database(
    monkeypatch, capsys, tmp_path
) -> None:
    def forbidden(*args, **kwargs):
        raise AssertionError("Invalid UUID must fail before connection")

    monkeypatch.setattr("hoop.domains.nba.history.lineage.connection", forbidden)
    value = "not-a-uuid; unexpected-command"
    monkeypatch.setenv("BASELINE_SEED_LINEAGE_ROOT_ID", value)
    report = tmp_path / "check.json"
    monkeypatch.setattr(
        "sys.argv", ["lineage", "check", "--confirm-rehearsal", "--report", str(report)]
    )
    assert main() == 1
    result = json.loads(capsys.readouterr().out)
    assert result["verified"] is False
    assert value not in report.read_text()
