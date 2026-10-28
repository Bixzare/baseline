"""Read-only quarantine audit. Evidence inspection never accepts or repairs a seed."""

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq

from hoop.domains.nba.sources.bulk_history import TARGETS
from hoop.domains.nba.sources.seed import row_hash
from hoop.platform.local_artifacts import LocalArtifacts, atomic_json


def audit_quarantine(report: dict[str, Any], archive: Path) -> dict[str, Any]:
    store = LocalArtifacts(archive)
    descriptor = report["manifest_artifact"]
    saved = json.loads(store.verify(descriptor).read_text(encoding="utf-8"))
    if any(report.get(key) != value for key, value in saved.items()):
        raise ValueError("Report differs from immutable manifest")
    artifacts = {item["sha256"]: item for item in saved["artifacts"]}
    by_file: dict[str, dict[int, dict[str, Any]]] = defaultdict(dict)
    for item in saved["quarantine"]:
        name, line = item["file"], item["source_row"]
        if type(line) is not int or line < 2 or line in by_file[name]:
            raise ValueError("Invalid or duplicate quarantine row reference")
        if item["raw_sha256"] != saved["input_identity"]["files"][name]:
            raise ValueError("Quarantine raw identity differs from manifest")
        by_file[name][line] = item
    players = pq.read_table(store.verify(saved["normalized"]["players"])).to_pylist()
    teams = pq.read_table(store.verify(saved["normalized"]["teams"])).to_pylist()
    player_keys = Counter((row["game_id"], row["player_id"]) for row in players)
    team_keys = Counter((row["game_id"], row["team_id"]) for row in teams)
    game_sides = Counter(row["game_id"] for row in teams)
    details = []
    for name, wanted in sorted(by_file.items()):
        sha = saved["input_identity"]["files"][name]
        found = set()
        with store.verify(artifacts[sha]).open(encoding="utf-8-sig", newline="") as stream:
            for line, row in enumerate(csv.DictReader(stream), 2):
                if line not in wanted:
                    continue
                item = wanted[line]
                gid = row.get("gameId", "")
                gid = gid.zfill(10) if gid.isdigit() else gid
                subject = row.get("personId", row.get("teamId"))
                if gid != item["game_id"] or subject != item["subject_id"] or None in row:
                    raise ValueError("Quarantine row reference does not match original bytes")
                found.add(line)
                keys = player_keys if name == "PlayerStatistics.csv" else team_keys
                fields = [
                    "gameType",
                    "playerteamId",
                    "teamId",
                    "opponentTeamId",
                    "numMinutes",
                    "comment",
                    *TARGETS,
                ]
                details.append(
                    {
                        **item,
                        "base_row_sha256": row_hash(row),
                        "raw_fields": {key: row[key] for key in fields if key in row},
                        "normalized_same_subject_rows": keys[(gid, subject)],
                        "normalized_team_sides": game_sides[gid],
                        "participation_resolution": "unresolved",
                    }
                )
                if found == wanted.keys():
                    break
        if found != wanted.keys():
            raise ValueError("Quarantine source row is absent")
    reasons = Counter((row["file"], row["reason"]) for row in details)
    return {
        "schema_version": 1,
        "operation": "read_only_quarantine_audit",
        "manifest_sha256": descriptor["sha256"],
        "parser_version": saved["parser_version"],
        "quarantine_count": len(details),
        "affected_game_count": len({row["game_id"] for row in details}),
        "reason_counts": [
            {"file": name, "reason": reason, "count": count}
            for (name, reason), count in sorted(reasons.items())
        ],
        "rows_with_existing_normalized_subject": sum(
            row["normalized_same_subject_rows"] > 0 for row in details
        ),
        "details": details,
        "source_accepted": False,
        "repairs_applied": 0,
        "limitation": "Zero statistics and normalized overlaps do not resolve participation.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    try:
        store = LocalArtifacts(args.archive)
        pointer = json.loads((args.archive / "candidate-current.json").read_text())
        descriptor = pointer["manifest_artifact"]
        report = {
            **json.loads(store.verify(descriptor).read_text()),
            "manifest_artifact": descriptor,
        }
        audit = audit_quarantine(report, args.archive)
        atomic_json(args.report, audit)
        print(json.dumps({key: value for key, value in audit.items() if key != "details"}))
        return 0
    except (ValueError, KeyError, OSError, TypeError):
        print(json.dumps({"status": "blocked", "reason_code": "quarantine_audit_failed"}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
