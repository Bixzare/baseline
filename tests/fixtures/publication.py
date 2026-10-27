"""Real Postgres + memory HTTP boundary, with source times relative to DB clock."""

from datetime import timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

from hoop.domains.nba.baselines.capture import capture_game
from hoop.domains.nba.baselines.model import prepare
from hoop.domains.nba.history.rosters import save_roster
from hoop.domains.nba.history.seed import apply_seed
from hoop.platform.artifacts import PrivateArtifacts, Session, retain
from hoop.platform.evidence import register
from hoop.platform.ledger.bootstrap import bootstrap
from hoop.platform.prepared import encoded, retain_prepared
from tests.fixtures.history_seed import fixture_seed
from tests.fixtures.storage_client import SETTINGS, MemoryStorage


def publication_fixture(conn: Any, root: Path) -> dict[str, Any]:
    store = PrivateArtifacts(Session(SETTINGS, MemoryStorage()))
    _, _, plan = fixture_seed(root / "archive")
    seed = apply_seed(conn, store, plan, root / "archive", root / "checkpoint.json")
    now = conn.execute("SELECT clock_timestamp()").fetchone()[0] - timedelta(seconds=5)
    event = uuid4()
    conn.execute(
        "INSERT INTO platform.events(event_id,domain,source_event_id,competition,se"
        "ason,occurrence_no) VALUES(%s,'nba','0022600001','regular','2026-27',1)",
        (event,),
    )
    conn.execute("INSERT INTO nba.games VALUES(%s,'101','102','Regular Season')", (event,))

    def source(capability: str, payload: dict[str, Any]) -> dict[str, Any]:
        raw = retain(conn, store, encoded(payload), kind="raw", format="json", manifest={})
        return register(
            conn,
            "source_checks",
            {
                "check_id": str(uuid4()),
                "run_id": seed["run_id"],
                "source_id": "fixture",
                "adapter_version": "fixture-v1",
                "requested_at": now - timedelta(seconds=2),
                "received_at": now - timedelta(seconds=1),
                "validated_at": now,
                "source_published_at": None,
                "raw_artifact_id": raw["artifact_id"],
                "http_status": None,
                "record_count": 1,
                "state": "accepted",
                "validation_summary": {"capability": capability},
            },
        )

    check = source("status", {"state": "scheduled"})
    observation = uuid4()
    conn.execute(
        "INSERT INTO platform.event_observations(observation_id,event_id,source_che"
        "ck_id,observed_at,scheduled_start,state,details) "
        "VALUES(%s,%s,%s,%s,%s,'scheduled','{}')",
        (observation, event, check["check_id"], now, now + timedelta(hours=2)),
    )
    for team, ids in [("101", ["201", "999"]), ("102", ["202"])]:
        members = [{"player_id": p} for p in ids]
        roster_check = source("roster", {"team_id": team, "players": members})
        save_roster(
            conn, store, team_id=team, season="2026-27", source_check=roster_check, players=members
        )
    inputs = capture_game(conn, store, event, now + timedelta(seconds=1))
    prepared = prepare(inputs, generated_at=now + timedelta(seconds=2))
    retained = retain_prepared(conn, store, prepared)
    registered = bootstrap(conn, store, retained["descriptor"])
    return {
        "store": store,
        "prepared": prepared,
        "retained": retained,
        "bundle": registered["bundle_id"],
        "event": event,
        "source": source,
        "now": now,
        "observation": observation,
    }
