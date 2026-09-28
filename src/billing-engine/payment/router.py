# Implements: architecture/reference/api-specs/business-platform.openapi.yaml §RelationshipCheckoutOutcome
# Constitutional basis: C-059, C-088, C-090
"""Payment FastAPI router — onboarding order + Razorpay webhook endpoint."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from uuid import NAMESPACE_URL, UUID, uuid5

import redis.asyncio as aioredis
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_session_factory
from config import Settings
from payment.models import (
    CheckoutOutcomeKind,
    OnboardingOrderRequest,
    PaymentCapturedEvent,
    PaymentEnvironment,
    RelationshipCheckoutRequest,
    RelationshipCheckoutResult,
)
from payment.commercial_outcomes import ZeroPriceCommercialOutcomeStore
from payment.onboarding import OnboardingService
from payment.razorpay_client import RazorpayClient
from payment.webhook import WebhookHandler
from promotions.service import PromotionsService
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


class HireCommercialPreviewBody(BaseModel):
    professional_type: str = Field(min_length=1, max_length=64)
    gross_amount_inr_paise: int = Field(gt=0)
    gst_amount_inr_paise: int = Field(ge=0)
    cadence: str = Field(min_length=1, max_length=32)
    coupon_code: str | None = Field(default=None, max_length=64)


class HireCommercialPreview(BaseModel):
    outcome_kind: str
    professional_type: str
    list_price_inr_paise: int
    discount_inr_paise: int
    tax_inr_paise: int
    payable_inr_paise: int
    currency: str = "INR"
    cadence: str
    coupon_code: str | None = None
    provider: str = "RAZORPAY"
    payment_method_required: bool
    payments_enabled: bool
    renewal_consequence: str


class RelationshipCheckoutBody(BaseModel):
    checkout_intent_id: UUID
    tenant_id: UUID
    customer_id: UUID
    relationship_id: UUID
    contract_id: UUID
    contract_version: int = Field(gt=0)
    contract_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    contract_acceptance_id: UUID
    payment_consent_evidence_id: UUID
    agent_type: str = Field(min_length=1)
    bundle_tier: str = Field(min_length=1)
    gross_amount_inr_paise: int = Field(gt=0)
    gst_amount_inr_paise: int = Field(ge=0)
    quote_version: str = Field(min_length=1)
    idempotency_key: str = Field(min_length=1, max_length=200)


class RelationshipCheckoutReconcileBody(BaseModel):
    tenant_id: UUID
    relationship_id: UUID
    contract_id: UUID
    contract_version: int = Field(gt=0)
    contract_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    contract_acceptance_id: UUID
    payment_consent_evidence_id: UUID


class RazorpayCheckoutConfirmationBody(BaseModel):
    razorpay_order_id: str = Field(min_length=1, max_length=128)
    razorpay_payment_id: str = Field(min_length=1, max_length=128)
    razorpay_signature: str = Field(min_length=1, max_length=256)


class PreHireCheckoutBody(HireCommercialPreviewBody):
    checkout_intent_id: UUID
    customer_id: UUID
    professional_version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    disclosure_revision: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    terms_version: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")


class PreHireCheckoutConfirmationBody(RazorpayCheckoutConfirmationBody):
    checkout_intent_id: UUID
    customer_id: UUID


class PreHireCheckoutBindingBody(BaseModel):
    checkout_intent_id: UUID
    customer_id: UUID
    relationship_id: UUID


class PreHireCheckoutOutcome(BaseModel):
    outcome_kind: str
    checkout_intent_id: UUID
    provider_order_reference: str | None = None
    public_checkout_key: str | None = None
    amount_inr_paise: int
    currency: str = "INR"
    merchant_display_name: str | None = None
    enabled_method_families: list[str] | None = None
    expires_at: datetime | None = None
    list_price_inr_paise: int
    discount_inr_paise: int
    tax_inr_paise: int
    payable_inr_paise: int
    coupon_code: str | None = None
    commercial_outcome_reference: str | None = None
    commercial_evidence_id: UUID | None = None
    customer_safe_next_action: str | None = None


@router.post("/hire-preview", response_model=HireCommercialPreview)
async def create_hire_commercial_preview(body: HireCommercialPreviewBody) -> HireCommercialPreview:
    """Return server-owned commercial truth before a Hire relationship is created."""
    if body.gst_amount_inr_paise > body.gross_amount_inr_paise:
        raise HTTPException(status_code=422, detail={"code": "INVALID_COMMERCIAL_PREVIEW"})
    coupon_code = body.coupon_code.strip().upper() if body.coupon_code else None
    discount_pct = 0
    if coupon_code:
        redis_client = aioredis.from_url(_settings.REDIS_URL, decode_responses=False)
        try:
            validation = await PromotionsService(
                session_factory=get_session_factory(),
                redis_client=redis_client,
                settings=_settings,
            ).validate_commercial_preview_coupon(coupon_code, body.professional_type)
        finally:
            await redis_client.aclose()
        if not validation.valid:
            raise HTTPException(status_code=422, detail={"code": validation.error_code or "COUPON_INVALID"})
        discount_pct = validation.discount_pct
    discount = body.gross_amount_inr_paise * discount_pct // 100
    fully_discounted = discount == body.gross_amount_inr_paise
    expected_readiness = (
        "READY_LIVE"
        if _settings.WAOOAW_ENVIRONMENT == PaymentEnvironment.PRODUCTION.value
        else "READY_TEST"
    )
    configured_values = (
        _settings.RAZORPAY_KEY_ID,
        _settings.RAZORPAY_KEY_SECRET,
        _settings.RAZORPAY_MERCHANT_DISPLAY_NAME,
        _settings.RAZORPAY_ENABLED_METHOD_FAMILIES,
    )
    payments_enabled = (
        all(isinstance(value, str) and bool(value.strip()) for value in configured_values)
        and _settings.RAZORPAY_READINESS_STATE == expected_readiness
    )
    return HireCommercialPreview(
        outcome_kind="FULLY_DISCOUNTED" if fully_discounted else "PAYMENT_REQUIRED_AFTER_CONTRACT",
        professional_type=body.professional_type,
        list_price_inr_paise=body.gross_amount_inr_paise,
        discount_inr_paise=discount,
        tax_inr_paise=body.gst_amount_inr_paise,
        payable_inr_paise=body.gross_amount_inr_paise - discount,
        cadence=body.cadence,
        coupon_code=coupon_code,
        payment_method_required=not fully_discounted,
        payments_enabled=payments_enabled,
        renewal_consequence=_settings.DEMO_RENEWAL_CONSEQUENCE,
    )


def _pre_hire_outcome(row: object) -> PreHireCheckoutOutcome:
    status = str(row.status)
    return PreHireCheckoutOutcome(
        outcome_kind={
            "AWAITING_PROVIDER": "RAZORPAY_CHECKOUT_REQUIRED",
            "CAPTURED": "CAPTURED",
            "FULLY_DISCOUNTED": "FULLY_DISCOUNTED",
        }.get(status, "OUTCOME_UNRESOLVED"),
        checkout_intent_id=UUID(str(row.checkout_intent_id)),
        provider_order_reference=row.razorpay_order_id,
        public_checkout_key=_settings.RAZORPAY_KEY_ID if status == "AWAITING_PROVIDER" else None,
        amount_inr_paise=row.payable_inr_paise,
        merchant_display_name=(
            _settings.RAZORPAY_MERCHANT_DISPLAY_NAME if status == "AWAITING_PROVIDER" else None
        ),
        enabled_method_families=(
            list(_settings.razorpay_enabled_method_families)
            if status == "AWAITING_PROVIDER"
            else None
        ),
        expires_at=(
            datetime.now(timezone.utc) + timedelta(seconds=_settings.RAZORPAY_CHECKOUT_TTL_SECONDS)
            if status == "AWAITING_PROVIDER"
            else None
        ),
        list_price_inr_paise=row.list_price_inr_paise,
        discount_inr_paise=row.discount_inr_paise,
        tax_inr_paise=row.tax_inr_paise,
        payable_inr_paise=row.payable_inr_paise,
        coupon_code=row.coupon_code,
        commercial_outcome_reference=(
            row.razorpay_payment_id
            if status == "CAPTURED"
            else f"zero-price:{row.checkout_intent_id}" if status == "FULLY_DISCOUNTED" else None
        ),
        commercial_evidence_id=(
            UUID(str(row.commercial_evidence_id)) if row.commercial_evidence_id else None
        ),
        customer_safe_next_action=(
            "Wait while the existing checkout is reconciled."
            if status in {"CREATING", "UNRESOLVED"}
            else None
        ),
    )


def _validate_pre_hire_replay(row: object, body: PreHireCheckoutBody) -> None:
    expected = (
        str(body.customer_id), body.professional_type, body.professional_version,
        body.disclosure_revision, body.terms_version, body.cadence,
        body.gross_amount_inr_paise, body.gst_amount_inr_paise,
        body.coupon_code.strip().upper() if body.coupon_code else None,
    )
    actual = (
        str(row.customer_id), row.professional_type, row.professional_version,
        row.disclosure_revision, row.terms_version, row.cadence,
        row.list_price_inr_paise, row.tax_inr_paise, row.coupon_code,
    )
    if actual != expected:
        raise HTTPException(status_code=409, detail={"code": "PRE_HIRE_CHECKOUT_CONFLICT"})


def _uuid_bind(db: AsyncSession, value: UUID) -> UUID | str:
    return value if db.bind is not None and db.bind.dialect.name == "postgresql" else str(value)


@router.post("/hire-checkout", response_model=PreHireCheckoutOutcome)
async def create_pre_hire_checkout(body: PreHireCheckoutBody) -> PreHireCheckoutOutcome:
    """Create one customer-bound Razorpay order before Hire setup begins."""
    session_factory = get_session_factory()
    async with session_factory() as db:
        existing = (await db.execute(text(
            "SELECT * FROM pre_hire_checkout_orders WHERE checkout_intent_id = :checkout_intent_id"
        ).bindparams(checkout_intent_id=_uuid_bind(db, body.checkout_intent_id)))).fetchone()
        if existing is not None:
            _validate_pre_hire_replay(existing, body)
            return _pre_hire_outcome(existing)

    preview = await create_hire_commercial_preview(
        HireCommercialPreviewBody(
            professional_type=body.professional_type,
            gross_amount_inr_paise=body.gross_amount_inr_paise,
            gst_amount_inr_paise=body.gst_amount_inr_paise,
            cadence=body.cadence,
            coupon_code=body.coupon_code,
        )
    )
    if preview.payable_inr_paise > 0 and not preview.payments_enabled:
        return PreHireCheckoutOutcome(
            outcome_kind="PROVIDER_CONFIGURATION_PENDING",
            checkout_intent_id=body.checkout_intent_id,
            amount_inr_paise=preview.payable_inr_paise,
            list_price_inr_paise=preview.list_price_inr_paise,
            discount_inr_paise=preview.discount_inr_paise,
            tax_inr_paise=preview.tax_inr_paise,
            payable_inr_paise=preview.payable_inr_paise,
            coupon_code=preview.coupon_code,
            customer_safe_next_action="Razorpay Checkout is not configured for this environment.",
        )

    async with session_factory() as db:
        existing = (await db.execute(text(
            "SELECT * FROM pre_hire_checkout_orders WHERE checkout_intent_id = :checkout_intent_id"
        ).bindparams(checkout_intent_id=_uuid_bind(db, body.checkout_intent_id)))).fetchone()
        if existing is not None:
            _validate_pre_hire_replay(existing, body)
            return _pre_hire_outcome(existing)

        evidence_id = uuid5(NAMESPACE_URL, f"waooaw:pre-hire:{body.checkout_intent_id}")
        status = "FULLY_DISCOUNTED" if preview.payable_inr_paise == 0 else "CREATING"
        inserted = await db.execute(text(
            "INSERT INTO pre_hire_checkout_orders "
            "(checkout_intent_id, customer_id, professional_type, professional_version, "
            "disclosure_revision, terms_version, cadence, list_price_inr_paise, "
            "discount_inr_paise, tax_inr_paise, payable_inr_paise, coupon_code, "
            "commercial_evidence_id, status) VALUES "
            "(:checkout_intent_id, :customer_id, :professional_type, :professional_version, "
            ":disclosure_revision, :terms_version, :cadence, :list_price, :discount, :tax, "
            ":payable, :coupon_code, :evidence_id, :status) "
            "ON CONFLICT (checkout_intent_id) DO NOTHING"
        ).bindparams(
            checkout_intent_id=_uuid_bind(db, body.checkout_intent_id),
            customer_id=_uuid_bind(db, body.customer_id),
            professional_type=body.professional_type, professional_version=body.professional_version,
            disclosure_revision=body.disclosure_revision, terms_version=body.terms_version,
            cadence=body.cadence, list_price=preview.list_price_inr_paise,
            discount=preview.discount_inr_paise, tax=preview.tax_inr_paise,
            payable=preview.payable_inr_paise, coupon_code=preview.coupon_code,
            evidence_id=_uuid_bind(db, evidence_id), status=status,
        ))
        if inserted.rowcount != 1:
            raced = (await db.execute(text(
                "SELECT * FROM pre_hire_checkout_orders WHERE checkout_intent_id = :checkout_intent_id"
            ).bindparams(checkout_intent_id=_uuid_bind(db, body.checkout_intent_id)))).one()
            _validate_pre_hire_replay(raced, body)
            return _pre_hire_outcome(raced)
        await db.commit()
        if status == "CREATING":
            try:
                order = await RazorpayClient(settings=_settings).create_order(
                    amount_paise=preview.payable_inr_paise,
                    notes={
                        "checkout_kind": "PRE_HIRE",
                        "checkout_intent_id": str(body.checkout_intent_id),
                        "customer_id": str(body.customer_id),
                        "agent_type": body.professional_type,
                        "professional_version": body.professional_version,
                    },
                )
                await db.execute(text(
                    "UPDATE pre_hire_checkout_orders SET razorpay_order_id = :order_id, "
                    "status = 'AWAITING_PROVIDER', updated_at = CURRENT_TIMESTAMP "
                    "WHERE checkout_intent_id = :checkout_intent_id AND status = 'CREATING'"
                ).bindparams(
                    order_id=str(order["id"]),
                    checkout_intent_id=_uuid_bind(db, body.checkout_intent_id),
                ))
                await db.commit()
            except Exception:
                await db.rollback()
                await db.execute(text(
                    "UPDATE pre_hire_checkout_orders SET status = 'UNRESOLVED', "
                    "updated_at = CURRENT_TIMESTAMP WHERE checkout_intent_id = :checkout_intent_id"
                ).bindparams(checkout_intent_id=_uuid_bind(db, body.checkout_intent_id)))
                await db.commit()
                raise HTTPException(status_code=503, detail={"code": "RAZORPAY_ORDER_UNRESOLVED"}) from None
        stored = (await db.execute(text(
            "SELECT * FROM pre_hire_checkout_orders WHERE checkout_intent_id = :checkout_intent_id"
        ).bindparams(checkout_intent_id=_uuid_bind(db, body.checkout_intent_id)))).one()
        return _pre_hire_outcome(stored)


@router.post("/hire-checkout/confirm", response_model=PreHireCheckoutOutcome)
async def confirm_pre_hire_checkout(
    body: PreHireCheckoutConfirmationBody,
) -> PreHireCheckoutOutcome:
    """Verify and retain Razorpay's signed browser result without activating an unconfigured agent."""
    session_factory = get_session_factory()
    async with session_factory() as db:
        row = (await db.execute(text(
            "SELECT * FROM pre_hire_checkout_orders WHERE checkout_intent_id = :checkout_intent_id"
        ).bindparams(checkout_intent_id=_uuid_bind(db, body.checkout_intent_id)))).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail={"code": "PRE_HIRE_CHECKOUT_NOT_FOUND"})
        if str(row.customer_id) != str(body.customer_id) or row.razorpay_order_id != body.razorpay_order_id:
            raise HTTPException(status_code=409, detail={"code": "PRE_HIRE_CHECKOUT_MISMATCH"})
        if row.status == "CAPTURED":
            if row.razorpay_payment_id != body.razorpay_payment_id:
                raise HTTPException(status_code=409, detail={"code": "PRE_HIRE_PAYMENT_CONFLICT"})
            return _pre_hire_outcome(row)
        if row.status != "AWAITING_PROVIDER":
            raise HTTPException(status_code=409, detail={"code": "PRE_HIRE_CHECKOUT_NOT_CONFIRMABLE"})
        razorpay = RazorpayClient(settings=_settings)
        if not razorpay.verify_payment_signature(
            order_id=body.razorpay_order_id,
            payment_id=body.razorpay_payment_id,
            signature=body.razorpay_signature,
        ):
            raise HTTPException(status_code=400, detail={"code": "INVALID_SIGNATURE"})
        try:
            provider_payment = await razorpay.fetch_payment(body.razorpay_payment_id)
        except Exception:
            raise HTTPException(status_code=503, detail={"code": "PAYMENT_STATUS_UNRESOLVED"}) from None
        if (
            provider_payment.get("id") != body.razorpay_payment_id
            or provider_payment.get("order_id") != body.razorpay_order_id
            or provider_payment.get("status") != "captured"
            or provider_payment.get("currency") != "INR"
            or provider_payment.get("amount") != row.payable_inr_paise
        ):
            raise HTTPException(status_code=409, detail={"code": "PAYMENT_NOT_CAPTURED"})
        await db.execute(text(
            "UPDATE pre_hire_checkout_orders SET razorpay_payment_id = :payment_id, "
            "status = 'CAPTURED', updated_at = CURRENT_TIMESTAMP "
            "WHERE checkout_intent_id = :checkout_intent_id AND status = 'AWAITING_PROVIDER'"
        ).bindparams(
            payment_id=body.razorpay_payment_id,
            checkout_intent_id=_uuid_bind(db, body.checkout_intent_id),
        ))
        await db.commit()
        stored = (await db.execute(text(
            "SELECT * FROM pre_hire_checkout_orders WHERE checkout_intent_id = :checkout_intent_id"
        ).bindparams(checkout_intent_id=_uuid_bind(db, body.checkout_intent_id)))).one()
        return _pre_hire_outcome(stored)


