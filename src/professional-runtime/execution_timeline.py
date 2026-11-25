"""PR-owned execution stream for real agent work: six states, artifact binding, stop fence, unknown outcomes."""

# Implements: architecture/reference/product/ae02-real-work-solution-contract.md DC-2 Execution binding, DC-4 Execution status and action timeline
# Constitutional basis: C-001, C-005, C-023, C-049, C-059, C-063
# IB: IB-170

from __future__ import annotations

import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any, Protocol
from uuid import UUID, uuid4

EXECUTE_STEP_ACTION = "REAL_WORK_EXECUTE_STEP"
STOP_WORK_ITEM_TYPE = "EMERGENCY_STOP"
_SECRET = re.compile(r"(?i)(bearer\s|access[_-]?token|secret|password|api[_-]?key|EAA[A-Za-z0-9]{20,})")


class WorkItemState(StrEnum):
    PROPOSED = "PROPOSED"
    APPROVED = "APPROVED"
    EXECUTING = "EXECUTING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    HALTED = "HALTED"


class ReasonCode(StrEnum):
    EMERGENCY_STOP = "EMERGENCY_STOP"
    PROVIDER_REJECTED = "PROVIDER_REJECTED"
    UNKNOWN_OUTCOME = "UNKNOWN_OUTCOME"
    RECONCILED = "RECONCILED"
    AWAITING_PROVIDER_PROOF = "AWAITING_PROVIDER_PROOF"
    POLICY_BLOCKED = "POLICY_BLOCKED"
    TIMED_OUT = "TIMED_OUT"


class ProviderStatus(StrEnum):
    CONFIRMED = "CONFIRMED"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"


class BlindRetryRefused(Exception):  # noqa: N818 - named for the refusal it records
    """A work item whose outcome is unknown is reconciled first; it is never dispatched again blindly."""


class ArtifactBindingRefused(Exception):  # noqa: N818 - named for the refusal it records
    """The step is not bound to one locked, approved and scope-confirmed artifact version."""


@dataclass(frozen=True)
class ArtifactBinding:
    artifact_id: UUID
    artifact_digest: str
    artifact_status: str
    approval_evidence_id: UUID
    scope_evidence_id: UUID

    def as_action_parameters(self, relationship_id: UUID) -> dict[str, str]:
        return {
            "relationshipId": str(relationship_id),
            "artifactId": str(self.artifact_id),
            "artifactDigest": self.artifact_digest,
            "artifactStatus": self.artifact_status,
            "approvalEvidenceId": str(self.approval_evidence_id),
            "scopeEvidenceId": str(self.scope_evidence_id),
        }


@dataclass(frozen=True)
class WorkItem:
    tenant_id: UUID
    relationship_id: UUID
    work_item_id: UUID
    work_item_type: str
    binding: ArtifactBinding | None = None
    produces_artifact: bool = False
    requires_provider_proof: bool = False

    def __post_init__(self) -> None:
        # The artifact-creating exemption is for non-consequential bootstrap steps only (DC-2).
        if self.produces_artifact and (self.binding is not None or self.requires_provider_proof):
            raise ValueError("an artifact-creating step cannot carry a binding or need provider proof")


@dataclass(frozen=True)
class ProviderResult:
    status: ProviderStatus
    provider_reference: str | None = None
    evidence_refs: tuple[str, ...] = ()


@dataclass(frozen=True)
class TimelineEvent:
    event_id: UUID
    tenant_id: UUID
    relationship_id: UUID
    work_item_id: UUID
    work_item_type: str
    state: WorkItemState
    occurred_at: datetime
    artifact_id: UUID | None = None
    artifact_digest: str | None = None
    produces_artifact: bool = False
    requires_provider_proof: bool = False
    evidence_refs: tuple[str, ...] = ()
    reason_code: ReasonCode | None = None
    provider_reference: str | None = None

    def to_payload(self) -> dict[str, Any]:
        """The BP ingest shape. Evidence and provider references are references only: a secret-looking value is refused."""
        for value in (*self.evidence_refs, self.provider_reference or ""):
            if _SECRET.search(value):
                raise ValueError("a credential-looking value cannot enter the timeline")
        payload: dict[str, Any] = {
            "eventId": str(self.event_id),
            "workItemId": str(self.work_item_id),
            "workItemType": self.work_item_type,
            "state": self.state.value,
            "occurredAt": self.occurred_at.isoformat(),
            "producesArtifact": self.produces_artifact,
            "requiresProviderProof": self.requires_provider_proof,
            "evidenceRefs": list(self.evidence_refs),
        }
        if self.artifact_id is not None:
            payload["artifactId"] = str(self.artifact_id)
            payload["artifactDigest"] = self.artifact_digest
        if self.reason_code is not None:
            payload["reasonCode"] = self.reason_code.value
        if self.provider_reference is not None:
            payload["providerReference"] = self.provider_reference
        return payload


class TimelineSink(Protocol):
    async def deliver(self, event: TimelineEvent) -> None: ...


class ConstitutionalStepGate(Protocol):
    """CE validation that precedes every consequential step. Raises when the action is denied."""

    async def validate(self, action_type: str, parameters: dict[str, str]) -> None: ...


