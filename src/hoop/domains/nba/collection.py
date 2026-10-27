"""Accepted source routing, immutable observations and occurrence transitions."""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

import psycopg
from psycopg.rows import dict_row

from hoop.domains.nba.history.rosters import save_roster
from hoop.domains.nba.sources.policy import Policy, ProbeRequest, ProbeRunner
from hoop.domains.nba.sources.runtime import refuse_denied
from hoop.domains.nba.sources.validate import game_identity, validate
from hoop.platform.artifacts import ArtifactError, PrivateArtifacts, retain
from hoop.platform.evidence import EvidenceError, register
from hoop.platform.prepared import encoded
from hoop.platform.provenance import Archive, digest, parse_time
from hoop.platform.records import immutable_insert

PARSER = "nba-collection-v1"


def accepted_request(
    route: dict[str, Any], environment: str, *, rehearsal: bool, parser_version: str = PARSER
) -> ProbeRequest:
    """Acceptance must bind the exact observed request/parser/environment identity."""
    evidence = route.get("evidence", {})
    request = ProbeRequest(route["capability"], route["url"], environment, route["context"])
    identity = digest(
        encoded(
            {
                "url": request.url,
                "context": request.context,
                "capability": request.capability,
                "environment": environment,
                "parser_version": parser_version,
            }
        )
    )
    if (
        route.get("status") != "accepted"
        or route.get("request_hash") != identity
        or evidence.get("outcome") != "verified_sample"
        or evidence.get("environment") != environment
        or not evidence.get("observation_id")
        or evidence.get("request_hash") != identity
        or not route.get("owner_acceptance_id")
        or route.get("parser_version") != parser_version
        or (evidence.get("kind") == "synthetic_fixture" and not rehearsal)
    ):
        raise EvidenceError("Exact owner-accepted capability/environment route required")
    return request


def collection_validator(body: bytes, request: ProbeRequest, now: datetime) -> dict[str, Any]:
    def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("Duplicate JSON key")
            result[key] = value
        return result

    payload = json.loads(body, object_pairs_hook=unique_object)
    summary = validate(body, request, now)
    generated = payload.get("meta", {}).get("time")
    if generated:
        if request.context.get("source_time_semantics") != "generated_utc":
            raise ValueError("Source time semantics require explicit route acceptance")
        timestamp = parse_time(generated)
        max_age = 86400 if request.capability == "roster" else 1800
        if not 0 <= (now - timestamp).total_seconds() <= max_age:
            raise ValueError("Stale or future source generation")
        summary["source_generated_at"] = timestamp.isoformat()
    # Only exact labels accepted with the route can establish these transitions.
    if request.capability in {"schedule", "status"}:
        games = (
            [g for day in payload["leagueSchedule"]["gameDates"] for g in day["games"]]
            if request.capability == "schedule"
            else payload["scoreboard"]["games"]
        )
        labels = request.context.get("accepted_state_labels", {})
        for row, game in zip(summary["records"], games, strict=True):
            label = game["gameStatusText"]
            state = labels.get(label)
            if state is None:
                state = {1: "scheduled", 2: "in_progress", 3: "final"}[row["status"]]
                if (
                    row["status"] == 1
                    and label not in {"Scheduled", "", "TBD"}
                    and " ET" not in label
                ):
                    state = "unknown"
            if state not in {
                "scheduled",
                "in_progress",
                "final",
                "postponed",
                "cancelled",
                "unknown",
            }:
                raise ValueError("Unsupported accepted status label")
            row["state"] = state
            # gameTimeUTC is scheduled time, not actual start evidence.
            row["actual_start"] = None
    return summary


