# Implements: WC134-R006, WC134-R014, WC134-R019; ADR-046
# constitutional_basis: C-023, C-026, C-059, C-063, C-083, C-084, C-085

from __future__ import annotations

import hashlib
import json
import time
import uuid
from dataclasses import replace
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import yaml
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from starlette.types import ASGIApp, Receive, Scope, Send

from relationship_workspace import WorkloadAuth
from routers.conversation_execution import EXECUTION_ID_NAMESPACE, router
from test_conversation_execution import FakeConstitutionalGateway, FakeTemporalClient, _body
from test_workload_identity import _certificate
from workload_identity import (
    DelegatedContext,
    DelegatedContextVerifier,
    PEER_CERTIFICATE_STATE_KEY,
    ReplayStore,
    RouteGrant,
    sign_delegated_context,
)

TRUST_DOMAIN = "waooaw.ci"
BP_URI = f"spiffe://{TRUST_DOMAIN}/workload/business-platform"
AUDIENCE = "urn:waooaw:service:professional-runtime"
START_ROUTE = "/api/v1/internal/conversations/{conversationId}/executions"
BATCH_ROUTE = "/api/v1/internal/conversations/{conversationId}/batch-executions"
CANCEL_ROUTE = START_ROUTE + "/{executionId}"
RECONCILE_ROUTE = CANCEL_ROUTE + "/reconcile"
STREAM_ROUTE = CANCEL_ROUTE + "/stream"
GRANTS = frozenset(
    {
        RouteGrant(BP_URI, AUDIENCE, "POST", START_ROUTE, "startConversationExecution", 1),
        RouteGrant(BP_URI, AUDIENCE, "POST", BATCH_ROUTE, "startConversationBatchExecution", 1),
        RouteGrant(
            BP_URI,
            AUDIENCE,
            "POST",
            RECONCILE_ROUTE,
            "reconcileConversationExecutionInternal",
            1,
        ),
        RouteGrant(BP_URI, AUDIENCE, "DELETE", CANCEL_ROUTE, "cancelConversationExecutionInternal", 1),
        RouteGrant(BP_URI, AUDIENCE, "GET", STREAM_ROUTE, "streamConversationExecution", 1),
    }
)


class PeerCertificateTransport:
    def __init__(self, application: ASGIApp, certificate: bytes | None) -> None:
        self.application = application
        self.certificate = certificate

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if self.certificate is not None:
            scope.setdefault("state", {})[PEER_CERTIFICATE_STATE_KEY] = self.certificate
        await self.application(scope, receive, send)


