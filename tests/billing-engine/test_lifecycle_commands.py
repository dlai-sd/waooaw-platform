# Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C4-10
# Constitutional basis: C-059, C-038, C-088, C-089, C-091, C-063
"""Lifecycle commands: hire credit, pause, resume, terminate, upgrade, downgrade, grace and refund dispatch."""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).parent))

from payment.lifecycle import (  # noqa: E402
    BillingAdjustments,
    LifecycleError,
    LifecycleService,
    PeriodCreditService,
    PeriodStore,
    credit_paid_period,
)
from promotions.coupon_versions import CouponError  # noqa: E402
from wallet.ledger import WalletLedger  # noqa: E402
from wc136_commercial_ddl import install  # noqa: E402
from wc136_commercial_fakes import (  # noqa: E402
    FakePackages,
    FakeRates,
    policy_body,
    policy_source,
    pro,
    starter,
)

START = datetime(2026, 1, 1, tzinfo=timezone.utc)
TENANT = UUID("11111111-1111-4111-8111-111111111111")
CUSTOMER = UUID("22222222-2222-4222-8222-222222222222")
RELATIONSHIP = UUID("44444444-4444-4444-8444-444444444444")
PERIOD_CREDIT_PAISE = 4 * 2 * 50


class _Clock:
    def __init__(self, at: datetime) -> None:
        self.at = at

    def __call__(self) -> datetime:
        return self.at


class _Provider:
    def __init__(self, fail: bool = False) -> None:
        self.fail = fail
        self.calls: list[tuple[str, int]] = []

    async def create_refund(self, payment_id: str, amount_paise: int, notes) -> str:
        if self.fail:
            raise RuntimeError("provider down")
        self.calls.append((payment_id, amount_paise))
        return f"rfnd_{len(self.calls)}"


@pytest_asyncio.fixture
async def env(wallet_db):
    async with wallet_db() as session:
        await install(session)
        clock = _Clock(START)
        await PeriodCreditService(session, rates=FakeRates(), now=clock).start_period(
            TENANT, RELATIONSHIP, CUSTOMER, starter(), START, 30_000, uuid4()
        )
        yield SimpleNamespace(session=session, clock=clock)


def _service(env, policy=None, *, with_policy: bool = True) -> LifecycleService:
    body = (policy or policy_body()) if with_policy else None
    return LifecycleService(
        env.session, rates=FakeRates(), packages=FakePackages(starter(), pro()), policy=policy_source(body), now=env.clock
    )


async def _balance(env):
    ledger = WalletLedger(env.session, now=env.clock)
    account = await ledger.find_account(TENANT, "SUBSCRIPTION", relationship_id=RELATIONSHIP)
    return await ledger.balance(account, env.clock.at)


async def _period(env):
    return await PeriodStore(env.session).current(TENANT, RELATIONSHIP, env.clock.at)


async def _adjustments(env):
    return (
        await env.session.execute(text("SELECT amount_paise, status, payment_reference FROM business.billing_adjustments"))
    ).all()


@pytest.mark.asyncio
async def test_hire_credit_is_sized_from_the_recipes_and_replay_credits_nothing_twice(env) -> None:
    assert (await _balance(env)).credited_paise == PERIOD_CREDIT_PAISE
    await PeriodCreditService(env.session, rates=FakeRates(), now=env.clock).start_period(
        TENANT, RELATIONSHIP, CUSTOMER, starter(), START, 30_000, uuid4()
    )
    assert (await _balance(env)).credited_paise == PERIOD_CREDIT_PAISE
    assert (await _period(env)).status == "ACTIVE"


@pytest.mark.asyncio
async def test_renewal_lapses_the_unspent_credit_instead_of_rolling_it_over(env) -> None:
    env.clock.at = START + timedelta(days=30)
    await PeriodCreditService(env.session, rates=FakeRates(), now=env.clock).start_period(
        TENANT, RELATIONSHIP, CUSTOMER, starter(), env.clock.at, 30_000, uuid4()
    )
    balance = await _balance(env)
    assert balance.credited_paise == PERIOD_CREDIT_PAISE and balance.available_paise == PERIOD_CREDIT_PAISE


