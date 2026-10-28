"""Exact raw recovery, bounded decoding, tampering and safe local finalization."""

import copy
import gzip
from pathlib import Path
from typing import Any

import pytest

from hoop.platform.local_artifacts import LocalArtifacts
from hoop.platform.provenance import digest
from hoop.platform.raw_archives import (
    MAX_LOGICAL_BYTES,
    MAX_PARTS,
    RawArchiveError,
    encode_raw,
    materialize_archive,
    materialize_raw,
    verify_archive,
)


def staged(
    tmp_path: Path, body: bytes = bytes(range(256)) * 32
) -> tuple[LocalArtifacts, dict[str, Any], bytes]:
    source = tmp_path / "input"
    source.write_bytes(body)
    store = LocalArtifacts(tmp_path / "objects")
    archive = encode_raw(
        source, store, original_sha256=digest(body), original_bytes=len(body), part_bytes=127
    )
    return store, archive, body


def read(store: LocalArtifacts, item: dict[str, Any]) -> bytes:
    return store.verify(item).read_bytes()


def replace_encoded(store: LocalArtifacts, archive: dict[str, Any], body: bytes) -> dict[str, Any]:
    path = store.root / "new-part"
    path.write_bytes(body)
    return {
        **archive,
        "encoded_sha256": digest(body),
        "encoded_byte_count": len(body),
        "parts": [store.put(path, kind="raw", format="gzip_part")],
    }


def test_multipart_roundtrip_reuse_and_domain_independence(tmp_path: Path) -> None:
    store, archive, body = staged(tmp_path)
    assert len(archive["parts"]) > 1
    assert all(p["byte_count"] <= 127 for p in archive["parts"])
    assert verify_archive(archive, lambda part: read(store, part)) == {
        "sha256": digest(body),
        "byte_count": 8192,
    }
    output = tmp_path / "recovered"
    materialize_archive(archive, lambda part: read(store, part), output)
    assert output.read_bytes() == body
    assert materialize_archive(archive, lambda part: read(store, part), output) == output
    assert not list(tmp_path.glob(".raw-pending-*"))
    assert (
        encode_raw(
            tmp_path / "input",
            store,
            original_sha256=digest(body),
            original_bytes=len(body),
            part_bytes=127,
        )
        == archive
    )


def test_original_hash_mismatch_never_finalizes_source(tmp_path: Path) -> None:
    source = tmp_path / "input"
    source.write_bytes(b"card-match-history")
    store = LocalArtifacts(tmp_path / "archive")
    with pytest.raises(RawArchiveError, match="input_hash_mismatch"):
        encode_raw(source, store, original_sha256="0" * 64, original_bytes=18)
    assert not list((store.root / "pending").iterdir())
    assert not (store.root / "objects").exists()


@pytest.mark.parametrize(
    "mode", ["corrupt", "missing", "reordered", "original_hash", "encoded_hash"]
)
def test_corruption_or_missing_parts_never_produce_final_file(tmp_path: Path, mode: str) -> None:
    store, archive, _ = staged(tmp_path)
    if mode == "corrupt":
        store.verify(archive["parts"][0]).write_bytes(b"invalid")
    elif mode == "missing":
        store.verify(archive["parts"][0]).unlink()
    elif mode == "reordered":
        archive["parts"].reverse()
    elif mode == "original_hash":
        archive["original"]["sha256"] = "0" * 64
    else:
        archive["encoded_sha256"] = "0" * 64
    destination = tmp_path / "recovered"
    with pytest.raises((ValueError, OSError)):
        materialize_archive(archive, lambda part: read(store, part), destination)
    assert not destination.exists()
    assert not list(tmp_path.glob(".raw-pending-*"))


@pytest.mark.parametrize("mode", ["truncated", "trailing", "concatenated", "logical_size"])
def test_gzip_attacks_fail_even_with_correct_physical_hashes(tmp_path: Path, mode: str) -> None:
    store, archive, body = staged(tmp_path)
    compressed = gzip.compress(body, compresslevel=6, mtime=0)
    if mode == "truncated":
        compressed = compressed[:-6]
    elif mode == "trailing":
        compressed += b"unclaimed data"
    elif mode == "concatenated":
        compressed += gzip.compress(b"second member", mtime=0)
    else:
        archive["original"]["byte_count"] = 8
    archive = replace_encoded(store, archive, compressed)
    with pytest.raises(RawArchiveError):
        verify_archive(archive, lambda part: read(store, part))


