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
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any, ClassVar
from unittest.mock import AsyncMock, MagicMock

import grpc
import httpx
import pytest
import yaml
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from starlette.testclient import TestClient, WebSocketDenialResponse
from temporalio.exceptions import ActivityError, WorkflowAlreadyStartedError
from temporalio.service import RPCError, RPCStatusCode
from temporalio.testing import ActivityEnvironment

import professional_runtime_main as main_module
from activities import conversation_dispatch as dispatch_module
from constitutional_gateway import EmergencyStopResult, GrpcConversationConstitutionalGateway
from professional_runtime_main import app, lifespan, validation_error
from activities.conversation_dispatch import ConversationDispatchActivity
from routers import conversation_execution as conversation_router
from routers.conversation_execution import (
    BPServiceContext,
    ConstitutionalDecision,
    ConstitutionalGatewayUnavailableError,
    ExecutionProblemCode,
    _resume_sequence,
    get_bp_service_context,
    get_conversation_service_context,
    stream_workflow_events,
)
from routers.emergency_stop import EmergencyStopAuthority, KeycloakJWTValidator, emergency_stop_websocket
from routers.conversation_models import (
    BatchExecutionSourceV1,
    ProfessionalExecutionEventV1,
    StartBatchExecutionRequestV1,
    batch_source_list_digest,
)
from workload_identity import DelegatedContext
from workflows import conversation_execution_workflow as workflow_module
from workflows.conversation_execution_workflow import (
    CancellationSignal,
    ConversationExecutionInput,
    ConversationExecutionWorkflow,
    ExecutionEventSignal,
)

SECRET = "bp-service-test-secret"
DEFAULT_IDEMPOTENCY_KEY = uuid.UUID("11111111-1111-1111-1111-111111111111")


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


class FakeEmploymentAirGateway:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.proposals: list[dict[str, Any]] = []
        self.proposal_id = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
        self.generations: list[dict[str, Any]] = []
        self.generated_text: str | None = None

    async def generate(self, context: Any, key: uuid.UUID, payload: dict[str, Any]) -> Any:
        self.generations.append(payload)
        result = {
            "schemaVersion": "1.0",
            "executionId": payload["executionId"],
            "requestDigest": payload["requestDigest"],
            "state": "FAILED",
            "text": None,
            "reason": "POLICY_OR_DEPENDENCY_UNAVAILABLE",
        }
        if self.generated_text is not None:
            result.update(
                state="COMPLETED",
                text=self.generated_text,
                reason=None,
                inputTokens=4,
                outputTokens=1,
                reservationId=str(uuid.uuid4()),
                commercialReservationId=str(uuid.uuid4()),
                evidenceId=str(uuid.uuid4()),
            )
        return SimpleNamespace(raise_for_status=lambda: None, json=lambda: result)

    async def propose(
        self,
        trusted_context: Any,
        idempotency_key: uuid.UUID,
        payload: dict[str, Any],
    ) -> Any:
        self.proposals.append(
            {
                "trusted_context": trusted_context,
                "idempotency_key": idempotency_key,
                "payload": payload,
            }
        )
        if self.fail:
            raise ValueError("AIR unavailable")
        return SimpleNamespace(
            raise_for_status=lambda: None,
            json=lambda: {"proposalId": str(self.proposal_id), "state": "PENDING"},
        )

    async def get(self, trusted_context: Any, proposal_id: uuid.UUID) -> Any:
        assert trusted_context.relationship_id == "relationship-a"
        assert proposal_id == self.proposal_id
        payload = self.proposals[-1]["payload"]
        return SimpleNamespace(
            raise_for_status=lambda: None,
            json=lambda: {
                **payload,
                "proposalId": str(self.proposal_id),
                "state": "PROPOSED",
                "confidence": 0.9,
                "operations": [{"op": "ADD", "semanticPath": "goal.objective", "value": "synthetic objective"}],
                "assumptions": [],
                "unresolvedQuestions": [],
                "sourceRefs": [],
                "createdAt": "2026-10-08T00:00:00Z",
            },
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
            "mandateId": workflow_input.mandate_id,
            "mandateDigest": workflow_input.mandate_digest,
            "decisionSpaceVersion": workflow_input.decision_space_version,
            "state": "ACCEPTED",
            "partial": False,
            "completionReason": None,
            "requestHash": workflow_input.request_hash,
            "batchId": workflow_input.batch_id,
            "sourceListDigest": workflow_input.source_list_digest,
            "acceptedAt": workflow_input.accepted_at,
            "updatedAt": workflow_input.accepted_at,
            "cancellationRequests": {},
        }
        self.events = [self._event("execution.accepted", {"serverTime": workflow_input.accepted_at})]
        self.queries: list[str] = []

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
        self.queries.append(query_name)
        if query_name == "GetConversationExecutionState":
            return copy.deepcopy(self.state)
        if query_name == "GetConversationExecutionEvents":
            return copy.deepcopy(self.events)
        if query_name == "GetConversationExecutionTerminalSnapshot":
            return {
                "state": copy.deepcopy(self.state),
                "events": copy.deepcopy(self.events)
                if self.state["state"]
                in {
                    "COMPLETED",
                    "FAILED",
                    "CANCELLED",
                    "STOPPED",
                }
                else [],
            }
        if query_name == "GetConversationGenerationRecoverySource":
            return {
                "state": copy.deepcopy(self.state),
                "events": copy.deepcopy(self.events),
                "dispatch": copy.deepcopy(self.workflow_input.dispatch),
            }
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
    headers = {"X-Correlation-Id": str(uuid.uuid4()), "Idempotency-Key": str(key or DEFAULT_IDEMPOTENCY_KEY)}
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _body(**overrides: Any) -> dict[str, Any]:
    mandate_id = uuid.uuid4()
    idempotency_identity = overrides.pop("idempotencyIdentity", DEFAULT_IDEMPOTENCY_KEY)
    operation = overrides.pop(
        "conversationOperation",
        {
            "kind": "EMPLOYMENT_CONTRIBUTION_INTERPRETATION",
            "governedAction": "CUSTOMER_PROFILING",
            "inputSchemaDigest": "sha256:" + "55" * 32,
            "outputSchemaDigest": "sha256:" + "66" * 32,
            "promptPolicy": {"ref": "prompt:synthetic-profile", "version": "1.0.0", "digest": "sha256:" + "77" * 32},
            "modelPolicy": {"ref": "model-policy:synthetic-profile", "version": "1.0.0", "digest": "sha256:" + "99" * 32},
            "patchType": "INDUCTION_CONTEXT",
        },
    )
    body: dict[str, Any] = {
        "schemaVersion": "1.0",
        "messageId": str(uuid.uuid4()),
        "decisionSpaceVersion": 1,
        "locale": "en-IN",
        "operationalMandate": {
            "schemaVersion": "1.0",
            "mandateId": str(mandate_id),
            "mandateDigest": "",
            "tenantId": "tenant-a",
            "relationshipId": "relationship-a",
            "agentInstanceId": "agent-instance-a",
            "actorId": "participant-a",
            "actorRole": "CUSTOMER",
            "relationshipLifecycle": "ACTIVE",
            "engagementMode": "LIVE",
            "professionalType": "DIGITAL_MARKETING_LOCAL_SERVICE",
            "releaseSequence": 1,
            "professionalVersion": "1.0.0",
            "specificationRevision": "3.1",
            "specificationDigest": "sha256:" + "22" * 32,
            "admissionRevision": 1,
            "admissionContentDigest": "sha256:" + "33" * 32,
            "artifactDigest": "sha256:" + "44" * 32,
            "baseSpecVersion": "1.0.0",
            "constitutionalDnaVersion": "1.0.0",
            "pacVersion": "1.0.0",
            "adapterProtocolVersion": "1.0.0",
            "customerContractDigest": "sha256:" + "88" * 32,
            "skillId": "CUSTOMER_PROFILING",
            "skillVersion": "1.0.0",
            "inputSchemaDigest": "sha256:" + "55" * 32,
            "outputSchemaDigest": "sha256:" + "66" * 32,
            "promptVersion": "1.0.0",
            "promptDigest": "sha256:" + "77" * 32,
            "contextRevision": 1,
            "configurationRevision": 1,
            "goalRevision": 1,
            "decisionSpaceRevision": 1,
            "budgetAllowanceRef": "allowance-a",
            "reviewPolicyRevision": 1,
            "approvalRefs": ["approval-a"],
            "stopped": False,
            "stopEvidenceRef": None,
            "operationalPurpose": "Prepare the next update",
            "permittedActions": ["CUSTOMER_PROFILING"],
            "exclusions": ["PUBLISH_WITHOUT_APPROVAL"],
            "deadline": "2027-01-01T00:00:00Z",
            "idempotencyIdentity": str(idempotency_identity),
            "constitutionalDecisionRef": "decision-a",
            "constitutionalEvidenceRef": "evidence-a",
            "billingReservationRef": "reservation-a",
            "billingAttributionRef": "attribution-a",
        },
        "content": {
            "schemaVersion": "1.0",
            "contentType": "TEXT",
            "text": "Prepare the next update",
            "language": "en",
        },
    }
    body.update(overrides)
    mandate = body["operationalMandate"]
    if operation is not None:
        mandate["conversationOperation"] = operation
    canonical = json.dumps(
        {key: value for key, value in mandate.items() if key != "mandateDigest"},
        separators=(",", ":"),
        sort_keys=True,
    ).encode()
    mandate["mandateDigest"] = f"sha256:{hashlib.sha256(canonical).hexdigest()}"
    return body


def _batch_body() -> dict[str, Any]:
    sources: list[dict[str, Any]] = []
    work_item_id = str(uuid.uuid4())
    work_item_invocation_id = str(uuid.uuid4())
    work_item_revision = 1
    for sequence, text in enumerate(("Make a post", "for Diwali"), start=1):
        idempotency_key = uuid.uuid4()
        evidence_id = uuid.uuid4()
        mandate = copy.deepcopy(_body(idempotencyIdentity=idempotency_key)["operationalMandate"])
        mandate["constitutionalEvidenceRef"] = f"ce-evidence:{evidence_id}"
        canonical_mandate = json.dumps(
            {key: value for key, value in mandate.items() if key != "mandateDigest"},
            separators=(",", ":"),
            sort_keys=True,
        ).encode()
        mandate["mandateDigest"] = "sha256:" + hashlib.sha256(canonical_mandate).hexdigest()
        sources.append(
            {
                "schemaVersion": "1.0",
                "messageId": str(uuid.uuid4()),
                "executionId": str(uuid.uuid4()),
                "sequence": sequence,
                "workItemId": work_item_id,
                "workItemRevision": work_item_revision,
                "workItemInvocationId": work_item_invocation_id,
                "idempotencyKey": str(idempotency_key),
                "evidenceId": str(evidence_id),
                "text": text,
                "language": "en",
                "operationalMandate": mandate,
            }
        )
    parsed_sources = tuple(BatchExecutionSourceV1.model_validate(source) for source in sources)
    return {
        "schemaVersion": "1.0",
        "batchId": str(uuid.uuid4()),
        "decisionSpaceVersion": sources[0]["operationalMandate"]["decisionSpaceRevision"],
        "locale": "en",
        "sourceListDigest": batch_source_list_digest(parsed_sources),
        "sources": sources,
        "content": {
            "schemaVersion": "1.0",
            "contentType": "TEXT",
            "text": "Make a post\nfor Diwali",
            "language": "en",
        },
    }


def _refresh_batch_source_digest(body: dict[str, Any]) -> None:
    sources = tuple(BatchExecutionSourceV1.model_validate(source) for source in body["sources"])
    body["sourceListDigest"] = batch_source_list_digest(sources)


