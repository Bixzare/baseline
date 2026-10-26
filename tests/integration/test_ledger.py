"""Real constraints, circular deferred keys, privilege boundaries and bootstrap."""

import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier
from typing import Any
from uuid import UUID, uuid4

import psycopg
import pytest
from psycopg.conninfo import make_conninfo
from psycopg.types.json import Jsonb

from hoop.domains.nba.baselines.model import POLICY_PATH, descriptor
from hoop.domains.nba.history.seed import apply_seed
from hoop.platform.artifacts import PrivateArtifacts, Session, retain
from hoop.platform.database import provision_runtime
from hoop.platform.evidence import EvidenceError
from hoop.platform.ledger.bootstrap import bootstrap
from hoop.platform.prepared import encoded
from tests.fixtures.history_seed import fixture_seed
from tests.fixtures.storage_client import SETTINGS, MemoryStorage

pytestmark = pytest.mark.postgres


@pytest.fixture
def ledger(migrated: Any, tmp_path: Path) -> Any:
    dsn, conn = migrated
    store = PrivateArtifacts(Session(SETTINGS, MemoryStorage()))
    desc = descriptor(json.loads(POLICY_PATH.read_text()))
    config = retain(
        conn, store, encoded(desc["configuration"]), kind="reports", format="json", manifest={}
    )
    desc["configuration_artifact"] = config
    registered = bootstrap(conn, store, desc)
    _, _, plan = fixture_seed(tmp_path / "archive")
    imported = apply_seed(conn, store, plan, tmp_path / "archive", tmp_path / "checkpoint.json")
    feature = retain(conn, store, b"[]", kind="features", format="json", manifest={})
    event, observation = conn.execute(
        "SELECT event_id,observation_id FROM platform.event_observations LIMIT 1"
    ).fetchone()
    yield dsn, conn, store, desc, registered, imported, feature, event, observation


def batch(
    ledger: Any,
    *,
    bundle: str | None = None,
    event: UUID | None = None,
    observation: UUID | None = None,
) -> UUID:
    _, conn, _, _, registered, imported, feature, source_event, source_observation = ledger
    value = uuid4()
    conn.execute(
        """INSERT INTO platform.forecast_batches(batch_id,run_id,event_id,bundle_id,
        feature_artifact_id,cohort_artifact_id,schedule_observation_id,generated_at,feature_cutoff,
        scheduled_start,publication_policy_version,content_hash)
        VALUES (%s,%s,%s,%s,%s,%s,%s,'2026-10-25 12:00+00','2026-10-25 11:00+00',
                '2026-10-27 16:00+00','fixture-v1',%s)""",
        (
            value,
            imported["run_id"],
            event or source_event,
            bundle or registered["bundle_id"],
            feature["artifact_id"],
            feature["artifact_id"],
            observation or source_observation,
            "a" * 64,
        ),
    )
    return value


def slot(
    conn: Any,
    ledger: Any,
    batch_id: UUID,
    kind: str,
    *,
    subject: str = "201",
    target: str = "points",
) -> None:
    conn.execute(
        """INSERT INTO platform.official_slots(event_id,subject_type,subject_id,
                    target,batch_id,decision_kind)
                    VALUES (%s,'player',%s,%s,%s,%s)""",
        (ledger[7], subject, target, batch_id, kind),
    )


def child(
    conn: Any,
    ledger: Any,
    batch_id: UUID,
    kind: str,
    *,
    subject: str = "201",
    target: str = "points",
    value: float = 12.5,
) -> UUID:
    row_id = uuid4()
    if kind == "prediction":
        conn.execute(
            """INSERT INTO platform.predictions(prediction_id,batch_id,subject_type,
             subject_id,target,role,model_id,value,unit)
             VALUES (%s,%s,'player',%s,%s,'official',%s,%s,'points')""",
            (row_id, batch_id, subject, target, ledger[4]["models"][target], value),
        )
    else:
        conn.execute(
            """INSERT INTO platform.abstentions(abstention_id,batch_id,subject_type,
             subject_id,target,role,reason_code,details)
             VALUES (%s,%s,'player',%s,%s,'official','no_history','{}')""",
            (row_id, batch_id, subject, target),
        )
    return row_id


