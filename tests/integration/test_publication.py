"""Actual runtime calls, separate visibility, lost responses and immutability."""

from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from typing import Any
from uuid import UUID, uuid4

import psycopg
import pytest
from psycopg.conninfo import make_conninfo

from hoop.domains.nba.publication import publish_player
from hoop.platform.database import provision_runtime
from hoop.platform.evidence import EvidenceError
from hoop.platform.ledger.publication import confirm
from hoop.platform.prepared import retain_prepared
from tests.fixtures.publication import publication_fixture

pytestmark = pytest.mark.postgres


@pytest.fixture
def publication(migrated: Any, tmp_path: Any) -> Any:
    dsn, owner = migrated
    fixture = publication_fixture(owner, tmp_path)
    provision_runtime(owner, "synthetic_fixture_password_only")
    runtime_dsn = make_conninfo(
        dsn, user="baseline_runtime", password="synthetic_fixture_password_only"
    )
    with psycopg.connect(runtime_dsn, autocommit=True) as conn:
        yield {**fixture, "conn": conn, "owner": owner, "dsn": runtime_dsn}


def publish(p: Any, **kwargs: Any) -> Any:
    return publish_player(p["conn"], p["store"], p["retained"], UUID(p["bundle"]), **kwargs)


def test_complete_atomic_batch_separate_receipt_and_exact_retry(publication: Any) -> None:
    p = publication
    result = publish(p)
    assert result["state"] == "timely_confirmed"
    assert publish(p) == result
    assert p["conn"].execute("SELECT count(*) FROM platform.official_slots").fetchone() == (15,)
    assert p["conn"].execute("SELECT count(*) FROM platform.abstentions").fetchone() == (5,)
    assert p["conn"].execute(
        "SELECT b.insertion_transaction_id<>r.confirming_transaction_id FROM "
        "platform.forecast_batches b JOIN platform.publication_receipts r "
        "USING(batch_id)"
    ).fetchone() == (True,)


@pytest.mark.parametrize(
    "stage", ["before_insert_commit", "after_insert_commit", "after_receipt_commit"]
)
def test_interruption_and_lost_response_recovery(publication: Any, stage: str) -> None:
    p = publication

    def fail(current: str) -> None:
        if current == stage:
            raise OSError("lost response")

    with pytest.raises(EvidenceError):
        publish(p, fault=fail)
    assert p["conn"].execute("SELECT count(*) FROM platform.forecast_batches").fetchone() == (
        0 if stage == "before_insert_commit" else 1,
    )
    assert publish(p)["state"] == "timely_confirmed"
    assert p["conn"].execute("SELECT count(*) FROM platform.forecast_batches").fetchone() == (1,)


def test_racing_complete_batches_share_original_identity(publication: Any) -> None:
    p = publication

    def run(_: int) -> Any:
        with psycopg.connect(p["dsn"], autocommit=True) as conn:
            return publish_player(conn, p["store"], p["retained"], UUID(p["bundle"]))

    with ThreadPoolExecutor(max_workers=2) as workers:
        results = list(workers.map(run, [1, 2]))
    assert results[0] == results[1]


@pytest.mark.parametrize(
    "change",
    ["missing_slot", "negative", "wrong_unit", "future_cutoff", "cohort", "model", "duplicate"],
)
def test_changed_or_incomplete_input_cannot_commit(publication: Any, change: str) -> None:
    import copy

    p = publication
    changed = copy.deepcopy(p["prepared"])
    if change == "missing_slot":
        changed["entries"].pop()
    elif change == "negative":
        changed["entries"][0]["value"] = -1
    elif change == "wrong_unit":
        changed["entries"][0]["unit"] = "seconds"
    elif change == "future_cutoff":
        changed["feature_cutoff"] = (p["now"] + timedelta(days=1)).isoformat()
    elif change == "cohort":
        changed["cohort"].pop()
    elif change == "model":
        changed["descriptor"]["code_version"] = "f" * 64
    else:
        changed["entries"][-1] = changed["entries"][0]
    with pytest.raises((EvidenceError, ValueError)):
        retained = retain_prepared(p["conn"], p["store"], changed)
        publish_player(p["conn"], p["store"], retained, UUID(p["bundle"]))
    assert p["conn"].execute("SELECT count(*) FROM platform.forecast_batches").fetchone() == (0,)


def test_invalidation_remains_visible_if_lifecycle_append_pending(publication: Any) -> None:
    p = publication
    result = publish(p)
    check = p["source"]("status", {"state": "postponed"})
    observation = uuid4()
    p["conn"].execute(
        "INSERT INTO platform.event_observations(observation_id,event_id,source_che"
        "ck_id,observed_at,state,details) VALUES(%s,%s,%s,%s,'postponed','{}')",
        (observation, p["event"], check["check_id"], p["now"]),
    )
    assert confirm(p["conn"], result["batch_id"])["state"] == "invalidated"
    p["conn"].execute("SELECT platform.append_lifecycle(%s,%s)", (result["batch_id"], observation))
    p["conn"].execute("SELECT platform.append_lifecycle(%s,%s)", (result["batch_id"], observation))
    assert p["conn"].execute("SELECT count(*) FROM platform.prediction_events").fetchone() == (1,)


