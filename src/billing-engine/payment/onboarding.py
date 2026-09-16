# Implements: architecture/reference/api-specs/business-platform.openapi.yaml §RelationshipCheckoutOutcome
# Constitutional basis: C-059, C-088 (billing profile gate and truthful commercial outcomes)
"""OnboardingService — creates combined Razorpay order for subscription + wallet seed.

Lower environments (WAOOAW_ENVIRONMENT=demo|uat) skip the live Razorpay API when a
100% discount coupon (DEMOWAOOAW / UATWAOOAW) is presented. FA-029.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Protocol
from uuid import NAMESPACE_URL, uuid5

from config import Settings
from payment.models import (
    CheckoutOutcomeKind,
    OnboardingOrderRequest,
    OnboardingOrderResult,
    PaymentEnvironment,
    RelationshipCheckoutRequest,
    RelationshipCheckoutResult,
)
from payment.razorpay_client import RazorpayClient

logger = logging.getLogger(__name__)


class ZeroPriceOutcomeWriter(Protocol):
    async def record(
        self,
        request: RelationshipCheckoutRequest,
        outcome: RelationshipCheckoutResult,
    ) -> None: ...

_BYPASS_COUPONS: dict[str, PaymentEnvironment] = {
    "DEMOWAOOAW": PaymentEnvironment.DEMO,
    "UATWAOOAW":  PaymentEnvironment.UAT,
}


class OnboardingService:
    """Creates a single Razorpay order covering first-month subscription + wallet seed (ADR-022 §1.2)."""

    def __init__(
        self,
        razorpay_client: RazorpayClient | None = None,
        settings: Settings | None = None,
        zero_price_outcomes: ZeroPriceOutcomeWriter | None = None,
    ) -> None:
        self._settings: Settings = settings or Settings()
        self._razorpay: RazorpayClient = razorpay_client or RazorpayClient(self._settings)
        self._zero_price_outcomes = zero_price_outcomes

    async def create_onboarding_order(
        self,
        req: OnboardingOrderRequest,
    ) -> OnboardingOrderResult:
        """Return a Razorpay order ID (or stub) for the frontend to complete payment.

        For DEMOWAOOAW / UATWAOOAW coupons: returns a ₹0 bypass order without calling
        Razorpay. The webhook handler treats bypass orders as pre-confirmed. FA-029.
        """
        coupon = req.coupon_code.upper().strip()

        if coupon in _BYPASS_COUPONS:
            env = _BYPASS_COUPONS[coupon]
            logger.info(
                "Payment bypass: coupon=%s env=%s customer_id=%s",
                coupon, env, req.customer_id,
            )
            return OnboardingOrderResult(
                order_id=f"bypass-{req.customer_id}",
                amount_paise=0,
                currency="INR",
                is_bypass=True,
                coupon_applied=coupon,
            )

        total_paise = req.subscription_amount_paise + req.wallet_seed_paise
        notes = {
            "customer_id": str(req.customer_id),
            "agent_type": req.agent_type,
            "bundle_tier": req.bundle_tier,
            "wallet_seed_paise": str(req.wallet_seed_paise),
        }
        if req.relationship_id is not None:
            notes.update({
                "tenant_id": str(req.tenant_id),
                "relationship_id": str(req.relationship_id),
                "contract_id": str(req.contract_id),
                "contract_version": str(req.contract_version),
                "contract_hash": req.contract_hash,
                "contract_acceptance_id": str(req.contract_acceptance_id),
                "payment_consent_evidence_id": str(req.payment_consent_evidence_id),
            })
        order = await self._razorpay.create_order(amount_paise=total_paise, notes=notes)

        return OnboardingOrderResult(
            order_id=order["id"],
            amount_paise=total_paise,
            currency="INR",
            is_bypass=False,
        )

    async def create_relationship_checkout(
        self,
        request: RelationshipCheckoutRequest,
    ) -> RelationshipCheckoutResult:
        """Create a typed relationship checkout outcome from trusted platform context."""
        if request.gross_amount_inr_paise <= 0 or request.gst_amount_inr_paise < 0:
            raise ValueError("accepted contract amounts are invalid")
        if request.gst_amount_inr_paise > request.gross_amount_inr_paise:
            raise ValueError("GST cannot exceed the accepted contract gross amount")
        if not request.idempotency_key.strip():
            raise ValueError("idempotency key is required")

        intent_id = request.checkout_intent_id
        common = {
            "checkout_intent_id": intent_id,
            "relationship_id": request.relationship_id,
            "contract_version": request.contract_version,
            "produced_at": datetime.now(timezone.utc),
        }

        if (
            self._settings.WAOOAW_ENVIRONMENT == PaymentEnvironment.DEMO.value
            and self._settings.DEMO_PROMOTION_ENABLED
        ):
            if self._settings.MAX_DISCOUNT_PCT < 100 or not self._settings.DEMO_PROMOTION_VERSION:
                return RelationshipCheckoutResult(
                    outcome_kind=CheckoutOutcomeKind.COMMERCIAL_CONFLICT,
                    reason_code="PROMOTION_CHANGED",
                    customer_safe_next_action="Refresh the commercial offer before continuing.",
                    **common,
                )
            outcome = RelationshipCheckoutResult(
                outcome_kind=CheckoutOutcomeKind.FULLY_DISCOUNTED,
                quote_version=request.quote_version,
                promotion_version=self._settings.DEMO_PROMOTION_VERSION,
                list_price_inr_paise=request.gross_amount_inr_paise,
                discount_inr_paise=request.gross_amount_inr_paise,
                tax_inr_paise=request.gst_amount_inr_paise,
                payable_inr_paise=0,
                renewal_consequence=self._settings.DEMO_RENEWAL_CONSEQUENCE,
                commercial_outcome_reference=f"zero-price:{intent_id}",
                commercial_evidence_id=uuid5(NAMESPACE_URL, f"waooaw:zero-price:{intent_id}"),
                evidence_state="COMMITTED",
                **common,
            )
            if self._zero_price_outcomes is None:
                raise RuntimeError("zero-price commercial outcome persistence is unavailable")
            await self._zero_price_outcomes.record(request, outcome)
            return outcome

        configured = bool(
            self._settings.RAZORPAY_KEY_ID
            and self._settings.RAZORPAY_KEY_SECRET
            and self._settings.RAZORPAY_MERCHANT_DISPLAY_NAME
            and self._settings.razorpay_enabled_method_families
        )
        readiness = self._settings.RAZORPAY_READINESS_STATE
        expected_readiness = "READY_LIVE" if self._settings.WAOOAW_ENVIRONMENT == "production" else "READY_TEST"
        if not configured or readiness != expected_readiness:
            reason = "RAZORPAY_ACCOUNT_NOT_CONFIGURED" if not configured or readiness == "NOT_CONFIGURED" else (
                "RAZORPAY_CONFIGURATION_UNVERIFIED"
            )
            return RelationshipCheckoutResult(
                outcome_kind=CheckoutOutcomeKind.PROVIDER_CONFIGURATION_PENDING,
                reason_code=reason,
                accountable_owner="PLATFORM_OWNER",
                retryable=False,
                customer_safe_next_action=(
                    "Payment setup is not available yet. Try again after the platform owner "
                    "completes configuration."
                ),
                **common,
            )

        notes = {
            "tenant_id": str(request.tenant_id),
            "customer_id": str(request.customer_id),
            "relationship_id": str(request.relationship_id),
            "contract_id": str(request.contract_id),
            "contract_version": str(request.contract_version),
            "contract_hash": request.contract_hash,
            "contract_acceptance_id": str(request.contract_acceptance_id),
            "payment_consent_evidence_id": str(request.payment_consent_evidence_id),
            "agent_type": request.agent_type,
            "bundle_tier": request.bundle_tier,
            "checkout_intent_id": str(intent_id),
        }
        order = await self._razorpay.create_order(
            amount_paise=request.gross_amount_inr_paise,
            notes=notes,
        )
        return RelationshipCheckoutResult(
            outcome_kind=CheckoutOutcomeKind.RAZORPAY_CHECKOUT_REQUIRED,
            order_id=str(order["id"]),
            checkout_session_id=str(order["id"]),
            provider_order_reference=str(order["id"]),
            public_checkout_key=self._settings.RAZORPAY_KEY_ID,
            amount_inr_paise=request.gross_amount_inr_paise,
            merchant_display_name=self._settings.RAZORPAY_MERCHANT_DISPLAY_NAME,
            enabled_method_families=self._settings.razorpay_enabled_method_families,
            expires_at=common["produced_at"] + timedelta(
                seconds=self._settings.RAZORPAY_CHECKOUT_TTL_SECONDS
            ),
            reconciliation_target=(
                f"/api/v1/employment/relationships/{request.relationship_id}"
                f"/checkout-intents/{intent_id}"
            ),
            **common,
        )
