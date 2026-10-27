"""Immutable typed-row insertion inside a caller-owned short transaction."""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import psycopg
from psycopg import sql
from psycopg.pq import TransactionStatus
from psycopg.types.json import Jsonb

from hoop.platform.evidence import EvidenceError, safe_summary


def canonical(value: Any) -> Any:
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime):
        if value.tzinfo is None:
            raise EvidenceError("Timezone-aware record timestamps required")
        return value.astimezone(UTC).isoformat()
    return value


def immutable_insert(
    conn: psycopg.Connection[Any],
    schema: str,
    table: str,
    record: dict[str, Any],
    keys: tuple[str, ...],
) -> None:
    if conn.info.transaction_status != TransactionStatus.INTRANS:
        raise EvidenceError("Immutable rows require a caller-owned transaction")
    if not keys or not set(keys) <= record.keys():
        raise EvidenceError("Record key contract missing")
    fields = list(record)
    values = []
    for value in record.values():
        canonical(value)
        if isinstance(value, dict):
            safe_summary(value)
            values.append(Jsonb(value))
        else:
            values.append(value)
    relation = sql.Identifier(schema, table)
    conn.execute(
        sql.SQL("INSERT INTO {} ({}) VALUES ({}) ON CONFLICT DO NOTHING").format(
            relation,
            sql.SQL(",").join(map(sql.Identifier, fields)),
            sql.SQL(",").join(sql.Placeholder() for _ in fields),
        ),
        values,
    )
    row = conn.execute(
        sql.SQL("SELECT {} FROM {} WHERE {}").format(
            sql.SQL(",").join(map(sql.Identifier, fields)),
            relation,
            sql.SQL(" AND ").join(sql.SQL("{}=%s").format(sql.Identifier(key)) for key in keys),
        ),
        [record[key] for key in keys],
    ).fetchone()
    if row is None or [canonical(value) for value in row] != [
        canonical(value) for value in record.values()
    ]:
        raise EvidenceError("Immutable record conflicts with existing identity")
