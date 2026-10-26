"""Store a verified current roster, never a historical participant cross product."""

import json
import re
from typing import Any
from uuid import UUID

import psycopg

from hoop.domains.nba.history.seed import stable_id
from hoop.platform.artifacts import PrivateArtifacts, retain
from hoop.platform.evidence import EvidenceError
from hoop.platform.records import immutable_insert


def save_roster(
    conn: psycopg.Connection[Any],
    store: PrivateArtifacts,
    *,
    team_id: str,
    season: str,
    source_check: dict[str, Any],
    players: list[dict[str, str]],
) -> UUID:
    ids = [player.get("player_id", "") for player in players]
    if (
        not ids
        or len(ids) != len(set(ids))
        or any(re.fullmatch(r"[1-9][0-9]*", value) is None for value in ids)
    ):
        raise EvidenceError("A nonempty roster of unique stable player IDs is required")
    if (
        source_check.get("state") != "accepted"
        or source_check.get("validation_summary", {}).get("capability") != "roster"
    ):
        raise EvidenceError("Accepted current-roster source capability required")
    for player in players:
        if set(player) - {"player_id", "availability"} or player.get(
            "availability", "unknown"
        ) not in {"unknown", "available", "unavailable", "questionable", "doubtful", "probable"}:
            raise EvidenceError("Unsupported roster member metadata")
    body = json.dumps(
        {
            "schema_version": 1,
            "team_id": team_id,
            "season": season,
            "players": sorted(players, key=lambda player: player["player_id"]),
        },
        sort_keys=True,
    ).encode()
    artifact = retain(
        conn,
        store,
        body,
        kind="history",
        format="json",
        manifest={"team_id": team_id, "season": season, "player_ids": sorted(ids)},
    )
    roster_id = stable_id(
        "roster", team_id, season, str(source_check["check_id"]), artifact["sha256"]
    )
    with conn.transaction():
        immutable_insert(
            conn,
            "nba",
            "roster_snapshots",
            {
                "roster_id": roster_id,
                "team_id": team_id,
                "season": season,
                "source_check_id": UUID(str(source_check["check_id"])),
                "validated_at": source_check["validated_at"],
                "members_artifact_id": UUID(artifact["artifact_id"]),
            },
            ("roster_id",),
        )
    return roster_id
