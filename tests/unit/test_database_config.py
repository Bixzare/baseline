"""Configuration fails safely before attempting a live connection."""

import pytest

from hoop.platform.database import DatabaseError, connection
from hoop.platform.database.__main__ import main


@pytest.mark.parametrize(
    "dsn,mode,reason",
    [
        ("postgresql://user:private_value@host/db", "direct", "verify-full"),
        (
            "postgresql://user:private_value@host:6543/db?sslmode=verify-full",
            "direct",
            "transaction",
        ),
        (
            "postgresql://user:private_value@host/db?sslmode=verify-full",
            "transaction",
            "transaction",
        ),
        ("postgresql://user:private_value@127.0.0.1/db", "direct", "LOCAL_TEST"),
        ("not a valid password=private_value dsn", "direct", "operation failed"),
    ],
)
def test_config_errors_never_disclose_credentials(
    monkeypatch: pytest.MonkeyPatch, dsn: str, mode: str, reason: str
) -> None:
    monkeypatch.setenv("BASELINE_RUNTIME_DSN", dsn)
    monkeypatch.setenv("BASELINE_DB_CONNECTION_MODE", mode)
    monkeypatch.delenv("BASELINE_DB_LOCAL_TEST", raising=False)
    with pytest.raises(DatabaseError, match=reason) as error, connection():
        pytest.fail("Invalid configuration connected")
    assert "private_value" not in str(error.value)


def test_cli_missing_credentials_is_sanitized(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv("BASELINE_RUNTIME_DSN", raising=False)
    monkeypatch.setattr("sys.argv", ["database", "check"])
    assert main() == 1
    assert "Configure BASELINE_RUNTIME_DSN privately" in capsys.readouterr().out
