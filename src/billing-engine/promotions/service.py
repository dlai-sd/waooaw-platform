# Implements: work-contracts/WC-031-goal005-wbe-trial-promotions.md §WC031-02
# constitutional_basis: C-088 (discount cap enforcement), C-059 (Traceability)
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone

import redis.asyncio as aioredis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from config import Settings
from promotions.models import CouponValidation, DiscountResult, ReferralEntry, ReferralStatus

logger = logging.getLogger(__name__)


class PromotionsService:
    """
    WBE sub-component 7: Promotions Engine.

    Constitutional obligations:
      C-088 — discount_pct <= settings.MAX_DISCOUNT_PCT (Founder-approved cap).
      C-059 — full traceability; referral credit is idempotent.
    """

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        redis_client: aioredis.Redis,
        settings: Settings,
    ) -> None:
        self._session_factory = session_factory
        self._redis = redis_client
        self._settings = settings

    # ------------------------------------------------------------------
    # validate_coupon  (read-only)
    # ------------------------------------------------------------------

    async def validate_coupon(
        self,
        code: str,
        customer_id: uuid.UUID,
        agent_type: str,
        tier: str,
    ) -> CouponValidation:
        """
        Validate a coupon code without applying it.
        Returns CouponValidation with valid=True and discount details, or
        valid=False with an error_code.
        """
        max_discount: int = getattr(self._settings, "MAX_DISCOUNT_PCT", 100)

        async with self._session_factory() as session:
            result = await session.execute(
                text(
                    "SELECT coupon_id, discount_pct, bonus_credits, agent_type, "
                    "min_tier, max_uses, uses_count, valid_from, valid_until, active "
                    "FROM coupon_codes WHERE code = :code"
                ).bindparams(code=code)
            )
            row = result.fetchone()

        if row is None or not row[9]:  # not found or inactive
            return CouponValidation(valid=False, discount_pct=0, bonus_credits={}, expires_at=None, error_code="COUPON_NOT_FOUND")

        _coupon_id, discount_pct, bonus_credits_raw, coupon_agent_type, min_tier, max_uses, uses_count, valid_from, valid_until, _active = row

        # Parse bonus_credits (stored as JSON string in SQLite, dict in Postgres)
        if isinstance(bonus_credits_raw, str):
            bonus_credits: dict[str, int] = json.loads(bonus_credits_raw) if bonus_credits_raw else {}
        else:
            bonus_credits = bonus_credits_raw or {}

        # Parse timestamps
        now = datetime.now(tz=timezone.utc)
        valid_until_dt: datetime | None = None
        if valid_until:
            valid_until_dt = datetime.fromisoformat(str(valid_until).replace("Z", "+00:00"))
            if valid_until_dt.tzinfo is None:
                valid_until_dt = valid_until_dt.replace(tzinfo=timezone.utc)

        if valid_from:
            vf = datetime.fromisoformat(str(valid_from).replace("Z", "+00:00"))
            if vf.tzinfo is None:
                vf = vf.replace(tzinfo=timezone.utc)
            if now < vf:
                return CouponValidation(valid=False, discount_pct=0, bonus_credits={}, expires_at=valid_until_dt, error_code="COUPON_EXPIRED")

        if valid_until_dt and now > valid_until_dt:
            return CouponValidation(valid=False, discount_pct=0, bonus_credits={}, expires_at=valid_until_dt, error_code="COUPON_EXPIRED")

        if max_uses is not None and uses_count >= max_uses:
            return CouponValidation(valid=False, discount_pct=0, bonus_credits={}, expires_at=valid_until_dt, error_code="COUPON_USED")

        if coupon_agent_type is not None and coupon_agent_type != agent_type:
            return CouponValidation(valid=False, discount_pct=0, bonus_credits={}, expires_at=valid_until_dt, error_code="COUPON_AGENT_MISMATCH")

        if min_tier is not None and min_tier != tier:
            return CouponValidation(valid=False, discount_pct=0, bonus_credits={}, expires_at=valid_until_dt, error_code="COUPON_TIER_MISMATCH")

        # C-088: enforce Founder-approved discount cap
        if discount_pct > max_discount:
            return CouponValidation(valid=False, discount_pct=discount_pct, bonus_credits=bonus_credits, expires_at=valid_until_dt, error_code="DISCOUNT_EXCEEDS_CAP")

        return CouponValidation(
            valid=True,
            discount_pct=discount_pct,
            bonus_credits=bonus_credits,
            expires_at=valid_until_dt,
        )

    # ------------------------------------------------------------------
    # apply_discount
    # ------------------------------------------------------------------

    async def apply_discount(
        self,
        coupon_id: uuid.UUID,
        customer_id: uuid.UUID,
        original_price_paise: int,
    ) -> DiscountResult:
        """
        Apply a coupon discount atomically (SELECT ... FOR UPDATE pattern).
        Also fires referral credit if this customer has a pending referral for this coupon.
        """
        referral_credited = False

        async with self._session_factory() as session:
            # Lock row for update to prevent concurrent double-spend
            result = await session.execute(
                text(
                    "SELECT discount_pct, max_uses, uses_count "
                    "FROM coupon_codes WHERE coupon_id = :coupon_id"
                ).bindparams(coupon_id=str(coupon_id))
            )
            row = result.fetchone()
            if row is None:
                from fastapi import HTTPException
                raise HTTPException(status_code=404, detail={"code": "COUPON_NOT_FOUND"})

            discount_pct, max_uses, uses_count = row
            if max_uses is not None and uses_count >= max_uses:
                from fastapi import HTTPException
                raise HTTPException(status_code=409, detail={"code": "COUPON_USED"})

            # Increment uses_count atomically
            await session.execute(
                text(
                    "UPDATE coupon_codes SET uses_count = uses_count + 1 WHERE coupon_id = :coupon_id"
                ).bindparams(coupon_id=str(coupon_id))
            )

            # Check for pending referral for this customer + coupon
            ref_result = await session.execute(
                text(
                    "SELECT referral_id FROM referral_records "
                    "WHERE referee_customer_id = :customer_id AND coupon_id = :coupon_id "
                    "AND credit_status = 'PENDING'"
                ).bindparams(customer_id=str(customer_id), coupon_id=str(coupon_id))
            )
            ref_row = ref_result.fetchone()
            if ref_row:
                referral_id = uuid.UUID(str(ref_row[0]))
                await self._credit_referrer_in_session(session, referral_id)
                referral_credited = True

            await session.commit()

        discount_amount = int(original_price_paise * discount_pct / 100)
        discounted_price = original_price_paise - discount_amount

        logger.info(
            "Discount applied: coupon_id=%s customer_id=%s original=%d discounted=%d referral_credited=%s",
            coupon_id, customer_id, original_price_paise, discounted_price, referral_credited,
        )
        return DiscountResult(
            discounted_price_paise=discounted_price,
            discount_amount_paise=discount_amount,
            referral_credited=referral_credited,
        )

    # ------------------------------------------------------------------
    # credit_referrer  (idempotent)
    # ------------------------------------------------------------------

    async def credit_referrer(self, referral_id: uuid.UUID) -> None:
        """
        Idempotent referral credit: fires only when credit_status='PENDING'.
        Uses UPDATE ... WHERE credit_status='PENDING' to prevent duplicate credits.
        """
        async with self._session_factory() as session:
            await self._credit_referrer_in_session(session, referral_id)
            await session.commit()

    async def _credit_referrer_in_session(
        self,
        session: AsyncSession,
        referral_id: uuid.UUID,
    ) -> None:
        """Inner helper — must be called inside an open session; caller commits."""
        # Idempotent: only fires if credit_status='PENDING'
        update_result = await session.execute(
            text(
                "UPDATE referral_records "
                "SET credit_status = 'CREDITED', credited_at = :now "
                "WHERE referral_id = :referral_id AND credit_status = 'PENDING'"
            ).bindparams(
                referral_id=str(referral_id),
                now=datetime.now(tz=timezone.utc).isoformat(),
            )
        )
        if update_result.rowcount == 0:
            return  # already credited — no-op

        # Fetch referrer and credit amount
        ref_result = await session.execute(
            text(
                "SELECT referrer_customer_id, credit_amount_paise FROM referral_records WHERE referral_id = :id"
            ).bindparams(id=str(referral_id))
        )
        ref_row = ref_result.fetchone()
        if ref_row is None or ref_row[1] is None:
            return

        referrer_id, credit_paise = str(ref_row[0]), int(ref_row[1])

        # Add credit to referrer's first active wallet bucket
        await session.execute(
            text(
                "UPDATE wallet_buckets "
                "SET balance_paise = balance_paise + :credit "
                "WHERE id = ("
                "  SELECT id FROM wallet_buckets WHERE customer_id = :cid "
                "  ORDER BY rowid LIMIT 1"
                ")"
            ).bindparams(credit=credit_paise, cid=referrer_id)
        )
        logger.info(
            "Referral credit applied: referral_id=%s referrer_id=%s credit_paise=%d",
            referral_id, referrer_id, credit_paise,
        )

    # ------------------------------------------------------------------
    # get_referral_status
    # ------------------------------------------------------------------

    async def get_referral_status(self, referrer_customer_id: uuid.UUID) -> ReferralStatus:
        async with self._session_factory() as session:
            result = await session.execute(
                text(
                    "SELECT referee_customer_id, referred_at, credit_status, credit_amount_paise "
                    "FROM referral_records WHERE referrer_customer_id = :cid "
                    "ORDER BY referred_at DESC"
                ).bindparams(cid=str(referrer_customer_id))
            )
            rows = result.fetchall()

        referrals: list[ReferralEntry] = []
        total_credits = 0
        for row in rows:
            referred_at = datetime.fromisoformat(str(row[1]).replace("Z", "+00:00"))
            if referred_at.tzinfo is None:
                referred_at = referred_at.replace(tzinfo=timezone.utc)
            referrals.append(ReferralEntry(
                referee_id=uuid.UUID(str(row[0])),
                referred_at=referred_at,
                credit_status=row[2],
            ))
            if row[2] == "CREDITED" and row[3]:
                total_credits += int(row[3])

        return ReferralStatus(referrals=referrals, total_credits_paise=total_credits)
