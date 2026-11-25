# Implements: work-contracts/WC-172-safe-to-charge-real-customers.md WC172-R011
# Constitutional basis: C-007, C-023, C-059, C-088
"""Independent reconciliation of the books against the payment provider.

For a window of time the provider's captured payments and refunds are compared with WAOOAW's tax invoices and credit
notes. A payment with no invoice, an invoice with no payment, an amount that differs, a refund with no credit note and
a credit note with no refund are each recorded as one open discrepancy. An open discrepancy blocks every new charge
(see ``payment.money_gate``) until the Founder resolves it with evidence. The reconciler never edits an invoice: a
correction is a new document.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Final, Protocol
from uuid import UUID, uuid4

from sqlalchemy import DateTime, bindparam, text
from sqlalchemy.ext.asyncio import AsyncSession

from wallet.entity_models import as_utc

logger = logging.getLogger(__name__)
_TS = DateTime(timezone=True)

PAYMENT_WITHOUT_INVOICE: Final = "PAYMENT_WITHOUT_INVOICE"
INVOICE_WITHOUT_PAYMENT: Final = "INVOICE_WITHOUT_PAYMENT"
AMOUNT_MISMATCH: Final = "AMOUNT_MISMATCH"
REFUND_WITHOUT_CREDIT_NOTE: Final = "REFUND_WITHOUT_CREDIT_NOTE"
CREDIT_NOTE_WITHOUT_REFUND: Final = "CREDIT_NOTE_WITHOUT_REFUND"


class MoneyReconciliationError(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class ProviderPayment:
    payment_id: str
    amount_paise: int
    captured: bool


@dataclass(frozen=True)
class ProviderRefund:
    refund_id: str
    payment_id: str
    amount_paise: int
    adjustment_id: str | None


class ProviderLedger(Protocol):
    async def payments(self, start: datetime, end: datetime) -> Sequence[ProviderPayment]: ...

    async def refunds(self, start: datetime, end: datetime) -> Sequence[ProviderRefund]: ...


@dataclass(frozen=True)
class ReconciliationReport:
    checked_payments: int
    checked_refunds: int
    opened: int

    @property
    def clean(self) -> bool:
        return self.opened == 0


def _stmt(sql: str, *datetime_params: str):
    statement = text(sql)
    if datetime_params:
        statement = statement.bindparams(*[bindparam(name, type_=_TS) for name in datetime_params])
    return statement


async def _record(
    session: AsyncSession, now: datetime, kind: str, reference: str, expected_paise: int, observed_paise: int
) -> int:
    result = await session.execute(
        _stmt(
            """
            INSERT INTO business.money_discrepancies
            (discrepancy_id, kind, reference, expected_paise, observed_paise, detected_at)
            VALUES (:id, :kind, :reference, :expected, :observed, :now)
            ON CONFLICT DO NOTHING
            """,
            "now",
        ),
        {
            "id": str(uuid4()), "kind": kind, "reference": reference, "expected": expected_paise,
            "observed": observed_paise, "now": as_utc(now),
        },
    )
    return int(result.rowcount or 0)


class MoneyReconciler:
    def __init__(
        self, session: AsyncSession, provider: ProviderLedger, *, now: Callable[[], datetime] | None = None
    ) -> None:
        self._session = session
        self._provider = provider
        self._now = now or (lambda: datetime.now(timezone.utc))

    async def reconcile(self, start: datetime, end: datetime) -> ReconciliationReport:
        now = self._now()
        opened = 0
        # An invoice is issued shortly after its payment, so the provider is asked one day further back.
        provider_start = start - timedelta(days=1)
        payments = [item for item in await self._provider.payments(provider_start, end) if item.captured]
        refunds = list(await self._provider.refunds(provider_start, end))
        invoices = await self._documents("TAX_INVOICE", "PAYMENT", start, end)
        notes = await self._documents("CREDIT_NOTE", "ADJUSTMENT", start, end)
        seen_payments = {item.payment_id: item for item in payments}
        for payment in payments:
            invoice = invoices.get(payment.payment_id)
            if invoice is None:
                invoice = await self._document("TAX_INVOICE", "PAYMENT", payment.payment_id)
            if invoice is None:
                opened += await _record(self._session, now, PAYMENT_WITHOUT_INVOICE, payment.payment_id, payment.amount_paise, 0)
            elif invoice != payment.amount_paise:
                opened += await _record(self._session, now, AMOUNT_MISMATCH, payment.payment_id, payment.amount_paise, invoice)
        for reference, total in invoices.items():
            if reference not in seen_payments:
                opened += await _record(self._session, now, INVOICE_WITHOUT_PAYMENT, reference, total, 0)
        refunded: set[str] = set()
        for refund in refunds:
            key = refund.adjustment_id or refund.refund_id
            refunded.add(key)
            note = notes.get(key)
            if note is None:
                note = await self._document("CREDIT_NOTE", "ADJUSTMENT", key)
            if note is None:
                opened += await _record(self._session, now, REFUND_WITHOUT_CREDIT_NOTE, key, refund.amount_paise, 0)
            elif note != refund.amount_paise:
                opened += await _record(self._session, now, AMOUNT_MISMATCH, key, refund.amount_paise, note)
        for key, total in await self._refund_credit_notes(start, end):
            if key not in refunded:
                opened += await _record(self._session, now, CREDIT_NOTE_WITHOUT_REFUND, key, 0, total)
        if opened:
            logger.error("money_reconciliation discrepancies=%s window=%s..%s", opened, start, end)
        return ReconciliationReport(len(payments), len(refunds), opened)

    async def _documents(self, kind: str, source_kind: str, start: datetime, end: datetime) -> Mapping[str, int]:
        rows = (
            await self._session.execute(
                _stmt(
                    """
                    SELECT source_reference, total_paise FROM business.tax_documents
                    WHERE document_kind = :kind AND source_kind = :source_kind
                      AND issued_at >= :start AND issued_at < :end
                    """,
                    "start",
                    "end",
                ),
                {"kind": kind, "source_kind": source_kind, "start": as_utc(start), "end": as_utc(end)},
            )
        ).all()
        return {str(row[0]): int(row[1]) for row in rows}

    async def _document(self, kind: str, source_kind: str, reference: str) -> int | None:
        row = (
            await self._session.execute(
                text(
                    "SELECT total_paise FROM business.tax_documents WHERE document_kind = :kind "
                    "AND source_kind = :source_kind AND source_reference = :reference"
                ),
                {"kind": kind, "source_kind": source_kind, "reference": reference},
            )
        ).first()
        return None if row is None else int(row[0])

    async def _refund_credit_notes(self, start: datetime, end: datetime) -> list[tuple[str, int]]:
        """Credit notes issued for provider refunds (a pause credit has no refund to match)."""
        rows = (
            await self._session.execute(
                _stmt(
                    """
                    SELECT d.source_reference, d.total_paise FROM business.tax_documents d
                    JOIN business.billing_adjustments a ON CAST(a.adjustment_id AS TEXT) = d.source_reference
                    WHERE d.document_kind = 'CREDIT_NOTE' AND a.adjustment_kind = 'FEE_REFUND'
                      AND d.issued_at >= :start AND d.issued_at < :end
                    """,
                    "start",
                    "end",
                ),
                {"start": as_utc(start), "end": as_utc(end)},
            )
        ).all()
        return [(str(row[0]), int(row[1])) for row in rows]


async def list_discrepancies(session: AsyncSession, *, open_only: bool = True) -> list[dict[str, Any]]:
    rows = (
        await session.execute(
            text(
                "SELECT discrepancy_id, kind, reference, expected_paise, observed_paise, detected_at, resolved_at, "
                "resolved_by, resolution_evidence_id FROM business.money_discrepancies "
                + ("WHERE resolved_at IS NULL " if open_only else "")
                + "ORDER BY detected_at DESC LIMIT 200"
            )
        )
    ).mappings().all()
    return [
        {
            "discrepancyId": str(row["discrepancy_id"]), "kind": row["kind"], "reference": row["reference"],
            "expectedPaise": int(row["expected_paise"]), "observedPaise": int(row["observed_paise"]),
            "detectedAt": as_utc(row["detected_at"]).isoformat(),
            "resolvedAt": None if row["resolved_at"] is None else as_utc(row["resolved_at"]).isoformat(),
            "resolvedBy": row["resolved_by"],
            "resolutionEvidenceId": None if row["resolution_evidence_id"] is None else str(row["resolution_evidence_id"]),
        }
        for row in rows
    ]


async def resolve_discrepancy(
    session: AsyncSession, discrepancy_id: UUID, actor: str, evidence_id: UUID, now: datetime
) -> None:
    """Only the Founder, with evidence, clears a discrepancy; a later clean run never clears an earlier one."""
    if evidence_id == UUID(int=0) or not actor:
        raise MoneyReconciliationError("MONEY_RESOLUTION_EVIDENCE_REQUIRED")
    result = await session.execute(
        _stmt(
            """
            UPDATE business.money_discrepancies
            SET resolved_at = :now, resolved_by = :actor, resolution_evidence_id = :evidence
            WHERE discrepancy_id = :id AND resolved_at IS NULL
            """,
            "now",
        ),
        {"now": as_utc(now), "actor": actor, "evidence": str(evidence_id), "id": str(discrepancy_id)},
    )
    if not result.rowcount:
        raise MoneyReconciliationError("MONEY_DISCREPANCY_NOT_OPEN")


class RazorpayProviderLedger:
    """The provider side of the reconciliation, read from Razorpay's payments and refunds lists."""

    def __init__(self, client: Any) -> None:
        self._client = client

    async def payments(self, start: datetime, end: datetime) -> list[ProviderPayment]:
        items = await self._client.list_collection("payments", int(as_utc(start).timestamp()), int(as_utc(end).timestamp()))
        return [
            ProviderPayment(str(item["id"]), int(item["amount"]), item.get("status") == "captured") for item in items
        ]

    async def refunds(self, start: datetime, end: datetime) -> list[ProviderRefund]:
        items = await self._client.list_collection("refunds", int(as_utc(start).timestamp()), int(as_utc(end).timestamp()))
        return [
            ProviderRefund(
                str(item["id"]), str(item.get("payment_id", "")), int(item["amount"]),
                (item.get("notes") or {}).get("adjustment_id") if isinstance(item.get("notes"), dict) else None,
            )
            for item in items
        ]
