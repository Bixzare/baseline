"""Immutable observations, concurrent rescheduling, and real retained source attempts."""

from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

import psycopg
import pytest

from hoop.domains.nba.collection import apply_game, collect, teams_needing_rosters, work_list
from hoop.domains.nba.publication import publish_player
from hoop.domains.nba.sources.policy import Policy, ProbeRunner, Response
from hoop.platform.evidence import EvidenceError
from hoop.platform.ledger.publication import status
from hoop.platform.provenance import Archive
from tests.fixtures.publication import publication_fixture
from tests.unit.test_collection import ROOT, route
from tests.unit.test_source_policy import FakeClock, FakeTransport

pytestmark = pytest.mark.postgres


def test_postponement_creates_one_successor_and_preserves_original_batch(
    migrated: Any, tmp_path: Path
) -> None:
    from uuid import UUID

    dsn, conn = migrated
    p = publication_fixture(conn, tmp_path)
    result = publish_player(conn, p["store"], p["retained"], UUID(p["bundle"]))
    record = {
        "game_id": "0022600001",
        "home_team_id": "101",
        "away_team_id": "102",
        "state": "postponed",
        "start_utc": None,
    }
    check = p["source"]("status", {})
    first = apply_game(conn, record, check)
    assert first["event_id"] == str(p["event"])
    assert status(conn, result["batch_id"])["state"] == "invalidated"
    check2 = p["source"]("schedule", {})
    # A later accepted observation, not an arbitrary missing/delayed entry.
    conn.execute(
        "UPDATE platform.source_checks SET validated_at=%s WHERE check_id=%s",
        (p["now"] + timedelta(seconds=1), check2["check_id"]),
    )
    check2["validated_at"] = conn.execute(
        "SELECT validated_at FROM platform.source_checks WHERE check_id=%s", (check2["check_id"],)
    ).fetchone()[0]
    record = {
        **record,
        "state": "scheduled",
        "start_utc": (p["now"] + timedelta(days=1)).isoformat(),
    }

    def run(_: int) -> Any:
        with psycopg.connect(dsn, autocommit=True) as other:
            return apply_game(other, record, check2)

    with ThreadPoolExecutor(max_workers=2) as workers:
        rows = list(workers.map(run, [1, 2]))
    assert rows[0]["event_id"] == rows[1]["event_id"] != first["event_id"]
    assert (
        apply_game(conn, {**record, "state": "postponed", "start_utc": None}, check)["event_id"]
        == first["event_id"]
    )
    assert conn.execute(
        "SELECT count(*) FROM platform.events WHERE predecessor_event_id=%s", (p["event"],)
    ).fetchone() == (1,)
    assert conn.execute("SELECT count(*) FROM platform.forecast_batches").fetchone() == (1,)
    assert len(work_list(conn, p["now"])) == 1
    assert teams_needing_rosters(conn, p["now"] + timedelta(hours=24))


def test_repeat_raw_bytes_keep_distinct_source_observation_times_and_rosters(
    migrated: Any, tmp_path: Path
) -> None:
    _, conn = migrated
    p = publication_fixture(conn, tmp_path / "seed")
    clock = FakeClock()
    transport = FakeTransport([Response(200, (ROOT / "scoreboard.json").read_bytes(), {})] * 2)
    runner = ProbeRunner(Archive(tmp_path / "archive"), transport, clock, Policy(), str(uuid4()))
    routes = [route(), route()]
    result = collect(conn, p["store"], runner, routes, "local", rehearsal=True)
    assert result["state"] == "succeeded" and result["requests"] == 2
    assert clock.elapsed == 3
    rows = conn.execute(
        "SELECT raw_artifact_id,received_at FROM platform.source_checks WHERE "
        "run_id=%s ORDER BY received_at",
        (runner.run_id,),
    ).fetchall()
    assert len(rows) == 2 and rows[0][0] == rows[1][0] and rows[0][1] != rows[1][1]
    assert len(result["results"]) == 2


