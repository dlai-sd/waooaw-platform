"""Uvicorn transport adapter for ADR-046 authenticated private listeners."""

# Implements: ADR-046 sections 3.1, 3.2, and 5.1
# constitutional_basis: C-026, C-059, C-063, C-083, C-084, C-085

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, MutableMapping
from typing import Any

from uvicorn.protocols.http.h11_impl import H11Protocol

from workload_identity import PEER_CERTIFICATE_STATE_KEY

AsgiReceive = Callable[[], Awaitable[MutableMapping[str, Any]]]
AsgiSend = Callable[[MutableMapping[str, Any]], Awaitable[None]]
AsgiApp = Callable[[MutableMapping[str, Any], AsgiReceive, AsgiSend], Awaitable[None]]


class MutualTlsH11Protocol(H11Protocol):
    """Expose only the certificate authenticated by the TLS transport."""

    def connection_made(self, transport: asyncio.Transport) -> None:
        ssl_object = transport.get_extra_info("ssl_object")
        peer_certificate = ssl_object.getpeercert(binary_form=True) if ssl_object is not None else None
        if not peer_certificate:
            transport.close()
            return

        application: AsgiApp = self.app

        async def authenticated_application(
            scope: MutableMapping[str, Any],
            receive: AsgiReceive,
            send: AsgiSend,
        ) -> None:
            state = scope.setdefault("state", {})
            state[PEER_CERTIFICATE_STATE_KEY] = peer_certificate
            await application(scope, receive, send)

        self.app = authenticated_application
        super().connection_made(transport)