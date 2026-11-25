# Implements: work-contracts/WC-170-real-agent-work-end-to-end.md WC170-R009
# Constitutional basis: C-059, C-063, C-088, C-089, C-076
"""Spend chain: authorize, reserve atomically, charge on proof, reconcile, block on discrepancy. Sandbox only."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from sqlalchemy import text

from spend_chain.service import SpendChain, SpendError
from wallet.ledger import WalletLedger

T0 = datetime(2026, 11, 1, tzinfo=timezone.utc)
TENANT = UUID("11111111-1111-4111-8111-111111111111")
CUSTOMER = UUID("33333333-3333-4333-8333-333333333333")
RELATIONSHIP = UUID("44444444-4444-4444-8444-444444444444")
OTHER_RELATIONSHIP = UUID("55555555-5555-4555-8555-555555555555")
DIGEST = "a" * 64

SPEND_DDL = (
    """CREATE TABLE business.spend_authorizations (
        authorization_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, relationship_id TEXT NOT NULL,
        artifact_id TEXT NOT NULL, artifact_digest TEXT NOT NULL, approval_evidence_id TEXT NOT NULL,
        scope_evidence_id TEXT NOT NULL, ceiling_paise INTEGER NOT NULL, reserved_paise INTEGER NOT NULL DEFAULT 0,
        currency TEXT NOT NULL, funding_account TEXT NOT NULL, window_start TEXT NOT NULL, window_end TEXT NOT NULL,
        provider_mode TEXT NOT NULL, status TEXT NOT NULL, idempotency_key TEXT NOT NULL, created_at TEXT NOT NULL,
        UNIQUE (tenant_id, idempotency_key))""",
    """CREATE TABLE business.spend_items (
        authorization_id TEXT NOT NULL, work_item_id TEXT NOT NULL, tenant_id TEXT NOT NULL,
        relationship_id TEXT NOT NULL, reservation_id TEXT NOT NULL, reserved_paise INTEGER NOT NULL,
        state TEXT NOT NULL, charged_paise INTEGER, provider_reference TEXT, created_at TEXT NOT NULL,
        PRIMARY KEY (authorization_id, work_item_id))""",
    """CREATE TABLE business.spend_observations (
        observation_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, authorization_id TEXT NOT NULL,
        work_item_id TEXT NOT NULL, observed_paise INTEGER NOT NULL, provider_reference TEXT NOT NULL,
        observed_at TEXT NOT NULL, UNIQUE (authorization_id, work_item_id, provider_reference))""",
    """CREATE TABLE business.spend_reconciliation_results (
        result_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, relationship_id TEXT NOT NULL, status TEXT NOT NULL,
        charged_paise INTEGER NOT NULL, observed_paise INTEGER NOT NULL, difference_paise INTEGER NOT NULL,
        unresolved_items INTEGER NOT NULL, created_at TEXT NOT NULL, resolved_at TEXT, resolution_evidence_id TEXT)""",
)


class _Clock:
    def __init__(self) -> None:
        self.value = T0

    def __call__(self) -> datetime:
        return self.value

    def advance(self, **delta: int) -> None:
        self.value += timedelta(**delta)


@dataclass
class ProviderEmulator:
    """Stands in for the provider's sandbox: it reports a reference and a figure, optionally skewed."""

    skew_paise: int = 0

    def spend(self, work_item_id: UUID, paise: int) -> tuple[str, int]:
        return f"sandbox:{work_item_id.hex[:12]}", paise + self.skew_paise


@pytest_asyncio.fixture
async def env(wallet_db):
    clock = _Clock()
    async with wallet_db() as session:
        for statement in SPEND_DDL:
            await session.execute(text(statement))
        ledger = WalletLedger(session, overrun_tolerance_paise=500, now=clock)
        customer = await ledger.open_account(TENANT, "SUBSCRIPTION", owner_ref=CUSTOMER, relationship_id=RELATIONSHIP)
        platform = await ledger.open_account(TENANT, "SIMULATION", environment="demo")
        for account in (customer, platform):
            await ledger.credit(
                account,
                "PERIOD_CREDIT",
                50_000,
                T0 - timedelta(days=1),
                T0 + timedelta(days=30),
                f"package:{account.account_class}",
                {"package": "p1"},
                uuid4(),
            )
        chain = SpendChain(session, ledger, tolerance_paise=50, now=clock)
        yield SimpleNamespace(session=session, ledger=ledger, chain=chain, clock=clock, customer=customer, platform=platform)


