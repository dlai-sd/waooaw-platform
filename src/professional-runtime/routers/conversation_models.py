# Implements: architecture/reference/api-specs/professional-runtime.openapi.yaml §Conversation Execution
# constitutional_basis: C-023, C-059, C-063, C-076
from __future__ import annotations

import hashlib
import hmac
import itertools
import json
import uuid
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any, Literal, cast

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    SerializerFunctionWrapHandler,
    field_validator,
    model_serializer,
    model_validator,
)


class AliasModel(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class ExecutionTextV1(AliasModel):
    schema_version: Literal["1.0"] = Field(alias="schemaVersion")
    content_type: Literal["TEXT"] = Field(alias="contentType")
    text: str = Field(min_length=1, max_length=32000)
    language: str = Field(min_length=2, max_length=35)


class ConversationInferencePolicyReferenceV1(AliasModel):
    ref: str = Field(min_length=1, max_length=200)
    version: str = Field(min_length=1, max_length=64)
    digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")


class ConversationOperationBindingV1(AliasModel):
    kind: Literal["PROFESSIONAL_RESPONSE", "EMPLOYMENT_CONTRIBUTION_INTERPRETATION"]
    governed_action: str = Field(alias="governedAction", min_length=1, max_length=200)
    input_schema_digest: str = Field(alias="inputSchemaDigest", pattern=r"^sha256:[0-9a-f]{64}$")
    output_schema_digest: str = Field(alias="outputSchemaDigest", pattern=r"^sha256:[0-9a-f]{64}$")
    prompt_policy: ConversationInferencePolicyReferenceV1 = Field(alias="promptPolicy")
    model_policy: ConversationInferencePolicyReferenceV1 = Field(alias="modelPolicy")
    patch_type: (
        Literal[
            "INDUCTION_CONTEXT",
            "GOAL",
            "PLAN",
            "CALENDAR",
            "DEPENDENCY",
            "OPERATING_CYCLE",
            "CORRECTIVE_PROPOSAL",
        ]
        | None
    ) = Field(default=None, alias="patchType")

    @model_validator(mode="after")
    def validate_operation(self) -> ConversationOperationBindingV1:
        if (self.kind == "EMPLOYMENT_CONTRIBUTION_INTERPRETATION") != (self.patch_type is not None) or (
            self.kind == "PROFESSIONAL_RESPONSE" and "patch_type" in self.model_fields_set
        ):
            raise ValueError("Only employment interpretation requires an explicit patch type")
        for value in (
            self.governed_action,
            self.prompt_policy.ref,
            self.prompt_policy.version,
            self.model_policy.ref,
            self.model_policy.version,
        ):
            if not value.strip():
                raise ValueError("Operation policy coordinates cannot be whitespace")
        return self

    @model_serializer(mode="wrap")
    def serialize_operation(self, handler: SerializerFunctionWrapHandler) -> dict[str, Any]:
        result = cast(dict[str, Any], handler(self))
        if self.patch_type is None:
            result.pop("patchType", None)
            result.pop("patch_type", None)
        return result


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
    conversation_operation: ConversationOperationBindingV1 | None = Field(default=None, alias="conversationOperation")

    @model_validator(mode="after")
    def validate_conversation_operation(self) -> OperationalMandateV1:
        operation = self.conversation_operation
        if operation is not None and (
            operation.governed_action not in self.permitted_actions
            or operation.governed_action in self.exclusions
            or operation.input_schema_digest != self.input_schema_digest
            or operation.output_schema_digest != self.output_schema_digest
            or operation.prompt_policy.version != self.prompt_version
            or operation.prompt_policy.digest != self.prompt_digest
        ):
            raise ValueError("Conversation operation is not bound to the current mandate")
        return self

    @model_serializer(mode="wrap")
    def serialize_mandate(self, handler: SerializerFunctionWrapHandler) -> dict[str, Any]:
        result = cast(dict[str, Any], handler(self))
        if self.conversation_operation is None:
            result.pop("conversationOperation", None)
            result.pop("conversation_operation", None)
        return result


class StartExecutionRequestV1(AliasModel):
    schema_version: Literal["1.0"] = Field(alias="schemaVersion")
    message_id: uuid.UUID = Field(alias="messageId")
    decision_space_version: int = Field(alias="decisionSpaceVersion", ge=1)
    locale: str = Field(min_length=2, max_length=35)
    operational_mandate: OperationalMandateV1 = Field(alias="operationalMandate")
    content: ExecutionTextV1
    active_goal_context_id: uuid.UUID | None = Field(default=None, alias="activeGoalContextId")


class BatchExecutionSourceV1(AliasModel):
    schema_version: Literal["1.0"] = Field(alias="schemaVersion")
    message_id: uuid.UUID = Field(alias="messageId")
    execution_id: uuid.UUID = Field(alias="executionId")
    sequence: int = Field(ge=1)
    work_item_id: uuid.UUID = Field(alias="workItemId")
    work_item_revision: int = Field(alias="workItemRevision", ge=1)
    work_item_invocation_id: uuid.UUID = Field(alias="workItemInvocationId")
    idempotency_key: uuid.UUID = Field(alias="idempotencyKey")
    evidence_id: uuid.UUID = Field(alias="evidenceId")
    text: str = Field(min_length=1, max_length=2000)
    language: str = Field(min_length=2, max_length=35)
    operational_mandate: OperationalMandateV1 = Field(alias="operationalMandate")


def batch_source_list_digest(sources: tuple[BatchExecutionSourceV1, ...]) -> str:
    source_payload = [
        {
            "schemaVersion": source.schema_version,
            "messageId": str(source.message_id),
            "executionId": str(source.execution_id),
            "sequence": source.sequence,
            "workItemId": str(source.work_item_id),
            "workItemRevision": source.work_item_revision,
            "workItemInvocationId": str(source.work_item_invocation_id),
            "idempotencyKey": str(source.idempotency_key),
            "evidenceId": str(source.evidence_id),
            "text": source.text,
            "language": source.language,
            "mandateId": str(source.operational_mandate.mandate_id),
            "mandateDigest": source.operational_mandate.mandate_digest,
        }
        for source in sources
    ]
    canonical_sources = json.dumps(
        source_payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode()
    return "sha256:" + hashlib.sha256(canonical_sources).hexdigest()


class StartBatchExecutionRequestV1(AliasModel):
    schema_version: Literal["1.0"] = Field(alias="schemaVersion")
    batch_id: uuid.UUID = Field(alias="batchId")
    decision_space_version: int = Field(alias="decisionSpaceVersion", ge=1)
    locale: str = Field(min_length=2, max_length=35)
    source_list_digest: str = Field(
        alias="sourceListDigest",
        pattern=r"^sha256:[0-9a-f]{64}$",
    )
    sources: tuple[BatchExecutionSourceV1, ...] = Field(min_length=2, max_length=3)
    content: ExecutionTextV1

    @model_validator(mode="after")
    def validate_batch_sources(self) -> StartBatchExecutionRequestV1:
        sources = self.sources
        if (
            self.batch_id.int == 0
            or len({source.message_id for source in sources}) != len(sources)
            or len({source.execution_id for source in sources}) != len(sources)
            or len({source.work_item_id for source in sources}) != 1
            or len({source.work_item_revision for source in sources}) != 1
            or len({source.work_item_invocation_id for source in sources}) != 1
            or len({source.idempotency_key for source in sources}) != len(sources)
            or len({source.evidence_id for source in sources}) != len(sources)
            or any(right.sequence != left.sequence + 1 for left, right in itertools.pairwise(sources))
            or any(
                source.message_id.int == 0
                or source.execution_id.int == 0
                or source.work_item_id.int == 0
                or source.work_item_invocation_id.int == 0
                or source.idempotency_key.int == 0
                or source.evidence_id.int == 0
                for source in sources
            )
        ):
            raise ValueError("Batch sources must be unique and canonically contiguous")

        first = sources[0]
        shared_authority = _batch_shared_authority(first.operational_mandate)
        for source in sources:
            mandate = source.operational_mandate
            source_authority = _batch_shared_authority(mandate)
            expected_evidence_ref = f"ce-evidence:{source.evidence_id}"
            canonical_mandate = json.dumps(
                {
                    **mandate.model_dump(
                        by_alias=True,
                        mode="json",
                        exclude={"mandate_digest"},
                    ),
                    "deadline": mandate.deadline.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                },
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            ).encode()
            expected_mandate_digest = "sha256:" + hashlib.sha256(canonical_mandate).hexdigest()
            if (
                source_authority != shared_authority
                or source.idempotency_key != mandate.idempotency_identity
                or mandate.constitutional_evidence_ref != expected_evidence_ref
                or not hmac.compare_digest(
                    mandate.mandate_digest,
                    expected_mandate_digest,
                )
                or mandate.stopped
                or mandate.stop_evidence_ref is not None
                or mandate.decision_space_revision != self.decision_space_version
                or source.language != first.language
                or not source.text.strip()
            ):
                raise ValueError("Batch source authority or canonical content differs")

        combined_text = "\n".join(source.text for source in sources)
        if (
            self.content.schema_version != "1.0"
            or self.content.content_type != "TEXT"
            or self.content.text != combined_text
            or self.content.language != first.language
            or len(combined_text.encode("utf-16-le")) // 2 > 2000
        ):
            raise ValueError("Batch content must exactly match bounded ordered source text")

        expected_digest = batch_source_list_digest(sources)
        if not hmac.compare_digest(self.source_list_digest, expected_digest):
            raise ValueError("Batch source-list digest does not match its ordered sources")
        return self


class BatchExecutionReceiptV1(AliasModel):
    schema_version: Literal["1.0"] = Field(alias="schemaVersion")
    batch_id: uuid.UUID = Field(alias="batchId")
    execution_id: uuid.UUID = Field(alias="executionId")
    conversation_id: uuid.UUID = Field(alias="conversationId")
    source_list_digest: str = Field(alias="sourceListDigest", pattern=r"^sha256:[0-9a-f]{64}$")
    request_digest: str = Field(alias="requestDigest", pattern=r"^sha256:[0-9a-f]{64}$")
    state: Literal["ACCEPTED"]
    replayed: bool
    accepted_at: AwareDatetime = Field(alias="acceptedAt")


def _batch_shared_authority(mandate: OperationalMandateV1) -> tuple[Any, ...]:
    return (
        mandate.tenant_id,
        mandate.relationship_id,
        mandate.actor_id,
        mandate.actor_role,
        mandate.agent_instance_id,
        mandate.relationship_lifecycle,
        mandate.engagement_mode,
        mandate.professional_type,
        mandate.release_sequence,
        mandate.professional_version,
        mandate.specification_revision,
        mandate.specification_digest,
        mandate.admission_revision,
        mandate.admission_content_digest,
        mandate.artifact_digest,
        mandate.base_spec_version,
        mandate.constitutional_dna_version,
        mandate.pac_version,
        mandate.adapter_protocol_version,
        mandate.customer_contract_digest,
        mandate.skill_id,
        mandate.skill_version,
        mandate.input_schema_digest,
        mandate.output_schema_digest,
        mandate.prompt_version,
        mandate.prompt_digest,
        mandate.context_revision,
        mandate.configuration_revision,
        mandate.goal_revision,
        mandate.decision_space_revision,
        mandate.budget_allowance_ref,
        mandate.review_policy_revision,
        mandate.approval_refs,
        mandate.permitted_actions,
        mandate.exclusions,
        mandate.conversation_operation,
    )


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


class ProfessionalSystemResponseV1(AliasModel):
    text: str = Field(min_length=1, max_length=8000)
    code: Literal[
        "MODEL_UNAVAILABLE",
        "MATERIAL_UNCERTAINTY",
        "SEMANTIC_PATH_UNREPRESENTABLE",
        "POLICY_REJECTED",
        "INTERNAL_FAILURE",
        "OPERATION_UNSUPPORTED",
    ]


EventData = (
    ProfessionalDeltaV1
    | ProfessionalCardProposalV1
    | ProfessionalEvidenceEventV1
    | ProfessionalTerminalEventV1
    | ProfessionalReconciliationEventV1
    | ProfessionalHeartbeatV1
    | ProfessionalSystemResponseV1
)


class ProfessionalExecutionEventV1(AliasModel):
    schema_version: Literal["1.0"] = Field(alias="schemaVersion")
    event_id: str = Field(alias="eventId", min_length=1, max_length=256)
    event_type: Literal[
        "execution.accepted",
        "processing.started",
        "response.delta",
        "response.system",
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


class OriginalConversationExecutionSourceV1(AliasModel):
    schema_version: Literal["1.0"] = Field(alias="schemaVersion")
    tenant_id: uuid.UUID = Field(alias="tenantId")
    relationship_id: uuid.UUID = Field(alias="relationshipId")
    conversation_id: uuid.UUID = Field(alias="conversationId")
    execution_id: uuid.UUID = Field(alias="executionId")
    original_message_id: uuid.UUID = Field(alias="originalMessageId")
    original_actor_id: uuid.UUID = Field(alias="originalActorId")
    mandate_id: uuid.UUID = Field(alias="mandateId")
    mandate_digest: str = Field(alias="mandateDigest", pattern=r"^sha256:[0-9a-f]{64}$")


class ReconcileConversationExecutionRequestV1(AliasModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=False)

    schema_version: Literal["1.0"] = Field(alias="schemaVersion")
    original_message_id: uuid.UUID = Field(alias="originalMessageId")
    original_source_digest: str = Field(alias="originalSourceDigest", pattern=r"^sha256:[0-9a-f]{64}$")
    after_sequence: int = Field(alias="afterSequence", ge=0)
    reconciliation_authority_id: uuid.UUID = Field(alias="reconciliationAuthorityId")
    permission_expires_at: AwareDatetime = Field(alias="permissionExpiresAt")
    expected_projection_version: int = Field(alias="expectedProjectionVersion", ge=0)

    @field_validator("after_sequence", "expected_projection_version", mode="before")
    @classmethod
    def reject_boolean_integer(cls, value: Any) -> Any:
        if isinstance(value, bool):
            raise ValueError("Boolean values are not integers")
        return value


class ConversationExecutionReconciliationV1(AliasModel):
    schema_version: Literal["1.0"] = Field(alias="schemaVersion")
    conversation_id: uuid.UUID = Field(alias="conversationId")
    execution_id: uuid.UUID = Field(alias="executionId")
    original_message_id: uuid.UUID = Field(alias="originalMessageId")
    original_source_digest: str = Field(alias="originalSourceDigest", pattern=r"^sha256:[0-9a-f]{64}$")
    reconciliation_authority_id: uuid.UUID = Field(alias="reconciliationAuthorityId")
    state: Literal["COMPLETED", "FAILED", "CANCELLED", "UNKNOWN"]
    events: list[ProfessionalExecutionEventV1] = Field(max_length=4096)
    original_request_digest: str | None = Field(default=None, alias="originalRequestDigest", pattern=r"^sha256:[0-9a-f]{64}$")
    result_digest: str | None = Field(default=None, alias="resultDigest", pattern=r"^sha256:[0-9a-f]{64}$")
    next_action: Literal["RECONCILE_CANONICAL_PROJECTION", "OPERATOR_RECONCILIATION_REQUIRED"] = Field(alias="nextAction")

    @model_validator(mode="after")
    def validate_result(self) -> ConversationExecutionReconciliationV1:
        if self.state == "UNKNOWN":
            if self.events or self.result_digest is not None or self.original_request_digest is not None:
                raise ValueError("Unknown recovery cannot carry a terminal result")
            if self.next_action != "OPERATOR_RECONCILIATION_REQUIRED":
                raise ValueError("Unknown recovery requires operator reconciliation")
        elif (
            self.result_digest is None
            or self.original_request_digest is None
            or self.next_action != "RECONCILE_CANONICAL_PROJECTION"
        ):
            raise ValueError("Terminal recovery requires bound owner evidence")
        return self
