"""Partial finals, explicit nonparticipation and versioned cohort reconciliation."""

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

import psycopg

from hoop.domains.nba.collection import accepted_request, persist_attempt
from hoop.domains.nba.outcomes.parsing import PARSER, final_validator
from hoop.domains.nba.outcomes.persistence import ingest_final, pending_work
from hoop.domains.nba.sources.policy import ProbeRequest, ProbeRunner
from hoop.domains.nba.sources.runtime import refuse_denied
from hoop.platform.artifacts import ArtifactError, PrivateArtifacts
from hoop.platform.evidence import EvidenceError, register
from hoop.platform.prepared import encoded
from hoop.platform.provenance import digest


def final_request(
    route: dict[str, Any], event: dict[str, Any], environment: str, *, rehearsal: bool
) -> ProbeRequest:
    from hoop.domains.nba.sources.probe import live_url

    accepted = accepted_request(route, environment, rehearsal=rehearsal, parser_version=PARSER)
    if accepted.capability != "final":
        raise EvidenceError("Final capability required")
    context = accepted.context
    if "{game_id}" in accepted.url:
        if (
            accepted.url != live_url("final", "{game_id}")
            or context.get("game_id") != "{game_id}"
            or context.get("season") != "{season}"
            or context.get("expected_team_ids") != "{team_ids}"
            or event["season"] not in context.get("allowed_seasons", [])
        ):
            raise EvidenceError(
                "Only a reviewed NBA boxscore template may use saved occurrence IDs"
            )
        context = {
            **context,
            "game_id": event["source_event_id"],
            "season": event["season"],
            "expected_team_ids": [event["home_team_id"], event["away_team_id"]],
        }
        url = accepted.url.replace("{game_id}", event["source_event_id"])
    else:
        url = accepted.url
    if (
        context.get("game_id") != event["source_event_id"]
        or context.get("season") != event["season"]
        or sorted(map(str, context.get("expected_team_ids", [])))
        != sorted([event["home_team_id"], event["away_team_id"]])
    ):
        raise EvidenceError("Accepted final route conflicts with saved occurrence")
    return ProbeRequest("final", url, environment, context)


def reconcile(
    conn: psycopg.Connection[Any],
    store: PrivateArtifacts,
    runner: ProbeRunner,
    config: dict[str, Any],
    environment: str,
    *,
    rehearsal: bool = False,
    event_ids: list[UUID] | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> dict[str, Any]:
    routes = config.get("routes", [])
    if not routes or len(routes) > 100:
        raise EvidenceError("Accepted bounded final routes required")
    admitted = [
        accepted_request(route, environment, rehearsal=rehearsal, parser_version=PARSER)
        for route in routes
    ]
    refuse_denied(conn, admitted, rehearsal=rehearsal)
    work = pending_work(
        conn, runner.clock.now(), event_ids=event_ids, date_from=date_from, date_to=date_to
    )
    run_id = runner.run_id
    register(
        conn,
        "runs",
        {
            "run_id": run_id,
            "operation": "reconcile",
            "domain": "nba",
            "environment": "rehearsal" if rehearsal else "production",
            "code_version": PARSER,
            "config_hash": digest(encoded(config)),
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
    results = []
    failed = 0
    for event in work:
        candidates = [
            route
            for route in routes
            if "{game_id}" in route["url"]
            or route["context"].get("game_id") == event["source_event_id"]
        ]
        if len(candidates) != 1:
            failed += 1
            continue
        try:
            request = final_request(candidates[0], event, environment, rehearsal=rehearsal)
            if request.context.get("dnp_semantics", "unknown_until_accepted") != config.get(
                "dnp_semantics", "unknown_until_accepted"
            ):
                raise EvidenceError("Final DNP configuration differs from accepted semantics")
            report = runner.fetch(request, final_validator)
            for attempt in runner.observations:
                persist_attempt(conn, store, runner, attempt, parser_version=PARSER)
            check = report.get("persisted")
            if not check or check["state"] != "accepted":
                failed += 1
                continue
            result = ingest_final(
                conn,
                store,
                event["event_id"],
                check,
                report["summary"]["normalized"],
                config=config,
            )
            results.append({"event_id": str(event["event_id"]), **result})
        except (ArtifactError, EvidenceError, psycopg.Error, ValueError, KeyError):
            failed += 1
    register(
        conn,
        "run_events",
        {
            "run_event_id": str(uuid4()),
            "run_id": run_id,
            "state": "incomplete" if failed else "succeeded",
            "reason_code": "reconciliation_incomplete" if failed else None,
            "details": {
                "counts": {
                    "processed": len(results),
                    "failed": failed,
                    "requests": runner.requests,
                },
                "duration_ms": round((runner.clock.monotonic() - runner.started) * 1000),
            },
        },
    )
    return {
        "run_id": run_id,
        "state": "incomplete" if failed else "succeeded",
        "results": results,
        "failed": failed,
        "requests": runner.requests,
        "seconds": runner.clock.monotonic() - runner.started,
        "production_ready": False,
    }
