import copy
from datetime import UTC, datetime, timedelta

import pytest

from hoop.domains.nba.evaluation import periods
from hoop.platform.evaluation import evaluate
from hoop.platform.evidence import EvidenceError
from tests.fixtures.evaluation import TARGETS, numeric_event


def test_independent_errors_coverage_dnp_and_retrospective_diagnostics() -> None:
    report = evaluate([numeric_event()], TARGETS)
    assert report["metrics"]["points"]["mae"] == 4
    assert report["metrics"]["points"]["played_only_mae"] == 3
    assert report["metrics"]["points"]["dnp"] == 1
    assert report["metrics"]["minutes"]["mae"] == 10
    assert report["metrics"]["minutes"]["unresolved"] == 1
    assert report["coverage"]["known_opportunities"] == 6
    assert report["coverage"]["numeric_predictions"] == 5
    assert report["coverage"]["numeric_coverage"] == 5 / 6
    assert report["retrospective_participant_coverage"]["rate"] == 0.5
    point_errors = [x["signed_error"] for x in report["examples"] if x["target"] == "points"]
    assert point_errors == [-3, 5]
    assert report["comparison"]["reason"] == "no_challenger"


@pytest.mark.parametrize(
    "state", ["stored_unverified", "invalidated", "excluded", "pending_occurrence", "missing_batch"]
)
def test_invalid_categories_never_enter_mae(state: str) -> None:
    event = {**numeric_event(), "state": state}
    report = evaluate([event], TARGETS)
    assert report["metrics"]["points"]["mae"] is None
    assert report["coverage"]["covered_games"] == 0
    assert report["categories"][state] == 1


def test_unknown_denominator_and_empty_season_are_unavailable() -> None:
    event = {**numeric_event(), "state": "missing_batch", "cohort": None, "decisions": []}
    report = evaluate([numeric_event(), {**event, "event_id": "unknown"}], TARGETS)
    assert report["coverage"]["expected_opportunities"] is None
    assert report["coverage"]["numeric_coverage"] is None
    assert report["coverage"]["unknown_roster_games"] == 1
    empty = evaluate([], TARGETS)
    assert empty["metrics"]["minutes"]["mae"] is None
    assert empty["coverage"]["schedule_coverage"] is None


def test_duplicate_or_unit_conflict_is_not_silently_averaged() -> None:
    event = numeric_event()
    with pytest.raises(EvidenceError):
        evaluate([event, event], TARGETS)
    other = copy.deepcopy(event)
    other["actuals"][0]["unit"] = "seconds"
    with pytest.raises(EvidenceError):
        evaluate([other], TARGETS)


def test_rolling_periods_are_half_open_utc_and_season_bounded() -> None:
    cutoff = datetime(2026, 10, 27, tzinfo=UTC)
    policy = {"season_lower_bound": "2026-09-01T00:00:00Z"}
    windows = periods(cutoff, policy)
    assert windows["7d"] == (cutoff - timedelta(days=7), cutoff)
    assert windows["30d"] == (cutoff - timedelta(days=30), cutoff)
    assert windows["season"][0] == datetime(2026, 9, 1, tzinfo=UTC)
