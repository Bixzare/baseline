"""Routine fixture tests must fail if a network connection is attempted."""

import socket
from typing import Any

import pytest


@pytest.fixture(autouse=True)
def forbid_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def blocked(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("Fixture tests cannot open network connections")

    monkeypatch.setattr(socket.socket, "connect", blocked)
