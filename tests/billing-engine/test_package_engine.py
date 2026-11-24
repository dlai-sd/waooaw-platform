# Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C4-06
# Constitutional basis: C-059, C-088, C-089, C-091
"""Package projection, cost floor and package rules (WC-136 C4-06)."""

from __future__ import annotations

import copy
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent))

from pricing_support import (  # noqa: E402
    AGENT_TYPE,
    AGENT_VERSION,
    DMA_BASE,
    DMA_FLOOR_PENDING,
    PROACTIVE_THREAD,
    START,
    FakeReference,
    dma_declarations,
    dma_package_body,
    dma_rates,
)

from markup.bundle_engine import BundleEngine  # noqa: E402
from markup.package_engine import (  # noqa: E402
    SqlPackageReferenceData,
    ThreadRate,
    base_price_paise,
    cadence_consistent,
    evaluate_package,
    margin_on_revenue_pct,
    marked_up_rate_paise,
    minimum_compliant_base_paise,
    minimum_compliant_price_paise,
    parse_package_body,
    project_package,
    round_half_up_div,
    thread_ids_of,
)
from markup.package_models import PackageComponent  # noqa: E402

MARGIN = 55


def _codes(evaluation):
    return [violation.code for violation in evaluation.violations]


async def _evaluate(body, *, reference=None, margin=MARGIN, require_availability=False, declarations=None, overrides=None):
    return await evaluate_package(
        parse_package_body(body),
        reference=reference or FakeReference(),
        declarations=declarations or dma_declarations(),
        minimum_margin_pct=margin,
        require_availability=require_availability,
        rate_overrides=overrides,
    )


def test_dma_illustration_floor_excludes_pending_proactive_messages() -> None:
    projection = project_package(parse_package_body(dma_package_body()), dma_rates(), MARGIN)
    assert projection.cost_floor_paise == DMA_FLOOR_PENDING == 19628
    assert projection.base_price_paise == DMA_BASE == 169492
    assert projection.gst_paise == 200000 - 169492
    assert projection.margin_pct == pytest.approx(88.42)
    proactive = next(item for item in projection.component_costs if item.component_id == "PROACTIVE_MESSAGE")
    assert proactive.total_cost_paise == 0
    assert projection.unauthorized_thread_ids == [PROACTIVE_THREAD]


def test_minimum_compliant_price_re_adds_gst_after_dividing_by_one_minus_margin() -> None:
    assert minimum_compliant_base_paise(19628, MARGIN) == 43618
    assert minimum_compliant_price_paise(19628, MARGIN, 18) == 51469
    assert base_price_paise(51469, 18) >= 43618 > base_price_paise(51468, 18)
    projection = project_package(parse_package_body(dma_package_body()), dma_rates(), MARGIN)
    assert projection.minimum_compliant_base_paise == 43618
    assert projection.minimum_compliant_price_paise == 51469
    assert projection.minimum_margin_pct == 55.0


def test_thread_rations_are_derived_from_recipes_and_quantities() -> None:
    projection = project_package(parse_package_body(dma_package_body()), dma_rates(), MARGIN)
    assert projection.thread_rations == {
        "llm_mid_gemini": 12,
        "llm_pro": 30,
        PROACTIVE_THREAD: 30,
        "whatsapp_window": 30,
    }
    body = dma_package_body()
    body["components"][1]["recipe"].append({"threadId": "whatsapp_window", "unitsPerUnit": 2})
    ration = project_package(parse_package_body(body), dma_rates(), MARGIN).thread_rations
    assert ration["whatsapp_window"] == 30 + 60


def test_rounding_is_half_up_and_deterministic() -> None:
    assert round_half_up_div(5, 2) == 3
    assert round_half_up_div(4, 2) == 2
    assert round_half_up_div(7, 3) == 2
    assert base_price_paise(200000, 18) == 169492
    assert base_price_paise(118, 18) == 100
    assert marked_up_rate_paise(300, 10, 15, 8) == 399
    assert marked_up_rate_paise(50, "0.5", "0.5", "0") == 51
    assert margin_on_revenue_pct(0, 10) is None
    first = project_package(parse_package_body(dma_package_body()), dma_rates(), MARGIN)
    again = project_package(parse_package_body(dma_package_body()), dma_rates(), MARGIN)
    assert first == again


def test_minimum_margin_must_be_below_one_hundred_percent() -> None:
    with pytest.raises(ValueError):
        minimum_compliant_base_paise(1000, 100)


