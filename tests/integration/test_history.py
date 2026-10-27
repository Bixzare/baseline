"""Real role, transaction, cutoff and cloud-reference checks on synthetic bytes."""

from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import uuid4

import psycopg
import pytest
from psycopg.conninfo import make_conninfo

from hoop.domains.nba.history.readers import player_history
from hoop.domains.nba.history.seed import apply_seed
from hoop.platform.artifacts import PrivateArtifacts, Session
from hoop.platform.database import provision_runtime
from hoop.platform.evidence import EvidenceError
from hoop.platform.provenance import parse_time
from hoop.platform.records import immutable_insert
from tests.fixtures.history_seed import fixture_seed
from tests.fixtures.storage_client import SETTINGS, MemoryStorage

pytestmark = pytest.mark.postgres


@pytest.fixture
def imported(migrated: Any, tmp_path: Path) -> Any:
    dsn, owner = migrated
    provision_runtime(owner, "synthetic_fixture_password_only")
    with psycopg.connect(
        make_conninfo(dsn, user="baseline_runtime", password="synthetic_fixture_password_only"),
        autocommit=True,
    ) as conn:
        _, _, plan = fixture_seed(tmp_path / "archive")
        store = PrivateArtifacts(Session(SETTINGS, MemoryStorage()))
        result = apply_seed(conn, store, plan, tmp_path / "archive", tmp_path / "checkpoint.json")
        yield owner, conn, plan, store, result, tmp_path


def test_repeat_import_retains_ids_and_reads_from_cloud_descriptors(imported: Any) -> None:
    owner, conn, plan, store, result, root = imported
    assert result["committed_games"] == 1
    assert apply_seed(conn, store, plan, root / "archive", root / "checkpoint.json") == result
    assert conn.execute("SELECT count(*) FROM nba.player_game_versions").fetchone() == (2,)
    for artifact_id in result["artifacts"]:
        with conn.cursor(row_factory=psycopg.rows.dict_row) as cursor:
            descriptor = cursor.execute(
                "SELECT * FROM platform.artifacts WHERE artifact_id=%s", (artifact_id,)
            ).fetchone()
        assert store.read(descriptor)
    before = player_history(conn, ["201"], parse_time("2026-10-25T11:59:59Z"))
    after = player_history(conn, ["201"], parse_time("2026-10-25T12:00:00Z"))
    assert not before and len(after) == 1
    assert after[0]["minutes_seconds"] == Decimal("1230.0")
    assert after[0]["actual_start"] is None
    assert after[0]["game_date"] == "2026-04-10"
    assert after[0]["evidence_tier"] == "archived_observed"
    assert owner.execute("SELECT count(*) FROM nba.roster_snapshots").fetchone() == (0,)


@pytest.mark.parametrize("stage", ["after_artifacts", "within_chunk", "before_checkpoint"])
def test_interrupted_import_can_resume_without_accepting_partial_chunk(
    migrated: Any, tmp_path: Path, stage: str
) -> None:
    _, conn = migrated
    _, _, plan = fixture_seed(tmp_path / "archive")
    store = PrivateArtifacts(Session(SETTINGS, MemoryStorage()))

    def fail(at: str) -> None:
        if at == stage:
            raise OSError("injected")

    with pytest.raises(OSError):
        apply_seed(
            conn, store, plan, tmp_path / "archive", tmp_path / "checkpoint.json", fault=fail
        )
    assert not (tmp_path / "checkpoint.json").exists()
    expected = 2 if stage == "before_checkpoint" else 0
    assert conn.execute("SELECT count(*) FROM nba.player_game_versions").fetchone() == (expected,)
    apply_seed(conn, store, plan, tmp_path / "archive", tmp_path / "checkpoint.json")
    assert conn.execute("SELECT count(*) FROM nba.player_game_versions").fetchone() == (2,)


def test_fact_membership_and_role_denials(imported: Any) -> None:
    owner, conn, _, _, _, _ = imported
    conn.execute("INSERT INTO nba.teams(team_id) VALUES ('999')")
    with conn.transaction(), pytest.raises(psycopg.errors.CheckViolation):
        conn.execute(
            "INSERT INTO nba.team_game_versions(fact_id,event_id,team_id,source_check_id,"
            "observed_at,evidence_tier,points_for,points_against) "
            "SELECT %s,event_id,'999',source_check_id,observed_at,evidence_tier,1,1 "
            "FROM nba.team_game_versions LIMIT 1",
            (uuid4(),),
        )
    for table in ["events", "event_observations"]:
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute(f"DELETE FROM platform.{table}")
    for table in ["games", "roster_snapshots", "player_game_versions", "team_game_versions"]:
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute(f"TRUNCATE nba.{table}")
    assert (
        conn.execute(
            "UPDATE nba.players SET display_name='Fixture player' WHERE player_id='201'"
        ).rowcount
        == 1
    )
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        conn.execute("UPDATE nba.players SET player_id='999'")
    owner.execute("SET ROLE anon")
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        owner.execute("SELECT * FROM nba.players")
    owner.execute("RESET ROLE")


