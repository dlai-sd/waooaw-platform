# Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C5-08
# Constitutional basis: C-059, C-088, C-089, C-091
"""Funding and margin dashboards over fixed ledger data: aggregates, tolerance states, empty states, no personal data."""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))

from markup.package_engine import ThreadRate, project_package  # noqa: E402
from markup.package_models import PackageBody  # noqa: E402
from pricing import dashboard  # noqa: E402
from pricing.models import PricingKind  # noqa: E402
from pricing_support import PACKAGE_SUBJECT, START, dma_package_body, make_harness  # noqa: E402

ALLOWED_KEYS = {
    "schemaVersion", "generatedAt", "periodFrom", "periodTo", "spendByAccountClass", "accountClass", "spentPaise",
    "spendByTenant", "tenantRef", "spendByCampaign", "campaignRef", "leadSpend", "leadRef", "costPerLeadPaise",
    "costPerConversationPaise", "trialToHire", "trials", "hires", "conversionPercent", "grantConsumption", "grantKind",
    "agentType", "agentVersion", "consumedPaise", "grantedPaise", "componentCost", "componentId", "recipeCostPaise",
    "actualCostPaise", "impliedMarginPercent", "toleranceState", "events", "eventKind", "count", "breakers", "breaker",
    "state", "liveMarginBreaches", "packages", "packageVersionId", "subjectKey", "priceInclGstPaise", "basePricePaise",
    "costFloorPaise", "marginPercent", "minimumMarginPercent",
}
TENANT = "11111111-1111-4111-8111-111111111111"


class FakeReader:
    def __init__(self, **rows) -> None:
        self.rows = rows
        self.periods: list[dashboard.Period] = []

    def _rows(self, name, period=None):
        if period is not None:
            self.periods.append(period)
        return self.rows.get(name, [])

    async def spend_by_account_class(self, period):
        return self._rows("class", period)

    async def spend_by_tenant(self, period):
        return self._rows("tenant")

    async def spend_by_campaign(self, period):
        return self._rows("campaign")

    async def spend_by_lead(self, period):
        return self._rows("lead")

    async def funnel(self, period):
        return self.rows.get("funnel", {"trials": 0, "hires": 0, "leads": 0})

    async def grant_consumption(self, period):
        return self._rows("grants")

    async def settled_by_component(self, period):
        return self._rows("components")

    async def lot_events(self, period):
        return self.rows.get("lots", {"topups": 0, "exhaustions": 0})

    async def breakers(self):
        return self._rows("breakers")


LEDGER = {
    "class": [
        {"account_class": "ACQUISITION", "spent": 3000},
        {"account_class": "TRIAL", "spent": 1000},
        {"account_class": "SUBSCRIPTION", "spent": 8000},
    ],
    "tenant": [{"tenant_ref": TENANT, "spent": 12000}],
    "campaign": [{"campaign_ref": "spring-launch", "spent": 3000}],
    "lead": [{"lead_ref": "visitor-1", "spent": 1800}, {"lead_ref": "visitor-2", "spent": 1200}],
    "funnel": {"trials": 4, "hires": 1, "leads": 2},
    "grants": [
        {"account_class": "TRIAL", "agent_type": "DMA", "agent_version": "1.0.0", "consumed": 300, "granted": 1000},
        {"account_class": "SETUP_GRANT", "agent_type": "DMA", "agent_version": "1.0.0", "consumed": 0, "granted": 500},
        {"account_class": "SUBSCRIPTION", "agent_type": "DMA", "agent_version": "1.0.0", "consumed": 9, "granted": 9},
    ],
    "components": [
        {"component_id": "CONTENT_POST", "settlements": 2, "settled": 1000},
        {"component_id": "CHAT_REPLY", "settlements": 5, "settled": 390},
        {"component_id": "PROACTIVE_MESSAGE", "settlements": 3, "settled": 15},
        {"component_id": "NOT_IN_ANY_PACKAGE", "settlements": 1, "settled": 99},
    ],
    "lots": {"topups": 2, "exhaustions": 1},
    "breakers": [{"breaker": "razorpay", "state": "OPEN"}, {"breaker": "other", "state": "unknown"}],
}


