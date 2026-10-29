"""Rehearse portable repair evidence only; no accepted source checks or NBA facts."""

import argparse
import json
import os
import re
import time
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import psycopg
from psycopg.rows import dict_row

from hoop.platform.artifacts import (
    MAX_BYTES,
    ArtifactError,
    PrivateArtifacts,
    Session,
    Settings,
    retain,
)
from hoop.platform.database import DatabaseError, connection, health
from hoop.platform.evidence import EvidenceError, register
from hoop.platform.local_artifacts import LocalArtifacts, atomic_json, checksum

KIND = "nba_seed_repair_lineage_v1"


def repair_inputs(report: dict[str, Any]) -> list[dict[str, Any]]:
    return list(
        {
            a["sha256"]: a
            for a in report["artifacts"]
            if a["kind"] in {"repair_evidence", "repair_overlay"}
        }.values()
    )


def retain_repairs(
    conn: psycopg.Connection[Any],
    store: PrivateArtifacts,
    local: LocalArtifacts,
    inputs: list[dict[str, Any]],
    *,
    max_seconds: float = 600,
) -> list[dict[str, Any]]:
    if len(inputs) > 512:
        raise EvidenceError("Repair inventory exceeds bounded rehearsal")
    paths = {a["sha256"]: local.verify(a) for a in inputs}
    if any(p.stat().st_size > MAX_BYTES for p in paths.values()):
        raise EvidenceError("Repair input exceeds object bound")
    deadline = time.monotonic() + max_seconds
    retained = []
    for item in inputs:
        if time.monotonic() >= deadline:
            raise EvidenceError("Repair retention budget exhausted")
        if item["kind"] not in {"repair_evidence", "repair_overlay"}:
            raise EvidenceError("Unexpected repair artifact kind")
        retained.append(
            {
                "source_kind": item["kind"],
                **retain(
                    conn,
                    store,
                    paths[item["sha256"]].read_bytes(),
                    kind="raw" if item["kind"] == "repair_evidence" else "reports",
                    format=item["format"],
                    manifest={},
                ),
            }
        )
    return retained


def retain_lineage(
    conn: psycopg.Connection[Any], store: PrivateArtifacts, report: dict[str, Any], archive: Path
) -> dict[str, Any]:
    local = LocalArtifacts(archive)
    descriptor = report["manifest_artifact"]
    body = local.verify(descriptor).read_bytes()
    saved = json.loads(body)
    if any(report.get(k) != v for k, v in saved.items()):
        raise EvidenceError("Lineage differs from immutable candidate")
    artifacts = retain_repairs(conn, store, local, repair_inputs(saved))
    candidate = {
        "source_kind": "candidate_manifest",
        **retain(conn, store, body, kind="reports", format="json", manifest={}),
    }
    graph = {
        "schema_version": 1,
        "lineage_kind": KIND,
        "candidate_manifest_sha256": descriptor["sha256"],
        "parser_version": saved["parser_version"],
        "artifacts": [candidate, *artifacts],
        "scope": "repair_lineage_only",
        "seed_accepted": False,
        "hosted_fact_import_performed": False,
    }
    encoded = json.dumps(graph, sort_keys=True, separators=(",", ":")).encode()
    return retain(
        conn,
        store,
        encoded,
        kind="reports",
        format="json",
        manifest={"lineage_kind": KIND, "candidate_manifest_sha256": descriptor["sha256"]},
    )


