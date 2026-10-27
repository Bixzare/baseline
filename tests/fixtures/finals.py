"""Small invented complete/partial/DNP finals, not NBA coverage evidence."""

from datetime import UTC, datetime
from typing import Any


def final_payload(start: datetime | None = None) -> dict[str, Any]:
    start = start or datetime(2026, 10, 25, 18, tzinfo=UTC)

    def player(identity: int, points: int) -> dict[str, Any]:
        return {
            "personId": identity,
            "played": "1",
            "statistics": {
                "minutes": "PT53M12.50S",
                "points": points,
                "reboundsTotal": 8,
                "assists": 4,
                "threePointersMade": 2,
            },
        }

    return {
        "game": {
            "gameId": "0022600001",
            "gameStatus": 3,
            "gameStatusText": "Final",
            "gameTimeUTC": start.isoformat(),
            "homeTeam": {
                "teamId": 101,
                "score": 100,
                "statistics": {"points": 100},
                "players": [player(201, 100)],
            },
            "awayTeam": {
                "teamId": 102,
                "score": 90,
                "statistics": {"points": 90},
                "players": [player(202, 90)],
            },
        }
    }


def final_context() -> dict[str, Any]:
    return {
        "game_id": "0022600001",
        "season": "2026-27",
        "expected_team_ids": ["101", "102"],
        "dnp_semantics": "played0_with_reason",
    }


def final_route(*, template: bool = False) -> dict[str, Any]:
    from hoop.domains.nba.outcomes import PARSER
    from hoop.domains.nba.sources.probe import live_url
    from hoop.platform.prepared import encoded
    from hoop.platform.provenance import digest

    context = final_context()
    if template:
        context.update(
            game_id="{game_id}",
            season="{season}",
            expected_team_ids="{team_ids}",
            allowed_seasons=["2026-27"],
        )
    url = live_url("final", "{game_id}" if template else context["game_id"])
    identity = digest(
        encoded(
            {
                "url": url,
                "context": context,
                "capability": "final",
                "environment": "local",
                "parser_version": PARSER,
            }
        )
    )
    return {
        "status": "accepted",
        "capability": "final",
        "url": url,
        "context": context,
        "parser_version": PARSER,
        "request_hash": identity,
        "owner_acceptance_id": "invented-fixture",
        "evidence": {
            "outcome": "verified_sample",
            "environment": "local",
            "observation_id": "invented",
            "request_hash": identity,
            "kind": "synthetic_fixture",
        },
    }
