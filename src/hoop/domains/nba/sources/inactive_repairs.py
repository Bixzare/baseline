"""Prepare evidence-bound inactive-player overlays offline; never accept a seed."""

import argparse
import json
import os
import re
import tempfile
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq

from hoop.domains.nba.sources.bulk_history import TARGETS, identity
from hoop.domains.nba.sources.seed_audit import audit_quarantine
from hoop.platform.local_artifacts import LocalArtifacts, atomic_json, checksum
from hoop.platform.provenance import parse_time


def _exclusive(path: Path, body: bytes) -> None:
    handle, temporary = tempfile.mkstemp(dir=path.parent, prefix=".repair-pending-")
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(body)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError:
            if path.read_bytes() != body:
                raise ValueError("Repair output conflicts with existing evidence") from None
    finally:
        Path(temporary).unlink(missing_ok=True)


def _zero(value: str) -> bool:
    try:
        number = Decimal(value)
        return number.is_finite() and number == 0
    except InvalidOperation:
        return False


def _summary(root: Path, expected: dict[str, dict[str, Any]], now: datetime) -> dict[str, Any]:
    request = json.loads((root / "identity.json").read_text())
    observations = list((root / "observations").glob("*.json"))
    if len(observations) != 1:
        raise ValueError("One source observation required")
    observation = json.loads(observations[0].read_text())
    if (
        request["source_id"] != "nba_api.BoxScoreSummaryV3"
        or request.get("header_policy") != "unchanged_released_defaults"
        or observation["http_status"] != 200
        or not parse_time(request["requested_at"])
        <= parse_time(observation["received_at"])
        <= parse_time(observation["validated_at"])
        <= now
    ):
        raise ValueError("Invalid source receipt or collection policy")
    raw = (root / observation["raw_path"]).resolve()
    if (
        not raw.is_relative_to((root / "raw").resolve())
        or raw.stat().st_size > 8 * 1024 * 1024
        or checksum(raw) != observation["raw_sha256"]
    ):
        raise ValueError("Source bytes do not match retained receipt")
    game = json.loads(raw.read_bytes())["boxScoreSummary"]
    gid = identity(str(game["gameId"]), game=True)
    if gid != request["parameters"]["game_id"] or game["gameStatus"] != 3:
        raise ValueError("Source game identity or final status mismatch")
    home, away = game["homeTeam"], game["awayTeam"]
    if {identity(str(t["teamId"])) for t in [home, away]} != set(expected):
        raise ValueError("Source teams differ from normalized game")
    inactive: dict[str, str] = {}
    active: set[str] = set()
    for is_home, team in [(True, home), (False, away)]:
        tid = identity(str(team["teamId"]))
        side = expected[tid]
        if (
            type(team["score"]) is not int
            or team["score"] != side["points_for"]
            or side["home"] != is_home
        ):
            raise ValueError("Source score or venue conflicts with existing facts")
        for player in team["players"]:
            pid = identity(str(player["personId"]))
            if pid in active:
                raise ValueError("Duplicate active player identity")
            active.add(pid)
        for player in team["inactives"]:
            pid = identity(str(player["personId"]))
            if pid in inactive:
                raise ValueError("Duplicate inactive player identity")
            inactive[pid] = tid
    if set(inactive) & active:
        raise ValueError("Player cannot be active and inactive in the same source")
    return {
        "game_id": gid,
        "inactive": inactive,
        "body": raw.read_bytes(),
        "raw_sha256": observation["raw_sha256"],
        "received_at": observation["received_at"],
        "source_id": request["source_id"] + ":" + request["nba_api_version"],
    }