def _refresh_batch_mandate_digest(mandate: dict[str, Any]) -> None:
    canonical = json.dumps(
        {key: value for key, value in mandate.items() if key != "mandateDigest"},
        separators=(",", ":"),
        sort_keys=True,
    ).encode()
    mandate["mandateDigest"] = "sha256:" + hashlib.sha256(canonical).hexdigest()


def test_batch_execution_contract_preserves_order_and_each_original_mandate() -> None:
    body = _batch_body()

    parsed = StartBatchExecutionRequestV1.model_validate(body)

    assert parsed.content.text == "Make a post\nfor Diwali"
    assert [source.sequence for source in parsed.sources] == [1, 2]
    assert len({source.work_item_id for source in parsed.sources}) == 1
    assert len({source.work_item_revision for source in parsed.sources}) == 1
    assert all(source.idempotency_key == source.operational_mandate.idempotency_identity for source in parsed.sources)
    assert all(
        source.operational_mandate.constitutional_evidence_ref == f"ce-evidence:{source.evidence_id}" for source in parsed.sources
    )


@pytest.mark.parametrize("missing_field", ["workItemId", "workItemRevision", "workItemInvocationId"])
def test_batch_execution_contract_requires_owner_work_item_binding(
    missing_field: str,
) -> None:
    body = _batch_body()
    del body["sources"][0][missing_field]

    with pytest.raises(ValidationError):
        StartBatchExecutionRequestV1.model_validate(body)


@pytest.mark.parametrize(
    "invalid_field",
    [
        "sequence",
        "content",
        "authority",
        "digest",
        "workItemId",
        "workItemRevision",
        "workItemInvocationId",
    ],
)
def test_batch_execution_contract_rejects_unbound_source_changes(
    invalid_field: str,
) -> None:
    body = _batch_body()
    if invalid_field == "sequence":
        body["sources"][1]["sequence"] += 1
        _refresh_batch_source_digest(body)
    elif invalid_field == "content":
        body["content"]["text"] = "Make a post\ncheck my invoice"
    elif invalid_field == "authority":
        body["sources"][1]["operationalMandate"]["skillVersion"] = "2.0.0"
        _refresh_batch_mandate_digest(body["sources"][1]["operationalMandate"])
        _refresh_batch_source_digest(body)
    elif invalid_field == "workItemId":
        body["sources"][1]["workItemId"] = str(uuid.uuid4())
        _refresh_batch_source_digest(body)
    elif invalid_field == "workItemRevision":
        body["sources"][1]["workItemRevision"] += 1
        _refresh_batch_source_digest(body)
    elif invalid_field == "workItemInvocationId":
        body["sources"][1]["workItemInvocationId"] = str(uuid.uuid4())
        _refresh_batch_source_digest(body)
    else:
        body["sourceListDigest"] = "sha256:" + "00" * 32

    with pytest.raises(ValidationError):
        StartBatchExecutionRequestV1.model_validate(body)


def test_batch_execution_contract_uses_utf16_code_unit_bound() -> None:
    body = _batch_body()
    body["sources"][0]["text"] = "😀" * 600
    body["sources"][1]["text"] = "x" * 800
    body["content"]["text"] = body["sources"][0]["text"] + "\n" + body["sources"][1]["text"]
    _refresh_batch_source_digest(body)

    with pytest.raises(ValidationError):
        StartBatchExecutionRequestV1.model_validate(body)


async def test_missing_operational_mandate_is_rejected_before_execution(client: Any) -> None:
    body = _body()
    del body["operationalMandate"]

    response = await client.post(
        f"/api/v1/internal/conversations/{uuid.uuid4()}/executions",
        headers=_headers(_service_token()),
        json=body,
    )

    assert response.status_code == 400
    assert response.json()["code"] == "EXECUTION_REQUEST_INVALID"
    assert app.state.temporal_client.started == []
    assert app.state.conversation_constitutional_gateway.authorizations == []


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("tenantId", "tenant-b"),
        ("relationshipId", "relationship-b"),
        ("actorId", "participant-b"),
        ("decisionSpaceRevision", 2),
        ("deadline", "2020-01-01T00:00:00Z"),
        ("stopped", True),
    ],
)
async def test_invalid_operational_mandate_is_rejected_before_authorization(
    client: Any,
    field: str,
    value: Any,
) -> None:
    body = _body()
    mandate = body["operationalMandate"]
    mandate[field] = value
    canonical = json.dumps(
        {name: item for name, item in mandate.items() if name != "mandateDigest"},
        separators=(",", ":"),
        sort_keys=True,
    ).encode()
    mandate["mandateDigest"] = f"sha256:{hashlib.sha256(canonical).hexdigest()}"

    response = await client.post(
        f"/api/v1/internal/conversations/{uuid.uuid4()}/executions",
        headers=_headers(_service_token()),
        json=body,
    )

    assert response.status_code == 409
    assert response.json()["code"] == "EXECUTION_MANDATE_INVALID"
    assert app.state.temporal_client.started == []
    assert app.state.conversation_constitutional_gateway.authorizations == []


@pytest.fixture(autouse=True)
def execution_state(monkeypatch: pytest.MonkeyPatch) -> FakeTemporalClient:
    # Execution-state tests isolate authorization; signed mTLS ingress is qualified separately.
    monkeypatch.setitem(app.dependency_overrides, get_conversation_service_context, get_bp_service_context)
    monkeypatch.setattr(app.state, "relationship_workload_auth", MagicMock())
    monkeypatch.setattr(workflow_module.workflow, "patched", lambda _patch_id: True)
    temporal = FakeTemporalClient()
    app.state.bp_service_jwt_secret = SECRET
    app.state.temporal_client = temporal
    app.state.conversation_constitutional_gateway = FakeConstitutionalGateway()
    app.state.emergency_stop_jwt_validator = FakeEmergencyStopJWTValidator()
    app.state.employment_air_gateway = None
    app.state.temporal_worker_task = MagicMock(done=MagicMock(return_value=False))
    app.state.relationship_execution_store = MagicMock(is_current_work_item=MagicMock(return_value=True))
    app.state.conversation_stream_poll_seconds = 0
    app.state.conversation_stream_heartbeat_seconds = 60
    return temporal


async def _start(client: Any, **kwargs: Any) -> tuple[uuid.UUID, dict[str, Any]]:
    conversation_id = uuid.uuid4()
    key = kwargs.get("key", DEFAULT_IDEMPOTENCY_KEY)
    response = await client.post(
        f"/api/v1/internal/conversations/{conversation_id}/executions",
        headers=_headers(_service_token(), key),
        json=kwargs.get("body", _body(idempotencyIdentity=key)),
    )
    assert response.status_code == 202
    if app.state.employment_air_gateway is not None:
        handle = app.state.temporal_client.handles[response.json()["executionId"]]
        await ConversationDispatchActivity(app).dispatch(handle.workflow_input)
    return conversation_id, response.json()


