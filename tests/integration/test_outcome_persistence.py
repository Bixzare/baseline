"""Immutable outcome versions and actual-role reconciliation on real Postgres."""

from datetime import timedelta
from pathlib import Path
from typing import Any
from uuid import UUID

import psycopg
import pytest
from psycopg.conninfo import make_conninfo

from hoop.domains.nba.outcomes import ingest_final, normalize_final, pending_work
from hoop.domains.nba.publication import publish_player
from hoop.platform.database import provision_runtime
from tests.fixtures.finals import final_context, final_payload
from tests.fixtures.publication import publication_fixture

pytestmark = pytest.mark.postgres
CONFIG = {
    "schema_version": 1,
    "dnp_semantics": "played0_with_reason",
    "calendar_convention": "source_calendar_verified",
}


@pytest.fixture
def final_fixture(migrated: Any, tmp_path: Path) -> Any:
    dsn, owner = migrated
    p = publication_fixture(owner, tmp_path)
    p["forecast"] = publish_player(owner, p["store"], p["retained"], UUID(p["bundle"]))
    p["payload"] = final_payload(p["now"] - timedelta(hours=3))
    p["check"] = p["source"]("final", p["payload"])
    p["normalized"] = normalize_final(p["payload"], final_context(), p["now"])
    provision_runtime(owner, "synthetic_fixture_password_only")
    with psycopg.connect(
        make_conninfo(dsn, user="baseline_runtime", password="synthetic_fixture_password_only"),
        autocommit=True,
    ) as conn:
        yield {
            **p,
            "conn": conn,
            "owner": owner,
            "dsn": make_conninfo(
                dsn, user="baseline_runtime", password="synthetic_fixture_password_only"
            ),
        }


def test_runtime_appends_corrected_outcomes_without_changing_forecasts(final_fixture: Any) -> None:
    p = final_fixture
    conn = p["conn"]
    before = conn.execute(
        "SELECT prediction_id,value FROM platform.predictions ORDER BY prediction_id"
    ).fetchall()
    first = ingest_final(conn, p["store"], p["event"], p["check"], p["normalized"], config=CONFIG)
    assert first["state"] == "partial" and first["unresolved"] == 5
    assert (
        ingest_final(conn, p["store"], p["event"], p["check"], p["normalized"], config=CONFIG)[
            "outcome_version_id"
        ]
        == first["outcome_version_id"]
    )
    p["payload"]["game"]["homeTeam"]["players"].append(
        {"personId": 999, "played": "0", "notPlayingReason": "inactive"}
    )
    changed_check = p["source"]("final", p["payload"])
    changed = normalize_final(p["payload"], final_context(), p["now"])
    second = ingest_final(conn, p["store"], p["event"], changed_check, changed, config=CONFIG)
    assert (
        second["state"] == "final" and second["outcome_version_id"] != first["outcome_version_id"]
    )
    assert conn.execute("SELECT count(*) FROM platform.outcome_versions").fetchone() == (2,)
    assert (
        conn.execute(
            "SELECT prediction_id,value FROM platform.predictions ORDER BY prediction_id"
        ).fetchall()
        == before
    )
    assert conn.execute("SELECT count(*) FROM platform.publication_receipts").fetchone() == (1,)
    for statement in [
        "DELETE FROM platform.outcome_versions",
        "UPDATE platform.outcome_versions SET state='final'",
        "TRUNCATE platform.outcome_observations",
    ]:
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute(statement)


def test_parser_config_revision_of_same_source_and_rollback_are_versioned(
    final_fixture: Any,
) -> None:
    p = final_fixture

    def fail(stage: str) -> None:
        raise OSError("injected")

    with pytest.raises(OSError):
        ingest_final(
            p["conn"],
            p["store"],
            p["event"],
            p["check"],
            p["normalized"],
            config=CONFIG,
            fault=fail,
        )
    assert p["conn"].execute("SELECT count(*) FROM platform.outcome_versions").fetchone() == (0,)
    first = ingest_final(
        p["conn"], p["store"], p["event"], p["check"], p["normalized"], config=CONFIG
    )
    second = ingest_final(
        p["conn"],
        p["store"],
        p["event"],
        p["check"],
        p["normalized"],
        config={**CONFIG, "revision": 2},
    )
    assert first["outcome_version_id"] != second["outcome_version_id"]
    assert p["conn"].execute(
        "SELECT count(*) FROM nba.player_game_versions WHERE event_id=%s", (p["event"],)
    ).fetchone() == (4,)


def test_same_facts_new_source_observation_reuses_semantic_version(final_fixture: Any) -> None:
    p = final_fixture
    first = ingest_final(
        p["conn"], p["store"], p["event"], p["check"], p["normalized"], config=CONFIG
    )
    later = p["source"]("final", p["payload"])
    second = ingest_final(p["conn"], p["store"], p["event"], later, p["normalized"], config=CONFIG)
    assert second["outcome_version_id"] == first["outcome_version_id"] and second["reused"]
    assert p["conn"].execute("SELECT count(*) FROM platform.outcome_observations").fetchone() == (
        2,
    )
    assert pending_work(p["conn"], p["now"] + timedelta(days=10), event_ids=[p["event"]])
    # Partial outcomes stay in work even outside seven days.
    assert pending_work(p["conn"], p["now"] + timedelta(days=10))


