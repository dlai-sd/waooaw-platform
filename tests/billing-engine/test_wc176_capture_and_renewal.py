# Implements: work-contracts/WC-176-customer-journeys-registration-trial-hire-and-pages.md WC176-R015, WC176-R016, WC176-R017
# Constitutional basis: C-023, C-059, C-063
"""A captured payment is never lost, renewals are collected and each capture has a readable GST invoice."""

from __future__ import annotations

import hashlib
import hmac
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import UUID

import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy import DateTime, bindparam, text
from starlette.requests import Request

sys.path.insert(0, str(Path(__file__).parent))

from invoicing.identity import supplier_from
from invoicing.render import render_html
from invoicing.service import TaxDocumentService
from payment import renewals
from payment import router as payment_router
from payment.capture_reconciliation import reconcile_captures
from payment.capture_records import SOURCE_WEBHOOK, CaptureLedger
from payment.lifecycle import LifecycleService, PeriodCreditService, PeriodStore
from payment.razorpay_client import RazorpayClient
from wc136_commercial_ddl import install
from wc136_commercial_fakes import (
    FakePackages,
    FakeRates,
    policy_body,
    policy_source,
    pro,
    starter,
)
from wc176_capture_ddl import capture_ddl

TENANT = UUID("11111111-1111-4111-8111-111111111111")
CUSTOMER = UUID("22222222-2222-4222-8222-222222222222")
RELATIONSHIP = UUID("44444444-4444-4444-8444-444444444444")
START = datetime(2026, 1, 1, tzinfo=timezone.utc)
NOW = datetime(2026, 11, 28, 8, 0, tzinfo=timezone.utc)
GST = SimpleNamespace(
    GST_LEGAL_NAME="DLAI Satellite Data (OPC) Pvt Ltd",
    GST_GSTIN="27AAKCD8188R1ZH",
    GST_ADDRESS="C8, Everest Heights, Park Road, Viman Nagar, Pune 411014, Maharashtra, India",
    GST_STATE_CODE="27",
    GST_SAC_CODE="9984",
    GST_RATE_PERCENT=18,
)


class _Clock:
    def __init__(self, at: datetime) -> None:
        self.at = at

    def __call__(self) -> datetime:
        return self.at


@pytest_asyncio.fixture
async def db(wallet_db):
    async with wallet_db() as session:
        await install(session)
        for statement in capture_ddl("business"):
            await session.execute(text(statement))
        await PeriodCreditService(session, rates=FakeRates(), now=_Clock(START)).start_period(
            TENANT, RELATIONSHIP, CUSTOMER, starter(), START, 30_000, UUID(int=7)
        )
        await session.commit()
    return wallet_db


def _fake_lifecycle(session, clock):
    return LifecycleService(
        session, rates=FakeRates(), packages=FakePackages(starter(), pro()), policy=policy_source(policy_body()), now=clock
    )


async def _rows(db, sql: str):
    async with db() as session:
        return (await session.execute(text(sql))).all()


def _captured_request(payment_id: str, event_id: str) -> Request:
    body = json.dumps(
        {
            "event": "payment.captured",
            "payload": {
                "payment": {
                    "entity": {
                        "id": payment_id,
                        "order_id": "order_1",
                        "amount": 59_000,
                        "currency": "INR",
                        "notes": {"checkout_kind": "RENEWAL", "customer_id": str(CUSTOMER)},
                    }
                }
            },
        }
    ).encode()

    async def receive():
        return {"type": "http.request", "body": body, "more_body": False}

    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/payments/webhooks/razorpay",
            "headers": [(b"x-razorpay-signature", b"valid"), (b"x-razorpay-event-id", event_id.encode())],
        },
        receive,
    )


@pytest.fixture
def webhook(db, monkeypatch):
    monkeypatch.setattr(payment_router, "get_session_factory", lambda: db)
    monkeypatch.setattr(payment_router.RazorpayClient, "verify_webhook_signature", lambda *_args: True)
    completer = AsyncMock()
    monkeypatch.setattr(payment_router, "complete_captured_payment", completer)
    return completer


def test_a_webhook_without_a_configured_secret_never_verifies() -> None:
    client = RazorpayClient(settings=SimpleNamespace(RAZORPAY_WEBHOOK_SECRET=""))
    forged = hmac.new(b"", b"{}", hashlib.sha256).hexdigest()
    assert client.verify_webhook_signature(b"{}", forged) is False


