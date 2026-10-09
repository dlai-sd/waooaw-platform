"""WC-116 direct Package A employment conformance tests."""

# Implements: architecture/reference/components/dma-employment-conformance-work-component.md §19
# Constitutional basis: C-023, C-035, C-059, C-063, C-071, C-076, C-079, C-094

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from digital_marketing.employment import (
    MATURITY_DIMENSIONS,
    DmaEmploymentSemantics,
    MaterialChangeContext,
    MaturityDimension,
    PlanContext,
    RelationshipContext,
    assess_maturity,
    resolve_compatibility_tuple,
)
from digital_marketing.service import create_service_app
from runtime_contract import AdapterContractError
from runtime_contract.employment import (
    DependencyIsolationRequest,
    MaterialChangeRequest,
    PerformanceAssessment,
    PlanValidationRequest,
)

NOW = datetime(2026, 10, 9, 7, 30, tzinfo=timezone.utc)
RELATIONSHIP = UUID("11111111-1111-1111-1111-111111111111")
OTHER_RELATIONSHIP = UUID("22222222-2222-2222-2222-222222222222")
ALL_SKILLS = frozenset(
    {
        "CUSTOMER_PROFILING",
        "MARKET_RESEARCH_AND_MATURITY",
        "CONTENT_STRATEGY_AND_CALENDAR",
    }
)


def performance(
    _relationship_id: UUID,
    review_period_ref: str,
    *,
    missed: int = 0,
) -> PerformanceAssessment:
    return PerformanceAssessment(
        assessmentVersion="1.0.0",
        reviewPeriodRef=review_period_ref,
        outcomeLabel="Profile coverage",
        outcomeState="UNKNOWN",
        attributionBasis="Customer-owned outcome evidence is not yet available.",
        attributionConfidence=0,
        agentPerformanceState="MEETING",
        missedReviewPeriods=missed,
        diagnosisRequired=missed >= 2,
        correctiveProposalRequired=missed >= 2,
        evidenceRefs=("evidence:profile-coverage",),
        limitations=("No customer-owned conversion evidence.",),
        producedAt=NOW,
    )


def semantics(
    selected: frozenset[str] = ALL_SKILLS,
    *,
    missed: int = 0,
) -> DmaEmploymentSemantics:
    return DmaEmploymentSemantics(
        lambda _relationship_id: RelationshipContext(selected),
        lambda _relationship_id, _plan_version: PlanContext(
            source_version="profile-1",
            mandatory_requirements_confirmed=True,
        ),
        lambda _relationship_id, _patch_ref: MaterialChangeContext(
            calendar_within_accepted_tolerance=True,
        ),
        lambda relationship_id, review_period_ref: performance(
            relationship_id,
            review_period_ref,
            missed=missed,
        ),
        clock=lambda: NOW,
    )


def plan(**changes: object) -> PlanValidationRequest:
    values: dict[str, object] = {
        "schemaVersion": "1.0",
        "manifestVersion": "1.0.0",
        "requirementSetVersion": "1.0.0",
        "planVersion": "plan-1",
        "goalType": "UNDERSTAND_CURRENT_POSITION",
        "skillRefs": ("CUSTOMER_PROFILING",),
        "milestoneTypes": ("PROFILE_CONFIRMED",),
        "sourceVersion": "profile-1",
    }
    values.update(changes)
    return PlanValidationRequest.model_validate(values)


def test_manifest_and_induction_are_exact_closed_package_a_contracts() -> None:
    subject = semantics(frozenset({"MARKET_RESEARCH_AND_MATURITY"}))

    manifest = subject.manifest("DIGITAL_MARKETING_LOCAL_SERVICE", "1.0.0", "1.0.0")
    requirements = subject.induction_requirements(RELATIONSHIP, "1.0.0")
    by_ref = {item.requirement_ref: item for item in requirements.requirements}

    assert manifest.protocol_version == "1.0-candidate"
    assert manifest.operations.shorter_missed_review_threshold is None
    assert len(requirements.requirements) == 17
    assert by_ref["DMA-IND-011"].mandatory is True
    assert by_ref["DMA-IND-014"].mandatory is False
    assert by_ref["DMA-IND-012"].mandatory is False
    with pytest.raises(AdapterContractError, match="DOMAIN_EMPLOYMENT_VERSION_UNSUPPORTED"):
        subject.manifest("DIGITAL_MARKETING_LOCAL_SERVICE", "1.0.0", "2.0.0")


