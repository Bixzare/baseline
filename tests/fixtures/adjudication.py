"""Invented zero-minute and invalid extra-team rows, with retained proof bytes."""

import csv
import json
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from hoop.domains.nba.sources.seed import build_seed, row_hash
from hoop.platform.local_artifacts import checksum

NOW = datetime(2026, 10, 27, 12, tzinfo=UTC)


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    fields = list(dict.fromkeys(k for row in rows for k in row))
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as stream:
        return list(csv.DictReader(stream))


def fixture(tmp_path: Path) -> dict[str, Any]:
    source = tmp_path / "source"
    shutil.copytree(Path(__file__).parent / "nba/seed", source)
    players = read_csv(source / "PlayerStatistics.csv")
    players.append(
        {
            **players[0],
            "personId": "203",
            "numMinutes": "0",
            "points": "0",
            "reboundsTotal": "0",
            "assists": "0",
            "threePointersMade": "0",
        }
    )
    write_csv(source / "PlayerStatistics.csv", players)
    names = read_csv(source / "Players.csv")
    write_csv(source / "Players.csv", [*names, {**names[0], "personId": "203"}])
    teams = read_csv(source / "TeamStatistics.csv")
    teams = [
        {**r, "opponentScore": "9" if r["teamId"] == "101" else "10", "numMinutes": ""}
        for r in teams
    ]
    teams.append(
        {
            **teams[0],
            "teamId": "0",
            "opponentTeamId": "0",
            "teamScore": "0",
            "opponentScore": "0",
            "gameType": "",
        }
    )
    write_csv(source / "TeamStatistics.csv", teams)
    manifest = json.loads((source / "manifest.json").read_text())
    manifest["files"] = {name: checksum(source / name) for name in manifest["files"]}
    inventory = json.loads((source / "inventory.json").read_text())
    archive = tmp_path / "archive"
    report = build_seed(
        source, manifest, archive, inventory=inventory, now=datetime(2026, 10, 25, 12, tzinfo=UTC)
    )
    proof = tmp_path / "proof"
    proof.mkdir()
    log = {
        "resource": "playergamelog",
        "parameters": {
            "PlayerID": 203,
            "Season": "2025-26",
            "SeasonType": "Regular Season",
            "LeagueID": "00",
            "DateFrom": "04/10/2026",
            "DateTo": "04/10/2026",
        },
        "resultSets": [
            {
                "name": "PlayerGameLog",
                "headers": [
                    "SEASON_ID",
                    "Player_ID",
                    "Game_ID",
                    "GAME_DATE",
                    "MIN",
                    "PTS",
                    "REB",
                    "AST",
                    "FG3M",
                ],
                "rowSet": [["22025", 203, "0022500001", "APR 10, 2026", 0, 0, 0, 0, 0]],
            }
        ],
    }
    summary = {
        "boxScoreSummary": {
            "gameId": "0022500001",
            "gameStatus": 3,
            "homeTeam": {"teamId": 101, "score": 10, "inactives": []},
            "awayTeam": {"teamId": 102, "score": 9, "inactives": []},
        }
    }
    patches = []
    for name, operation, body, endpoint in [
        ("PlayerStatistics.csv", "confirm_appearance", log, "PlayerGameLog"),
        ("TeamStatistics.csv", "exclude_invalid_extra_team", summary, "BoxScoreSummaryV3"),
    ]:
        evidence = proof / (endpoint + ".json")
        evidence.write_text(json.dumps(body))
        patch = {
            "operation": operation,
            "source_id": "nba_api." + endpoint + ":1.11.4",
            "target_file": name,
            "source_row": 4,
            "parent_raw_sha256": manifest["files"][name],
            "base_row_sha256": row_hash(read_csv(source / name)[2]),
            "collected_at": "2026-10-26T10:00:00Z",
            "evidence_file": evidence.name,
            "evidence_sha256": checksum(evidence),
            "reason": "explicit synthetic proof",
            "changes": {},
        }
        path = proof / (operation + ".json")
        path.write_text(json.dumps(patch))
        patches.append(path)
    return {
        "source": source,
        "archive": archive,
        "manifest": manifest,
        "inventory": inventory,
        "report": report,
        "patches": tuple(patches),
        "proof": proof,
    }
