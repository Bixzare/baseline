"""Plan a compact seed before any network or database writes."""

import csv
import json
import time
from collections import Counter, defaultdict
from collections.abc import Callable
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

import psycopg
import pyarrow as pa
import pyarrow.parquet as pq

from hoop.domains.nba.history import lineage
from hoop.domains.nba.history import quarantine as quarantine_policy
from hoop.domains.nba.history.lineage import retain_repairs
from hoop.domains.nba.history.raw import verify_raw_archives
from hoop.platform import raw_archives as raw_codec
from hoop.platform.artifacts import MAX_BYTES, PrivateArtifacts, retain
from hoop.platform.evidence import EvidenceError, register
from hoop.platform.local_artifacts import LocalArtifacts, atomic_json, checksum
from hoop.platform.provenance import digest, parse_time
from hoop.platform.records import immutable_insert

POLICY = "compact-seed-v3"


def stable_id(*parts: str) -> UUID:
    return uuid5(NAMESPACE_URL, "baseline:" + json.dumps(parts, separators=(",", ":")))


def recent_rows(
    rows: list[dict[str, Any]], subject: str, blockers: list[str]
) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if row["competition"] == "regular" and row["season"] == "2025-26":
            groups[row[subject]].append(row)
    chosen = []
    for values in groups.values():
        values.sort(key=lambda row: row["game_date"], reverse=True)
        selected = values[:10]
        # A source date is an ordered calendar key, not a fabricated start.
        if len({row["game_date"] for row in selected}) != len(selected) or (
            len(values) > 10 and values[9]["game_date"] == values[10]["game_date"]
        ):
            blockers.append("ambiguous_source_date_order")
        chosen.extend(selected)
    return chosen


