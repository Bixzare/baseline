"""Exercise real Parquet, immutable objects, interrupted work, and repair lineage."""

import csv
import json
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq
import pytest

from hoop.domains.nba.sources.bulk_history import file_hash
from hoop.domains.nba.sources.inventory import parse_inventory
from hoop.domains.nba.sources.seed import build_seed, row_hash
from hoop.platform.local_artifacts import LocalArtifacts
from hoop.platform.provenance import parse_time

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures/nba/seed"
NOW = datetime(2026, 10, 25, 12, tzinfo=UTC)


@pytest.fixture
def inputs(tmp_path: Path) -> tuple[Path, dict[str, Any], dict[str, Any], Path]:
    source = tmp_path / "source"
    shutil.copytree(FIXTURE, source)
    return (
        source,
        json.loads((source / "manifest.json").read_text()),
        json.loads((source / "inventory.json").read_text()),
        tmp_path / "archive",
    )


def update(
    source: Path, manifest: dict[str, Any], name: str, changes: dict[str, str]
) -> dict[str, str]:
    with (source / name).open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    rows[0].update(changes)
    with (source / name).open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    manifest["files"][name] = file_hash(source / name)
    return rows[0]


def test_fixture_parquet_and_unchanged_resume(inputs: Any) -> None:
    source, manifest, inventory, archive = inputs
    first = build_seed(source, manifest, archive, inventory=inventory, now=NOW)
    second = build_seed(source, manifest, archive, inventory=inventory, now=NOW)
    assert not first["reused"] and second["reused"]
    assert first["unit_id"] == second["unit_id"]
    assert first["row_counts"] == {"players": 2, "teams": 2}
    assert not first["source_accepted"]
    table = pq.read_table(LocalArtifacts(archive).verify(first["normalized"]["players"]))
    assert table["game_id"].to_pylist() == ["0022500001", "0022500001"]
    assert table["seconds"].to_pylist() == [1230.0, 1155.0]
    assert table["start_utc"].to_pylist() == [None, None]
    assert table.schema.field("start_utc").type.tz == "UTC"
    assert len(list((archive / "runs").glob("*.json"))) == 2


@pytest.mark.parametrize("stage", ["after_raw", "after_parquet", "before_checkpoint"])
def test_interruption_never_completes_checkpoint_and_resume_recovers(
    inputs: Any, stage: str
) -> None:
    source, manifest, inventory, archive = inputs

    def fail(current: str) -> None:
        if current == stage:
            raise OSError("synthetic interrupted write")

    with pytest.raises(OSError, match="interrupted"):
        build_seed(source, manifest, archive, inventory=inventory, now=NOW, fault=fail)
    assert not list((archive / "checkpoints").glob("*.json"))
    report = build_seed(source, manifest, archive, inventory=inventory, now=NOW)
    assert report["row_counts"]["players"] == 2
    assert not report["reused"]


def test_corrupt_artifact_and_checkpoint_refuse_reuse(inputs: Any) -> None:
    source, manifest, inventory, archive = inputs
    report = build_seed(source, manifest, archive, inventory=inventory, now=NOW)
    checkpoint = archive / "checkpoints" / (report["unit_id"] + ".json")
    old = checkpoint.read_bytes()
    altered = json.loads(old)
    altered["row_counts"]["players"] = 1000
    checkpoint.write_text(json.dumps(altered))
    with pytest.raises(ValueError, match="Checkpoint differs"):
        build_seed(source, manifest, archive, inventory=inventory, now=NOW)
    checkpoint.write_bytes(old)
    artifact = LocalArtifacts(archive).verify(report["normalized"]["players"])
    artifact.write_bytes(b"corrupt")
    with pytest.raises(ValueError, match="mismatch"):
        build_seed(source, manifest, archive, inventory=inventory, now=NOW)


