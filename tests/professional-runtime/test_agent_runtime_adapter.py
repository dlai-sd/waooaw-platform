"""WC-080 common adapter and generic Professional Runtime gateway proof."""

# Implements: architecture/agent-runtime-adapter-contract-v1-execution-plan.md §9
# Constitutional basis: C-023, C-035, C-059, C-065, C-071, C-079, C-080

from __future__ import annotations

import hashlib
import json
import threading
import time
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from adapter_gateway import (
    ActiveAdapterBinding,
    AdapterInvocationCoordinator,
    AdapterGatewayError,
    AdapterResolver,
    AgentRuntimeAdapterGateway,
    ResolvedAdapter,
)
from admission_guard import AdmissionActivationBinding
from digital_marketing import create_adapter as create_digital_marketing_adapter
from runtime_contract import (
    AdapterContractError,
    AdapterDescriptorV1,
    AdapterInvocationEnvelopeV1,
    InvocationState,
    ReferenceAdapter,
)
from trading import create_adapter as create_trading_adapter
from runtime_contract.http import create_app


def digest(payload: dict[str, Any]) -> str:
    value = json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True).encode()
    return f"sha256:{hashlib.sha256(value).hexdigest()}"


def envelope(descriptor: AdapterDescriptorV1, **changes: Any) -> AdapterInvocationEnvelopeV1:
    payload = {"inputReference": "opaque-input-1"}
    values: dict[str, Any] = {
        "schema_version": "1.0.0",
        "tenant_ref": "tenant-opaque-1",
        "relationship_id": str(uuid4()),
        "professional_type_id": descriptor.professional_type_id,
        "professional_version": descriptor.professional_version,
        "skill_id": next(iter(descriptor.skill_versions)),
        "skill_version": next(iter(descriptor.skill_versions.values())),
        "admission_content_digest": descriptor.admission_content_digest,
        "artifact_digest": descriptor.artifact_digest,
        "customer_contract_digest": "sha256:" + "31" * 32,
        "decision_space_version": "decision-space-7",
        "configuration_revision": "configuration-3",
        "goal_revision": "goal-4",
        "invocation_id": str(uuid4()),
        "idempotency_key": str(uuid4()),
        "payload_digest": digest(payload),
        "ce_decision_ref": "ce-decision-9",
        "evidence_context_ref": "evidence-context-2",
        "deadline": datetime.now(timezone.utc) + timedelta(minutes=1),
        "correlation_id": str(uuid4()),
        "mode": "LIVE",
    }
    values.update(changes)
    return AdapterInvocationEnvelopeV1(**values)


@pytest.mark.parametrize("factory", [create_digital_marketing_adapter, create_trading_adapter])
def test_both_professions_pass_one_common_operation_contract(factory: Any) -> None:
    adapter = factory()
    descriptor = adapter.describe()
    request = envelope(descriptor)
    payload = {"inputReference": "opaque-input-1"}

    assert adapter.health() == {"schemaVersion": "1.0.0", "status": "READY"}
    assert adapter.configure(request, {"approved": True})["valid"] is True
    assert adapter.plan(replace(request, mode="PLANNING"), payload)["sideEffects"] == []

    invocation = adapter.execute(request, payload)
    assert invocation.state is InvocationState.SUCCEEDED
    assert adapter.execute(request, payload) is invocation
    assert adapter.status(request, request.invocation_id) is invocation
    assert [event.sequence for event in adapter.events(request, request.invocation_id)] == [1, 2, 3, 4]
    result = adapter.result(request, request.invocation_id)
    assert result.state is InvocationState.SUCCEEDED
    assert result.output_payload_digest.startswith("sha256:")