def plan_seed(
    report: dict[str, Any],
    archive: Path,
    source_manifest: dict[str, Any],
    acceptance: dict[str, Any] | None = None,
    observations: dict[str, dict[str, str]] | None = None,
    raw_archives: dict[str, Any] | None = None,
) -> dict[str, Any]:
    store = LocalArtifacts(archive)
    if report["season"] != "2025-26":
        raise EvidenceError("Only the reviewed launch seed season is supported")
    stored = json.loads(store.verify(report["manifest_artifact"]).read_text())
    if any(report.get(key) != value for key, value in stored.items()):
        raise EvidenceError("Seed report differs from its immutable manifest")
    for item in report["artifacts"]:
        store.verify(item)
    raw = {
        name: next(item for item in report["artifacts"] if item["sha256"] == sha)
        for name, sha in report["input_identity"]["files"].items()
    }
    if (
        source_manifest["files"] != report["input_identity"]["files"]
        or source_manifest["source_id"] != report["source_id"]
        or source_manifest["dataset_version"] != report["dataset_version"]
    ):
        raise EvidenceError("Original source provenance differs from normalized seed")
    if parse_time(source_manifest["collected_at"]) > parse_time(report["validated_at"]):
        raise EvidenceError("Invalid original source chronology")
    blockers = []
    observations = observations or {}
    if set(observations) != set(raw):
        blockers.append("original_request_observations_missing")
    else:
        for name, item in observations.items():
            if item.get("sha256") != raw[name]["sha256"] or not (
                parse_time(item["requested_at"])
                <= parse_time(item["received_at"])
                <= parse_time(report["validated_at"])
            ):
                raise EvidenceError("Original request observation mismatch")
    approved = acceptance or {}
    review_matches_seed = (
        approved.get("manifest_sha256") == report["manifest_artifact"]["sha256"]
        and approved.get("parser_version") == report["parser_version"]
    )
    if not review_matches_seed or approved.get("kind") not in {"owner_review", "synthetic_fixture"}:
        blockers.append("seed_acceptance_missing")
    if (
        not review_matches_seed
        or approved.get("kind")
        not in {"owner_review", "synthetic_fixture", "owner_calendar_review"}
        or approved.get("calendar_convention") != "source_calendar_verified"
    ):
        blockers.append("calendar_convention_unverified")
    if report["coverage"]["status"] != "matched_declared_inventory":
        blockers.append("game_coverage_unverified")
    if raw_archives is not None:
        verify_raw_archives(raw_archives, report, raw, store)
    if raw_archives is None and any(item["byte_count"] > MAX_BYTES for item in raw.values()):
        blockers.append("original_raw_exceeds_verified_upload_limit")
    players = pq.read_table(store.verify(report["normalized"]["players"])).to_pylist()
    teams = pq.read_table(store.verify(report["normalized"]["teams"])).to_pylist()

    chosen_players = recent_rows(
        [row for row in players if row["participation"] == "played"], "player_id", blockers
    )
    quarantine_review = quarantine_policy.compact_review(report, chosen_players, teams, approved)
    if report["quarantine"] and not quarantine_review["review_accepted"]:
        blockers.append("seed_quarantine_unresolved")
    chosen_teams = recent_rows(teams, "team_id", blockers)
    game_ids = {row["game_id"] for row in chosen_players + chosen_teams}
    supporting = [row for row in teams if row["game_id"] in game_ids]
    games = []
    for gid in sorted(game_ids):
        sides = [row for row in supporting if row["game_id"] == gid]
        homes = [row for row in sides if row["home"]]
        aways = [row for row in sides if not row["home"]]
        if len(homes) != 1 or len(aways) != 1:
            blockers.append("supporting_team_sides_missing")
            continue
        home, away = homes[0], aways[0]
        if (
            home["opponent_team_id"] != away["team_id"]
            or home["points_for"] != away["points_against"]
            or away["points_for"] != home["points_against"]
            or home["game_date"] != away["game_date"]
        ):
            blockers.append("supporting_team_sides_conflict")
            continue
        games.append(
            {
                "game_id": gid,
                "home": home["team_id"],
                "away": away["team_id"],
                "game_date": home["game_date"],
                "season": home["season"],
            }
        )
    plan = {
        "policy": POLICY,
        "importer_sha256": checksum(Path(__file__)),
        "seed_unit": report["unit_id"],
        "seed_manifest": report["manifest_artifact"],
        "acceptance": approved,
        "source_manifest": source_manifest,
        "observations": observations,
        "validated_at": report["validated_at"],
        "source_normalized": report["normalized"],
        "quarantine_review": quarantine_review,
        "quarantine_policy_sha256": checksum(Path(quarantine_policy.__file__)),
        "repair_lineage_implementation_sha256": checksum(Path(lineage.__file__)),
        "repair_inputs": list(
            {
                a["sha256"]: a
                for a in report["artifacts"]
                if a["kind"] in {"repair_evidence", "repair_overlay"}
            }.values()
        ),
        "raw": raw,
        "raw_archives": raw_archives,
        "raw_archive_implementation_sha256": checksum(Path(raw_codec.__file__)),
        "players": chosen_players,
        "teams": supporting,
        "games": games,
        "blockers": sorted(set(blockers)),
        "counts": {
            "players": len(chosen_players),
            "teams": len(supporting),
            "games": len(games),
            "short_player_histories": sum(
                n < 10 for n in Counter(row["player_id"] for row in chosen_players).values()
            ),
        },
        "required_raw_bytes": sum(item["byte_count"] for item in raw.values()),
        "original_raw_limit_bytes": MAX_BYTES,
        "hosted_ready": False,
        "historical_pregame_cohort_verified": False,
    }
    plan["plan_sha256"] = digest(json.dumps(plan, sort_keys=True, allow_nan=False).encode())
    return plan


