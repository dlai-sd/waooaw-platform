# Implements: WC058-07 Professional Evaluation Adapter conformance
# constitutional_basis: C-036, C-041, C-048, C-049, C-050, C-055, C-056, C-057, C-076
from __future__ import annotations

import json
from pathlib import Path

import pytest

from evaluation_workflow import (
    AdapterAnswerProposal,
    TrialCapability,
    TrialDemonstration,
    TrialDemonstrationRequest,
    TrialDemonstrationService,
)
from professionals.digital_marketing import (
    DMA_RECIPES,
    DMA_TRIAL_CAPABILITIES,
    DigitalMarketingEvaluationAdapter,
)


ROOT = Path(__file__).resolve().parents[2]
DMA_CATALOG = ROOT / "src/business-platform/Catalog/Professionals/digital-marketing-local-service.v1.json"


def capabilities() -> tuple[TrialCapability, ...]:
    return tuple(TrialCapability(capability_id, source_type) for capability_id, source_type in DMA_TRIAL_CAPABILITIES.items())


@pytest.mark.asyncio
async def test_dma_adapter_covers_exact_catalog_and_all_19_demonstrations() -> None:
    catalog = json.loads(DMA_CATALOG.read_text(encoding="utf-8"))
    catalog_skills = {item["skillId"] for item in catalog["skills"]}
    assert len(catalog_skills) == 19
    assert set(DMA_RECIPES) == catalog_skills

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

    assert len(results) == 19
    assert sum(result.applicable for result in results) == 17
    assert all(not result.external_actions for result in results)
    assert all(result.artifact and result.artifact["mode"] == "SIMULATION_ONLY" for result in results if result.applicable)
    assert all(result.reason and result.activation_condition for result in results if not result.applicable)


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


class ResultAdapter:
    def __init__(self, result: TrialDemonstration) -> None:
        self.result = result

    async def demonstrate(self, request: TrialDemonstrationRequest) -> TrialDemonstration:
        return self.result


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "result,error",
    [
        (TrialDemonstration("OTHER", True, "artifact", {}, ("safe",)), "different skill"),
        (TrialDemonstration("SKILL", True, "artifact", {}, ("safe",), ("publish",)), "external actions"),
        (TrialDemonstration("SKILL", True, "artifact", {}, ("undeclared",)), "undeclared"),
        (TrialDemonstration("SKILL", True, None, {}, ("safe",)), "simulated artifact"),
        (TrialDemonstration("SKILL", True, "artifact", {}, ("safe",), reason="not applicable"), "cannot carry"),
        (TrialDemonstration("SKILL", False, None, None, (), reason="reason"), "activation condition"),
    ],
)
async def test_shared_runtime_rejects_invalid_adapter_results(
    result: TrialDemonstration,
    error: str,
) -> None:
    service = TrialDemonstrationService(ResultAdapter(result))
    with pytest.raises(ValueError, match=error):
        await service.demonstrate(
            TrialDemonstrationRequest(
                "SKILL",
                "Goal",
                {},
                (TrialCapability("safe", "LOCAL_INFERENCE"),),
            )
        )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "demonstration_request,error",
    [
        (TrialDemonstrationRequest("", "Goal", {}, (TrialCapability("safe", "LOCAL_INFERENCE"),)), "skill and goal"),
        (TrialDemonstrationRequest("SKILL", "", {}, (TrialCapability("safe", "LOCAL_INFERENCE"),)), "skill and goal"),
        (TrialDemonstrationRequest("SKILL", "Goal", {}, ()), "capabilities are required"),
        (
            TrialDemonstrationRequest(
                "SKILL",
                "Goal",
                {},
                (
                    TrialCapability("safe", "LOCAL_INFERENCE"),
                    TrialCapability("safe", "LOCAL_INFERENCE"),
                ),
            ),
            "identifiers must be unique",
        ),
    ],
)
async def test_shared_runtime_rejects_invalid_demonstration_requests(
    demonstration_request: TrialDemonstrationRequest,
    error: str,
) -> None:
    service = TrialDemonstrationService(
        ResultAdapter(
            TrialDemonstration("SKILL", True, "artifact", {}, ("safe",)),
        )
    )
    with pytest.raises(ValueError, match=error):
        await service.demonstrate(demonstration_request)


class ThreeSkillNonDmaAdapter:
    async def describe_suitability(
        self,
        outcome: str,
        confirmed_context: dict[str, str],
    ) -> dict[str, object]:
        return {"outcome": outcome}

    async def answer_interview(
        self,
        question: str,
        evidence_context: tuple[str, ...],
    ) -> tuple[AdapterAnswerProposal, ...]:
        return (AdapterAnswerProposal("LIMITATION", "Fixture answer."),)

    async def demonstrate(self, request: TrialDemonstrationRequest) -> TrialDemonstration:
        if request.skill_id not in {"FORECAST", "SCHEDULE", "SUMMARISE"}:
            raise ValueError("Unknown fixture skill")
        return TrialDemonstration(
            skill_id=request.skill_id,
            applicable=True,
            artifact_type="fixture-artifact",
            artifact={"skill": request.skill_id, "goal": request.goal},
            capability_ids=("fixture-local",),
        )

    async def plan_trial(
        self,
        days: int,
        applicable_skills: tuple[str, ...],
    ) -> tuple[dict[str, object], ...]:
        return tuple({"day": index + 1, "skill_id": skill} for index, skill in enumerate(applicable_skills))

    async def propose_configuration(
        self,
        goals: tuple[str, ...],
        measures: tuple[str, ...],
        skills: tuple[str, ...],
    ) -> dict[str, object]:
        return {"goals": goals, "measures": measures, "skills": skills}


@pytest.mark.asyncio
async def test_non_dma_three_skill_fixture_uses_same_shared_contract() -> None:
    service = TrialDemonstrationService(ThreeSkillNonDmaAdapter())
    fixture_capabilities = (TrialCapability("fixture-local", "LOCAL_INFERENCE"),)
    results = [
        await service.demonstrate(
            TrialDemonstrationRequest(
                skill_id=skill_id,
                goal="Fixture goal",
                context={},
                capabilities=fixture_capabilities,
            )
        )
        for skill_id in ("FORECAST", "SCHEDULE", "SUMMARISE")
    ]
    assert [result.skill_id for result in results] == ["FORECAST", "SCHEDULE", "SUMMARISE"]
