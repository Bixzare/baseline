"""Partial finals, explicit nonparticipation and versioned cohort reconciliation."""

import json
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid5
from zoneinfo import ZoneInfo

import psycopg
from psycopg.rows import dict_row

from hoop.domains.nba.collection import append_pending_lifecycle
from hoop.domains.nba.outcomes.parsing import PARSER, normalize_final, outcome_entries
from hoop.platform.artifacts import PrivateArtifacts, retain
from hoop.platform.evidence import EvidenceError
from hoop.platform.outcomes import validate_outcomes
from hoop.platform.prepared import encoded
from hoop.platform.provenance import digest, parse_time
from hoop.platform.records import immutable_insert


def ingest_final(
    conn: psycopg.Connection[Any],
    store: PrivateArtifacts,
    event_id: UUID,
    check: dict[str, Any],
    normalized: dict[str, Any],
    *,
    config: dict[str, Any],
    fault: Any = lambda stage: None,
) -> dict[str, Any]:
    with conn.cursor(row_factory=dict_row) as cursor:
        event = cursor.execute(
            "SELECT e.*,g.home_team_id,g.away_team_id FROM platform.events e JOIN "
            "nba.games g USING(event_id) WHERE event_id=%s",
            (event_id,),
        ).fetchone()
        if (
            event is None
            or event["source_event_id"] != normalized["game"]["game_id"]
            or event["season"] != normalized["game"]["season"]
        ):
            raise EvidenceError("Final occurrence mismatch")
        state = cursor.execute(
            "SELECT state FROM platform.event_observations WHERE event_id=%s ORDER BY "
            "observed_at DESC,recorded_at DESC,observation_id DESC LIMIT 1",
            (event_id,),
        ).fetchone()
        if not state or state["state"] in {"postponed", "cancelled", "unknown"}:
            raise EvidenceError("Excluded or unresolved occurrence remains pending")
        if {event["home_team_id"], event["away_team_id"]} != {
            t["team_id"] for t in normalized["teams"]
        }:
            raise EvidenceError("Final teams conflict with occurrence")
        batch = cursor.execute(
            "SELECT a.* FROM platform.forecast_batches b JOIN platform.artifacts a ON "
            "a.artifact_id=b.cohort_artifact_id WHERE b.event_id=%s AND "
            "b.family='player_recent_appearance_mean'",
            (event_id,),
        ).fetchone()
    if check.get("state") != "accepted" or check["validation_summary"].get("capability") != "final":
        raise EvidenceError("Accepted final source required")
    # Verify the original raw body still exists; never run HTTP inside the transaction.
    with conn.cursor(row_factory=dict_row) as cursor:
        raw = cursor.execute(
            "SELECT * FROM platform.artifacts WHERE artifact_id=%s", (check["raw_artifact_id"],)
        ).fetchone()
    if raw is None:
        raise EvidenceError("Final raw artifact missing")
    raw_body = store.read(raw)
    verified = normalize_final(
        json.loads(raw_body),
        {
            "game_id": event["source_event_id"],
            "season": event["season"],
            "expected_team_ids": [event["home_team_id"], event["away_team_id"]],
            "dnp_semantics": config.get("dnp_semantics", "unknown_until_accepted"),
        },
        parse_time(str(check["validated_at"])),
    )
    if verified != normalized:
        raise EvidenceError("Normalized facts differ from retained final body")
    cohort = json.loads(store.read(batch)) if batch else []
    entries = outcome_entries(normalized, cohort)
    outcome_state = validate_outcomes(entries)
    semantic = digest(
        encoded(
            {
                "event_id": str(event_id),
                "normalized": normalized,
                "cohort": cohort,
                "parser_version": PARSER,
                "config": config,
            }
        )
    )
    identity = uuid5(NAMESPACE_URL, "baseline:outcome:" + str(event_id) + ":" + semantic)
    clock_row = conn.execute("SELECT clock_timestamp()").fetchone()
    assert clock_row is not None
    observed = clock_row[0]
    with conn.cursor(row_factory=dict_row) as cursor:
        existing = cursor.execute(
            "SELECT * FROM platform.outcome_versions WHERE event_id=%s AND semantic_hash=%s",
            (event_id, semantic),
        ).fetchone()
    artifact = None
    if existing:
        with conn.cursor(row_factory=dict_row) as cursor:
            prior_artifact = cursor.execute(
                "SELECT * FROM platform.artifacts WHERE artifact_id=%s",
                (existing["outcome_artifact_id"],),
            ).fetchone()
        if prior_artifact is None:
            raise EvidenceError("Original outcome artifact missing")
        saved = json.loads(store.read(prior_artifact))
        if saved.get("semantic_hash") != semantic or saved.get("event_id") != str(event_id):
            raise EvidenceError("Original outcome artifact identity mismatch")
    else:
        artifact = retain(
            conn,
            store,
            encoded(
                {
                    "schema_version": 1,
                    "event_id": str(event_id),
                    "source_event_id": event["source_event_id"],
                    "season": event["season"],
                    "entries": entries,
                    "normalized": normalized,
                    "cohort_artifact_id": str(batch["artifact_id"]) if batch else None,
                    "source_check_id": str(check["check_id"]),
                    "source_validated_at": str(check["validated_at"]),
                    "prepared_at": observed.isoformat(),
                    "parser_version": PARSER,
                    "config_hash": digest(encoded(config)),
                    "semantic_hash": semantic,
                    "fact_ids": [
                        str(uuid5(identity, "player:" + p["player_id"]))
                        for p in normalized["players"]
                    ],
                }
            ),
            kind="reports",
            format="json",
            manifest={"event_id": str(event_id), "semantic_hash": semantic},
        )
    with conn.transaction(), conn.cursor(row_factory=dict_row) as cursor:
        cursor.execute("SET LOCAL statement_timeout='10s'")
        cursor.execute("SET LOCAL lock_timeout='2s'")
        cursor.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s,617))", (str(event_id),))
        # A parser/config revision cannot be made available before its guarded
        # normalization write, including time spent uploading or waiting on locks.
        observed_row = cursor.execute("SELECT clock_timestamp() AS observed_at").fetchone()
        assert observed_row is not None
        observed = observed_row["observed_at"]
        existing = cursor.execute(
            "SELECT * FROM platform.outcome_versions WHERE event_id=%s AND semantic_hash=%s",
            (event_id, semantic),
        ).fetchone()
        if not existing:
            assert artifact is not None
            for player in normalized["players"]:
                cursor.execute(
                    "INSERT INTO nba.players(player_id) VALUES(%s) ON CONFLICT DO NOTHING",
                    (player["player_id"],),
                )
                immutable_insert(
                    conn,
                    "nba",
                    "player_game_versions",
                    {
                        "fact_id": uuid5(identity, "player:" + player["player_id"]),
                        "event_id": event_id,
                        "player_id": player["player_id"],
                        "team_id": player["team_id"],
                        "source_check_id": UUID(str(check["check_id"])),
                        "observed_at": observed,
                        "evidence_tier": "live_observed",
                        "participation": player["participation"],
                        "minutes_seconds": Decimal(player["minutes_seconds"])
                        if player["minutes_seconds"] is not None
                        else None,
                        "points": player["points"],
                        "rebounds": player["rebounds"],
                        "assists": player["assists"],
                        "threes_made": player["threes_made"],
                        "started": None,
                        "normalization_hash": semantic,
                    },
                    ("fact_id",),
                )
            for team, opponent in [
                (normalized["teams"][0], normalized["teams"][1]),
                (normalized["teams"][1], normalized["teams"][0]),
            ]:
                immutable_insert(
                    conn,
                    "nba",
                    "team_game_versions",
                    {
                        "fact_id": uuid5(identity, "team:" + team["team_id"]),
                        "event_id": event_id,
                        "team_id": team["team_id"],
                        "source_check_id": UUID(str(check["check_id"])),
                        "observed_at": observed,
                        "evidence_tier": "live_observed",
                        "points_for": team["points"],
                        "points_against": opponent["points"],
                        "extras_artifact_id": None,
                        "normalization_hash": semantic,
                    },
                    ("fact_id",),
                )
            start = parse_time(normalized["game"]["start_utc"])
            details = {
                "game_date": start.astimezone(ZoneInfo("America/New_York")).date().isoformat(),
                "date_convention": config.get("calendar_convention"),
            }
            known_status = cursor.execute(
                "SELECT 1 FROM platform.event_observations WHERE event_id=%s AND "
                "source_check_id=%s",
                (event_id, check["check_id"]),
            ).fetchone()
            if not known_status:
                immutable_insert(
                    conn,
                    "platform",
                    "event_observations",
                    {
                        "observation_id": uuid5(identity, "final-status"),
                        "event_id": event_id,
                        "source_check_id": UUID(str(check["check_id"])),
                        "observed_at": observed,
                        "scheduled_start": start,
                        "actual_start": None,
                        "state": "final",
                        "details": details,
                    },
                    ("observation_id",),
                )
            fault("after_facts")
            immutable_insert(
                conn,
                "platform",
                "outcome_versions",
                {
                    "outcome_version_id": identity,
                    "event_id": event_id,
                    "observed_at": observed,
                    "source_check_id": UUID(str(check["check_id"])),
                    "outcome_artifact_id": UUID(artifact["artifact_id"]),
                    "state": outcome_state,
                    "semantic_hash": semantic,
                    "parser_version": PARSER,
                    "config_hash": digest(encoded(config)),
                },
                ("outcome_version_id",),
            )
        else:
            identity = existing["outcome_version_id"]
        immutable_insert(
            conn,
            "platform",
            "outcome_observations",
            {
                "event_id": event_id,
                "source_check_id": UUID(str(check["check_id"])),
                "parser_version": PARSER,
                "config_hash": digest(encoded(config)),
                "outcome_version_id": identity,
            },
            ("event_id", "source_check_id", "parser_version", "config_hash"),
        )
    final_observation = conn.execute(
        "SELECT observation_id FROM platform.event_observations WHERE event_id=%s "
        "AND source_check_id=%s",
        (event_id, check["check_id"]),
    ).fetchone()
    if final_observation:
        append_pending_lifecycle(conn, event_id, final_observation[0])
    return {
        "outcome_version_id": str(identity),
        "state": outcome_state,
        "reused": existing is not None,
        "resolved": sum(x["value"] is not None for x in entries),
        "unresolved": sum(x["value"] is None for x in entries),
    }


