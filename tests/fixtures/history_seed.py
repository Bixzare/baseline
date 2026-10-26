"""Invented acceptance and download observations, never production approval."""

import json
from pathlib import Path
from typing import Any

from hoop.domains.nba.history.seed import plan_seed
from hoop.domains.nba.sources.seed import build_seed
from hoop.platform.provenance import parse_time

SOURCE = Path(__file__).parent / "nba/seed"


def fixture_seed(archive: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    manifest = json.loads((SOURCE / "manifest.json").read_text())
    report = build_seed(
        SOURCE,
        manifest,
        archive,
        inventory=json.loads((SOURCE / "inventory.json").read_text()),
        now=parse_time("2026-10-25T12:00:00Z"),
    )
    acceptance = {
        "kind": "synthetic_fixture",
        "manifest_sha256": report["manifest_artifact"]["sha256"],
        "parser_version": report["parser_version"],
        "calendar_convention": "source_calendar_verified",
    }
    observations = {
        name: {
            "requested_at": "2026-10-24T11:59:00Z",
            "received_at": manifest["collected_at"],
            "sha256": sha,
        }
        for name, sha in manifest["files"].items()
    }
    plan = plan_seed(report, archive, manifest, acceptance, observations)
    return report, manifest, plan
