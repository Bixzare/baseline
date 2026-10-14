"""Explicit capability contracts; fixtures alone do not prove source access."""

import json
import math
import re
from datetime import datetime
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

from hoop.domains.nba.sources.policy import ProbeRequest
from hoop.platform.provenance import parse_time, utc

EASTERN = ZoneInfo("America/New_York")


def integer(value: Any, field: str, *, positive: bool = False) -> int:
    if type(value) is not int or value < (1 if positive else 0):
        raise ValueError(f"{field} must be a {'positive' if positive else 'nonnegative'} integer")
    return value


def game_identity(value: Any) -> tuple[str, str, str]:
    if not isinstance(value, str) or not re.fullmatch(r"\d{10}", value):
        raise ValueError("gameId must be a ten-digit string")
    competition = {"001": "preseason", "002": "regular", "004": "playoffs", "005": "play-in"}.get(
        value[:3], "unknown"
    )
    start = 2000 + int(value[3:5])
    return value, competition, f"{start}-{str(start + 1)[2:]}"


def minutes(value: Any, *, iso: bool) -> str:
    if iso:
        if not isinstance(value, str):
            raise ValueError("minutes must be an ISO duration")
        match = re.fullmatch(r"PT(?:(\d+)M)?(?:(\d+(?:\.\d+)?)S)?", value)
        if not match or not any(match.groups()):
            raise ValueError("Invalid minutes duration")
        seconds = Decimal(match[1] or "0") * 60 + Decimal(match[2] or "0")
        if Decimal(match[2] or "0") >= 60:
            raise ValueError("Duration seconds must be below 60")
    else:
        if type(value) not in {int, float} or not math.isfinite(value) or value < 0:
            raise ValueError("MIN must be finite nonnegative numeric minutes; null remains unknown")
        seconds = Decimal(str(value)) * 60
    return str(seconds)


def unique(records: list[dict[str, Any]], fields: tuple[str, ...]) -> None:
    seen: set[tuple[Any, ...]] = set()
    for record in records:
        key = tuple(record[field] for field in fields)
        if key in seen:
            raise ValueError(f"Duplicate/conflicting identity: {key}")
        seen.add(key)


def game_record(game: dict[str, Any], *, schedule: bool = False) -> dict[str, Any]:
    game_id, competition, season = game_identity(game["gameId"])
    status = integer(game["gameStatus"], "gameStatus", positive=True)
    if status not in {1, 2, 3} or not isinstance(game["gameStatusText"], str):
        raise ValueError("Unknown game status semantics")
    home = integer(game["homeTeam"]["teamId"], "home teamId", positive=True)
    away = integer(game["awayTeam"]["teamId"], "away teamId", positive=True)
    if home == away:
        raise ValueError("Home and away identities conflict")
    timestamp = game.get("gameDateTimeUTC") if schedule else game.get("gameTimeUTC")
    unknown_time = timestamp in {None, ""}
    if not unknown_time and not isinstance(timestamp, str):
        raise ValueError("Game UTC time must be a timestamp string")
    start = None if unknown_time else utc(parse_time(str(timestamp)))
    return {
        "game_id": game_id,
        "competition": competition,
        "season": season,
        "home_team_id": home,
        "away_team_id": away,
        "status": status,
        "start_utc": start,
        "unscheduled": unknown_time,
    }


def schedule(payload: dict[str, Any], request: ProbeRequest) -> dict[str, Any]:
    league = payload["leagueSchedule"]
    if league["leagueId"] != "00" or league["seasonYear"] != request.context["season"]:
        raise ValueError("Schedule league/season mismatch")
    records = [
        game_record(game, schedule=True) for day in league["gameDates"] for game in day["games"]
    ]
    unique(records, ("game_id",))
    regular = [row for row in records if row["competition"] == "regular"]
    if not regular or any(row["season"] != request.context["season"] for row in regular):
        raise ValueError("No verified requested regular-season schedule")
    opening = [
        row
        for row in regular
        if row["start_utc"] is not None
        and parse_time(row["start_utc"]).astimezone(EASTERN).date().isoformat()
        == request.context["opening_date"]
    ]
    if not opening:
        raise ValueError("Opening-night games not demonstrated")
    return {
        "record_count": len(records),
        "records": records,
        "opening_night": opening,
        "regular_season_games": len(regular),
        "unknown_start_count": sum(row["unscheduled"] for row in records),
        "explicit_empty_days": [
            datetime.strptime(day["gameDate"].split()[0], "%m/%d/%Y").date().isoformat()
            for day in league["gameDates"]
            if day["games"] == []
        ],
        "limitations": [
            "Observed schedule version only; unscheduled slots stay unknown",
            "Count does not prove complete eventual season coverage",
        ],
    }