def test_compatibility_tuple_requires_exact_source_and_evidence_identities() -> None:
    result = resolve_compatibility_tuple(
        "a" * 40,
        "sha256:" + "b" * 64,
    )

    assert result["professionalTypeId"] == "DIGITAL_MARKETING_LOCAL_SERVICE"
    assert result["professionalVersion"] == "1.0.0"
    assert result["specificationRevision"] == "3.1"
    assert result["sourceCommit"] == "a" * 40
    assert result["evidenceDigest"] == "sha256:" + "b" * 64
    with pytest.raises(ValueError, match="DMA_SOURCE_COMMIT_INVALID"):
        resolve_compatibility_tuple("main", "sha256:" + "b" * 64)
    with pytest.raises(ValueError, match="DMA_EVIDENCE_DIGEST_INVALID"):
        resolve_compatibility_tuple("a" * 40, "pending")


def test_manifest_contract_references_match_repository_content() -> None:
    root = Path(__file__).resolve().parents[3]
    manifest = json.loads(
        (root / "src/digital-marketing-agent/contracts/employment-interface-manifest.v1.json").read_text(encoding="utf-8")
    )
    references = [
        *manifest["governance"].values(),
        manifest["induction"]["domainSummaryAdapter"],
        manifest["planning"]["planAdapter"],
        manifest["operations"]["outcomeAdapter"],
        manifest["operations"]["billingProfile"],
        manifest["operations"]["degradationProfile"],
    ]

    for reference in references:
        path = root / reference["contractRef"].split("#", maxsplit=1)[0]
        assert path.is_file()
        assert hashlib.sha256(path.read_bytes()).hexdigest() == reference["contractDigest"]


@pytest.mark.asyncio
async def test_dma_semantics_use_the_existing_private_wc115_routes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DMA_ARTIFACT_DIGEST", "sha256:" + "ab" * 32)
    monkeypatch.setenv("DMA_ADMISSION_CONTENT_DIGEST", "sha256:" + "cd" * 32)
    monkeypatch.setenv("PR_SERVICE_JWT_SECRET", "test-service-assertion")

    async def authorize(_request: object) -> None:
        return None

    app = create_service_app(semantics(), authorize)
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://adapter",
    ) as client:
        response = await client.get(
            "/internal/v1/employment-interface/manifest"
            "?agentType=DIGITAL_MARKETING_LOCAL_SERVICE"
            "&agentVersion=1.0.0"
            "&manifestVersion=1.0.0",
            headers={"X-Correlation-Id": str(uuid4())},
        )

    assert response.status_code == 200
    assert response.json()["protocolVersion"] == "1.0-candidate"


@pytest.mark.parametrize(
    ("plan_request", "state"),
    [
        (plan(), "VALID"),
        (
            plan(
                goalType="PLAN_CONTENT_AND_CAMPAIGNS",
                skillRefs=("CONTENT_STRATEGY_AND_CALENDAR",),
                milestoneTypes=("CAMPAIGN_BRIEF_ACCEPTED",),
            ),
            "PARTIAL",
        ),
        (plan(goalType="RUN_PAID_ADS"), "INVALID"),
        (plan(manifestVersion="2.0.0"), "UNKNOWN"),
    ],
)
def test_plan_validation_has_closed_outcomes_and_idempotent_replay(
    plan_request: PlanValidationRequest,
    state: str,
) -> None:
    subject = semantics()
    idempotency_key = uuid4()

    first = subject.validate_plan(RELATIONSHIP, idempotency_key, plan_request)
    second = subject.validate_plan(RELATIONSHIP, idempotency_key, plan_request)

    assert first is second
    assert first.state == state
    with pytest.raises(AdapterContractError, match="DOMAIN_EMPLOYMENT_CONFLICT"):
        subject.validate_plan(
            RELATIONSHIP,
            idempotency_key,
            plan(planVersion="plan-2"),
        )
    assert subject.validate_plan(OTHER_RELATIONSHIP, idempotency_key, plan_request).state == state