def test_bootstrap_exact_retry_preserves_audit_and_empty_ledger(ledger: Any) -> None:
    _, conn, store, desc, first, *_ = ledger
    times = conn.execute("SELECT created_at FROM platform.models ORDER BY model_id").fetchall()
    count = conn.execute(
        "SELECT count(*) FROM platform.run_events WHERE reason_code='initial_baseline_activation'"
    ).fetchone()
    assert bootstrap(conn, store, desc) == first
    assert (
        conn.execute("SELECT created_at FROM platform.models ORDER BY model_id").fetchall() == times
    )
    assert (
        conn.execute(
            "SELECT count(*) FROM platform.run_events "
            "WHERE reason_code='initial_baseline_activation'"
        ).fetchone()
        == count
        == (1,)
    )
    assert conn.execute("SELECT count(*) FROM platform.forecast_batches").fetchone() == (0,)
    assert conn.execute("SELECT count(*) FROM platform.publication_receipts").fetchone() == (0,)
    changed = {**desc, "code_version": "f" * 64}
    with pytest.raises(EvidenceError, match="conflicts"):
        bootstrap(conn, store, changed)


@pytest.mark.parametrize("stage", ["after_models", "after_bundle", "after_pointer"])
def test_failed_bootstrap_rolls_back_every_related_row(migrated: Any, stage: str) -> None:
    _, conn = migrated
    store = PrivateArtifacts(Session(SETTINGS, MemoryStorage()))
    desc = descriptor(json.loads(POLICY_PATH.read_text()))
    desc["configuration_artifact"] = retain(
        conn, store, encoded(desc["configuration"]), kind="reports", format="json", manifest={}
    )

    def fail(point: str) -> None:
        if point == stage:
            raise OSError("injected")

    with pytest.raises(OSError):
        bootstrap(conn, store, desc, fault=fail)
    for table in ["models", "model_bundles", "active_bundles", "runs", "run_events"]:
        assert conn.execute(f"SELECT count(*) FROM platform.{table}").fetchone() == (0,)


def test_bootstrap_concurrency_and_later_activation_not_reversed(ledger: Any) -> None:
    dsn, conn, store, desc, first, *_ = ledger
    original_batch = batch(ledger)

    def repeat(_: int) -> Any:
        with psycopg.connect(dsn, autocommit=True) as independent:
            return bootstrap(independent, store, desc)

    with ThreadPoolExecutor(max_workers=2) as workers:
        assert list(workers.map(repeat, [1, 2])) == [first, first]
    later = uuid4()
    conn.execute(
        "INSERT INTO platform.model_bundles(bundle_id,domain,components,config_hash) "
        "VALUES (%s,%s,%s,%s)",
        (later, desc["domain"], Jsonb(first["models"]), desc["config_hash"]),
    )
    conn.execute("UPDATE platform.active_bundles SET bundle_id=%s,generation=2", (later,))
    result = bootstrap(conn, store, desc)
    assert (
        result["active_bundle_id"] == str(later)
        and result["generation"] == 2
        and not result["active_is_initial"]
    )
    assert result["bootstrap_event_id"] == first["bootstrap_event_id"]
    assert conn.execute(
        "SELECT bundle_id FROM platform.forecast_batches WHERE batch_id=%s", (original_batch,)
    ).fetchone() == (UUID(first["bundle_id"]),)


@pytest.mark.parametrize("kind", ["prediction", "abstention"])
@pytest.mark.parametrize("order", ["reservation_first", "child_first"])
def test_exactly_one_child_can_commit_in_either_insertion_order(
    ledger: Any, kind: str, order: str
) -> None:
    conn = ledger[1]
    batch_id = batch(ledger)
    with conn.transaction():
        if order == "child_first":
            child(conn, ledger, batch_id, kind)
        slot(conn, ledger, batch_id, kind)
        if order == "reservation_first":
            child(conn, ledger, batch_id, kind)
    assert conn.execute("SELECT count(*) FROM platform.official_slots").fetchone() == (1,)
    opposite = "abstention" if kind == "prediction" else "prediction"
    with pytest.raises(psycopg.errors.ForeignKeyViolation), conn.transaction():
        child(conn, ledger, batch_id, opposite)


