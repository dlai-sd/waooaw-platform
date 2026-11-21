# Implements: wbe-relationship-workspace.openapi.yaml 1.0.0
# Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C4-09
# constitutional_basis: C-002, C-023, C-026, C-059, C-063, C-088, C-089, C-090, C-091
# Constitutional basis: C-059, C-038, C-088, C-089, C-063

from __future__ import annotations

import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest
import pytest_asyncio
from fastapi import HTTPException
from fastapi import FastAPI
from sqlalchemy import text
from starlette.requests import Request
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent))

import relationship_workspace  # noqa: E402
from payment.lifecycle import PeriodCreditService  # noqa: E402
from relationship_workspace import (  # noqa: E402
    CommercialCommandRequest,
    CommercialProjection,
    CommercialStore,
    OfferabilityValidationRequest,
    PaidActivationBody,
    _rebind_component_unit,
    _rebind_offerability_validation,
    _rebind_paid_activation,
    router,
    validate_relationship_offerability,
)
from wc136_commercial_ddl import install  # noqa: E402
from wc136_commercial_fakes import (  # noqa: E402
    FakePackages,
    FakeRates,
    policy_body,
    policy_source,
    pro,
    starter,
)
from workload_identity import ServiceAuthError  # noqa: E402


START = datetime(2026, 1, 1, tzinfo=timezone.utc)
TENANT = uuid.UUID("11111111-1111-4111-8111-111111111111")
CUSTOMER = uuid.UUID("22222222-2222-4222-8222-222222222222")
RELATIONSHIP_ID = uuid.UUID("44444444-4444-4444-8444-444444444444")
CONTEXT = SimpleNamespace(actor_subject="actor-a", tenant_id=str(TENANT), relationship_id=str(RELATIONSHIP_ID))


class _Clock:
    def __init__(self, at: datetime) -> None:
        self.at = at

    def __call__(self) -> datetime:
        return self.at


def request(kind="CHANGE_PACING", version="7", **payload_fields):
    payload = {"commandKind": kind, **payload_fields}
    if kind == "CHANGE_PACING":
        payload["pacingChoice"] = "CONSERVATIVE"
    return CommercialCommandRequest.model_validate(
        {"schemaVersion": "1.0", "expectedProjectionVersion": version, "payload": payload}
    )


def _store(db, clock, *, policy=None):
    return CommercialStore(
        db, now=clock, rates=FakeRates(), packages=FakePackages(starter(), pro()),
        policy=policy_source(policy_body() if policy is None else policy),
    )


@pytest_asyncio.fixture
async def db(wallet_db):
    async with wallet_db() as session:
        await install(session)
        await session.commit()
    return wallet_db


@pytest_asyncio.fixture
async def hired(db):
    clock = _Clock(START)
    async with db() as session:
        await PeriodCreditService(session, rates=FakeRates(), now=clock).start_period(
            TENANT, RELATIONSHIP_ID, CUSTOMER, starter(), START, 30_000, uuid.uuid4()
        )
        await session.commit()
    return SimpleNamespace(db=db, clock=clock, store=_store(db, clock))


@pytest.mark.asyncio
async def test_absent_commercial_truth_is_explicitly_unavailable(db) -> None:
    projection = await _store(db, _Clock(START)).projection(str(TENANT), RELATIONSHIP_ID)
    assert projection.currency_state == "UNAVAILABLE"
    assert projection.actuals == "Actual use unavailable"


@pytest.mark.asyncio
async def test_projection_is_built_from_the_stored_period_and_saved(hired) -> None:
    projection = await hired.store.projection(str(TENANT), RELATIONSHIP_ID)
    again = await hired.store.projection(str(TENANT), RELATIONSHIP_ID)
    assert projection.currency_state == "CURRENT"
    assert projection.allowance == "4 units left this period"
    assert projection.wallet is not None and projection.wallet.top_up_available
    assert {item.component_id: item.quantity for item in projection.wallet.components} == {"POSTS": 4, "INBOX": 1}
    assert again.projection_version == projection.projection_version
    async with hired.db() as session:
        saved = (await session.execute(text("SELECT COUNT(*) FROM business.commercial_projections"))).scalar_one()
    assert saved == 1


@pytest.mark.asyncio
async def test_stored_projection_answers_when_no_period_exists_and_goes_stale(db) -> None:
    clock = _Clock(datetime.now(timezone.utc))
    store = _store(db, clock)
    await store.set_projection(str(TENANT), _projection("7", clock.at + timedelta(minutes=5)))
    assert (await store.projection(str(TENANT), RELATIONSHIP_ID)).currency_state == "CURRENT"
    clock.at += timedelta(minutes=10)
    assert (await store.projection(str(TENANT), RELATIONSHIP_ID)).currency_state == "STALE"


