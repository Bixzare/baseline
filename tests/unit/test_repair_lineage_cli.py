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
