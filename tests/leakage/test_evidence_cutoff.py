"""Observed collection and validation cannot be backdated by event/publication."""

from datetime import UTC, datetime

import pytest

from hoop.platform.evidence import known_by

CUTOFF = datetime(2020, 1, 2, 12, tzinfo=UTC)


@pytest.mark.parametrize(
    "changes,expected",
    [
        ({}, True),
        ({"received_at": "2020-01-02T12:00:01Z", "validated_at": "2020-01-02T12:00:02Z"}, False),
        ({"validated_at": "2020-01-02T12:00:01Z"}, False),
        (
            {
                "source_published_at": "2019-01-01T00:00:00Z",
                "received_at": "2020-01-03T00:00:00Z",
                "validated_at": "2020-01-03T00:00:01Z",
            },
            False,
        ),
        ({"source_published_at": None}, True),
        ({"received_at": None}, False),
        ({"validated_at": None}, False),
        ({"source_published_at": "2020-01-03T00:00:00Z"}, False),
        ({"state": "invalid"}, False),
    ],
)
def test_second_domain_cutoff(changes: dict[str, str | None], expected: bool) -> None:
    check = {
        "state": "accepted",
        "source_id": "synthetic-card-game",
        "requested_at": "2020-01-02T11:58:00Z",
        "received_at": "2020-01-02T11:59:00Z",
        "validated_at": CUTOFF.isoformat(),
        "source_published_at": None,
        **changes,
    }
    assert known_by(check, CUTOFF) == expected
