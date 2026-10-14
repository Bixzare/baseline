"""Synthetic NBA schema and identity cases; no live source acceptance claims."""

import copy
import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from hoop.domains.nba.sources.policy import ProbeRequest
from hoop.domains.nba.sources.probe import local_requests
from hoop.domains.nba.sources.validate import game_identity, identity_joins, minutes, validate

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "nba"
NOW = datetime(2026, 10, 14, 23, 30, tzinfo=UTC)


def fixture(name: str) -> dict[str, Any]:
    return json.loads((FIXTURES / f"{name}.json").read_text())


def request(capability: str, **context: Any) -> ProbeRequest:
    return ProbeRequest(
        capability,
        "https://cdn.nba.com/fixture.json",
        "local",
        {
            "season": "2026-27",
            "opening_date": "2026-10-20",
            "game_id": "0012600001",
            **context,
        },
    )


def check(name: str, capability: str, **context: Any) -> dict[str, Any]:
    return validate(json.dumps(fixture(name)).encode(), request(capability, **context), NOW)


def test_opening_night_uses_eastern_day_not_utc_date() -> None:
    result = check("schedule", "schedule")
    opening = result["opening_night"]
    assert len(opening) == 1
    assert opening[0]["start_utc"] == "2026-10-21T00:30:00+00:00"
    assert opening[0]["home_team_id"] == 1610612738
    assert opening[0]["competition"] == "regular"
    assert result["source_time_interpretation"].startswith("Uninterpreted")


def test_nonempty_scoreboard_is_not_future_schedule() -> None:
    result = check("scoreboard", "status")
    assert result["record_count"] == 1
    assert result["source_day"] == "2026-10-14"
    with pytest.raises(KeyError):
        check("scoreboard", "schedule")


def test_empty_scoreboard_requires_independent_no_game_evidence() -> None:
    body = json.dumps(fixture("no-games")).encode()
    with pytest.raises(ValueError, match="independently verified"):
        validate(body, request("status"), NOW)
    result = validate(
        body, request("status", expected_game_ids=[], schedule_day_verified=True), NOW
    )
    assert result["record_count"] == 0
    assert result["genuine_no_game_day"] is True
    with pytest.raises(ValueError):
        validate(body, request("status", expected_game_ids=[]), NOW)
    with pytest.raises(ValueError):
        validate(body, request("status", expected_game_ids=["0012600001"]), NOW)


def test_nba_source_day_crosses_utc_midnight() -> None:
    body = json.dumps(fixture("scoreboard")).encode()
    result = validate(body, request("status"), datetime(2026, 10, 15, 1, tzinfo=UTC))
    assert result["source_day"] == "2026-10-14"
    with pytest.raises(ValueError, match="differs from NBA Eastern day"):
        validate(body, request("status"), datetime(2026, 10, 15, 12, tzinfo=UTC))


def test_boxscore_preserves_fractional_minutes_and_preseason_label() -> None:
    result = check("boxscore", "final")
    assert result["players"][0]["seconds"] == "754.50"
    assert result["players"][0]["threes"] == 1
    assert result["records"][0]["competition"] == "preseason"
    assert "Preseason samples are rehearsal only" in result["limitations"]


def test_explicit_dnp_and_missing_participation_are_distinct() -> None:
    payload = fixture("boxscore")
    player = payload["game"]["homeTeam"]["players"][0]
    player["played"] = "0"
    result = validate(json.dumps(payload).encode(), request("final"), NOW)
    assert result["players"][0]["participation"] == "unknown"
    assert result["players"][0]["points"] is None
    player["notPlayingReason"] = "DNP - Coach's Decision"
    player["statistics"] = {
        "points": 0,
        "reboundsTotal": 0,
        "assists": 0,
        "threePointersMade": 0,
        "minutes": "PT00M00.00S",
    }
    result = validate(json.dumps(payload).encode(), request("final"), NOW)
    assert result["players"][0]["participation"] == "explicit_dnp"
    assert result["players"][0]["points"] == 0
    player["statistics"]["points"] = 1
    with pytest.raises(ValueError, match="DNP contains nonzero"):
        validate(json.dumps(payload).encode(), request("final"), NOW)


@pytest.mark.parametrize("value", [None, "12:01", "PT-01M", "PT01M60S", "PT", "nan"])
def test_invalid_precise_minutes(value: Any) -> None:
    with pytest.raises(ValueError):
        minutes(value, iso=True)


@pytest.mark.parametrize("value", [None, -1, float("nan"), float("inf"), True, "12"])
def test_invalid_history_minutes(value: Any) -> None:
    with pytest.raises(ValueError):
        minutes(value, iso=False)


def test_missing_player_is_not_invented_as_zero_outcome() -> None:
    result = check("boxscore", "final")
    assert {p["player_id"] for p in result["players"]} == {10, 20}
    assert 30 not in {p["player_id"] for p in result["players"]}


