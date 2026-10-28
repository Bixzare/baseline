"""Pure planning verifies immutable inputs and reports every unresolved gate."""

from pathlib import Path

import pytest

from hoop.domains.nba.history.seed import plan_seed, recent_rows
from tests.fixtures.history_seed import fixture_seed


def test_fixture_plan_has_supporting_closure_and_short_histories(tmp_path: Path) -> None:
    _, _, plan = fixture_seed(tmp_path / "archive")
    assert not plan["blockers"]
    assert plan["counts"] == {"players": 2, "teams": 2, "games": 1, "short_player_histories": 2}
    assert plan["required_raw_bytes"] > 0 and not plan["historical_pregame_cohort_verified"]


def test_acceptance_is_not_inferred_from_a_successful_normalization(tmp_path: Path) -> None:
    report, manifest, _ = fixture_seed(tmp_path / "archive")
    plan = plan_seed(report, tmp_path / "archive", manifest)
    assert "seed_acceptance_missing" in plan["blockers"]
    assert "calendar_convention_unverified" in plan["blockers"]
    assert "original_request_observations_missing" in plan["blockers"]


def test_corrupt_source_prevents_even_planning(tmp_path: Path) -> None:
    report, manifest, _ = fixture_seed(tmp_path / "archive")
    artifact = report["normalized"]["players"]
    (tmp_path / "archive" / artifact["path"]).write_bytes(b"corrupt")
    with pytest.raises(ValueError):
        plan_seed(report, tmp_path / "archive", manifest)


@pytest.mark.parametrize("count", [0, 1, 9, 10, 11, 15])
def test_recent_window_crosses_teams_without_using_game_ids(count: int) -> None:
    rows = [
        {
            "player_id": "201",
            "team_id": "101" if i < 7 else "102",
            "game_date": f"2026-03-{i + 1:02d}",
            "game_id": str(100 - i),
            "competition": "regular",
            "season": "2025-26",
        }
        for i in range(count)
    ]
    blockers: list[str] = []
    selected = recent_rows(rows, "player_id", blockers)
    assert len(selected) == min(count, 10)
    assert [r["game_date"] for r in selected] == [
        f"2026-03-{i + 1:02d}" for i in range(count - 1, max(-1, count - 11), -1)
    ]
    assert not blockers


def test_ambiguous_dates_and_other_competitions_are_explicit() -> None:
    rows = [
        {
            "player_id": "201",
            "game_date": "2026-03-01",
            "competition": "regular",
            "season": "2025-26",
        }
    ] * 2
    blockers: list[str] = []
    assert len(recent_rows(rows, "player_id", blockers)) == 2
    assert blockers == ["ambiguous_source_date_order"]
    assert recent_rows([{**rows[0], "competition": "preseason"}], "player_id", []) == []


def test_staged_encoding_does_not_infer_source_acceptance(tmp_path: Path) -> None:
    from hoop.domains.nba.history.raw import stage_raw_archives

    report, manifest, _ = fixture_seed(tmp_path / "archive")
    staged = stage_raw_archives(report, tmp_path / "archive")
    plan = plan_seed(report, tmp_path / "archive", manifest, raw_archives=staged)
    assert "seed_acceptance_missing" in plan["blockers"]
    assert "calendar_convention_unverified" in plan["blockers"]
    assert plan["raw_archives"] == staged
    staged["files"]["Players.csv"]["original"]["sha256"] = "0" * 64
    with pytest.raises(ValueError):
        plan_seed(report, tmp_path / "archive", manifest, raw_archives=staged)


def test_calendar_only_owner_review_does_not_accept_seed(tmp_path: Path) -> None:
    report, manifest, original = fixture_seed(tmp_path / "archive")
    calendar_review = {**original["acceptance"], "kind": "owner_calendar_review"}
    plan = plan_seed(
        report, tmp_path / "archive", manifest, calendar_review, original["observations"]
    )
    assert plan["blockers"] == ["seed_acceptance_missing"]
    assert not plan["hosted_ready"]
    assert not plan["historical_pregame_cohort_verified"]


@pytest.mark.parametrize(
    "field,value",
    [
        ("manifest_sha256", "0" * 64),
        ("parser_version", "different-parser"),
        ("kind", "unreviewed"),
    ],
)
def test_calendar_approval_is_scoped_to_exact_seed_and_review_kind(
    tmp_path: Path, field: str, value: str
) -> None:
    report, manifest, original = fixture_seed(tmp_path / "archive")
    review = {**original["acceptance"], "kind": "owner_calendar_review", field: value}
    plan = plan_seed(report, tmp_path / "archive", manifest, review, original["observations"])
    assert plan["blockers"] == ["calendar_convention_unverified", "seed_acceptance_missing"]