@dataclass
class ExecutionTimeline:
    """One append-only stream per relationship. BP owns the customer projection; this class owns what is reported.

    The stop fence is checked at dispatch, before any provider call, and again when the call returns, so a provider
    result that arrives after Emergency Stop is recorded as halted evidence and never as success.
    """

    sink: TimelineSink
    gate: ConstitutionalStepGate
    clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc)
    _stopped: set[tuple[UUID, UUID]] = field(default_factory=set)
    _unknown: set[UUID] = field(default_factory=set)

    def is_stopped(self, item: WorkItem) -> bool:
        return (item.tenant_id, item.relationship_id) in self._stopped

    async def propose(self, item: WorkItem) -> TimelineEvent:
        return await self._emit(item, WorkItemState.PROPOSED)

    async def emergency_stop(self, tenant_id: UUID, relationship_id: UUID) -> TimelineEvent:
        """Fence dispatch for this relationship only, then record the stop on its own timeline."""
        self._stopped.add((tenant_id, relationship_id))
        marker = WorkItem(tenant_id, relationship_id, uuid4(), STOP_WORK_ITEM_TYPE)
        return await self._emit(marker, WorkItemState.HALTED, reason=ReasonCode.EMERGENCY_STOP)

    async def dispatch(self, item: WorkItem, call: Callable[[], Awaitable[ProviderResult]]) -> TimelineEvent:
        if item.work_item_id in self._unknown:
            raise BlindRetryRefused(str(item.work_item_id))
        if self.is_stopped(item):
            return await self._emit(item, WorkItemState.HALTED, reason=ReasonCode.EMERGENCY_STOP)
        if not item.produces_artifact:
            await self._require_binding(item)
        await self._emit(item, WorkItemState.APPROVED)
        await self._emit(item, WorkItemState.EXECUTING)
        # Nothing awaits between this last check and the provider call starting, so a stop recorded at any earlier
        # point is seen here and no provider is called after it (checked at dispatch, bounded by one attempt).
        if self.is_stopped(item):
            return await self._emit(item, WorkItemState.HALTED, reason=ReasonCode.EMERGENCY_STOP)
        try:
            result = await call()
        except Exception:
            # The provider may have acted. Reconcile; never repeat the call.
            self._unknown.add(item.work_item_id)
            return await self._emit(item, WorkItemState.EXECUTING, reason=ReasonCode.UNKNOWN_OUTCOME)
        return await self._settle(item, result)

    async def reconcile(self, item: WorkItem, result: ProviderResult) -> TimelineEvent:
        """Append the reconciled truth for an unknown outcome. History is never rewritten."""
        self._unknown.discard(item.work_item_id)
        if self.is_stopped(item):
            return await self._emit(item, WorkItemState.HALTED, reason=ReasonCode.EMERGENCY_STOP, evidence=_late(result))
        if result.status is ProviderStatus.CONFIRMED and result.provider_reference:
            return await self._emit(
                item,
                WorkItemState.COMPLETED,
                reason=ReasonCode.RECONCILED,
                evidence=result.evidence_refs,
                provider_reference=result.provider_reference,
            )
        return await self._emit(item, WorkItemState.FAILED, reason=ReasonCode.RECONCILED, evidence=result.evidence_refs)

    async def _settle(self, item: WorkItem, result: ProviderResult) -> TimelineEvent:
        if self.is_stopped(item):
            return await self._emit(item, WorkItemState.HALTED, reason=ReasonCode.EMERGENCY_STOP, evidence=_late(result))
        if result.status is ProviderStatus.REJECTED:
            return await self._emit(
                item, WorkItemState.FAILED, reason=ReasonCode.PROVIDER_REJECTED, evidence=result.evidence_refs
            )
        proven = result.status is ProviderStatus.CONFIRMED and bool(result.provider_reference)
        if item.requires_provider_proof and not proven:
            return await self._emit(
                item,
                WorkItemState.EXECUTING,
                reason=ReasonCode.AWAITING_PROVIDER_PROOF,
                evidence=result.evidence_refs,
            )
        return await self._emit(
            item,
            WorkItemState.COMPLETED,
            evidence=result.evidence_refs,
            provider_reference=result.provider_reference,
        )

    async def _require_binding(self, item: WorkItem) -> None:
        binding = item.binding
        if binding is None:
            await self._emit(item, WorkItemState.FAILED, reason=ReasonCode.POLICY_BLOCKED)
            raise ArtifactBindingRefused("no artifact binding")
        try:
            await self.gate.validate(EXECUTE_STEP_ACTION, binding.as_action_parameters(item.relationship_id))
        except Exception as error:
            await self._emit(item, WorkItemState.FAILED, reason=ReasonCode.POLICY_BLOCKED)
            raise ArtifactBindingRefused(str(error)) from error

    async def _emit(
        self,
        item: WorkItem,
        state: WorkItemState,
        reason: ReasonCode | None = None,
        evidence: tuple[str, ...] = (),
        provider_reference: str | None = None,
    ) -> TimelineEvent:
        binding = item.binding
        event = TimelineEvent(
            event_id=uuid4(),
            tenant_id=item.tenant_id,
            relationship_id=item.relationship_id,
            work_item_id=item.work_item_id,
            work_item_type=item.work_item_type,
            state=state,
            occurred_at=self.clock(),
            artifact_id=binding.artifact_id if binding else None,
            artifact_digest=binding.artifact_digest if binding else None,
            produces_artifact=item.produces_artifact,
            requires_provider_proof=item.requires_provider_proof,
            evidence_refs=evidence,
            reason_code=reason,
            provider_reference=provider_reference,
        )
        await self.sink.deliver(event)
        return event


def _late(result: ProviderResult) -> tuple[str, ...]:
    """A result that arrived after Emergency Stop is kept as evidence only."""
    references = result.evidence_refs or ("late-provider-result",)
    return (*references, f"late-result:{result.status.value.lower()}")
