# Implements: work-contracts/WC-172-safe-to-charge-real-customers.md WC172-R006, WC172-R007
# Constitutional basis: C-007, C-038, C-059, C-088
"""GST tax invoices and credit notes: numbering, identity, exact paise, immutability, payer and funder."""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from sqlalchemy import DateTime, bindparam, text

sys.path.insert(0, str(Path(__file__).parent))

from invoicing.identity import TaxIdentityNotConfigured, is_valid_gstin, supplier_from  # noqa: E402
from invoicing.service import InvoiceLine, TaxDocumentError, TaxDocumentService, recompute_digest  # noqa: E402
from invoicing.tax import document_number, fiscal_year_of, split_inclusive  # noqa: E402
from wc136_commercial_ddl import COMMERCIAL_DDL, WC172_DDL, install  # noqa: E402

TENANT = UUID("11111111-1111-4111-8111-111111111111")
RELATIONSHIP = UUID("44444444-4444-4444-8444-444444444444")
PAYER = UUID("22222222-2222-4222-8222-222222222222")
FUNDER = UUID("33333333-3333-4333-8333-333333333333")
SUPPLIER = supplier_from("DLAI Satellite Data (OPC) Pvt Ltd", "27AAKCD8188R1ZH", "Pune, Maharashtra", "27")
JAN = datetime(2027, 1, 15, 6, 0, tzinfo=timezone.utc)


class _Clock:
    def __init__(self, at: datetime) -> None:
        self.at = at

    def __call__(self) -> datetime:
        return self.at


@pytest_asyncio.fixture
async def env(wallet_db):
    async with wallet_db() as session:
        await install(session, WC172_DDL)
        clock = _Clock(JAN)
        yield type("Env", (), {"session": session, "clock": clock, "service": TaxDocumentService(session, SUPPLIER, now=clock)})


async def _profile(env, customer: UUID, state: str, gstin: str | None = None) -> None:
    statement = text(
        "INSERT INTO business.billing_profiles (customer_id, tenant_id, legal_name, gstin, state_code, address, updated_at) "
        "VALUES (:customer, :tenant, :name, :gstin, :state, 'Somewhere', :at)"
    ).bindparams(bindparam("at", type_=DateTime(timezone=True)))
    await env.session.execute(
        statement,
        {"customer": str(customer), "tenant": str(TENANT), "name": f"Customer {state}", "gstin": gstin, "state": state, "at": JAN},
    )


def test_the_gstin_check_character_is_verified_and_an_incomplete_identity_is_refused() -> None:
    assert is_valid_gstin("27AAKCD8188R1ZH")
    assert not is_valid_gstin("27AAKCD8188R1ZA")
    with pytest.raises(TaxIdentityNotConfigured):
        supplier_from("", "27AAKCD8188R1ZH", "Pune", "27")
    with pytest.raises(TaxIdentityNotConfigured):
        supplier_from("WAOOAW", "27AAKCD8188R1ZH", "Pune", "29")


@pytest.mark.parametrize("amount", [1, 2, 3, 99, 100, 118, 119, 1_000, 29_999, 59_000, 1_234_567])
@pytest.mark.parametrize("intra", [True, False])
def test_the_tax_split_always_adds_up_to_the_paise_paid(amount: int, intra: bool) -> None:
    split = split_inclusive(amount, 18, intra)
    assert split.total_paise == amount
    assert split.igst_paise == 0 or not intra
    assert split.total_paise - split.taxable_paise == split.cgst_paise + split.sgst_paise + split.igst_paise
    if intra:
        assert split.sgst_paise - split.cgst_paise in (0, 1)


def test_numbers_follow_the_indian_financial_year_in_ist() -> None:
    assert fiscal_year_of(datetime(2027, 3, 31, 18, 29, tzinfo=timezone.utc)) == "2026-27"
    assert fiscal_year_of(datetime(2027, 3, 31, 18, 30, tzinfo=timezone.utc)) == "2027-28"
    assert document_number("WAOOAW", "INV", "2026-27", 42) == "WAOOAW/2026-27/000042"
    assert document_number("WAOOAW", "CN", "2026-27", 7) == "WAOOAW/CN/2026-27/000007"


