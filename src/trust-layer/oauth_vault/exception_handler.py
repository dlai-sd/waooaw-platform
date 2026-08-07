# Implements: work-contracts/WC-038-trust-layer-s2-provider-registry-oauth-vault.md §WC038-06
# constitutional_basis: OWASP A02 (no secrets in logs), ADR-014 (secret management)

from __future__ import annotations

import logging
from collections.abc import Callable

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

_SANITIZED_ERROR = {"error": "VAULT_ERROR", "code": "TOKEN_UNAVAILABLE"}


class _SecureExceptionMiddleware(BaseHTTPMiddleware):
    """
    Catches ALL unhandled exceptions at the ASGI boundary.
    Raw exceptions (including any token fragments in stack traces) written to WARN log only.
    Callers receive sanitized JSON — no stack trace, no token fragment, no AKV path.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> JSONResponse:
        try:
            return await call_next(request)
        except Exception as exc:
            # HTTPException carries its own status code and safe message — let it through.
            if isinstance(exc, HTTPException):
                raise
            # ADR-014: exception type + path logged. No stack trace. No token value.
            logger.warning(
                "oauth-vault unhandled exception type=%s path=%s",
                type(exc).__name__,
                request.url.path,
            )
            return JSONResponse(status_code=500, content=_SANITIZED_ERROR)


def install_exception_handler(app: FastAPI) -> None:
    app.add_middleware(_SecureExceptionMiddleware)
