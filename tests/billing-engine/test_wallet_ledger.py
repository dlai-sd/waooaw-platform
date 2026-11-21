# Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C4-02
# Constitutional basis: C-059, C-088, C-089, C-063
"""WalletLedger arithmetic, lot order, idempotency, unknown outcomes, expiry and overrun fencing."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from sqlalchemy import text

from wallet.entity_models import ReservationIdentity, WalletError
from wallet.ledger import WalletLedger

T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
TENANT = UUID("11111111-1111-4111-8111-111111111111")
OTHER_TENANT = UUID("22222222-2222-4222-8222-222222222222")
CUSTOMER = UUID("33333333-3333-4333-8333-333333333333")
RELATIONSHIP = UUID("44444444-4444-4444-8444-444444444444")


class _Clock:
    def __init__(self) -> None:
        self.value = T0

    def __call__(self) -> datetime:
        return self.value

    def advance(self, **delta: int) -> None:
        self.value += timedelta(**delta)


@pytest_asyncio.fixture
async def env(wallet_db):
    clock = _Clock()
    async with wallet_db() as session:
        ledger = WalletLedger(session, overrun_tolerance_paise=10, now=clock)
        account = await ledger.open_account(
            TENANT, "SUBSCRIPTION", owner_ref=CUSTOMER, relationship_id=RELATIONSHIP
        )
        yield SimpleNamespace(session=session, ledger=ledger, clock=clock, account=account)


async def _credit(env, paise: int, *, days: int = 30, key: UUID | None = None, kind="PERIOD_CREDIT"):
    return await env.ledger.credit(
        env.account,
        kind,
        paise,
        T0,
        T0 + timedelta(days=days),
        "package:period-1",
        {"package": "p1"},
        key or uuid4(),
    )


async def _reserve(env, paise: int, key: UUID | None = None, *, component: str = "llm_cloud"):
    return await env.ledger.reserve(
        env.account,
        component,
        paise,
        T0 + timedelta(hours=1),
        ReservationIdentity(pinned_versions={"rate": "r1"}),
        key or uuid4(),
    )


async def _available(env, at: datetime = T0) -> int:
    return (await env.ledger.balance(env.account, at)).available_paise


async def _count(env, table: str) -> int:
    return (await env.session.execute(text(f"SELECT COUNT(*) FROM business.{table}"))).scalar_one()


async def test_open_account_is_idempotent_by_account_key(env):
    again = await env.ledger.open_account(
        TENANT, "SUBSCRIPTION", owner_ref=CUSTOMER, relationship_id=RELATIONSHIP
    )
    other = await env.ledger.open_account(
        TENANT, "SUBSCRIPTION", owner_ref=CUSTOMER, relationship_id=uuid4()
    )
    assert again.account_id == env.account.account_id
    assert other.account_id != env.account.account_id
    assert await _count(env, "wallet_accounts") == 2
    assert env.account.owner_kind == "CUSTOMER" and env.account.scope_kind == "RELATIONSHIP"


async def test_open_account_refuses_incoherent_shapes(env):
    with pytest.raises(WalletError) as missing_owner:
        await env.ledger.open_account(TENANT, "SUBSCRIPTION", relationship_id=uuid4())
    with pytest.raises(WalletError) as platform_with_owner:
        await env.ledger.open_account(TENANT, "ACQUISITION", owner_ref=CUSTOMER)
    with pytest.raises(WalletError) as no_environment:
        await env.ledger.open_account(TENANT, "SIMULATION")
    assert {missing_owner.value.code, platform_with_owner.value.code, no_environment.value.code} == {
        "WALLET_ACCOUNT_INVALID"
    }


async def test_credit_reserve_settle_release_arithmetic(env):
    await _credit(env, 1000)
    assert await _available(env) == 1000
    first = await _reserve(env, 400)
    second = await _reserve(env, 300)
    assert first.state == "RESERVED" and await _available(env) == 300
    settled = await env.ledger.settle(TENANT, first.reservation_id, 350, uuid4())
    assert settled.state == "SETTLED" and settled.actual_paise == 350 and settled.overrun_paise == 0
    assert await _available(env) == 1000 - 300 - 350
    released = await env.ledger.release(TENANT, second.reservation_id, uuid4())
    assert released.state == "RELEASED" and released.actual_paise == 0
    balance = await env.ledger.balance(env.account, T0)
    assert (balance.credited_paise, balance.reserved_paise, balance.settled_paise) == (1000, 0, 350)
    assert balance.available_paise == 650


async def test_reserve_uses_lot_with_oldest_expiry_first(env):
    long_lot = await _credit(env, 500, days=60)
    short_lot = await _credit(env, 500, days=10)
    first = await _reserve(env, 100)
    second = await _reserve(env, 450)
    assert first.lot_id == short_lot.lot_id
    assert second.lot_id == long_lot.lot_id


async def test_insufficient_balance_and_fragmented_lots_are_refused(env):
    await _credit(env, 60)
    await _credit(env, 60)
    with pytest.raises(WalletError) as insufficient:
        await _reserve(env, 101)
    assert insufficient.value.code == "WALLET_INSUFFICIENT"
    assert await _count(env, "wallet_reservations") == 0
    assert (await _reserve(env, 60)).state == "RESERVED"


async def test_exact_replays_return_stored_receipts_and_changed_replays_conflict(env):
    credit_key, reserve_key = uuid4(), uuid4()
    lot = await _credit(env, 1000, key=credit_key)
    credit_replay = await _credit(env, 1000, key=credit_key)
    assert credit_replay.replayed and credit_replay.lot_id == lot.lot_id
    with pytest.raises(WalletError) as changed_credit:
        await _credit(env, 999, key=credit_key)
    assert await _count(env, "wallet_lots") == 1

    reserved = await _reserve(env, 400, reserve_key)
    replay = await _reserve(env, 400, reserve_key)
    assert replay.replayed and replay.lot_id == reserved.lot_id
    assert await _available(env) == 600 and await _count(env, "wallet_reservations") == 1
    with pytest.raises(WalletError) as changed_reserve:
        await _reserve(env, 401, reserve_key)

    evidence = uuid4()
    await env.ledger.settle(TENANT, reserved.reservation_id, 300, evidence)
    settle_replay = await env.ledger.settle(TENANT, reserved.reservation_id, 300, evidence)
    assert settle_replay.replayed and settle_replay.actual_paise == 300
    with pytest.raises(WalletError) as changed_settle:
        await env.ledger.settle(TENANT, reserved.reservation_id, 301, evidence)
    with pytest.raises(WalletError) as release_after_settle:
        await env.ledger.release(TENANT, reserved.reservation_id, uuid4())
    assert {
        changed_credit.value.code,
        changed_reserve.value.code,
        changed_settle.value.code,
        release_after_settle.value.code,
    } == {"WALLET_IDEMPOTENCY_CONFLICT"}
    assert await _count(env, "wallet_entries") == 3


async def test_release_replay_returns_stored_receipt_and_never_double_returns(env):
    await _credit(env, 1000)
    reserved = await _reserve(env, 400)
    evidence = uuid4()
    await env.ledger.release(TENANT, reserved.reservation_id, evidence)
    replay = await env.ledger.release(TENANT, reserved.reservation_id, evidence)
    assert replay.replayed and replay.state == "RELEASED"
    assert await _available(env) == 1000
    with pytest.raises(WalletError) as conflict:
        await env.ledger.release(TENANT, reserved.reservation_id, uuid4())
    assert conflict.value.code == "WALLET_IDEMPOTENCY_CONFLICT"


async def test_unknown_outcome_retains_the_reservation(env):
    await _credit(env, 1000)
    reserved = await _reserve(env, 400)
    unknown = await env.ledger.mark_unknown(TENANT, reserved.reservation_id)
    assert unknown.state == "UNKNOWN" and not unknown.replayed
    assert await _available(env) == 600
    assert (await env.ledger.mark_unknown(TENANT, reserved.reservation_id)).replayed
    settled = await env.ledger.settle(TENANT, reserved.reservation_id, 400, uuid4())
    assert settled.state == "SETTLED" and await _available(env) == 600


async def test_expiry_writes_entries_and_never_moves_value_to_another_period(env):
    await _credit(env, 1000, days=10)
    reserved = await _reserve(env, 200)
    await env.ledger.settle(TENANT, reserved.reservation_id, 200, uuid4())
    env.clock.advance(days=5)
    assert await env.ledger.expire(env.account, T0 + timedelta(days=5)) == []

    after = T0 + timedelta(days=11)
    receipts = await env.ledger.expire(env.account, after)
    assert [receipt.expired_paise for receipt in receipts] == [800]
    assert await env.ledger.expire(env.account, after) == []
    assert await _available(env, after) == 0

    next_period = await env.ledger.credit(
        env.account, "PERIOD_CREDIT", 500, after, after + timedelta(days=30),
        "package:period-2", {"package": "p1"}, uuid4(),
    )
    assert next_period.credited_paise == 500
    assert await _available(env, after) == 500
    expired = (
        await env.session.execute(
            text("SELECT COUNT(*) FROM business.wallet_entries WHERE entry_kind = 'EXPIRE'")
        )
    ).scalar_one()
    assert expired == 1


async def test_overrun_beyond_tolerance_fences_admission_until_next_credit(env):
    await _credit(env, 1000)
    env.clock.advance(minutes=1)
    small = await _reserve(env, 100)
    env.clock.advance(minutes=1)
    within = await env.ledger.settle(TENANT, small.reservation_id, 105, uuid4())
    assert within.overrun_paise == 5 and not within.fenced
    env.clock.advance(minutes=1)
    big = await _reserve(env, 100)
    env.clock.advance(minutes=1)
    settled = await env.ledger.settle(TENANT, big.reservation_id, 125, uuid4())
    assert settled.overrun_paise == 25 and settled.fenced
    adjusts = (
        await env.session.execute(
            text(
                "SELECT amount_paise FROM business.wallet_entries "
                "WHERE entry_kind = 'ADJUST' ORDER BY amount_paise"
            )
        )
    ).scalars().all()
    assert adjusts == [5, 25]

    env.clock.advance(minutes=1)
    with pytest.raises(WalletError) as fenced:
        await _reserve(env, 10)
    assert fenced.value.code == "WALLET_INSUFFICIENT" and fenced.value.detail == "OVERRUN_FENCE"

    env.clock.advance(minutes=1)
    await _credit(env, 500)
    env.clock.advance(minutes=1)
    assert (await _reserve(env, 10)).state == "RESERVED"


async def test_reservation_pins_account_class_and_versions_for_later_operations(env):
    await _credit(env, 1000)
    reserved = await env.ledger.reserve(
        env.account, "llm_cloud", 100, T0 + timedelta(hours=1),
        ReservationIdentity(pinned_versions={"rate": "r1", "package": "p1"}), uuid4(),
    )
    stored = await env.ledger.get_reservation(TENANT, reserved.reservation_id)
    settled = await env.ledger.settle(TENANT, reserved.reservation_id, 90, uuid4())
    assert stored.pinned_account_class == "SUBSCRIPTION"
    assert dict(stored.pinned_versions) == {"rate": "r1", "package": "p1"}
    assert settled.pinned_account_class == "SUBSCRIPTION"
    assert dict(settled.pinned_versions) == {"rate": "r1", "package": "p1"}


async def test_other_tenants_cannot_read_or_resolve_the_wallet(env):
    await _credit(env, 1000)
    reserved = await _reserve(env, 100)
    foreign = WalletLedger(env.session, now=env.clock)
    assert await foreign.get_account(OTHER_TENANT, env.account.account_id) is None
    assert await foreign.get_reservation(OTHER_TENANT, reserved.reservation_id) is None
    with pytest.raises(WalletError) as unknown:
        await foreign.settle(OTHER_TENANT, reserved.reservation_id, 50, uuid4())
    assert unknown.value.code == "WALLET_RESERVATION_UNKNOWN"


async def test_settle_requires_a_positive_actual(env):
    await _credit(env, 1000)
    reserved = await _reserve(env, 100)
    with pytest.raises(WalletError) as invalid:
        await env.ledger.settle(TENANT, reserved.reservation_id, 0, uuid4())
    assert invalid.value.code == "WALLET_AMOUNT_INVALID"