def test_binding_deadline_scope_and_replay_fail_closed_without_leakage() -> None:
    adapter = create_digital_marketing_adapter()
    descriptor = adapter.describe()
    request = envelope(descriptor)
    payload = {"inputReference": "opaque-input-1"}
    adapter.execute(request, payload)

    denials = [
        (replace(request, professional_version="9.9.9"), "ADAPTER_BINDING_MISMATCH"),
        (replace(request, deadline=datetime.now(timezone.utc) - timedelta(seconds=1)), "ADAPTER_DEADLINE_EXPIRED"),
        (replace(request, mode="PLANNING", invocation_id=str(uuid4()), idempotency_key=str(uuid4())), "ADAPTER_EXECUTION_DENIED"),
        (replace(request, payload_digest="sha256:" + "ff" * 32), "ADAPTER_IDEMPOTENCY_CONFLICT"),
    ]
    for invalid, code in denials:
        with pytest.raises(AdapterContractError, match=code) as failure:
            adapter.execute(invalid, payload)
        assert request.tenant_ref not in str(failure.value)

    other_tenant = replace(request, tenant_ref="tenant-opaque-2")
    with pytest.raises(AdapterContractError, match="ADAPTER_NOT_ACCESSIBLE"):
        adapter.status(other_tenant, request.invocation_id)


def test_cancel_and_emergency_stop_preempt_active_work_under_250ms() -> None:
    started = threading.Event()
    release = threading.Event()
    descriptor = create_digital_marketing_adapter().describe()

    def blocking_handler(_envelope: AdapterInvocationEnvelopeV1, _payload: dict[str, Any]) -> dict[str, Any]:
        started.set()
        assert release.wait(timeout=2)
        return {"late": True}

    adapter = ReferenceAdapter(descriptor, blocking_handler)
    request = envelope(descriptor)
    worker = threading.Thread(target=adapter.execute, args=(request, {"inputReference": "opaque-input-1"}))
    worker.start()
    assert started.wait(timeout=1)

    stop_started = time.perf_counter()
    acknowledgement = adapter.emergency_stop(request, "stop-evidence-1")
    stop_elapsed = time.perf_counter() - stop_started
    release.set()
    worker.join(timeout=1)

    assert stop_elapsed < 0.250
    assert acknowledgement["state"] == "STOPPED"
    assert adapter.status(request, request.invocation_id).state is InvocationState.STOPPED
    with pytest.raises(AdapterContractError, match="ADAPTER_STOPPED"):
        adapter.execute(envelope(descriptor, relationship_id=request.relationship_id), {})
    with pytest.raises(AdapterContractError, match="ADAPTER_RESUME_DENIED"):
        adapter.resume(envelope(descriptor, relationship_id=request.relationship_id))

    resumed = adapter.resume(
        envelope(
            descriptor,
            relationship_id=request.relationship_id,
            ce_decision_ref="fresh-ce-authority-10",
            stop_evidence_ref="stop-evidence-1",
        )
    )
    assert resumed["state"] == "ELIGIBLE"


@pytest.mark.parametrize("factory", [create_digital_marketing_adapter, create_trading_adapter])
def test_generic_gateway_resolves_exact_artifact_without_type_branch(factory: Any) -> None:
    adapter = factory()
    descriptor = adapter.describe()
    activation = AdmissionActivationBinding(
        professional_type_id=descriptor.professional_type_id,
        professional_version=descriptor.professional_version,
        admission_state="ACTIVE",
        admission_content_digest=descriptor.admission_content_digest,
        artifact_digest=descriptor.artifact_digest,
        runtime_version="1.3.0",
        customer_contract_digest="sha256:" + "31" * 32,
    )
    binding = ActiveAdapterBinding(
        environment="demo",
        activation=activation,
        protocol_version="1.0.0",
        conformance_digest="sha256:" + "41" * 32,
        isolation_profile="ONE_ARTIFACT_PER_DEPLOYMENT",
        private_endpoint="https://adapter.internal:8443",
        workload_uri_san="spiffe://demo.waooaw.internal/workload/professional-runtime",
        audience="urn:waooaw:adapter",
    )
    resolver = AdapterResolver()
    resolver.register(ResolvedAdapter(binding, adapter))
    gateway = AgentRuntimeAdapterGateway(resolver)
    request = envelope(descriptor)

    assert gateway.execute("demo", activation, request, {"inputReference": "opaque-input-1"}).state is InvocationState.SUCCEEDED
    assert gateway.result("demo", activation, request, request.invocation_id).state is InvocationState.SUCCEEDED

    forged = replace(activation, artifact_digest="sha256:" + "ff" * 32)
    with pytest.raises(AdapterGatewayError, match="ADAPTER_NOT_ACCESSIBLE"):
        gateway.resolve_and_verify("demo", forged)