@pytest.mark.asyncio
async def test_a_payment_gets_one_numbered_invoice_with_the_gst_identity_and_a_replay_returns_it(env) -> None:
    first = await env.service.issue_for_payment(
        payment_reference="pay_1", amount_paise=59_000, payer_customer_id=PAYER, tenant_id=TENANT,
        relationship_id=RELATIONSHIP,
    )
    again = await env.service.issue_for_payment(
        payment_reference="pay_1", amount_paise=59_000, payer_customer_id=PAYER, tenant_id=TENANT,
        relationship_id=RELATIONSHIP,
    )
    assert first.document_number == "WAOOAW/2026-27/000001" and not first.replayed
    assert again.replayed and again.document_id == first.document_id
    assert first.supplier["gstin"] == "27AAKCD8188R1ZH" and first.supplier["sacCode"] == "9984"
    assert first.total_paise == 59_000 and first.split.taxable_paise == 50_000
    assert recompute_digest(first) == first.body_digest
    count = (await env.session.execute(text("SELECT COUNT(*) FROM business.tax_documents"))).scalar_one()
    assert count == 1


@pytest.mark.asyncio
async def test_numbers_are_gap_free_per_series_and_restart_with_the_financial_year(env) -> None:
    numbers = [
        (await env.service.issue_for_payment(payment_reference=f"pay_{n}", amount_paise=1_000 + n, payer_customer_id=PAYER)).document_number
        for n in range(3)
    ]
    assert numbers == [f"WAOOAW/2026-27/00000{n}" for n in (1, 2, 3)]
    env.clock.at = datetime(2027, 4, 2, tzinfo=timezone.utc)
    later = await env.service.issue_for_payment(payment_reference="pay_new_year", amount_paise=5_000, payer_customer_id=PAYER)
    assert later.document_number == "WAOOAW/2027-28/000001"


@pytest.mark.asyncio
async def test_a_failed_issue_gives_its_number_back_so_no_gap_appears(wallet_db) -> None:
    async with wallet_db() as session:
        await install(session, WC172_DDL)
        service = TaxDocumentService(session, SUPPLIER, now=_Clock(JAN))
        await service.issue_for_payment(payment_reference="pay_a", amount_paise=1_000, payer_customer_id=PAYER)
        await session.commit()
        await session.execute(
            text("UPDATE business.tax_document_counters SET last_number = last_number + 1")
        )
        await session.rollback()
        second = await service.issue_for_payment(payment_reference="pay_b", amount_paise=2_000, payer_customer_id=PAYER)
        assert second.document_number == "WAOOAW/2026-27/000002"


@pytest.mark.asyncio
async def test_issued_numbers_are_unique_and_consecutive(wallet_db) -> None:
    async with wallet_db() as session:
        await install(session, WC172_DDL)
        service = TaxDocumentService(session, SUPPLIER, now=_Clock(JAN))
        issued = []
        for n in range(10):
            issued.append(await service.issue_for_payment(payment_reference=f"pay_{n}", amount_paise=999 + n, payer_customer_id=PAYER))
        assert sorted(item.sequence_no for item in issued) == list(range(1, 11))
        assert len({item.document_number for item in issued}) == 10


@pytest.mark.asyncio
async def test_the_place_of_supply_decides_cgst_sgst_or_igst(env) -> None:
    await _profile(env, PAYER, "29", "29AAAAA0000A1Z5")
    inter = await env.service.issue_for_payment(payment_reference="pay_ka", amount_paise=11_800, payer_customer_id=PAYER)
    assert inter.supply_type == "INTER_STATE" and inter.place_of_supply == "29"
    assert (inter.split.igst_paise, inter.split.cgst_paise, inter.split.sgst_paise) == (1_800, 0, 0)
    assert inter.bill_to["source"] == "BILLING_PROFILE"
    other = UUID("55555555-5555-4555-8555-555555555555")
    intra = await env.service.issue_for_payment(payment_reference="pay_mh", amount_paise=11_800, payer_customer_id=other)
    assert intra.supply_type == "INTRA_STATE" and intra.bill_to["source"] == "NO_BILLING_PROFILE"
    assert (intra.split.cgst_paise, intra.split.sgst_paise, intra.split.igst_paise) == (900, 900, 0)


@pytest.mark.asyncio
async def test_a_charge_with_no_known_payer_is_refused(env) -> None:
    for payer in (None, UUID(int=0)):
        with pytest.raises(TaxDocumentError) as refused:
            await env.service.issue_for_payment(payment_reference="pay_x", amount_paise=1_000, payer_customer_id=payer)
        assert refused.value.code == "PAYER_UNKNOWN"