async def _authorize(env, *, ceiling: int = 1_000, funding: str = "CUSTOMER", relationship: UUID = RELATIONSHIP, key=None):
    return await env.chain.authorize(
        TENANT,
        relationship,
        uuid4(),
        DIGEST,
        uuid4(),
        uuid4(),
        ceiling,
        funding,
        T0,
        T0 + timedelta(days=7),
        key or uuid4(),
    )


async def _reserved(env, authorization) -> int:
    row = (
        await env.session.execute(
            text("SELECT reserved_paise FROM business.spend_authorizations WHERE authorization_id = :id"),
            {"id": str(authorization.authorization_id)},
        )
    ).scalar_one()
    return int(row)


@pytest.mark.asyncio
async def test_authorization_needs_the_exact_artifact_two_evidence_ids_and_never_real_money(env) -> None:
    base = (TENANT, RELATIONSHIP, uuid4(), DIGEST, uuid4(), uuid4(), 1_000, "CUSTOMER", T0, T0 + timedelta(days=1), uuid4())

    for bad in (
        (TENANT, RELATIONSHIP, uuid4(), "short", uuid4(), uuid4(), 1_000, "CUSTOMER", T0, T0 + timedelta(days=1), uuid4()),
        (TENANT, RELATIONSHIP, UUID(int=0), DIGEST, uuid4(), uuid4(), 1_000, "CUSTOMER", T0, T0 + timedelta(days=1), uuid4()),
    ):
        with pytest.raises(SpendError, match="SPEND_ARTIFACT_BINDING_REQUIRED"):
            await env.chain.authorize(*bad)
    same = uuid4()
    with pytest.raises(SpendError, match="SPEND_ARTIFACT_BINDING_REQUIRED"):
        await env.chain.authorize(
            TENANT, RELATIONSHIP, uuid4(), DIGEST, same, same, 1_000, "CUSTOMER", T0, T0 + timedelta(days=1), uuid4()
        )
    with pytest.raises(SpendError, match="SPEND_AUTHORIZATION_INVALID"):
        await env.chain.authorize(*base[:6], 0, "CUSTOMER", T0, T0 + timedelta(days=1), uuid4())
    with pytest.raises(SpendError, match="SPEND_AUTHORIZATION_INVALID"):
        await env.chain.authorize(*base[:7], "BANK", T0, T0 + timedelta(days=1), uuid4())
    with pytest.raises(SpendError, match="SPEND_REAL_MONEY_OUT_OF_SCOPE"):
        await env.chain.authorize(*base, provider_mode="LIVE")


@pytest.mark.asyncio
async def test_authorization_replays_on_its_key_and_refuses_a_changed_request(env) -> None:
    key = uuid4()
    first = await _authorize(env, key=key)

    replay = await env.chain.authorize(
        TENANT, RELATIONSHIP, first.artifact_id, DIGEST, uuid4(), uuid4(), 1_000, "CUSTOMER", T0, T0 + timedelta(days=7), key
    )
    assert replay.replayed and replay.authorization_id == first.authorization_id
    with pytest.raises(SpendError, match="SPEND_IDEMPOTENCY_CONFLICT"):
        await env.chain.authorize(
            TENANT, RELATIONSHIP, first.artifact_id, DIGEST, uuid4(), uuid4(), 9_999, "CUSTOMER", T0, T0 + timedelta(days=7), key
        )