@pytest.mark.asyncio
async def test_terminate_on_day_twelve_refunds_the_fee_share_and_never_the_wallet(env) -> None:
    env.clock.at = START + timedelta(days=12)
    outcome = await _service(env).execute("TERMINATE_RELATIONSHIP", TENANT, RELATIONSHIP, uuid4())
    assert (outcome.status, outcome.refund_fee_paise) == ("COMPLETED", 18_000)
    assert (await _period(env)).status == "TERMINATED"
    assert [(row[0], row[1]) for row in await _adjustments(env)] == [(18_000, "NOT_PAYABLE")]
    balance = await _balance(env)
    assert balance.available_paise == 0 and balance.expired_paise == PERIOD_CREDIT_PAISE
    lots = (await env.session.execute(text("SELECT COUNT(*) FROM business.wallet_lots"))).scalar_one()
    assert lots == 1


@pytest.mark.asyncio
async def test_terminate_and_renew_are_blocked_when_no_policy_version_exists(env) -> None:
    for kind in ("TERMINATE_RELATIONSHIP", "RENEW_RELATIONSHIP"):
        outcome = await _service(env, with_policy=False).execute(kind, TENANT, RELATIONSHIP, uuid4())
        assert (outcome.status, outcome.blocked_reason) == ("BLOCKED", "POLICY_ABSENT")
    assert (await _period(env)).status == "ACTIVE"
    assert await _adjustments(env) == []


@pytest.mark.asyncio
async def test_renew_is_pending_until_the_end_of_the_period(env) -> None:
    outcome = await _service(env).execute("RENEW_RELATIONSHIP", TENANT, RELATIONSHIP, uuid4())
    assert (outcome.status, outcome.effective_at) == ("PENDING", START + timedelta(days=30))


@pytest.mark.asyncio
async def test_refund_goes_to_the_provider_against_the_activation_payment(env) -> None:
    await env.session.execute(
        text(
            "INSERT INTO payment_intents (razorpay_payment_id, tenant_id, relationship_id, status, activated_at) "
            "VALUES ('pay_77', :tenant, :relationship, 'ACTIVATED', :at)"
        ),
        {"tenant": str(TENANT), "relationship": str(RELATIONSHIP), "at": START},
    )
    env.clock.at = START + timedelta(days=15)
    await _service(env).execute("TERMINATE_RELATIONSHIP", TENANT, RELATIONSHIP, uuid4())
    provider = _Provider()
    adjustments = BillingAdjustments(env.session, now=env.clock)
    assert await adjustments.dispatch_pending(provider, 10) == 1
    assert provider.calls == [("pay_77", 15_000)]
    assert await adjustments.dispatch_pending(provider, 10) == 0
    assert [row[1] for row in await _adjustments(env)] == ["DISPATCHED"]


@pytest.mark.asyncio
async def test_provider_failure_leaves_the_refund_retryable(env) -> None:
    await env.session.execute(
        text(
            "INSERT INTO payment_intents (razorpay_payment_id, tenant_id, relationship_id, status, activated_at) "
            "VALUES ('pay_78', :tenant, :relationship, 'ACTIVATED', :at)"
        ),
        {"tenant": str(TENANT), "relationship": str(RELATIONSHIP), "at": START},
    )
    await _service(env).execute("TERMINATE_RELATIONSHIP", TENANT, RELATIONSHIP, uuid4())
    adjustments = BillingAdjustments(env.session, now=env.clock)
    assert await adjustments.dispatch_pending(_Provider(fail=True), 10) == 0
    assert [row[1] for row in await _adjustments(env)] == ["FAILED_RETRYABLE"]
    assert await adjustments.dispatch_pending(_Provider(), 10) == 1


