"""Interrupted multipart evidence registration resumes without accepting a source."""

from pathlib import Path
from typing import Any

import pytest

from hoop.platform.artifacts import ArtifactError, PrivateArtifacts, Session
from hoop.platform.local_artifacts import LocalArtifacts
from hoop.platform.raw_archives import materialize_raw
from tests.fixtures.storage_client import SETTINGS, MemoryStorage

pytestmark = pytest.mark.postgres


def test_partial_part_registration_is_safe_to_resume(
    migrated: Any, tmp_path: Path, monkeypatch: Any
) -> None:
    from hoop.platform.provenance import digest
    from hoop.platform.raw_archives import encode_raw, retain_archive

    _, conn = migrated
    source = tmp_path / "input"
    body = bytes(range(256)) * 32
    source.write_bytes(body)
    local = LocalArtifacts(tmp_path / "local")
    encoded = encode_raw(
        source, local, original_sha256=digest(body), original_bytes=len(body), part_bytes=127
    )
    store = PrivateArtifacts(Session(SETTINGS, MemoryStorage()))
    original_put = store.put
    calls = 0

    def fail_second(*args: Any, **kwargs: Any) -> Any:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise ArtifactError("injected interruption")
        return original_put(*args, **kwargs)

    monkeypatch.setattr(store, "put", fail_second)
    with pytest.raises(ArtifactError, match="interruption"):
        retain_archive(conn, store, local, encoded)
    assert conn.execute("SELECT count(*) FROM platform.artifacts").fetchone() == (1,)
    assert conn.execute("SELECT count(*) FROM platform.source_checks").fetchone() == (0,)
    monkeypatch.setattr(store, "put", original_put)
    root = retain_archive(conn, store, local, encoded)
    count = conn.execute("SELECT count(*) FROM platform.artifacts").fetchone()[0]
    assert retain_archive(conn, store, local, encoded) == root
    assert conn.execute("SELECT count(*) FROM platform.artifacts").fetchone()[0] == count
    assert materialize_raw(root, store.read, tmp_path / "recovered").read_bytes() == body