def _projection(version: str, valid_until: datetime | None = None) -> CommercialProjection:
    return CommercialProjection(
        schemaVersion="1.0", relationshipId=RELATIONSHIP_ID, projectionVersion=version,
        producedAt=datetime.now(timezone.utc), validUntil=valid_until, currencyState="CURRENT", actuals="INR 100",
        allowance="INR 900 remaining", budget="INR 1,000 ceiling", forecast="INR 800 to INR 1,000",
        thresholds="Below threshold", commercialConsequences="No current restriction")


@pytest.mark.asyncio
async def test_current_owner_state_accepts_exact_replay_and_rejects_changed_intent(db) -> None:
    store = _store(db, _Clock(START))
    await store.set_projection(str(TENANT), _projection("7"))
    first = await store.submit(CONTEXT, request(), "key-a")
    replay = await _store(db, _Clock(START)).submit(CONTEXT, request(), "key-a")
    assert first.status == "PENDING"
    assert replay.command_id == first.command_id and replay.replayed
    with pytest.raises(HTTPException) as conflict:
        await store.submit(CONTEXT, request("PAUSE_RELATIONSHIP"), "key-a")
    assert conflict.value.status_code == 409
    assert conflict.value.detail == "WBE_COMMERCIAL_CONFLICT"


@pytest.mark.asyncio
async def test_unresolved_lifecycle_policy_blocks_and_cross_tenant_outcome_is_hidden(db) -> None:
    store = CommercialStore(db, now=_Clock(START), policy=policy_source(None))
    receipt = await store.submit(CONTEXT, request("TERMINATE_RELATIONSHIP"), "key-b")
    assert receipt.status == "BLOCKED"
    assert (await store.outcome(CONTEXT, receipt.command_id)).blocked_reason == "POLICY_ABSENT"
    other = SimpleNamespace(actor_subject="actor-a", tenant_id=str(uuid.uuid4()), relationship_id=str(RELATIONSHIP_ID))
    assert await store.outcome(other, receipt.command_id) is None


@pytest.mark.asyncio
async def test_stale_projection_version_conflicts_and_pause_refunds_the_unelapsed_fee(hired) -> None:
    hired.clock.at = START + timedelta(days=15)
    version = (await hired.store.projection(str(TENANT), RELATIONSHIP_ID)).projection_version
    stale = await hired.store.submit(CONTEXT, request("PAUSE_RELATIONSHIP", "old-version"), "key-c")
    assert stale.status == "CONFLICT"
    paused = await hired.store.submit(CONTEXT, request("PAUSE_RELATIONSHIP", version), "key-d")
    outcome = await hired.store.outcome(CONTEXT, paused.command_id)
    assert paused.status == "COMPLETED"
    assert outcome.refund_fee_paise == 15_000 and outcome.resolved_at is not None
    async with hired.db() as session:
        adjustments = (await session.execute(text("SELECT amount_paise, status FROM business.billing_adjustments"))).all()
        wallet_entries = (await session.execute(text("SELECT COUNT(*) FROM business.wallet_lots"))).scalar_one()
    assert adjustments == [(15_000, "NOT_PAYABLE")]
    assert wallet_entries == 1


@pytest.mark.asyncio
async def test_terminate_is_allowed_on_a_stale_projection_and_ends_the_period(hired) -> None:
    hired.clock.at = START + timedelta(days=12)
    receipt = await hired.store.submit(CONTEXT, request("TERMINATE_RELATIONSHIP", "any"), "key-e")
    outcome = await hired.store.outcome(CONTEXT, receipt.command_id)
    assert receipt.status == "COMPLETED"
    assert outcome.refund_fee_paise == 18_000
    projection = await hired.store.projection(str(TENANT), RELATIONSHIP_ID)
    assert projection.currency_state == "BLOCKED"


def test_component_unit_rebind_requires_the_exact_delegated_context() -> None:
    relationship_id = uuid.uuid4()
    key = str(uuid.uuid4())
    body = SimpleNamespace(component_id="POSTS")
    context = SimpleNamespace(
        effective_role="SYSTEM", purpose="COMPONENT_UNIT_USAGE", relationship_id=str(relationship_id),
        idempotency_key=key, subject_reference="POSTS",
    )
    _rebind_component_unit(context, relationship_id, key, body)
    context.purpose = "OFFERING_COMPONENT_USAGE"
    with pytest.raises(ServiceAuthError, match="SERVICE_AUTHORIZATION_DENIED"):
        _rebind_component_unit(context, relationship_id, key, body)


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