class SignedExecution:
    def __init__(self) -> None:
        self.key = ec.generate_private_key(ec.SECP256R1())
        self.app = FastAPI()
        self.app.include_router(router)
        self.app.state.relationship_workload_auth = WorkloadAuth(
            DelegatedContextVerifier(GRANTS, {(BP_URI, "test-key"): self.key.public_key()}, ReplayStore()),
            TRUST_DOMAIN,
            AUDIENCE,
        )
        self.temporal = FakeTemporalClient()
        self.app.state.temporal_client = self.temporal
        self.app.state.temporal_worker_task = MagicMock(done=MagicMock(return_value=False))
        self.app.state.conversation_constitutional_gateway = FakeConstitutionalGateway()
        self.app.state.employment_air_gateway = None
        self.app.state.conversation_stream_poll_seconds = 0
        self.app.state.conversation_stream_heartbeat_seconds = 60
        self.certificate = _certificate(BP_URI).public_bytes(serialization.Encoding.DER)
        self.conversation_id = uuid.uuid4()
        self.body = _body()
        self.start_key = uuid.UUID(self.body["operationalMandate"]["idempotencyIdentity"])
        self.execution_id = uuid.uuid5(
            EXECUTION_ID_NAMESPACE,
            f"tenant-a:relationship-a:participant-a:{self.conversation_id}:{self.start_key}",
        )

    def context(self, method: str = "POST", **changes: object) -> DelegatedContext:
        now = int(time.time())
        route, operation = {
            "POST": (START_ROUTE, "startConversationExecution"),
            "DELETE": (CANCEL_ROUTE, "cancelConversationExecutionInternal"),
            "GET": (STREAM_ROUTE, "streamConversationExecution"),
        }[method]
        canonical = (
            json.dumps(self.body, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode() if method == "POST" else b""
        )
        versions = {"constitutional_decision": "decision-a", "message": self.body["messageId"]}
        if method == "GET":
            versions["cursor"] = ""
        context = DelegatedContext(
            schema_version="1.0",
            key_id="test-key",
            issuer_uri=BP_URI,
            target_audience=AUDIENCE,
            method=method,
            route=route,
            operation=operation,
            contract_major=1,
            actor_subject="participant-a",
            actor_source="BP_SESSION",
            effective_role="CUSTOMER",
            tenant_id="tenant-a",
            relationship_id="relationship-a",
            purpose=operation,
            subject_reference=str(self.conversation_id),
            request_digest=hashlib.sha256(canonical).hexdigest(),
            command_id=str(self.execution_id),
            idempotency_key=str(self.start_key) if method == "POST" else str(uuid.uuid4()),
            expected_versions=versions,
            issued_at=now,
            not_before=now,
            expires_at=now + 60,
            envelope_id=str(uuid.uuid4()),
            correlation_id=str(uuid.uuid4()),
        )
        return replace(context, **changes)

    async def send(
        self,
        context: DelegatedContext,
        *,
        certificate: bytes | None = None,
        omit_certificate: bool = False,
        token: str | None = None,
        body: object | None = None,
        cursor: str | None = None,
    ):
        peer = None if omit_certificate else certificate or self.certificate
        headers = {
            "Authorization": f"Bearer {token or sign_delegated_context(context, self.key)}",
            "X-Correlation-Id": context.correlation_id,
            "Idempotency-Key": context.idempotency_key or "",
        }
        if cursor is not None:
            headers["Last-Event-ID"] = cursor
        path = f"/api/v1/internal/conversations/{self.conversation_id}/executions"
        if context.method != "POST":
            path += f"/{self.execution_id}"
        if context.method == "GET":
            path += "/stream"
        async with AsyncClient(
            transport=ASGITransport(app=PeerCertificateTransport(self.app, peer)),
            base_url="https://runtime.test",
        ) as client:
            return await client.request(
                context.method,
                path,
                headers={**headers, "Content-Type": "application/json"},
                content=json.dumps(body or self.body, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode()
                if context.method == "POST"
                else None,
            )


@pytest.fixture
def signed_execution() -> SignedExecution:
    return SignedExecution()


async def test_signed_start_fresh_retry_cancel_and_stream_use_original_execution(signed_execution: SignedExecution) -> None:
    fixture = signed_execution
    fixture.body["content"]["text"] = "मराठी — 😀"
    first = await fixture.send(fixture.context())
    assert first.status_code == 202
    assert first.json()["executionId"] == str(fixture.execution_id)
    replay = await fixture.send(fixture.context())
    assert replay.status_code == 200
    assert replay.json()["replayed"] is True
    assert len(fixture.temporal.started) == 1
    cancelled = await fixture.send(fixture.context("DELETE"))
    assert cancelled.status_code == 202
    assert cancelled.json()["state"] == "CANCELLED"
    stream = await fixture.send(fixture.context("GET"))
    assert stream.status_code == 200
    assert "execution.cancelled" in stream.text


@pytest.mark.parametrize(
    "change",
    [
        {"issuer_uri": "spiffe://waooaw.ci/workload/browser"},
        {"target_audience": "urn:waooaw:service:billing-engine"},
        {"route": "/api/v1/internal/relationships/{relationshipId}/workspace-execution"},
        {"operation": "getRelationshipExecutionProjection"},
        {"request_digest": "b" * 64},
        {"actor_source": "CALLER_HEADER"},
        {"effective_role": ""},
        {"purpose": "OTHER"},
        {"subject_reference": str(uuid.uuid4())},
        {"command_id": str(uuid.uuid4())},
        {"expires_at": 1},
        {"expected_versions": {"message": str(uuid.uuid4())}},
        {"expected_versions": {"message": "different-message", "constitutional_decision": "decision-a"}},
    ],
)
async def test_wrong_envelope_binding_denies_before_temporal(signed_execution: SignedExecution, change: dict) -> None:
    result = await signed_execution.send(signed_execution.context(**change))
    assert result.status_code == 401
    assert result.json()["code"] == "EXECUTION_NOT_ACCESSIBLE"
    assert signed_execution.temporal.started == []
    assert signed_execution.app.state.conversation_constitutional_gateway.authorizations == []


async def test_missing_wrong_and_cross_environment_peer_denied(signed_execution: SignedExecution) -> None:
    fixture = signed_execution
    assert (await fixture.send(fixture.context(), omit_certificate=True)).status_code == 401
    for uri in (
        f"spiffe://{TRUST_DOMAIN}/workload/ai-runtime",
        "spiffe://demo.waooaw.internal/workload/business-platform",
    ):
        certificate = _certificate(uri).public_bytes(serialization.Encoding.DER)
        assert (await fixture.send(fixture.context(), certificate=certificate)).status_code == 401
    assert fixture.temporal.started == []


async def test_envelope_replay_denied_but_new_envelope_reuses_durable_outcome(signed_execution: SignedExecution) -> None:
    fixture = signed_execution
    context = fixture.context()
    assert (await fixture.send(context)).status_code == 202
    assert (await fixture.send(context)).status_code == 401
    assert (await fixture.send(fixture.context())).status_code == 200
    assert len(fixture.temporal.started) == 1


async def test_changed_body_and_legacy_jwt_cannot_authorize_execution(signed_execution: SignedExecution) -> None:
    fixture = signed_execution
    changed = {**fixture.body, "content": {**fixture.body["content"], "text": "changed"}}
    assert (await fixture.send(fixture.context(), body=changed)).status_code == 401
    assert (await fixture.send(fixture.context(), token="legacy.jwt.assertion")).status_code == 401
    assert fixture.temporal.started == []


async def test_cancel_and_stream_rebind_execution_and_cursor(signed_execution: SignedExecution) -> None:
    fixture = signed_execution
    assert (await fixture.send(fixture.context())).status_code == 202
    for method in ("DELETE", "GET"):
        result = await fixture.send(fixture.context(method, command_id=str(uuid.uuid4())))
        assert result.status_code == 401
        result = await fixture.send(
            fixture.context(method, expected_versions={"constitutional_decision": "decision-a", "message": "other", "cursor": ""})
        )
        assert result.status_code == 404
    result = await fixture.send(fixture.context("GET"), cursor="different-cursor")
    assert result.status_code == 401
    assert fixture.temporal.handles[str(fixture.execution_id)].signals == []


def test_registry_declares_only_exact_conversation_route_grants() -> None:
    registry = yaml.safe_load((Path(__file__).parents[2] / "infrastructure/workload-identity/registry.yaml").read_text())
    actual = {
        (grant["method"], grant["route"], grant["operation"], grant["contract_major"])
        for grant in registry["route_grants"]
        if grant["caller"] == "business-platform"
        and grant["target"] == "professional-runtime"
        and grant["route"].startswith("/api/v1/internal/conversations/")
    }
    assert actual == {(grant.method, grant.route, grant.operation, grant.contract_major) for grant in GRANTS}
