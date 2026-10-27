from datetime import UTC, datetime

import pytest

from hoop.domains.nba.outcomes import normalize_final, outcome_entries
from hoop.platform.outcomes import validate_outcomes
from tests.fixtures.finals import final_context, final_payload

NOW = datetime(2026, 10, 27, tzinfo=UTC)
COHORT = [{"player_id": "201", "team_id": "101"}, {"player_id": "999", "team_id": "101"}]


def test_overtime_precision_absent_player_and_confirmed_dnp_are_distinct() -> None:
    payload = final_payload()
    normalized = normalize_final(payload, final_context(), NOW)
    assert normalized["players"][0]["minutes_seconds"] == "3192.50"
    entries = outcome_entries(normalized, COHORT)
    assert validate_outcomes(entries) == "partial"
    assert all(x["value"] is None for x in entries if x["subject_id"] == "999")
    payload["game"]["homeTeam"]["players"].append(
        {"personId": 999, "played": "0", "notPlayingReason": "injury", "statistics": {}}
    )
    entries = outcome_entries(normalize_final(payload, final_context(), NOW), COHORT)
    assert all(x["value"] == 0 for x in entries if x["subject_id"] == "999")
    assert validate_outcomes(entries) == "final"
    unknown_context = {**final_context(), "dnp_semantics": "unknown_until_accepted"}
    assert all(
        x["value"] is None
        for x in outcome_entries(normalize_final(payload, unknown_context, NOW), COHORT)
        if x["subject_id"] == "999"
    )


def test_missing_single_stat_stays_partial_and_zero_minutes_does_not_imply_dnp() -> None:
    payload = final_payload()
    payload["game"]["homeTeam"]["players"][0]["statistics"].pop("assists")
    payload["game"]["homeTeam"]["players"][0]["statistics"]["minutes"] = "PT0M00.00S"
    normalized = normalize_final(payload, final_context(), NOW)
    assert normalized["players"][0]["participation"] == "played"
    entries = outcome_entries(normalized, COHORT[:1])
    assert (
        next(x["value"] for x in entries if x["subject_id"] == "201" and x["target"] == "assists")
        is None
    )
    assert (
        next(x["value"] for x in entries if x["subject_id"] == "201" and x["target"] == "minutes")
        == 0
    )
    assert validate_outcomes(entries) == "partial"


@pytest.mark.parametrize(
    "problem",
    ["team", "score", "player", "negative", "nonfinite", "dnp", "duplicate", "future", "tied"],
)
def test_conflicting_final_is_rejected(problem: str) -> None:
    payload = final_payload()
    home = payload["game"]["homeTeam"]
    if problem == "team":
        home["teamId"] = 103
    elif problem == "score":
        home["score"] = 99
    elif problem == "player":
        home["players"][0]["personId"] = None
    elif problem == "negative":
        home["players"][0]["statistics"]["assists"] = -1
    elif problem == "nonfinite":
        home["players"][0]["statistics"]["points"] = float("nan")
    elif problem == "dnp":
        home["players"][0].update(played="0", notPlayingReason="injury")
    elif problem == "duplicate":
        home["players"].append(home["players"][0])
    elif problem == "future":
        payload["game"]["gameTimeUTC"] = "2027-01-01T00:00:00Z"
    else:
        home["score"] = 90
        home["statistics"]["points"] = 90
        home["players"][0]["statistics"]["points"] = 90
    with pytest.raises((ValueError, KeyError, TypeError)):
        normalize_final(payload, final_context(), NOW)


def test_generic_outcomes_allow_a_signed_second_domain() -> None:
    assert (
        validate_outcomes(
            [
                {
                    "subject_type": "deck",
                    "subject_id": "d1",
                    "target": "margin",
                    "unit": "crowns",
                    "value": -2,
                    "reason_code": None,
                }
            ]
        )
        == "final"
    )
