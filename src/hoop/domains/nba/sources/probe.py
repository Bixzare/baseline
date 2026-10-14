"""Run a small repeatable capability assessment, not a production collector."""

import argparse
import json
import os
import subprocess
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from uuid import uuid4

from hoop.domains.nba.sources.policy import (
    HTTPTransport,
    Policy,
    ProbeRequest,
    ProbeRunner,
    SystemClock,
)
from hoop.domains.nba.sources.validate import EASTERN, identity_joins, validate
from hoop.platform.provenance import Archive, digest, parse_time, utc


def live_url(kind: str, game_id: str | None = None) -> str:
    from nba_api.live.nba.endpoints.boxscore import BoxScore
    from nba_api.live.nba.endpoints.scoreboard import ScoreBoard
    from nba_api.live.nba.library.http import NBALiveHTTP

    endpoint = (
        ScoreBoard.endpoint_url
        if kind == "status"
        else BoxScore.endpoint_url.format(game_id=game_id)
    )
    return str(NBALiveHTTP.base_url.format(endpoint=endpoint))


def local_requests(config: dict[str, Any]) -> list[ProbeRequest]:
    from nba_api.stats.endpoints.commonteamroster import CommonTeamRoster
    from nba_api.stats.endpoints.leaguegamelog import LeagueGameLog
    from nba_api.stats.library.http import NBAStatsHTTP

    requests = []
    for side in ["P", "T"]:
        start = datetime.fromisoformat(config["history_date_from"]).strftime("%m/%d/%Y")
        end = datetime.fromisoformat(config["history_date_to"]).strftime("%m/%d/%Y")
        endpoint = LeagueGameLog(
            season=config["history_season"],
            player_or_team_abbreviation=side,
            season_type_all_star="Regular Season",
            date_from_nullable=start,
            date_to_nullable=end,
            get_request=False,
        )
        url = (
            NBAStatsHTTP.base_url.format(endpoint=endpoint.endpoint)
            + "?"
            + urlencode(endpoint.parameters)
        )
        requests.append(
            ProbeRequest(
                "history",
                url,
                "local",
                {
                    "season": config["history_season"],
                    "side": side,
                    "date_from": config["history_date_from"],
                    "date_to": config["history_date_to"],
                },
            )
        )
    for team in config["team_ids"]:
        roster = CommonTeamRoster(team_id=team, season=config["season"], get_request=False)
        url = (
            NBAStatsHTTP.base_url.format(endpoint=roster.endpoint)
            + "?"
            + urlencode(roster.parameters)
        )
        requests.append(
            ProbeRequest("roster", url, "local", {"season": config["season"], "team_id": team})
        )
    return requests


def run_pass(
    runner: ProbeRunner, config: dict[str, Any], environment: str, *, repeat: bool = False
) -> None:
    previous_successes = {
        row["request_url"] for row in runner.observations if row["outcome"] == "verified_sample"
    }

    def fetch(request: ProbeRequest) -> dict[str, Any] | None:
        if repeat and request.url not in previous_successes:
            return None
        return runner.fetch(request, validate)

    context = {"season": config["season"], "opening_date": config["opening_date"]}
    scheduled = fetch(ProbeRequest("schedule", config["schedule_url"], environment, context))
    records = []
    if scheduled and scheduled["outcome"] == "verified_sample":
        records = list(scheduled["summary"]["records"])
        source_day = runner.clock.now().astimezone(EASTERN).date()
        # Unknown starts cannot establish genuine no-game evidence.
        if not any(row["start_utc"] is None for row in records):
            context["expected_game_ids"] = [
                row["game_id"]
                for row in records
                if parse_time(row["start_utc"]).astimezone(EASTERN).date() == source_day
            ]
            context["schedule_day_verified"] = (
                source_day.isoformat() in scheduled["summary"]["explicit_empty_days"]
            )
    board = fetch(ProbeRequest("status", live_url("status"), environment, context))
    if board and board["outcome"] == "verified_sample":
        records += board["summary"]["records"]
    finals = [
        row
        for row in records
        if row["status"] == 3
        and row["start_utc"] is not None
        and parse_time(row["start_utc"]) < runner.clock.now()
    ]
    if finals:
        game = max(finals, key=lambda row: str(row["start_utc"]))
        fetch(
            ProbeRequest(
                "final",
                live_url("final", game["game_id"]),
                environment,
                {
                    "game_id": game["game_id"],
                    "season": config["season"],
                    "expected_team_ids": [game["home_team_id"], game["away_team_id"]],
                },
            )
        )
    elif not repeat:
        runner.save(
            ProbeRequest("final", live_url("status"), environment, context),
            outcome="unverified",
            reason="no_completed_game_id_in_retained_validated_sources",
        )
    if environment == "local":
        for request in local_requests(config):
            fetch(request)


