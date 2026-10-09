# Implements: WC058-07 Professional Evaluation Adapter conformance
# Constitutional basis: C-036, C-041, C-048, C-049, C-050, C-055, C-056, C-057, C-076

from __future__ import annotations

import pytest

from evaluation_workflow import (
    AdapterAnswerProposal,
    TrialCapability,
    TrialDemonstration,
    TrialDemonstrationRequest,
    TrialDemonstrationService,
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


class ThreeSkillAdapter:
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
async def test_three_skill_fixture_uses_shared_contract() -> None:
    service = TrialDemonstrationService(ThreeSkillAdapter())
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