def _retained_recovery(
    monkeypatch: pytest.MonkeyPatch, temporal: FakeTemporalClient
) -> tuple[FakeWorkflowHandle, dict[str, Any], DelegatedContext, AsyncMock]:
    original_actor = str(uuid.uuid4())
    requester = str(uuid.uuid4())
    conversation_id = str(uuid.uuid4())
    execution_id = str(uuid.uuid4())
    tenant_id, relationship_id = str(uuid.uuid4()), str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    source = {
        "schemaVersion": "1.0",
        "tenantId": tenant_id,
        "relationshipId": relationship_id,
        "conversationId": conversation_id,
        "executionId": execution_id,
        "originalMessageId": str(uuid.uuid4()),
        "originalActorId": original_actor,
        "mandateId": str(uuid.uuid4()),
        "mandateDigest": "sha256:" + "ab" * 32,
    }
    source_digest = "sha256:" + hashlib.sha256(json.dumps(source, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    body = {
        "schemaVersion": "1.0",
        "originalMessageId": source["originalMessageId"],
        "originalSourceDigest": source_digest,
        "afterSequence": 0,
        "reconciliationAuthorityId": str(uuid.uuid4()),
        "permissionExpiresAt": (now + timedelta(minutes=4)).isoformat(),
        "expectedProjectionVersion": 7,
    }
    context = DelegatedContext(
        schema_version="1.0",
        key_id="synthetic-key",
        issuer_uri="spiffe://waooaw.ci/business-platform",
        target_audience="urn:waooaw:service:professional-runtime",
        method="POST",
        route=conversation_router.RECONCILIATION_ROUTE,
        operation=conversation_router.RECONCILIATION_OPERATION,
        contract_major=1,
        actor_subject=requester,
        actor_source="BP_SESSION",
        effective_role="OWNER",
        tenant_id=tenant_id,
        relationship_id=relationship_id,
        purpose="READ_EXISTING_RUNTIME_RESULT",
        subject_reference=conversation_id,
        request_digest="cd" * 32,
        command_id=body["reconciliationAuthorityId"],
        idempotency_key=str(DEFAULT_IDEMPOTENCY_KEY),
        expected_versions={
            "message": body["originalMessageId"],
            "source_digest": source_digest,
            "projection_version": "7",
            "after_sequence": "0",
            "decision_space": "2",
            "constitutional_decision": "ce-decision:" + str(uuid.uuid4()),
            "constitutional_evidence": "ce-evidence:" + str(uuid.uuid4()),
        },
        issued_at=int(now.timestamp()),
        not_before=int(now.timestamp()) - 1,
        expires_at=int(now.timestamp()) + 60,
        envelope_id=str(uuid.uuid4()),
        correlation_id=str(uuid.uuid4()),
    )
    workflow_input = ConversationExecutionInput(
        schema_version="1.0",
        execution_id=execution_id,
        conversation_id=conversation_id,
        message_id=source["originalMessageId"],
        tenant_id=tenant_id,
        relationship_id=relationship_id,
        delegated_actor_id=original_actor,
        participant_role="CUSTOMER",
        mandate_id=source["mandateId"],
        mandate_digest=source["mandateDigest"],
        decision_space_version=1,
        locale="en-IN",
        content={"schemaVersion": "1.0", "contentType": "TEXT", "text": "Synthetic input", "language": "en-IN"},
        active_goal_context_id=None,
        request_hash="ef" * 32,
        accepted_at=now.isoformat(),
    )
    handle = FakeWorkflowHandle(workflow_input)
    handle.events.append(
        handle._event(
            "response.delta",
            {"contentIndex": 0, "appendText": "Synthetic retained reply", "partial": True},
        )
    )
    handle.events.append(
        handle._event(
            "execution.completed",
            {"state": "COMPLETED", "partial": False, "completionReason": "COMPLETE"},
        )
    )
    handle.state.update(state="COMPLETED", partial=False, completionReason="COMPLETE")
    temporal.handles[execution_id] = handle
    authorize = AsyncMock(return_value=context)
    monkeypatch.setattr(conversation_router, "_authorize", authorize)
    app.state.temporal_worker_task = MagicMock(done=MagicMock(return_value=True))
    return handle, body, context, authorize


def _recovery_path(handle: FakeWorkflowHandle) -> str:
    return (
        f"/api/v1/internal/conversations/{handle.workflow_input.conversation_id}"
        f"/executions/{handle.workflow_input.execution_id}/reconcile"
    )


@pytest.mark.parametrize("role", ["OWNER", "MANAGER"])
async def test_fresh_owner_reads_one_retained_snapshot_without_original_impersonation(
    client: Any, monkeypatch: pytest.MonkeyPatch, execution_state: FakeTemporalClient, role: str
) -> None:
    handle, body, context, authorize = _retained_recovery(monkeypatch, execution_state)
    context = replace(context, effective_role=role)
    authorize.return_value = context
    before = copy.deepcopy(handle.state), copy.deepcopy(handle.events)
    response = await client.post(_recovery_path(handle), headers=_headers(), json=body)
    assert response.status_code == 200
    result = response.json()
    assert result["state"] == "COMPLETED"
    assert result["events"] == [
        ProfessionalExecutionEventV1.model_validate(event).model_dump(by_alias=True, mode="json", exclude_none=True)
        for event in before[1]
    ]
    assert result["originalRequestDigest"] == "sha256:" + handle.workflow_input.request_hash
    assert context.actor_subject != handle.workflow_input.delegated_actor_id
    assert (handle.state, handle.events) == before
    assert handle.queries == ["GetConversationExecutionTerminalSnapshot"]
    assert handle.signals == [] and execution_state.started == []
    assert app.state.conversation_constitutional_gateway.authorizations == []
    assert response.headers["Cache-Control"] == "no-store"
    digest = result.pop("resultDigest")
    assert digest == "sha256:" + hashlib.sha256(json.dumps(result, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    authorization = authorize.await_args
    assert authorization.args[1:3] == (
        conversation_router.RECONCILIATION_ROUTE,
        conversation_router.RECONCILIATION_OPERATION,
    )
    assert authorization.kwargs["idempotency_key"] == str(DEFAULT_IDEMPOTENCY_KEY)


@pytest.mark.parametrize(
    ("state", "event_type", "reason"),
    [("FAILED", "execution.failed", "PARTIAL_FAILURE"), ("CANCELLED", "execution.cancelled", "CANCELLED")],
)
async def test_recovery_preserves_known_failure_or_cancellation_without_reclassification(
    client: Any,
    monkeypatch: pytest.MonkeyPatch,
    execution_state: FakeTemporalClient,
    state: str,
    event_type: str,
    reason: str,
) -> None:
    handle, body, _, _ = _retained_recovery(monkeypatch, execution_state)
    handle.state.update(state=state, partial=True, completionReason=reason)
    handle.events[-1].update(
        eventType=event_type,
        data={"state": state, "partial": True, "completionReason": reason},
    )
    response = await client.post(_recovery_path(handle), headers=_headers(), json=body)
    assert response.status_code == 200
    assert response.json()["state"] == state
    assert response.json()["events"][-1]["eventType"] == event_type
    assert response.json()["events"][-1]["data"]["completionReason"] == reason
    assert handle.signals == [] and execution_state.started == []


@pytest.mark.parametrize("state", ["ACCEPTED", "QUEUED", "RUNNING", "UNRESOLVED"])
async def test_recovery_unknown_never_schedules_or_manufactures_terminal(
    client: Any, monkeypatch: pytest.MonkeyPatch, execution_state: FakeTemporalClient, state: str
) -> None:
    handle, body, _, _ = _retained_recovery(monkeypatch, execution_state)
    handle.state.update(state=state, completionReason=None)
    response = await client.post(_recovery_path(handle), headers=_headers(), json=body)
    assert response.status_code == 200
    assert response.json()["state"] == "UNKNOWN"
    assert response.json()["events"] == []
    assert "resultDigest" not in response.json() and "originalRequestDigest" not in response.json()
    assert response.json()["nextAction"] == "OPERATOR_RECONCILIATION_REQUIRED"
    assert handle.signals == [] and execution_state.started == []


@pytest.mark.parametrize(
    ("mutation", "status"),
    [
        ("source", 409),
        ("tenant", 404),
        ("actor", 409),
        ("event_gap", 503),
        ("missing_terminal", 503),
        ("wrong_terminal", 503),
        ("system_only", 503),
        ("missing_mandate", 503),
        ("missing_request_hash", 503),
        ("invalid_state", 503),
        ("stop", 423),
    ],
)
async def test_recovery_fences_divergent_or_incomplete_original_results(
    client: Any,
    monkeypatch: pytest.MonkeyPatch,
    execution_state: FakeTemporalClient,
    mutation: str,
    status: int,
) -> None:
    handle, body, context, authorize = _retained_recovery(monkeypatch, execution_state)
    if mutation == "source":
        body["originalSourceDigest"] = "sha256:" + "00" * 32
        authorize.return_value = replace(
            context,
            expected_versions={**context.expected_versions, "source_digest": body["originalSourceDigest"]},
        )
    elif mutation == "tenant":
        handle.state["tenantId"] = str(uuid.uuid4())
    elif mutation == "actor":
        handle.state["delegatedActorId"] = str(uuid.uuid4())
    elif mutation == "event_gap":
        handle.events[1]["sequence"] = 4
    elif mutation == "missing_terminal":
        handle.events.pop()
    elif mutation == "wrong_terminal":
        handle.events[-1]["data"]["state"] = "FAILED"
    elif mutation == "system_only":
        handle.events[1].update(
            eventType="response.system",
            data={"text": "Synthetic limitation", "code": "MODEL_UNAVAILABLE"},
        )
    elif mutation == "missing_mandate":
        handle.state.pop("mandateDigest")
    elif mutation == "missing_request_hash":
        handle.state.pop("requestHash")
    elif mutation == "invalid_state":
        handle.state["state"] = "NOT_A_RUNTIME_STATE"
    else:
        handle.state["state"] = "STOPPED"
    response = await client.post(_recovery_path(handle), headers=_headers(), json=body)
    assert response.status_code == status
    assert handle.signals == [] and execution_state.started == []
    assert "events" not in response.json()


@pytest.mark.parametrize(
    "mutation",
    [
        "role",
        "purpose",
        "authority",
        "cursor",
        "projection",
        "expired",
        "too_long",
        "decision_space",
        "evidence",
    ],
)
async def test_recovery_requires_fresh_exact_read_only_permission_before_lookup(
    client: Any, monkeypatch: pytest.MonkeyPatch, execution_state: FakeTemporalClient, mutation: str
) -> None:
    handle, body, context, authorize = _retained_recovery(monkeypatch, execution_state)
    if mutation == "role":
        context = replace(context, effective_role="CUSTOMER")
    elif mutation == "purpose":
        context = replace(context, purpose="startConversationExecution")
    elif mutation == "authority":
        context = replace(context, command_id=str(uuid.uuid4()))
    elif mutation == "cursor":
        body["afterSequence"] = 1
    elif mutation == "projection":
        body["expectedProjectionVersion"] = 8
    elif mutation == "expired":
        body["permissionExpiresAt"] = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
    elif mutation == "decision_space":
        context = replace(context, expected_versions={**context.expected_versions, "decision_space": "0"})
    elif mutation == "evidence":
        context = replace(context, expected_versions={**context.expected_versions, "constitutional_evidence": "not-evidence"})
    else:
        body["permissionExpiresAt"] = (datetime.now(timezone.utc) + timedelta(minutes=6)).isoformat()
    authorize.return_value = context
    response = await client.post(_recovery_path(handle), headers=_headers(), json=body)
    assert response.status_code == 401
    assert handle.queries == [] and handle.signals == [] and execution_state.started == []


async def test_recovery_rechecks_permission_after_snapshot(
    client: Any, monkeypatch: pytest.MonkeyPatch, execution_state: FakeTemporalClient
) -> None:
    handle, body, _, _ = _retained_recovery(monkeypatch, execution_state)

    class Clock(datetime):
        current = datetime.now(timezone.utc)

        @classmethod
        def now(cls, tz: Any = None) -> datetime:
            return cls.current

    original_query = handle.query

    async def expire_after_query(query: str) -> Any:
        snapshot = await original_query(query)
        Clock.current = datetime.fromisoformat(body["permissionExpiresAt"]) + timedelta(seconds=1)
        return snapshot

    monkeypatch.setattr(conversation_router, "datetime", Clock)
    monkeypatch.setattr(handle, "query", expire_after_query)
    response = await client.post(_recovery_path(handle), headers=_headers(), json=body)
    assert response.status_code == 401
    assert handle.queries == ["GetConversationExecutionTerminalSnapshot"]
    assert handle.signals == [] and execution_state.started == []


async def test_recovery_requires_workload_peer_not_legacy_service_jwt(
    client: Any, monkeypatch: pytest.MonkeyPatch, execution_state: FakeTemporalClient
) -> None:
    handle, body, _, _ = _retained_recovery(monkeypatch, execution_state)
    from relationship_workspace import _authorize

    monkeypatch.setattr(conversation_router, "_authorize", _authorize)
    response = await client.post(_recovery_path(handle), headers=_headers(_service_token()), json=body)
    assert response.status_code == 401
    assert handle.queries == [] and handle.signals == []


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("tenantId", str(uuid.uuid4())),
        ("actorRole", "OWNER"),
        ("provider", "synthetic"),
        ("afterSequence", True),
        ("afterSequence", -1),
        ("expectedProjectionVersion", 0.5),
        ("permissionExpiresAt", "2026-11-08T12:00:00"),
    ],
)
async def test_recovery_request_rejects_open_or_coerced_authority_fields(
    client: Any, monkeypatch: pytest.MonkeyPatch, execution_state: FakeTemporalClient, field: str, value: Any
) -> None:
    handle, body, _, _ = _retained_recovery(monkeypatch, execution_state)
    body[field] = value
    response = await client.post(_recovery_path(handle), headers=_headers(), json=body)
    assert response.status_code == 400
    assert handle.queries == [] and handle.signals == []


@pytest.mark.parametrize(("cursor", "status"), [(3, 200), (4, 409)])
async def test_recovery_cursor_can_replay_terminal_tail_but_not_skip_it(
    client: Any,
    monkeypatch: pytest.MonkeyPatch,
    execution_state: FakeTemporalClient,
    cursor: int,
    status: int,
) -> None:
    handle, body, context, authorize = _retained_recovery(monkeypatch, execution_state)
    body["afterSequence"] = cursor
    authorize.return_value = replace(
        context,
        expected_versions={**context.expected_versions, "after_sequence": str(cursor)},
    )
    response = await client.post(_recovery_path(handle), headers=_headers(), json=body)
    assert response.status_code == status
    if status == 200:
        assert response.json()["events"] == []
        assert response.json()["state"] == "COMPLETED"
        assert "resultDigest" in response.json()
    assert handle.signals == [] and execution_state.started == []


async def test_recovery_timeout_is_unavailable_not_missing_result_or_zero_usage(
    client: Any, monkeypatch: pytest.MonkeyPatch, execution_state: FakeTemporalClient
) -> None:
    handle, body, _, _ = _retained_recovery(monkeypatch, execution_state)
    monkeypatch.setattr(handle, "query", AsyncMock(side_effect=TimeoutError))
    response = await client.post(_recovery_path(handle), headers=_headers(), json=body)
    assert response.status_code == 503
    assert "events" not in response.json()
    assert handle.signals == [] and execution_state.started == []


@pytest.mark.parametrize(("count", "status"), [(4096, 200), (4097, 503)])
async def test_recovery_enforces_exact_retained_event_bound(
    client: Any,
    monkeypatch: pytest.MonkeyPatch,
    execution_state: FakeTemporalClient,
    count: int,
    status: int,
) -> None:
    handle, body, _, _ = _retained_recovery(monkeypatch, execution_state)
    terminal = handle.events.pop()
    while len(handle.events) < count - 1:
        handle.events.append(handle._event("evidence.pending", {"state": "PENDING"}))
    terminal.update(sequence=count, eventId=f"{handle.workflow_input.execution_id}:{count}")
    handle.events.append(terminal)
    response = await client.post(_recovery_path(handle), headers=_headers(), json=body)
    assert response.status_code == status
    if status == 200:
        assert len(response.json()["events"]) == 4096
    assert handle.signals == [] and execution_state.started == []


def test_terminal_snapshot_query_is_read_only_and_never_exposes_nonterminal_output(
    monkeypatch: pytest.MonkeyPatch, execution_state: FakeTemporalClient
) -> None:
    handle, _, _, _ = _retained_recovery(monkeypatch, execution_state)
    workflow = ConversationExecutionWorkflow()
    workflow._input = handle.workflow_input
    workflow._events = copy.deepcopy(handle.events)
    workflow._state = "RUNNING"
    assert workflow.terminal_snapshot()["events"] == []
    workflow._state = "COMPLETED"
    workflow._completion_reason = "COMPLETE"
    workflow._terminal = True
    before = copy.deepcopy(workflow._events)
    snapshot = workflow.terminal_snapshot()
    assert snapshot["state"]["delegatedActorId"] == handle.workflow_input.delegated_actor_id
    assert snapshot["events"] == before == workflow._events
    assert workflow._dispatch_task is None


def _air_retained_recovery(monkeypatch, temporal):
    handle, permission, context, authorize = _retained_recovery(monkeypatch, temporal)
    body = _body(
        conversationOperation={
            "kind": "PROFESSIONAL_RESPONSE",
            "governedAction": "CUSTOMER_PROFILING",
            "inputSchemaDigest": "sha256:" + "55" * 32,
            "outputSchemaDigest": "sha256:" + "66" * 32,
            "promptPolicy": {"ref": "prompt:synthetic", "version": "1.0.0", "digest": "sha256:" + "77" * 32},
            "modelPolicy": {"ref": "model:synthetic", "version": "1", "digest": "sha256:" + "99" * 32},
        }
    )
    body["messageId"] = handle.workflow_input.message_id
    mandate = body["operationalMandate"]
    mandate.update(
        tenantId=context.tenant_id,
        relationshipId=context.relationship_id,
        actorId=handle.workflow_input.delegated_actor_id,
        actorRole="EMPLOYER",
        mandateId=handle.workflow_input.mandate_id,
        deadline=(datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(),
    )
    mandate["mandateDigest"] = (
        "sha256:"
        + hashlib.sha256(
            json.dumps({k: v for k, v in mandate.items() if k != "mandateDigest"}, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
    )
    parsed = conversation_router.StartExecutionRequestV1.model_validate(body)
    original_context = BPServiceContext(
        contract_id="synthetic-contract",
        tenant_id=context.tenant_id,
        relationship_id=context.relationship_id,
        delegated_actor_id=handle.workflow_input.delegated_actor_id,
        participant_role="EMPLOYER",
    )
    execution_id = conversation_router._execution_id(
        original_context, uuid.UUID(handle.workflow_input.conversation_id), DEFAULT_IDEMPOTENCY_KEY
    )
    new_input = replace(
        handle.workflow_input,
        execution_id=str(execution_id),
        participant_role="EMPLOYER",
        mandate_digest=mandate["mandateDigest"],
        request_hash=conversation_router._request_hash(
            parsed, uuid.UUID(handle.workflow_input.conversation_id), original_context
        ),
        dispatch={
            "body": body,
            "contractId": "synthetic-contract",
            "idempotencyKey": str(DEFAULT_IDEMPOTENCY_KEY),
            "operationPolicyVersion": "1.0",
        },
    )
    handle = FakeWorkflowHandle(new_input)
    handle.state.update(state="RUNNING")
    source = {
        "schemaVersion": "1.0",
        "tenantId": context.tenant_id,
        "relationshipId": context.relationship_id,
        "conversationId": new_input.conversation_id,
        "executionId": str(execution_id),
        "originalMessageId": new_input.message_id,
        "originalActorId": new_input.delegated_actor_id,
        "mandateId": new_input.mandate_id,
        "mandateDigest": new_input.mandate_digest,
    }
    digest = "sha256:" + hashlib.sha256(json.dumps(source, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    permission["originalSourceDigest"] = digest
    context = replace(context, expected_versions={**context.expected_versions, "source_digest": digest})
    authorize.return_value = context
    temporal.handles[str(execution_id)] = handle
    gateway = SimpleNamespace(recover_generation_content=AsyncMock())

    def response(_context, _key, payload):
        return httpx.Response(
            200,
            request=httpx.Request("POST", "https://air.example.invalid"),
            json={
                "retainedAt": handle.workflow_input.accepted_at,
                "result": {
                    "schemaVersion": "1.0",
                    "executionId": str(execution_id),
                    "requestDigest": payload["generation"]["requestDigest"],
                    "state": "COMPLETED",
                    "text": "Synthetic retained DMA reply",
                    "reason": None,
                    "inputTokens": 10,
                    "outputTokens": 10,
                    "reservationId": str(uuid.uuid4()),
                    "commercialReservationId": str(uuid.uuid4()),
                    "evidenceId": str(uuid.uuid4()),
                },
            },
        )

    gateway.recover_generation_content.side_effect = response
    app.state.employment_air_gateway = gateway
    return handle, permission, context, gateway


async def test_fresh_owner_recovers_air_only_output_after_deadline_without_workflow_mutation(
    client,
    monkeypatch,
    execution_state,
):
    handle, permission, context, gateway = _air_retained_recovery(monkeypatch, execution_state)
    before = copy.deepcopy(handle.state), copy.deepcopy(handle.events)
    response = await client.post(_recovery_path(handle), headers=_headers(), json=permission)
    assert response.status_code == 200 and response.json()["state"] == "COMPLETED"
    assert response.json()["events"][-1]["eventType"] == "execution.completed"
    assert any(event["eventType"] == "response.delta" for event in response.json()["events"])
    assert (handle.state, handle.events) == before and handle.signals == [] and execution_state.started == []
    assert handle.queries == [
        "GetConversationExecutionTerminalSnapshot",
        "GetConversationGenerationRecoverySource",
        "GetConversationGenerationRecoverySource",
    ]
    sent_context, key, payload = gateway.recover_generation_content.await_args.args
    assert sent_context.actor_subject == context.actor_subject != handle.workflow_input.delegated_actor_id
    assert sent_context.command_id == permission["reconciliationAuthorityId"]
    assert key == DEFAULT_IDEMPOTENCY_KEY
    assert conversation_router.ReconcileConversationExecutionRequestV1.model_validate(
        payload["permission"]
    ) == conversation_router.ReconcileConversationExecutionRequestV1.model_validate(permission)
    assert datetime.fromisoformat(payload["generation"]["operationalMandate"]["deadline"].replace("Z", "+00:00")) == (
        datetime.fromisoformat(handle.workflow_input.dispatch["body"]["operationalMandate"]["deadline"])
    )
    replay = await client.post(_recovery_path(handle), headers=_headers(), json=permission)
    assert replay.status_code == 200 and replay.json() == response.json()
    assert (handle.state, handle.events) == before and handle.signals == [] and execution_state.started == []


@pytest.mark.parametrize(
    "failure", ["unresolved", "revoked", "partial", "digest", "missing_timestamp", "future_timestamp", "source_changed"]
)
async def test_air_only_recovery_never_restarts_or_replaces_uncertain_work(
    client,
    monkeypatch,
    execution_state,
    failure,
):
    handle, permission, _, gateway = _air_retained_recovery(monkeypatch, execution_state)
    if failure == "unresolved":

        def unknown(_context, _key, payload):
            return httpx.Response(
                200,
                request=httpx.Request("POST", "https://air.example.invalid"),
                json={
                    "retainedAt": None,
                    "result": {
                        "schemaVersion": "1.0",
                        "executionId": handle.workflow_input.execution_id,
                        "requestDigest": payload["generation"]["requestDigest"],
                        "state": "UNRESOLVED",
                        "reason": "ORIGINAL_RESULT_UNAVAILABLE",
                        "text": None,
                    },
                },
            )

        gateway.recover_generation_content.side_effect = unknown
    elif failure == "revoked":
        gateway.recover_generation_content.side_effect = None
        gateway.recover_generation_content.return_value = httpx.Response(
            403, request=httpx.Request("POST", "https://air.example.invalid")
        )
    elif failure == "partial":
        handle.events.append(handle._event("response.delta", {"contentIndex": 0, "appendText": "Partial", "partial": True}))
    elif failure in {"missing_timestamp", "future_timestamp", "source_changed"}:
        original_response = gateway.recover_generation_content.side_effect

        def altered(context, key, payload):
            value = original_response(context, key, payload).json()
            if failure == "source_changed":
                handle.state["updatedAt"] = datetime.now(timezone.utc).isoformat()
            else:
                value["retainedAt"] = (
                    None if failure == "missing_timestamp" else (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
                )
            return httpx.Response(200, request=httpx.Request("POST", "https://air.example.invalid"), json=value)

        gateway.recover_generation_content.side_effect = altered
    else:
        handle.workflow_input.dispatch["body"]["content"]["text"] = "Substituted request"
    before = copy.deepcopy(handle.state), copy.deepcopy(handle.events)
    response = await client.post(_recovery_path(handle), headers=_headers(), json=permission)
    if failure == "unresolved":
        assert response.status_code == 200 and response.json()["state"] == "UNKNOWN" and response.json()["events"] == []
    else:
        assert response.status_code == 503
    if failure == "source_changed":
        assert handle.state["state"] == before[0]["state"] and handle.events == before[1]
    else:
        assert (handle.state, handle.events) == before
    assert handle.signals == [] and execution_state.started == []
    if failure == "digest":
        gateway.recover_generation_content.assert_not_awaited()


async def test_employment_contribution_dispatches_air_proposal_after_durable_acceptance(
    client: Any,
) -> None:
    gateway = FakeEmploymentAirGateway()
    app.state.employment_air_gateway = gateway
    body = _body()

    conversation_id, execution = await _start(client, body=body)

    assert len(gateway.proposals) == 1
    dispatched = gateway.proposals[0]
    assert dispatched["trusted_context"].tenant_id == "tenant-a"
    assert dispatched["trusted_context"].relationship_id == "relationship-a"
    assert dispatched["trusted_context"].actor_source == "BP_SESSION"
    assert dispatched["payload"]["contributionRef"] == body["messageId"]
    assert dispatched["payload"]["agentType"] == body["operationalMandate"]["professionalType"]
    assert "boundedContext" in dispatched["payload"]
    assert dispatched["payload"]["boundedContext"] is None
    assert dispatched["payload"]["modelPolicy"] == {
        "ref": "model-policy:synthetic-profile",
        "version": "1.0.0",
        "digest": "99" * 32,
    }
    assert dispatched["payload"]["modelPolicy"]["digest"] != body["operationalMandate"]["specificationDigest"].removeprefix(
        "sha256:"
    )
    expected = dict(dispatched["payload"])
    request_digest = expected.pop("requestDigest")
    canonical = json.dumps(expected, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode()
    assert request_digest == hashlib.sha256(canonical).hexdigest()
    handle = app.state.temporal_client.handles[execution["executionId"]]
    proposal_event = handle.events[-2]
    assert proposal_event["eventType"] == "card.proposed"
    assert proposal_event["data"]["data"]["employmentPatchProposal"]["state"] == "PROPOSED"
    assert proposal_event["conversationId"] == str(conversation_id)
    assert handle.events[-1]["eventType"] == "execution.completed"


async def test_legacy_mandate_serialization_preserves_original_digest() -> None:
    from routers.conversation_models import StartExecutionRequestV1

    body = _body(conversationOperation=None)
    parsed = StartExecutionRequestV1.model_validate(body)
    assert "conversationOperation" not in parsed.model_dump(by_alias=True, mode="json")["operationalMandate"]
    assert conversation_router._mandate_digest(parsed) == body["operationalMandate"]["mandateDigest"]


@pytest.mark.parametrize("kind", [None, "PROFESSIONAL_RESPONSE"])
async def test_ordinary_or_undeclared_operation_never_dispatches_employment_patch(
    client: Any,
    kind: str | None,
) -> None:
    gateway = FakeEmploymentAirGateway()
    app.state.employment_air_gateway = gateway
    operation = None
    if kind is not None:
        operation = _body()["operationalMandate"]["conversationOperation"]
        operation["kind"] = kind
        operation.pop("patchType")
    _, execution = await _start(client, body=_body(conversationOperation=operation))
    handle = app.state.temporal_client.handles[execution["executionId"]]
    assert gateway.proposals == []
    assert len(gateway.generations) == (0 if kind is None else 1)
    assert not any(event["eventType"] in {"card.proposed", "execution.completed"} for event in handle.events)
    assert handle.events[-1]["eventType"] == "execution.failed"
    assert handle.events[-1]["data"]["errorCode"] == ("OPERATION_UNSUPPORTED" if kind is None else "MODEL_UNAVAILABLE")


@pytest.mark.parametrize(
    "field,value",
    [
        ("governedAction", "UNDECLARED_ACTION"),
        ("inputSchemaDigest", "sha256:" + "ab" * 32),
        ("outputSchemaDigest", "sha256:" + "ab" * 32),
        ("promptPolicy", {"ref": "prompt:synthetic-profile", "version": "2.0.0", "digest": "sha256:" + "77" * 32}),
        ("promptPolicy", {"ref": "prompt:synthetic-profile", "version": "1.0.0", "digest": "sha256:" + "ab" * 32}),
        ("modelPolicy", {"ref": "model-policy:synthetic-profile", "version": "1.0.0", "digest": "not-a-digest"}),
        ("patchType", None),
    ],
)
async def test_operation_policy_drift_is_denied_before_authorization_or_dispatch(
    client: Any,
    field: str,
    value: Any,
) -> None:
    operation = _body()["operationalMandate"]["conversationOperation"]
    operation[field] = value
    gateway = FakeEmploymentAirGateway()
    app.state.employment_air_gateway = gateway
    response = await client.post(
        f"/api/v1/internal/conversations/{uuid.uuid4()}/executions",
        headers=_headers(_service_token()),
        json=_body(conversationOperation=operation),
    )
    assert response.status_code == 400
    assert app.state.conversation_constitutional_gateway.authorizations == []
    assert app.state.temporal_client.started == []
    assert gateway.proposals == []


async def test_declared_interpretation_uses_its_patch_type_not_channel_heuristics(client: Any) -> None:
    gateway = FakeEmploymentAirGateway()
    app.state.employment_air_gateway = gateway
    operation = _body()["operationalMandate"]["conversationOperation"]
    operation["patchType"] = "GOAL"
    await _start(client, body=_body(conversationOperation=operation))
    assert gateway.proposals[0]["payload"]["patchType"] == "GOAL"


async def test_pre_policy_execution_remains_unknown_without_redispatch_or_fabricated_failure(client: Any) -> None:
    _, execution = await _start(client, body=_body(conversationOperation=None))
    handle = app.state.temporal_client.handles[execution["executionId"]]
    assert handle.workflow_input.dispatch is not None
    payload = dict(handle.workflow_input.dispatch)
    payload.pop("operationPolicyVersion")
    legacy = replace(handle.workflow_input, dispatch=payload)
    gateway = FakeEmploymentAirGateway()
    app.state.employment_air_gateway = gateway
    await ConversationDispatchActivity(app).dispatch(legacy)
    assert gateway.proposals == []
    assert handle.events[-1]["eventType"] == "reconciliation.required"
    assert not any(
        event["eventType"] in {"execution.failed", "execution.completed", "response.system"} for event in handle.events
    )


async def test_employment_air_failure_preserves_durable_execution_and_requests_reconciliation(
    client: Any,
) -> None:
    app.state.employment_air_gateway = FakeEmploymentAirGateway(fail=True)

    _, execution = await _start(client)

    handle = app.state.temporal_client.handles[execution["executionId"]]
    assert handle.events[-1]["eventType"] == "reconciliation.required"
    assert handle.events[-1]["data"] == {"reason": "STATE_CONFLICT"}


@pytest.mark.parametrize(
    "reason",
    [
        "MODEL_UNAVAILABLE",
        "MATERIAL_UNCERTAINTY",
        "SEMANTIC_PATH_UNREPRESENTABLE",
        "POLICY_REJECTED",
        "INTERNAL_FAILURE",
    ],
)
async def test_bound_known_air_failure_emits_system_limitation_then_failed_terminal(
    client: Any,
    reason: str,
) -> None:
    gateway = FakeEmploymentAirGateway()
    original_get = gateway.get

    async def failed_get(context: Any, proposal_id: uuid.UUID) -> Any:
        response = await original_get(context, proposal_id)
        result = response.json()
        result.update(state="UNREPRESENTABLE", operations=[], reasonCode=reason)
        return SimpleNamespace(raise_for_status=lambda: None, json=lambda: result)

    gateway.get = failed_get
    app.state.employment_air_gateway = gateway
    _, execution = await _start(client)
    handle = app.state.temporal_client.handles[execution["executionId"]]
    assert [event["eventType"] for event in handle.events][-2:] == ["response.system", "execution.failed"]
    assert handle.events[-2]["data"]["code"] == reason
    assert handle.events[-1]["data"]["completionReason"] == "PARTIAL_FAILURE"
    assert not any(event["eventType"] in {"card.proposed", "execution.completed"} for event in handle.events)
    conversation_router.ProfessionalExecutionEventV1.model_validate(handle.events[-2])


async def test_empty_proposal_is_reconciliation_not_professional_completion(client: Any) -> None:
    gateway = FakeEmploymentAirGateway()
    original_get = gateway.get

    async def empty_get(context: Any, proposal_id: uuid.UUID) -> Any:
        response = await original_get(context, proposal_id)
        result = response.json()
        result["operations"] = []
        return SimpleNamespace(raise_for_status=lambda: None, json=lambda: result)

    gateway.get = empty_get
    app.state.employment_air_gateway = gateway
    _, execution = await _start(client)
    handle = app.state.temporal_client.handles[execution["executionId"]]
    assert handle.events[-1]["eventType"] == "reconciliation.required"
    assert not any(event["eventType"] in {"card.proposed", "execution.completed"} for event in handle.events)


@pytest.mark.parametrize("failure", ["connection", "server", "rate_limit"])
async def test_transient_air_failure_is_retried_with_same_dispatch_identity(client: Any, failure: str) -> None:
    gateway = FakeEmploymentAirGateway()
    original_propose = gateway.propose
    attempts: list[tuple[uuid.UUID, dict[str, Any]]] = []

    async def propose(context: Any, key: uuid.UUID, payload: dict[str, Any]) -> Any:
        attempts.append((key, copy.deepcopy(payload)))
        if len(attempts) == 1:
            request = httpx.Request("POST", "https://air.test/proposals")
            if failure == "connection":
                raise httpx.ReadTimeout("response lost", request=request)
            status = 503 if failure == "server" else 429
            response = httpx.Response(status, request=request)
            raise httpx.HTTPStatusError("unavailable", request=request, response=response)
        return await original_propose(context, key, payload)

    gateway.propose = propose
    app.state.employment_air_gateway = gateway
    response = await client.post(
        f"/api/v1/internal/conversations/{uuid.uuid4()}/executions",
        headers=_headers(_service_token()),
        json=_body(),
    )
    assert response.status_code == 202
    handle = app.state.temporal_client.handles[response.json()["executionId"]]
    activity = ConversationDispatchActivity(app)
    with pytest.raises(httpx.HTTPError):
        await activity.dispatch(handle.workflow_input)
    assert [event["eventType"] for event in handle.events] == ["execution.accepted"]
    await activity.dispatch(handle.workflow_input)
    assert attempts[0] == attempts[1]
    assert handle.events[-2]["eventType"] == "card.proposed"
    assert handle.events[-1]["eventType"] == "execution.completed"


async def test_permanent_air_failure_requires_reconciliation(client: Any) -> None:
    gateway = FakeEmploymentAirGateway()
    request = httpx.Request("POST", "https://air.test/proposals")
    response = httpx.Response(400, request=request)
    gateway.propose = AsyncMock(side_effect=httpx.HTTPStatusError("invalid", request=request, response=response))
    app.state.employment_air_gateway = gateway
    _, execution = await _start(client)
    handle = app.state.temporal_client.handles[execution["executionId"]]
    assert handle.events[-1]["eventType"] == "reconciliation.required"


async def test_lost_air_response_recovers_persisted_proposal_on_retry(client: Any) -> None:
    gateway = FakeEmploymentAirGateway()
    original_propose = gateway.propose
    proposal_key = None

    async def propose(context: Any, key: uuid.UUID, payload: dict[str, Any]) -> Any:
        nonlocal proposal_key
        if proposal_key is None:
            proposal_key = key
            await original_propose(context, key, payload)
            raise httpx.ReadTimeout("response lost", request=httpx.Request("POST", "https://air.test"))
        assert key == proposal_key
        assert payload == gateway.proposals[0]["payload"]
        return await gateway.get(context, gateway.proposal_id)

    gateway.propose = propose
    app.state.employment_air_gateway = gateway
    response = await client.post(
        f"/api/v1/internal/conversations/{uuid.uuid4()}/executions",
        headers=_headers(_service_token()),
        json=_body(),
    )
    assert response.status_code == 202
    handle = app.state.temporal_client.handles[response.json()["executionId"]]
    activity = ConversationDispatchActivity(app)
    with pytest.raises(httpx.ReadTimeout):
        await activity.dispatch(handle.workflow_input)
    await activity.dispatch(handle.workflow_input)
    assert len(gateway.proposals) == 1
    assert handle.events[-2]["eventType"] == "card.proposed"
    assert handle.events[-1]["eventType"] == "execution.completed"


@pytest.mark.parametrize("outcome", ["STOPPED", "STALE", "DENY", "UNAVAILABLE", "CANCELLED", "MISMATCH", "INVALID_STATE"])
async def test_dispatch_rechecks_authority_and_execution_before_air(client: Any, outcome: str) -> None:
    air = FakeEmploymentAirGateway()
    app.state.employment_air_gateway = air
    gateway = app.state.conversation_constitutional_gateway
    original_authorize = gateway.authorize_execution
    calls = 0

    async def authorize(*args: Any) -> ConstitutionalDecision:
        nonlocal calls
        calls += 1
        if calls == 1:
            return await original_authorize(*args)
        if outcome == "UNAVAILABLE":
            raise ConstitutionalGatewayUnavailableError()
        if outcome == "CANCELLED":
            handle = next(iter(app.state.temporal_client.handles.values()))
            handle.state.update(state="CANCELLED", completionReason="CANCELLED")
            return ConstitutionalDecision.ALLOW
        if outcome in {"MISMATCH", "INVALID_STATE"}:
            handle = next(iter(app.state.temporal_client.handles.values()))
            if outcome == "MISMATCH":
                handle.state["messageId"] = str(uuid.uuid4())
            else:
                handle.state["state"] = "UNKNOWN"
            return ConstitutionalDecision.ALLOW
        return ConstitutionalDecision(outcome)

    gateway.authorize_execution = authorize
    response = await client.post(
        f"/api/v1/internal/conversations/{uuid.uuid4()}/executions",
        headers=_headers(_service_token()),
        json=_body(),
    )
    assert response.status_code == 202
    handle = next(iter(app.state.temporal_client.handles.values()))
    if outcome == "UNAVAILABLE":
        with pytest.raises(ConstitutionalGatewayUnavailableError):
            await ConversationDispatchActivity(app).dispatch(handle.workflow_input)
    else:
        await ConversationDispatchActivity(app).dispatch(handle.workflow_input)
    assert calls == 2
    assert not air.proposals
    if outcome == "STOPPED":
        assert handle.state["state"] == "STOPPED"
        assert handle.events[-1]["eventType"] == "execution.stopped"
    elif outcome == "CANCELLED":
        assert handle.state["state"] == "CANCELLED"
    elif outcome != "UNAVAILABLE":
        assert handle.events[-1]["eventType"] == "reconciliation.required"


async def test_dispatch_rejects_mandate_expiring_during_authority_recheck(client: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    air = FakeEmploymentAirGateway()
    app.state.employment_air_gateway = air
    valid_mandate = conversation_router._mandate_is_valid
    checks = 0

    def mandate_valid(*args: Any) -> bool:
        nonlocal checks
        checks += 1
        return checks < 3 and valid_mandate(*args)

    monkeypatch.setattr(conversation_router, "_mandate_is_valid", mandate_valid)
    _, execution = await _start(client)
    handle = app.state.temporal_client.handles[execution["executionId"]]
    assert checks == 3
    assert not air.proposals
    assert handle.events[-1]["eventType"] == "reconciliation.required"


async def test_dispatch_query_failure_returns_unavailable_without_calling_air(client: Any) -> None:
    air = FakeEmploymentAirGateway()
    app.state.employment_air_gateway = air
    gateway = app.state.conversation_constitutional_gateway
    original_authorize = gateway.authorize_execution
    calls = 0

    async def authorize(*args: Any) -> ConstitutionalDecision:
        nonlocal calls
        calls += 1
        if calls == 2:
            handle = next(iter(app.state.temporal_client.handles.values()))
            handle.query = AsyncMock(side_effect=RPCError("unavailable", RPCStatusCode.UNAVAILABLE, b""))
        return await original_authorize(*args)

    gateway.authorize_execution = authorize
    response = await client.post(
        f"/api/v1/internal/conversations/{uuid.uuid4()}/executions",
        headers=_headers(_service_token()),
        json=_body(),
    )
    assert response.status_code == 202
    handle = next(iter(app.state.temporal_client.handles.values()))
    with pytest.raises(RPCError):
        await ConversationDispatchActivity(app).dispatch(handle.workflow_input)
    assert not air.proposals


@pytest.mark.parametrize("malformed_at", ["propose", "get"])
async def test_malformed_air_response_requires_reconciliation(client: Any, malformed_at: str) -> None:
    gateway = FakeEmploymentAirGateway()
    if malformed_at == "propose":
        gateway.propose = AsyncMock(return_value=SimpleNamespace(raise_for_status=lambda: None, json=lambda: []))
    else:
        gateway.get = AsyncMock(return_value=SimpleNamespace(raise_for_status=lambda: None, json=lambda: []))
    app.state.employment_air_gateway = gateway

    _, execution = await _start(client)

    handle = app.state.temporal_client.handles[execution["executionId"]]
    assert handle.events[-1]["eventType"] == "reconciliation.required"
    assert handle.events[-1]["data"] == {"reason": "STATE_CONFLICT"}


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("relationshipRef", "other-relationship"),
        ("contributionRef", "00000000-0000-0000-0000-000000000099"),
        ("requestDigest", "0" * 64),
        ("semanticCatalogue", {"ref": "wrong", "version": "1", "digest": "a" * 64}),
        ("proposalId", "not-a-uuid"),
    ],
)
async def test_mismatched_air_proposal_is_not_published(client: Any, field: str, replacement: object) -> None:
    gateway = FakeEmploymentAirGateway()
    original_get = gateway.get

    async def mismatched_get(context: Any, proposal_id: uuid.UUID) -> Any:
        response = await original_get(context, proposal_id)
        proposal = response.json()
        proposal[field] = replacement
        return SimpleNamespace(raise_for_status=lambda: None, json=lambda: proposal)

    gateway.get = mismatched_get
    app.state.employment_air_gateway = gateway
    _, execution = await _start(client)
    handle = app.state.temporal_client.handles[execution["executionId"]]
    assert handle.events[-1]["eventType"] == "reconciliation.required"
    assert not any(event["eventType"] == "card.proposed" for event in handle.events)


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
    body = _body(idempotencyIdentity=key)
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


async def test_batch_start_replays_exact_request_and_rejects_stale_or_divergent_work(
    client: Any,
) -> None:
    body = _batch_body()
    key = uuid.UUID(body["batchId"])
    relationship_id = uuid.uuid4()
    for source in body["sources"]:
        source["operationalMandate"]["relationshipId"] = str(relationship_id)
        _refresh_batch_mandate_digest(source["operationalMandate"])
    _refresh_batch_source_digest(body)
    conversation_id = uuid.uuid4()
    url = f"/api/v1/internal/conversations/{conversation_id}/batch-executions"
    headers = _headers(_service_token(relationship_id=str(relationship_id)), key)
    store = app.state.relationship_execution_store
    temporal = app.state.temporal_client

    context_override = app.dependency_overrides[get_conversation_service_context]
    app.dependency_overrides[get_conversation_service_context] = lambda: None
    not_accessible = await client.post(url, headers=headers, json=body)
    app.dependency_overrides[get_conversation_service_context] = context_override
    wrong_key = await client.post(
        url,
        headers=_headers(
            _service_token(relationship_id=str(relationship_id)),
            uuid.uuid4(),
        ),
        json=body,
    )
    store.is_current_work_item.return_value = False
    stale = await client.post(url, headers=headers, json=body)
    store.is_current_work_item.return_value = True
    first = await client.post(url, headers=headers, json=body)
    replay = await client.post(url, headers=headers, json=body)
    divergent = await client.post(
        url,
        headers=headers,
        json={**body, "locale": "hi-IN"},
    )
    batch_execution = temporal.handles[first.json()["executionId"]].workflow_input
    with pytest.raises(ValueError, match="admitted professional response"):
        await ConversationDispatchActivity(app).dispatch(batch_execution)
    app.state.conversation_constitutional_gateway = FakeConstitutionalGateway(decision=ConstitutionalDecision.STOPPED)
    stopped = await client.post(url, headers=headers, json=body)
    app.state.conversation_constitutional_gateway = FakeConstitutionalGateway(ready=False)
    unavailable = await client.post(url, headers=headers, json=body)
    failed_gateway = FakeConstitutionalGateway()
    failed_gateway.authorize_execution = AsyncMock(side_effect=ConstitutionalGatewayUnavailableError)
    app.state.conversation_constitutional_gateway = failed_gateway
    constitutional_failure = await client.post(url, headers=headers, json=body)
    app.state.conversation_constitutional_gateway = FakeConstitutionalGateway()
    app.state.temporal_client = None
    runtime_unavailable = await client.post(url, headers=headers, json=body)
    app.state.temporal_client = temporal
    app.state.conversation_constitutional_gateway = None
    gateway_unavailable = await client.post(url, headers=headers, json=body)

    assert not_accessible.status_code == 401
    assert wrong_key.status_code == 409
    assert stale.status_code == 409
    assert stale.json()["code"] == "EXECUTION_MANDATE_INVALID"
    assert first.status_code == 202
    assert replay.status_code == 200
    assert replay.json()["replayed"] is True
    assert divergent.status_code == 409
    assert divergent.json()["code"] == "EXECUTION_IDEMPOTENCY_CONFLICT"
    assert stopped.status_code == 423
    assert unavailable.status_code == 503
    assert constitutional_failure.status_code == 503
    assert runtime_unavailable.status_code == 503
    assert gateway_unavailable.status_code == 503
    assert len(temporal.started) == 1


async def test_durable_dispatch_requires_temporal_and_constitutional_dependencies(
    client: Any,
) -> None:
    _, receipt = await _start(client)
    temporal = app.state.temporal_client
    gateway = app.state.conversation_constitutional_gateway
    execution = temporal.handles[receipt["executionId"]].workflow_input

    with pytest.raises(RuntimeError, match="dependencies unavailable"):
        await ConversationDispatchActivity(app).dispatch(replace(execution, dispatch=None))
    app.state.temporal_client = None
    with pytest.raises(RuntimeError, match="dependencies unavailable"):
        await ConversationDispatchActivity(app).dispatch(execution)
    app.state.temporal_client = temporal
    app.state.conversation_constitutional_gateway = None
    with pytest.raises(RuntimeError, match="dependencies unavailable"):
        await ConversationDispatchActivity(app).dispatch(execution)
    app.state.conversation_constitutional_gateway = gateway


@pytest.mark.parametrize("has_result", [True, False])
async def test_legacy_replay_records_reconciliation_without_redispatch(client: Any, has_result: bool) -> None:
    key = uuid.uuid4()
    body = _body(idempotencyIdentity=key)
    conversation_id = uuid.uuid4()
    url = f"/api/v1/internal/conversations/{conversation_id}/executions"
    headers = _headers(_service_token(), key)
    first = await client.post(url, headers=headers, json=body)
    handle = app.state.temporal_client.handles[first.json()["executionId"]]
    handle.state["legacyDispatchNeedsReconciliation"] = True
    gateway = FakeEmploymentAirGateway()
    payload = conversation_router._employment_proposal_payload(
        conversation_router.StartExecutionRequestV1.model_validate(body),
        BPServiceContext("contract-a", "tenant-a", "relationship-a", "participant-a", "CUSTOMER"),
    )
    gateway.proposals.append({"payload": payload})
    gateway.reconcile = AsyncMock(
        return_value=httpx.Response(
            200 if has_result else 503,
            json={
                **payload,
                "state": "PROPOSED",
                "proposalId": str(gateway.proposal_id),
                "operations": [{"op": "ADD", "semanticPath": "goal.objective", "value": "synthetic objective"}],
            }
            if has_result
            else {"code": "AIR_EMPLOYMENT_RECONCILIATION_REQUIRED"},
            request=httpx.Request("POST", "https://air.test/reconcile"),
        )
    )
    app.state.employment_air_gateway = gateway
    replay = await client.post(url, headers=headers, json=body)
    assert replay.status_code == 200
    assert len(app.state.temporal_client.started) == 1
    assert handle.signals[-1][0] == "AppendConversationExecutionEvent"
    signal = handle.signals[-2 if has_result else -1][1]
    assert signal.event_type == ("card.proposed" if has_result else "reconciliation.required")
    assert signal.dispatch_result_key == f"employment-proposal:{first.json()['executionId']}"
    assert len(gateway.proposals) == 1
    gateway.reconcile.assert_awaited_once()


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
    whatsapp_body = _body()
    web_body = _body()
    for body in (whatsapp_body, web_body):
        mandate = body["operationalMandate"]
        mandate["relationshipId"] = "relationship-shared"
        canonical = json.dumps(
            {name: item for name, item in mandate.items() if name != "mandateDigest"},
            separators=(",", ":"),
            sort_keys=True,
        ).encode()
        mandate["mandateDigest"] = f"sha256:{hashlib.sha256(canonical).hexdigest()}"

    whatsapp = await client.post(
        f"/api/v1/internal/conversations/{whatsapp_conversation}/executions",
        headers=_headers(token),
        json=whatsapp_body,
    )
    web = await client.post(
        f"/api/v1/internal/conversations/{web_conversation}/executions",
        headers=_headers(token),
        json=web_body,
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
        str(uuid.uuid4()),
        "sha256:" + "11" * 32,
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


@pytest.mark.parametrize("stop", [False, True])
async def test_durable_dispatch_is_scheduled_once_and_stop_cancels_it(monkeypatch: pytest.MonkeyPatch, stop: bool) -> None:
    workflow = ConversationExecutionWorkflow()
    pending = asyncio.get_running_loop().create_future()
    start_activity = MagicMock(return_value=pending)
    monkeypatch.setattr(workflow_module.workflow, "start_activity", start_activity)
    monkeypatch.setattr(workflow_module.workflow, "wait_condition", AsyncMock())
    execution_input = ConversationExecutionInput(
        "1.0",
        str(uuid.uuid4()),
        str(uuid.uuid4()),
        str(uuid.uuid4()),
        "tenant-a",
        "relationship-a",
        "participant-a",
        "CUSTOMER",
        str(uuid.uuid4()),
        "sha256:" + "11" * 32,
        1,
        "en-IN",
        {"text": "x"},
        None,
        "request-hash",
        _now(),
        {"body": {}},
    )
    run = asyncio.create_task(workflow.run(execution_input))
    await asyncio.sleep(0)
    start_activity.assert_called_once()
    assert start_activity.call_args.args == ("DispatchConversationEmploymentProposal", execution_input)
    assert start_activity.call_args.kwargs["retry_policy"].maximum_attempts == 3
    assert start_activity.call_args.kwargs["heartbeat_timeout"].total_seconds() == 6
    if stop:
        await workflow.emergency_stop(_now())
    else:
        pending.set_result(None)
    result = await run
    assert result["state"] == ("STOPPED" if stop else "ACCEPTED")
    assert pending.cancelled() is stop


async def test_dispatch_activity_heartbeats_and_cancels_inflight_request(client: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    _, execution = await _start(client)
    execution_input = app.state.temporal_client.handles[execution["executionId"]].workflow_input
    dispatched = asyncio.Event()
    heartbeat = asyncio.Event()
    cancelled = asyncio.Event()

    async def pending_dispatch(*_args: Any, **_kwargs: Any) -> None:
        dispatched.set()
        try:
            await asyncio.Event().wait()
        finally:
            cancelled.set()

    monkeypatch.setattr(dispatch_module, "_dispatch_employment_proposal", pending_dispatch)
    environment = ActivityEnvironment()
    environment.info = replace(environment.info, heartbeat_timeout=timedelta(seconds=1))
    environment.on_heartbeat = lambda *_args: heartbeat.set()
    running = asyncio.create_task(environment.run(ConversationDispatchActivity(app).dispatch, execution_input))
    await asyncio.wait_for(dispatched.wait(), 1)
    await asyncio.wait_for(heartbeat.wait(), 1)
    environment.cancel()
    with pytest.raises(asyncio.CancelledError):
        await running
    assert cancelled.is_set()


async def test_dispatch_result_signal_replay_is_idempotent_and_conflicts_are_visible(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(workflow_module.workflow, "wait_condition", AsyncMock())
    workflow = ConversationExecutionWorkflow()
    await workflow.run(
        ConversationExecutionInput(
            "1.0",
            str(uuid.uuid4()),
            str(uuid.uuid4()),
            str(uuid.uuid4()),
            "tenant-a",
            "relationship-a",
            "participant-a",
            "CUSTOMER",
            str(uuid.uuid4()),
            "sha256:" + "11" * 32,
            1,
            "en-IN",
            {"text": "x"},
            None,
            "request-hash",
            _now(),
        )
    )
    first = ExecutionEventSignal("card.proposed", {"cardId": "one"}, _now(), "dispatch-1")
    await workflow.append_event(first)
    await workflow.append_event(ExecutionEventSignal("card.proposed", {"cardId": "one"}, _now(), "dispatch-1"))
    assert [event["eventType"] for event in workflow.events()] == ["execution.accepted", "card.proposed"]
    await workflow.append_event(ExecutionEventSignal("card.proposed", {"cardId": "two"}, _now(), "dispatch-1"))
    assert workflow.events()[-1]["eventType"] == "reconciliation.required"


@pytest.mark.parametrize("prior_result", [False, True])
async def test_legacy_reconciliation_is_idempotent_and_does_not_override_result(
    monkeypatch: pytest.MonkeyPatch, prior_result: bool
) -> None:
    monkeypatch.setattr(workflow_module.workflow, "wait_condition", AsyncMock())
    workflow = ConversationExecutionWorkflow()
    execution_id = str(uuid.uuid4())
    await workflow.run(
        ConversationExecutionInput(
            "1.0",
            execution_id,
            str(uuid.uuid4()),
            str(uuid.uuid4()),
            "tenant-a",
            "relationship-a",
            "participant-a",
            "CUSTOMER",
            str(uuid.uuid4()),
            "sha256:" + "11" * 32,
            1,
            "en-IN",
            {"text": "x"},
            None,
            "request-hash",
            _now(),
        )
    )
    assert workflow.state()["legacyDispatchNeedsReconciliation"] is True
    if prior_result:
        await workflow.append_event(ExecutionEventSignal("card.proposed", {"cardId": "one"}, _now()))
    signal = ExecutionEventSignal(
        "reconciliation.required",
        {"reason": "STATE_CONFLICT"},
        _now(),
        f"legacy-dispatch-reconciliation:{execution_id}",
    )
    await workflow.append_event(signal)
    await workflow.append_event(signal)
    assert [event["eventType"] for event in workflow.events()] == [
        "execution.accepted",
        "card.proposed" if prior_result else "reconciliation.required",
    ]
    assert workflow.state()["legacyDispatchNeedsReconciliation"] is not prior_result
    assert workflow.state()["dispatchNeedsReconciliation"] is not prior_result


async def test_known_result_can_resolve_prior_unknown_outcome_without_conflicting_replay(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(workflow_module.workflow, "wait_condition", AsyncMock())
    workflow = ConversationExecutionWorkflow()
    execution_id = str(uuid.uuid4())
    await workflow.run(
        ConversationExecutionInput(
            "1.0",
            execution_id,
            str(uuid.uuid4()),
            str(uuid.uuid4()),
            "tenant-a",
            "relationship-a",
            "participant-a",
            "CUSTOMER",
            str(uuid.uuid4()),
            "sha256:" + "11" * 32,
            1,
            "en-IN",
            {"text": "x"},
            None,
            "request-hash",
            _now(),
        )
    )
    key = f"employment-proposal:{execution_id}"
    await workflow.append_event(
        ExecutionEventSignal(
            "reconciliation.required",
            {"reason": "STATE_CONFLICT"},
            _now(),
            key,
        )
    )
    result = ExecutionEventSignal("card.proposed", {"cardId": "one"}, _now(), key)
    await workflow.append_event(result)
    await workflow.append_event(result)
    await workflow.append_event(
        ExecutionEventSignal(
            "reconciliation.required",
            {"reason": "STATE_CONFLICT"},
            _now(),
            key,
        )
    )
    assert [event["eventType"] for event in workflow.events()] == [
        "execution.accepted",
        "reconciliation.required",
        "card.proposed",
    ]
    assert workflow.state()["dispatchNeedsReconciliation"] is False


@pytest.mark.parametrize("recorded", [True, False])
async def test_exhausted_activity_records_reconciliation_only_without_durable_result(
    monkeypatch: pytest.MonkeyPatch, recorded: bool
) -> None:
    workflow = ConversationExecutionWorkflow()
    pending = asyncio.get_running_loop().create_future()
    monkeypatch.setattr(workflow_module.workflow, "start_activity", MagicMock(return_value=pending))
    monkeypatch.setattr(workflow_module.workflow, "wait_condition", AsyncMock())
    monkeypatch.setattr(workflow_module.workflow, "now", MagicMock(return_value=datetime.now(timezone.utc)))
    execution_id = str(uuid.uuid4())
    execution_input = ConversationExecutionInput(
        "1.0",
        execution_id,
        str(uuid.uuid4()),
        str(uuid.uuid4()),
        "tenant-a",
        "relationship-a",
        "participant-a",
        "CUSTOMER",
        str(uuid.uuid4()),
        "sha256:" + "11" * 32,
        1,
        "en-IN",
        {"text": "x"},
        None,
        "request-hash",
        _now(),
        {"body": {}},
    )
    run = asyncio.create_task(workflow.run(execution_input))
    await asyncio.sleep(0)
    if recorded:
        await workflow.append_event(
            ExecutionEventSignal("card.proposed", {"cardId": "one"}, _now(), f"employment-proposal:{execution_id}")
        )
    pending.set_exception(
        ActivityError(
            "dispatch failed",
            scheduled_event_id=1,
            started_event_id=2,
            identity="worker",
            activity_type="dispatch",
            activity_id="1",
            retry_state=None,
        )
    )
    await run
    assert [event["eventType"] for event in workflow.events()] == (
        ["execution.accepted", "card.proposed"] if recorded else ["execution.accepted", "reconciliation.required"]
    )


async def test_stopped_before_run_does_not_schedule_dispatch(monkeypatch: pytest.MonkeyPatch) -> None:
    workflow = ConversationExecutionWorkflow()
    start_activity = MagicMock()
    monkeypatch.setattr(workflow_module.workflow, "start_activity", start_activity)
    monkeypatch.setattr(workflow_module.workflow, "wait_condition", AsyncMock())
    await workflow.emergency_stop(_now())
    result = await workflow.run(
        ConversationExecutionInput(
            "1.0",
            str(uuid.uuid4()),
            str(uuid.uuid4()),
            str(uuid.uuid4()),
            "tenant-a",
            "relationship-a",
            "participant-a",
            "CUSTOMER",
            str(uuid.uuid4()),
            "sha256:" + "11" * 32,
            1,
            "en-IN",
            {"text": "x"},
            None,
            "request-hash",
            _now(),
            {"body": {}},
        )
    )
    assert result["state"] == "STOPPED"
    assert [event["eventType"] for event in workflow.events()] == ["execution.accepted", "execution.stopped"]
    start_activity.assert_not_called()


async def test_start_stores_dispatch_input_before_http_response(client: Any) -> None:
    air = FakeEmploymentAirGateway()
    app.state.employment_air_gateway = air
    body = _body()
    response = await client.post(
        f"/api/v1/internal/conversations/{uuid.uuid4()}/executions",
        headers=_headers(_service_token()),
        json=body,
    )
    assert response.status_code == 202
    handle = app.state.temporal_client.handles[response.json()["executionId"]]
    assert handle.workflow_input.dispatch is not None
    assert handle.workflow_input.dispatch["body"]["messageId"] == body["messageId"]
    assert not air.proposals
    await ConversationDispatchActivity(app).dispatch(handle.workflow_input)
    assert len(air.proposals) == 1


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
        str(uuid.uuid4()),
        "sha256:" + "11" * 32,
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


@pytest.mark.parametrize(
    ("event_type", "state", "reason"),
    [
        ("execution.completed", "COMPLETED", "COMPLETE"),
        ("execution.failed", "FAILED", "PARTIAL_FAILURE"),
    ],
)
async def test_runtime_terminal_event_closes_real_workflow_and_cannot_be_overwritten(
    monkeypatch: pytest.MonkeyPatch,
    event_type: str,
    state: str,
    reason: str,
) -> None:
    monkeypatch.setattr(workflow_module.workflow, "wait_condition", AsyncMock())
    workflow = ConversationExecutionWorkflow()
    await workflow.run(
        ConversationExecutionInput(
            "1.0",
            str(uuid.uuid4()),
            str(uuid.uuid4()),
            str(uuid.uuid4()),
            "tenant-a",
            "relationship-a",
            "participant-a",
            "CUSTOMER",
            str(uuid.uuid4()),
            "sha256:" + "11" * 32,
            1,
            "en-IN",
            {"text": "x"},
            None,
            "request-hash",
            _now(),
        )
    )
    await workflow.append_event(
        ExecutionEventSignal(
            "processing.started",
            {"serverTime": _now()},
            _now(),
        )
    )
    assert workflow.state()["state"] == "RUNNING"
    await workflow.append_event(
        ExecutionEventSignal(
            event_type,
            {"state": state, "partial": False, "completionReason": reason},
            _now(),
        )
    )
    count = len(workflow.events())
    await workflow.cancel(CancellationSignal("late", "hash", _now()))
    await workflow.append_event(
        ExecutionEventSignal(
            "response.delta",
            {"contentIndex": 0, "appendText": "late", "partial": True},
            _now(),
        )
    )
    assert len(workflow.events()) == count
    assert workflow.state()["state"] == state
    assert workflow.state()["completionReason"] == reason
    assert workflow._terminal is True
    await workflow.emergency_stop(_now())
    assert workflow.state()["state"] == "STOPPED"


@pytest.mark.parametrize(
    ("event_type", "data"),
    [
        ("execution.completed", {"state": "FAILED", "partial": False, "completionReason": "COMPLETE"}),
        ("execution.failed", {"state": "FAILED", "partial": "false", "completionReason": "PARTIAL_FAILURE"}),
        ("execution.cancelled", {"state": "CANCELLED", "partial": False, "completionReason": "CANCELLED"}),
        ("execution.stopped", {"state": "STOPPED", "partial": False, "completionReason": "EMERGENCY_STOPPED"}),
    ],
)
async def test_invalid_terminal_signal_records_conflict_without_closing_workflow(
    monkeypatch: pytest.MonkeyPatch,
    event_type: str,
    data: dict[str, Any],
) -> None:
    monkeypatch.setattr(workflow_module.workflow, "wait_condition", AsyncMock())
    workflow = ConversationExecutionWorkflow()
    await workflow.run(
        ConversationExecutionInput(
            "1.0",
            str(uuid.uuid4()),
            str(uuid.uuid4()),
            str(uuid.uuid4()),
            "tenant-a",
            "relationship-a",
            "participant-a",
            "CUSTOMER",
            str(uuid.uuid4()),
            "sha256:" + "11" * 32,
            1,
            "en-IN",
            {"text": "x"},
            None,
            "request-hash",
            _now(),
        )
    )
    await workflow.append_event(ExecutionEventSignal(event_type, data, _now()))
    assert workflow.state()["state"] == "ACCEPTED"
    assert workflow.state()["completionReason"] is None
    assert workflow.events()[-1]["eventType"] == "reconciliation.required"
    assert workflow.events()[-1]["data"] == {"reason": "STATE_CONFLICT"}
    assert workflow._terminal is False


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
    auth = app.state.relationship_workload_auth
    app.state.relationship_workload_auth = None
    missing_auth = await client.get("/health")
    app.state.relationship_workload_auth = auth
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


async def test_non_conversation_validation_uses_problem_contract() -> None:
    request = MagicMock()
    request.url.path = "/other"
    request.headers = {}
    response = await validation_error(request, RequestValidationError([]))
    assert response.status_code == 400
    assert response.media_type == "application/problem+json"


async def test_lifespan_registers_conversation_worker(monkeypatch: pytest.MonkeyPatch) -> None:
    temporal = MagicMock(namespace="default")
    temporal.workflow_service.describe_namespace = AsyncMock()
    connected = AsyncMock(return_value=temporal)
    gateway = MagicMock(close=AsyncMock())
    gateway_factory = MagicMock(return_value=gateway)

    class FakeWorker:
        instances: ClassVar[list[FakeWorker]] = []

        def __init__(self, client: Any, *, task_queue: str, workflows: list[type[Any]], activities: list[Any]) -> None:
            self.client = client
            self.task_queue = task_queue
            self.workflows = workflows
            self.activities = activities
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
        assert len(worker.activities) == 1
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
    temporal = MagicMock(namespace="default")
    temporal.workflow_service.describe_namespace = AsyncMock()
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


async def test_lifespan_retries_until_temporal_namespace_is_ready(monkeypatch: pytest.MonkeyPatch) -> None:
    temporal = MagicMock(namespace="default")
    temporal.workflow_service.describe_namespace = AsyncMock(
        side_effect=[ValueError("namespace unavailable"), None],
    )
    worker_stopped = asyncio.Event()
    worker = MagicMock()

    async def run_worker() -> None:
        await worker_stopped.wait()

    async def stop_worker() -> None:
        worker_stopped.set()

    worker.run = run_worker
    worker.shutdown = stop_worker
    connect = AsyncMock(return_value=temporal)
    monkeypatch.setattr(main_module, "connect_temporal_client", connect)
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

    assert connect.await_count == 2
    assert temporal.workflow_service.describe_namespace.await_count == 2


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
    batch_source = canonical["components"]["schemas"]["BatchExecutionSourceV1"]
    assert {
        "workItemId",
        "workItemRevision",
        "workItemInvocationId",
    } <= set(batch_source["required"])
    assert batch_source["properties"]["workItemId"]["format"] == "uuid"
    assert batch_source["properties"]["workItemRevision"]["minimum"] == 1
    assert batch_source["properties"]["workItemInvocationId"]["format"] == "uuid"
    operations = {
        "/api/v1/internal/conversations/{conversationId}/executions": "post",
        "/api/v1/internal/conversations/{conversationId}/batch-executions": "post",
        "/api/v1/internal/conversations/{conversationId}/executions/{executionId}/stream": "get",
        "/api/v1/internal/conversations/{conversationId}/executions/{executionId}": "delete",
        "/api/v1/internal/conversations/{conversationId}/executions/{executionId}/reconcile": "post",
    }
    for path, method in operations.items():
        expected = canonical["paths"][path][method]
        actual = generated["paths"][path][method]
        assert actual["operationId"] == expected["operationId"]
        assert set(actual["responses"]) == set(expected["responses"])
        assert actual["x-internal"] is True
        assert actual["security"] == [{"WorkloadMutualTLS": [], "DelegatedContextAuth": []}]
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
    for scheme in ("DelegatedContextAuth", "WorkloadMutualTLS"):
        assert generated["components"]["securitySchemes"][scheme] == canonical["components"]["securitySchemes"][scheme]
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
        "ReconcileConversationExecutionRequestV1",
        "ConversationExecutionReconciliationV1",
    ):
        assert generated["components"]["schemas"][schema_name] == canonical["components"]["schemas"][schema_name]
    assert "/api/v1/paas/sessions" in generated["paths"]
    assert "HTTPValidationError" in generated["components"]["schemas"]
    assert generated["paths"]["/health"]["get"]["security"] == []
    assert generated["paths"]["/health"]["get"]["responses"] == canonical["paths"]["/health"]["get"]["responses"]


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


def test_emergency_stop_rest_confirms_only_from_ce_evidence() -> None:
    contract_id = "11111111-1111-1111-1111-111111111111"
    session_id = "22222222-2222-2222-2222-222222222222"
    validator = MagicMock(validate=AsyncMock(return_value=EmergencyStopAuthority("tenant-a", "customer-a", contract_id)))
    gateway = FakeEmergencyStopGateway()
    app.state.emergency_stop_jwt_validator = validator
    app.state.conversation_constitutional_gateway = gateway

    response = TestClient(app).post(
        "/api/v1/emergency-stop",
        headers={"Authorization": "Bearer valid"},
        json={"contractId": contract_id, "activeSessionIds": [session_id]},
    )

    assert response.status_code == 200
    assert response.json() == {
        "emergencyStopRecordId": "11111111-1111-1111-1111-111111111111",
        "affectedSessions": [session_id],
        "confirmedAt": "2026-08-10T01:02:03.456000Z",
    }
    validator.validate.assert_awaited_once_with("valid")
    assert gateway.stop_requests == [
        {
            "contract_id": contract_id,
            "tenant_id": "tenant-a",
            "stopped_by": "customer-a",
            "active_session_ids": [session_id],
        }
    ]


@pytest.mark.parametrize(
    ("validator", "authorization"),
    [
        (None, "Bearer valid"),
        (FakeEmergencyStopJWTValidator(), None),
        (FakeEmergencyStopJWTValidator(), "Basic invalid"),
        (FakeEmergencyStopJWTValidator(valid=False), "Bearer invalid"),
    ],
)
def test_emergency_stop_rest_rejects_missing_or_invalid_auth(
    validator: FakeEmergencyStopJWTValidator | None,
    authorization: str | None,
) -> None:
    app.state.emergency_stop_jwt_validator = validator
    headers = {"Authorization": authorization} if authorization is not None else {}

    response = TestClient(app).post(
        "/api/v1/emergency-stop",
        headers=headers,
        json={"contractId": "11111111-1111-1111-1111-111111111111"},
    )

    assert response.status_code == 401


def test_emergency_stop_rest_hides_unauthorized_contract() -> None:
    app.state.conversation_constitutional_gateway = FakeEmergencyStopGateway()

    response = TestClient(app).post(
        "/api/v1/emergency-stop",
        headers={"Authorization": "Bearer valid"},
        json={"contractId": "11111111-1111-1111-1111-111111111111"},
    )

    assert response.status_code == 404


@pytest.mark.parametrize("gateway", [None, FakeEmergencyStopGateway(failure=True)])
def test_emergency_stop_rest_fails_closed_without_ce_confirmation(
    gateway: FakeEmergencyStopGateway | None,
) -> None:
    contract_id = "11111111-1111-1111-1111-111111111111"
    app.state.emergency_stop_jwt_validator = MagicMock(
        validate=AsyncMock(return_value=EmergencyStopAuthority("tenant-a", "customer-a", contract_id))
    )
    app.state.conversation_constitutional_gateway = gateway

    response = TestClient(app).post(
        "/api/v1/emergency-stop",
        headers={"Authorization": "Bearer valid"},
        json={"contractId": contract_id},
    )

    assert response.status_code == 503


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
                pending_sessions=[],
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


async def test_grpc_gateway_does_not_confirm_pending_stop_propagation() -> None:
    recorded_at = MagicMock()
    recorded_at.ToDatetime.return_value = datetime(2026, 8, 10, tzinfo=timezone.utc)
    stub = MagicMock(
        TriggerEmergencyStop=AsyncMock(
            return_value=SimpleNamespace(
                emergency_stop_record_id="EMERGENCY_STOP:persisted",
                affected_sessions=["session-a"],
                recorded_at=recorded_at,
                pending_sessions=["session-a"],
            )
        )
    )
    gateway = GrpcConversationConstitutionalGateway(
        "unused",
        channel=MagicMock(),
        stub=stub,
        protobuf=SimpleNamespace(EmergencyStopRequest=lambda **values: SimpleNamespace(**values)),
    )
    with pytest.raises(ConstitutionalGatewayUnavailableError):
        await gateway.trigger_emergency_stop(
            contract_id="contract-a",
            tenant_id="tenant-a",
            stopped_by="customer-a",
            active_session_ids=["session-a"],
        )
    stub.TriggerEmergencyStop.assert_awaited_once()


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
        "EXECUTION_MANDATE_INVALID",
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
