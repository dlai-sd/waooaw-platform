# Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C4-12
# Constitutional basis: C-059, C-088, C-089, C-063
"""Proactive-message accounting: classification, the 30-per-period counter and its typed refusals."""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
import pytest_asyncio

sys.path.insert(0, str(Path(__file__).parent))

from wc136_commercial_ddl import COMPONENT_DDL, install  # noqa: E402
from markup.package_models import PROACTIVE_MESSAGE_COMPONENT_ID, PROACTIVE_MESSAGE_QUANTITY, PackageBody  # noqa: E402
from meter.component_units import ComponentUnitError, ComponentUnitService  # noqa: E402
from meter.proactive_messages import (  # noqa: E402
    ALLOWANCE_EXHAUSTED,
    COUNTED_STATUS,
    NO_ALLOWANCE,
    NOT_COUNTED_STATUS,
    PROACTIVE_COUNTED,
    PROACTIVE_UNCOUNTED,
    REPLY,
    ProactiveMessageAccounting,
    classify_message,
)

START = datetime(2026, 1, 1, tzinfo=timezone.utc)
END = START + timedelta(days=30)
TENANT = UUID("11111111-1111-4111-8111-111111111111")
RELATIONSHIP = UUID("44444444-4444-4444-8444-444444444444")
TRIAL_RELATIONSHIP = UUID("55555555-5555-4555-8555-555555555555")
INSTANCE = UUID("77777777-7777-4777-8777-777777777777")
PACKAGE_ID = UUID("88888888-8888-4888-8888-888888888888")


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
                {
                    "componentId": PROACTIVE_MESSAGE_COMPONENT_ID,
                    "kind": "COUNTED",
                    "quantity": PROACTIVE_MESSAGE_QUANTITY,
                    "cadence": "SPREAD",
                    "priceAllocationPaise": 0,
                    "recipe": [],
                }
            ],
        }
    )


class _Floor:
    def __init__(self) -> None:
        self.uses: dict[UUID, tuple] = {}

    async def record_floor_use(
        self, tenant_id, environment, purpose, component_id, paise, evidence_id, *, invocation_id=None, use_id=None
    ):
        recorded = use_id not in self.uses
        self.uses.setdefault(use_id, (tenant_id, environment, purpose, component_id, paise, evidence_id))
        return SimpleNamespace(recorded=recorded)


@pytest_asyncio.fixture
async def env(wallet_db):
    async with wallet_db() as session:
        await install(session, COMPONENT_DDL)
        components = ComponentUnitService(session, now=lambda: START)
        await components.open_period(TENANT, RELATIONSHIP, INSTANCE, PACKAGE_ID, _package(), START, END)
        floor = _Floor()
        yield SimpleNamespace(accounting=ProactiveMessageAccounting(components, floor), floor=floor)


@pytest.mark.parametrize(
    ("inside", "capacity", "emergency", "expected"),
    [
        (True, False, False, REPLY),
        (True, True, False, REPLY),
        (False, False, False, PROACTIVE_COUNTED),
        (False, True, False, PROACTIVE_UNCOUNTED),
        (False, False, True, PROACTIVE_UNCOUNTED),
    ],
)
def test_classification_table(inside: bool, capacity: bool, emergency: bool, expected: str) -> None:
    assert (
        classify_message(inside_service_window=inside, capacity_notice=capacity, emergency_alert=emergency)
        == expected
    )


@pytest.mark.asyncio
async def test_only_counted_messages_increment_the_counter(env) -> None:
    await env.accounting.account(TENANT, RELATIONSHIP, REPLY, uuid4())
    await env.accounting.account(TENANT, RELATIONSHIP, PROACTIVE_UNCOUNTED, uuid4())
    first = await env.accounting.account(TENANT, RELATIONSHIP, PROACTIVE_COUNTED, uuid4())
    assert (first.status, first.used, first.remaining, first.quantity) == (COUNTED_STATUS, 1, 29, 30)
    assert not first.deliver_in_portal


@pytest.mark.asyncio
async def test_the_same_message_counts_once(env) -> None:
    evidence = uuid4()
    await env.accounting.account(TENANT, RELATIONSHIP, PROACTIVE_COUNTED, evidence)
    again = await env.accounting.account(TENANT, RELATIONSHIP, PROACTIVE_COUNTED, evidence)
    assert again.used == 1


@pytest.mark.asyncio
async def test_the_thirty_first_message_is_refused_with_the_typed_result(env) -> None:
    for _ in range(PROACTIVE_MESSAGE_QUANTITY):
        decision = await env.accounting.account(TENANT, RELATIONSHIP, PROACTIVE_COUNTED, uuid4())
        assert decision.status == COUNTED_STATUS
    over = await env.accounting.account(TENANT, RELATIONSHIP, PROACTIVE_COUNTED, uuid4())
    assert over.status == ALLOWANCE_EXHAUSTED
    assert over.deliver_in_portal and over.remaining == 0


@pytest.mark.asyncio
async def test_capacity_notices_never_count_and_never_block(env) -> None:
    for _ in range(PROACTIVE_MESSAGE_QUANTITY):
        await env.accounting.account(TENANT, RELATIONSHIP, PROACTIVE_COUNTED, uuid4())
    evidence = uuid4()
    notice = await env.accounting.account(
        TENANT, RELATIONSHIP, PROACTIVE_UNCOUNTED, evidence, floor_paise=25
    )
    repeat = await env.accounting.account(
        TENANT, RELATIONSHIP, PROACTIVE_UNCOUNTED, evidence, floor_paise=25
    )
    assert notice.status == NOT_COUNTED_STATUS and not notice.deliver_in_portal
    assert notice.floor_recorded and not repeat.floor_recorded
    assert len(env.floor.uses) == 1
    (tenant, environment, purpose, component, paise, recorded_evidence), = env.floor.uses.values()
    assert (tenant, environment, component, paise, recorded_evidence) == (
        TENANT,
        "production",
        PROACTIVE_MESSAGE_COMPONENT_ID,
        25,
        evidence,
    )
    assert purpose == "PROACTIVE_UNCOUNTED"


@pytest.mark.asyncio
async def test_a_trial_relationship_has_no_allowance(env) -> None:
    decision = await env.accounting.account(TENANT, TRIAL_RELATIONSHIP, PROACTIVE_COUNTED, uuid4())
    assert decision.status == NO_ALLOWANCE
    assert decision.deliver_in_portal


@pytest.mark.asyncio
async def test_an_unknown_class_is_refused(env) -> None:
    with pytest.raises(ComponentUnitError) as refused:
        await env.accounting.account(TENANT, RELATIONSHIP, "BROADCAST", uuid4())
    assert refused.value.code == "PROACTIVE_CLASS_INVALID"