def apply_game(
    conn: psycopg.Connection[Any], record: dict[str, Any], check: dict[str, Any]
) -> dict[str, Any]:
    game_id, competition, season = game_identity(record["game_id"])
    home, away = str(record["home_team_id"]), str(record["away_team_id"])
    state = record["state"]
    if (
        home == away
        or not home.isdecimal()
        or not away.isdecimal()
        or state not in {"scheduled", "in_progress", "final", "postponed", "cancelled", "unknown"}
        or check.get("state") != "accepted"
        or record.get("season", season) != season
        or check["validation_summary"].get("capability") not in {"schedule", "status"}
    ):
        raise EvidenceError("Accepted schedule/status and consistent identities required")
    observed = parse_time(str(check["validated_at"]))
    start = parse_time(record["start_utc"]) if record.get("start_utc") else None
    actual = parse_time(record["actual_start"]) if record.get("actual_start") else None
    with conn.transaction(), conn.cursor(row_factory=dict_row) as cursor:
        cursor.execute("SET LOCAL lock_timeout='2s'")
        cursor.execute("SET LOCAL statement_timeout='10s'")
        cursor.execute(
            "SELECT pg_advisory_xact_lock(hashtextextended(%s,617))", ("nba:" + game_id,)
        )
        prior = cursor.execute(
            "SELECT * FROM platform.events WHERE domain='nba' AND source_event_id=%s "
            "ORDER BY occurrence_no DESC LIMIT 1",
            (game_id,),
        ).fetchone()
        existing = cursor.execute(
            """SELECT e.* FROM platform.events e
            JOIN platform.event_observations o USING(event_id)
            WHERE e.domain='nba' AND e.source_event_id=%s AND o.source_check_id=%s""",
            (game_id, check["check_id"]),
        ).fetchone()
        if existing:
            prior = existing
        previous = None
        successor = False
        if prior:
            cursor.execute(
                "SELECT pg_advisory_xact_lock(hashtextextended(%s,617))", (str(prior["event_id"]),)
            )
            previous = cursor.execute(
                "SELECT * FROM platform.event_observations WHERE event_id=%s ORDER BY "
                "observed_at DESC,recorded_at DESC,observation_id DESC LIMIT 1",
                (prior["event_id"],),
            ).fetchone()
            if previous and observed < previous["observed_at"] and not existing:
                raise EvidenceError(
                    "Older observation cannot be assigned to the current occurrence"
                )
            successor = bool(
                previous
                and not existing
                and previous["state"] == "postponed"
                and state == "scheduled"
                and start
                and start > observed
                and observed > previous["observed_at"]
                and check["validation_summary"]["capability"] == "schedule"
            )
        number = (
            prior["occurrence_no"] + 1
            if successor and prior
            else (prior["occurrence_no"] if prior else 1)
        )
        event_id = (
            uuid5(NAMESPACE_URL, f"baseline:nba:occurrence:{game_id}:{number}")
            if not prior or successor
            else prior["event_id"]
        )
        immutable_insert(
            conn,
            "platform",
            "events",
            {
                "event_id": event_id,
                "domain": "nba",
                "source_event_id": game_id,
                "competition": competition,
                "season": season,
                "occurrence_no": number,
                "predecessor_event_id": prior["event_id"]
                if successor and prior
                else (prior["predecessor_event_id"] if prior else None),
            },
            ("event_id",),
        )
        for team in [home, away]:
            cursor.execute(
                "INSERT INTO nba.teams(team_id) VALUES(%s) ON CONFLICT DO NOTHING", (team,)
            )
        immutable_insert(
            conn,
            "nba",
            "games",
            {
                "event_id": event_id,
                "home_team_id": home,
                "away_team_id": away,
                "source_season_type": {
                    "regular": "Regular Season",
                    "preseason": "Pre Season",
                    "playoffs": "Playoffs",
                    "play-in": "PlayIn",
                    "unknown": "Unknown",
                }[competition],
            },
            ("event_id",),
        )
        observation = uuid5(NAMESPACE_URL, f"baseline:observation:{event_id}:{check['check_id']}")
        immutable_insert(
            conn,
            "platform",
            "event_observations",
            {
                "observation_id": observation,
                "event_id": event_id,
                "source_check_id": UUID(str(check["check_id"])),
                "observed_at": observed,
                "scheduled_start": start,
                "actual_start": actual,
                "state": state,
                "details": {
                    "source_generated_at": check["validation_summary"].get("source_generated_at"),
                    "unscheduled": start is None,
                },
            },
            ("observation_id",),
        )
    # Source/transition is durable before lifecycle retries. Derived status already
    # sees invalidating observations even if this append fails.
    append_pending_lifecycle(conn, event_id, observation)
    return {"event_id": str(event_id), "observation_id": str(observation), "successor": successor}


def append_pending_lifecycle(
    conn: psycopg.Connection[Any], event_id: UUID, observation: UUID
) -> None:
    affected = conn.execute(
        "SELECT batch_id FROM platform.forecast_batches WHERE event_id=%s", (event_id,)
    ).fetchall()
    for batch in affected:
        conn.execute("SELECT platform.append_lifecycle(%s,%s)", (batch[0], observation))


def work_list(conn: psycopg.Connection[Any], now: datetime) -> list[dict[str, Any]]:
    if now.tzinfo is None:
        raise EvidenceError("Upcoming work needs timezone-aware UTC time")
    with conn.cursor(row_factory=dict_row) as cursor:
        rows = cursor.execute(
            """SELECT e.event_id,e.source_event_id,e.season,g.home_team_id,g.away_team_id,
          o.state,o.scheduled_start,o.source_check_id FROM platform.events e
          JOIN nba.games g USING(event_id)
          JOIN LATERAL(SELECT * FROM platform.event_observations v WHERE v.event_id=e.event_id
             ORDER BY observed_at DESC,recorded_at DESC,observation_id DESC LIMIT 1)o ON true
          WHERE o.state='scheduled' AND o.scheduled_start BETWEEN %s AND %s
          AND NOT EXISTS(SELECT FROM platform.events child
             WHERE child.predecessor_event_id=e.event_id)
          ORDER BY o.scheduled_start,e.event_id LIMIT 1001""",
            (now, now + timedelta(days=7)),
        ).fetchall()
    if len(rows) > 1000:
        raise EvidenceError("Upcoming work budget exceeded")
    return list(rows)


