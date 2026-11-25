# Implements: work-contracts/WC-172-safe-to-charge-real-customers.md WC172-R010, WC172-R011
# Constitutional basis: C-007, C-023, C-059, C-088
"""Money mode, the real-money gate and the provider-to-invoice reconciliation."""

from __future__ import annotations

import sys
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from sqlalchemy import DateTime, bindparam, text

sys.path.insert(0, str(Path(__file__).parent))

from invoicing.identity import supplier_from  # noqa: E402
from invoicing.service import TaxDocumentService  # noqa: E402
from payment.money_gate import ChargeRefused, MoneyGate, MoneyGateError  # noqa: E402
from payment.money_jobs import make_charge_guard, run_money_reconciliation  # noqa: E402
from payment.money_mode import MoneyModeError, require_consistent_mode  # noqa: E402
from payment.money_reconciliation import (  # noqa: E402
    MoneyReconciler,
    MoneyReconciliationError,
    ProviderPayment,
    ProviderRefund,
    list_discrepancies,
    resolve_discrepancy,
)
from payment.razorpay_client import RazorpayClient, set_charge_guard  # noqa: E402
from wc136_commercial_ddl import COMMERCIAL_DDL, WC172_DDL, install  # noqa: E402

NOW = datetime(2027, 1, 15, 6, 0, tzinfo=timezone.utc)
PAYER = UUID("22222222-2222-4222-8222-222222222222")
SUPPLIER = supplier_from("DLAI Satellite Data (OPC) Pvt Ltd", "27AAKCD8188R1ZH", "Pune", "27")


@pytest.mark.parametrize(
    ("environment", "mode", "key", "readiness"),
    [
        ("demo", "TEST", "rzp_test_abc", "READY_TEST"),
        ("uat", "TEST", "", "NOT_CONFIGURED"),
        ("production", "LIVE", "rzp_live_abc", "READY_LIVE"),
        ("production", "LIVE", "", "NOT_CONFIGURED"),
    ],
)
def test_a_consistent_environment_starts(environment: str, mode: str, key: str, readiness: str) -> None:
    assert require_consistent_mode(environment, mode, key, readiness).payment_mode == mode


@pytest.mark.parametrize(
    ("environment", "mode", "key", "readiness", "code"),
    [
        ("demo", "TEST", "rzp_live_abc", "NOT_CONFIGURED", "LIVE_KEY_OUTSIDE_PRODUCTION"),
        ("uat", "LIVE", "rzp_test_abc", "NOT_CONFIGURED", "MONEY_MODE_ENVIRONMENT_MISMATCH"),
        ("production", "LIVE", "rzp_test_abc", "NOT_CONFIGURED", "TEST_KEY_IN_PRODUCTION"),
        ("production", "TEST", "rzp_test_abc", "NOT_CONFIGURED", "MONEY_MODE_ENVIRONMENT_MISMATCH"),
        ("demo", "TEST", "sk_something", "NOT_CONFIGURED", "MONEY_KEY_MODE_UNKNOWN"),
        ("demo", "TEST", "rzp_test_abc", "READY_LIVE", "READINESS_STATE_MISMATCH"),
        ("production", "LIVE", "rzp_live_abc", "READY_TEST", "READINESS_STATE_MISMATCH"),
    ],
)
def test_a_live_key_outside_production_or_a_test_key_in_it_stops_the_service(
    environment: str, mode: str, key: str, readiness: str, code: str
) -> None:
    with pytest.raises(MoneyModeError) as refused:
        require_consistent_mode(environment, mode, key, readiness)
    assert refused.value.code == code


def test_the_service_checks_the_mode_before_it_opens_the_database() -> None:
    source = (Path(__file__).parents[2] / "src/billing-engine/main.py").read_text(encoding="utf-8")
    assert source.index("require_consistent_mode(") < source.index("await init_db()")


@pytest_asyncio.fixture
async def env(wallet_db):
    async with wallet_db() as session:
        await install(session, COMMERCIAL_DDL, WC172_DDL)
        yield SimpleNamespace(session=session, clock=lambda: NOW)


def _sessions(env):
    """A session opener that hands back the test's own session, as the service's session factory does."""

    @asynccontextmanager
    async def open_session():
        yield env.session

    return open_session


def _gate(env, environment: str = "production", mode: str = "LIVE") -> MoneyGate:
    return MoneyGate(env.session, environment, mode, now=env.clock)


@pytest.mark.asyncio
async def test_real_money_is_off_by_default_and_a_live_charge_is_refused_until_the_founder_turns_it_on(env) -> None:
    gate = _gate(env)
    assert (await gate.state()).enabled is False
    with pytest.raises(ChargeRefused) as closed:
        await gate.require_charge_allowed()
    assert closed.value.code == "REAL_MONEY_GATE_CLOSED"
    state = await gate.set(True, "founder-1", True, "Go-live approved in writing")
    assert state.enabled and state.changed_by == "founder-1"
    await gate.require_charge_allowed()


