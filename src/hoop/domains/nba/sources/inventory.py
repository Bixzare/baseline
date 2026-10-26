"""Explicit bounded local NBA inventory capture with retained raw evidence."""

import argparse
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from hoop.domains.nba.sources.bulk_history import identity
from hoop.platform.provenance import Archive, digest, utc


def parse_inventory(body: bytes, season: str, collected_at: str) -> dict[str, Any]:
    payload = json.loads(body)
    table = next(item for item in payload["resultSets"] if item["name"] == "LeagueGameLog")
    rows = [dict(zip(table["headers"], row, strict=True)) for row in table["rowSet"]]
    games: dict[str, set[str]] = {}
    for row in rows:
        gid = identity(str(row["GAME_ID"]), game=True)
        if not gid.startswith("002" + season[2:4]) or str(row["SEASON_ID"]) != "2" + season[:4]:
            raise ValueError("Inventory includes an unexpected competition or season")
        teams = games.setdefault(gid, set())
        team = identity(str(row["TEAM_ID"]))
        if team in teams:
            raise ValueError("Duplicate team/game inventory record")
        teams.add(team)
    if not games or any(len(teams) != 2 for teams in games.values()):
        raise ValueError("Inventory needs two distinct team sides per game")
    return {
        "source_id": "nba_api.LeagueGameLog:separate-local-inventory",
        "season": season,
        "collected_at": collected_at,
        "game_ids": sorted(games),
        "raw_sha256": digest(body),
        "evidence_kind": "observed_local",
        "limitations": [
            "Separate collection shares underlying NBA provenance",
            "Game dates do not prove pregame roster availability",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--season", default="2025-26")
    parser.add_argument("--archive", required=True, type=Path)
    parser.add_argument("--confirm-local-machine", action="store_true")
    args = parser.parse_args()
    if not args.confirm_local_machine or any(
        os.environ.get(k) for k in ["CI", "GITHUB_ACTIONS", "CODEX_PROXY_CERT"]
    ):
        parser.error("Inventory requires an explicit actual-local-machine confirmation")
    from nba_api.stats.endpoints.leaguegamelog import LeagueGameLog
    from nba_api.stats.library.http import NBAStatsHTTP

    run = args.archive / uuid4().hex
    archive = Archive(run)
    captured: list[dict[str, Any]] = []
    session = NBAStatsHTTP.get_session()
    if session.cookies or session.hooks.get("response"):
        raise RuntimeError("Use a fresh process without supplied cookies or response hooks")

    def retain(response: Any, **kwargs: Any) -> None:
        body = response.content
        if len(body) > 8 * 1024 * 1024:
            raise ValueError("Inventory body exceeds diagnostic limit")
        sha, path = archive.raw(body)
        captured.append(
            {
                "http_status": response.status_code,
                "raw_sha256": sha,
                "raw_path": path,
                "received_at": utc(datetime.now(UTC)),
            }
        )

    session.hooks["response"].append(retain)
    request = {
        "source": "nba_api.LeagueGameLog",
        "season": args.season,
        "side": "T",
        "headers": dict(NBAStatsHTTP.headers),
        "requested_at": utc(datetime.now(UTC)),
        "maximum_endpoint_calls": 1,
        "timeout_seconds": 30,
        "retries": 0,
    }
    (run / "identity.json").write_text(json.dumps(request, indent=2), encoding="utf-8")
    try:
        endpoint = LeagueGameLog(
            season=args.season,
            season_type_all_star="Regular Season",
            player_or_team_abbreviation="T",
            timeout=30,
        )
        if len(captured) != 1 or captured[0]["http_status"] != 200:
            raise ValueError("Inventory did not receive one accepted response")
        body = (run / captured[0]["raw_path"]).read_bytes()
        inventory = parse_inventory(body, args.season, captured[0]["received_at"])
        (run / "inventory.json").write_text(json.dumps(inventory, indent=2), encoding="utf-8")
        archive.observation(
            {
                **captured[0],
                "outcome": "verified_sample",
                "record_count": len(inventory["game_ids"]),
                "validated_at": utc(datetime.now(UTC)),
            }
        )
        assert endpoint.nba_response is not None
        archive.verify()
        print(json.dumps({"archive": str(run), "games": len(inventory["game_ids"])}))
        return 0
    except Exception as error:
        archive.observation(
            {
                **(captured[-1] if captured else {}),
                "outcome": "failed",
                "reason": type(error).__name__,
            }
        )
        print(
            json.dumps({"archive": str(run), "outcome": "failed", "reason": type(error).__name__})
        )
        return 1
    finally:
        session.hooks["response"].remove(retain)


if __name__ == "__main__":
    raise SystemExit(main())
