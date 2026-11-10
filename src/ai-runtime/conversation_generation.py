# Implements: work-contracts/WC-134-batching-offering-and-spend-work-component.md §9.2
"""Agent-bound bounded inference; dispatch claims are never replay permission."""

from __future__ import annotations

import hashlib
import hmac
import itertools
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Literal, Protocol
from collections.abc import Awaitable, Callable
from uuid import UUID
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, Header, Request
from fastapi.responses import JSONResponse
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator, model_validator

from employment_auth import EmploymentAuthError
from employment_persistence import EmploymentDispatchStoppedError

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/internal/v1/conversation-generations", tags=["Conversation Generation"])


class GenerationInput(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    text: str = Field(min_length=1, max_length=32000)
    language: str = Field(min_length=2, max_length=35)

    @field_validator("text")
    @classmethod
    def bounded_text(cls, value: str) -> str:
        if not value.strip() or "\x00" in value or len(value.encode("utf-16-le")) // 2 > 32000:
            raise ValueError("Generation input is not bounded canonical text")
        return value


class BatchGenerationSource(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    schema_version: Literal["1.0"] = Field(alias="schemaVersion")
    message_id: UUID = Field(alias="messageId")
    execution_id: UUID = Field(alias="executionId")
    sequence: int = Field(ge=1)
    work_item_id: UUID = Field(alias="workItemId")
    work_item_revision: int = Field(alias="workItemRevision", ge=1)
    work_item_invocation_id: UUID = Field(alias="workItemInvocationId")
    idempotency_key: UUID = Field(alias="idempotencyKey")
    evidence_id: UUID = Field(alias="evidenceId")
    text: str = Field(min_length=1, max_length=2000)
    language: str = Field(min_length=2, max_length=35)
    operational_mandate: dict[str, Any] = Field(alias="operationalMandate")


class BatchGenerationBinding(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    batch_id: UUID = Field(alias="batchId")
    source_list_digest: str = Field(alias="sourceListDigest", pattern=r"^sha256:[0-9a-f]{64}$")
    sources: tuple[BatchGenerationSource, ...] = Field(min_length=2, max_length=3)

    def verify(self, generation_input: GenerationInput, mandate: dict[str, Any]) -> None:
        sources = self.sources
        canonical_sources = canonical(
            [
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
                    "mandateId": str(source.operational_mandate.get("mandateId")),
                    "mandateDigest": source.operational_mandate.get("mandateDigest"),
                }
                for source in sources
            ]
        )
        if (
            not hmac.compare_digest(
                self.source_list_digest,
                f"sha256:{hashlib.sha256(canonical_sources).hexdigest()}",
            )
            or any(right.sequence != left.sequence + 1 for left, right in itertools.pairwise(sources))
            or len({source.message_id for source in sources}) != len(sources)
            or len({source.execution_id for source in sources}) != len(sources)
            or len({source.idempotency_key for source in sources}) != len(sources)
            or len({source.evidence_id for source in sources}) != len(sources)
            or len({source.work_item_id for source in sources}) != 1
            or len({source.work_item_revision for source in sources}) != 1
            or len({source.work_item_invocation_id for source in sources}) != 1
            or generation_input.text != "\n".join(source.text for source in sources)
            or generation_input.language != sources[0].language
            or len(generation_input.text.encode("utf-16-le")) // 2 > 2000
            or mandate != sources[0].operational_mandate
        ):
            raise ValueError("Generation batch identity or canonical content differs")
        for source in sources:
            source_mandate = source.operational_mandate
            shared_keys = (
                "tenantId",
                "relationshipId",
                "agentInstanceId",
                "actorId",
                "actorRole",
                "relationshipLifecycle",
                "engagementMode",
                "professionalType",
                "releaseSequence",
                "professionalVersion",
                "specificationRevision",
                "specificationDigest",
                "admissionRevision",
                "admissionContentDigest",
                "artifactDigest",
                "customerContractDigest",
                "skillId",
                "skillVersion",
                "inputSchemaDigest",
                "outputSchemaDigest",
                "promptVersion",
                "promptDigest",
                "contextRevision",
                "configurationRevision",
                "goalRevision",
                "decisionSpaceRevision",
                "budgetAllowanceRef",
                "reviewPolicyRevision",
                "approvalRefs",
                "permittedActions",
                "exclusions",
                "conversationOperation",
            )
            digest = source_mandate.get("mandateDigest")
            unsigned = {key: value for key, value in source_mandate.items() if key != "mandateDigest"}
            deadline = datetime.fromisoformat(str(unsigned.get("deadline", "")).replace("Z", "+00:00"))
            unsigned["deadline"] = deadline.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            if (
                source.idempotency_key != UUID(str(source_mandate.get("idempotencyIdentity")))
                or source_mandate.get("constitutionalEvidenceRef") != f"ce-evidence:{source.evidence_id}"
                or not isinstance(digest, str)
                or not hmac.compare_digest(digest, f"sha256:{hashlib.sha256(canonical(unsigned)).hexdigest()}")
                or source_mandate.get("stopped") is not False
                or source_mandate.get("stopEvidenceRef") is not None
                or source.language != sources[0].language
                or any(source_mandate.get(key) != sources[0].operational_mandate.get(key) for key in shared_keys)
            ):
                raise ValueError("Generation batch source authority differs")


class GenerationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    schema_version: Literal["1.0"] = Field(alias="schemaVersion")
    relationship_ref: UUID = Field(alias="relationshipRef")
    conversation_id: UUID = Field(alias="conversationId")
    execution_id: UUID = Field(alias="executionId")
    contribution_ref: UUID = Field(alias="contributionRef")
    operational_mandate: dict[str, Any] = Field(alias="operationalMandate")
    input: GenerationInput
    batch: BatchGenerationBinding | None = None
    request_digest: str = Field(alias="requestDigest", pattern=r"^[0-9a-f]{64}$")

    def verify_binding(self, context: Any, idempotency_key: UUID, *, recovery: bool) -> None:
        payload = self.model_dump(by_alias=True, mode="json", exclude={"request_digest"})
        digests = {
            hashlib.sha256(canonical(payload)).hexdigest(),
            hashlib.sha256(canonical({key: value for key, value in payload.items() if value is not None})).hexdigest(),
        }
        mandate = self.operational_mandate
        operation = mandate.get("conversationOperation")
        if self.batch is not None:
            self.batch.verify(self.input, mandate)
        idempotency_matches = (
            mandate.get("idempotencyIdentity") == str(idempotency_key)
            if self.batch is None
            else self.batch.batch_id == idempotency_key
        )
        if (
            self.request_digest not in digests
            or mandate.get("schemaVersion") != "1.0"
            or mandate.get("tenantId") != context.tenant_id
            or mandate.get("relationshipId") != str(self.relationship_ref)
            or mandate.get("actorId") != context.actor_subject
            or mandate.get("actorRole") != context.effective_role
            or not idempotency_matches
            or not isinstance(operation, dict)
            or operation.get("kind") != "PROFESSIONAL_RESPONSE"
            or operation.get("governedAction") not in mandate.get("permittedActions", [])
            or operation.get("governedAction") in mandate.get("exclusions", [])
            or mandate.get("stopped") is not False
            or mandate.get("stopEvidenceRef") is not None
            or mandate.get("relationshipLifecycle") not in {"TRIAL_ACTIVE", "ACTIVE"}
            or mandate.get("engagementMode") != ("TRIAL" if mandate.get("relationshipLifecycle") == "TRIAL_ACTIVE" else "LIVE")
            or not mandate.get("approvalRefs")
            or not mandate.get("agentInstanceId")
            or context.subject_reference != str(self.contribution_ref)
            or (self.batch is None) != (self.contribution_ref != idempotency_key)
        ):
            raise ValueError("Generation is not bound to the accepted agent skill and relationship")
        deadline = datetime.fromisoformat(str(mandate["deadline"]).replace("Z", "+00:00"))
        if deadline.tzinfo is None or (not recovery and deadline <= datetime.now(timezone.utc)):
            raise ValueError("Generation authority expired")
        if context.command_id != str(self.execution_id):
            raise ValueError("Generation command differs from the original execution")


class GenerationResult(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    schema_version: Literal["1.0"] = Field(default="1.0", alias="schemaVersion")
    execution_id: UUID = Field(alias="executionId")
    request_digest: str = Field(alias="requestDigest", pattern=r"^[0-9a-f]{64}$")
    state: Literal["COMPLETED", "FAILED", "UNRESOLVED"]
    text: str | None = Field(default=None, min_length=1, max_length=32000)
    reason: str | None = None
    input_tokens: int | None = Field(default=None, alias="inputTokens", ge=0)
    output_tokens: int | None = Field(default=None, alias="outputTokens", ge=0)
    reservation_id: UUID | None = Field(default=None, alias="reservationId")
    commercial_reservation_id: UUID | None = Field(default=None, alias="commercialReservationId")
    evidence_id: UUID | None = Field(default=None, alias="evidenceId")

    @model_validator(mode="after")
    def terminal_shape(self) -> GenerationResult:
        if self.state == "COMPLETED":
            if (
                self.text is None
                or not self.text.strip()
                or "\x00" in self.text
                or len(self.text.encode("utf-16-le")) // 2 > 32000
                or self.reason is not None
                or self.input_tokens is None
                or self.input_tokens > 8192
                or self.output_tokens is None
                or self.output_tokens > 2048
                or self.reservation_id is None
                or self.commercial_reservation_id is None
                or self.evidence_id is None
                or self.reservation_id.int == 0
                or self.commercial_reservation_id.int == 0
                or self.evidence_id.int == 0
            ):
                raise ValueError("Completed generation lacks bounded output and evidence")
        elif self.text is not None or not self.reason:
            raise ValueError("Non-completed generation must not release professional content")
        return self


class ContentRecoveryPermission(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    schema_version: Literal["1.0"] = Field(alias="schemaVersion")
    original_message_id: UUID = Field(alias="originalMessageId")
    original_source_digest: str = Field(alias="originalSourceDigest", pattern=r"^sha256:[0-9a-f]{64}$")
    after_sequence: int = Field(alias="afterSequence", ge=0, strict=True)
    reconciliation_authority_id: UUID = Field(alias="reconciliationAuthorityId")
    permission_expires_at: AwareDatetime = Field(alias="permissionExpiresAt")
    expected_projection_version: int = Field(alias="expectedProjectionVersion", ge=0, strict=True)


class GenerationContentRecoveryResult(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    result: GenerationResult
    retained_at: AwareDatetime | None = Field(alias="retainedAt")

    @model_validator(mode="after")
    def retained_shape(self) -> GenerationContentRecoveryResult:
        if self.result.state == "COMPLETED" and self.retained_at is None:
            raise ValueError("Recovered completion lacks its durable result timestamp")
        return self


class GenerationContentRecoveryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    relationship_ref: UUID = Field(alias="relationshipRef")
    generation: GenerationRequest
    permission: ContentRecoveryPermission

    def verify_reader(self, context: Any, key: UUID) -> None:
        now = datetime.now(timezone.utc)
        permission = self.permission
        if (
            self.relationship_ref != self.generation.relationship_ref
            or context.tenant_id != self.generation.operational_mandate.get("tenantId")
            or context.relationship_id != str(self.relationship_ref)
            or context.effective_role not in {"OWNER", "MANAGER"}
            or context.command_id != str(permission.reconciliation_authority_id)
            or context.subject_reference != str(permission.original_message_id)
            or permission.original_message_id != self.generation.contribution_ref
            or not now < permission.permission_expires_at <= now + timedelta(minutes=5)
            or permission.reconciliation_authority_id.int == 0
            or key.int == 0
        ):
            raise ValueError("Content recovery lacks separate current reader authority")
        payload = self.generation.model_dump(by_alias=True, mode="json", exclude={"request_digest"})
        digests = {
            hashlib.sha256(canonical(payload)).hexdigest(),
            hashlib.sha256(canonical({key: value for key, value in payload.items() if value is not None})).hexdigest(),
        }
        if self.generation.request_digest not in digests:
            raise ValueError("Content recovery changed the original generation request")


class ConversationResumeTurn(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    message_id: UUID = Field(alias="messageId")
    sequence: int = Field(ge=1, strict=True)
    actor: Literal["CUSTOMER", "PROFESSIONAL"]
    text: str = Field(min_length=1, max_length=8000)
    language: str = Field(min_length=2, max_length=35)


class ConversationResumeContext(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    schema_version: Literal["1.0"] = Field(alias="schemaVersion")
    tenant_id: UUID = Field(alias="tenantId")
    relationship_id: UUID = Field(alias="relationshipId")
    conversation_id: UUID = Field(alias="conversationId")
    original_message_id: UUID = Field(alias="originalMessageId")
    skill_id: str = Field(alias="skillId", min_length=1)
    before_sequence: int = Field(alias="beforeSequence", ge=1, strict=True)
    turns: list[ConversationResumeTurn] = Field(max_length=12)
    digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def bounded_source(self) -> ConversationResumeContext:
        payload = self.model_dump(by_alias=True, mode="json", exclude={"digest"})
        if (
            "sha256:" + hashlib.sha256(canonical(payload)).hexdigest() != self.digest
            or sum(len(turn.text.encode("utf-16-le")) // 2 for turn in self.turns) > 8000
            or any(not turn.text.strip() or "\x00" in turn.text for turn in self.turns)
            or any(turn.sequence >= self.before_sequence or turn.message_id == self.original_message_id for turn in self.turns)
            or len({turn.message_id for turn in self.turns}) != len(self.turns)
            or any(left.sequence >= right.sequence for left, right in itertools.pairwise(self.turns))
        ):
            raise ValueError("Conversation resume context is not bounded canonical history")
        return self

    def verify_request(self, request: GenerationRequest) -> None:
        if (
            str(self.tenant_id) != request.operational_mandate["tenantId"]
            or self.relationship_id != request.relationship_ref
            or self.conversation_id != request.conversation_id
            or self.original_message_id != request.contribution_ref
            or self.skill_id != request.operational_mandate["skillId"]
        ):
            raise ValueError("Conversation resume context differs from the original agent skill")


class InferenceBinding(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    provider_id: str = Field(alias="providerId", min_length=1, max_length=128)
    provider_identity_uri: str = Field(alias="providerIdentityUri", pattern=r"^spiffe://[^ ]+$")
    adapter: Literal["OLLAMA_INSTITUTIONAL"]
    endpoint: str
    model: str = Field(min_length=1, max_length=200)
    model_digest: str = Field(alias="modelDigest", pattern=r"^sha256:[0-9a-f]{64}$")
    tokenizer_digest: str = Field(alias="tokenizerDigest", pattern=r"^sha256:[0-9a-f]{64}$")
    tokenizer_version: str = Field(alias="tokenizerVersion", min_length=1)
    region: str = Field(min_length=1)
    tier: Literal["LOCAL", "MID", "FRONTIER"]
    languages: list[str] = Field(min_length=1)
    domains: list[str] = Field(min_length=1)
    plan_tiers: list[str] = Field(alias="planTiers", min_length=1)
    resolved_plan_tier: str = Field(alias="resolvedPlanTier", min_length=1)
    mandatory_tiers: list[Literal["LOCAL", "MID", "FRONTIER"]] = Field(alias="mandatoryTiers", min_length=1)
    residency_regions: list[str] = Field(alias="residencyRegions", min_length=1)
    institutional_boundary: Literal[True] = Field(alias="institutionalBoundary")
    configuration_digest: str = Field(alias="configurationDigest", pattern=r"^sha256:[0-9a-f]{64}$")
    rate_digest: str = Field(alias="rateDigest", pattern=r"^sha256:[0-9a-f]{64}$")
    input_paise_per_million: int = Field(alias="inputPaisePerMillion", ge=0, le=1000000000)
    output_paise_per_million: int = Field(alias="outputPaisePerMillion", ge=0, le=1000000000)
    system_prompt: str = Field(alias="systemPrompt", min_length=1, max_length=32000)
    prompt_version: str = Field(alias="promptVersion", min_length=1)
    prompt_digest: str = Field(alias="promptDigest", pattern=r"^sha256:[0-9a-f]{64}$")
    prompt_wrapper: Literal["RAW_SYSTEM_DOUBLE_NEWLINE", "RAW_SYSTEM_CANONICAL_HISTORY_V1"] = Field(alias="promptWrapper")
    model_policy_digest: str = Field(alias="modelPolicyDigest", pattern=r"^sha256:[0-9a-f]{64}$")
    expires_at: AwareDatetime = Field(alias="expiresAt")
    binding_id: UUID = Field(alias="bindingId")
    conversation_context: ConversationResumeContext | None = Field(default=None, alias="conversationContext")

    @model_validator(mode="after")
    def exact_rate_artifact(self) -> InferenceBinding:
        rates = {
            "schemaVersion": "1.0",
            "currency": "INR",
            "rounding": "CEIL_COMPONENT_PER_MILLION",
            "inputPaisePerMillion": self.input_paise_per_million,
            "outputPaisePerMillion": self.output_paise_per_million,
        }
        if "sha256:" + hashlib.sha256(canonical(rates)).hexdigest() != self.rate_digest:
            raise ValueError("Approved rate artifact differs from the resolved rates")
        endpoint = urlparse(self.endpoint)
        if (
            self.tier != "LOCAL"
            or endpoint.scheme != "https"
            or not endpoint.hostname
            or endpoint.username
            or endpoint.password
            or endpoint.query
            or endpoint.fragment
            or endpoint.path not in {"", "/"}
        ):
            raise ValueError("No implemented admitted institutional socket for this selection")
        return self


class InferencePermit(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    reservation_id: UUID = Field(alias="reservationId")
    commercial_reservation_id: UUID = Field(alias="commercialReservationId")
    evidence_id: UUID = Field(alias="evidenceId")
    maximum_cost_paise: int = Field(alias="maximumCostPaise", ge=0)
    expires_at: AwareDatetime = Field(alias="expiresAt")
    binding: InferenceBinding


class InferenceReceipt(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    state: Literal["UNRESOLVED", "RESERVED", "SETTLED", "RELEASED"]
    reservation_id: UUID | None = Field(default=None, alias="reservationId")
    commercial_reservation_id: UUID | None = Field(default=None, alias="commercialReservationId")
    evidence_id: UUID | None = Field(default=None, alias="evidenceId")
    maximum_cost_paise: int | None = Field(default=None, alias="maximumCostPaise", ge=0)
    expires_at: AwareDatetime | None = Field(default=None, alias="expiresAt")

    @model_validator(mode="after")
    def financial_shape(self) -> InferenceReceipt:
        if self.state == "UNRESOLVED":
            if any(
                value is not None
                for value in (
                    self.reservation_id,
                    self.commercial_reservation_id,
                    self.evidence_id,
                    self.maximum_cost_paise,
                    self.expires_at,
                )
            ):
                raise ValueError("Unknown receipt cannot assert financial coordinates")
        elif (
            self.reservation_id is None
            or self.reservation_id.int == 0
            or self.commercial_reservation_id is None
            or self.commercial_reservation_id.int == 0
            or self.evidence_id is None
            or self.evidence_id.int == 0
            or self.maximum_cost_paise is None
            or self.expires_at is None
        ):
            raise ValueError("Known financial receipt lacks its original reservation coordinates")
        return self


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()


class GenerationOwner(Protocol):
    async def resolve(self, request: GenerationRequest, context: Any, key: UUID) -> InferenceBinding: ...
    async def reserve(
        self, request: GenerationRequest, context: Any, key: UUID, binding: InferenceBinding
    ) -> InferencePermit: ...
    async def settle(
        self, request: GenerationRequest, context: Any, key: UUID, permit: InferencePermit, input_tokens: int, output_tokens: int
    ) -> None: ...
    async def release(self, request: GenerationRequest, context: Any, key: UUID, permit: InferencePermit) -> None: ...
    async def reconcile(self, request: GenerationRequest, context: Any, key: UUID) -> InferenceReceipt: ...
    async def authorize_content(self, request: GenerationContentRecoveryRequest, context: Any, key: UUID) -> None: ...


class GovernedProvider(Protocol):
    def count_prompt(self, binding: InferenceBinding, request: GenerationRequest) -> int: ...
    async def generate(
        self,
        binding: InferenceBinding,
        request: GenerationRequest,
        permit: InferencePermit,
        authorize: Callable[[], Awaitable[None]],
        settle: Callable[[int, int], Awaitable[None]],
    ) -> tuple[str, int, int]: ...


class GenerationRepository(Protocol):
    async def claim(
        self, tenant: str, relationship: UUID, key: UUID, request: GenerationRequest
    ) -> tuple[bool, GenerationResult | None]: ...
    async def save(self, tenant: str, relationship: UUID, key: UUID, result: GenerationResult) -> None: ...
    async def lookup(self, tenant: str, relationship: UUID, key: UUID, request: GenerationRequest) -> GenerationResult | None: ...
    async def begin_dispatch(self, tenant: str, relationship: UUID, key: UUID, request: GenerationRequest) -> bool: ...
    async def release_queue_claim(self, tenant: str, relationship: UUID, key: UUID, request: GenerationRequest) -> None: ...
    async def lookup_retained(
        self, tenant: str, relationship: UUID, key: UUID, request: GenerationRequest
    ) -> tuple[GenerationResult | None, datetime | None]: ...


class GovernedGenerationService:
    def __init__(self, repository: GenerationRepository, owner: GenerationOwner, provider: GovernedProvider) -> None:
        self.repository, self.owner, self.provider = repository, owner, provider

    async def recover_content(
        self, request: GenerationContentRecoveryRequest, context: Any, key: UUID
    ) -> GenerationContentRecoveryResult:
        request.verify_reader(context, key)
        await self.owner.authorize_content(request, context, key)
        original_key = (
            request.generation.batch.batch_id
            if request.generation.batch is not None
            else UUID(str(request.generation.operational_mandate["idempotencyIdentity"]))
        )
        result, retained_at = await self.repository.lookup_retained(
            context.tenant_id, request.relationship_ref, original_key, request.generation
        )
        await self.owner.authorize_content(request, context, key)
        request.verify_reader(context, key)
        return GenerationContentRecoveryResult(
            result=result
            or GenerationResult(
                executionId=request.generation.execution_id,
                requestDigest=request.generation.request_digest,
                state="UNRESOLVED",
                reason="ORIGINAL_RESULT_UNAVAILABLE",
            ),
            retainedAt=retained_at,
        )

    async def _release_recovered(
        self, request: GenerationRequest, context: Any, key: UUID, result: GenerationResult | None
    ) -> GenerationResult | None:
        if result is not None and result.state == "COMPLETED":
            request.verify_binding(context, key, recovery=False)
            binding = await self.owner.resolve(request, context, key)
            if binding.conversation_context is not None:
                binding.conversation_context.verify_request(request)
            operation = request.operational_mandate["conversationOperation"]
            if (
                binding.prompt_digest != operation["promptPolicy"]["digest"]
                or binding.model_policy_digest != operation["modelPolicy"]["digest"]
            ):
                raise ValueError("Stored output no longer has current original-owner authority")
        elif result is None or (result.state == "UNRESOLVED" and result.reason != "GENERATION_QUEUED"):
            receipt = await self.owner.reconcile(request, context, key)
            if receipt.state != "UNRESOLVED":
                if result is not None and result.reservation_id is not None and result.reservation_id != receipt.reservation_id:
                    raise ValueError("Recovered financial receipt changed the original reservation")
                if (
                    result is not None
                    and result.commercial_reservation_id is not None
                    and result.commercial_reservation_id != receipt.commercial_reservation_id
                ):
                    raise ValueError("Recovered commercial receipt changed the original reservation")
                # Financial knowledge does not restore output or authorize another attempt.
                return GenerationResult(
                    executionId=request.execution_id,
                    requestDigest=request.request_digest,
                    state="UNRESOLVED",
                    reason=result.reason if result is not None else "ORIGINAL_RESULT_UNAVAILABLE",
                    reservationId=receipt.reservation_id,
                    commercialReservationId=receipt.commercial_reservation_id,
                    evidenceId=receipt.evidence_id,
                )
        return result

    async def execute(self, request: GenerationRequest, context: Any, key: UUID, *, recovery: bool) -> GenerationResult:
        request.verify_binding(context, key, recovery=recovery)
        if recovery:
            # Claims on recovery are read-only; absence must never initiate inference.
            prior = await self._release_recovered(
                request, context, key, await self.repository.lookup(context.tenant_id, request.relationship_ref, key, request)
            )
            return prior or GenerationResult(
                executionId=request.execution_id,
                requestDigest=request.request_digest,
                state="UNRESOLVED",
                reason="ORIGINAL_RESULT_UNAVAILABLE",
            )
        fresh, prior = await self.repository.claim(context.tenant_id, request.relationship_ref, key, request)
        if not fresh:
            prior = await self._release_recovered(request, context, key, prior)
            return prior or GenerationResult(
                executionId=request.execution_id,
                requestDigest=request.request_digest,
                state="UNRESOLVED",
                reason="ORIGINAL_OUTCOME_UNKNOWN",
            )
        permit: InferencePermit | None = None
        provider_started = False
        reservation_requested = False
        try:
            binding = await self.owner.resolve(request, context, key)
            operation = request.operational_mandate["conversationOperation"]
            if (
                binding.prompt_digest != operation["promptPolicy"]["digest"]
                or binding.prompt_version != operation["promptPolicy"]["version"]
                or binding.model_policy_digest != operation["modelPolicy"]["digest"]
                or binding.expires_at <= datetime.now(timezone.utc)
                or request.input.language not in binding.languages
                or request.operational_mandate["professionalType"] not in binding.domains
                or binding.resolved_plan_tier not in binding.plan_tiers
                or binding.tier not in binding.mandatory_tiers
                or binding.region not in binding.residency_regions
            ):
                raise ValueError("Resolved policy does not admit this agent skill")
            input_tokens = self.provider.count_prompt(binding, request)
            if input_tokens > 8192:
                raise ValueError("Bound tokenizer rejects prompt above 8192 tokens")
            reservation_requested = True
            permit = await self.owner.reserve(request, context, key, binding)
            if permit.binding != binding or permit.expires_at <= datetime.now(timezone.utc):
                raise ValueError("Inference permit changed")
            if not await self.repository.begin_dispatch(context.tenant_id, request.relationship_ref, key, request):
                raise ValueError("Original generation is already claimed")

            async def authorize() -> None:
                request.verify_binding(context, key, recovery=False)
                if await self.owner.resolve(request, context, key) != binding:
                    raise ValueError("Current inference authority changed")
                if permit is None or permit.expires_at <= datetime.now(timezone.utc):
                    raise ValueError("Dispatch permit expired")

            async def settle(reported_input: int, reported_output: int) -> None:
                if permit is None:
                    raise ValueError("Usage has no original permit")
                await self.owner.settle(request, context, key, permit, reported_input, reported_output)

            provider_started = True
            text, reported_input, output_tokens = await self.provider.generate(binding, request, permit, authorize, settle)
            if not text.strip() or "\x00" in text or len(text) > 32000 or reported_input != input_tokens or output_tokens > 2048:
                raise ValueError("Provider output or token usage is outside the admitted bounds")
            await authorize()
            result = GenerationResult(
                executionId=request.execution_id,
                requestDigest=request.request_digest,
                state="COMPLETED",
                text=text,
                inputTokens=reported_input,
                outputTokens=output_tokens,
                reservationId=permit.reservation_id,
                commercialReservationId=permit.commercial_reservation_id,
                evidenceId=permit.evidence_id,
            )
        except (ValueError, OSError, TimeoutError, httpx.HTTPError) as error:
            logger.warning("Governed generation withheld: %s", type(error).__name__)
            if isinstance(error, httpx.HTTPStatusError) and not provider_started and permit is None:
                if error.response.status_code == 503 and error.response.headers.get("X-Inference-State") == "QUEUED":
                    await self.repository.release_queue_claim(context.tenant_id, request.relationship_ref, key, request)
                    return GenerationResult(
                        executionId=request.execution_id,
                        requestDigest=request.request_digest,
                        state="UNRESOLVED",
                        reason="GENERATION_QUEUED",
                    )
            if permit is not None and not provider_started:
                await self.owner.release(request, context, key, permit)
            reservation_unknown = (
                reservation_requested
                and permit is None
                and not (isinstance(error, httpx.HTTPStatusError) and error.response.status_code < 500)
            )
            result = GenerationResult(
                executionId=request.execution_id,
                requestDigest=request.request_digest,
                state="UNRESOLVED" if provider_started or reservation_unknown else "FAILED",
                reason=(
                    "PROVIDER_OUTCOME_UNKNOWN"
                    if provider_started
                    else "RESERVATION_OUTCOME_UNKNOWN"
                    if reservation_unknown
                    else "POLICY_OR_DEPENDENCY_UNAVAILABLE"
                ),
                reservationId=permit.reservation_id if permit is not None else None,
                commercialReservationId=(permit.commercial_reservation_id if permit is not None else None),
            )
        await self.repository.save(context.tenant_id, request.relationship_ref, key, result)
        return result


async def _execute(
    body: GenerationRequest | GenerationContentRecoveryRequest, request: Request, key: UUID, recovery: bool
) -> JSONResponse:
    auth = getattr(request.app.state, "employment_workload_auth", None)
    service = getattr(request.app.state, "conversation_generation_service", None)
    content_read = isinstance(body, GenerationContentRecoveryRequest)
    route = "/internal/v1/conversation-generations" + ("/recover-content" if content_read else "/reconcile" if recovery else "")
    if auth is None or service is None:
        return JSONResponse({"code": "GENERATION_DEPENDENCY_UNAVAILABLE"}, status_code=503)
    try:
        context = auth.authorize(
            request,
            route,
            "recoverConversationGenerationContent"
            if content_read
            else "reconcileConversationGeneration"
            if recovery
            else "generateConversation",
            hashlib.sha256(
                json.dumps(
                    body.model_dump(by_alias=True, mode="json"),
                    sort_keys=True,
                    separators=(",", ":"),
                    ensure_ascii=True,
                    allow_nan=False,
                ).encode()
            ).hexdigest(),
            str(body.relationship_ref),
            str(key),
        )
        if context.purpose != (
            "CONVERSATION_CONTENT_RECOVERY"
            if content_read
            else "CONVERSATION_GENERATION_RECONCILIATION"
            if recovery
            else "CONVERSATION_GENERATION"
        ):
            raise EmploymentAuthError("AIR_EMPLOYMENT_UNAUTHORIZED")
        result = (
            await service.recover_content(body, context, key)
            if content_read
            else await service.execute(body, context, key, recovery=recovery)
        )
        return JSONResponse(result.model_dump(by_alias=True, mode="json"))
    except EmploymentAuthError:
        return JSONResponse({"code": "GENERATION_UNAUTHORIZED"}, status_code=401)
    except EmploymentDispatchStoppedError:
        return JSONResponse({"code": "GENERATION_STOPPED"}, status_code=423)
    except ValueError:
        logger.warning("Generation source or read authority conflicts")
        return JSONResponse({"code": "GENERATION_BINDING_CONFLICT"}, status_code=409)
    except httpx.HTTPStatusError as error:
        logger.warning("Original generation read authority withheld: %s", error.response.status_code)
        status = error.response.status_code if error.response.status_code in {403, 423} else 503
        return JSONResponse({"code": "GENERATION_AUTHORITY_UNAVAILABLE"}, status_code=status)
    except httpx.RequestError:
        logger.warning("Original generation read authority is unavailable")
        return JSONResponse({"code": "GENERATION_AUTHORITY_UNAVAILABLE"}, status_code=503)


@router.post("")
async def generate(
    body: GenerationRequest, request: Request, idempotency_key: UUID = Header(alias="Idempotency-Key")
) -> JSONResponse:
    return await _execute(body, request, idempotency_key, False)


@router.post("/reconcile")
async def reconcile(
    body: GenerationRequest, request: Request, idempotency_key: UUID = Header(alias="Idempotency-Key")
) -> JSONResponse:
    return await _execute(body, request, idempotency_key, True)


@router.post("/recover-content")
async def recover_content(
    body: GenerationContentRecoveryRequest, request: Request, idempotency_key: UUID = Header(alias="Idempotency-Key")
) -> JSONResponse:
    return await _execute(body, request, idempotency_key, True)