@router.post("/hire-checkout/bind", response_model=PreHireCheckoutOutcome)
async def bind_pre_hire_checkout(
    body: PreHireCheckoutBindingBody,
) -> PreHireCheckoutOutcome:
    """Bind one captured or zero-price outcome to the relationship created after payment."""
    session_factory = get_session_factory()
    async with session_factory() as db:
        row = (await db.execute(text(
            "SELECT * FROM pre_hire_checkout_orders WHERE checkout_intent_id = :checkout_intent_id"
        ).bindparams(checkout_intent_id=_uuid_bind(db, body.checkout_intent_id)))).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail={"code": "PRE_HIRE_CHECKOUT_NOT_FOUND"})
        if str(row.customer_id) != str(body.customer_id) or row.status not in {"CAPTURED", "FULLY_DISCOUNTED"}:
            raise HTTPException(status_code=409, detail={"code": "PRE_HIRE_CHECKOUT_NOT_BINDABLE"})
        if row.relationship_id is not None and str(row.relationship_id) != str(body.relationship_id):
            raise HTTPException(status_code=409, detail={"code": "PRE_HIRE_RELATIONSHIP_CONFLICT"})
        await db.execute(text(
            "UPDATE pre_hire_checkout_orders SET relationship_id = :relationship_id, "
            "updated_at = CURRENT_TIMESTAMP WHERE checkout_intent_id = :checkout_intent_id"
        ).bindparams(
            relationship_id=_uuid_bind(db, body.relationship_id),
            checkout_intent_id=_uuid_bind(db, body.checkout_intent_id),
        ))
        await db.commit()
        stored = (await db.execute(text(
            "SELECT * FROM pre_hire_checkout_orders WHERE checkout_intent_id = :checkout_intent_id"
        ).bindparams(checkout_intent_id=_uuid_bind(db, body.checkout_intent_id)))).one()
        return _pre_hire_outcome(stored)


