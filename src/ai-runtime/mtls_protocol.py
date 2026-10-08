"""Expose the authenticated peer certificate to AIR's ASGI scope."""

from __future__ import annotations

import ssl
from collections.abc import Awaitable, Callable, MutableMapping
from typing import Any

from uvicorn.protocols.http.h11_impl import H11Protocol

from employment_auth import PEER_CERTIFICATE_STATE_KEY

AsgiScope = MutableMapping[str, Any]
AsgiReceive = Callable[[], Awaitable[MutableMapping[str, Any]]]
AsgiSend = Callable[[MutableMapping[str, Any]], Awaitable[None]]


class MutualTlsH11Protocol(H11Protocol):
    def connection_made(self, transport: Any) -> None:
        ssl_object: ssl.SSLObject | None = transport.get_extra_info("ssl_object")
        peer_certificate = ssl_object.getpeercert(binary_form=True) if ssl_object else None
        if peer_certificate is None:
            transport.close()
            return
        application = self.app

        async def authenticated_application(
            scope: AsgiScope,
            receive: AsgiReceive,
            send: AsgiSend,
        ) -> None:
            scope.setdefault("state", {})[PEER_CERTIFICATE_STATE_KEY] = peer_certificate
            await application(scope, receive, send)

        self.app = authenticated_application
        super().connection_made(transport)
