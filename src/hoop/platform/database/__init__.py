"""Explicit, bounded connections and transactional repository migrations."""

import hashlib
import os
import re
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import psycopg
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict

LOCK_ID = 617420260001


class DatabaseError(RuntimeError):
    """Safe operational error. Never includes a DSN or server error text."""


@contextmanager
def connection(variable: str = "BASELINE_RUNTIME_DSN") -> Iterator[psycopg.Connection[Any]]:
    dsn = os.environ.get(variable)
    if not dsn:
        raise DatabaseError(f"Configure {variable} privately")
    try:
        options = conninfo_to_dict(dsn)
        mode = os.environ.get("BASELINE_DB_CONNECTION_MODE", "direct")
        if mode not in {"direct", "session"} or options.get("port") == "6543":
            raise DatabaseError(
                "Use the verified direct or session connection, not transaction pooling"
            )
        local = options.get("host") in {"localhost", "127.0.0.1", "::1"}
        if local:
            if os.environ.get("BASELINE_DB_LOCAL_TEST") != "1":
                raise DatabaseError("Local connections require BASELINE_DB_LOCAL_TEST=1")
        elif options.get("sslmode") != "verify-full":
            raise DatabaseError("Hosted connections require sslmode=verify-full and a trusted CA")
        with psycopg.connect(
            dsn,
            autocommit=True,
            connect_timeout=5,
            application_name="baseline",
            options="-c statement_timeout=10000 -c lock_timeout=2000",
        ) as conn:
            yield conn
    except DatabaseError:
        raise
    except (psycopg.Error, ValueError):
        raise DatabaseError(
            "Database operation failed; inspect setup or isolated server logs"
        ) from None


def health(conn: psycopg.Connection[Any]) -> dict[str, Any]:
    row = conn.execute(
        "SELECT current_user, current_setting('server_version'), "
        "coalesce((SELECT ssl FROM pg_stat_ssl WHERE pid=pg_backend_pid()),false)"
    ).fetchone()
    assert row is not None
    # Behind a pooler, pg_stat_ssl describes the pooler-to-Postgres leg.
    # libpq reports the transport actually negotiated by this client.
    return {
        "role": row[0],
        "server_version": row[1],
        "tls": conn.pgconn.ssl_in_use,
        "postgres_backend_tls": row[2],
    }


@dataclass(frozen=True)
class Migration:
    id: str
    filename: str
    sha256: str
    body: str


def migrations(directory: Path) -> list[Migration]:
    result = []
    for path in sorted(directory.glob("*.sql")):
        match = re.fullmatch(r"([0-9]{4})_[a-z0-9_]+\.sql", path.name)
        if match is None:
            raise DatabaseError("Migration filenames need four-digit IDs and lowercase names")
        body = path.read_bytes()
        result.append(
            Migration(match[1], path.name, hashlib.sha256(body).hexdigest(), body.decode())
        )
    if not result or [item.id for item in result] != [
        f"{i:04d}" for i in range(1, len(result) + 1)
    ]:
        raise DatabaseError("Migration IDs must be unique, contiguous and start at 0001")
    return result


def inspect(conn: psycopg.Connection[Any], files: list[Migration]) -> list[Migration]:
    relation = conn.execute("SELECT to_regclass('platform.schema_migrations')").fetchone()
    if not relation or not relation[0]:
        return files
    rows = conn.execute(
        "SELECT migration_id, filename, sha256 "
        "FROM platform.schema_migrations ORDER BY migration_id"
    ).fetchall()
    if len(rows) > len(files):
        raise DatabaseError("An applied migration file is missing")
    for row, file in zip(rows, files, strict=False):
        if row != (file.id, file.filename, file.sha256):
            raise DatabaseError(
                "Applied migration history differs; restore original files, add a new migration"
            )
    return files[len(rows) :]


def apply(
    conn: psycopg.Connection[Any], directory: Path, *, lock_timeout: float = 5.0
) -> list[str]:
    if not conn.autocommit or lock_timeout < 0 or lock_timeout > 60:
        raise DatabaseError(
            "Migrations require autocommit and a lock timeout between 0 and 60 seconds"
        )
    files = migrations(directory)
    privileged = conn.execute(
        "SELECT rolcreaterole OR rolsuper FROM pg_roles WHERE rolname=current_user"
    ).fetchone()
    if not privileged or not privileged[0]:
        raise DatabaseError("Migration access requires the separate privileged setup identity")
    deadline = time.monotonic() + lock_timeout
    while True:
        acquired = conn.execute("SELECT pg_try_advisory_lock(%s)", (LOCK_ID,)).fetchone()
        if acquired and acquired[0]:
            break
        if time.monotonic() >= deadline:
            raise DatabaseError("Migration lock timed out; another runner may be active")
        time.sleep(min(0.05, max(0, deadline - time.monotonic())))
    applied = []
    try:
        for file in inspect(conn, files):
            try:
                with conn.transaction():
                    if file.id != "0001":
                        conn.execute("SET LOCAL ROLE baseline_owner")
                    conn.execute(file.body, prepare=False)
                    conn.execute(
                        "INSERT INTO platform.schema_migrations(migration_id,filename,sha256) "
                        "VALUES (%s,%s,%s)",
                        (file.id, file.filename, file.sha256),
                    )
            except psycopg.Error:
                raise DatabaseError(f"Migration {file.id} failed and rolled back") from None
            applied.append(file.id)
    finally:
        conn.execute("SELECT pg_advisory_unlock(%s)", (LOCK_ID,))
    return applied


def provision_runtime(conn: psycopg.Connection[Any], password: str) -> None:
    if not password or len(password) < 20:
        raise DatabaseError("Runtime password must contain at least 20 characters")
    # Identifier is fixed; literal quoting is driver-owned. Never log this SQL.
    conn.execute(
        sql.SQL("ALTER ROLE baseline_runtime LOGIN PASSWORD {}").format(sql.Literal(password))
    )
