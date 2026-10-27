"""Local fixtures only: create, inspect and remove an isolated test database."""

import json
import os
from datetime import timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import UUID, uuid4

import psycopg
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict, make_conninfo

from hoop.domains.nba.outcomes import ingest_final, normalize_final
from hoop.domains.nba.publication import publish_player
from hoop.platform.database import apply, provision_runtime
from hoop.platform.ledger.publication import status
from tests.fixtures.finals import final_context, final_payload
from tests.fixtures.publication import publication_fixture


def run(*, include_outcomes: bool = False) -> dict[str, object]:
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
                        report: dict[str, object] = {
                            **result,
                            "insertion_transaction_id": tx[0],
                            "confirming_transaction_id": tx[1],
                            "evidence": "synthetic_fixture",
                            "production_ready": False,
                        }
                        if include_outcomes:
                            before = conn.execute(
                                "SELECT prediction_id,value FROM platform.predictions ORDER BY "
                                "prediction_id"
                            ).fetchall()
                            payload = final_payload(p["now"] - timedelta(hours=3))
                            config = {
                                "schema_version": 1,
                                "dnp_semantics": "played0_with_reason",
                                "calendar_convention": "source_calendar_verified",
                            }
                            first_check = p["source"]("final", payload)
                            first = ingest_final(
                                conn,
                                p["store"],
                                p["event"],
                                first_check,
                                normalize_final(payload, final_context(), p["now"]),
                                config=config,
                            )
                            payload["game"]["homeTeam"]["players"].append(
                                {"personId": 999, "played": "0", "notPlayingReason": "inactive"}
                            )
                            second_check = p["source"]("final", payload)
                            second = ingest_final(
                                conn,
                                p["store"],
                                p["event"],
                                second_check,
                                normalize_final(payload, final_context(), p["now"]),
                                config=config,
                            )
                            assert (
                                conn.execute(
                                    "SELECT prediction_id,value FROM platform.predictions ORDER BY "
                                    "prediction_id"
                                ).fetchall()
                                == before
                            )
                            report.update(
                                outcome_first=first,
                                outcome_corrected=second,
                                publication_state_before_final=result["state"],
                                state=status(conn, result["batch_id"])["state"],
                                forecast_values_preserved=True,
                                timing_scenario="synthetic_earlier_start_correction",
                            )
                        return report
        finally:
            assert name.startswith("baseline_test_rehearsal_") and len(name) == 56
            admin.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(name)))


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--outcomes", action="store_true")
    args = parser.parse_args()
    print(json.dumps(run(include_outcomes=args.outcomes), default=str, sort_keys=True))