@pytest.mark.parametrize(
    ("cadence", "quantity", "period", "expected"),
    [
        ("DAILY", 30, 30, True),
        ("DAILY", 29, 30, False),
        ("WEEKLY", 4, 30, True),
        ("WEEKLY", 3, 30, False),
        ("WEEKLY", 5, 6, False),
        ("SPREAD", 1, 30, True),
        ("UPFRONT", 1, 30, True),
    ],
)
def test_cadence_must_be_able_to_release_the_quantity(cadence: str, quantity: int, period: int, expected: bool) -> None:
    component = PackageComponent.model_validate(
        {
            "componentId": "X",
            "kind": "COUNTED",
            "quantity": quantity,
            "cadence": cadence,
            "priceAllocationPaise": 1,
            "recipe": [{"threadId": "t", "unitsPerUnit": 1}],
        }
    )
    assert cadence_consistent(component, period) is expected


async def test_a_complete_package_with_authorized_threads_is_valid() -> None:
    evaluation = await _evaluate(dma_package_body())
    assert evaluation.valid
    assert evaluation.violations == []
    assert evaluation.projection.cost_floor_paise == DMA_FLOOR_PENDING + 30 * 5


async def test_price_below_the_floor_is_rejected_with_the_minimum_compliant_price() -> None:
    evaluation = await _evaluate(dma_package_body(), margin=90)
    assert _codes(evaluation) == ["PRICING_BELOW_FLOOR"]
    details = evaluation.violations[0].details
    floor = evaluation.projection.cost_floor_paise
    needed = minimum_compliant_base_paise(floor, 90)
    assert details["costFloorPaise"] == floor
    assert details["minimumCompliantPricePaise"] == minimum_compliant_price_paise(floor, 90, 18)
    assert base_price_paise(details["minimumCompliantPricePaise"], 18) >= needed
    assert base_price_paise(details["minimumCompliantPricePaise"] - 1, 18) < needed
    compliant = await _evaluate(dma_package_body(price=details["minimumCompliantPricePaise"]), margin=90)
    assert compliant.valid


async def test_missing_margin_policy_blocks_the_package() -> None:
    evaluation = await _evaluate(dma_package_body(), margin=None)
    assert _codes(evaluation) == ["PRICING_MARGIN_POLICY_MISSING"]


async def test_allocations_must_add_up_exactly_to_the_price() -> None:
    body = dma_package_body()
    body["components"][1]["priceAllocationPaise"] += 1
    evaluation = await _evaluate(body)
    assert _codes(evaluation) == ["PACKAGE_ALLOCATION_MISMATCH"]
    assert evaluation.violations[0].details == {"allocatedPaise": 200001, "pricePaise": 200000}


async def test_every_component_needs_a_recipe() -> None:
    body = dma_package_body()
    body["components"][3]["recipe"] = []
    evaluation = await _evaluate(body)
    assert _codes(evaluation) == ["PACKAGE_RECIPE_MISSING"]
    assert evaluation.violations[0].details["componentId"] == "CHANNEL"


async def test_recipe_threads_need_an_active_founder_authorized_entry() -> None:
    pending = FakeReference(dma_rates())
    evaluation = await _evaluate(dma_package_body(), reference=pending)
    assert _codes(evaluation) == ["RECIPE_THREAD_NOT_AUTHORIZED"]
    assert evaluation.violations[0].details["threadId"] == PROACTIVE_THREAD
    unknown = dma_rates(proactive_authorized=True)
    del unknown["llm_pro"]
    missing = await _evaluate(dma_package_body(), reference=FakeReference(unknown))
    assert "RECIPE_THREAD_NOT_AUTHORIZED" in _codes(missing)
    assert missing.projection.unauthorized_thread_ids == ["llm_pro"]


async def test_unknown_component_and_kind_mismatch_are_reported() -> None:
    body = dma_package_body()
    body["components"][2]["componentId"] = "MYSTERY"
    body["components"][1]["kind"] = "CAPACITY"
    evaluation = await _evaluate(body)
    assert sorted(_codes(evaluation)) == ["PACKAGE_COMPONENT_KIND_MISMATCH", "PACKAGE_COMPONENT_UNKNOWN"]


async def test_unknown_agent_version_declaration_blocks_the_package() -> None:
    body = dma_package_body()
    body["agentVersion"] = "9.9.9"
    evaluation = await _evaluate(body)
    assert "PACKAGE_DECLARATION_UNAVAILABLE" in _codes(evaluation)


async def test_cadence_contradiction_is_reported() -> None:
    body = dma_package_body()
    body["components"][1]["quantity"] = 10
    evaluation = await _evaluate(body)
    assert _codes(evaluation) == ["PACKAGE_CADENCE_INCONSISTENT"]


async def test_selectable_maximum_belongs_to_selected_components_only() -> None:
    body = dma_package_body()
    del body["components"][3]["selectableMaximum"]
    body["components"][2]["selectableMaximum"] = 2
    evaluation = await _evaluate(body)
    assert sorted(_codes(evaluation)) == ["PACKAGE_SELECTABLE_MAXIMUM_NOT_ALLOWED", "PACKAGE_SELECTABLE_MAXIMUM_REQUIRED"]