@pytest.mark.asyncio
async def test_the_ceiling_check_and_the_hold_are_one_operation_and_a_replay_returns_the_same_hold(env) -> None:
    authorization = await _authorize(env, ceiling=1_000)
    first, second = uuid4(), uuid4()

    held = await env.chain.reserve(TENANT, authorization.authorization_id, first, 600, env.customer, "social-post")
    replay = await env.chain.reserve(TENANT, authorization.authorization_id, first, 600, env.customer, "social-post")
    with pytest.raises(SpendError, match="SPEND_CEILING_EXCEEDED"):
        await env.chain.reserve(TENANT, authorization.authorization_id, second, 600, env.customer, "social-post")
    with pytest.raises(SpendError, match="SPEND_IDEMPOTENCY_CONFLICT"):
        await env.chain.reserve(TENANT, authorization.authorization_id, first, 700, env.customer, "social-post")

    assert replay.replayed and replay.reservation_id == held.reservation_id
    assert await _reserved(env, authorization) == 600


@pytest.mark.asyncio
async def test_unfunded_or_wrongly_funded_work_does_not_run_and_says_why(env) -> None:
    hired = await _authorize(env, funding="CUSTOMER")
    owned = await _authorize(env, funding="PLATFORM")

    with pytest.raises(SpendError) as unfunded:
        await env.chain.reserve(TENANT, hired.authorization_id, uuid4(), 100, None, "post")
    assert unfunded.value.code == "SPEND_UNFUNDED"
    with pytest.raises(SpendError, match="SPEND_FUNDING_MISMATCH"):
        await env.chain.reserve(TENANT, hired.authorization_id, uuid4(), 100, env.platform, "post")
    with pytest.raises(SpendError, match="SPEND_FUNDING_MISMATCH"):
        await env.chain.reserve(TENANT, owned.authorization_id, uuid4(), 100, env.customer, "post")

    assert (await env.chain.reserve(TENANT, hired.authorization_id, uuid4(), 100, env.customer, "post")).state == "RESERVED"
    assert (await env.chain.reserve(TENANT, owned.authorization_id, uuid4(), 100, env.platform, "post")).state == "RESERVED"
    assert await _reserved(env, hired) == 100


@pytest.mark.asyncio
async def test_a_refused_hold_gives_the_ceiling_back_and_a_closed_window_refuses_work(env) -> None:
    authorization = await _authorize(env, ceiling=100_000)

    with pytest.raises(SpendError, match="SPEND_FUNDING_REFUSED"):
        await env.chain.reserve(TENANT, authorization.authorization_id, uuid4(), 80_000, env.customer, "post")
    assert await _reserved(env, authorization) == 0
    env.clock.advance(days=8)
    with pytest.raises(SpendError, match="SPEND_AUTHORIZATION_NOT_ACTIVE"):
        await env.chain.reserve(TENANT, authorization.authorization_id, uuid4(), 100, env.customer, "post")
    with pytest.raises(SpendError, match="SPEND_NOT_AUTHORIZED"):
        await env.chain.reserve(TENANT, uuid4(), uuid4(), 100, env.customer, "post")


@pytest.mark.asyncio
async def test_a_charge_is_written_only_on_verified_proof_and_the_providers_figure_is_an_observation(env) -> None:
    emulator = ProviderEmulator()
    authorization = await _authorize(env)
    item = uuid4()
    await env.chain.reserve(TENANT, authorization.authorization_id, item, 500, env.customer, "post")
    reference, observed = emulator.spend(item, 480)

    with pytest.raises(SpendError, match="SPEND_PROOF_REQUIRED"):
        await env.chain.charge(TENANT, authorization.authorization_id, item, observed, reference, False, uuid4())
    with pytest.raises(SpendError, match="SPEND_AMOUNT_INVALID"):
        await env.chain.charge(TENANT, authorization.authorization_id, item, observed, "Bearer abc.def", True, uuid4())
    charged = await env.chain.charge(TENANT, authorization.authorization_id, item, observed, reference, True, uuid4())
    replay = await env.chain.charge(TENANT, authorization.authorization_id, item, observed, reference, True, uuid4())
    with pytest.raises(SpendError, match="SPEND_IDEMPOTENCY_CONFLICT"):
        await env.chain.charge(TENANT, authorization.authorization_id, item, observed + 1, reference, True, uuid4())

    assert (charged.state, charged.charged_paise, charged.provider_reference) == ("CHARGED", 480, reference)
    assert replay.replayed
    observations = (await env.session.execute(text("SELECT provider_reference FROM business.spend_observations"))).all()
    assert [row[0] for row in observations] == [reference]


