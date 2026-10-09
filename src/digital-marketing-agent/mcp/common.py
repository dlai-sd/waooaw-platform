"""Closed provider-neutral social MCP contracts and deterministic emulator."""

# Implements: architecture/reference/components/dma-content-and-social-publication-solution-contract.md §6, §8.2.1
# Constitutional basis: C-023, C-041, C-059, C-063, C-070, C-078, ADR-020, ADR-021

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
from typing import Protocol
from urllib.parse import urlparse


class SocialToolError(StrEnum):
    INVALID_REQUEST = "INVALID_REQUEST"
    NOT_ACCESSIBLE = "NOT_ACCESSIBLE"
    AUTHORITY_DENIED = "AUTHORITY_DENIED"
    ASSURANCE_REQUIRED = "ASSURANCE_REQUIRED"
    VERSION_CONFLICT = "VERSION_CONFLICT"
    IDEMPOTENCY_CONFLICT = "IDEMPOTENCY_CONFLICT"
    NOT_CONFIGURED = "NOT_CONFIGURED"
    CREDENTIAL_EXPIRED = "CREDENTIAL_EXPIRED"
    SCOPE_INSUFFICIENT = "SCOPE_INSUFFICIENT"
    ACCOUNT_UNSUPPORTED = "ACCOUNT_UNSUPPORTED"
    CAPABILITY_STALE = "CAPABILITY_STALE"
    RATE_LIMITED = "RATE_LIMITED"
    PROVIDER_UNAVAILABLE = "PROVIDER_UNAVAILABLE"
    OUTCOME_UNKNOWN = "OUTCOME_UNKNOWN"
    STOPPED = "STOPPED"


class SocialToolDenied(ValueError):
    def __init__(self, reason: SocialToolError) -> None:
        super().__init__(reason.value)
        self.reason = reason


@dataclass(frozen=True)
class SocialToolContext:
    operation_id: str
    intent_id: str
    idempotency_key: str
    canonical_request_digest: str
    tenant_authority_ref: str
    relationship_ref: str
    agent_instance_ref: str
    channel: str
    channel_account_ref: str
    credential_ref_version: str
    decision_space_version: str
    ce_evidence_ref: str
    wbe_eligibility_version: str
    capability_profile_version: str
    requested_at: datetime
    deadline_at: datetime
    trace_id: str


@dataclass(frozen=True)
class CredentialHealth:
    state: str
    credential_ref: str
    token_version: str
    scopes: frozenset[str]
    account_ref: str
    expires_at: datetime


class PurposeBoundTokenBroker(Protocol):
    def health(
        self,
        *,
        tenant_ref: str,
        relationship_ref: str,
        account_ref: str,
        purpose: str,
    ) -> CredentialHealth: ...

    def consume(
        self,
        *,
        tenant_ref: str,
        relationship_ref: str,
        account_ref: str,
        purpose: str,
        operation_id: str,
    ) -> str: ...


class CeValidator(Protocol):
    def validate(self, action: str, context: SocialToolContext) -> None: ...


def require_configured_reference(value: str, *, oauth: bool = False) -> str:
    normalized = value.strip()
    lowered = normalized.lower()
    invalid_markers = ("changeme", "placeholder", "fixture")
    expected_scheme = "oauthref" if oauth else "secretref"
    if (
        not normalized
        or any(marker in lowered for marker in invalid_markers)
        or ".invalid" in lowered
        or lowered.startswith(f"{expected_scheme}://") and "{" in normalized
        or lowered.startswith("unresolved:")
    ):
        raise SocialToolDenied(SocialToolError.NOT_CONFIGURED)
    parsed = urlparse(normalized)
    if parsed.scheme == expected_scheme and not parsed.netloc:
        raise SocialToolDenied(SocialToolError.NOT_CONFIGURED)
    return normalized


def require_ready_credential(
    broker: PurposeBoundTokenBroker,
    context: SocialToolContext,
    *,
    purpose: str,
    required_scopes: frozenset[str],
    now: datetime | None = None,
) -> CredentialHealth:
    require_configured_reference(context.credential_ref_version, oauth=True)
    health = broker.health(
        tenant_ref=context.tenant_authority_ref,
        relationship_ref=context.relationship_ref,
        account_ref=context.channel_account_ref,
        purpose=purpose,
    )
    current = now or datetime.now(timezone.utc)
    if health.state != "VALID" or health.expires_at <= current:
        raise SocialToolDenied(SocialToolError.CREDENTIAL_EXPIRED)
    if health.account_ref != context.channel_account_ref:
        raise SocialToolDenied(SocialToolError.NOT_ACCESSIBLE)
    if not required_scopes <= health.scopes:
        raise SocialToolDenied(SocialToolError.SCOPE_INSUFFICIENT)
    return health


class DeterministicTokenBroker:
    def __init__(self, health: CredentialHealth) -> None:
        self._health = health
        self.consumed_purposes: list[str] = []

    def health(
        self,
        *,
        tenant_ref: str,
        relationship_ref: str,
        account_ref: str,
        purpose: str,
    ) -> CredentialHealth:
        del tenant_ref, relationship_ref, account_ref, purpose
        return self._health

    def consume(
        self,
        *,
        tenant_ref: str,
        relationship_ref: str,
        account_ref: str,
        purpose: str,
        operation_id: str,
    ) -> str:
        del tenant_ref, relationship_ref, account_ref, operation_id
        self.consumed_purposes.append(purpose)
        return "opaque-emulator-token"
