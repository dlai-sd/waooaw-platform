# Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C4-04
# Constitutional basis: C-059, C-088, C-089, C-063
"""Platform-owned wallet accounts: keys, hierarchical caps, setup and trial grants, floor uses."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from sqlalchemy import DateTime, bindparam, text

from wallet.entity_models import ReservationIdentity, WalletError
from wallet.platform_accounts import (
    PlatformAccounts,
    effective_grant,
    is_simulated_traffic,
)

T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
TENANT = UUID("11111111-1111-4111-8111-111111111111")
RELATIONSHIP = UUID("44444444-4444-4444-8444-444444444444")
OTHER_RELATIONSHIP = UUID("55555555-5555-4555-8555-555555555555")


class _Clock:
    def __call__(self) -> datetime:
        return T0


@pytest_asyncio.fixture
async def env(wallet_db):
    async with wallet_db() as session:
        yield SimpleNamespace(session=session, accounts=PlatformAccounts(session, now=_Clock()))


async def _version(env, kind: str, subject: str, body: dict, *, state: str = "EFFECTIVE") -> None:
    await env.session.execute(
        text(
            "INSERT INTO institutional.pricing_versions "
            "(version_id, kind, subject_key, version_no, state, body, effective_from) "
            "VALUES (:id, :kind, :subject, 1, :state, :body, :effective)"
        ).bindparams(bindparam("effective", type_=DateTime(timezone=True))),
        {
            "id": str(uuid4()),
            "kind": kind,
            "subject": subject,
            "state": state,
            "body": json.dumps(body),
            "effective": T0 - timedelta(days=1),
        },
    )


async def _budget(env, scope: str, reference: str, maximum: int) -> None:
    await _version(
        env,
        "BUDGET",
        f"budget:{scope}|{reference}",
        {"scope": scope, "reference": reference, "maximumPaise": maximum},
    )


async def _grant(env, kind: str, version: str, body: dict, *, state: str = "EFFECTIVE") -> None:
    await _version(
        env,
        "GRANT",
        f"grant:{kind}|DMA|{version}",
        {"grantKind": kind, "agentType": "DMA", "agentVersion": version, "durationDays": 7, **body},
        state=state,
    )


async def _reserve(env, paise: int, *, campaign: str | None = None, lead: str | None = None, key=None):
    return await env.accounts.reserve_acquisition(
        TENANT,
        "llm_cloud",
        paise,
        T0 + timedelta(hours=1),
        ReservationIdentity(),
        key or uuid4(),
        campaign_ref=campaign,
        lead_ref=lead,
    )


async def _count(env, table: str, where: str = "1 = 1") -> int:
    return (
        await env.session.execute(text(f"SELECT COUNT(*) FROM business.{table} WHERE {where}"))
    ).scalar_one()


async def test_each_account_class_opens_idempotently_as_a_platform_account(env):
    accounts = env.accounts
    acquisition = await accounts.open_acquisition_account(TENANT)
    campaign = await accounts.open_acquisition_account(TENANT, "spring")
    lead = await accounts.open_acquisition_account(TENANT, "spring", "lead-1")
    simulation = await accounts.open_simulation_account(TENANT, "demo")
    floor = await accounts.open_floor_account(TENANT, "demo")
    await _grant(env, "SETUP", "1.0.0", {"amountPaise": 500})
    setup = await accounts.open_setup_grant(TENANT, RELATIONSHIP, "DMA", "1.0.0")

    assert acquisition.campaign_ref == "DEFAULT" and acquisition.lead_ref is None
    assert (await accounts.open_acquisition_account(TENANT)).account_id == acquisition.account_id
    assert (await accounts.open_acquisition_account(TENANT, "spring")).account_id == campaign.account_id
    assert (await accounts.open_acquisition_account(TENANT, "spring", "lead-1")).account_id == lead.account_id
    assert (await accounts.open_simulation_account(TENANT, "demo")).account_id == simulation.account_id
    assert (await accounts.open_floor_account(TENANT, "demo")).account_id == floor.account_id
    again = await accounts.open_setup_grant(TENANT, RELATIONSHIP, "DMA", "1.0.0")
    assert again.account.account_id == setup.account.account_id
    all_accounts = [acquisition, campaign, lead, simulation, floor, setup.account]
    assert len({account.account_id for account in all_accounts}) == 6
    assert {(a.owner_kind, a.owner_ref) for a in all_accounts} == {("PLATFORM", None)}
    assert await _count(env, "wallet_accounts") == 6


async def test_lead_and_campaign_references_must_be_pseudonymous_ids(env):
    for bad_lead in ("919876543210", "visitor@example.com", "+919876543210", "A Name"):
        with pytest.raises(WalletError) as refused:
            await env.accounts.open_acquisition_account(TENANT, "spring", bad_lead)
        assert refused.value.code == "WALLET_ACCOUNT_INVALID"
    assert await _count(env, "wallet_accounts") == 0


async def test_hierarchical_caps_name_the_exhausted_level(env):
    await _budget(env, "ACQUISITION_TENANT", str(TENANT), 1000)
    await _budget(env, "ACQUISITION_CAMPAIGN", "spring", 400)
    await _budget(env, "ACQUISITION_LEAD", "lead-1", 150)

    await _reserve(env, 100, campaign="spring", lead="lead-1")
    with pytest.raises(WalletError) as lead_level:
        await _reserve(env, 100, campaign="spring", lead="lead-1")
    await _reserve(env, 100, campaign="spring", lead="lead-2")
    await _reserve(env, 100, campaign="spring", lead="lead-2")
    with pytest.raises(WalletError) as campaign_level:
        await _reserve(env, 150, campaign="spring", lead="lead-3")
    with pytest.raises(WalletError) as tenant_level:
        await _reserve(env, 800, campaign="autumn")

    assert [
        (error.value.code, error.value.detail) for error in (lead_level, campaign_level, tenant_level)
    ] == [("ACQUISITION_BUDGET_EXHAUSTED", level) for level in ("LEAD", "CAMPAIGN", "TENANT")]
    assert await _count(env, "wallet_reservations") == 3


async def test_acquisition_without_a_tenant_budget_fails_closed(env):
    with pytest.raises(WalletError) as refused:
        await _reserve(env, 1)
    assert (refused.value.code, refused.value.detail) == ("ACQUISITION_BUDGET_EXHAUSTED", "TENANT")
    assert await _count(env, "wallet_reservations") == 0


async def test_acquisition_replay_conflict_and_release_frees_the_cap(env):
    await _budget(env, "ACQUISITION_TENANT", str(TENANT), 300)
    key = uuid4()
    first = await _reserve(env, 300, key=key)
    replay = await _reserve(env, 300, key=key)
    assert (first.replayed, replay.replayed) == (False, True)
    assert replay.reservation_id == first.reservation_id
    assert await _count(env, "wallet_reservations") == 1 and await _count(env, "wallet_lots") == 1
    with pytest.raises(WalletError) as changed:
        await _reserve(env, 200, key=key)
    with pytest.raises(WalletError) as exhausted:
        await _reserve(env, 100)
    assert changed.value.code == "WALLET_IDEMPOTENCY_CONFLICT"
    assert exhausted.value.code == "ACQUISITION_BUDGET_EXHAUSTED"

    await env.accounts.ledger.release(TENANT, first.reservation_id, uuid4())
    assert (await _reserve(env, 300)).state == "RESERVED"


async def test_simulation_draws_never_touch_acquisition(env):
    await _budget(env, "ACQUISITION_TENANT", str(TENANT), 1000)
    await _budget(env, "SIMULATION", "demo", 500)

    def simulate(environment: str, paise: int):
        return env.accounts.reserve_simulation(
            TENANT, environment, "llm_cloud", paise, T0 + timedelta(hours=1), ReservationIdentity(), uuid4()
        )

    assert (await simulate("demo", 300)).pinned_account_class == "SIMULATION"
    with pytest.raises(WalletError) as capped:
        await simulate("demo", 300)
    with pytest.raises(WalletError) as unbudgeted:
        await simulate("stage", 1)
    assert capped.value.code == unbudgeted.value.code == "SIMULATION_BUDGET_EXHAUSTED"
    assert await _count(env, "wallet_accounts", "account_class = 'ACQUISITION'") == 0

    assert (await _reserve(env, 1000)).pinned_account_class == "ACQUISITION"


async def test_platform_floor_succeeds_at_zero_balance_and_records_each_use_once(env):
    use, evidence = uuid4(), uuid4()
    first = await env.accounts.record_floor_use(
        TENANT, "demo", "STOP_ACK", "whatsapp_service", 25, evidence, use_id=use
    )
    replay = await env.accounts.record_floor_use(
        TENANT, "demo", "STOP_ACK", "whatsapp_service", 25, evidence, use_id=use
    )
    other = await env.accounts.record_floor_use(TENANT, "demo", "STOP_ACK", "whatsapp_service", 0, evidence)

    assert (first.recorded, replay.recorded, other.recorded) == (True, False, True)
    assert first.account_id == replay.account_id == other.account_id
    assert await _count(env, "wallet_floor_uses") == 2
    assert await _count(env, "wallet_lots") == 0 and await _count(env, "wallet_reservations") == 0
    floor = await env.accounts.ledger.get_account(TENANT, first.account_id)
    assert floor.account_class == "PLATFORM_FLOOR" and floor.environment == "demo"
    assert (await env.accounts.ledger.balance(floor, T0)).available_paise == 0


async def test_setup_grant_is_credited_once_per_relationship(env):
    await _grant(env, "SETUP", "1.0.0", {"amountPaise": 500})
    first = await env.accounts.open_setup_grant(TENANT, RELATIONSHIP, "DMA", "1.0.0")
    replay = await env.accounts.open_setup_grant(TENANT, RELATIONSHIP, "DMA", "1.0.0")
    second = await env.accounts.open_setup_grant(TENANT, OTHER_RELATIONSHIP, "DMA", "1.0.0")

    assert (first.created, first.credited_paise) == (True, 500)
    assert (replay.created, replay.lot_id) == (False, first.lot_id)
    assert second.created and second.account.account_id != first.account.account_id
    assert await _count(env, "wallet_lots", "source_kind = 'SETUP_GRANT'") == 2


async def test_setup_grant_exhaustion_is_a_typed_result_and_replays_return_the_reservation(env):
    await _grant(env, "SETUP", "1.0.0", {"amountPaise": 300})

    async def draw(paise: int, key: UUID, relationship: UUID = RELATIONSHIP, version: str = "1.0.0"):
        return await env.accounts.reserve_setup_grant(
            TENANT,
            relationship,
            "DMA",
            version,
            "llm_cloud",
            paise,
            T0 + timedelta(hours=1),
            ReservationIdentity(),
            key,
        )

    key = uuid4()
    first = await draw(200, key)
    replay = await draw(200, key)
    exhausted = await draw(200, uuid4())
    ungranted = await draw(1, uuid4(), OTHER_RELATIONSHIP, "9.9.9")

    assert first.status == "RESERVED" and first.receipt.pinned_account_class == "SETUP_GRANT"
    assert replay.status == "RESERVED" and replay.receipt.replayed
    assert (exhausted.status, exhausted.receipt) == ("SETUP_GRANT_EXHAUSTED", None)
    assert (ungranted.status, ungranted.receipt) == ("SETUP_GRANT_EXHAUSTED", None)
    assert await _count(env, "wallet_reservations") == 1


async def test_trial_grant_credits_the_versioned_grant_and_falls_back_to_settings(env):
    await _grant(env, "TRIAL", "1.0.0", {"threadUnits": {"whatsapp": 3, "email": 2}})
    await _grant(env, "TRIAL", "3.0.0", {"amountPaise": 100, "disabled": True})
    await _grant(env, "TRIAL", "4.0.0", {"amountPaise": 100}, state="DRAFT")
    trial_id = uuid4()
    window = (T0, T0 + timedelta(days=14))

    granted = await effective_grant(env.session, "TRIAL", "DMA", "1.0.0")
    assert granted.paise == 500 and granted.duration_days == 7 and not granted.disabled
    receipt = await env.accounts.credit_trial_grant(
        TENANT, RELATIONSHIP, "DMA", "1.0.0", trial_id, *window, grant=granted, fallback_units={"x": 9}
    )
    replay = await env.accounts.credit_trial_grant(
        TENANT, RELATIONSHIP, "DMA", "1.0.0", trial_id, *window, grant=granted, fallback_units={"x": 9}
    )
    account = await env.accounts.ledger.get_account(TENANT, receipt.account_id)

    assert (receipt.credited_paise, receipt.source_kind, receipt.lot_kind) == (500, "TRIAL_GRANT", "GRANT")
    assert (receipt.valid_from, receipt.valid_until) == window
    assert replay.replayed and replay.lot_id == receipt.lot_id
    assert (account.account_class, account.owner_kind, account.agent_version) == ("TRIAL", "PLATFORM", "1.0.0")
    assert await _count(env, "wallet_lots") == 1

    assert await effective_grant(env.session, "TRIAL", "DMA", "4.0.0") is None
    fallback = await env.accounts.credit_trial_grant(
        TENANT, OTHER_RELATIONSHIP, "DMA", "2.0.0", uuid4(), *window, grant=None, fallback_units={"a": 1, "b": 2}
    )
    assert fallback.credited_paise == 300
    disabled = await effective_grant(env.session, "TRIAL", "DMA", "3.0.0")
    assert disabled.disabled
    assert (
        await env.accounts.credit_trial_grant(
            TENANT, RELATIONSHIP, "DMA", "3.0.0", uuid4(), *window, grant=disabled
        )
        is None
    )
    assert await _count(env, "wallet_lots") == 2


def test_simulated_traffic_is_identified_only_by_verified_role_or_channel():
    assert is_simulated_traffic(roles=["visitor-simulator"], channel="WEB")
    assert is_simulated_traffic(roles=[], channel="SIMULATION")
    assert not is_simulated_traffic(roles=["customer"], channel="WEB")
    assert not is_simulated_traffic(roles=[], channel=None)