def prepare_inactive_overlays(
    report: dict[str, Any],
    archive: Path,
    evidence_roots: list[Path],
    output: Path,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    current = now or datetime.now(UTC)
    if current.tzinfo is None:
        raise ValueError("Timezone-aware assessment required")
    audit = audit_quarantine(report, archive)
    store = LocalArtifacts(archive)
    teams = pq.read_table(store.verify(report["normalized"]["teams"])).to_pylist()
    sides: dict[str, dict[str, dict[str, Any]]] = {}
    for row in teams:
        sides.setdefault(row["game_id"], {})[row["team_id"]] = row
    summaries = {}
    # Validate the complete requested evidence set before writing any overlay.
    for root in evidence_roots:
        request = json.loads((root / "identity.json").read_text())
        gid = request["parameters"]["game_id"]
        if gid in summaries or gid not in sides or len(sides[gid]) != 2:
            raise ValueError("Duplicate or unsupported source game")
        summaries[gid] = _summary(root, sides[gid], current)
    proposed = []
    unresolved = []
    for row in audit["details"]:
        if row["file"] != "PlayerStatistics.csv" or row["reason"] not in {
            "invalid_identity",
            "unsupported_competition_label",
        }:
            continue
        source = summaries.get(row["game_id"])
        tid = source["inactive"].get(row["subject_id"]) if source else None
        fields = row["raw_fields"]
        zero_stats = all(_zero(fields[key]) for key in TARGETS)
        minutes = fields.get("numMinutes", "").strip()
        minutes_compatible = not minutes or _zero(minutes)
        if (
            tid is None
            or not zero_stats
            or not minutes_compatible
            or fields.get("playerteamId", "") not in {"", tid}
            or fields.get("gameType", "") not in {"", "Regular Season"}
            or fields.get("comment", "").strip()
        ):
            unresolved.append(
                {
                    "game_id": row["game_id"],
                    "player_id": row["subject_id"],
                    "source_row": row["source_row"],
                    "reason": "no_unambiguous_inactive_repair",
                }
            )
            continue
        assert source is not None
        evidence_name = "evidence-" + source["raw_sha256"] + ".json"
        patch = {
            "source_id": source["source_id"],
            "target_file": row["file"],
            "source_row": row["source_row"],
            "parent_raw_sha256": row["raw_sha256"],
            "base_row_sha256": row["base_row_sha256"],
            "collected_at": source["received_at"],
            "evidence_file": evidence_name,
            "evidence_sha256": source["raw_sha256"],
            "reason": (
                "Explicit inactive identity, game, team and final-score evidence; "
                "no injury reason inferred"
            ),
            "changes": {
                "playerteamId": tid,
                "gameType": "Regular Season",
                "comment": "DND - listed inactive by NBA; reason unspecified",
            },
        }
        proposed.append((f"PlayerStatistics-{row['source_row']}.json", patch, source["body"]))
    output.mkdir(parents=True, exist_ok=True)
    for filename, patch, body in proposed:
        if not re.fullmatch(r"PlayerStatistics-[0-9]+\.json", filename):
            raise ValueError("Invalid repair filename")
        _exclusive(output / patch["evidence_file"], body)
        _exclusive(output / filename, json.dumps(patch, sort_keys=True, indent=2).encode())
    result = {
        "schema_version": 1,
        "candidate_manifest_sha256": report["manifest_artifact"]["sha256"],
        "operation": "prepare_inactive_overlays",
        "patch_count": len(proposed),
        "patches": [name for name, _, _ in proposed],
        "unresolved_identity_rows": unresolved,
        "source_accepted": False,
        "repairs_applied": False,
        "network_access": False,
    }
    atomic_json(output / "repair-plan.json", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        local = LocalArtifacts(args.archive)
        pointer = json.loads((args.archive / "candidate-current.json").read_text())
        descriptor = pointer["manifest_artifact"]
        report = {
            **json.loads(local.verify(descriptor).read_text()),
            "manifest_artifact": descriptor,
        }
        result = prepare_inactive_overlays(report, args.archive, args.evidence, args.output)
        print(json.dumps({key: value for key, value in result.items() if key != "patches"}))
        return 0
    except (ValueError, KeyError, TypeError, OSError):
        print(
            json.dumps({"status": "blocked", "reason_code": "inactive_repair_preparation_failed"})
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
