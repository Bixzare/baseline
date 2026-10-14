"""Immutable, credential-free observations and cutoff checks."""

import copy
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4


def utc(value: datetime) -> str:
    if value.tzinfo is None:
        raise ValueError("Timestamp must be timezone-aware")
    return value.astimezone(UTC).isoformat()


def parse_time(value: str) -> datetime:
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("Timestamp must include a timezone")
    return result.astimezone(UTC)


def digest(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


class Archive:
    """Deduplicate raw bytes, never overwrite an earlier observation."""

    def __init__(self, root: Path) -> None:
        self.root = root
        (root / "raw").mkdir(parents=True, exist_ok=True)
        (root / "observations").mkdir(exist_ok=True)

    def raw(self, body: bytes) -> tuple[str, str]:
        checksum = digest(body)
        relative = f"raw/{checksum}.bin"
        path = self.root / relative
        try:
            with path.open("xb") as stream:
                stream.write(body)
        except FileExistsError:
            if digest(path.read_bytes()) != checksum:
                raise ValueError(f"Archived raw bytes changed: {relative}") from None
        return checksum, relative

    def observation(self, manifest: dict[str, Any]) -> dict[str, Any]:
        observation_id = uuid4().hex
        result = copy.deepcopy({**manifest, "observation_id": observation_id})
        with (self.root / "observations" / f"{observation_id}.json").open("x") as stream:
            json.dump(result, stream, indent=2, sort_keys=True, allow_nan=False)
        return result

    def verify(self) -> int:
        count = 0
        for path in sorted((self.root / "observations").glob("*.json")):
            manifest = json.loads(path.read_text())
            relative = manifest.get("raw_path")
            if relative is not None:
                target = (self.root / relative).resolve()
                if not target.is_relative_to((self.root / "raw").resolve()):
                    raise ValueError("Raw path escapes archive")
                if digest(target.read_bytes()) != manifest["raw_sha256"]:
                    raise ValueError(f"Checksum mismatch for {path.name}")
            count += 1
        if not count:
            raise ValueError("Archive contains no observations")
        return count


def known_by(manifest: dict[str, Any], cutoff: datetime, *, purpose: str = "input") -> bool:
    """Source/event timestamps cannot backdate a collected or validated input."""
    if cutoff.tzinfo is None:
        raise ValueError("Cutoff must be timezone-aware")
    if manifest.get("outcome") != "verified_sample":
        return False
    if purpose == "roster" and manifest.get("capability") != "roster":
        return False
    received = manifest.get("received_at")
    validated = manifest.get("validated_at")
    if received is None or validated is None:
        return False
    return parse_time(received) <= parse_time(validated) <= cutoff
