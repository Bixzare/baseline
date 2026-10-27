from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import psycopg
import pytest
from psycopg.conninfo import make_conninfo

from hoop.domains.nba.health import snapshot
from hoop.platform.database import provision_runtime
from hoop.platform.monitoring import append_condition, reconcile_conditions
from hoop.platform.operations import db_now
from tests.fixtures.publication import publication_fixture

pytestmark = pytest.mark.postgres


def test_stable_alert_open_ack_resolve_and_actual_role_denials(migrated: Any) -> None:
    dsn, owner = migrated
    provision_runtime(owner, "synthetic_fixture_password_only")
    runtime = make_conninfo(
        dsn, user="baseline_runtime", password="synthetic_fixture_password_only"
    )
    base = {
        "alert_key": "nba:backup:age",
        "severity": "warning",
        "state": "open",
        "reason_code": "backup_stale_or_unverified",
        "observed_at": db_now(owner),
        "details": {},
    }

    def run(_: int) -> Any:
        with psycopg.connect(runtime, autocommit=True) as conn:
            return append_condition(conn, base)

    with ThreadPoolExecutor(max_workers=2) as workers:
        values = list(workers.map(run, [1, 2]))
    assert sum(v is not None for v in values) == 1
    with psycopg.connect(runtime, autocommit=True) as conn:
        assert append_condition(conn, {**base, "state": "acknowledged"})
        assert append_condition(conn, base) is None
        assert append_condition(conn, {**base, "severity": "critical"})
        assert append_condition(
            conn, {**base, "state": "resolved", "reason_code": "backup_verified"}
        )
        assert conn.execute("SELECT count(*) FROM platform.alert_events").fetchone() == (4,)
        assert append_condition(conn, {**base, "alert_key": "nba:outcome:fixture"})
        assert reconcile_conditions(conn, [], db_now(conn), namespace="nba") == 1
        assert reconcile_conditions(conn, [], db_now(conn), namespace="nba") == 0
        for query in [
            "UPDATE platform.alert_events SET state='resolved'",
            "DELETE FROM platform.alert_events",
            "TRUNCATE platform.alert_events",
        ]:
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                conn.execute(query)


def test_health_keeps_capacity_backup_and_missing_completion_unknown(
    migrated: Any, tmp_path: Path
) -> None:
    import json

    _, conn = migrated
    publication_fixture(conn, tmp_path)
    config = json.loads(Path("configs/health.json").read_text())
    operations = json.loads(Path("configs/operations.json").read_text())
    result = snapshot(conn, config, operations, rehearsal=True)
    assert result["snapshot"]["backup"]["verified"] is False
    assert result["snapshot"]["capacity"]["objects"]["provider_usage_known"] is False
    assert result["snapshot"]["runs"]["dispatcher"]["succeeded"] is None
    assert result["assessment"]["state"] == "degraded"
