# Implements: ADR-046 sections 3.1, 3.2, 5.1, and 10.1
# constitutional_basis: C-026, C-059, C-063, C-076, C-083, C-084, C-085

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from mtls_protocol import MutualTlsH11Protocol
from workload_identity import PEER_CERTIFICATE_STATE_KEY


def _protocol(application):
    protocol = object.__new__(MutualTlsH11Protocol)
    protocol.app = application
    protocol.connections = set()
    protocol.logger = Mock(level=100)
    return protocol


@pytest.mark.asyncio
async def test_tls_peer_certificate_is_injected_from_transport(monkeypatch) -> None:
    observed_scope = None

    async def application(scope, receive, send) -> None:
        nonlocal observed_scope
        observed_scope = scope

    peer_certificate = b"authenticated-der"
    ssl_object = Mock()
    ssl_object.getpeercert.return_value = peer_certificate
    transport = Mock()
    transport.get_extra_info.side_effect = lambda name: ssl_object if name == "ssl_object" else None
    protocol = _protocol(application)
    monkeypatch.setattr(
        "mtls_protocol.H11Protocol.connection_made",
        lambda self, authenticated_transport: None,
    )

    protocol.connection_made(transport)
    await protocol.app({"type": "http", "state": {}}, Mock(), Mock())

    assert observed_scope["state"][PEER_CERTIFICATE_STATE_KEY] == peer_certificate
    transport.close.assert_not_called()


@pytest.mark.parametrize("ssl_object", [None, SimpleNamespace(getpeercert=lambda binary_form: None)])
def test_plaintext_or_missing_peer_certificate_is_rejected(monkeypatch, ssl_object) -> None:
    transport = Mock()
    transport.get_extra_info.side_effect = lambda name: ssl_object if name == "ssl_object" else None
    protocol = _protocol(Mock())
    parent_connection = Mock()
    monkeypatch.setattr("mtls_protocol.H11Protocol.connection_made", parent_connection)

    protocol.connection_made(transport)

    transport.close.assert_called_once_with()
    parent_connection.assert_not_called()
