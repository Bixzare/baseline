"""Derive a private backup inventory from an accepted immutable seed graph."""

import argparse
import json
from pathlib import Path
from typing import Any

from hoop.domains.nba.history.seed import plan_seed
from hoop.platform.evidence import EvidenceError
from hoop.platform.local_artifacts import LocalArtifacts, checksum


def prepare(
    archive: Path,
    source_manifest: Path,
    downloads: Path,
    acceptance: Path,
    inventory_raw: Path,
    raw_archives: Path | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    local = LocalArtifacts(archive)
    descriptor = json.loads((archive / "candidate-current.json").read_text())["manifest_artifact"]
    report = {**json.loads(local.verify(descriptor).read_text()), "manifest_artifact": descriptor}
    approved = json.loads(acceptance.read_text())
    if approved.get("kind") != "owner_review":
        raise EvidenceError("Exact owner acceptance required for backup inventory")
    receipts = json.loads(downloads.read_text())
    observations = {
        r["file"]: {
            "requested_at": r["started_at"],
            "received_at": r["finished_at"],
            "sha256": r["sha256"],
        }
        for r in receipts
    }
    if len(observations) != len(receipts):
        raise EvidenceError("Duplicate original download receipts")
    plan = plan_seed(
        report,
        archive,
        json.loads(source_manifest.read_text()),
        approved,
        observations,
        json.loads(raw_archives.read_text()) if raw_archives else None,
    )
    if plan["blockers"]:
        raise EvidenceError("Seed review gates block backup inventory")
    if checksum(inventory_raw) != report["input_identity"]["inventory"]["raw_sha256"]:
        raise EvidenceError("Original game inventory proof differs from candidate")
    files: dict[str, dict[str, Any]] = {}

    def add(label: str, path: Path, sha: str | None = None) -> None:
        if (
            path.is_symlink()
            or path.name.startswith(".env")
            or path.name == "rclone.conf"
            or path.suffix.lower() in {".key", ".pem"}
        ):
            raise EvidenceError("Credential or symlink input refused")
        actual = checksum(path)
        if sha is not None and actual != sha:
            raise EvidenceError("Backup inventory input changed")
        files.setdefault(
            actual,
            {
                "label": label,
                "source": str(path.resolve()),
                "sha256": actual,
                "byte_count": path.stat().st_size,
            },
        )

    for item in [descriptor, *report["artifacts"]]:
        add("seed-object:" + item["sha256"], local.verify(item), item["sha256"])
    for label, path in [
        ("source-manifest", source_manifest),
        ("download-receipts", downloads),
        ("owner-acceptance", acceptance),
        ("game-inventory-proof", inventory_raw),
    ]:
        add(label, path)
    inventory = sorted(files.values(), key=lambda a: a["label"])
    summary = {
        "schema_version": 1,
        "candidate_manifest_sha256": descriptor["sha256"],
        "parser_version": report["parser_version"],
        "scope": "accepted_compact_seed_backup_only",
        "required_files": len(inventory),
        "required_bytes": sum(a["byte_count"] for a in inventory),
        "compact_seed_accepted": True,
        "full_historical_dataset_accepted": False,
        "hosted_fact_import_performed": False,
        "launch_backup_gate_satisfied": False,
        "network_access": False,
    }
    return inventory, summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in [
        "archive",
        "source-manifest",
        "downloads",
        "acceptance",
        "inventory-raw",
        "output",
    ]:
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--raw-archives", type=Path)
    args = parser.parse_args()
    try:
        files, summary = prepare(
            args.archive,
            args.source_manifest,
            args.downloads,
            args.acceptance,
            args.inventory_raw,
            args.raw_archives,
        )
        # Absolute source paths stay in this private ignored inventory, never stdout.
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x", encoding="utf-8") as stream:
            json.dump(files, stream, sort_keys=True, allow_nan=False)
        print(json.dumps(summary, sort_keys=True))
        return 0
    except (EvidenceError, ValueError, KeyError, TypeError, OSError):
        print(json.dumps({"verified": False, "reason_code": "seed_backup_inventory_failed"}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
