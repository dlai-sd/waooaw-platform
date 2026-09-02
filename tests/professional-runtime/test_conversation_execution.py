# Implements: architecture/reference/components/conversation-core.md §9 F3 Acceptance Mapping
# constitutional_basis: C-001, C-023, C-059, C-063, C-076
from __future__ import annotations

import asyncio
import base64
import copy
import hashlib
import hmac
import json
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any, ClassVar
from unittest.mock import AsyncMock, MagicMock

import grpc
import pytest
import yaml
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from fastapi.exceptions import RequestValidationError
from starlette.testclient import TestClient, WebSocketDenialResponse
from temporalio.exceptions import WorkflowAlreadyStartedError

import professional_runtime_main as main_module
from constitutional_gateway import EmergencyStopResult, GrpcConversationConstitutionalGateway
from professional_runtime_main import app, lifespan, validation_error
from routers.conversation_execution import (
    BPServiceContext,
    ConstitutionalDecision,
    ConstitutionalGatewayUnavailableError,
    ExecutionProblemCode,
    _resume_sequence,
    stream_workflow_events,
)
from routers.emergency_stop import EmergencyStopAuthority, KeycloakJWTValidator, emergency_stop_websocket
from routers.conversation_models import ProfessionalExecutionEventV1
from workflows import conversation_execution_workflow as workflow_module
from workflows.conversation_execution_workflow import (
    CancellationSignal,
    ConversationExecutionInput,
    ConversationExecutionWorkflow,
    ExecutionEventSignal,
)

SECRET = "bp-service-test-secret"


class FakeConstitutionalGateway:
    def __init__(
        self,
        *,
        ready: bool = True,
        decision: ConstitutionalDecision = ConstitutionalDecision.ALLOW,
    ) -> None:
        self.ready = ready
        self.decision = decision
        self.authorizations: list[dict[str, Any]] = []

    async def is_ready(self) -> bool:
        return self.ready

    async def authorize_execution(
        self,
        context: Any,
        conversation_id: uuid.UUID,
        decision_space_version: int,
        request_hash: str,
    ) -> ConstitutionalDecision:
        self.authorizations.append(
            {
                "context": context,
                "conversation_id": conversation_id,
                "decision_space_version": decision_space_version,
                "request_hash": request_hash,
            }
        )
        return self.decision


class FakeEmergencyStopJWTValidator:
    def __init__(self, *, valid: bool = True) -> None:
        self.valid = valid

    async def validate(self, _token: str) -> EmergencyStopAuthority:
        if not self.valid:
            raise ValueError("invalid token")
        return EmergencyStopAuthority("tenant-a", "customer-a", "contract-a")


class FakeEmergencyStopGateway(FakeConstitutionalGateway):
    def __init__(self, *, failure: bool = False) -> None:
        super().__init__()
        self.failure = failure
        self.stop_requests: list[dict[str, Any]] = []

    async def trigger_emergency_stop(self, **request: Any) -> EmergencyStopResult:
        self.stop_requests.append(request)
        if self.failure:
            raise ConstitutionalGatewayUnavailableError
        return EmergencyStopResult(
            emergency_stop_record_id="EMERGENCY_STOP:11111111-1111-1111-1111-111111111111",
            affected_sessions=("22222222-2222-2222-2222-222222222222",),
            recorded_at="2026-08-10T01:02:03.456000Z",
        )


class FakeWorkflowHandle:
    def __init__(self, workflow_input: ConversationExecutionInput) -> None:
        self.workflow_input = workflow_input
        self.signals: list[tuple[str, Any]] = []
        self.state = {
            "schemaVersion": workflow_input.schema_version,
            "executionId": workflow_input.execution_id,
            "conversationId": workflow_input.conversation_id,
            "messageId": workflow_input.message_id,
            "tenantId": workflow_input.tenant_id,
            "relationshipId": workflow_input.relationship_id,
            "delegatedActorId": workflow_input.delegated_actor_id,
            "participantRole": workflow_input.participant_role,
            "decisionSpaceVersion": workflow_input.decision_space_version,
            "state": "ACCEPTED",
            "partial": False,
            "completionReason": None,
            "requestHash": workflow_input.request_hash,
            "acceptedAt": workflow_input.accepted_at,
            "updatedAt": workflow_input.accepted_at,
            "cancellationRequests": {},
        }
        self.events = [self._event("execution.accepted", {"serverTime": workflow_input.accepted_at})]

    def _event(self, event_type: str, data: dict[str, Any]) -> dict[str, Any]:
        sequence = len(getattr(self, "events", [])) + 1
        occurred_at = datetime.now(timezone.utc).isoformat()
        return {
            "schemaVersion": "1.0",
            "eventId": f"{self.workflow_input.execution_id}:{sequence}",
            "eventType": event_type,
            "conversationId": self.workflow_input.conversation_id,
            "executionId": self.workflow_input.execution_id,
            "messageId": self.workflow_input.message_id,
            "sequence": sequence,
            "occurredAt": occurred_at,
            "data": data,
        }

    async def query(self, query_name: str) -> Any:
        if query_name == "GetConversationExecutionState":
            return copy.deepcopy(self.state)
        if query_name == "GetConversationExecutionEvents":
            return copy.deepcopy(self.events)
        raise AssertionError(f"Unexpected query: {query_name}")

    async def signal(self, signal_name: str, payload: Any = None) -> None:
        self.signals.append((signal_name, payload))
        if signal_name == "AppendConversationExecutionEvent":
            self.events.append(self._event(payload.event_type, payload.data))
            return
        if signal_name == "EmergencyStop":
            self.state.update(
                state="STOPPED",
                partial=any(event["eventType"] == "response.delta" for event in self.events),
                completionReason="EMERGENCY_STOPPED",
                updatedAt=str(payload or datetime.now(timezone.utc).isoformat()),
            )
            self.events.append(
                self._event(
                    "execution.stopped",
                    {
                        "state": "STOPPED",
                        "partial": self.state["partial"],
                        "completionReason": "EMERGENCY_STOPPED",
                    },
                )
            )
            return
        if signal_name == "CancelConversationExecution":
            key = payload.idempotency_key
            self.state["cancellationRequests"][key] = payload.request_hash
            if self.state["state"] != "STOPPED":
                partial = any(event["eventType"] == "response.delta" for event in self.events)
                self.state.update(
                    state="CANCELLED",
                    partial=partial,
                    completionReason="CANCELLED",
                    updatedAt=payload.requested_at,
                )
                self.events.append(
                    self._event(
                        "execution.cancelled",
                        {"state": "CANCELLED", "partial": partial, "completionReason": "CANCELLED"},
                    )
                )


class FakeTemporalClient:
    def __init__(self) -> None:
        self.started: list[dict[str, Any]] = []
        self.handles: dict[str, FakeWorkflowHandle] = {}
        self.service_client = SimpleNamespace(check_health=AsyncMock(return_value=True))

    async def start_workflow(
        self,
        workflow: Any,
        workflow_input: ConversationExecutionInput,
        *,
        id: str,
        task_queue: str,
    ) -> FakeWorkflowHandle:
        if id in self.handles:
            raise WorkflowAlreadyStartedError(id, "ConversationExecutionWorkflow")
        handle = FakeWorkflowHandle(workflow_input)
        self.handles[id] = handle
        self.started.append({"workflow": workflow, "input": workflow_input, "id": id, "task_queue": task_queue})
        return handle

    def get_workflow_handle(self, workflow_id: str) -> FakeWorkflowHandle:
        return self.handles[workflow_id]


