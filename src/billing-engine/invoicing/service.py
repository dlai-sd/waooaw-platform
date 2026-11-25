# Implements: work-contracts/WC-172-safe-to-charge-real-customers.md WC172-R006, WC172-R007
# Implements: adr/ADR-022-payment-processing-razorpay-india.md section 5 (GST invoices and credit notes)
# Constitutional basis: C-007, C-038, C-059, C-088
"""GST tax invoices and credit notes.

Every captured payment has one tax invoice and every refund or credit one credit note, numbered without gaps per
series and financial year, with WAOOAW's GST identity, the payer, the funder when there is one, the place of supply
and an exact tax split. A document is immutable: a correction is a new credit note followed by a new invoice. A
replay of the same source returns the document already issued and never a second one.

Numbers are taken from a counter row that is locked by the transaction that also inserts the document, so a
rolled-back issue gives its number back and no gap can appear. The caller owns the transaction.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Final
from uuid import NAMESPACE_URL, UUID, uuid5

from sqlalchemy import DateTime, bindparam, text
from sqlalchemy.ext.asyncio import AsyncSession

from invoicing.identity import DEFAULT_RATE_PERCENT, SupplierIdentity, TaxIdentityNotConfigured
from invoicing.tax import TaxSplit, digest_of, document_number, fiscal_year_of, split_inclusive, sum_splits
from wallet.entity_models import as_utc

logger = logging.getLogger(__name__)

_TS = DateTime(timezone=True)
INVOICE: Final = "TAX_INVOICE"
CREDIT_NOTE: Final = "CREDIT_NOTE"
_SERIES: Final = {INVOICE: "INV", CREDIT_NOTE: "CN"}

PAYER_UNKNOWN: Final = "PAYER_UNKNOWN"
FUNDER_NOT_ACCEPTED: Final = "FUNDER_NOT_ACCEPTED"
FUNDER_IS_PAYER: Final = "FUNDER_IS_PAYER"
AMOUNT_INVALID: Final = "TAX_DOCUMENT_AMOUNT_INVALID"
SOURCE_CONFLICT: Final = "TAX_DOCUMENT_SOURCE_CONFLICT"
ORIGINAL_NOT_FOUND: Final = "ORIGINAL_INVOICE_NOT_FOUND"
CREDIT_EXCEEDS_INVOICE: Final = "CREDIT_EXCEEDS_INVOICE"


class TaxDocumentError(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class InvoiceLine:
    description: str
    amount_paise: int


@dataclass(frozen=True)
class TaxDocument:
    document_id: UUID
    document_kind: str
    document_number: str
    fiscal_year: str
    sequence_no: int
    tenant_id: UUID | None
    relationship_id: UUID | None
    payer_customer_id: UUID
    funder_customer_id: UUID | None
    source_kind: str
    source_reference: str
    original_document_id: UUID | None
    issued_at: datetime
    supplier: Mapping[str, Any]
    bill_to: Mapping[str, Any]
    place_of_supply: str
    supply_type: str
    lines: Sequence[Mapping[str, Any]]
    split: TaxSplit
    body_digest: str
    replayed: bool = False

    @property
    def total_paise(self) -> int:
        return self.split.total_paise

    def as_public(self) -> dict[str, Any]:
        return {
            "documentId": str(self.document_id),
            "documentKind": self.document_kind,
            "documentNumber": self.document_number,
            "issuedAt": self.issued_at.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
            "supplier": dict(self.supplier),
            "billTo": dict(self.bill_to),
            "payerCustomerId": str(self.payer_customer_id),
            "funderCustomerId": None if self.funder_customer_id is None else str(self.funder_customer_id),
            "originalDocumentId": None if self.original_document_id is None else str(self.original_document_id),
            "placeOfSupply": self.place_of_supply,
            "supplyType": self.supply_type,
            "lines": [dict(line) for line in self.lines],
            "taxablePaise": self.split.taxable_paise,
            "cgstPaise": self.split.cgst_paise,
            "sgstPaise": self.split.sgst_paise,
            "igstPaise": self.split.igst_paise,
            "totalPaise": self.total_paise,
            "currency": "INR",
            "bodyDigest": self.body_digest,
        }


def _stmt(sql: str, *datetime_params: str):
    statement = text(sql)
    if datetime_params:
        statement = statement.bindparams(*[bindparam(name, type_=_TS) for name in datetime_params])
    return statement


def _body(
    *,
    kind: str,
    number: str,
    issued_at: datetime,
    supplier: Mapping[str, Any],
    bill_to: Mapping[str, Any],
    payer: UUID,
    funder: UUID | None,
    original: UUID | None,
    place: str,
    supply_type: str,
    lines: Sequence[Mapping[str, Any]],
    split: TaxSplit,
) -> dict[str, Any]:
    return {
        "kind": kind,
        "number": number,
        "issuedAt": as_utc(issued_at).isoformat(),
        "supplier": dict(supplier),
        "billTo": dict(bill_to),
        "payer": str(payer),
        "funder": None if funder is None else str(funder),
        "original": None if original is None else str(original),
        "placeOfSupply": place,
        "supplyType": supply_type,
        "lines": [dict(line) for line in lines],
        "taxable": split.taxable_paise,
        "cgst": split.cgst_paise,
        "sgst": split.sgst_paise,
        "igst": split.igst_paise,
        "total": split.total_paise,
    }


class TaxDocumentService:
    def __init__(
        self,
        session: AsyncSession,
        supplier: SupplierIdentity | None,
        *,
        now: Callable[[], datetime] | None = None,
        rate_percent: int = DEFAULT_RATE_PERCENT,
    ) -> None:
        self._session = session
        self._supplier = supplier
        self._now = now or (lambda: datetime.now(timezone.utc))
        self._rate = rate_percent

    # ----------------------------------------------------------------------------- parties

    async def _profile(self, customer_id: UUID) -> Mapping[str, Any] | None:
        row = (
            await self._session.execute(
                text(
                    "SELECT legal_name, gstin, state_code, address FROM business.billing_profiles "
                    "WHERE customer_id = :customer"
                ),
                {"customer": str(customer_id)},
            )
        ).mappings().first()
        return None if row is None else dict(row)

    async def _require_funder(self, tenant_id: UUID | None, relationship_id: UUID | None, payer: UUID, funder: UUID) -> None:
        """A funder needs a billing profile and their own acceptance for this relationship (D5, C-088)."""
        if funder == payer:
            raise TaxDocumentError(FUNDER_IS_PAYER)
        if await self._profile(funder) is None or relationship_id is None or tenant_id is None:
            raise TaxDocumentError(FUNDER_NOT_ACCEPTED)
        accepted = (
            await self._session.execute(
                text(
                    "SELECT 1 FROM business.funder_acceptances WHERE tenant_id = :tenant "
                    "AND relationship_id = :relationship AND funder_customer_id = :funder"
                ),
                {"tenant": str(tenant_id), "relationship": str(relationship_id), "funder": str(funder)},
            )
        ).first()
        if accepted is None:
            raise TaxDocumentError(FUNDER_NOT_ACCEPTED)

    # ----------------------------------------------------------------------------- numbering and storage

    async def _next_sequence(self, series: str, fiscal_year: str) -> int:
        row = (
            await self._session.execute(
                text(
                    """
                    INSERT INTO business.tax_document_counters AS counter (series, fiscal_year, last_number)
                    VALUES (:series, :fiscal_year, 1)
                    ON CONFLICT (series, fiscal_year) DO UPDATE SET last_number = counter.last_number + 1
                    RETURNING last_number
                    """
                ),
                {"series": series, "fiscal_year": fiscal_year},
            )
        ).first()
        return int(row[0])

    async def _insert(self, document: TaxDocument) -> None:
        await self._session.execute(
            _stmt(
                """
                INSERT INTO business.tax_documents
                (document_id, document_kind, series, fiscal_year, sequence_no, document_number, tenant_id,
                 relationship_id, payer_customer_id, funder_customer_id, source_kind, source_reference,
                 original_document_id, issued_at, supplier, bill_to, place_of_supply, supply_type, lines,
                 taxable_paise, cgst_paise, sgst_paise, igst_paise, total_paise, currency, body_digest)
                VALUES (:id, :kind, :series, :fy, :sequence, :number, :tenant, :relationship, :payer, :funder,
                        :source_kind, :source_reference, :original, :issued_at, :supplier, :bill_to, :place,
                        :supply_type, :lines, :taxable, :cgst, :sgst, :igst, :total, 'INR', :digest)
                """,
                "issued_at",
            ),
            {
                "id": str(document.document_id),
                "kind": document.document_kind,
                "series": _SERIES[document.document_kind],
                "fy": document.fiscal_year,
                "sequence": document.sequence_no,
                "number": document.document_number,
                "tenant": None if document.tenant_id is None else str(document.tenant_id),
                "relationship": None if document.relationship_id is None else str(document.relationship_id),
                "payer": str(document.payer_customer_id),
                "funder": None if document.funder_customer_id is None else str(document.funder_customer_id),
                "source_kind": document.source_kind,
                "source_reference": document.source_reference,
                "original": None if document.original_document_id is None else str(document.original_document_id),
                "issued_at": as_utc(document.issued_at),
                "supplier": json.dumps(dict(document.supplier), sort_keys=True),
                "bill_to": json.dumps(dict(document.bill_to), sort_keys=True),
                "place": document.place_of_supply,
                "supply_type": document.supply_type,
                "lines": json.dumps([dict(line) for line in document.lines], sort_keys=True),
                "taxable": document.split.taxable_paise,
                "cgst": document.split.cgst_paise,
                "sgst": document.split.sgst_paise,
                "igst": document.split.igst_paise,
                "total": document.total_paise,
                "digest": document.body_digest,
            },
        )

    @staticmethod
    def _load(row: Mapping[str, Any], *, replayed: bool = False) -> TaxDocument:
        def parsed(value: Any) -> Any:
            return json.loads(value) if isinstance(value, (str, bytes)) else value

        def optional(value: Any) -> UUID | None:
            return None if value in (None, "") else UUID(str(value))

        return TaxDocument(
            document_id=UUID(str(row["document_id"])),
            document_kind=str(row["document_kind"]),
            document_number=str(row["document_number"]),
            fiscal_year=str(row["fiscal_year"]),
            sequence_no=int(row["sequence_no"]),
            tenant_id=optional(row["tenant_id"]),
            relationship_id=optional(row["relationship_id"]),
            payer_customer_id=UUID(str(row["payer_customer_id"])),
            funder_customer_id=optional(row["funder_customer_id"]),
            source_kind=str(row["source_kind"]),
            source_reference=str(row["source_reference"]),
            original_document_id=optional(row["original_document_id"]),
            issued_at=as_utc(row["issued_at"]),
            supplier=parsed(row["supplier"]),
            bill_to=parsed(row["bill_to"]),
            place_of_supply=str(row["place_of_supply"]),
            supply_type=str(row["supply_type"]),
            lines=parsed(row["lines"]),
            split=TaxSplit(
                int(row["taxable_paise"]), int(row["cgst_paise"]), int(row["sgst_paise"]), int(row["igst_paise"])
            ),
            body_digest=str(row["body_digest"]),
            replayed=replayed,
        )

    async def _by_source(self, kind: str, source_kind: str, source_reference: str) -> TaxDocument | None:
        row = (
            await self._session.execute(
                text(
                    "SELECT * FROM business.tax_documents WHERE document_kind = :kind "
                    "AND source_kind = :source_kind AND source_reference = :reference"
                ),
                {"kind": kind, "source_kind": source_kind, "reference": source_reference},
            )
        ).mappings().first()
        return None if row is None else self._load(row, replayed=True)

    def _require_supplier(self) -> SupplierIdentity:
        if self._supplier is None:
            raise TaxIdentityNotConfigured("The GST identity is not configured.")
        return self._supplier

    # ----------------------------------------------------------------------------- issuing

    async def issue_for_payment(
        self,
        *,
        payment_reference: str,
        amount_paise: int,
        payer_customer_id: UUID | None,
        tenant_id: UUID | None = None,
        relationship_id: UUID | None = None,
        funder_customer_id: UUID | None = None,
        lines: Sequence[InvoiceLine] | None = None,
    ) -> TaxDocument:
        """One tax invoice for one captured payment. Refused when the payer is unknown (C-088)."""
        supplier = self._require_supplier()
        if payer_customer_id is None or payer_customer_id == UUID(int=0):
            raise TaxDocumentError(PAYER_UNKNOWN)
        chosen = list(lines or [InvoiceLine("WAOOAW digital professional subscription", amount_paise)])
        if amount_paise <= 0 or any(line.amount_paise <= 0 for line in chosen) or sum(
            line.amount_paise for line in chosen
        ) != amount_paise:
            raise TaxDocumentError(AMOUNT_INVALID)
        existing = await self._by_source(INVOICE, "PAYMENT", payment_reference)
        if existing is not None:
            if existing.total_paise != amount_paise or existing.payer_customer_id != payer_customer_id:
                raise TaxDocumentError(SOURCE_CONFLICT)
            return existing
        if funder_customer_id is not None:
            await self._require_funder(tenant_id, relationship_id, payer_customer_id, funder_customer_id)
        profile = await self._profile(payer_customer_id)
        bill_to: dict[str, Any] = (
            {"name": profile["legal_name"], "gstin": profile["gstin"], "address": profile["address"],
             "stateCode": profile["state_code"], "source": "BILLING_PROFILE"}
            if profile is not None
            # No profile: the place of supply is the supplier's state, and the document says so.
            else {"name": "Customer", "gstin": None, "address": None, "stateCode": supplier.state_code,
                  "source": "NO_BILLING_PROFILE"}
        )
        place = str(bill_to["stateCode"])
        intra = place == supplier.state_code
        priced = [
            {"description": line.description, "sacCode": supplier.sac_code, "totalPaise": line.amount_paise,
             **_line_split(split_inclusive(line.amount_paise, self._rate, intra))}
            for line in chosen
        ]
        split = sum_splits([split_inclusive(line.amount_paise, self._rate, intra) for line in chosen])
        issued_at = as_utc(self._now())
        document = await self._build_and_store(
            INVOICE, supplier, issued_at, tenant_id, relationship_id, payer_customer_id, funder_customer_id,
            "PAYMENT", payment_reference, None, bill_to, place, intra, priced, split,
        )
        return document

    async def issue_credit_note(
        self,
        *,
        source_reference: str,
        original_payment_reference: str,
        amount_paise: int,
    ) -> TaxDocument:
        """One credit note for a refund or credit, tied to the invoice of the payment it returns money from."""
        supplier = self._require_supplier()
        if amount_paise <= 0:
            raise TaxDocumentError(AMOUNT_INVALID)
        existing = await self._by_source(CREDIT_NOTE, "ADJUSTMENT", source_reference)
        if existing is not None:
            if existing.total_paise != amount_paise:
                raise TaxDocumentError(SOURCE_CONFLICT)
            return existing
        original = await self._by_source(INVOICE, "PAYMENT", original_payment_reference)
        if original is None:
            raise TaxDocumentError(ORIGINAL_NOT_FOUND)
        credited = (
            await self._session.execute(
                text(
                    "SELECT COALESCE(SUM(total_paise), 0) FROM business.tax_documents "
                    "WHERE original_document_id = :original AND document_kind = 'CREDIT_NOTE'"
                ),
                {"original": str(original.document_id)},
            )
        ).scalar_one()
        if int(credited) + amount_paise > original.total_paise:
            raise TaxDocumentError(CREDIT_EXCEEDS_INVOICE)
        intra = original.supply_type == "INTRA_STATE"
        split = split_inclusive(amount_paise, self._rate, intra)
        lines = [
            {"description": f"Credit against {original.document_number}", "sacCode": supplier.sac_code,
             "totalPaise": amount_paise, **_line_split(split)}
        ]
        return await self._build_and_store(
            CREDIT_NOTE, supplier, as_utc(self._now()), original.tenant_id, original.relationship_id,
            original.payer_customer_id, original.funder_customer_id, "ADJUSTMENT", source_reference,
            original.document_id, original.bill_to, original.place_of_supply, intra, lines, split,
        )

    async def _build_and_store(
        self,
        kind: str,
        supplier: SupplierIdentity,
        issued_at: datetime,
        tenant_id: UUID | None,
        relationship_id: UUID | None,
        payer: UUID,
        funder: UUID | None,
        source_kind: str,
        source_reference: str,
        original: UUID | None,
        bill_to: Mapping[str, Any],
        place: str,
        intra: bool,
        lines: Sequence[Mapping[str, Any]],
        split: TaxSplit,
    ) -> TaxDocument:
        series = _SERIES[kind]
        fiscal_year = fiscal_year_of(issued_at)
        sequence = await self._next_sequence(series, fiscal_year)
        number = document_number(supplier.series_prefix, series, fiscal_year, sequence)
        supply_type = "INTRA_STATE" if intra else "INTER_STATE"
        document = TaxDocument(
            document_id=uuid5(NAMESPACE_URL, f"waooaw:tax-document:{kind}:{source_kind}:{source_reference}"),
            document_kind=kind,
            document_number=number,
            fiscal_year=fiscal_year,
            sequence_no=sequence,
            tenant_id=tenant_id,
            relationship_id=relationship_id,
            payer_customer_id=payer,
            funder_customer_id=funder,
            source_kind=source_kind,
            source_reference=source_reference,
            original_document_id=original,
            issued_at=issued_at,
            supplier=supplier.as_document(),
            bill_to=bill_to,
            place_of_supply=place,
            supply_type=supply_type,
            lines=lines,
            split=split,
            body_digest=digest_of(
                _body(
                    kind=kind, number=number, issued_at=issued_at, supplier=supplier.as_document(),
                    bill_to=bill_to, payer=payer, funder=funder, original=original, place=place,
                    supply_type=supply_type, lines=lines, split=split,
                )
            ),
        )
        await self._insert(document)
        return document

    # ----------------------------------------------------------------------------- retrieval and proof

    async def get(self, document_id: UUID, *, tenant_id: UUID | None = None) -> TaxDocument | None:
        sql = "SELECT * FROM business.tax_documents WHERE document_id = :id"
        params: dict[str, Any] = {"id": str(document_id)}
        if tenant_id is not None:
            sql += " AND tenant_id = :tenant"
            params["tenant"] = str(tenant_id)
        row = (await self._session.execute(text(sql), params)).mappings().first()
        return None if row is None else self._load(row)

    async def list_documents(
        self,
        *,
        tenant_id: UUID | None = None,
        payer_customer_id: UUID | None = None,
        relationship_id: UUID | None = None,
        limit: int = 50,
    ) -> list[TaxDocument]:
        clauses, params = ["1 = 1"], {"limit": max(1, min(limit, 200))}
        for column, value in (
            ("tenant_id", tenant_id), ("payer_customer_id", payer_customer_id), ("relationship_id", relationship_id)
        ):
            if value is not None:
                clauses.append(f"{column} = :{column}")
                params[column] = str(value)
        rows = (
            await self._session.execute(
                text(
                    f"SELECT * FROM business.tax_documents WHERE {' AND '.join(clauses)} "
                    "ORDER BY fiscal_year DESC, series, sequence_no DESC LIMIT :limit"
                ),
                params,
            )
        ).mappings().all()
        return [self._load(row) for row in rows]


def _line_split(split: TaxSplit) -> dict[str, int]:
    return {
        "taxablePaise": split.taxable_paise,
        "cgstPaise": split.cgst_paise,
        "sgstPaise": split.sgst_paise,
        "igstPaise": split.igst_paise,
    }


def recompute_digest(document: TaxDocument) -> str:
    """Re-derive the digest from the stored content: equal to ``body_digest`` when nothing changed."""
    return digest_of(
        _body(
            kind=document.document_kind, number=document.document_number, issued_at=document.issued_at,
            supplier=document.supplier, bill_to=document.bill_to, payer=document.payer_customer_id,
            funder=document.funder_customer_id, original=document.original_document_id,
            place=document.place_of_supply, supply_type=document.supply_type, lines=document.lines,
            split=document.split,
        )
    )
