"""Capture database identities consistently, then verify artifacts after the transaction."""

import json
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

import psycopg
from psycopg.rows import dict_row

from hoop.domains.nba.history.readers import eligible_latest, player_history
from hoop.platform.artifacts import PrivateArtifacts
from hoop.platform.evidence import EvidenceError
from hoop.platform.prepared import encoded


def capture_game(
    conn: psycopg.Connection[Any],
    store: PrivateArtifacts,
    event_id: UUID,
    cutoff: datetime,
    *,
    environment: str = "rehearsal",
) -> dict[str, Any]:
    with conn.transaction(), conn.cursor(row_factory=dict_row) as cursor:
        cursor.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
        game = cursor.execute(
            """SELECT e.*,g.home_team_id,g.away_team_id FROM platform.events e
              JOIN nba.games g USING(event_id) WHERE event_id=%s""",
            (event_id,),
        ).fetchone()
        if game is None:
            raise EvidenceError("NBA game occurrence not found")
        schedule_rows = cursor.execute(
            """SELECT o.*,o.state AS event_state,s.state,
              e.source_event_id,s.requested_at,s.received_at,s.validated_at,s.source_published_at,
              s.validation_summary AS source_summary
              FROM platform.event_observations o JOIN platform.events e USING(event_id)
              JOIN platform.source_checks s ON s.check_id=o.source_check_id
              JOIN platform.runs r USING(run_id) WHERE o.event_id=%s AND r.environment=%s
              LIMIT 1001""",
            (event_id, environment),
        ).fetchall()
        if len(schedule_rows) > 1000:
            raise EvidenceError("Schedule read budget exceeded")
        schedules = eligible_latest(
            schedule_rows,
            cutoff,
            ("event_id",),
            ("event_state", "scheduled_start", "actual_start", "details"),
        )
        if len(schedules) != 1 or schedules[0]["ambiguous_revision"]:
            raise EvidenceError("Unambiguous eligible schedule required")
        rosters = cursor.execute(
            """SELECT t.*,s.validated_at AS observed_at,s.state,
              s.requested_at,s.received_at,s.source_published_at,to_jsonb(a) AS artifact,
              s.validation_summary AS source_summary
              FROM nba.roster_snapshots t
              JOIN platform.source_checks s ON s.check_id=t.source_check_id
              JOIN platform.artifacts a ON a.artifact_id=t.members_artifact_id
              JOIN platform.runs r USING(run_id)
              WHERE team_id=ANY(%s) AND season=%s AND r.environment=%s LIMIT 1001""",
            ([game["home_team_id"], game["away_team_id"]], game["season"], environment),
        ).fetchall()
        if len(rosters) > 1000:
            raise EvidenceError("Roster read budget exceeded")
        selected = eligible_latest(rosters, cutoff, ("team_id",), ("members_artifact_id", "season"))
        if len(selected) != 2 or any(row["ambiguous_revision"] for row in selected):
            raise EvidenceError("Both unambiguous eligible rosters required")
        ids = []
        for row in selected:
            members = row["artifact"]["manifest"].get("player_ids")
            if (
                not isinstance(members, list)
                or not members
                or any(not isinstance(i, str) for i in members)
            ):
                raise EvidenceError("Roster manifest must declare captured player identities")
            ids.extend(members)
        history = player_history(conn, ids, cutoff, environment=environment, in_snapshot=True)
    # The repeatable snapshot is closed before authentication/download calls.
    for row in selected:
        body = store.read(row["artifact"])
        members = json.loads(body)
        if sorted(member["player_id"] for member in members["players"]) != sorted(
            row["artifact"]["manifest"]["player_ids"]
        ):
            raise EvidenceError("Roster body differs from captured membership manifest")
        row["artifact_body"] = body.decode()
    package = {
        "schema_version": 1,
        "run_id": str(uuid4()),
        "environment": environment,
        "event": {
            "event_id": str(event_id),
            "source_event_id": game["source_event_id"],
            "season": game["season"],
            "team_ids": [game["home_team_id"], game["away_team_id"]],
        },
        "feature_cutoff": cutoff.isoformat(),
        "schedule": schedules[0],
        "rosters": selected,
        "history": history,
        "gaps": [],
    }
    result: dict[str, Any] = json.loads(encoded(package))
    return result
