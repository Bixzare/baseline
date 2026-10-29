"""Real restricted SQL import keeps repair lineage portable and observed times honest."""

import copy
import json
from pathlib import Path
from typing import Any

import psycopg
import pytest
from psycopg.conninfo import make_conninfo
from psycopg.rows import dict_row

from hoop.domains.nba.history.readers import player_history
from hoop.domains.nba.history.seed import apply_seed, plan_seed
from hoop.domains.nba.sources.seed import build_seed
from hoop.platform.artifacts import PrivateArtifacts, Session
from hoop.platform.database import provision_runtime
from hoop.platform.evidence import EvidenceError
from hoop.platform.provenance import digest, parse_time
from tests.fixtures.adjudication import NOW, fixture
from tests.fixtures.storage_client import SETTINGS, MemoryStorage

pytestmark = pytest.mark.postgres


def prepared(tmp_path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    case = fixture(tmp_path)
    report = build_seed(
        case["source"],
        case["manifest"],
        case["archive"],
        inventory=case["inventory"],
        repair_paths=case["patches"],
        now=NOW,
    )
    acceptance = {
        "kind": "synthetic_fixture",
        "manifest_sha256": report["manifest_artifact"]["sha256"],
        "parser_version": report["parser_version"],
        "calendar_convention": "source_calendar_verified",
    }
    observations = {
        name: {
            "requested_at": "2026-10-24T11:59:00Z",
            "received_at": case["manifest"]["collected_at"],
            "sha256": sha,
        }
        for name, sha in case["manifest"]["files"].items()
    }
    plan = plan_seed(report, case["archive"], case["manifest"], acceptance, observations)
    assert not plan["blockers"]
    return case, plan


def test_runtime_import_retains_every_repair_and_its_late_availability(
    migrated: Any, tmp_path: Path
) -> None:
    dsn, owner = migrated
    provision_runtime(owner, "synthetic_fixture_password_only")
    case, plan = prepared(tmp_path)
    store = PrivateArtifacts(Session(SETTINGS, MemoryStorage()))
    with psycopg.connect(
        make_conninfo(dsn, user="baseline_runtime", password="synthetic_fixture_password_only"),
        autocommit=True,
    ) as conn:
        first = apply_seed(conn, store, plan, case["archive"], tmp_path / "checkpoint.json")
        count = conn.execute("SELECT count(*) FROM platform.artifacts").fetchone()[0]
        assert apply_seed(conn, store, plan, case["archive"], tmp_path / "checkpoint.json") == first
        assert conn.execute("SELECT count(*) FROM platform.artifacts").fetchone()[0] == count
        with conn.cursor(row_factory=dict_row) as cursor:
            artifacts = cursor.execute("SELECT * FROM platform.artifacts").fetchall()
            checks = cursor.execute(
                "SELECT validation_summary FROM platform.source_checks"
            ).fetchall()
        registered = {str(a["artifact_id"]): a for a in artifacts}
        cloud = next(
            json.loads(store.read(a))
            for a in artifacts
            if a["kind"] == "reports"
            and a["format"] == "json"
            and '"repair_lineage"' in store.read(a).decode()
        )
        assert {a["sha256"] for a in cloud["repair_lineage"]} == {
            a["sha256"] for a in plan["repair_inputs"]
        }
        for item in cloud["repair_lineage"]:
            assert store.read(registered[item["artifact_id"]])
        for check in checks:
            summary = check["validation_summary"]
            assert summary["scope"] == "compact_seed_only"
            assert len(summary["repair_artifact_ids"]) == 4
            assert summary["reviewed_exclusions"] == 1
        assert not player_history(conn, ["203"], parse_time("2026-10-26T11:00:00Z"))
        rows = player_history(conn, ["203"], parse_time("2026-10-28T12:00:00Z"))
        assert (
            len(rows) == 1
            and rows[0]["participation"] == "played"
            and rows[0]["minutes_seconds"] == 0
        )
        assert conn.execute("SELECT count(*) FROM platform.predictions").fetchone() == (0,)


@pytest.mark.parametrize(
    "mutation", ["repair_inventory", "selected_window", "lineage_implementation"]
)
def test_rehashed_plan_cannot_drop_lineage_or_change_selected_history(
    migrated: Any, tmp_path: Path, mutation: str
) -> None:
    _, conn = migrated
    case, plan = prepared(tmp_path)
    changed = copy.deepcopy(plan)
    if mutation == "repair_inventory":
        changed["repair_inputs"] = []
    elif mutation == "lineage_implementation":
        changed["repair_lineage_implementation_sha256"] = "0" * 64
    else:
        changed["players"][0]["game_date"] = "2026-01-01"
    changed.pop("plan_sha256")
    changed["plan_sha256"] = digest(json.dumps(changed, sort_keys=True, allow_nan=False).encode())
    transport = MemoryStorage()
    store = PrivateArtifacts(Session(SETTINGS, transport))
    with pytest.raises(EvidenceError):
        apply_seed(conn, store, changed, case["archive"], tmp_path / "checkpoint.json")
    assert not transport.calls
    assert conn.execute("SELECT count(*) FROM platform.runs").fetchone() == (0,)