@router.post("/relationship-checkout", response_model=RelationshipCheckoutResult)
async def create_relationship_checkout(body: RelationshipCheckoutBody) -> RelationshipCheckoutResult:
    """Return WBE-owned commercial truth for one accepted relationship contract."""
    session_factory = get_session_factory()
    async with session_factory() as db:
        pre_hire = (await db.execute(text(
            "SELECT * FROM pre_hire_checkout_orders WHERE relationship_id = :relationship_id "
            "AND customer_id = :customer_id AND professional_type = :agent_type "
            "ORDER BY created_at DESC LIMIT 1"
        ).bindparams(
            relationship_id=_uuid_bind(db, body.relationship_id),
            customer_id=_uuid_bind(db, body.customer_id),
            agent_type=body.agent_type,
        ))).fetchone()
        if pre_hire is not None:
            if (
                pre_hire.contract_checkout_intent_id is not None
                and str(pre_hire.contract_checkout_intent_id) != str(body.checkout_intent_id)
            ):
                raise HTTPException(status_code=409, detail={"code": "PRE_HIRE_CONTRACT_CONFLICT"})
            if (
                pre_hire.list_price_inr_paise != body.gross_amount_inr_paise
                or pre_hire.tax_inr_paise != body.gst_amount_inr_paise
            ):
                raise HTTPException(status_code=409, detail={"code": "PRE_HIRE_CONTRACT_PRICE_MISMATCH"})
            claim = await db.execute(text(
                "UPDATE pre_hire_checkout_orders SET contract_checkout_intent_id = :contract_checkout_intent_id, "
                "updated_at = CURRENT_TIMESTAMP WHERE checkout_intent_id = :pre_hire_checkout_intent_id "
                "AND (contract_checkout_intent_id IS NULL OR contract_checkout_intent_id = :contract_checkout_intent_id)"
            ).bindparams(
                contract_checkout_intent_id=_uuid_bind(db, body.checkout_intent_id),
                pre_hire_checkout_intent_id=_uuid_bind(db, UUID(str(pre_hire.checkout_intent_id))),
            ))
            if claim.rowcount != 1:
                await db.rollback()
                raise HTTPException(status_code=409, detail={"code": "PRE_HIRE_CONTRACT_CONFLICT"})
            if pre_hire.status == "CAPTURED":
                await db.execute(text(
                    "INSERT INTO payment_intents "
                    "(razorpay_order_id, razorpay_payment_id, customer_id, status, relationship_id, "
                    "tenant_id, accepted_contract_id, contract_version, contract_hash, "
                    "contract_acceptance_id, payment_consent_evidence_id, payment_evidence_id, "
                    "checkout_intent_id, agent_type, bundle_tier) VALUES "
                    "(:order_id, :payment_id, :customer_id, 'CAPTURED', :relationship_id, :tenant_id, "
                    ":contract_id, :contract_version, :contract_hash, :acceptance_id, :consent_id, "
                    ":evidence_id, :checkout_intent_id, :agent_type, :bundle_tier) "
                    "ON CONFLICT (razorpay_payment_id) DO NOTHING"
                ).bindparams(
                    order_id=pre_hire.razorpay_order_id, payment_id=pre_hire.razorpay_payment_id,
                    customer_id=_uuid_bind(db, body.customer_id),
                    relationship_id=_uuid_bind(db, body.relationship_id),
                    tenant_id=_uuid_bind(db, body.tenant_id),
                    contract_id=_uuid_bind(db, body.contract_id),
                    contract_version=body.contract_version, contract_hash=body.contract_hash,
                    acceptance_id=_uuid_bind(db, body.contract_acceptance_id),
                    consent_id=_uuid_bind(db, body.payment_consent_evidence_id),
                    evidence_id=_uuid_bind(db, UUID(str(pre_hire.commercial_evidence_id))),
                    checkout_intent_id=_uuid_bind(db, body.checkout_intent_id), agent_type=body.agent_type,
                    bundle_tier=body.bundle_tier,
                ))
                await db.commit()
                return RelationshipCheckoutResult(
                    outcome_kind=CheckoutOutcomeKind.CAPTURED,
                    checkout_intent_id=body.checkout_intent_id,
                    relationship_id=body.relationship_id,
                    contract_version=body.contract_version,
                    produced_at=datetime.now(timezone.utc),
                    commercial_outcome_reference=pre_hire.razorpay_payment_id,
                    commercial_evidence_id=UUID(str(pre_hire.commercial_evidence_id)),
                    evidence_state="COMMITTED",
                )
            if pre_hire.status == "FULLY_DISCOUNTED":
                outcome = RelationshipCheckoutResult(
                    outcome_kind=CheckoutOutcomeKind.FULLY_DISCOUNTED,
                    checkout_intent_id=body.checkout_intent_id,
                    relationship_id=body.relationship_id,
                    contract_version=body.contract_version,
                    produced_at=datetime.now(timezone.utc),
                    quote_version=body.quote_version,
                    promotion_version="pre-hire-coupon-v1",
                    coupon_code=pre_hire.coupon_code,
                    list_price_inr_paise=pre_hire.list_price_inr_paise,
                    discount_inr_paise=pre_hire.discount_inr_paise,
                    tax_inr_paise=pre_hire.tax_inr_paise,
                    payable_inr_paise=0,
                    commercial_outcome_reference=f"zero-price:{body.checkout_intent_id}",
                    commercial_evidence_id=UUID(str(pre_hire.commercial_evidence_id)),
                    evidence_state="COMMITTED",
                )
                await ZeroPriceCommercialOutcomeStore(db).record(
                    RelationshipCheckoutRequest(**body.model_dump()), outcome
                )
                await db.commit()
                return outcome
            await db.rollback()
            raise HTTPException(status_code=409, detail={"code": "PRE_HIRE_PAYMENT_NOT_FINAL"})
        result = await OnboardingService(
            settings=_settings,
            zero_price_outcomes=ZeroPriceCommercialOutcomeStore(db),
        ).create_relationship_checkout(RelationshipCheckoutRequest(**body.model_dump()))
        if result.outcome_kind == CheckoutOutcomeKind.RAZORPAY_CHECKOUT_REQUIRED:
            await db.execute(text(
                "INSERT INTO razorpay_checkout_orders "
                "(checkout_intent_id, razorpay_order_id, tenant_id, customer_id, relationship_id, "
                "accepted_contract_id, contract_version, contract_hash, contract_acceptance_id, "
                "payment_consent_evidence_id, agent_type, bundle_tier) "
                "VALUES (:checkout_intent_id, :order_id, :tenant_id, :customer_id, :relationship_id, "
                ":contract_id, :contract_version, :contract_hash, :acceptance_id, :consent_id, "
                ":agent_type, :bundle_tier) ON CONFLICT (checkout_intent_id) DO NOTHING"
            ).bindparams(
                checkout_intent_id=_uuid_bind(db, body.checkout_intent_id),
                order_id=result.provider_order_reference,
                tenant_id=_uuid_bind(db, body.tenant_id),
                customer_id=_uuid_bind(db, body.customer_id),
                relationship_id=_uuid_bind(db, body.relationship_id),
                contract_id=_uuid_bind(db, body.contract_id),
                contract_version=body.contract_version,
                contract_hash=body.contract_hash,
                acceptance_id=_uuid_bind(db, body.contract_acceptance_id),
                consent_id=_uuid_bind(db, body.payment_consent_evidence_id),
                agent_type=body.agent_type,
                bundle_tier=body.bundle_tier,
            ))
            await db.commit()
        return result


