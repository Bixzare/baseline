"""Domain-neutral numeric errors and separate opportunity/diagnostic coverage."""

import math
from collections import Counter
from typing import Any

from hoop.platform.evidence import EvidenceError


def evaluate(events: list[dict[str, Any]], targets: dict[str, str]) -> dict[str, Any]:
    totals: dict[str, dict[str, Any]] = {
        t: {
            "errors": [],
            "played_errors": [],
            "games": set(),
            "numeric": 0,
            "abstained": 0,
            "unresolved": 0,
            "dnp": 0,
        }
        for t in targets
    }
    categories: Counter[str] = Counter()
    decision_counts: Counter[str] = Counter()
    groups: dict[tuple[str, str], list[float]] = {}
    expected = covered = known_opportunities = unknown_rosters = unknown_schedule = 0
    participant_count = participant_numeric = 0
    examples: list[dict[str, Any]] = []
    event_ids = set()
    for event in events:
        identity = event["event_id"]
        if identity in event_ids:
            raise EvidenceError("Duplicate evaluation occurrence")
        event_ids.add(identity)
        state = event["state"]
        categories[state] += 1
        decision_counts[state] += len(event["decisions"])
        if state == "unknown_schedule":
            unknown_schedule += 1
            continue
        if state in {"excluded", "pending_occurrence"}:
            continue
        expected += 1
        diagnostics = event.get("participants", [])
        participant_count += len(diagnostics) * len(targets)
        if event["cohort"] is None:
            unknown_rosters += 1
            continue
        cohort = event["cohort"]
        subjects = [(m["subject_type"], m["subject_id"]) for m in cohort]
        if not subjects or len(set(subjects)) != len(subjects):
            raise EvidenceError("A known evaluation cohort must have unique subjects")
        known_opportunities += len(subjects) * len(targets)
        decisions = {}
        for d in event["decisions"]:
            key = (d["subject_type"], d["subject_id"], d["target"])
            if key in decisions:
                raise EvidenceError("Duplicate evaluated decision")
            decisions[key] = d
        complete = set(decisions) == {(*subject, t) for subject in subjects for t in targets}
        valid = state == "timely_confirmed" and complete
        if valid:
            covered += 1
        actuals = {}
        for a in event["actuals"]:
            key = (a["subject_type"], a["subject_id"], a["target"])
            if key in actuals:
                raise EvidenceError("Duplicate evaluated actual")
            actuals[key] = a
        if valid:
            participant_numeric += sum(
                decisions.get((p["subject_type"], p["subject_id"], t), {}).get("value") is not None
                for p in diagnostics
                for t in targets
            )
        if not valid:
            continue
        for key, d in decisions.items():
            target = key[-1]
            if d["unit"] != targets[target]:
                raise EvidenceError("Prediction unit mismatch")
            if d["value"] is None:
                totals[target]["abstained"] += 1
                continue
            value = d["value"]
            if type(value) not in {int, float} or not math.isfinite(value):
                raise EvidenceError("Nonfinite prediction")
            totals[target]["numeric"] += 1
            a = actuals.get(key)
            if a is None or a.get("value") is None:
                totals[target]["unresolved"] += 1
                continue
            if (
                a["unit"] != targets[target]
                or type(a["value"]) not in {int, float}
                or not math.isfinite(a["value"])
            ):
                raise EvidenceError("Invalid actual or unit")
            if a.get("participation") == "unknown":
                totals[target]["unresolved"] += 1
                continue
            error = value - a["value"]
            absolute = abs(error)
            totals[target]["errors"].append(absolute)
            totals[target]["games"].add(identity)
            if a.get("participation") == "played":
                totals[target]["played_errors"].append(absolute)
            if a.get("participation") == "did_not_play":
                totals[target]["dnp"] += 1
            for label in a.get("diagnostic_groups", []):
                groups.setdefault((target, label), []).append(absolute)
            if len(examples) < 5:
                examples.append(
                    {
                        "event_id": identity,
                        "subject_id": key[1],
                        "target": target,
                        "prediction": value,
                        "actual": a["value"],
                        "signed_error": error,
                        "absolute_error": absolute,
                        "unit": targets[target],
                    }
                )
    metrics: dict[str, dict[str, Any]] = {}
    for target, result in totals.items():
        errors = result.pop("errors")
        played = result.pop("played_errors")
        games = result.pop("games")
        metrics[target] = {
            **result,
            "unit": targets[target],
            "scored": len(errors),
            "distinct_games": len(games),
            "mae": math.fsum(errors) / len(errors) if errors else None,
            "played_only_mae": math.fsum(played) / len(played) if played else None,
            "played_scored": len(played),
            "unavailable_reason": None if errors else "no_scored_observations",
        }
    numeric = sum(x["numeric"] for x in metrics.values())
    return {
        "metrics": metrics,
        "categories": dict(sorted(categories.items())),
        "decision_counts_by_state": dict(sorted(decision_counts.items())),
        "coverage": {
            "expected_games": expected,
            "covered_games": covered,
            "unknown_schedule_games": unknown_schedule,
            "unknown_roster_games": unknown_rosters,
            "schedule_coverage": covered / expected if expected and not unknown_schedule else None,
            "known_opportunities": known_opportunities,
            "expected_opportunities": None
            if unknown_rosters or unknown_schedule
            else known_opportunities,
            "numeric_predictions": numeric,
            "numeric_coverage": numeric / known_opportunities
            if known_opportunities and not unknown_rosters and not unknown_schedule
            else None,
        },
        "retrospective_participant_coverage": {
            "opportunities": participant_count,
            "numeric_predictions": participant_numeric,
            "rate": participant_numeric / participant_count if participant_count else None,
            "label": "actual participants, diagnostic only",
        },
        "diagnostic_groups": [
            {
                "target": key[0],
                "group": key[1],
                "count": len(values),
                "mae": math.fsum(values) / len(values),
            }
            for key, values in sorted(groups.items())
        ],
        "comparison": {"available": False, "reason": "no_challenger"},
        "examples": examples,
    }
