# Implements: WC-115 R017-R019, R064-R066, R097-R098
# Constitutional basis: C-023, C-035, C-059, C-076, C-079, ADR-051
# IB: N/A - Founder-assigned WC-115

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from runtime_contract.employment import (
    ConformanceScenario,
    EmploymentInterfaceManifest,
    GovernanceReferences,
    ImmutableContractReference,
    InductionManifest,
    OperationsManifest,
    PerformanceAssessment,
    PlanningManifest,
)


def _ref(name: str) -> ImmutableContractReference:
    return ImmutableContractReference(
        contractRef=name,
        contractVersion="1",
        contractDigest="a" * 64,
    )


def _manifest(agent_type: str) -> EmploymentInterfaceManifest:
    return EmploymentInterfaceManifest(
        agentType=agent_type,
        agentVersion="1.0.0",
        manifestVersion="1.0.0",
        governance=GovernanceReferences(
            agentSpecification=_ref(f"{agent_type}:spec"),
            promptPolicy=_ref(f"{agent_type}:prompt"),
            toolProfile=_ref(f"{agent_type}:tools"),
            decisionConsequenceMap=_ref(f"{agent_type}:consequence"),
        ),
        induction=InductionManifest(
            requirementSetVersion="1",
            mandatoryContext=("customer-outcome",),
            dependencyTypes=("authority-source",),
            readinessRules=("mandatory-confirmed",),
            domainSummaryAdapter=_ref(f"{agent_type}:summary"),
        ),
        planning=PlanningManifest(
            supportedGoalTypes=("outcome",),
            milestoneTypes=("review",),
            calendarConstraints=("iana-time-zone",),
            materialChangeRules=("authority-change",),
            performanceMeasureTypes=("outcome-state",),
            planAdapter=_ref(f"{agent_type}:plan"),
        ),
        operations=OperationsManifest(
            operatingCycleTypes=("bounded-cycle",),
            workItemTypes=("governed-work",),
            reassessmentTriggers=("dependency-loss",),
            outcomeAdapter=_ref(f"{agent_type}:outcome"),
            billingProfile=_ref(f"{agent_type}:billing"),
            degradationProfile=_ref(f"{agent_type}:degradation"),
            shorterMissedReviewThreshold=2,
        ),
        conformanceScenarios=(
            ConformanceScenario(
                scenarioId=f"{agent_type}:generic-employment",
                evidenceRef=f"test:evidence:{agent_type}",
                result="PASS",
                validatedProtocolVersion="1.0-candidate",
                validatedManifestVersion="1.0.0",
                validatedAt=datetime.now(timezone.utc),
            ),
        ),
    )


@pytest.mark.parametrize("agent_type", ["digital-marketing", "trading", "tutor"])
def test_cew_fit_17_neutral_agents_implement_the_same_generic_contract(
    agent_type: str,
) -> None:
    manifest = _manifest(agent_type)

    assert manifest.protocol_version == "1.0-candidate"
    assert manifest.agent_type == agent_type
    assert manifest.operations.shorter_missed_review_threshold == 2


def test_cew_fit_08_performance_assessment_requires_explicit_attribution() -> None:
    with pytest.raises(ValidationError):
        PerformanceAssessment(
            assessmentVersion="assessment-1",
            reviewPeriodRef="period-1",
            outcomeLabel="Qualified customer outcome",
            outcomeState="UNKNOWN",
            attributionBasis="",
            attributionConfidence=0,
            agentPerformanceState="UNKNOWN",
            missedReviewPeriods=0,
            evidenceRefs=(),
            limitations=("Owner evidence unavailable.",),
            producedAt=datetime.now(timezone.utc),
        )
