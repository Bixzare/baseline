"""Local fixtures only: create, inspect and remove an isolated test database."""

import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import UUID, uuid4

import psycopg
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict, make_conninfo

from hoop.domains.nba.publication import publish_player
from hoop.platform.database import apply, provision_runtime
from tests.fixtures.publication import publication_fixture


def run() -> dict[str, object]:
    root = Path(__file__).resolve().parents[1]
    dsn = os.environ.get("BASELINE_TEST_DSN", "")
    if conninfo_to_dict(dsn).get("host") not in {"localhost", "127.0.0.1", "::1", "postgres"}:
        raise ValueError("Rehearsal requires explicit local BASELINE_TEST_DSN")
    name = "baseline_test_rehearsal_" + uuid4().hex
    (root / ".cache").mkdir(exist_ok=True)
    with psycopg.connect(dsn, autocommit=True) as admin:
        admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
        try:
            with psycopg.connect(make_conninfo(dsn, dbname=name), autocommit=True) as owner:
                owner.execute(
                    (root / "tests/fixtures/postgres/provider.sql").read_text(), prepare=False
                )
                apply(owner, root / "migrations")
                with TemporaryDirectory(dir=root / ".cache") as folder:
                    p = publication_fixture(owner, Path(folder))
                    provision_runtime(owner, "synthetic_fixture_password_only")
                    runtime = make_conninfo(
                        dsn,
                        dbname=name,
                        user="baseline_runtime",
                        password="synthetic_fixture_password_only",
                    )
                    with psycopg.connect(runtime, autocommit=True) as conn:
                        result = publish_player(conn, p["store"], p["retained"], UUID(p["bundle"]))
                        assert (
                            publish_player(conn, p["store"], p["retained"], UUID(p["bundle"]))
                            == result
                        )
                        tx = conn.execute(
                            "SELECT insertion_transaction_id,confirming_transaction_id "
                            "FROM platform.forecast_batches "
                            "JOIN platform.publication_receipts USING(batch_id)"
                        ).fetchone()
                        return {
                            **result,
                            "insertion_transaction_id": tx[0],
                            "confirming_transaction_id": tx[1],
                            "evidence": "synthetic_fixture",
                            "production_ready": False,
                        }
        finally:
            assert name.startswith("baseline_test_rehearsal_") and len(name) == 56
            admin.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(name)))


if __name__ == "__main__":
    print(json.dumps(run(), default=str, sort_keys=True))
