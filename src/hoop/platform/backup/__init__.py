"""Independent content-addressed backup sets and explicit remote readback."""

import json
import os
import re
import shutil
import time
from pathlib import Path
from typing import Any, Protocol
from uuid import UUID, uuid4

from hoop.platform.local_artifacts import LocalArtifacts
from hoop.platform.prepared import encoded
from hoop.platform.provenance import digest, parse_time


class BackupError(RuntimeError):
    """Sanitized backup failure. Never includes subprocess output or credentials."""


class Remote(Protocol):
    evidence_kind: str

    def download(self, relative: str, destination: Path, limit: int) -> None: ...


def contained(root: Path, relative: str) -> Path:
    if not isinstance(relative, str) or "\\" in relative:
        raise BackupError("unsafe_backup_path")
    if (
        not relative
        or relative.startswith("/")
        or any(p in {"", ".", ".."} for p in relative.split("/"))
    ):
        raise BackupError("unsafe_backup_path")
    target = (root / relative).resolve()
    if not target.is_relative_to(root.resolve()):
        raise BackupError("unsafe_backup_path")
    return target


def exclusive(path: Path, body: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("xb") as stream:
            stream.write(body)
            stream.flush()
            os.fsync(stream.fileno())
    except FileExistsError:
        if path.read_bytes() != body:
            raise BackupError("conflicting_backup_file") from None


def verify_set(root: Path, backup_id: str, expected_hash: str) -> dict[str, Any]:
    identity = str(UUID(backup_id))
    base = root / "sets" / identity
    body = (base / "manifest.json").read_bytes()
    if len(body) > 8 * 1024 * 1024 or digest(body) != expected_hash:
        raise BackupError("backup_manifest_hash_mismatch")
    if (base / "COMPLETE").read_text(encoding="ascii") != expected_hash:
        raise BackupError("backup_set_incomplete")
    manifest = json.loads(body)
    if not isinstance(manifest, dict):
        raise BackupError("backup_manifest_invalid")
    if manifest["backup_id"] != identity or manifest["schema_version"] != 1:
        raise BackupError("backup_manifest_identity_mismatch")
    parse_time(manifest["represented_cutoff"])
    if not manifest["files"] or len(manifest["files"]) > 100000:
        raise BackupError("backup_file_inventory_invalid")
    labels = set()
    for item in manifest["files"]:
        if item["label"] in labels:
            raise BackupError("duplicate_backup_label")
        labels.add(item["label"])
        try:
            LocalArtifacts(root).verify(item)
        except (OSError, ValueError, KeyError):
            raise BackupError("backup_file_missing_or_corrupt") from None
    if "database" not in labels:
        raise BackupError("backup_database_missing")
    for item in manifest.get("artifact_inventory", []):
        match = next(
            (f for f in manifest["files"] if f["label"] == "artifact:" + str(item["artifact_id"])),
            None,
        )
        if match is None or any(match[k] != item[k] for k in ["sha256", "byte_count"]):
            raise BackupError("required_artifact_not_in_complete_set")
    for item in manifest.get("archive_inventory", []):
        match = next(
            (f for f in manifest["files"] if f["label"] == "archive:" + item["label"]), None
        )
        if match is None or any(match[k] != item[k] for k in ["sha256", "byte_count"]):
            raise BackupError("required_archive_not_in_complete_set")
    return manifest


def finalize(
    stage: Path, destination: Path, manifest: dict[str, Any], *, max_seconds: float = 1800
) -> str:
    deadline = time.monotonic() + max_seconds
    stage, destination = stage.resolve(), destination.resolve()
    if (
        stage == destination
        or stage.is_relative_to(destination)
        or destination.is_relative_to(stage)
    ):
        raise BackupError("staging_must_be_independent_of_sync_folder")
    body = encoded(manifest)
    sha = digest(body)
    identity = str(UUID(manifest["backup_id"]))
    base = stage / "sets" / identity
    exclusive(base / "manifest.json", body)
    exclusive(base / "COMPLETE", sha.encode("ascii"))
    verify_set(stage, identity, sha)
    required = sum(item["byte_count"] for item in manifest["files"])
    destination.mkdir(parents=True, exist_ok=True)
    if shutil.disk_usage(destination).free < required + 16 * 1024 * 1024:
        raise BackupError("insufficient_backup_disk_capacity")
    store = LocalArtifacts(destination)
    for item in manifest["files"]:
        if time.monotonic() >= deadline:
            raise BackupError("backup_copy_budget_exhausted")
        descriptor = store.put(
            contained(stage, item["path"]), kind=item["kind"], format=item["format"]
        )
        if descriptor["sha256"] != item["sha256"] or descriptor["byte_count"] != item["byte_count"]:
            raise BackupError("backup_copy_mismatch")
    exclusive(destination / "sets" / identity / "manifest.json", body)
    # The completion marker is last. A partially synchronized set cannot pass verification.
    exclusive(destination / "sets" / identity / "COMPLETE", sha.encode("ascii"))
    verify_set(destination, identity, sha)
    return sha


def remote_readback(
    remote: Remote,
    readback: Path,
    *,
    backup_id: str,
    expected_hash: str,
    source_project: str,
    forbidden_roots: list[Path],
    max_seconds: float = 1800,
) -> dict[str, Any]:
    deadline = time.monotonic() + max_seconds
    readback = readback.resolve()
    if any(
        readback == p.resolve()
        or readback.is_relative_to(p.resolve())
        or p.resolve().is_relative_to(readback)
        for p in forbidden_roots
    ):
        raise BackupError("remote_readback_must_use_independent_location")
    if readback.exists():
        raise BackupError("remote_readback_requires_new_directory")
    readback.mkdir(parents=True)
    identity = str(UUID(backup_id))
    prefix = "sets/" + identity + "/"
    for name in ["COMPLETE", "manifest.json"]:
        remote.download(
            prefix + name,
            contained(readback, prefix + name),
            65 if name == "COMPLETE" else 8 * 1024 * 1024 + 1,
        )
    body = contained(readback, prefix + "manifest.json").read_bytes()
    if len(body) > 8 * 1024 * 1024 or digest(body) != expected_hash:
        raise BackupError("remote_manifest_mismatch")
    manifest = json.loads(body)
    if manifest.get("source_project") != source_project:
        raise BackupError("remote_project_identity_mismatch")
    if manifest.get("backup_id") != identity or len(manifest.get("files", [])) > 100000:
        raise BackupError("remote_manifest_identity_mismatch")
    objects: dict[str, int] = {}
    for item in manifest["files"]:
        relative = item["path"]
        if (
            not isinstance(relative, str)
            or not re.fullmatch(r"objects/[0-9a-f]{2}/[0-9a-f]{64}", relative)
            or type(item["byte_count"]) is not int
            or item["byte_count"] < 0
        ):
            raise BackupError("unsafe_remote_object_path")
        limit = item["byte_count"] + 1
        if relative in objects and objects[relative] != limit:
            raise BackupError("conflicting_remote_object_size")
        objects[relative] = limit
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise BackupError("remote_readback_budget_exhausted")
    batch = getattr(remote, "download_many", None)
    if callable(batch):
        batch(objects, readback, max_seconds=remaining)
    else:
        for relative, limit in objects.items():
            if time.monotonic() >= deadline:
                raise BackupError("remote_readback_budget_exhausted")
            remote.download(relative, contained(readback, relative), limit)
    verify_set(readback, identity, expected_hash)
    return {
        "verification_id": str(uuid4()),
        "backup_id": identity,
        "manifest_sha256": expected_hash,
        "represented_cutoff": manifest["represented_cutoff"],
        "remote_kind": remote.evidence_kind,
        "off_device_verified": remote.evidence_kind == "onedrive_rclone_readback",
        "files_verified": len(manifest["files"]),
        "bytes_verified": sum(i["byte_count"] for i in manifest["files"]),
    }


class ArchiveArtifacts:
    """Explicit read-only recovery mapping; preserve original Storage URIs in rows."""

    def __init__(self, root: Path, backup_id: str, manifest_hash: str):
        self.root = root
        self.manifest = verify_set(root, backup_id, manifest_hash)
        self.references = {a["storage_uri"]: a for a in self.manifest.get("artifact_inventory", [])}

    def read(self, descriptor: dict[str, Any]) -> bytes:
        original = self.references.get(descriptor["storage_uri"])
        if original is None or any(original[k] != descriptor[k] for k in ["sha256", "byte_count"]):
            raise BackupError("artifact_not_in_restored_snapshot")
        entry = next(
            f
            for f in self.manifest["files"]
            if f["label"] == "artifact:" + str(original["artifact_id"])
        )
        path = LocalArtifacts(self.root).verify(entry)
        return path.read_bytes()