def test_runtime_cannot_bypass_or_forge_protected_fields(publication: Any) -> None:
    p = publication
    for query in [
        "SELECT platform.bound_json(NULL,NULL,NULL)",
        "SELECT platform.store_batch(NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL)",
        "INSERT INTO platform.publication_receipts "
        "VALUES(gen_random_uuid(),NULL,clock_timestamp(),'fake','v1')",
        "SET ROLE baseline_publisher",
        "CREATE FUNCTION nba.bypass() RETURNS int LANGUAGE sql AS 'SELECT 1'",
    ]:
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            p["conn"].execute(query)
    with p["conn"].transaction(), pytest.raises(EvidenceError, match="separate"):
        publish(p)


def test_stored_batch_without_receipt_cannot_be_replaced_or_confirmed_late(
    publication: Any,
) -> None:
    p = publication

    def stop(stage: str) -> None:
        if stage == "after_insert_commit":
            raise OSError("lost commit response")

    with pytest.raises(EvidenceError):
        publish(p, fault=stop)
    original = (
        p["conn"]
        .execute("SELECT batch_id,recorded_at,content_hash FROM platform.forecast_batches")
        .fetchone()
    )
    assert p["conn"].execute("SELECT state FROM platform.batch_status").fetchone() == (
        "stored_unverified",
    )
    # Owner adjusts a fixture clock boundary only; production has no clock override.
    p["owner"].execute(
        "UPDATE platform.event_observations SET "
        "scheduled_start=clock_timestamp()+interval '14 minutes' WHERE event_id=%s",
        (p["event"],),
    )
    with pytest.raises(psycopg.Error):
        confirm(p["conn"], original[0])
    assert p["conn"].execute("SELECT count(*) FROM platform.publication_receipts").fetchone() == (
        0,
    )
    assert (
        p["conn"]
        .execute("SELECT batch_id,recorded_at,content_hash FROM platform.forecast_batches")
        .fetchone()
        == original
    )


def test_commit_delayed_past_deadline_remains_unverified(publication: Any) -> None:
    p = publication
    deadline = p["owner"].execute("SELECT clock_timestamp()+interval '0.5 seconds'").fetchone()[0]
    p["owner"].execute(
        "UPDATE platform.event_observations SET scheduled_start=%s WHERE event_id=%s",
        (deadline + timedelta(minutes=15), p["event"]),
    )

    def cross_deadline(stage: str) -> None:
        if stage == "before_insert_commit":
            p["conn"].execute(
                "SELECT pg_sleep(greatest(0,extract(epoch FROM %s::timestamptz-"
                "clock_timestamp()))+0.01)",
                (deadline,),
            )

    with pytest.raises(EvidenceError):
        publish(p, fault=cross_deadline)
    assert p["conn"].execute("SELECT count(*) FROM platform.forecast_batches").fetchone() == (1,)
    assert p["conn"].execute("SELECT state FROM platform.batch_status").fetchone() == (
        "stored_unverified",
    )


def test_new_started_status_stale_roster_and_late_reopening_block(publication: Any) -> None:
    p = publication
    p["owner"].execute(
        "UPDATE platform.source_checks SET received_at=received_at-interval '2 "
        "days',requested_at=requested_at-interval '2 days' WHERE "
        "validation_summary->>'capability'='roster'"
    )
    with pytest.raises(EvidenceError):
        publish(p)
    p["owner"].execute(
        "UPDATE platform.source_checks SET received_at=received_at+interval '2 "
        "days',requested_at=requested_at+interval '2 days' WHERE "
        "validation_summary->>'capability'='roster'"
    )
    p["owner"].execute(
        "UPDATE platform.event_observations SET "
        "scheduled_start=clock_timestamp()+interval '14 minutes' WHERE event_id=%s",
        (p["event"],),
    )
    check = p["source"]("status", {"state": "scheduled"})
    p["conn"].execute(
        "INSERT INTO platform.event_observations(observation_id,event_id,source_che"
        "ck_id,observed_at,scheduled_start,state,details) "
        "VALUES(%s,%s,%s,clock_timestamp(),clock_timestamp()+interval '2 "
        "hours','scheduled','{}')",
        (uuid4(), p["event"], check["check_id"]),
    )
    with pytest.raises(EvidenceError):
        publish(p)


def test_same_transaction_confirmation_and_substituted_bytes_are_rejected(publication: Any) -> None:
    import json

    from psycopg.types.json import Jsonb

    p = publication
    objects = p["retained"]["objects"]
    bodies = {key: p["store"].read(objects[key]) for key in objects}
    rosters = []
    for r in p["prepared"]["roster_sources"]:
        rosters.append(
            {"roster_id": r["roster_id"], "body": p["store"].read(r["artifact"]).decode()}
        )
    args = [
        objects["prepared"]["artifact_id"],
        bodies["prepared"],
        objects["features"]["artifact_id"],
        bodies["features"],
        objects["cohort"]["artifact_id"],
        bodies["cohort"],
        Jsonb(rosters),
        p["bundle"],
    ]
    with pytest.raises(psycopg.Error), p["conn"].transaction():
        b = (
            p["conn"]
            .execute("SELECT nba.publish_player(%s,%s,%s,%s,%s,%s,%s,%s)", args)
            .fetchone()[0]
        )
        p["conn"].execute("SELECT platform.confirm_batch(%s)", (b,))
    args[1] = json.dumps({"not": "the prepared body"}).encode()
    with pytest.raises(psycopg.Error):
        p["conn"].execute("SELECT nba.publish_player(%s,%s,%s,%s,%s,%s,%s,%s)", args)
    assert p["conn"].execute("SELECT count(*) FROM platform.forecast_batches").fetchone() == (0,)


