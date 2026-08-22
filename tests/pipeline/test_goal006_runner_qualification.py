"""Contracts for private runner Storage and Terraform qualification."""

from __future__ import annotations

import socket

import pytest

from scripts.goal006_runner_qualification import QualificationError, resolve_private_addresses


def test_private_dns_accepts_only_private_addresses(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *args, **kwargs: [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.70.0.36", 443))
        ],
    )
    assert resolve_private_addresses("state.blob.core.windows.net") == ["10.70.0.36"]


@pytest.mark.parametrize("address", ["20.60.1.2", "8.8.8.8"])
def test_public_dns_answer_fails_closed(
    monkeypatch: pytest.MonkeyPatch, address: str
) -> None:
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *args, **kwargs: [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", (address, 443))
        ],
    )
    with pytest.raises(QualificationError, match="public or empty"):
        resolve_private_addresses("state.blob.core.windows.net")


def test_dns_failure_is_not_inferred_as_isolation(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(*args, **kwargs):
        raise socket.gaierror("NXDOMAIN")

    monkeypatch.setattr(socket, "getaddrinfo", fail)
    with pytest.raises(QualificationError, match="resolution failed"):
        resolve_private_addresses("state.blob.core.windows.net")