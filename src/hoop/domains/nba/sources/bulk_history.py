"""Assess a pinned historical CSV snapshot offline; never collect or publish forecasts."""

import argparse
import csv
import hashlib
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from hoop.platform.provenance import digest, parse_time

FILES = {
    "Games.csv": {"gameId", "hometeamId", "awayteamId", "homeScore", "awayScore"},
    "TeamStatistics.csv": {"gameId", "teamId", "opponentTeamId", "teamScore"},
    "PlayerStatistics.csv": {
        "gameId",
        "personId",
        "playerteamId",
        "numMinutes",
        "points",
        "reboundsTotal",
        "assists",
        "threePointersMade",
        "comment",
    },
    "Players.csv": {"personId"},
}
TARGETS = ("points", "reboundsTotal", "assists", "threePointersMade")


def file_hash(path: Path) -> str:
    checksum = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            checksum.update(chunk)
    return checksum.hexdigest()


def identity(value: str, *, game: bool = False) -> str:
    if not re.fullmatch(r"[0-9]+", value) or int(value) <= 0:
        raise ValueError("invalid_identity")
    if game:
        if len(value) > 10:
            raise ValueError("invalid_game_identity")
        return value.zfill(10)
    return str(int(value))


def numeric(value: str, *, integer: bool = False) -> float:
    result = float(value)
    if not math.isfinite(result) or result < 0 or (integer and not result.is_integer()):
        raise ValueError("invalid_target")
    return result


