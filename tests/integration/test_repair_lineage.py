"""Portable repair evidence can be rehearsed without accepting or importing facts."""

import json
from pathlib import Path
from typing import Any

import psycopg
import pytest
from psycopg.conninfo import make_conninfo

from hoop.domains.nba.history.lineage import KIND, retain_lineage, verify_lineage
from hoop.domains.nba.sources.seed import build_seed
from hoop.platform.artifacts import PrivateArtifacts, Session, retain
from hoop.platform.database import provision_runtime
from hoop.platform.evidence import EvidenceError
from tests.fixtures.adjudication import NOW, fixture
from tests.fixtures.storage_client import SETTINGS, MemoryStorage

pytestmark = pytest.mark.postgres


@pytest.fixture
def staged(migrated: Any, tmp_path: Path) -> Any:
    dsn, owner = migrated
    provision_runtime(owner, "synthetic_fixture_password_only")
    case = fixture(tmp_path)
    report = build_seed(
        case["source"],
        case["manifest"],
        case["archive"],
        inventory=case["inventory"],
        repair_paths=case["patches"],
        now=NOW,
    )
    transport = MemoryStorage()
    store = PrivateArtifacts(Session(SETTINGS, transport))
    with psycopg.connect(
        make_conninfo(dsn, user="baseline_runtime", password="synthetic_fixture_password_only"),
        autocommit=True,
    ) as conn:
        root = retain_lineage(conn, store, report, case["archive"])
        yield conn, store, transport, root, report, case


def test_exact_retries_and_readback_do_not_create_accepted_data(staged: Any) -> None:
    conn, store, _, root, report, case = staged
    before = conn.execute("SELECT count(*) FROM platform.artifacts").fetchone()[0]
    assert retain_lineage(conn, store, report, case["archive"]) == root
    assert conn.execute("SELECT count(*) FROM platform.artifacts").fetchone()[0] == before
    verified = verify_lineage(conn, store, root["artifact_id"])
    assert verified["verified"] and verified["artifacts_verified"] == 5
    assert verified["candidate_manifest_sha256"] == report["manifest_artifact"]["sha256"]
    assert not verified["seed_accepted"] and not verified["hosted_fact_import_performed"]
    for table in ["platform.source_checks", "nba.player_game_versions", "platform.predictions"]:
        assert conn.execute("SELECT count(*) FROM " + table).fetchone() == (0,)


@pytest.mark.parametrize("mode", ["missing_proof", "wrong_reference", "accepted_marker"])
def test_semantically_incomplete_graph_cannot_pass_even_with_valid_root_hash(
    staged: Any, mode: str
) -> None:
    conn, store, _, root, _, _ = staged
    graph = json.loads(store.read(root))
    if mode == "missing_proof":
        graph["artifacts"].pop()
    elif mode == "wrong_reference":
        graph["artifacts"][1]["storage_uri"] = "supabase://wrong/bucket/key"
    else:
        graph["seed_accepted"] = True
    forged = retain(
        conn,
        store,
        json.dumps(graph).encode(),
        kind="reports",
        format="json",
        manifest={
            "lineage_kind": KIND,
            "candidate_manifest_sha256": graph["candidate_manifest_sha256"],
        },
    )
    with pytest.raises(EvidenceError):
        verify_lineage(conn, store, forged["artifact_id"])


@pytest.mark.parametrize("fail_readback", [False, True])
def test_cli_records_durable_terminal_event_and_never_accepts_seed(
    staged: Any, monkeypatch: Any, tmp_path: Path, capsys: Any, fail_readback: bool
) -> None:
    from contextlib import contextmanager

    from hoop.domains.nba.history import lineage

    conn, store, _, _, _, case = staged

    @contextmanager
    def connected():
        yield conn

    monkeypatch.setattr(lineage, "connection", connected)
    monkeypatch.setattr(lineage, "health", lambda c: {"role": "baseline_runtime"})
    monkeypatch.setattr(lineage.Settings, "from_env", lambda: SETTINGS)
    monkeypatch.setattr(lineage, "PrivateArtifacts", lambda session: store)
    if fail_readback:

        def failure(*args, **kwargs):
            raise EvidenceError("Synthetic readback failure")

        monkeypatch.setattr(lineage, "verify_lineage", failure)
    output = tmp_path / "rehearsal.json"
    monkeypatch.setattr(
        "sys.argv",
        [
            "lineage",
            "stage",
            "--archive",
            str(case["archive"]),
            "--confirm-rehearsal",
            "--report",
            str(output),
        ],
    )
    assert lineage.main() == int(fail_readback)
    report = json.loads(capsys.readouterr().out)
    assert report["verified"] is not fail_readback and not report["seed_accepted"]
    events = conn.execute(
        "SELECT state,details FROM platform.run_events ORDER BY recorded_at"
    ).fetchall()
    assert [e[0] for e in events] == ["started", "failed" if fail_readback else "succeeded"]
    assert isinstance(events[1][1]["counts"], dict)
    assert events[1][1]["duration_ms"] >= 0
    if fail_readback:
        assert report["failure_phase"] == "readback"
        assert events[1][1]["failure_type"] == "EvidenceError"
    assert conn.execute("SELECT count(*) FROM nba.player_game_versions").fetchone() == (0,)