def teams_needing_rosters(conn: psycopg.Connection[Any], now: datetime) -> list[dict[str, str]]:
    due = {
        (str(row[key]), row["season"])
        for row in work_list(conn, now)
        for key in ["home_team_id", "away_team_id"]
    }
    result = []
    for team, season in sorted(due):
        row = conn.execute(
            """SELECT EXISTS(SELECT FROM nba.roster_snapshots r JOIN platform.source_checks s
            ON s.check_id=r.source_check_id WHERE team_id=%s AND season=%s
            AND s.state='accepted' AND s.validated_at<=%s AND s.received_at>%s-interval '23 hours'
            AND (s.source_published_at IS NULL OR s.source_published_at>%s-interval '23 hours')
            AND (NOT(s.validation_summary ? 'source_generated_at') OR
              (s.validation_summary->>'source_generated_at')::timestamptz
                >%s-interval '23 hours'))""",
            (team, season, now, now, now, now),
        ).fetchone()
        assert row is not None
        fresh = row[0]
        if not fresh:
            result.append({"team_id": team, "season": season})
    return result


def persist_attempt(
    conn: psycopg.Connection[Any],
    store: PrivateArtifacts,
    runner: ProbeRunner,
    attempt: dict[str, Any],
    *,
    parser_version: str = PARSER,
) -> dict[str, Any] | None:
    if attempt.get("persisted") or attempt.get("requested_at") is None:
        return attempt.get("persisted")
    raw = None
    storage_failed = False
    if attempt.get("raw_path"):
        body = (runner.archive.root / attempt["raw_path"]).read_bytes()
        if digest(body) != attempt["raw_sha256"]:
            raise EvidenceError("Raw checksum changed")
        try:
            raw = retain(conn, store, body, kind="raw", format="json", manifest={})
        except ArtifactError:
            storage_failed = True
    good = attempt["outcome"] == "verified_sample" and not storage_failed
    summary = {
        "capability": attempt["capability"],
        "observation_id": attempt["observation_id"],
        "environment": attempt["environment"],
        "parser_version": parser_version,
        "request_url": attempt["request_url"],
        "raw_complete": attempt.get("raw_complete"),
        "reason_code": "accepted"
        if good
        else "storage_failure"
        if storage_failed
        else "access_denied"
        if attempt.get("reason") == "access_denied_or_html_challenge"
        else "source_validation_or_transport_failure",
        "request_hash": digest(
            encoded({"url": attempt["request_url"], "context": attempt["request_context"]})
        ),
        "source_generated_at": attempt.get("summary", {}).get("source_generated_at"),
    }
    if summary["source_generated_at"] is None:
        summary.pop("source_generated_at")
    check = register(
        conn,
        "source_checks",
        {
            "check_id": str(uuid5(NAMESPACE_URL, runner.run_id + attempt["observation_id"])),
            "run_id": runner.run_id,
            "source_id": attempt["source"],
            "adapter_version": parser_version,
            "requested_at": attempt["requested_at"],
            "received_at": attempt.get("received_at"),
            "validated_at": attempt.get("validated_at") if good else None,
            "source_published_at": attempt.get("source_publication_time"),
            "raw_artifact_id": raw["artifact_id"] if raw else None,
            "http_status": attempt.get("http_status"),
            "record_count": attempt.get("record_count"),
            "state": "storage_failure"
            if storage_failed
            else "accepted"
            if good
            else ("invalid" if attempt.get("received_at") else "transport_failure"),
            "validation_summary": summary,
        },
    )
    attempt["persisted"] = check
    return check


