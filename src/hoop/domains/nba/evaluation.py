"""Freeze as-of NBA ledger/opportunity references, then read verified artifacts."""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid5

import psycopg
from psycopg.rows import dict_row

from hoop.platform.artifacts import PrivateArtifacts, retain
from hoop.platform.evaluation import evaluate
from hoop.platform.evidence import EvidenceError
from hoop.platform.prepared import encoded
from hoop.platform.provenance import digest, parse_time
from hoop.platform.records import immutable_insert

POLICY = Path(__file__).parents[4] / "configs/evaluation.json"


def periods(cutoff: datetime, policy: dict[str, Any]) -> dict[str, tuple[datetime, datetime]]:
    start = parse_time(policy["season_lower_bound"])
    if cutoff.tzinfo is None or cutoff <= start:
        raise EvidenceError("Report cutoff must follow the season bound")
    return {
        **{f"{days}d": (max(start, cutoff - timedelta(days=days)), cutoff) for days in [7, 30]},
        "season": (start, cutoff),
    }


def capture(
    conn: psycopg.Connection[Any],
    store: PrivateArtifacts,
    start: datetime,
    end: datetime,
    cutoff: datetime,
    *,
    kind: str = "live",
    policy: dict[str, Any] | None = None,
    references: dict[str, Any] | None = None,
) -> dict[str, Any]:
    policy = policy or json.loads(POLICY.read_text())
    if (
        kind not in {"live", "rehearsal"}
        or any(t.tzinfo is None for t in [start, end, cutoff])
        or not start < end <= cutoff
    ):
        raise EvidenceError("Explicit supported report kind and aware half-open period required")
    environment = "production" if kind == "live" else "rehearsal"
    with conn.transaction(), conn.cursor(row_factory=dict_row) as cursor:
        cursor.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
        clock = cursor.execute("SELECT clock_timestamp() AS now").fetchone()
        if clock is None or cutoff > clock["now"]:
            raise EvidenceError("Report cutoff cannot be in the future")
        events = cursor.execute(
            "SELECT e.*,g.home_team_id,g.away_team_id FROM platform.events e JOIN "
            "nba.games g USING(event_id) WHERE domain='nba' AND season=%s AND "
            "competition='regular' AND created_at<=%s ORDER BY event_id LIMIT 2001",
            (policy["season"], cutoff),
        ).fetchall()
        if len(events) > 2000:
            raise EvidenceError("Report event budget exceeded")
        if references:
            events = [
                e for e in events if str(e["event_id"]) in references["predictions"]["event_ids"]
            ]
        ids = [e["event_id"] for e in events]
        observations = cursor.execute(
            """SELECT o.*,s.received_at,s.validated_at,s.source_published_at,
          s.validation_summary FROM platform.event_observations o
          JOIN platform.source_checks s ON s.check_id=o.source_check_id
          JOIN platform.runs r ON r.run_id=s.run_id
          WHERE o.event_id=ANY(%s) AND o.recorded_at<=%s AND o.observed_at<=%s
          AND s.state='accepted' AND s.validated_at<=%s AND s.recorded_at<=%s
          AND r.environment=%s ORDER BY o.observed_at,o.recorded_at,o.observation_id LIMIT 50001""",
            (ids, cutoff, cutoff, cutoff, cutoff, environment),
        ).fetchall()
        batches = cursor.execute(
            """SELECT b.* FROM platform.forecast_batches b JOIN platform.runs r USING(run_id)
          WHERE b.event_id=ANY(%s) AND b.family='player_recent_appearance_mean'
          AND b.recorded_at<=%s AND r.environment=%s ORDER BY b.batch_id LIMIT 2001""",
            (ids, cutoff, environment),
        ).fetchall()
        batch_ids = [b["batch_id"] for b in batches]
        receipts = cursor.execute(
            "SELECT * FROM platform.publication_receipts WHERE batch_id=ANY(%s) AND "
            "observed_committed_at<=%s",
            (batch_ids, cutoff),
        ).fetchall()
        invalidations = cursor.execute(
            "SELECT * FROM platform.prediction_events WHERE batch_id=ANY(%s) AND "
            "recorded_at<=%s AND kind='invalidation'",
            (batch_ids, cutoff),
        ).fetchall()
        predictions = cursor.execute(
            "SELECT * FROM platform.predictions WHERE batch_id=ANY(%s) ORDER BY "
            "batch_id,subject_id,target LIMIT 700001",
            (batch_ids,),
        ).fetchall()
        abstentions = cursor.execute(
            "SELECT * FROM platform.abstentions WHERE batch_id=ANY(%s) ORDER BY "
            "batch_id,subject_id,target LIMIT 700001",
            (batch_ids,),
        ).fetchall()
        rosters = cursor.execute(
            """SELECT rs.*,s.received_at,s.validated_at,s.source_published_at,s.validation_summary
          FROM nba.roster_snapshots rs
          JOIN platform.source_checks s ON s.check_id=rs.source_check_id
          JOIN platform.runs r ON r.run_id=s.run_id
          WHERE rs.season=%s AND rs.recorded_at<=%s
          AND s.state='accepted' AND s.validated_at<=%s AND s.recorded_at<=%s AND r.environment=%s
          ORDER BY rs.validated_at,rs.recorded_at,rs.roster_id LIMIT 10001""",
            (policy["season"], cutoff, cutoff, cutoff, environment),
        ).fetchall()
        versions = cursor.execute(
            """SELECT DISTINCT ON(v.event_id) v.* FROM platform.outcome_versions v
          JOIN platform.source_checks s ON s.check_id=v.source_check_id
          JOIN platform.runs r ON r.run_id=s.run_id
          WHERE v.event_id=ANY(%s) AND v.observed_at<=%s
          AND v.recorded_at<=%s AND r.environment=%s
          AND (%s::uuid[] IS NULL OR v.outcome_version_id=ANY(%s::uuid[]))
          ORDER BY v.event_id,v.observed_at DESC,v.recorded_at DESC,v.outcome_version_id DESC""",
            (
                ids,
                cutoff,
                cutoff,
                environment,
                references["outcomes"]["outcome_version_ids"] if references else None,
                references["outcomes"]["outcome_version_ids"] if references else None,
            ),
        ).fetchall()
        artifacts = cursor.execute(
            "SELECT * FROM platform.artifacts WHERE artifact_id=ANY(%s)",
            (
                [b["cohort_artifact_id"] for b in batches]
                + [r["members_artifact_id"] for r in rosters]
                + [v["outcome_artifact_id"] for v in versions],
            ),
        ).fetchall()
        models = cursor.execute(
            "SELECT m.*,b.bundle_id FROM platform.models m JOIN platform.model_bundles "
            "b ON b.components->>m.target=m.model_id::text WHERE b.bundle_id=ANY(%s) "
            "ORDER BY b.bundle_id,m.target,m.model_id",
            ([b["bundle_id"] for b in batches],),
        ).fetchall()
    if references:
        refs = references["predictions"]
        observations = [
            o for o in observations if str(o["observation_id"]) in refs["observation_ids"]
        ]
        batches = [b for b in batches if str(b["batch_id"]) in refs["batch_ids"]]
        receipts = [r for r in receipts if str(r["receipt_id"]) in refs["receipt_ids"]]
        invalidations = [
            i for i in invalidations if str(i["prediction_event_id"]) in refs["invalidation_ids"]
        ]
        rosters = [r for r in rosters if str(r["roster_id"]) in refs["roster_ids"]]
    if (
        len(observations) > 50000
        or len(predictions) > 700000
        or len(abstentions) > 700000
        or len(rosters) > 10000
    ):
        raise EvidenceError("Report input budget exceeded")
    by_artifact = {a["artifact_id"]: a for a in artifacts}
    bodies = {}

    def body(identity: UUID) -> Any:
        if identity not in bodies:
            if identity not in by_artifact:
                raise EvidenceError("Report artifact reference missing")
            bodies[identity] = json.loads(store.read(by_artifact[identity]))
        return bodies[identity]

    frozen_events = []
    selected_observations: list[str] = []
    selected_rosters: list[str] = []
    selected_batches = []
    selected_versions = []
    for e in events:
        obs = [o for o in observations if o["event_id"] == e["event_id"]]
        # No evidence from the chosen environment means this isn't its inventory.
        if not obs:
            continue
        effective = None
        selected = None
        for o in obs:
            if o["scheduled_start"] is None:
                continue
            if (
                effective
                and o["scheduled_start"] > effective
                and max(o["observed_at"], o["recorded_at"]) >= effective - timedelta(minutes=15)
            ):
                continue
            effective = o["scheduled_start"]
            selected = o
        if effective is not None and not start <= effective < end:
            continue
        selected_observations.extend(str(o["observation_id"]) for o in obs)
        row: dict[str, Any] = {
            "event_id": str(e["event_id"]),
            "state": "missing_batch",
            "cohort": None,
            "decisions": [],
            "actuals": [],
            "participants": [],
            "schedule_observation_id": str(selected["observation_id"]) if selected else None,
        }
        if effective is None:
            row["state"] = "unknown_schedule"
            frozen_events.append(row)
            continue
        if any(o["state"] in {"postponed", "cancelled"} for o in obs):
            row["state"] = "excluded"
        elif obs[-1]["state"] == "unknown":
            row["state"] = "pending_occurrence"
        found = [b for b in batches if b["event_id"] == e["event_id"]]
        if len(found) > 1:
            raise EvidenceError("Multiple family batches in report")
        if found:
            b = found[0]
            selected_batches.append(str(b["batch_id"]))
            row["cohort"] = [
                {"subject_type": "player", "subject_id": m["player_id"]}
                for m in body(b["cohort_artifact_id"])
            ]
            receipt = next((r for r in receipts if r["batch_id"] == b["batch_id"]), None)
            invalid = any(i["batch_id"] == b["batch_id"] for i in invalidations)
            if receipt:
                invalid = invalid or any(
                    (
                        o["actual_start"] is not None
                        and o["actual_start"] <= receipt["observed_committed_at"]
                    )
                    or (
                        o["scheduled_start"] is not None
                        and o["scheduled_start"] - timedelta(minutes=15)
                        <= receipt["observed_committed_at"]
                    )
                    for o in obs
                )
            if row["state"] not in {"excluded", "pending_occurrence"}:
                row["state"] = (
                    "invalidated"
                    if invalid
                    else "timely_confirmed"
                    if receipt
                    and receipt["observed_committed_at"] < effective - timedelta(minutes=15)
                    and receipt["confirming_transaction_id"] != b["insertion_transaction_id"]
                    else "stored_unverified"
                )
            row["decisions"] = [
                {**p, "value": p.get("value"), "unit": policy["targets"][p["target"]]}
                for p in [*predictions, *abstentions]
                if p["batch_id"] == b["batch_id"]
            ]
        else:
            candidates = []
            deadline = min(cutoff, effective - timedelta(minutes=15))
            for team in [e["home_team_id"], e["away_team_id"]]:
                eligible = [
                    r
                    for r in rosters
                    if r["team_id"] == team
                    and r["recorded_at"] <= deadline
                    and r["validated_at"] <= deadline
                    and r["received_at"] >= deadline - timedelta(hours=24)
                    and (
                        r["source_published_at"] is None
                        or deadline - timedelta(hours=24) <= r["source_published_at"] <= deadline
                    )
                    and (
                        not r["validation_summary"].get("source_generated_at")
                        or deadline - timedelta(hours=24)
                        <= parse_time(r["validation_summary"]["source_generated_at"])
                        <= deadline
                    )
                ]
                if not eligible:
                    break
                best = eligible[-1]
                if any(
                    r["validated_at"] == best["validated_at"]
                    and r["members_artifact_id"] != best["members_artifact_id"]
                    for r in eligible
                ):
                    break
                members = body(best["members_artifact_id"])
                if members.get("team_id") != team or members.get("season") != e["season"]:
                    raise EvidenceError("Roster opportunity identity mismatch")
                candidates.append(best)
            if len(candidates) == 2:
                row["cohort"] = [
                    {"subject_type": "player", "subject_id": m["player_id"]}
                    for r in candidates
                    for m in body(r["members_artifact_id"])["players"]
                ]
                selected_rosters.extend(str(r["roster_id"]) for r in candidates)
        outcome = next((v for v in versions if v["event_id"] == e["event_id"]), None)
        if outcome:
            selected_versions.append(str(outcome["outcome_version_id"]))
            data = body(outcome["outcome_artifact_id"])
            if data.get("event_id") != str(e["event_id"]):
                raise EvidenceError("Outcome report identity mismatch")
            players = {p["player_id"]: p for p in data["normalized"]["players"]}
            row["participants"] = [
                {"subject_type": "player", "subject_id": p["player_id"]}
                for p in players.values()
                if p["participation"] == "played"
            ]
            for a in data["entries"]:
                if a["subject_type"] != "player" or a["target"] not in policy["targets"]:
                    continue
                p = players.get(a["subject_id"], {})
                seconds = p.get("minutes_seconds")
                band = (
                    "unknown_actual_minutes"
                    if seconds is None
                    else "actual_minutes_lt10"
                    if float(seconds) < 600
                    else "actual_minutes_10_lt25"
                    if float(seconds) < 1500
                    else "actual_minutes_ge25"
                )
                row["actuals"].append(
                    {**a, "diagnostic_groups": [band, "team:" + p.get("team_id", "unknown")]}
                )
        frozen_events.append(row)
    common = {
        "schema_version": 1,
        "kind": kind,
        "domain": "nba",
        "period_start": start.isoformat(),
        "period_end": end.isoformat(),
        "cutoff": cutoff.isoformat(),
        "policy": policy,
        "code_hash": digest(
            Path(__file__).read_text().encode()
            + b"\n"
            + (Path(__file__).parents[2] / "platform/evaluation.py").read_text().encode()
        ),
        "dependency_hash": digest((Path(__file__).parents[4] / "uv.lock").read_text().encode()),
    }
    pred_manifest = {
        **common,
        "event_ids": [r["event_id"] for r in frozen_events],
        "observation_ids": sorted(set(selected_observations)),
        "batch_ids": sorted(selected_batches),
        "roster_ids": sorted(set(selected_rosters)),
        "receipt_ids": sorted(
            str(r["receipt_id"]) for r in receipts if str(r["batch_id"]) in selected_batches
        ),
        "invalidation_ids": sorted(
            str(i["prediction_event_id"])
            for i in invalidations
            if str(i["batch_id"]) in selected_batches
        ),
    }
    outcome_manifest = {**common, "outcome_version_ids": sorted(selected_versions)}
    report = evaluate(frozen_events, policy["targets"])
    report["metadata_unavailable"] = ["role", "availability diagnostic grouping"]
    report["model_versions"] = [
        {
            k: str(m[k])
            for k in ["model_id", "bundle_id", "target", "version", "code_version", "config_hash"]
        }
        for m in models
        if any(
            str(b["bundle_id"]) == str(m["bundle_id"]) and str(b["batch_id"]) in selected_batches
            for b in batches
        )
    ]
    return {
        "predictions_manifest": pred_manifest,
        "outcomes_manifest": outcome_manifest,
        "report": report,
    }


