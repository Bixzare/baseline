"""Controlled, atomic deterministic-baseline registration without forecasts."""

import re
import time
from collections.abc import Callable
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid5

import psycopg
from psycopg.pq import TransactionStatus
from psycopg.rows import dict_row

from hoop.platform.artifacts import PrivateArtifacts
from hoop.platform.evidence import EvidenceError
from hoop.platform.prepared import encoded
from hoop.platform.provenance import digest
from hoop.platform.records import immutable_insert


def identity(*parts: str) -> UUID:
    return uuid5(NAMESPACE_URL, "baseline:ledger:" + encoded(parts).decode())


def bootstrap(
    conn: psycopg.Connection[Any],
    store: PrivateArtifacts,
    descriptor: dict[str, Any],
    *,
    fault: Callable[[str], None] | None = None,
    environment: str = "rehearsal",
) -> dict[str, Any]:
    if not conn.autocommit or conn.info.transaction_status != TransactionStatus.IDLE:
        raise EvidenceError("Bootstrap must verify artifacts outside a database transaction")
    if environment not in {"rehearsal", "production"}:
        raise EvidenceError("Explicit bootstrap environment required")
    started = time.monotonic()
    config = descriptor["configuration"]
    artifact = descriptor["configuration_artifact"]
    if (
        descriptor.get("schema_version") != 1
        or not isinstance(config, dict)
        or not isinstance(artifact, dict)
        or not isinstance(config.get("targets"), dict)
        or not isinstance(descriptor.get("targets"), dict)
        or any(
            not isinstance(value, str) or not value.strip() or value != value.strip()
            for value in [
                *descriptor["targets"],
                *descriptor["targets"].values(),
                *[descriptor.get(key) for key in ["domain", "family", "version", "code_version"]],
            ]
        )
    ):
        raise EvidenceError("Descriptor fields and target units require nonempty strings")
    if (
        digest(encoded(config)) != descriptor["config_hash"]
        or artifact["sha256"] != descriptor["config_hash"]
        or set(descriptor["targets"]) != set(config["targets"])
        or descriptor["targets"] != config["targets"]
        or any(descriptor[key] != config[key] for key in ["domain", "family", "version"])
        or descriptor.get("learned_artifact_id") is not None
        or descriptor.get("training_cutoff") is not None
        or not descriptor["targets"]
        or not re.fullmatch(r"[0-9a-f]{64}", descriptor["code_version"])
        or artifact.get("kind") != "reports"
        or artifact.get("format") != "json"
        or artifact.get("schema_version") != 1
    ):
        raise EvidenceError("Baseline descriptor/configuration identity mismatch")
    if store.read(artifact) != encoded(config):
        raise EvidenceError("Verified configuration bytes differ from descriptor")
    domain, family, version = (descriptor[key] for key in ["domain", "family", "version"])
    components = {
        target: str(identity("model", domain, family, target, version))
        for target in sorted(descriptor["targets"])
    }
    bundle_id = identity("bundle", domain, family, version)
    run_id = identity("bootstrap-run", domain, family, version, environment)
    event_id = identity("bootstrap-event", domain, family, version, environment)
    lock = int(digest(encoded([domain, family]))[:15], 16)
    with conn.transaction(), conn.cursor(row_factory=dict_row) as cursor:
        cursor.execute("SET LOCAL lock_timeout='2s'")
        cursor.execute("SET LOCAL ROLE baseline_owner")
        cursor.execute("SELECT pg_advisory_xact_lock(%s)", (lock,))
        registered = cursor.execute(
            "SELECT sha256,kind,format,schema_version,byte_count,storage_uri "
            "FROM platform.artifacts WHERE artifact_id=%s",
            (artifact["artifact_id"],),
        ).fetchone()
        if registered is None or any(registered[key] != artifact[key] for key in registered):
            raise EvidenceError("Configuration artifact is not the canonical registered object")
        active = cursor.execute(
            "SELECT bundle_id,generation FROM platform.active_bundles "
            "WHERE domain=%s AND family=%s",
            (domain, family),
        ).fetchone()
        if (
            active
            and not cursor.execute(
                "SELECT 1 FROM platform.model_bundles WHERE bundle_id=%s", (bundle_id,)
            ).fetchone()
        ):
            raise EvidenceError(
                "Family is already initialized; use reviewed promotion for a new version"
            )
        for target, model_id in components.items():
            immutable_insert(
                conn,
                "platform",
                "models",
                {
                    "model_id": UUID(model_id),
                    "domain": domain,
                    "family": family,
                    "target": target,
                    "version": version,
                    "code_version": descriptor["code_version"],
                    "config_hash": descriptor["config_hash"],
                    "artifact_id": None,
                    "training_cutoff": None,
                },
                ("model_id",),
            )
        if fault:
            fault("after_models")
        immutable_insert(
            conn,
            "platform",
            "model_bundles",
            {
                "bundle_id": bundle_id,
                "domain": domain,
                "components": components,
                "config_hash": descriptor["config_hash"],
            },
            ("bundle_id",),
        )
        if fault:
            fault("after_bundle")
        if active is None:
            immutable_insert(
                conn,
                "platform",
                "runs",
                {
                    "run_id": run_id,
                    "operation": "baseline_bootstrap",
                    "domain": domain,
                    "environment": environment,
                    "code_version": descriptor["code_version"],
                    "config_hash": descriptor["config_hash"],
                },
                ("run_id",),
            )
            immutable_insert(
                conn,
                "platform",
                "active_bundles",
                {"domain": domain, "family": family, "bundle_id": bundle_id, "generation": 1},
                ("domain", "family"),
            )
            immutable_insert(
                conn,
                "platform",
                "run_events",
                {
                    "run_event_id": event_id,
                    "run_id": run_id,
                    "state": "succeeded",
                    "reason_code": "initial_baseline_activation",
                    "details": {
                        "counts": {"models": len(components)},
                        "duration_ms": round((time.monotonic() - started) * 1000),
                        "configuration_artifact_id": artifact["artifact_id"],
                        "configuration_sha256": artifact["sha256"],
                        "bundle_id": str(bundle_id),
                        "generation": 1,
                    },
                },
                ("run_event_id",),
            )
            active = {"bundle_id": bundle_id, "generation": 1}
        elif not cursor.execute(
            "SELECT 1 FROM platform.run_events WHERE run_event_id=%s AND run_id=%s",
            (event_id, run_id),
        ).fetchone():
            raise EvidenceError("Existing bootstrap activation audit is missing")
        if fault:
            fault("after_pointer")
    return {
        "bundle_id": str(bundle_id),
        "models": components,
        "bootstrap_run_id": str(run_id),
        "bootstrap_event_id": str(event_id),
        "active_bundle_id": str(active["bundle_id"]),
        "generation": active["generation"],
        "active_is_initial": active["bundle_id"] == bundle_id,
        "official_publication_available": False,
    }
