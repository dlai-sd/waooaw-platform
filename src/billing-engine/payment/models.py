# Implements: architecture/reference/api-specs/business-platform.openapi.yaml §RelationshipCheckoutOutcome
# Constitutional basis: C-059, C-088 (Implementation Traceability and truthful commercial outcomes)
"""Payment domain models for onboarding order and webhook handling."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class PaymentEnvironment(StrEnum):
    DEMO = "demo"
    UAT = "uat"
    PRODUCTION = "production"


class CheckoutOutcomeKind(StrEnum):
    RAZORPAY_CHECKOUT_REQUIRED = "RAZORPAY_CHECKOUT_REQUIRED"
    CAPTURED = "CAPTURED"
    FULLY_DISCOUNTED = "FULLY_DISCOUNTED"
    PROVIDER_CONFIGURATION_PENDING = "PROVIDER_CONFIGURATION_PENDING"
    COMMERCIAL_CONFLICT = "COMMERCIAL_CONFLICT"
    OUTCOME_UNRESOLVED = "OUTCOME_UNRESOLVED"


@dataclass(frozen=True)
class RelationshipCheckoutRequest:
    checkout_intent_id: UUID
    tenant_id: UUID
    customer_id: UUID
    relationship_id: UUID
    contract_id: UUID
    contract_version: int
    contract_hash: str
    contract_acceptance_id: UUID
    payment_consent_evidence_id: UUID
    agent_type: str
    bundle_tier: str
    gross_amount_inr_paise: int
    gst_amount_inr_paise: int
    quote_version: str
    idempotency_key: str


@dataclass(frozen=True)
class RelationshipCheckoutResult:
    outcome_kind: CheckoutOutcomeKind
    checkout_intent_id: UUID
    relationship_id: UUID
    contract_version: int
    produced_at: datetime
    order_id: str | None = None
    checkout_session_id: str | None = None
    provider_order_reference: str | None = None
    public_checkout_key: str | None = None
    amount_inr_paise: int | None = None
    currency: str = "INR"
    merchant_display_name: str | None = None
    enabled_method_families: tuple[str, ...] | None = None
    expires_at: datetime | None = None
    reconciliation_target: str | None = None
    quote_version: str | None = None
    promotion_version: str | None = None
    list_price_inr_paise: int | None = None
    discount_inr_paise: int | None = None
    tax_inr_paise: int | None = None
    payable_inr_paise: int | None = None
    renewal_consequence: str | None = None
    commercial_outcome_reference: str | None = None
    commercial_evidence_id: UUID | None = None
    evidence_state: str | None = None
    reason_code: str | None = None
    accountable_owner: str | None = None
    retryable: bool | None = None
    customer_safe_next_action: str | None = None


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
    tenant_id: UUID | None = None
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
    tenant_id: UUID | None = None
    relationship_id: UUID | None = None
    accepted_contract_id: UUID | None = None
    contract_version: int | None = None
    contract_hash: str = ""
    contract_acceptance_id: UUID | None = None
    payment_consent_evidence_id: UUID | None = None
    payment_evidence_id: UUID | None = None
    checkout_intent_id: UUID | None = None


@dataclass(frozen=True)
class PaymentCaptureResult:
    payment_reference: str
    payment_evidence_id: UUID
    status: str


@dataclass(frozen=True)
class PaidActivationRequest:
    tenant_id: UUID
    relationship_id: UUID
    activation_intent_id: UUID
    accepted_contract_id: UUID
    contract_version: int
    contract_acceptance_id: UUID
    payment_reference: str
    payment_evidence_id: UUID
    correlation_id: UUID


@dataclass(frozen=True)
class PaidActivationResult:
    subscription_id: UUID
    status: str = "ACTIVE"


@dataclass(frozen=True)
class ZeroPriceActivationRequest:
    tenant_id: UUID
    relationship_id: UUID
    activation_intent_id: UUID
    accepted_contract_id: UUID
    contract_version: int
    contract_acceptance_id: UUID
    commercial_outcome_reference: str
    commercial_evidence_id: UUID
    correlation_id: UUID
