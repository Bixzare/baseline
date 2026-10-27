"""Durable denial stop for automatic work until later verified acceptance."""

from typing import Any
from urllib.parse import urlsplit

import psycopg

from hoop.domains.nba.sources.policy import ProbeRequest
from hoop.platform.evidence import EvidenceError


def refuse_denied(
    conn: psycopg.Connection[Any], requests: list[ProbeRequest], *, rehearsal: bool
) -> None:
    for host in sorted({str(urlsplit(r.url).hostname) for r in requests}):
        row = conn.execute(
            """SELECT max(s.recorded_at) FILTER(WHERE
             s.http_status IN(401,403) OR s.validation_summary->>'reason_code'='access_denied'),
             max(s.recorded_at) FILTER(WHERE s.state='accepted')
             FROM platform.source_checks s JOIN platform.runs r USING(run_id)
             WHERE s.source_id=%s AND r.environment=%s""",
            (host, "rehearsal" if rehearsal else "production"),
        ).fetchone()
        if row and row[0] and (row[1] is None or row[0] >= row[1]):
            raise EvidenceError(
                "Source stopped after denial; owner-reviewed re-verification required"
            )