@pytest.mark.asyncio
async def test_pausing_every_component_pauses_the_period_and_replay_refunds_once(env) -> None:
    env.clock.at = START + timedelta(days=15)
    command = uuid4()
    first = await _service(env).execute("PAUSE_RELATIONSHIP", TENANT, RELATIONSHIP, command)
    again = await _service(env).execute("PAUSE_RELATIONSHIP", TENANT, RELATIONSHIP, command)
    assert first.refund_fee_paise == 15_000
    assert again.status in {"COMPLETED", "REJECTED"} and not again.refund_fee_paise
    assert (await _period(env)).status == "PAUSED"
    assert [row[0] for row in await _adjustments(env)] == [15_000]


@pytest.mark.asyncio
async def test_pausing_one_component_refunds_its_share_and_keeps_the_period_active(env) -> None:
    env.clock.at = START + timedelta(days=12)
    outcome = await _service(env).execute(
        "PAUSE_RELATIONSHIP", TENANT, RELATIONSHIP, uuid4(), component_ids=["POSTS"]
    )
    period = await _period(env)
    assert outcome.refund_fee_paise == 12_000
    assert period.status == "ACTIVE" and period.paused_component_ids == ("POSTS",)
    unknown = await _service(env).execute(
        "PAUSE_RELATIONSHIP", TENANT, RELATIONSHIP, uuid4(), component_ids=["GHOST"]
    )
    assert (unknown.status, unknown.blocked_reason) == ("REJECTED", "COMPONENT_NOT_IN_PACKAGE")


@pytest.mark.asyncio
async def test_resume_takes_effect_with_the_next_period(env) -> None:
    await _service(env).execute("PAUSE_RELATIONSHIP", TENANT, RELATIONSHIP, uuid4())
    outcome = await _service(env).execute("RESUME_RELATIONSHIP", TENANT, RELATIONSHIP, uuid4())
    assert (outcome.status, outcome.effective_at) == ("PENDING", START + timedelta(days=30))


class _Orders:
    def __init__(self, fail: bool = False) -> None:
        self.fail = fail
        self.calls: list[tuple[int, dict[str, str]]] = []

    async def create_order(self, amount_paise: int, notes: dict[str, str]) -> dict:
        if self.fail:
            raise RuntimeError("provider down")
        self.calls.append((amount_paise, notes))
        return {"id": f"order_{len(self.calls)}"}


def _redeemer(discount_paise: int, refusal: CouponError | None = None):
    calls: list[dict] = []

    async def redeem(session, **kwargs):
        calls.append(kwargs)
        if refusal is not None:
            raise refusal
        price = kwargs["price_incl_gst_paise"]
        return SimpleNamespace(quote=SimpleNamespace(discounted_price_paise=price - discount_paise))

    redeem.calls = calls
    return redeem


async def _renew(env, *, fee: int = 30_000, reference: str = "pay_r1", authority: str = "WALLET", **kwargs):
    return await _service(env).renew_paid(
        TENANT, RELATIONSHIP, CUSTOMER, payment_reference=reference, fee_paid_paise=fee, evidence_id=uuid4(),
        authority=authority, **kwargs,
    )


@pytest.mark.asyncio
async def test_paid_renewal_credits_a_new_lot_lapses_the_old_period_and_replays_once(env) -> None:
    env.clock.at = START + timedelta(days=30)
    renewed = await _renew(env)
    again = await _renew(env)
    assert renewed.period_start == START + timedelta(days=30) and renewed.payment_reference == "pay_r1"
    assert again.period_start == renewed.period_start
    balance = await _balance(env)
    assert balance.credited_paise == PERIOD_CREDIT_PAISE and balance.available_paise == PERIOD_CREDIT_PAISE
    lots = (await env.session.execute(text("SELECT COUNT(*) FROM business.wallet_lots"))).scalar_one()
    assert lots == 2
    assert (await PeriodStore(env.session).starting_at(TENANT, RELATIONSHIP, START)).status == "LAPSED"
    outcome = await _service(env).execute("RENEW_RELATIONSHIP", TENANT, RELATIONSHIP, uuid4())
    assert (outcome.status, outcome.effective_at) == ("COMPLETED", renewed.period_start)