@pytest.mark.asyncio
async def test_a_captured_event_is_recorded_completed_once_and_its_replay_is_acknowledged(db, webhook) -> None:
    webhook.return_value = {"status": "RENEWED", "payment_reference": "pay_1"}

    first = await payment_router.razorpay_webhook(_captured_request("pay_1", "evt_1"))
    again = await payment_router.razorpay_webhook(_captured_request("pay_1", "evt_1"))

    assert first["status"] == "RENEWED"
    assert again["status"] == "replayed"
    assert webhook.await_count == 1
    assert (await _rows(db, "SELECT status, amount_paise, source FROM razorpay_captures")) == [
        ("COMPLETED", 59_000, SOURCE_WEBHOOK)
    ]
    assert (await _rows(db, "SELECT outcome FROM razorpay_webhook_events")) == [("RENEWED",)]


@pytest.mark.asyncio
async def test_a_capture_whose_completion_failed_stays_recorded_and_the_retry_completes_it(db, webhook) -> None:
    webhook.side_effect = [HTTPException(503, {"code": "PAYMENT_STATUS_UNRESOLVED"}), {"status": "CAPTURED"}]

    with pytest.raises(HTTPException):
        await payment_router.razorpay_webhook(_captured_request("pay_2", "evt_2"))
    assert (await _rows(db, "SELECT status, attempts, last_error FROM razorpay_captures")) == [
        ("RECEIVED", 1, "PAYMENT_STATUS_UNRESOLVED")
    ]
    assert (await _rows(db, "SELECT processed_at FROM razorpay_webhook_events")) == [(None,)]

    retried = await payment_router.razorpay_webhook(_captured_request("pay_2", "evt_2"))

    assert retried["status"] == "CAPTURED"
    assert (await _rows(db, "SELECT status FROM razorpay_captures")) == [("COMPLETED",)]


class _Provider:
    def __init__(self, payments: list[dict]) -> None:
        self.payments = payments

    async def list_collection(self, resource: str, start: int, end: int) -> list[dict]:
        return self.payments


def _payment(payment_id: str, **notes: str) -> dict:
    return {"id": payment_id, "order_id": "order_x", "amount": 59_000, "status": "captured", "notes": notes}


@pytest.mark.asyncio
async def test_a_payment_the_webhook_missed_is_recorded_completed_and_invoiced_once(db) -> None:
    provider = _Provider(
        [
            _payment(
                "pay_missed",
                checkout_kind="RENEWAL",
                customer_id=str(CUSTOMER),
                tenant_id=str(TENANT),
                relationship_id=str(RELATIONSHIP),
            ),
            {**_payment("pay_failed"), "status": "failed"},
        ]
    )
    completer = AsyncMock(return_value={"status": "RENEWED"})

    report = await reconcile_captures(db, provider, settings=GST, completer=completer, now=_Clock(NOW))
    rerun = await reconcile_captures(db, provider, settings=GST, completer=completer, now=_Clock(NOW))

    assert (report.ingested, report.completed, report.invoiced, report.refund_due) == (1, 1, 1, 0)
    assert (rerun.ingested, rerun.completed, rerun.invoiced, rerun.refund_due) == (0, 0, 0, 0)
    assert completer.await_count == 1
    numbers = [row[0] for row in await _rows(db, "SELECT document_number FROM business.tax_documents")]
    assert len(numbers) == 1 and re.fullmatch(r"WAOOAW/\d{4}-\d{2}/000001", numbers[0])


@pytest.mark.asyncio
async def test_a_capture_that_cannot_complete_or_has_no_hire_in_time_is_marked_refund_due(db) -> None:
    async with db() as session:
        ledger = CaptureLedger(session, now=_Clock(NOW - timedelta(days=2)))
        for payment_id in ("pay_unhired", "pay_hired"):
            await ledger.record_capture(_payment(payment_id, checkout_kind="PRE_HIRE", customer_id=str(CUSTOMER)), "WEBHOOK")
            await ledger.mark_completed(payment_id)
        await session.execute(text("INSERT INTO payment_intents (razorpay_payment_id, status) VALUES ('pay_hired', 'ACTIVATED')"))
        await session.commit()
    provider = _Provider([_payment("pay_nobody")])
    completer = AsyncMock(side_effect=HTTPException(400, {"code": "MISSING_CUSTOMER_ID"}))

    report = await reconcile_captures(db, provider, settings=GST, completer=completer, now=_Clock(NOW))

    assert report.refund_due == 2
    assert dict(await _rows(db, "SELECT payment_id, status FROM razorpay_captures")) == {
        "pay_nobody": "REFUND_DUE",
        "pay_unhired": "REFUND_DUE",
        "pay_hired": "COMPLETED",
    }
    assert dict(await _rows(db, "SELECT payment_id, last_error FROM razorpay_captures WHERE status = 'REFUND_DUE'")) == {
        "pay_nobody": "MISSING_CUSTOMER_ID",
        "pay_unhired": "HIRE_NOT_COMPLETED",
    }


