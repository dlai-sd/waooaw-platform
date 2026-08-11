# Implements: adr/ADR-022-payment-processing-razorpay-india.md §Amendment 1.2
# constitutional_basis: C-059, C-088, C-090
"""Payment FastAPI router — onboarding order + Razorpay webhook endpoint."""
from __future__ import annotations

import logging
from uuid import NAMESPACE_URL, UUID, uuid5

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field, model_validator

import redis.asyncio as aioredis
from database import get_session_factory
from config import Settings
from payment.models import OnboardingOrderRequest, PaymentCapturedEvent
from payment.onboarding import OnboardingService
from payment.razorpay_client import RazorpayClient
from payment.webhook import WebhookHandler
from wallet.service import WalletService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/payments", tags=["payments"])

_settings = Settings()


class OnboardingOrderBody(BaseModel):
    tenant_id: UUID | None = None
    customer_id: UUID
    agent_type: str
    bundle_tier: str
    subscription_amount_paise: int = Field(gt=0)
    wallet_seed_paise: int = Field(ge=0)
    coupon_code: str = ""
    relationship_id: UUID | None = None
    contract_id: UUID | None = None
    contract_version: int | None = Field(default=None, gt=0)
    contract_hash: str = Field(default="", pattern=r"^[0-9a-f]{64}$|^$")
    contract_acceptance_id: UUID | None = None
    payment_consent_evidence_id: UUID | None = None

    @model_validator(mode="after")
    def require_complete_contract_link(self) -> OnboardingOrderBody:
        if self.relationship_id is not None and self.coupon_code:
            raise ValueError("relationship onboarding orders cannot use payment bypass coupons")
        contract_link = (
            self.tenant_id,
            self.relationship_id,
            self.contract_id,
            self.contract_version,
            self.contract_hash or None,
            self.contract_acceptance_id,
            self.payment_consent_evidence_id,
        )
        if any(value is not None for value in contract_link) and any(
            value is None for value in contract_link
        ):
            raise ValueError("relationship onboarding orders require the complete contract link")
        return self


class PaymentCaptureBody(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str
    customer_id: UUID
    agent_type: str
    bundle_tier: str
    is_bypass: bool = False


@router.post("/onboarding-order")
async def create_onboarding_order(body: OnboardingOrderBody) -> dict:
    """Create a Razorpay order combining first-month subscription + wallet seed (ADR-022 §1.2).

    Demo/UAT: DEMOWAOOAW / UATWAOOAW coupon → ₹0 bypass order, no Razorpay API call. FA-029.
    """
    svc = OnboardingService(settings=_settings)
    req = OnboardingOrderRequest(
        customer_id=body.customer_id,
        agent_type=body.agent_type,
        bundle_tier=body.bundle_tier,
        subscription_amount_paise=body.subscription_amount_paise,
        wallet_seed_paise=body.wallet_seed_paise,
        coupon_code=body.coupon_code,
        tenant_id=body.tenant_id,
        relationship_id=body.relationship_id,
        contract_id=body.contract_id,
        contract_version=body.contract_version,
        contract_hash=body.contract_hash,
        contract_acceptance_id=body.contract_acceptance_id,
        payment_consent_evidence_id=body.payment_consent_evidence_id,
    )
    result = await svc.create_onboarding_order(req)
    return {
        "order_id": result.order_id,
        "amount_paise": result.amount_paise,
        "currency": result.currency,
        "is_bypass": result.is_bypass,
        "coupon_applied": result.coupon_applied,
    }


@router.post("/webhooks/razorpay")
async def razorpay_webhook(request: Request) -> dict:
    """Razorpay webhook endpoint — handles payment.captured.

    Signature verified via HMAC-SHA256 (ADR-014). Idempotent (payment_intents table).
    """
    signature = request.headers.get("X-Razorpay-Signature", "")
    payload = await request.json()

    event_type = payload.get("event", "")
    if event_type != "payment.captured":
        # Acknowledge unhandled events gracefully
        return {"status": "ignored", "event": event_type}

    payment = payload.get("payload", {}).get("payment", {}).get("entity", {})
    notes = payment.get("notes", {})

    try:
        customer_id = UUID(notes.get("customer_id", ""))
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail={"code": "MISSING_CUSTOMER_ID"}) from None

    event = PaymentCapturedEvent(
        razorpay_order_id=payment.get("order_id", ""),
        razorpay_payment_id=payment.get("id", ""),
        razorpay_signature=signature,
        customer_id=customer_id,
        agent_type=notes.get("agent_type", ""),
        bundle_tier=notes.get("bundle_tier", ""),
        tenant_id=_optional_uuid(notes.get("tenant_id")),
        relationship_id=_optional_uuid(notes.get("relationship_id")),
        accepted_contract_id=_optional_uuid(notes.get("contract_id")),
        contract_version=int(notes["contract_version"]) if notes.get("contract_version") else None,
        contract_hash=notes.get("contract_hash", ""),
        contract_acceptance_id=_optional_uuid(notes.get("contract_acceptance_id")),
        payment_consent_evidence_id=_optional_uuid(notes.get("payment_consent_evidence_id")),
        payment_evidence_id=uuid5(NAMESPACE_URL, f"waooaw:payment:{payment.get('id', '')}"),
    )

    session_factory = get_session_factory()
    async with session_factory() as db:
        redis_client = aioredis.from_url(_settings.REDIS_URL, decode_responses=True)
        wallet_svc = WalletService(db=db, redis_client=redis_client)
        razorpay_client = RazorpayClient(settings=_settings)
        handler = WebhookHandler(
            db=db,
            wallet_service=wallet_svc,
            razorpay_client=razorpay_client,
            settings=_settings,
        )
        result = await handler.handle_payment_captured(event, is_bypass=False)

    if hasattr(result, "payment_evidence_id"):
        return {
            "status": result.status,
            "payment_reference": result.payment_reference,
            "payment_evidence_id": str(result.payment_evidence_id),
        }
    return {"status": "activated", "subscription_id": str(result.subscription_id), "customer_id": str(result.customer_id)}


def _optional_uuid(value: object) -> UUID | None:
    if value in (None, ""):
        return None
    try:
        return UUID(str(value))
    except (ValueError, TypeError, AttributeError):
        raise HTTPException(status_code=400, detail={"code": "INVALID_CONTRACT_LINK"}) from None


@router.post("/activate-bypass")
async def activate_bypass(body: PaymentCaptureBody) -> dict:
    """Activate subscription for demo/UAT bypass order (coupon = 100% discount). FA-029."""
    if not body.is_bypass:
        raise HTTPException(status_code=400, detail={"code": "NOT_A_BYPASS_ORDER"})

    event = PaymentCapturedEvent(
        razorpay_order_id=body.razorpay_order_id,
        razorpay_payment_id=body.razorpay_payment_id,
        razorpay_signature="",
        customer_id=body.customer_id,
        agent_type=body.agent_type,
        bundle_tier=body.bundle_tier,
    )
    session_factory = get_session_factory()
    async with session_factory() as db:
        redis_client = aioredis.from_url(_settings.REDIS_URL, decode_responses=True)
        wallet_svc = WalletService(db=db, redis_client=redis_client)
        handler = WebhookHandler(db=db, wallet_service=wallet_svc, settings=_settings)
        result = await handler.handle_payment_captured(event, is_bypass=True)

    return {
        "status": "activated",
        "subscription_id": str(result.subscription_id),
        "customer_id": str(result.customer_id),
    }
