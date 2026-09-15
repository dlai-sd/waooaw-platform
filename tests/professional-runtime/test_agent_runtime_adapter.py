"""WC-080 common adapter and generic Professional Runtime gateway proof."""

# Implements: architecture/agent-runtime-adapter-contract-v1-execution-plan.md §9
# Constitutional basis: C-023, C-035, C-059, C-065, C-071, C-079, C-080

from __future__ import annotations

import hashlib
import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor
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


def domain_payload(descriptor: AdapterDescriptorV1) -> dict[str, Any]:
    if descriptor.professional_type_id != "DIGITAL_MARKETING_LOCAL_SERVICE":
        return {"inputReference": "opaque-input-1"}
    return {
        "fields": {
            "accountMode": {"value": "OWNER_OPERATED", "provenance": "CONFIRMED"},
            "businessIdentity": {"value": "Local clinic", "provenance": "CONFIRMED"},
            "audience": {"value": "Local families", "provenance": "CONFIRMED"},
            "priority": {"value": "Qualified enquiries", "provenance": "CONFIRMED"},
            "constraints": {"value": "No health claims", "provenance": "CONFIRMED"},
            "approvedChannels": {"value": ["WEB"], "provenance": "CONFIRMED"},
        }
    }


def envelope(descriptor: AdapterDescriptorV1, **changes: Any) -> AdapterInvocationEnvelopeV1:
    payload = domain_payload(descriptor)
    values: dict[str, Any] = {
        "schema_version": "1.0.0",
        "tenant_ref": "tenant-opaque-1",
        "relationship_id": str(uuid4()),
        "agent_instance_id": str(uuid4()),
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
    payload = domain_payload(descriptor)

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
    payload = domain_payload(descriptor)
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


def test_request_validation_and_handler_failures_are_stable() -> None:
    descriptor = create_digital_marketing_adapter().describe()
    adapter = create_digital_marketing_adapter()
    request = envelope(descriptor)

    with pytest.raises(AdapterContractError, match="ADAPTER_REQUEST_INVALID"):
        adapter.configure(replace(request, configuration_revision=None), {})
    with pytest.raises(AdapterContractError, match="ADAPTER_REQUEST_INVALID"):
        adapter.plan(replace(request, invocation_id="not-a-uuid"), {})
    with pytest.raises(AdapterContractError, match="ADAPTER_REQUEST_INVALID"):
        adapter.plan(replace(request, payload_digest="not-a-digest"), {})
    with pytest.raises(AdapterContractError, match="ADAPTER_NOT_ACCESSIBLE"):
        adapter.status(request, str(uuid4()))

    denied = ReferenceAdapter(
        descriptor,
        lambda current, _payload: (_ for _ in ()).throw(AdapterContractError("ADAPTER_EXECUTION_DENIED", current.correlation_id)),
    )
    with pytest.raises(AdapterContractError, match="ADAPTER_EXECUTION_DENIED"):
        denied.execute(envelope(descriptor), {})

    failed = ReferenceAdapter(descriptor, lambda _current, _payload: 1 / 0)
    with pytest.raises(AdapterContractError, match="ADAPTER_INTERNAL_FAILURE"):
        failed.execute(envelope(descriptor), {})


def test_cancel_and_unresolved_result_paths() -> None:
    started = threading.Event()
    release = threading.Event()
    descriptor = create_digital_marketing_adapter().describe()

    def blocking_handler(_envelope: AdapterInvocationEnvelopeV1, _payload: dict[str, Any]) -> dict[str, Any]:
        started.set()
        assert release.wait(timeout=2)
        return {"late": True}

    adapter = ReferenceAdapter(descriptor, blocking_handler)
    request = envelope(descriptor)
    worker = threading.Thread(target=adapter.execute, args=(request, {}))
    worker.start()
    assert started.wait(timeout=1)
    with pytest.raises(AdapterContractError, match="ADAPTER_RESULT_UNRESOLVED") as unresolved:
        adapter.result(request, request.invocation_id)
    assert unresolved.value.retryable is True
    assert adapter.cancel(request, request.invocation_id).state is InvocationState.CANCELLED
    assert adapter.cancel(request, request.invocation_id).state is InvocationState.CANCELLED
    release.set()
    worker.join(timeout=1)


def test_stop_skips_other_relationships_and_terminal_work() -> None:
    adapter = create_digital_marketing_adapter()
    descriptor = adapter.describe()
    terminal = envelope(descriptor)
    other = envelope(descriptor)
    adapter.execute(terminal, domain_payload(descriptor))
    adapter.execute(other, domain_payload(descriptor))

    adapter.emergency_stop(terminal, "stop-evidence-terminal")

    assert adapter.status(terminal, terminal.invocation_id).state is InvocationState.SUCCEEDED
    assert adapter.status(other, other.invocation_id).state is InvocationState.SUCCEEDED


def test_same_relationship_instances_are_isolated_for_status_replay_and_stop() -> None:
    adapter = create_digital_marketing_adapter()
    descriptor = adapter.describe()
    relationship_id = str(uuid4())
    first = envelope(descriptor, relationship_id=relationship_id)
    second = envelope(descriptor, relationship_id=relationship_id)
    adapter.execute(first, domain_payload(descriptor))

    with pytest.raises(AdapterContractError, match="ADAPTER_NOT_ACCESSIBLE"):
        adapter.status(second, first.invocation_id)

    adapter.emergency_stop(first, "stop-evidence-first-instance")
    second_result = adapter.execute(second, domain_payload(descriptor))

    assert second_result.state is InvocationState.SUCCEEDED
    with pytest.raises(AdapterContractError, match="ADAPTER_STOPPED"):
        adapter.execute(
            envelope(
                descriptor,
                relationship_id=relationship_id,
                agent_instance_id=first.agent_instance_id,
            ),
            {},
        )


def test_two_tenants_complete_release_one_skill_sequence_on_one_digest_without_crossover() -> None:
    adapter = create_digital_marketing_adapter()
    descriptor = adapter.describe()

    def run_sequence(tenant_ref: str, business_name: str, source_id: str, theme: str) -> tuple[Any, Any, Any]:
        base = envelope(descriptor, tenant_ref=tenant_ref)

        def execute(skill_id: str, payload: dict[str, Any]) -> Any:
            request = replace(
                base,
                skill_id=skill_id,
                invocation_id=str(uuid4()),
                idempotency_key=str(uuid4()),
                payload_digest=digest(payload),
            )
            return adapter.execute(request, payload).output

        profile_payload = domain_payload(descriptor)
        profile_payload["fields"]["businessIdentity"]["value"] = business_name
        profile = execute("CUSTOMER_PROFILING", profile_payload)
        research = execute(
            "MARKET_RESEARCH",
            {
                "sources": [{"sourceId": source_id, "url": f"https://{source_id}.example/market", "observedAt": "2026-09-15"}],
                "claims": [{"claim": f"Evidence for {business_name}.", "sourceId": source_id}],
                "maturitySignals": {"website": 2},
                "unavailableProviders": [],
            },
        )
        strategy = execute(
            "CONTENT_STRATEGY",
            {
                "profileRevision": f"profile-{source_id}",
                "researchRevision": f"research-{source_id}",
                "researchStatus": "REVIEWED",
                "startDate": "2026-10-01",
                "themes": [theme],
            },
        )
        return profile, research, strategy

    with ThreadPoolExecutor(max_workers=2) as workers:
        first = workers.submit(run_sequence, "tenant-opaque-1", "Clinic Alpha", "alpha", "education")
        second = workers.submit(run_sequence, "tenant-opaque-2", "Studio Beta", "beta", "community")
        alpha = first.result(timeout=2)
        beta = second.result(timeout=2)

    assert descriptor.artifact_digest == adapter.describe().artifact_digest
    assert alpha[0]["fields"]["businessIdentity"]["value"] == "Clinic Alpha"
    assert beta[0]["fields"]["businessIdentity"]["value"] == "Studio Beta"
    assert alpha[1]["sources"][0]["sourceId"] == "alpha"
    assert beta[1]["sources"][0]["sourceId"] == "beta"
    assert {item["theme"] for item in alpha[2]["calendar"]} == {"education"}
    assert {item["theme"] for item in beta[2]["calendar"]} == {"community"}


def test_cancel_and_emergency_stop_preempt_active_work_under_250ms() -> None:
    started = threading.Barrier(3)
    release = threading.Event()
    descriptor = create_digital_marketing_adapter().describe()

    def blocking_handler(current: AdapterInvocationEnvelopeV1, _payload: dict[str, Any]) -> dict[str, Any]:
        started.wait(timeout=2)
        assert release.wait(timeout=2)
        return {"tenantRef": current.tenant_ref}

    adapter = ReferenceAdapter(descriptor, blocking_handler)
    request = envelope(descriptor)
    other_tenant = envelope(descriptor, tenant_ref="tenant-opaque-2")
    worker = threading.Thread(target=adapter.execute, args=(request, {"inputReference": "opaque-input-1"}))
    other_worker = threading.Thread(target=adapter.execute, args=(other_tenant, {"inputReference": "opaque-input-2"}))
    worker.start()
    other_worker.start()
    started.wait(timeout=2)

    stop_started = time.perf_counter()
    acknowledgement = adapter.emergency_stop(request, "stop-evidence-1")
    stop_elapsed = time.perf_counter() - stop_started
    release.set()
    worker.join(timeout=1)
    other_worker.join(timeout=1)

    assert stop_elapsed < 0.250
    assert acknowledgement["state"] == "STOPPED"
    stopped = adapter.status(request, request.invocation_id)
    assert stopped.state is InvocationState.STOPPED
    assert stopped.output is None
    assert adapter.result(other_tenant, other_tenant.invocation_id).output == {"tenantRef": "tenant-opaque-2"}
    with pytest.raises(AdapterContractError, match="ADAPTER_STOPPED"):
        adapter.execute(
            envelope(
                descriptor,
                relationship_id=request.relationship_id,
                agent_instance_id=request.agent_instance_id,
            ),
            {},
        )
    with pytest.raises(AdapterContractError, match="ADAPTER_RESUME_DENIED"):
        adapter.resume(
            envelope(
                descriptor,
                relationship_id=request.relationship_id,
                agent_instance_id=request.agent_instance_id,
            )
        )

    resumed = adapter.resume(
        envelope(
            descriptor,
            relationship_id=request.relationship_id,
            agent_instance_id=request.agent_instance_id,
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

    assert gateway.execute("demo", activation, request, domain_payload(descriptor)).state is InvocationState.SUCCEEDED
    assert gateway.result("demo", activation, request, request.invocation_id).state is InvocationState.SUCCEEDED

    forged = replace(activation, artifact_digest="sha256:" + "ff" * 32)
    with pytest.raises(AdapterGatewayError, match="ADAPTER_NOT_ACCESSIBLE"):
        gateway.resolve_and_verify("demo", forged)


def test_gateway_denials_stop_resume_and_error_mapping() -> None:
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
    resolver = AdapterResolver()
    resolved = ResolvedAdapter(binding, adapter)
    resolver.register(resolved)
    with pytest.raises(AdapterGatewayError, match="ADAPTER_BINDING_CONFLICT"):
        resolver.register(resolved)
    gateway = AgentRuntimeAdapterGateway(resolver)

    with pytest.raises(AdapterGatewayError, match="ADAPTER_EXECUTION_DENIED"):
        gateway.resolve_and_verify("demo", replace(activation, admission_state="SUSPENDED"))

    request = envelope(descriptor)
    assert gateway.emergency_stop("demo", activation, request, "stop-evidence-1")["state"] == "STOPPED"
    with pytest.raises(AdapterGatewayError, match="ADAPTER_STOPPED"):
        gateway.execute("demo", activation, request, {})
    sibling = envelope(descriptor, relationship_id=request.relationship_id)
    assert gateway.execute("demo", activation, sibling, domain_payload(descriptor)).state is InvocationState.SUCCEEDED
    with pytest.raises(AdapterGatewayError, match="ADAPTER_RESUME_DENIED"):
        gateway.resume("demo", activation, replace(request, stop_evidence_ref="wrong"))
    resumed_request = replace(
        request,
        invocation_id=str(uuid4()),
        idempotency_key=str(uuid4()),
        ce_decision_ref="fresh-ce-decision",
        stop_evidence_ref="stop-evidence-1",
    )
    assert gateway.resume("demo", activation, resumed_request)["state"] == "ELIGIBLE"

    invalid = replace(envelope(descriptor), payload_digest="invalid")
    with pytest.raises(AdapterGatewayError, match="ADAPTER_REQUEST_INVALID"):
        gateway.execute("demo", activation, invalid, {})

    class GatewayFailureClient:
        def describe(self) -> Any:
            return descriptor

        def execute(self, _envelope: Any, _payload: Any) -> None:
            raise AdapterGatewayError("ADAPTER_EXECUTION_DENIED")

    alternate_resolver = AdapterResolver()
    alternate_resolver.register(ResolvedAdapter(binding, GatewayFailureClient()))  # type: ignore[arg-type]
    with pytest.raises(AdapterGatewayError, match="ADAPTER_EXECUTION_DENIED"):
        AgentRuntimeAdapterGateway(alternate_resolver).execute("demo", activation, envelope(descriptor), {})


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

    coordinator.execute("demo", activation, request, domain_payload(descriptor))
    assert order == ["store", "workflow", "outcome"]


def test_coordinator_records_unknown_when_retryable_dispatch_cannot_reconcile() -> None:
    order: list[str] = []

    class Gateway:
        def resolve_and_verify(self, _environment: str, _activation: Any) -> None:
            return None

        def execute(self, _environment: str, _activation: Any, _envelope: Any, _payload: Any) -> None:
            raise AdapterGatewayError("ADAPTER_UNAVAILABLE", retryable=True)

        def reconcile(self, _environment: str, _activation: Any, _envelope: Any, _invocation_id: str) -> None:
            raise AdapterGatewayError("ADAPTER_NOT_ACCESSIBLE")

    class Store:
        def create_pending(self, _envelope: Any) -> None:
            order.append("store")

        def record_outcome(self, _invocation_id: str, _outcome: Any) -> None:
            order.append("outcome")

        def record_unknown(self, _invocation_id: str, code: str) -> None:
            order.append(code)

    class Workflow:
        def start(self, _workflow_id: str, _envelope: Any) -> None:
            order.append("workflow")

    descriptor = create_digital_marketing_adapter().describe()
    request = envelope(descriptor)
    coordinator = AdapterInvocationCoordinator(Gateway(), Store(), Workflow())  # type: ignore[arg-type]
    with pytest.raises(AdapterGatewayError, match="ADAPTER_RESULT_UNRESOLVED"):
        coordinator.execute("demo", object(), request, {})  # type: ignore[arg-type]
    assert order == ["store", "workflow", "ADAPTER_UNAVAILABLE"]


def test_coordinator_records_deterministic_denial_without_reconciliation() -> None:
    order: list[str] = []

    class Gateway:
        def resolve_and_verify(self, _environment: str, _activation: Any) -> None:
            return None

        def execute(self, _environment: str, _activation: Any, _envelope: Any, _payload: Any) -> None:
            raise AdapterGatewayError("ADAPTER_EXECUTION_DENIED")

    class Store:
        def create_pending(self, _envelope: Any) -> None:
            order.append("store")

        def record_outcome(self, _invocation_id: str, outcome: Any) -> None:
            order.append(str(outcome))

        def record_unknown(self, _invocation_id: str, _code: str) -> None:
            order.append("unknown")

    class Workflow:
        def start(self, _workflow_id: str, _envelope: Any) -> None:
            order.append("workflow")

    request = envelope(create_digital_marketing_adapter().describe())
    coordinator = AdapterInvocationCoordinator(Gateway(), Store(), Workflow())  # type: ignore[arg-type]
    with pytest.raises(AdapterGatewayError, match="ADAPTER_EXECUTION_DENIED"):
        coordinator.execute("demo", object(), request, {})  # type: ignore[arg-type]
    assert order == ["store", "workflow", "ADAPTER_EXECUTION_DENIED"]


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
            "agentInstanceId": request.agent_instance_id,
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
            json={"envelope": wire_envelope, "payload": domain_payload(descriptor)},
        )
        assert response.status_code == 202
        assert set(response.json()) == {"schemaVersion", "invocationId", "state", "stateVersion", "replayed", "updatedAt"}

        missing_instance = dict(wire_envelope)
        del missing_instance["agentInstanceId"]
        invalid = await client.post(
            "/internal/v1/invocations",
            headers=headers,
            json={"envelope": missing_instance, "payload": {"inputReference": "opaque-input-1"}},
        )
        assert invalid.status_code == 400
        assert invalid.json()["detail"] == "ADAPTER_REQUEST_INVALID"

        body = {"envelope": wire_envelope, "payload": domain_payload(descriptor)}
        assert (await client.get("/internal/v1/health/ready", headers=headers)).status_code == 200
        assert (await client.post("/internal/v1/configurations:validate", headers=headers, json=body)).status_code == 200
        planning = dict(wire_envelope)
        planning.update({"mode": "PLANNING", "invocationId": str(uuid4()), "idempotencyKey": str(uuid4())})
        assert (
            await client.post("/internal/v1/plans", headers=headers, json={"envelope": planning, "payload": {}})
        ).status_code == 200
        status = await client.request(
            "GET",
            f"/internal/v1/invocations/{request.invocation_id}",
            headers=headers,
            json=body,
        )
        assert status.status_code == 200
        events = await client.request(
            "GET",
            f"/internal/v1/invocations/{request.invocation_id}/events",
            headers=headers,
            json=body,
        )
        assert events.status_code == 200
        result = await client.request(
            "GET",
            f"/internal/v1/invocations/{request.invocation_id}/result",
            headers=headers,
            json=body,
        )
        assert result.status_code == 200
        conflict = dict(wire_envelope)
        conflict["payloadDigest"] = "sha256:" + "ff" * 32
        failure = await client.post(
            "/internal/v1/invocations",
            headers=headers,
            json={"envelope": conflict, "payload": {}},
        )
        assert failure.status_code == 409
        assert failure.json()["code"] == "ADAPTER_IDEMPOTENCY_CONFLICT"
