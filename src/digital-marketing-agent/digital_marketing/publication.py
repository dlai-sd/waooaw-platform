"""B2 publication intent, idempotency, reconciliation, and Stop semantics."""

# Implements: architecture/reference/components/dma-content-and-social-publication-solution-contract.md §8.1, §8.3, §8.4
# Constitutional basis: C-001, C-023, C-035, C-041, C-059, C-063, C-070, C-071, C-079

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum
from threading import Lock
from typing import Protocol

from mcp.common import SocialToolContext


class PublicationError(ValueError):
    """Closed publication denial."""


class PublicationState(StrEnum):
    REQUESTED = "REQUESTED"
    VALIDATING = "VALIDATING"
    BLOCKED = "BLOCKED"
    ACCEPTED = "ACCEPTED"
    DISPATCHING = "DISPATCHING"
    RECONCILING = "RECONCILING"
    PUBLISHED = "PUBLISHED"
    FAILED = "FAILED"
    OUTCOME_UNKNOWN = "OUTCOME_UNKNOWN"
    STOPPED = "STOPPED"
    CORRECTION_REQUIRED = "CORRECTION_REQUIRED"
    DELETE_PENDING = "DELETE_PENDING"
    DELETED = "DELETED"


@dataclass(frozen=True)
class PublicationPreconditions:
    b1_qualified: bool
    exact_draft_approved: bool
    rights_current: bool
    calendar_current: bool
    entitlement_current: bool
    decision_space_current: bool
    credential_valid: bool
    capability_fresh: bool
    ce_allowed: bool
    stop_active: bool

    @property
    def ready(self) -> bool:
        return all(
            (
                self.b1_qualified,
                self.exact_draft_approved,
                self.rights_current,
                self.calendar_current,
                self.entitlement_current,
                self.decision_space_current,
                self.credential_valid,
                self.capability_fresh,
                self.ce_allowed,
                not self.stop_active,
            )
        )


@dataclass(frozen=True)
class PublicationIntent:
    intent_id: str
    canonical_hash: str
    idempotency_key: str
    tenant_ref: str
    relationship_ref: str
    agent_instance_ref: str
    channel: str
    account_ref: str
    draft_ref: str
    draft_version: int
    draft_digest: str
    approval_ref: str
    credential_ref_version: str
    capability_profile_version: str
    state: PublicationState
    provider_correlation: str | None = None
    receipt_digest: str | None = None


class SocialPublisher(Protocol):
    def call(self, operation: str, context: SocialToolContext) -> dict[str, str]: ...


class PublicationCoordinator:
    def __init__(self, publisher: SocialPublisher, *, b2_enabled: bool = False) -> None:
        self._publisher = publisher
        self._b2_enabled = b2_enabled
        self._intents: dict[tuple[str, str], PublicationIntent] = {}
        self._lock = Lock()
        self._stopped_instances: set[str] = set()

    def reserve(self, intent: PublicationIntent, preconditions: PublicationPreconditions) -> PublicationIntent:
        if not self._b2_enabled:
            raise PublicationError("B2_LOCKED")
        identity = (intent.tenant_ref, intent.idempotency_key)
        with self._lock:
            existing = self._intents.get(identity)
            if existing is not None:
                if existing.canonical_hash != intent.canonical_hash:
                    raise PublicationError("IDEMPOTENCY_CONFLICT")
                return existing
            if intent.agent_instance_ref in self._stopped_instances or not preconditions.ready:
                blocked = replace(intent, state=PublicationState.BLOCKED)
                self._intents[identity] = blocked
                return blocked
            accepted = replace(intent, state=PublicationState.ACCEPTED)
            self._intents[identity] = accepted
            return accepted

    def dispatch(self, intent: PublicationIntent, context: SocialToolContext) -> PublicationIntent:
        identity = (intent.tenant_ref, intent.idempotency_key)
        with self._lock:
            durable = self._intents.get(identity)
            if durable is None or durable.state is not PublicationState.ACCEPTED:
                raise PublicationError("PUBLICATION_INTENT_NOT_DURABLE")
            if durable.agent_instance_ref in self._stopped_instances:
                stopped = replace(durable, state=PublicationState.STOPPED)
                self._intents[identity] = stopped
                return stopped
            self._intents[identity] = replace(durable, state=PublicationState.DISPATCHING)

        operation = f"{intent.channel.lower()}.post_content"
        try:
            result = self._publisher.call(operation, context)
        except TimeoutError:
            reconciled = replace(durable, state=PublicationState.RECONCILING)
        else:
            provider_state = result.get("state")
            if provider_state == "PUBLISHED" and result.get("receiptDigest") == intent.canonical_hash:
                reconciled = replace(
                    durable,
                    state=PublicationState.PUBLISHED,
                    provider_correlation=result.get("correlation"),
                    receipt_digest=result.get("receiptDigest"),
                )
            elif provider_state in {"ACCEPTED", "PROCESSING"}:
                reconciled = replace(
                    durable,
                    state=PublicationState.RECONCILING,
                    provider_correlation=result.get("correlation"),
                )
            else:
                reconciled = replace(durable, state=PublicationState.OUTCOME_UNKNOWN)
        with self._lock:
            if durable.agent_instance_ref in self._stopped_instances:
                reconciled = replace(reconciled, state=PublicationState.STOPPED)
            self._intents[identity] = reconciled
        return reconciled

    def stop(self, agent_instance_ref: str) -> None:
        with self._lock:
            self._stopped_instances.add(agent_instance_ref)

    def request_delete(self, intent: PublicationIntent, *, supported: bool, authorized: bool) -> PublicationIntent:
        if intent.state is not PublicationState.PUBLISHED:
            raise PublicationError("PUBLICATION_NOT_VERIFIED")
        if not supported:
            return replace(intent, state=PublicationState.CORRECTION_REQUIRED)
        if not authorized:
            raise PublicationError("DELETE_AUTHORITY_REQUIRED")
        return replace(intent, state=PublicationState.DELETE_PENDING)
