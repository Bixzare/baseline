"""Hand-computable outcomes in two different units; no live NBA evidence."""

from typing import Any

TARGETS = {"minutes": "minutes", "points": "points"}


def numeric_event() -> dict[str, Any]:
    values = {
        "1": {"minutes": (20, 10), "points": (12, 15)},
        "2": {"minutes": (10, 0), "points": (5, 0)},
        "3": {"minutes": (7, None), "points": (None, None)},
    }
    decisions = []
    actuals = []
    for subject, targets in values.items():
        for target, (predicted, actual) in targets.items():
            decisions.append(
                {
                    "subject_type": "player",
                    "subject_id": subject,
                    "target": target,
                    "unit": TARGETS[target],
                    "value": predicted,
                    "reason_code": "no_history" if predicted is None else None,
                }
            )
            actuals.append(
                {
                    "subject_type": "player",
                    "subject_id": subject,
                    "target": target,
                    "unit": TARGETS[target],
                    "value": actual,
                    "participation": "did_not_play"
                    if subject == "2"
                    else "played"
                    if subject == "1"
                    else "unknown",
                    "diagnostic_groups": ["team:fixture"],
                }
            )
    return {
        "event_id": "fixture1",
        "state": "timely_confirmed",
        "cohort": [{"subject_type": "player", "subject_id": s} for s in values],
        "decisions": decisions,
        "actuals": actuals,
        "participants": [{"subject_type": "player", "subject_id": s} for s in ["1", "4"]],
    }