def _keys(value) -> set[str]:
    if isinstance(value, dict):
        return set(value) | {key for item in value.values() for key in _keys(item)}
    if isinstance(value, list):
        return {key for item in value for key in _keys(item)}
    return set()


def _harness():
    harness = make_harness()
    harness.repository.seed(PricingKind.PACKAGE, PACKAGE_SUBJECT, dma_package_body())
    return harness


async def _funding(harness, reader, **period):
    return await dashboard.funding_dashboard(
        None,
        harness.service,
        period_from=period.get("start"),
        period_to=period.get("end"),
        now=START,
        reader_factory=lambda _: reader,
        reference_factory=lambda _: harness.reference,
    )


async def test_the_funding_dashboard_aggregates_fixed_ledger_data():
    harness = _harness()

    report = await _funding(harness, FakeReader(**LEDGER), start=date(2026, 2, 1), end=date(2026, 2, 28))

    assert (report["periodFrom"], report["periodTo"]) == ("2026-02-01", "2026-02-28")
    assert {row["accountClass"]: row["spentPaise"] for row in report["spendByAccountClass"]} == {
        "ACQUISITION": 3000,
        "SETUP_GRANT": 0,
        "TRIAL": 1000,
        "SUBSCRIPTION": 8000,
        "PLATFORM_FLOOR": 0,
        "SIMULATION": 0,
    }
    assert report["spendByTenant"] == [{"tenantRef": TENANT, "spentPaise": 12000}]
    assert report["spendByCampaign"] == [{"campaignRef": "spring-launch", "spentPaise": 3000}]
    assert report["costPerLeadPaise"] == 1500
    assert report["costPerConversationPaise"] == 1000
    assert report["trialToHire"] == {"trials": 4, "hires": 1, "conversionPercent": 25.0}
    assert report["grantConsumption"] == [
        {"grantKind": "TRIAL", "agentType": "DMA", "agentVersion": "1.0.0", "consumedPaise": 300, "grantedPaise": 1000},
        {"grantKind": "SETUP", "agentType": "DMA", "agentVersion": "1.0.0", "consumedPaise": 0, "grantedPaise": 500},
    ]
    assert report["events"] == [{"eventKind": "EXHAUSTION", "count": 1}, {"eventKind": "TOPUP", "count": 2}]
    assert report["breakers"] == [{"breaker": "razorpay", "state": "OPEN"}]
    assert report["liveMarginBreaches"] == 0


async def test_the_period_window_includes_the_last_day_and_defaults_to_thirty_days_ending_today():
    reader = FakeReader()

    explicit = await _funding(_harness(), reader, start=date(2026, 2, 1), end=date(2026, 2, 28))
    defaulted = await _funding(_harness(), reader)

    first, last = reader.periods[0], reader.periods[-1]
    assert first.start.isoformat() == "2026-02-01T00:00:00+00:00"
    assert first.end.isoformat() == "2026-03-01T00:00:00+00:00"
    assert (defaulted["periodFrom"], defaulted["periodTo"]) == ("2026-01-31", "2026-03-01")
    assert (last.first_day, last.last_day) == (date(2026, 1, 31), date(2026, 3, 1))
    assert explicit["periodTo"] == "2026-02-28"


async def test_a_lead_is_shown_only_through_its_pseudonymous_reference():
    report = await _funding(_harness(), FakeReader(**LEDGER))

    expected = "lead_" + hashlib.sha256(b"visitor-1").hexdigest()[:32]
    assert [row["leadRef"] for row in report["leadSpend"]][0] == expected
    assert "visitor-1" not in json.dumps(report)
    assert all(row["leadRef"].startswith("lead_") and len(row["leadRef"]) == 37 for row in report["leadSpend"])


async def test_the_response_schema_carries_no_personal_field():
    funding = await _funding(_harness(), FakeReader(**LEDGER))
    margin = await dashboard.margin_dashboard(
        None, _harness().service, period_from=None, period_to=None, now=START,
        reader_factory=lambda _: FakeReader(**LEDGER), reference_factory=lambda _: _harness().reference,
    )

    assert _keys(funding) <= ALLOWED_KEYS
    assert _keys(margin) <= ALLOWED_KEYS
    assert not {key for key in _keys(funding) | _keys(margin) if key.lower() in {"email", "phone", "name", "mobile", "leadid"}}


