"""Configuration fails safely before attempting a live connection."""

from contextlib import nullcontext
from types import SimpleNamespace

import pytest

from hoop.platform.database import DatabaseError, connection, health
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


@pytest.mark.parametrize(
    "client_tls,backend_tls", [(True, False), (False, True), (True, True), (False, False)]
)
def test_health_distinguishes_client_and_postgres_backend_tls(
    client_tls: bool,
    backend_tls: bool,
) -> None:
    conn = SimpleNamespace(
        pgconn=SimpleNamespace(ssl_in_use=client_tls),
        execute=lambda query: SimpleNamespace(
            fetchone=lambda: ("baseline_runtime", "17.11", backend_tls)
        ),
    )
    assert health(conn) == {
        "role": "baseline_runtime",
        "server_version": "17.11",
        "tls": client_tls,
        "postgres_backend_tls": backend_tls,
    }


@pytest.mark.parametrize("client_tls,expected_exit", [(True, 0), (False, 1)])
def test_hosted_check_requires_client_tls_even_when_backend_disagrees(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    client_tls: bool,
    expected_exit: int,
) -> None:
    conn = SimpleNamespace(
        pgconn=SimpleNamespace(ssl_in_use=client_tls),
        execute=lambda query: SimpleNamespace(
            fetchone=lambda: ("baseline_runtime", "17.11", not client_tls)
        ),
    )
    monkeypatch.delenv("BASELINE_DB_LOCAL_TEST", raising=False)
    monkeypatch.setattr(
        "hoop.platform.database.__main__.connection", lambda variable: nullcontext(conn)
    )
    monkeypatch.setattr("sys.argv", ["database", "check"])
    assert main() == expected_exit
    output = capsys.readouterr().out
    if client_tls:
        assert '"tls": true' in output and '"postgres_backend_tls": false' in output
    else:
        assert "did not negotiate TLS" in output