@pytest.mark.parametrize("mode", ["oversized", "too_many_parts", "unsupported_codec", "part_size"])
def test_descriptor_budgets_reject_before_read(tmp_path: Path, mode: str) -> None:
    _, archive, _ = staged(tmp_path)
    if mode == "oversized":
        archive["original"]["byte_count"] = MAX_LOGICAL_BYTES + 1
    elif mode == "too_many_parts":
        archive["parts"] *= MAX_PARTS
    elif mode == "part_size":
        archive["parts"][0]["byte_count"] = 16 * 1024 * 1024 + 1
    else:
        archive["encoding"]["codec"] = "pickle"

    def forbidden(part: dict[str, Any]) -> bytes:
        raise AssertionError("Invalid descriptor must not read parts")

    with pytest.raises(RawArchiveError):
        verify_archive(archive, forbidden)


def test_large_decompression_is_streamed_and_conflicting_destination_survives(
    tmp_path: Path,
) -> None:
    store, archive, body = staged(tmp_path, b"A" * (4 * 1024 * 1024))
    sizes = []
    verify_archive(
        archive, lambda part: read(store, part), write=lambda block: sizes.append(len(block))
    )
    assert sum(sizes) == len(body)
    assert max(sizes) <= 1024 * 1024
    destination = tmp_path / "existing"
    destination.write_bytes(b"preserve unrelated bytes")
    with pytest.raises(RawArchiveError, match="destination_conflict"):
        materialize_archive(archive, lambda part: read(store, part), destination)
    assert destination.read_bytes() == b"preserve unrelated bytes"


def test_legacy_direct_raw_remains_readable(tmp_path: Path) -> None:
    store = LocalArtifacts(tmp_path / "archive")
    source = tmp_path / "input"
    source.write_bytes(b"game,score\nfixture,12\n")
    direct = store.put(source, kind="raw", format="csv")
    assert (
        materialize_raw(direct, lambda part: read(store, part), tmp_path / "restored").read_bytes()
        == source.read_bytes()
    )
    forged = copy.deepcopy(direct)
    forged["kind"] = "models"
    with pytest.raises(RawArchiveError, match="raw_artifact_required"):
        materialize_raw(forged, lambda part: read(store, part), tmp_path / "forbidden")


def test_backup_reconstructs_original_from_saved_parts_and_rejects_missing_part(
    tmp_path: Path,
) -> None:
    import json
    from uuid import uuid4

    from hoop.platform.backup import BackupError
    from hoop.platform.backup.database import verify_raw_inputs

    store, archive, body = staged(tmp_path)
    inventory, files, parts = [], [], []
    for part in archive["parts"]:
        remote = {k: v for k, v in part.items() if k != "path"}
        remote.update(
            artifact_id=str(uuid4()),
            storage_uri="supabase://fixture/raw/" + part["sha256"],
            manifest={},
        )
        inventory.append(remote)
        files.append({**part, "label": "artifact:" + remote["artifact_id"]})
        parts.append(remote)
    payload = {**archive, "parts": parts}
    source = tmp_path / "root.json"
    source.write_text(json.dumps(payload))
    local_root = store.put(source, kind="raw", format="json")
    root = {k: v for k, v in local_root.items() if k != "path"}
    root.update(
        artifact_id=str(uuid4()),
        storage_uri="supabase://fixture/raw/" + local_root["sha256"],
        manifest={
            "representation": "gzip_parts_v1",
            "original_sha256": digest(body),
            "original_byte_count": len(body),
            "part_artifact_ids": [p["artifact_id"] for p in parts],
        },
    )
    inventory.append(root)
    files.append({**local_root, "label": "artifact:" + root["artifact_id"]})
    manifest = {"artifact_inventory": inventory, "files": files}
    assert verify_raw_inputs(manifest, store.root) == {
        "encoded_files_verified": 1,
        "original_bytes_verified": 8192,
    }
    files.pop(0)
    with pytest.raises(BackupError, match="reconstruction_failed"):
        verify_raw_inputs(manifest, store.root)
