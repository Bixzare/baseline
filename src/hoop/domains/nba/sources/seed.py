"""Resumable candidate-seed normalization; immutable artifacts, no database writes."""

import csv
import json
import re
import sys
import tempfile
from collections import Counter
from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal
from importlib.metadata import version
from pathlib import Path
from typing import Any
from uuid import uuid4

import pyarrow as pa
import pyarrow.parquet as pq

from hoop.domains.nba.sources.adjudication import OPERATIONS, verify_operation
from hoop.domains.nba.sources.bulk_history import FILES, TARGETS, assess_snapshot, identity, numeric
from hoop.platform.local_artifacts import LocalArtifacts, atomic_json, checksum
from hoop.platform.provenance import digest, parse_time

PARSER_VERSION = "eoin-seed-v2"


def row_hash(row: dict[str, str]) -> str:
    return digest(json.dumps(row, sort_keys=True).encode())


def build_seed(
    source: Path,
    manifest: dict[str, Any],
    destination: Path,
    *,
    season: str = "2025-26",
    inventory: dict[str, Any] | None = None,
    repair_paths: tuple[Path, ...] = (),
    now: datetime | None = None,
    fault: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    observed = now or datetime.now(UTC)
    if observed.tzinfo is None or parse_time(manifest["collected_at"]) > observed:
        raise ValueError("Assessment time must follow actual collection")
    store = LocalArtifacts(destination)
    patches: dict[tuple[str, int], dict[str, Any]] = {}
    repair_inputs = []
    evidence_paths = {}
    overlay_hashes = {}
    for path in repair_paths:
        patch = json.loads(path.read_text(encoding="utf-8"))
        if patch.get("operation", "field_update") not in OPERATIONS:
            raise ValueError("Unsupported repair operation")
        if not patch.get("source_id"):
            raise ValueError("Repair source identity is required")
        if patch["target_file"] not in FILES or patch["target_file"] == "Players.csv":
            raise ValueError("Unsupported repair target")
        if patch["parent_raw_sha256"] != manifest["files"][patch["target_file"]]:
            raise ValueError("Repair references another raw version")
        key = (patch["target_file"], patch["source_row"])
        if type(key[1]) is not int or key[1] < 2 or key in patches or not patch["reason"]:
            raise ValueError("Invalid or conflicting repair identity")
        if parse_time(patch["collected_at"]) > observed:
            raise ValueError("Repair evidence has not been collected yet")
        evidence_path = (path.parent / patch["evidence_file"]).resolve()
        if not evidence_path.is_relative_to(path.parent.resolve()):
            raise ValueError("Repair evidence escapes its input directory")
        if checksum(evidence_path) != patch["evidence_sha256"]:
            raise ValueError("Repair evidence checksum mismatch")
        evidence = store.put(evidence_path, kind="repair_evidence", format="source")
        descriptor = store.put(path, kind="repair_overlay", format="json")
        repair_inputs.extend([evidence, descriptor])
        patches[key] = patch
        evidence_paths[key] = store.verify(evidence)
        overlay_hashes[key] = descriptor["sha256"]
    cache_identity = {
        "source_id": manifest["source_id"],
        "dataset_version": manifest["dataset_version"],
        "files": manifest["files"],
        "parser": PARSER_VERSION,
        "code_hash": checksum(Path(__file__)),
        "adjudication_code_hash": checksum(Path(__file__).with_name("adjudication.py")),
        "season": season,
        "inventory": inventory,
        "repairs": [item["sha256"] for item in repair_inputs],
        "arrow_version": pa.__version__,
        "dependency_versions": {name: version(name) for name in ("pandas", "nba-api")},
        "python_version": sys.version.split()[0],
        "lock_sha256": checksum(Path(__file__).parents[5] / "uv.lock")
        if (Path(__file__).parents[5] / "uv.lock").is_file()
        else None,
    }
    unit = digest(json.dumps(cache_identity, sort_keys=True).encode())
    checkpoint = destination / "checkpoints" / f"{unit}.json"
    source_artifacts = {name: store.put(source / name, kind="raw", format="csv") for name in FILES}
    for name, artifact in source_artifacts.items():
        if artifact["sha256"] != manifest["files"][name]:
            raise ValueError(f"Raw snapshot checksum mismatch: {name}")
    if fault:
        fault("after_raw")
    reused = checkpoint.exists()
    if reused:
        result = json.loads(checkpoint.read_text(encoding="utf-8"))
        stored = json.loads(store.verify(result["manifest_artifact"]).read_text(encoding="utf-8"))
        if result != {**stored, "manifest_artifact": result["manifest_artifact"]}:
            raise ValueError("Checkpoint differs from immutable manifest")
        if result["unit_id"] != unit:
            raise ValueError("Checkpoint identity mismatch")
        for descriptor in result["artifacts"]:
            store.verify(descriptor)
    else:
        base_assessment = assess_snapshot(source, manifest, season, inventory)
        prefix = "002" + season[2:4]
        quarantine: list[dict[str, Any]] = []
        normalized_players: list[dict[str, Any]] = []
        normalized_teams: list[dict[str, Any]] = []
        games: dict[str, dict[str, Any]] = {}
        applied_patches: set[tuple[str, int]] = set()
        original_hashes: dict[tuple[str, int], str] = {}
        appearance_rows: set[tuple[str, int]] = set()
        confirmed_appearances = []
        reviewed_exclusions = []
        unresolved_adjudications = []

        def problem(name: str, line: int, row: dict[str, str], reason: str) -> None:
            quarantine.append(
                {
                    "file": name,
                    "source_row": line,
                    "game_id": row.get("gameId"),
                    "subject_id": row.get("personId", row.get("teamId")),
                    "reason": reason,
                    "raw_sha256": source_artifacts[name]["sha256"],
                    "base_row_sha256": original_hashes.get((name, line)),
                    "adjudication_evidence_sha256": patches.get((name, line), {}).get(
                        "evidence_sha256"
                    ),
                }
            )

        def read(name: str) -> list[tuple[int, dict[str, str]]]:
            rows = []
            with store.verify(source_artifacts[name]).open(
                encoding="utf-8-sig", newline=""
            ) as stream:
                reader = csv.DictReader(stream)
                for line, row in enumerate(reader, start=2):
                    if None in row or any(value is None for value in row.values()):
                        problem(name, line, row, "malformed_csv_row")
                        continue
                    key = (name, line)
                    if key in patches:
                        original_hashes[key] = row_hash(row)
                        patch = patches[key]
                        if patch["base_row_sha256"] != original_hashes[key]:
                            raise ValueError("Repair parent row has changed")
                        try:
                            operation = verify_operation(
                                patch, evidence_paths[key], row, games, season
                            )
                        except (KeyError, TypeError, AttributeError):
                            raise ValueError("Malformed typed adjudication evidence") from None
                        changes = patch["changes"]
                        if operation == "field_update":
                            if (
                                not changes
                                or not set(changes).issubset(row)
                                or any(not isinstance(value, str) for value in changes.values())
                            ):
                                raise ValueError(
                                    "Repair changes must preserve the input column contract"
                                )
                            row = {**row, **changes}
                        else:
                            record = {
                                "operation": operation,
                                "file": name,
                                "source_row": line,
                                "game_id": identity(row["gameId"], game=True),
                                "raw_sha256": source_artifacts[name]["sha256"],
                                "base_row_sha256": original_hashes[key],
                                "overlay_sha256": overlay_hashes[key],
                                "evidence_sha256": patch["evidence_sha256"],
                                "reason": patch["reason"],
                            }
                            if operation == "confirm_appearance":
                                appearance_rows.add(key)
                                confirmed_appearances.append(record)
                            elif operation == "exclude_invalid_extra_team":
                                reviewed_exclusions.append(record)
                            else:
                                unresolved_adjudications.append(record)
                        applied_patches.add(key)
                        if operation == "exclude_invalid_extra_team":
                            continue
                    try:
                        gid = identity(row["gameId"], game=True)
                    except ValueError:
                        problem(name, line, row, "invalid_game_id")
                        continue
                    if gid.startswith(prefix):
                        if key not in original_hashes:
                            original_hashes[key] = row_hash(row)
                        rows.append((line, {**row, "gameId": gid}))
            return rows

        def common(name: str, line: int, row: dict[str, str]) -> dict[str, Any]:
            if row.get("gameType", "") not in {
                "Regular Season",
                "NBA Cup",
                "NBA Emirates Cup",
                "Emirates NBA Cup",
            }:
                raise ValueError("unsupported_competition_label")
            raw_date = row.get("gameDateTimeEst") or row.get("gameDate", "")
            game_date = datetime.fromisoformat(raw_date).date().isoformat()
            return {
                "game_id": row["gameId"],
                "season": season,
                "competition": "regular",
                "game_date": game_date,
                "source_datetime": raw_date,
                "start_utc": None,
                "time_semantics": "source_local_unverified",
                "raw_sha256": source_artifacts[name]["sha256"],
                "source_row": line,
            }

        for line, row in read("Games.csv"):
            try:
                base = common("Games.csv", line, row)
                home, away = identity(row["hometeamId"]), identity(row["awayteamId"])
                if home == away or row["gameId"] in games:
                    raise ValueError("duplicate_or_conflicting_game")
                games[row["gameId"]] = {
                    **base,
                    "home": home,
                    "away": away,
                    "home_points": numeric(row["homeScore"], integer=True),
                    "away_points": numeric(row["awayScore"], integer=True),
                }
            except ValueError as error:
                problem("Games.csv", line, row, str(error))
        team_keys = set()
        for line, row in read("TeamStatistics.csv"):
            try:
                base = common("TeamStatistics.csv", line, row)
                team, opponent = identity(row["teamId"]), identity(row["opponentTeamId"])
                game = games.get(row["gameId"])
                if game is None or (team, opponent) not in {
                    (game["home"], game["away"]),
                    (game["away"], game["home"]),
                }:
                    raise ValueError("team_game_identity_conflict")
                key = (row["gameId"], team)
                if key in team_keys:
                    raise ValueError("duplicate_team_key")
                points_for = numeric(row["teamScore"], integer=True)
                home = team == game["home"]
                if points_for != game["home_points" if home else "away_points"]:
                    raise ValueError("team_score_conflict")
                team_keys.add(key)
                normalized_teams.append(
                    {
                        **base,
                        "team_id": team,
                        "opponent_team_id": opponent,
                        "home": home,
                        "points_for": int(points_for),
                        "points_against": int(game["away_points" if home else "home_points"]),
                    }
                )
            except ValueError as error:
                problem("TeamStatistics.csv", line, row, str(error))
        for exclusion in reviewed_exclusions:
            gid = exclusion["game_id"]
            if any(
                (gid, side) not in team_keys for side in [games[gid]["home"], games[gid]["away"]]
            ):
                raise ValueError("Reviewed exclusion requires both valid normalized team sides")
        player_ids = set()
        with store.verify(source_artifacts["Players.csv"]).open(
            encoding="utf-8-sig", newline=""
        ) as stream:
            for row in csv.DictReader(stream):
                try:
                    player_ids.add(identity(row["personId"]))
                except ValueError:
                    continue
        seen = set()
        for line, row in read("PlayerStatistics.csv"):
            try:
                base = common("PlayerStatistics.csv", line, row)
                player, team = identity(row["personId"]), identity(row["playerteamId"])
                key = (row["gameId"], player)
                if (
                    key in seen
                    or player not in player_ids
                    or (row["gameId"], team) not in team_keys
                ):
                    raise ValueError("player_identity_or_team_join_conflict")
                values = {target: int(numeric(row[target], integer=True)) for target in TARGETS}
                comment = row["comment"].strip()
                nonparticipant = bool(re.match(r"^(DNP|DND|NWT)(?:\b|_)", comment))
                minutes_text = row["numMinutes"].strip()
                minutes = numeric(minutes_text) if minutes_text else None
                if nonparticipant:
                    if any(values.values()) or (minutes is not None and minutes > 0):
                        raise ValueError("conflicting_nonparticipation")
                    participation = "did_not_play"
                elif ("PlayerStatistics.csv", line) in appearance_rows:
                    participation = "played"
                elif minutes is None or (minutes == 0 and not any(values.values())):
                    raise ValueError("unknown_participation_or_minutes")
                else:
                    participation = "played"
                seen.add(key)
                normalized_players.append(
                    {
                        **base,
                        "player_id": player,
                        "team_id": team,
                        "seconds": None if minutes is None else float(Decimal(minutes_text) * 60),
                        "reported_minutes": minutes_text or None,
                        "minute_precision": "reported_decimal"
                        if "." in minutes_text
                        else "reported_whole_or_unknown",
                        "participation": participation,
                        "participation_evidence": "observed_game_log_entry"
                        if ("PlayerStatistics.csv", line) in appearance_rows
                        else comment or None,
                        "rate_eligible": participation == "played"
                        and minutes is not None
                        and minutes > 0,
                        **values,
                    }
                )
            except ValueError as error:
                problem("PlayerStatistics.csv", line, row, str(error))
        if applied_patches != set(patches):
            raise ValueError("A repair did not match an input row")
        for gid, game in games.items():
            if any((gid, side) not in team_keys for side in [game["home"], game["away"]]):
                problem(
                    "Games.csv", game["source_row"], {"gameId": gid}, "missing_normalized_team_side"
                )
        player_points: Counter[tuple[str, str]] = Counter()
        player_sides = set()
        for record in normalized_players:
            side = (record["game_id"], record["team_id"])
            player_sides.add(side)
            player_points[side] += record["points"]
        for record in normalized_teams:
            side = (record["game_id"], record["team_id"])
            if side not in player_sides or player_points[side] != record["points_for"]:
                problem(
                    "TeamStatistics.csv",
                    record["source_row"],
                    {"gameId": record["game_id"], "teamId": record["team_id"]},
                    "normalized_player_team_points_conflict",
                )
        coverage = dict(base_assessment["coverage"])
        if inventory is not None:
            expected = {identity(value, game=True) for value in inventory["game_ids"]}
            coverage.update(
                status="matched_declared_inventory" if expected == set(games) else "mismatch",
                missing_game_ids=sorted(expected - games.keys()),
                unexpected_game_ids=sorted(games.keys() - expected),
            )
        artifacts = list(source_artifacts.values()) + repair_inputs
        normalized = {}
        for name, rows in [("players", normalized_players), ("teams", normalized_teams)]:
            if not rows:
                raise ValueError(f"No valid {name} records for requested seed")
            with tempfile.TemporaryDirectory(dir=store.root / "pending") as temp:
                path = Path(temp) / f"{name}.parquet"
                types = {
                    "source_row": pa.int64(),
                    "seconds": pa.float64(),
                    "start_utc": pa.timestamp("us", tz="UTC"),
                    "home": pa.bool_(),
                    "rate_eligible": pa.bool_(),
                    "points_for": pa.int64(),
                    "points_against": pa.int64(),
                    **{target: pa.int64() for target in TARGETS},
                }
                schema = pa.schema([pa.field(key, types.get(key, pa.string())) for key in rows[0]])
                pq.write_table(pa.Table.from_pylist(rows, schema=schema), path, compression="zstd")
                if fault:
                    fault("after_parquet")
                if pq.read_table(path).num_rows != len(rows):
                    raise ValueError("Parquet readback count mismatch")
                normalized[name] = store.put(path, kind=f"normalized_{name}", format="parquet")
                artifacts.append(normalized[name])
        completed = now or datetime.now(UTC)
        available_at = max(
            [
                parse_time(manifest["collected_at"]),
                completed,
                *[parse_time(p["collected_at"]) for p in patches.values()],
            ]
        )
        summary = {
            "unit_id": unit,
            "input_identity": cache_identity,
            "parser_version": PARSER_VERSION,
            "season": season,
            "source_id": manifest["source_id"],
            "dataset_version": manifest["dataset_version"],
            "evidence_kind": manifest["evidence_kind"],
            "validated_at": completed.isoformat(),
            "available_at": available_at.isoformat(),
            "coverage": coverage,
            "row_counts": {"players": len(normalized_players), "teams": len(normalized_teams)},
            "input_row_counts": base_assessment["selected_rows"],
            "game_count": len(games),
            "participation": dict(Counter(row["participation"] for row in normalized_players)),
            "quarantine": quarantine,
            "base_repair_items": base_assessment["repair_items"],
            "repairs_applied": len(patches),
            "confirmed_appearances": confirmed_appearances,
            "reviewed_exclusions": reviewed_exclusions,
            "unresolved_adjudications": unresolved_adjudications,
            "artifacts": artifacts,
            "normalized": normalized,
            "source_accepted": False,
            "historical_pregame_cohort_verified": False,
            "seed_status": "incomplete"
            if quarantine or coverage["status"] != "matched_declared_inventory"
            else "candidate_pending_owner_acceptance",
            "backup_status": "unverified",
            "time_mapping": "date_only; no UTC start invented",
        }
        with tempfile.TemporaryDirectory(dir=store.root / "pending") as temp:
            path = Path(temp) / "manifest.json"
            path.write_text(json.dumps(summary, sort_keys=True, allow_nan=False), encoding="utf-8")
            summary_artifact = store.put(path, kind="seed_manifest", format="json")
        result = {**summary, "manifest_artifact": summary_artifact}
        if fault:
            fault("before_checkpoint")
        atomic_json(checkpoint, result)
    store.verify(result["manifest_artifact"])
    observation = {
        "run_id": uuid4().hex,
        "unit_id": unit,
        "reused": reused,
        "observed_at": observed.isoformat(),
        "source_collected_at": manifest["collected_at"],
        "source_manifest_hash": digest(json.dumps(manifest, sort_keys=True).encode()),
        "manifest_artifact": result["manifest_artifact"],
    }
    run_path = destination / "runs" / f"{observation['run_id']}.json"
    atomic_json(run_path, observation)
    atomic_json(
        destination / "candidate-current.json",
        {
            "unit_id": unit,
            "manifest_artifact": result["manifest_artifact"],
            "source_accepted": False,
        },
    )
    return {**result, "reused": reused, "observation": observation}