def pending_work(
    conn: psycopg.Connection[Any],
    now: datetime,
    *,
    event_ids: list[UUID] | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> list[dict[str, Any]]:
    if (
        now.tzinfo is None
        or (date_from and date_from.tzinfo is None)
        or (date_to and date_to.tzinfo is None)
    ):
        raise EvidenceError("Reconciliation ranges require timezone-aware times")
    if event_ids and len(event_ids) > 1000:
        raise EvidenceError("Explicit ID budget exceeded")
    if date_from and date_to and date_from > date_to:
        raise EvidenceError("Reconciliation range is reversed")
    with conn.cursor(row_factory=dict_row) as cursor:
        rows = cursor.execute(
            """SELECT e.*,g.home_team_id,g.away_team_id,o.scheduled_start,o.state,
        v.state AS outcome_state FROM platform.events e JOIN nba.games g USING(event_id)
        JOIN LATERAL(SELECT * FROM platform.event_observations WHERE event_id=e.event_id
          ORDER BY observed_at DESC,recorded_at DESC,observation_id DESC LIMIT 1)o ON true
        LEFT JOIN LATERAL(SELECT * FROM platform.outcome_versions WHERE event_id=e.event_id
          ORDER BY observed_at DESC,recorded_at DESC,outcome_version_id DESC LIMIT 1)v ON true
        WHERE o.state NOT IN('postponed','cancelled','unknown')
        AND NOT EXISTS(SELECT FROM platform.events child
           WHERE child.predecessor_event_id=e.event_id)
        AND (o.scheduled_start<=%s OR o.state='final')
        AND (%s::uuid[] IS NULL OR e.event_id=ANY(%s::uuid[]))
        AND (%s::timestamptz IS NULL OR o.scheduled_start>=%s)
        AND (%s::timestamptz IS NULL OR o.scheduled_start<=%s)
        AND (%s OR %s::uuid[] IS NOT NULL OR v.state IS DISTINCT FROM 'final'
             OR o.scheduled_start>=%s)
        AND (%s::uuid[] IS NOT NULL OR %s OR v.outcome_version_id IS NOT NULL
          OR EXISTS(SELECT FROM platform.forecast_batches f WHERE f.event_id=e.event_id)
          OR EXISTS(SELECT FROM platform.source_checks sc JOIN platform.runs r USING(run_id)
             WHERE sc.check_id=o.source_check_id AND r.operation<>'seed_import'))
        ORDER BY o.scheduled_start NULLS FIRST,e.event_id LIMIT 1001""",
            (
                now,
                event_ids,
                event_ids,
                date_from,
                date_from,
                date_to,
                date_to,
                date_from is not None or date_to is not None,
                event_ids,
                now - timedelta(days=7),
                event_ids,
                date_from is not None or date_to is not None,
            ),
        ).fetchall()
    if len(rows) > 1000:
        raise EvidenceError("Reconciliation work budget exceeded; narrow the range")
    return list(rows)
