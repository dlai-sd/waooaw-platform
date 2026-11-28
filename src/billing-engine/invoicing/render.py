# Implements: work-contracts/WC-176-customer-journeys-registration-trial-hire-and-pages.md WC176-R017
# Constitutional basis: C-023, C-059, C-063
"""A tax invoice or credit note a customer can read: the stored document, laid out, with every value escaped."""

from __future__ import annotations

from html import escape

from invoicing.service import CREDIT_NOTE, TaxDocument


def rupees(paise: int) -> str:
    return f"{paise // 100}.{paise % 100:02d}"


def render_html(document: TaxDocument) -> str:
    title = "Credit Note" if document.document_kind == CREDIT_NOTE else "Tax Invoice"
    supplier, bill_to = document.supplier, document.bill_to
    intra = document.supply_type == "INTRA_STATE"
    rows = "".join(
        "<tr>"
        f"<td>{escape(str(line['description']))}</td><td>{escape(str(line['sacCode']))}</td>"
        f"<td>{rupees(int(line['taxablePaise']))}</td>"
        + (
            f"<td>{rupees(int(line['cgstPaise']))}</td><td>{rupees(int(line['sgstPaise']))}</td>"
            if intra
            else f"<td>{rupees(int(line['igstPaise']))}</td>"
        )
        + f"<td>{rupees(int(line['totalPaise']))}</td></tr>"
        for line in document.lines
    )
    tax_heads = "<th>CGST</th><th>SGST</th>" if intra else "<th>IGST</th>"
    gstin = bill_to.get("gstin")
    return (
        f"<article><h1>{title} {escape(document.document_number)}</h1>"
        f"<p>Date: {document.issued_at.date().isoformat()}</p>"
        f"<h2>Supplier</h2><p>{escape(str(supplier['legalName']))}<br>GSTIN {escape(str(supplier['gstin']))}"
        f"<br>{escape(str(supplier['address']))}</p>"
        f"<h2>Bill to</h2><p>{escape(str(bill_to.get('name', '')))}"
        + (f"<br>GSTIN {escape(str(gstin))}" if gstin else "")
        + (f"<br>{escape(str(bill_to['address']))}" if bill_to.get("address") else "")
        + f"</p><p>Place of supply: state code {escape(document.place_of_supply)}</p>"
        f"<table><thead><tr><th>Description</th><th>SAC</th><th>Taxable value (INR)</th>{tax_heads}"
        f"<th>Total (INR)</th></tr></thead><tbody>{rows}</tbody></table>"
        f"<p>Total {rupees(document.total_paise)} INR, inclusive of GST.</p></article>"
    )
