# Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C5-06
# Constitutional basis: C-059, C-088, C-089, C-090, C-091
"""The Demo pricing baseline file: seed rows conform to the validators and stay honest."""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from markup.package_engine import ThreadRate  # noqa: E402
from pricing.declarations import ManifestDeclarationSource  # noqa: E402
from pricing.models import ActorContext, EffectiveRole, PricingKind  # noqa: E402
from pricing.service import PricingService  # noqa: E402
from pricing.validators import canonical_body, parse_body, subject_key_for  # noqa: E402
from pricing_support import (  # noqa: E402
    FakeEvidence,
    FakeReference,
    FixedClock,
    InMemoryPricingRepository,
    policy_body,
)

ROOT = Path(__file__).resolve().parents[2]
BASELINE = ROOT / "infrastructure/postgres/init/99zzzzzzzz-wc136-11-demo-pricing-baseline.sql"
CONTRACTS = ROOT / "src/digital-marketing-agent/contracts"
ROW = re.compile(
    r"'136c0000-[0-9a-f-]+',\s*'(\w+)',\s*'([^']+)',\s*'(\w+)',\s*'(\{.*?\})'::JSONB",
    re.DOTALL,
)
ADMIN = ActorContext("admin-1", EffectiveRole.PRICING_ADMIN)


def _rows() -> list[tuple[str, str, str, dict]]:
    import json

    return [
        (kind, subject, state, json.loads(body))
        for kind, subject, state, body in ROW.findall(BASELINE.read_text(encoding="utf-8"))
    ]


def test_the_baseline_seeds_the_documented_rows():
    rows = _rows()
    by_kind = sorted(kind for kind, _, _, _ in rows)

    assert by_kind == ["BUDGET", "BUDGET", "BUDGET", "GRANT", "GRANT", "PACKAGE", "POLICY"]
    assert {state for kind, _, state, _ in rows if kind != "PACKAGE"} == {"EFFECTIVE"}
    assert [state for kind, _, state, _ in rows if kind == "PACKAGE"] == ["DRAFT"]


def test_every_seed_body_is_in_the_canonical_stored_form_of_its_validator():
    for kind, subject, _, body in _rows():
        model, violations = parse_body(PricingKind(kind), body)

        assert violations == [], (subject, violations)
        assert canonical_body(model) == body, subject
        assert subject_key_for(PricingKind(kind), model) == subject


def test_the_demo_ceiling_policy_and_starter_package_match_the_contract():
    bodies = {subject: body for _, subject, _, body in _rows()}
    ceiling = bodies["budget:ENVIRONMENT_CEILING|demo"]
    policy = bodies["policy:platform"]
    package = bodies["package:DIGITAL_MARKETING_LOCAL_SERVICE|1.0.0|STARTER"]
    components = {item["componentId"]: item for item in package["components"]}

    assert ceiling["maximumPaise"] == 50000
    assert policy["minimumMarginNote"] == "SEED_UNCONFIRMED"
    assert (policy["minimumMarginPct"], policy["paymentGraceDays"], policy["sunsetNoticeDays"]) == (55.0, 7, 30)
    assert (policy["costToleranceFraction"], policy["costAlertFraction"]) == (0.2, 0.1)
    assert (policy["upgradeTiming"], policy["downgradeTiming"]) == ("IMMEDIATE", "AT_RENEWAL")
    assert package["priceInclGstPaise"] == 200000 and package["gstRatePercent"] == 18
    assert "ILLUSTRATIVE_NOT_FOR_SALE" in package["displayName"]
    assert components["SOCIAL_PUBLICATION"]["quantity"] == 4
    assert components["AD_BOOST"]["quantity"] == 1
    assert components["SOCIAL_OBSERVATION"]["selectableMaximum"] == 4
    assert components["PROACTIVE_MESSAGE"]["quantity"] == 30
    assert sum(item["priceAllocationPaise"] for item in package["components"]) == 200000


def test_the_baseline_is_idempotent_and_flagged_as_seed_in_sql():
    sql = BASELINE.read_text(encoding="utf-8")

    assert "ON CONFLICT (kind, subject_key, version_no) DO NOTHING" in sql
    assert "ON CONFLICT (event_id) DO NOTHING" in sql
    assert "seed.body,\n    institutional.pricing_body_digest(seed.body), true," in sql
    assert "DROP TRIGGER" not in sql


async def test_the_illustrative_package_cannot_be_authorized_on_demo():
    repository = InMemoryPricingRepository()
    repository.seed(PricingKind.POLICY, "policy:platform", policy_body())
    reference = FakeReference(
        {
            "llm_mid_gemini": ThreadRate("llm_mid_gemini", 44, True),
            "image_gen_per_image": ThreadRate("image_gen_per_image", 210, True),
            "ad_spend_meta": ThreadRate("ad_spend_meta", 0, True),
            "whatsapp_template_utility": ThreadRate("whatsapp_template_utility", 0, False),
        },
        authorized_agents=("DIGITAL_MARKETING_LOCAL_SERVICE",),
    )
    service = PricingService(
        repository=repository,
        reference=reference,
        declarations=ManifestDeclarationSource.from_directory(CONTRACTS),
        evidence=FakeEvidence(),
        clock=FixedClock(),
    )
    package = next(body for kind, _, _, body in _rows() if kind == "PACKAGE")

    result = await service.create_draft(ADMIN, PricingKind.PACKAGE, package)

    codes = {violation.code for violation in result.violations}
    assert {"PACKAGE_COMPONENT_NOT_AVAILABLE", "RECIPE_THREAD_NOT_AUTHORIZED"} <= codes
    assert result.version.state.value == "DRAFT"
