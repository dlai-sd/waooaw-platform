# Implements: WC-112 R056
# Constitutional basis: C-023, C-059, C-088
from __future__ import annotations

import asyncio
import os
import uuid

import pytest
from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from payment import router as payment_router


@pytest.mark.asyncio
async def test_coupon_capacity_is_serialized_across_concurrent_reservations(monkeypatch) -> None:
    sync_url = os.getenv("WC112_POSTGRES_URL")
    if not sync_url:
        pytest.skip("set WC112_POSTGRES_URL to run PostgreSQL coupon concurrency validation")
    engine = create_async_engine(
        sync_url.replace("postgresql://", "postgresql+asyncpg://"),
        connect_args={"server_settings": {"search_path": "business,public"}},
    )
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    monkeypatch.setattr(payment_router._settings, "RAZORPAY_CHECKOUT_TTL_SECONDS", 900)
    coupon_id = uuid.uuid4()
    coupon_code = "WC112RACE"
    async with factory() as session:
        await session.execute(
            text("DELETE FROM coupon_reservations WHERE coupon_id IN (SELECT coupon_id FROM coupon_codes WHERE code = :code)"),
            {"code": coupon_code},
        )
        await session.execute(text("DELETE FROM coupon_codes WHERE code = :code"), {"code": coupon_code})
        await session.execute(
            text(
                "INSERT INTO coupon_codes "
                "(coupon_id, code, discount_pct, agent_type, agent_version, max_uses, created_by) "
                "VALUES (:coupon_id, :code, 50, 'DMA', '1.0.0', 1, 'founder')"
            ),
            {"coupon_id": coupon_id, "code": coupon_code},
        )
        await session.commit()

    preview = payment_router.HireCommercialPreview(
        outcome_kind="POSITIVE_PAYMENT_REQUIRED",
        professional_type="DMA",
        list_price_inr_paise=10000,
        discount_inr_paise=5000,
        tax_inr_paise=900,
        payable_inr_paise=5900,
        cadence="MONTHLY",
        coupon_code=coupon_code,
        payment_method_required=True,
        payments_enabled=True,
        renewal_consequence="Renews monthly.",
    )
    first_has_lock = asyncio.Event()

    async def reserve(checkout_id: uuid.UUID, hold_lock: bool) -> str:
        body = payment_router.PreHireCheckoutBody(
            checkout_intent_id=checkout_id,
            correlation_id=uuid.uuid4(),
            customer_id=uuid.uuid4(),
            professional_type="DMA",
            professional_version="1.0.0",
            gross_amount_inr_paise=10000,
            gst_amount_inr_paise=900,
            cadence="MONTHLY",
            coupon_code=coupon_code,
            disclosure_revision="1.0.0",
            terms_version="2026-07-18",
        )
        try:
            async with factory() as session, session.begin():
                await payment_router._reserve_checkout_coupon(session, body, preview)
                if hold_lock:
                    first_has_lock.set()
                    await asyncio.sleep(0.2)
            return "RESERVED"
        except HTTPException as error:
            assert error.status_code == 409
            assert error.detail == {"code": "COUPON_RESERVATION_UNAVAILABLE"}
            return "REJECTED"

    try:
        first = asyncio.create_task(reserve(uuid.uuid4(), True))
        try:
            await asyncio.wait_for(first_has_lock.wait(), timeout=10)
        except TimeoutError:
            await first
            raise
        second = asyncio.create_task(reserve(uuid.uuid4(), False))
        assert sorted(await asyncio.gather(first, second)) == ["REJECTED", "RESERVED"]
        async with factory() as session:
            count = await session.scalar(
                text("SELECT COUNT(*) FROM coupon_reservations WHERE coupon_id = :coupon_id AND status = 'RESERVED'"),
                {"coupon_id": coupon_id},
            )
        assert count == 1
    finally:
        async with factory() as session:
            await session.execute(
                text("DELETE FROM coupon_reservations WHERE coupon_id = :coupon_id"),
                {"coupon_id": coupon_id},
            )
            await session.execute(text("DELETE FROM coupon_codes WHERE coupon_id = :coupon_id"), {"coupon_id": coupon_id})
            await session.commit()
        await engine.dispose()
