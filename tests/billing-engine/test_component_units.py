# Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C4-08
# Constitutional basis: C-059, C-088, C-089, C-063
"""Component units: the four kinds, pacing, idempotency, swaps and the cost tolerance."""

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

from wc136_commercial_ddl import COMPONENT_DDL, install  # noqa: E402
from markup.package_models import PackageBody  # noqa: E402
from meter.component_units import (  # noqa: E402
    ComponentUnitError,
    ComponentUnitService,
    cost_tolerance_verdict,
    initial_quantity,
    released_units,
)

START = datetime(2026, 1, 1, tzinfo=timezone.utc)
END = START + timedelta(days=30)
TENANT = UUID("11111111-1111-4111-8111-111111111111")
RELATIONSHIP = UUID("44444444-4444-4444-8444-444444444444")
INSTANCE = UUID("77777777-7777-4777-8777-777777777777")
PACKAGE_ID = UUID("88888888-8888-4888-8888-888888888888")


def _component(component_id: str, kind: str, quantity: int, cadence: str = "SPREAD", maximum: int | None = None):
    body = {
        "componentId": component_id,
        "kind": kind,
        "quantity": quantity,
        "cadence": cadence,
        "priceAllocationPaise": 100,
        "recipe": [],
    }
    if maximum is not None:
        body["selectableMaximum"] = maximum
    return body


def _package() -> PackageBody:
    return PackageBody.model_validate(
        {
            "agentType": "marketing",
            "agentVersion": "1",
            "packageCode": "STARTER",
            "displayName": "Starter",
            "billingPeriodDays": 30,
            "priceInclGstPaise": 1000,
            "infrastructureSharePaise": 0,
            "components": [
                _component("POSTS", "COUNTED", 4),
                _component("PAGES", "SELECTED", 3, "UPFRONT", 2),
                _component("INBOX", "TIME_ACCESS", 1, "UPFRONT"),
                _component("CALLS", "CAPACITY", 2, "UPFRONT"),
            ],
        }
    )


class _Clock:
    def __init__(self, at: datetime) -> None:
        self.at = at

    def __call__(self) -> datetime:
        return self.at


@pytest_asyncio.fixture
async def env(wallet_db):
    async with wallet_db() as session:
        await install(session, COMPONENT_DDL)
        clock = _Clock(START)
        service = ComponentUnitService(session, swaps_per_period=1, now=clock)
        await service.open_period(TENANT, RELATIONSHIP, INSTANCE, PACKAGE_ID, _package(), START, END)
        yield SimpleNamespace(session=session, service=service, clock=clock)


def test_pacing_curve_for_four_units_in_thirty_days() -> None:
    released = [released_units(4, "SPREAD", START, END, START + timedelta(days=day)) for day in (0, 7, 8, 15, 22, 23, 29, 30)]
    assert released == [0, 0, 1, 2, 2, 3, 3, 4]


def test_weekly_and_upfront_cadence() -> None:
    assert released_units(8, "WEEKLY", START, END, START + timedelta(days=13)) == 8 * 7 // 30
    assert released_units(8, "UPFRONT", START, END, START) == 8
    assert released_units(8, "SPREAD", START, END, START - timedelta(days=1)) == 0


def test_cost_tolerance_verdicts() -> None:
    assert cost_tolerance_verdict(100, 100, "0.2", "0.1") == "WITHIN"
    assert cost_tolerance_verdict(111, 100, "0.2", "0.1") == "ALERT"
    assert cost_tolerance_verdict(121, 100, "0.2", "0.1") == "OVER_TOLERANCE"


def test_selected_quantity_is_capped_by_selectable_maximum() -> None:
    component = _package().components[1]
    assert initial_quantity(component) == 2


@pytest.mark.asyncio
async def test_consume_before_release_is_refused(env) -> None:
    with pytest.raises(ComponentUnitError) as refused:
        await env.service.consume(TENANT, RELATIONSHIP, "POSTS", uuid4(), uuid4())
    assert refused.value.code == "COMPONENT_NOT_YET_RELEASED"


@pytest.mark.asyncio
async def test_consume_counts_once_per_evidence_and_replays(env) -> None:
    env.clock.at = START + timedelta(days=8)
    evidence, key = uuid4(), uuid4()
    first = await env.service.consume(TENANT, RELATIONSHIP, "POSTS", evidence, key)
    retry = await env.service.consume(TENANT, RELATIONSHIP, "POSTS", evidence, uuid4())
    same_key = await env.service.consume(TENANT, RELATIONSHIP, "POSTS", evidence, key)
    assert (first.used, first.remaining, first.replayed) == (1, 3, False)
    assert retry.replayed and retry.used == 1 and same_key.replayed
    assert retry.entry_id == first.entry_id


@pytest.mark.asyncio
async def test_consume_beyond_released_amount_then_exhaustion(env) -> None:
    env.clock.at = START + timedelta(days=8)
    await env.service.consume(TENANT, RELATIONSHIP, "POSTS", uuid4(), uuid4())
    with pytest.raises(ComponentUnitError) as early:
        await env.service.consume(TENANT, RELATIONSHIP, "POSTS", uuid4(), uuid4())
    assert early.value.code == "COMPONENT_NOT_YET_RELEASED"
    env.clock.at = END - timedelta(seconds=1)
    for _ in range(3):
        await env.service.consume(TENANT, RELATIONSHIP, "POSTS", uuid4(), uuid4())
    with pytest.raises(ComponentUnitError) as exhausted:
        await env.service.consume(TENANT, RELATIONSHIP, "POSTS", uuid4(), uuid4())
    assert exhausted.value.code == "COMPONENT_EXHAUSTED"
    assert await env.service.available_units(TENANT, RELATIONSHIP, "POSTS") == 0


