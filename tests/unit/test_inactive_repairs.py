"""Inactive repairs require exact identities, complete scores and retained raw proof."""

import csv
import json
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from hoop.domains.nba.sources.inactive_repairs import prepare_inactive_overlays
from hoop.domains.nba.sources.seed import build_seed
from hoop.platform.local_artifacts import checksum
from hoop.platform.provenance import Archive

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures/nba/seed"
NOW = datetime(2026, 10, 27, 12, tzinfo=UTC)


def inputs(tmp_path: Path) -> tuple[dict[str, Any], Path, Path, Path, dict[str, Any]]:
    source = tmp_path / "source"
    shutil.copytree(FIXTURE, source)
    raw = source / "PlayerStatistics.csv"
    with raw.open(newline="") as stream:
        reader = csv.DictReader(stream)
        fields, rows = reader.fieldnames, list(reader)
    assert fields is not None
    extra = {
        **rows[0],
        "personId": "203",
        "playerteamId": "",
        "numMinutes": "0",
        "points": "0",
        "reboundsTotal": "0",
        "assists": "0",
        "threePointersMade": "0",
    }
    with raw.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows([*rows, extra])
    manifest = json.loads((source / "manifest.json").read_text())
    manifest["files"][raw.name] = checksum(raw)
    names = source / "Players.csv"
    with names.open(newline="") as stream:
        people = csv.DictReader(stream)
        person_fields, people_rows = people.fieldnames, list(people)
    assert person_fields is not None
    with names.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=person_fields)
        writer.writeheader()
        writer.writerows([*people_rows, {**people_rows[0], "personId": "203"}])
    manifest["files"][names.name] = checksum(names)
    archive = tmp_path / "archive"
    report = build_seed(
        source,
        manifest,
        archive,
        inventory=json.loads((source / "inventory.json").read_text()),
        now=datetime(2026, 10, 25, 12, tzinfo=UTC),
    )
    evidence = tmp_path / "evidence"
    payload = {
        "boxScoreSummary": {
            "gameId": "0022500001",
            "gameStatus": 3,
            "homeTeam": {
                "teamId": 101,
                "score": 10,
                "players": [{"personId": 201}],
                "inactives": [{"personId": 203}],
            },
            "awayTeam": {
                "teamId": 102,
                "score": 9,
                "players": [{"personId": 202}],
                "inactives": [],
            },
        }
    }
    write_evidence(evidence, payload)
    return report, archive, source, evidence, manifest


def write_evidence(root: Path, payload: dict[str, Any]) -> None:
    archive = Archive(root)
    for p in (root / "observations").glob("*.json"):
        p.unlink()
    sha, path = archive.raw(json.dumps(payload).encode())
    request = {
        "source_id": "nba_api.BoxScoreSummaryV3",
        "nba_api_version": "1.11.4",
        "header_policy": "unchanged_released_defaults",
        "requested_at": "2026-10-26T10:00:00Z",
        "parameters": {"game_id": "0022500001"},
    }
    (root / "identity.json").write_text(json.dumps(request))
    archive.observation(
        {
            **request,
            "raw_path": path,
            "raw_sha256": sha,
            "http_status": 200,
            "received_at": "2026-10-26T10:00:01Z",
            "validated_at": "2026-10-26T10:00:02Z",
        }
    )


def test_explicit_inactive_repair_reuses_bytes_and_preserves_original_availability(
    tmp_path: Path,
) -> None:
    report, archive, source, evidence, manifest = inputs(tmp_path)
    output = tmp_path / "repairs"
    result = prepare_inactive_overlays(report, archive, [evidence], output, now=NOW)
    assert result["patch_count"] == 1 and result["unresolved_identity_rows"] == []
    assert (
        not result["source_accepted"]
        and not result["repairs_applied"]
        and not result["network_access"]
    )
    path = output / result["patches"][0]
    original_patch = path.read_bytes()
    assert prepare_inactive_overlays(report, archive, [evidence], output, now=NOW) == result
    assert path.read_bytes() == original_patch
    patch = json.loads(original_patch)
    assert patch["changes"]["playerteamId"] == "101"
    assert patch["collected_at"] == "2026-10-26T10:00:01Z"
    assert "reason unspecified" in patch["changes"]["comment"]
    repaired = build_seed(
        source,
        manifest,
        archive,
        inventory=json.loads((source / "inventory.json").read_text()),
        repair_paths=(path,),
        now=NOW,
    )
    assert repaired["participation"] == {"played": 2, "did_not_play": 1}
    assert not repaired["quarantine"] and not repaired["source_accepted"]
    assert repaired["available_at"] == NOW.isoformat()
    assert report["row_counts"]["players"] == 2
    assert checksum(source / "PlayerStatistics.csv") == manifest["files"]["PlayerStatistics.csv"]


@pytest.mark.parametrize(
    "mode", ["wrong_game", "wrong_score", "duplicate_player", "active_and_inactive", "future"]
)
def test_invalid_source_cannot_create_overlays(tmp_path: Path, mode: str) -> None:
    report, archive, _, evidence, _ = inputs(tmp_path)
    receipt = json.loads(next((evidence / "observations").glob("*.json")).read_text())
    payload = json.loads((evidence / receipt["raw_path"]).read_text())
    game = payload["boxScoreSummary"]
    if mode == "wrong_game":
        game["gameId"] = "0022500002"
    elif mode == "wrong_score":
        game["homeTeam"]["score"] = 99
    elif mode == "duplicate_player":
        game["awayTeam"]["inactives"] = [{"personId": 203}]
    elif mode == "active_and_inactive":
        game["homeTeam"]["players"].append({"personId": 203})
    write_evidence(evidence, payload)
    if mode == "future":
        obs_path = next((evidence / "observations").glob("*.json"))
        obs = json.loads(obs_path.read_text())
        obs["validated_at"] = "2026-10-28T12:00:00Z"
        obs_path.write_text(json.dumps(obs))
    output = tmp_path / "repairs"
    with pytest.raises(ValueError):
        prepare_inactive_overlays(report, archive, [evidence], output, now=NOW)
    assert not output.exists()


def test_absent_player_stays_unknown_and_corrupted_source_is_refused(tmp_path: Path) -> None:
    report, archive, _, evidence, _ = inputs(tmp_path)
    obs = json.loads(next((evidence / "observations").glob("*.json")).read_text())
    raw = evidence / obs["raw_path"]
    payload = json.loads(raw.read_text())
    payload["boxScoreSummary"]["homeTeam"]["inactives"] = []
    write_evidence(evidence, payload)
    result = prepare_inactive_overlays(report, archive, [evidence], tmp_path / "repairs", now=NOW)
    assert result["patch_count"] == 0
    assert result["unresolved_identity_rows"][0]["player_id"] == "203"
    obs = json.loads(next((evidence / "observations").glob("*.json")).read_text())
    (evidence / obs["raw_path"]).write_bytes(b"corrupt")
    with pytest.raises(ValueError, match="retained receipt"):
        prepare_inactive_overlays(report, archive, [evidence], tmp_path / "blocked", now=NOW)
