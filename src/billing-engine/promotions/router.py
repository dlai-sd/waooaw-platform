# Implements: work-contracts/WC-031-goal005-wbe-trial-promotions.md §WC031-02
# constitutional_basis: C-059 (Implementation Traceability)
from __future__ import annotations

import uuid

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from config import Settings
from promotions.service import PromotionsService

router = APIRouter(prefix="/promotions", tags=["promotions"])


# ---------------------------------------------------------------------------
# Dependency helpers
# ---------------------------------------------------------------------------

def _get_settings() -> Settings:
    return Settings()


def _get_redis(settings: Settings = Depends(_get_settings)) -> aioredis.Redis:
    return aioredis.from_url(settings.REDIS_URL, decode_responses=False)


def _get_promotions_service(
    settings: Settings = Depends(_get_settings),
    redis_client: aioredis.Redis = Depends(_get_redis),
) -> PromotionsService:
    from database import get_session_factory
    sf = get_session_factory()
    return PromotionsService(session_factory=sf, redis_client=redis_client, settings=settings)


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class ValidateCouponRequest(BaseModel):
    coupon_code: str
    customer_id: uuid.UUID
    agent_type: str
    subscription_tier: str


class ValidateCouponResponse(BaseModel):
    valid: bool
    discount_pct: int
    bonus_credits: dict[str, int]
    expires_at: str | None
    error_code: str | None = None


class ApplyDiscountRequest(BaseModel):
    coupon_id: uuid.UUID
    customer_id: uuid.UUID
    original_price_paise: int


class ApplyDiscountResponse(BaseModel):
    discounted_price_paise: int
    discount_amount_paise: int
    referral_credited: bool


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/validate-coupon", response_model=ValidateCouponResponse)
async def validate_coupon(
    body: ValidateCouponRequest,
    service: PromotionsService = Depends(_get_promotions_service),
) -> ValidateCouponResponse:
    result = await service.validate_coupon(
        code=body.coupon_code,
        customer_id=body.customer_id,
        agent_type=body.agent_type,
        tier=body.subscription_tier,
    )
    return ValidateCouponResponse(
        valid=result.valid,
        discount_pct=result.discount_pct,
        bonus_credits=result.bonus_credits,
        expires_at=result.expires_at.isoformat() if result.expires_at else None,
        error_code=result.error_code,
    )


@router.post("/apply-discount", response_model=ApplyDiscountResponse)
async def apply_discount(
    body: ApplyDiscountRequest,
    service: PromotionsService = Depends(_get_promotions_service),
) -> ApplyDiscountResponse:
    result = await service.apply_discount(
        coupon_id=body.coupon_id,
        customer_id=body.customer_id,
        original_price_paise=body.original_price_paise,
    )
    return ApplyDiscountResponse(
        discounted_price_paise=result.discounted_price_paise,
        discount_amount_paise=result.discount_amount_paise,
        referral_credited=result.referral_credited,
    )


@router.get("/referral-status/{referrer_customer_id}")
async def get_referral_status(
    referrer_customer_id: uuid.UUID,
    service: PromotionsService = Depends(_get_promotions_service),
) -> dict:
    status = await service.get_referral_status(referrer_customer_id)
    return {
        "referrals": [
            {
                "referee_id": str(r.referee_id),
                "referred_at": r.referred_at.isoformat(),
                "credit_status": r.credit_status,
            }
            for r in status.referrals
        ],
        "total_credits_paise": status.total_credits_paise,
    }
