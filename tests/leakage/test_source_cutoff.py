"""Late collection/validation and final participants cannot backdate evidence."""

from datetime import UTC, datetime

import pytest

from hoop.platform.provenance import known_by


def manifest() -> dict[str, str]:
    return {
        "outcome": "verified_sample",
        "capability": "roster",
        "source_publication_time": "2026-10-14T10:00:00Z",
        "received_at": "2026-10-14T11:00:00Z",
        "validated_at": "2026-10-14T11:01:00Z",
    }


def test_late_corrected_collection_is_not_known_before_cutoff() -> None:
    cutoff = datetime(2026, 10, 14, 12, tzinfo=UTC)
    original = manifest()
    corrected = {
        **original,
        "received_at": "2026-10-14T13:00:00Z",
        "validated_at": "2026-10-14T13:01:00Z",
    }
    assert known_by(original, cutoff)
    assert not known_by(corrected, cutoff)
    assert known_by(original, cutoff)  # A later version cannot alter the earlier observation.


def test_validation_after_cutoff_or_reversed_times_is_not_eligible() -> None:
    cutoff = datetime(2026, 10, 14, 12, tzinfo=UTC)
    assert not known_by({**manifest(), "validated_at": "2026-10-14T12:01:00Z"}, cutoff)
    assert not known_by({**manifest(), "received_at": "2026-10-14T11:02:00Z"}, cutoff)


def test_final_boxscore_cannot_establish_prior_roster() -> None:
    cutoff = datetime(2026, 10, 14, 12, tzinfo=UTC)
    assert not known_by({**manifest(), "capability": "final"}, cutoff, purpose="roster")
    assert known_by(manifest(), cutoff, purpose="roster")


def test_failure_or_missing_collection_is_not_a_known_input() -> None:
    cutoff = datetime(2026, 10, 14, 12, tzinfo=UTC)
    assert not known_by({**manifest(), "outcome": "failed"}, cutoff)
    assert not known_by({**manifest(), "received_at": None}, cutoff)


def test_naive_cutoff_is_rejected() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        known_by(manifest(), datetime(2026, 10, 14, 12))
