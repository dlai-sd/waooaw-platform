# Implements: architecture/reference/components/conversation-core.md §4 Internal PR Execution and Stream Contract
# constitutional_basis: C-001, C-023, C-025, C-059, C-063, C-076; ADR-015, ADR-018, ADR-031
from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import json
import logging
import os
import time
import uuid
from collections.abc import Mapping
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from enum import StrEnum
from typing import Any, Literal, Protocol, cast

import httpx
from fastapi import APIRouter, Depends, Header, Path, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import ValidationError
from temporalio.client import Client as TemporalClient, WorkflowHandle
from employment_air_gateway import EmploymentAirGateway
from temporalio.exceptions import WorkflowAlreadyStartedError
from temporalio.service import RPCError

from .conversation_models import (
    ExecutionProblemCode,
    ExecutionProblemDetail,
    BatchExecutionReceiptV1,
    ConversationExecutionReconciliationV1,
    OriginalConversationExecutionSourceV1,
    ProfessionalCardProposalV1,
    ProfessionalDeltaV1,
    ProfessionalExecutionEventV1,
    ProfessionalExecutionV1,
    ProfessionalExecutionState,
    ProfessionalHeartbeatV1,
    ProfessionalTerminalEventV1,
    ReconcileConversationExecutionRequestV1,
    StartBatchExecutionRequestV1,
    StartExecutionRequestV1,
)
from workflows.conversation_execution_workflow import (
    CancellationSignal,
    ConversationExecutionInput,
    ConversationExecutionWorkflow,
    ExecutionEventSignal,
)
from workload_identity import DelegatedContext
from workload_identity import ServiceAuthError
from relationship_workspace import authorize_service_request

router = APIRouter(prefix="/api/v1/internal/conversations", tags=["Conversation Execution"])
logger = logging.getLogger(__name__)

SCHEMA_VERSION: Literal["1.0"] = "1.0"
BP_AUDIENCE = "professional-runtime"
BP_ISSUER = "business-platform"
BP_REQUIRED_SCOPE = "conversation:execute"
TEMPORAL_TASK_QUEUE = "conversation-execution-queue"
EXECUTION_ID_NAMESPACE = uuid.UUID("f3e57984-3923-4f89-91bd-32453502471a")
TERMINAL_STATES = frozenset({"COMPLETED", "FAILED", "CANCELLED", "STOPPED", "UNRESOLVED"})
RECONCILIATION_ROUTE = "/api/v1/internal/conversations/{conversationId}/executions/{executionId}/reconcile"
RECONCILIATION_OPERATION = "reconcileConversationExecutionInternal"
RECONCILIATION_PURPOSE = "READ_EXISTING_RUNTIME_RESULT"

ApiResponses = dict[int | str, dict[str, Any]]

START_RESPONSES: ApiResponses = {
    200: {"model": ProfessionalExecutionV1},
    202: {"model": ProfessionalExecutionV1},
    400: {"model": ExecutionProblemDetail},
    401: {"model": ExecutionProblemDetail},
    404: {"model": ExecutionProblemDetail},
    409: {"model": ExecutionProblemDetail},
    423: {"model": ExecutionProblemDetail},
    503: {"model": ExecutionProblemDetail, "headers": {"Retry-After": {"schema": {"type": "string"}}}},
}
BATCH_START_RESPONSES: ApiResponses = {
    **START_RESPONSES,
    200: {"model": BatchExecutionReceiptV1},
    202: {"model": BatchExecutionReceiptV1},
}
STREAM_RESPONSES: ApiResponses = {
    200: {
        "model": ProfessionalExecutionEventV1,
        "content": {"text/event-stream": {}},
        "headers": {"Cache-Control": {"schema": {"type": "string", "const": "no-store"}}},
    },
    400: {"model": ExecutionProblemDetail},
    401: {"model": ExecutionProblemDetail},
    404: {"model": ExecutionProblemDetail},
    410: {"model": ExecutionProblemDetail},
    423: {"model": ExecutionProblemDetail},
    503: {"model": ExecutionProblemDetail, "headers": {"Retry-After": {"schema": {"type": "string"}}}},
}
CANCEL_RESPONSES: ApiResponses = {
    200: {"model": ProfessionalExecutionV1},
    202: {"model": ProfessionalExecutionV1},
    400: {"model": ExecutionProblemDetail},
    401: {"model": ExecutionProblemDetail},
    404: {"model": ExecutionProblemDetail},
    409: {"model": ExecutionProblemDetail},
    423: {"model": ExecutionProblemDetail},
    503: {"model": ExecutionProblemDetail, "headers": {"Retry-After": {"schema": {"type": "string"}}}},
}


@dataclass(frozen=True)
class BPServiceContext:
    contract_id: str
    tenant_id: str
    relationship_id: str
    delegated_actor_id: str
    participant_role: str
    message_id: str | None = None


