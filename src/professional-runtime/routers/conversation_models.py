# Implements: architecture/reference/api-specs/professional-runtime.openapi.yaml §Conversation Execution
# constitutional_basis: C-023, C-059, C-063, C-076
from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class AliasModel(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class ExecutionTextV1(AliasModel):
    schema_version: Literal["1.0"] = Field(alias="schemaVersion")
    content_type: Literal["TEXT"] = Field(alias="contentType")
    text: str = Field(min_length=1, max_length=32000)
    language: str = Field(min_length=2, max_length=35)


class OperationalMandateV1(AliasModel):
    schema_version: Literal["1.0"] = Field(alias="schemaVersion")
    mandate_id: uuid.UUID = Field(alias="mandateId")
    mandate_digest: str = Field(alias="mandateDigest", pattern=r"^sha256:[0-9a-f]{64}$")
    tenant_id: str = Field(alias="tenantId", min_length=1)
    relationship_id: str = Field(alias="relationshipId", min_length=1)
    agent_instance_id: str = Field(alias="agentInstanceId", min_length=1)
    actor_id: str = Field(alias="actorId", min_length=1)
    actor_role: str = Field(alias="actorRole", min_length=1)
    relationship_lifecycle: str = Field(alias="relationshipLifecycle", min_length=1)
    engagement_mode: Literal["TRIAL", "LIVE"] = Field(alias="engagementMode")
    professional_type: str = Field(alias="professionalType", min_length=1)
    release_sequence: int = Field(alias="releaseSequence", ge=1)
    professional_version: str = Field(alias="professionalVersion", min_length=1)
    specification_revision: str = Field(alias="specificationRevision", min_length=1)
    specification_digest: str = Field(alias="specificationDigest", pattern=r"^sha256:[0-9a-f]{64}$")
    admission_revision: int = Field(alias="admissionRevision", ge=1)
    admission_content_digest: str = Field(alias="admissionContentDigest", pattern=r"^sha256:[0-9a-f]{64}$")
    artifact_digest: str = Field(alias="artifactDigest", pattern=r"^sha256:[0-9a-f]{64}$")
    base_spec_version: str = Field(alias="baseSpecVersion", min_length=1)
    constitutional_dna_version: str = Field(alias="constitutionalDnaVersion", min_length=1)
    pac_version: str = Field(alias="pacVersion", min_length=1)
    adapter_protocol_version: str = Field(alias="adapterProtocolVersion", min_length=1)
    customer_contract_digest: str = Field(alias="customerContractDigest", pattern=r"^sha256:[0-9a-f]{64}$")
    skill_id: str = Field(alias="skillId", min_length=1)
    skill_version: str = Field(alias="skillVersion", min_length=1)
    input_schema_digest: str = Field(alias="inputSchemaDigest", pattern=r"^sha256:[0-9a-f]{64}$")
    output_schema_digest: str = Field(alias="outputSchemaDigest", pattern=r"^sha256:[0-9a-f]{64}$")
    prompt_version: str = Field(alias="promptVersion", min_length=1)
    prompt_digest: str = Field(alias="promptDigest", pattern=r"^sha256:[0-9a-f]{64}$")
    context_revision: int = Field(alias="contextRevision", ge=1)
    configuration_revision: int = Field(alias="configurationRevision", ge=1)
    goal_revision: int = Field(alias="goalRevision", ge=1)
    decision_space_revision: int = Field(alias="decisionSpaceRevision", ge=1)
    budget_allowance_ref: str = Field(alias="budgetAllowanceRef", min_length=1)
    review_policy_revision: int = Field(alias="reviewPolicyRevision", ge=1)
    approval_refs: tuple[str, ...] = Field(alias="approvalRefs", min_length=1)
    stopped: bool
    stop_evidence_ref: str | None = Field(default=None, alias="stopEvidenceRef")
    operational_purpose: str = Field(alias="operationalPurpose", min_length=1)
    permitted_actions: tuple[str, ...] = Field(alias="permittedActions", min_length=1)
    exclusions: tuple[str, ...]
    deadline: datetime
    idempotency_identity: uuid.UUID = Field(alias="idempotencyIdentity")
    constitutional_decision_ref: str = Field(alias="constitutionalDecisionRef", min_length=1)
    constitutional_evidence_ref: str = Field(alias="constitutionalEvidenceRef", min_length=1)
    billing_reservation_ref: str | None = Field(default=None, alias="billingReservationRef")
    billing_attribution_ref: str | None = Field(default=None, alias="billingAttributionRef")


class StartExecutionRequestV1(AliasModel):
    schema_version: Literal["1.0"] = Field(alias="schemaVersion")
    message_id: uuid.UUID = Field(alias="messageId")
    decision_space_version: int = Field(alias="decisionSpaceVersion", ge=1)
    locale: str = Field(min_length=2, max_length=35)
    operational_mandate: OperationalMandateV1 = Field(alias="operationalMandate")
    content: ExecutionTextV1
    active_goal_context_id: uuid.UUID | None = Field(default=None, alias="activeGoalContextId")


class ProfessionalExecutionState(StrEnum):
    ACCEPTED = "ACCEPTED"
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    STOPPED = "STOPPED"
    UNRESOLVED = "UNRESOLVED"


class ProfessionalExecutionCompletionReason(StrEnum):
    COMPLETE = "COMPLETE"
    PARTIAL_FAILURE = "PARTIAL_FAILURE"
    CANCELLED = "CANCELLED"
    EMERGENCY_STOPPED = "EMERGENCY_STOPPED"


class ProfessionalExecutionV1(AliasModel):
    schema_version: Literal["1.0"] = Field(alias="schemaVersion")
    execution_id: uuid.UUID = Field(alias="executionId")
    conversation_id: uuid.UUID = Field(alias="conversationId")
    message_id: uuid.UUID = Field(alias="messageId")
    state: ProfessionalExecutionState
    partial: bool
    completion_reason: ProfessionalExecutionCompletionReason | None = Field(default=None, alias="completionReason")
    replayed: bool
    accepted_at: datetime = Field(alias="acceptedAt")
    updated_at: datetime | None = Field(default=None, alias="updatedAt")


class ExecutionProblemCode(StrEnum):
    REQUEST_INVALID = "EXECUTION_REQUEST_INVALID"
    NOT_ACCESSIBLE = "EXECUTION_NOT_ACCESSIBLE"
    MANDATE_INVALID = "EXECUTION_MANDATE_INVALID"
    IDEMPOTENCY_CONFLICT = "EXECUTION_IDEMPOTENCY_CONFLICT"
    SCHEMA_UNSUPPORTED = "EXECUTION_SCHEMA_UNSUPPORTED"
    CURSOR_EXPIRED = "EXECUTION_CURSOR_EXPIRED"
    STOPPED = "EXECUTION_STOPPED"
    DECISION_SPACE_STALE = "EXECUTION_DECISION_SPACE_STALE"
    CONSTITUTIONAL_UNAVAILABLE = "EXECUTION_CONSTITUTIONAL_UNAVAILABLE"
    RUNTIME_UNAVAILABLE = "EXECUTION_RUNTIME_UNAVAILABLE"


class ExecutionProblemDetail(AliasModel):
    type: str
    title: str
    status: int
    code: ExecutionProblemCode
    correlation_id: uuid.UUID = Field(alias="correlationId")
    retry_after_seconds: int | None = Field(default=None, alias="retryAfterSeconds", ge=1)


class HealthResponse(AliasModel):
    status: Literal["healthy", "degraded", "unhealthy"]
    temporal_connected: bool = Field(alias="temporalConnected")
    constitutional_engine_reachable: bool = Field(alias="constitutionalEngineReachable")
    active_paas_sessions: int = Field(alias="activePAASSessions", ge=0)


class ProfessionalDeltaV1(AliasModel):
    content_index: int = Field(alias="contentIndex", ge=0)
    append_text: str = Field(alias="appendText", max_length=8000)
    partial: Literal[True]


class ProfessionalCardProposalV1(AliasModel):
    schema_version: Literal["1.0"] = Field(alias="schemaVersion")
    card_type: Literal["ACTION", "PLAN", "DELIVERABLE", "DECISION"] = Field(alias="cardType")
    card_id: uuid.UUID = Field(alias="cardId")
    owner: Literal["CUSTOMER", "PROFESSIONAL", "SHARED"]
    state: str = Field(min_length=1, max_length=64)
    effect: str = Field(min_length=1, max_length=500)
    data: dict[str, Any]


class ProfessionalEvidenceEventV1(AliasModel):
    state: Literal["PENDING", "RECORDED", "FAILED"]
    evidence_record_id: uuid.UUID | None = Field(default=None, alias="evidenceRecordId")


class ProfessionalTerminalEventV1(AliasModel):
    state: ProfessionalExecutionState
    partial: bool
    completion_reason: ProfessionalExecutionCompletionReason = Field(alias="completionReason")
    error_code: str | None = Field(default=None, alias="errorCode", max_length=64)


class ProfessionalReconciliationEventV1(AliasModel):
    reason: Literal["EVENT_CURSOR_EXPIRED", "EVENT_GAP", "STATE_CONFLICT"]


class ProfessionalHeartbeatV1(AliasModel):
    server_time: datetime = Field(alias="serverTime")


EventData = (
    ProfessionalDeltaV1
    | ProfessionalCardProposalV1
    | ProfessionalEvidenceEventV1
    | ProfessionalTerminalEventV1
    | ProfessionalReconciliationEventV1
    | ProfessionalHeartbeatV1
)


class ProfessionalExecutionEventV1(AliasModel):
    schema_version: Literal["1.0"] = Field(alias="schemaVersion")
    event_id: str = Field(alias="eventId", min_length=1, max_length=256)
    event_type: Literal[
        "execution.accepted",
        "processing.started",
        "response.delta",
        "card.proposed",
        "evidence.pending",
        "evidence.recorded",
        "execution.completed",
        "execution.failed",
        "execution.cancelled",
        "execution.stopped",
        "reconciliation.required",
        "heartbeat",
    ] = Field(alias="eventType")
    conversation_id: uuid.UUID = Field(alias="conversationId")
    execution_id: uuid.UUID = Field(alias="executionId")
    message_id: uuid.UUID = Field(alias="messageId")
    sequence: int = Field(ge=1)
    occurred_at: datetime = Field(alias="occurredAt")
    data: EventData
