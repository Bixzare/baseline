"""Accepted immutable source graphs define backup completeness, not a folder scan."""

import json
from pathlib import Path

import pytest

from hoop.domains.nba.history.backup_inventory import prepare
from hoop.domains.nba.sources.seed import build_seed
from hoop.platform.evidence import EvidenceError
from hoop.platform.local_artifacts import LocalArtifacts, checksum
from tests.fixtures.adjudication import NOW, fixture


def setup(tmp_path):
    case = fixture(tmp_path)
    proof = tmp_path / "inventory.bin"
    proof.write_bytes(b"synthetic retained inventory body")
    case["inventory"]["raw_sha256"] = checksum(proof)
    report = build_seed(
        case["source"],
        case["manifest"],
        case["archive"],
        inventory=case["inventory"],
        repair_paths=case["patches"],
        now=NOW,
    )
    source = tmp_path / "source-manifest.json"
    source.write_text(json.dumps(case["manifest"]))
    downloads = tmp_path / "downloads.json"
    downloads.write_text(
        json.dumps(
            [
                {
                    "file": name,
                    "started_at": "2026-10-24T11:59:00Z",
                    "finished_at": case["manifest"]["collected_at"],
                    "sha256": sha,
                }
                for name, sha in case["manifest"]["files"].items()
            ]
        )
    )
    acceptance = tmp_path / "acceptance.json"
    acceptance.write_text(
        json.dumps(
            {
                "kind": "owner_review",
                "manifest_sha256": report["manifest_artifact"]["sha256"],
                "parser_version": report["parser_version"],
                "calendar_convention": "source_calendar_verified",
            }
        )
    )
    return case, report, [case["archive"], source, downloads, acceptance, proof]


def test_inventory_preserves_every_required_object_and_rehydrates_exact_manifest(tmp_path):
    case, report, args = setup(tmp_path)
    unrelated = case["archive"] / "unrelated-private.txt"
    unrelated.write_text("outside reviewed graph")
    files, summary = prepare(*args)
    required = {a["sha256"] for a in [report["manifest_artifact"], *report["artifacts"]]}
    assert required <= {f["sha256"] for f in files}
    assert checksum(unrelated) not in {f["sha256"] for f in files}
    assert len({f["sha256"] for f in files}) == len(files)
    restored = LocalArtifacts(tmp_path / "restored")
    for item in files:
        assert (
            restored.put(Path(item["source"]), kind="archive", format="bin")["sha256"]
            == item["sha256"]
        )
    for descriptor in [report["manifest_artifact"], *report["artifacts"]]:
        assert restored.verify(descriptor).is_file()
    assert summary["required_bytes"] == sum(f["byte_count"] for f in files)
    assert summary["compact_seed_accepted"] and not summary["network_access"]
    assert not summary["launch_backup_gate_satisfied"]
    assert str(tmp_path) not in json.dumps(summary)


@pytest.mark.parametrize(
    "mode", ["pending", "stale_manifest", "wrong_proof", "duplicate_receipt", "changed_object"]
)
def test_incomplete_or_unaccepted_inputs_cannot_produce_inventory(tmp_path, mode):
    case, report, args = setup(tmp_path)
    if mode in {"pending", "stale_manifest"}:
        p = args[3]
        approval = json.loads(p.read_text())
        approval["kind" if mode == "pending" else "manifest_sha256"] = (
            "pending_owner_review" if mode == "pending" else "0" * 64
        )
        p.write_text(json.dumps(approval))
    elif mode == "wrong_proof":
        args[4].write_bytes(b"changed proof")
    elif mode == "duplicate_receipt":
        p = args[2]
        rows = json.loads(p.read_text())
        p.write_text(json.dumps([*rows, rows[0]]))
    else:
        (case["archive"] / report["normalized"]["players"]["path"]).write_bytes(b"corrupt")
    with pytest.raises((EvidenceError, ValueError)):
        prepare(*args)
