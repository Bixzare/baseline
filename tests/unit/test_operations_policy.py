from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from hoop.domains.nba.operations import SourceBudget, due
from hoop.domains.nba.sources.policy import Response
from hoop.domains.nba.sources.validate import validate
from hoop.platform.operations import READY_KEYS, production_enabled
from tests.unit.test_source_policy import FakeClock, FakeTransport, request, valid_response


def test_due_window_has_strict_stop_and_no_late_catchup() -> None:
    start = datetime(2026, 11, 1, 19, tzinfo=UTC)
    assert not due(start - timedelta(minutes=121), start)
    assert due(start - timedelta(minutes=120), start)
    assert due(start - timedelta(minutes=90), start)
    assert not due(start - timedelta(minutes=15), start)
    assert not due(start + timedelta(minutes=5), start)


def test_production_requires_explicit_enable_and_every_reviewed_gate(monkeypatch: Any) -> None:
    config = {"readiness": {key: True for key in READY_KEYS}}
    config["readiness"]["backup_verified"] = False
    monkeypatch.setenv("BASELINE_PRODUCTION_ENABLE", "true")
    assert not production_enabled(config)
    config["readiness"]["backup_verified"] = True
    assert production_enabled(config)
    monkeypatch.delenv("BASELINE_PRODUCTION_ENABLE")
    assert not production_enabled(config)


def test_request_gap_budget_and_denial_survive_stage_boundaries(tmp_path: Path) -> None:
    transport = FakeTransport([Response(403, b"denied", {})])
    budget = SourceBudget(
        tmp_path,
        "local",
        {"max_seconds": 180, "max_requests": 3},
        transport=transport,
        clock=FakeClock(),
    )
    first = budget.runner()
    first.fetch(request(), validate)
    second = budget.runner()
    assert second.fetch(request(), validate)["reason"] == "source_stopped_after_access_denial"
    assert len(transport.calls) == 1
    # Separate healthy stages retain the enforced three-second gap too.
    transport = FakeTransport([valid_response(), valid_response()])
    clock = FakeClock()
    budget = SourceBudget(
        tmp_path / "good",
        "local",
        {"max_seconds": 180, "max_requests": 2},
        transport=transport,
        clock=clock,
    )
    budget.runner().fetch(request(), validate)
    budget.runner().fetch(request(), validate)
    assert clock.elapsed == 3
    with pytest.raises(Exception, match="budget"):
        budget.runner()


def test_default_production_cli_is_disabled_without_connections(
    tmp_path: Path, monkeypatch: Any
) -> None:
    import json
    import sys

    from hoop.domains.nba.operations import main

    monkeypatch.delenv("BASELINE_PRODUCTION_ENABLE", raising=False)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "operations",
            "dispatcher",
            "--mode",
            "production",
            "--environment",
            "github-actions",
            "--output",
            str(tmp_path),
        ],
    )
    assert main() == 0
    result = json.loads((tmp_path / "operation.json").read_text())
    assert result == {"state": "disabled", "production_heartbeat": False}
