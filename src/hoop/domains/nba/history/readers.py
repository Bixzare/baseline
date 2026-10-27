"""Consistent database reads; eligibility precedes latest-revision selection."""

from contextlib import nullcontext
from datetime import datetime
from typing import Any

import psycopg
from psycopg.rows import dict_row

from hoop.platform.evidence import EvidenceError, known_by
from hoop.platform.provenance import parse_time


def eligible_latest(
    rows: list[dict[str, Any]],
    cutoff: datetime,
    keys: tuple[str, ...],
    value_fields: tuple[str, ...],
) -> list[dict[str, Any]]:
    groups: dict[tuple[Any, ...], list[dict[str, Any]]] = {}
    for row in rows:
        if (
            row.get("evidence_tier") == "historical_assumption"
            or parse_time(str(row["observed_at"])) > cutoff
            or not known_by(row, cutoff)
        ):
            continue
        groups.setdefault(tuple(row[key] for key in keys), []).append(row)
    result = []
    for candidates in groups.values():
        best = max(
            (parse_time(str(row["observed_at"])), parse_time(str(row["validated_at"])))
            for row in candidates
        )
        tied = [
            row
            for row in candidates
            if (parse_time(str(row["observed_at"])), parse_time(str(row["validated_at"]))) == best
        ]
        first = tuple(tied[0].get(field) for field in value_fields)
        ambiguous = any(
            tuple(row.get(field) for field in value_fields) != first for row in tied[1:]
        )
        chosen = min(tied, key=lambda row: str(row["source_check_id"]))
        result.append({**chosen, "ambiguous_revision": ambiguous})
    return result


def player_history(
    conn: psycopg.Connection[Any],
    player_ids: list[str],
    cutoff: datetime,
    *,
    environment: str = "rehearsal",
    in_snapshot: bool = False,
) -> list[dict[str, Any]]:
    if cutoff.tzinfo is None or environment not in {"rehearsal", "production"}:
        raise EvidenceError("Explicit cutoff and environment required")
    if len(player_ids) > 1000:
        raise EvidenceError("Bounded player history request exceeded")
    with (
        nullcontext() if in_snapshot else conn.transaction(),
        conn.cursor(row_factory=dict_row) as cursor,
    ):
        if in_snapshot:
            isolation = cursor.execute("SHOW transaction_isolation").fetchone()
            read_only = cursor.execute("SHOW transaction_read_only").fetchone()
            if (
                isolation is None
                or read_only is None
                or isolation["transaction_isolation"] != "repeatable read"
                or read_only["transaction_read_only"] != "on"
            ):
                raise EvidenceError("Existing snapshot must be repeatable-read and read-only")
        else:
            cursor.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
        cursor.execute(
            """SELECT p.*,e.source_event_id,e.competition,e.season,
             s.requested_at,s.received_at,s.validated_at,s.source_published_at,s.state
             FROM nba.player_game_versions p JOIN platform.events e USING(event_id)
             JOIN platform.source_checks s ON s.check_id=p.source_check_id
             JOIN platform.runs r USING(run_id)
             WHERE p.player_id=ANY(%s) AND r.environment=%s LIMIT 100001""",
            (player_ids, environment),
        )
        facts = cursor.fetchall()
        if len(facts) > 100000:
            raise EvidenceError("History result exceeds bounded read")
        cursor.execute(
            """SELECT o.*,o.state AS event_state,s.state,
             s.requested_at,s.received_at,s.validated_at,s.source_published_at
             FROM platform.event_observations o
             JOIN platform.source_checks s ON s.check_id=o.source_check_id
             JOIN platform.runs r USING(run_id) WHERE o.event_id=ANY(%s) AND r.environment=%s
             LIMIT 100001""",
            ([row["event_id"] for row in facts], environment),
        )
        observations = cursor.fetchall()
        if len(observations) > 100000:
            raise EvidenceError("Observation result exceeds bounded read")
    events = {
        row["event_id"]: row
        for row in eligible_latest(
            observations,
            cutoff,
            ("event_id",),
            ("event_state", "details", "actual_start", "scheduled_start"),
        )
    }
    latest = eligible_latest(
        facts,
        cutoff,
        ("event_id", "player_id"),
        (
            "team_id",
            "participation",
            "minutes_seconds",
            "points",
            "rebounds",
            "assists",
            "threes_made",
            "started",
        ),
    )
    result = []
    for row in latest:
        event = events.get(row["event_id"])
        if event is None:
            result.append(
                {
                    **row,
                    "event_state": "unknown",
                    "game_date": None,
                    "date_convention": None,
                    "actual_start": None,
                    "scheduled_start": None,
                    "ambiguous_revision": True,
                }
            )
            continue
        result.append(
            {
                **row,
                "event_state": event["event_state"],
                "game_date": event["details"].get("game_date"),
                "date_convention": event["details"].get("date_convention"),
                "actual_start": event["actual_start"],
                "scheduled_start": event["scheduled_start"],
                "ambiguous_revision": row["ambiguous_revision"] or event["ambiguous_revision"],
            }
        )
    return result
