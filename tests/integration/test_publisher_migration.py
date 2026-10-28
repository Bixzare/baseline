"""Publisher ownership transfer must work without superuser privileges."""

import shutil
from pathlib import Path

import psycopg
import pytest

from hoop.platform.database import apply

pytestmark = pytest.mark.postgres


def test_publisher_transfer_with_non_superuser_migrator(database: str, tmp_path: Path) -> None:
    from uuid import uuid4

    from psycopg import sql
    from psycopg.conninfo import make_conninfo

    root = Path(__file__).resolve().parents[2]
    files = tmp_path / "migrations"
    files.mkdir()
    for original in sorted((root / "migrations").glob("*.sql"))[:5]:
        shutil.copy(original, files / original.name)
    caller = "fixture_migrator_" + uuid4().hex
    with psycopg.connect(database, autocommit=True) as admin:
        apply(admin, files)
        admin.execute(
            sql.SQL("CREATE ROLE {} LOGIN CREATEROLE PASSWORD 'synthetic_fixture_only'").format(
                sql.Identifier(caller)
            )
        )
        try:
            admin.execute(
                sql.SQL("GRANT baseline_owner TO {} WITH SET TRUE, INHERIT TRUE").format(
                    sql.Identifier(caller)
                )
            )
            admin.execute(
                sql.SQL(
                    "GRANT baseline_publisher TO {} WITH ADMIN TRUE, SET FALSE, INHERIT FALSE"
                ).format(sql.Identifier(caller))
            )
            assert not admin.execute(
                "SELECT pg_has_role(%s,'baseline_publisher','SET')", (caller,)
            ).fetchone()[0]
            shutil.copy(root / "migrations/0006_publication.sql", files / "0006_publication.sql")
            with psycopg.connect(
                make_conninfo(database, user=caller, password="synthetic_fixture_only"),
                autocommit=True,
            ) as setup:
                assert apply(setup, files) == ["0006"]
                assert setup.execute(
                    "SELECT pg_has_role(current_user,'baseline_publisher','SET')"
                ).fetchone()[0]
                assert not setup.execute(
                    "SELECT pg_has_role(current_user,'baseline_publisher','USAGE')"
                ).fetchone()[0]
                assert not setup.execute(
                    "SELECT pg_has_role('baseline_runtime','baseline_publisher','MEMBER')"
                ).fetchone()[0]
        finally:
            admin.execute(sql.SQL("DROP OWNED BY {}").format(sql.Identifier(caller)))
            admin.execute(sql.SQL("DROP ROLE {}").format(sql.Identifier(caller)))
