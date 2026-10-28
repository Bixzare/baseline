"""Lossless bounded raw archives. Physical objects never claim the original hash."""

import gzip
import hashlib
import json
import os
import re
import tempfile
import zlib
from collections.abc import Callable
from pathlib import Path
from typing import Any

import psycopg

from hoop.platform.artifacts import MAX_BYTES, PrivateArtifacts, retain
from hoop.platform.local_artifacts import LocalArtifacts, checksum
from hoop.platform.provenance import digest

REPRESENTATION = "gzip_parts_v1"
MAX_LOGICAL_BYTES = 1024 * 1024 * 1024
MAX_PARTS = 128
BUFFER_BYTES = 1024 * 1024
Read = Callable[[dict[str, Any]], bytes]


class RawArchiveError(ValueError):
    """Archive validation failed without exposing transport credentials."""


def _hash(value: Any) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def validate_descriptor(archive: dict[str, Any]) -> None:
    try:
        original, parts = archive["original"], archive["parts"]
        if (
            type(archive["schema_version"]) is not int
            or archive["schema_version"] != 1
            or archive["representation"] != REPRESENTATION
            or archive["encoding"] != {"codec": "gzip", "level": 6, "mtime": 0}
            or not _hash(original["sha256"])
            or type(original["byte_count"]) is not int
            or not 0 <= original["byte_count"] <= MAX_LOGICAL_BYTES
            or not _hash(archive["encoded_sha256"])
            or type(archive["encoded_byte_count"]) is not int
            or not isinstance(parts, list)
            or not 1 <= len(parts) <= MAX_PARTS
        ):
            raise RawArchiveError("invalid_raw_archive_descriptor")
        for part in parts:
            if (
                not _hash(part["sha256"])
                or type(part["byte_count"]) is not int
                or not 0 < part["byte_count"] <= MAX_BYTES
                or part["kind"] != "raw"
                or part["format"] != "gzip_part"
                or part["schema_version"] != 1
            ):
                raise RawArchiveError("invalid_raw_archive_part")
        if archive["encoded_byte_count"] != sum(p["byte_count"] for p in parts):
            raise RawArchiveError("raw_archive_encoded_size_mismatch")
    except (KeyError, TypeError, AttributeError):
        raise RawArchiveError("invalid_raw_archive_descriptor") from None


def _read(part: dict[str, Any], read: Read) -> bytes:
    size = part["byte_count"]
    if type(size) is not int or not 0 <= size <= MAX_BYTES:
        raise RawArchiveError("physical_object_exceeds_bound")
    body = read(part)
    if len(body) != size or digest(body) != part["sha256"]:
        raise RawArchiveError("raw_archive_physical_hash_mismatch")
    return body


def verify_archive(
    archive: dict[str, Any], read: Read, *, write: Callable[[bytes], Any] | None = None
) -> dict[str, Any]:
    """Decode one gzip member with bounded output; reject concatenation and trailing bytes."""
    validate_descriptor(archive)
    original = archive["original"]
    encoded_hash, logical_hash = hashlib.sha256(), hashlib.sha256()
    decoder = zlib.decompressobj(16 + zlib.MAX_WBITS)
    count = 0
    try:
        for part in archive["parts"]:
            body = _read(part, read)
            encoded_hash.update(body)
            data = body
            while True:
                output = decoder.decompress(data, BUFFER_BYTES)
                count += len(output)
                if count > original["byte_count"] or count > MAX_LOGICAL_BYTES:
                    raise RawArchiveError("raw_archive_logical_size_exceeded")
                logical_hash.update(output)
                if write is not None:
                    write(output)
                if decoder.unused_data:
                    raise RawArchiveError("raw_archive_trailing_data")
                data = decoder.unconsumed_tail
                if not data and len(output) < BUFFER_BYTES:
                    break
        if not decoder.eof:
            raise RawArchiveError("raw_archive_truncated")
    except zlib.error:
        raise RawArchiveError("raw_archive_invalid_gzip") from None
    if encoded_hash.hexdigest() != archive["encoded_sha256"]:
        raise RawArchiveError("raw_archive_encoded_hash_mismatch")
    if count != original["byte_count"] or logical_hash.hexdigest() != original["sha256"]:
        raise RawArchiveError("raw_archive_original_hash_mismatch")
    return dict(original)