async def test_proactive_message_with_quantity_thirty_is_mandatory() -> None:
    wrong_quantity = dma_package_body()
    wrong_quantity["components"][0]["quantity"] = 29
    assert _codes(await _evaluate(wrong_quantity)) == ["PACKAGE_PROACTIVE_MESSAGE_REQUIRED"]
    absent = dma_package_body()
    del absent["components"][0]
    assert "PACKAGE_PROACTIVE_MESSAGE_REQUIRED" in _codes(await _evaluate(absent))


async def test_duplicate_component_is_reported() -> None:
    body = dma_package_body()
    body["components"].append(copy.deepcopy(body["components"][3]))
    assert "PACKAGE_COMPONENT_DUPLICATE" in _codes(await _evaluate(body))


async def test_agent_without_authorized_billing_profile_is_refused() -> None:
    evaluation = await _evaluate(dma_package_body(), reference=FakeReference(authorized_agents=()))
    assert _codes(evaluation) == ["BILLING_PROFILE_NOT_AUTHORIZED"]


async def test_sale_readiness_gate_names_every_component_that_is_not_available() -> None:
    declarations = dma_declarations(overrides={"CHANNEL": "DEFAULT_OFF", "CONTENT_POST": "UNAVAILABLE"})
    authorizable = await _evaluate(dma_package_body(), declarations=declarations)
    assert authorizable.valid
    for_sale = await _evaluate(dma_package_body(), declarations=declarations, require_availability=True)
    assert _codes(for_sale) == ["PACKAGE_COMPONENT_NOT_AVAILABLE"] * 2
    assert {item.details["componentId"] for item in for_sale.violations} == {"CHANNEL", "CONTENT_POST"}
    assert (await _evaluate(dma_package_body(), require_availability=True)).valid


async def test_rate_overrides_drive_what_if_floors_without_touching_the_catalogue() -> None:
    reference = FakeReference()
    base = await _evaluate(dma_package_body(), reference=reference)
    raised = await _evaluate(
        dma_package_body(), reference=reference, overrides={"whatsapp_window": ThreadRate("whatsapp_window", 700, True)}
    )
    assert raised.projection.cost_floor_paise == base.projection.cost_floor_paise + 30 * (700 - 70)
    assert reference.rates["whatsapp_window"].marked_up_cost_paise == 70


def test_thread_ids_of_lists_distinct_sorted_recipe_threads() -> None:
    bodies = [parse_package_body(dma_package_body()), parse_package_body(dma_package_body(package_code="PRO"))]
    assert thread_ids_of(bodies) == ["llm_mid_gemini", "llm_pro", PROACTIVE_THREAD, "whatsapp_window"]


async def test_sql_reference_data_authorizes_only_active_founder_authorized_threads() -> None:
    result = MagicMock()
    result.fetchall.return_value = [
        SimpleNamespace(thread_id="a", marked_up_cost_paise=5, status="ACTIVE", founder_authorized_at=START),
        SimpleNamespace(thread_id="b", marked_up_cost_paise=0, status="PENDING_FOUNDER_AUTH", founder_authorized_at=None),
        SimpleNamespace(thread_id="c", marked_up_cost_paise=9, status="ACTIVE", founder_authorized_at=None),
    ]
    session = MagicMock()
    session.execute = AsyncMock(return_value=result)
    rates = await SqlPackageReferenceData(session).thread_rates(["a", "b", "c"])
    assert [rates[key].authorized for key in "abc"] == [True, False, False]
    assert rates["a"].marked_up_cost_paise == 5
    assert session.execute.await_args.args[1] == {"thread_ids": ["a", "b", "c"]}
    session.execute.reset_mock()
    assert await SqlPackageReferenceData(session).thread_rates([]) == {}
    session.execute.assert_not_awaited()


@pytest.mark.parametrize(("status", "expected"), [("FOUNDER_AUTHORIZED", True), ("DRAFT", False), (None, False)])
async def test_sql_reference_data_reads_billing_profile_authority(status: str | None, expected: bool) -> None:
    result = MagicMock()
    result.fetchone.return_value = None if status is None else (status,)
    session = MagicMock()
    session.execute = AsyncMock(return_value=result)
    assert await SqlPackageReferenceData(session).billing_profile_authorized(AGENT_TYPE) is expected
    assert session.execute.await_args.args[1] == {"agent_type": AGENT_TYPE}


async def test_bundle_engine_narrows_the_lookup_by_agent_version_only_when_given() -> None:
    result = MagicMock()
    result.fetchone.return_value = (19628,)
    db = MagicMock()
    db.execute = AsyncMock(return_value=result)
    engine = BundleEngine(db=db)
    assert await engine.cost_floor(AGENT_TYPE, "STARTER", agent_version=AGENT_VERSION) == 19628
    assert db.execute.await_args.args[1]["agent_version"] == AGENT_VERSION
    assert await engine.cost_floor(AGENT_TYPE, "STARTER") == 19628
    assert db.execute.await_args.args[1]["agent_version"] is None