@pytest.mark.asyncio
async def test_only_a_step_up_in_production_can_turn_real_money_on_and_off_needs_none(env) -> None:
    with pytest.raises(MoneyGateError) as no_step_up:
        await _gate(env).set(True, "founder-1", False, "reason")
    assert no_step_up.value.code == "MONEY_GATE_STEP_UP_REQUIRED"
    for environment, mode in (("demo", "TEST"), ("uat", "TEST")):
        with pytest.raises(MoneyGateError) as elsewhere:
            await _gate(env, environment, mode).set(True, "founder-1", True, "reason")
        assert elsewhere.value.code == "MONEY_GATE_NOT_PRODUCTION"
    with pytest.raises(MoneyGateError) as blank:
        await _gate(env).set(True, "founder-1", True, "  ")
    assert blank.value.code == "MONEY_GATE_REASON_REQUIRED"
    await _gate(env).set(True, "founder-1", True, "open")
    off = await _gate(env).set(False, "ops-1", False, "Stop everything")
    assert off.enabled is False
    audit = (await env.session.execute(text("SELECT enabled, changed_by, step_up FROM business.money_gate_audit ORDER BY changed_at, rowid"))).all()
    assert [(bool(row[0]), row[1], bool(row[2])) for row in audit] == [(True, "founder-1", True), (False, "ops-1", False)]


@pytest.mark.asyncio
async def test_a_test_mode_environment_charges_without_the_gate_but_never_in_production_test_mode(env) -> None:
    await _gate(env, "demo", "TEST").require_charge_allowed()
    with pytest.raises(ChargeRefused) as invalid:
        await _gate(env, "production", "TEST").require_charge_allowed()
    assert invalid.value.code == "MONEY_MODE_INVALID"


@pytest.mark.asyncio
async def test_the_provider_client_creates_no_order_while_the_guard_refuses(env) -> None:
    async def closed(settings) -> None:
        raise ChargeRefused("REAL_MONEY_GATE_CLOSED")

    set_charge_guard(closed)
    try:
        with pytest.raises(ChargeRefused):
            await RazorpayClient(settings=SimpleNamespace(RAZORPAY_PAYMENT_MODE="LIVE")).create_order(1_000, {})
    finally:
        set_charge_guard(None)
    with pytest.raises(ChargeRefused) as unguarded:
        await RazorpayClient(settings=SimpleNamespace(RAZORPAY_PAYMENT_MODE="LIVE")).create_order(1_000, {})
    assert unguarded.value.code == "REAL_MONEY_GATE_UNAVAILABLE"


@pytest.mark.asyncio
async def test_the_installed_guard_reads_the_gate_from_the_database(env) -> None:
    guard = make_charge_guard(_sessions(env))
    settings = SimpleNamespace(WAOOAW_ENVIRONMENT="production", RAZORPAY_PAYMENT_MODE="LIVE")
    with pytest.raises(ChargeRefused):
        await guard(settings)
    await _gate(env).set(True, "founder-1", True, "open")
    await guard(settings)


class _Provider:
    def __init__(self, payments=(), refunds=()) -> None:
        self._payments, self._refunds = list(payments), list(refunds)

    async def payments(self, start, end):
        return self._payments

    async def refunds(self, start, end):
        return self._refunds


async def _invoice(env, reference: str, amount: int):
    return await TaxDocumentService(env.session, SUPPLIER, now=env.clock).issue_for_payment(
        payment_reference=reference, amount_paise=amount, payer_customer_id=PAYER
    )


def _window():
    return NOW - timedelta(hours=1), NOW + timedelta(hours=1)


@pytest.mark.asyncio
async def test_matching_books_are_clean_and_leave_charges_open(env) -> None:
    await _invoice(env, "pay_1", 30_000)
    report = await MoneyReconciler(env.session, _Provider([ProviderPayment("pay_1", 30_000, True)]), now=env.clock).reconcile(*_window())
    assert report.clean and report.checked_payments == 1
    await _gate(env, "demo", "TEST").require_charge_allowed()