def persist(
    conn: psycopg.Connection[Any],
    store: PrivateArtifacts,
    frozen: dict[str, Any],
    *,
    fault: Any = lambda: None,
) -> dict[str, Any]:
    prediction = frozen["predictions_manifest"]
    identity = digest(encoded({"predictions": prediction, "outcomes": frozen["outcomes_manifest"]}))
    report_id = uuid5(NAMESPACE_URL, "baseline:evaluation:" + identity)
    objects = {
        key: retain(conn, store, encoded(frozen[key]), kind="reports", format="json", manifest={})
        for key in ["predictions_manifest", "outcomes_manifest", "report"]
    }
    with conn.transaction():
        immutable_insert(
            conn,
            "platform",
            "evaluation_reports",
            {
                "report_id": report_id,
                "domain": "nba",
                "report_kind": prediction["kind"],
                "policy_version": prediction["policy"]["policy_version"],
                "period_start": parse_time(prediction["period_start"]),
                "period_end": parse_time(prediction["period_end"]),
                "report_cutoff": parse_time(prediction["cutoff"]),
                "predictions_manifest_id": UUID(objects["predictions_manifest"]["artifact_id"]),
                "outcomes_manifest_id": UUID(objects["outcomes_manifest"]["artifact_id"]),
                "report_artifact_id": UUID(objects["report"]["artifact_id"]),
                "input_hash": identity,
                "summary": {
                    "counts": frozen["report"]["coverage"],
                    "metrics": frozen["report"]["metrics"],
                },
            },
            ("report_id",),
        )
        fault()
    return {
        "report_id": str(report_id),
        "input_hash": identity,
        "objects": objects,
        "artifact_bytes": sum(o["byte_count"] for o in objects.values()),
        "summary": frozen["report"],
    }


