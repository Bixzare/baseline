import sys
from pathlib import Path
from typing import Any

import pytest

from hoop.domains.nba.outcomes import final_request
from hoop.domains.nba.outcomes.__main__ import main
from hoop.platform.evidence import EvidenceError
from tests.fixtures.finals import final_route


def test_reviewed_final_template_binds_saved_identity_and_season() -> None:
    event = {
        "source_event_id": "0022600001",
        "season": "2026-27",
        "home_team_id": "101",
        "away_team_id": "102",
    }
    request = final_request(final_route(template=True), event, "local", rehearsal=True)
    assert request.url.endswith("boxscore_0022600001.json")
    assert request.context["expected_team_ids"] == ["101", "102"]
    with pytest.raises(EvidenceError):
        final_request(
            final_route(template=True), {**event, "season": "2027-28"}, "local", rehearsal=True
        )


def test_outcome_cli_refuses_unaccepted_sources_before_connection(
    tmp_path: Path, monkeypatch: Any
) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "outcomes",
            "reconcile",
            "--environment",
            "local",
            "--output",
            str(tmp_path),
            "--confirm-source-gates",
        ],
    )
    assert main() == 1
