"""Real transactions, independent connections and denied application roles."""

import shutil
from pathlib import Path
from typing import Any

import psycopg
import pytest
from psycopg.conninfo import make_conninfo

from hoop.platform.database import (
    LOCK_ID,
    DatabaseError,
    apply,
    inspect,
    migrations,
    provision_runtime,
)

pytestmark = pytest.mark.postgres
MIGRATIONS = Path(__file__).resolve().parents[2] / "migrations"


def test_empty_repeat_upgrade_failure_and_changed_history(database: str, tmp_path: Path) -> None:
    files = tmp_path / "migrations"
    shutil.copytree(MIGRATIONS, files)
    with psycopg.connect(database, autocommit=True) as conn:
        assert inspect(conn, migrations(files))
        assert apply(conn, files) == [p.name[:4] for p in sorted(files.glob("*.sql"))]
        original = conn.execute("TABLE platform.schema_migrations").fetchall()
        assert apply(conn, files) == []
        assert conn.execute("TABLE platform.schema_migrations").fetchall() == original
        next_id = len(original) + 1
        upgrade = files / f"{next_id:04d}_upgrade.sql"
        upgrade.write_text("CREATE TABLE platform.upgrade_fixture(value int);")
        assert apply(conn, files) == [f"{next_id:04d}"]
        bad = files / f"{next_id + 1:04d}_failure.sql"
        bad.write_text("CREATE TABLE platform.failed_fixture(value int); SELECT missing_column;")
        (files / f"{next_id + 2:04d}_never.sql").write_text(
            "CREATE TABLE platform.never_fixture(value int);"
        )
        with pytest.raises(DatabaseError, match="rolled back"):
            apply(conn, files)
        assert conn.execute("SELECT to_regclass('platform.failed_fixture')").fetchone() == (None,)
        assert conn.execute("SELECT to_regclass('platform.never_fixture')").fetchone() == (None,)
        assert len(conn.execute("TABLE platform.schema_migrations").fetchall()) == next_id
        upgrade.write_text("SELECT 1;")
        with pytest.raises(DatabaseError, match="history differs"):
            apply(conn, files)
        upgrade.unlink()
        bad.unlink()
        (files / f"{next_id + 2:04d}_never.sql").unlink()
        with pytest.raises(DatabaseError, match="missing"):
            apply(conn, files)


def test_lock_contention_has_bounded_wait_before_bootstrap(database: str) -> None:
    with (
        psycopg.connect(database, autocommit=True) as first,
        psycopg.connect(database, autocommit=True) as second,
    ):
        first.execute("SELECT pg_advisory_lock(%s)", (LOCK_ID,))
        with pytest.raises(DatabaseError, match="lock timed out"):
            apply(second, MIGRATIONS, lock_timeout=0)
        assert second.execute("SELECT to_regclass('platform.schema_migrations')").fetchone() == (
            None,
        )
        first.execute("SELECT pg_advisory_unlock(%s)", (LOCK_ID,))
        assert apply(second, MIGRATIONS)


def test_connection_interruption_cannot_record_partial_migration(
    database: str, tmp_path: Path
) -> None:
    files = tmp_path / "migrations"
    shutil.copytree(MIGRATIONS, files)
    next_id = len(list(files.glob("*.sql"))) + 1
    (files / f"{next_id:04d}_interrupted.sql").write_text(
        "CREATE TABLE platform.interrupted_fixture(value int); "
        "SELECT pg_terminate_backend(pg_backend_pid());"
    )
    with psycopg.connect(database, autocommit=True) as conn:
        with pytest.raises((psycopg.Error, DatabaseError)):
            apply(conn, files)
    with psycopg.connect(database, autocommit=True) as observer:
        assert observer.execute(
            "SELECT to_regclass('platform.interrupted_fixture')"
        ).fetchone() == (None,)
        assert (
            observer.execute("SELECT count(*) FROM platform.schema_migrations").fetchone()[0]
            == next_id - 1
        )


def test_real_roles_and_safe_defaults(migrated: Any) -> None:
    dsn, owner = migrated
    provision_runtime(owner, "synthetic_fixture_password_only")
    # Provider-role stand-in exists only in disposable test setup.
    owner.execute(
        "DO $$ BEGIN IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='anon') "
        "THEN CREATE ROLE anon NOLOGIN; END IF; END $$"
    )
    owner.execute("SET ROLE baseline_owner")
    owner.execute("CREATE TABLE platform.private_fixture(value int)")
    owner.execute(
        "CREATE FUNCTION platform.private_fixture_fn() RETURNS int LANGUAGE sql AS 'SELECT 1'"
    )
    owner.execute("RESET ROLE")
    with psycopg.connect(
        make_conninfo(dsn, user="baseline_runtime", password="synthetic_fixture_password_only"),
        autocommit=True,
    ) as runtime:
        for statement in [
            "CREATE TABLE platform.forbidden(value int)",
            "ALTER TABLE platform.private_fixture ADD COLUMN forbidden int",
            "GRANT ALL ON platform.private_fixture TO baseline_runtime",
            "SELECT * FROM platform.private_fixture",
            "SELECT platform.private_fixture_fn()",
            "TRUNCATE platform.schema_migrations",
            "SET ROLE baseline_owner",
        ]:
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                runtime.execute(statement)
        with pytest.raises(DatabaseError, match="privileged"):
            apply(runtime, MIGRATIONS)
    owner.execute("SET ROLE anon")
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        owner.execute("SELECT * FROM platform.private_fixture")
    owner.execute("RESET ROLE")
    assert owner.execute("SELECT count(*) FROM platform.schema_migrations").fetchone()[0] > 0


@pytest.mark.parametrize("names", [["0001_a.sql", "0001_b.sql"], ["0002_a.sql"], ["bad.sql"]])
def test_invalid_file_order_refused(names: list[str], tmp_path: Path) -> None:
    for name in names:
        (tmp_path / name).write_text("SELECT 1;")
    with pytest.raises(DatabaseError):
        migrations(tmp_path)