def test_platform_occurrences_support_second_domain_and_reject_wrong_predecessor(
    imported: Any,
) -> None:
    _, conn, _, _, _, _ = imported
    a, b = uuid4(), uuid4()
    with conn.transaction():
        immutable_insert(
            conn,
            "platform",
            "events",
            {
                "event_id": a,
                "domain": "cards",
                "source_event_id": "match-a",
                "competition": "ranked",
                "season": "v1",
                "occurrence_no": 1,
                "predecessor_event_id": None,
            },
            ("event_id",),
        )
    with conn.transaction(), pytest.raises(psycopg.errors.CheckViolation):
        immutable_insert(
            conn,
            "platform",
            "events",
            {
                "event_id": b,
                "domain": "cards",
                "source_event_id": "other-match",
                "competition": "ranked",
                "season": "v1",
                "occurrence_no": 2,
                "predecessor_event_id": a,
            },
            ("event_id",),
        )


def test_later_revision_does_not_erase_eligible_older_history(imported: Any) -> None:
    _, conn, _, _, _, _ = imported
    # New revision has later receipt/validation and an older source publication.
    check = uuid4()
    conn.execute(
        "INSERT INTO platform.source_checks(check_id,run_id,source_id,adapter_version,"
        "requested_at,received_at,validated_at,source_published_at,raw_artifact_id,"
        "record_count,state,validation_summary) SELECT %s,run_id,source_id,adapter_version,"
        "'2026-10-25 12:30+00','2026-10-25 12:31+00','2026-10-25 12:32+00',"
        "'2026-01-01+00',raw_artifact_id,record_count,state,validation_summary "
        "FROM platform.source_checks LIMIT 1",
        (check,),
    )
    conn.execute(
        "INSERT INTO nba.player_game_versions(fact_id,event_id,player_id,team_id,source_check_id,"
        "observed_at,evidence_tier,participation,minutes_seconds,points) "
        "SELECT %s,event_id,player_id,team_id,%s,'2026-10-25 12:33+00',evidence_tier,"
        "participation,minutes_seconds,99 FROM nba.player_game_versions WHERE player_id='201'",
        (uuid4(), check),
    )
    early = player_history(conn, ["201"], parse_time("2026-10-25T12:15:00Z"))
    late = player_history(conn, ["201"], parse_time("2026-10-25T13:00:00Z"))
    assert early[0]["points"] == 10 and late[0]["points"] == 99


def test_synthetic_acceptance_never_authorizes_production(imported: Any) -> None:
    _, conn, plan, store, _, root = imported
    with pytest.raises(EvidenceError, match="Synthetic"):
        apply_seed(
            conn, store, plan, root / "archive", root / "checkpoint.json", environment="production"
        )


def test_roster_uses_verified_capability_and_keeps_rookies(imported: Any) -> None:
    from hoop.domains.nba.history.rosters import save_roster

    _, conn, _, store, _, _ = imported
    check = uuid4()
    conn.execute(
        """INSERT INTO platform.source_checks(check_id,run_id,source_id,adapter_version,
       requested_at,received_at,validated_at,raw_artifact_id,record_count,state,validation_summary)
       SELECT %s,run_id,source_id,adapter_version,requested_at,received_at,validated_at,
       raw_artifact_id,2,state,'{"capability":"roster"}'::jsonb
       FROM platform.source_checks LIMIT 1""",
        (check,),
    )
    with conn.cursor(row_factory=psycopg.rows.dict_row) as cursor:
        source = cursor.execute(
            "SELECT * FROM platform.source_checks WHERE check_id=%s", (check,)
        ).fetchone()
    roster = save_roster(
        conn,
        store,
        team_id="101",
        season="2026-27",
        source_check=source,
        players=[{"player_id": "201"}, {"player_id": "999", "availability": "unknown"}],
    )
    assert (
        save_roster(
            conn,
            store,
            team_id="101",
            season="2026-27",
            source_check=source,
            players=[{"player_id": "999", "availability": "unknown"}, {"player_id": "201"}],
        )
        == roster
    )
    assert conn.execute("SELECT count(*) FROM nba.roster_snapshots").fetchone() == (1,)
    with pytest.raises(EvidenceError):
        save_roster(conn, store, team_id="101", season="2026-27", source_check=source, players=[])


@pytest.mark.parametrize("minutes", ["NaN", "Infinity", "-Infinity", "-1"])
def test_invalid_minutes_are_rejected_in_sql(imported: Any, minutes: str) -> None:
    _, conn, _, _, _, _ = imported
    with pytest.raises(psycopg.errors.CheckViolation):
        conn.execute(
            """INSERT INTO nba.player_game_versions(fact_id,event_id,player_id,team_id,
          source_check_id,observed_at,evidence_tier,participation,minutes_seconds)
          SELECT %s,event_id,player_id,team_id,source_check_id,observed_at,evidence_tier,
          participation,%s FROM nba.player_game_versions LIMIT 1""",
            (uuid4(), minutes),
        )


def test_missing_event_status_remains_visible_in_history(imported: Any) -> None:
    owner, conn, _, _, _, _ = imported
    owner.execute("DELETE FROM platform.event_observations")
    rows = player_history(conn, ["201"], parse_time("2026-10-25T13:00:00Z"))
    assert len(rows) == 1 and rows[0]["event_state"] == "unknown"
    assert rows[0]["ambiguous_revision"]