@pytest.mark.asyncio
async def test_renewal_after_the_grace_starts_now_and_an_early_one_starts_at_the_period_end(env) -> None:
    env.clock.at = START + timedelta(days=10)
    early = await _renew(env)
    assert early.period_start == START + timedelta(days=30)
    assert (await PeriodStore(env.session).starting_at(TENANT, RELATIONSHIP, START)).status == "ACTIVE"
    env.clock.at = START + timedelta(days=60)
    late = await _renew(env, reference="pay_r2")
    assert late.period_start == env.clock.at


@pytest.mark.asyncio
async def test_paid_renewal_uses_the_downgrade_scheduled_for_renewal(env) -> None:
    await _service(env).execute("UPGRADE_PACKAGE", TENANT, RELATIONSHIP, uuid4(), target_package_code="PRO")
    await _service(env).execute("DOWNGRADE_PACKAGE", TENANT, RELATIONSHIP, uuid4(), target_package_code="STARTER")
    env.clock.at = START + timedelta(days=30)
    renewed = await _renew(env, fee=30_000)
    assert renewed.package_version_id == starter().version_id
    assert (await PeriodStore(env.session).starting_at(TENANT, RELATIONSHIP, START)).scheduled_package_version_id is None


@pytest.mark.asyncio
async def test_paid_renewal_refuses_a_wrong_amount_a_missing_policy_and_a_terminated_relationship(env) -> None:
    env.clock.at = START + timedelta(days=30)
    with pytest.raises(LifecycleError) as amount:
        await _renew(env, fee=20_000)
    assert amount.value.code == "RENEWAL_AMOUNT_MISMATCH"
    assert await PeriodStore(env.session).starting_at(TENANT, RELATIONSHIP, env.clock.at) is None
    with pytest.raises(LifecycleError) as policy:
        await _service(env, with_policy=False).renew_paid(
            TENANT, RELATIONSHIP, CUSTOMER, payment_reference="pay_x", fee_paid_paise=30_000,
            evidence_id=uuid4(), authority="WALLET",
        )
    assert policy.value.code == "POLICY_ABSENT"
    await _service(env).execute("TERMINATE_RELATIONSHIP", TENANT, RELATIONSHIP, uuid4())
    with pytest.raises(LifecycleError) as terminated:
        await _renew(env, reference="pay_y")
    assert terminated.value.code == "RELATIONSHIP_TERMINATED"
    assert (await _service(env).execute("RENEW_RELATIONSHIP", TENANT, RELATIONSHIP, uuid4())).blocked_reason == (
        "RELATIONSHIP_TERMINATED"
    )


@pytest.mark.asyncio
async def test_legacy_authority_renews_nothing(env) -> None:
    env.clock.at = START + timedelta(days=30)
    assert await _renew(env, authority="LEGACY") is None
    assert await PeriodStore(env.session).starting_at(TENANT, RELATIONSHIP, env.clock.at) is None


@pytest.mark.asyncio
async def test_renewal_redeems_a_goodwill_coupon_and_the_captured_amount_is_the_discounted_price(env) -> None:
    env.clock.at = START + timedelta(days=30)
    redeem = _redeemer(5_000)
    with pytest.raises(LifecycleError) as full_price:
        await _renew(env, coupon_code="GOODWILL", redeem=redeem)
    assert full_price.value.code == "RENEWAL_AMOUNT_MISMATCH"
    renewed = await _renew(env, fee=25_000, coupon_code="GOODWILL", redeem=redeem, reference="pay_c1")
    assert renewed.fee_paid_paise == 25_000
    assert redeem.calls[-1]["event"] == "RENEWAL" and redeem.calls[-1]["code"] == "GOODWILL"
    assert (await _balance(env)).credited_paise == PERIOD_CREDIT_PAISE


