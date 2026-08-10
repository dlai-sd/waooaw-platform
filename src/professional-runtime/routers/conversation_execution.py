# Implements: architecture/reference/components/conversation-core.md §4 Internal PR Execution and Stream Contract
# constitutional_basis: C-001, C-023, C-025, C-059, C-063, C-076; ADR-015, ADR-018, ADR-031
from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import json
import os
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any, Protocol

from fastapi import APIRouter, Depends, Header, Path, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import ValidationError
from temporalio.client import Client as TemporalClient
from temporalio.exceptions import WorkflowAlreadyStartedError
from temporalio.service import RPCError

from routers.conversation_models import (
    ExecutionProblemCode,
    ExecutionProblemDetail,
    ProfessionalExecutionEventV1,
    ProfessionalExecutionV1,
    ProfessionalHeartbeatV1,
    StartExecutionRequestV1,
)
from workflows.conversation_execution_workflow import (
    CancellationSignal,
    ConversationExecutionInput,
    ConversationExecutionWorkflow,
)

router = APIRouter(prefix="/api/v1/internal/conversations", tags=["Conversation Execution"])

SCHEMA_VERSION = "1.0"
BP_AUDIENCE = "professional-runtime"
BP_ISSUER = "business-platform"
BP_REQUIRED_SCOPE = "conversation:execute"
TEMPORAL_TASK_QUEUE = "conversation-execution-queue"
EXECUTION_ID_NAMESPACE = uuid.UUID("f3e57984-3923-4f89-91bd-32453502471a")
TERMINAL_STATES = frozenset({"COMPLETED", "FAILED", "CANCELLED", "STOPPED", "UNRESOLVED"})

START_RESPONSES: dict[int, dict[str, Any]] = {
    200: {"model": ProfessionalExecutionV1},
    202: {"model": ProfessionalExecutionV1},
    400: {"model": ExecutionProblemDetail},
    401: {"model": ExecutionProblemDetail},
    404: {"model": ExecutionProblemDetail},
    409: {"model": ExecutionProblemDetail},
    423: {"model": ExecutionProblemDetail},
    503: {"model": ExecutionProblemDetail, "headers": {"Retry-After": {"schema": {"type": "string"}}}},
}
STREAM_RESPONSES: dict[int, dict[str, Any]] = {
    200: {
        "model": ProfessionalExecutionEventV1,
        "content": {"text/event-stream": {}},
        "headers": {"Cache-Control": {"schema": {"type": "string", "const": "no-store"}}},
    },
    401: {"model": ExecutionProblemDetail},
    404: {"model": ExecutionProblemDetail},
    410: {"model": ExecutionProblemDetail},
    423: {"model": ExecutionProblemDetail},
    503: {"model": ExecutionProblemDetail, "headers": {"Retry-After": {"schema": {"type": "string"}}}},
}
CANCEL_RESPONSES: dict[int, dict[str, Any]] = {
    200: {"model": ProfessionalExecutionV1},
    202: {"model": ProfessionalExecutionV1},
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


class ConstitutionalDecision(StrEnum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    STOPPED = "STOPPED"
    STALE = "STALE"


class ConstitutionalGatewayUnavailableError(RuntimeError):
    """The canonical CE client could not complete an authorization decision."""


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
    claims = json.loads(_b64decode(payload_part))
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


def get_temporal_client(request: Request) -> TemporalClient | None:
    temporal = getattr(request.app.state, "temporal_client", None)
    worker_task = getattr(request.app.state, "temporal_worker_task", None)
    if temporal is None or worker_task is None or worker_task.done():
        return None
    return temporal


def get_constitutional_gateway(request: Request) -> ConversationConstitutionalGateway | None:
    return getattr(request.app.state, "conversation_constitutional_gateway", None)


async def _query_state(temporal: TemporalClient, execution_id: uuid.UUID) -> dict[str, Any]:
    return await temporal.get_workflow_handle(str(execution_id)).query("GetConversationExecutionState")


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
    conversation_id: uuid.UUID = Path(alias="conversationId"),
    idempotency_key: uuid.UUID = Header(alias="Idempotency-Key"),
    correlation_id: uuid.UUID = Header(alias="X-Correlation-Id"),
    context: BPServiceContext | None = Depends(get_bp_service_context),
    temporal: TemporalClient | None = Depends(get_temporal_client),
    gateway: ConversationConstitutionalGateway | None = Depends(get_constitutional_gateway),
) -> JSONResponse:
    if context is None:
        return problem_response(401, ExecutionProblemCode.NOT_ACCESSIBLE, "Execution is not accessible", correlation_id)
    if body.schema_version != SCHEMA_VERSION or body.content.schema_version != SCHEMA_VERSION:
        return problem_response(
            400, ExecutionProblemCode.SCHEMA_UNSUPPORTED, "Execution schema version is unsupported", correlation_id
        )
    if temporal is None:
        return problem_response(
            503, ExecutionProblemCode.RUNTIME_UNAVAILABLE, "Professional execution is unavailable", correlation_id, 30
        )
    try:
        constitutional_ready = gateway is not None and await gateway.is_ready()
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
        decision_space_version=body.decision_space_version,
        locale=body.locale,
        content=body.content.model_dump(by_alias=True, mode="json"),
        active_goal_context_id=str(body.active_goal_context_id) if body.active_goal_context_id else None,
        request_hash=request_hash,
        accepted_at=accepted_at,
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
    context: BPServiceContext | None = Depends(get_bp_service_context),
    temporal: TemporalClient | None = Depends(get_temporal_client),
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
    context: BPServiceContext | None = Depends(get_bp_service_context),
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
