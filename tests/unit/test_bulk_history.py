"""Historical snapshot assessment is offline, conservative, and source-version aware."""

import csv
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from hoop.domains.nba.sources.bulk_history import assess_snapshot, file_hash
from hoop.platform.provenance import known_by, parse_time

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures/nba/eoin-history"
SOURCE = "eoinamoore/historical-nba-data-and-player-box-scores"


@pytest.fixture
def snapshot(tmp_path: Path) -> tuple[Path, dict[str, Any], dict[str, Any]]:
    root = tmp_path / "snapshot"
    shutil.copytree(FIXTURES, root)
    manifest = json.loads((root / "manifest.json").read_text())
    inventory = json.loads((root / "inventory.json").read_text())
    return root, manifest, inventory


def amend(root: Path, manifest: dict[str, Any], name: str, rows: list[dict[str, str]]) -> None:
    with (root / name).open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    manifest["files"][name] = file_hash(root / name)


def records(root: Path, name: str) -> list[dict[str, str]]:
    with (root / name).open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def test_exact_synthetic_game_and_fractional_minutes(snapshot: Any) -> None:
    root, manifest, inventory = snapshot
    report = assess_snapshot(root, manifest, "2025-26", inventory)
    assert report["status"] == "checks_passed_pending_owner_acceptance"
    assert report["valid_game_count"] == 1
    assert report["valid_team_rows"] == 2
    assert report["participation"] == {"positive_minutes": 2}
    assert report["coverage"]["status"] == "matched_declared_inventory"
    assert not report["source_accepted"] and not report["historical_availability_verified"]
    assert report["evidence_kind"] == "synthetic_fixture"


def test_missing_expected_inventory_never_claims_complete(snapshot: Any) -> None:
    root, manifest, _ = snapshot
    report = assess_snapshot(root, manifest, "2025-26")
    assert report["status"] == "needs_review"
    assert report["coverage"]["status"] == "unknown"


def test_expected_missing_game_and_wrong_competition(snapshot: Any) -> None:
    root, manifest, inventory = snapshot
    inventory["game_ids"].append("0022500002")
    report = assess_snapshot(root, manifest, "2025-26", inventory)
    assert report["coverage"]["missing_game_ids"] == ["0022500002"]
    inventory["game_ids"] = ["0012500001"]
    with pytest.raises(ValueError, match="Invalid expected"):
        assess_snapshot(root, manifest, "2025-26", inventory)


@pytest.mark.parametrize("value", ["", "nan", "inf", "-1", "1.5"])
def test_invalid_counting_targets_quarantined(snapshot: Any, value: str) -> None:
    root, manifest, inventory = snapshot
    rows = records(root, "PlayerStatistics.csv")
    rows[0]["points"] = value
    amend(root, manifest, "PlayerStatistics.csv", rows)
    report = assess_snapshot(root, manifest, "2025-26", inventory)
    assert report["status"] == "needs_review"
    assert any(item["file"] == "PlayerStatistics.csv" for item in report["repair_items"])


@pytest.mark.parametrize(
    "comment,minutes,label",
    [
        ("DNP - Coach's Decision", "", "nonparticipation_comment"),
        ("DND - Injury/Illness", "0", "nonparticipation_comment"),
        ("", "", "unknown"),
        ("", "0", "zero_minutes_unknown"),
    ],
)
def test_nonparticipation_is_not_inferred_from_missing_or_zero(
    snapshot: Any, comment: str, minutes: str, label: str
) -> None:
    root, manifest, inventory = snapshot
    rows = records(root, "PlayerStatistics.csv")
    rows[0].update(
        numMinutes=minutes,
        comment=comment,
        points="0",
        reboundsTotal="0",
        assists="0",
        threePointersMade="0",
    )
    amend(root, manifest, "PlayerStatistics.csv", rows)
    report = assess_snapshot(root, manifest, "2025-26", inventory)
    assert report["participation"][label] == 1
    assert not report["source_accepted"]


def test_comment_conflicting_with_actual_statistics_is_quarantined(snapshot: Any) -> None:
    root, manifest, inventory = snapshot
    rows = records(root, "PlayerStatistics.csv")
    rows[0]["comment"] = "DNP - Coach's Decision"
    amend(root, manifest, "PlayerStatistics.csv", rows)
    report = assess_snapshot(root, manifest, "2025-26", inventory)
    assert any(item["reason"] == "conflicting_nonparticipation" for item in report["repair_items"])


