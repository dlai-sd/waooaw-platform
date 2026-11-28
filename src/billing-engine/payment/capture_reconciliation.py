# Implements: work-contracts/WC-176-customer-journeys-registration-trial-hire-and-pages.md WC176-R015, WC176-R017
# Constitutional basis: C-023, C-059, C-063
"""Reconciliation of captured payments: none is lost, each ends as a completed Hire with an invoice, or REFUND_DUE.

Run by the billing engine every fifteen minutes and by hand:

    python -m payment.capture_reconciliation reconcile [--window-hours 48] [--stale-hours 24]

1. Payments Razorpay shows as captured that the webhook never recorded are recorded now (source RECONCILIATION).
2. Every capture still RECEIVED is completed through ``complete_captured_payment``, the path the webhook uses. A capture
   that can never be completed (no customer, a conflicting order) or that stayed uncompleted past ``stale-hours`` is
   marked REFUND_DUE.
3. Every COMPLETED capture without a tax invoice gets one, and a hire capture whose Hire was not completed within
   ``stale-hours`` is marked REFUND_DUE. A refund is sent by the Founder or the lifecycle refund path, never here.
Every step is replay-safe, so the run can be repeated at any time.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from collections.abc import Awaitable, Callable
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from invoicing.hooks import issue_invoice_safely, payer_of
from payment import capture_records as records
from wallet.entity_models import as_utc

logger = logging.getLogger(__name__)

_BATCH = 100
# A retry cannot fix these: the capture has no customer or conflicts with what is stored.
_TERMINAL_CODES = frozenset(
    {
        "MISSING_CUSTOMER_ID",
        "MISSING_CHECKOUT_INTENT_ID",
        "INVALID_PAYMENT_REFERENCE",
        "INVALID_CONTRACT_LINK",
        "PRE_HIRE_CAPTURE_CONFLICT",
        "PAYMENT_CAPTURE_CONFLICT",
        "INCOMPLETE_CONTRACT_LINK",
    }
)
# These kinds are finished by the capture itself; every other kind is a Hire that must reach ACTIVATED.
_SELF_COMPLETING_KINDS = frozenset({"RENEWAL", "UPGRADE_FEE"})

Completer = Callable[[dict], Awaitable[dict]]


@dataclass(frozen=True)
class CaptureReconciliationReport:
    ingested: int
    completed: int
    invoiced: int
    refund_due: int
    unresolved: int


async def _default_completer(payment: dict) -> dict:
    from payment.razorpay_client import RazorpayClient
    from payment.router import complete_captured_payment

    return await complete_captured_payment(payment, "", RazorpayClient())


def _uuid(value: object) -> UUID | None:
    try:
        return UUID(str(value))
    except (ValueError, TypeError):
        return None


async def _has_invoice(session: AsyncSession, payment_id: str) -> bool:
    row = (
        await session.execute(
            text(
                "SELECT 1 FROM business.tax_documents WHERE document_kind = 'TAX_INVOICE' "
                "AND source_kind = 'PAYMENT' AND source_reference = :id"
            ),
            {"id": payment_id},
        )
    ).first()
    return row is not None


async def _hire_activated(session: AsyncSession, payment_id: str) -> bool:
    row = (
        await session.execute(
            text("SELECT 1 FROM payment_intents WHERE razorpay_payment_id = :id AND status = 'ACTIVATED'"),
            {"id": payment_id},
        )
    ).first()
    return row is not None


async def reconcile_captures(
    open_session: Callable[[], AsyncSession],
    provider: Any | None = None,
    *,
    settings: Any | None = None,
    completer: Completer | None = None,
    now: Callable[[], datetime] | None = None,
    window_hours: int = 48,
    stale_hours: int = 24,
) -> CaptureReconciliationReport:
    clock = now or (lambda: datetime.now(timezone.utc))
    complete = completer or _default_completer
    if settings is None:
        from config import Settings

        settings = Settings()
    stale_before = as_utc(clock()) - timedelta(hours=stale_hours)
    ingested = completed = invoiced = refund_due = unresolved = 0

    if provider is not None:
        end = as_utc(clock())
        try:
            items = await provider.list_collection(
                "payments", int((end - timedelta(hours=window_hours)).timestamp()), int(end.timestamp())
            )
        except Exception:
            logger.exception("capture_reconciliation provider_unavailable")
            items = []
        async with open_session() as session:
            ledger = records.CaptureLedger(session, now=clock)
            for item in items:
                if item.get("status") == "captured" and item.get("id") and not await ledger.known(str(item["id"])):
                    ingested += await ledger.record_capture(item, records.SOURCE_RECONCILIATION)

    async with open_session() as session:
        received = await records.CaptureLedger(session, now=clock).captures_with_status(records.RECEIVED, _BATCH)
    for capture in received:
        async with open_session() as session:
            ledger = records.CaptureLedger(session, now=clock)
            payment = {k: capture[k] for k in ("id", "order_id", "amount", "notes")}
            try:
                await complete(payment)
            except HTTPException as error:
                code = str(error.detail.get("code", "")) if isinstance(error.detail, dict) else ""
                if code in _TERMINAL_CODES:
                    await ledger.mark_refund_due(capture["id"], code)
                    refund_due += 1
                    continue
                await ledger.mark_failed(capture["id"], code or "COMPLETION_FAILED")
            except Exception:
                logger.exception("capture_reconciliation completion_failed payment=%s", capture["id"][:60])
                await ledger.mark_failed(capture["id"], "COMPLETION_FAILED")
            else:
                await ledger.mark_completed(capture["id"])
                completed += 1
                continue
            if capture["first_seen_at"] <= stale_before:
                await ledger.mark_refund_due(capture["id"], "COMPLETION_TIMED_OUT")
                refund_due += 1
            else:
                unresolved += 1

    async with open_session() as session:
        done = await records.CaptureLedger(session, now=clock).captures_with_status(records.COMPLETED, _BATCH * 2)
    for capture in done:
        async with open_session() as session:
            kind = capture["notes"].get("checkout_kind", "")
            if not await _has_invoice(session, capture["id"]):
                tenant, relationship = _uuid(capture["notes"].get("tenant_id")), _uuid(capture["notes"].get("relationship_id"))
                payer = _uuid(capture["notes"].get("customer_id"))
                if payer is None and tenant is not None and relationship is not None:
                    payer = await payer_of(session, tenant, relationship)
                issued = await issue_invoice_safely(
                    session,
                    settings,
                    payment_reference=capture["id"],
                    amount_paise=capture["amount"],
                    payer_customer_id=payer,
                    tenant_id=tenant,
                    relationship_id=relationship,
                )
                invoiced += issued is not None
            if (
                kind not in _SELF_COMPLETING_KINDS
                and (capture["completed_at"] or capture["first_seen_at"]) <= stale_before
                and not await _hire_activated(session, capture["id"])
            ):
                await records.CaptureLedger(session, now=clock).mark_refund_due(capture["id"], "HIRE_NOT_COMPLETED")
                refund_due += 1

    report = CaptureReconciliationReport(ingested, completed, invoiced, refund_due, unresolved)
    logger.info("capture_reconciliation %s", asdict(report))
    return report


async def run_capture_reconciliation(
    open_session: Callable[[], AsyncSession], *, window_hours: int = 48, stale_hours: int = 24
) -> CaptureReconciliationReport | None:
    """The scheduled run. None when it could not run; the next schedule retries and nothing is reported as clean."""
    from payment.razorpay_client import RazorpayClient

    try:
        return await reconcile_captures(open_session, RazorpayClient(), window_hours=window_hours, stale_hours=stale_hours)
    except Exception:
        logger.exception("capture_reconciliation unavailable")
        return None


async def _run_cli(window_hours: int, stale_hours: int) -> int:
    from database import close_db, get_session_factory, init_db

    await init_db()
    try:
        report = await run_capture_reconciliation(get_session_factory(), window_hours=window_hours, stale_hours=stale_hours)
    finally:
        await close_db()
    if report is None:
        print(json.dumps({"status": "UNAVAILABLE"}))
        return 1
    print(json.dumps({"status": "OK", **asdict(report)}))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="capture_reconciliation", description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)
    reconcile = commands.add_parser("reconcile", help="complete captured payments or mark them REFUND_DUE")
    reconcile.add_argument("--window-hours", type=int, default=48)
    reconcile.add_argument("--stale-hours", type=int, default=24)
    args = parser.parse_args(argv)
    return asyncio.run(_run_cli(args.window_hours, args.stale_hours))


if __name__ == "__main__":
    sys.exit(main())
