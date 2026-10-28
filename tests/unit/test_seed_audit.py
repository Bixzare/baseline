"""Quarantine diagnostics preserve unknowns and bind rows to verified raw bytes."""

import csv
import json
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from hoop.domains.nba.sources.seed import build_seed
from hoop.domains.nba.sources.seed_audit import audit_quarantine
from hoop.platform.local_artifacts import LocalArtifacts, checksum

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures/nba/seed"


def candidate(tmp_path: Path, *, duplicate: bool = False) -> tuple[dict[str, Any], Path]:
    source = tmp_path / "source"
    shutil.copytree(FIXTURE, source)
    path = source / "PlayerStatistics.csv"
    with path.open(newline="") as stream:
        reader = csv.DictReader(stream)
        fields, rows = reader.fieldnames, list(reader)
    extra = {
        **rows[0],
        "numMinutes": "0",
        "points": "0",
        "reboundsTotal": "0",
        "assists": "0",
        "threePointersMade": "0",
        "playerteamId": "",
    }
    if not duplicate:
        extra["personId"] = "203"
    with path.open("w", newline="") as stream:
        assert fields is not None
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows([*rows, extra])
    manifest = json.loads((source / "manifest.json").read_text())
    manifest["files"][path.name] = checksum(path)
    archive = tmp_path / "archive"
    report = build_seed(
        source,
        manifest,
        archive,
        inventory=json.loads((source / "inventory.json").read_text()),
        now=datetime(2026, 10, 25, 12, tzinfo=UTC),
    )
    return report, archive


def test_zero_unknown_is_inspected_without_repair_or_acceptance(tmp_path: Path) -> None:
    report, archive = candidate(tmp_path)
    pointer = (archive / "candidate-current.json").read_bytes()
    result = audit_quarantine(report, archive)
    assert result["quarantine_count"] == 1
    assert result["affected_game_count"] == 1
    assert result["reason_counts"] == [
        {"file": "PlayerStatistics.csv", "reason": "invalid_identity", "count": 1}
    ]
    row = result["details"][0]
    assert row["source_row"] == 4
    assert row["normalized_team_sides"] == 2
    assert row["raw_fields"]["playerteamId"] == ""
    assert row["participation_resolution"] == "unresolved"
    assert not result["source_accepted"] and result["repairs_applied"] == 0
    assert (archive / "candidate-current.json").read_bytes() == pointer


def test_overlap_is_not_silently_deduplicated(tmp_path: Path) -> None:
    report, archive = candidate(tmp_path, duplicate=True)
    result = audit_quarantine(report, archive)
    assert result["rows_with_existing_normalized_subject"] == 1
    assert result["quarantine_count"] == 1
    assert result["details"][0]["normalized_same_subject_rows"] == 1
    assert result["details"][0]["participation_resolution"] == "unresolved"


def test_changed_report_and_corrupt_raw_refuse_audit(tmp_path: Path) -> None:
    report, archive = candidate(tmp_path)
    report["quarantine"][0]["source_row"] = 5
    with pytest.raises(ValueError, match="immutable manifest"):
        audit_quarantine(report, archive)
    descriptor = report["manifest_artifact"]
    saved = json.loads(LocalArtifacts(archive).verify(descriptor).read_text())
    report = {**saved, "manifest_artifact": descriptor}
    raw = next(
        a
        for a in saved["artifacts"]
        if a["sha256"] == saved["input_identity"]["files"]["PlayerStatistics.csv"]
    )
    path = LocalArtifacts(archive).verify(raw)
    body = path.read_bytes()
    path.write_bytes(body.replace(b"22500001", b"22500002", 1))
    with pytest.raises(ValueError, match="checksum mismatch"):
        audit_quarantine(report, archive)


@pytest.mark.parametrize("mode", ["missing", "wrong_subject", "duplicate_reference"])
def test_self_consistent_manifest_still_needs_real_row_references(
    tmp_path: Path, mode: str
) -> None:
    report, archive = candidate(tmp_path)
    descriptor = report["manifest_artifact"]
    store = LocalArtifacts(archive)
    saved = json.loads(store.verify(descriptor).read_text())
    if mode == "missing":
        saved["quarantine"][0]["source_row"] = 99
        expected = "source row is absent"
    elif mode == "wrong_subject":
        saved["quarantine"][0]["source_row"] = 2
        expected = "does not match original bytes"
    else:
        saved["quarantine"].append(dict(saved["quarantine"][0]))
        expected = "duplicate quarantine row reference"
    changed = tmp_path / "changed.json"
    changed.write_text(json.dumps(saved))
    new_descriptor = store.put(changed, kind="seed_manifest", format="json")
    with pytest.raises(ValueError, match=expected):
        audit_quarantine({**saved, "manifest_artifact": new_descriptor}, archive)


def test_audit_cli_success_does_not_remove_import_blocker(tmp_path: Path) -> None:
    from hoop.domains.nba.history.seed import plan_seed

    report, archive = candidate(tmp_path)
    output = tmp_path / "audit.json"
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "hoop.domains.nba.sources.seed_audit",
            "--archive",
            str(archive),
            "--report",
            str(output),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout)["quarantine_count"] == 1
    assert json.loads(output.read_text())["repairs_applied"] == 0
    manifest = json.loads((tmp_path / "source/manifest.json").read_text())
    # Match the actual changed bytes; the fixture manifest on disk is the unmodified input.
    manifest["files"] = report["input_identity"]["files"]
    plan = plan_seed(report, archive, manifest)
    assert "seed_quarantine_unresolved" in plan["blockers"]
    assert "seed_acceptance_missing" in plan["blockers"]
