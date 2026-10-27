from datetime import UTC, datetime, timedelta

import pytest

from hoop.platform.ledger.publication import before_deadline


def test_exact_cutoff_equality_is_closed() -> None:
    start = datetime(2026, 11, 1, 19, tzinfo=UTC)
    cutoff = start - timedelta(minutes=15)
    assert before_deadline(cutoff - timedelta(microseconds=1), start)
    assert not before_deadline(cutoff, start)
    assert not before_deadline(cutoff + timedelta(microseconds=1), start)
    with pytest.raises(ValueError):
        before_deadline(cutoff.replace(tzinfo=None), start)
