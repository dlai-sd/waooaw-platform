# Implements: WC058-07 Professional Evaluation Adapter conformance
# constitutional_basis: C-036, C-041, C-048, C-049, C-050, C-055, C-056, C-057, C-076
from __future__ import annotations

import json
from pathlib import Path

import pytest

from evaluation_workflow import (
    TrialCapability,
    TrialDemonstrationRequest,
    TrialDemonstrationService,
)
from digital_marketing.evaluation import (
    DMA_RECIPES,
    DMA_TRIAL_CAPABILITIES,
    DigitalMarketingEvaluationAdapter,
)


ROOT = Path(__file__).resolve().parents[3]
DMA_CATALOG = ROOT / "src/digital-marketing-agent/integration/business-platform/digital-marketing-local-service.v1.json"


def capabilities() -> tuple[TrialCapability, ...]:
    return tuple(TrialCapability(capability_id, source_type) for capability_id, source_type in DMA_TRIAL_CAPABILITIES.items())


@pytest.mark.asyncio
async def test_dma_adapter_covers_exact_release_one_catalog() -> None:
    catalog = json.loads(DMA_CATALOG.read_text(encoding="utf-8"))
    catalog_skills = {item["skillId"] for item in catalog["skills"]}
    assert catalog_skills == {
        "CUSTOMER_PROFILING",
        "MARKET_RESEARCH_AND_MATURITY",
        "CONTENT_STRATEGY_AND_CALENDAR",
    }
    assert catalog_skills <= set(DMA_RECIPES)

    service = TrialDemonstrationService(DigitalMarketingEvaluationAdapter())
    results = [
        await service.demonstrate(
            TrialDemonstrationRequest(
                skill_id=skill_id,
                goal="Increase qualified local enquiries",
                context={"business_name": "Example Services", "location": "Pune"},
                capabilities=capabilities(),
            )
        )
        for skill_id in sorted(catalog_skills)
    ]

    assert len(results) == 3
    assert all(result.applicable for result in results)
    assert all(not result.external_actions for result in results)
    assert all(result.artifact and result.artifact["mode"] == "SIMULATION_ONLY" for result in results)


@pytest.mark.asyncio
async def test_context_activates_conditional_dma_skill_without_changing_shared_runtime() -> None:
    service = TrialDemonstrationService(DigitalMarketingEvaluationAdapter())
    result = await service.demonstrate(
        TrialDemonstrationRequest(
            skill_id="AGENCY_OPERATIONS",
            goal="Standardise client delivery",
            context={"agency_mode": "true"},
            capabilities=capabilities(),
        )
    )
    assert result.applicable is True
    assert result.artifact_type == "agency-workspace-plan"


@pytest.mark.asyncio
async def test_dma_adapter_plans_exact_14_days_and_proposes_configuration() -> None:
    adapter = DigitalMarketingEvaluationAdapter()
    skills = tuple(DMA_RECIPES)
    suitability = await adapter.describe_suitability(
        "Increase qualified enquiries",
        {"business_name": "Example Services"},
    )
    plan = await adapter.plan_trial(14, skills)
    configuration = await adapter.propose_configuration(
        ("Increase qualified enquiries",),
        ("Qualified enquiry count",),
        skills,
    )

    assert len(plan) == 19
    assert suitability["outcome"] == "Increase qualified enquiries"
    assert min(item["day"] for item in plan) == 1
    assert max(item["day"] for item in plan) <= 14
    assert configuration["skills"] == skills
    assert configuration["requires_item_level_customer_decision"] is True
    with pytest.raises(ValueError, match="exactly 14"):
        await adapter.plan_trial(7, skills)
    with pytest.raises(ValueError, match="Unknown DMA skills"):
        await adapter.plan_trial(14, ("UNKNOWN",))
    with pytest.raises(ValueError, match="Unknown DMA skills"):
        await adapter.propose_configuration((), (), ("UNKNOWN",))


@pytest.mark.asyncio
async def test_dma_adapter_rejects_unknown_skill_and_missing_recipe_capability() -> None:
    adapter = DigitalMarketingEvaluationAdapter()
    with pytest.raises(ValueError, match="Unknown DMA skill"):
        await adapter.demonstrate(
            TrialDemonstrationRequest(
                "UNKNOWN",
                "Goal",
                {},
                capabilities(),
            )
        )
    with pytest.raises(ValueError, match="Required trial capability unavailable"):
        await adapter.demonstrate(
            TrialDemonstrationRequest(
                "CUSTOMER_PROFILING",
                "Goal",
                {},
                (TrialCapability("approved-template", "APPROVED_TEMPLATE"),),
            )
        )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "unsafe_capability",
    [
        TrialCapability("paid-provider", "PUBLIC_FREE_SOURCE", paid=True),
        TrialCapability("publisher", "DETERMINISTIC_TOOL", external_mutation=True),
        TrialCapability("unknown-source", "PROVIDER_API"),
    ],
)
async def test_shared_runtime_rejects_paid_external_or_unknown_capabilities(
    unsafe_capability: TrialCapability,
) -> None:
    service = TrialDemonstrationService(DigitalMarketingEvaluationAdapter())
    with pytest.raises(ValueError, match="local, free, approved, or synthetic"):
        await service.demonstrate(
            TrialDemonstrationRequest(
                skill_id="CUSTOMER_PROFILING",
                goal="Profile business",
                context={},
                capabilities=(unsafe_capability,),
            )
        )
