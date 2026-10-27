"""Domain-independent prepared entries and immutable local snapshot handling."""

import json
import math
import time
from pathlib import Path
from typing import Any
from uuid import uuid4

import psycopg

from hoop.platform.artifacts import PrivateArtifacts, retain
from hoop.platform.evidence import EvidenceError, register
from hoop.platform.local_artifacts import LocalArtifacts, atomic_json
from hoop.platform.provenance import digest


def encoded(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, allow_nan=False, separators=(",", ":"), default=str
    ).encode()


def validate_entries(entries: list[dict[str, Any]]) -> None:
    seen = set()
    if not entries:
        raise EvidenceError("An empty cohort is not a successful preparation")
    for entry in entries:
        key = tuple(entry.get(field) for field in ["subject_type", "subject_id", "target"])
        if (
            not all(isinstance(part, str) and part for part in key)
            or key in seen
            or not entry.get("unit")
        ):
            raise EvidenceError("Invalid or duplicate prepared slot")
        seen.add(key)
        value = entry.get("value")
        reason = entry.get("reason_code")
        if value is None:
            if not isinstance(reason, str) or not reason:
                raise EvidenceError("Abstention reason required")
        elif type(value) not in {float, int} or not math.isfinite(value) or reason is not None:
            raise EvidenceError("Numeric entry must be finite and have no abstention reason")


def save_local(prepared: dict[str, Any], destination: Path) -> dict[str, Any]:
    validate_entries(prepared["entries"])
    if prepared.get("official_publication") is not False:
        raise EvidenceError("Prepared snapshots cannot assert official publication")
    store = LocalArtifacts(destination)
    descriptors = {}
    import tempfile

    for name in ["cohort", "features", "descriptor"]:
        value = prepared[name]
        with tempfile.TemporaryDirectory(dir=store.root) as temp:
            path = Path(temp) / f"{name}.json"
            path.write_bytes(encoded(value))
            descriptors[name] = store.put(path, kind=name, format="json")
    identity = digest(encoded(prepared))
    manifest = {
        "snapshot_id": identity,
        "objects": descriptors,
        "prepared": prepared,
        "official_publication": False,
    }
    path = destination / "snapshots" / f"{identity}.json"
    reused = path.exists()
    if reused:
        previous = json.loads(path.read_text())
        descriptor = previous.pop("manifest_artifact")
        if json.loads(store.verify(descriptor).read_text()) != previous:
            raise EvidenceError("Prepared manifest content changed")
        if previous != json.loads(encoded(manifest)):
            raise EvidenceError("Prepared snapshot differs from its immutable content")
        for descriptor in previous["objects"].values():
            store.verify(descriptor)
    else:
        # Content itself is an immutable artifact; this pointer is only an index.
        with tempfile.TemporaryDirectory(dir=store.root) as temp:
            file = Path(temp) / "prepared.json"
            file.write_bytes(encoded(manifest))
            descriptor = store.put(file, kind="prepared", format="json")
        atomic_json(path, {"manifest_artifact": descriptor, **json.loads(encoded(manifest))})
    # Verify the content artifact before reporting a usable prepared snapshot.
    saved = json.loads(path.read_text())
    if "manifest_artifact" in saved:
        immutable = json.loads(store.verify(saved["manifest_artifact"]).read_text())
        if immutable != json.loads(encoded(manifest)):
            raise EvidenceError("Prepared manifest identity mismatch")
    atomic_json(
        destination / "current.json", {"snapshot_id": identity, "official_publication": False}
    )
    return {
        "snapshot_id": identity,
        "reused": reused,
        "objects": descriptors,
        "official_publication": False,
    }


def retain_prepared(
    conn: psycopg.Connection[Any], store: PrivateArtifacts, prepared: dict[str, Any]
) -> dict[str, Any]:
    validate_entries(prepared["entries"])
    version = prepared["descriptor"]
    if (
        prepared.get("official_publication") is not False
        or digest(encoded(version["configuration"])) != version["config_hash"]
    ):
        raise EvidenceError("Prepared configuration or publication state is invalid")
    started = time.monotonic()
    run_id = prepared["run_id"]
    register(
        conn,
        "runs",
        {
            "run_id": run_id,
            "operation": "prepare",
            "domain": version["domain"],
            "environment": prepared["environment"],
            "code_version": version["code_version"],
            "config_hash": version["config_hash"],
        },
    )
    register(
        conn,
        "run_events",
        {
            "run_event_id": str(uuid4()),
            "run_id": run_id,
            "state": "started",
            "reason_code": None,
            "details": {},
        },
    )
    try:
        config = retain(
            conn,
            store,
            encoded(version["configuration"]),
            kind="reports",
            format="json",
            manifest={},
        )
        objects = {
            name: retain(
                conn, store, encoded(prepared[name]), kind="features", format="json", manifest={}
            )
            for name in ["cohort", "features"]
        }
        objects["prepared"] = retain(
            conn, store, encoded(prepared), kind="reports", format="json", manifest={}
        )
    except Exception:
        register(
            conn,
            "run_events",
            {
                "run_event_id": str(uuid4()),
                "run_id": run_id,
                "state": "failed",
                "reason_code": "prepared_artifact_failed",
                "details": {
                    "counts": {},
                    "duration_ms": round((time.monotonic() - started) * 1000),
                },
            },
        )
        raise
    register(
        conn,
        "run_events",
        {
            "run_event_id": str(uuid4()),
            "run_id": run_id,
            "state": "succeeded",
            "reason_code": None,
            "details": {
                "counts": {"entries": len(prepared["entries"])},
                "duration_ms": round((time.monotonic() - started) * 1000),
            },
        },
    )
    return {
        "run_id": run_id,
        "descriptor": {**version, "configuration_artifact": config},
        "objects": objects,
        "official_publication": False,
    }
