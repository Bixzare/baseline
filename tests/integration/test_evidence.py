"""Evidence constraints and real role permissions, with HTTP mocked separately."""

import json
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import psycopg
import pytest
from psycopg.conninfo import make_conninfo
from psycopg.types.json import Jsonb

from hoop.domains.nba.sources.persist import persist_observation
from hoop.platform.artifacts import ArtifactError, PrivateArtifacts, Session, retain
from hoop.platform.database import provision_runtime
from hoop.platform.evidence import EvidenceError, register
from hoop.platform.provenance import Archive
from tests.fixtures.storage_client import OTHER, SETTINGS, USER, MemoryStorage

pytestmark = pytest.mark.postgres


@pytest.fixture
def runtime(migrated: Any) -> Any:
    dsn, owner = migrated
    provision_runtime(owner, "synthetic_fixture_password_only")
    runtime_dsn = make_conninfo(
        dsn, user="baseline_runtime", password="synthetic_fixture_password_only"
    )
    with psycopg.connect(runtime_dsn, autocommit=True) as conn:
        yield owner, conn, runtime_dsn


def run(conn: Any) -> dict[str, Any]:
    return register(
        conn,
        "runs",
        {
            "run_id": str(uuid4()),
            "operation": "collect",
            "domain": "synthetic",
            "environment": "rehearsal",
            "code_version": "fixture-v1",
            "config_hash": "a" * 64,
        },
    )


def source_record(run_id: str, artifact_id: str | None) -> dict[str, Any]:
    return {
        "check_id": str(uuid4()),
        "run_id": run_id,
        "source_id": "synthetic-card-game",
        "adapter_version": "v1",
        "requested_at": datetime(2020, 1, 1, 0, 0, tzinfo=UTC),
        "received_at": datetime(2020, 1, 1, 0, 1, tzinfo=UTC),
        "validated_at": datetime(2020, 1, 1, 0, 2, tzinfo=UTC),
        "source_published_at": None,
        "raw_artifact_id": artifact_id,
        "http_status": 200,
        "record_count": 0,
        "state": "accepted",
        "validation_summary": {"parser": "v1"},
    }


def test_exact_retries_conflicts_and_runtime_immutability(runtime: Any) -> None:
    owner, conn, _ = runtime
    record = run(conn)
    assert register(conn, "runs", record) == record
    with pytest.raises(EvidenceError, match="conflicts"):
        register(conn, "runs", {**record, "operation": "different"})
    artifact = retain(
        conn,
        PrivateArtifacts(Session(SETTINGS, MemoryStorage())),
        b"{}",
        kind="raw",
        format="json",
        manifest={"schema": "fixture-v1"},
    )
    accepted = source_record(record["run_id"], artifact["artifact_id"])
    result = register(conn, "source_checks", accepted)
    assert result["record_count"] == 0
    assert register(conn, "source_checks", accepted) == result
    event = {
        "run_event_id": str(uuid4()),
        "run_id": record["run_id"],
        "state": "succeeded",
        "reason_code": None,
        "details": {"counts": {"checks": 1}, "duration_ms": 5},
    }
    assert register(conn, "run_events", event) == event
    for table in ["runs", "run_events", "artifacts", "source_checks"]:
        identity = {
            "runs": "run_id",
            "run_events": "run_event_id",
            "artifacts": "artifact_id",
            "source_checks": "check_id",
        }[table]
        for operation in [
            f"DELETE FROM platform.{table}",
            f"TRUNCATE platform.{table}",
            f"UPDATE platform.{table} SET {identity}=gen_random_uuid()",
        ]:
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                conn.execute(operation)
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        conn.execute(
            "INSERT INTO platform.runs(run_id,operation,domain,environment,code_version,"
            "config_hash,started_at) VALUES (%s,'x','x','rehearsal','x',%s,'2000-01-01')",
            (uuid4(), "a" * 64),
        )
    owner.execute("SET ROLE anon")
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        owner.execute("SELECT * FROM platform.runs")
    owner.execute("RESET ROLE")


@pytest.mark.parametrize(
    "change",
    [
        {"raw_artifact_id": None},
        {"record_count": None},
        {"record_count": -1},
        {"received_at": None},
        {"validated_at": "2019-01-01T00:00:00Z"},
        {"http_status": 403},
        {"state": "invalid"},
        {"validation_summary": {"password": "hidden"}},
    ],
)
def test_bad_source_contract_is_refused(runtime: Any, change: dict[str, Any]) -> None:
    _, conn, _ = runtime
    parent = run(conn)
    artifact = retain(
        conn,
        PrivateArtifacts(Session(SETTINGS, MemoryStorage())),
        b"{}",
        kind="raw",
        format="json",
        manifest={},
    )
    with pytest.raises(EvidenceError):
        register(
            conn,
            "source_checks",
            {**source_record(parent["run_id"], artifact["artifact_id"]), **change},
        )


