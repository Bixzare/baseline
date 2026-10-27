from pathlib import Path
from typing import Any

import psycopg
import pytest

from hoop.platform.operations import operation_lock, run_pipeline
from tests.fixtures.publication import publication_fixture

pytestmark = pytest.mark.postgres
CONFIG = {"domain": "nba", "max_seconds": 600, "readiness": {"activation_approved": False}}


def test_independent_session_lock_releases_after_failure_and_disconnect(migrated: Any) -> None:
    dsn, first = migrated
    with psycopg.connect(dsn, autocommit=True) as second:
        with operation_lock(first, "nba") as a, operation_lock(second, "nba") as b:
            assert a and not b
        with operation_lock(second, "nba") as acquired:
            assert acquired
        with pytest.raises(OSError), operation_lock(first, "nba"):
            raise OSError("failure")
        with operation_lock(second, "nba") as acquired:
            assert acquired
        disconnected = psycopg.connect(dsn, autocommit=True)
        disconnected.execute(
            "SELECT pg_advisory_lock(hashtextextended('baseline:shared-operations:nba',617))"
        )
        disconnected.close()
        with operation_lock(second, "nba") as acquired:
            assert acquired


def test_partial_stage_does_not_become_operation_success(migrated: Any, tmp_path: Path) -> None:
    _, conn = migrated
    publication_fixture(conn, tmp_path)

    def fail() -> dict[str, Any]:
        raise RuntimeError("Bearer do-not-record-this")

    result = run_pipeline(
        conn,
        "nightly",
        [("reconcile", fail), ("reports", lambda: {"state": "succeeded"})],
        CONFIG,
        rehearsal=True,
    )
    assert result["state"] == "incomplete" and not result["production_heartbeat"]
    assert result["stages"][1]["state"] == "succeeded"
    rows = conn.execute(
        "SELECT details FROM platform.run_events WHERE run_id=%s ORDER BY recorded_at",
        (result["run_id"],),
    ).fetchall()
    assert "Bearer" not in str(rows)
    assert rows[-1][0]["scope"] == "operation"
    assert conn.execute(
        "SELECT state FROM platform.run_events WHERE run_id=%s AND "
        "details->>'scope'='operation' ORDER BY recorded_at DESC LIMIT 1",
        (result["run_id"],),
    ).fetchone() == ("incomplete",)


def test_disabled_invocation_writes_no_fake_production_heartbeat(migrated: Any) -> None:
    _, conn = migrated
    result = run_pipeline(conn, "dispatcher", [], CONFIG)
    assert result == {"state": "disabled", "production_heartbeat": False, "stages": []}
    assert conn.execute("SELECT count(*) FROM platform.runs").fetchone() == (0,)
