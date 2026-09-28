# Implements: architecture/reference/api-specs/business-platform.openapi.yaml §RelationshipCheckoutOutcome
# Constitutional basis: C-059, C-088, C-090, ADR-022 §1.2/1.3/1.4
"""
CCT-ONBOARD-01   — Single onboarding order: subscription + wallet seed in one Razorpay call.
CCT-WEBHOOK-01   — payment.captured webhook: HMAC verified, idempotent, activates wallet.
CCT-GRANDFATHER-01 — C-090: renewal blocked when plan price > agreed price without notice.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import uuid
from dataclasses import replace
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import fakeredis
import pytest
import pytest_asyncio
import respx
from fastapi import HTTPException
from httpx import Response
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool
from starlette.requests import Request

from payment.models import (
    CheckoutOutcomeKind,
    OnboardingOrderRequest,
    PaidActivationRequest,
    PaymentCapturedEvent,
    RelationshipCheckoutRequest,
)
from payment.onboarding import OnboardingService
from payment.paid_activation import PaidActivationService
from payment.razorpay_client import RazorpayClient
from payment.router import HireCommercialPreviewBody, OnboardingOrderBody
from payment.webhook import WebhookHandler
from wallet.models import RenewalResult, SubscriptionActivationResult
from wallet.service import WalletService


@pytest.mark.asyncio
@pytest.mark.parametrize("payment_id", ["../orders", "pay_../orders", "https://attacker.invalid", "pay_id?expand=card"])
async def test_razorpay_fetch_payment_rejects_non_opaque_identifiers(payment_id):
    client = RazorpayClient(settings=MagicMock())

    with pytest.raises(ValueError, match="Invalid Razorpay payment identifier"):
        await client.fetch_payment(payment_id)


# ---------------------------------------------------------------------------
# Schema DDL (SQLite in-memory)
# ---------------------------------------------------------------------------

_PAYMENT_DDL = [
    """CREATE TABLE IF NOT EXISTS pre_hire_checkout_orders (
        checkout_intent_id TEXT PRIMARY KEY,
        customer_id TEXT NOT NULL,
        professional_type TEXT NOT NULL,
        professional_version TEXT NOT NULL,
        disclosure_revision TEXT NOT NULL,
        terms_version TEXT NOT NULL,
        cadence TEXT NOT NULL,
        list_price_inr_paise INTEGER NOT NULL,
        discount_inr_paise INTEGER NOT NULL,
        tax_inr_paise INTEGER NOT NULL,
        payable_inr_paise INTEGER NOT NULL,
        coupon_code TEXT,
        razorpay_order_id TEXT UNIQUE,
        razorpay_payment_id TEXT UNIQUE,
        commercial_evidence_id TEXT,
        relationship_id TEXT UNIQUE,
        contract_checkout_intent_id TEXT UNIQUE,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        updated_at TEXT NOT NULL DEFAULT (datetime('now'))
    )""",
    """CREATE TABLE IF NOT EXISTS razorpay_checkout_orders (
        checkout_intent_id TEXT PRIMARY KEY,
        razorpay_order_id TEXT NOT NULL UNIQUE,
        tenant_id TEXT NOT NULL,
        customer_id TEXT NOT NULL,
        relationship_id TEXT NOT NULL,
        accepted_contract_id TEXT NOT NULL,
        contract_version INTEGER NOT NULL,
        contract_hash TEXT NOT NULL,
        contract_acceptance_id TEXT NOT NULL,
        payment_consent_evidence_id TEXT NOT NULL,
        agent_type TEXT NOT NULL,
        bundle_tier TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS payment_intents (
        razorpay_payment_id TEXT PRIMARY KEY,
        razorpay_order_id   TEXT NOT NULL,
        customer_id         TEXT NOT NULL,
        status              TEXT NOT NULL DEFAULT 'IN_PROGRESS',
        tenant_id           TEXT,
        relationship_id     TEXT,
        accepted_contract_id TEXT,
        contract_version    INTEGER,
        contract_hash       TEXT,
        contract_acceptance_id TEXT,
        payment_consent_evidence_id TEXT,
        payment_evidence_id TEXT,
        checkout_intent_id TEXT,
        agent_type          TEXT,
        bundle_tier         TEXT,
        activation_intent_id TEXT,
        activation_correlation_id TEXT,
        outcome_subscription_id TEXT,
        created_at          TEXT NOT NULL DEFAULT (datetime('now')),
        activated_at        TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS paid_subscriptions (
        subscription_id     TEXT PRIMARY KEY,
        organisation_id     TEXT NOT NULL,
        agent_type          TEXT NOT NULL,
        bundle_tier         TEXT NOT NULL,
        razorpay_order_id   TEXT NOT NULL,
        razorpay_payment_id TEXT NOT NULL,
        activated_at        TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS billing_profiles (
        agent_type  TEXT PRIMARY KEY,
        status      TEXT NOT NULL DEFAULT 'PENDING'
    )""",
    """CREATE TABLE IF NOT EXISTS customers (
        id   TEXT PRIMARY KEY,
        mode TEXT NOT NULL DEFAULT 'FREE'
    )""",
    """CREATE TABLE IF NOT EXISTS trial_allocations (
        trial_id            TEXT PRIMARY KEY,
        customer_id         TEXT NOT NULL,
        status              TEXT NOT NULL,
        converted_at        TEXT,
        new_subscription_id TEXT
    )""",
]


@pytest.mark.asyncio
async def test_relationship_checkout_reconciliation_is_exact_bound(payment_session, monkeypatch):
    from payment import router as payment_router

    class SessionContext:
        async def __aenter__(self):
            return payment_session

        async def __aexit__(self, _type, _value, _traceback):
            return False

    monkeypatch.setattr(payment_router, "get_session_factory", lambda: lambda: SessionContext())
    checkout_intent_id = uuid.uuid4()
    tenant_id = uuid.uuid4()
    relationship_id = uuid.uuid4()
    contract_id = uuid.uuid4()
    acceptance_id = uuid.uuid4()
    consent_id = uuid.uuid4()
    evidence_id = uuid.uuid4()
    body = payment_router.RelationshipCheckoutReconcileBody(
        tenant_id=tenant_id,
        relationship_id=relationship_id,
        contract_id=contract_id,
        contract_version=1,
        contract_hash="a" * 64,
        contract_acceptance_id=acceptance_id,
        payment_consent_evidence_id=consent_id,
    )

    unresolved = await payment_router.reconcile_relationship_checkout(checkout_intent_id, body)
    assert unresolved.outcome_kind is CheckoutOutcomeKind.OUTCOME_UNRESOLVED

    await payment_session.execute(text(
        "INSERT INTO payment_intents (razorpay_payment_id, razorpay_order_id, customer_id, status, "
        "tenant_id, relationship_id, accepted_contract_id, contract_version, contract_hash, "
        "contract_acceptance_id, payment_consent_evidence_id, payment_evidence_id, checkout_intent_id, "
        "agent_type, bundle_tier) VALUES (:payment, 'order_exact', :customer, 'CAPTURED', :tenant, "
        ":relationship, :contract, 1, :hash, :acceptance, :consent, :evidence, :checkout, 'DMA', 'STARTER')"
    ).bindparams(
        payment="pay_exact", customer=str(tenant_id), tenant=str(tenant_id),
        relationship=str(relationship_id), contract=str(contract_id), hash="a" * 64,
        acceptance=str(acceptance_id), consent=str(consent_id), evidence=str(evidence_id),
        checkout=str(checkout_intent_id),
    ))
    await payment_session.commit()

    captured = await payment_router.reconcile_relationship_checkout(checkout_intent_id, body)
    assert captured.outcome_kind is CheckoutOutcomeKind.CAPTURED
    assert captured.commercial_outcome_reference == "pay_exact"
    assert captured.commercial_evidence_id == evidence_id
    with pytest.raises(HTTPException) as conflict:
        await payment_router.reconcile_relationship_checkout(
            checkout_intent_id,
            body.model_copy(update={"tenant_id": uuid.uuid4()}),
        )
    assert conflict.value.status_code == 409


@pytest.mark.asyncio
async def test_signed_razorpay_checkout_confirmation_uses_persisted_order(payment_session, monkeypatch):
    from payment import router as payment_router

    class SessionContext:
        async def __aenter__(self):
            return payment_session

        async def __aexit__(self, _type, _value, _traceback):
            return False

    monkeypatch.setattr(payment_router, "get_session_factory", lambda: lambda: SessionContext())
    redis_client = fakeredis.aioredis.FakeRedis()
    monkeypatch.setattr(payment_router.aioredis, "from_url", lambda *_args, **_kwargs: redis_client)
    settings = MagicMock()
    settings.RAZORPAY_KEY_SECRET = "test-secret"
    settings.REDIS_URL = "redis://redis:6379/0"
    monkeypatch.setattr(payment_router, "_settings", settings)
    monkeypatch.setattr(payment_router.RazorpayClient, "fetch_payment", AsyncMock(return_value={
        "id": "pay_test_123", "order_id": "order_test_123", "status": "captured", "currency": "INR",
    }))
    checkout_intent_id = uuid.uuid4()
    ids = [uuid.uuid4() for _ in range(7)]
    await payment_session.execute(text(
        "INSERT INTO razorpay_checkout_orders "
        "(checkout_intent_id, razorpay_order_id, tenant_id, customer_id, relationship_id, "
        "accepted_contract_id, contract_version, contract_hash, contract_acceptance_id, "
        "payment_consent_evidence_id, agent_type, bundle_tier) VALUES "
        "(:checkout, 'order_test_123', :tenant, :customer, :relationship, :contract, 1, :hash, "
        ":acceptance, :consent, 'DMA', 'STARTER')"
    ).bindparams(
        checkout=str(checkout_intent_id), tenant=str(ids[0]), customer=str(ids[1]),
        relationship=str(ids[2]), contract=str(ids[3]), hash="a" * 64,
        acceptance=str(ids[4]), consent=str(ids[5]),
    ))
    await payment_session.commit()
    payment_id = "pay_test_123"
    signature = hmac.new(
        b"test-secret",
        f"order_test_123|{payment_id}".encode(),
        hashlib.sha256,
    ).hexdigest()

    result = await payment_router.confirm_razorpay_checkout(
        checkout_intent_id,
        payment_router.RazorpayCheckoutConfirmationBody(
            razorpay_order_id="order_test_123",
            razorpay_payment_id=payment_id,
            razorpay_signature=signature,
        ),
    )

    assert result.outcome_kind is CheckoutOutcomeKind.CAPTURED
    assert result.relationship_id == ids[2]
    assert result.commercial_outcome_reference == payment_id
    stored = (await payment_session.execute(text(
        "SELECT status, checkout_intent_id FROM payment_intents WHERE razorpay_payment_id = :payment_id"
    ).bindparams(payment_id=payment_id))).fetchone()
    assert stored.status == "CAPTURED"
    assert stored.checkout_intent_id == str(checkout_intent_id)


@pytest.mark.asyncio
async def test_pre_hire_checkout_is_idempotent_and_signature_verified(payment_session, monkeypatch):
    from payment import router as payment_router

    class SessionContext:
        async def __aenter__(self):
            return payment_session

        async def __aexit__(self, _type, _value, _traceback):
            return False

    monkeypatch.setattr(payment_router, "get_session_factory", lambda: lambda: SessionContext())
    settings = MagicMock()
    settings.WAOOAW_ENVIRONMENT = "demo"
    settings.RAZORPAY_KEY_ID = "rzp_test_key"
    settings.RAZORPAY_KEY_SECRET = "test-secret"
    settings.RAZORPAY_MERCHANT_DISPLAY_NAME = "WAOOAW"
    settings.RAZORPAY_READINESS_STATE = "READY_TEST"
    settings.RAZORPAY_CHECKOUT_TTL_SECONDS = 900
    settings.razorpay_enabled_method_families = ("UPI", "CARD")
    monkeypatch.setattr(payment_router, "_settings", settings)
    fetch_payment = AsyncMock(return_value={
        "id": "pay_pre_hire_1", "order_id": "order_pre_hire_1", "status": "captured",
        "currency": "INR", "amount": 249900,
    })
    monkeypatch.setattr(payment_router.RazorpayClient, "fetch_payment", fetch_payment)
    preview = payment_router.HireCommercialPreview(
        outcome_kind="PAYMENT_REQUIRED",
        professional_type="DIGITAL_MARKETING_LOCAL_SERVICE",
        list_price_inr_paise=249900,
        discount_inr_paise=0,
        tax_inr_paise=38120,
        payable_inr_paise=249900,
        cadence="MONTHLY",
        payment_method_required=True,
        payments_enabled=True,
        renewal_consequence="Renews monthly.",
    )
    create_preview = AsyncMock(return_value=preview)
    monkeypatch.setattr(payment_router, "create_hire_commercial_preview", create_preview)
    create_order = AsyncMock(return_value={"id": "order_pre_hire_1"})
    monkeypatch.setattr(payment_router.RazorpayClient, "create_order", create_order)
    checkout_id = uuid.uuid4()
    customer_id = uuid.uuid4()
    body = payment_router.PreHireCheckoutBody(
        checkout_intent_id=checkout_id,
        customer_id=customer_id,
        professional_type="DIGITAL_MARKETING_LOCAL_SERVICE",
        professional_version="1.0.0",
        disclosure_revision="1.0.0",
        terms_version="2026-07-18",
        gross_amount_inr_paise=249900,
        gst_amount_inr_paise=38120,
        cadence="MONTHLY",
    )

    created = await payment_router.create_pre_hire_checkout(body)
    replayed = await payment_router.create_pre_hire_checkout(body)

    assert created.outcome_kind == "RAZORPAY_CHECKOUT_REQUIRED"
    assert created.provider_order_reference == "order_pre_hire_1"
    assert created.public_checkout_key == "rzp_test_key"
    assert replayed.provider_order_reference == created.provider_order_reference
    create_order.assert_awaited_once()
    create_preview.assert_awaited_once()

    payment_id = "pay_pre_hire_1"
    signature = hmac.new(
        b"test-secret",
        f"order_pre_hire_1|{payment_id}".encode(),
        hashlib.sha256,
    ).hexdigest()
    fetch_payment.return_value = {
        "id": payment_id, "order_id": "order_pre_hire_1", "status": "authorized",
        "currency": "INR", "amount": 249900,
    }
    with pytest.raises(HTTPException) as not_captured:
        await payment_router.confirm_pre_hire_checkout(
            checkout_id,
            payment_router.PreHireCheckoutConfirmationBody(
                customer_id=customer_id,
                razorpay_order_id="order_pre_hire_1",
                razorpay_payment_id=payment_id,
                razorpay_signature=signature,
            ),
        )
    assert not_captured.value.status_code == 409
    assert not_captured.value.detail["code"] == "PAYMENT_NOT_CAPTURED"
    fetch_payment.return_value = {
        "id": payment_id, "order_id": "order_pre_hire_1", "status": "captured",
        "currency": "INR", "amount": 249900,
    }
    captured = await payment_router.confirm_pre_hire_checkout(
        checkout_id,
        payment_router.PreHireCheckoutConfirmationBody(
            customer_id=customer_id,
            razorpay_order_id="order_pre_hire_1",
            razorpay_payment_id=payment_id,
            razorpay_signature=signature,
        ),
    )

    assert captured.outcome_kind == "CAPTURED"
    assert captured.commercial_outcome_reference == payment_id
    assert captured.commercial_evidence_id is not None


@pytest.mark.asyncio
async def test_pre_hire_checkout_rejects_invalid_signature(payment_session, monkeypatch):
    from payment import router as payment_router

    class SessionContext:
        async def __aenter__(self):
            return payment_session

        async def __aexit__(self, _type, _value, _traceback):
            return False

    monkeypatch.setattr(payment_router, "get_session_factory", lambda: lambda: SessionContext())
    settings = MagicMock()
    settings.RAZORPAY_KEY_SECRET = "test-secret"
    monkeypatch.setattr(payment_router, "_settings", settings)
    checkout_id = uuid.uuid4()
    customer_id = uuid.uuid4()
    await payment_session.execute(text(
        "INSERT INTO pre_hire_checkout_orders "
        "(checkout_intent_id, customer_id, professional_type, professional_version, "
        "disclosure_revision, terms_version, cadence, list_price_inr_paise, "
        "discount_inr_paise, tax_inr_paise, payable_inr_paise, razorpay_order_id, "
        "commercial_evidence_id, status) VALUES "
        "(:checkout, :customer, 'DIGITAL_MARKETING_LOCAL_SERVICE', '1.0.0', '1.0.0', "
        "'2026-07-18', 'MONTHLY', 249900, 0, 38120, 249900, 'order_pre_hire_2', "
        ":evidence, 'AWAITING_PROVIDER')"
    ).bindparams(
        checkout=str(checkout_id), customer=str(customer_id), evidence=str(uuid.uuid4())
    ))
    await payment_session.commit()

    with pytest.raises(HTTPException) as invalid:
        await payment_router.confirm_pre_hire_checkout(
            checkout_id,
            payment_router.PreHireCheckoutConfirmationBody(
                customer_id=customer_id,
                razorpay_order_id="order_pre_hire_2",
                razorpay_payment_id="pay_pre_hire_2",
                razorpay_signature="0" * 64,
            ),
        )

    assert invalid.value.status_code == 400
    stored = (await payment_session.execute(text(
        "SELECT status FROM pre_hire_checkout_orders WHERE checkout_intent_id = :checkout"
    ).bindparams(checkout=str(checkout_id)))).one()
    assert stored.status == "AWAITING_PROVIDER"


@pytest.mark.asyncio
async def test_pre_hire_webhook_records_capture_without_activating_wallet(payment_session, monkeypatch):
    from payment import router as payment_router

    class SessionContext:
        async def __aenter__(self):
            return payment_session

        async def __aexit__(self, _type, _value, _traceback):
            return False

    monkeypatch.setattr(payment_router, "get_session_factory", lambda: lambda: SessionContext())
    monkeypatch.setattr(payment_router.RazorpayClient, "verify_webhook_signature", lambda *_args: True)
    monkeypatch.setattr(
        payment_router,
        "WalletService",
        MagicMock(side_effect=AssertionError("pre-hire capture must not activate a wallet")),
    )
    checkout_id = uuid.uuid4()
    customer_id = uuid.uuid4()
    evidence_id = uuid.uuid4()
    await payment_session.execute(text(
        "INSERT INTO pre_hire_checkout_orders "
        "(checkout_intent_id, customer_id, professional_type, professional_version, disclosure_revision, "
        "terms_version, cadence, list_price_inr_paise, discount_inr_paise, tax_inr_paise, "
        "payable_inr_paise, razorpay_order_id, commercial_evidence_id, status) VALUES "
        "(:checkout, :customer, 'DIGITAL_MARKETING_LOCAL_SERVICE', '1.0.0', '1.0.0', '2026-07-18', "
        "'MONTHLY', 249900, 0, 38120, 249900, 'order_webhook_1', :evidence, 'AWAITING_PROVIDER')"
    ).bindparams(checkout=str(checkout_id), customer=str(customer_id), evidence=str(evidence_id)))
    await payment_session.commit()
    payload = json.dumps({
        "event": "payment.captured",
        "payload": {"payment": {"entity": {
            "id": "pay_webhook_1",
            "order_id": "order_webhook_1",
            "notes": {
                "checkout_kind": "PRE_HIRE",
                "checkout_intent_id": str(checkout_id),
                "customer_id": str(customer_id),
                "agent_type": "DIGITAL_MARKETING_LOCAL_SERVICE",
                "professional_version": "1.0.0",
            },
        }}},
    }).encode()

    async def receive():
        return {"type": "http.request", "body": payload, "more_body": False}

    request = Request({
        "type": "http",
        "method": "POST",
        "path": "/payments/webhooks/razorpay",
        "headers": [(b"x-razorpay-signature", b"valid")],
    }, receive)
    result = await payment_router.razorpay_webhook(request)

    assert result == {
        "status": "CAPTURED",
        "payment_reference": "pay_webhook_1",
        "payment_evidence_id": str(evidence_id),
    }
    stored = (await payment_session.execute(text(
        "SELECT status, razorpay_payment_id FROM pre_hire_checkout_orders "
        "WHERE checkout_intent_id = :checkout"
    ).bindparams(checkout=str(checkout_id)))).one()
    assert stored.status == "CAPTURED"
    assert stored.razorpay_payment_id == "pay_webhook_1"
    assert (await payment_session.execute(text("SELECT COUNT(*) FROM paid_subscriptions"))).scalar_one() == 0


@pytest.mark.asyncio
async def test_bound_pre_hire_capture_funds_exact_contract_without_second_order(payment_session, monkeypatch):
    from payment import router as payment_router

    class SessionContext:
        async def __aenter__(self):
            return payment_session

        async def __aexit__(self, _type, _value, _traceback):
            return False

    monkeypatch.setattr(payment_router, "get_session_factory", lambda: lambda: SessionContext())
    monkeypatch.setattr(
        payment_router,
        "OnboardingService",
        MagicMock(side_effect=AssertionError("a funded relationship must not create another order")),
    )
    pre_hire_checkout_id = uuid.uuid4()
    relationship_checkout_id = uuid.uuid4()
    customer_id = uuid.uuid4()
    relationship_id = uuid.uuid4()
    evidence_id = uuid.uuid4()
    await payment_session.execute(text(
        "INSERT INTO pre_hire_checkout_orders "
        "(checkout_intent_id, customer_id, professional_type, professional_version, disclosure_revision, "
        "terms_version, cadence, list_price_inr_paise, discount_inr_paise, tax_inr_paise, "
        "payable_inr_paise, razorpay_order_id, razorpay_payment_id, commercial_evidence_id, "
        "relationship_id, status) VALUES (:checkout, :customer, 'DIGITAL_MARKETING_LOCAL_SERVICE', "
        "'1.0.0', '1.0.0', '2026-07-18', 'MONTHLY', 249900, 0, 38120, 249900, "
        "'order_funded_1', 'pay_funded_1', :evidence, :relationship, 'CAPTURED')"
    ).bindparams(
        checkout=str(pre_hire_checkout_id), customer=str(customer_id), evidence=str(evidence_id),
        relationship=str(relationship_id),
    ))
    await payment_session.commit()
    body = payment_router.RelationshipCheckoutBody(
        checkout_intent_id=relationship_checkout_id,
        tenant_id=uuid.uuid4(),
        customer_id=customer_id,
        relationship_id=relationship_id,
        contract_id=uuid.uuid4(),
        contract_version=1,
        contract_hash="a" * 64,
        contract_acceptance_id=uuid.uuid4(),
        payment_consent_evidence_id=uuid.uuid4(),
        agent_type="DIGITAL_MARKETING_LOCAL_SERVICE",
        bundle_tier="STARTER",
        gross_amount_inr_paise=249900,
        gst_amount_inr_paise=38120,
        quote_version="quote-v1",
        idempotency_key="contract-checkout-1",
    )

    with pytest.raises(HTTPException) as price_mismatch:
        await payment_router.create_relationship_checkout(body.model_copy(update={
            "gross_amount_inr_paise": 249901,
        }))
    assert price_mismatch.value.status_code == 409
    assert price_mismatch.value.detail["code"] == "PRE_HIRE_CONTRACT_PRICE_MISMATCH"

    result = await payment_router.create_relationship_checkout(body)

    assert result.outcome_kind is CheckoutOutcomeKind.CAPTURED
    assert result.commercial_outcome_reference == "pay_funded_1"
    payment = (await payment_session.execute(text(
        "SELECT relationship_id, accepted_contract_id, checkout_intent_id, status "
        "FROM payment_intents WHERE razorpay_payment_id = 'pay_funded_1'"
    ))).one()
    assert payment.relationship_id == str(relationship_id)
    assert payment.accepted_contract_id == str(body.contract_id)
    assert payment.checkout_intent_id == str(relationship_checkout_id)
    assert payment.status == "CAPTURED"
    with pytest.raises(HTTPException) as second_contract:
        await payment_router.create_relationship_checkout(body.model_copy(update={
            "checkout_intent_id": uuid.uuid4(),
        }))
    assert second_contract.value.status_code == 409
    assert second_contract.value.detail["code"] == "PRE_HIRE_CONTRACT_CONFLICT"



# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def payment_engine():
    eng = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with eng.begin() as conn:
        for ddl in _PAYMENT_DDL:
            await conn.execute(text(ddl))
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def payment_session(payment_engine):
    factory = async_sessionmaker(payment_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as s:
        yield s


@pytest_asyncio.fixture
def fake_redis():
    return fakeredis.aioredis.FakeRedis()


# ---------------------------------------------------------------------------
# CCT-ONBOARD-01 — Single onboarding order combines subscription + wallet seed
# ---------------------------------------------------------------------------

class TestCCT_ONBOARD_01:
    """ADR-022 §1.2: One Razorpay order = subscription amount + wallet seed. FA-029."""

    @pytest.fixture
    def mock_settings(self):
        s = MagicMock()
        s.RAZORPAY_KEY_ID = "rzp_test_key"
        s.RAZORPAY_KEY_SECRET = "rzp_test_secret"
        s.RAZORPAY_WEBHOOK_SECRET = "rzp_wh_secret"
        s.WAOOAW_ENVIRONMENT = "demo"
        s.DEMO_PROMOTION_ENABLED = True
        s.DEMO_COUPON_CODE = "DEMO100"
        return s

    def test_relationship_order_requires_complete_contract_link_and_forbids_coupon(self):
        relationship_id = uuid.uuid4()
        base = {
            "customer_id": uuid.uuid4(), "agent_type": "DMA", "bundle_tier": "STARTER",
            "subscription_amount_paise": 149900, "wallet_seed_paise": 100000,
        }
        with pytest.raises(ValueError, match="complete contract link"):
            OnboardingOrderBody(**base, relationship_id=relationship_id)
        with pytest.raises(ValueError, match="cannot use payment bypass coupons"):
            OnboardingOrderBody(
                **base, tenant_id=uuid.uuid4(), relationship_id=relationship_id, contract_id=uuid.uuid4(),
                contract_version=1, contract_hash="a" * 64,
                contract_acceptance_id=uuid.uuid4(), payment_consent_evidence_id=uuid.uuid4(),
                coupon_code="DEMO100",
            )

    @pytest.mark.asyncio
    async def test_demo_coupon_bypasses_razorpay(self, mock_settings):
        """DEMO100 coupon → ₹0 bypass order, no Razorpay HTTP call. FA-029."""
        svc = OnboardingService(settings=mock_settings)
        req = OnboardingOrderRequest(
            customer_id=uuid.uuid4(),
            agent_type="DMA",
            bundle_tier="STARTER",
            subscription_amount_paise=49900,
            wallet_seed_paise=100000,
            coupon_code="DEMO100",
        )
        result = await svc.create_onboarding_order(req)

        assert result.is_bypass is True
        assert result.amount_paise == 0
        assert result.currency == "INR"
        assert result.coupon_applied == "DEMO100"
        assert result.order_id.startswith("bypass-")

    @pytest.mark.asyncio
    async def test_uat_coupon_bypasses_razorpay(self, mock_settings):
        """UATWAOOAW coupon → ₹0 bypass order. FA-029."""
        mock_settings.WAOOAW_ENVIRONMENT = "uat"
        mock_settings.DEMO_COUPON_CODE = "UATWAOOAW"
        svc = OnboardingService(settings=mock_settings)
        req = OnboardingOrderRequest(
            customer_id=uuid.uuid4(),
            agent_type="DMA",
            bundle_tier="RUNNER",
            subscription_amount_paise=99900,
            wallet_seed_paise=200000,
            coupon_code="UATWAOOAW",
        )
        result = await svc.create_onboarding_order(req)

        assert result.is_bypass is True
        assert result.amount_paise == 0
        assert result.coupon_applied == "UATWAOOAW"

    @pytest.mark.asyncio
    async def test_coupon_code_case_insensitive(self, mock_settings):
        """Coupon matching is case-insensitive (lowercase → bypass). FA-029."""
        svc = OnboardingService(settings=mock_settings)
        req = OnboardingOrderRequest(
            customer_id=uuid.uuid4(),
            agent_type="DMA",
            bundle_tier="STARTER",
            subscription_amount_paise=49900,
            wallet_seed_paise=50000,
            coupon_code="demo100",
        )
        result = await svc.create_onboarding_order(req)
        assert result.is_bypass is True

    @pytest.mark.asyncio
    @respx.mock
    async def test_production_order_calls_razorpay_with_combined_amount(self, mock_settings):
        """No coupon → Razorpay API called with subscription_amount + wallet_seed. ADR-022 §1.2."""
        cid = uuid.uuid4()
        expected_total = 49900 + 100000  # 1499 + 1000 = 2499 INR

        respx.post("https://api.razorpay.com/v1/orders").mock(
            return_value=Response(
                200,
                json={"id": "order_real_123", "amount": expected_total, "currency": "INR"},
            )
        )

        client = RazorpayClient(settings=mock_settings)
        svc = OnboardingService(razorpay_client=client, settings=mock_settings)
        req = OnboardingOrderRequest(
            customer_id=cid,
            agent_type="DMA",
            bundle_tier="STARTER",
            subscription_amount_paise=49900,
            wallet_seed_paise=100000,
            coupon_code="",  # production — no coupon
        )
        result = await svc.create_onboarding_order(req)

        assert result.is_bypass is False
        assert result.order_id == "order_real_123"
        assert result.amount_paise == expected_total
        assert respx.calls.called

    @pytest.mark.asyncio
    @respx.mock
    async def test_production_order_notes_carry_customer_context(self, mock_settings):
        """Razorpay order notes carry customer_id, agent_type, bundle_tier. ADR-022 §1.2."""
        cid = uuid.uuid4()

        route = respx.post("https://api.razorpay.com/v1/orders").mock(
            return_value=Response(200, json={"id": "order_456", "amount": 0, "currency": "INR"})
        )

        client = RazorpayClient(settings=mock_settings)
        svc = OnboardingService(razorpay_client=client, settings=mock_settings)
        await svc.create_onboarding_order(
            OnboardingOrderRequest(
                customer_id=cid,
                agent_type="DMA",
                bundle_tier="WINNER",
                subscription_amount_paise=199900,
                wallet_seed_paise=500000,
            )
        )

        sent = route.calls[0].request
        import json
        body = json.loads(sent.content)
        assert body["notes"]["customer_id"] == str(cid)
        assert body["notes"]["agent_type"] == "DMA"
        assert body["notes"]["bundle_tier"] == "WINNER"

    @pytest.mark.asyncio
    @respx.mock
    async def test_relationship_order_notes_carry_contract_and_consent_evidence(self, mock_settings):
        """WC059-04: hosted order is bound to accepted contract and explicit proceed evidence."""
        ids = [uuid.uuid4() for _ in range(5)]
        route = respx.post("https://api.razorpay.com/v1/orders").mock(
            return_value=Response(200, json={"id": "order_contract_1"})
        )
        await OnboardingService(
            razorpay_client=RazorpayClient(settings=mock_settings), settings=mock_settings
        ).create_onboarding_order(OnboardingOrderRequest(
            customer_id=ids[0], agent_type="DMA", bundle_tier="STARTER",
            subscription_amount_paise=149900, wallet_seed_paise=100000,
            relationship_id=ids[1], contract_id=ids[2], contract_version=3,
            contract_hash="a" * 64, contract_acceptance_id=ids[3],
            payment_consent_evidence_id=ids[4],
        ))

        import json
        notes = json.loads(route.calls[0].request.content)["notes"]
        assert notes["relationship_id"] == str(ids[1])
        assert notes["contract_id"] == str(ids[2])
        assert notes["contract_version"] == "3"
        assert notes["contract_hash"] == "a" * 64
        assert notes["contract_acceptance_id"] == str(ids[3])
        assert notes["payment_consent_evidence_id"] == str(ids[4])


class TestWC095RelationshipCheckout:
    @staticmethod
    def request() -> RelationshipCheckoutRequest:
        return RelationshipCheckoutRequest(
            checkout_intent_id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            customer_id=uuid.uuid4(),
            relationship_id=uuid.uuid4(),
            contract_id=uuid.uuid4(),
            contract_version=1,
            contract_hash="a" * 64,
            contract_acceptance_id=uuid.uuid4(),
            payment_consent_evidence_id=uuid.uuid4(),
            agent_type="DIGITAL_MARKETING_LOCAL_SERVICE",
            bundle_tier="STARTER",
            gross_amount_inr_paise=249900,
            gst_amount_inr_paise=38120,
            quote_version="quote-v1",
            idempotency_key="checkout-1",
        )

    @pytest.mark.asyncio
    async def test_demo_discount_returns_zero_price_without_calling_razorpay(self):
        settings = MagicMock()
        settings.WAOOAW_ENVIRONMENT = "demo"
        settings.DEMO_PROMOTION_ENABLED = True
        settings.DEMO_PROMOTION_VERSION = "demo-100-v1"
        settings.DEMO_COUPON_CODE = "DEMO100"
        settings.DEMO_RENEWAL_CONSEQUENCE = "Renews at the accepted monthly price."
        settings.MAX_DISCOUNT_PCT = 100
        settings.RAZORPAY_KEY_ID = ""
        settings.RAZORPAY_KEY_SECRET = ""
        settings.RAZORPAY_MERCHANT_DISPLAY_NAME = ""
        settings.RAZORPAY_ENABLED_METHOD_FAMILIES = ""
        settings.RAZORPAY_READINESS_STATE = "NOT_CONFIGURED"
        razorpay = AsyncMock()
        outcomes = AsyncMock()

        result = await OnboardingService(
            razorpay_client=razorpay,
            settings=settings,
            zero_price_outcomes=outcomes,
        ).create_relationship_checkout(self.request())

        assert result.outcome_kind is CheckoutOutcomeKind.FULLY_DISCOUNTED
        assert result.payable_inr_paise == 0
        assert result.discount_inr_paise == result.list_price_inr_paise
        assert result.coupon_code == "DEMO100"
        assert result.commercial_outcome_reference is not None
        assert result.commercial_evidence_id is not None
        assert result.evidence_state == "COMMITTED"
        assert result.order_id is None
        outcomes.record.assert_awaited_once()
        razorpay.create_order.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_missing_razorpay_account_returns_typed_pending_outcome(self):
        settings = MagicMock()
        settings.WAOOAW_ENVIRONMENT = "production"
        settings.DEMO_PROMOTION_ENABLED = False
        settings.RAZORPAY_KEY_ID = ""
        settings.RAZORPAY_KEY_SECRET = ""
        razorpay = AsyncMock()

        result = await OnboardingService(
            razorpay_client=razorpay,
            settings=settings,
        ).create_relationship_checkout(self.request())

        assert result.outcome_kind is CheckoutOutcomeKind.PROVIDER_CONFIGURATION_PENDING
        assert result.reason_code == "RAZORPAY_ACCOUNT_NOT_CONFIGURED"
        assert result.accountable_owner == "PLATFORM_OWNER"
        assert result.retryable is False
        razorpay.create_order.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_payable_checkout_uses_exact_contract_total_and_stable_intent(self):
        settings = MagicMock()
        settings.WAOOAW_ENVIRONMENT = "production"
        settings.DEMO_PROMOTION_ENABLED = False
        settings.RAZORPAY_KEY_ID = "rzp_test_public"
        settings.RAZORPAY_KEY_SECRET = "configured-secret"
        settings.RAZORPAY_MERCHANT_DISPLAY_NAME = "WAOOAW"
        settings.RAZORPAY_ENABLED_METHOD_FAMILIES = "CREDIT_CARD,DEBIT_CARD,UPI,NETBANKING,WALLET"
        settings.RAZORPAY_CHECKOUT_TTL_SECONDS = 900
        settings.RAZORPAY_READINESS_STATE = "READY_LIVE"
        settings.razorpay_enabled_method_families = (
            "CREDIT_CARD", "DEBIT_CARD", "UPI", "NETBANKING", "WALLET",
        )
        razorpay = AsyncMock()
        razorpay.create_order.return_value = {"id": "order_wc095"}
        request = self.request()
        service = OnboardingService(razorpay_client=razorpay, settings=settings)

        first = await service.create_relationship_checkout(request)
        second = await service.create_relationship_checkout(request)

        assert first.outcome_kind is CheckoutOutcomeKind.RAZORPAY_CHECKOUT_REQUIRED
        assert first.checkout_intent_id == second.checkout_intent_id
        assert first.amount_inr_paise == request.gross_amount_inr_paise
        assert first.public_checkout_key == "rzp_test_public"
        assert first.provider_order_reference == "order_wc095"
        assert first.merchant_display_name == "WAOOAW"
        assert first.enabled_method_families == settings.razorpay_enabled_method_families
        assert first.expires_at is not None
        assert first.reconciliation_target is not None
        assert razorpay.create_order.await_args.kwargs["amount_paise"] == request.gross_amount_inr_paise


@pytest.mark.asyncio
@pytest.mark.parametrize("professional_type", [
    "DIGITAL_MARKETING_LOCAL_SERVICE",
    "TUTOR",
    "SHARE_TRADER",
])
async def test_demo_hire_preview_does_not_apply_a_coupon_automatically(monkeypatch, professional_type):
    from payment import router as payment_router

    settings = MagicMock()
    settings.WAOOAW_ENVIRONMENT = "demo"
    settings.DEMO_RENEWAL_CONSEQUENCE = "Standard paid renewal terms apply after the Demo period."
    monkeypatch.setattr(payment_router, "_settings", settings)

    result = await payment_router.create_hire_commercial_preview(HireCommercialPreviewBody(
        professional_type=professional_type,
        gross_amount_inr_paise=118000,
        gst_amount_inr_paise=18000,
        cadence="MONTHLY",
    ))

    assert result.outcome_kind == "PAYMENT_REQUIRED_AFTER_CONTRACT"
    assert result.professional_type == professional_type
    assert result.coupon_code is None
    assert result.discount_inr_paise == 0
    assert result.payable_inr_paise == 118000
    assert result.payment_method_required is True
    assert result.payments_enabled is False


@pytest.mark.asyncio
async def test_hire_preview_applies_an_explicit_registry_validated_coupon(monkeypatch):
    from payment import router as payment_router
    from promotions.models import CouponValidation

    settings = MagicMock()
    settings.WAOOAW_ENVIRONMENT = "demo"
    settings.REDIS_URL = "redis://redis:6379/0"
    settings.DEMO_RENEWAL_CONSEQUENCE = "Standard paid renewal terms apply after the Demo period."
    monkeypatch.setattr(payment_router, "_settings", settings)
    redis_client = AsyncMock()
    monkeypatch.setattr(payment_router.aioredis, "from_url", lambda *_args, **_kwargs: redis_client)
    promotions = MagicMock()
    promotions.validate_commercial_preview_coupon = AsyncMock(return_value=CouponValidation(
        valid=True,
        discount_pct=100,
        bonus_credits={},
        expires_at=None,
    ))
    monkeypatch.setattr(payment_router, "PromotionsService", lambda **_kwargs: promotions)

    result = await payment_router.create_hire_commercial_preview(HireCommercialPreviewBody(
        professional_type="TUTOR",
        gross_amount_inr_paise=118000,
        gst_amount_inr_paise=18000,
        cadence="MONTHLY",
        coupon_code=" welcome100 ",
    ))

    promotions.validate_commercial_preview_coupon.assert_awaited_once_with("WELCOME100", "TUTOR")
    redis_client.aclose.assert_awaited_once()
    assert result.coupon_code == "WELCOME100"
    assert result.discount_inr_paise == 118000
    assert result.payable_inr_paise == 0
    assert result.payment_method_required is False


@pytest.mark.asyncio
@pytest.mark.parametrize("environment", ["uat", "production"])
async def test_non_demo_hire_preview_preserves_contract_bound_payment(monkeypatch, environment):
    from payment import router as payment_router

    settings = MagicMock()
    settings.WAOOAW_ENVIRONMENT = environment
    settings.DEMO_RENEWAL_CONSEQUENCE = "Standard paid renewal terms apply."
    settings.RAZORPAY_KEY_ID = ""
    settings.RAZORPAY_KEY_SECRET = ""
    settings.RAZORPAY_MERCHANT_DISPLAY_NAME = "WAOOAW"
    settings.RAZORPAY_ENABLED_METHOD_FAMILIES = "UPI,CARD,NETBANKING,WALLET"
    settings.RAZORPAY_READINESS_STATE = "NOT_CONFIGURED"
    monkeypatch.setattr(payment_router, "_settings", settings)

    result = await payment_router.create_hire_commercial_preview(HireCommercialPreviewBody(
        professional_type="TUTOR",
        gross_amount_inr_paise=118000,
        gst_amount_inr_paise=18000,
        cadence="MONTHLY",
    ))

    assert result.outcome_kind == "PAYMENT_REQUIRED_AFTER_CONTRACT"
    assert result.coupon_code is None
    assert result.discount_inr_paise == 0
    assert result.payable_inr_paise == 118000
    assert result.payment_method_required is True
    assert result.payments_enabled is False


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("environment", "readiness"),
    [("demo", "READY_TEST"), ("uat", "READY_TEST"), ("production", "READY_LIVE")],
)
async def test_hire_preview_enables_official_checkout_when_razorpay_is_ready(
    monkeypatch,
    environment,
    readiness,
):
    from payment import router as payment_router

    settings = MagicMock()
    settings.WAOOAW_ENVIRONMENT = environment
    settings.DEMO_RENEWAL_CONSEQUENCE = "Standard paid renewal terms apply."
    settings.RAZORPAY_KEY_ID = "rzp_test_public" if environment != "production" else "rzp_live_public"
    settings.RAZORPAY_KEY_SECRET = "configured-secret"
    settings.RAZORPAY_MERCHANT_DISPLAY_NAME = "WAOOAW"
    settings.RAZORPAY_ENABLED_METHOD_FAMILIES = "UPI,CARD,NETBANKING,WALLET"
    settings.RAZORPAY_READINESS_STATE = readiness
    monkeypatch.setattr(payment_router, "_settings", settings)

    result = await payment_router.create_hire_commercial_preview(HireCommercialPreviewBody(
        professional_type="TUTOR",
        gross_amount_inr_paise=118000,
        gst_amount_inr_paise=18000,
        cadence="MONTHLY",
    ))

    assert result.payments_enabled is True


# ---------------------------------------------------------------------------
# CCT-WEBHOOK-01 — payment.captured activates wallet, HMAC verified, idempotent
# ---------------------------------------------------------------------------

class TestCCT_WEBHOOK_01:
    """ADR-022 §1.2: payment.captured → wallet activated, S-09 mode flip before insert."""

    @pytest.fixture
    def mock_settings(self):
        s = MagicMock()
        s.RAZORPAY_KEY_SECRET = "rzp_test_secret"
        s.RAZORPAY_WEBHOOK_SECRET = "rzp_wh_secret"
        return s

    def _make_activation_result(self, customer_id: uuid.UUID) -> SubscriptionActivationResult:
        return SubscriptionActivationResult(
            subscription_id=uuid.uuid4(),
            customer_id=customer_id,
            agent_type="DMA",
            bundle_tier="STARTER",
            activated_at=datetime.now(timezone.utc),
        )

    @pytest.mark.asyncio
    async def test_relationship_capture_waits_for_bp_activation_and_replays_one_subscription(
        self, payment_session, fake_redis, mock_settings
    ):
        customer_id = uuid.uuid4()
        relationship_id = uuid.uuid4()
        contract_id = uuid.uuid4()
        acceptance_id = uuid.uuid4()
        consent_id = uuid.uuid4()
        payment_evidence_id = uuid.uuid4()
        mock_wallet = AsyncMock(spec=WalletService)
        subscription_id = uuid.uuid4()
        mock_wallet.activate_subscription.return_value = SubscriptionActivationResult(
            subscription_id=subscription_id, customer_id=customer_id, agent_type="DMA",
            bundle_tier="STARTER", activated_at=datetime.now(timezone.utc),
        )
        mock_razorpay = MagicMock(spec=RazorpayClient)
        mock_razorpay.verify_payment_signature.return_value = True
        handler = WebhookHandler(
            db=payment_session, wallet_service=mock_wallet,
            razorpay_client=mock_razorpay, settings=mock_settings,
        )
        event = PaymentCapturedEvent(
            razorpay_order_id="order_relationship", razorpay_payment_id="pay_relationship",
            razorpay_signature="valid", customer_id=customer_id, agent_type="DMA",
            bundle_tier="STARTER", tenant_id=customer_id, relationship_id=relationship_id,
            accepted_contract_id=contract_id, contract_version=1, contract_hash="a" * 64,
            contract_acceptance_id=acceptance_id,
            payment_consent_evidence_id=consent_id, payment_evidence_id=payment_evidence_id,
        )

        captured = await handler.handle_payment_captured(event)

        assert captured.status == "CAPTURED"
        mock_wallet.activate_subscription.assert_not_awaited()
        activation_request = PaidActivationRequest(
            tenant_id=customer_id, relationship_id=relationship_id, activation_intent_id=uuid.uuid4(),
            accepted_contract_id=contract_id, contract_version=1, contract_acceptance_id=acceptance_id,
            payment_reference="pay_relationship", payment_evidence_id=payment_evidence_id,
            correlation_id=uuid.uuid4(),
        )
        service = PaidActivationService(payment_session, mock_wallet)
        with pytest.raises(HTTPException) as cross_tenant:
            await service.activate(replace(activation_request, tenant_id=uuid.uuid4()))
        assert cross_tenant.value.status_code == 409
        with pytest.raises(HTTPException) as stale_contract:
            await service.activate(replace(activation_request, contract_version=2))
        assert stale_contract.value.status_code == 409
        mock_wallet.activate_subscription.assert_not_awaited()

        first = await service.activate(activation_request)
        replay = await service.activate(activation_request)

        assert first.subscription_id == replay.subscription_id == subscription_id
        mock_wallet.activate_subscription.assert_awaited_once()
        stored = (await payment_session.execute(text(
            "SELECT status, outcome_subscription_id FROM payment_intents WHERE razorpay_payment_id = 'pay_relationship'"
        ))).fetchone()
        assert stored.status == "ACTIVATED"
        assert stored.outcome_subscription_id == str(subscription_id)

    @pytest.mark.asyncio
    async def test_bypass_order_activates_subscription_without_signature_check(
        self, payment_session, mock_settings
    ):
        """Bypass order (is_bypass=True) skips HMAC check and activates subscription."""
        cid = uuid.uuid4()
        mock_wallet = AsyncMock(spec=WalletService)
        mock_wallet.activate_subscription.return_value = self._make_activation_result(cid)

        handler = WebhookHandler(
            db=payment_session,
            wallet_service=mock_wallet,
            settings=mock_settings,
        )
        event = PaymentCapturedEvent(
            razorpay_order_id=f"bypass-{cid}",
            razorpay_payment_id="pay_bypass_001",
            razorpay_signature="",  # empty — not verified for bypass
            customer_id=cid,
            agent_type="DMA",
            bundle_tier="STARTER",
        )
        result = await handler.handle_payment_captured(event, is_bypass=True)

        assert result.customer_id == cid
        mock_wallet.activate_subscription.assert_awaited_once()
        # S-09: activate_subscription called with the correct order_id
        call_kwargs = mock_wallet.activate_subscription.call_args.kwargs
        assert call_kwargs["razorpay_order_id"] == f"bypass-{cid}"

    @pytest.mark.asyncio
    async def test_invalid_signature_raises_400(self, payment_session, mock_settings):
        """Invalid HMAC signature → HTTP 400. ADR-014 / ADR-022 §1.2."""
        mock_wallet = AsyncMock(spec=WalletService)
        mock_razorpay = MagicMock(spec=RazorpayClient)
        mock_razorpay.verify_payment_signature.return_value = False

        handler = WebhookHandler(
            db=payment_session,
            wallet_service=mock_wallet,
            razorpay_client=mock_razorpay,
            settings=mock_settings,
        )
        event = PaymentCapturedEvent(
            razorpay_order_id="order_real",
            razorpay_payment_id="pay_real_001",
            razorpay_signature="bad_sig",
            customer_id=uuid.uuid4(),
            agent_type="DMA",
            bundle_tier="STARTER",
        )
        with pytest.raises(HTTPException) as exc_info:
            await handler.handle_payment_captured(event, is_bypass=False)

        assert exc_info.value.status_code == 400
        assert exc_info.value.detail["code"] == "INVALID_SIGNATURE"
        mock_wallet.activate_subscription.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_duplicate_payment_id_is_idempotent(self, payment_session, mock_settings):
        """Second call with same payment_id returns gracefully without re-activating. C-002."""
        cid = uuid.uuid4()
        pay_id = "pay_idempotent_001"

        # Pre-insert an already-activated payment_intent
        await payment_session.execute(
            text(
                "INSERT INTO payment_intents "
                "(razorpay_payment_id, razorpay_order_id, customer_id, status) "
                "VALUES (:pid, :oid, :cid, 'ACTIVATED')"
            ).bindparams(pid=pay_id, oid="order_abc", cid=str(cid))
        )
        # Pre-insert matching subscription so the handler can fetch it
        await payment_session.execute(
            text(
                "INSERT INTO paid_subscriptions "
                "(subscription_id, organisation_id, agent_type, bundle_tier, razorpay_order_id, "
                "razorpay_payment_id, activated_at) "
                "VALUES (:sid, :cid, 'DMA', 'STARTER', 'order_abc', :pid, datetime('now'))"
            ).bindparams(sid=str(uuid.uuid4()), cid=str(cid), pid=pay_id)
        )
        await payment_session.commit()

        mock_wallet = AsyncMock(spec=WalletService)
        handler = WebhookHandler(
            db=payment_session,
            wallet_service=mock_wallet,
            settings=mock_settings,
        )
        event = PaymentCapturedEvent(
            razorpay_order_id="order_abc",
            razorpay_payment_id=pay_id,
            razorpay_signature="",
            customer_id=cid,
            agent_type="DMA",
            bundle_tier="STARTER",
        )
        result = await handler.handle_payment_captured(event, is_bypass=True)

        # activate_subscription must NOT be called again
        mock_wallet.activate_subscription.assert_not_awaited()
        assert result.customer_id == cid


# ---------------------------------------------------------------------------
# CCT-GRANDFATHER-01 — C-090 grandfather pricing at renewal
# ---------------------------------------------------------------------------

# Session-mock helpers (service uses schema-qualified table names incompatible with SQLite)
def _mock_session(*execute_side_effects):
    s = MagicMock()
    s.execute = AsyncMock(side_effect=list(execute_side_effects))
    s.commit = AsyncMock()
    return s


def _fetchone(row_or_none):
    r = MagicMock()
    r.fetchone = MagicMock(return_value=row_or_none)
    return r


def _contract_row(agreed: int, plan: int):
    row = MagicMock()
    row.id = str(uuid.uuid4())
    row.agreed_price_paise = agreed
    row.plan_price_paise = plan
    row.customer_id = str(uuid.uuid4())
    row.thread_type = "DMA"
    return row


class TestCCT_GRANDFATHER_01:
    """C-090: subscription renewal blocked when plan price > agreed price without notice."""

    @pytest.mark.asyncio
    async def test_renewal_blocked_when_price_increased_without_notice(self, fake_redis):
        """Plan price > agreed price, no acknowledged notice → HTTP 422. C-090."""
        session = _mock_session(
            _fetchone(_contract_row(agreed=49900, plan=59900)),  # contract fetch
            _fetchone(None),                                      # no notice
        )
        svc = WalletService(db=session, redis_client=fake_redis)

        with pytest.raises(HTTPException) as exc_info:
            await svc.renew(
                customer_id=uuid.uuid4(),
                contract_id=uuid.uuid4(),
                new_period_start=datetime.now(timezone.utc).date(),
            )

        assert exc_info.value.status_code == 422
        assert exc_info.value.detail["code"] == "PRICE_INCREASE_WITHOUT_NOTICE"

    @pytest.mark.asyncio
    async def test_renewal_allowed_with_acknowledged_notice(self, fake_redis):
        """Plan price > agreed price AND acknowledged notice exists → renewal proceeds. C-090."""
        notice_row = MagicMock()
        notice_row.id = str(uuid.uuid4())
        session = _mock_session(
            _fetchone(_contract_row(agreed=49900, plan=59900)),  # contract fetch
            _fetchone(notice_row),                               # notice found
            MagicMock(),                                          # UPDATE
        )
        svc = WalletService(db=session, redis_client=fake_redis)

        result = await svc.renew(
            customer_id=uuid.uuid4(),
            contract_id=uuid.uuid4(),
            new_period_start=datetime.now(timezone.utc).date(),
        )

        assert isinstance(result, RenewalResult)

    @pytest.mark.asyncio
    async def test_renewal_allowed_at_same_price(self, fake_redis):
        """Plan price == agreed price → no notice query made, renewal proceeds. C-090."""
        session = _mock_session(
            _fetchone(_contract_row(agreed=49900, plan=49900)),  # contract fetch
            MagicMock(),                                          # UPDATE
        )
        svc = WalletService(db=session, redis_client=fake_redis)

        result = await svc.renew(
            customer_id=uuid.uuid4(),
            contract_id=uuid.uuid4(),
            new_period_start=datetime.now(timezone.utc).date(),
        )

        assert isinstance(result, RenewalResult)

    @pytest.mark.asyncio
    async def test_renewal_blocked_with_unacknowledged_notice(self, fake_redis):
        """Notice exists but acknowledged_at IS NULL → still blocked. C-090."""
        session = _mock_session(
            _fetchone(_contract_row(agreed=49900, plan=59900)),  # contract fetch
            _fetchone(None),                                      # notice query returns None (acknowledged_at IS NOT NULL filters it out)
        )
        svc = WalletService(db=session, redis_client=fake_redis)

        with pytest.raises(HTTPException) as exc_info:
            await svc.renew(
                customer_id=uuid.uuid4(),
                contract_id=uuid.uuid4(),
                new_period_start=datetime.now(timezone.utc).date(),
            )

        assert exc_info.value.status_code == 422


# ---------------------------------------------------------------------------
# Payment router HTTP-level tests (covers payment/router.py lines 52-62, 77-115, 125-143)
# ---------------------------------------------------------------------------


class TestPaymentRouterHTTP:
    """HTTP-level tests for payment/router.py route handlers."""

    @pytest.mark.asyncio
    async def test_onboarding_order_endpoint_demo_coupon(self, monkeypatch):
        """POST /payments/onboarding-order with DEMO100 → router returns bypass order."""
        from httpx import ASGITransport, AsyncClient
        from main import app
        from payment import router as payment_router

        monkeypatch.setattr(payment_router._settings, "WAOOAW_ENVIRONMENT", "demo")
        monkeypatch.setattr(payment_router._settings, "DEMO_PROMOTION_ENABLED", True)
        monkeypatch.setattr(payment_router._settings, "DEMO_COUPON_CODE", "DEMO100")

        body = {
            "customer_id": str(uuid.uuid4()),
            "agent_type": "DMA",
            "bundle_tier": "STARTER",
            "subscription_amount_paise": 49900,
            "wallet_seed_paise": 100000,
            "coupon_code": "DEMO100",
        }
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as c:
            resp = await c.post("/payments/onboarding-order", json=body)

        assert resp.status_code == 200
        data = resp.json()
        assert data["is_bypass"] is True
        assert data["amount_paise"] == 0
        assert data["coupon_applied"] == "DEMO100"

    @pytest.mark.asyncio
    async def test_webhook_ignores_non_payment_captured_events(self):
        """POST /payments/webhooks/razorpay with unknown event → 200 ignored."""
        from httpx import ASGITransport, AsyncClient
        from main import app

        payload = {
            "event": "order.paid",
            "payload": {},
        }
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as c:
            resp = await c.post(
                "/payments/webhooks/razorpay",
                json=payload,
                headers={"X-Razorpay-Signature": ""},
            )

        assert resp.status_code == 200
        assert resp.json()["status"] == "ignored"
        assert resp.json()["event"] == "order.paid"

    @pytest.mark.asyncio
    async def test_webhook_returns_400_when_customer_id_missing(self):
        """POST /payments/webhooks/razorpay with missing customer_id → 400 MISSING_CUSTOMER_ID."""
        from httpx import ASGITransport, AsyncClient
        from main import app

        payload = {
            "event": "payment.captured",
            "payload": {
                "payment": {
                    "entity": {
                        "order_id": "order_abc",
                        "id": "pay_abc",
                        "notes": {},
                    }
                }
            },
        }
        raw_body = json.dumps(payload, separators=(",", ":")).encode()
        from payment.router import _settings
        signature = hmac.new(_settings.RAZORPAY_WEBHOOK_SECRET.encode(), raw_body, hashlib.sha256).hexdigest()
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as c:
            resp = await c.post(
                "/payments/webhooks/razorpay",
                content=raw_body,
                headers={"Content-Type": "application/json", "X-Razorpay-Signature": signature},
            )

        assert resp.status_code == 400
        assert resp.json()["detail"]["code"] == "MISSING_CUSTOMER_ID"

    @pytest.mark.asyncio
    async def test_webhook_rejects_invalid_raw_body_signature_before_capture(self):
        from httpx import ASGITransport, AsyncClient
        from main import app

        raw_body = json.dumps({
            "event": "payment.captured",
            "payload": {"payment": {"entity": {"id": "pay_tampered", "notes": {}}}},
        }, separators=(",", ":")).encode()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/payments/webhooks/razorpay",
                content=raw_body,
                headers={"Content-Type": "application/json", "X-Razorpay-Signature": "invalid"},
            )

        assert response.status_code == 400
        assert response.json()["detail"]["code"] == "INVALID_SIGNATURE"

    @pytest.mark.asyncio
    async def test_activate_bypass_returns_400_when_not_bypass(self):
        """POST /payments/activate-bypass with is_bypass=False → 400 NOT_A_BYPASS_ORDER."""
        from httpx import ASGITransport, AsyncClient
        from main import app

        body = {
            "razorpay_order_id": "order_abc",
            "razorpay_payment_id": "pay_abc",
            "razorpay_signature": "",
            "customer_id": str(uuid.uuid4()),
            "agent_type": "DMA",
            "bundle_tier": "STARTER",
            "is_bypass": False,
        }
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as c:
            resp = await c.post("/payments/activate-bypass", json=body)

        assert resp.status_code == 400
        assert resp.json()["detail"]["code"] == "NOT_A_BYPASS_ORDER"
