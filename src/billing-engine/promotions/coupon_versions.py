# Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C5-07
# Constitutional basis: C-059, C-088, C-089
"""Goodwill coupons read from COUPON pricing versions (WC-136 C5-07).

A coupon is the only goodwill mechanism: it lowers a package price at hire or renewal, is recorded with
its reason, and never creates wallet credit. The cost floor (C-089) is checked again at redemption
against the rates in force, because rates may have moved since the coupon was authorized.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from markup.package_engine import SqlPackageReferenceData, base_price_paise, project_package
from markup.package_models import PackageBody
from pricing.models import CouponBody, PricingKind, PricingVersion
from pricing.repository import SqlPricingRepository
from pricing.validators import coupon_discount_paise

REDEMPTION_EVENTS = ("HIRE", "RENEWAL")


class CouponError(Exception):
    """A coupon refusal; ``code`` is stable and ``status_code`` is the HTTP status a router maps it to."""

    def __init__(self, code: str, status_code: int, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.status_code = status_code
        self.message = message


@dataclass(frozen=True)
class CouponQuote:
    version_id: uuid.UUID
    code: str
    price_incl_gst_paise: int
    discount_paise: int
    discounted_price_paise: int
    reason: str
    expires_at: datetime | None
    max_redemptions: int | None
    redemptions: int | None


@dataclass(frozen=True)
class CouponRedemption:
    redemption_id: uuid.UUID
    quote: CouponQuote
    event: str
    period_start: datetime
    redeemed_at: datetime
    replayed: bool


def _coupon_body(version: PricingVersion) -> CouponBody:
    return CouponBody.model_validate(version.body)


async def _effective_coupon(session: AsyncSession, code: str, at: datetime) -> tuple[PricingVersion, CouponBody]:
    repository = SqlPricingRepository(session)
    version = await repository.effective_at(PricingKind.COUPON, f"coupon:{code}", at)
    if version is None:
        raise CouponError("COUPON_NOT_FOUND", 404, "No effective coupon has this code.")
    return version, _coupon_body(version)


async def _assert_floor(
    session: AsyncSession, coupon: CouponBody, price_incl_gst_paise: int, discount_paise: int, at: datetime
) -> None:
    repository = SqlPricingRepository(session)
    packages = [
        PackageBody.model_validate(version.body)
        for version in await repository.list_in_force(PricingKind.PACKAGE, at)
        if version.body.get("agentType") == coupon.agent_type
        and version.body.get("agentVersion") == coupon.agent_version
        and version.body.get("priceInclGstPaise") == price_incl_gst_paise
    ]
    if not packages:
        raise CouponError(
            "COUPON_FLOOR_UNVERIFIABLE", 422, "No effective package has this price, so the cost floor cannot be checked."
        )
    reference = SqlPackageReferenceData(session)
    for package in packages:
        thread_ids = sorted({entry.thread_id for component in package.components for entry in component.recipe})
        rates = await reference.thread_rates(thread_ids)
        floor = project_package(package, rates, None).cost_floor_paise
        if base_price_paise(price_incl_gst_paise - discount_paise, package.gst_rate_percent) < floor:
            raise CouponError("PRICING_BELOW_FLOOR", 422, "The discounted price is below the package cost floor.")


async def _redemption_count(session: AsyncSession, version_id: uuid.UUID) -> int:
    row = await session.execute(
        text("SELECT count(*) FROM business.coupon_version_redemptions WHERE version_id = :version"),
        {"version": str(version_id)},
    )
    return int(row.scalar_one())


def _check_applicable(coupon: CouponBody, agent_type: str, agent_version: str, event: str, at: datetime) -> None:
    if event not in REDEMPTION_EVENTS:
        raise CouponError("COUPON_EVENT_NOT_ALLOWED", 422, "A coupon applies at hire or renewal only.")
    if coupon.expires_at <= at:
        raise CouponError("COUPON_EXPIRED", 409, "The coupon has expired.")
    if coupon.agent_type != agent_type:
        raise CouponError("COUPON_AGENT_MISMATCH", 422, "The coupon is for another agent.")
    if coupon.agent_version != agent_version:
        raise CouponError("COUPON_VERSION_MISMATCH", 422, "The coupon is for another agent version.")


async def quote_coupon(
    session: AsyncSession,
    *,
    code: str,
    agent_type: str,
    agent_version: str,
    price_incl_gst_paise: int,
    event: str,
    at: datetime,
) -> CouponQuote:
    """What the coupon would give on this price now; writes nothing."""
    version, coupon = await _effective_coupon(session, code, at)
    _check_applicable(coupon, agent_type, agent_version, event, at)
    discount = coupon_discount_paise(price_incl_gst_paise, coupon)
    await _assert_floor(session, coupon, price_incl_gst_paise, discount, at)
    redemptions = await _redemption_count(session, version.version_id)
    if redemptions >= coupon.max_redemptions:
        raise CouponError("COUPON_USED", 409, "The coupon has reached its maximum redemptions.")
    return CouponQuote(
        version_id=version.version_id,
        code=coupon.code,
        price_incl_gst_paise=price_incl_gst_paise,
        discount_paise=discount,
        discounted_price_paise=price_incl_gst_paise - discount,
        reason=coupon.reason,
        expires_at=coupon.expires_at,
        max_redemptions=coupon.max_redemptions,
        redemptions=redemptions,
    )


async def redeem_coupon(
    session: AsyncSession,
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
    at: datetime,
) -> CouponRedemption:
    """Record one redemption at hire or renewal; a retry with the same key returns the first result."""
    replay = await _replay(session, idempotency_key, code, event, relationship_id, period_start)
    if replay is not None:
        return replay
    version, _ = await _effective_coupon(session, code, at)
    await session.execute(
        text("SELECT pg_advisory_xact_lock(hashtextextended(:version, 0))"), {"version": str(version.version_id)}
    )
    quote = await quote_coupon(
        session,
        code=code,
        agent_type=agent_type,
        agent_version=agent_version,
        price_incl_gst_paise=price_incl_gst_paise,
        event=event,
        at=at,
    )
    redemption_id = uuid.uuid4()
    inserted = await session.execute(
        text(
            """
            INSERT INTO business.coupon_version_redemptions
                (redemption_id, version_id, coupon_code, tenant_id, relationship_id, event, period_start,
                 price_incl_gst_paise, discount_paise, reason, idempotency_key, redeemed_at)
            VALUES (:redemption, :version, :code, :tenant, :relationship, :event, :period,
                    :price, :discount, :reason, :key, :at)
            ON CONFLICT (version_id, relationship_id, event, period_start) DO NOTHING
            """
        ),
        {
            "redemption": str(redemption_id),
            "version": str(quote.version_id),
            "code": quote.code,
            "tenant": str(tenant_id),
            "relationship": str(relationship_id),
            "event": event,
            "period": period_start,
            "price": price_incl_gst_paise,
            "discount": quote.discount_paise,
            "reason": quote.reason,
            "key": str(idempotency_key),
            "at": at,
        },
    )
    if inserted.rowcount == 0:
        raise CouponError("COUPON_ALREADY_REDEEMED", 409, "The coupon was already redeemed for this period.")
    return CouponRedemption(redemption_id, quote, event, period_start, at, replayed=False)


async def _replay(
    session: AsyncSession,
    idempotency_key: uuid.UUID,
    code: str,
    event: str,
    relationship_id: uuid.UUID,
    period_start: datetime,
) -> CouponRedemption | None:
    row = (
        await session.execute(
            text(
                """
                SELECT redemption_id, version_id, coupon_code, relationship_id, event, period_start,
                       price_incl_gst_paise, discount_paise, reason, redeemed_at
                FROM business.coupon_version_redemptions WHERE idempotency_key = :key
                """
            ),
            {"key": str(idempotency_key)},
        )
    ).mappings().one_or_none()
    if row is None:
        return None
    if (row["coupon_code"], row["event"], str(row["relationship_id"])) != (code, event, str(relationship_id)) or row[
        "period_start"
    ] != period_start:
        raise CouponError("COUPON_IDEMPOTENCY_CONFLICT", 409, "The key was used for a different redemption.")
    return CouponRedemption(
        redemption_id=uuid.UUID(str(row["redemption_id"])),
        quote=_stored_quote(row),
        event=row["event"],
        period_start=row["period_start"],
        redeemed_at=row["redeemed_at"],
        replayed=True,
    )


def _stored_quote(row: Any) -> CouponQuote:
    return CouponQuote(
        version_id=uuid.UUID(str(row["version_id"])),
        code=row["coupon_code"],
        price_incl_gst_paise=int(row["price_incl_gst_paise"]),
        discount_paise=int(row["discount_paise"]),
        discounted_price_paise=int(row["price_incl_gst_paise"]) - int(row["discount_paise"]),
        reason=row["reason"],
        expires_at=None,
        max_redemptions=None,
        redemptions=None,
    )