@pytest.mark.asyncio
async def test_a_failed_renewal_starts_grace_once_and_a_replay_never_extends_it(db) -> None:
    clock = _Clock(START + timedelta(days=31))
    async with db() as session:
        first = await renewals.start_grace_once(session, TENANT, RELATIONSHIP, now=clock, lifecycle_factory=_fake_lifecycle)
    clock.at = START + timedelta(days=32)
    async with db() as session:
        second = await renewals.start_grace_once(session, TENANT, RELATIONSHIP, now=clock, lifecycle_factory=_fake_lifecycle)
        period = await PeriodStore(session).current(TENANT, RELATIONSHIP, clock.at)

    assert (first, second) == ("GRACE_STARTED", "NOT_APPLICABLE")
    assert period.grace_until == START + timedelta(days=34)


@pytest.mark.asyncio
async def test_the_renewal_sweep_opens_one_order_then_starts_grace_when_it_stays_unpaid(db, monkeypatch) -> None:
    monkeypatch.setattr(renewals.mirror, "wallet_authority", lambda *_args: "WALLET")
    monkeypatch.setattr(renewals, "payer_of", AsyncMock(return_value=CUSTOMER))
    orders = AsyncMock()
    orders.create_order.return_value = {"id": "order_renewal_1"}
    clock = _Clock(START + timedelta(days=28))

    async def sweep():
        return await renewals.run_renewal_sweep(db, orders, now=clock, lifecycle_factory=_fake_lifecycle)

    assert (await sweep()) == renewals.RenewalSweepReport(1, 0, 0)
    assert (await sweep()) == renewals.RenewalSweepReport(0, 0, 0)
    orders.create_order.assert_awaited_once_with(
        30_000,
        {
            "checkout_kind": "RENEWAL",
            "customer_id": str(CUSTOMER),
            "tenant_id": str(TENANT),
            "relationship_id": str(RELATIONSHIP),
        },
    )
    clock.at = START + timedelta(days=31)
    assert (await sweep()) == renewals.RenewalSweepReport(0, 0, 1)
    assert (await sweep()) == renewals.RenewalSweepReport(0, 0, 0)
    assert (await _rows(db, "SELECT status, order_id FROM renewal_collections")) == [("GRACE_STARTED", "order_renewal_1")]


@pytest.mark.asyncio
async def test_the_invoice_is_readable_with_the_right_tax_heads_and_escapes_the_customer_name(db) -> None:
    clock = _Clock(datetime(2027, 1, 15, 6, 0, tzinfo=timezone.utc))
    supplier = supplier_from(GST.GST_LEGAL_NAME, GST.GST_GSTIN, GST.GST_ADDRESS, "27")
    async with db() as session:
        await session.execute(
            text(
                "INSERT INTO business.billing_profiles (customer_id, tenant_id, legal_name, gstin, state_code, address, "
                "updated_at) VALUES (:customer, :tenant, '<b>Acme</b>', NULL, '29', 'Bengaluru', :at)"
            ).bindparams(bindparam("at", type_=DateTime(timezone=True))),
            {"customer": str(CUSTOMER), "tenant": str(TENANT), "at": clock.at},
        )
        service = TaxDocumentService(session, supplier, now=clock)
        inter = await service.issue_for_payment(payment_reference="pay_a", amount_paise=59_000, payer_customer_id=CUSTOMER)
        intra = await service.issue_for_payment(payment_reference="pay_b", amount_paise=59_000, payer_customer_id=UUID(int=9))

    assert (inter.document_number, intra.document_number) == ("WAOOAW/2026-27/000001", "WAOOAW/2026-27/000002")
    html = render_html(inter)
    assert "WAOOAW/2026-27/000001" in html and "<th>IGST</th>" in html and "&lt;b&gt;Acme&lt;/b&gt;" in html
    assert "<b>Acme</b>" not in html and "590.00" in html
    assert "<th>CGST</th><th>SGST</th>" in render_html(intra)