@pytest.mark.asyncio
async def test_each_kind_of_difference_opens_one_discrepancy_and_blocks_new_charges(env) -> None:
    await _invoice(env, "pay_ok", 10_000)
    await _invoice(env, "pay_wrong", 20_000)
    await _invoice(env, "pay_phantom", 5_000)
    adjustment = uuid4()
    insert = text(
        "INSERT INTO business.billing_adjustments (adjustment_id, tenant_id, relationship_id, command_id, adjustment_kind, "
        "amount_paise, payment_reference, status, created_at, updated_at) VALUES (:id, :tenant, :relationship, :command, "
        "'FEE_REFUND', 500, 'pay_ok', 'DISPATCHED', :at, :at)"
    ).bindparams(bindparam("at", type_=DateTime(timezone=True)))
    await env.session.execute(
        insert, {"id": str(adjustment), "tenant": str(uuid4()), "relationship": str(uuid4()), "command": str(uuid4()), "at": NOW}
    )
    await TaxDocumentService(env.session, SUPPLIER, now=env.clock).issue_credit_note(
        source_reference=str(adjustment), original_payment_reference="pay_ok", amount_paise=500
    )
    provider = _Provider(
        payments=[
            ProviderPayment("pay_ok", 10_000, True),
            ProviderPayment("pay_wrong", 21_000, True),
            ProviderPayment("pay_missing", 7_000, True),
            ProviderPayment("pay_failed", 9_000, False),
        ],
        refunds=[ProviderRefund("rfnd_1", "pay_ok", 300, "adj-no-note")],
    )
    reconciler = MoneyReconciler(env.session, provider, now=env.clock)
    report = await reconciler.reconcile(*_window())
    assert report.opened == 5 and not report.clean
    kinds = sorted((item["kind"], item["reference"]) for item in await list_discrepancies(env.session))
    assert kinds == [
        ("AMOUNT_MISMATCH", "pay_wrong"),
        ("CREDIT_NOTE_WITHOUT_REFUND", str(adjustment)),
        ("INVOICE_WITHOUT_PAYMENT", "pay_phantom"),
        ("PAYMENT_WITHOUT_INVOICE", "pay_missing"),
        ("REFUND_WITHOUT_CREDIT_NOTE", "adj-no-note"),
    ]
    assert (await reconciler.reconcile(*_window())).opened == 0
    assert len(await list_discrepancies(env.session)) == 5
    with pytest.raises(ChargeRefused) as blocked:
        await _gate(env, "demo", "TEST").require_charge_allowed()
    assert blocked.value.code == "MONEY_RECONCILIATION_BLOCKED"


@pytest.mark.asyncio
async def test_only_the_founder_with_evidence_clears_a_discrepancy_and_a_clean_run_never_does(env) -> None:
    await MoneyReconciler(env.session, _Provider([ProviderPayment("pay_missing", 7_000, True)]), now=env.clock).reconcile(*_window())
    [item] = await list_discrepancies(env.session)
    discrepancy = UUID(item["discrepancyId"])
    await MoneyReconciler(env.session, _Provider(), now=env.clock).reconcile(*_window())
    assert len(await list_discrepancies(env.session)) == 1
    with pytest.raises(MoneyReconciliationError) as no_evidence:
        await resolve_discrepancy(env.session, discrepancy, "founder-1", UUID(int=0), NOW)
    assert no_evidence.value.code == "MONEY_RESOLUTION_EVIDENCE_REQUIRED"
    await resolve_discrepancy(env.session, discrepancy, "founder-1", uuid4(), NOW)
    assert await list_discrepancies(env.session) == []
    await _gate(env, "demo", "TEST").require_charge_allowed()
    with pytest.raises(MoneyReconciliationError) as again:
        await resolve_discrepancy(env.session, discrepancy, "founder-1", uuid4(), NOW)
    assert again.value.code == "MONEY_DISCREPANCY_NOT_OPEN"


@pytest.mark.asyncio
async def test_an_unreadable_provider_is_never_reported_as_a_clean_run(env) -> None:
    class _Down:
        async def payments(self, start, end):
            raise RuntimeError("provider down")

        async def refunds(self, start, end):
            return []

    assert await run_money_reconciliation(_sessions(env), _Down(), now=env.clock) is None
    clean = await run_money_reconciliation(_sessions(env), _Provider(), now=env.clock)
    assert clean is not None and clean.clean


def test_the_money_router_implements_exactly_the_money_controls_contract_and_its_grants() -> None:
    import yaml

    import money_admin

    root = Path(__file__).resolve().parents[2]
    spec = yaml.safe_load((root / "architecture/reference/api-specs/wbe-money-controls.openapi.yaml").read_text("utf-8"))
    registry = yaml.safe_load((root / "infrastructure/workload-identity/registry.yaml").read_text("utf-8"))
    declared = {
        (method.upper(), route, operation["operationId"])
        for route, item in spec["paths"].items()
        for method, operation in item.items()
        if method in {"get", "post", "put", "patch", "delete"}
    }
    implemented = {(item.method, item.route, item.operation) for item in money_admin.OPERATIONS.values()}
    granted = {
        (grant["method"], grant["route"], grant["operation"])
        for grant in registry["route_grants"]
        if grant["target"] == "billing-engine" and grant["route"].startswith("/internal/v1/money/")
    }
    assert implemented == declared == granted
    assert {item.operation for item in money_admin.OPERATIONS.values() if item.writes} == {"wbeSetMoneyGate", "wbeResolveMoneyDiscrepancy"}
    founder_only = {name for name, item in money_admin.OPERATIONS.items() if item.roles == money_admin.ROLES_FOUNDER}
    assert {"wbeSetMoneyGate", "wbeResolveMoneyDiscrepancy"} <= founder_only
