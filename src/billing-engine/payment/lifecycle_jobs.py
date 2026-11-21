# Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C4-10
# Constitutional basis: C-059, C-038, ADR-026
"""Scheduled sweep of the package lifecycle (WC-136 C4-10): grace expiry, fee-refund dispatch, upgrade-fee orders."""

from __future__ import annotations

import logging
from collections.abc import Callable

from sqlalchemy.ext.asyncio import AsyncSession

from markup.package_engine import SqlPackageReferenceData
from payment.lifecycle import BillingAdjustments, LifecycleService, OrderClient, RefundClient
from payment.razorpay_client import RazorpayClient

logger = logging.getLogger(__name__)

_DISPATCH_BATCH = 50


async def run_lifecycle_sweep(
    open_session: Callable[[], AsyncSession],
    client: RefundClient | None = None,
    order_client: OrderClient | None = None,
) -> tuple[int, int, int]:
    """Suspend relationships whose grace has ended, send open fee refunds and open upgrade-fee orders.

    Returns (suspended, dispatched, collected). The steps commit separately so a provider outage never undoes
    a suspension, and a refund or order failure stays retryable for the next sweep.
    """
    async with open_session() as session:
        suspended = await LifecycleService(session, rates=SqlPackageReferenceData(session)).suspend_expired_grace()
        await session.commit()
    async with open_session() as session:
        dispatched = await BillingAdjustments(session).dispatch_pending(client or RazorpayClient(), _DISPATCH_BATCH)
        await session.commit()
    async with open_session() as session:
        collected = await BillingAdjustments(session).collect_pending(order_client or RazorpayClient(), _DISPATCH_BATCH)
        await session.commit()
    logger.info("lifecycle_sweep suspended=%s dispatched=%s collected=%s", suspended, dispatched, collected)
    return suspended, dispatched, collected
