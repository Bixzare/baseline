"""Capture a consistent roster/history snapshot and retain prepared evidence."""

from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import psycopg
import pytest
from psycopg.conninfo import make_conninfo
from psycopg.pq import TransactionStatus

from hoop.domains.nba.baselines.capture import capture_game
from hoop.domains.nba.baselines.model import prepare
from hoop.domains.nba.history.rosters import save_roster
from hoop.domains.nba.history.seed import apply_seed
from hoop.platform.artifacts import PrivateArtifacts, Session, retain
from hoop.platform.database import provision_runtime
from hoop.platform.evidence import register
from hoop.platform.prepared import encoded, retain_prepared
from hoop.platform.provenance import parse_time
from hoop.platform.records import immutable_insert
from tests.fixtures.history_seed import fixture_seed
from tests.fixtures.storage_client import SETTINGS, MemoryStorage

pytestmark = pytest.mark.postgres


def test_capture_reads_history_once_and_downloads_after_transaction(
    migrated: Any, tmp_path: Path
) -> None:
    dsn, owner = migrated
    provision_runtime(owner, "synthetic_fixture_password_only")
    with psycopg.connect(
        make_conninfo(dsn, user="baseline_runtime", password="synthetic_fixture_password_only"),
        autocommit=True,
    ) as conn:

        class GuardedStorage(MemoryStorage):
            def request(
                self, method: str, url: str, headers: dict[str, str], body: bytes | None
            ) -> Any:
                assert conn.info.transaction_status == TransactionStatus.IDLE
                return super().request(method, url, headers, body)

        store = PrivateArtifacts(Session(SETTINGS, GuardedStorage()))
        _, _, plan = fixture_seed(tmp_path / "archive")
        imported = apply_seed(conn, store, plan, tmp_path / "archive", tmp_path / "checkpoint.json")
        run_id = imported["run_id"]
        event_id = uuid4()

        def source(capability: str, payload: dict[str, Any], count: int) -> dict[str, Any]:
            raw = retain(conn, store, encoded(payload), kind="raw", format="json", manifest={})
            return register(
                conn,
                "source_checks",
                {
                    "check_id": str(uuid4()),
                    "run_id": run_id,
                    "source_id": "synthetic-fixture",
                    "adapter_version": "v1",
                    "requested_at": parse_time("2026-10-26T13:54:00Z"),
                    "received_at": parse_time("2026-10-26T13:55:00Z"),
                    "validated_at": parse_time("2026-10-26T13:56:00Z"),
                    "source_published_at": None,
                    "raw_artifact_id": raw["artifact_id"],
                    "http_status": None,
                    "record_count": count,
                    "state": "accepted",
                    "validation_summary": {"capability": capability},
                },
            )

        status = source("status", {"state": "scheduled"}, 1)
        with conn.transaction():
            immutable_insert(
                conn,
                "platform",
                "events",
                {
                    "event_id": event_id,
                    "domain": "nba",
                    "source_event_id": "0022600001",
                    "competition": "regular",
                    "season": "2026-27",
                    "occurrence_no": 1,
                    "predecessor_event_id": None,
                },
                ("event_id",),
            )
            immutable_insert(
                conn,
                "nba",
                "games",
                {
                    "event_id": event_id,
                    "home_team_id": "101",
                    "away_team_id": "102",
                    "source_season_type": "Regular Season",
                },
                ("event_id",),
            )
            immutable_insert(
                conn,
                "platform",
                "event_observations",
                {
                    "observation_id": uuid4(),
                    "event_id": event_id,
                    "source_check_id": UUID(status["check_id"]),
                    "observed_at": parse_time("2026-10-26T13:56:00Z"),
                    "scheduled_start": parse_time("2026-10-26T16:00:00Z"),
                    "actual_start": None,
                    "state": "scheduled",
                    "details": {},
                },
                ("observation_id",),
            )
        for team, members in [
            ("101", [{"player_id": "201"}, {"player_id": "999"}]),
            ("102", [{"player_id": "202"}]),
        ]:
            check = source("roster", {"team_id": team, "players": members}, len(members))
            check["validated_at"] = parse_time(check["validated_at"])
            save_roster(
                conn, store, team_id=team, season="2026-27", source_check=check, players=members
            )
        inputs = capture_game(conn, store, event_id, parse_time("2026-10-26T14:00:00Z"))
        result = prepare(inputs, generated_at=parse_time("2026-10-26T14:01:00Z"))
        entries = [row for row in result["entries"] if row["subject_id"] == "201"]
        assert next(row["value"] for row in entries if row["target"] == "points") == 10
        assert len(result["cohort"]) == 3 and result["coverage"]["entries"] == 15
        retained = retain_prepared(conn, store, result)
        assert (
            retained["descriptor"]["config_hash"]
            == retained["descriptor"]["configuration_artifact"]["sha256"]
        )
        assert not retained["official_publication"]
        for obj in retained["objects"].values():
            assert store.read(obj)
