"""Platform artifacts also work for arbitrary non-NBA bytes."""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from hoop.platform.local_artifacts import LocalArtifacts


def test_concurrent_content_addressed_put_has_one_immutable_object(tmp_path: Path) -> None:
    source = tmp_path / "synthetic-other-domain.txt"
    source.write_bytes(b"a synthetic match outcome\n" * 100)
    store = LocalArtifacts(tmp_path / "archive")

    def write() -> dict[str, object]:
        return store.put(source, kind="synthetic_second_domain", format="text")

    with ThreadPoolExecutor(max_workers=2) as pool:
        first, second = list(pool.map(lambda _: write(), range(2)))
    assert first == second
    assert store.verify(first).read_bytes() == source.read_bytes()
    assert len(list((store.root / "objects").glob("*/*"))) == 1


def test_artifact_corruption_and_path_escape_are_rejected(tmp_path: Path) -> None:
    source = tmp_path / "input.txt"
    source.write_text("fixture")
    store = LocalArtifacts(tmp_path / "archive")
    item = store.put(source, kind="fixture", format="text")
    with pytest.raises(ValueError, match="path"):
        store.verify({**item, "path": "../input.txt"})
    store.verify(item).write_bytes(b"corrupt")
    with pytest.raises(ValueError, match="mismatch"):
        store.put(source, kind="fixture", format="text")
