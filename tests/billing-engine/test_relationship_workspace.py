# Implements: wbe-relationship-workspace.openapi.yaml 1.0.0
# constitutional_basis: C-002, C-023, C-026, C-059, C-063, C-088, C-089, C-090, C-091

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi import FastAPI
from fastapi.testclient import TestClient

from relationship_workspace import (
    CommercialCommandRequest,
    CommercialProjection,
    CommercialStore,
    PaidActivationBody,
    _rebind_paid_activation,
    router,
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