@pytest.mark.asyncio
async def test_a_funder_needs_a_billing_profile_and_their_own_acceptance(env) -> None:
    kwargs = dict(
        payment_reference="pay_f", amount_paise=11_800, payer_customer_id=PAYER, tenant_id=TENANT,
        relationship_id=RELATIONSHIP, funder_customer_id=FUNDER,
    )
    with pytest.raises(TaxDocumentError) as no_profile:
        await env.service.issue_for_payment(**kwargs)
    assert no_profile.value.code == "FUNDER_NOT_ACCEPTED"
    await _profile(env, FUNDER, "27")
    with pytest.raises(TaxDocumentError) as no_acceptance:
        await env.service.issue_for_payment(**kwargs)
    assert no_acceptance.value.code == "FUNDER_NOT_ACCEPTED"
    statement = text(
        "INSERT INTO business.funder_acceptances (acceptance_id, tenant_id, relationship_id, funder_customer_id, "
        "acceptance_evidence_id, accepted_at) VALUES (:id, :tenant, :relationship, :funder, :evidence, :at)"
    ).bindparams(bindparam("at", type_=DateTime(timezone=True)))
    await env.session.execute(
        statement,
        {"id": str(uuid4()), "tenant": str(TENANT), "relationship": str(RELATIONSHIP), "funder": str(FUNDER),
         "evidence": str(uuid4()), "at": JAN},
    )
    document = await env.service.issue_for_payment(**kwargs)
    assert document.funder_customer_id == FUNDER and document.payer_customer_id == PAYER
    with pytest.raises(TaxDocumentError) as same:
        await env.service.issue_for_payment(**{**kwargs, "payment_reference": "pay_g", "funder_customer_id": PAYER})
    assert same.value.code == "FUNDER_IS_PAYER"


@pytest.mark.asyncio
async def test_lines_must_sum_to_the_payment_and_a_different_amount_for_the_same_payment_conflicts(env) -> None:
    with pytest.raises(TaxDocumentError) as mismatch:
        await env.service.issue_for_payment(
            payment_reference="pay_l", amount_paise=1_000, payer_customer_id=PAYER,
            lines=[InvoiceLine("a", 400), InvoiceLine("b", 500)],
        )
    assert mismatch.value.code == "TAX_DOCUMENT_AMOUNT_INVALID"
    two = await env.service.issue_for_payment(
        payment_reference="pay_l", amount_paise=1_000, payer_customer_id=PAYER,
        lines=[InvoiceLine("a", 400), InvoiceLine("b", 600)],
    )
    assert two.total_paise == 1_000 and len(two.lines) == 2
    with pytest.raises(TaxDocumentError) as conflict:
        await env.service.issue_for_payment(payment_reference="pay_l", amount_paise=2_000, payer_customer_id=PAYER)
    assert conflict.value.code == "TAX_DOCUMENT_SOURCE_CONFLICT"


@pytest.mark.asyncio
async def test_a_credit_note_is_tied_to_its_invoice_numbered_in_its_own_series_and_never_exceeds_it(env) -> None:
    invoice = await env.service.issue_for_payment(
        payment_reference="pay_c", amount_paise=30_000, payer_customer_id=PAYER, tenant_id=TENANT
    )
    note = await env.service.issue_credit_note(
        source_reference="adj-1", original_payment_reference="pay_c", amount_paise=15_000
    )
    assert note.document_number == "WAOOAW/CN/2026-27/000001"
    assert note.original_document_id == invoice.document_id and note.supply_type == invoice.supply_type
    assert note.split.total_paise == 15_000 and recompute_digest(note) == note.body_digest
    replay = await env.service.issue_credit_note(
        source_reference="adj-1", original_payment_reference="pay_c", amount_paise=15_000
    )
    assert replay.document_id == note.document_id
    await env.service.issue_credit_note(source_reference="adj-2", original_payment_reference="pay_c", amount_paise=15_000)
    with pytest.raises(TaxDocumentError) as over:
        await env.service.issue_credit_note(source_reference="adj-3", original_payment_reference="pay_c", amount_paise=1)
    assert over.value.code == "CREDIT_EXCEEDS_INVOICE"
    with pytest.raises(TaxDocumentError) as orphan:
        await env.service.issue_credit_note(source_reference="adj-4", original_payment_reference="pay_none", amount_paise=10)
    assert orphan.value.code == "ORIGINAL_INVOICE_NOT_FOUND"


