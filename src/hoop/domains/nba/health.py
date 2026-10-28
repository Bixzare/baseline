"""Least-privilege operational snapshot; unavailable provider measurements stay unknown."""

import json
from datetime import timedelta
from typing import Any

import psycopg
from psycopg.rows import dict_row

from hoop.domains.nba.health_policy import assess
from hoop.platform.operations import production_enabled
from hoop.platform.prepared import encoded
from hoop.platform.provenance import digest, parse_time


def snapshot(
    conn: psycopg.Connection[Any],
    config: dict[str, Any],
    operations: dict[str, Any],
    *,
    rehearsal: bool = False,
) -> dict[str, Any]:
    environment = "rehearsal" if rehearsal else "production"
    with conn.transaction(), conn.cursor(row_factory=dict_row) as cursor:
        cursor.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
        now_row = cursor.execute("SELECT clock_timestamp() AS now").fetchone()
        assert now_row is not None
        now = now_row["now"]
        runs = {}
        for operation in ["nightly", "dispatcher"]:
            started = cursor.execute(
                "SELECT max(started_at) AS time FROM platform.runs WHERE domain='nba' AND "
                "operation=%s AND environment=%s",
                (operation, environment),
            ).fetchone()
            complete = cursor.execute(
                """SELECT max(e.recorded_at) AS time FROM platform.run_events e
                JOIN platform.runs r USING(run_id) WHERE r.operation=%s AND r.environment=%s
                AND e.state='succeeded' AND e.details->>'scope'='operation'""",
                (operation, environment),
            ).fetchone()
            runs[operation] = {
                "started": started["time"] if started else None,
                "succeeded": complete["time"] if complete else None,
            }
        sources = cursor.execute(
            """SELECT DISTINCT ON(s.source_id,s.validation_summary->>'capability',
            s.validation_summary->>'environment')
          s.* FROM platform.source_checks s JOIN platform.runs r USING(run_id)
          WHERE r.environment=%s ORDER BY s.source_id,s.validation_summary->>'capability',
          s.validation_summary->>'environment',s.recorded_at DESC,s.check_id DESC LIMIT 1001""",
            (environment,),
        ).fetchall()
        stage_rows = cursor.execute(
            """SELECT DISTINCT ON(r.operation,e.details->>'stage',e.state)
            r.operation,e.state,e.recorded_at,e.details->>'stage' AS stage
            FROM platform.run_events e JOIN platform.runs r USING(run_id)
            WHERE r.domain='nba' AND r.environment=%s AND e.details->>'scope'='stage'
            ORDER BY r.operation,e.details->>'stage',e.state,e.recorded_at DESC LIMIT 101""",
            (environment,),
        ).fetchall()
        pending = cursor.execute(
            """SELECT e.event_id,o.scheduled_start,o.state,v.state AS outcome_state
            FROM platform.events e JOIN nba.games g USING(event_id)
            JOIN LATERAL(SELECT * FROM platform.event_observations x WHERE x.event_id=e.event_id
              ORDER BY observed_at DESC,recorded_at DESC,observation_id DESC LIMIT 1)o ON true
            JOIN platform.source_checks sc ON sc.check_id=o.source_check_id
            JOIN platform.runs r USING(run_id)
            LEFT JOIN LATERAL(SELECT state FROM platform.outcome_versions x
              WHERE x.event_id=e.event_id ORDER BY observed_at DESC,recorded_at DESC,
              outcome_version_id DESC LIMIT 1)v ON true
            WHERE e.season='2026-27' AND e.competition='regular' AND r.environment=%s
              AND (o.state='final' OR o.scheduled_start<=%s)
              AND o.state IN('scheduled','in_progress','final')
              AND v.state IS DISTINCT FROM 'final'
              AND NOT EXISTS(SELECT FROM platform.events c WHERE c.predecessor_event_id=e.event_id)
            ORDER BY o.scheduled_start NULLS FIRST,e.event_id LIMIT 1001""",
            (environment, now),
        ).fetchall()
        events = cursor.execute(
            """SELECT e.event_id,o.*,g.home_team_id,g.away_team_id,s.received_at,
           s.source_published_at,s.validation_summary FROM platform.events e
           JOIN nba.games g USING(event_id)
           JOIN LATERAL(SELECT * FROM platform.event_observations v WHERE v.event_id=e.event_id
             ORDER BY observed_at DESC,recorded_at DESC,observation_id DESC LIMIT 1)o ON true
           JOIN platform.source_checks s ON s.check_id=o.source_check_id
           JOIN platform.runs r USING(run_id)
           WHERE e.season='2026-27' AND e.competition='regular' AND r.environment=%s
           AND (o.scheduled_start IS NULL OR o.scheduled_start BETWEEN %s AND %s)
           AND NOT EXISTS(SELECT FROM platform.events child
             WHERE child.predecessor_event_id=e.event_id)
           ORDER BY e.event_id LIMIT 2001""",
            (environment, now - timedelta(days=1), now + timedelta(days=7)),
        ).fetchall()
        status = cursor.execute(
            "SELECT * FROM platform.batch_status WHERE event_id=ANY(%s)",
            ([e["event_id"] for e in events],),
        ).fetchall()
        rosters = cursor.execute(
            """SELECT rs.*,s.received_at,s.source_published_at,s.validation_summary
          FROM nba.roster_snapshots rs
          JOIN platform.source_checks s ON s.check_id=rs.source_check_id
          JOIN platform.runs r USING(run_id) WHERE r.environment=%s AND s.state='accepted'
          ORDER BY rs.validated_at DESC LIMIT 10001""",
            (environment,),
        ).fetchall()
        backup = cursor.execute(
            """SELECT e.details,a.sha256 FROM platform.run_events e
          JOIN platform.runs r USING(run_id)
          JOIN platform.artifacts a ON a.artifact_id=CASE WHEN e.details->>'backup_manifest_id'
            ~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
            THEN (e.details->>'backup_manifest_id')::uuid END
          WHERE r.operation='backup' AND r.environment=%s AND e.state='succeeded'
          AND e.reason_code='backup_remote_verified' AND e.details->>'off_device_verified'='true'
          ORDER BY e.recorded_at DESC LIMIT 1""",
            (environment,),
        ).fetchone()
        usage = cursor.execute(
            "SELECT pg_database_size(current_database()) AS database_bytes,(SELECT "
            "coalesce(sum(byte_count),0) FROM platform.artifacts) AS registered_bytes"
        ).fetchone()
        assert usage is not None
    if (
        len(sources) > 1000
        or len(events) > 2000
        or len(rosters) > 10000
        or len(pending) > 1000
        or len(stage_rows) > 100
    ):
        raise ValueError("Health snapshot budget exceeded")

    def fresh(row: dict[str, Any], age: int) -> bool:
        times = [
            row.get("received_at"),
            row.get("source_published_at"),
            row.get("validation_summary", {}).get("source_generated_at"),
        ]
        return bool(times[0]) and all(
            0 <= (now - parse_time(str(t))).total_seconds() <= age for t in times if t
        )

    source_rows = []
    for source in sources:
        capability = source["validation_summary"].get("capability", "unknown")
        env = source["validation_summary"].get("environment", "unverified")
        source_rows.append(
            {
                "alert_key": "nba:source:"
                + digest(encoded([source["source_id"], capability, env]))[:20],
                "source_id": source["source_id"],
                "capability": capability,
                "environment": env,
                "state": source["state"],
                "received_at": source["received_at"],
                "generated_at": source["validation_summary"].get("source_generated_at"),
                "max_age_seconds": 1800
                if capability in {"schedule", "status"}
                else 86400
                if capability == "roster"
                else None,
            }
        )
    game_rows = []
    for event in events:
        teams = [event["home_team_id"], event["away_team_id"]]

        def roster_current(team: str) -> bool:
            candidates = [r for r in rosters if r["team_id"] == team and r["season"] == "2026-27"]
            return (
                bool(candidates)
                and fresh(candidates[0], 86400)
                and not any(
                    r["validated_at"] == candidates[0]["validated_at"]
                    and r["members_artifact_id"] != candidates[0]["members_artifact_id"]
                    for r in candidates
                )
            )

        roster_fresh = all(roster_current(t) for t in teams)
        game_rows.append(
            {
                "event_id": str(event["event_id"]),
                "start": event["scheduled_start"],
                "state": event["state"],
                "valid_forecast": any(
                    s["event_id"] == event["event_id"] and s["state"] == "timely_confirmed"
                    for s in status
                ),
                "essential_fresh": fresh(event, 1800) and roster_fresh,
            }
        )
    data = {
        "production_active": production_enabled(operations),
        "activation_at": config.get("activation_at"),
        "fallback_enabled": config.get("local_fallback_enabled", False),
        "events": game_rows,
        "runs": runs,
        "stages": list(stage_rows),
        "pending_outcomes": list(pending),
        "coverage": {
            "events_observed": len(game_rows),
            "valid_forecast_events": sum(e["valid_forecast"] for e in game_rows),
            "scope": "observed current occurrences from past day through next seven days",
            "participant_coverage": "unmeasured; see immutable evaluation reports",
        },
        "schedule_known": any(
            s["validation_summary"].get("capability") == "schedule"
            and s["state"] == "accepted"
            and fresh(s, 86400)
            for s in sources
        ),
        "sources": source_rows,
        "missing_capabilities": sorted(
            {"schedule", "status", "roster", "final"} - {s["capability"] for s in source_rows}
        ),
        "backup": {
            "verified": bool(
                backup and backup["details"].get("remote_readback_sha256") == backup["sha256"]
            ),
            "cutoff": backup["details"].get("backup_cutoff") if backup else None,
        },
        "capacity": {
            "database": {
                "used_bytes": usage["database_bytes"],
                "limit_bytes": config.get("database_limit_bytes"),
                "limit_verified": config.get("account_limits_verified", False),
                "measurement": "pg_database_size",
                "provider_usage_known": True,
            },
            "objects": {
                "used_bytes": int(usage["registered_bytes"]),
                "limit_bytes": config.get("object_limit_bytes"),
                "limit_verified": config.get("account_limits_verified", False),
                "measurement": "registered_artifact_estimate",
                "provider_usage_known": False,
            },
        },
    }
    return {
        "now": now,
        "snapshot": data,
        "assessment": assess(now, json.loads(encoded(data))),
    }
