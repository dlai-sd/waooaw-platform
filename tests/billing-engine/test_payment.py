# Implements: work-contracts/WC-042-wbe-s7-onboarding-payment-renewal-saga.md §WC042-05
# constitutional_basis: C-059, ADR-022 §1.2/1.3/1.4, C-090, FA-029
"""
CCT-ONBOARD-01   — Single onboarding order: subscription + wallet seed in one Razorpay call.
CCT-WEBHOOK-01   — payment.captured webhook: HMAC verified, idempotent, activates wallet.
CCT-GRANDFATHER-01 — C-090: renewal blocked when plan price > agreed price without notice.
"""
from __future__ import annotations

import uuid
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

from payment.models import OnboardingOrderRequest, PaymentCapturedEvent
from payment.onboarding import OnboardingService
from payment.razorpay_client import RazorpayClient
from payment.webhook import WebhookHandler
from wallet.models import RenewalResult, SubscriptionActivationResult
from wallet.service import WalletService


# ---------------------------------------------------------------------------
# Schema DDL (SQLite in-memory)
# ---------------------------------------------------------------------------

_PAYMENT_DDL = [
    """CREATE TABLE IF NOT EXISTS payment_intents (
        razorpay_payment_id TEXT PRIMARY KEY,
        razorpay_order_id   TEXT NOT NULL,
        customer_id         TEXT NOT NULL,
        status              TEXT NOT NULL DEFAULT 'IN_PROGRESS',
        created_at          TEXT NOT NULL DEFAULT (datetime('now')),
        activated_at        TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS subscriptions (
        id                  TEXT PRIMARY KEY,
        customer_id         TEXT NOT NULL,
        agent_type          TEXT NOT NULL,
        bundle_tier         TEXT NOT NULL,
        razorpay_order_id   TEXT NOT NULL,
        razorpay_payment_id TEXT NOT NULL,
        activated_at        TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS billing_profiles (
        id          TEXT PRIMARY KEY,
        customer_id TEXT NOT NULL,
        status      TEXT NOT NULL DEFAULT 'PENDING'
    )""",
    """CREATE TABLE IF NOT EXISTS customers (
        id   TEXT PRIMARY KEY,
        mode TEXT NOT NULL DEFAULT 'FREE'
    )""",
]



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
        return s

    @pytest.mark.asyncio
    async def test_demo_coupon_bypasses_razorpay(self, mock_settings):
        """DEMOWAOOAW coupon → ₹0 bypass order, no Razorpay HTTP call. FA-029."""
        svc = OnboardingService(settings=mock_settings)
        req = OnboardingOrderRequest(
            customer_id=uuid.uuid4(),
            agent_type="DMA",
            bundle_tier="STARTER",
            subscription_amount_paise=49900,
            wallet_seed_paise=100000,
            coupon_code="DEMOWAOOAW",
        )
        result = await svc.create_onboarding_order(req)

        assert result.is_bypass is True
        assert result.amount_paise == 0
        assert result.currency == "INR"
        assert result.coupon_applied == "DEMOWAOOAW"
        assert result.order_id.startswith("bypass-")

    @pytest.mark.asyncio
    async def test_uat_coupon_bypasses_razorpay(self, mock_settings):
        """UATWAOOAW coupon → ₹0 bypass order. FA-029."""
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
            coupon_code="demowaooaw",
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
                "INSERT INTO subscriptions "
                "(id, customer_id, agent_type, bundle_tier, razorpay_order_id, "
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
    async def test_onboarding_order_endpoint_demo_coupon(self):
        """POST /payments/onboarding-order with DEMOWAOOAW → router returns bypass order."""
        from httpx import ASGITransport, AsyncClient
        from main import app

        body = {
            "customer_id": str(uuid.uuid4()),
            "agent_type": "DMA",
            "bundle_tier": "STARTER",
            "subscription_amount_paise": 49900,
            "wallet_seed_paise": 100000,
            "coupon_code": "DEMOWAOOAW",
        }
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as c:
            resp = await c.post("/payments/onboarding-order", json=body)

        assert resp.status_code == 200
        data = resp.json()
        assert data["is_bypass"] is True
        assert data["amount_paise"] == 0
        assert data["coupon_applied"] == "DEMOWAOOAW"

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
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as c:
            resp = await c.post(
                "/payments/webhooks/razorpay",
                json=payload,
                headers={"X-Razorpay-Signature": "sig"},
            )

        assert resp.status_code == 400
        assert resp.json()["detail"]["code"] == "MISSING_CUSTOMER_ID"

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