class ConstitutionalDecision(StrEnum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    STOPPED = "STOPPED"
    STALE = "STALE"


class ConstitutionalGatewayUnavailableError(RuntimeError):
    """The canonical CE client could not complete an authorization decision."""


class ExecutionStoppedDuringDispatchError(RuntimeError):
    """Emergency Stop was observed after durable execution acceptance."""


class ConversationConstitutionalGateway(Protocol):
    async def is_ready(self) -> bool:
        """Return true only when the CE health convention reports SERVING."""
        ...

    async def authorize_execution(
        self,
        context: BPServiceContext,
        conversation_id: uuid.UUID,
        decision_space_version: int,
        request_hash: str,
    ) -> ConstitutionalDecision:
        """Authorize this exact execution identity before Temporal mutation."""
        ...


def _b64decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def _decode_service_assertion(token: str, secret: str) -> dict[str, Any]:
    header_part, payload_part, signature_part = token.split(".")
    signed = f"{header_part}.{payload_part}".encode()
    supplied_signature = _b64decode(signature_part)
    expected_signature = hmac.new(secret.encode(), signed, hashlib.sha256).digest()
    if not hmac.compare_digest(supplied_signature, expected_signature):
        raise ValueError("invalid signature")
    header = json.loads(_b64decode(header_part))
    claims = cast(dict[str, Any], json.loads(_b64decode(payload_part)))
    if header.get("alg") != "HS256" or header.get("typ", "JWT") != "JWT":
        raise ValueError("unsupported assertion header")
    now = int(time.time())
    if int(claims["exp"]) <= now or int(claims.get("nbf", 0)) > now:
        raise ValueError("assertion is not active")
    audience = claims.get("aud")
    if audience != BP_AUDIENCE and (not isinstance(audience, list) or BP_AUDIENCE not in audience):
        raise ValueError("invalid audience")
    if claims.get("iss") != BP_ISSUER:
        raise ValueError("invalid issuer")
    return claims


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def problem_response(
    status_code: int,
    code: ExecutionProblemCode,
    title: str,
    correlation_id: uuid.UUID,
    retry_after_seconds: int | None = None,
) -> JSONResponse:
    problem = ExecutionProblemDetail(
        type=f"https://waooaw.com/problems/{code.value.lower().replace('_', '-')}",
        title=title,
        status=status_code,
        code=code,
        correlationId=correlation_id,
        retryAfterSeconds=retry_after_seconds,
    )
    headers = {"Retry-After": str(retry_after_seconds)} if retry_after_seconds is not None else None
    return JSONResponse(
        status_code=status_code,
        media_type="application/problem+json",
        content=problem.model_dump(by_alias=True, mode="json", exclude_none=True),
        headers=headers,
    )


def _request_hash(body: StartExecutionRequestV1, conversation_id: uuid.UUID, context: BPServiceContext) -> str:
    canonical = {
        "body": body.model_dump(by_alias=True, mode="json"),
        "conversationId": str(conversation_id),
        "contractId": context.contract_id,
        "tenantId": context.tenant_id,
        "relationshipId": context.relationship_id,
        "delegatedActorId": context.delegated_actor_id,
        "participantRole": context.participant_role,
    }
    return hashlib.sha256(json.dumps(canonical, separators=(",", ":"), sort_keys=True).encode()).hexdigest()


def _mandate_digest(body: StartExecutionRequestV1) -> str:
    mandate = body.operational_mandate.model_dump(by_alias=True, mode="json", exclude={"mandate_digest"})
    mandate["deadline"] = body.operational_mandate.deadline.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    canonical = json.dumps(mandate, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode()
    return f"sha256:{hashlib.sha256(canonical).hexdigest()}"


def _batch_request_hash(
    body: StartBatchExecutionRequestV1,
    conversation_id: uuid.UUID,
    context: BPServiceContext,
) -> str:
    canonical = {
        "body": body.model_dump(by_alias=True, mode="json"),
        "conversationId": str(conversation_id),
        "contractId": context.contract_id,
        "tenantId": context.tenant_id,
        "relationshipId": context.relationship_id,
        "delegatedActorId": context.delegated_actor_id,
        "participantRole": context.participant_role,
    }
    return hashlib.sha256(json.dumps(canonical, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode()).hexdigest()


def _batch_body_digest(body: StartBatchExecutionRequestV1) -> str:
    canonical = json.dumps(
        body.model_dump(by_alias=True, mode="json"),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode()
    return f"sha256:{hashlib.sha256(canonical).hexdigest()}"


def _batch_mandates_are_valid(
    body: StartBatchExecutionRequestV1,
    context: BPServiceContext,
) -> bool:
    now = datetime.now(timezone.utc)
    return all(
        hmac.compare_digest(source.operational_mandate.tenant_id, context.tenant_id)
        and hmac.compare_digest(source.operational_mandate.relationship_id, context.relationship_id)
        and hmac.compare_digest(source.operational_mandate.actor_id, context.delegated_actor_id)
        and hmac.compare_digest(source.operational_mandate.actor_role, context.participant_role)
        and source.operational_mandate.idempotency_identity == source.idempotency_key
        and source.operational_mandate.deadline > now
        and source.operational_mandate.decision_space_revision == body.decision_space_version
        and not source.operational_mandate.stopped
        and source.operational_mandate.stop_evidence_ref is None
        for source in body.sources
    )


def _mandate_is_valid(
    body: StartExecutionRequestV1,
    context: BPServiceContext,
    idempotency_key: uuid.UUID,
) -> bool:
    mandate = body.operational_mandate
    return all(
        (
            hmac.compare_digest(mandate.mandate_digest, _mandate_digest(body)),
            hmac.compare_digest(mandate.tenant_id, context.tenant_id),
            hmac.compare_digest(mandate.relationship_id, context.relationship_id),
            hmac.compare_digest(mandate.actor_id, context.delegated_actor_id),
            hmac.compare_digest(mandate.actor_role, context.participant_role),
            mandate.decision_space_revision == body.decision_space_version,
            mandate.idempotency_identity == idempotency_key,
            mandate.deadline > datetime.now(timezone.utc),
            not mandate.stopped,
            mandate.stop_evidence_ref is None,
        )
    )


def _cancellation_hash(
    conversation_id: uuid.UUID,
    execution_id: uuid.UUID,
    context: BPServiceContext,
) -> str:
    canonical = {
        "operation": "cancelConversationExecutionInternal",
        "conversationId": str(conversation_id),
        "executionId": str(execution_id),
        "contractId": context.contract_id,
        "tenantId": context.tenant_id,
        "relationshipId": context.relationship_id,
        "delegatedActorId": context.delegated_actor_id,
        "participantRole": context.participant_role,
    }
    return hashlib.sha256(json.dumps(canonical, separators=(",", ":"), sort_keys=True).encode()).hexdigest()


def _execution_id(context: BPServiceContext, conversation_id: uuid.UUID, key: uuid.UUID) -> uuid.UUID:
    identity = ":".join(
        (
            context.tenant_id,
            context.relationship_id,
            context.delegated_actor_id,
            str(conversation_id),
            str(key),
        )
    )
    return uuid.uuid5(EXECUTION_ID_NAMESPACE, identity)


def _state_is_authorized(
    state: dict[str, Any],
    conversation_id: uuid.UUID,
    execution_id: uuid.UUID,
    context: BPServiceContext,
) -> bool:
    return all(
        (
            state.get("executionId") == str(execution_id),
            state.get("conversationId") == str(conversation_id),
            state.get("tenantId") == context.tenant_id,
            state.get("relationshipId") == context.relationship_id,
            state.get("delegatedActorId") == context.delegated_actor_id,
            state.get("participantRole") == context.participant_role,
            context.message_id is None or state.get("messageId") == context.message_id,
        )
    )


def _execution_response(state: dict[str, Any], replayed: bool) -> ProfessionalExecutionV1:
    return ProfessionalExecutionV1.model_validate(
        {
            "schemaVersion": state["schemaVersion"],
            "executionId": state["executionId"],
            "conversationId": state["conversationId"],
            "messageId": state["messageId"],
            "state": state["state"],
            "partial": state["partial"],
            "completionReason": state.get("completionReason"),
            "replayed": replayed,
            "acceptedAt": state["acceptedAt"],
            "updatedAt": state.get("updatedAt"),
        }
    )


def _employment_proposal_payload(body: StartExecutionRequestV1, context: BPServiceContext) -> dict[str, Any]:
    mandate = body.operational_mandate
    operation = mandate.conversation_operation
    if operation is None or operation.kind != "EMPLOYMENT_CONTRIBUTION_INTERPRETATION":
        raise ValueError("The admitted skill does not declare employment interpretation")
    payload: dict[str, Any] = {
        "schemaVersion": "1.0",
        "protocolVersion": "1.0-candidate",
        "relationshipRef": context.relationship_id,
        "contributionRef": str(body.message_id),
        "agentType": mandate.professional_type,
        "agentVersion": mandate.professional_version,
        "manifestVersion": f"admission-{mandate.admission_revision}",
        "semanticCatalogue": {
            "ref": f"skill:{mandate.skill_id}",
            "version": mandate.skill_version,
            "digest": mandate.input_schema_digest.removeprefix("sha256:"),
        },
        "promptPolicy": {
            "ref": operation.prompt_policy.ref,
            "version": operation.prompt_policy.version,
            "digest": operation.prompt_policy.digest.removeprefix("sha256:"),
        },
        "modelPolicy": {
            "ref": operation.model_policy.ref,
            "version": operation.model_policy.version,
            "digest": operation.model_policy.digest.removeprefix("sha256:"),
        },
        "patchType": operation.patch_type,
        "contribution": {
            "text": body.content.text,
            "locale": body.content.language,
        },
        "boundedContext": None,
    }
    canonical = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode()
    payload["requestDigest"] = hashlib.sha256(canonical).hexdigest()
    return payload


def _generation_payload(
    body: StartExecutionRequestV1 | StartBatchExecutionRequestV1,
    conversation_id: uuid.UUID,
    execution_id: uuid.UUID,
    context: BPServiceContext,
) -> dict[str, Any]:
    if isinstance(body, StartBatchExecutionRequestV1):
        first_mandate = body.sources[0].operational_mandate
        contribution_ref = str(body.batch_id)
        sources = [source.model_dump(by_alias=True, mode="json") for source in body.sources]
        batch_id = body.batch_id
        source_list_digest = body.source_list_digest
    else:
        first_mandate = body.operational_mandate
        contribution_ref = str(body.message_id)
        sources = None
        batch_id = None
        source_list_digest = None
    payload: dict[str, Any] = {
        "schemaVersion": "1.0",
        "relationshipRef": context.relationship_id,
        "conversationId": str(conversation_id),
        "executionId": str(execution_id),
        "contributionRef": contribution_ref,
        "operationalMandate": first_mandate.model_dump(by_alias=True, mode="json", exclude_none=True),
        "input": {"text": body.content.text, "language": body.content.language},
    }
    if sources is not None and batch_id is not None and source_list_digest is not None:
        payload["batch"] = {
            "batchId": str(batch_id),
            "sourceListDigest": source_list_digest,
            "sources": sources,
        }
    payload["requestDigest"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()
    ).hexdigest()
    return payload


async def _dispatch_professional_generation(
    gateway: EmploymentAirGateway,
    handle: WorkflowHandle[Any, Any],
    body: StartExecutionRequestV1 | StartBatchExecutionRequestV1,
    context: BPServiceContext,
    key: uuid.UUID,
    conversation_id: uuid.UUID,
    execution_id: uuid.UUID,
    trusted_context: DelegatedContext,
    reconcile_only: bool,
) -> None:
    expected = _generation_payload(body, conversation_id, execution_id, context)
    dispatch = gateway.reconcile_generation if reconcile_only else gateway.generate
    response = await dispatch(trusted_context, key, expected)
    response.raise_for_status()
    result = response.json()
    if (
        not isinstance(result, dict)
        or result.get("schemaVersion") != "1.0"
        or result.get("executionId") != str(execution_id)
        or result.get("requestDigest") != expected["requestDigest"]
        or set(result)
        - {
            "schemaVersion",
            "executionId",
            "requestDigest",
            "state",
            "text",
            "reason",
            "inputTokens",
            "outputTokens",
            "reservationId",
            "commercialReservationId",
            "evidenceId",
        }
    ):
        raise ValueError("AIR generation result differs from the original agent-skill execution")
    if result.get("state") == "UNRESOLVED":
        if result.get("text") is not None:
            raise ValueError("Unknown generation must not expose professional content")
        if result.get("reason") == "GENERATION_QUEUED" and not reconcile_only:
            raise RuntimeError("Governed generation remains in the durable dispatch queue")
        await handle.signal(
            "AppendConversationExecutionEvent",
            ExecutionEventSignal(
                event_type="reconciliation.required",
                data={"reason": "STATE_CONFLICT"},
                occurred_at=_now_iso(),
                dispatch_result_key=f"generation-reconciliation:{execution_id}",
            ),
        )
        return
    if result.get("state") == "FAILED":
        if result.get("text") is not None or not result.get("reason"):
            raise ValueError("Failed generation has an invalid terminal shape")
        await handle.signal(
            "AppendConversationExecutionEvent",
            ExecutionEventSignal(
                event_type="response.system",
                data={
                    "code": "MODEL_UNAVAILABLE",
                    "text": "The governed professional response was not generated. No professional work was completed. Review the request in the secure portal.",
                },
                occurred_at=_now_iso(),
                dispatch_result_key=f"generation-system:{execution_id}",
            ),
        )
        await handle.signal(
            "AppendConversationExecutionEvent",
            ExecutionEventSignal(
                event_type="execution.failed",
                data={
                    "state": "FAILED",
                    "partial": False,
                    "completionReason": "PARTIAL_FAILURE",
                    "errorCode": "MODEL_UNAVAILABLE",
                },
                occurred_at=_now_iso(),
                dispatch_result_key=f"generation-completion:{execution_id}",
            ),
        )
        return
    text = result.get("text")
    if (
        result.get("state") != "COMPLETED"
        or not isinstance(text, str)
        or not text.strip()
        or "\x00" in text
        or len(text.encode("utf-16-le")) // 2 > 32000
        or result.get("reason") is not None
        or type(result.get("inputTokens")) is not int
        or not 0 <= result["inputTokens"] <= 8192
        or type(result.get("outputTokens")) is not int
        or not 0 <= result["outputTokens"] <= 2048
        or uuid.UUID(str(result.get("reservationId"))).int == 0
        or uuid.UUID(str(result.get("commercialReservationId"))).int == 0
        or uuid.UUID(str(result.get("evidenceId"))).int == 0
        or not (
            _batch_mandates_are_valid(body, context)
            if isinstance(body, StartBatchExecutionRequestV1)
            else _mandate_is_valid(body, context, key)
        )
    ):
        raise ValueError("Generation has no bounded current-authority terminal result")
    for offset in range(0, len(text), 4000):
        await handle.signal(
            "AppendConversationExecutionEvent",
            ExecutionEventSignal(
                event_type="response.delta",
                data={"contentIndex": 0, "appendText": text[offset : offset + 4000], "partial": True},
                occurred_at=_now_iso(),
                dispatch_result_key=f"generation-text:{execution_id}:{offset}",
            ),
        )
    await handle.signal(
        "AppendConversationExecutionEvent",
        ExecutionEventSignal(
            event_type="execution.completed",
            data={"state": "COMPLETED", "partial": False, "completionReason": "COMPLETE"},
            occurred_at=_now_iso(),
            dispatch_result_key=f"generation-completion:{execution_id}",
        ),
    )


async def _dispatch_employment_proposal(
    request: Request,
    temporal: TemporalClient,
    execution_id: uuid.UUID,
    body: StartExecutionRequestV1,
    context: BPServiceContext,
    idempotency_key: uuid.UUID,
    correlation_id: uuid.UUID,
    constitutional_gateway: ConversationConstitutionalGateway,
    conversation_id: uuid.UUID,
    request_hash: str,
    *,
    reconcile_only: bool = False,
) -> None:
    employment_gateway = getattr(request.app.state, "employment_air_gateway", None)
    trusted_context = DelegatedContext(
        schema_version="1.0",
        key_id="bp-service-context",
        issuer_uri="spiffe://waooaw.internal/workload/business-platform",
        target_audience="professional-runtime",
        method="POST",
        route="/api/v1/internal/conversations/{conversationId}/executions",
        operation="startConversationExecution",
        contract_major=1,
        actor_subject=context.delegated_actor_id,
        actor_source="BP_SESSION",
        effective_role=context.participant_role,
        tenant_id=context.tenant_id,
        relationship_id=context.relationship_id,
        purpose="EMPLOYMENT_CONTRIBUTION_INTERPRETATION",
        subject_reference=str(body.message_id),
        request_digest=hashlib.sha256(
            json.dumps(
                body.model_dump(by_alias=True, mode="json"),
                separators=(",", ":"),
                sort_keys=True,
            ).encode()
        ).hexdigest(),
        command_id=str(execution_id),
        idempotency_key=str(idempotency_key),
        expected_versions={
            "decisionSpaceVersion": str(body.decision_space_version),
            "agentVersion": body.operational_mandate.professional_version,
            "manifestVersion": f"admission-{body.operational_mandate.admission_revision}",
        },
        issued_at=0,
        not_before=0,
        expires_at=0,
        envelope_id=str(uuid.UUID(int=0)),
        correlation_id=str(correlation_id),
    )
    handle = temporal.get_workflow_handle(str(execution_id))
    try:
        if not _mandate_is_valid(body, context, idempotency_key):
            raise ValueError("Execution mandate is no longer valid")
        decision = await constitutional_gateway.authorize_execution(
            context, conversation_id, body.decision_space_version, request_hash
        )
        if decision == ConstitutionalDecision.STOPPED:
            await handle.signal("EmergencyStop", _now_iso())
            raise ExecutionStoppedDuringDispatchError
        if decision != ConstitutionalDecision.ALLOW:
            raise ValueError("Execution authorization is no longer valid")
        state = await _query_state(temporal, execution_id)
        if (
            not _state_is_authorized(state, conversation_id, execution_id, context)
            or state.get("messageId") != str(body.message_id)
            or state.get("decisionSpaceVersion") != body.decision_space_version
            or not hmac.compare_digest(str(state.get("requestHash", "")), request_hash)
        ):
            raise ValueError("Execution identity no longer matches")
        if state.get("state") in TERMINAL_STATES:
            return
        if state.get("state") not in {"ACCEPTED", "RUNNING"}:
            raise ValueError("Execution state is not dispatchable")
        if not _mandate_is_valid(body, context, idempotency_key):
            raise ValueError("Execution mandate is no longer valid")
        operation = body.operational_mandate.conversation_operation
        if operation is not None and operation.kind == "PROFESSIONAL_RESPONSE":
            if employment_gateway is None:
                raise RuntimeError("Governed AIR generation gateway unavailable")
            await _dispatch_professional_generation(
                employment_gateway,
                handle,
                body,
                context,
                idempotency_key,
                conversation_id,
                execution_id,
                trusted_context,
                reconcile_only,
            )
            return
        if operation is None:
            if reconcile_only:
                logger.warning("Conversation recovery requires original operation/result reconciliation")
                await handle.signal(
                    "AppendConversationExecutionEvent",
                    ExecutionEventSignal(
                        event_type="reconciliation.required",
                        data={"reason": "STATE_CONFLICT"},
                        occurred_at=_now_iso(),
                        dispatch_result_key=f"employment-proposal:{execution_id}",
                    ),
                )
                return
            code = "OPERATION_UNSUPPORTED" if operation is None else "MODEL_UNAVAILABLE"
            text = (
                "The admitted skill has no supported conversation operation. No professional work "
                "or workspace change was completed. Review the available task in the secure portal."
                if operation is None
                else "The governed professional generation backend is unavailable. No professional work "
                "or workspace change was completed. Review the request in the secure portal."
            )
            logger.warning("Conversation dispatch denied before AIR admission: code=%s", code)
            await handle.signal(
                "AppendConversationExecutionEvent",
                ExecutionEventSignal(
                    event_type="response.system",
                    data={"text": text, "code": code},
                    occurred_at=_now_iso(),
                    dispatch_result_key=f"operation-system:{execution_id}",
                ),
            )
            await handle.signal(
                "AppendConversationExecutionEvent",
                ExecutionEventSignal(
                    event_type="execution.failed",
                    data={"state": "FAILED", "partial": False, "completionReason": "PARTIAL_FAILURE", "errorCode": code},
                    occurred_at=_now_iso(),
                    dispatch_result_key=f"operation-completion:{execution_id}",
                ),
            )
            return
        if employment_gateway is None:
            raise RuntimeError("Employment proposal gateway unavailable")
        expected = _employment_proposal_payload(body, context)
        dispatch = employment_gateway.reconcile if reconcile_only else employment_gateway.propose
        response = await dispatch(
            trusted_context,
            idempotency_key,
            expected,
        )
        response.raise_for_status()
        proposal = response.json()
        if not isinstance(proposal, dict):
            raise ValueError("AIR proposal response is not an object")
        if proposal.get("state") == "PENDING":
            response = await employment_gateway.get(
                trusted_context,
                uuid.UUID(str(proposal["proposalId"])),
            )
            response.raise_for_status()
            proposal = response.json()
        if not isinstance(proposal, dict):
            raise ValueError("AIR proposal response is not an object")
        for field in (
            "schemaVersion",
            "protocolVersion",
            "relationshipRef",
            "contributionRef",
            "agentType",
            "agentVersion",
            "manifestVersion",
            "semanticCatalogue",
            "promptPolicy",
            "modelPolicy",
            "patchType",
            "requestDigest",
        ):
            if proposal.get(field) != expected[field]:
                raise ValueError("AIR proposal binding does not match the execution")
        proposal_id = uuid.UUID(str(proposal["proposalId"]))
        decision = await constitutional_gateway.authorize_execution(
            context, conversation_id, body.decision_space_version, request_hash
        )
        if decision == ConstitutionalDecision.STOPPED:
            await handle.signal("EmergencyStop", _now_iso())
            raise ExecutionStoppedDuringDispatchError
        if decision != ConstitutionalDecision.ALLOW or not _mandate_is_valid(body, context, idempotency_key):
            raise ValueError("Execution authorization expired during interpretation")
        state = await _query_state(temporal, execution_id)
        if state.get("state") in TERMINAL_STATES:
            return
        if not _state_is_authorized(state, conversation_id, execution_id, context):
            raise ValueError("Execution authority changed during interpretation")
        if proposal.get("state") in {"FAILED", "UNREPRESENTABLE"}:
            notices = {
                "MODEL_UNAVAILABLE": "Professional interpretation is currently unavailable. No professional work or workspace change was completed. Please try again later in the secure portal.",
                "MATERIAL_UNCERTAINTY": "I need clarification before a reliable workspace proposal can be made. Review your request in the secure portal; no workspace change was made.",
                "SEMANTIC_PATH_UNREPRESENTABLE": "This request cannot be represented by the current authorized skill. Choose an available task in the secure portal; no workspace change was made.",
                "POLICY_REJECTED": "This request is not permitted by the current policy. Continue in the secure portal to review the authorized options; no workspace change was made.",
                "INTERNAL_FAILURE": "Professional interpretation could not finish. No completed professional result is available; review the request in the secure portal.",
            }
            reason = proposal.get("reasonCode")
            if not isinstance(reason, str) or reason not in notices or proposal.get("operations"):
                raise ValueError("AIR failure response is invalid")
            await handle.signal(
                "AppendConversationExecutionEvent",
                ExecutionEventSignal(
                    event_type="response.system",
                    data={"text": notices[reason], "code": reason},
                    occurred_at=_now_iso(),
                    dispatch_result_key=f"employment-system:{execution_id}",
                ),
            )
            await handle.signal(
                "AppendConversationExecutionEvent",
                ExecutionEventSignal(
                    event_type="execution.failed",
                    data={"state": "FAILED", "partial": False, "completionReason": "PARTIAL_FAILURE", "errorCode": reason},
                    occurred_at=_now_iso(),
                    dispatch_result_key=f"employment-completion:{execution_id}",
                ),
            )
            return
        if proposal.get("state") != "PROPOSED":
            raise ValueError("AIR proposal did not reach a known terminal result")
        operations = proposal.get("operations")
        if (
            not isinstance(operations, list)
            or not 1 <= len(operations) <= 100
            or proposal.get("reasonCode") is not None
            or proposal.get("unresolvedQuestions")
        ):
            raise ValueError("AIR success response contains no reliable proposal")
        for operation in operations:
            if (
                not isinstance(operation, dict)
                or operation.get("op") not in {"ADD", "REPLACE", "REMOVE"}
                or not isinstance(operation.get("semanticPath"), str)
                or not 1 <= len(operation["semanticPath"]) <= 240
            ):
                raise ValueError("AIR proposal operation is invalid")
        await handle.signal(
            "AppendConversationExecutionEvent",
            ExecutionEventSignal(
                event_type="card.proposed",
                data={
                    "schemaVersion": "1.0",
                    "cardType": "DECISION",
                    "cardId": str(proposal_id),
                    "owner": "SHARED",
                    "state": "PROPOSED",
                    "effect": "Review and confirm the proposed employment workspace update.",
                    "data": {"employmentPatchProposal": proposal},
                },
                occurred_at=_now_iso(),
                dispatch_result_key=f"employment-proposal:{execution_id}",
            ),
        )
        await handle.signal(
            "AppendConversationExecutionEvent",
            ExecutionEventSignal(
                event_type="execution.completed",
                data={"state": "COMPLETED", "partial": False, "completionReason": "COMPLETE"},
                occurred_at=_now_iso(),
                dispatch_result_key=f"employment-completion:{execution_id}",
            ),
        )
    except (httpx.HTTPError, KeyError, TypeError, ValueError) as error:
        if isinstance(error, httpx.HTTPStatusError) and error.response.status_code == 423:
            await handle.signal("EmergencyStop", _now_iso())
            raise ExecutionStoppedDuringDispatchError from error
        reconciliation_unknown = False
        if isinstance(error, httpx.HTTPStatusError) and error.response.status_code == 503:
            try:
                problem = error.response.json()
            except ValueError:
                logger.warning("AIR returned an invalid unavailable problem response")
            else:
                reconciliation_unknown = (
                    isinstance(problem, dict) and problem.get("code") == "AIR_EMPLOYMENT_RECONCILIATION_REQUIRED"
                )
        if isinstance(error, httpx.RequestError) or (
            isinstance(error, httpx.HTTPStatusError)
            and (error.response.status_code >= 500 or error.response.status_code == 429)
            and not reconciliation_unknown
        ):
            raise
        await handle.signal(
            "AppendConversationExecutionEvent",
            ExecutionEventSignal(
                event_type="reconciliation.required",
                data={"reason": "STATE_CONFLICT"},
                occurred_at=_now_iso(),
                dispatch_result_key=f"employment-proposal:{execution_id}",
            ),
        )


async def _dispatch_batch_execution(
    request: Request,
    temporal: TemporalClient,
    execution_id: uuid.UUID,
    body: StartBatchExecutionRequestV1,
    context: BPServiceContext,
    idempotency_key: uuid.UUID,
    correlation_id: uuid.UUID,
    constitutional_gateway: ConversationConstitutionalGateway,
    conversation_id: uuid.UUID,
    request_hash: str,
    *,
    reconcile_only: bool = False,
) -> None:
    if not _batch_mandates_are_valid(body, context):
        raise ValueError("Batch source authority is no longer valid")
    first = body.sources[0]
    store = getattr(request.app.state, "relationship_execution_store", None)
    if store is None or not store.is_current_work_item(
        context.tenant_id,
        uuid.UUID(context.relationship_id),
        first.work_item_id,
        first.work_item_revision,
        first.work_item_invocation_id,
        first.operational_mandate.agent_instance_id,
        first.operational_mandate.skill_id,
        first.operational_mandate.skill_version,
    ):
        raise ValueError("PR-owned work item is no longer current")
    decision = await constitutional_gateway.authorize_execution(
        context,
        conversation_id,
        body.decision_space_version,
        request_hash,
    )
    handle = temporal.get_workflow_handle(str(execution_id))
    if decision == ConstitutionalDecision.STOPPED:
        await handle.signal("EmergencyStop", _now_iso())
        raise ExecutionStoppedDuringDispatchError
    if decision != ConstitutionalDecision.ALLOW:
        raise ValueError("Batch execution authorization is no longer valid")
    state = await _query_state(temporal, execution_id)
    if (
        not _state_is_authorized(state, conversation_id, execution_id, context)
        or state.get("batchId") != str(body.batch_id)
        or not hmac.compare_digest(str(state.get("requestHash", "")), request_hash)
        or not hmac.compare_digest(str(state.get("sourceListDigest", "")), body.source_list_digest)
    ):
        raise ValueError("Durable batch execution identity differs")
    if state.get("state") in TERMINAL_STATES:
        return
    if state.get("state") not in {"ACCEPTED", "RUNNING"}:
        raise ValueError("Batch execution is not dispatchable")
    if not _batch_mandates_are_valid(body, context):
        raise ValueError("Batch source authority is no longer valid")
    operation = first.operational_mandate.conversation_operation
    if operation is None or operation.kind != "PROFESSIONAL_RESPONSE":
        raise ValueError("Batch execution requires an admitted professional response")
    employment_gateway = getattr(request.app.state, "employment_air_gateway", None)
    if employment_gateway is None:
        raise RuntimeError("Governed AIR generation gateway unavailable")
    trusted_context = DelegatedContext(
        schema_version="1.0",
        key_id="bp-service-context",
        issuer_uri="spiffe://waooaw.internal/workload/business-platform",
        target_audience="professional-runtime",
        method="POST",
        route="/api/v1/internal/conversations/{conversationId}/batch-executions",
        operation="startConversationBatchExecution",
        contract_major=1,
        actor_subject=context.delegated_actor_id,
        actor_source="BP_SESSION",
        effective_role=context.participant_role,
        tenant_id=context.tenant_id,
        relationship_id=context.relationship_id,
        purpose="PROFESSIONAL_RESPONSE",
        subject_reference=str(body.batch_id),
        request_digest=_batch_body_digest(body).removeprefix("sha256:"),
        command_id=str(execution_id),
        idempotency_key=str(idempotency_key),
        expected_versions={
            "decisionSpaceVersion": str(body.decision_space_version),
            "workItemRevision": str(first.work_item_revision),
            "sourceListDigest": body.source_list_digest,
        },
        issued_at=0,
        not_before=0,
        expires_at=0,
        envelope_id=str(uuid.UUID(int=0)),
        correlation_id=str(correlation_id),
    )
    await _dispatch_professional_generation(
        employment_gateway,
        handle,
        body,
        context,
        idempotency_key,
        conversation_id,
        execution_id,
        trusted_context,
        reconcile_only,
    )


async def get_bp_service_context(
    request: Request,
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> BPServiceContext | None:
    if authorization is None or not authorization.startswith("Bearer "):
        return None
    secret = getattr(request.app.state, "bp_service_jwt_secret", None) or os.getenv("BP_SERVICE_JWT_SECRET")
    if not secret:
        return None
    try:
        claims = _decode_service_assertion(authorization.removeprefix("Bearer ").strip(), str(secret))
        scopes = set(str(claims.get("scope", "")).split())
        if claims.get("sub") != BP_ISSUER or BP_REQUIRED_SCOPE not in scopes:
            return None
        values = (
            str(claims["contract_id"]),
            str(claims["tenant_id"]),
            str(claims["relationship_id"]),
            str(claims["delegated_actor_id"]),
            str(claims["participant_role"]),
        )
        if not all(values):
            return None
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return None
    return BPServiceContext(*values)


async def get_conversation_service_context(request: Request) -> BPServiceContext | None:
    operations = {
        "POST": ("/api/v1/internal/conversations/{conversationId}/executions", "startConversationExecution"),
        "GET": (
            "/api/v1/internal/conversations/{conversationId}/executions/{executionId}/stream",
            "streamConversationExecution",
        ),
        "DELETE": (
            "/api/v1/internal/conversations/{conversationId}/executions/{executionId}",
            "cancelConversationExecutionInternal",
        ),
    }
    if request.method == "POST" and request.url.path.endswith("/batch-executions"):
        route, operation = (
            "/api/v1/internal/conversations/{conversationId}/batch-executions",
            "startConversationBatchExecution",
        )
    else:
        route, operation = operations[request.method]
    try:
        # BP sends its shared canonical representation verbatim; retain its Unicode escaping.
        canonical = await request.body() if request.method == "POST" else b""
        context = await authorize_service_request(
            request,
            route,
            operation,
            None,
            idempotency_key=request.headers.get("Idempotency-Key"),
            request_digest=hashlib.sha256(canonical).hexdigest(),
        )
        body = json.loads(canonical) if request.method == "POST" else None
        conversation_id = str(uuid.UUID(str(request.path_params["conversationId"])))
        decision_ref = context.expected_versions.get("constitutional_decision")
        if (
            context.purpose != operation
            or context.subject_reference != conversation_id
            or not decision_ref
            or not context.effective_role
            or not context.expected_versions.get("message")
            or (request.method != "POST" and context.command_id != str(uuid.UUID(str(request.path_params["executionId"]))))
            or (request.method == "GET" and context.expected_versions.get("cursor") != request.headers.get("Last-Event-ID", ""))
        ):
            raise ServiceAuthError("DELEGATED_CONTEXT_INVALID")
        if request.method == "POST":
            parsed = (
                StartBatchExecutionRequestV1.model_validate(body)
                if operation == "startConversationBatchExecution"
                else StartExecutionRequestV1.model_validate(body)
            )
            message_id = parsed.sources[0].message_id if isinstance(parsed, StartBatchExecutionRequestV1) else parsed.message_id
            decision_reference = (
                parsed.sources[0].operational_mandate.constitutional_decision_ref
                if isinstance(parsed, StartBatchExecutionRequestV1)
                else parsed.operational_mandate.constitutional_decision_ref
            )
            runtime_execution_id = uuid.uuid5(
                EXECUTION_ID_NAMESPACE,
                f"{context.tenant_id}:{context.relationship_id}:{context.actor_subject}:"
                f"{conversation_id}:{context.idempotency_key}",
            )
            if (
                context.command_id != str(runtime_execution_id)
                or context.expected_versions["message"] != str(message_id)
                or decision_ref != decision_reference
            ):
                raise ServiceAuthError("DELEGATED_CONTEXT_INVALID")
        return BPServiceContext(
            decision_ref,
            context.tenant_id,
            context.relationship_id,
            context.actor_subject,
            context.effective_role,
            context.expected_versions["message"],
        )
    except (ServiceAuthError, ValueError, KeyError, TypeError) as exc:
        logger.warning(
            "service_auth decision=deny target=professional-runtime operation=%s reason_class=%s",
            operation,
            exc.code if isinstance(exc, ServiceAuthError) else "DELEGATED_CONTEXT_INVALID",
        )
        return None


def get_temporal_client(request: Request) -> TemporalClient | None:
    temporal = getattr(request.app.state, "temporal_client", None)
    worker_task = getattr(request.app.state, "temporal_worker_task", None)
    if temporal is None or worker_task is None or worker_task.done():
        return None
    return cast(TemporalClient, temporal)


def get_reconciliation_temporal_client(request: Request) -> TemporalClient | None:
    # A retained read needs a Temporal client, not a running inference/activity worker.
    return cast(TemporalClient | None, getattr(request.app.state, "temporal_client", None))


def _reconciliation_permission_active(body: ReconcileConversationExecutionRequestV1, context: DelegatedContext) -> bool:
    now = datetime.now(timezone.utc)
    return (
        now < body.permission_expires_at <= now + timedelta(minutes=5)
        and context.not_before <= int(now.timestamp()) < context.expires_at
    )


async def get_reconciliation_service_context(
    request: Request, body: ReconcileConversationExecutionRequestV1
) -> DelegatedContext | None:
    try:
        key = str(uuid.UUID(request.headers["Idempotency-Key"]))
        context = await authorize_service_request(
            request,
            RECONCILIATION_ROUTE,
            RECONCILIATION_OPERATION,
            None,
            idempotency_key=key,
            request_digest=hashlib.sha256(await request.body()).hexdigest(),
        )
        if not isinstance(context.expected_versions, Mapping):
            raise ServiceAuthError("DELEGATED_CONTEXT_INVALID")
        decision_space = int(context.expected_versions["decision_space"])
        for name, prefix in (
            ("constitutional_decision", "ce-decision:"),
            ("constitutional_evidence", "ce-evidence:"),
        ):
            reference = context.expected_versions[name]
            if (
                not isinstance(reference, str)
                or not reference.startswith(prefix)
                or uuid.UUID(reference.removeprefix(prefix)).int == 0
            ):
                raise ServiceAuthError("DELEGATED_CONTEXT_INVALID")
        if (
            context.purpose != RECONCILIATION_PURPOSE
            or context.effective_role not in {"OWNER", "MANAGER"}
            or context.subject_reference != str(uuid.UUID(str(request.path_params["conversationId"])))
            or context.command_id != str(body.reconciliation_authority_id)
            or context.expected_versions.get("message") != str(body.original_message_id)
            or context.expected_versions.get("source_digest") != body.original_source_digest
            or context.expected_versions.get("projection_version") != str(body.expected_projection_version)
            or context.expected_versions.get("after_sequence") != str(body.after_sequence)
            or decision_space < 1
            or str(decision_space) != context.expected_versions["decision_space"]
            or body.reconciliation_authority_id.int == 0
            or not _reconciliation_permission_active(body, context)
        ):
            raise ServiceAuthError("DELEGATED_CONTEXT_INVALID")
        if any(
            not isinstance(value, str) or uuid.UUID(value).int == 0
            for value in (
                context.tenant_id,
                context.relationship_id,
                context.actor_subject,
            )
        ):
            raise ServiceAuthError("DELEGATED_CONTEXT_INVALID")
        return context
    except (ServiceAuthError, ValueError, KeyError, TypeError) as exc:
        logger.warning(
            "service_auth decision=deny target=professional-runtime operation=%s reason_class=%s",
            RECONCILIATION_OPERATION,
            exc.code if isinstance(exc, ServiceAuthError) else "DELEGATED_CONTEXT_INVALID",
        )
        return None


def _original_source_digest(source: OriginalConversationExecutionSourceV1) -> str:
    canonical = json.dumps(source.model_dump(by_alias=True, mode="json"), separators=(",", ":"), sort_keys=True)
    return f"sha256:{hashlib.sha256(canonical.encode()).hexdigest()}"


def _validate_terminal_snapshot(
    state: dict[str, Any], raw_events: list[Any], source: OriginalConversationExecutionSourceV1
) -> list[ProfessionalExecutionEventV1]:
    if not raw_events or len(raw_events) > 4096:
        raise ValueError("Terminal events are missing or exceed the retained-result bound")
    events = [ProfessionalExecutionEventV1.model_validate(event) for event in raw_events]
    for sequence, event in enumerate(events, 1):
        if (
            event.sequence != sequence
            or event.event_id != f"{source.execution_id}:{sequence}"
            or event.conversation_id != source.conversation_id
            or event.execution_id != source.execution_id
            or event.message_id != source.original_message_id
            or event.event_type == "heartbeat"
            or event.occurred_at.tzinfo is None
        ):
            raise ValueError("Terminal events do not retain the original ordered source")
    terminal_type = {
        "COMPLETED": ("execution.completed", "COMPLETE"),
        "FAILED": ("execution.failed", "PARTIAL_FAILURE"),
        "CANCELLED": ("execution.cancelled", "CANCELLED"),
    }[state["state"]]
    terminal = events[-1]
    if (
        terminal.event_type != terminal_type[0]
        or not isinstance(terminal.data, ProfessionalTerminalEventV1)
        or terminal.data.state != state["state"]
        or terminal.data.completion_reason != terminal_type[1]
        or terminal.data.completion_reason != state.get("completionReason")
        or not isinstance(state.get("partial"), bool)
        or terminal.data.partial != state["partial"]
        or any(
            event.event_type
            in {
                "execution.completed",
                "execution.failed",
                "execution.cancelled",
                "execution.stopped",
            }
            for event in events[:-1]
        )
    ):
        raise ValueError("The durable terminal state and events disagree")
    if state["state"] == "COMPLETED" and not any(
        (isinstance(event.data, ProfessionalDeltaV1) and event.data.append_text.strip())
        or (isinstance(event.data, ProfessionalCardProposalV1) and event.data.effect.strip())
        for event in events[:-1]
    ):
        raise ValueError("A system-only or empty result is not professional completion")
    return events


@router.post(
    "/{conversationId}/executions/{executionId}/reconcile",
    operation_id=RECONCILIATION_OPERATION,
    response_model=ConversationExecutionReconciliationV1,
    responses={
        400: {"model": ExecutionProblemDetail},
        401: {"model": ExecutionProblemDetail},
        404: {"model": ExecutionProblemDetail},
        409: {"model": ExecutionProblemDetail},
        423: {"model": ExecutionProblemDetail},
        503: {"model": ExecutionProblemDetail},
    },
)
async def reconcile_conversation_execution(
    request: Request,
    body: ReconcileConversationExecutionRequestV1,
    conversation_id: uuid.UUID = Path(alias="conversationId"),
    execution_id: uuid.UUID = Path(alias="executionId"),
    idempotency_key: uuid.UUID = Header(alias="Idempotency-Key"),
    correlation_id: uuid.UUID = Header(alias="X-Correlation-Id"),
    context: DelegatedContext | None = Depends(get_reconciliation_service_context),
    temporal: TemporalClient | None = Depends(get_reconciliation_temporal_client),
) -> JSONResponse:
    if context is None or not _reconciliation_permission_active(body, context):
        return problem_response(401, ExecutionProblemCode.NOT_ACCESSIBLE, "Recovery permission is unavailable", correlation_id)
    if temporal is None:
        return problem_response(
            503, ExecutionProblemCode.RUNTIME_UNAVAILABLE, "Retained runtime result is unavailable", correlation_id, 30
        )
    try:
        timeout = min(
            10.0,
            (body.permission_expires_at - datetime.now(timezone.utc)).total_seconds(),
            context.expires_at - time.time(),
        )
        async with asyncio.timeout(timeout):
            snapshot = await temporal.get_workflow_handle(str(execution_id)).query("GetConversationExecutionTerminalSnapshot")
    except (RPCError, TimeoutError) as exc:
        logger.warning("runtime_reconciliation decision=unavailable reason_class=%s", type(exc).__name__)
        return problem_response(
            503, ExecutionProblemCode.RUNTIME_UNAVAILABLE, "Retained runtime result is unavailable", correlation_id, 30
        )
    if not _reconciliation_permission_active(body, context):
        return problem_response(401, ExecutionProblemCode.NOT_ACCESSIBLE, "Recovery permission expired", correlation_id)
    try:
        state = snapshot["state"]
        source = OriginalConversationExecutionSourceV1.model_validate(
            {
                "schemaVersion": state["schemaVersion"],
                "tenantId": state["tenantId"],
                "relationshipId": state["relationshipId"],
                "conversationId": state["conversationId"],
                "executionId": state["executionId"],
                "originalMessageId": state["messageId"],
                "originalActorId": state["delegatedActorId"],
                "mandateId": state["mandateId"],
                "mandateDigest": state["mandateDigest"],
            }
        )
        ProfessionalExecutionState(state["state"])
        if any(
            value.int == 0
            for value in (
                source.tenant_id,
                source.relationship_id,
                source.conversation_id,
                source.execution_id,
                source.original_message_id,
                source.original_actor_id,
                source.mandate_id,
            )
        ):
            raise ValueError("Original source identities cannot be empty")
        if (
            str(source.tenant_id) != context.tenant_id
            or str(source.relationship_id) != context.relationship_id
            or source.conversation_id != conversation_id
            or source.execution_id != execution_id
            or source.original_message_id != body.original_message_id
        ):
            return problem_response(404, ExecutionProblemCode.NOT_ACCESSIBLE, "Execution is not accessible", correlation_id)
        if not hmac.compare_digest(_original_source_digest(source), body.original_source_digest):
            return problem_response(409, ExecutionProblemCode.IDEMPOTENCY_CONFLICT, "Original source conflicts", correlation_id)
        if state["state"] == "STOPPED":
            return problem_response(423, ExecutionProblemCode.STOPPED, "Emergency Stop is active", correlation_id)
        if state["state"] not in {"COMPLETED", "FAILED", "CANCELLED"}:
            snapshot = await _recover_air_terminal_snapshot(
                request,
                temporal,
                snapshot,
                source,
                body,
                context,
                idempotency_key,
            )
            state = snapshot["state"]
        result: dict[str, Any] = {
            "schemaVersion": "1.0",
            "conversationId": str(conversation_id),
            "executionId": str(execution_id),
            "originalMessageId": str(body.original_message_id),
            "originalSourceDigest": body.original_source_digest,
            "reconciliationAuthorityId": str(body.reconciliation_authority_id),
            "state": "UNKNOWN",
            "events": [],
            "nextAction": "OPERATOR_RECONCILIATION_REQUIRED",
        }
        if state["state"] in {"COMPLETED", "FAILED", "CANCELLED"}:
            events = _validate_terminal_snapshot(state, snapshot["events"], source)
            if body.after_sequence > len(events):
                return problem_response(
                    409, ExecutionProblemCode.IDEMPOTENCY_CONFLICT, "Runtime cursor conflicts", correlation_id
                )
            result.update(
                state=state["state"],
                events=[
                    event.model_dump(by_alias=True, mode="json", exclude_none=True) for event in events[body.after_sequence :]
                ],
                originalRequestDigest=f"sha256:{state['requestHash']}",
                nextAction="RECONCILE_CANONICAL_PROJECTION",
            )
            result["resultDigest"] = (
                "sha256:"
                + hashlib.sha256(json.dumps(result, separators=(",", ":"), sort_keys=True, allow_nan=False).encode()).hexdigest()
            )
        response = ConversationExecutionReconciliationV1.model_validate(result)
    except (ValidationError, ValueError, KeyError, TypeError, httpx.HTTPError, RPCError, TimeoutError) as exc:
        logger.warning("runtime_reconciliation decision=unavailable reason_class=%s", type(exc).__name__)
        return problem_response(
            503,
            ExecutionProblemCode.RUNTIME_UNAVAILABLE,
            "Retained runtime result requires operator recovery",
            correlation_id,
            30,
        )
    if not _reconciliation_permission_active(body, context):
        return problem_response(401, ExecutionProblemCode.NOT_ACCESSIBLE, "Recovery permission expired", correlation_id)
    return JSONResponse(
        content=response.model_dump(by_alias=True, mode="json", exclude_none=True),
        headers={"Cache-Control": "no-store"},
    )


async def _recover_air_terminal_snapshot(
    request: Request,
    temporal: TemporalClient,
    snapshot: dict[str, Any],
    source: OriginalConversationExecutionSourceV1,
    permission: ReconcileConversationExecutionRequestV1,
    context: DelegatedContext,
    key: uuid.UUID,
) -> dict[str, Any]:
    gateway = getattr(request.app.state, "employment_air_gateway", None)
    if gateway is None:
        return snapshot
    timeout = min(
        8.0, (permission.permission_expires_at - datetime.now(timezone.utc)).total_seconds(), context.expires_at - time.time()
    )
    async with asyncio.timeout(timeout):
        retained = await temporal.get_workflow_handle(str(source.execution_id)).query("GetConversationGenerationRecoverySource")
        state = retained["state"]
        if state != snapshot["state"]:
            raise ValueError("Runtime state changed during content recovery")
        dispatch = retained.get("dispatch")
        if dispatch is None:
            return snapshot
        original = StartExecutionRequestV1.model_validate(dispatch["body"])
        operation = original.operational_mandate.conversation_operation
        if operation is None or operation.kind != "PROFESSIONAL_RESPONSE":
            return snapshot
        original_key = uuid.UUID(dispatch["idempotencyKey"])
        mandate = original.operational_mandate
        if (
            original.message_id != source.original_message_id
            or mandate.actor_id != str(source.original_actor_id)
            or mandate.tenant_id != str(source.tenant_id)
            or mandate.relationship_id != str(source.relationship_id)
            or mandate.mandate_id != source.mandate_id
            or mandate.mandate_digest != source.mandate_digest
            or mandate.idempotency_identity != original_key
        ):
            raise ValueError("Retained generation source differs from the original source")
        original_context = BPServiceContext(
            contract_id=dispatch["contractId"],
            tenant_id=str(source.tenant_id),
            relationship_id=str(source.relationship_id),
            delegated_actor_id=str(source.original_actor_id),
            participant_role=state["participantRole"],
            message_id=str(source.original_message_id),
        )
        if not hmac.compare_digest(_request_hash(original, source.conversation_id, original_context), state["requestHash"]):
            raise ValueError("Retained generation request differs from the original accepted digest")
        if str(_execution_id(original_context, source.conversation_id, original_key)) != str(source.execution_id):
            raise ValueError("Retained generation execution differs from original idempotency identity")
        payload: dict[str, Any] = {
            "schemaVersion": "1.0",
            "relationshipRef": str(source.relationship_id),
            "conversationId": str(source.conversation_id),
            "executionId": str(source.execution_id),
            "contributionRef": str(source.original_message_id),
            "operationalMandate": mandate.model_dump(by_alias=True, mode="json", exclude_none=True),
            "input": {"text": original.content.text, "language": original.content.language},
        }
        payload["requestDigest"] = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()
        ).hexdigest()
        read_context = replace(context, subject_reference=str(source.original_message_id))
        response = await gateway.recover_generation_content(
            read_context,
            key,
            {
                "relationshipRef": str(source.relationship_id),
                "generation": payload,
                "permission": permission.model_dump(by_alias=True, mode="json"),
            },
        )
        response.raise_for_status()
        receipt = response.json()
        if not isinstance(receipt, dict) or set(receipt) != {"result", "retainedAt"}:
            raise ValueError("AIR recovery lacks its durable result envelope")
        value = receipt["result"]
        if (
            not isinstance(value, dict)
            or value.get("schemaVersion") != "1.0"
            or set(value)
            - {
                "schemaVersion",
                "executionId",
                "requestDigest",
                "state",
                "text",
                "reason",
                "inputTokens",
                "outputTokens",
                "reservationId",
                "commercialReservationId",
                "evidenceId",
            }
            or value.get("executionId") != str(source.execution_id)
            or value.get("requestDigest") != payload["requestDigest"]
        ):
            raise ValueError("Retained AIR result differs from the original request")
        if value.get("state") != "COMPLETED":
            if value.get("text") is not None:
                raise ValueError("Unresolved AIR recovery released content")
            return snapshot
        text = value.get("text")
        if (
            not isinstance(text, str)
            or not text.strip()
            or "\x00" in text
            or len(text.encode("utf-16-le")) // 2 > 32000
            or value.get("reason") is not None
            or type(value.get("inputTokens")) is not int
            or not 0 <= value["inputTokens"] <= 8192
            or type(value.get("outputTokens")) is not int
            or not 0 <= value["outputTokens"] <= 2048
            or uuid.UUID(str(value.get("reservationId"))).int == 0
            or uuid.UUID(str(value.get("commercialReservationId"))).int == 0
            or uuid.UUID(str(value.get("evidenceId"))).int == 0
        ):
            raise ValueError("AIR recovery lacks a complete bounded original result")
        events = [
            ProfessionalExecutionEventV1.model_validate(event).model_dump(by_alias=True, mode="json")
            for event in retained["events"]
        ]
        if (
            not events
            or len(events) > 4086
            or any(
                event["eventType"]
                in {
                    "response.delta",
                    "card.proposed",
                    "execution.completed",
                    "execution.failed",
                    "execution.cancelled",
                    "execution.stopped",
                }
                for event in events
            )
        ):
            raise ValueError("Partial or competing runtime output requires operator recovery")
        retained_at = datetime.fromisoformat(str(receipt["retainedAt"]).replace("Z", "+00:00"))
        if retained_at.tzinfo is None or retained_at > datetime.now(timezone.utc):
            raise ValueError("AIR recovery lacks a valid durable completion timestamp")
        occurred = retained_at.isoformat()

        def append(event_type: str, data: dict[str, Any]) -> None:
            sequence = len(events) + 1
            events.append(
                {
                    "schemaVersion": "1.0",
                    "eventId": f"{source.execution_id}:{sequence}",
                    "eventType": event_type,
                    "conversationId": str(source.conversation_id),
                    "executionId": str(source.execution_id),
                    "messageId": str(source.original_message_id),
                    "sequence": sequence,
                    "occurredAt": occurred,
                    "data": data,
                }
            )

        for offset in range(0, len(text), 4000):
            append("response.delta", {"contentIndex": 0, "appendText": text[offset : offset + 4000], "partial": True})
        append("execution.completed", {"state": "COMPLETED", "partial": False, "completionReason": "COMPLETE"})
        recovered_state = {**state, "state": "COMPLETED", "partial": False, "completionReason": "COMPLETE"}
        _validate_terminal_snapshot(recovered_state, events, source)
        current = await temporal.get_workflow_handle(str(source.execution_id)).query("GetConversationGenerationRecoverySource")
        if current != retained:
            raise ValueError("Retained runtime source changed before content release")
        if not _reconciliation_permission_active(permission, context):
            raise ValueError("Content recovery permission expired")
        return {"state": recovered_state, "events": events}


def get_constitutional_gateway(request: Request) -> ConversationConstitutionalGateway | None:
    return getattr(request.app.state, "conversation_constitutional_gateway", None)


async def _query_state(temporal: TemporalClient, execution_id: uuid.UUID) -> dict[str, Any]:
    return cast(
        dict[str, Any],
        await temporal.get_workflow_handle(str(execution_id)).query("GetConversationExecutionState"),
    )


async def _query_events(temporal: TemporalClient, execution_id: uuid.UUID) -> list[ProfessionalExecutionEventV1]:
    raw_events = await temporal.get_workflow_handle(str(execution_id)).query("GetConversationExecutionEvents")
    return [ProfessionalExecutionEventV1.model_validate(event) for event in raw_events]


def _resume_sequence(last_event_id: str | None, events: list[ProfessionalExecutionEventV1]) -> int:
    if last_event_id is None:
        return 0
    for event in events:
        if hmac.compare_digest(event.event_id, last_event_id):
            return event.sequence
    raise ValueError("cursor is not retained")


def _sse_frame(event: ProfessionalExecutionEventV1, *, durable: bool = True) -> str:
    event_id = f"id: {event.event_id}\n" if durable else ""
    payload = event.model_dump(by_alias=True, mode="json", exclude_none=True)
    return f"{event_id}event: {event.event_type}\ndata: {json.dumps(payload, separators=(',', ':'))}\n\n"


async def stream_workflow_events(
    request: Request,
    temporal: TemporalClient,
    execution_id: uuid.UUID,
    after_sequence: int,
    poll_seconds: float,
    heartbeat_seconds: float,
) -> Any:
    cursor = after_sequence
    last_emit = time.monotonic()
    while not await request.is_disconnected():
        state = await _query_state(temporal, execution_id)
        events = await _query_events(temporal, execution_id)
        for event in events:
            if event.sequence > cursor:
                cursor = event.sequence
                last_emit = time.monotonic()
                yield _sse_frame(event)
        if state["state"] in TERMINAL_STATES and cursor >= len(events):
            return
        if time.monotonic() - last_emit >= heartbeat_seconds and events:
            latest = events[-1]
            now = datetime.now(timezone.utc)
            heartbeat = ProfessionalExecutionEventV1(
                schemaVersion=SCHEMA_VERSION,
                eventId=latest.event_id,
                eventType="heartbeat",
                conversationId=latest.conversation_id,
                executionId=latest.execution_id,
                messageId=latest.message_id,
                sequence=latest.sequence,
                occurredAt=now,
                data=ProfessionalHeartbeatV1(serverTime=now),
            )
            last_emit = time.monotonic()
            yield _sse_frame(heartbeat, durable=False)
        await asyncio.sleep(poll_seconds)


@router.post(
    "/{conversationId}/executions",
    operation_id="startConversationExecution",
    response_model=ProfessionalExecutionV1,
    responses=START_RESPONSES,
)
async def start_conversation_execution(
    body: StartExecutionRequestV1,
    request: Request,
    conversation_id: uuid.UUID = Path(alias="conversationId"),
    idempotency_key: uuid.UUID = Header(alias="Idempotency-Key"),
    correlation_id: uuid.UUID = Header(alias="X-Correlation-Id"),
    context: BPServiceContext | None = Depends(get_conversation_service_context),
    temporal: TemporalClient | None = Depends(get_temporal_client),
    gateway: ConversationConstitutionalGateway | None = Depends(get_constitutional_gateway),
) -> JSONResponse:
    if context is None:
        return problem_response(401, ExecutionProblemCode.NOT_ACCESSIBLE, "Execution is not accessible", correlation_id)
    if not _mandate_is_valid(body, context, idempotency_key):
        return problem_response(409, ExecutionProblemCode.MANDATE_INVALID, "Operational mandate is invalid", correlation_id)
    if body.schema_version != SCHEMA_VERSION or body.content.schema_version != SCHEMA_VERSION:
        return problem_response(
            400, ExecutionProblemCode.SCHEMA_UNSUPPORTED, "Execution schema version is unsupported", correlation_id
        )
    if temporal is None:
        return problem_response(
            503, ExecutionProblemCode.RUNTIME_UNAVAILABLE, "Professional execution is unavailable", correlation_id, 30
        )
    if gateway is None:
        return problem_response(
            503,
            ExecutionProblemCode.CONSTITUTIONAL_UNAVAILABLE,
            "Constitutional execution is unavailable",
            correlation_id,
            30,
        )
    try:
        constitutional_ready = await gateway.is_ready()
    except ConstitutionalGatewayUnavailableError:
        constitutional_ready = False
    if not constitutional_ready:
        return problem_response(
            503,
            ExecutionProblemCode.CONSTITUTIONAL_UNAVAILABLE,
            "Constitutional execution is unavailable",
            correlation_id,
            30,
        )

    request_hash = _request_hash(body, conversation_id, context)
    try:
        decision = await gateway.authorize_execution(
            context,
            conversation_id,
            body.decision_space_version,
            request_hash,
        )
    except ConstitutionalGatewayUnavailableError:
        return problem_response(
            503,
            ExecutionProblemCode.CONSTITUTIONAL_UNAVAILABLE,
            "Constitutional execution is unavailable",
            correlation_id,
            30,
        )
    if decision == ConstitutionalDecision.STOPPED:
        return problem_response(423, ExecutionProblemCode.STOPPED, "Emergency Stop is active", correlation_id)
    if decision == ConstitutionalDecision.STALE:
        return problem_response(409, ExecutionProblemCode.DECISION_SPACE_STALE, "Decision Space version is stale", correlation_id)
    if decision != ConstitutionalDecision.ALLOW:
        return problem_response(404, ExecutionProblemCode.NOT_ACCESSIBLE, "Execution is not accessible", correlation_id)

    execution_id = _execution_id(context, conversation_id, idempotency_key)
    accepted_at = _now_iso()
    workflow_input = ConversationExecutionInput(
        schema_version=SCHEMA_VERSION,
        execution_id=str(execution_id),
        conversation_id=str(conversation_id),
        message_id=str(body.message_id),
        tenant_id=context.tenant_id,
        relationship_id=context.relationship_id,
        delegated_actor_id=context.delegated_actor_id,
        participant_role=context.participant_role,
        mandate_id=str(body.operational_mandate.mandate_id),
        mandate_digest=body.operational_mandate.mandate_digest,
        decision_space_version=body.decision_space_version,
        locale=body.locale,
        content=body.content.model_dump(by_alias=True, mode="json"),
        active_goal_context_id=str(body.active_goal_context_id) if body.active_goal_context_id else None,
        request_hash=request_hash,
        accepted_at=accepted_at,
        dispatch={
            "body": body.model_dump(by_alias=True, mode="json"),
            "contractId": context.contract_id,
            "idempotencyKey": str(idempotency_key),
            "correlationId": str(correlation_id),
            "operationPolicyVersion": "1.0",
        },
    )
    try:
        await temporal.start_workflow(
            ConversationExecutionWorkflow.run,
            workflow_input,
            id=str(execution_id),
            task_queue=TEMPORAL_TASK_QUEUE,
        )
    except WorkflowAlreadyStartedError:
        try:
            state = await _query_state(temporal, execution_id)
        except RPCError:
            return problem_response(
                503, ExecutionProblemCode.RUNTIME_UNAVAILABLE, "Professional execution is unavailable", correlation_id, 30
            )
        if not _state_is_authorized(state, conversation_id, execution_id, context):
            return problem_response(404, ExecutionProblemCode.NOT_ACCESSIBLE, "Execution is not accessible", correlation_id)
        if not hmac.compare_digest(str(state.get("requestHash", "")), request_hash):
            return problem_response(
                409,
                ExecutionProblemCode.IDEMPOTENCY_CONFLICT,
                "Idempotency identity conflicts with the accepted request",
                correlation_id,
            )
        if (
            state.get("legacyDispatchNeedsReconciliation") is True
            or state.get("dispatchNeedsReconciliation") is True
            or state.get("dispatchNeedsCompletion") is True
        ):
            try:
                await _dispatch_employment_proposal(
                    request,
                    temporal,
                    execution_id,
                    body,
                    context,
                    idempotency_key,
                    correlation_id,
                    gateway,
                    conversation_id,
                    request_hash,
                    reconcile_only=True,
                )
                state = await _query_state(temporal, execution_id)
            except ExecutionStoppedDuringDispatchError:
                return problem_response(423, ExecutionProblemCode.STOPPED, "Emergency Stop is active", correlation_id)
            except (RPCError, httpx.HTTPError, ConstitutionalGatewayUnavailableError, RuntimeError):
                return problem_response(
                    503, ExecutionProblemCode.RUNTIME_UNAVAILABLE, "Professional execution is unavailable", correlation_id, 30
                )
        response = _execution_response(state, True)
        return JSONResponse(status_code=200, content=response.model_dump(by_alias=True, mode="json", exclude_none=True))
    except RPCError:
        return problem_response(
            503, ExecutionProblemCode.RUNTIME_UNAVAILABLE, "Professional execution is unavailable", correlation_id, 30
        )

    state = {
        "schemaVersion": SCHEMA_VERSION,
        "executionId": str(execution_id),
        "conversationId": str(conversation_id),
        "messageId": str(body.message_id),
        "state": "ACCEPTED",
        "partial": False,
        "acceptedAt": accepted_at,
        "updatedAt": accepted_at,
    }
    response = _execution_response(state, False)
    return JSONResponse(status_code=202, content=response.model_dump(by_alias=True, mode="json", exclude_none=True))


@router.post(
    "/{conversationId}/batch-executions",
    operation_id="startConversationBatchExecution",
    response_model=BatchExecutionReceiptV1,
    responses=BATCH_START_RESPONSES,
)
async def start_conversation_batch_execution(
    body: StartBatchExecutionRequestV1,
    request: Request,
    conversation_id: uuid.UUID = Path(alias="conversationId"),
    idempotency_key: uuid.UUID = Header(alias="Idempotency-Key"),
    correlation_id: uuid.UUID = Header(alias="X-Correlation-Id"),
    context: BPServiceContext | None = Depends(get_conversation_service_context),
    temporal: TemporalClient | None = Depends(get_temporal_client),
    gateway: ConversationConstitutionalGateway | None = Depends(get_constitutional_gateway),
) -> JSONResponse:
    if context is None:
        return problem_response(
            401,
            ExecutionProblemCode.NOT_ACCESSIBLE,
            "Execution is not accessible",
            correlation_id,
        )
    if body.batch_id != idempotency_key or not _batch_mandates_are_valid(body, context):
        return problem_response(
            409,
            ExecutionProblemCode.MANDATE_INVALID,
            "Batch source authority is invalid",
            correlation_id,
        )
    if temporal is None or gateway is None:
        return problem_response(
            503,
            ExecutionProblemCode.RUNTIME_UNAVAILABLE,
            "Professional execution is unavailable",
            correlation_id,
            30,
        )
    first = body.sources[0]
    store = getattr(request.app.state, "relationship_execution_store", None)
    if store is None or not store.is_current_work_item(
        context.tenant_id,
        uuid.UUID(context.relationship_id),
        first.work_item_id,
        first.work_item_revision,
        first.work_item_invocation_id,
        first.operational_mandate.agent_instance_id,
        first.operational_mandate.skill_id,
        first.operational_mandate.skill_version,
    ):
        return problem_response(
            409,
            ExecutionProblemCode.MANDATE_INVALID,
            "PR-owned work item is stale or unavailable",
            correlation_id,
        )
    try:
        ready = await gateway.is_ready()
        decision = (
            await gateway.authorize_execution(
                context,
                conversation_id,
                body.decision_space_version,
                _batch_request_hash(body, conversation_id, context),
            )
            if ready
            else None
        )
    except ConstitutionalGatewayUnavailableError:
        decision = None
    if decision == ConstitutionalDecision.STOPPED:
        return problem_response(423, ExecutionProblemCode.STOPPED, "Emergency Stop is active", correlation_id)
    if decision != ConstitutionalDecision.ALLOW:
        return problem_response(
            503,
            ExecutionProblemCode.CONSTITUTIONAL_UNAVAILABLE,
            "Constitutional execution is unavailable",
            correlation_id,
            30,
        )

    request_hash = _batch_request_hash(body, conversation_id, context)
    execution_id = _execution_id(context, conversation_id, idempotency_key)
    accepted_at = _now_iso()
    workflow_input = ConversationExecutionInput(
        schema_version=SCHEMA_VERSION,
        execution_id=str(execution_id),
        conversation_id=str(conversation_id),
        message_id=str(first.message_id),
        tenant_id=context.tenant_id,
        relationship_id=context.relationship_id,
        delegated_actor_id=context.delegated_actor_id,
        participant_role=context.participant_role,
        mandate_id=str(first.operational_mandate.mandate_id),
        mandate_digest=first.operational_mandate.mandate_digest,
        decision_space_version=body.decision_space_version,
        locale=body.locale,
        content=body.content.model_dump(by_alias=True, mode="json"),
        active_goal_context_id=None,
        request_hash=request_hash,
        accepted_at=accepted_at,
        dispatch={
            "kind": "batch",
            "body": body.model_dump(by_alias=True, mode="json"),
            "contractId": context.contract_id,
            "idempotencyKey": str(idempotency_key),
            "correlationId": str(correlation_id),
            "operationPolicyVersion": "1.0",
        },
        batch_id=str(body.batch_id),
        source_list_digest=body.source_list_digest,
    )
    replayed = False
    try:
        await temporal.start_workflow(
            ConversationExecutionWorkflow.run,
            workflow_input,
            id=str(execution_id),
            task_queue=TEMPORAL_TASK_QUEUE,
        )
    except WorkflowAlreadyStartedError:
        replayed = True
        try:
            state = await _query_state(temporal, execution_id)
        except RPCError:
            return problem_response(
                503,
                ExecutionProblemCode.RUNTIME_UNAVAILABLE,
                "Professional execution is unavailable",
                correlation_id,
                30,
            )
        if (
            not _state_is_authorized(state, conversation_id, execution_id, context)
            or state.get("batchId") != str(body.batch_id)
            or not hmac.compare_digest(str(state.get("requestHash", "")), request_hash)
            or not hmac.compare_digest(str(state.get("sourceListDigest", "")), body.source_list_digest)
        ):
            return problem_response(
                409,
                ExecutionProblemCode.IDEMPOTENCY_CONFLICT,
                "Batch identity conflicts with the accepted request",
                correlation_id,
            )
        accepted_at = str(state["acceptedAt"])
    except RPCError:
        return problem_response(
            503,
            ExecutionProblemCode.RUNTIME_UNAVAILABLE,
            "Professional execution is unavailable",
            correlation_id,
            30,
        )
    receipt = BatchExecutionReceiptV1(
        schemaVersion=SCHEMA_VERSION,
        batchId=body.batch_id,
        executionId=execution_id,
        conversationId=conversation_id,
        sourceListDigest=body.source_list_digest,
        requestDigest=f"sha256:{hashlib.sha256(await request.body()).hexdigest()}",
        state="ACCEPTED",
        replayed=replayed,
        acceptedAt=datetime.fromisoformat(accepted_at.replace("Z", "+00:00")),
    )
    return JSONResponse(
        status_code=200 if replayed else 202,
        content=receipt.model_dump(by_alias=True, mode="json"),
    )


@router.get(
    "/{conversationId}/executions/{executionId}/stream",
    operation_id="streamConversationExecution",
    response_model=None,
    responses=STREAM_RESPONSES,
)
async def stream_conversation_execution(
    request: Request,
    conversation_id: uuid.UUID = Path(alias="conversationId"),
    execution_id: uuid.UUID = Path(alias="executionId"),
    correlation_id: uuid.UUID = Header(alias="X-Correlation-Id"),
    last_event_id: str | None = Header(default=None, alias="Last-Event-ID"),
    context: BPServiceContext | None = Depends(get_conversation_service_context),
    temporal: TemporalClient | None = Depends(get_temporal_client),
    gateway: ConversationConstitutionalGateway | None = Depends(get_constitutional_gateway),
) -> JSONResponse | StreamingResponse:
    if context is None:
        return problem_response(401, ExecutionProblemCode.NOT_ACCESSIBLE, "Execution is not accessible", correlation_id)
    if temporal is None:
        return problem_response(
            503, ExecutionProblemCode.RUNTIME_UNAVAILABLE, "Professional execution is unavailable", correlation_id, 30
        )
    try:
        state = await _query_state(temporal, execution_id)
        events = await _query_events(temporal, execution_id)
    except (RPCError, ValidationError):
        return problem_response(404, ExecutionProblemCode.NOT_ACCESSIBLE, "Execution is not accessible", correlation_id)
    if not _state_is_authorized(state, conversation_id, execution_id, context):
        return problem_response(404, ExecutionProblemCode.NOT_ACCESSIBLE, "Execution is not accessible", correlation_id)
    if state["state"] == "STOPPED":
        return problem_response(423, ExecutionProblemCode.STOPPED, "Emergency Stop is active", correlation_id)
    if gateway is None:
        return problem_response(
            503,
            ExecutionProblemCode.CONSTITUTIONAL_UNAVAILABLE,
            "Constitutional execution is unavailable",
            correlation_id,
            30,
        )
    try:
        constitutional_ready = await gateway.is_ready()
        decision = (
            await gateway.authorize_execution(
                context,
                conversation_id,
                int(state["decisionSpaceVersion"]),
                str(state["requestHash"]),
            )
            if constitutional_ready
            else None
        )
    except (ConstitutionalGatewayUnavailableError, KeyError, TypeError, ValueError):
        decision = None
    if decision is None:
        return problem_response(
            503,
            ExecutionProblemCode.CONSTITUTIONAL_UNAVAILABLE,
            "Constitutional execution is unavailable",
            correlation_id,
            30,
        )
    if decision == ConstitutionalDecision.STOPPED:
        return problem_response(423, ExecutionProblemCode.STOPPED, "Emergency Stop is active", correlation_id)
    if decision == ConstitutionalDecision.STALE:
        return problem_response(409, ExecutionProblemCode.DECISION_SPACE_STALE, "Decision Space version is stale", correlation_id)
    if decision != ConstitutionalDecision.ALLOW:
        return problem_response(404, ExecutionProblemCode.NOT_ACCESSIBLE, "Execution is not accessible", correlation_id)
    try:
        after_sequence = _resume_sequence(last_event_id, events)
    except ValueError:
        return problem_response(
            410, ExecutionProblemCode.CURSOR_EXPIRED, "Execution cursor requires reconciliation", correlation_id
        )
    poll_seconds = float(getattr(request.app.state, "conversation_stream_poll_seconds", 0.25))
    heartbeat_seconds = float(getattr(request.app.state, "conversation_stream_heartbeat_seconds", 15.0))
    return StreamingResponse(
        stream_workflow_events(request, temporal, execution_id, after_sequence, poll_seconds, heartbeat_seconds),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
    )


@router.delete(
    "/{conversationId}/executions/{executionId}",
    operation_id="cancelConversationExecutionInternal",
    response_model=ProfessionalExecutionV1,
    responses=CANCEL_RESPONSES,
)
async def cancel_conversation_execution(
    conversation_id: uuid.UUID = Path(alias="conversationId"),
    execution_id: uuid.UUID = Path(alias="executionId"),
    idempotency_key: uuid.UUID = Header(alias="Idempotency-Key"),
    correlation_id: uuid.UUID = Header(alias="X-Correlation-Id"),
    context: BPServiceContext | None = Depends(get_conversation_service_context),
    temporal: TemporalClient | None = Depends(get_temporal_client),
) -> JSONResponse:
    if context is None:
        return problem_response(401, ExecutionProblemCode.NOT_ACCESSIBLE, "Execution is not accessible", correlation_id)
    if temporal is None:
        return problem_response(
            503, ExecutionProblemCode.RUNTIME_UNAVAILABLE, "Professional execution is unavailable", correlation_id, 30
        )
    handle = temporal.get_workflow_handle(str(execution_id))
    try:
        state = await handle.query("GetConversationExecutionState")
    except RPCError:
        return problem_response(404, ExecutionProblemCode.NOT_ACCESSIBLE, "Execution is not accessible", correlation_id)
    if not _state_is_authorized(state, conversation_id, execution_id, context):
        return problem_response(404, ExecutionProblemCode.NOT_ACCESSIBLE, "Execution is not accessible", correlation_id)
    if state["state"] == "STOPPED":
        return problem_response(423, ExecutionProblemCode.STOPPED, "Emergency Stop is active", correlation_id)

    request_hash = _cancellation_hash(conversation_id, execution_id, context)
    prior_hash = dict(state.get("cancellationRequests", {})).get(str(idempotency_key))
    if prior_hash is not None and not hmac.compare_digest(str(prior_hash), request_hash):
        return problem_response(
            409,
            ExecutionProblemCode.IDEMPOTENCY_CONFLICT,
            "Idempotency identity conflicts with the accepted request",
            correlation_id,
        )
    if prior_hash is not None or state["state"] in TERMINAL_STATES:
        response = _execution_response(state, True)
        return JSONResponse(status_code=200, content=response.model_dump(by_alias=True, mode="json", exclude_none=True))
    try:
        await handle.signal(
            "CancelConversationExecution",
            CancellationSignal(str(idempotency_key), request_hash, _now_iso()),
        )
        updated_state = await handle.query("GetConversationExecutionState")
    except RPCError:
        return problem_response(
            503, ExecutionProblemCode.RUNTIME_UNAVAILABLE, "Professional execution is unavailable", correlation_id, 30
        )
    if updated_state["state"] == "STOPPED":
        return problem_response(423, ExecutionProblemCode.STOPPED, "Emergency Stop is active", correlation_id)
    response = _execution_response(updated_state, False)
    return JSONResponse(status_code=202, content=response.model_dump(by_alias=True, mode="json", exclude_none=True))