async def test_actual_against_recipe_cost_gives_the_implied_margin_and_the_tolerance_state():
    report = await _funding(_harness(), FakeReader(**LEDGER))

    components = {row["componentId"]: row for row in report["componentCost"]}
    assert set(components) == {"CONTENT_POST", "CHAT_REPLY", "PROACTIVE_MESSAGE"}
    assert (components["CONTENT_POST"]["recipeCostPaise"], components["CONTENT_POST"]["actualCostPaise"]) == (400, 500)
    assert components["CONTENT_POST"]["toleranceState"] == "EXCEEDED"
    assert components["CHAT_REPLY"]["toleranceState"] == "ALERT"
    assert components["PROACTIVE_MESSAGE"]["toleranceState"] == "WITHIN_TOLERANCE"
    unit_revenue = dashboard.base_price_paise(120000, 18) / 30
    assert components["CONTENT_POST"]["impliedMarginPercent"] == pytest.approx(
        round(100 * (unit_revenue - 500) / unit_revenue, 2), abs=0.01
    )


async def test_without_a_policy_every_component_is_within_tolerance():
    harness = make_harness(with_policy=False)
    harness.repository.seed(PricingKind.PACKAGE, PACKAGE_SUBJECT, dma_package_body())

    report = await _funding(harness, FakeReader(**LEDGER))

    assert {row["toleranceState"] for row in report["componentCost"]} == {"WITHIN_TOLERANCE"}


async def test_every_section_is_empty_but_present_when_there_is_no_ledger_data():
    harness = make_harness()

    report = await _funding(harness, FakeReader())

    assert report["spendByTenant"] == report["spendByCampaign"] == report["leadSpend"] == []
    assert report["grantConsumption"] == report["componentCost"] == report["breakers"] == []
    assert (report["costPerLeadPaise"], report["costPerConversationPaise"]) == (0, 0)
    assert report["trialToHire"] == {"trials": 0, "hires": 0, "conversionPercent": 0.0}
    assert {row["spentPaise"] for row in report["spendByAccountClass"]} == {0}
    assert [row["count"] for row in report["events"]] == [0, 0]


async def test_a_rate_rise_below_the_floor_is_counted_as_a_live_margin_breach():
    harness = _harness()
    harness.reference.rates["llm_pro"] = ThreadRate("llm_pro", 40000, True)

    report = await _funding(harness, FakeReader())

    assert report["liveMarginBreaches"] == 1


async def test_the_margin_dashboard_projects_every_effective_package_at_current_rates():
    harness = _harness()
    body = PackageBody.model_validate(dma_package_body())
    projection = project_package(body, harness.reference.rates, 55)

    report = await dashboard.margin_dashboard(
        None, harness.service, period_from=None, period_to=None, now=START,
        reader_factory=lambda _: FakeReader(**LEDGER), reference_factory=lambda _: harness.reference,
    )

    assert len(report["packages"]) == 1
    row = report["packages"][0]
    assert row["subjectKey"] == PACKAGE_SUBJECT
    assert (row["priceInclGstPaise"], row["basePricePaise"], row["costFloorPaise"]) == (
        projection.price_incl_gst_paise, projection.base_price_paise, projection.cost_floor_paise
    )
    assert row["marginPercent"] == projection.margin_pct
    assert row["minimumMarginPercent"] == 55.0
    assert report["liveMarginBreaches"] == 0
    assert len(report["componentCost"]) == 3


async def test_an_empty_catalogue_gives_an_empty_margin_dashboard():
    report = await dashboard.margin_dashboard(
        None, make_harness().service, period_from=None, period_to=None, now=START,
        reader_factory=lambda _: FakeReader(), reference_factory=lambda _: make_harness().reference,
    )

    assert report["packages"] == [] and report["componentCost"] == [] and report["liveMarginBreaches"] == 0
