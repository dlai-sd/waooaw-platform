# Implements: wbe-relationship-workspace.openapi.yaml 1.0.0
# constitutional_basis: C-002, C-023, C-026, C-059, C-063, C-088, C-089, C-090, C-091

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi import FastAPI
from starlette.requests import Request
from fastapi.testclient import TestClient

import relationship_workspace
from relationship_workspace import (
    CommercialCommandRequest,
    CommercialProjection,
    CommercialStore,
    OfferabilityValidationRequest,
    PaidActivationBody,
    _rebind_offerability_validation,
    _rebind_paid_activation,
    router,
    validate_relationship_offerability,
)
from workload_identity import ServiceAuthError


RELATIONSHIP_ID = uuid.uuid4()
CONTEXT = SimpleNamespace(actor_subject="actor-a", tenant_id="tenant-a", relationship_id=str(RELATIONSHIP_ID))


def request(kind="CHANGE_PACING", version="7"):
    payload = {"commandKind": kind}
    if kind == "CHANGE_PACING":
        payload["pacingChoice"] = "CONSERVATIVE"
    return CommercialCommandRequest.model_validate(
        {"schemaVersion": "1.0", "expectedProjectionVersion": version, "payload": payload}
    )


def test_absent_commercial_truth_is_explicitly_unavailable() -> None:
    projection = CommercialStore().projection("tenant-a", RELATIONSHIP_ID)
    assert projection.currency_state == "UNAVAILABLE"
    assert projection.actuals == "Actual use unavailable"


def test_current_owner_state_accepts_exact_replay_and_rejects_changed_intent() -> None:
    store = CommercialStore()
    store.set_projection("tenant-a", CommercialProjection(
        schemaVersion="1.0", relationshipId=RELATIONSHIP_ID, projectionVersion="7",
        producedAt=datetime.now(timezone.utc), currencyState="CURRENT", actuals="INR 100",
        allowance="INR 900 remaining", budget="INR 1,000 ceiling", forecast="INR 800 to INR 1,000",
        thresholds="Below threshold", commercialConsequences="No current restriction"))
    first = store.submit(CONTEXT, request(), "key-a")
    replay = store.submit(CONTEXT, request(), "key-a")
    assert first.status == "PENDING"
    assert replay.command_id == first.command_id and replay.replayed
    with pytest.raises(HTTPException) as conflict:
        store.submit(CONTEXT, request("PAUSE_RELATIONSHIP"), "key-a")
    assert conflict.value.status_code == 409


def test_unresolved_lifecycle_policy_blocks_and_cross_tenant_outcome_is_hidden() -> None:
    store = CommercialStore()
    receipt = store.submit(CONTEXT, request("TERMINATE_RELATIONSHIP"), "key-b")
    assert receipt.status == "BLOCKED"
    other = SimpleNamespace(actor_subject="actor-a", tenant_id="tenant-b", relationship_id=str(RELATIONSHIP_ID))
    assert store.outcome(other, receipt.command_id) is None


def _activation_binding() -> tuple[SimpleNamespace, uuid.UUID, PaidActivationBody, str]:
    relationship_id = uuid.uuid4()
    activation_intent_id = uuid.uuid4()
    contract_id = uuid.uuid4()
    correlation_id = uuid.uuid4()
    body = PaidActivationBody(
        activation_intent_id=activation_intent_id,
        accepted_contract_id=contract_id,
        contract_version=3,
        contract_acceptance_id=uuid.uuid4(),
        payment_reference="pay_verified_123",
        payment_evidence_id=uuid.uuid4(),
        correlation_id=correlation_id,
    )
    context = SimpleNamespace(
        effective_role="EMPLOYER",
        purpose="activatePaidRelationship",
        subject_reference=str(contract_id),
        command_id=str(activation_intent_id),
        idempotency_key=str(correlation_id),
        correlation_id=str(correlation_id),
        relationship_id=str(relationship_id),
        expected_versions={"activation_intent": str(activation_intent_id), "contract": "3"},
        tenant_id=str(uuid.uuid4()),
        actor_subject=str(uuid.uuid4()),
    )
    return context, relationship_id, body, str(correlation_id)


def test_paid_activation_rebinds_exact_delegated_context() -> None:
    context, relationship_id, body, idempotency_key = _activation_binding()
    _rebind_paid_activation(context, relationship_id, body, idempotency_key)


def _offerability_binding() -> tuple[SimpleNamespace, uuid.UUID, OfferabilityValidationRequest]:
    relationship_id = uuid.uuid4()
    body = OfferabilityValidationRequest(
        schemaVersion="1.0",
        offeringId="dma-starter-v1",
        agentType="DMA",
        bundleTier="STARTER",
        proposedPricePaise=7000,
    )
    context = SimpleNamespace(
        effective_role="FOUNDER",
        purpose="validateRelationshipOfferability",
        subject_reference=body.offering_id,
        relationship_id=str(relationship_id),
        expected_versions={
            "agent_type": body.agent_type,
            "bundle_tier": body.bundle_tier,
            "offering": body.offering_id,
            "proposed_price_paise": str(body.proposed_price_paise),
        },
        tenant_id=str(uuid.uuid4()),
        actor_subject=str(uuid.uuid4()),
    )
    return context, relationship_id, body


def test_offerability_validation_rebinds_exact_delegated_context() -> None:
    context, relationship_id, body = _offerability_binding()
    _rebind_offerability_validation(context, relationship_id, body)