@pytest.mark.parametrize(
    "minutes,comment,expected",
    [
        ("", "DNP - Coach's Decision", "did_not_play"),
        ("0", "DND - Injury/Illness", "did_not_play"),
        ("", "", None),
        ("0", "", None),
        ("nan", "", None),
    ],
)
def test_dnp_unknown_and_invalid_minutes_remain_distinct(
    inputs: Any, minutes: str, comment: str, expected: str | None
) -> None:
    source, manifest, inventory, archive = inputs
    update(
        source,
        manifest,
        "PlayerStatistics.csv",
        {
            "numMinutes": minutes,
            "comment": comment,
            "points": "0",
            "reboundsTotal": "0",
            "assists": "0",
            "threePointersMade": "0",
        },
    )
    update(source, manifest, "Games.csv", {"homeScore": "0"})
    update(source, manifest, "TeamStatistics.csv", {"teamScore": "0"})
    report = build_seed(source, manifest, archive, inventory=inventory, now=NOW)
    table = pq.read_table(LocalArtifacts(archive).verify(report["normalized"]["players"]))
    first = [row for row in table.to_pylist() if row["player_id"] == "201"]
    if expected:
        assert first[0]["participation"] == expected
        assert not first[0]["rate_eligible"]
        assert not report["quarantine"]
    else:
        assert first == [] and report["quarantine"]


def test_inventory_gaps_remain_explicit(inputs: Any) -> None:
    source, manifest, inventory, archive = inputs
    inventory["game_ids"].append("0022500002")
    report = build_seed(source, manifest, archive, inventory=inventory, now=NOW)
    assert report["coverage"]["missing_game_ids"] == ["0022500002"]
    assert report["seed_status"] == "incomplete"


def test_repair_parent_checksum_and_later_availability(inputs: Any, tmp_path: Path) -> None:
    source, manifest, inventory, archive = inputs
    row = update(source, manifest, "PlayerStatistics.csv", {"numMinutes": ""})
    first = build_seed(source, manifest, archive, inventory=inventory, now=NOW)
    evidence = tmp_path / "evidence.json"
    evidence.write_text('{"observed_minutes":20.5}')
    patch = {
        "source_id": "synthetic-repair",
        "target_file": "PlayerStatistics.csv",
        "source_row": 2,
        "parent_raw_sha256": manifest["files"]["PlayerStatistics.csv"],
        "base_row_sha256": row_hash(row),
        "collected_at": "2026-10-26T10:00:00+00:00",
        "evidence_file": evidence.name,
        "evidence_sha256": file_hash(evidence),
        "reason": "observed source minutes",
        "changes": {"numMinutes": "20.5"},
    }
    path = tmp_path / "patch.json"
    path.write_text(json.dumps(patch))
    with pytest.raises(ValueError, match="not been collected"):
        build_seed(source, manifest, archive, inventory=inventory, repair_paths=(path,), now=NOW)
    later = datetime(2026, 10, 26, 11, tzinfo=UTC)
    repaired = build_seed(
        source, manifest, archive, inventory=inventory, repair_paths=(path,), now=later
    )
    assert first["unit_id"] != repaired["unit_id"]
    assert repaired["row_counts"]["players"] == 2
    assert parse_time(repaired["available_at"]) > NOW
    assert first["row_counts"]["players"] == 1
    assert (archive / "checkpoints" / (first["unit_id"] + ".json")).exists()
    patch["base_row_sha256"] = "0" * 64
    path.write_text(json.dumps(patch))
    with pytest.raises(ValueError, match="parent row"):
        build_seed(source, manifest, archive, inventory=inventory, repair_paths=(path,), now=later)


def test_cli_uses_same_semantic_tables(inputs: Any, tmp_path: Path) -> None:
    source, manifest, inventory, archive = inputs
    report = build_seed(source, manifest, archive, inventory=inventory)
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest))
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "hoop.cli",
            "seed",
            "--source",
            str(source),
            "--manifest",
            str(manifest_path),
            "--inventory",
            str(source / "inventory.json"),
            "--archive",
            str(archive),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["unit_id"] == report["unit_id"]
    assert json.loads(result.stdout)["reused"]


def test_inventory_parser_requires_actual_two_team_game_sides() -> None:
    headers = ["SEASON_ID", "GAME_ID", "TEAM_ID"]
    body = {
        "resultSets": [
            {
                "name": "LeagueGameLog",
                "headers": headers,
                "rowSet": [["22025", "0022500001", 101], ["22025", "0022500001", 102]],
            }
        ]
    }
    result = parse_inventory(json.dumps(body).encode(), "2025-26", NOW.isoformat())
    assert result["game_ids"] == ["0022500001"]
    body["resultSets"][0]["rowSet"].pop()
    with pytest.raises(ValueError, match="two distinct"):
        parse_inventory(json.dumps(body).encode(), "2025-26", NOW.isoformat())
