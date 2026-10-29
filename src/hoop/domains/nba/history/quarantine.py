"""Compact-window review never declares unresolved historical participation known."""

import re
from typing import Any

FIELDS = (
    "file",
    "source_row",
    "game_id",
    "subject_id",
    "raw_sha256",
    "base_row_sha256",
    "adjudication_evidence_sha256",
)


def compact_review(
    report: dict[str, Any],
    selected: list[dict[str, Any]],
    teams: list[dict[str, Any]],
    approval: dict[str, Any],
) -> dict[str, Any]:
    unknowns = report["quarantine"]
    reviews = approval.get("compact_quarantine_review", [])
    if not isinstance(reviews, list):
        raise ValueError("Compact quarantine review must be a list")
    identity_matches = (
        approval.get("manifest_sha256") == report["manifest_artifact"]["sha256"]
        and approval.get("parser_version") == report["parser_version"]
        and approval.get("kind") in {"owner_review", "synthetic_fixture"}
    )
    evaluations = []
    for row in unknowns:
        signature = {key: row.get(key) for key in FIELDS}
        matches = [
            r
            for r in reviews
            if isinstance(r, dict) and all(r.get(key) == value for key, value in signature.items())
        ]
        game_dates = {t["game_date"] for t in teams if t["game_id"] == row["game_id"]}
        chosen = [p for p in selected if p["player_id"] == row["subject_id"]]
        well_bound = all(
            isinstance(signature.get(k), str) and re.fullmatch(r"[0-9a-f]{64}", signature[k])
            for k in ["raw_sha256", "base_row_sha256", "adjudication_evidence_sha256"]
        )
        strictly_later = (
            len(game_dates) == 1
            and len(chosen) == 10
            and len({p["game_date"] for p in chosen}) == 10
            and all(p["game_date"] > next(iter(game_dates)) for p in chosen)
        )
        adjudications = [
            a
            for a in report.get("unresolved_adjudications", [])
            if a.get("operation") == "retain_unresolved"
            and all(
                a.get(k) == row.get(k)
                for k in ["file", "source_row", "game_id", "raw_sha256", "base_row_sha256"]
            )
            and a.get("evidence_sha256") == row.get("adjudication_evidence_sha256")
        ]
        eligible = (
            row["file"] == "PlayerStatistics.csv"
            and row["reason"] in {"invalid_identity", "unsupported_competition_label"}
            and well_bound
            and len(adjudications) == 1
            and all(p.get("participation") == "played" for p in chosen)
            and strictly_later
        )
        reviewed = (
            identity_matches
            and eligible
            and len(matches) == 1
            and matches[0].get("disposition") == "outside_selected_appearance_window"
        )
        evaluations.append(
            {
                **signature,
                "eligible": eligible,
                "reviewed": reviewed,
                "selected_appearance_count": len(chosen),
                "unknown_game_date": next(iter(game_dates)) if len(game_dates) == 1 else None,
            }
        )
    exact_review_count = len(reviews) == len(unknowns)
    return {
        "evaluations": evaluations,
        "all_outside_required_window": all(e["eligible"] for e in evaluations),
        "review_accepted": identity_matches
        and exact_review_count
        and all(e["reviewed"] for e in evaluations),
        "historical_participation_resolved": False,
    }