@pytest.mark.parametrize("field,value", [
    ("effective_role", "EMPLOYER"),
    ("purpose", "getRelationshipCommercialProjection"),
    ("subject_reference", "changed-offering"),
    ("relationship_id", "changed-relationship"),
    ("expected_versions", {"offering": "changed"}),
    ("tenant_id", ""),
])
def test_offerability_validation_denies_confused_deputy_context(field: str, value: object) -> None:
    context, relationship_id, body = _offerability_binding()
    setattr(context, field, value)
    with pytest.raises(ServiceAuthError, match="SERVICE_AUTHORIZATION_DENIED"):
        _rebind_offerability_validation(context, relationship_id, body)


def test_offerability_route_denies_missing_workload_identity_before_owner_call() -> None:
    _, relationship_id, body = _offerability_binding()
    application = FastAPI()
    application.include_router(router)
    application.state.relationship_workload_auth = None

    response = TestClient(application).post(
        f"/internal/v1/relationships/{relationship_id}/offerability-validation",
        json=body.model_dump(by_alias=True, mode="json"),
        headers={"X-Correlation-ID": str(uuid.uuid4())},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "WBE_OFFERABILITY_UNAUTHORIZED"


def test_offerability_route_rejects_invalid_body_with_contract_status() -> None:
    _, relationship_id, _ = _offerability_binding()
    app = FastAPI()
    app.include_router(router)

    response = TestClient(app).post(
        f"/internal/v1/relationships/{relationship_id}/offerability-validation",
        json={"schemaVersion": "1.0"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "WBE_OFFERABILITY_REQUEST_INVALID"


@pytest.mark.asyncio
async def test_offerability_route_returns_owner_validation(monkeypatch: pytest.MonkeyPatch) -> None:
    context, relationship_id, body = _offerability_binding()

    class Session:
        async def __aenter__(self) -> object:
            return object()

        async def __aexit__(self, *args: object) -> None:
            return None

    class Engine:
        def __init__(self, db: object) -> None:
            pass

        async def validate_price(self, agent_type: str, bundle_tier: str, proposed_price_paise: int) -> SimpleNamespace:
            return SimpleNamespace(
                outcome="APPROVED",
                cost_floor_paise=5_000,
                minimum_compliant_price_paise=6_250,
                proposed_price_paise=proposed_price_paise,
            )

    monkeypatch.setattr(relationship_workspace, "_authorize", lambda *args, **kwargs: context)
    monkeypatch.setattr(relationship_workspace, "get_session_factory", lambda: Session)
    monkeypatch.setattr(relationship_workspace, "BundleEngine", Engine)

    result = await validate_relationship_offerability(
        relationship_id,
        body.model_dump(by_alias=True, mode="json"),
        Request({"type": "http", "method": "POST", "path": "/"}),
    )

    assert result["outcome"] == "APPROVED"
    assert result["directContributionPaise"] == 2_000
    assert result["relationshipId"] == str(relationship_id)
    assert len(str(result["validationVersion"])) == 64


@pytest.mark.asyncio
async def test_offerability_route_fails_closed_when_owner_truth_is_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    context, relationship_id, body = _offerability_binding()

    class Session:
        async def __aenter__(self) -> object:
            return object()

        async def __aexit__(self, *args: object) -> None:
            return None

    class Engine:
        def __init__(self, db: object) -> None:
            pass

        async def validate_price(self, agent_type: str, bundle_tier: str, proposed_price_paise: int) -> None:
            raise ValueError("owner truth unavailable")

    monkeypatch.setattr(relationship_workspace, "_authorize", lambda *args, **kwargs: context)
    monkeypatch.setattr(relationship_workspace, "get_session_factory", lambda: Session)
    monkeypatch.setattr(relationship_workspace, "BundleEngine", Engine)

    with pytest.raises(HTTPException) as unavailable:
        await validate_relationship_offerability(
            relationship_id,
            body.model_dump(by_alias=True, mode="json"),
            Request({"type": "http", "method": "POST", "path": "/"}),
        )

    assert unavailable.value.status_code == 503
    assert unavailable.value.detail == "WBE_OFFERABILITY_UNAVAILABLE"


def test_paid_activation_route_denies_missing_workload_identity_before_owner_call() -> None:
    _, relationship_id, body, idempotency_key = _activation_binding()
    application = FastAPI()
    application.include_router(router)
    application.state.relationship_workload_auth = None

    response = TestClient(application).post(
        f"/internal/v1/relationships/{relationship_id}/paid-activation",
        json=body.model_dump(mode="json"),
        headers={"Idempotency-Key": idempotency_key, "X-Correlation-ID": idempotency_key},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "WBE_PAID_ACTIVATION_UNAUTHORIZED"


@pytest.mark.parametrize("field,value", [
    ("effective_role", "VIEWER"),
    ("purpose", "getRelationshipCommercialProjection"),
    ("subject_reference", "changed-contract"),
    ("command_id", "changed-intent"),
    ("idempotency_key", "changed-key"),
    ("correlation_id", "changed-correlation"),
    ("relationship_id", "changed-relationship"),
    ("expected_versions", {"activation_intent": "changed", "contract": "4"}),
    ("tenant_id", ""),
])
def test_paid_activation_denies_confused_deputy_context(field: str, value: object) -> None:
    context, relationship_id, body, idempotency_key = _activation_binding()
    setattr(context, field, value)
    with pytest.raises(ServiceAuthError, match="SERVICE_AUTHORIZATION_DENIED"):
        _rebind_paid_activation(context, relationship_id, body, idempotency_key)