def assessment(runner: ProbeRunner, environment: str) -> dict[str, Any]:
    matrix = {}
    for capability in ["history", "schedule", "status", "final", "roster", "availability"]:
        rows = [row for row in runner.observations if row["capability"] == capability]
        valid = [row for row in rows if row["outcome"] == "verified_sample"]
        outcome = (
            "verified_sample"
            if valid
            else "failed"
            if any(row["outcome"] == "failed" for row in rows)
            else "unverified"
        )
        matrix[capability] = {
            "outcome": outcome,
            "successful_observations": len(valid),
            "observation_ids": [row["observation_id"] for row in rows],
            "reasons": sorted({str(row["reason"]) for row in rows if row["reason"]}),
            "later_failure": bool(valid and rows[-1]["outcome"] != "verified_sample"),
        }
        if not rows:
            matrix[capability]["reasons"] = [
                "no_validated_adapter_selected"
                if capability in {"roster", "availability"} and environment != "local"
                else "local_machine_evidence_required"
            ]
    return {
        "capabilities": matrix,
        "identity_joins": identity_joins(runner.observations),
        "requests_used": runner.requests,
        "elapsed_seconds": runner.clock.monotonic() - runner.started,
        "availability_recommendation": "Recommend injury deferral; availability stays unknown",
        "source_acceptance": "Owner review required; Phase 0 remains incomplete",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--environment", choices=["local", "github-actions", "cloud-development"])
    parser.add_argument("--config", type=Path)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--confirm-local-machine", action="store_true")
    parser.add_argument("--verify-archive", action="store_true")
    parser.add_argument("--run-url")
    args = parser.parse_args()
    if args.verify_archive:
        count = Archive(args.archive).verify()
        print(f"Verified {count} retained observations and their raw-body checksums")
        return 0
    if args.environment is None or args.config is None:
        parser.error("--environment and --config are required for live probes")
    if args.environment == "local" and (
        not args.confirm_local_machine
        or os.environ.get("GITHUB_ACTIONS") == "true"
        or "CODEX_PROXY_CERT" in os.environ
    ):
        parser.error(
            "Local stats probes require an actual local machine; cloud execution is forbidden"
        )
    if args.environment == "github-actions" and os.environ.get("GITHUB_ACTIONS") != "true":
        parser.error("github-actions evidence must come from an actual Actions job")
    # Start a new directory even when refreshing an existing archive parent.
    run_id = uuid4().hex
    root = args.archive / run_id
    archive = Archive(root)
    config_bytes = args.config.read_bytes()
    config = json.loads(config_bytes)
    runner = ProbeRunner(
        archive, HTTPTransport(), SystemClock(), Policy(**config["policy"]), run_id
    )
    identity = {
        "run_id": run_id,
        "environment": args.environment,
        "run_url": args.run_url,
        "code_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "dependency_lock_sha256": digest(Path("uv.lock").read_bytes()),
        "nba_api_version": version("nba_api"),
        "config_sha256": digest(config_bytes),
        "config_version": config["version"],
        "config": config,
        "started_at": utc(datetime.now(UTC)),
    }
    (root / "identity.json").write_text(json.dumps(identity, indent=2))
    run_pass(runner, config, args.environment)
    run_pass(runner, config, args.environment, repeat=True)
    report = assessment(runner, args.environment)
    (root / "assessment.json").write_text(json.dumps(report, indent=2))
    archive.verify()
    print(json.dumps({"archive": str(root), **report}, indent=2))
    required = ["schedule", "status", "final"] + (
        ["history", "roster"] if args.environment == "local" else []
    )
    return (
        0
        if all(
            report["capabilities"][cap]["outcome"] == "verified_sample"
            and not report["capabilities"][cap]["later_failure"]
            for cap in required
        )
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(main())
