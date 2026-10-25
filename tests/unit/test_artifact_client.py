"""Bounded authentication, immutable uploads, and safe reporting."""

from dataclasses import replace

import pytest

from hoop.platform.artifacts import ArtifactError, PrivateArtifacts, Session
from tests.fixtures.storage_client import SETTINGS, MemoryStorage, other_settings


def test_upload_read_and_existing_key_reuse() -> None:
    transport = MemoryStorage()
    store = PrivateArtifacts(Session(SETTINGS, transport))
    first = store.put(b"hello", kind="raw", format="json")
    assert first == store.put(b"hello", kind="raw", format="json")
    assert first["byte_count"] == 5
    assert first["sha256"] == "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"
    assert sum(method == "POST" and "object" in path for method, path in transport.calls) == 1


def test_lost_upload_response_recovers_only_by_verified_read() -> None:
    transport = MemoryStorage()
    transport.lost_upload = True
    assert (
        PrivateArtifacts(Session(SETTINGS, transport)).put(b"hello", kind="reports", format="txt")[
            "byte_count"
        ]
        == 5
    )
    assert len(transport.objects) == 1


@pytest.mark.parametrize("failure", ["corrupt", "forbidden", "missing_after_failed_upload"])
def test_bad_storage_never_returns_usable_descriptor(failure: str) -> None:
    transport = MemoryStorage()
    transport.corrupt = failure == "corrupt"
    transport.upload_status = (
        403
        if failure == "forbidden"
        else (500 if failure == "missing_after_failed_upload" else 200)
    )
    with pytest.raises(ArtifactError):
        PrivateArtifacts(Session(SETTINGS, transport)).put(b"hello", kind="raw", format="json")


def test_expiry_and_401_renew_only_own_memory_session() -> None:
    transport = MemoryStorage()
    first, second = Session(SETTINGS, transport), Session(other_settings(), transport)
    first.authenticate()
    second.authenticate()
    second_token = second.refresh
    first.expires_at = 0
    first.request("GET", "/storage/v1/object/authenticated/bucket/key")
    assert second.refresh == second_token
    assert first.refresh != second.refresh
    transport.force_401 = True
    first.request("GET", "/storage/v1/object/authenticated/bucket/key")
    assert transport.auth_count == 4
    assert not any("logout" in path for _, path in transport.calls)


def test_refused_renewal_does_not_fallback_or_disclose_server_message() -> None:
    transport = MemoryStorage()
    session = Session(SETTINGS, transport)
    session.authenticate()
    session.expires_at = 0
    transport.renewal_refused = True
    with pytest.raises(ArtifactError, match="session_renewal_refused") as error:
        session.request("GET", "/storage/v1/object/authenticated/bucket/key")
    assert "not_real" not in str(error.value)
    assert transport.auth_count == 1


@pytest.mark.parametrize(
    "statuses,works", [([429, 200], True), ([429, 429], False), ([400], False), ([500, 500], False)]
)
def test_authentication_attempts_are_bounded(statuses: list[int], works: bool) -> None:
    transport = MemoryStorage()
    transport.auth_statuses = statuses
    session = Session(SETTINGS, transport)
    if works:
        session.authenticate()
    else:
        with pytest.raises(ArtifactError):
            session.authenticate()
    assert len(transport.calls) <= 2


@pytest.mark.parametrize(
    "change",
    [
        {"url": "https://attacker.test"},
        {"bucket": "../escape"},
        {"key": "sb_secret_no"},
        {"user_id": "invalid"},
    ],
)
def test_unsafe_configuration_is_rejected(change: dict[str, str]) -> None:
    with pytest.raises(ArtifactError):
        replace(SETTINGS, **change)


def test_bad_descriptor_does_not_contact_storage() -> None:
    transport = MemoryStorage()
    with pytest.raises(ArtifactError):
        PrivateArtifacts(Session(SETTINGS, transport)).put(b"hi", kind="../raw", format="json")
    assert not transport.calls