@pytest.mark.asyncio
async def test_renewal_surfaces_a_coupon_refusal_by_its_code(env) -> None:
    env.clock.at = START + timedelta(days=30)
    refused = _redeemer(0, CouponError("COUPON_EXPIRED", 422, "expired"))
    with pytest.raises(LifecycleError) as error:
        await _renew(env, coupon_code="OLD", redeem=refused)
    assert error.value.code == "COUPON_EXPIRED"


@pytest.mark.asyncio
async def test_hire_redeems_a_goodwill_coupon_and_a_refused_or_legacy_code_leaves_the_price(env) -> None:
    packages = FakePackages(starter(), pro())
    redeem = _redeemer(10_000)
    period = await credit_paid_period(
        env.session, rates=FakeRates(), tenant_id=TENANT, relationship_id=uuid4(), customer_id=CUSTOMER,
        period_start=START, evidence_id=uuid4(), authority="WALLET", coupon_code="GOODWILL", redeem=redeem,
        packages=packages,
    )
    assert period.fee_paid_paise == 20_000
    assert redeem.calls[0]["event"] == "HIRE" and redeem.calls[0]["price_incl_gst_paise"] == 30_000
    legacy = await credit_paid_period(
        env.session, rates=FakeRates(), tenant_id=TENANT, relationship_id=uuid4(), customer_id=CUSTOMER,
        period_start=START, evidence_id=uuid4(), authority="WALLET", coupon_code="DEMO10",
        redeem=_redeemer(0, CouponError("COUPON_NOT_FOUND", 404, "not versioned")), packages=packages,
    )
    assert legacy.fee_paid_paise == 30_000


@pytest.mark.asyncio
async def test_immediate_upgrade_charges_the_unelapsed_difference_and_tops_up_the_wallet(env) -> None:
    env.clock.at = START + timedelta(days=15)
    outcome = await _service(env).execute(
        "UPGRADE_PACKAGE", TENANT, RELATIONSHIP, uuid4(), target_package_code="PRO"
    )
    period = await _period(env)
    assert (outcome.status, outcome.prorated_fee_difference_paise) == ("COMPLETED", 15_000)
    assert period.package_version_id == pro().version_id and period.fee_paid_paise == 45_000
    assert (await _balance(env)).credited_paise == PERIOD_CREDIT_PAISE + PERIOD_CREDIT_PAISE // 2
    assert await _adjustments(env) == [(15_000, "PENDING_PROVIDER", None)]


@pytest.mark.asyncio
async def test_the_upgrade_fee_is_collected_through_a_provider_order_and_recorded_on_capture(env) -> None:
    env.clock.at = START + timedelta(days=15)
    await _service(env).execute("UPGRADE_PACKAGE", TENANT, RELATIONSHIP, uuid4(), target_package_code="PRO")
    adjustments = BillingAdjustments(env.session, now=env.clock)
    assert await adjustments.collect_pending(_Orders(fail=True), 10) == 0
    assert [row[1] for row in await _adjustments(env)] == ["FAILED_RETRYABLE"]
    orders = _Orders()
    assert await adjustments.collect_pending(orders, 10) == 1
    assert await adjustments.collect_pending(orders, 10) == 0
    amount, notes = orders.calls[0]
    assert amount == 15_000 and notes["checkout_kind"] == "UPGRADE_FEE" and notes["relationship_id"] == str(RELATIONSHIP)
    adjustment = UUID(notes["adjustment_id"])
    with pytest.raises(LifecycleError) as mismatch:
        await adjustments.mark_charge_captured(adjustment, "pay_u1", 1)
    assert mismatch.value.code == "CHARGE_MISMATCH"
    assert await adjustments.mark_charge_captured(adjustment, "pay_u1", 15_000) is True
    assert await adjustments.mark_charge_captured(adjustment, "pay_u1", 15_000) is False
    assert await _adjustments(env) == [(15_000, "COLLECTED", "pay_u1")]
    with pytest.raises(LifecycleError):
        await adjustments.mark_charge_captured(uuid4(), "pay_u2", 15_000)
    provider = _Provider()
    assert await adjustments.dispatch_pending(provider, 10) == 0 and provider.calls == []