def collect(
    conn: psycopg.Connection[Any],
    store: PrivateArtifacts,
    runner: ProbeRunner,
    routes: list[dict[str, Any]],
    environment: str,
    *,
    rehearsal: bool = False,
) -> dict[str, Any]:
    if len(routes) > 100:
        raise EvidenceError("Route count exceeds bounded work policy")
    requests = [accepted_request(route, environment, rehearsal=rehearsal) for route in routes]
    if any(request.capability not in {"schedule", "status", "roster"} for request in requests):
        raise EvidenceError("Collection supports schedule/status/roster only")
    if not requests:
        raise EvidenceError("No accepted routes; source gate remains blocked")
    refuse_denied(conn, requests, rehearsal=rehearsal)
    run_id = runner.run_id
    register(
        conn,
        "runs",
        {
            "run_id": run_id,
            "operation": "collect",
            "domain": "nba",
            "environment": "rehearsal" if rehearsal else "production",
            "code_version": PARSER,
            "config_hash": digest(encoded(routes)),
        },
    )
    register(
        conn,
        "run_events",
        {
            "run_event_id": str(uuid4()),
            "run_id": run_id,
            "state": "started",
            "reason_code": None,
            "details": {},
        },
    )
    results: list[dict[str, Any]] = []
    incomplete = False

    def failed(reason: str) -> None:
        register(
            conn,
            "run_events",
            {
                "run_event_id": str(uuid4()),
                "run_id": run_id,
                "state": "incomplete",
                "reason_code": reason,
                "details": {
                    "counts": {"processed": len(results)},
                    "duration_ms": round((runner.clock.monotonic() - runner.started) * 1000),
                },
            },
        )

    for request in requests:
        report = runner.fetch(request, collection_validator)
        # Preserve all genuine attempts, not just the final retry result.
        for attempt in runner.observations:
            persist_attempt(conn, store, runner, attempt)
        current = report.get("persisted")
        if not current or current["state"] != "accepted":
            incomplete = True
            failed("source_unavailable")
            continue
        check = current
        try:
            if request.capability == "roster":
                summary = report["summary"]
                players = [{"player_id": str(p["player_id"])} for p in summary["records"]]
                results.append(
                    {
                        "roster_id": str(
                            save_roster(
                                conn,
                                store,
                                team_id=str(request.context["team_id"]),
                                season=request.context["season"],
                                source_check=check,
                                players=players,
                            )
                        )
                    }
                )
            else:
                results.extend(apply_game(conn, row, check) for row in report["summary"]["records"])
        except (psycopg.Error, EvidenceError):
            incomplete = True
            failed("transition_or_lifecycle_failed")
    register(
        conn,
        "run_events",
        {
            "run_event_id": str(uuid4()),
            "run_id": run_id,
            "state": "incomplete" if incomplete else "succeeded",
            "reason_code": "collection_incomplete" if incomplete else None,
            "details": {
                "counts": {"processed": len(results), "requests": runner.requests},
                "duration_ms": round((runner.clock.monotonic() - runner.started) * 1000),
            },
        },
    )
    return {
        "run_id": run_id,
        "state": "incomplete" if incomplete else "succeeded",
        "results": results,
        "requests": runner.requests,
        "seconds": runner.clock.monotonic() - runner.started,
        "production_ready": False,
    }


def main() -> int:
    import argparse

    from hoop.domains.nba.sources.policy import HTTPTransport, SystemClock
    from hoop.platform.artifacts import Session, Settings
    from hoop.platform.database import DatabaseError, connection, health
    from hoop.platform.local_artifacts import atomic_json

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=["collect", "work"])
    parser.add_argument("--config", type=Path, default=Path("configs/collection.json"))
    parser.add_argument("--environment", choices=["local", "github-actions"], required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--confirm-source-gates", action="store_true")
    args = parser.parse_args()
    result: dict[str, Any]
    try:
        config = json.loads(args.config.read_text())
        if (
            config.get("schema_version") != 1
            or config.get("upcoming_days") != 7
            or config.get("parser_version") != PARSER
        ):
            raise EvidenceError("Reviewed collection policy required")
        if args.operation == "collect":
            if not args.confirm_source_gates or not config["routes"]:
                raise EvidenceError("No accepted routes or source gates unconfirmed")
            for route in config["routes"]:
                accepted_request(route, args.environment, rehearsal=False)
        with connection() as conn:
            if health(conn)["role"] != "baseline_runtime":
                raise EvidenceError("Restricted runtime role required")
            clock = SystemClock()
            if args.operation == "work":
                result = {
                    "upcoming": work_list(conn, clock.now()),
                    "rosters_due": teams_needing_rosters(conn, clock.now()),
                }
            else:
                runner = ProbeRunner(
                    Archive(args.output / "source"),
                    HTTPTransport(),
                    clock,
                    Policy(**config["policy"]),
                    str(uuid4()),
                )
                result = collect(
                    conn,
                    PrivateArtifacts(Session(Settings.from_env())),
                    runner,
                    config["routes"],
                    args.environment,
                )
        atomic_json(args.output / "collection-report.json", json.loads(encoded(result)))
        print(json.dumps(result, default=str, sort_keys=True))
        return 0 if result.get("state", "succeeded") == "succeeded" else 1
    except (
        EvidenceError,
        ArtifactError,
        DatabaseError,
        psycopg.Error,
        ValueError,
        KeyError,
        OSError,
    ):
        result = {
            "state": "blocked",
            "reason_code": "collection_failed",
            "durable_audit_confirmed": False,
        }
        atomic_json(args.output / "collection-failure.json", result)
        print(json.dumps(result))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
