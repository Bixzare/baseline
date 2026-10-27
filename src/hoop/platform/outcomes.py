"""Generic immutable outcome entry validation, independent of sports columns."""

import math
from typing import Any

from hoop.platform.evidence import EvidenceError


def validate_outcomes(entries: list[dict[str, Any]]) -> str:
    seen = set()
    resolved = 0
    for entry in entries:
        key = tuple(entry.get(k) for k in ["subject_type", "subject_id", "target"])
        if not all(isinstance(x, str) and x for x in key) or key in seen or not entry.get("unit"):
            raise EvidenceError("Invalid or duplicate outcome identity")
        seen.add(key)
        value = entry.get("value")
        if value is None:
            if not entry.get("reason_code"):
                raise EvidenceError("Unknown outcome needs a reason")
        else:
            if (
                type(value) not in {float, int}
                or not math.isfinite(value)
                or entry.get("reason_code")
            ):
                raise EvidenceError("Outcome values must be finite and unambiguous")
            resolved += 1
    return "pending" if resolved == 0 else "final" if resolved == len(entries) else "partial"