def scoreboard(payload: dict[str, Any], request: ProbeRequest, now: datetime) -> dict[str, Any]:
    board = payload["scoreboard"]
    if board["leagueId"] != "00":
        raise ValueError("Scoreboard is not NBA league 00")
    expected = now.astimezone(EASTERN).date().isoformat()
    if board["gameDate"] != expected:
        raise ValueError(f"Source day {board['gameDate']} differs from NBA Eastern day {expected}")
    if not isinstance(board["games"], list):
        raise ValueError("Scoreboard games must be a list")
    if not board["games"] and (
        request.context.get("expected_game_ids") != []
        or request.context.get("schedule_day_verified") is not True
    ):
        raise ValueError(
            "Empty scoreboard lacks independently verified schedule evidence for no games"
        )
    records = [game_record(game) for game in board["games"]]
    unique(records, ("game_id",))
    if any(row["start_utc"] is None for row in records):
        raise ValueError("Scoreboard game start is unknown")
    if any(row["season"] != request.context["season"] for row in records):
        raise ValueError("Scoreboard season mismatch")
    return {
        "record_count": len(records),
        "records": records,
        "source_day": board["gameDate"],
        "genuine_no_game_day": not records,
        "limitations": ["Today only; not future schedule or current roster evidence"],
    }


def boxscore(payload: dict[str, Any], request: ProbeRequest, now: datetime) -> dict[str, Any]:
    game = payload["game"]
    record = game_record(game)
    if record["game_id"] != request.context["game_id"] or record["status"] != 3:
        raise ValueError("Requested observed game identity or final status mismatch")
    if record["season"] != request.context["season"] or record["start_utc"] is None:
        raise ValueError("Box score season/start mismatch")
    if parse_time(record["start_utc"]) > now:
        raise ValueError("A future game cannot supply final results")
    expected = request.context.get("expected_team_ids")
    if expected is not None and sorted(expected) != sorted(
        [record["home_team_id"], record["away_team_id"]]
    ):
        raise ValueError("Box score teams conflict with independently observed game")
    players: list[dict[str, Any]] = []
    totals = []
    for side in ["homeTeam", "awayTeam"]:
        team = game[side]
        team_id = integer(team["teamId"], "teamId", positive=True)
        stats = team["statistics"]
        totals.append(
            {
                "team_id": team_id,
                "points": integer(stats["points"], "team points"),
                "seconds": minutes(stats["minutes"], iso=True),
            }
        )
        if integer(team["score"], "score") != stats["points"]:
            raise ValueError("Team score and points totals conflict")
        if not isinstance(team["players"], list) or not team["players"]:
            raise ValueError("Final player records are missing")
        for player in team["players"]:
            identity = integer(player["personId"], "personId", positive=True)
            played = player.get("played")
            participation = "played" if played == "1" else "unknown"
            if played == "0" and player.get("notPlayingReason"):
                participation = "explicit_dnp"
            if played not in {None, "0", "1"}:
                raise ValueError("Unknown played field semantics")
            row = {
                "player_id": identity,
                "team_id": team_id,
                "game_id": record["game_id"],
                "participation": participation,
                "seconds": None,
                "points": None,
                "rebounds": None,
                "assists": None,
                "threes": None,
            }
            if participation != "unknown":
                values = player["statistics"]
                row.update(seconds=minutes(values["minutes"], iso=True))
                for source, target in [
                    ("points", "points"),
                    ("reboundsTotal", "rebounds"),
                    ("assists", "assists"),
                    ("threePointersMade", "threes"),
                ]:
                    row[target] = integer(values[source], source)
                if participation == "explicit_dnp" and any(
                    row[key] != 0 for key in ["points", "rebounds", "assists", "threes"]
                ):
                    raise ValueError("Explicit DNP contains nonzero counting stats")
                if participation == "explicit_dnp" and Decimal(row["seconds"]) != 0:
                    raise ValueError("Explicit DNP contains playing minutes")
            players.append(row)
    unique(players, ("game_id", "player_id"))
    return {
        "record_count": len(players),
        "records": [record],
        "players": players,
        "team_totals": totals,
        "unknown_participation_count": sum(p["participation"] == "unknown" for p in players),
        "limitations": [
            "Absent players remain unknown; this is not a prior forecast roster",
            "Preseason samples are rehearsal only"
            if record["competition"] == "preseason"
            else "Observed final only; corrections and DNP coverage are not guaranteed",
        ],
    }


def stats_rows(payload: dict[str, Any], name: str) -> list[dict[str, Any]]:
    datasets = payload["resultSets"]
    if not isinstance(datasets, list):
        raise ValueError("resultSets must be a list")
    matches = [dataset for dataset in datasets if dataset["name"] == name]
    if len(matches) != 1:
        raise ValueError(f"Expected exactly one {name} result set")
    dataset = matches[0]
    headers = dataset["headers"]
    if len(headers) != len(set(headers)):
        raise ValueError("Duplicate result headers")
    rows = []
    for values in dataset["rowSet"]:
        if len(values) != len(headers):
            raise ValueError("Row length differs from headers")
        rows.append(dict(zip(headers, values, strict=True)))
    if not rows:
        raise ValueError("Empty history/roster is not verified coverage")
    return rows


