"""Independent arithmetic, abstention policy, chronology and immutable snapshots."""

import copy
import json
import subprocess
import sys
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest

from hoop.domains.nba.baselines.model import prepare
from hoop.platform.evidence import EvidenceError
from hoop.platform.prepared import save_local, validate_entries
from hoop.platform.provenance import parse_time

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures/nba/preparation.json"


@pytest.fixture
def inputs() -> dict[str, Any]:
    return json.loads(FIXTURE.read_text())


def prepared(inputs: dict[str, Any]) -> dict[str, Any]:
    return prepare(inputs, generated_at=parse_time(inputs["fixture_generated_at"]))


def values(result: dict[str, Any], player: str = "201") -> dict[str, Any]:
    return {row["target"]: row["value"] for row in result["entries"] if row["subject_id"] == player}


def test_hand_calculated_minutes_and_pooled_rate_composition(inputs: dict[str, Any]) -> None:
    result = prepared(inputs)
    assert values(result) == {
        "minutes": 20.0,
        "points": 12.0,
        "rebounds": 5.0,
        "assists": 3.0,
        "threes_made": 2.0,
    }
    assert result["coverage"] == {"players": 3, "entries": 15, "numeric_entries": 10}
    assert all(
        row["reason_code"] == "no_history"
        for row in result["entries"]
        if row["subject_id"] == "999"
    )
    assert result["cohort"][0]["availability"] == "unavailable"
    assert not result["official_publication"] and result["publication_receipt"] is None


@pytest.mark.parametrize("seconds", [None, 0, -1, float("nan"), float("inf")])
def test_invalid_minutes_abstain_without_older_substitution(
    inputs: dict[str, Any], seconds: Any
) -> None:
    inputs["history"][0]["minutes_seconds"] = seconds
    result = prepared(inputs)
    assert set(values(result).values()) == {None}
    assert all(
        row["reason_code"] == "invalid_minutes"
        for row in result["entries"]
        if row["subject_id"] == "201"
    )
    assert result["features"][0]["history_count"] == 2


def test_missing_one_counting_stat_uses_no_smaller_window(inputs: dict[str, Any]) -> None:
    inputs["history"][0]["points"] = None
    result = prepared(inputs)
    assert values(result) == {
        "minutes": 20.0,
        "points": None,
        "rebounds": 5.0,
        "assists": 3.0,
        "threes_made": 2.0,
    }
    assert result["features"][0]["history_count"] == 2


@pytest.mark.parametrize("count", [1, 9, 10, 14])
def test_window_is_latest_ten_across_teams_and_seasons(inputs: dict[str, Any], count: int) -> None:
    template = inputs["history"][0]
    rows = []
    for number in range(1, count + 1):
        rows.append(
            {
                **template,
                "event_id": str(uuid4()),
                "source_event_id": str(100 - number),
                "fact_id": str(uuid4()),
                "game_date": f"2026-03-{number:02d}",
                "season": "2024-25" if number < 7 else "2025-26",
                "team_id": "101" if number < 7 else "102",
                "minutes_seconds": 600,
                "points": number,
            }
        )
    inputs["history"] = rows
    result = prepared(inputs)
    expected = (count + max(1, count - 9)) / 2
    assert values(result)["points"] == pytest.approx(expected)
    assert values(result)["minutes"] == 10
    assert result["features"][0]["history_count"] == min(10, count)


def test_overtime_is_not_capped_and_fractional_forecasts_are_retained(
    inputs: dict[str, Any],
) -> None:
    inputs["history"] = [
        {**inputs["history"][0], "minutes_seconds": 3300, "points": 5},
        {**inputs["history"][1], "minutes_seconds": 3000, "points": 6},
    ]
    assert values(prepared(inputs))["minutes"] == 52.5
    assert values(prepared(inputs))["points"] == 5.5


@pytest.mark.parametrize("change", ["late_correction", "future_game", "target_game"])
def test_future_and_target_outcomes_do_not_change_frozen_features(
    inputs: dict[str, Any], change: str
) -> None:
    original = prepared(inputs)
    row = copy.deepcopy(inputs["history"][0])
    row["fact_id"] = str(uuid4())
    row["source_check_id"] = str(uuid4())
    row["points"] = 999
    if change == "late_correction":
        row["received_at"] = "2026-10-26T14:00:01Z"
        row["validated_at"] = "2026-10-26T14:00:02Z"
        row["observed_at"] = "2026-10-26T14:00:03Z"
    else:
        row["event_id"] = str(uuid4())
        if change == "future_game":
            row["game_date"] = "2026-10-27"
        else:
            row["source_event_id"] = inputs["event"]["source_event_id"]
    inputs["history"].append(row)
    inputs["target_final_participants"] = ["999"]
    after = prepared(inputs)
    assert after["features"] == original["features"] and after["entries"] == original["entries"]
    assert after["input_hash"] == original["input_hash"]