@pytest.mark.parametrize("partial", ["reservation_only", "child_only"])
def test_no_partial_slot_commits(ledger: Any, partial: str) -> None:
    conn = ledger[1]
    batch_id = batch(ledger)
    with pytest.raises(psycopg.errors.ForeignKeyViolation), conn.transaction():
        if partial == "reservation_only":
            slot(conn, ledger, batch_id, "prediction")
        else:
            child(conn, ledger, batch_id, "prediction")
    assert conn.execute("SELECT count(*) FROM platform.official_slots").fetchone() == (0,)
    assert conn.execute("SELECT count(*) FROM platform.predictions").fetchone() == (0,)


@pytest.mark.parametrize("level", ["READ COMMITTED", "REPEATABLE READ", "SERIALIZABLE"])
@pytest.mark.parametrize("order", ["reservation_first", "child_first"])
def test_opposite_writers_cannot_commit_same_official_slot(
    ledger: Any, level: str, order: str
) -> None:
    dsn = ledger[0]
    batches = [batch(ledger), batch(ledger)]
    ready = Barrier(2)

    def attempt(index: int) -> bool:
        kind = ["prediction", "abstention"][index]
        try:
            with psycopg.connect(dsn, autocommit=True) as conn, conn.transaction():
                conn.execute("SET LOCAL lock_timeout='3s'")
                conn.execute("SET TRANSACTION ISOLATION LEVEL " + level)
                ready.wait(timeout=5)
                if order == "child_first":
                    child(conn, ledger, batches[index], kind)
                slot(conn, ledger, batches[index], kind)
                if order == "reservation_first":
                    child(conn, ledger, batches[index], kind)
            return True
        except (psycopg.errors.UniqueViolation, psycopg.errors.SerializationFailure):
            return False

    with ThreadPoolExecutor(max_workers=2) as workers:
        assert sorted(workers.map(attempt, [0, 1])) == [False, True]
    assert ledger[1].execute("SELECT count(*) FROM platform.official_slots").fetchone() == (1,)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_nonfinite_values_fail_in_actual_sql(ledger: Any, value: float) -> None:
    conn = ledger[1]
    batch_id = batch(ledger)
    with pytest.raises(psycopg.errors.CheckViolation), conn.transaction():
        slot(conn, ledger, batch_id, "prediction")
        child(conn, ledger, batch_id, "prediction", value=value)


def test_receipt_transaction_policy_and_lifecycle_batch_identity(ledger: Any) -> None:
    conn = ledger[1]
    with pytest.raises(psycopg.errors.CheckViolation), conn.transaction():
        batch_id = batch(ledger)
        conn.execute(
            "INSERT INTO platform.publication_receipts(receipt_id,batch_id,policy_version) "
            "VALUES (%s,%s,'fixture-v1')",
            (uuid4(), batch_id),
        )
    batch_id = batch(ledger)
    with pytest.raises(psycopg.errors.CheckViolation):
        conn.execute(
            "INSERT INTO platform.publication_receipts(receipt_id,batch_id,policy_version) "
            "VALUES (%s,%s,'wrong-policy')",
            (uuid4(), batch_id),
        )
    conn.execute(
        "INSERT INTO platform.publication_receipts(receipt_id,batch_id,policy_version) "
        "VALUES (%s,%s,'fixture-v1')",
        (uuid4(), batch_id),
    )
    other = batch(ledger)
    with conn.transaction():
        slot(conn, ledger, batch_id, "prediction")
        prediction_id = child(conn, ledger, batch_id, "prediction")
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        conn.execute(
            "INSERT INTO platform.prediction_events(prediction_event_id,batch_id,prediction_id,"
            "kind,reason_code) VALUES (%s,%s,%s,'status','fixture')",
            (uuid4(), other, prediction_id),
        )