def test_invalid_identity_duplicate_and_point_conflicts_are_visible(snapshot: Any) -> None:
    root, manifest, inventory = snapshot
    rows = records(root, "TeamStatistics.csv")
    rows.append({**rows[0], "teamId": "0"})
    rows.append(rows[0].copy())
    rows[1]["teamScore"] = "12"
    amend(root, manifest, "TeamStatistics.csv", rows)
    report = assess_snapshot(root, manifest, "2025-26", inventory)
    reasons = {item["reason"] for item in report["repair_items"]}
    assert {
        "invalid_identity",
        "duplicate_team_key",
        "team_game_score_conflict",
        "missing_team_side",
    } <= reasons
    assert report["selected_rows"]["TeamStatistics.csv"] == 4


def test_tampering_and_missing_columns_fail_before_acceptance(snapshot: Any) -> None:
    root, manifest, inventory = snapshot
    (root / "Games.csv").write_text("wrong\n1\n")
    with pytest.raises(ValueError, match="Checksum mismatch"):
        assess_snapshot(root, manifest, "2025-26", inventory)
    manifest["files"]["Games.csv"] = file_hash(root / "Games.csv")
    with pytest.raises(ValueError, match="Invalid columns"):
        assess_snapshot(root, manifest, "2025-26", inventory)


@pytest.mark.parametrize("minutes", ["nan", "inf", "-0.1"])
def test_invalid_minutes_are_not_accepted_as_appearances(snapshot: Any, minutes: str) -> None:
    root, manifest, inventory = snapshot
    rows = records(root, "PlayerStatistics.csv")
    rows[0]["numMinutes"] = minutes
    amend(root, manifest, "PlayerStatistics.csv", rows)
    report = assess_snapshot(root, manifest, "2025-26", inventory)
    assert any(item["reason"] == "invalid_target" for item in report["repair_items"])
    assert report["participation"] == {"positive_minutes": 1}


def test_same_dataset_inventory_cannot_establish_separate_coverage(snapshot: Any) -> None:
    root, manifest, inventory = snapshot
    inventory["source_id"] = SOURCE
    with pytest.raises(ValueError, match="separate collection source"):
        assess_snapshot(root, manifest, "2025-26", inventory)


def test_other_season_and_preseason_do_not_enter_seed(snapshot: Any) -> None:
    root, manifest, inventory = snapshot
    rows = records(root, "Games.csv")
    rows.extend([{**rows[0], "gameId": "22400001"}, {**rows[0], "gameId": "12500001"}])
    amend(root, manifest, "Games.csv", rows)
    report = assess_snapshot(root, manifest, "2025-26", inventory)
    assert report["valid_game_count"] == 1
    assert report["selected_rows"]["Games.csv"] == 1
    assert not report["repair_items"]


def test_revised_file_retains_later_collection_time_and_changed_identity(snapshot: Any) -> None:
    root, manifest, inventory = snapshot
    old = assess_snapshot(root, manifest, "2025-26", inventory)
    rows = records(root, "PlayerStatistics.csv")
    rows[0]["numMinutes"] = "21.25"
    amend(root, manifest, "PlayerStatistics.csv", rows)
    manifest["collected_at"] = "2026-10-25T10:00:00+00:00"
    new = assess_snapshot(root, manifest, "2025-26", inventory)
    assert old["manifest_sha256"] != new["manifest_sha256"]
    assert old["inputs"] != new["inputs"]
    assert new["collected_at"] == "2026-10-25T10:00:00+00:00"

    # Even an otherwise valid observed input cannot backdate this revision.
    def input_observation(report: dict[str, Any]) -> dict[str, Any]:
        return {
            "outcome": "verified_sample",
            "capability": "history",
            "received_at": report["collected_at"],
            "validated_at": report["collected_at"],
        }

    cutoff = parse_time("2026-10-24T23:00:00+00:00")
    assert known_by(input_observation(old), cutoff)
    assert not known_by(input_observation(new), cutoff)
    assert known_by(input_observation(new), parse_time("2026-10-25T11:00:00+00:00"))
    assert not new["historical_availability_verified"]


def test_cli_report_is_exclusive_and_no_inventory_returns_unverified(
    snapshot: Any, tmp_path: Path
) -> None:
    root, _, _ = snapshot
    output = tmp_path / "report.json"
    command = [
        sys.executable,
        "-m",
        "hoop.domains.nba.sources.bulk_history",
        "--root",
        str(root),
        "--manifest",
        str(root / "manifest.json"),
        "--report",
        str(output),
    ]
    first = subprocess.run(command, capture_output=True, text=True, check=False)
    assert first.returncode == 1
    original = output.read_bytes()
    second = subprocess.run(command, capture_output=True, text=True, check=False)
    assert second.returncode != 0
    assert output.read_bytes() == original
