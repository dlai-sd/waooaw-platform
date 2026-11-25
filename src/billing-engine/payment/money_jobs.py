# Implements: work-contracts/WC-172-safe-to-charge-real-customers.md WC172-R010, WC172-R011
# Constitutional basis: C-007, C-023, C-059, C-088
"""Wiring of the money guard: the check each new order passes and the daily reconciliation run."""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from config import Settings
from payment.money_gate import MoneyGate
from payment.money_reconciliation import MoneyReconciler, ProviderLedger, RazorpayProviderLedger, ReconciliationReport
from payment.razorpay_client import RazorpayClient

logger = logging.getLogger(__name__)

# The newest minutes are left out so a payment whose invoice is still being issued is not reported.
_SETTLING_MINUTES = 15


def make_charge_guard(open_session: Callable[[], AsyncSession]):
    async def guard(settings: Settings) -> None:
        async with open_session() as session:
            await MoneyGate(session, settings.WAOOAW_ENVIRONMENT, settings.RAZORPAY_PAYMENT_MODE).require_charge_allowed()

    return guard


async def run_money_reconciliation(
    open_session: Callable[[], AsyncSession],
    ledger: ProviderLedger | None = None,
    *,
    window_hours: int = 48,
    now: Callable[[], datetime] | None = None,
) -> ReconciliationReport | None:
    """Compare the provider's last ``window_hours`` with the books. Returns None when the provider cannot be read:
    the run is retried by the next schedule and never reported as clean."""
    clock = now or (lambda: datetime.now(timezone.utc))
    end = clock() - timedelta(minutes=_SETTLING_MINUTES)
    start = end - timedelta(hours=window_hours)
    try:
        provider = ledger or RazorpayProviderLedger(RazorpayClient())
        async with open_session() as session:
            report = await MoneyReconciler(session, provider, now=clock).reconcile(start, end)
            await session.commit()
    except Exception:
        logger.exception("money_reconciliation unavailable")
        return None
    logger.info(
        "money_reconciliation payments=%s refunds=%s opened=%s", report.checked_payments, report.checked_refunds, report.opened
    )
    return report