def encode_raw(
    source: Path,
    local: LocalArtifacts,
    *,
    original_sha256: str,
    original_bytes: int,
    part_bytes: int = MAX_BYTES,
) -> dict[str, Any]:
    if (
        not _hash(original_sha256)
        or type(original_bytes) is not int
        or not 0 <= original_bytes <= MAX_LOGICAL_BYTES
        or type(part_bytes) is not int
        or not 1 <= part_bytes <= MAX_BYTES
        or source.stat().st_size != original_bytes
    ):
        raise RawArchiveError("invalid_raw_archive_input")
    pending = local.root / "pending"
    pending.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=pending) as temp:
        compressed = Path(temp) / "raw.gz"
        observed, count = hashlib.sha256(), 0
        with source.open("rb") as incoming, compressed.open("wb") as outgoing:
            with gzip.GzipFile(
                filename="", mode="wb", fileobj=outgoing, compresslevel=6, mtime=0
            ) as zipped:
                for body in iter(lambda: incoming.read(BUFFER_BYTES), b""):
                    count += len(body)
                    if count > original_bytes:
                        raise RawArchiveError("raw_archive_input_changed")
                    observed.update(body)
                    zipped.write(body)
        if count != original_bytes or observed.hexdigest() != original_sha256:
            raise RawArchiveError("raw_archive_input_hash_mismatch")
        if (compressed.stat().st_size + part_bytes - 1) // part_bytes > MAX_PARTS:
            raise RawArchiveError("raw_archive_part_budget_exceeded")
        parts = []
        with compressed.open("rb") as incoming:
            for body in iter(lambda: incoming.read(part_bytes), b""):
                part_path = Path(temp) / "part"
                part_path.write_bytes(body)
                parts.append(local.put(part_path, kind="raw", format="gzip_part"))
        archive = {
            "schema_version": 1,
            "representation": REPRESENTATION,
            "encoding": {"codec": "gzip", "level": 6, "mtime": 0},
            "original": {"sha256": original_sha256, "byte_count": original_bytes},
            "encoded_sha256": checksum(compressed),
            "encoded_byte_count": compressed.stat().st_size,
            "parts": parts,
        }
        verify_archive(archive, lambda part: local.verify(part).read_bytes())
        return archive


def retain_archive(
    conn: psycopg.Connection[Any],
    store: PrivateArtifacts,
    local: LocalArtifacts,
    archive: dict[str, Any],
) -> dict[str, Any]:
    # Verify all local bytes before the first remote write. Each retain operation
    # closes its own short SQL registration; network is never inside a transaction.
    verify_archive(archive, lambda part: local.verify(part).read_bytes())
    parts = [
        retain(
            conn,
            store,
            local.verify(part).read_bytes(),
            kind="raw",
            format="gzip_part",
            manifest={},
        )
        for part in archive["parts"]
    ]
    remote = {**archive, "parts": parts}
    verify_archive(remote, store.read)
    body = json.dumps(remote, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    original = archive["original"]
    return retain(
        conn,
        store,
        body,
        kind="raw",
        format="json",
        manifest={
            "representation": REPRESENTATION,
            "original_sha256": original["sha256"],
            "original_byte_count": original["byte_count"],
            "part_artifact_ids": [p["artifact_id"] for p in parts],
        },
    )


def _materialize(
    original: dict[str, Any], destination: Path, produce: Callable[[Callable[[bytes], Any]], Any]
) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(dir=destination.parent, prefix=".raw-pending-")
    try:
        with os.fdopen(handle, "wb") as stream:
            produce(stream.write)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temporary, destination)
        except FileExistsError:
            if (
                destination.stat().st_size != original["byte_count"]
                or checksum(destination) != original["sha256"]
            ):
                raise RawArchiveError("raw_archive_destination_conflict") from None
        return destination
    finally:
        Path(temporary).unlink(missing_ok=True)


def materialize_archive(archive: dict[str, Any], read: Read, destination: Path) -> Path:
    validate_descriptor(archive)
    return _materialize(
        archive["original"], destination, lambda write: verify_archive(archive, read, write=write)
    )


def _root(artifact: dict[str, Any], read: Read) -> tuple[dict[str, Any] | None, bytes]:
    if artifact.get("kind") != "raw":
        raise RawArchiveError("raw_artifact_required")
    body = _read(artifact, read)
    if artifact["format"] == "csv":
        return None, body
    if artifact["format"] != "json":
        raise RawArchiveError("unsupported_raw_representation")
    try:
        archive = json.loads(body)
        validate_descriptor(archive)
        original = archive["original"]
        expected = {
            "representation": REPRESENTATION,
            "original_sha256": original["sha256"],
            "original_byte_count": original["byte_count"],
            "part_artifact_ids": [p["artifact_id"] for p in archive["parts"]],
        }
        if artifact.get("manifest") != expected:
            raise RawArchiveError("raw_root_manifest_mismatch")
    except (ValueError, KeyError, TypeError):
        raise RawArchiveError("invalid_raw_archive_root") from None
    return archive, body


def verify_raw(artifact: dict[str, Any], read: Read) -> dict[str, Any]:
    """Verify logical raw content without materializing the decompressed file."""
    archive, body = _root(artifact, read)
    if archive is None:
        return {"sha256": digest(body), "byte_count": len(body)}
    return verify_archive(archive, read)


def materialize_raw(artifact: dict[str, Any], read: Read, destination: Path) -> Path:
    """Recover a registered archive or legacy CSV with exclusive finalization."""
    archive, body = _root(artifact, read)
    if archive is None:
        return _materialize(artifact, destination, lambda write: write(body))
    return materialize_archive(archive, read, destination)