@pytest.mark.asyncio
async def test_reconciliation_matches_within_tolerance_or_breaks_and_a_break_blocks_new_spend_until_resolved(env) -> None:
    emulator = ProviderEmulator()
    authorization = await _authorize(env, ceiling=5_000)
    first, second = uuid4(), uuid4()
    for item in (first, second):
        await env.chain.reserve(TENANT, authorization.authorization_id, item, 1_000, env.customer, "post")
    reference, observed = emulator.spend(first, 900)
    await env.chain.charge(TENANT, authorization.authorization_id, first, observed, reference, True, uuid4())

    matched = await env.chain.reconcile(TENANT, RELATIONSHIP)
    assert (matched.status, matched.difference_paise, matched.unresolved_items) == ("MATCHED", 0, 0)
    assert not await env.chain.blocked(TENANT, RELATIONSHIP)

    # An unconfirmed dispatch stays reserved and uncertain until reconciliation can settle it.
    await env.chain.mark_uncertain(TENANT, authorization.authorization_id, second)
    env.clock.advance(seconds=1)
    broken = await env.chain.reconcile(TENANT, RELATIONSHIP)
    assert broken.status == "DISCREPANCY" and broken.unresolved_items == 1
    assert await env.chain.blocked(TENANT, RELATIONSHIP)
    with pytest.raises(SpendError, match="SPEND_BLOCKED_DISCREPANCY"):
        await env.chain.reserve(TENANT, authorization.authorization_id, uuid4(), 100, env.customer, "post")
    with pytest.raises(SpendError, match="SPEND_BLOCKED_DISCREPANCY"):
        await _authorize(env)
    other = await _authorize(env, relationship=OTHER_RELATIONSHIP)
    assert other.status == "ACTIVE"

    with pytest.raises(SpendError, match="SPEND_EVIDENCE_REQUIRED"):
        await env.chain.resolve_discrepancy(TENANT, broken.result_id, UUID(int=0))
    await env.chain.resolve_discrepancy(TENANT, broken.result_id, uuid4())
    with pytest.raises(SpendError, match="SPEND_RESULT_NOT_RESOLVABLE"):
        await env.chain.resolve_discrepancy(TENANT, broken.result_id, uuid4())
    assert not await env.chain.blocked(TENANT, RELATIONSHIP)


@pytest.mark.asyncio
async def test_a_provider_figure_beyond_tolerance_is_a_discrepancy_and_a_small_one_is_within_tolerance(env) -> None:
    authorization = await _authorize(env, ceiling=5_000)
    item = uuid4()
    await env.chain.reserve(TENANT, authorization.authorization_id, item, 1_000, env.customer, "post")
    await env.chain.charge(TENANT, authorization.authorization_id, item, 900, "sandbox:one", True, uuid4())
    await env.chain.observe(TENANT, authorization.authorization_id, item, 20, "sandbox:extra")

    within = await env.chain.reconcile(TENANT, RELATIONSHIP)
    assert (within.status, within.difference_paise) == ("WITHIN_TOLERANCE", 20)

    await env.chain.observe(TENANT, authorization.authorization_id, item, 200, "sandbox:big")
    env.clock.advance(seconds=1)
    broken = await env.chain.reconcile(TENANT, RELATIONSHIP)
    assert (broken.status, broken.difference_paise) == ("DISCREPANCY", 220)
    with pytest.raises(SpendError, match="SPEND_AMOUNT_INVALID"):
        await env.chain.observe(TENANT, authorization.authorization_id, item, -1, "sandbox:neg")