@router.post("/relationship-checkout/{checkout_intent_id}/confirm")
async def confirm_razorpay_checkout(
    checkout_intent_id: UUID,
    body: RazorpayCheckoutConfirmationBody,
) -> RelationshipCheckoutResult:
    """Verify Razorpay Standard Checkout's signed browser response."""
    session_factory = get_session_factory()
    async with session_factory() as db:
        row = (await db.execute(text(
            "SELECT razorpay_order_id, tenant_id, customer_id, relationship_id, accepted_contract_id, "
            "contract_version, contract_hash, contract_acceptance_id, payment_consent_evidence_id, "
            "agent_type, bundle_tier FROM razorpay_checkout_orders "
            "WHERE checkout_intent_id = :checkout_intent_id"
        ).bindparams(checkout_intent_id=_uuid_bind(db, checkout_intent_id)))).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail={"code": "CHECKOUT_ORDER_NOT_FOUND"})
        if row.razorpay_order_id != body.razorpay_order_id:
            raise HTTPException(status_code=409, detail={"code": "CHECKOUT_ORDER_MISMATCH"})

        razorpay = RazorpayClient(settings=_settings)
        if not razorpay.verify_payment_signature(
            order_id=body.razorpay_order_id,
            payment_id=body.razorpay_payment_id,
            signature=body.razorpay_signature,
        ):
            raise HTTPException(status_code=400, detail={"code": "INVALID_SIGNATURE"})
        try:
            provider_payment = await razorpay.fetch_payment(body.razorpay_payment_id)
        except Exception:
            raise HTTPException(status_code=503, detail={"code": "PAYMENT_STATUS_UNRESOLVED"}) from None
        if (
            provider_payment.get("id") != body.razorpay_payment_id
            or provider_payment.get("order_id") != body.razorpay_order_id
            or provider_payment.get("status") != "captured"
            or provider_payment.get("currency") != "INR"
        ):
            raise HTTPException(status_code=409, detail={"code": "PAYMENT_NOT_CAPTURED"})

        event = PaymentCapturedEvent(
            razorpay_order_id=body.razorpay_order_id,
            razorpay_payment_id=body.razorpay_payment_id,
            razorpay_signature=body.razorpay_signature,
            customer_id=UUID(str(row.customer_id)),
            agent_type=row.agent_type,
            bundle_tier=row.bundle_tier,
            tenant_id=UUID(str(row.tenant_id)),
            relationship_id=UUID(str(row.relationship_id)),
            accepted_contract_id=UUID(str(row.accepted_contract_id)),
            contract_version=row.contract_version,
            contract_hash=row.contract_hash,
            contract_acceptance_id=UUID(str(row.contract_acceptance_id)),
            payment_consent_evidence_id=UUID(str(row.payment_consent_evidence_id)),
            payment_evidence_id=uuid5(NAMESPACE_URL, f"waooaw:payment:{body.razorpay_payment_id}"),
            checkout_intent_id=checkout_intent_id,
        )
        redis_client = aioredis.from_url(_settings.REDIS_URL, decode_responses=True)
        try:
            result = await WebhookHandler(
                db=db,
                wallet_service=WalletService(db=db, redis_client=redis_client),
                razorpay_client=razorpay,
                settings=_settings,
            ).handle_payment_captured(event)
        finally:
            await redis_client.aclose()
        return RelationshipCheckoutResult(
            outcome_kind=CheckoutOutcomeKind.CAPTURED,
            checkout_intent_id=checkout_intent_id,
            relationship_id=UUID(str(row.relationship_id)),
            contract_version=row.contract_version,
            produced_at=datetime.now(timezone.utc),
            commercial_outcome_reference=result.payment_reference,
            commercial_evidence_id=result.payment_evidence_id,
            evidence_state="COMMITTED",
        )


