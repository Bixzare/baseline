"""Immutable generic evidence registration and point in time eligibility."""

import json
import re
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import psycopg
from psycopg import sql
from psycopg.pq import TransactionStatus
from psycopg.types.json import Jsonb

from hoop.platform.provenance import parse_time

FIELDS = {
    "runs": ("run_id", "operation", "domain", "environment", "code_version", "config_hash"),
    "run_events": ("run_event_id", "run_id", "state", "reason_code", "details"),
    "artifacts": (
        "artifact_id",
        "sha256",
        "kind",
        "format",
        "schema_version",
        "byte_count",
        "storage_uri",
        "manifest",
    ),
    "source_checks": (
        "check_id",
        "run_id",
        "source_id",
        "adapter_version",
        "requested_at",
        "received_at",
        "validated_at",
        "source_published_at",
        "raw_artifact_id",
        "http_status",
        "record_count",
        "state",
        "validation_summary",
    ),
}
JSON_FIELDS = {"details", "manifest", "validation_summary"}
UNSAFE = re.compile(
    r'"(?:password|secret|token|access_token|refresh_token|authorization|cookie|set-cookie|api_key|apikey|dsn|credentials)"\s*:|'
    r"Bearer |postgres(?:ql)?://|sb_secret_|[?&](?:token|key|signature|access_token)=|eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.",
    re.I,
)


class EvidenceError(RuntimeError):
    pass


def safe_summary(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise EvidenceError("Evidence summaries must be JSON objects")
    try:
        encoded = json.dumps(value, allow_nan=False)
    except (ValueError, TypeError):
        raise EvidenceError("Evidence summary must contain finite JSON values") from None
    if len(encoded.encode()) > 16384 or UNSAFE.search(encoded):
        raise EvidenceError("Evidence summary is oversized or contains credential markers")
    return value


def canonical(value: Any) -> Any:
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime):
        return value.astimezone(UTC).isoformat()
    return value


def register(conn: psycopg.Connection[Any], table: str, record: dict[str, Any]) -> dict[str, Any]:
    """One transaction, no network. ON CONFLICT never modifies an existing row."""
    if table not in FIELDS or set(record) != set(FIELDS[table]):
        raise EvidenceError("Evidence fields do not match the versioned contract")
    if not conn.autocommit or conn.info.transaction_status != TransactionStatus.IDLE:
        raise EvidenceError("Evidence registration needs its own short transaction")
    fields = FIELDS[table]
    identity = fields[0]
    supplied = {key: canonical(value) for key, value in record.items()}
    for key, value in record.items():
        if value is not None and key.endswith("_at"):
            supplied[key] = parse_time(str(value)).isoformat()
        if value is not None and key.endswith("_id"):
            supplied[key] = str(UUID(str(value))) if key != "source_id" else value
    for key in JSON_FIELDS & record.keys():
        safe_summary(record[key])
    values = [Jsonb(record[key]) if key in JSON_FIELDS else record[key] for key in fields]
    try:
        with conn.transaction():
            conn.execute(
                sql.SQL("INSERT INTO platform.{} ({}) VALUES ({}) ON CONFLICT DO NOTHING").format(
                    sql.Identifier(table),
                    sql.SQL(",").join(map(sql.Identifier, fields)),
                    sql.SQL(",").join(sql.Placeholder() for _ in fields),
                ),
                values,
            )
            predicate = sql.SQL("{}=%s").format(sql.Identifier(identity))
            params = [record[identity]]
            if table == "artifacts":
                predicate += sql.SQL(" OR storage_uri=%s")
                params.append(record["storage_uri"])
            rows = conn.execute(
                sql.SQL("SELECT {} FROM platform.{} WHERE {}").format(
                    sql.SQL(",").join(map(sql.Identifier, fields)),
                    sql.Identifier(table),
                    predicate,
                ),
                params,
            ).fetchall()
            if len(rows) != 1:
                raise EvidenceError("Conflicting evidence identity or URI")
            existing = {key: canonical(value) for key, value in zip(fields, rows[0], strict=True)}
            compare = dict(supplied)
            if table == "artifacts":
                compare[identity] = existing[identity]
            if existing != compare:
                raise EvidenceError("Evidence retry conflicts with immutable content")
            return existing
    except psycopg.Error:
        raise EvidenceError("Evidence database write failed") from None


def known_by(check: dict[str, Any], cutoff: datetime) -> bool:
    if cutoff.tzinfo is None:
        raise ValueError("Cutoff must include a timezone")
    if check.get("state") != "accepted":
        return False
    received, validated = check.get("received_at"), check.get("validated_at")
    if not received or not validated:
        return False
    requested = check.get("requested_at")
    publication = check.get("source_published_at")
    return (
        requested is not None
        and parse_time(str(requested))
        <= parse_time(str(received))
        <= parse_time(str(validated))
        <= cutoff
        and (publication is None or parse_time(str(publication)) <= cutoff)
    )