def reproduce(
    conn: psycopg.Connection[Any], store: PrivateArtifacts, report_id: UUID
) -> dict[str, Any]:
    with conn.cursor(row_factory=dict_row) as cursor:
        row = cursor.execute(
            "SELECT * FROM platform.evaluation_reports WHERE report_id=%s", (report_id,)
        ).fetchone()
        if row is None:
            raise EvidenceError("Report does not exist")
        artifacts = cursor.execute(
            "SELECT * FROM platform.artifacts WHERE artifact_id=ANY(%s)",
            (
                [
                    row[k]
                    for k in [
                        "predictions_manifest_id",
                        "outcomes_manifest_id",
                        "report_artifact_id",
                    ]
                ],
            ),
        ).fetchall()
    objects = {a["artifact_id"]: json.loads(store.read(a)) for a in artifacts}
    prediction = objects[row["predictions_manifest_id"]]
    frozen = capture(
        conn,
        store,
        row["period_start"],
        row["period_end"],
        row["report_cutoff"],
        kind=row["report_kind"],
        policy=prediction["policy"],
        references={"predictions": prediction, "outcomes": objects[row["outcomes_manifest_id"]]},
    )
    if (
        frozen["predictions_manifest"] != prediction
        or frozen["outcomes_manifest"] != objects[row["outcomes_manifest_id"]]
        or frozen["report"] != objects[row["report_artifact_id"]]
    ):
        raise EvidenceError(
            "Report reproduction differs; preserve original and inspect code/input identity"
        )
    return {"report_id": str(report_id), "reproduced": True, "summary": frozen["report"]}