@pytest.mark.asyncio
async def test_changed_replay_of_a_key_conflicts_and_non_completed_is_refused(env) -> None:
    env.clock.at = START + timedelta(days=8)
    key = uuid4()
    await env.service.consume(TENANT, RELATIONSHIP, "POSTS", uuid4(), key)
    with pytest.raises(ComponentUnitError) as changed:
        await env.service.consume(TENANT, RELATIONSHIP, "POSTS", uuid4(), key)
    assert changed.value.code == "COMPONENT_IDEMPOTENCY_CONFLICT"
    with pytest.raises(ComponentUnitError) as refused:
        await env.service.consume(TENANT, RELATIONSHIP, "POSTS", uuid4(), uuid4(), outcome="FAILED")
    assert refused.value.code == "COMPONENT_OUTCOME_NOT_COMPLETED"


@pytest.mark.asyncio
async def test_kind_mismatch_and_unknown_component(env) -> None:
    with pytest.raises(ComponentUnitError) as mismatch:
        await env.service.record_access(TENANT, RELATIONSHIP, "POSTS", uuid4())
    assert mismatch.value.code == "COMPONENT_KIND_MISMATCH"
    with pytest.raises(ComponentUnitError) as unknown:
        await env.service.consume(TENANT, RELATIONSHIP, "NOPE", uuid4(), uuid4())
    assert unknown.value.code == "COMPONENT_UNKNOWN"


@pytest.mark.asyncio
async def test_selected_needs_proof_respects_maximum_and_swap_limit(env) -> None:
    with pytest.raises(ComponentUnitError) as no_proof:
        await env.service.select(TENANT, RELATIONSHIP, "PAGES", "page-a", None, uuid4())
    assert no_proof.value.code == "COMPONENT_CONNECTION_REQUIRED"
    balance = {item.component_id: item for item in await env.service.balances(TENANT, RELATIONSHIP)}
    assert balance["PAGES"].used == 0 and balance["PAGES"].quantity == 2

    await env.service.select(TENANT, RELATIONSHIP, "PAGES", "page-a", uuid4(), uuid4())
    await env.service.select(TENANT, RELATIONSHIP, "PAGES", "page-b", uuid4(), uuid4())
    with pytest.raises(ComponentUnitError) as full:
        await env.service.select(TENANT, RELATIONSHIP, "PAGES", "page-c", uuid4(), uuid4())
    assert full.value.code == "COMPONENT_SLOTS_FULL"

    swapped = await env.service.swap(TENANT, RELATIONSHIP, "PAGES", "page-a", "page-c", uuid4(), uuid4())
    assert swapped.used == 2
    with pytest.raises(ComponentUnitError) as limit:
        await env.service.swap(TENANT, RELATIONSHIP, "PAGES", "page-b", "page-d", uuid4(), uuid4())
    assert limit.value.code == "COMPONENT_SWAP_LIMIT"
    with pytest.raises(ComponentUnitError) as unknown_item:
        await env.service.swap(TENANT, RELATIONSHIP, "PAGES", "page-z", "page-d", uuid4(), uuid4())
    assert unknown_item.value.code == "COMPONENT_ITEM_UNKNOWN"


@pytest.mark.asyncio
async def test_failed_connection_consumes_no_slot_and_deselect_frees_one(env) -> None:
    with pytest.raises(ComponentUnitError):
        await env.service.select(TENANT, RELATIONSHIP, "PAGES", "page-a", None, uuid4())
    assert (await env.service.select(TENANT, RELATIONSHIP, "PAGES", "page-a", uuid4(), uuid4())).used == 1
    assert (await env.service.deselect(TENANT, RELATIONSHIP, "PAGES", "page-a", uuid4())).used == 0


@pytest.mark.asyncio
async def test_selected_replay_does_not_take_a_second_slot(env) -> None:
    proof, key = uuid4(), uuid4()
    first = await env.service.select(TENANT, RELATIONSHIP, "PAGES", "page-a", proof, key)
    again = await env.service.select(TENANT, RELATIONSHIP, "PAGES", "page-a", proof, key)
    assert again.replayed and again.used == first.used == 1


@pytest.mark.asyncio
async def test_time_access_consumes_nothing_per_use(env) -> None:
    for _ in range(3):
        receipt = await env.service.record_access(TENANT, RELATIONSHIP, "INBOX", uuid4())
    assert (receipt.used, receipt.remaining) == (0, 1)


@pytest.mark.asyncio
async def test_capacity_counts_at_close_once_per_session(env) -> None:
    key = uuid4()
    first = await env.service.close(TENANT, RELATIONSHIP, "CALLS", "session-1", key)
    replay = await env.service.close(TENANT, RELATIONSHIP, "CALLS", "session-1", key)
    await env.service.close(TENANT, RELATIONSHIP, "CALLS", "session-2", uuid4())
    assert first.used == 1 and replay.replayed
    with pytest.raises(ComponentUnitError) as exhausted:
        await env.service.close(TENANT, RELATIONSHIP, "CALLS", "session-3", uuid4())
    assert exhausted.value.code == "COMPONENT_EXHAUSTED"


@pytest.mark.asyncio
async def test_open_period_is_idempotent(env) -> None:
    again = await env.service.open_period(TENANT, RELATIONSHIP, INSTANCE, PACKAGE_ID, _package(), START, END)
    assert len(again) == 4
    count = (await env.session.execute(text("SELECT COUNT(*) FROM business.component_units"))).scalar_one()
    assert count == 4
