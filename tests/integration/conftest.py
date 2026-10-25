"""Disposable real Postgres databases. Required setup fails instead of skipping."""

import os
from collections.abc import Iterator
from pathlib import Path
from typing import Any
from uuid import uuid4

import psycopg
import pytest
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict, make_conninfo

from hoop.platform.database import apply

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def database() -> Iterator[str]:
    configured = os.environ.get("BASELINE_TEST_DSN")
    if not configured:
        pytest.fail("Required Postgres tests need BASELINE_TEST_DSN for a disposable local service")
    options = conninfo_to_dict(configured)
    if options.get("host") not in {"localhost", "127.0.0.1", "::1", "postgres"}:
        pytest.fail("Postgres tests refuse nonlocal database hosts")
    name = "baseline_test_" + uuid4().hex
    with psycopg.connect(configured, autocommit=True) as admin:
        admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
        try:
            yield make_conninfo(configured, dbname=name)
        finally:
            admin.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(name)))


@pytest.fixture
def migrated(database: str) -> Iterator[tuple[str, psycopg.Connection[Any]]]:
    with psycopg.connect(database, autocommit=True) as conn:
        apply(conn, ROOT / "migrations")
        yield database, conn