@router.post("/relationship-checkout/{checkout_intent_id}/reconcile", response_model=RelationshipCheckoutResult)
async def reconcile_relationship_checkout(
    checkout_intent_id: UUID,
    body: RelationshipCheckoutReconcileBody,
) -> RelationshipCheckoutResult:
    session_factory = get_session_factory()
    async with session_factory() as db:
        row = (await db.execute(text(
            "SELECT tenant_id, relationship_id, accepted_contract_id, contract_version, contract_hash, "
            "contract_acceptance_id, payment_consent_evidence_id, payment_evidence_id, "
            "razorpay_payment_id, status FROM payment_intents WHERE checkout_intent_id = :checkout_intent_id"
        ).bindparams(checkout_intent_id=_uuid_bind(db, checkout_intent_id)))).fetchone()
        if row is None:
            return RelationshipCheckoutResult(
                outcome_kind=CheckoutOutcomeKind.OUTCOME_UNRESOLVED,
                checkout_intent_id=checkout_intent_id,
                relationship_id=body.relationship_id,
                contract_version=body.contract_version,
                produced_at=datetime.now(timezone.utc),
                reason_code="RECONCILIATION_PENDING",
                retryable=True,
                customer_safe_next_action="Wait while the existing checkout is reconciled.",
            )
        expected = tuple(str(value) for value in (
            body.tenant_id, body.relationship_id, body.contract_id, body.contract_version,
            body.contract_hash, body.contract_acceptance_id, body.payment_consent_evidence_id,
        ))
        if tuple(str(row[index]) for index in range(7)) != expected:
            raise HTTPException(status_code=409, detail={"code": "CHECKOUT_RECONCILIATION_CONFLICT"})
        if row.status != "CAPTURED":
            return RelationshipCheckoutResult(
                outcome_kind=CheckoutOutcomeKind.OUTCOME_UNRESOLVED,
                checkout_intent_id=checkout_intent_id,
                relationship_id=body.relationship_id,
                contract_version=body.contract_version,
                produced_at=datetime.now(timezone.utc),
                reason_code="RECONCILIATION_PENDING",
                retryable=True,
                customer_safe_next_action="Wait while the existing checkout is reconciled.",
            )
        return RelationshipCheckoutResult(
            outcome_kind=CheckoutOutcomeKind.CAPTURED,
            checkout_intent_id=checkout_intent_id,
            relationship_id=body.relationship_id,
            contract_version=body.contract_version,
            produced_at=datetime.now(timezone.utc),
            commercial_outcome_reference=str(row.razorpay_payment_id),
            commercial_evidence_id=UUID(str(row.payment_evidence_id)),
            evidence_state="COMMITTED",
        )