def test_database_sanitization_cannot_be_bypassed_by_direct_insert(runtime: Any) -> None:
    _, conn, _ = runtime
    for unsafe in [
        {"nested": {"refresh_token": "hidden"}},
        {"request": "https://host/path?token=hidden"},
        {"text": "x" * 17000},
    ]:
        with pytest.raises(psycopg.errors.CheckViolation):
            conn.execute(
                "INSERT INTO platform.run_events(run_event_id,run_id,state,details) "
                "VALUES (%s,%s,'started',%s)",
                (uuid4(), run(conn)["run_id"], Jsonb(unsafe)),
            )


def test_concurrent_artifact_registration_and_uri_conflict(runtime: Any) -> None:
    _, conn, dsn = runtime
    store = PrivateArtifacts(Session(SETTINGS, MemoryStorage()))
    descriptor = store.put(b"hello", kind="raw", format="json")

    def attempt(format: str) -> dict[str, Any] | None:
        with psycopg.connect(dsn, autocommit=True) as independent:
            try:
                return register(
                    independent,
                    "artifacts",
                    {"artifact_id": str(uuid4()), **descriptor, "format": format, "manifest": {}},
                )
            except EvidenceError:
                return None

    with ThreadPoolExecutor(max_workers=2) as workers:
        results = list(workers.map(attempt, ["json", "json"]))
    assert results[0] == results[1]
    assert conn.execute("SELECT count(*) FROM platform.artifacts").fetchone() == (1,)
    assert attempt("csv") is None
    parent = run(conn)
    a, b = (
        source_record(parent["run_id"], results[0]["artifact_id"]),
        source_record(parent["run_id"], results[0]["artifact_id"]),
    )
    register(conn, "source_checks", a)
    register(conn, "source_checks", b)
    assert conn.execute("SELECT count(*) FROM platform.source_checks").fetchone() == (2,)


def test_network_is_refused_inside_an_open_transaction(runtime: Any) -> None:
    _, conn, _ = runtime
    transport = MemoryStorage()
    with conn.transaction(), pytest.raises(ArtifactError, match="transaction"):
        retain(
            conn,
            PrivateArtifacts(Session(SETTINGS, transport)),
            b"hi",
            kind="raw",
            format="txt",
            manifest={},
        )
    assert not transport.calls


def test_upload_then_database_failure_can_recover_same_object(runtime: Any) -> None:
    _, conn, dsn = runtime
    transport = MemoryStorage()
    store = PrivateArtifacts(Session(SETTINGS, transport))

    class DisconnectAfterUpload(PrivateArtifacts):
        def put(self, body: bytes, **kwargs: Any) -> dict[str, Any]:
            result = super().put(body, **kwargs)
            conn.close()
            return result

    with pytest.raises(EvidenceError):
        retain(
            conn,
            DisconnectAfterUpload(store.session),
            b"hello",
            kind="raw",
            format="txt",
            manifest={},
        )
    assert len(transport.objects) == 1
    with psycopg.connect(dsn, autocommit=True) as recovered:
        assert (
            retain(recovered, store, b"hello", kind="raw", format="txt", manifest={})["byte_count"]
            == 5
        )
        assert recovered.execute("SELECT count(*) FROM platform.artifacts").fetchone() == (1,)


def test_actual_storage_policies_in_isolated_provider_fixture(migrated: Any) -> None:
    _, conn = migrated
    conn.execute(
        "INSERT INTO platform.artifact_storage_bindings(backend_user_id,bucket_id) "
        "VALUES (%s,'baseline-artifacts')",
        (USER,),
    )
    conn.execute("INSERT INTO storage.buckets(id) VALUES ('baseline-artifacts'),('unrelated')")
    key = "raw/aa/" + "a" * 64
    conn.execute("SET ROLE authenticated")
    conn.execute("SELECT set_config('request.jwt.claim.sub',%s,false)", (USER,))
    conn.execute(
        "INSERT INTO storage.objects(id,bucket_id,name) VALUES (%s,'baseline-artifacts',%s)",
        (uuid4(), key),
    )
    assert conn.execute("SELECT count(*) FROM storage.objects").fetchone() == (1,)
    assert conn.execute("UPDATE storage.objects SET name=%s", ("raw/bb/" + "b" * 64,)).rowcount == 0
    assert conn.execute("DELETE FROM storage.objects").rowcount == 0
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        conn.execute("INSERT INTO storage.buckets(id) VALUES ('forbidden')")
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        conn.execute(
            "INSERT INTO storage.objects(id,bucket_id,name) VALUES (%s,'unrelated',%s)",
            (uuid4(), key),
        )
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        conn.execute("SELECT * FROM platform.runs")
    conn.execute("SELECT set_config('request.jwt.claim.sub',%s,false)", (OTHER,))
    assert conn.execute("SELECT count(*) FROM storage.objects").fetchone() == (0,)
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        conn.execute(
            "INSERT INTO storage.objects(id,bucket_id,name) VALUES (%s,'baseline-artifacts',%s)",
            (uuid4(), key),
        )
    conn.execute("RESET ROLE")
    conn.execute("SET ROLE anon")
    assert conn.execute("SELECT count(*) FROM storage.objects").fetchone() == (0,)
    conn.execute("RESET ROLE")
    conn.execute("SET ROLE baseline_runtime")
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        conn.execute(
            "INSERT INTO storage.objects(id,bucket_id,name) VALUES (%s,'baseline-artifacts',%s)",
            (uuid4(), key),
        )
    conn.execute("RESET ROLE")