def test_real_runtime_and_anonymous_denials_and_narrow_owner(ledger: Any) -> None:
    dsn, owner, *_ = ledger
    provision_runtime(owner, "synthetic_fixture_password_only")
    with psycopg.connect(
        make_conninfo(dsn, user="baseline_runtime", password="synthetic_fixture_password_only"),
        autocommit=True,
    ) as conn:
        from hoop.platform.ledger.registry import active_bundle

        current = active_bundle(conn, ledger[3]["domain"], ledger[3]["family"])
        assert current["components"] == ledger[4]["models"] and len(current["models"]) == 5
        for table in [
            "models",
            "model_bundles",
            "active_bundles",
            "forecast_batches",
            "predictions",
            "abstentions",
            "official_slots",
            "publication_receipts",
            "prediction_events",
        ]:
            for statement in [
                f"DELETE FROM platform.{table}",
                f"TRUNCATE platform.{table}",
                f"INSERT INTO platform.{table} DEFAULT VALUES",
            ]:
                with pytest.raises(psycopg.errors.InsufficientPrivilege):
                    conn.execute(statement)
        for statement in [
            "SET ROLE baseline_publisher",
            "SET ROLE baseline_owner",
            "SELECT platform.check_bundle()",
        ]:
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                conn.execute(statement)
    row = owner.execute(
        "SELECT rolcanlogin,rolsuper,rolcreaterole,rolbypassrls FROM pg_roles "
        "WHERE rolname='baseline_publisher'"
    ).fetchone()
    assert row == (False, False, False, False)
    assert not owner.execute(
        "SELECT has_schema_privilege('baseline_publisher','platform','CREATE')"
    ).fetchone()[0]
    owner.execute("SET ROLE anon")
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        owner.execute("SELECT * FROM platform.models")
    owner.execute("RESET ROLE")


def test_two_first_bootstraps_create_only_one_activation(migrated: Any) -> None:
    dsn, conn = migrated
    transport = MemoryStorage()
    store = PrivateArtifacts(Session(SETTINGS, transport))
    desc = descriptor(json.loads(POLICY_PATH.read_text()))
    desc["configuration_artifact"] = retain(
        conn, store, encoded(desc["configuration"]), kind="reports", format="json", manifest={}
    )
    start = Barrier(2)

    def initialize(_: int) -> dict[str, Any]:
        with psycopg.connect(dsn, autocommit=True) as other:
            start.wait(timeout=5)
            return bootstrap(other, PrivateArtifacts(Session(SETTINGS, transport)), desc)

    with ThreadPoolExecutor(max_workers=2) as workers:
        results = list(workers.map(initialize, [1, 2]))
    assert results[0] == results[1]
    assert conn.execute("SELECT count(*) FROM platform.models").fetchone() == (5,)
    assert conn.execute("SELECT count(*) FROM platform.active_bundles").fetchone() == (1,)
    assert conn.execute("SELECT count(*) FROM platform.run_events").fetchone() == (1,)


@pytest.mark.parametrize(
    "components",
    [{}, [], {"wrong_target": "00000000-0000-4000-8000-000000000000"}, {"points": "not-a-uuid"}],
)
def test_malformed_bundles_are_rejected(ledger: Any, components: Any) -> None:
    conn = ledger[1]
    with pytest.raises(psycopg.Error):
        conn.execute(
            "INSERT INTO platform.model_bundles(bundle_id,domain,components,config_hash) "
            "VALUES (%s,'nba',%s,%s)",
            (uuid4(), Jsonb(components), "a" * 64),
        )


def test_feature_schedule_model_and_generation_mismatches(ledger: Any) -> None:
    conn = ledger[1]
    bad = list(ledger)
    bad[6] = ledger[3]["configuration_artifact"]
    with pytest.raises(psycopg.errors.CheckViolation):
        batch(bad)
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        batch(ledger, observation=uuid4())
    with pytest.raises(psycopg.errors.CheckViolation):
        conn.execute("UPDATE platform.active_bundles SET generation=0")
    batch_id = batch(ledger)
    with pytest.raises(psycopg.errors.CheckViolation), conn.transaction():
        slot(conn, ledger, batch_id, "prediction")
        conn.execute(
            """INSERT INTO platform.predictions(prediction_id,batch_id,subject_type,
            subject_id,target,role,model_id,value,unit) VALUES (%s,%s,'player','201','points',
            'official',%s,1.5,'points')""",
            (uuid4(), batch_id, ledger[4]["models"]["minutes"]),
        )