def main() -> int:
    import argparse

    from hoop.platform.artifacts import ArtifactError, Session, Settings
    from hoop.platform.database import DatabaseError, connection, health
    from hoop.platform.local_artifacts import atomic_json

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=["report", "reproduce"])
    parser.add_argument("--period", choices=["7d", "30d", "season"], default="7d")
    parser.add_argument("--kind", choices=["live", "rehearsal"], default="rehearsal")
    parser.add_argument("--cutoff", type=parse_time)
    parser.add_argument("--report", type=UUID)
    parser.add_argument("--persist", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        with connection() as conn:
            if health(conn)["role"] != "baseline_runtime":
                raise EvidenceError("Restricted report role required")
            store = PrivateArtifacts(Session(Settings.from_env()))
            if args.operation == "reproduce":
                if args.report is None:
                    raise EvidenceError("Saved report ID required")
                result = reproduce(conn, store, args.report)
            else:
                clock_row = conn.execute("SELECT clock_timestamp()").fetchone()
                assert clock_row is not None
                cutoff = args.cutoff or clock_row[0]
                policy = json.loads(POLICY.read_text())
                start, end = periods(cutoff, policy)[args.period]
                frozen = capture(conn, store, start, end, cutoff, kind=args.kind, policy=policy)
                result = persist(conn, store, frozen) if args.persist else frozen
        atomic_json(args.output / "evaluation.json", json.loads(encoded(result)))
        print(json.dumps(result, default=str, sort_keys=True))
        return 0
    except (
        EvidenceError,
        ArtifactError,
        DatabaseError,
        psycopg.Error,
        ValueError,
        KeyError,
        OSError,
    ):
        print(json.dumps({"state": "blocked", "reason_code": "evaluation_failed"}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
