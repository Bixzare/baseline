"""Bounded two-transaction protocol; no network calls inside either transaction."""

from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import psycopg
from psycopg.pq import TransactionStatus
from psycopg.rows import dict_row

from hoop.platform.evidence import EvidenceError, register


def before_deadline(now: datetime, scheduled: datetime) -> bool:
    if now.tzinfo is None or scheduled.tzinfo is None:
        raise ValueError("Timezone-aware times required")
    return now < scheduled - timedelta(minutes=15)


def status(conn: psycopg.Connection[Any], batch_id: UUID) -> dict[str, Any]:
    with conn.cursor(row_factory=dict_row) as cursor:
        result = cursor.execute(
            "SELECT * FROM platform.batch_status WHERE batch_id=%s", (batch_id,)
        ).fetchone()
    if result is None:
        raise EvidenceError("Stored batch not visible")
    return dict(result)


def confirm(conn: psycopg.Connection[Any], batch_id: UUID) -> dict[str, Any]:
    idle(conn)
    with conn.transaction():
        conn.execute("SET LOCAL statement_timeout='10s'")
        conn.execute("SELECT platform.confirm_batch(%s)", (batch_id,))
    # Success means the receipt transaction committed and is visible too.
    return status(conn, batch_id)


def idle(conn: psycopg.Connection[Any]) -> None:
    if not conn.autocommit or conn.info.transaction_status != TransactionStatus.IDLE:
        raise EvidenceError("Publication requires separate top-level transactions")


def commit_and_confirm(
    conn: psycopg.Connection[Any],
    insert: Callable[[], UUID],
    run_id: str,
    *,
    fault: Callable[[str], None] = lambda stage: None,
) -> dict[str, Any]:
    idle(conn)
    try:
        with conn.transaction():
            conn.execute("SET LOCAL statement_timeout='10s'")
            batch_id = insert()
            fault("before_insert_commit")
        fault("after_insert_commit")
        result = confirm(conn, batch_id)
        fault("after_receipt_commit")
        return result
    except (psycopg.Error, OSError):
        # This audit is outside the failed transaction; never log server text.
        report = {"status": "failed", "reason_code": "publication_failed", "audit_saved": False}
        try:
            register(
                conn,
                "run_events",
                {
                    "run_event_id": str(uuid4()),
                    "run_id": run_id,
                    "state": "failed",
                    "reason_code": "publication_failed",
                    "details": {"counts": {}, "duration_ms": 0},
                },
            )
            report["audit_saved"] = True
        except (EvidenceError, psycopg.Error):
            pass
        raise EvidenceError(str(report)) from None