def history(payload: dict[str, Any], request: ProbeRequest) -> dict[str, Any]:
    rows = stats_rows(payload, "LeagueGameLog")
    records = []
    side = request.context["side"]
    for row in rows:
        game_id, competition, season = game_identity(row["GAME_ID"])
        if competition != "regular" or season != request.context["season"]:
            raise ValueError("Historical seed contains another season/competition")
        if str(row["SEASON_ID"]) != "2" + request.context["season"][:4]:
            raise ValueError("Historical SEASON_ID mismatch")
        game_date = datetime.fromisoformat(row["GAME_DATE"]).date().isoformat()
        if not request.context["date_from"] <= game_date <= request.context["date_to"]:
            raise ValueError("History date outside requested sample")
        record: dict[str, Any] = {
            "game_id": game_id,
            "competition": competition,
            "season": season,
            "game_date": game_date,
            "team_id": integer(row["TEAM_ID"], "TEAM_ID", positive=True),
            "seconds": None if row["MIN"] is None else minutes(row["MIN"], iso=False),
            "minute_precision": "unknown" if row["MIN"] is None else type(row["MIN"]).__name__,
        }
        if side == "P":
            record["player_id"] = integer(row["PLAYER_ID"], "PLAYER_ID", positive=True)
        for source, target in [
            ("PTS", "points"),
            ("REB", "rebounds"),
            ("AST", "assists"),
            ("FG3M", "threes"),
        ]:
            record[target] = None if row[source] is None else integer(row[source], source)
        records.append(record)
    unique(records, ("game_id", "player_id" if side == "P" else "team_id"))
    return {
        "record_count": len(records),
        "records": records,
        "date_range": [min(r["game_date"] for r in records), max(r["game_date"] for r in records)],
        "limitations": [
            "Bounded date sample; not a season backfill",
            "Null targets stay unknown; integer MIN cannot establish subminute precision",
            "Collection now does not prove historical availability or correction history",
        ],
    }


def roster(payload: dict[str, Any], request: ProbeRequest) -> dict[str, Any]:
    rows = stats_rows(payload, "CommonTeamRoster")
    records = []
    for row in rows:
        if str(row["SEASON"]) not in {request.context["season"], request.context["season"][:4]}:
            raise ValueError("Roster season mismatch")
        if str(row["LeagueID"]) != "00" or row["TeamID"] != request.context["team_id"]:
            raise ValueError("Roster team/league mismatch")
        if not isinstance(row["PLAYER"], str) or not row["PLAYER"].strip():
            raise ValueError("Roster player name is missing")
        records.append(
            {
                "player_id": integer(row["PLAYER_ID"], "PLAYER_ID", positive=True),
                "team_id": integer(row["TeamID"], "TeamID", positive=True),
            }
        )
    unique(records, ("player_id",))
    return {
        "record_count": len(records),
        "records": records,
        "limitations": [
            "Observed team sample, not complete league or trade-history evidence",
            "New players may have no prior seed history",
        ],
    }


def validate(body: bytes, request: ProbeRequest, now: datetime) -> dict[str, Any]:
    payload = json.loads(body)
    if not isinstance(payload, dict):
        raise ValueError("JSON object required")
    if request.capability == "schedule":
        summary = schedule(payload, request)
    elif request.capability == "status":
        summary = scoreboard(payload, request, now)
    elif request.capability == "final":
        summary = boxscore(payload, request, now)
    elif request.capability == "history":
        summary = history(payload, request)
    elif request.capability == "roster":
        summary = roster(payload, request)
    else:
        raise ValueError("No validated parser for this capability")
    meta = payload.get("meta", {})
    if not isinstance(meta, dict):
        raise ValueError("meta must be an object")
    summary["supplied_source_time"] = meta.get("time")
    summary["source_time_interpretation"] = "Uninterpreted; no inferred publication timestamp"
    return summary


def identity_joins(observations: list[dict[str, Any]]) -> dict[str, Any]:
    """Report joins only when both independent samples exist, never invent coverage."""
    accepted = [row for row in observations if row["outcome"] == "verified_sample"]
    players = [
        p
        for row in accepted
        if row["capability"] == "history"
        for p in row["summary"]["records"]
        if "player_id" in p
    ]
    team_logs = {
        (p["game_id"], p["team_id"])
        for row in accepted
        if row["capability"] == "history"
        for p in row["summary"]["records"]
        if "player_id" not in p
    }
    rosters = {
        (p["player_id"], p["team_id"])
        for row in accepted
        if row["capability"] == "roster"
        for p in row["summary"]["records"]
    }
    boxes = [
        p for row in accepted if row["capability"] == "final" for p in row["summary"]["players"]
    ]
    history_ids = {p["player_id"] for p in players}
    return {
        "history_player_team_game_matches": sum(
            (p["game_id"], p["team_id"]) in team_logs for p in players
        ),
        "box_roster_matches": sum((p["player_id"], p["team_id"]) in rosters for p in boxes),
        "roster_players_with_seed_history": sum(p in history_ids for p, _ in rosters),
        "join_evidence": "observed_sample"
        if players and team_logs and rosters and boxes
        else "incomplete",
        "limitations": ["No membership is inferred for missing or unmatched players"],
    }
