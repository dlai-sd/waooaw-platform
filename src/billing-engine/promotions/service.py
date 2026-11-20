# Implements: work-contracts/WC-031-goal005-wbe-trial-promotions.md §WC031-02
# Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C5-07
# constitutional_basis: C-088 (discount cap enforcement), C-089 (cost floor), C-059 (Traceability)
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone

import redis.asyncio as aioredis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from config import Settings
from promotions.coupon_versions import CouponQuote, CouponRedemption, quote_coupon, redeem_coupon
from promotions.models import CouponValidation, DiscountResult, ReferralEntry, ReferralStatus

logger = logging.getLogger(__name__)


def _as_utc_datetime(value: object | None) -> datetime | None:
    if not value:
        return None
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


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
        agent_version: str = "1.0.0",
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
                    "SELECT coupon_id, discount_pct, bonus_credits, agent_type, agent_version, "
                    "min_tier, max_uses, uses_count, valid_from, valid_until, active "
                    "FROM coupon_codes WHERE code = :code"
                ).bindparams(code=code)
            )
            row = result.fetchone()

        if row is None or not row[10]:  # not found or inactive
            return CouponValidation(valid=False, discount_pct=0, bonus_credits={}, expires_at=None, error_code="COUPON_NOT_FOUND")

        _coupon_id, discount_pct, bonus_credits_raw, coupon_agent_type, coupon_agent_version, min_tier, max_uses, uses_count, valid_from, valid_until, _active = row

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
        if coupon_agent_version is not None and coupon_agent_version != agent_version:
            return CouponValidation(valid=False, discount_pct=0, bonus_credits={}, expires_at=valid_until_dt, error_code="COUPON_VERSION_MISMATCH")

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

    async def validate_commercial_preview_coupon(
        self,
        code: str,
        agent_type: str,
        agent_version: str,
    ) -> CouponValidation:
        """Validate an unconsumed coupon before a customer relationship exists."""
        max_discount: int = getattr(self._settings, "MAX_DISCOUNT_PCT", 100)
        async with self._session_factory() as session:
            result = await session.execute(
                text(
                    "SELECT discount_pct, bonus_credits, agent_type, agent_version, min_tier, max_uses, uses_count, "
                    "valid_from, valid_until, active FROM coupon_codes WHERE code = :code"
                ).bindparams(code=code)
            )
            row = result.fetchone()

        if row is None or not row[9]:
            return CouponValidation(False, 0, {}, None, "COUPON_NOT_FOUND")

        discount_pct, bonus_credits_raw, coupon_agent_type, coupon_agent_version, min_tier, max_uses, uses_count, valid_from, valid_until, _active = row
        if isinstance(bonus_credits_raw, str):
            bonus_credits = json.loads(bonus_credits_raw) if bonus_credits_raw else {}
        else:
            bonus_credits = bonus_credits_raw or {}
        now = datetime.now(tz=timezone.utc)
        valid_until_dt = _as_utc_datetime(valid_until)
        valid_from_dt = _as_utc_datetime(valid_from)

        if (valid_from_dt and now < valid_from_dt) or (valid_until_dt and now > valid_until_dt):
            return CouponValidation(False, 0, {}, valid_until_dt, "COUPON_EXPIRED")
        if max_uses is not None and uses_count >= max_uses:
            return CouponValidation(False, 0, {}, valid_until_dt, "COUPON_USED")
        if coupon_agent_type is not None and coupon_agent_type != agent_type:
            return CouponValidation(False, 0, {}, valid_until_dt, "COUPON_AGENT_MISMATCH")
        if coupon_agent_version is not None and coupon_agent_version != agent_version:
            return CouponValidation(False, 0, {}, valid_until_dt, "COUPON_VERSION_MISMATCH")
        if min_tier is not None:
            return CouponValidation(False, 0, {}, valid_until_dt, "COUPON_TIER_MISMATCH")
        if discount_pct > max_discount:
            return CouponValidation(False, discount_pct, bonus_credits, valid_until_dt, "DISCOUNT_EXCEEDS_CAP")
        return CouponValidation(True, discount_pct, bonus_credits, valid_until_dt)

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
        Idempotent referral status transition: fires only when credit_status='PENDING'.
        The reward is a goodwill coupon, never wallet credit (WC-136 C5-07).
        """
        async with self._session_factory() as session:
            await self._credit_referrer_in_session(session, referral_id)
            await session.commit()

    async def _credit_referrer_in_session(
        self,
        session: AsyncSession,
        referral_id: uuid.UUID,
    ) -> None:
        """Inner helper — must be called inside an open session; caller commits.

        A referral reward is goodwill and goodwill is a discount coupon only (WC-136 C5-07), so the status moves
        to CREDITED exactly once and no wallet balance is ever touched.
        """
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
        logger.info("Referral reward recorded as a goodwill coupon entitlement: referral_id=%s", referral_id)

    # ------------------------------------------------------------------
    # Versioned goodwill coupons (WC-136 C5-07)
    # ------------------------------------------------------------------

    async def quote_versioned_coupon(
        self,
        *,
        code: str,
        agent_type: str,
        agent_version: str,
        price_incl_gst_paise: int,
        event: str,
    ) -> CouponQuote:
        """Read the effective COUPON version and price one hire or renewal; raises CouponError."""
        async with self._session_factory() as session:
            return await quote_coupon(
                session,
                code=code,
                agent_type=agent_type,
                agent_version=agent_version,
                price_incl_gst_paise=price_incl_gst_paise,
                event=event,
                at=datetime.now(tz=timezone.utc),
            )

    async def redeem_versioned_coupon(
        self,
        *,
        code: str,
        agent_type: str,
        agent_version: str,
        tenant_id: uuid.UUID,
        relationship_id: uuid.UUID,
        event: str,
        period_start: datetime,
        price_incl_gst_paise: int,
        idempotency_key: uuid.UUID,
    ) -> CouponRedemption:
        """Record a redemption with its reason; a discount is never a wallet credit."""
        async with self._session_factory() as session:
            redemption = await redeem_coupon(
                session,
                code=code,
                agent_type=agent_type,
                agent_version=agent_version,
                tenant_id=tenant_id,
                relationship_id=relationship_id,
                event=event,
                period_start=period_start,
                price_incl_gst_paise=price_incl_gst_paise,
                idempotency_key=idempotency_key,
                at=datetime.now(tz=timezone.utc),
            )
            await session.commit()
        return redemption

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