@pytest.mark.asyncio
async def test_downgrade_is_scheduled_for_the_renewal_when_the_policy_says_so(env) -> None:
    await _service(env).execute("UPGRADE_PACKAGE", TENANT, RELATIONSHIP, uuid4(), target_package_code="PRO")
    outcome = await _service(env).execute(
        "DOWNGRADE_PACKAGE", TENANT, RELATIONSHIP, uuid4(), target_package_code="STARTER"
    )
    period = await _period(env)
    assert (outcome.status, outcome.effective_at) == ("PENDING", START + timedelta(days=30))
    assert period.scheduled_package_version_id == starter().version_id
    assert period.package_version_id == pro().version_id


@pytest.mark.asyncio
async def test_package_changes_refuse_a_wrong_direction_an_unchanged_or_unknown_target(env) -> None:
    service = _service(env)
    cases = [
        ("UPGRADE_PACKAGE", "STARTER", "TARGET_PACKAGE_UNCHANGED"),
        ("DOWNGRADE_PACKAGE", "PRO", "TARGET_PACKAGE_NOT_CHEAPER"),
        ("UPGRADE_PACKAGE", "GOLD", "TARGET_PACKAGE_UNKNOWN"),
        ("UPGRADE_PACKAGE", None, "TARGET_PACKAGE_UNKNOWN"),
    ]
    for kind, code, reason in cases:
        outcome = await service.execute(kind, TENANT, RELATIONSHIP, uuid4(), target_package_code=code)
        assert (outcome.status, outcome.blocked_reason) == ("REJECTED", reason)


@pytest.mark.asyncio
async def test_package_change_without_policy_is_blocked(env) -> None:
    outcome = await _service(env, with_policy=False).execute(
        "UPGRADE_PACKAGE", TENANT, RELATIONSHIP, uuid4(), target_package_code="PRO"
    )
    assert (outcome.status, outcome.blocked_reason) == ("BLOCKED", "POLICY_ABSENT")


@pytest.mark.asyncio
async def test_unpaid_renewal_suspends_only_after_the_policy_grace_and_lapses_the_credit(env) -> None:
    env.clock.at = START + timedelta(days=31)
    grace_until = await _service(env).record_payment_failure(TENANT, RELATIONSHIP)
    assert grace_until == START + timedelta(days=34)
    env.clock.at = START + timedelta(days=33)
    assert await _service(env).suspend_expired_grace() == 0
    env.clock.at = START + timedelta(days=34)
    assert await _service(env).suspend_expired_grace() == 1
    assert (await _period(env)).status == "SUSPENDED"
    assert await _service(env).suspend_expired_grace() == 0


@pytest.mark.asyncio
async def test_payment_failure_without_policy_never_invents_a_grace(env) -> None:
    with pytest.raises(LifecycleError) as refused:
        await _service(env, with_policy=False).record_payment_failure(TENANT, RELATIONSHIP)
    assert refused.value.code == "POLICY_ABSENT"


@pytest.mark.asyncio
async def test_relationship_without_a_period_is_unavailable(env) -> None:
    outcome = await _service(env).execute("PAUSE_RELATIONSHIP", TENANT, uuid4(), uuid4())
    assert (outcome.status, outcome.blocked_reason) == ("UNAVAILABLE", "NO_ACTIVE_PERIOD")


@pytest.mark.asyncio
async def test_legacy_authority_credits_no_period(env) -> None:
    other = uuid4()
    assert (
        await credit_paid_period(
            env.session, rates=FakeRates(), tenant_id=TENANT, relationship_id=other, customer_id=CUSTOMER,
            period_start=START, evidence_id=uuid4(), authority="LEGACY",
        )
        is None
    )
    assert await PeriodStore(env.session).current(TENANT, other, START) is None
