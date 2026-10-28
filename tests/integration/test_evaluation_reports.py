"""As-of manifests, immutable reports, actual roles and later correction isolation."""

from datetime import timedelta
from pathlib import Path
from typing import Any
from uuid import UUID

import psycopg
import pytest
from psycopg.conninfo import make_conninfo

from hoop.domains.nba.evaluation import capture, persist, reproduce
from hoop.domains.nba.publication import publish_player
from hoop.platform.database import provision_runtime
from tests.fixtures.publication import publication_fixture

pytestmark = pytest.mark.postgres


def test_real_report_reproduces_at_cutoff_after_later_observation(
    migrated: Any, tmp_path: Path
) -> None:
    dsn, owner = migrated
    p = publication_fixture(owner, tmp_path)
    publish_player(owner, p["store"], p["retained"], UUID(p["bundle"]))
    provision_runtime(owner, "synthetic_fixture_password_only")
    with psycopg.connect(
        make_conninfo(dsn, user="baseline_runtime", password="synthetic_fixture_password_only"),
        autocommit=True,
    ) as conn:
        cutoff = conn.execute("SELECT clock_timestamp()").fetchone()[0]
        start = p["now"] - timedelta(days=1)
        # Future games cannot belong to a completed report period. Owner fixture
        # moves its saved schedule into this period before freezing a new cutoff.
        owner.execute(
            "UPDATE platform.event_observations SET scheduled_start=%s WHERE event_id=%s",
            (p["now"], p["event"]),
        )
        cutoff = conn.execute("SELECT clock_timestamp()").fetchone()[0]
        frozen = capture(conn, p["store"], start, cutoff, cutoff, kind="rehearsal")
        assert frozen["report"]["categories"] == {"invalidated": 1}
        first = persist(conn, p["store"], frozen)
        assert persist(conn, p["store"], frozen)["report_id"] == first["report_id"]
        assert reproduce(conn, p["store"], UUID(first["report_id"]))["reproduced"]
        # A genuine later append must never affect the earlier report manifest.
        check = p["source"]("status", {})
        owner.execute(
            "INSERT INTO platform.event_observations(observation_id,event_id,source_che"
            "ck_id,observed_at,state,details) "
            "VALUES(gen_random_uuid(),%s,%s,clock_timestamp(),'cancelled','{}')",
            (p["event"], check["check_id"]),
        )
        again = capture(conn, p["store"], start, cutoff, cutoff, kind="rehearsal")
        assert again == frozen
        later = conn.execute("SELECT clock_timestamp()").fetchone()[0]
        revised = capture(conn, p["store"], start, cutoff, later, kind="rehearsal")
        assert revised["report"]["categories"] == {"excluded": 1}
        assert persist(conn, p["store"], revised)["report_id"] != first["report_id"]
        live = capture(conn, p["store"], start, cutoff, later, kind="live")
        assert live["report"]["coverage"]["expected_games"] == 0
        for statement in [
            "UPDATE platform.evaluation_reports SET report_kind='live'",
            "DELETE FROM platform.evaluation_reports",
            "TRUNCATE platform.evaluation_reports",
        ]:
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                conn.execute(statement)
        owner.execute("SET ROLE anon")
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            owner.execute("SELECT * FROM platform.evaluation_reports")
        owner.execute("RESET ROLE")


def test_uncovered_rosters_after_deadline_cannot_reconstruct_denominator(
    migrated: Any, tmp_path: Path
) -> None:
    _, conn = migrated
    p = publication_fixture(conn, tmp_path)
    conn.execute(
        "UPDATE platform.event_observations SET scheduled_start=%s WHERE event_id=%s",
        (p["now"], p["event"]),
    )
    cutoff = conn.execute("SELECT clock_timestamp()").fetchone()[0]
    frozen = capture(
        conn, p["store"], p["now"] - timedelta(days=1), cutoff, cutoff, kind="rehearsal"
    )
    assert frozen["report"]["coverage"]["unknown_roster_games"] == 1
    assert frozen["report"]["coverage"]["expected_opportunities"] is None


def test_positive_report_freezes_outcome_revision_and_rolls_back_interrupted_write(
    migrated: Any, tmp_path: Path
) -> None:
    from hoop.domains.nba.outcomes import ingest_final, normalize_final
    from tests.fixtures.finals import final_context, final_payload

    _, conn = migrated
    p = publication_fixture(conn, tmp_path)
    result = publish_player(conn, p["store"], p["retained"], UUID(p["bundle"]))
    # Invented historical ledger metadata in a disposable owner-only fixture.
    # This tests report arithmetic, not the production timing guarantee.
    now = conn.execute("SELECT clock_timestamp()").fetchone()[0]
    conn.execute(
        "UPDATE platform.forecast_batches SET "
        "feature_cutoff=%s,generated_at=%s,recorded_at=%s,scheduled_start=%s WHERE "
        "batch_id=%s",
        (
            now - timedelta(hours=4),
            now - timedelta(hours=3, minutes=30),
            now - timedelta(hours=3),
            now - timedelta(hours=2),
            result["batch_id"],
        ),
    )
    conn.execute(
        "UPDATE platform.publication_receipts SET observed_committed_at=%s WHERE batch_id=%s",
        (now - timedelta(hours=2, minutes=30), result["batch_id"]),
    )
    conn.execute(
        "UPDATE platform.event_observations SET scheduled_start=%s WHERE event_id=%s",
        (now - timedelta(hours=2), p["event"]),
    )
    payload = final_payload(now - timedelta(hours=2))
    check = p["source"]("final", payload)
    normalized = normalize_final(payload, final_context(), now)
    config = {
        "dnp_semantics": "played0_with_reason",
        "calendar_convention": "source_calendar_verified",
    }
    ingest_final(conn, p["store"], p["event"], check, normalized, config=config)
    cutoff = conn.execute("SELECT clock_timestamp()").fetchone()[0]
    frozen = capture(conn, p["store"], now - timedelta(days=1), cutoff, cutoff, kind="rehearsal")
    # 201: |10-100|=90; 202: |9-90|=81, mean=85.5 points.
    assert frozen["report"]["metrics"]["points"]["mae"] == 85.5
    assert frozen["report"]["coverage"]["numeric_coverage"] == 10 / 15
    assert frozen["report"]["metrics"]["points"]["abstained"] == 1

    def fail() -> None:
        raise OSError("interrupted")

    with pytest.raises(OSError):
        persist(conn, p["store"], frozen, fault=fail)
    assert conn.execute("SELECT count(*) FROM platform.evaluation_reports").fetchone() == (0,)
    first = persist(conn, p["store"], frozen)
    payload["game"]["homeTeam"]["players"][0]["statistics"]["points"] = 102
    payload["game"]["homeTeam"]["score"] = 102
    payload["game"]["homeTeam"]["statistics"]["points"] = 102
    revised = p["source"]("final", payload)
    ingest_final(
        conn,
        p["store"],
        p["event"],
        revised,
        normalize_final(payload, final_context(), now),
        config=config,
    )
    assert (
        reproduce(conn, p["store"], UUID(first["report_id"]))["summary"]["metrics"]["points"]["mae"]
        == 85.5
    )
    later = conn.execute("SELECT clock_timestamp()").fetchone()[0]
    newer = capture(conn, p["store"], now - timedelta(days=1), cutoff, later, kind="rehearsal")
    assert newer["report"]["metrics"]["points"]["mae"] == 86.5