def test_second_domain_signed_target_uses_same_ledger(ledger: Any) -> None:
    _, conn, store, *_ = ledger
    config = {
        "domain": "cards",
        "family": "match_margin",
        "version": "v1",
        "targets": {"margin": "score"},
    }
    from hoop.platform.evidence import register
    from hoop.platform.provenance import digest, parse_time
    from hoop.platform.records import immutable_insert

    desc = {
        "schema_version": 1,
        "domain": "cards",
        "family": "match_margin",
        "version": "v1",
        "targets": config["targets"],
        "code_version": "f" * 64,
        "config_hash": digest(encoded(config)),
        "configuration": config,
        "learned_artifact_id": None,
        "training_cutoff": None,
    }
    desc["configuration_artifact"] = retain(
        conn, store, encoded(config), kind="reports", format="json", manifest={}
    )
    registered = bootstrap(conn, store, desc)
    raw = retain(conn, store, b'{"fixture":"card-result"}', kind="raw", format="json", manifest={})
    check = register(
        conn,
        "source_checks",
        {
            "check_id": str(uuid4()),
            "run_id": registered["bootstrap_run_id"],
            "source_id": "synthetic-cards",
            "adapter_version": "v1",
            "requested_at": parse_time("2020-01-01T00:00:00Z"),
            "received_at": parse_time("2020-01-01T00:01:00Z"),
            "validated_at": parse_time("2020-01-01T00:02:00Z"),
            "source_published_at": None,
            "raw_artifact_id": raw["artifact_id"],
            "http_status": None,
            "record_count": 1,
            "state": "accepted",
            "validation_summary": {},
        },
    )
    event_id, observation = uuid4(), uuid4()
    with conn.transaction():
        immutable_insert(
            conn,
            "platform",
            "events",
            {
                "event_id": event_id,
                "domain": "cards",
                "source_event_id": "match-blue-red",
                "competition": "ranked",
                "season": "v1",
                "occurrence_no": 1,
                "predecessor_event_id": None,
            },
            ("event_id",),
        )
        immutable_insert(
            conn,
            "platform",
            "event_observations",
            {
                "observation_id": observation,
                "event_id": event_id,
                "source_check_id": UUID(check["check_id"]),
                "observed_at": parse_time("2020-01-01T00:02:00Z"),
                "scheduled_start": None,
                "actual_start": None,
                "state": "unknown",
                "details": {},
            },
            ("observation_id",),
        )
    other = list(ledger)
    other[4] = registered
    other[7] = event_id
    other[8] = observation
    batch_id = batch(other)
    with conn.transaction():
        slot(conn, other, batch_id, "prediction", subject="blue", target="margin")
        child(conn, other, batch_id, "prediction", subject="blue", target="margin", value=-1.25)
    assert conn.execute(
        "SELECT value FROM platform.predictions WHERE batch_id=%s", (batch_id,)
    ).fetchone() == (-1.25,)
    with pytest.raises(psycopg.errors.CheckViolation):
        batch(ledger, bundle=registered["bundle_id"])


@pytest.mark.parametrize(
    "change",
    [
        {"targets": "points"},
        {"targets": []},
        {"targets": {"minutes": None}},
        {"code_version": "z" * 64},
        {"configuration_artifact": None},
        {"schema_version": 2},
    ],
)
def test_invalid_bootstrap_descriptors_fail_without_mutation(
    ledger: Any, change: dict[str, Any]
) -> None:
    _, conn, store, desc, *_ = ledger
    before = conn.execute("SELECT count(*) FROM platform.models").fetchone()
    with pytest.raises(EvidenceError):
        bootstrap(conn, store, {**desc, **change})
    assert conn.execute("SELECT count(*) FROM platform.models").fetchone() == before
