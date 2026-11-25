# Implements: work-contracts/WC-172-safe-to-charge-real-customers.md WC172-R006, WC172-R007
# Constitutional basis: C-059, C-088
"""Issue the tax document of a capture, refund or credit without ever undoing the money movement.

A captured payment cannot be un-captured because a document failed to issue, so a failure is logged and left for
the daily reconciliation, which reports every payment without an invoice and every refund without a credit note.
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from invoicing.identity import DEFAULT_RATE_PERCENT, DEFAULT_SAC, SupplierIdentity, TaxIdentityNotConfigured, supplier_from
from invoicing.service import TaxDocument, TaxDocumentError, TaxDocumentService

logger = logging.getLogger(__name__)


def supplier_from_settings(settings: Any) -> SupplierIdentity | None:
    """The configured GST identity, or None while the Founder has not supplied it (decision D6)."""
    values = [
        getattr(settings, name, "")
        for name in ("GST_LEGAL_NAME", "GST_GSTIN", "GST_ADDRESS", "GST_STATE_CODE", "GST_SAC_CODE")
    ]
    if not all(isinstance(value, str) for value in values):
        return None
    name, gstin, address, state, sac = values
    try:
        return supplier_from(name, gstin, address, state, sac or DEFAULT_SAC)
    except TaxIdentityNotConfigured:
        return None


def service_for(session: AsyncSession, settings: Any) -> TaxDocumentService:
    rate = getattr(settings, "GST_RATE_PERCENT", DEFAULT_RATE_PERCENT)
    return TaxDocumentService(
        session, supplier_from_settings(settings), rate_percent=rate if isinstance(rate, int) else DEFAULT_RATE_PERCENT
    )


async def issue_invoice_safely(
    session: AsyncSession, settings: Any, *, payment_reference: str, amount_paise: int | None, payer_customer_id: UUID | None,
    tenant_id: UUID | None = None, relationship_id: UUID | None = None,
) -> TaxDocument | None:
    if not amount_paise or amount_paise <= 0:
        return None
    try:
        document = await service_for(session, settings).issue_for_payment(
            payment_reference=payment_reference,
            amount_paise=amount_paise,
            payer_customer_id=payer_customer_id,
            tenant_id=tenant_id,
            relationship_id=relationship_id,
        )
        await session.commit()
        return document
    except (TaxIdentityNotConfigured, TaxDocumentError) as error:
        await session.rollback()
        logger.warning("tax_invoice not_issued payment=%s reason=%s", payment_reference, getattr(error, "code", "IDENTITY"))
    except Exception:
        await session.rollback()
        logger.exception("tax_invoice failed payment=%s", payment_reference)
    return None


async def issue_credit_note_safely(
    session: AsyncSession, settings: Any, *, adjustment_id: UUID, original_payment_reference: str | None, amount_paise: int
) -> TaxDocument | None:
    if not original_payment_reference:
        logger.warning("credit_note not_issued adjustment=%s reason=NO_ORIGINAL_PAYMENT", adjustment_id)
        return None
    try:
        document = await service_for(session, settings).issue_credit_note(
            source_reference=str(adjustment_id),
            original_payment_reference=original_payment_reference,
            amount_paise=amount_paise,
        )
        await session.commit()
        return document
    except (TaxIdentityNotConfigured, TaxDocumentError) as error:
        await session.rollback()
        logger.warning("credit_note not_issued adjustment=%s reason=%s", adjustment_id, getattr(error, "code", "IDENTITY"))
    except Exception:
        await session.rollback()
        logger.exception("credit_note failed adjustment=%s", adjustment_id)
    return None


async def latest_invoice_payment_of(session: AsyncSession, tenant_id: UUID, relationship_id: UUID) -> str | None:
    """The payment behind a relationship's latest tax invoice, the document a pause credit is raised against."""
    row = (
        await session.execute(
            text(
                """
                SELECT source_reference FROM business.tax_documents
                WHERE tenant_id = :tenant AND relationship_id = :relationship AND document_kind = 'TAX_INVOICE'
                ORDER BY issued_at DESC, sequence_no DESC LIMIT 1
                """
            ),
            {"tenant": str(tenant_id), "relationship": str(relationship_id)},
        )
    ).first()
    return None if row is None else str(row[0])


async def payer_of(session: AsyncSession, tenant_id: UUID, relationship_id: UUID) -> UUID | None:
    """The account holder who paid for a relationship: the customer of its activation payment (D5)."""
    row = (
        await session.execute(
            text(
                """
                SELECT customer_id FROM payment_intents
                WHERE tenant_id = :tenant AND relationship_id = :relationship AND customer_id IS NOT NULL
                ORDER BY activated_at DESC LIMIT 1
                """
            ),
            {"tenant": str(tenant_id), "relationship": str(relationship_id)},
        )
    ).first()
    return None if row is None else UUID(str(row[0]))


async def issue_pending_credit_notes(session: AsyncSession, settings: Any, limit: int = 50) -> int:
    """A credit note for every refund sent to the provider and every pause credit that has none yet.

    Idempotent and self-healing: a refund or credit that was recorded before the GST identity was configured, or whose
    invoice did not exist yet, is picked up by the next sweep.
    """
    rows = (
        await session.execute(
            text(
                """
                SELECT a.adjustment_id, a.tenant_id, a.relationship_id, a.amount_paise, a.adjustment_kind, a.payment_reference
                FROM business.billing_adjustments a
                WHERE ((a.adjustment_kind = 'FEE_REFUND' AND a.status = 'DISPATCHED')
                       OR (a.adjustment_kind = 'FEE_CREDIT' AND a.status IN ('AVAILABLE', 'APPLIED')))
                  AND NOT EXISTS (
                    SELECT 1 FROM business.tax_documents d
                    WHERE d.document_kind = 'CREDIT_NOTE' AND d.source_kind = 'ADJUSTMENT'
                      AND d.source_reference = CAST(a.adjustment_id AS TEXT))
                ORDER BY a.created_at LIMIT :limit
                """
            ),
            {"limit": limit},
        )
    ).mappings().all()
    issued = 0
    for row in rows:
        # A refund returns money from the payment it was dispatched against; a pause credit is raised against the
        # relationship's latest invoice.
        original = (
            row["payment_reference"]
            if row["adjustment_kind"] == "FEE_REFUND"
            else await latest_invoice_payment_of(session, UUID(str(row["tenant_id"])), UUID(str(row["relationship_id"])))
        )
        document = await issue_credit_note_safely(
            session,
            settings,
            adjustment_id=UUID(str(row["adjustment_id"])),
            original_payment_reference=original,
            amount_paise=int(row["amount_paise"]),
        )
        issued += document is not None
    return issued
