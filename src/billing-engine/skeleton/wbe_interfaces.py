# Implements: architecture/reference/components/manifest/wbe.yaml §surface.endpoints
# Constitutional basis: C-088, C-089, C-090, C-091, C-038, C-048, C-051
# EA-PRODUCED SKELETON — DO NOT change signatures. Raise SPEC_GAP if change needed.

from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID
from datetime import date, datetime


class PacingMode(StrEnum):
    SPREAD = "SPREAD"
    BURST  = "BURST"


class IWalletService(ABC):
    """
    One wallet, multiple bucket architecture per customer.
    Constitutional: C-091 (Thread Catalog), C-088 (Billing Profile gate).
    SLA: get_bucket_balance ≤50ms p99 (Redis cache — ADR-034).
    """

    @abstractmethod
    async def get_bucket_balance(self, customer_id: UUID, thread_type: str) -> BucketBalance:
        # SLA: ≤50ms p99
        # Raises: BucketNotFoundError
        ...

    @abstractmethod
    async def reserve(self, customer_id: UUID, thread_type: str,
                      amount_paise: int, idempotency_key: UUID) -> BucketReservation:
        # Raises: InsufficientBalanceError → HTTP 402
        # Raises: DuplicateReservationError → HTTP 409
        ...

    @abstractmethod
    async def release(self, reservation_id: UUID, consumed: bool) -> None: ...

    @abstractmethod
    async def activate_subscription(self, customer_id: UUID, agent_type: str,
                                    bundle_tier: str, razorpay_order_id: str,
                                    razorpay_payment_id: str) -> SubscriptionActivationResult:
        # MUST check billing_profiles.status == FOUNDER_AUTHORIZED (C-088)
        # MUST flip customer mode before subscription object creation (race condition fix)
        ...

    @abstractmethod
    async def renew(self, customer_id: UUID, contract_id: UUID,
                    new_period_start: date) -> RenewalResult:
        # MUST reject if plan price > agreed price without C-090 notice
        ...


class IMarkupEngine(ABC):
    """
    Three-layer price derivation + C-089 constitutional margin floor enforcement.
    """

    @abstractmethod
    def cost_floor(self, agent_type: str, bundle_tier: str) -> int:
        # Returns: cost_floor_paise from bundle_profiles (DB read, not recomputed)
        ...

    @abstractmethod
    def derive_price(self, agent_type: str, bundle_tier: str,
                     target_margin_pct: float | None = None) -> int:
        # Formula: int(cost_floor / (1 - target_margin_pct / 100))
        # Uses bundle_profiles.minimum_margin_pct when target_margin_pct is None
        ...

    @abstractmethod
    def validate_price(self, agent_type: str, bundle_tier: str,
                       proposed_price_paise: int) -> "PriceValidation":
        # C-089: logs to pricing_floor_log on BOTH APPROVED and REJECTED outcomes
        ...


class IMeterService(ABC):
    """Usage meter + threshold alert engine."""

    @abstractmethod
    async def record_usage(self, customer_id: UUID, thread_type: str, amount_paise: int) -> None: ...

    @abstractmethod
    async def project_depletion(self, customer_id: UUID, thread_type: str) -> DepletionProjection: ...

    @abstractmethod
    async def run_daily_scan(self) -> DailyScanResult:
        # Runs at 06:00 IST: projection + threshold checks + proactive offers
        ...


@dataclass(frozen=True)
class BucketBalance:
    wallet_id: UUID; thread_type: str; balance_paise: int
    reserved_paise: int; available_paise: int
    period_end: date; pacing_mode: PacingMode
    weekly_sub_limit_paise: int | None

@dataclass(frozen=True)
class BucketReservation:
    reservation_id: UUID; bucket_id: UUID
    reserved_paise: int; reserved_at: datetime; expires_at: datetime

@dataclass(frozen=True)
class SubscriptionActivationResult:
    wallet_id: UUID; buckets_seeded: list[str]; mode_flipped_to: str

@dataclass(frozen=True)
class RenewalResult:
    buckets_refilled: list[str]; c090_check_passed: bool; renewed_at: datetime

@dataclass(frozen=True)
class PriceValidation:
    outcome: str                         # "APPROVED" | "REJECTED"
    cost_floor_paise: int
    minimum_compliant_price_paise: int   # int(floor / (1 - min_margin/100))
    proposed_price_paise: int

@dataclass(frozen=True)
class DepletionProjection:
    days_remaining: float; projected_empty_date: date; daily_burn_rate_paise: float

@dataclass
class DailyScanResult:
    customers_scanned: int; alerts_sent: int; offers_generated: int; fa_items_created: int


