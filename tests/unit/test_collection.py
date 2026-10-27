"""Route acceptance and real parser contracts, without live transport."""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from hoop.domains.nba.collection import PARSER, accepted_request, collection_validator
from hoop.domains.nba.sources.policy import ProbeRequest
from hoop.platform.evidence import EvidenceError
from hoop.platform.prepared import encoded
from hoop.platform.provenance import digest

ROOT = Path(__file__).parents[1] / "fixtures/nba"


def route(
    capability: str = "status", environment: str = "local", context: Any = None
) -> dict[str, Any]:
    context = context or {"season": "2026-27"}
    url = "https://cdn.nba.com/fixture/" + capability + ".json"
    identity = digest(
        encoded(
            {
                "url": url,
                "capability": capability,
                "context": context,
                "environment": environment,
                "parser_version": PARSER,
            }
        )
    )
    return {
        "status": "accepted",
        "capability": capability,
        "url": url,
        "context": context,
        "parser_version": PARSER,
        "request_hash": identity,
        "owner_acceptance_id": "invented-fixture",
        "evidence": {
            "outcome": "verified_sample",
            "environment": environment,
            "observation_id": "invented",
            "kind": "synthetic_fixture",
            "request_hash": identity,
        },
    }


def test_fixture_acceptance_cannot_authorize_live_routing() -> None:
    r = route()
    assert accepted_request(r, "local", rehearsal=True).capability == "status"
    with pytest.raises(EvidenceError):
        accepted_request(r, "local", rehearsal=False)
    r["url"] += "?changed=1"
    with pytest.raises(EvidenceError):
        accepted_request(r, "local", rehearsal=True)


def test_collection_preserves_ids_and_does_not_infer_actual_start() -> None:
    request = ProbeRequest("status", route()["url"], "local", {"season": "2026-27"})
    result = collection_validator(
        (ROOT / "scoreboard.json").read_bytes(), request, datetime(2026, 10, 14, 23, 30, tzinfo=UTC)
    )
    assert result["records"][0]["game_id"] == "0012600002"
    assert result["records"][0]["actual_start"] is None
    assert result["records"][0]["state"] == "scheduled"


def test_unknown_label_stale_generation_and_duplicate_keys_fail_honestly() -> None:
    payload = json.loads((ROOT / "scoreboard.json").read_text())
    request = ProbeRequest("status", route()["url"], "local", {"season": "2026-27"})
    now = datetime(2026, 10, 14, 23, 30, tzinfo=UTC)
    payload["scoreboard"]["games"][0]["gameStatusText"] = "Suspended"
    assert collection_validator(encoded(payload), request, now)["records"][0]["state"] == "unknown"
    payload["meta"] = {"time": "2026-10-14T12:00:00Z"}
    with pytest.raises(ValueError, match="semantics"):
        collection_validator(encoded(payload), request, now)
    approved = ProbeRequest(
        "status",
        request.url,
        "local",
        {**request.context, "source_time_semantics": "generated_utc"},
    )
    with pytest.raises(ValueError, match="Stale"):
        collection_validator(encoded(payload), approved, now)
    with pytest.raises(ValueError, match="Duplicate"):
        collection_validator(b'{"x":1,"x":2}', request, now)


def test_default_cli_routes_refuse_before_database_or_live_requests(
    tmp_path: Path, monkeypatch: Any
) -> None:
    import sys

    from hoop.domains.nba.collection import main

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "collection",
            "collect",
            "--environment",
            "local",
            "--output",
            str(tmp_path),
            "--confirm-source-gates",
        ],
    )
    assert main() == 1
    assert (
        json.loads((tmp_path / "collection-failure.json").read_text())["durable_audit_confirmed"]
        is False
    )