@pytest.mark.asyncio
async def test_nothing_is_issued_without_the_gst_identity(env) -> None:
    service = TaxDocumentService(env.session, None, now=env.clock)
    with pytest.raises(TaxIdentityNotConfigured):
        await service.issue_for_payment(payment_reference="pay_z", amount_paise=1_000, payer_customer_id=PAYER)


@pytest.mark.asyncio
async def test_documents_are_retrievable_by_tenant_payer_and_relationship_and_a_tenant_cannot_read_anothers(env) -> None:
    mine = await env.service.issue_for_payment(
        payment_reference="pay_m", amount_paise=5_000, payer_customer_id=PAYER, tenant_id=TENANT, relationship_id=RELATIONSHIP
    )
    await env.service.issue_for_payment(
        payment_reference="pay_o", amount_paise=6_000, payer_customer_id=FUNDER, tenant_id=UUID(int=9)
    )
    assert [d.document_id for d in await env.service.list_documents(tenant_id=TENANT)] == [mine.document_id]
    assert len(await env.service.list_documents()) == 2
    assert [d.document_id for d in await env.service.list_documents(payer_customer_id=PAYER)] == [mine.document_id]
    assert (await env.service.get(mine.document_id, tenant_id=TENANT)).document_number == mine.document_number
    assert await env.service.get(mine.document_id, tenant_id=UUID(int=9)) is None


@pytest.mark.asyncio
async def test_the_sweep_issues_one_credit_note_for_a_pause_credit_and_for_a_dispatched_refund(env) -> None:
    from types import SimpleNamespace

    from invoicing.hooks import issue_invoice_safely, issue_pending_credit_notes, supplier_from_settings

    await install(env.session, COMMERCIAL_DDL)

    settings = SimpleNamespace(
        GST_LEGAL_NAME="DLAI Satellite Data (OPC) Pvt Ltd", GST_GSTIN="27AAKCD8188R1ZH", GST_ADDRESS="Pune",
        GST_STATE_CODE="27", GST_SAC_CODE="9984", GST_RATE_PERCENT=18,
    )
    assert supplier_from_settings(settings).gstin == "27AAKCD8188R1ZH"
    assert supplier_from_settings(SimpleNamespace(GST_GSTIN="")) is None
    assert await issue_invoice_safely(
        env.session, settings, payment_reference="pay_s", amount_paise=30_000, payer_customer_id=PAYER,
        tenant_id=TENANT, relationship_id=RELATIONSHIP,
    )
    at = bindparam("at", type_=DateTime(timezone=True))
    insert = text(
        "INSERT INTO business.billing_adjustments (adjustment_id, tenant_id, relationship_id, command_id, adjustment_kind, "
        "amount_paise, payment_reference, status, created_at, updated_at, remaining_paise) VALUES "
        "(:id, :tenant, :relationship, :command, :kind, :amount, :reference, :status, :at, :at, :amount)"
    ).bindparams(at)
    base = {"tenant": str(TENANT), "relationship": str(RELATIONSHIP), "at": JAN}
    await env.session.execute(
        insert, {**base, "id": str(uuid4()), "command": str(uuid4()), "kind": "FEE_CREDIT", "amount": 10_000,
                 "reference": None, "status": "AVAILABLE"},
    )
    await env.session.execute(
        insert, {**base, "id": str(uuid4()), "command": str(uuid4()), "kind": "FEE_REFUND", "amount": 5_000,
                 "reference": "pay_s", "status": "DISPATCHED"},
    )
    await env.session.execute(
        insert, {**base, "id": str(uuid4()), "command": str(uuid4()), "kind": "FEE_REFUND", "amount": 700,
                 "reference": "pay_s", "status": "NOT_PAYABLE"},
    )
    assert await issue_pending_credit_notes(env.session, settings) == 2
    assert await issue_pending_credit_notes(env.session, settings) == 0
    notes = (await env.session.execute(text("SELECT COUNT(*) FROM business.tax_documents WHERE document_kind = 'CREDIT_NOTE'"))).scalar_one()
    assert notes == 2
