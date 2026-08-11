# Implements: adr/ADR-022-payment-processing-razorpay-india.md §Amendment 1.2
# constitutional_basis: C-059 (Implementation Traceability)
"""Payment domain models for onboarding order and webhook handling."""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID


class PaymentEnvironment(StrEnum):
    DEMO = "demo"
    UAT = "uat"
    PRODUCTION = "production"


class WebhookEvent(StrEnum):
    PAYMENT_CAPTURED = "payment.captured"
    PAYMENT_FAILED = "payment.failed"
    SUBSCRIPTION_CHARGED = "subscription.charged"
    SUBSCRIPTION_HALTED = "subscription.halted"


@dataclass(frozen=True)
class OnboardingOrderRequest:
    customer_id: UUID
    agent_type: str
    bundle_tier: str
    subscription_amount_paise: int   # first month subscription price
    wallet_seed_paise: int           # initial ad wallet seed amount
    coupon_code: str = ""            # optional — DEMOWAOOAW/UATWAOOAW bypasses Razorpay
    relationship_id: UUID | None = None
    contract_id: UUID | None = None
    contract_version: int | None = None
    contract_hash: str = ""
    contract_acceptance_id: UUID | None = None
    payment_consent_evidence_id: UUID | None = None


@dataclass(frozen=True)
class OnboardingOrderResult:
    order_id: str            # Razorpay order ID (or stub-{customer_id} for demo/UAT)
    amount_paise: int        # total amount charged (0 for 100% coupon environments)
    currency: str            # "INR"
    is_bypass: bool          # True when coupon bypasses live Razorpay call
    coupon_applied: str = ""


@dataclass(frozen=True)
class PaymentCapturedEvent:
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str    # HMAC-SHA256 for verification
    customer_id: UUID
    agent_type: str
    bundle_tier: str