@router.post("/onboarding-order")
async def create_onboarding_order(body: OnboardingOrderBody) -> dict:
    """Create a Razorpay order combining first-month subscription + wallet seed (ADR-022 §1.2)."""
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
    raw_body = await request.body()
    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail={"code": "INVALID_WEBHOOK_BODY"}) from None

    event_type = payload.get("event", "")
    if event_type != "payment.captured":
        # Acknowledge unhandled events gracefully
        return {"status": "ignored", "event": event_type}
    razorpay_client = RazorpayClient(settings=_settings)
    if not razorpay_client.verify_webhook_signature(raw_body, signature):
        raise HTTPException(status_code=400, detail={"code": "INVALID_SIGNATURE"})

    payment = payload.get("payload", {}).get("payment", {}).get("entity", {})
    notes = payment.get("notes", {})

    try:
        customer_id = UUID(notes.get("customer_id", ""))
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail={"code": "MISSING_CUSTOMER_ID"}) from None

    if notes.get("checkout_kind") == "PRE_HIRE":
        try:
            checkout_intent_id = UUID(notes.get("checkout_intent_id", ""))
        except (ValueError, AttributeError):
            raise HTTPException(status_code=400, detail={"code": "MISSING_CHECKOUT_INTENT_ID"}) from None
        order_id = payment.get("order_id", "")
        payment_id = payment.get("id", "")
        if not order_id or not payment_id:
            raise HTTPException(status_code=400, detail={"code": "INVALID_PAYMENT_REFERENCE"})
        session_factory = get_session_factory()
        async with session_factory() as db:
            stored = (await db.execute(text(
                "SELECT * FROM pre_hire_checkout_orders WHERE checkout_intent_id = :checkout_intent_id"
            ).bindparams(checkout_intent_id=_uuid_bind(db, checkout_intent_id)))).fetchone()
            if (
                stored is None
                or str(stored.customer_id) != str(customer_id)
                or stored.razorpay_order_id != order_id
                or stored.professional_type != notes.get("agent_type")
                or stored.professional_version != notes.get("professional_version")
            ):
                raise HTTPException(status_code=409, detail={"code": "PRE_HIRE_CAPTURE_CONFLICT"})
            if stored.status not in {"AWAITING_PROVIDER", "CAPTURED"} or (
                stored.razorpay_payment_id is not None and stored.razorpay_payment_id != payment_id
            ):
                raise HTTPException(status_code=409, detail={"code": "PRE_HIRE_CAPTURE_CONFLICT"})
            evidence_id = UUID(str(stored.commercial_evidence_id))
            await db.execute(text(
                "UPDATE pre_hire_checkout_orders SET razorpay_payment_id = :payment_id, "
                "status = 'CAPTURED', updated_at = CURRENT_TIMESTAMP "
                "WHERE checkout_intent_id = :checkout_intent_id"
            ).bindparams(
                payment_id=payment_id,
                checkout_intent_id=_uuid_bind(db, checkout_intent_id),
            ))
            await db.commit()
        return {
            "status": "CAPTURED",
            "payment_reference": payment_id,
            "payment_evidence_id": str(evidence_id),
        }

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
        checkout_intent_id=_optional_uuid(notes.get("checkout_intent_id")),
    )

    session_factory = get_session_factory()
    async with session_factory() as db:
        redis_client = aioredis.from_url(_settings.REDIS_URL, decode_responses=True)
        wallet_svc = WalletService(db=db, redis_client=redis_client)
        handler = WebhookHandler(
            db=db,
            wallet_service=wallet_svc,
            razorpay_client=razorpay_client,
            settings=_settings,
        )
        result = await handler.handle_payment_captured(event, is_bypass=False, webhook_signature_verified=True)

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