def test_conflicting_retry_and_new_champion_do_not_change_original(publication: Any) -> None:
    import copy

    from psycopg.types.json import Jsonb

    p = publication
    original = publish(p)
    changed = copy.deepcopy(p["prepared"])
    changed["entries"][0]["value"] = 99
    retained = retain_prepared(p["conn"], p["store"], changed)
    with pytest.raises(EvidenceError):
        publish_player(p["conn"], p["store"], retained, UUID(p["bundle"]))
    components = (
        p["owner"]
        .execute("SELECT components FROM platform.model_bundles WHERE bundle_id=%s", (p["bundle"],))
        .fetchone()[0]
    )
    config = p["prepared"]["descriptor"]["config_hash"]
    later = uuid4()
    p["owner"].execute(
        "INSERT INTO "
        "platform.model_bundles(bundle_id,domain,components,config_hash) "
        "VALUES(%s,'nba',%s,%s)",
        (later, Jsonb(components), config),
    )
    p["owner"].execute("UPDATE platform.active_bundles SET bundle_id=%s,generation=2", (later,))
    assert publish(p) == original
    assert confirm(p["conn"], original["batch_id"]) == original


def test_server_rejects_duplicate_json_keys_and_authoritative_fields(publication: Any) -> None:
    from hoop.platform.artifacts import retain

    p = publication
    body = b'{"schema_version":1,"schema_version":1}'
    artifact = retain(p["conn"], p["store"], body, kind="reports", format="json", manifest={})
    # No runtime grant exists even to the byte verifier; owner fixture exercises encoding.
    with pytest.raises(psycopg.Error, match="json_encoding"):
        p["owner"].execute(
            "SELECT platform.bound_json(%s,%s,'reports')", (artifact["artifact_id"], body)
        )
    prepared = {**p["prepared"], "recorded_at": p["now"].isoformat()}
    retained = retain_prepared(p["conn"], p["store"], prepared)
    with pytest.raises(EvidenceError):
        publish_player(p["conn"], p["store"], retained, UUID(p["bundle"]))


def test_generic_core_supports_signed_second_domain_only_for_trusted_owner(
    publication: Any,
) -> None:
    from psycopg.types.json import Jsonb

    p = publication
    owner = p["owner"]
    event, model, bundle = uuid4(), uuid4(), uuid4()
    owner.execute(
        "INSERT INTO platform.events(event_id,domain,source_event_id,competition,se"
        "ason,occurrence_no) VALUES(%s,'cards','match1','ranked','s1',1)",
        (event,),
    )
    owner.execute(
        "INSERT INTO platform.models(model_id,domain,family,target,version,code_ver"
        "sion,config_hash) VALUES(%s,'cards','signed','margin','1','fixture',%s)",
        (model, "a" * 64),
    )
    owner.execute(
        "INSERT INTO "
        "platform.model_bundles(bundle_id,domain,components,config_hash) "
        "VALUES(%s,'cards',%s,%s)",
        (bundle, Jsonb({"margin": str(model)}), "a" * 64),
    )
    check = p["source"]("status", {})
    observation = uuid4()
    owner.execute(
        "INSERT INTO platform.event_observations(observation_id,event_id,source_che"
        "ck_id,observed_at,scheduled_start,state,details) "
        "VALUES(%s,%s,%s,%s,%s,'scheduled','{}')",
        (observation, event, check["check_id"], p["now"], p["now"] + timedelta(hours=2)),
    )
    prepared = {
        "event": {"event_id": str(event)},
        "run_id": p["prepared"]["run_id"],
        "feature_cutoff": p["prepared"]["feature_cutoff"],
        "generated_at": p["prepared"]["generated_at"],
        "entries": [
            {
                "subject_type": "deck",
                "subject_id": "d1",
                "target": "margin",
                "value": -1.25,
                "unit": "crowns",
            }
        ],
    }
    objects = p["retained"]["objects"]
    with owner.transaction():
        owner.execute(
            "SELECT platform.store_batch(%s,%s,%s,%s,%s,%s,%s,'signed')",
            (
                Jsonb(prepared),
                bundle,
                objects["prepared"]["artifact_id"],
                objects["features"]["artifact_id"],
                objects["cohort"]["artifact_id"],
                observation,
                p["now"] + timedelta(hours=2),
            ),
        )
    assert owner.execute("SELECT value FROM platform.predictions").fetchone() == (-1.25,)
