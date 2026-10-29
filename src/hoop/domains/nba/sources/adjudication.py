"""Narrow source-backed historical adjudication under owner-locked ADR 0018."""

import json
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from hoop.domains.nba.sources.bulk_history import identity

OPERATIONS = {
    "field_update",
    "confirm_appearance",
    "exclude_invalid_extra_team",
    "retain_unresolved",
}


def number(value: Any) -> Decimal:
    try:
        result = Decimal(str(value))
    except InvalidOperation:
        raise ValueError("Invalid numeric source evidence") from None
    if not result.is_finite() or result < 0:
        raise ValueError("Invalid numeric source evidence")
    return result


def verify_operation(
    patch: dict[str, Any],
    evidence: Path,
    row: dict[str, str],
    games: dict[str, dict[str, Any]],
    season: str,
) -> str:
    operation = patch.get("operation", "field_update")
    if not isinstance(operation, str) or operation not in OPERATIONS:
        raise ValueError("Unsupported repair operation")
    if operation == "field_update":
        return operation
    if patch["changes"] != {}:
        raise ValueError("Typed adjudication cannot also edit source fields")
    gid = identity(row["gameId"], game=True)
    game = games.get(gid)
    if game is None or game["season"] != season:
        raise ValueError("Adjudication requires a known seed game")
    if evidence.stat().st_size > 8 * 1024 * 1024:
        raise ValueError("Typed source evidence exceeds diagnostic bound")
    payload = json.loads(evidence.read_bytes())
    if not isinstance(payload, dict):
        raise ValueError("Typed source evidence must be a JSON object")
    if operation == "confirm_appearance":
        if (
            patch["target_file"] != "PlayerStatistics.csv"
            or not patch["source_id"].startswith("nba_api.PlayerGameLog:")
            or payload.get("resource") != "playergamelog"
            or row["comment"].strip()
            or number(row["numMinutes"]) != 0
        ):
            raise ValueError("Positive appearance requires compatible raw participation")
        pid = identity(row["personId"])
        if identity(row["playerteamId"]) not in {game["home"], game["away"]}:
            raise ValueError("Appearance team does not belong to game")
        params = payload["parameters"]
        when = datetime.fromisoformat(row.get("gameDateTimeEst") or row["gameDate"]).date()
        if (
            identity(str(params["PlayerID"])) != pid
            or params["Season"] != season
            or params["SeasonType"] != "Regular Season"
            or params["LeagueID"] != "00"
            or datetime.strptime(params["DateFrom"], "%m/%d/%Y").date() != when
            or datetime.strptime(params["DateTo"], "%m/%d/%Y").date() != when
        ):
            raise ValueError("Appearance request does not match player, season and date")
        tables = [t for t in payload["resultSets"] if t["name"] == "PlayerGameLog"]
        if len(tables) != 1 or len(tables[0]["rowSet"]) != 1:
            raise ValueError("One positive appearance entry required; absence is not DNP")
        entry = dict(zip(tables[0]["headers"], tables[0]["rowSet"][0], strict=True))
        month, day, year = entry["GAME_DATE"].replace(",", "").upper().split()
        log_date = date(
            int(year),
            "JAN FEB MAR APR MAY JUN JUL AUG SEP OCT NOV DEC".split().index(month) + 1,
            int(day),
        )
        if (
            identity(str(entry["Player_ID"])) != pid
            or identity(str(entry["Game_ID"]), game=True) != gid
            or str(entry["SEASON_ID"]) != "2" + season[:4]
            or log_date != when
            or number(entry["MIN"]) != 0
        ):
            raise ValueError("Positive appearance row conflicts with source identity or minutes")
        for source_key, target in [
            ("PTS", "points"),
            ("REB", "reboundsTotal"),
            ("AST", "assists"),
            ("FG3M", "threePointersMade"),
        ]:
            if number(entry[source_key]) != number(row[target]) or number(row[target]) != 0:
                raise ValueError("Appearance targets conflict with reported source row")
    else:
        if not patch["source_id"].startswith("nba_api.BoxScoreSummaryV3:"):
            raise ValueError("Summary evidence required for this adjudication")
        if operation == "exclude_invalid_extra_team":
            if (
                patch["target_file"] != "TeamStatistics.csv"
                or row["teamId"] != "0"
                or row["opponentTeamId"] != "0"
                or number(row["teamScore"]) != 0
                or number(row["opponentScore"]) != 0
                or row["numMinutes"].strip()
                or row["gameType"].strip()
            ):
                raise ValueError("Exclusion requires the reviewed invalid extra-team shape")
        elif patch["target_file"] != "PlayerStatistics.csv":
            raise ValueError("Retained uncertainty requires a player row")
        summary = payload["boxScoreSummary"]
        if identity(str(summary["gameId"]), game=True) != gid or summary["gameStatus"] != 3:
            raise ValueError("Exclusion requires matching final source game")
        for name, side, score in [
            ("homeTeam", "home", "home_points"),
            ("awayTeam", "away", "away_points"),
        ]:
            if identity(str(summary[name]["teamId"])) != game[side] or number(
                summary[name]["score"]
            ) != number(game[score]):
                raise ValueError("Exclusion conflicts with valid team sides or scores")
    if operation == "retain_unresolved":
        pid = identity(row["personId"])
        if any(
            identity(str(p["personId"])) == pid
            for team in [summary["homeTeam"], summary["awayTeam"]]
            for p in team["inactives"]
        ):
            raise ValueError("Explicit inactive evidence must not be relabeled unresolved")
    return operation