@pytest.mark.parametrize(
    "mutation",
    [
        "duplicate",
        "team_conflict",
        "bad_minutes",
        "missing_field",
        "wrong_id",
        "not_final",
        "negative_target",
        "bool_target",
    ],
)
def test_final_contract_rejects_broken_schema(mutation: str) -> None:
    payload = fixture("boxscore")
    game = payload["game"]
    player = game["homeTeam"]["players"][0]
    if mutation == "duplicate":
        game["homeTeam"]["players"].append(copy.deepcopy(player))
    elif mutation == "team_conflict":
        game["awayTeam"]["teamId"] = game["homeTeam"]["teamId"]
    elif mutation == "bad_minutes":
        player["statistics"]["minutes"] = "bad"
    elif mutation == "missing_field":
        del player["statistics"]["reboundsTotal"]
    elif mutation == "wrong_id":
        game["gameId"] = "0012609999"
    elif mutation == "not_final":
        game["gameStatus"] = 2
    elif mutation == "negative_target":
        player["statistics"]["points"] = -1
    else:
        player["statistics"]["points"] = True
    with pytest.raises((ValueError, KeyError)):
        validate(json.dumps(payload).encode(), request("final"), NOW)


@pytest.mark.parametrize(
    "mutation", ["wrong_season", "duplicate", "no_opening", "naive_time", "missing_status"]
)
def test_schedule_contract_rejects_incomplete_or_conflicting_data(mutation: str) -> None:
    payload = fixture("schedule")
    league = payload["leagueSchedule"]
    game = league["gameDates"][0]["games"][0]
    if mutation == "wrong_season":
        league["seasonYear"] = "2025-26"
    elif mutation == "duplicate":
        league["gameDates"][0]["games"].append(copy.deepcopy(game))
    elif mutation == "no_opening":
        game["gameDateTimeUTC"] = "2026-10-23T00:30:00Z"
    elif mutation == "naive_time":
        game["gameDateTimeUTC"] = "2026-10-21T00:30:00"
    else:
        del game["gameStatus"]
    with pytest.raises((ValueError, KeyError)):
        validate(json.dumps(payload).encode(), request("schedule"), NOW)


def test_unscheduled_slot_stays_unknown() -> None:
    payload = fixture("schedule")
    unknown = copy.deepcopy(payload["leagueSchedule"]["gameDates"][0]["games"][0])
    unknown["gameId"] = "0022600002"
    unknown["gameDateTimeUTC"] = None
    payload["leagueSchedule"]["gameDates"][0]["games"].append(unknown)
    result = validate(json.dumps(payload).encode(), request("schedule"), NOW)
    assert result["unknown_start_count"] == 1
    assert result["records"][1]["start_utc"] is None


@pytest.mark.parametrize(
    "gid,label",
    [
        ("0012600001", "preseason"),
        ("0022600001", "regular"),
        ("0042600001", "playoffs"),
        ("0062600001", "unknown"),
    ],
)
def test_competitions_are_not_inferred_from_stats_or_month(gid: str, label: str) -> None:
    assert game_identity(gid) == (gid, label, "2026-27")


def history_context(side: str) -> dict[str, str]:
    return {"season": "2025-26", "side": side, "date_from": "2026-04-10", "date_to": "2026-04-12"}


def test_history_is_bounded_and_preserves_reported_precision_and_nulls() -> None:
    result = check("history-player", "history", **history_context("P"))
    assert result["records"][0]["seconds"] == "750.0"
    assert result["records"][0]["player_id"] == 10
    payload = fixture("history-player")
    payload["resultSets"][0]["rowSet"][0][4] = None
    result = validate(json.dumps(payload).encode(), request("history", **history_context("P")), NOW)
    assert result["records"][0]["seconds"] is None


def test_current_season_preseason_cannot_enter_seed_history() -> None:
    payload = fixture("history-player")
    payload["resultSets"][0]["rowSet"][0][2] = "0012600001"
    with pytest.raises(ValueError, match="another season/competition"):
        validate(json.dumps(payload).encode(), request("history", **history_context("P")), NOW)


def test_roster_is_not_final_participant_list_or_player_directory() -> None:
    assert check("roster", "roster", team_id=1610612738)["record_count"] == 1
    with pytest.raises(KeyError):
        check("boxscore", "roster", team_id=1610612738)
    with pytest.raises(ValueError, match="team/league mismatch"):
        check("roster", "roster", team_id=1610612752)


def test_joins_need_independent_samples_and_allow_rookies_without_history() -> None:
    observed = []
    for name, capability, context in [
        ("history-player", "history", history_context("P")),
        ("history-team", "history", history_context("T")),
        ("roster", "roster", {"team_id": 1610612738}),
        ("boxscore", "final", {}),
    ]:
        observed.append(
            {
                "outcome": "verified_sample",
                "capability": capability,
                "summary": check(name, capability, **context),
            }
        )
    result = identity_joins(observed)
    assert result["history_player_team_game_matches"] == 1
    assert result["box_roster_matches"] == 1
    assert result["roster_players_with_seed_history"] == 1
    assert result["join_evidence"] == "observed_sample"
    assert identity_joins(observed[:-1])["join_evidence"] == "incomplete"


def test_pinned_nba_api_interfaces_generate_local_only_sample_requests() -> None:
    root = Path(__file__).resolve().parents[2]
    config = json.loads((root / "configs/sources/local.json").read_text())
    requests = local_requests(config)
    assert len(requests) == 4
    assert all(r.environment == "local" for r in requests)
    assert "Season=2025-26" in requests[0].url
    assert "DateFrom=04%2F10%2F2026" in requests[0].url


def test_local_cli_rejects_cloud_machine_before_any_network_request(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "hoop.domains.nba.sources.probe",
            "--environment",
            "local",
            "--config",
            "configs/sources/local.json",
            "--archive",
            str(tmp_path),
            "--confirm-local-machine",
        ],
        env={**os.environ, "GITHUB_ACTIONS": "true"},
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 2
    assert "actual local machine" in result.stderr
    assert list(tmp_path.iterdir()) == []
