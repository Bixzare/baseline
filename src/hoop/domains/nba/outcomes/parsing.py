"""Partial finals, explicit nonparticipation and versioned cohort reconciliation."""

import json
from datetime import datetime
from typing import Any

from hoop.domains.nba.sources.policy import ProbeRequest
from hoop.domains.nba.sources.validate import game_record, integer, minutes, unique
from hoop.platform.evidence import EvidenceError
from hoop.platform.outcomes import validate_outcomes
from hoop.platform.provenance import parse_time

PARSER = "nba-outcomes-v1"
UNITS = {
    "minutes": "minutes",
    "points": "points",
    "rebounds": "rebounds",
    "assists": "assists",
    "threes_made": "threes made",
}


def normalize_final(
    payload: dict[str, Any], context: dict[str, Any], now: datetime
) -> dict[str, Any]:
    if context.get("dnp_semantics", "unknown_until_accepted") not in {
        "unknown_until_accepted",
        "played0_with_reason",
    }:
        raise ValueError("Unsupported DNP semantics")
    game = payload["game"]
    record = game_record(game)
    if (
        record["game_id"] != context["game_id"]
        or record["season"] != context["season"]
        or record["status"] != 3
        or record["start_utc"] is None
        or parse_time(record["start_utc"]) > now
        or sorted([str(record["home_team_id"]), str(record["away_team_id"])])
        != sorted(map(str, context["expected_team_ids"]))
    ):
        raise ValueError("Final identity, teams, season or timing mismatch")
    players: list[dict[str, Any]] = []
    teams: list[dict[str, Any]] = []
    for side in ["homeTeam", "awayTeam"]:
        team = game[side]
        team_id = str(integer(team["teamId"], "team_id", positive=True))
        score = integer(team["score"], "score")
        if score != integer(team["statistics"]["points"], "team_points"):
            raise ValueError("Score and team total mismatch")
        if not isinstance(team.get("players"), list):
            raise ValueError("Missing player payload")
        teams.append({"team_id": team_id, "points": score})
        for p in team["players"]:
            player_id = str(integer(p["personId"], "player_id", positive=True))
            played = p.get("played")
            if played not in {None, "0", "1"}:
                raise ValueError("Unsupported participation flag")
            explicit = played == "0" and bool(p.get("notPlayingReason"))
            confirmed = explicit and context.get("dnp_semantics") == "played0_with_reason"
            participation = (
                "played" if played == "1" else "did_not_play" if confirmed else "unknown"
            )
            stats = p.get("statistics", {})
            seconds = (
                minutes(stats["minutes"], iso=True) if stats.get("minutes") is not None else None
            )
            counts = {}
            for field, target in [
                ("points", "points"),
                ("reboundsTotal", "rebounds"),
                ("assists", "assists"),
                ("threePointersMade", "threes_made"),
            ]:
                counts[target] = (
                    integer(stats[field], field) if stats.get(field) is not None else None
                )
            if explicit and (
                any(x not in {None, 0} for x in counts.values())
                or (seconds is not None and float(seconds) != 0)
            ):
                raise ValueError("Explicit nonparticipant has nonzero production")
            if confirmed:
                seconds = "0"
                counts = {key: 0 for key in counts}
            elif participation == "unknown":
                seconds = None
                counts = {key: None for key in counts}
            players.append(
                {
                    "player_id": player_id,
                    "team_id": team_id,
                    "participation": participation,
                    "minutes_seconds": seconds,
                    **counts,
                    "participation_evidence": "played0_with_reason"
                    if confirmed
                    else "played1"
                    if played == "1"
                    else "unknown",
                }
            )
        team_players = [p for p in players if p["team_id"] == team_id]
        if team_players and all(p["points"] is not None for p in team_players):
            if sum(p["points"] for p in team_players) != score:
                raise ValueError("Player points contradict team score")
    unique(players, ("player_id",))
    if teams[0]["points"] == teams[1]["points"]:
        raise ValueError("A completed NBA game cannot be tied")
    return {
        "schema_version": 1,
        "game": record,
        "players": sorted(players, key=lambda p: p["player_id"]),
        "teams": teams,
        "minute_precision": "reported_iso_seconds",
    }


def outcome_entries(
    normalized: dict[str, Any], cohort: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    by_player = {row["player_id"]: row for row in normalized["players"]}
    entries = []
    for member in cohort:
        player = str(member["player_id"])
        actual = by_player.get(player)
        if actual and actual["team_id"] != str(member["team_id"]):
            raise EvidenceError("Final player team conflicts with saved cohort")
        for target, unit in UNITS.items():
            value = None
            if actual:
                value = (
                    float(actual["minutes_seconds"]) / 60
                    if target == "minutes" and actual["minutes_seconds"] is not None
                    else actual.get(target)
                    if target != "minutes"
                    else None
                )
            entries.append(
                {
                    "subject_type": "player",
                    "subject_id": player,
                    "target": target,
                    "unit": unit,
                    "value": value,
                    "reason_code": None if value is not None else "outcome_unresolved",
                    "participation": actual["participation"] if actual else "unknown",
                    "participation_evidence": actual["participation_evidence"]
                    if actual
                    else "absent_row",
                }
            )
    home, away = normalized["teams"]
    total = home["points"] + away["points"]
    for team, opponent in [(home, away), (away, home)]:
        for target, value, unit in [
            ("points", team["points"], "points"),
            ("margin", team["points"] - opponent["points"], "points"),
            ("total", total, "points"),
            ("win", int(team["points"] > opponent["points"]), "indicator"),
        ]:
            entries.append(
                {
                    "subject_type": "team",
                    "subject_id": team["team_id"],
                    "target": target,
                    "unit": unit,
                    "value": value,
                    "reason_code": None,
                }
            )
    validate_outcomes(entries)
    return entries


def final_validator(body: bytes, request: ProbeRequest, now: datetime) -> dict[str, Any]:
    def pairs(values: list[tuple[str, Any]]) -> dict[str, Any]:
        result = {}
        for key, value in values:
            if key in result:
                raise ValueError("Duplicate JSON key")
            result[key] = value
        return result

    normalized = normalize_final(json.loads(body, object_pairs_hook=pairs), request.context, now)
    return {"record_count": len(normalized["players"]), "normalized": normalized}
