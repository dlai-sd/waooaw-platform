# Implements: adr/ADR-022-payment-processing-razorpay-india.md §Amendment 1.2
# constitutional_basis: C-059, C-088 (billing profile gate), ADR-022 §1.2
"""OnboardingService — creates combined Razorpay order for subscription + wallet seed.

Lower environments (WAOOAW_ENVIRONMENT=demo|uat) skip the live Razorpay API when a
100% discount coupon (DEMOWAOOAW / UATWAOOAW) is presented. FA-029.
"""
from __future__ import annotations

import logging

from config import Settings
from payment.models import (
    OnboardingOrderRequest,
    OnboardingOrderResult,
    PaymentEnvironment,
)
from payment.razorpay_client import RazorpayClient

logger = logging.getLogger(__name__)

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
    ) -> None:
        self._settings: Settings = settings or Settings()
        self._razorpay: RazorpayClient = razorpay_client or RazorpayClient(self._settings)

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
