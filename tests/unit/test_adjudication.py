"""Typed historical adjudication requires positive evidence, never zero/absence alone."""

import json
from pathlib import Path

import pyarrow.parquet as pq
import pytest

from hoop.domains.nba.sources.seed import build_seed
from hoop.platform.local_artifacts import LocalArtifacts, checksum
from tests.fixtures.adjudication import NOW, fixture


def test_positive_appearance_and_extra_team_exclusion_keep_originals(tmp_path: Path) -> None:
    case = fixture(tmp_path)
    result = build_seed(
        case["source"],
        case["manifest"],
        case["archive"],
        inventory=case["inventory"],
        repair_paths=case["patches"],
        now=NOW,
    )
    assert result["participation"] == {"played": 3}
    assert len(result["reviewed_exclusions"]) == 1
    assert len(result["confirmed_appearances"]) == 1
    assert not result["quarantine"] and not result["source_accepted"]
    rows = pq.read_table(
        LocalArtifacts(case["archive"]).verify(result["normalized"]["players"])
    ).to_pylist()
    row = next(r for r in rows if r["player_id"] == "203")
    assert row["seconds"] == 0 and not row["rate_eligible"]
    assert row["participation_evidence"] == "observed_game_log_entry"
    assert result["available_at"] == NOW.isoformat()
    assert len(case["report"]["quarantine"]) == 2
    for name, sha in case["manifest"]["files"].items():
        assert checksum(case["source"] / name) == sha


@pytest.mark.parametrize(
    "mode", ["missing", "wrong_player", "wrong_game", "wrong_date", "wrong_stats", "wrong_request"]
)
def test_bad_or_absent_game_log_cannot_confirm_appearance(tmp_path: Path, mode: str) -> None:
    case = fixture(tmp_path)
    path = case["proof"] / "PlayerGameLog.json"
    body = json.loads(path.read_text())
    table = body["resultSets"][0]
    if mode == "missing":
        table["rowSet"] = []
    elif mode == "wrong_player":
        table["rowSet"][0][1] = 999
    elif mode == "wrong_game":
        table["rowSet"][0][2] = "0022500002"
    elif mode == "wrong_date":
        table["rowSet"][0][3] = "APR 11, 2026"
    elif mode == "wrong_stats":
        table["rowSet"][0][5] = 3
    else:
        body["parameters"]["Season"] = "2024-25"
    path.write_text(json.dumps(body))
    patch_path = case["patches"][0]
    patch = json.loads(patch_path.read_text())
    patch["evidence_sha256"] = checksum(path)
    patch_path.write_text(json.dumps(patch))
    with pytest.raises(ValueError):
        build_seed(
            case["source"],
            case["manifest"],
            case["archive"],
            inventory=case["inventory"],
            repair_paths=case["patches"],
            now=NOW,
        )


def test_retained_unknown_does_not_become_nonparticipant(tmp_path: Path) -> None:
    case = fixture(tmp_path)
    path = case["patches"][0]
    patch = json.loads(path.read_text())
    evidence = case["proof"] / "BoxScoreSummaryV3.json"
    patch.update(
        operation="retain_unresolved",
        source_id="nba_api.BoxScoreSummaryV3:1.11.4",
        evidence_file=evidence.name,
        evidence_sha256=checksum(evidence),
    )
    path.write_text(json.dumps(patch))
    result = build_seed(
        case["source"],
        case["manifest"],
        case["archive"],
        inventory=case["inventory"],
        repair_paths=case["patches"],
        now=NOW,
    )
    assert result["participation"] == {"played": 2}
    assert len(result["quarantine"]) == 1
    assert len(result["unresolved_adjudications"]) == 1
    assert result["quarantine"][0]["reason"] == "unknown_participation_or_minutes"
    assert result["quarantine"][0]["adjudication_evidence_sha256"] == checksum(evidence)
    assert not result["source_accepted"]


@pytest.mark.parametrize("mode", ["wrong_game", "wrong_score"])
def test_exclusion_needs_real_game_and_scores(tmp_path: Path, mode: str) -> None:
    case = fixture(tmp_path)
    path = case["proof"] / "BoxScoreSummaryV3.json"
    body = json.loads(path.read_text())
    if mode == "wrong_game":
        body["boxScoreSummary"]["gameId"] = "0022500002"
    else:
        body["boxScoreSummary"]["homeTeam"]["score"] = 0
    path.write_text(json.dumps(body))
    patch_path = case["patches"][1]
    patch = json.loads(patch_path.read_text())
    patch["evidence_sha256"] = checksum(path)
    patch_path.write_text(json.dumps(patch))
    with pytest.raises(ValueError):
        build_seed(
            case["source"],
            case["manifest"],
            case["archive"],
            inventory=case["inventory"],
            repair_paths=case["patches"],
            now=NOW,
        )


def test_late_positive_evidence_cannot_backdate_a_candidate(tmp_path: Path) -> None:
    from datetime import UTC, datetime

    case = fixture(tmp_path)
    with pytest.raises(ValueError, match="not been collected"):
        build_seed(
            case["source"],
            case["manifest"],
            case["archive"],
            inventory=case["inventory"],
            repair_paths=case["patches"],
            now=datetime(2026, 10, 25, 13, tzinfo=UTC),
        )


@pytest.mark.parametrize("mode", ["non_object", "oversized"])
def test_malformed_or_oversized_typed_proof_fails_before_normalization(
    tmp_path: Path, mode: str
) -> None:
    case = fixture(tmp_path)
    evidence = case["proof"] / "PlayerGameLog.json"
    evidence.write_bytes(b"[]" if mode == "non_object" else b"x" * (8 * 1024 * 1024 + 1))
    path = case["patches"][0]
    patch = json.loads(path.read_text())
    patch["evidence_sha256"] = checksum(evidence)
    path.write_text(json.dumps(patch))
    with pytest.raises(ValueError):
        build_seed(
            case["source"],
            case["manifest"],
            case["archive"],
            inventory=case["inventory"],
            repair_paths=case["patches"],
            now=NOW,
        )
