"""Content-addressed local artifacts with atomic, exclusive finalization."""

import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any


def checksum(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def atomic_json(path: Path, value: dict[str, Any]) -> None:
    """Replace a mutable checkpoint/pointer, never an immutable artifact."""
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(dir=path.parent, prefix=".pending-")
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(value, stream, sort_keys=True, allow_nan=False)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


class LocalArtifacts:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def verify(self, descriptor: dict[str, Any]) -> Path:
        sha = descriptor["sha256"]
        if (
            not isinstance(sha, str)
            or len(sha) != 64
            or any(c not in "0123456789abcdef" for c in sha)
        ):
            raise ValueError("Invalid artifact checksum")
        expected = f"objects/{sha[:2]}/{sha}"
        if descriptor["path"] != expected:
            raise ValueError("Artifact path must match its checksum")
        path = (self.root / expected).resolve()
        if not path.is_relative_to(self.root) or path.stat().st_size != descriptor["byte_count"]:
            raise ValueError("Artifact path or size mismatch")
        if checksum(path) != sha:
            raise ValueError("Artifact checksum mismatch")
        return path

    def put(self, source: Path, *, kind: str, format: str) -> dict[str, Any]:
        pending = self.root / "pending"
        pending.mkdir(exist_ok=True)
        handle, temporary = tempfile.mkstemp(dir=pending)
        digest = hashlib.sha256()
        size = 0
        try:
            with os.fdopen(handle, "wb") as outgoing, source.open("rb") as incoming:
                for chunk in iter(lambda: incoming.read(1024 * 1024), b""):
                    outgoing.write(chunk)
                    digest.update(chunk)
                    size += len(chunk)
                outgoing.flush()
                os.fsync(outgoing.fileno())
            sha = digest.hexdigest()
            relative = f"objects/{sha[:2]}/{sha}"
            destination = self.root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            descriptor = {
                "sha256": sha,
                "path": relative,
                "byte_count": size,
                "kind": kind,
                "format": format,
                "schema_version": 1,
            }
            try:
                os.link(temporary, destination)
            except FileExistsError:
                self.verify(descriptor)
            self.verify(descriptor)
            return descriptor
        finally:
            Path(temporary).unlink(missing_ok=True)