def test_coordinator_persists_before_workflow_and_dispatch() -> None:
    adapter = create_digital_marketing_adapter()
    descriptor = adapter.describe()
    activation = AdmissionActivationBinding(
        professional_type_id=descriptor.professional_type_id,
        professional_version=descriptor.professional_version,
        admission_state="ACTIVE",
        admission_content_digest=descriptor.admission_content_digest,
        artifact_digest=descriptor.artifact_digest,
        runtime_version="1.3.0",
        customer_contract_digest="sha256:" + "31" * 32,
    )
    binding = ActiveAdapterBinding(
        environment="demo",
        activation=activation,
        protocol_version="1.0.0",
        conformance_digest="sha256:" + "41" * 32,
        isolation_profile="ONE_ARTIFACT_PER_DEPLOYMENT",
        private_endpoint="https://adapter.internal:8443",
        workload_uri_san="spiffe://demo.waooaw.internal/workload/professional-runtime",
        audience="urn:waooaw:adapter",
    )
    order: list[str] = []

    class Store:
        def create_pending(self, _envelope: Any) -> None:
            order.append("store")

        def record_outcome(self, _invocation_id: str, _outcome: Any) -> None:
            order.append("outcome")

        def record_unknown(self, _invocation_id: str, _code: str) -> None:
            order.append("unknown")

    class Workflow:
        def start(self, workflow_id: str, _envelope: Any) -> None:
            assert workflow_id.startswith("ara-")
            order.append("workflow")

    resolver = AdapterResolver()
    resolver.register(ResolvedAdapter(binding, adapter))
    coordinator = AdapterInvocationCoordinator(AgentRuntimeAdapterGateway(resolver), Store(), Workflow())
    request = envelope(descriptor)

    coordinator.execute("demo", activation, request, {"inputReference": "opaque-input-1"})
    assert order == ["store", "workflow", "outcome"]


@pytest.mark.asyncio
async def test_private_http_transport_requires_pr_identity_and_projects_strict_response() -> None:
    adapter = create_digital_marketing_adapter()
    descriptor = adapter.describe()
    app = create_app(adapter)
    headers = {
        "X-WAOOAW-Workload-URI": "spiffe://demo.waooaw.internal/workload/professional-runtime",
        "Authorization": "Bearer test-service-assertion",
    }
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://adapter") as client:
        assert (await client.get("/internal/v1/descriptor")).status_code == 422
        described = await client.get("/internal/v1/descriptor", headers=headers)
        assert described.status_code == 200
        assert described.json()["professionalTypeId"] == descriptor.professional_type_id

        request = envelope(descriptor)
        wire_envelope = {
            "schemaVersion": request.schema_version,
            "tenantRef": request.tenant_ref,
            "relationshipId": request.relationship_id,
            "professionalTypeId": request.professional_type_id,
            "professionalVersion": request.professional_version,
            "skillId": request.skill_id,
            "skillVersion": request.skill_version,
            "admissionContentDigest": request.admission_content_digest,
            "artifactDigest": request.artifact_digest,
            "customerContractDigest": request.customer_contract_digest,
            "decisionSpaceVersion": request.decision_space_version,
            "configurationRevision": request.configuration_revision,
            "goalRevision": request.goal_revision,
            "invocationId": request.invocation_id,
            "idempotencyKey": request.idempotency_key,
            "payloadDigest": request.payload_digest,
            "ceDecisionRef": request.ce_decision_ref,
            "evidenceContextRef": request.evidence_context_ref,
            "deadline": request.deadline.isoformat(),
            "correlationId": request.correlation_id,
            "mode": request.mode,
        }
        response = await client.post(
            "/internal/v1/invocations",
            headers=headers,
            json={"envelope": wire_envelope, "payload": {"inputReference": "opaque-input-1"}},
        )
        assert response.status_code == 202
        assert set(response.json()) == {"schemaVersion", "invocationId", "state", "stateVersion", "replayed", "updatedAt"}