# WC-169 R017 to R019: package description, per-package target margin and the suggested price.
from markup.package_engine import suggested_price_paise  # noqa: E402


def test_the_suggested_price_is_exact_before_it_is_rounded_up_to_a_whole_rupee() -> None:
    # Cost floor 825 rupees at a 40 percent margin: base 1,375 rupees, GST-inclusive 1,622.50, suggested 1,623.
    assert suggested_price_paise(82500, 40, 18) == 162300
    # A helper that rounds before the rupee step would give 100 paise here; the exact value is 100.3 paise.
    assert suggested_price_paise(85, 0, 18) == 200
    assert suggested_price_paise(100000, 0, 18) == 118000


def test_a_target_margin_of_zero_on_the_package_is_a_real_target_not_a_fallback() -> None:
    body = dma_package_body()
    body["targetMarginPct"] = 0
    projection = project_package(parse_package_body(body), dma_rates(proactive_authorized=True, proactive_cost=100), MARGIN)
    assert projection.target_margin_pct == 0.0
    assert projection.suggested_price_incl_gst_paise == suggested_price_paise(projection.cost_floor_paise, 0, 18)


def test_without_a_package_margin_the_policy_minimum_margin_is_the_target() -> None:
    projection = project_package(parse_package_body(dma_package_body()), dma_rates(proactive_authorized=True, proactive_cost=100), MARGIN)
    assert projection.target_margin_pct == float(MARGIN)
    assert projection.suggested_price_incl_gst_paise == suggested_price_paise(projection.cost_floor_paise, MARGIN, 18)
    assert projection.suggestion_status == "COMPLETE"


def test_an_unauthorized_thread_makes_the_suggestion_incomplete_and_shows_its_cost_line() -> None:
    projection = project_package(parse_package_body(dma_package_body()), dma_rates(), MARGIN)
    assert projection.suggestion_status == "INCOMPLETE"
    assert PROACTIVE_THREAD in projection.unauthorized_thread_ids
    line = next(item for item in projection.cost_lines if item.thread_id == PROACTIVE_THREAD)
    assert line.authorized is False


def test_a_thread_with_no_rate_at_all_is_unknown_not_zero() -> None:
    rates = dma_rates(proactive_authorized=True, proactive_cost=100)
    del rates["llm_pro"]
    projection = project_package(parse_package_body(dma_package_body()), rates, MARGIN)
    line = next(item for item in projection.cost_lines if item.thread_id == "llm_pro")
    assert line.unit_cost_paise is None and line.line_cost_paise is None
    assert projection.suggestion_status == "INCOMPLETE"


def test_a_component_without_a_recipe_makes_the_suggestion_incomplete() -> None:
    body = dma_package_body()
    body["components"][1]["recipe"] = []
    projection = project_package(parse_package_body(body), dma_rates(proactive_authorized=True, proactive_cost=100), MARGIN)
    assert projection.uncosted_component_ids == ["CONTENT_POST"]
    assert projection.suggestion_status == "INCOMPLETE"


def test_a_package_with_no_known_cost_has_no_usable_suggestion() -> None:
    body = dma_package_body()
    body["infrastructureSharePaise"] = 0
    for component in body["components"]:
        component["recipe"] = []
    projection = project_package(parse_package_body(body), dma_rates(), MARGIN)
    assert projection.cost_floor_paise == 0
    assert projection.suggested_price_incl_gst_paise is None
    assert projection.suggestion_status == "UNUSABLE"


def test_with_neither_a_package_margin_nor_a_policy_margin_there_is_no_suggestion() -> None:
    projection = project_package(parse_package_body(dma_package_body()), dma_rates(proactive_authorized=True, proactive_cost=100), None)
    assert projection.suggested_price_incl_gst_paise is None
    assert projection.suggestion_status == "UNUSABLE"


def test_the_description_and_target_margin_are_optional_and_bounded() -> None:
    plain = parse_package_body(dma_package_body())
    assert plain.description is None and plain.target_margin_pct is None
    described = dma_package_body()
    described["description"] = "For a business new to digital marketing with no accounts yet."
    described["targetMarginPct"] = 40
    parsed = parse_package_body(described)
    assert parsed.description.startswith("For a business") and parsed.target_margin_pct == 40
    for bad in ({"description": "x" * 501}, {"targetMarginPct": 100}, {"targetMarginPct": -1}):
        with pytest.raises(Exception):  # noqa: B017 - pydantic ValidationError
            parse_package_body({**dma_package_body(), **bad})
