"""Verify NBA prepared artifacts, then invoke the shared commit protocol."""

import json
from typing import Any
from uuid import UUID

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from hoop.platform.artifacts import PrivateArtifacts
from hoop.platform.evidence import EvidenceError
from hoop.platform.ledger.publication import commit_and_confirm, idle


def publish_player(
    conn: psycopg.Connection[Any],
    store: PrivateArtifacts,
    retained: dict[str, Any],
    bundle_id: UUID,
    *,
    fault: Any = lambda stage: None,
) -> dict[str, Any]:
    idle(conn)
    objects = retained["objects"]
    # Original bodies are downloaded and checked before transaction one.
    bodies = {name: store.read(objects[name]) for name in ["prepared", "features", "cohort"]}
    prepared = json.loads(bodies["prepared"])
    roster_bodies = []
    for roster in prepared["roster_sources"]:
        with conn.cursor(row_factory=dict_row) as cursor:
            artifact = cursor.execute(
                "SELECT a.* FROM nba.roster_snapshots r JOIN platform.artifacts a "
                "ON a.artifact_id=r.members_artifact_id WHERE r.roster_id=%s",
                (roster["roster_id"],),
            ).fetchone()
        if artifact is None:
            raise EvidenceError("Saved roster artifact missing")
        roster_bodies.append(
            {"roster_id": roster["roster_id"], "body": store.read(artifact).decode()}
        )

    def insert() -> UUID:
        row = conn.execute(
            "SELECT nba.publish_player(%s,%s,%s,%s,%s,%s,%s,%s)",
            (
                objects["prepared"]["artifact_id"],
                bodies["prepared"],
                objects["features"]["artifact_id"],
                bodies["features"],
                objects["cohort"]["artifact_id"],
                bodies["cohort"],
                Jsonb(roster_bodies),
                bundle_id,
            ),
        ).fetchone()
        assert row is not None
        return UUID(str(row[0]))

    return commit_and_confirm(conn, insert, prepared["run_id"], fault=fault)


def main() -> int:
    import argparse
    from pathlib import Path

    from hoop.platform.artifacts import ArtifactError, Session, Settings
    from hoop.platform.database import DatabaseError, connection, health

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--retained", type=Path, required=True)
    parser.add_argument("--bundle", type=UUID, required=True)
    parser.add_argument("--confirm-hosted-gates", action="store_true")
    args = parser.parse_args()
    try:
        if not args.confirm_hosted_gates:
            raise EvidenceError("Reviewed readiness gates required")
        with connection() as conn:
            if health(conn)["role"] != "baseline_runtime":
                raise EvidenceError("Restricted runtime required")
            result = publish_player(
                conn,
                PrivateArtifacts(Session(Settings.from_env())),
                json.loads(args.retained.read_text()),
                args.bundle,
            )
        print(json.dumps(result, default=str, sort_keys=True))
        return 0 if result["state"] == "timely_confirmed" else 1
    except (EvidenceError, ArtifactError, DatabaseError, ValueError, KeyError, OSError):
        print(json.dumps({"status": "blocked", "reason_code": "publication_failed"}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
