# Implements: architecture/reference/components/manifest/wbe.yaml §surface.endpoints
# Constitutional basis: C-088, C-089, C-090, C-091, C-038, C-048, C-051
# EA-PRODUCED SKELETON — DO NOT change signatures. Raise SPEC_GAP if change needed.

from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from uuid import UUID
from datetime import date, datetime
from typing import Optional


class PacingMode(str, Enum):
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
    def derive_bundle_cost_floor(self, agent_type: str, bundle_tier: str) -> int:
        # Returns: cost floor in INR paise
        # Layer 2: Σ(marked_up_thread_cost × ration) + infra_share
        ...

    @abstractmethod
    def validate_price(self, agent_type: str, bundle_tier: str,
                       proposed_price_paise: int) -> PriceValidation:
        # C-089: raises BelowConstitutionalFloorError if below min margin
        # Logs to institutional.pricing_floor_log regardless of outcome
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
    weekly_sub_limit_paise: Optional[int]

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
    valid: bool; cost_floor_paise: int; margin_pct: float
    constitutional_minimum_margin_pct: float; below_floor: bool

@dataclass(frozen=True)
class DepletionProjection:
    days_remaining: float; projected_empty_date: date; daily_burn_rate_paise: float

@dataclass
class DailyScanResult:
    customers_scanned: int; alerts_sent: int; offers_generated: int; fa_items_created: int


class InsufficientBalanceError(Exception):
    def __init__(self, thread_type: str, requested: int, available: int): ...
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
