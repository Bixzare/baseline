"""Nightly/dispatcher adapters over shared tested source, ledger and report commands."""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import psycopg

from hoop.domains.nba.baselines.capture import capture_game
from hoop.domains.nba.baselines.model import prepare
from hoop.domains.nba.collection import collect, teams_needing_rosters, work_list
from hoop.domains.nba.evaluation import POLICY as EVALUATION_POLICY
from hoop.domains.nba.evaluation import capture as capture_report
from hoop.domains.nba.evaluation import periods, persist
from hoop.domains.nba.outcomes import reconcile
from hoop.domains.nba.publication import publish_player
from hoop.domains.nba.sources.policy import HTTPTransport, Policy, ProbeRunner, SystemClock
from hoop.platform.artifacts import ArtifactError, PrivateArtifacts, Session, Settings
from hoop.platform.database import DatabaseError, connection, health
from hoop.platform.evidence import EvidenceError
from hoop.platform.ledger.publication import confirm, status
from hoop.platform.ledger.registry import active_bundle
from hoop.platform.local_artifacts import atomic_json
from hoop.platform.operations import db_now, production_enabled, run_pipeline
from hoop.platform.prepared import encoded, retain_prepared
from hoop.platform.provenance import Archive, digest

ROOT = Path(__file__).parents[4]


def due(now: datetime, start: datetime) -> bool:
    if now.tzinfo is None or start.tzinfo is None:
        raise EvidenceError("Aware deadline times required")
    return start - timedelta(minutes=120) <= now < start - timedelta(minutes=15)


class SourceBudget:
    def __init__(
        self,
        root: Path,
        environment: str,
        config: dict[str, Any],
        *,
        transport: Any = None,
        clock: Any = None,
    ):
        self.root = root
        self.environment = environment
        self.config = config
        self.clock = clock or SystemClock()
        self.transport = transport or HTTPTransport()
        self.started = self.clock.monotonic()
        self.requests = 0
        self.previous: ProbeRunner | None = None

    def runner(self) -> ProbeRunner:
        if self.previous:
            self.requests += self.previous.requests
        remaining = self.config["max_seconds"] - (self.clock.monotonic() - self.started)
        if remaining <= 0 or self.requests >= self.config["max_requests"]:
            raise EvidenceError("Shared operation request/time budget exhausted")
        runner = ProbeRunner(
            Archive(self.root / str(uuid4())),
            self.transport,
            self.clock,
            Policy(
                max_requests=self.config["max_requests"] - self.requests,
                max_seconds=min(180, remaining),
            ),
            str(uuid4()),
        )
        if self.previous:
            runner.last_end = self.previous.last_end
            runner.blocked = set(self.previous.blocked)
        self.previous = runner
        return runner


def dispatcher(
    conn: psycopg.Connection[Any],
    store: PrivateArtifacts,
    budget: SourceBudget,
    sources: dict[str, Any],
    finals: dict[str, Any],
    *,
    rehearsal: bool = False,
) -> dict[str, Any]:
    now = db_now(conn)
    work = [r for r in work_list(conn, now) if due(now, r["scheduled_start"])]
    failures = 0
    published = confirmed = 0
    for event in work:
        existing = conn.execute(
            "SELECT batch_id FROM platform.forecast_batches WHERE event_id=%s AND "
            "family='player_recent_appearance_mean'",
            (event["event_id"],),
        ).fetchone()
        try:
            if existing:
                result = status(conn, existing[0])
                if result["state"] == "stored_unverified":
                    # Refresh safety evidence, but never regenerate this batch.
                    routes = [
                        r for r in sources["routes"] if r["capability"] in {"schedule", "status"}
                    ]
                    refreshed = collect(
                        conn,
                        store,
                        budget.runner(),
                        routes,
                        budget.environment,
                        rehearsal=rehearsal,
                    )
                    if refreshed["state"] != "succeeded":
                        raise EvidenceError(
                            "Commit confirmation requires successful safety refresh"
                        )
                    result = confirm(conn, existing[0])
                confirmed += result["state"] == "timely_confirmed"
                failures += result["state"] != "timely_confirmed"
                continue
            routes = [r for r in sources["routes"] if r["capability"] in {"schedule", "status"}]
            refreshed = collect(
                conn, store, budget.runner(), routes, budget.environment, rehearsal=rehearsal
            )
            if refreshed["state"] != "succeeded":
                raise EvidenceError("Essential source refresh incomplete")
            needed = teams_needing_rosters(conn, now)
            teams = {
                r["team_id"]
                for r in needed
                if r["team_id"] in {event["home_team_id"], event["away_team_id"]}
            }
            rosters = [
                r
                for r in sources["routes"]
                if r["capability"] == "roster" and str(r["context"].get("team_id")) in teams
            ]
            if teams:
                if len({str(r["context"]["team_id"]) for r in rosters}) != len(teams):
                    raise EvidenceError("Required local-only or missing roster route")
                if (
                    collect(
                        conn,
                        store,
                        budget.runner(),
                        rosters,
                        budget.environment,
                        rehearsal=rehearsal,
                    )["state"]
                    != "succeeded"
                ):
                    raise EvidenceError("Roster refresh incomplete")
            prior = reconcile(
                conn, store, budget.runner(), finals, budget.environment, rehearsal=rehearsal
            )
            if prior["state"] != "succeeded":
                raise EvidenceError("Prior final reconciliation incomplete")
            cutoff = db_now(conn)
            inputs = capture_game(
                conn,
                store,
                event["event_id"],
                cutoff,
                environment="rehearsal" if rehearsal else "production",
            )
            generated = db_now(conn)
            prepared = prepare(inputs, generated_at=generated)
            retained = retain_prepared(conn, store, prepared)
            bundle = active_bundle(conn, "nba", "player_recent_appearance_mean")
            if bundle is None:
                raise EvidenceError("Active baseline registration missing")
            result = publish_player(conn, store, retained, UUID(str(bundle["bundle_id"])))
            published += result["state"] == "timely_confirmed"
        except (EvidenceError, ArtifactError, psycopg.Error, ValueError, KeyError):
            failures += 1
    return {
        "state": "incomplete" if failures else "succeeded",
        "counts": {
            "due": len(work),
            "published": published,
            "confirmed": confirmed,
            "failed": failures,
        },
        "reason_code": "due_games_failed" if failures else "no_due_games" if not work else None,
    }


