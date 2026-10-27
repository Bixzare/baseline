"""Actual stage adapters on disposable Postgres and invented HTTP responses only."""

import json
import os
import sys
import time
from datetime import timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any
from uuid import uuid4
from zoneinfo import ZoneInfo

import psycopg
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict, make_conninfo

from hoop.domains.nba.collection import PARSER as SOURCE_PARSER
from hoop.domains.nba.operations import SourceBudget, stages
from hoop.domains.nba.outcomes import PARSER as FINAL_PARSER
from hoop.domains.nba.sources.policy import Response
from hoop.domains.nba.sources.probe import live_url
from hoop.platform.database import apply, provision_runtime
from hoop.platform.operations import run_pipeline
from hoop.platform.prepared import encoded
from hoop.platform.provenance import digest
from tests.fixtures.publication import publication_fixture

ROOT = Path(__file__).resolve().parents[1]


def route(
    capability: str, url: str, context: dict[str, Any], environment: str, parser: str
) -> dict[str, Any]:
    identity = digest(
        encoded(
            {
                "capability": capability,
                "url": url,
                "context": context,
                "environment": environment,
                "parser_version": parser,
            }
        )
    )
    return {
        "status": "accepted",
        "capability": capability,
        "url": url,
        "context": context,
        "parser_version": parser,
        "request_hash": identity,
        "owner_acceptance_id": "invented-fixture",
        "evidence": {
            "outcome": "verified_sample",
            "kind": "synthetic_fixture",
            "environment": environment,
            "observation_id": "invented",
            "request_hash": identity,
        },
    }


def run(operation: str, *, environment: str = "local", fail_stage: bool = False) -> dict[str, Any]:
    started = time.monotonic()
    configured = os.environ.get("BASELINE_TEST_DSN", "")
    if conninfo_to_dict(configured).get("host") not in {
        "localhost",
        "127.0.0.1",
        "::1",
        "postgres",
    }:
        raise ValueError("Explicit disposable local test service required")
    name = "baseline_test_ops_" + uuid4().hex
    (ROOT / ".cache").mkdir(exist_ok=True)
    with psycopg.connect(configured, autocommit=True) as admin:
        admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
        try:
            with (
                psycopg.connect(make_conninfo(configured, dbname=name), autocommit=True) as owner,
                TemporaryDirectory(dir=ROOT / ".cache") as folder,
            ):
                owner.execute(
                    (ROOT / "tests/fixtures/postgres/provider.sql").read_text(), prepare=False
                )
                apply(owner, ROOT / "migrations")
                fixture = publication_fixture(owner, Path(folder) / "seed")
                start = fixture["now"] + timedelta(hours=2)
                game = {
                    "gameId": "0022600001",
                    "gameStatus": 1,
                    "gameStatusText": "Scheduled",
                    "gameTimeUTC": start.isoformat(),
                    "gameDateTimeUTC": start.isoformat(),
                    "homeTeam": {"teamId": 101},
                    "awayTeam": {"teamId": 102},
                }
                day = start.astimezone(ZoneInfo("America/New_York")).date()
                payload = {
                    "leagueSchedule": {
                        "leagueId": "00",
                        "seasonYear": "2026-27",
                        "gameDates": [{"gameDate": day.strftime("%m/%d/%Y"), "games": [game]}],
                    }
                }
                # Initial full inventory is an explicitly invented accepted fixture.
                fixture["source"]("schedule", payload)
                context = {"season": "2026-27", "opening_date": day.isoformat()}
                source_routes = [
                    route(
                        "schedule",
                        "https://cdn.nba.com/fixture/schedule.json",
                        context,
                        environment,
                        SOURCE_PARSER,
                    )
                ]
                finals = {
                    "dnp_semantics": "unknown_until_accepted",
                    "routes": [
                        route(
                            "final",
                            live_url("final", "{game_id}"),
                            {
                                "game_id": "{game_id}",
                                "season": "{season}",
                                "expected_team_ids": "{team_ids}",
                                "allowed_seasons": ["2026-27"],
                            },
                            environment,
                            FINAL_PARSER,
                        )
                    ],
                }

                class FixtureHTTP:
                    requests = 0

                    def get(self, url: str, timeout: float) -> Response:
                        self.requests += 1
                        assert url == source_routes[0]["url"]
                        return (
                            Response(403, b"denied", {})
                            if fail_stage
                            else Response(200, encoded(payload), {})
                        )

                transport = FixtureHTTP()
                provision_runtime(owner, "synthetic_fixture_password_only")
                with psycopg.connect(
                    make_conninfo(
                        configured,
                        dbname=name,
                        user="baseline_runtime",
                        password="synthetic_fixture_password_only",
                    ),
                    autocommit=True,
                ) as conn:
                    config = json.loads((ROOT / "configs/operations.json").read_text())
                    budget = SourceBudget(
                        Path(folder) / "sources",
                        environment,
                        config,
                        transport=transport,
                        conn=conn,
                        rehearsal=True,
                    )
                    callbacks = stages(
                        conn,
                        fixture["store"],
                        budget,
                        operation,
                        rehearsal=True,
                        source_config={"routes": source_routes},
                        final_config=finals,
                    )
                    result = run_pipeline(conn, operation, callbacks, config, rehearsal=True)
                    result.update(
                        evidence="synthetic_fixture",
                        provider_access_verified=False,
                        requests=transport.requests,
                        wall_seconds=round(time.monotonic() - started, 3),
                        forecasts=conn.execute(
                            "SELECT count(*) FROM platform.forecast_batches"
                        ).fetchone()[0],
                        receipts=conn.execute(
                            "SELECT count(*) FROM platform.publication_receipts"
                        ).fetchone()[0],
                        reports=conn.execute(
                            "SELECT count(*) FROM platform.evaluation_reports"
                        ).fetchone()[0],
                    )
                    if sys.platform.startswith("linux"):
                        import resource

                        result["peak_memory_bytes"] = (
                            resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
                        )
                    else:
                        result["peak_memory_bytes"] = None
                    return result
        finally:
            assert name.startswith("baseline_test_ops_") and len(name) == 50
            admin.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(name)))


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--operation", choices=["nightly", "dispatcher"], required=True)
    parser.add_argument("--environment", choices=["local", "github-actions"], default="local")
    parser.add_argument("--fail-stage", action="store_true")
    args = parser.parse_args()
    result = run(args.operation, environment=args.environment, fail_stage=args.fail_stage)
    print(json.dumps(result, default=str, sort_keys=True))
    raise SystemExit(0 if result["state"] == "succeeded" else 1)