def test_denial_stops_source_and_keeps_failed_health(migrated: Any, tmp_path: Path) -> None:
    _, conn = migrated
    p = publication_fixture(conn, tmp_path / "seed")
    runner = ProbeRunner(
        Archive(tmp_path / "archive"),
        FakeTransport([Response(403, b"denied", {})]),
        FakeClock(),
        Policy(),
        str(uuid4()),
    )
    result = collect(conn, p["store"], runner, [route(), route()], "local", rehearsal=True)
    assert result["state"] == "incomplete" and result["requests"] == 1
    assert conn.execute(
        "SELECT state FROM platform.source_checks WHERE run_id=%s", (runner.run_id,)
    ).fetchone() == ("invalid",)
    with pytest.raises(EvidenceError):
        collect(conn, p["store"], runner, [], "local", rehearsal=True)


def test_restricted_runtime_collects_current_roster_without_using_final_members(
    migrated: Any, tmp_path: Path
) -> None:
    from psycopg.conninfo import make_conninfo

    from hoop.platform.database import provision_runtime

    dsn, owner = migrated
    p = publication_fixture(owner, tmp_path / "seed")
    provision_runtime(owner, "synthetic_fixture_password_only")
    r = route("roster", context={"season": "2026-27", "team_id": 1610612738})
    runner = ProbeRunner(
        Archive(tmp_path / "archive"),
        FakeTransport([Response(200, (ROOT / "roster.json").read_bytes(), {})]),
        FakeClock(),
        Policy(),
        str(uuid4()),
    )
    # The new team identity is supported separately from any final participant list.
    owner.execute("INSERT INTO nba.teams(team_id) VALUES('1610612738')")
    with psycopg.connect(
        make_conninfo(dsn, user="baseline_runtime", password="synthetic_fixture_password_only"),
        autocommit=True,
    ) as conn:
        result = collect(conn, p["store"], runner, [r], "local", rehearsal=True)
        assert result["state"] == "succeeded"
        assert conn.execute(
            "SELECT count(*) FROM nba.roster_snapshots WHERE team_id='1610612738'"
        ).fetchone() == (1,)


def test_storage_failure_cannot_create_accepted_source(migrated: Any, tmp_path: Path) -> None:
    _, conn = migrated
    p = publication_fixture(conn, tmp_path / "seed")
    p["store"].session.transport.upload_status = 503
    runner = ProbeRunner(
        Archive(tmp_path / "archive"),
        FakeTransport([Response(200, (ROOT / "scoreboard.json").read_bytes(), {})]),
        FakeClock(),
        Policy(),
        str(uuid4()),
    )
    result = collect(conn, p["store"], runner, [route()], "local", rehearsal=True)
    assert result["state"] == "incomplete"
    assert conn.execute(
        "SELECT state,validated_at FROM platform.source_checks WHERE run_id=%s", (runner.run_id,)
    ).fetchone() == ("storage_failure", None)


def test_lifecycle_failure_preserves_source_and_can_retry_without_refetch(
    migrated: Any, tmp_path: Path, monkeypatch: Any
) -> None:
    from uuid import UUID

    from hoop.domains.nba import collection

    _, conn = migrated
    p = publication_fixture(conn, tmp_path)
    result = publish_player(conn, p["store"], p["retained"], UUID(p["bundle"]))
    original = collection.append_pending_lifecycle

    def fail(*args: Any) -> None:
        raise EvidenceError("injected lifecycle outage")

    monkeypatch.setattr(collection, "append_pending_lifecycle", fail)
    check = p["source"]("status", {})
    record = {
        "game_id": "0022600001",
        "home_team_id": "101",
        "away_team_id": "102",
        "state": "cancelled",
        "start_utc": None,
    }
    with pytest.raises(EvidenceError):
        apply_game(conn, record, check)
    assert status(conn, result["batch_id"])["state"] == "invalidated"
    observation = conn.execute(
        "SELECT observation_id FROM platform.event_observations WHERE source_check_id=%s",
        (check["check_id"],),
    ).fetchone()[0]
    original(conn, p["event"], observation)
    original(conn, p["event"], observation)
    assert conn.execute("SELECT count(*) FROM platform.prediction_events").fetchone() == (1,)
