"""NBA final parsing, immutable persistence and bounded reconciliation."""

from hoop.domains.nba.outcomes.operations import final_request, reconcile
from hoop.domains.nba.outcomes.parsing import PARSER, normalize_final, outcome_entries
from hoop.domains.nba.outcomes.persistence import ingest_final, pending_work

__all__ = [
    "PARSER",
    "normalize_final",
    "outcome_entries",
    "ingest_final",
    "pending_work",
    "final_request",
    "reconcile",
]