@pytest.mark.parametrize(
    ("context", "expected"),
    [
        (
            PlanContext(
                source_version="profile-1",
                mandatory_requirements_confirmed=True,
                deferred_requirement_refs=("DMA-IND-009",),
                deferred_isolation_proven=True,
            ),
            "PARTIAL",
        ),
        (
            PlanContext(
                source_version="profile-1",
                mandatory_requirements_confirmed=True,
                deferred_requirement_refs=("DMA-IND-009",),
            ),
            "UNKNOWN",
        ),
        (
            PlanContext(
                source_version="profile-1",
                mandatory_requirements_confirmed=False,
            ),
            "INVALID",
        ),
        (
            PlanContext(
                source_version="profile-1",
                mandatory_requirements_confirmed=True,
                requested_side_effects=("PUBLISH",),
            ),
            "INVALID",
        ),
        (
            PlanContext(
                source_version="profile-2",
                mandatory_requirements_confirmed=True,
            ),
            "UNKNOWN",
        ),
        (
            PlanContext(
                source_version="profile-1",
                mandatory_requirements_confirmed=True,
                calendar_commitments_complete=False,
            ),
            "INVALID",
        ),
    ],
)
def test_plan_context_preserves_deferral_and_side_effect_boundaries(
    context: PlanContext,
    expected: str,
) -> None:
    subject = DmaEmploymentSemantics(
        lambda _relationship_id: RelationshipContext(ALL_SKILLS),
        lambda _relationship_id, _plan_version: context,
        lambda _relationship_id, _patch_ref: MaterialChangeContext(),
        lambda relationship_id, review_period_ref: performance(relationship_id, review_period_ref),
        clock=lambda: NOW,
    )

    assert subject.validate_plan(RELATIONSHIP, uuid4(), plan()).state == expected


def test_plan_rejects_coordinates_outside_package_a() -> None:
    result = semantics().validate_plan(
        RELATIONSHIP,
        uuid4(),
        plan(skillRefs=("UNAVAILABLE_SKILL",)),
    )

    assert result.state == "INVALID"
    assert result.unmet_domain_conditions == ("PACKAGE_A_COORDINATES_REQUIRED",)


@pytest.mark.parametrize(
    ("flags", "classification", "renewed"),
    [
        ((), "UNKNOWN", True),
        (("CALENDAR",), "NON_MATERIAL", False),
        (("OUTCOME",), "MATERIAL", True),
        (("MEASUREMENT",), "MATERIAL", True),
        (("AUTHORITY", "CREDENTIAL"), "MATERIAL", True),
    ],
)
def test_material_change_classification_fails_closed(
    flags: tuple[str, ...],
    classification: str,
    renewed: bool,
) -> None:
    request = MaterialChangeRequest.model_validate(
        {
            "schemaVersion": "1.0",
            "manifestVersion": "1.0.0",
            "currentPlanVersion": "plan-1",
            "candidatePatchRef": uuid4(),
            "protectedCategoryFlags": flags,
        }
    )

    result = semantics().classify_material_change(RELATIONSHIP, uuid4(), request)

    assert result.classification == classification
    assert result.renewed_agreement_required is renewed


def test_calendar_change_outside_tolerance_is_material() -> None:
    subject = DmaEmploymentSemantics(
        lambda _relationship_id: RelationshipContext(ALL_SKILLS),
        lambda _relationship_id, _plan_version: PlanContext(
            source_version="profile-1",
            mandatory_requirements_confirmed=True,
        ),
        lambda _relationship_id, _patch_ref: MaterialChangeContext(
            calendar_within_accepted_tolerance=False,
        ),
        lambda relationship_id, review_period_ref: performance(relationship_id, review_period_ref),
        clock=lambda: NOW,
    )
    request = MaterialChangeRequest.model_validate(
        {
            "schemaVersion": "1.0",
            "manifestVersion": "1.0.0",
            "currentPlanVersion": "plan-1",
            "candidatePatchRef": uuid4(),
            "protectedCategoryFlags": ("CALENDAR",),
        }
    )

    assert (
        subject.classify_material_change(
            RELATIONSHIP,
            uuid4(),
            request,
        ).classification
        == "MATERIAL"
    )