def stages(
    conn: psycopg.Connection[Any],
    store: PrivateArtifacts,
    budget: SourceBudget,
    operation: str,
    *,
    rehearsal: bool = False,
    source_config: dict[str, Any] | None = None,
    final_config: dict[str, Any] | None = None,
) -> list[Any]:
    sources = source_config or json.loads((ROOT / "configs/collection.json").read_text())
    finals = final_config or json.loads((ROOT / "configs/outcomes.json").read_text())
    sources = {
        **sources,
        "routes": [
            r
            for r in sources["routes"]
            if r.get("evidence", {}).get("environment") == budget.environment
        ],
    }
    finals = {
        **finals,
        "routes": [
            r
            for r in finals["routes"]
            if r.get("evidence", {}).get("environment") == budget.environment
        ],
    }

    def discover() -> dict[str, Any]:
        now = db_now(conn)
        fresh_row = conn.execute(
            """SELECT EXISTS(SELECT FROM platform.source_checks s
           JOIN platform.runs r USING(run_id) WHERE s.state='accepted'
           AND s.validation_summary->>'capability'='schedule'
           AND s.received_at>=%s-interval '24 hours' AND s.validated_at<=%s
           AND r.environment=%s)""",
            (now, now, "rehearsal" if rehearsal else "production"),
        ).fetchone()
        assert fresh_row is not None
        fresh = fresh_row[0]
        return (
            {"state": "succeeded", "counts": {"requests": 0}, "reason_code": "inventory_reused"}
            if fresh
            else refresh("schedule")
        )

    def refresh(capability: str) -> dict[str, Any]:
        routes = [r for r in sources["routes"] if r["capability"] == capability]
        if capability == "roster":
            now = db_now(conn)
            needed = {r["team_id"] for r in teams_needing_rosters(conn, now)}
            routes = [r for r in routes if str(r["context"].get("team_id")) in needed]
            if not needed:
                return {"state": "succeeded", "counts": {"renewals": 0}}
            if {str(r["context"]["team_id"]) for r in routes} != needed:
                raise EvidenceError("Missing accepted roster routes")
        return collect(
            conn, store, budget.runner(), routes, budget.environment, rehearsal=rehearsal
        )

    def reports() -> dict[str, Any]:
        cutoff = db_now(conn)
        policy = json.loads(EVALUATION_POLICY.read_text())
        for start, end in periods(cutoff, policy).values():
            persist(
                conn,
                store,
                capture_report(
                    conn,
                    store,
                    start,
                    end,
                    cutoff,
                    kind="rehearsal" if rehearsal else "live",
                    policy=policy,
                ),
            )
        return {"state": "succeeded", "counts": {"reports": 3}}

    if operation == "nightly":
        return [
            (
                "reconcile",
                lambda: reconcile(
                    conn, store, budget.runner(), finals, budget.environment, rehearsal=rehearsal
                ),
            ),
            ("schedule", lambda: refresh("schedule")),
            ("rosters", lambda: refresh("roster")),
            ("reports", reports),
        ]
    return [
        ("discover", discover),
        (
            "due_games",
            lambda: dispatcher(conn, store, budget, sources, finals, rehearsal=rehearsal),
        ),
    ]


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=["nightly", "dispatcher"])
    parser.add_argument("--mode", choices=["production", "read-only"], default="read-only")
    parser.add_argument("--environment", choices=["local", "github-actions"], required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    config = json.loads((ROOT / "configs/operations.json").read_text())
    if config.get("schema_version") != 1 or config.get("domain") != "nba":
        raise EvidenceError("Unsupported operation configuration")
    config["domain_code_hash"] = digest(Path(__file__).read_text().encode())
    try:
        if args.mode == "production" and not production_enabled(config):
            result = {"state": "disabled", "production_heartbeat": False}
        else:
            with connection() as conn:
                identity = health(conn)
                if identity["role"] != "baseline_runtime":
                    raise EvidenceError("Restricted operation role required")
                if args.mode == "read-only":
                    result = {
                        "state": "read_only",
                        "database": identity,
                        "production_heartbeat": False,
                    }
                else:
                    store = PrivateArtifacts(Session(Settings.from_env()))
                    budget = SourceBudget(args.output / "sources", args.environment, config)
                    result = run_pipeline(
                        conn, args.operation, stages(conn, store, budget, args.operation), config
                    )
        atomic_json(args.output / "operation.json", json.loads(encoded(result)))
        print(json.dumps(result, default=str, sort_keys=True))
        return 0 if result["state"] in {"succeeded", "disabled", "read_only"} else 1
    except (
        EvidenceError,
        ArtifactError,
        DatabaseError,
        psycopg.Error,
        ValueError,
        KeyError,
        OSError,
    ):
        result = {"state": "failed", "reason_code": "operation_failed", "durable_completion": False}
        atomic_json(args.output / "operation.json", result)
        print(json.dumps(result))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
