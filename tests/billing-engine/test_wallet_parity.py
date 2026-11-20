# Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C4-03
# Constitutional basis: C-059, C-088, C-089, C-063
"""Shadow mirroring of the component allowance tables into the Wallet, and their parity (C4-03).

The SQLite twin cannot run ``OfferingAllowanceService.reserve`` (it locks rows with FOR UPDATE), so
these tests drive the mirror and the service's mirror hook directly over hand-written allowance rows;
the full reserve, settle, release path under SHADOW is covered in test_offering_usage_postgres.py.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from sqlalchemy import text

from meter.allowance_service import AllowanceDenied, OfferingAllowanceService
from wallet import metrics as wallet_metrics
from wallet import mirror as mirror_module
from wallet import parity as parity_module
from wallet.entity_models import WalletError
from wallet.ledger import WalletLedger
from wallet.mirror import WalletMirror, wallet_authority, wallet_overrun_tolerance
from wallet.parity import compute_parity, report_parity

T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
TENANT = UUID("11111111-1111-4111-8111-111111111111")
OTHER_TENANT = UUID("22222222-2222-4222-8222-222222222222")
CUSTOMER = UUID("33333333-3333-4333-8333-333333333333")
RELATIONSHIP = UUID("44444444-4444-4444-8444-444444444444")
ALLOCATION_A = UUID("a1000000-0000-4000-8000-000000000001")
ALLOCATION_B = UUID("a1000000-0000-4000-8000-000000000002")

ALLOWANCE_SQLITE_DDL = (
    """CREATE TABLE business.relationship_commercial_authorities (
        tenant_id TEXT NOT NULL, relationship_id TEXT NOT NULL, authority_kind TEXT NOT NULL,
        PRIMARY KEY (tenant_id, relationship_id)
    )""",
    """CREATE TABLE business.offering_component_allocations (
        allocation_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, relationship_id TEXT NOT NULL,
        component_id TEXT NOT NULL, period_start TIMESTAMP NOT NULL, period_end TIMESTAMP NOT NULL,
        granted_units INTEGER NOT NULL, authority_evidence_id TEXT NOT NULL
    )""",
    """CREATE TABLE business.offering_component_reservations (
        reservation_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, customer_id TEXT NOT NULL,
        relationship_id TEXT NOT NULL, allocation_id TEXT NOT NULL, component_id TEXT NOT NULL,
        professional_type TEXT NOT NULL, professional_version TEXT NOT NULL,
        invocation_id TEXT NOT NULL, owner_evidence_id TEXT NOT NULL, rate_version TEXT NOT NULL,
        marked_up_unit_cost_paise INTEGER NOT NULL, reserved_marked_up_paise INTEGER NOT NULL,
        actual_marked_up_paise INTEGER, state TEXT NOT NULL, settlement_evidence_id TEXT,
        non_dispatch_evidence_id TEXT
    )""",
)


class _Clock:
    def __init__(self, value: datetime = T0) -> None:
        self.value = value

    def __call__(self) -> datetime:
        return self.value


def _ts(value: datetime) -> str:
    return value.isoformat()


@pytest_asyncio.fixture
async def factory(wallet_db):
    async with wallet_db.kw["bind"].begin() as connection:
        for statement in ALLOWANCE_SQLITE_DDL:
            await connection.execute(text(statement))
    return wallet_db


async def _authority(session, kind: str = "ACCEPTED_OFFERING", tenant: UUID = TENANT) -> None:
    await session.execute(
        text(
            "INSERT INTO business.relationship_commercial_authorities "
            "VALUES (:tenant, :relationship, :kind)"
        ),
        {"tenant": str(tenant), "relationship": str(RELATIONSHIP), "kind": kind},
    )


async def _allocation(
    session,
    allocation: UUID,
    component: str,
    *,
    granted: int = 10,
    start: datetime = T0 - timedelta(days=1),
    end: datetime = T0 + timedelta(days=30),
    tenant: UUID = TENANT,
) -> None:
    await session.execute(
        text(
            "INSERT INTO business.offering_component_allocations VALUES "
            "(:allocation, :tenant, :relationship, :component, :start, :end, :granted, :evidence)"
        ),
        {
            "allocation": str(allocation),
            "tenant": str(tenant),
            "relationship": str(RELATIONSHIP),
            "component": component,
            "start": _ts(start),
            "end": _ts(end),
            "granted": granted,
            "evidence": str(uuid4()),
        },
    )


async def _reservation(
    session,
    allocation: UUID,
    component: str,
    *,
    state: str = "RESERVED",
    reserved: int = 100,
    actual: int | None = None,
    unit: int = 50,
    tenant: UUID = TENANT,
) -> UUID:
    reservation = uuid4()
    await session.execute(
        text(
            "INSERT INTO business.offering_component_reservations VALUES "
            "(:reservation, :tenant, :customer, :relationship, :allocation, :component, "
            " 'marketing', '1.0.0', :invocation, :owner, 'rate-1', :unit, :reserved, :actual, "
            " :state, :settlement, :non_dispatch)"
        ),
        {
            "reservation": str(reservation),
            "tenant": str(tenant),
            "customer": str(CUSTOMER),
            "relationship": str(RELATIONSHIP),
            "allocation": str(allocation),
            "component": component,
            "invocation": str(uuid4()),
            "owner": str(uuid4()),
            "unit": unit,
            "reserved": reserved,
            "actual": actual,
            "state": state,
            "settlement": str(uuid4()) if state == "SETTLED" else None,
            "non_dispatch": str(uuid4()) if state == "RELEASED" else None,
        },
    )
    return reservation


async def _set_state(session, reservation: UUID, state: str, actual: int | None) -> None:
    await session.execute(
        text(
            "UPDATE business.offering_component_reservations SET state = :state, "
            "actual_marked_up_paise = :actual, settlement_evidence_id = :settlement, "
            "non_dispatch_evidence_id = :non_dispatch WHERE reservation_id = :reservation"
        ),
        {
            "state": state,
            "actual": actual,
            "settlement": str(uuid4()) if state == "SETTLED" else None,
            "non_dispatch": str(uuid4()) if state == "RELEASED" else None,
            "reservation": str(reservation),
        },
    )


async def _count(session, table: str) -> int:
    return (await session.execute(text(f"SELECT COUNT(*) FROM business.{table}"))).scalar_one()


def _mirror(session) -> WalletMirror:
    return WalletMirror(session, ledger=WalletLedger(session, now=_Clock()))


async def test_parity_is_zero_after_a_reserve_settle_and_release_sequence(factory) -> None:
    async with factory() as session:
        await _authority(session)
        await _allocation(session, ALLOCATION_A, "llm_cloud", granted=10)
        await _allocation(session, ALLOCATION_B, "voice", granted=4)
        held = await _reservation(session, ALLOCATION_A, "llm_cloud", reserved=100)
        settled = await _reservation(
            session, ALLOCATION_A, "llm_cloud", state="SETTLED", reserved=150, actual=120
        )
        released = await _reservation(session, ALLOCATION_B, "voice", state="RELEASED", reserved=100)
        zero_actual = await _reservation(
            session, ALLOCATION_B, "voice", state="SETTLED", reserved=50, actual=0
        )
        mirror = _mirror(session)
        for reservation in (held, settled, released, zero_actual):
            await mirror.sync_reservation(TENANT, reservation)

        report = await compute_parity(session, TENANT, now=T0)

        assert report.clean
        assert report.compared == 2
        by_component = {row.component_id: row for row in report.rows}
        assert (by_component["llm_cloud"].allowance_open_paise, by_component["llm_cloud"].wallet_open_paise) == (100, 100)
        assert (by_component["llm_cloud"].allowance_settled_paise, by_component["llm_cloud"].wallet_settled_paise) == (120, 120)
        assert by_component["voice"].wallet_open_paise == 0
        assert by_component["voice"].wallet_settled_paise == 0
        account = await WalletLedger(session, now=_Clock()).find_account(
            TENANT, "SUBSCRIPTION", relationship_id=RELATIONSHIP
        )
        assert account is not None and account.owner_ref == CUSTOMER
        balance = await WalletLedger(session, now=_Clock()).balance(account, T0)
        assert (balance.credited_paise, balance.reserved_paise, balance.settled_paise) == (700, 100, 120)
        assert balance.available_paise == 480


async def test_a_dropped_mirror_write_is_detected_and_repaired_by_a_later_sync(factory) -> None:
    async with factory() as session:
        await _authority(session)
        await _allocation(session, ALLOCATION_A, "llm_cloud")
        await _allocation(session, ALLOCATION_B, "voice")
        mirrored = await _reservation(session, ALLOCATION_A, "llm_cloud", reserved=100)
        dropped = await _reservation(session, ALLOCATION_B, "voice", reserved=100)
        mirror = _mirror(session)
        await mirror.sync_reservation(TENANT, mirrored)
        await mirror.sync_reservation(TENANT, dropped)
        # the allowance settles but the settle mirror write never happens
        await _set_state(session, dropped, "SETTLED", 80)

        report = await compute_parity(session, TENANT, now=T0)

        assert not report.clean
        assert [row.component_id for row in report.differences] == ["voice"]
        difference = report.differences[0]
        assert (difference.open_difference_paise, difference.settled_difference_paise) == (-100, 80)

        await mirror.sync_reservation(TENANT, dropped)

        assert (await compute_parity(session, TENANT, now=T0)).clean


async def test_a_reservation_with_no_wallet_rows_at_all_is_a_difference(factory) -> None:
    async with factory() as session:
        await _authority(session)
        await _allocation(session, ALLOCATION_A, "llm_cloud")
        await _reservation(session, ALLOCATION_A, "llm_cloud", reserved=100)

        report = await compute_parity(session, TENANT, RELATIONSHIP, now=T0)

        assert [(r.allowance_open_paise, r.wallet_open_paise) for r in report.differences] == [(100, 0)]
        assert (await compute_parity(session, OTHER_TENANT, now=T0)).compared == 0


async def test_report_parity_raises_a_metric_and_a_log_line_without_raising(
    factory, monkeypatch, caplog
) -> None:
    counted: list[tuple[str, int]] = []
    monkeypatch.setattr(
        parity_module.metrics, "count", lambda name, amount=1, **_: counted.append((name, amount))
    )
    async with factory() as session:
        await _authority(session)
        await _allocation(session, ALLOCATION_A, "llm_cloud")
        await _reservation(session, ALLOCATION_A, "llm_cloud", reserved=100)

        with caplog.at_level(logging.WARNING, logger=parity_module.logger.name):
            report = await report_parity(session, TENANT)
        clean_report = await report_parity(session, OTHER_TENANT)

    assert not report.clean
    assert counted == [("wbe.wallet.parity_difference", 1)]
    assert "wallet parity differs" in caplog.text
    assert str(CUSTOMER) not in caplog.text
    assert clean_report.clean


async def test_a_replayed_sync_writes_each_wallet_row_exactly_once(factory) -> None:
    async with factory() as session:
        await _authority(session)
        await _allocation(session, ALLOCATION_A, "llm_cloud")
        reservation = await _reservation(session, ALLOCATION_A, "llm_cloud", reserved=100)
        mirror = _mirror(session)

        for _ in range(3):
            await mirror.sync_reservation(TENANT, reservation)
        await _set_state(session, reservation, "SETTLED", 90)
        for _ in range(3):
            outcome = await mirror.sync_reservation(TENANT, reservation)

        assert outcome.wallet_state == "SETTLED"
        assert await _count(session, "wallet_lots") == 1
        assert await _count(session, "wallet_reservations") == 1
        kinds = (
            await session.execute(
                text("SELECT entry_kind, COUNT(*) FROM business.wallet_entries GROUP BY entry_kind")
            )
        ).all()
        assert dict(kinds) == {"CREDIT": 1, "RESERVE": 1, "SETTLE": 1}


async def test_the_allocation_lot_is_credited_once_even_when_the_rate_changes(factory) -> None:
    async with factory() as session:
        await _authority(session)
        await _allocation(session, ALLOCATION_A, "llm_cloud", granted=10)
        first = await _reservation(session, ALLOCATION_A, "llm_cloud", reserved=100, unit=50)
        second = await _reservation(session, ALLOCATION_A, "llm_cloud", reserved=60, unit=60)
        mirror = _mirror(session)

        await mirror.sync_reservation(TENANT, first)
        await mirror.sync_reservation(TENANT, second)

        credited = (await session.execute(text("SELECT credited_paise, source_ref FROM business.wallet_lots"))).all()
        assert credited == [(500, f"allocation:{ALLOCATION_A}")]


async def test_a_zero_priced_component_is_skipped_and_writes_nothing(factory) -> None:
    async with factory() as session:
        await _authority(session)
        await _allocation(session, ALLOCATION_A, "free_component")
        reservation = await _reservation(
            session, ALLOCATION_A, "free_component", reserved=0, unit=0
        )

        outcome = await _mirror(session).sync_reservation(TENANT, reservation)

        assert outcome.skipped and outcome.detail == "ZERO_PRICED"
        assert await _count(session, "wallet_accounts") == 0


async def test_an_unknown_allowance_reservation_is_refused(factory) -> None:
    async with factory() as session:
        with pytest.raises(WalletError) as refusal:
            await _mirror(session).sync_reservation(TENANT, uuid4())
        assert refusal.value.code == "WALLET_RESERVATION_UNKNOWN"


async def test_a_trial_relationship_mirrors_to_the_trial_account_with_its_own_lot(factory) -> None:
    async with factory() as session:
        await _authority(session, "TRIAL")
        await _allocation(session, ALLOCATION_A, "llm_cloud", granted=4)
        reservation = await _reservation(session, ALLOCATION_A, "llm_cloud", reserved=100)

        await _mirror(session).sync_reservation(TENANT, reservation)

        account = await WalletLedger(session, now=_Clock()).find_account(
            TENANT, "TRIAL", relationship_id=RELATIONSHIP
        )
        assert account is not None
        assert (account.owner_kind, account.agent_type, account.agent_version) == ("PLATFORM", "marketing", "1.0.0")
        lot = (await session.execute(text("SELECT lot_kind, source_kind, credited_paise FROM business.wallet_lots"))).one()
        assert tuple(lot) == ("GRANT", "TRIAL_GRANT", 200)


async def test_a_trial_grant_credited_at_trial_start_is_not_doubled_by_the_mirror(factory) -> None:
    async with factory() as session:
        await _authority(session, "TRIAL")
        await _allocation(session, ALLOCATION_A, "llm_cloud", granted=4)
        reservation = await _reservation(session, ALLOCATION_A, "llm_cloud", reserved=100)
        ledger = WalletLedger(session, now=_Clock())
        account = await ledger.open_account(
            TENANT, "TRIAL", relationship_id=RELATIONSHIP, agent_type="marketing", agent_version="1.0.0"
        )
        await ledger.credit(
            account, "GRANT", 1000, T0 - timedelta(days=1), T0 + timedelta(days=14),
            f"trial:{uuid4()}", {}, uuid4(), source_kind="TRIAL_GRANT",
        )

        await WalletMirror(session, ledger=ledger).sync_reservation(TENANT, reservation)

        refs = (await session.execute(text("SELECT source_ref FROM business.wallet_lots"))).scalars().all()
        assert len(refs) == 1 and refs[0].startswith("trial:")
        assert (await ledger.balance(account, T0)).reserved_paise == 100


async def test_settings_are_read_defensively() -> None:
    assert wallet_authority(SimpleNamespace(WALLET_AUTHORITY="SHADOW")) == "SHADOW"
    assert wallet_authority(SimpleNamespace(WALLET_AUTHORITY="WALLET")) == "WALLET"
    assert wallet_authority(SimpleNamespace(WALLET_AUTHORITY="OTHER")) == "LEGACY"
    assert wallet_authority(SimpleNamespace()) == "LEGACY"
    assert wallet_overrun_tolerance(SimpleNamespace(WALLET_OVERRUN_TOLERANCE_PAISE=7)) == 7
    assert wallet_overrun_tolerance(SimpleNamespace(WALLET_OVERRUN_TOLERANCE_PAISE=-1)) == 0
    assert wallet_overrun_tolerance(SimpleNamespace()) == 0


def _wall_period() -> tuple[datetime, datetime]:
    now = datetime.now(timezone.utc)
    return now - timedelta(days=1), now + timedelta(days=30)


async def _hook_reservation(session, *, granted: int = 10, reserved: int = 100) -> UUID:
    start, end = _wall_period()
    await _authority(session)
    await _allocation(session, ALLOCATION_A, "llm_cloud", granted=granted, start=start, end=end)
    return await _reservation(session, ALLOCATION_A, "llm_cloud", reserved=reserved)


async def _wallet_rows(session) -> int:
    return sum([await _count(session, t) for t in ("wallet_accounts", "wallet_lots", "wallet_reservations", "wallet_entries")])


async def test_legacy_makes_zero_wallet_writes(factory) -> None:
    service = OfferingAllowanceService(factory, SimpleNamespace(WALLET_AUTHORITY="LEGACY"))
    async with factory() as session:
        reservation = await _hook_reservation(session)
        for operation in ("reserve", "settle", "release", "reconcile"):
            await service._mirror(session, TENANT, reservation, operation)

        assert await _wallet_rows(session) == 0


async def test_default_settings_without_the_mode_behave_as_legacy(factory) -> None:
    service = OfferingAllowanceService(factory, SimpleNamespace())
    async with factory() as session:
        reservation = await _hook_reservation(session)
        await service._mirror(session, TENANT, reservation, "reserve")

        assert await _wallet_rows(session) == 0


async def test_shadow_mirrors_every_operation_including_replays_exactly_once(factory) -> None:
    service = OfferingAllowanceService(factory, SimpleNamespace(WALLET_AUTHORITY="SHADOW"))
    async with factory() as session:
        reservation = await _hook_reservation(session)

        await service._mirror(session, TENANT, reservation, "reserve")
        await service._mirror(session, TENANT, reservation, "reserve")
        await _set_state(session, reservation, "SETTLED", 70)
        await service._mirror(session, TENANT, reservation, "settle")
        await service._mirror(session, TENANT, reservation, "settle")
        await service._mirror(session, TENANT, reservation, "reconcile")

        kinds = (
            await session.execute(
                text("SELECT entry_kind, COUNT(*) FROM business.wallet_entries GROUP BY entry_kind")
            )
        ).all()
        assert dict(kinds) == {"CREDIT": 1, "RESERVE": 1, "SETTLE": 1}
        assert (await compute_parity(session, TENANT)).clean


async def test_shadow_never_fails_the_customer_path_and_counts_the_failure(
    factory, monkeypatch, caplog
) -> None:
    counted: list[tuple[str, dict[str, str]]] = []
    monkeypatch.setattr(
        wallet_metrics, "count", lambda name, amount=1, **attrs: counted.append((name, attrs))
    )

    async def broken(self, tenant_id, reservation_id):
        raise WalletError("WALLET_INSUFFICIENT", "BALANCE")

    monkeypatch.setattr(mirror_module.WalletMirror, "sync_reservation", broken)
    service = OfferingAllowanceService(factory, SimpleNamespace(WALLET_AUTHORITY="SHADOW"))
    async with factory() as session:
        reservation = await _hook_reservation(session)
        with caplog.at_level(logging.WARNING):
            await service._mirror(session, TENANT, reservation, "settle")

        assert await _count(session, "offering_component_reservations") == 1
    assert counted == [("wbe.wallet.shadow_failure", {"operation": "settle"})]
    assert "WALLET_INSUFFICIENT" in caplog.text


async def test_a_failed_shadow_mirror_leaves_no_partial_wallet_rows(factory) -> None:
    service = OfferingAllowanceService(factory, SimpleNamespace(WALLET_AUTHORITY="SHADOW"))
    async with factory() as session:
        # 1 unit at 50 paise funds the lot with 50 paise, so holding 100 paise is refused
        reservation = await _hook_reservation(session, granted=1, reserved=100)

        await service._mirror(session, TENANT, reservation, "reserve")

        assert await _count(session, "wallet_reservations") == 0
        assert await _count(session, "wallet_lots") == 0
        assert await _count(session, "wallet_entries") == 0


async def test_wallet_mode_denies_when_the_wallet_cannot_cover_the_hold(factory) -> None:
    service = OfferingAllowanceService(factory, SimpleNamespace(WALLET_AUTHORITY="WALLET"))
    async with factory() as session:
        reservation = await _hook_reservation(session, granted=1, reserved=100)

        with pytest.raises(AllowanceDenied) as denied:
            await service._mirror(session, TENANT, reservation, "reserve")

        assert str(denied.value) == "ALLOWANCE_EXHAUSTED"


async def test_wallet_mode_makes_the_wallet_hold_the_authoritative_reservation(factory) -> None:
    service = OfferingAllowanceService(factory, SimpleNamespace(WALLET_AUTHORITY="WALLET"))
    async with factory() as session:
        reservation = await _hook_reservation(session)

        await service._mirror(session, TENANT, reservation, "reserve")

        held = (await session.execute(text("SELECT reserved_paise, state FROM business.wallet_reservations"))).one()
        assert tuple(held) == (100, "RESERVED")
