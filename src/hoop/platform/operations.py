"""Small stage runner with session coordination and explicit completion evidence."""

import os
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import psycopg
from psycopg.pq import TransactionStatus

from hoop.platform.evidence import EvidenceError, register
from hoop.platform.prepared import encoded
from hoop.platform.provenance import digest

READY_KEYS = {
    "activation_approved",
    "hosted_verified",
    "sources_verified",
    "seed_accepted",
    "fallback_verified",
    "backup_verified",
}


def production_enabled(config: dict[str, Any]) -> bool:
    return (
        os.environ.get("BASELINE_PRODUCTION_ENABLE") == "true"
        and READY_KEYS <= set(config.get("readiness", {}))
        and all(config["readiness"][key] is True for key in READY_KEYS)
    )


def db_now(conn: psycopg.Connection[Any]) -> datetime:
    row = conn.execute("SELECT clock_timestamp()").fetchone()
    assert row is not None
    value: datetime = row[0]
    return value


def verify_rehearsal(conn: psycopg.Connection[Any]) -> None:
    if conn.info.host not in {
        "localhost",
        "127.0.0.1",
        "::1",
        "postgres",
    } or not conn.info.dbname.startswith("baseline_test_"):
        raise EvidenceError("Rehearsal refuses the production database")


@contextmanager
def operation_lock(conn: psycopg.Connection[Any], domain: str) -> Iterator[bool]:
    if not conn.autocommit or conn.info.transaction_status != TransactionStatus.IDLE:
        raise EvidenceError("Coordination requires an idle session outside network transactions")
    key = "baseline:shared-operations:" + domain
    row = conn.execute("SELECT pg_try_advisory_lock(hashtextextended(%s,617))", (key,)).fetchone()
    assert row is not None
    acquired = bool(row[0])
    try:
        yield acquired
    finally:
        if acquired and not conn.closed:
            conn.execute("SELECT pg_advisory_unlock(hashtextextended(%s,617))", (key,))


def run_pipeline(
    conn: psycopg.Connection[Any],
    operation: str,
    stages: list[tuple[str, Callable[[], dict[str, Any]]]],
    config: dict[str, Any],
    *,
    rehearsal: bool = False,
    monotonic: Callable[[], float] = time.monotonic,
) -> dict[str, Any]:
    if rehearsal:
        verify_rehearsal(conn)
    elif not production_enabled(config):
        return {"state": "disabled", "production_heartbeat": False, "stages": []}
    started = monotonic()
    run_id = str(uuid4())
    if not stages or len({name for name, _ in stages}) != len(stages):
        raise EvidenceError("An operation needs distinct executable stages")
    results: list[dict[str, Any]] = []
    audit = True

    def event(state: str, reason: str | None, scope: str, **details: Any) -> None:
        register(
            conn,
            "run_events",
            {
                "run_event_id": str(uuid4()),
                "run_id": run_id,
                "state": state,
                "reason_code": reason,
                "details": {
                    "scope": scope,
                    "counts": {},
                    "duration_ms": round((monotonic() - started) * 1000),
                    **details,
                },
            },
        )

    try:
        register(
            conn,
            "runs",
            {
                "run_id": run_id,
                "operation": operation,
                "domain": config["domain"],
                "environment": "rehearsal" if rehearsal else "production",
                "code_version": digest(Path(__file__).read_text().encode()),
                "config_hash": digest(encoded(config)),
            },
        )
        event("started", None, "operation")
        with operation_lock(conn, config["domain"]) as acquired:
            if not acquired:
                event("incomplete", "operation_overlap", "operation")
                return {
                    "run_id": run_id,
                    "state": "incomplete",
                    "reason_code": "operation_overlap",
                    "production_heartbeat": False,
                    "stages": [],
                }
            failed = False
            for name, execute in stages:
                if monotonic() - started >= config["max_seconds"]:
                    results.append(
                        {"stage": name, "state": "not_run", "reason_code": "budget_exhausted"}
                    )
                    failed = True
                    break
                event("started", None, "stage", stage=name)
                stage_start = monotonic()
                try:
                    result = execute()
                    healthy = result.get("state") == "succeeded"
                except Exception as error:
                    # Never include exception/server text or environment values.
                    result = {
                        "state": "failed",
                        "reason_code": "stage_failed",
                        "error_type": type(error).__name__,
                    }
                    healthy = False
                elapsed = round((monotonic() - stage_start) * 1000)
                counts = result.get(
                    "counts",
                    {
                        "requests": result.get("requests", 0),
                        "records": len(result.get("results", [])),
                    },
                )
                results.append(
                    {
                        "stage": name,
                        "state": result["state"],
                        "duration_ms": elapsed,
                        "counts": counts,
                        "reason_code": result.get("reason_code"),
                    }
                )
                event(
                    "succeeded" if healthy else "incomplete",
                    None if healthy else "stage_incomplete",
                    "stage",
                    stage=name,
                    counts=counts,
                    child_run_id=result.get("run_id"),
                    error_type=result.get("error_type"),
                )
                failed = failed or not healthy
            state = "incomplete" if failed else "succeeded"
            event(
                state,
                "operation_incomplete" if failed else None,
                "operation",
                counts={"stages": len(results)},
            )
    except (EvidenceError, psycopg.Error, OSError):
        state = "failed"
        audit = False
    return {
        "run_id": run_id,
        "state": state,
        "stages": results,
        "durable_completion": audit,
        "production_heartbeat": not rehearsal and audit and state == "succeeded",
        "duration_ms": round((monotonic() - started) * 1000),
    }
