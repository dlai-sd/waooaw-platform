"""Typed Agent Runtime Adapter v1 value objects."""

# Implements: architecture/agent-runtime-adapter-contract-v1-execution-plan.md §5
# Constitutional basis: C-023, C-035, C-059, C-065, C-071, C-079, C-080

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any


class InvocationState(StrEnum):
    RECEIVED = "RECEIVED"
    VALIDATING = "VALIDATING"
    ACCEPTED = "ACCEPTED"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    PARTIAL = "PARTIAL"
    CANCEL_REQUESTED = "CANCEL_REQUESTED"
    CANCELLED = "CANCELLED"
    STOP_REQUESTED = "STOP_REQUESTED"
    STOPPED = "STOPPED"


TERMINAL_STATES = frozenset(
    {
        InvocationState.SUCCEEDED,
        InvocationState.FAILED,
        InvocationState.PARTIAL,
        InvocationState.CANCELLED,
        InvocationState.STOPPED,
    }
)


@dataclass(frozen=True)
class AdapterDescriptorV1:
    protocol_version: str
    compatible_minor_versions: tuple[str, ...]
    professional_type_id: str
    professional_version: str
    artifact_digest: str
    admission_content_digest: str
    pac_version: str
    pac_digest: str
    skill_versions: dict[str, str]
    schema_digests: dict[str, str]
    execution_models: tuple[str, ...]
    capabilities: tuple[str, ...]
    maximum_request_bytes: int = 1_048_576
    minimum_deadline_seconds: int = 1
    maximum_deadline_seconds: int = 300
    health_contract_version: str = "1.0.0"


@dataclass(frozen=True)
class AdapterInvocationEnvelopeV1:
    schema_version: str
    tenant_ref: str
    relationship_id: str
    professional_type_id: str
    professional_version: str
    skill_id: str
    skill_version: str
    admission_content_digest: str
    artifact_digest: str
    customer_contract_digest: str
    decision_space_version: str
    configuration_revision: str | None
    goal_revision: str | None
    invocation_id: str
    idempotency_key: str
    payload_digest: str
    ce_decision_ref: str
    evidence_context_ref: str
    deadline: datetime
    correlation_id: str
    mode: str
    traceparent: str | None = None
    stop_evidence_ref: str | None = None

    def deadline_utc(self) -> datetime:
        if self.deadline.tzinfo is None:
            return self.deadline.replace(tzinfo=timezone.utc)
        return self.deadline.astimezone(timezone.utc)


@dataclass
class AdapterInvocationV1:
    envelope: AdapterInvocationEnvelopeV1
    state: InvocationState = InvocationState.RECEIVED
    state_version: int = 0
    output: dict[str, Any] | None = None
    completion_reason: str | None = None
    evidence_references: tuple[str, ...] = ()
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class AdapterEventV1:
    event_id: str
    invocation_id: str
    sequence: int
    event_type: str
    state: InvocationState
    timestamp: datetime
    payload_digest: str
    partial: bool = False


@dataclass(frozen=True)
class AdapterResultV1:
    schema_version: str
    invocation_id: str
    state: InvocationState
    completion_reason: str
    output: dict[str, Any]
    output_payload_digest: str
    evidence_references: tuple[str, ...]
    warnings: tuple[str, ...]
    started_at: datetime
    completed_at: datetime