def assess_snapshot(
    root: Path,
    manifest: dict[str, Any],
    season: str,
    inventory: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate identity/target joins and report every excluded row without repairing it."""
    if (
        not re.fullmatch(r"20\d{2}-\d{2}", season)
        or int(season[-2:]) != (int(season[:4]) + 1) % 100
    ):
        raise ValueError("Invalid NBA season")
    if manifest.get("source_id") != "eoinamoore/historical-nba-data-and-player-box-scores":
        raise ValueError("Unexpected source identity")
    if type(manifest.get("dataset_version")) is not int or manifest["dataset_version"] <= 0:
        raise ValueError("A positive pinned dataset version is required")
    observed_at = parse_time(manifest["collected_at"])
    if manifest.get("evidence_kind") not in {"observed_download", "synthetic_fixture"}:
        raise ValueError("Evidence must be labeled")
    prefix = "002" + season[2:4]
    issues: list[dict[str, Any]] = []
    inputs = []
    counts: dict[str, int] = {}
    root = root.resolve()

    def problem(name: str, line: int, row: dict[str, Any], reason: str) -> None:
        issues.append(
            {
                "file": name,
                "line": line,
                "game_id": row.get("gameId"),
                "subject_id": row.get("personId", row.get("teamId")),
                "reason": reason,
                "resolution": "unresolved",
                "action": "quarantine_or_obtain_source_evidence",
            }
        )

    def read(name: str) -> list[tuple[int, dict[str, str]]]:
        path = (root / name).resolve()
        if not path.is_relative_to(root):
            raise ValueError("Input path escapes snapshot")
        checksum = file_hash(path)
        if manifest["files"].get(name) != checksum:
            raise ValueError(f"Checksum mismatch: {name}")
        inputs.append({"file": name, "sha256": checksum})
        selected = []
        with path.open(encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            headers = reader.fieldnames or []
            if len(headers) != len(set(headers)) or not FILES[name].issubset(headers):
                raise ValueError(f"Invalid columns: {name}")
            for line, row in enumerate(reader, start=2):
                if None in row or any(value is None for value in row.values()):
                    problem(name, line, row, "malformed_csv_row")
                    continue
                if name != "Players.csv":
                    try:
                        row["gameId"] = identity(row["gameId"], game=True)
                    except ValueError:
                        problem(name, line, row, "invalid_game_identity")
                        continue
                    if not row["gameId"].startswith(prefix):
                        continue
                selected.append((line, row))
        counts[name] = len(selected)
        if file_hash(path) != checksum:
            raise ValueError(f"Snapshot changed during assessment: {name}")
        return selected

    player_ids = set()
    for line, row in read("Players.csv"):
        try:
            player_ids.add(identity(row["personId"]))
        except ValueError:
            problem("Players.csv", line, row, "invalid_player_identity")
    games: dict[str, tuple[str, str, float, float]] = {}
    for line, row in read("Games.csv"):
        try:
            home, away = identity(row["hometeamId"]), identity(row["awayteamId"])
            if home == away or row["gameId"] in games:
                raise ValueError("duplicate_or_conflicting_game")
            games[row["gameId"]] = (
                home,
                away,
                numeric(row["homeScore"], integer=True),
                numeric(row["awayScore"], integer=True),
            )
        except ValueError as error:
            problem("Games.csv", line, row, str(error))
    teams: dict[tuple[str, str], float] = {}
    for line, row in read("TeamStatistics.csv"):
        try:
            team, opponent = identity(row["teamId"]), identity(row["opponentTeamId"])
            key = (row["gameId"], team)
            if key in teams:
                raise ValueError("duplicate_team_key")
            if row["gameId"] not in games:
                raise ValueError("missing_game_join")
            home, away, home_score, away_score = games[row["gameId"]]
            if (team, opponent) not in {(home, away), (away, home)}:
                raise ValueError("conflicting_team_identity")
            score = numeric(row["teamScore"], integer=True)
            if score != (home_score if team == home else away_score):
                raise ValueError("team_game_score_conflict")
            teams[key] = score
        except ValueError as error:
            problem("TeamStatistics.csv", line, row, str(error))
    for gid, (home, away, _, _) in games.items():
        if any((gid, team) not in teams for team in [home, away]):
            problem("Games.csv", 0, {"gameId": gid}, "missing_team_side")
    seen = set()
    points: dict[tuple[str, str], float] = defaultdict(float)
    participation: Counter[str] = Counter()
    for line, row in read("PlayerStatistics.csv"):
        try:
            person = identity(row["personId"])
            if person not in player_ids:
                raise ValueError("missing_player_identity_join")
            player_key = (row["gameId"], person)
            if player_key in seen:
                raise ValueError("duplicate_player_key")
            seen.add(player_key)
            values = {target: numeric(row[target], integer=True) for target in TARGETS}
            comment = row["comment"].strip()
            nonparticipant = bool(re.match(r"^(DNP|DND|NWT)(?:\b|_)", comment))
            if nonparticipant and (
                any(values.values())
                or (row["numMinutes"].strip() and numeric(row["numMinutes"]) > 0)
            ):
                raise ValueError("conflicting_nonparticipation")
            if not row["numMinutes"].strip():
                # This is outcome evidence, never a pregame cohort or feature.
                label = "nonparticipation_comment" if nonparticipant else "unknown"
                participation[label] += 1
                if label == "unknown":
                    problem("PlayerStatistics.csv", line, row, "unknown_minutes")
            else:
                minutes = numeric(row["numMinutes"])
                label = (
                    "nonparticipation_comment"
                    if nonparticipant
                    else "positive_minutes"
                    if minutes > 0
                    else "zero_minutes_unknown"
                )
                participation[label] += 1
                if label == "zero_minutes_unknown":
                    problem("PlayerStatistics.csv", line, row, "zero_minutes_not_dnp_proof")
            team = identity(row["playerteamId"])
            key = (row["gameId"], team)
            if key not in teams:
                raise ValueError("missing_player_team_join")
            points[key] += values["points"]
        except ValueError as error:
            problem("PlayerStatistics.csv", line, row, str(error))
    for key, score in teams.items():
        if key not in points or points[key] != score:
            problem(
                "TeamStatistics.csv",
                0,
                {"gameId": key[0], "teamId": key[1]},
                "player_team_points_conflict",
            )

    coverage: dict[str, Any] = {"status": "unknown", "reason": "expected_game_inventory_required"}
    if inventory is not None:
        if not inventory.get("source_id") or inventory["source_id"] == manifest["source_id"]:
            raise ValueError("Expected inventory must declare a separate collection source")
        parse_time(inventory["collected_at"])
        expected_list = [identity(gid, game=True) for gid in inventory["game_ids"]]
        if (
            not expected_list
            or len(set(expected_list)) != len(expected_list)
            or any(not gid.startswith(prefix) for gid in expected_list)
        ):
            raise ValueError("Invalid expected regular-season game inventory")
        expected = set(expected_list)
        coverage = {
            "status": "matched_declared_inventory" if expected == set(games) else "mismatch",
            "inventory_sha256": digest(json.dumps(inventory, sort_keys=True).encode()),
            "source_id": inventory["source_id"],
            "missing_game_ids": sorted(expected - games.keys()),
            "unexpected_game_ids": sorted(games.keys() - expected),
            "limitation": (
                "Separate collection is declared provenance, not certified source truth"
            ),
        }
    return {
        "schema_version": 1,
        "parser_version": "eoin-assessment-v1",
        "season": season,
        "source_id": manifest["source_id"],
        "dataset_version": manifest["dataset_version"],
        "evidence_kind": manifest["evidence_kind"],
        "collected_at": observed_at.isoformat(),
        "manifest_sha256": digest(json.dumps(manifest, sort_keys=True).encode()),
        "inputs": inputs,
        "selected_rows": counts,
        "valid_game_count": len(games),
        "valid_team_rows": len(teams),
        "participation": dict(participation),
        "coverage": coverage,
        "repair_items": issues,
        "historical_availability_verified": False,
        "source_accepted": False,
        "status": "needs_review"
        if issues or coverage["status"] != "matched_declared_inventory"
        else "checks_passed_pending_owner_acceptance",
        "limitations": [
            "No forecast population or historical pregame timing inferred",
            "Timezone and competition mappings require source review",
            "No normalization, repair, or production writes performed",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--season", default="2025-26")
    parser.add_argument("--expected-inventory", type=Path)
    parser.add_argument("--report", required=True, type=Path)
    args = parser.parse_args()
    report = assess_snapshot(
        args.root,
        json.loads(args.manifest.read_text(encoding="utf-8")),
        args.season,
        json.loads(args.expected_inventory.read_text(encoding="utf-8"))
        if args.expected_inventory
        else None,
    )
    with args.report.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2, allow_nan=False)
    print(
        json.dumps(
            {
                "report": str(args.report),
                "status": report["status"],
                "repair_items": len(report["repair_items"]),
            }
        )
    )
    return 0 if report["status"] == "checks_passed_pending_owner_acceptance" else 1


if __name__ == "__main__":
    raise SystemExit(main())
