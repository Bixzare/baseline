"""A reviewed old unknown cannot alter a compact ten-appearance seed window."""

import copy
from typing import Any

import pytest

from hoop.domains.nba.history.quarantine import FIELDS, compact_review


def inputs() -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    row = {
        "file": "PlayerStatistics.csv",
        "source_row": 4,
        "game_id": "0022500001",
        "subject_id": "203",
        "raw_sha256": "a" * 64,
        "base_row_sha256": "b" * 64,
        "adjudication_evidence_sha256": "c" * 64,
        "reason": "invalid_identity",
    }
    record = {**row, "operation": "retain_unresolved", "evidence_sha256": "c" * 64}
    report = {
        "quarantine": [row],
        "manifest_artifact": {"sha256": "d" * 64},
        "parser_version": "eoin-seed-v2",
        "unresolved_adjudications": [record],
    }
    players = [
        {"player_id": "203", "game_date": f"2026-03-{i:02d}", "participation": "played"}
        for i in range(1, 11)
    ]
    teams = [{"game_id": "0022500001", "game_date": "2026-02-22"}]
    review = {k: row[k] for k in FIELDS}
    approval = {
        "manifest_sha256": "d" * 64,
        "parser_version": "eoin-seed-v2",
        "kind": "owner_review",
        "compact_quarantine_review": [
            {**review, "disposition": "outside_selected_appearance_window"}
        ],
    }
    return report, players, teams, approval


def test_exact_review_allows_scope_without_resolving_past_participation() -> None:
    report, players, teams, approval = inputs()
    before = copy.deepcopy(report)
    result = compact_review(report, players, teams, approval)
    assert result["all_outside_required_window"] and result["review_accepted"]
    assert not result["historical_participation_resolved"]
    assert result["evaluations"][0]["selected_appearance_count"] == 10
    assert report == before


@pytest.mark.parametrize(
    "mode", ["missing", "calendar_only", "stale_seed", "stale_parser", "extra", "wrong_row"]
)
def test_review_identity_and_exact_scope_are_required(mode: str) -> None:
    report, players, teams, approval = inputs()
    if mode == "missing":
        approval = {}
    elif mode == "calendar_only":
        approval["kind"] = "owner_calendar_review"
    elif mode == "stale_seed":
        approval["manifest_sha256"] = "f" * 64
    elif mode == "stale_parser":
        approval["parser_version"] = "older"
    elif mode == "extra":
        approval["compact_quarantine_review"] *= 2
    else:
        approval["compact_quarantine_review"][0]["source_row"] = 99
    result = compact_review(report, players, teams, approval)
    assert not result["review_accepted"]
    assert not any(row["reviewed"] for row in result["evaluations"])


@pytest.mark.parametrize(
    "mode",
    ["fewer", "same_date", "older", "duplicate_date", "not_played", "no_proof", "wrong_reason"],
)
def test_unsafe_windows_cannot_be_approved(mode: str) -> None:
    report, players, teams, approval = inputs()
    if mode == "fewer":
        players.pop()
    elif mode == "same_date":
        players[0]["game_date"] = "2026-02-22"
    elif mode == "older":
        players[0]["game_date"] = "2026-02-21"
    elif mode == "duplicate_date":
        players[1]["game_date"] = players[0]["game_date"]
    elif mode == "not_played":
        players[0]["participation"] = "did_not_play"
    elif mode == "no_proof":
        report["unresolved_adjudications"] = []
    else:
        report["quarantine"][0]["reason"] = "unknown_participation_or_minutes"
    result = compact_review(report, players, teams, approval)
    assert not result["all_outside_required_window"] and not result["review_accepted"]