def verify_lineage(
    conn: psycopg.Connection[Any], store: PrivateArtifacts, root_id: str
) -> dict[str, Any]:
    root_id = str(UUID(root_id))
    with conn.transaction(), conn.cursor(row_factory=dict_row) as cursor:
        cursor.execute("SET TRANSACTION READ ONLY")
        root = cursor.execute(
            "SELECT * FROM platform.artifacts WHERE artifact_id=%s", (root_id,)
        ).fetchone()
    if root is None or root["manifest"].get("lineage_kind") != KIND:
        raise EvidenceError("Registered lineage root required")
    graph = json.loads(store.read(root))
    objects = graph["artifacts"]
    if (
        graph.get("schema_version") != 1
        or graph.get("lineage_kind") != KIND
        or graph.get("candidate_manifest_sha256") != root["manifest"]["candidate_manifest_sha256"]
        or not isinstance(objects, list)
        or not 1 <= len(objects) <= 513
        or graph.get("scope") != "repair_lineage_only"
        or graph.get("seed_accepted") is not False
        or graph.get("hosted_fact_import_performed") is not False
    ):
        raise EvidenceError("Invalid lineage manifest")
    ids = [str(UUID(a["artifact_id"])) for a in objects]
    if len(set(ids)) != len(ids):
        raise EvidenceError("Duplicate lineage references")
    with conn.transaction(), conn.cursor(row_factory=dict_row) as cursor:
        cursor.execute("SET TRANSACTION READ ONLY")
        rows = cursor.execute(
            "SELECT * FROM platform.artifacts WHERE artifact_id=ANY(%s::uuid[])", (ids,)
        ).fetchall()
    registered = {str(r["artifact_id"]): r for r in rows}
    deadline = time.monotonic() + 180
    verified_bytes = 0
    candidate_body = None
    for item in objects:
        if time.monotonic() >= deadline:
            raise EvidenceError("Lineage readback budget exhausted")
        actual = registered.get(item["artifact_id"])
        if actual is None or any(
            item[k] != actual[k]
            for k in ["sha256", "kind", "format", "schema_version", "byte_count", "storage_uri"]
        ):
            raise EvidenceError("Lineage reference differs from registry")
        body = store.read(actual)
        verified_bytes += len(body)
        if item.get("source_kind") == "candidate_manifest":
            candidate_body = body
    candidates = [a for a in objects if a.get("source_kind") == "candidate_manifest"]
    if len(candidates) != 1 or candidates[0]["sha256"] != graph["candidate_manifest_sha256"]:
        raise EvidenceError("Lineage candidate identity missing")
    if candidate_body is None:
        raise EvidenceError("Candidate bytes missing from lineage")
    candidate_report = json.loads(candidate_body)
    expected = {(a["kind"], a["sha256"]) for a in repair_inputs(candidate_report)}
    supplied = {
        (a.get("source_kind"), a["sha256"])
        for a in objects
        if a.get("source_kind") != "candidate_manifest"
    }
    if expected != supplied or candidate_report["parser_version"] != graph["parser_version"]:
        raise EvidenceError("Incomplete or conflicting repair lineage")
    return {
        "verified": True,
        "root_artifact_id": root_id,
        "candidate_manifest_sha256": graph["candidate_manifest_sha256"],
        "artifacts_verified": len(objects),
        "bytes_verified": verified_bytes,
        "scope": "repair_lineage_only",
        "seed_accepted": False,
        "hosted_fact_import_performed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=["plan", "stage", "check"], nargs="?", default="plan")
    parser.add_argument("--archive", type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--confirm-rehearsal", action="store_true")
    args = parser.parse_args()
    if args.operation == "plan":
        print(json.dumps({"operation": "plan", "network_access": False, "seed_accepted": False}))
        return 0
    failure: dict[str, Any] = {}
    try:
        if not args.confirm_rehearsal or args.report is None:
            raise EvidenceError("Explicit rehearsal and report required")
        with connection() as conn:
            if health(conn)["role"] != "baseline_runtime":
                raise EvidenceError("Restricted runtime required")
            store = PrivateArtifacts(Session(Settings.from_env()))
            if args.operation == "stage":
                if args.archive is None:
                    raise EvidenceError("Candidate archive required")
                local = LocalArtifacts(args.archive)
                pointer = json.loads((args.archive / "candidate-current.json").read_text())
                d = pointer["manifest_artifact"]
                candidate = {**json.loads(local.verify(d).read_text()), "manifest_artifact": d}
                run_id = str(uuid4())
                started = time.monotonic()
                register(
                    conn,
                    "runs",
                    {
                        "run_id": run_id,
                        "operation": "repair_lineage_rehearsal",
                        "domain": "nba",
                        "environment": "rehearsal",
                        "code_version": checksum(Path(__file__)),
                        "config_hash": d["sha256"],
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
                phase = "retention"
                try:
                    root = retain_lineage(conn, store, candidate, args.archive)
                    phase = "readback"
                    result = verify_lineage(conn, store, str(root["artifact_id"]))
                    phase = "terminal_audit"
                    register(
                        conn,
                        "run_events",
                        {
                            "run_event_id": str(uuid4()),
                            "run_id": run_id,
                            "state": "succeeded",
                            "reason_code": None,
                            "details": {
                                "source_accepted": False,
                                "counts": {"artifacts_verified": result["artifacts_verified"]},
                                "duration_ms": int((time.monotonic() - started) * 1000),
                            },
                        },
                    )
                    result["run_id"] = run_id
                except Exception as error:
                    failure = {"failure_phase": phase, "failure_type": type(error).__name__}
                    if isinstance(error, ArtifactError) and re.fullmatch(
                        r"[a-z0-9_]{1,80}", str(error)
                    ):
                        failure["artifact_reason"] = str(error)
                    register(
                        conn,
                        "run_events",
                        {
                            "run_event_id": str(uuid4()),
                            "run_id": run_id,
                            "state": "failed",
                            "reason_code": "repair_lineage_stage_failed",
                            "details": {
                                **failure,
                                "counts": {},
                                "duration_ms": int((time.monotonic() - started) * 1000),
                            },
                        },
                    )
                    raise
            else:
                result = verify_lineage(
                    conn, store, os.environ.get("BASELINE_SEED_LINEAGE_ROOT_ID", "")
                )
        atomic_json(args.report, result)
        print(json.dumps(result))
        return 0
    except (
        EvidenceError,
        ArtifactError,
        DatabaseError,
        ValueError,
        KeyError,
        TypeError,
        OSError,
        psycopg.Error,
    ):
        result = {
            "verified": False,
            "reason_code": "repair_lineage_rehearsal_failed",
            **failure,
            "seed_accepted": False,
        }
        if args.report is not None:
            atomic_json(args.report, result)
        print(json.dumps(result))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
