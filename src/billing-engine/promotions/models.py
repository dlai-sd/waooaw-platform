# Implements: work-contracts/WC-031-goal005-wbe-trial-promotions.md §WC031-02
# constitutional_basis: C-088 (discount cap), C-059 (Traceability)
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime


@dataclass
class CouponValidation:
    valid: bool
    discount_pct: int
    bonus_credits: dict[str, int]
    expires_at: datetime | None
    error_code: str | None = None


@dataclass
class DiscountResult:
    discounted_price_paise: int
    discount_amount_paise: int
    referral_credited: bool


@dataclass
class ReferralEntry:
    referee_id: uuid.UUID
    referred_at: datetime
    credit_status: str


@dataclass
class ReferralStatus:
    referrals: list[ReferralEntry]
    total_credits_paise: int
