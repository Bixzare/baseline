"""Read immutable component identities through the current active pointer."""

from typing import Any

import psycopg
from psycopg.rows import dict_row

from hoop.platform.evidence import EvidenceError


def active_bundle(conn: psycopg.Connection[Any], domain: str, family: str) -> dict[str, Any] | None:
    with conn.cursor(row_factory=dict_row) as cursor:
        pointer = cursor.execute(
            """SELECT a.domain,a.family,a.bundle_id,a.generation,
             b.components,b.config_hash FROM platform.active_bundles a
             JOIN platform.model_bundles b USING(bundle_id) WHERE a.domain=%s AND a.family=%s""",
            (domain, family),
        ).fetchone()
        if pointer is None:
            return None
        ids = list(pointer["components"].values())
        if len(ids) > 1000:
            raise EvidenceError("Model bundle exceeds bounded read")
        pointer["models"] = cursor.execute(
            "SELECT * FROM platform.models WHERE model_id=ANY(%s::uuid[])", (ids,)
        ).fetchall()
        if len(pointer["models"]) != len(ids):
            raise EvidenceError("Incomplete model bundle identity")
        return pointer