@dataclass(frozen=True)
class AlertFired:
    """Return type of MeterService.check_thresholds(). C-043 threshold breach record."""
    customer_id: UUID
    bucket_type: str       # thread_type | "AGENCY" | "PROCUREMENT"
    threshold_name: str    # e.g. WARN_10, RUNWAY_P0
    pct_consumed: float    # 0.0–1.0
    scope: str             # CUSTOMER_BUCKET | AGENCY | PROCUREMENT
    fired_at: datetime


@dataclass
class UsageStatus:
    """Response model for GET /meter/{customer_id}/status."""
    customer_id: UUID
    depletion_projections: list[DepletionProjection]
    alerts_active: list[str]    # threshold_names in meter_alert_log for current period
    billing_halted: bool        # from Redis wbe:billing_halted


@dataclass(frozen=True)
class FounderActionCreated:
    """Returned by ProcurementService.check_and_alert() when FA entry is appended."""
    fa_number: str         # e.g. FA-042
    provider_name: str
    days_remaining: float
    priority: str          # P0 | P1 | P2
    created_at: datetime


@dataclass(frozen=True)
class ProviderRunwayStatus:
    """One entry in GET /platform/procurement/status response. ADR-029 providers."""
    provider_name: str
    balance_paise: int
    daily_burn_rate_paise: float
    days_remaining: float
    last_fa_level_triggered: str | None


@dataclass
class DailyAuditResult:
    """Returned by ReconciliationService.run_daily_audit()."""
    audit_date: date
    reservations_checked: int
    unlinked_reservations: list[UUID]  # bucket_reservation_ids with no cost_ledger match
    completed_at: datetime


@dataclass
class SelfAuditResult:
    """C-091: discrepancy >1 paise → billing_halted=True + FA created."""
    discrepancy_paise: int
    billing_halted: bool
    founder_action_created: bool
    buckets_checked: int
    audited_at: datetime


@dataclass(frozen=True)
class CustomerMarginRow:
    """One row in ReconciliationService.generate_margin_report(). margin_pct=(rev-cost)/rev."""
    customer_id: UUID
    revenue_paise: int
    cost_paise: int
    margin_pct: float    # 1.0 = 100%
    period_date: date


@dataclass
class TrialStartResult:
    """Returned by TrialService.start_trial(). C-019: phone_verified gate enforced before creation."""
    trial_id: UUID
    customer_id: UUID
    agent_type: str
    expires_at: datetime
    wallet_bucket_ids: list[UUID]
    units_granted: dict[str, int]   # thread_type → granted units


@dataclass(frozen=True)
class ConvertResult:
    """Returned by TrialService.convert_to_paid(). C-090 grandfather applies ≤14d from trial start."""
    trial_id: UUID
    converted_at: datetime
    c090_grandfather_applied: bool
    subscription_id: UUID


@dataclass(frozen=True)
class CouponValidation:
    """Returned by PromotionsService.validate_coupon(). valid=False carries error_code."""
    valid: bool
    discount_pct: float | None   # None when valid=False
    error_code: str | None       # COUPON_EXPIRED | COUPON_USED | DISCOUNT_EXCEEDS_CAP | AGENT_TYPE_MISMATCH | TIER_MISMATCH


@dataclass(frozen=True)
class DiscountResult:
    """Returned by PromotionsService.apply_discount(). SELECT FOR UPDATE guards coupon double-spend."""
    original_price_paise: int
    discount_pct: float
    discounted_price_paise: int
    coupon_id: UUID
    referral_credited: bool


class InsufficientBalanceError(Exception):
    def __init__(self, thread_type: str, requested: int, available: int) -> None: ...
class BucketNotFoundError(Exception): pass
class DuplicateReservationError(Exception): pass
class BillingProfileMissingError(Exception):
    """C-088: agent_type has no FOUNDER_AUTHORIZED billing profile."""
class BelowConstitutionalFloorError(Exception):
    """C-089: proposed price below minimum margin floor."""
class GrandfatherPriceViolationError(Exception):
    """C-090: renewal price exceeds agreed price without acknowledged notice."""
class BillingIntegrityHaltError(Exception):
    """Raised when reconciliation detects discrepancy >1 paise — halts all billing."""
class TrialAlreadyActiveError(Exception):
    """CCT-TRIAL-01: start_trial called when active or converted trial already exists → HTTP 409."""
class TrialConfigMissingError(Exception):
    """settings.TRIAL_FREE_UNITS missing key for agent_type → HTTP 422 TRIAL_CONFIG_MISSING."""
class PhoneVerificationRequiredError(Exception):
    """C-019: phone_verified=False on start_trial — informed consent gate → HTTP 422."""