def _apply_seed(
    conn: psycopg.Connection[Any],
    store: PrivateArtifacts,
    plan: dict[str, Any],
    archive: Path,
    checkpoint: Path,
    *,
    environment: str = "rehearsal",
    fault: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    expected = dict(plan)
    sha = expected.pop("plan_sha256")
    if plan["importer_sha256"] != checksum(Path(__file__)) or plan[
        "raw_archive_implementation_sha256"
    ] != checksum(Path(raw_codec.__file__)):
        raise EvidenceError("Seed plan belongs to a different importer version")
    if digest(json.dumps(expected, sort_keys=True, allow_nan=False).encode()) != sha:
        raise EvidenceError("Seed plan identity changed")
    if plan["blockers"] or environment not in {"rehearsal", "production"}:
        raise EvidenceError("Seed import blocked by unresolved plan gates")
    if environment == "production" and plan["acceptance"]["kind"] != "owner_review":
        raise EvidenceError("Synthetic acceptance cannot authorize production import")
    if plan["quarantine_policy_sha256"] != checksum(Path(quarantine_policy.__file__)):
        raise EvidenceError("Seed plan belongs to another quarantine policy")
    if plan["repair_lineage_implementation_sha256"] != checksum(Path(lineage.__file__)):
        raise EvidenceError("Seed plan belongs to another repair-lineage implementation")
    archive_store = LocalArtifacts(archive)
    manifest = plan["seed_manifest"]
    seed_report = {
        **json.loads(archive_store.verify(manifest).read_text()),
        "manifest_artifact": manifest,
    }
    all_players = pq.read_table(
        archive_store.verify(plan["source_normalized"]["players"])
    ).to_pylist()
    all_teams = pq.read_table(archive_store.verify(plan["source_normalized"]["teams"])).to_pylist()
    selection_blockers: list[str] = []
    actual_selected = recent_rows(
        [p for p in all_players if p["participation"] == "played"], "player_id", selection_blockers
    )
    review = quarantine_policy.compact_review(
        seed_report, actual_selected, all_teams, plan["acceptance"]
    )
    if (
        selection_blockers
        or actual_selected != plan["players"]
        or review != plan["quarantine_review"]
        or seed_report["quarantine"]
        and not review["review_accepted"]
    ):
        raise EvidenceError("Compact quarantine window no longer matches reviewed plan")
    expected_repairs = list(
        {
            a["sha256"]: a
            for a in seed_report["artifacts"]
            if a["kind"] in {"repair_evidence", "repair_overlay"}
        }.values()
    )
    if plan["repair_inputs"] != expected_repairs:
        raise EvidenceError("Repair lineage differs from immutable seed manifest")
    repair_paths = {a["sha256"]: archive_store.verify(a) for a in plan["repair_inputs"]}
    if any(path.stat().st_size > MAX_BYTES for path in repair_paths.values()):
        raise EvidenceError("Repair input exceeds physical object bound")
    raw_paths = {name: archive_store.verify(item) for name, item in plan["raw"].items()}
    staged = plan["raw_archives"]
    if staged is not None:
        # Recheck the staged identity before any database or network operation.
        for name, item in plan["raw"].items():
            original = raw_codec.verify_archive(
                staged["files"][name], lambda part: archive_store.verify(part).read_bytes()
            )
            if original != {"sha256": item["sha256"], "byte_count": item["byte_count"]}:
                raise EvidenceError("Staged raw differs from import plan")
    # Resolve/check all local inputs before retaining anything remotely.
    selected = {}
    for name in ["players", "teams"]:
        schema = pq.read_schema(archive_store.verify(plan["source_normalized"][name]))
        buffer = pa.BufferOutputStream()
        pq.write_table(pa.Table.from_pylist(plan[name], schema=schema), buffer, compression="zstd")
        selected[name] = buffer.getvalue().to_pybytes()
    run_id = stable_id("seed-import", sha, environment)
    register(
        conn,
        "runs",
        {
            "run_id": str(run_id),
            "operation": "seed_import",
            "domain": "nba",
            "environment": environment,
            "code_version": POLICY,
            "config_hash": sha,
        },
    )
    register(
        conn,
        "run_events",
        {
            "run_event_id": str(uuid4()),
            "run_id": str(run_id),
            "state": "started",
            "reason_code": None,
            "details": {"plan_sha256": sha},
        },
    )
    raw_objects = {}
    for name, path in raw_paths.items():
        if staged is None:
            if path.stat().st_size > MAX_BYTES:
                raise EvidenceError("Direct raw exceeds physical object bound")
            raw_objects[name] = retain(
                conn, store, path.read_bytes(), kind="raw", format="csv", manifest={}
            )
        else:
            raw_objects[name] = raw_codec.retain_archive(
                conn, store, archive_store, staged["files"][name]
            )
    repair_objects = retain_repairs(conn, store, archive_store, plan["repair_inputs"])
    objects = [
        retain(conn, store, body, kind="history", format="parquet", manifest={})
        for body in selected.values()
    ]
    seed_manifest = retain(
        conn,
        store,
        archive_store.verify(plan["seed_manifest"]).read_bytes(),
        kind="reports",
        format="json",
        manifest={},
    )
    cloud_manifest = {
        "policy": POLICY,
        "plan_sha256": sha,
        "raw": raw_objects,
        "repair_lineage": repair_objects,
        "quarantine_review": plan["quarantine_review"],
        "selected": objects,
        "seed_manifest": seed_manifest,
        "source_manifest": plan["source_manifest"],
        "observations": plan["observations"],
    }
    objects.append(seed_manifest)
    objects.append(
        retain(
            conn,
            store,
            json.dumps(cloud_manifest, sort_keys=True).encode(),
            kind="reports",
            format="json",
            manifest={},
        )
    )
    checks = {}
    raw_counts = {}
    for name, path in raw_paths.items():
        with path.open(encoding="utf-8-sig", newline="") as incoming:
            raw_counts[name] = sum(1 for _ in csv.DictReader(incoming))
    for name, raw_object in raw_objects.items():
        check_id = stable_id("seed-check", sha, name, environment)
        register(
            conn,
            "source_checks",
            {
                "check_id": str(check_id),
                "run_id": str(run_id),
                "source_id": plan["source_manifest"]["source_id"],
                "adapter_version": POLICY,
                "requested_at": parse_time(plan["observations"][name]["requested_at"]),
                "received_at": parse_time(plan["observations"][name]["received_at"]),
                "validated_at": parse_time(plan["validated_at"]),
                "source_published_at": None,
                "raw_artifact_id": raw_object["artifact_id"],
                "http_status": None,
                "record_count": raw_counts[name],
                "state": "accepted",
                "validation_summary": {
                    "evidence_tier": "archived_observed",
                    "import_plan": sha,
                    "original_request_time_unknown": False,
                    "scope": "compact_seed_only",
                    "repair_artifact_ids": [r["artifact_id"] for r in repair_objects],
                    "unresolved_historical_rows": len(seed_report["quarantine"]),
                    "reviewed_exclusions": len(seed_report.get("reviewed_exclusions", [])),
                    "raw_representation": raw_codec.REPRESENTATION if staged else "direct_csv",
                    "original_raw_sha256": plan["raw"][name]["sha256"],
                    "original_raw_byte_count": plan["raw"][name]["byte_count"],
                },
            },
        )
        checks[name] = check_id
    if fault:
        fault("after_artifacts")
    observed = parse_time(plan["validated_at"])
    completed = []
    # Checkpoints are an optimization; exact database identity is authoritative.
    for game in plan["games"]:
        gid = game["game_id"]
        event_id = stable_id("nba-event", gid, "1")
        with conn.transaction():
            for team in [game["home"], game["away"]]:
                immutable_insert(conn, "nba", "teams", {"team_id": team}, ("team_id",))
            immutable_insert(
                conn,
                "platform",
                "events",
                {
                    "event_id": event_id,
                    "domain": "nba",
                    "source_event_id": gid,
                    "competition": "regular",
                    "season": game["season"],
                    "occurrence_no": 1,
                    "predecessor_event_id": None,
                },
                ("event_id",),
            )
            immutable_insert(
                conn,
                "nba",
                "games",
                {
                    "event_id": event_id,
                    "home_team_id": game["home"],
                    "away_team_id": game["away"],
                    "source_season_type": "Regular Season",
                },
                ("event_id",),
            )
            immutable_insert(
                conn,
                "platform",
                "event_observations",
                {
                    "observation_id": stable_id("seed-observation", sha, gid),
                    "event_id": event_id,
                    "source_check_id": checks["Games.csv"],
                    "observed_at": observed,
                    "scheduled_start": None,
                    "actual_start": None,
                    "state": "final",
                    "details": {
                        "game_date": game["game_date"],
                        "date_convention": "source_calendar_verified",
                        "evidence_tier": "archived_observed",
                    },
                },
                ("observation_id",),
            )
            for row in [r for r in plan["teams"] if r["game_id"] == gid]:
                immutable_insert(
                    conn,
                    "nba",
                    "team_game_versions",
                    {
                        "fact_id": stable_id("team-fact", sha, gid, row["team_id"]),
                        "event_id": event_id,
                        "team_id": row["team_id"],
                        "source_check_id": checks["TeamStatistics.csv"],
                        "observed_at": observed,
                        "evidence_tier": "archived_observed",
                        "points_for": row["points_for"],
                        "points_against": row["points_against"],
                        "extras_artifact_id": None,
                    },
                    ("fact_id",),
                )
            for row in [r for r in plan["players"] if r["game_id"] == gid]:
                immutable_insert(
                    conn, "nba", "players", {"player_id": row["player_id"]}, ("player_id",)
                )
                immutable_insert(
                    conn,
                    "nba",
                    "player_game_versions",
                    {
                        "fact_id": stable_id("player-fact", sha, gid, row["player_id"]),
                        "event_id": event_id,
                        "player_id": row["player_id"],
                        "team_id": row["team_id"],
                        "source_check_id": checks["PlayerStatistics.csv"],
                        "observed_at": observed,
                        "evidence_tier": "archived_observed",
                        "participation": row["participation"],
                        "minutes_seconds": Decimal(str(row["seconds"]))
                        if row["seconds"] is not None
                        else None,
                        "points": row["points"],
                        "rebounds": row["reboundsTotal"],
                        "assists": row["assists"],
                        "threes_made": row["threePointersMade"],
                        "started": None,
                    },
                    ("fact_id",),
                )
            if fault:
                fault("within_chunk")
        if fault:
            fault("before_checkpoint")
        completed.append(gid)
        atomic_json(checkpoint, {"plan_sha256": sha, "committed_games": completed})
    return {
        "run_id": str(run_id),
        "plan_sha256": sha,
        "committed_games": len(completed),
        "artifacts": [obj["artifact_id"] for obj in objects],
        "environment": environment,
        "hosted_reference_resolution_verified": False,
    }


def apply_seed(
    conn: psycopg.Connection[Any],
    store: PrivateArtifacts,
    plan: dict[str, Any],
    archive: Path,
    checkpoint: Path,
    *,
    environment: str = "rehearsal",
    fault: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    started = time.monotonic()
    run_id = stable_id("seed-import", plan["plan_sha256"], environment)
    try:
        result = _apply_seed(
            conn, store, plan, archive, checkpoint, environment=environment, fault=fault
        )
    except Exception:
        try:
            if conn.execute("SELECT 1 FROM platform.runs WHERE run_id=%s", (run_id,)).fetchone():
                register(
                    conn,
                    "run_events",
                    {
                        "run_event_id": str(uuid4()),
                        "run_id": str(run_id),
                        "state": "failed",
                        "reason_code": "seed_import_failed",
                        "details": {
                            "counts": {},
                            "duration_ms": round((time.monotonic() - started) * 1000),
                        },
                    },
                )
        except (psycopg.Error, EvidenceError):
            atomic_json(
                checkpoint.parent / f"{uuid4().hex}.failure.json",
                {
                    "reason_code": "seed_import_recording_failed",
                    "durable_recording_confirmed": False,
                },
            )
        raise
    register(
        conn,
        "run_events",
        {
            "run_event_id": str(uuid4()),
            "run_id": str(run_id),
            "state": "succeeded",
            "reason_code": None,
            "details": {
                "counts": {"committed_games": result["committed_games"]},
                "duration_ms": round((time.monotonic() - started) * 1000),
            },
        },
    )
    return result
