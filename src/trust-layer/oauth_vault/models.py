# Implements: adr/ADR-021-external-platform-oauth-token-management.md §2 Token data model
# constitutional_basis: ADR-014 (secret management — token value never logged), ADR-021

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field


class StoreTokenRequest(BaseModel):
    """Body for POST /tokens/{contract_id}/{provider_name}."""

    access_token: str
    refresh_token: str | None = None
    expires_at: datetime | None = None  # None = no expiry (API_KEY providers)
    extra_data: dict = Field(default_factory=dict)


class TokenData(BaseModel):
    """Internal token representation. Never serialised to caller responses."""

    access_token: str
    refresh_token: str | None = None
    expires_at: datetime | None = None
    provider_name: str
    contract_id: str
    extra_data: dict = Field(default_factory=dict)

    def health_status(self) -> str:
        """Compute token health without logging token value."""
        if self.expires_at is None:
            return "VALID"  # API_KEY: no expiry
        now = datetime.now(tz=timezone.utc)
        remaining = (self.expires_at - now).total_seconds()
        if remaining <= 0:
            return "EXPIRED"
        if remaining <= 7200:  # 2 hours
            return "EXPIRING_SOON"
        return "VALID"


class TokenHealthResponse(BaseModel):
    status: str  # VALID | EXPIRING_SOON | EXPIRED | NOT_CONNECTED
    provider_name: str
    contract_id: str
    expires_at: datetime | None = None
