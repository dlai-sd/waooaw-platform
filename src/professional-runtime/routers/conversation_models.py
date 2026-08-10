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


class StartExecutionRequestV1(AliasModel):
    schema_version: Literal["1.0"] = Field(alias="schemaVersion")
    message_id: uuid.UUID = Field(alias="messageId")
    decision_space_version: int = Field(alias="decisionSpaceVersion", ge=1)
    locale: str = Field(min_length=2, max_length=35)
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
