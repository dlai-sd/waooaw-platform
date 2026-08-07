# Implements: adr/ADR-042-provider-registry-constitutional-tool-gateway.md §4
# constitutional_basis: ADR-014 (no secrets in logs), OWASP A02 (credential exposure)
from __future__ import annotations

import logging

import httpx

from .models import MCPToolError

logger = logging.getLogger(__name__)


class ExceptionTranslator:
    """
    Maps raw exceptions from external provider calls to sanitized MCPToolError.

    ADR-042 §4: the full exception (including any token fragments in stack traces)
    is written to a secured internal log channel — NEVER returned to caller.
    Token structural prevention: the token is a local variable in gateway.py and
    is never passed into this method, so it cannot appear in MCPToolError.message.
    """

    def translate(self, raw_exc: BaseException, provider_name: str) -> MCPToolError:
        # Full exception to secured internal log — exc_info includes stack trace
        logger.warning(
            "CTG provider call failed provider=%s exc_type=%s",
            provider_name,
            type(raw_exc).__name__,
            exc_info=True,
            extra={"secure": True},
        )

        if isinstance(raw_exc, httpx.TimeoutException):
            return MCPToolError(
                code="TIMEOUT",
                message="Provider request timed out",
                retry_eligible=True,
            )
        if isinstance(raw_exc, httpx.HTTPStatusError):
            status = raw_exc.response.status_code
            if status in (401, 403):
                return MCPToolError(
                    code="TOKEN_DEGRADED",
                    message="Provider authentication failed",
                    retry_eligible=True,
                )
            return MCPToolError(
                code="PROVIDER_ERROR",
                message=f"Provider returned HTTP {status}",
                retry_eligible=status >= 500,
            )
        if isinstance(raw_exc, httpx.RequestError):
            return MCPToolError(
                code="PROVIDER_ERROR",
                message="Provider connection failed",
                retry_eligible=True,
            )
        return MCPToolError(
            code="PROVIDER_ERROR",
            message="Provider call failed",
            retry_eligible=False,
        )
