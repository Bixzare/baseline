"""Explicit offline archive staging; no source acceptance, network, or database writes."""

import json
from pathlib import Path
from typing import Any

from hoop.platform.local_artifacts import LocalArtifacts
from hoop.platform.raw_archives import encode_raw, verify_archive


def stage_raw_archives(report: dict[str, Any], archive: Path) -> dict[str, Any]:
    store = LocalArtifacts(archive)
    saved = json.loads(store.verify(report["manifest_artifact"]).read_text())
    if any(report.get(key) != value for key, value in saved.items()):
        raise ValueError("Report differs from immutable manifest")
    artifacts = {item["sha256"]: item for item in saved["artifacts"]}
    files = {}
    for name, sha in saved["input_identity"]["files"].items():
        item = artifacts[sha]
        files[name] = encode_raw(
            store.verify(item), store, original_sha256=sha, original_bytes=item["byte_count"]
        )
    return {
        "schema_version": 1,
        "seed_manifest_sha256": report["manifest_artifact"]["sha256"],
        "files": files,
    }


def verify_raw_archives(
    staged: dict[str, Any], report: dict[str, Any], raw: dict[str, Any], store: LocalArtifacts
) -> None:
    if (
        staged.get("schema_version") != 1
        or staged.get("seed_manifest_sha256") != report["manifest_artifact"]["sha256"]
        or set(staged.get("files", {})) != set(raw)
    ):
        raise ValueError("Staged archives belong to another seed")
    for name, item in raw.items():
        original = verify_archive(
            staged["files"][name], lambda part: store.verify(part).read_bytes()
        )
        if original != {"sha256": item["sha256"], "byte_count": item["byte_count"]}:
            raise ValueError("Encoded archive differs from original raw input")