@pytest.mark.parametrize(
    "change",
    [
        "stale_schedule",
        "late_roster",
        "started",
        "missing_roster",
        "dual_membership",
        "corrupt_roster",
    ],
)
def test_invalid_essential_cohorts_block_game(inputs: dict[str, Any], change: str) -> None:
    if change == "stale_schedule":
        inputs["schedule"]["received_at"] = "2026-10-26T12:00:00Z"
    elif change == "late_roster":
        inputs["rosters"][0]["validated_at"] = "2026-10-26T14:00:01Z"
    elif change == "started":
        inputs["schedule"]["event_state"] = "in_progress"
    elif change == "missing_roster":
        inputs["rosters"].pop()
    elif change == "dual_membership":
        inputs["rosters"][1] = inputs["rosters"][0]
    else:
        inputs["rosters"][0]["artifact_body"] = "{}"
    with pytest.raises(EvidenceError):
        prepared(inputs)


def test_known_gap_requests_reconciliation_and_ambiguous_date_abstains(
    inputs: dict[str, Any],
) -> None:
    inputs["gaps"] = [
        {"player_id": "201", "game_date": "2026-04-02", "observed_at": "2026-10-25T12:00:00Z"}
    ]
    result = prepared(inputs)
    assert result["reconciliation_requested"] == ["201"] and set(values(result).values()) == {None}
    inputs["gaps"] = []
    inputs["history"][0]["game_date"] = inputs["history"][1]["game_date"]
    assert all(
        row["reason_code"] == "ambiguous_history_order"
        for row in prepared(inputs)["entries"]
        if row["subject_id"] == "201"
    )


def test_saved_snapshot_reuses_verified_objects_and_detects_corruption(
    inputs: dict[str, Any], tmp_path: Path
) -> None:
    result = prepared(inputs)
    first = save_local(result, tmp_path)
    second = save_local(result, tmp_path)
    assert (
        not first["reused"] and second["reused"] and first["snapshot_id"] == second["snapshot_id"]
    )
    (tmp_path / first["objects"]["features"]["path"]).write_bytes(b"corrupt")
    with pytest.raises((EvidenceError, ValueError)):
        save_local(result, tmp_path)


def test_cli_and_package_agree_and_second_domain_output_is_generic(
    inputs: dict[str, Any], tmp_path: Path
) -> None:
    expected = save_local(prepared(inputs), tmp_path)
    run = subprocess.run(
        [
            sys.executable,
            "-m",
            "hoop.domains.nba.baselines",
            "fixture",
            "--input",
            str(FIXTURE),
            "--output",
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert run.returncode == 0, run.stdout + run.stderr
    assert json.loads(run.stdout)["snapshot_id"] == expected["snapshot_id"]
    validate_entries(
        [
            {
                "subject_type": "deck",
                "subject_id": "blue",
                "target": "margin",
                "unit": "score",
                "value": -0.5,
                "reason_code": None,
            }
        ]
    )


def test_verified_starts_resolve_same_day_order_and_unknown_dates_abstain(
    inputs: dict[str, Any],
) -> None:
    inputs["history"][0]["actual_start"] = "2026-04-01T12:00:00Z"
    inputs["history"][1]["actual_start"] = "2026-04-01T20:00:00Z"
    inputs["history"][1]["game_date"] = "2026-04-01"
    assert values(prepared(inputs))["points"] == 12
    for row in inputs["history"]:
        row["actual_start"] = None
        row["game_date"] = "unverified-date"
    assert set(values(prepared(inputs)).values()) == {None}


def test_unknown_schedule_time_is_a_blocked_game(inputs: dict[str, Any]) -> None:
    inputs["schedule"]["scheduled_start"] = None
    with pytest.raises(EvidenceError):
        prepared(inputs)


@pytest.mark.parametrize("container", ["details", "source_summary"])
def test_stale_source_generation_blocks_even_with_recent_collection(
    inputs: dict[str, Any], container: str
) -> None:
    inputs["schedule"][container] = {"source_generated_at": "2026-10-25T00:00:00Z"}
    with pytest.raises(EvidenceError):
        prepared(inputs)


def test_equivalent_revision_json_ties_are_not_marked_conflicting(inputs: dict[str, Any]) -> None:
    from hoop.domains.nba.history.readers import eligible_latest

    source = inputs["history"][0]
    first = {**source, "details": {"a": 1, "b": 2}}
    other = {**source, "source_check_id": str(uuid4()), "details": {"b": 2, "a": 1}}
    result = eligible_latest(
        [first, other], parse_time(inputs["feature_cutoff"]), ("event_id",), ("details",)
    )
    assert len(result) == 1 and not result[0]["ambiguous_revision"]