def test_full_outcome_leaves_automatic_horizon_but_explicit_ids_and_ranges_recover_it(
    final_fixture: Any,
) -> None:
    p = final_fixture
    p["payload"]["game"]["homeTeam"]["players"].append(
        {"personId": 999, "played": "0", "notPlayingReason": "inactive"}
    )
    check = p["source"]("final", p["payload"])
    normalized = normalize_final(p["payload"], final_context(), p["now"])
    ingest_final(p["conn"], p["store"], p["event"], check, normalized, config=CONFIG)
    later = p["now"] + timedelta(days=10)
    assert pending_work(p["conn"], later) == []
    assert pending_work(p["conn"], later, event_ids=[p["event"]])
    assert pending_work(p["conn"], later, date_from=p["now"] - timedelta(days=1), date_to=p["now"])


def test_final_revisions_cannot_change_earlier_feature_cohort(final_fixture: Any) -> None:
    from hoop.domains.nba.baselines.capture import capture_game
    from hoop.domains.nba.baselines.model import prepare
    from hoop.platform.provenance import parse_time

    p = final_fixture
    ingest_final(p["conn"], p["store"], p["event"], p["check"], p["normalized"], config=CONFIG)
    inputs = capture_game(
        p["conn"], p["store"], p["event"], parse_time(p["prepared"]["feature_cutoff"])
    )
    reproduced = prepare(inputs, generated_at=parse_time(p["prepared"]["generated_at"]))
    assert reproduced["cohort"] == p["prepared"]["cohort"]
    assert reproduced["entries"] == p["prepared"]["entries"]
    assert reproduced["input_hash"] == p["prepared"]["input_hash"]


def test_raw_corruption_and_substituted_normalization_are_refused(final_fixture: Any) -> None:
    import copy

    from hoop.platform.artifacts import ArtifactError
    from hoop.platform.evidence import EvidenceError

    p = final_fixture
    changed = copy.deepcopy(p["normalized"])
    changed["players"][0]["points"] = 1
    with pytest.raises(EvidenceError):
        ingest_final(p["conn"], p["store"], p["event"], p["check"], changed, config=CONFIG)
    p["store"].session.transport.corrupt = True
    with pytest.raises(ArtifactError):
        ingest_final(p["conn"], p["store"], p["event"], p["check"], p["normalized"], config=CONFIG)


def test_two_workers_reuse_one_semantic_version(final_fixture: Any) -> None:
    from concurrent.futures import ThreadPoolExecutor

    p = final_fixture
    dsn = p["dsn"]

    def run(_: int) -> Any:
        with psycopg.connect(dsn, autocommit=True) as other:
            return ingest_final(
                other, p["store"], p["event"], p["check"], p["normalized"], config=CONFIG
            )

    with ThreadPoolExecutor(max_workers=2) as workers:
        results = list(workers.map(run, [1, 2]))
    assert results[0]["outcome_version_id"] == results[1]["outcome_version_id"]
    assert p["conn"].execute("SELECT count(*) FROM platform.outcome_versions").fetchone() == (1,)


@pytest.mark.parametrize("denied", [False, True])
def test_reconciliation_uses_persisted_work_and_retains_source_health(
    final_fixture: Any, tmp_path: Path, denied: bool
) -> None:
    from uuid import uuid4

    from hoop.domains.nba.outcomes import reconcile
    from hoop.domains.nba.sources.policy import Policy, ProbeRunner, Response
    from hoop.platform.prepared import encoded
    from hoop.platform.provenance import Archive
    from tests.fixtures.finals import final_route
    from tests.unit.test_source_policy import FakeClock, FakeTransport

    p = final_fixture
    p["owner"].execute(
        "UPDATE platform.event_observations SET scheduled_start=%s WHERE event_id=%s",
        (p["now"] - timedelta(hours=3), p["event"]),
    )

    class Clock(FakeClock):
        def now(self) -> Any:
            return p["now"] + timedelta(seconds=self.elapsed)

    response = Response(403, b"denied", {}) if denied else Response(200, encoded(p["payload"]), {})
    runner = ProbeRunner(
        Archive(tmp_path / "source"), FakeTransport([response]), Clock(), Policy(), str(uuid4())
    )
    result = reconcile(
        p["conn"],
        p["store"],
        runner,
        {**CONFIG, "routes": [final_route(template=True)]},
        "local",
        rehearsal=True,
        event_ids=[p["event"]],
    )
    assert result["requests"] == 1
    assert result["state"] == ("incomplete" if denied else "succeeded")
    assert p["conn"].execute(
        "SELECT state FROM platform.source_checks WHERE run_id=%s", (runner.run_id,)
    ).fetchone() == ("invalid" if denied else "accepted",)