class ConnectedRequest:
    async def is_disconnected(self) -> bool:
        return False


def _encode_segment(value: dict[str, Any]) -> str:
    raw = json.dumps(value, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _encode_bytes(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode().rstrip("=")


def _service_token(**overrides: Any) -> str:
    claims: dict[str, Any] = {
        "iss": "business-platform",
        "sub": "business-platform",
        "aud": "professional-runtime",
        "exp": int(time.time()) + 300,
        "scope": "conversation:execute",
        "contract_id": "contract-a",
        "tenant_id": "tenant-a",
        "relationship_id": "relationship-a",
        "delegated_actor_id": "participant-a",
        "participant_role": "CUSTOMER",
    }
    claims.update(overrides)
    header = _encode_segment({"alg": "HS256", "typ": "JWT"})
    payload = _encode_segment(claims)
    signed = f"{header}.{payload}".encode()
    signature = base64.urlsafe_b64encode(hmac.new(SECRET.encode(), signed, hashlib.sha256).digest()).decode().rstrip("=")
    return f"{header}.{payload}.{signature}"


def _headers(token: str | None = None, key: uuid.UUID | None = None) -> dict[str, str]:
    headers = {"X-Correlation-Id": str(uuid.uuid4()), "Idempotency-Key": str(key or uuid.uuid4())}
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _body(**overrides: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "schemaVersion": "1.0",
        "messageId": str(uuid.uuid4()),
        "decisionSpaceVersion": 1,
        "locale": "en-IN",
        "content": {
            "schemaVersion": "1.0",
            "contentType": "TEXT",
            "text": "Prepare the next update",
            "language": "en",
        },
    }
    body.update(overrides)
    return body


@pytest.fixture(autouse=True)
def execution_state() -> FakeTemporalClient:
    temporal = FakeTemporalClient()
    app.state.bp_service_jwt_secret = SECRET
    app.state.temporal_client = temporal
    app.state.conversation_constitutional_gateway = FakeConstitutionalGateway()
    app.state.emergency_stop_jwt_validator = FakeEmergencyStopJWTValidator()
    app.state.temporal_worker_task = MagicMock(done=MagicMock(return_value=False))
    app.state.conversation_stream_poll_seconds = 0
    app.state.conversation_stream_heartbeat_seconds = 60
    return temporal


async def _start(client: Any, **kwargs: Any) -> tuple[uuid.UUID, dict[str, Any]]:
    conversation_id = uuid.uuid4()
    response = await client.post(
        f"/api/v1/internal/conversations/{conversation_id}/executions",
        headers=_headers(_service_token(), kwargs.get("key")),
        json=kwargs.get("body", _body()),
    )
    assert response.status_code == 202
    return conversation_id, response.json()


@pytest.mark.parametrize(
    "token",
    [None, _service_token(sub="browser-user"), _service_token(scope="profile:read"), _service_token(exp=1)],
)
async def test_bp_authentication_is_fail_closed(client: Any, token: str | None) -> None:
    response = await client.post(
        f"/api/v1/internal/conversations/{uuid.uuid4()}/executions",
        headers=_headers(token),
        json=_body(),
    )
    assert response.status_code == 401
    assert response.json()["code"] == "EXECUTION_NOT_ACCESSIBLE"
    assert app.state.temporal_client.started == []


async def test_start_requires_ce_readiness_and_authorization_before_temporal(client: Any) -> None:
    app.state.conversation_constitutional_gateway = None
    unavailable = await client.post(
        f"/api/v1/internal/conversations/{uuid.uuid4()}/executions",
        headers=_headers(_service_token()),
        json=_body(),
    )
    app.state.conversation_constitutional_gateway = FakeConstitutionalGateway(decision=ConstitutionalDecision.DENY)
    denied = await client.post(
        f"/api/v1/internal/conversations/{uuid.uuid4()}/executions",
        headers=_headers(_service_token()),
        json=_body(),
    )
    assert unavailable.status_code == 503
    assert unavailable.json()["code"] == "EXECUTION_CONSTITUTIONAL_UNAVAILABLE"
    assert unavailable.headers["retry-after"] == "30"
    assert denied.status_code == 404
    assert denied.json()["code"] == "EXECUTION_NOT_ACCESSIBLE"
    assert "tenant-a" not in unavailable.text + denied.text
    assert app.state.temporal_client.started == []


@pytest.mark.parametrize(
    ("decision", "status_code", "code"),
    [
        (ConstitutionalDecision.STOPPED, 423, "EXECUTION_STOPPED"),
        (ConstitutionalDecision.STALE, 409, "EXECUTION_DECISION_SPACE_STALE"),
    ],
)
async def test_constitutional_decisions_prevent_start(
    client: Any,
    decision: ConstitutionalDecision,
    status_code: int,
    code: str,
) -> None:
    app.state.conversation_constitutional_gateway = FakeConstitutionalGateway(decision=decision)
    response = await client.post(
        f"/api/v1/internal/conversations/{uuid.uuid4()}/executions",
        headers=_headers(_service_token()),
        json=_body(),
    )
    assert response.status_code == status_code
    assert response.json()["code"] == code
    assert app.state.temporal_client.started == []


async def test_not_ready_gateway_and_missing_temporal_are_fail_safe(client: Any) -> None:
    app.state.conversation_constitutional_gateway = FakeConstitutionalGateway(ready=False)
    not_ready = await client.post(
        f"/api/v1/internal/conversations/{uuid.uuid4()}/executions",
        headers=_headers(_service_token()),
        json=_body(),
    )
    app.state.temporal_client = None
    no_temporal = await client.post(
        f"/api/v1/internal/conversations/{uuid.uuid4()}/executions",
        headers=_headers(_service_token()),
        json=_body(),
    )
    assert not_ready.status_code == no_temporal.status_code == 503
    assert no_temporal.json()["code"] == "EXECUTION_RUNTIME_UNAVAILABLE"


async def test_exited_temporal_worker_is_fail_safe(client: Any) -> None:
    temporal = app.state.temporal_client
    app.state.temporal_worker_task.done.return_value = True
    response = await client.post(
        f"/api/v1/internal/conversations/{uuid.uuid4()}/executions",
        headers=_headers(_service_token()),
        json=_body(),
    )
    assert response.status_code == 503
    assert response.json()["code"] == "EXECUTION_RUNTIME_UNAVAILABLE"
    assert temporal.started == []


async def test_start_and_replay_recover_entirely_from_temporal(client: Any) -> None:
    key = uuid.uuid4()
    body = _body()
    conversation_id = uuid.uuid4()
    first = await client.post(
        f"/api/v1/internal/conversations/{conversation_id}/executions",
        headers=_headers(_service_token(), key),
        json=body,
    )
    app.state.non_authoritative_cache = {"discarded": True}
    replay = await client.post(
        f"/api/v1/internal/conversations/{conversation_id}/executions",
        headers=_headers(_service_token(), key),
        json=body,
    )
    divergent = await client.post(
        f"/api/v1/internal/conversations/{conversation_id}/executions",
        headers=_headers(_service_token(), key),
        json={**body, "locale": "hi-IN"},
    )
    assert first.status_code == 202
    assert replay.status_code == 200
    assert replay.json()["replayed"] is True
    assert divergent.status_code == 409
    assert divergent.json()["code"] == "EXECUTION_IDEMPOTENCY_CONFLICT"
    assert len(app.state.temporal_client.started) == 1


async def test_schema_version_has_canonical_unsupported_code(client: Any) -> None:
    response = await client.post(
        f"/api/v1/internal/conversations/{uuid.uuid4()}/executions",
        headers=_headers(_service_token()),
        json=_body(schemaVersion="2.0"),
    )
    assert response.status_code == 400
    assert response.json()["code"] == "EXECUTION_REQUEST_INVALID"


async def test_stream_and_cancel_query_durable_authority_after_app_restart(client: Any) -> None:
    conversation_id, execution = await _start(client)
    execution_id = execution["executionId"]
    app.state.non_authoritative_cache = {}
    handle = app.state.temporal_client.handles[execution_id]
    handle.state["state"] = "STOPPED"
    handle.state["completionReason"] = "EMERGENCY_STOPPED"
    stream = await client.get(
        f"/api/v1/internal/conversations/{conversation_id}/executions/{execution_id}/stream",
        headers=_headers(_service_token()),
    )
    cancel = await client.delete(
        f"/api/v1/internal/conversations/{conversation_id}/executions/{execution_id}",
        headers=_headers(_service_token()),
    )
    assert stream.status_code == cancel.status_code == 423
    assert handle.signals == []


async def test_stream_rejects_invalid_cursor_and_cross_context(client: Any) -> None:
    conversation_id, execution = await _start(client)
    execution_id = execution["executionId"]
    url = f"/api/v1/internal/conversations/{conversation_id}/executions/{execution_id}/stream"
    invalid_headers = _headers(_service_token())
    invalid_headers["Last-Event-ID"] = "expired-or-unknown"
    invalid = await client.get(url, headers=invalid_headers)
    cross_context = await client.get(url, headers=_headers(_service_token(tenant_id="tenant-b")))
    assert invalid.status_code == 410
    assert invalid.json()["code"] == "EXECUTION_CURSOR_EXPIRED"
    assert cross_context.status_code == 404


async def test_reconnect_reauthenticates_current_relationship_authority(client: Any) -> None:
    conversation_id, execution = await _start(client)
    gateway = app.state.conversation_constitutional_gateway
    gateway.decision = ConstitutionalDecision.STOPPED

    response = await client.get(
        f"/api/v1/internal/conversations/{conversation_id}/executions/{execution['executionId']}/stream",
        headers=_headers(_service_token()),
    )

    assert response.status_code == 423
    assert response.json()["code"] == "EXECUTION_STOPPED"
    assert len(gateway.authorizations) == 2
    reconnect = gateway.authorizations[-1]
    assert reconnect["context"].relationship_id == "relationship-a"
    assert reconnect["decision_space_version"] == 1


async def test_distinct_channels_keep_separate_execution_state_for_same_relationship(client: Any) -> None:
    whatsapp_conversation = uuid.uuid4()
    web_conversation = uuid.uuid4()
    token = _service_token(relationship_id="relationship-shared")

    whatsapp = await client.post(
        f"/api/v1/internal/conversations/{whatsapp_conversation}/executions",
        headers=_headers(token),
        json=_body(),
    )
    web = await client.post(
        f"/api/v1/internal/conversations/{web_conversation}/executions",
        headers=_headers(token),
        json=_body(),
    )

    assert whatsapp.status_code == web.status_code == 202
    assert whatsapp.json()["executionId"] != web.json()["executionId"]
    inputs = [started["input"] for started in app.state.temporal_client.started]
    assert {item.relationship_id for item in inputs} == {"relationship-shared"}
    assert {item.conversation_id for item in inputs} == {
        str(whatsapp_conversation),
        str(web_conversation),
    }


async def test_terminal_stream_has_canonical_headers_and_closes(client: Any) -> None:
    conversation_id, execution = await _start(client)
    execution_id = execution["executionId"]
    handle = app.state.temporal_client.handles[execution_id]
    handle.state.update(state="COMPLETED", completionReason="COMPLETE")
    handle.events.append(
        handle._event(
            "execution.completed",
            {"state": "COMPLETED", "partial": False, "completionReason": "COMPLETE"},
        )
    )
    response = await client.get(
        f"/api/v1/internal/conversations/{conversation_id}/executions/{execution_id}/stream",
        headers=_headers(_service_token()),
    )
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-accel-buffering"] == "no"
    assert "event: execution.completed" in response.text


async def test_cancel_is_idempotent_and_partial_comes_from_delta(client: Any) -> None:
    conversation_id, execution = await _start(client)
    execution_id = execution["executionId"]
    handle = app.state.temporal_client.handles[execution_id]
    await handle.signal(
        "AppendConversationExecutionEvent",
        ExecutionEventSignal(
            "response.delta",
            {"contentIndex": 0, "appendText": "actual output", "partial": True},
            datetime.now(timezone.utc).isoformat(),
        ),
    )
    key = uuid.uuid4()
    url = f"/api/v1/internal/conversations/{conversation_id}/executions/{execution_id}"
    first = await client.delete(url, headers=_headers(_service_token(), key))
    replay = await client.delete(url, headers=_headers(_service_token(), key))
    assert first.status_code == 202
    assert first.json()["partial"] is True
    assert first.json()["completionReason"] == "CANCELLED"
    assert replay.status_code == 200
    assert replay.json()["replayed"] is True
    assert [name for name, _payload in handle.signals].count("CancelConversationExecution") == 1


async def test_cancel_without_delta_is_not_partial_and_terminal_replays(client: Any) -> None:
    conversation_id, execution = await _start(client)
    execution_id = execution["executionId"]
    url = f"/api/v1/internal/conversations/{conversation_id}/executions/{execution_id}"
    cancelled = await client.delete(url, headers=_headers(_service_token()))
    terminal_replay = await client.delete(url, headers=_headers(_service_token()))
    assert cancelled.status_code == 202
    assert cancelled.json()["partial"] is False
    assert terminal_replay.status_code == 200
    assert terminal_replay.json()["state"] == "CANCELLED"


async def test_stream_and_cancel_fail_when_temporal_is_missing(client: Any) -> None:
    app.state.temporal_client = None
    conversation_id = uuid.uuid4()
    execution_id = uuid.uuid4()
    stream = await client.get(
        f"/api/v1/internal/conversations/{conversation_id}/executions/{execution_id}/stream",
        headers=_headers(_service_token()),
    )
    cancel = await client.delete(
        f"/api/v1/internal/conversations/{conversation_id}/executions/{execution_id}",
        headers=_headers(_service_token()),
    )
    assert stream.status_code == cancel.status_code == 503


async def test_cancel_divergent_key_reuse_conflicts_without_signal(client: Any) -> None:
    conversation_id, execution = await _start(client)
    execution_id = execution["executionId"]
    handle = app.state.temporal_client.handles[execution_id]
    key = uuid.uuid4()
    handle.state["cancellationRequests"][str(key)] = "different-request-hash"
    response = await client.delete(
        f"/api/v1/internal/conversations/{conversation_id}/executions/{execution_id}",
        headers=_headers(_service_token(), key),
    )
    assert response.status_code == 409
    assert response.json()["code"] == "EXECUTION_IDEMPOTENCY_CONFLICT"
    assert handle.signals == []


async def test_live_stream_delivers_post_connect_event_and_replays_cursor(client: Any) -> None:
    _conversation_id, execution = await _start(client)
    execution_id = execution["executionId"]
    temporal = app.state.temporal_client
    handle = temporal.handles[execution_id]
    generator = stream_workflow_events(ConnectedRequest(), temporal, uuid.UUID(execution_id), 1, 0, 60)
    pending_frame = asyncio.create_task(anext(generator))
    await asyncio.sleep(0)
    await handle.signal(
        "AppendConversationExecutionEvent",
        ExecutionEventSignal(
            "response.delta",
            {"contentIndex": 0, "appendText": "after connect", "partial": True},
            datetime.now(timezone.utc).isoformat(),
        ),
    )
    frame = await asyncio.wait_for(pending_frame, timeout=1)
    events = [
        ProfessionalExecutionEventV1.model_validate(event) for event in await handle.query("GetConversationExecutionEvents")
    ]
    assert "event: response.delta" in frame
    assert "after connect" in frame
    assert _resume_sequence(events[0].event_id, events) == 1
    assert [event.sequence for event in events if event.sequence > 1] == [2]
    await generator.aclose()


async def test_heartbeat_is_typed_and_does_not_advance_durable_cursor(client: Any) -> None:
    _conversation_id, execution = await _start(client)
    execution_id = execution["executionId"]
    temporal = app.state.temporal_client
    generator = stream_workflow_events(ConnectedRequest(), temporal, uuid.UUID(execution_id), 1, 0, 0)
    frame = await asyncio.wait_for(anext(generator), timeout=1)
    assert "event: heartbeat" in frame
    assert "id: " not in frame
    assert '"sequence":1' in frame
    assert len(await temporal.handles[execution_id].query("GetConversationExecutionEvents")) == 1
    await generator.aclose()


async def test_real_workflow_signal_order_preserves_stopped(monkeypatch: pytest.MonkeyPatch) -> None:
    workflow = ConversationExecutionWorkflow()
    wait_condition = AsyncMock()
    monkeypatch.setattr(workflow_module.workflow, "wait_condition", wait_condition)
    monkeypatch.setattr(
        workflow_module.workflow,
        "now",
        MagicMock(return_value=datetime(2026, 8, 10, 0, 0, 3, tzinfo=timezone.utc)),
    )
    workflow_input = ConversationExecutionInput(
        "1.0",
        str(uuid.uuid4()),
        str(uuid.uuid4()),
        str(uuid.uuid4()),
        "tenant-a",
        "relationship-a",
        "participant-a",
        "CUSTOMER",
        1,
        "en-IN",
        {"text": "x"},
        None,
        "request-hash",
        "2026-08-10T00:00:00+00:00",
    )
    await workflow.run(workflow_input)
    await workflow.append_event(
        ExecutionEventSignal(
            "response.delta",
            {"contentIndex": 0, "appendText": "x", "partial": True},
            "2026-08-10T00:00:01+00:00",
        )
    )
    await workflow.cancel(CancellationSignal("key", "cancel-hash", "2026-08-10T00:00:02+00:00"))
    await workflow.emergency_stop()
    await workflow.cancel(CancellationSignal("key-2", "cancel-hash-2", "2026-08-10T00:00:04+00:00"))
    assert workflow.state()["state"] == "STOPPED"
    assert workflow.state()["completionReason"] == "EMERGENCY_STOPPED"
    assert workflow.state()["partial"] is True
    assert [event["eventType"] for event in workflow.events()][-1] == "execution.stopped"


async def test_real_workflow_ignores_duplicate_cancel_and_post_terminal_event(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workflow = ConversationExecutionWorkflow()
    await workflow.append_event(ExecutionEventSignal("processing.started", {"serverTime": _now()}, _now()))
    monkeypatch.setattr(workflow_module.workflow, "wait_condition", AsyncMock())
    workflow_input = ConversationExecutionInput(
        "1.0",
        str(uuid.uuid4()),
        str(uuid.uuid4()),
        str(uuid.uuid4()),
        "tenant-a",
        "relationship-a",
        "participant-a",
        "CUSTOMER",
        1,
        "en-IN",
        {"text": "x"},
        None,
        "request-hash",
        _now(),
    )
    await workflow.run(workflow_input)
    cancellation = CancellationSignal("same-key", "same-hash", _now())
    await workflow.cancel(cancellation)
    event_count = len(workflow.events())
    await workflow.cancel(cancellation)
    await workflow.append_event(ExecutionEventSignal("processing.started", {"serverTime": _now()}, _now()))
    await workflow.emergency_stop(_now())
    await workflow.emergency_stop(_now())
    assert len(workflow.events()) == event_count + 1


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def test_validation_error_is_privacy_safe_and_health_reports_worker(client: Any) -> None:
    headers = _headers(_service_token())
    headers["X-Correlation-Id"] = "private-invalid-value"
    invalid = await client.post(
        f"/api/v1/internal/conversations/{uuid.uuid4()}/executions",
        headers=headers,
        json={"private": "customer text"},
    )
    health = await client.get("/health")
    assert invalid.status_code == 400
    assert invalid.json()["code"] == "EXECUTION_REQUEST_INVALID"
    assert "customer text" not in invalid.text
    assert invalid.json()["correlationId"] != "private-invalid-value"
    assert health.json() == {
        "status": "healthy",
        "temporalConnected": True,
        "constitutionalEngineReachable": True,
        "activePAASSessions": 0,
    }


async def test_health_degrades_for_missing_bp_auth_or_ce_and_is_unhealthy_without_worker(client: Any) -> None:
    app.state.bp_service_jwt_secret = None
    missing_auth = await client.get("/health")
    app.state.bp_service_jwt_secret = SECRET
    app.state.conversation_constitutional_gateway = None
    missing_ce = await client.get("/health")
    app.state.temporal_worker_task.done.return_value = True
    missing_worker = await client.get("/health")
    app.state.temporal_worker_task.done.return_value = False
    app.state.temporal_client.service_client.check_health.return_value = False
    disconnected_temporal = await client.get("/health")
    assert missing_auth.status_code == 503
    assert missing_auth.json()["status"] == "degraded"
    assert missing_ce.status_code == 503
    assert missing_ce.json()["status"] == "degraded"
    assert missing_worker.status_code == 503
    assert missing_worker.json()["status"] == "unhealthy"
    assert disconnected_temporal.status_code == 503
    assert disconnected_temporal.json()["status"] == "unhealthy"


@pytest.mark.parametrize(
    ("token", "expected_status"),
    [
        (_service_token(iss="other-service"), 401),
        (_service_token(aud="other-audience"), 401),
        (_service_token(aud=["other-audience", "professional-runtime"]), 202),
        (_service_token(participant_role=""), 401),
    ],
)
async def test_service_assertion_claim_variants(client: Any, token: str, expected_status: int) -> None:
    response = await client.post(
        f"/api/v1/internal/conversations/{uuid.uuid4()}/executions",
        headers=_headers(token),
        json=_body(),
    )
    assert response.status_code == expected_status


async def test_missing_service_secret_is_unauthorized(client: Any) -> None:
    del app.state.bp_service_jwt_secret
    response = await client.post(
        f"/api/v1/internal/conversations/{uuid.uuid4()}/executions",
        headers=_headers(_service_token()),
        json=_body(),
    )
    assert response.status_code == 401


async def test_non_conversation_validation_remains_generic() -> None:
    request = MagicMock()
    request.url.path = "/other"
    response = await validation_error(request, RequestValidationError([]))
    assert response.status_code == 422


async def test_lifespan_registers_conversation_worker(monkeypatch: pytest.MonkeyPatch) -> None:
    temporal = MagicMock()
    connected = AsyncMock(return_value=temporal)
    gateway = MagicMock(close=AsyncMock())
    gateway_factory = MagicMock(return_value=gateway)

    class FakeWorker:
        instances: ClassVar[list[FakeWorker]] = []

        def __init__(self, client: Any, *, task_queue: str, workflows: list[type[Any]]) -> None:
            self.client = client
            self.task_queue = task_queue
            self.workflows = workflows
            self.stopped = asyncio.Event()
            self.shutdown_called = False
            self.instances.append(self)

        async def run(self) -> None:
            await self.stopped.wait()

        async def shutdown(self) -> None:
            self.shutdown_called = True
            self.stopped.set()

    monkeypatch.setattr(main_module, "connect_temporal_client", connected)
    monkeypatch.setattr(main_module, "Worker", FakeWorker)
    monkeypatch.setattr(main_module, "GrpcConversationConstitutionalGateway", gateway_factory)
    monkeypatch.setenv("CONSTITUTIONAL_ENGINE_ADDRESS", "constitutional-engine:5002")
    monkeypatch.setenv("BP_SERVICE_JWT_SECRET", SECRET)
    async with lifespan(app):
        worker = FakeWorker.instances[0]
        assert app.state.temporal_client is temporal
        assert app.state.conversation_constitutional_gateway is gateway
        assert app.state.bp_service_jwt_secret == SECRET
        assert worker.task_queue == "conversation-execution-queue"
        assert worker.workflows == [ConversationExecutionWorkflow]
        gateway_factory.assert_called_once_with("constitutional-engine:5002")
    assert worker.shutdown_called is True
    gateway.close.assert_awaited_once()
    assert app.state.temporal_client is None
    assert app.state.conversation_constitutional_gateway is None


async def test_lifespan_connection_failure_is_fail_safe(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(main_module, "connect_temporal_client", AsyncMock(side_effect=ValueError("unavailable")))
    monkeypatch.setenv("TEMPORAL_STARTUP_ATTEMPTS", "1")
    async with lifespan(app):
        await asyncio.sleep(0)
        assert app.state.temporal_client is None
        assert app.state.temporal_worker is None


async def test_lifespan_retries_transient_temporal_startup_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    temporal = MagicMock()
    connected = AsyncMock(side_effect=[ValueError("starting"), temporal])
    worker_stopped = asyncio.Event()
    worker = MagicMock()

    async def run_worker() -> None:
        await worker_stopped.wait()

    async def stop_worker() -> None:
        worker_stopped.set()

    worker.run = run_worker
    worker.shutdown = stop_worker
    monkeypatch.setattr(main_module, "connect_temporal_client", connected)
    monkeypatch.setattr(main_module, "Worker", MagicMock(return_value=worker))
    monkeypatch.setenv("TEMPORAL_STARTUP_ATTEMPTS", "2")
    monkeypatch.setenv("TEMPORAL_STARTUP_INTERVAL_SECONDS", "0")

    async with lifespan(app):
        for _attempt in range(10):
            if app.state.temporal_client is not None:
                break
            await asyncio.sleep(0)
        assert app.state.temporal_client is temporal
        assert app.state.temporal_worker is worker

    assert connected.await_count == 2


async def test_temporal_cloud_configuration_names_are_supported(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    certificate = tmp_path / "client.pem"
    private_key = tmp_path / "client.key"
    certificate.write_bytes(b"certificate")
    private_key.write_bytes(b"private-key")
    connect = AsyncMock(return_value=MagicMock())
    monkeypatch.delenv("TEMPORAL_ADDRESS", raising=False)
    monkeypatch.setenv("TEMPORAL_CLOUD_NAMESPACE", "waooaw-prod.tmprl.cloud:7233")
    monkeypatch.setenv("TEMPORAL_CLOUD_NAMESPACE_NAME", "waooaw-prod")
    monkeypatch.setenv("TEMPORAL_CLOUD_CERT_PATH", str(certificate))
    monkeypatch.setenv("TEMPORAL_CLOUD_KEY_PATH", str(private_key))
    monkeypatch.setattr(main_module.TemporalClient, "connect", connect)
    await main_module.connect_temporal_client()
    args, kwargs = connect.await_args
    assert args == ("waooaw-prod.tmprl.cloud:7233",)
    assert kwargs["namespace"] == "waooaw-prod"
    assert kwargs["tls"].client_cert == b"certificate"
    assert kwargs["tls"].client_private_key == b"private-key"


async def test_temporal_cloud_requires_cert_and_key_pair(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TEMPORAL_CLOUD_CERT_PATH", "/tmp/client.pem")
    monkeypatch.delenv("TEMPORAL_CLOUD_KEY_PATH", raising=False)
    with pytest.raises(ValueError, match="configured together"):
        await main_module.connect_temporal_client()


def test_openapi_conforms_to_canonical_conversation_contract() -> None:
    canonical_path = Path(__file__).parents[2] / "architecture" / "reference" / "api-specs" / "professional-runtime.openapi.yaml"
    canonical = yaml.safe_load(canonical_path.read_text())
    generated = app.openapi()
    assert generated["info"]["version"] == canonical["info"]["version"] == "1.3.0"
    operations = {
        "/api/v1/internal/conversations/{conversationId}/executions": "post",
        "/api/v1/internal/conversations/{conversationId}/executions/{executionId}/stream": "get",
        "/api/v1/internal/conversations/{conversationId}/executions/{executionId}": "delete",
    }
    for path, method in operations.items():
        expected = canonical["paths"][path][method]
        actual = generated["paths"][path][method]
        assert actual["operationId"] == expected["operationId"]
        assert set(actual["responses"]) == set(expected["responses"])
        assert actual["x-internal"] is True
        assert actual["security"] == [{"ServiceBearerAuth": []}]
        assert actual["tags"] == ["Conversation Execution"]
        assert actual["responses"] == expected["responses"]
        assert actual["parameters"] == expected["parameters"]
    stream_response = generated["paths"][next(path for path in operations if path.endswith("/stream"))]["get"]["responses"]["200"]
    assert set(stream_response["content"]) == {"text/event-stream"}
    assert (
        stream_response["headers"]
        == canonical["paths"]["/api/v1/internal/conversations/{conversationId}/executions/{executionId}/stream"]["get"][
            "responses"
        ]["200"]["headers"]
    )
    assert generated["servers"] == canonical["servers"]
    assert (
        generated["components"]["securitySchemes"]["ServiceBearerAuth"]
        == canonical["components"]["securitySchemes"]["ServiceBearerAuth"]
    )
    for response_name in (
        "ExecutionInvalidRequest",
        "ExecutionUnauthorized",
        "ExecutionNotFound",
        "ExecutionConflict",
        "ExecutionCursorExpired",
        "ExecutionStopped",
        "ExecutionUnavailable",
    ):
        assert generated["components"]["responses"][response_name] == canonical["components"]["responses"][response_name]
        assert set(generated["components"]["responses"][response_name]["content"]) == {"application/problem+json"}
    for schema_name in (
        "ConversationExecutionSchemaVersion",
        "ConversationExecutionTextV1",
        "StartConversationExecutionRequestV1",
        "ProfessionalExecutionEventType",
        "ProfessionalExecutionEventV1",
        "HealthResponse",
    ):
        assert generated["components"]["schemas"][schema_name] == canonical["components"]["schemas"][schema_name]
    assert "/api/v1/paas/sessions" in generated["paths"]
    assert "HTTPValidationError" in generated["components"]["schemas"]
    assert generated["paths"]["/health"]["get"]["security"] == []


async def test_grpc_gateway_sends_canonical_validate_action_with_tenant_metadata() -> None:
    channel = MagicMock(channel_ready=AsyncMock(), close=AsyncMock())
    request_factory = MagicMock(side_effect=lambda **values: SimpleNamespace(**values))

    validation_decision = MagicMock()
    validation_decision.Name.return_value = "VALIDATION_DECISION_ALLOW"

    protobuf = SimpleNamespace(
        APPROVAL_TYPE_PRE_AUTHORIZED=4,
        ValidateActionRequest=request_factory,
        ValidationDecision=validation_decision,
    )
    stub = MagicMock(
        ValidateAction=AsyncMock(return_value=SimpleNamespace(decision=1, constitutional_basis="C-023; C-041", reason=""))
    )
    gateway = GrpcConversationConstitutionalGateway(
        "unused",
        channel=channel,
        stub=stub,
        protobuf=protobuf,
    )
    context = BPServiceContext("contract-a", "tenant-a", "relationship-a", "participant-a", "CUSTOMER")
    conversation_id = uuid.uuid4()
    decision = await gateway.authorize_execution(context, conversation_id, 7, "request-hash")
    request = stub.ValidateAction.await_args.args[0]
    assert decision == ConstitutionalDecision.ALLOW
    assert request.contract_id == "contract-a"
    assert request.action_type == "CONVERSATION_EXECUTION"
    assert request.decision_space_version == 7
    assert request.approval_type == 4
    assert json.loads(request.action_parameters)["request_hash"] == "request-hash"
    assert stub.ValidateAction.await_args.kwargs["metadata"] == (("x-tenant-id", "tenant-a"),)


async def test_grpc_gateway_requires_constitutional_basis_and_translates_transport_failure() -> None:
    channel = MagicMock(channel_ready=AsyncMock(), close=AsyncMock())

    validation_decision = MagicMock()
    validation_decision.Name.return_value = "VALIDATION_DECISION_ALLOW"

    protobuf = SimpleNamespace(
        APPROVAL_TYPE_PRE_AUTHORIZED=4,
        ValidateActionRequest=lambda **values: SimpleNamespace(**values),
        ValidationDecision=validation_decision,
    )
    stub = MagicMock(ValidateAction=AsyncMock(return_value=SimpleNamespace(decision=1, constitutional_basis="", reason="")))
    gateway = GrpcConversationConstitutionalGateway("unused", channel=channel, stub=stub, protobuf=protobuf)
    context = BPServiceContext("contract-a", "tenant-a", "relationship-a", "participant-a", "CUSTOMER")
    assert await gateway.authorize_execution(context, uuid.uuid4(), 1, "hash") == ConstitutionalDecision.DENY
    stub.ValidateAction.side_effect = RuntimeError("CE unavailable")
    with pytest.raises(ConstitutionalGatewayUnavailableError):
        await gateway.authorize_execution(context, uuid.uuid4(), 1, "hash")


@pytest.mark.parametrize(("serving_status", "expected"), [(1, True), (2, False)])
async def test_grpc_gateway_readiness_requires_serving(serving_status: int, expected: bool) -> None:
    health_check = AsyncMock(return_value=SimpleNamespace(status=serving_status))
    channel = MagicMock(unary_unary=MagicMock(return_value=health_check), close=AsyncMock())
    gateway = GrpcConversationConstitutionalGateway("unused", channel=channel)
    assert await gateway.is_ready() is expected
    rpc_path = channel.unary_unary.call_args.args[0]
    rpc_options = channel.unary_unary.call_args.kwargs
    assert rpc_path == "/grpc.health.v1.Health/Check"
    assert callable(rpc_options["request_serializer"])
    assert callable(rpc_options["response_deserializer"])
    request = health_check.await_args.args[0]
    assert request.service == ""
    assert health_check.await_args.kwargs["timeout"] == 2.0


async def test_grpc_gateway_readiness_fails_closed_on_rpc_error() -> None:
    health_check = AsyncMock(side_effect=grpc.aio.AioRpcError(grpc.StatusCode.UNIMPLEMENTED, None, None, None, None))
    channel = MagicMock(unary_unary=MagicMock(return_value=health_check), close=AsyncMock())
    gateway = GrpcConversationConstitutionalGateway("unused", channel=channel)
    assert await gateway.is_ready() is False


async def test_grpc_gateway_proto_loading_and_close(monkeypatch: pytest.MonkeyPatch) -> None:
    channel = MagicMock(unary_unary=MagicMock(), close=AsyncMock())
    generated_stub = MagicMock()
    protobuf = SimpleNamespace()
    protobuf_grpc = SimpleNamespace(ConstitutionalServiceStub=MagicMock(return_value=generated_stub))
    compile_contract = MagicMock(return_value=(protobuf, protobuf_grpc))
    monkeypatch.setattr("constitutional_gateway.grpc.protos_and_services", compile_contract)
    gateway = GrpcConversationConstitutionalGateway("unused", channel=channel)
    assert gateway._load_contract() == (protobuf, generated_stub)
    assert gateway._load_contract() == (protobuf, generated_stub)
    compile_contract.assert_called_once()
    await gateway.close()
    channel.close.assert_awaited_once()


@pytest.mark.parametrize(
    ("ce_ready", "expected_http_status", "expected_status", "expected_reachable"),
    [(True, 200, "healthy", True), (False, 503, "degraded", False)],
)
async def test_health_uses_canonical_ce_readiness(
    client: Any,
    ce_ready: bool,
    expected_http_status: int,
    expected_status: str,
    expected_reachable: bool,
) -> None:
    app.state.conversation_constitutional_gateway = FakeConstitutionalGateway(ready=ce_ready)
    response = await client.get("/health")
    assert response.status_code == expected_http_status
    assert response.json() == {
        "status": expected_status,
        "temporalConnected": True,
        "constitutionalEngineReachable": expected_reachable,
        "activePAASSessions": 0,
    }


@pytest.mark.parametrize(
    ("reason", "expected"),
    [
        ("EMERGENCY_STOP_ACTIVE", ConstitutionalDecision.STOPPED),
        ("DECISION_SPACE_STALE", ConstitutionalDecision.STALE),
        ("OUTSIDE_AUTHORITY", ConstitutionalDecision.DENY),
    ],
)
async def test_grpc_gateway_maps_ce_denial_reasons(reason: str, expected: ConstitutionalDecision) -> None:
    channel = MagicMock(channel_ready=AsyncMock(), close=AsyncMock())
    validation_decision = MagicMock()
    validation_decision.Name.return_value = "VALIDATION_DECISION_DENY"
    protobuf = SimpleNamespace(
        APPROVAL_TYPE_PRE_AUTHORIZED=4,
        ValidateActionRequest=lambda **values: SimpleNamespace(**values),
        ValidationDecision=validation_decision,
    )
    stub = MagicMock(
        ValidateAction=AsyncMock(return_value=SimpleNamespace(decision=2, constitutional_basis="C-041", reason=reason))
    )
    gateway = GrpcConversationConstitutionalGateway("unused", channel=channel, stub=stub, protobuf=protobuf)
    context = BPServiceContext("contract-a", "tenant-a", "relationship-a", "participant-a", "CUSTOMER")
    assert await gateway.authorize_execution(context, uuid.uuid4(), 1, "hash") == expected


def test_emergency_stop_websocket_refuses_missing_and_invalid_auth() -> None:
    websocket_client = TestClient(app)
    with pytest.raises(WebSocketDenialResponse) as missing:
        with websocket_client.websocket_connect("/ws/emergency-stop"):
            pass
    assert missing.value.status_code == 401

    app.state.emergency_stop_jwt_validator = FakeEmergencyStopJWTValidator(valid=False)
    with pytest.raises(WebSocketDenialResponse) as invalid:
        with websocket_client.websocket_connect(
            "/ws/emergency-stop",
            headers={"Authorization": "Bearer invalid"},
            subprotocols=["waooaw-emergency-stop-v1"],
        ):
            pass
    assert invalid.value.status_code == 401


async def test_keycloak_validator_enforces_rs256_authority_claims() -> None:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_numbers = private_key.public_key().public_numbers()
    jwks_response = MagicMock()
    jwks_response.raise_for_status.return_value = None
    jwks_response.json.return_value = {
        "keys": [
            {
                "kid": "key-a",
                "kty": "RSA",
                "n": _encode_bytes(public_numbers.n.to_bytes((public_numbers.n.bit_length() + 7) // 8, "big")),
                "e": _encode_bytes(public_numbers.e.to_bytes((public_numbers.e.bit_length() + 7) // 8, "big")),
            }
        ]
    }
    http_client = MagicMock(get=AsyncMock(return_value=jwks_response))
    validator = KeycloakJWTValidator(
        "https://keycloak/realms/waooaw/protocol/openid-connect/certs",
        "https://keycloak/realms/waooaw",
        "waooaw-platform",
        http_client,
    )
    header = _encode_segment({"alg": "RS256", "typ": "JWT", "kid": "key-a"})
    payload = _encode_segment(
        {
            "iss": "https://keycloak/realms/waooaw",
            "sub": "customer-a",
            "aud": "waooaw-platform",
            "exp": int(time.time()) + 300,
            "tenant_id": "tenant-a",
            "contract_id": "contract-a",
        }
    )
    signed = f"{header}.{payload}".encode()
    signature = private_key.sign(signed, padding.PKCS1v15(), hashes.SHA256())
    authority = await validator.validate(f"{header}.{payload}.{_encode_bytes(signature)}")
    assert authority == EmergencyStopAuthority("tenant-a", "customer-a", "contract-a")
    http_client.get.assert_awaited_once()
    invalid_payload = _encode_segment(
        {
            "iss": "https://keycloak/realms/waooaw",
            "sub": "customer-a",
            "aud": "wrong-audience",
            "exp": int(time.time()) + 300,
            "tenant_id": "tenant-a",
            "contract_id": "contract-a",
        }
    )
    invalid_signed = f"{header}.{invalid_payload}".encode()
    invalid_signature = private_key.sign(invalid_signed, padding.PKCS1v15(), hashes.SHA256())
    with pytest.raises(ValueError, match="invalid audience"):
        await validator.validate(f"{header}.{invalid_payload}.{_encode_bytes(invalid_signature)}")


def test_emergency_stop_websocket_rejects_claim_contract_mismatch() -> None:
    gateway = FakeEmergencyStopGateway()
    app.state.conversation_constitutional_gateway = gateway
    with TestClient(app).websocket_connect(
        "/ws/emergency-stop",
        headers={"Authorization": "Bearer valid"},
        subprotocols=["waooaw-emergency-stop-v1"],
    ) as websocket:
        assert websocket.receive_json()["contractId"] == "contract-a"
        websocket.send_json({"type": "EMERGENCY_STOP", "contractId": "contract-b"})
        error = websocket.receive_json()
    assert error["type"] == "ERROR"
    assert error["code"] == "INVALID_CONTRACT"
    assert gateway.stop_requests == []


@pytest.mark.parametrize(
    "frame",
    [
        {"type": "UNEXPECTED"},
        {"type": "EMERGENCY_STOP", "contractId": "contract-a", "activeSessionIds": "not-a-list"},
        {"type": "EMERGENCY_STOP", "contractId": "contract-a", "activeSessionIds": ["not-a-uuid"]},
    ],
)
def test_emergency_stop_websocket_rejects_invalid_frames(frame: dict[str, Any]) -> None:
    app.state.conversation_constitutional_gateway = FakeEmergencyStopGateway()
    with TestClient(app).websocket_connect(
        "/ws/emergency-stop",
        headers={"Authorization": "Bearer valid"},
        subprotocols=["waooaw-emergency-stop-v1"],
    ) as websocket:
        websocket.receive_json()
        websocket.send_json(frame)
        error = websocket.receive_json()
    assert error["type"] == "ERROR"
    assert error["code"] == "INTERNAL"


def test_emergency_stop_websocket_rejects_malformed_json_and_missing_ce() -> None:
    websocket_client = TestClient(app)
    with websocket_client.websocket_connect(
        "/ws/emergency-stop",
        headers={"Authorization": "Bearer valid"},
        subprotocols=["waooaw-emergency-stop-v1"],
    ) as websocket:
        websocket.receive_json()
        websocket.send_text("{")
        malformed = websocket.receive_json()
    assert malformed["type"] == "ERROR"

    app.state.conversation_constitutional_gateway = None
    with websocket_client.websocket_connect(
        "/ws/emergency-stop",
        headers={"Authorization": "Bearer valid"},
        subprotocols=["waooaw-emergency-stop-v1"],
    ) as websocket:
        websocket.receive_json()
        websocket.send_json({"type": "EMERGENCY_STOP", "contractId": "contract-a"})
        unavailable = websocket.receive_json()
    assert unavailable["type"] == "ERROR"
    assert unavailable["code"] == "INTERNAL"


def test_emergency_stop_websocket_handles_disconnect_before_command() -> None:
    with TestClient(app).websocket_connect(
        "/ws/emergency-stop",
        headers={"Authorization": "Bearer valid"},
        subprotocols=["waooaw-emergency-stop-v1"],
    ) as websocket:
        websocket.receive_json()


async def test_emergency_stop_websocket_handles_ready_send_failure() -> None:
    class FailedReadyWebSocket:
        def __init__(self) -> None:
            self.headers = {"Authorization": "Bearer valid"}
            self.app = SimpleNamespace(
                state=SimpleNamespace(
                    emergency_stop_jwt_validator=FakeEmergencyStopJWTValidator(),
                    conversation_constitutional_gateway=FakeEmergencyStopGateway(),
                )
            )

        async def accept(self, **_kwargs: Any) -> None:
            return None

        async def send_json(self, _frame: dict[str, Any]) -> None:
            raise RuntimeError("connection closed")

    await emergency_stop_websocket(FailedReadyWebSocket())


async def test_emergency_stop_websocket_handles_confirmation_send_failure() -> None:
    session_id = "22222222-2222-2222-2222-222222222222"

    class FailedConfirmationWebSocket:
        def __init__(self) -> None:
            self.headers = {"Authorization": "Bearer valid"}
            self.app = SimpleNamespace(
                state=SimpleNamespace(
                    emergency_stop_jwt_validator=FakeEmergencyStopJWTValidator(),
                    conversation_constitutional_gateway=FakeEmergencyStopGateway(),
                )
            )
            self.send_count = 0

        async def accept(self, **_kwargs: Any) -> None:
            return None

        async def send_json(self, _frame: dict[str, Any]) -> None:
            self.send_count += 1
            if self.send_count == 2:
                raise RuntimeError("connection closed")

        async def receive_json(self) -> dict[str, Any]:
            return {
                "type": "EMERGENCY_STOP",
                "contractId": "contract-a",
                "activeSessionIds": [session_id],
            }

    websocket = FailedConfirmationWebSocket()
    await emergency_stop_websocket(websocket)
    assert websocket.send_count == 2


async def test_emergency_stop_websocket_handles_close_failure_after_confirmation() -> None:
    session_id = "22222222-2222-2222-2222-222222222222"

    class FailedCloseWebSocket:
        def __init__(self) -> None:
            self.headers = {"Authorization": "Bearer valid"}
            self.app = SimpleNamespace(
                state=SimpleNamespace(
                    emergency_stop_jwt_validator=FakeEmergencyStopJWTValidator(),
                    conversation_constitutional_gateway=FakeEmergencyStopGateway(),
                )
            )
            self.sent: list[dict[str, Any]] = []

        async def accept(self, **_kwargs: Any) -> None:
            return None

        async def send_json(self, frame: dict[str, Any]) -> None:
            self.sent.append(frame)

        async def receive_json(self) -> dict[str, Any]:
            return {
                "type": "EMERGENCY_STOP",
                "contractId": "contract-a",
                "activeSessionIds": [session_id],
            }

        async def close(self, **_kwargs: Any) -> None:
            raise RuntimeError("connection closed")

    websocket = FailedCloseWebSocket()
    await emergency_stop_websocket(websocket)
    assert websocket.sent[-1]["type"] == "EMERGENCY_STOP_CONFIRMED"


def test_emergency_stop_websocket_ce_failure_sends_no_confirmation() -> None:
    gateway = FakeEmergencyStopGateway(failure=True)
    app.state.conversation_constitutional_gateway = gateway
    with TestClient(app).websocket_connect(
        "/ws/emergency-stop",
        headers={"Authorization": "Bearer valid"},
        subprotocols=["waooaw-emergency-stop-v1"],
    ) as websocket:
        websocket.receive_json()
        websocket.send_json({"type": "EMERGENCY_STOP", "contractId": "contract-a", "activeSessionIds": []})
        response = websocket.receive_json()
    assert response["type"] == "ERROR"
    assert response["code"] == "INTERNAL"
    assert gateway.stop_requests[0]["stopped_by"] == "customer-a"


def test_emergency_stop_websocket_confirms_only_from_ce_evidence() -> None:
    gateway = FakeEmergencyStopGateway()
    app.state.conversation_constitutional_gateway = gateway
    session_id = "22222222-2222-2222-2222-222222222222"
    with TestClient(app).websocket_connect(
        "/ws/emergency-stop",
        headers={"Authorization": "Bearer valid"},
        subprotocols=["waooaw-emergency-stop-v1"],
    ) as websocket:
        websocket.receive_json()
        websocket.send_json({"type": "EMERGENCY_STOP", "contractId": "contract-a", "activeSessionIds": [session_id]})
        confirmation = websocket.receive_json()
    assert gateway.stop_requests == [
        {
            "contract_id": "contract-a",
            "tenant_id": "tenant-a",
            "stopped_by": "customer-a",
            "active_session_ids": [session_id],
        }
    ]
    assert confirmation == {
        "type": "EMERGENCY_STOP_CONFIRMED",
        "emergencyStopRecordId": "EMERGENCY_STOP:11111111-1111-1111-1111-111111111111",
        "affectedSessions": [session_id],
        "confirmedAt": "2026-08-10T01:02:03.456000Z",
    }


async def test_grpc_gateway_sends_canonical_emergency_stop_with_tenant_metadata() -> None:
    channel = MagicMock(unary_unary=MagicMock(), close=AsyncMock())
    request_factory = MagicMock(side_effect=lambda **values: SimpleNamespace(**values))
    recorded_at = MagicMock()
    recorded_at.ToDatetime.return_value = datetime(2026, 8, 10, 1, 2, 3, 456000, tzinfo=timezone.utc)
    stub = MagicMock(
        TriggerEmergencyStop=AsyncMock(
            return_value=SimpleNamespace(
                emergency_stop_record_id="EMERGENCY_STOP:record-a",
                affected_sessions=["session-a"],
                recorded_at=recorded_at,
            )
        )
    )
    protobuf = SimpleNamespace(EmergencyStopRequest=request_factory)
    gateway = GrpcConversationConstitutionalGateway("unused", channel=channel, stub=stub, protobuf=protobuf)
    result = await gateway.trigger_emergency_stop(
        contract_id="contract-a",
        tenant_id="tenant-a",
        stopped_by="customer-a",
        active_session_ids=["session-a"],
    )
    request = stub.TriggerEmergencyStop.await_args.args[0]
    assert vars(request) == {
        "contract_id": "contract-a",
        "stopped_by": "customer-a",
        "active_session_ids": ["session-a"],
    }
    assert stub.TriggerEmergencyStop.await_args.kwargs == {
        "metadata": (("x-tenant-id", "tenant-a"),),
        "timeout": 0.2,
    }
    assert result.recorded_at == "2026-08-10T01:02:03.456000Z"


@pytest.mark.parametrize(
    "event_data",
    [
        {"contentIndex": 0, "appendText": "delta", "partial": True},
        {
            "schemaVersion": "1.0",
            "cardType": "ACTION",
            "cardId": str(uuid.uuid4()),
            "owner": "PROFESSIONAL",
            "state": "PROPOSED",
            "effect": "Review before action",
            "data": {},
        },
        {"state": "RECORDED", "evidenceRecordId": str(uuid.uuid4())},
        {"state": "COMPLETED", "partial": False, "completionReason": "COMPLETE"},
        {"reason": "EVENT_GAP"},
        {"serverTime": datetime.now(timezone.utc).isoformat()},
    ],
)
def test_all_canonical_event_data_variants_are_typed(event_data: dict[str, Any]) -> None:
    event = ProfessionalExecutionEventV1.model_validate(
        {
            "schemaVersion": "1.0",
            "eventId": "execution:1",
            "eventType": "heartbeat",
            "conversationId": str(uuid.uuid4()),
            "executionId": str(uuid.uuid4()),
            "messageId": str(uuid.uuid4()),
            "sequence": 1,
            "occurredAt": datetime.now(timezone.utc).isoformat(),
            "data": event_data,
        }
    )
    assert event.data is not None


def test_problem_codes_match_canonical_openapi() -> None:
    assert {code.value for code in ExecutionProblemCode} == {
        "EXECUTION_REQUEST_INVALID",
        "EXECUTION_NOT_ACCESSIBLE",
        "EXECUTION_IDEMPOTENCY_CONFLICT",
        "EXECUTION_SCHEMA_UNSUPPORTED",
        "EXECUTION_CURSOR_EXPIRED",
        "EXECUTION_STOPPED",
        "EXECUTION_DECISION_SPACE_STALE",
        "EXECUTION_CONSTITUTIONAL_UNAVAILABLE",
        "EXECUTION_RUNTIME_UNAVAILABLE",
    }


def test_constitutional_engine_uses_canonical_emergency_stop_signal() -> None:
    service_path = Path(__file__).parents[2] / "src" / "constitutional-engine" / "Services" / "ConstitutionalEngineService.cs"
    service_source = service_path.read_text()
    assert '"EmergencyStop"' in service_source
    assert '"emergency-stop"' not in service_source


async def test_paas_workflow_accepts_canonical_no_payload_emergency_stop() -> None:
    from workflows.paas_workflow import (
        EmergencyStopSignalPayload,
        PAASSessionWorkflow,
        SessionState,
    )

    canonical_workflow = PAASSessionWorkflow()
    await canonical_workflow.signal_emergency_stop()
    assert canonical_workflow._state == SessionState.EMERGENCY_STOPPED
    assert canonical_workflow._emergency_stop_payload is not None
    assert canonical_workflow._emergency_stop_payload.stopped_by == "constitutional-engine"

    legacy_workflow = PAASSessionWorkflow()
    legacy_payload = EmergencyStopSignalPayload(stopped_by="customer", reason="requested")
    await legacy_workflow.signal_emergency_stop(legacy_payload)
    assert legacy_workflow._emergency_stop_payload is legacy_payload