@pytest.mark.asyncio
async def test_opposite_differences_do_not_cancel_and_a_later_match_never_clears_a_break(env) -> None:
    authorization = await _authorize(env, ceiling=9_000)
    over, under = uuid4(), uuid4()
    for item in (over, under):
        await env.chain.reserve(TENANT, authorization.authorization_id, item, 1_000, env.customer, "post")
    await env.chain.charge(TENANT, authorization.authorization_id, over, 900, "sandbox:over", True, uuid4())
    await env.chain.charge(TENANT, authorization.authorization_id, under, 900, "sandbox:under", True, uuid4())
    await env.chain.observe(TENANT, authorization.authorization_id, over, 400, "sandbox:over-extra")
    # The second item is reported 400 below what was charged: the totals cancel, the items do not.
    await env.session.execute(
        text("UPDATE business.spend_observations SET observed_paise = 500 WHERE provider_reference = 'sandbox:under'")
    )

    broken = await env.chain.reconcile(TENANT, RELATIONSHIP)

    assert broken.status == "DISCREPANCY" and broken.difference_paise == 0
    # Fixing the books later does not unblock spend: only the Founder's resolution with evidence does.
    await env.session.execute(text("DELETE FROM business.spend_observations WHERE provider_reference = 'sandbox:over-extra'"))
    await env.session.execute(
        text("UPDATE business.spend_observations SET observed_paise = 900 WHERE provider_reference = 'sandbox:under'")
    )
    env.clock.advance(seconds=1)
    clean = await env.chain.reconcile(TENANT, RELATIONSHIP)
    assert clean.status == "MATCHED"
    assert await env.chain.blocked(TENANT, RELATIONSHIP)
    await env.chain.resolve_discrepancy(TENANT, broken.result_id, uuid4())
    assert not await env.chain.blocked(TENANT, RELATIONSHIP)


@pytest.mark.asyncio
async def test_another_tenant_cannot_read_or_charge_an_item_it_does_not_own(env) -> None:
    authorization = await _authorize(env)
    item = uuid4()
    await env.chain.reserve(TENANT, authorization.authorization_id, item, 100, env.customer, "post")
    other = UUID("99999999-9999-4999-8999-999999999999")

    with pytest.raises(SpendError, match="SPEND_NOT_AUTHORIZED"):
        await env.chain.charge(other, authorization.authorization_id, item, 100, "sandbox:x", True, uuid4())
    with pytest.raises(SpendError, match="SPEND_NOT_AUTHORIZED"):
        await env.chain.mark_uncertain(other, authorization.authorization_id, item)


@pytest.mark.asyncio
async def test_every_spend_route_refuses_a_caller_without_workload_identity() -> None:
    from fastapi import FastAPI
    from httpx import ASGITransport, AsyncClient

    from spend_chain.private_routes import router

    app = FastAPI()
    app.include_router(router)
    ident = str(uuid4())
    bodies = {
        "authorize": {
            "relationshipId": ident,
            "artifactId": ident,
            "artifactDigest": DIGEST,
            "approvalEvidenceId": ident,
            "scopeEvidenceId": str(uuid4()),
            "ceilingPaise": 100,
            "fundingAccount": "CUSTOMER",
            "windowStart": "2026-11-01T00:00:00Z",
            "windowEnd": "2026-11-08T00:00:00Z",
        },
        "reserve": {"authorizationId": ident, "workItemId": ident, "paise": 10, "componentId": "post", "environment": "demo"},
        "charge": {
            "authorizationId": ident,
            "workItemId": ident,
            "observedPaise": 10,
            "providerReference": "sandbox:1",
            "verified": True,
            "evidenceId": ident,
        },
        "reconcile": {"relationshipId": ident},
    }
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        for name, body in bodies.items():
            response = await client.post(
                f"/internal/v1/real-work/spend/{name}", json=body, headers={"Idempotency-Key": str(uuid4())}
            )
            assert response.status_code == 401, name
            assert response.json()["detail"] == "WBE_WALLET_UNAUTHORIZED"