def test_saved_probe_bridge_success_invalid_timeout_storage_and_db_failure(
    runtime: Any, tmp_path: Path
) -> None:
    _, conn, _ = runtime
    parent = run(conn)
    archive = Archive(tmp_path / "archive")
    sha, path = archive.raw(b"{}")
    report = {
        "observation_id": "fixture",
        "capability": "status",
        "request_url": "https://cdn.nba.com/static/fixture.json",
        "request_context": {},
        "environment": "local",
        "parser_version": "fixture-v1",
        "policy": {},
        "outcome": "verified_sample",
        "requested_at": "2020-01-01T00:00:00Z",
        "received_at": "2020-01-01T00:01:00Z",
        "validated_at": "2020-01-01T00:02:00Z",
        "source_publication_time": None,
        "record_count": 0,
        "http_status": 200,
        "raw_sha256": sha,
        "raw_path": path,
    }
    store = PrivateArtifacts(Session(SETTINGS, MemoryStorage()))

    def persist(value: dict[str, Any], client: Any = store) -> dict[str, Any]:
        return persist_observation(
            conn,
            client,
            value,
            archive.root,
            run_id=parent["run_id"],
            failure_directory=tmp_path / "failures",
        )

    assert persist(report)["state"] == "accepted"
    invalid = {
        **report,
        "observation_id": "invalid",
        "outcome": "failed",
        "validated_at": None,
        "record_count": None,
    }
    assert persist(invalid)["state"] == "invalid"
    timeout = {
        **invalid,
        "observation_id": "timeout",
        "received_at": None,
        "raw_path": None,
        "raw_sha256": None,
        "http_status": None,
    }
    assert persist(timeout)["state"] == "transport_failure"
    transport = MemoryStorage()
    transport.upload_status = 403
    assert (
        persist(
            {**report, "observation_id": "storage-failure"},
            PrivateArtifacts(Session(SETTINGS, transport)),
        )["state"]
        == "storage_failure"
    )
    conn.close()
    with pytest.raises(EvidenceError, match="local report"):
        persist({**timeout, "observation_id": "db-failure"})
    failures = list((tmp_path / "failures").glob("*.json"))
    assert len(failures) == 1
    assert json.loads(failures[0].read_text())["durable_recording_confirmed"] is False


@pytest.mark.parametrize(
    "changes",
    [
        {"sha256": "invalid"},
        {"byte_count": -1},
        {"schema_version": 0},
        {"storage_uri": "https://host/file?token=private"},
        {"kind": "models"},
        {"manifest": {"token": "private"}},
    ],
)
def test_invalid_artifact_metadata_is_never_registered(
    runtime: Any, changes: dict[str, Any]
) -> None:
    _, conn, _ = runtime
    descriptor = PrivateArtifacts(Session(SETTINGS, MemoryStorage())).put(
        b"hello", kind="raw", format="json"
    )
    with pytest.raises(EvidenceError):
        register(
            conn,
            "artifacts",
            {"artifact_id": str(uuid4()), **descriptor, "manifest": {}, **changes},
        )
    assert conn.execute("SELECT count(*) FROM platform.artifacts").fetchone() == (0,)


def test_source_evidence_cannot_reference_a_model_artifact(runtime: Any) -> None:
    _, conn, _ = runtime
    parent = run(conn)
    artifact = retain(
        conn,
        PrivateArtifacts(Session(SETTINGS, MemoryStorage())),
        b"{}",
        kind="models",
        format="json",
        manifest={},
    )
    with pytest.raises(EvidenceError):
        register(conn, "source_checks", source_record(parent["run_id"], artifact["artifact_id"]))