@pytest.mark.parametrize(
    ("dependency", "state", "candidate", "expected"),
    [
        (
            "PUBLIC_OBSERVATION",
            "LOST",
            ("MARKET_RESEARCH_AND_MATURITY",),
            "PROVEN_BOUNDED",
        ),
        ("PUBLIC_OBSERVATION", "LOST", ("CUSTOMER_PROFILING",), "NOT_BOUNDED"),
        (
            "MANIFEST_ADMISSION_COMPATIBILITY",
            "LOST",
            tuple(sorted(ALL_SKILLS)),
            "NOT_BOUNDED",
        ),
        ("UNKNOWN_NODE", "LOST", ("CUSTOMER_PROFILING",), "UNKNOWN"),
        ("PUBLIC_OBSERVATION", "UNKNOWN", ("MARKET_RESEARCH_AND_MATURITY",), "UNKNOWN"),
    ],
)
def test_dependency_isolation_distrusts_caller_completeness(
    dependency: str,
    state: str,
    candidate: tuple[str, ...],
    expected: str,
) -> None:
    request = DependencyIsolationRequest.model_validate(
        {
            "schemaVersion": "1.0",
            "manifestVersion": "1.0.0",
            "dependencyRef": dependency,
            "dependencyState": state,
            "candidateAffectedSkillRefs": candidate,
        }
    )

    result = semantics().evaluate_dependency_isolation(RELATIONSHIP, uuid4(), request)

    assert result.isolation == expected


def test_maturity_uses_equal_weights_threshold_rounding_and_missing_as_unknown() -> None:
    dimensions = {
        dimension_id: MaturityDimension(
            dimension_id=dimension_id,
            score=score,
            evidence_refs=(f"evidence:{dimension_id.lower()}",),
            confidence=Decimal("0.8"),
        )
        for dimension_id, score in zip(MATURITY_DIMENSIONS, (7, 8, 7, 8, 7, 8, 7, 8, 7, 8), strict=True)
    }
    published = assess_maturity(dimensions)
    assert published.audit_score == Decimal("7.5")
    assert published.display_level == 8
    assert published.evidence_coverage == "10/10"

    for dimension_id in MATURITY_DIMENSIONS[6:]:
        dimensions[dimension_id] = MaturityDimension(
            dimension_id=dimension_id,
            score=None,
            evidence_refs=(),
            confidence=Decimal("0"),
        )
    incomplete = assess_maturity(dimensions)
    assert incomplete.state == "MATURITY_ASSESSMENT_IN_PROGRESS"
    assert incomplete.audit_score is None
    assert incomplete.evidence_coverage == "6/10"

    dimensions[MATURITY_DIMENSIONS[0]] = MaturityDimension(
        dimension_id=MATURITY_DIMENSIONS[0],
        score=11,
        evidence_refs=("evidence:invalid",),
        confidence=Decimal("1"),
    )
    with pytest.raises(ValueError, match="DMA_MATURITY_SCORE_INVALID"):
        assess_maturity(dimensions)


def test_maturity_rejects_incomplete_and_mismatched_dimension_sets() -> None:
    dimensions = {
        dimension_id: MaturityDimension(
            dimension_id=dimension_id,
            score=7,
            evidence_refs=(f"evidence:{dimension_id.lower()}",),
            confidence=Decimal("0.8"),
        )
        for dimension_id in MATURITY_DIMENSIONS
    }

    incomplete = dict(dimensions)
    incomplete.pop(MATURITY_DIMENSIONS[-1])
    with pytest.raises(ValueError, match="DMA_MATURITY_DIMENSIONS_INVALID"):
        assess_maturity(incomplete)

    mismatched = dict(dimensions)
    mismatched[MATURITY_DIMENSIONS[0]] = MaturityDimension(
        dimension_id="WRONG_DIMENSION",
        score=7,
        evidence_refs=("evidence:wrong",),
        confidence=Decimal("0.8"),
    )
    with pytest.raises(ValueError, match="DMA_MATURITY_DIMENSION_ID_MISMATCH"):
        assess_maturity(mismatched)


def test_performance_keeps_customer_outcome_and_professional_state_independent() -> None:
    result = semantics(missed=2).performance_assessment(RELATIONSHIP, "2026-Q4")

    assert result.outcome_state == "UNKNOWN"
    assert result.agent_performance_state == "MEETING"
    assert result.diagnosis_required is True
    assert result.corrective_proposal_required is True


def test_dma_specific_source_is_confined_to_dedicated_subtree() -> None:
    root = Path(__file__).resolve().parents[3]
    forbidden = root / "src/agent-adapters/digital_marketing"

    assert not forbidden.exists()
    assert (root / "src/digital-marketing-agent/digital_marketing/employment.py").is_file()
