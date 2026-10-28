"""Immutable stable-key alert transitions shared across domains."""

from datetime import datetime
from typing import Any
from uuid import uuid4

import psycopg
from psycopg.rows import dict_row

from hoop.platform.records import immutable_insert


def append_condition(conn: psycopg.Connection[Any], condition: dict[str, Any]) -> str | None:
    key = condition["alert_key"]
    with conn.transaction(), conn.cursor(row_factory=dict_row) as cursor:
        cursor.execute("SET LOCAL lock_timeout='2s'")
        cursor.execute(
            "SELECT pg_advisory_xact_lock(hashtextextended(%s,617))", ("baseline:alert:" + key,)
        )
        previous = cursor.execute(
            "SELECT * FROM platform.alert_events WHERE alert_key=%s ORDER BY "
            "recorded_at DESC,alert_event_id DESC LIMIT 1",
            (key,),
        ).fetchone()
        if previous is None and condition["state"] in {"resolved", "acknowledged"}:
            return None
        if previous:
            unchanged = (
                (
                    condition["state"] == previous["state"]
                    or condition["state"] == "open"
                    and previous["state"] == "acknowledged"
                )
                and condition["severity"] == previous["severity"]
                and condition["reason_code"] == previous["reason_code"]
            )
            if unchanged:
                return None
        identity = uuid4()
        immutable_insert(
            conn,
            "platform",
            "alert_events",
            {
                "alert_event_id": identity,
                "alert_key": key,
                "severity": condition["severity"],
                "state": condition["state"],
                "reason_code": condition["reason_code"],
                "observed_at": condition["observed_at"],
                "run_id": None,
                "report_id": None,
                "details": condition.get("details", {}),
            },
            ("alert_event_id",),
        )
    return str(identity)


def reconcile_conditions(
    conn: psycopg.Connection[Any],
    conditions: list[dict[str, Any]],
    observed_at: datetime,
    *,
    namespace: str,
) -> int:
    """Only a complete authoritative assessment can close no-longer-applicable keys."""
    keys = {c["alert_key"] for c in conditions}
    previous = conn.execute(
        """SELECT alert_key,severity FROM (
          SELECT DISTINCT ON(alert_key) alert_key,severity,state FROM platform.alert_events
          WHERE starts_with(alert_key,%s) ORDER BY alert_key,recorded_at DESC,alert_event_id DESC
        ) latest WHERE state IN('open','acknowledged')""",
        (namespace + ":",),
    ).fetchall()
    current = list(conditions)
    current.extend(
        {
            "alert_key": key,
            "severity": severity,
            "state": "resolved",
            "reason_code": "condition_no_longer_applicable",
            "observed_at": observed_at,
            "details": {},
        }
        for key, severity in previous
        if key not in keys
    )
    return sum(append_condition(conn, condition) is not None for condition in current)
