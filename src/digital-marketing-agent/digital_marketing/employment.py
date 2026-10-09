"""DMA Package A semantics for the generic WC-115 employment interface."""

# Implements: architecture/reference/components/dma-employment-conformance-work-component.md §5-18
# Constitutional basis: C-023, C-035, C-041, C-049, C-059, C-063, C-071, C-079, C-094

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from threading import Lock
from typing import Any
from uuid import UUID

from runtime_contract import AdapterContractError
from runtime_contract.employment import (
    DependencyIsolationAssessment,
    DependencyIsolationRequest,
    DomainRequirement,
    EmploymentInterfaceManifest,
    InductionRequirementSet,
    MaterialChangeAssessment,
    MaterialChangeRequest,
    PerformanceAssessment,
    PlanValidationAssessment,
    PlanValidationRequest,
)

PACKAGE_ROOT = Path(__file__).resolve().parent.parent
CONTRACT_ROOT = PACKAGE_ROOT / "contracts"
MANIFEST_VERSION = "1.0.0"
REQUIREMENT_SET_VERSION = "1.0.0"
ASSESSMENT_VERSION = "1.0.0"
SHA256_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}$")

STABLE_SKILLS = frozenset(
    {
        "CUSTOMER_PROFILING",
        "MARKET_RESEARCH_AND_MATURITY",
        "CONTENT_STRATEGY_AND_CALENDAR",
    }
)
SUPPORTED_GOALS = frozenset(
    {
        "UNDERSTAND_CURRENT_POSITION",
        "PRIORITIZE_MARKETING_IMPROVEMENTS",
        "PLAN_CONTENT_AND_CAMPAIGNS",
    }
)
SUPPORTED_MILESTONES = frozenset(
    {
        "PROFILE_CONFIRMED",
        "MATURITY_ASSESSMENT_REVIEWED",
        "PRIORITIES_CONFIRMED",
        "CAMPAIGN_BRIEF_ACCEPTED",
        "CONTENT_CALENDAR_ACCEPTED",
    }
)
MATURITY_DIMENSIONS = (
    "BUSINESS_DIRECTION",
    "ONLINE_PRESENCE",
    "SEARCH_VISIBILITY",
    "CONTENT_CONSISTENCY",
    "CUSTOMER_ENGAGEMENT",
    "LEAD_HANDLING",
    "CUSTOMER_RETENTION",
    "MEASUREMENT",
    "IMPROVEMENT_DISCIPLINE",
    "GOVERNANCE_AND_TRUST",
)


@dataclass(frozen=True)
class RelationshipContext:
    selected_skill_refs: frozenset[str]


@dataclass(frozen=True)
class PlanContext:
    source_version: str
    mandatory_requirements_confirmed: bool
    deferred_requirement_refs: tuple[str, ...] = ()
    deferred_isolation_proven: bool = False
    requested_side_effects: tuple[str, ...] = ()
    calendar_commitments_complete: bool = True


@dataclass(frozen=True)
class MaterialChangeContext:
    calendar_within_accepted_tolerance: bool = False


@dataclass(frozen=True)
class MaturityDimension:
    dimension_id: str
    score: int | None
    evidence_refs: tuple[str, ...]
    confidence: Decimal
    limitations: tuple[str, ...] = ()
    disputed: bool = False
    stale: bool = False


@dataclass(frozen=True)
class MaturityAssessment:
    state: str
    audit_score: Decimal | None
    display_level: int | None
    evidence_coverage: str
    missing_dimensions: tuple[str, ...]


def assess_maturity(dimensions: Mapping[str, MaturityDimension]) -> MaturityAssessment:
    if set(dimensions) != set(MATURITY_DIMENSIONS):
        raise ValueError("DMA_MATURITY_DIMENSIONS_INVALID")

    scored: list[int] = []
    missing: list[str] = []
    for dimension_id in MATURITY_DIMENSIONS:
        dimension = dimensions[dimension_id]
        if dimension.dimension_id != dimension_id:
            raise ValueError("DMA_MATURITY_DIMENSION_ID_MISMATCH")
        if (
            dimension.score is None
            or not dimension.evidence_refs
            or dimension.disputed
            or dimension.stale
        ):
            missing.append(dimension_id)
            continue
        if not 1 <= dimension.score <= 10:
            raise ValueError("DMA_MATURITY_SCORE_INVALID")
        scored.append(dimension.score)

    coverage = f"{len(scored)}/10"
    if len(scored) < 7:
        return MaturityAssessment(
            state="MATURITY_ASSESSMENT_IN_PROGRESS",
            audit_score=None,
            display_level=None,
            evidence_coverage=coverage,
            missing_dimensions=tuple(missing),
        )

    audit_score = (Decimal(sum(scored)) / Decimal(len(scored))).quantize(
        Decimal("0.1"),
        rounding=ROUND_HALF_UP,
    )
    return MaturityAssessment(
        state="PUBLISHED",
        audit_score=audit_score,
        display_level=int(audit_score.quantize(Decimal("1"), rounding=ROUND_HALF_UP)),
        evidence_coverage=coverage,
        missing_dimensions=tuple(missing),
    )


def resolve_compatibility_tuple(
    source_commit: str,
    evidence_digest: str,
) -> dict[str, str]:
    if not COMMIT_PATTERN.fullmatch(source_commit):
        raise ValueError("DMA_SOURCE_COMMIT_INVALID")
    if not SHA256_PATTERN.fullmatch(evidence_digest):
        raise ValueError("DMA_EVIDENCE_DIGEST_INVALID")

    contract = _load_json("compatibility-tuple.v1.json")
    oci_digest = contract["ociDigest"]
    if not isinstance(oci_digest, str) or not SHA256_PATTERN.fullmatch(oci_digest):
        raise RuntimeError("DMA_OCI_DIGEST_INVALID")
    resolved: dict[str, str] = {}
    for key in (
        "professionalTypeId",
        "professionalVersion",
        "specificationRevision",
        "manifestVersion",
        "adapterVersion",
        "wc115ProtocolVersion",
        "ociDigest",
    ):
        value = contract.get(key)
        if not isinstance(value, str) or not value:
            raise RuntimeError("DMA_COMPATIBILITY_TUPLE_INVALID")
        resolved[key] = value
    return resolved | {
        "sourceCommit": source_commit,
        "evidenceDigest": evidence_digest,
    }


class DmaEmploymentSemantics:
    def __init__(
        self,
        context_provider: Callable[[UUID], RelationshipContext],
        plan_context_provider: Callable[[UUID, str], PlanContext],
        material_change_provider: Callable[[UUID, UUID], MaterialChangeContext],
        performance_provider: Callable[[UUID, str], PerformanceAssessment],
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._context_provider = context_provider
        self._plan_context_provider = plan_context_provider
        self._material_change_provider = material_change_provider
        self._performance_provider = performance_provider
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._manifest = EmploymentInterfaceManifest.model_validate(_load_json("employment-interface-manifest.v1.json"))
        self._requirement_contract = _load_json("induction-requirements.v1.json")
        self._dependency_graph = _load_json("dependency-graph.v1.json")
        self._replays: dict[tuple[str, UUID, UUID], tuple[str, Any]] = {}
        self._replay_lock = Lock()

    def manifest(
        self,
        agent_type: str,
        agent_version: str,
        manifest_version: str,
    ) -> EmploymentInterfaceManifest:
        if (
            agent_type != self._manifest.agent_type
            or agent_version != self._manifest.agent_version
            or manifest_version != self._manifest.manifest_version
        ):
            raise _contract_error("DOMAIN_EMPLOYMENT_VERSION_UNSUPPORTED")
        return self._manifest

    def induction_requirements(
        self,
        relationship_id: UUID,
        manifest_version: str,
    ) -> InductionRequirementSet:
        self._require_manifest(manifest_version)
        selected = self._context_provider(relationship_id).selected_skill_refs
        if not selected or not selected <= STABLE_SKILLS:
            raise _contract_error("DOMAIN_EMPLOYMENT_INVALID")

        requirements = tuple(
            DomainRequirement.model_validate(_requirement_payload(item, selected))
            for item in self._requirement_contract["requirements"]
        )
        return InductionRequirementSet(
            manifestVersion=MANIFEST_VERSION,
            requirementSetVersion=REQUIREMENT_SET_VERSION,
            requirements=requirements,
            producedAt=self._clock(),
        )

    def validate_plan(
        self,
        relationship_id: UUID,
        idempotency_key: UUID,
        request: PlanValidationRequest,
    ) -> PlanValidationAssessment:
        digest = _digest(request.model_dump(mode="json"))
        return self._once(
            "validate-plan",
            relationship_id,
            idempotency_key,
            digest,
            lambda: self._validate_plan(
                request,
                self._plan_context_provider(relationship_id, request.plan_version),
            ),
        )

    def classify_material_change(
        self,
        relationship_id: UUID,
        idempotency_key: UUID,
        request: MaterialChangeRequest,
    ) -> MaterialChangeAssessment:
        digest = _digest(request.model_dump(mode="json"))
        return self._once(
            "classify-material-change",
            relationship_id,
            idempotency_key,
            digest,
            lambda: self._classify_material_change(
                request,
                self._material_change_provider(relationship_id, request.candidate_patch_ref),
            ),
        )

    def evaluate_dependency_isolation(
        self,
        relationship_id: UUID,
        idempotency_key: UUID,
        request: DependencyIsolationRequest,
    ) -> DependencyIsolationAssessment:
        digest = _digest(request.model_dump(mode="json"))
        return self._once(
            "evaluate-dependency-isolation",
            relationship_id,
            idempotency_key,
            digest,
            lambda: self._evaluate_dependency_isolation(request),
        )

    def performance_assessment(
        self,
        relationship_id: UUID,
        review_period_ref: str,
    ) -> PerformanceAssessment:
        assessment = self._performance_provider(relationship_id, review_period_ref)
        if assessment.missed_review_periods >= 2 and (
            assessment.diagnosis_required is not True
            or assessment.corrective_proposal_required is not True
        ):
            raise _contract_error("DOMAIN_EMPLOYMENT_INVALID")
        return assessment

    def _validate_plan(
        self,
        request: PlanValidationRequest,
        context: PlanContext,
    ) -> PlanValidationAssessment:
        produced_at = self._clock()
        if (
            request.manifest_version != MANIFEST_VERSION
            or request.requirement_set_version != REQUIREMENT_SET_VERSION
        ):
            return PlanValidationAssessment(
                assessmentVersion=ASSESSMENT_VERSION,
                state="UNKNOWN",
                unmetDomainConditions=("CURRENT_VERSION_REQUIRED",),
                limitations=("Plan versions cannot be reconciled to the admitted Package A tuple.",),
                producedAt=produced_at,
            )
        if context.source_version != request.source_version:
            return PlanValidationAssessment(
                assessmentVersion=ASSESSMENT_VERSION,
                state="UNKNOWN",
                unmetDomainConditions=("CURRENT_SOURCE_VERSION_REQUIRED",),
                limitations=("The plan source cannot be reconciled to current owner evidence.",),
                producedAt=produced_at,
            )
        if request.goal_type not in SUPPORTED_GOALS:
            return PlanValidationAssessment(
                assessmentVersion=ASSESSMENT_VERSION,
                state="INVALID",
                unmetDomainConditions=("SUPPORTED_GOAL_REQUIRED",),
                limitations=("The requested goal is outside Package A.",),
                producedAt=produced_at,
            )
        if not context.mandatory_requirements_confirmed:
            return PlanValidationAssessment(
                assessmentVersion=ASSESSMENT_VERSION,
                state="INVALID",
                unmetDomainConditions=("MANDATORY_INDUCTION_REQUIRED",),
                limitations=("A mandatory Package A induction requirement is incomplete.",),
                producedAt=produced_at,
            )
        if context.requested_side_effects:
            return PlanValidationAssessment(
                assessmentVersion=ASSESSMENT_VERSION,
                state="INVALID",
                unmetDomainConditions=("PACKAGE_A_SIDE_EFFECT_PROHIBITED",),
                limitations=("Package A cannot publish, spend, contact leads, or mutate a provider.",),
                producedAt=produced_at,
            )
        if not context.calendar_commitments_complete:
            return PlanValidationAssessment(
                assessmentVersion=ASSESSMENT_VERSION,
                state="INVALID",
                unmetDomainConditions=("COMPLETE_CALENDAR_SEMANTICS_REQUIRED",),
                limitations=("Calendar commitments require complete WC-115 time semantics.",),
                producedAt=produced_at,
            )
        if context.deferred_requirement_refs:
            if not context.deferred_isolation_proven:
                return PlanValidationAssessment(
                    assessmentVersion=ASSESSMENT_VERSION,
                    state="UNKNOWN",
                    unmetDomainConditions=("DEFERRED_SCOPE_ISOLATION_REQUIRED",),
                    limitations=("Deferred work cannot be bounded from the current dependency proof.",),
                    producedAt=produced_at,
                )
            return PlanValidationAssessment(
                assessmentVersion=ASSESSMENT_VERSION,
                state="PARTIAL",
                unmetDomainConditions=context.deferred_requirement_refs,
                limitations=("Optional work is deferred with proven bounded impact.",),
                producedAt=produced_at,
            )
        if not set(request.skill_refs) <= STABLE_SKILLS or not set(request.milestone_types) <= SUPPORTED_MILESTONES:
            return PlanValidationAssessment(
                assessmentVersion=ASSESSMENT_VERSION,
                state="INVALID",
                unmetDomainConditions=("PACKAGE_A_COORDINATES_REQUIRED",),
                limitations=("The plan contains an unavailable skill or milestone.",),
                producedAt=produced_at,
            )
        if request.goal_type == "PLAN_CONTENT_AND_CAMPAIGNS" and "CONTENT_CALENDAR_ACCEPTED" not in request.milestone_types:
            return PlanValidationAssessment(
                assessmentVersion=ASSESSMENT_VERSION,
                state="PARTIAL",
                unmetDomainConditions=("CONTENT_CALENDAR_MILESTONE_REQUIRED",),
                limitations=("Content planning remains bounded and cannot publish.",),
                producedAt=produced_at,
            )
        return PlanValidationAssessment(
            assessmentVersion=ASSESSMENT_VERSION,
            state="VALID",
            unmetDomainConditions=(),
            limitations=("Package A grants no publication, provider mutation, spend, or lead-contact authority.",),
            producedAt=produced_at,
        )

    def _classify_material_change(
        self,
        request: MaterialChangeRequest,
        context: MaterialChangeContext,
    ) -> MaterialChangeAssessment:
        self._require_manifest(request.manifest_version)
        flags = frozenset(request.protected_category_flags)
        if not flags:
            return MaterialChangeAssessment(
                classification="UNKNOWN",
                reasons=("NO_CLOSED_CHANGE_CATEGORY",),
                affectedSkillRefs=tuple(sorted(STABLE_SKILLS)),
                affectedWorkRefs=("PACKAGE_A_ACTIVE_WORK",),
                renewedAgreementRequired=True,
            )
        if flags == {"CALENDAR"} and context.calendar_within_accepted_tolerance:
            return MaterialChangeAssessment(
                classification="NON_MATERIAL",
                reasons=("CALENDAR_WITHIN_ACCEPTED_TOLERANCE",),
                affectedSkillRefs=("CONTENT_STRATEGY_AND_CALENDAR",),
                affectedWorkRefs=("CONTENT_CALENDAR",),
                renewedAgreementRequired=False,
            )
        affected = _skills_for_flags(flags)
        return MaterialChangeAssessment(
            classification="MATERIAL",
            reasons=tuple(f"{flag}_CHANGED" for flag in sorted(flags)),
            affectedSkillRefs=tuple(sorted(affected)),
            affectedWorkRefs=("PACKAGE_A_ACTIVE_WORK",),
            renewedAgreementRequired=True,
        )

    def _evaluate_dependency_isolation(
        self,
        request: DependencyIsolationRequest,
    ) -> DependencyIsolationAssessment:
        self._require_manifest(request.manifest_version)
        node = self._dependency_graph["dependencies"].get(request.dependency_ref)
        if node is None or request.dependency_state == "UNKNOWN":
            return DependencyIsolationAssessment(
                isolation="UNKNOWN",
                affectedSkillRefs=tuple(sorted(STABLE_SKILLS)),
                dependentWorkRefs=("PACKAGE_A_ACTIVE_WORK",),
                rationale="The dependency graph cannot prove a complete current impact.",
            )
        affected = frozenset(node["affectedSkillRefs"])
        candidate = frozenset(request.candidate_affected_skill_refs)
        shared_gate = bool(node["sharedMandatoryGate"])
        if shared_gate or not affected <= candidate:
            return DependencyIsolationAssessment(
                isolation="NOT_BOUNDED",
                affectedSkillRefs=tuple(sorted(affected)),
                dependentWorkRefs=tuple(node["dependentWorkRefs"]),
                rationale="The dependency reaches omitted work or a shared mandatory gate.",
            )
        return DependencyIsolationAssessment(
            isolation="PROVEN_BOUNDED",
            affectedSkillRefs=tuple(sorted(affected)),
            dependentWorkRefs=tuple(node["dependentWorkRefs"]),
            rationale="Every transitive dependent is present in the caller candidate set.",
        )

    def _require_manifest(self, manifest_version: str) -> None:
        if manifest_version != MANIFEST_VERSION:
            raise _contract_error("DOMAIN_EMPLOYMENT_VERSION_UNSUPPORTED")

    def _once(
        self,
        operation: str,
        relationship_id: UUID,
        idempotency_key: UUID,
        digest: str,
        execute: Callable[[], Any],
    ) -> Any:
        key = (operation, relationship_id, idempotency_key)
        with self._replay_lock:
            previous = self._replays.get(key)
            if previous is not None:
                if previous[0] != digest:
                    raise _contract_error("DOMAIN_EMPLOYMENT_CONFLICT")
                return previous[1]
            result = execute()
            self._replays[key] = (digest, result)
            return result


def _load_json(name: str) -> dict[str, Any]:
    with (CONTRACT_ROOT / name).open(encoding="utf-8") as stream:
        value = json.load(stream)
    if not isinstance(value, dict):
        raise RuntimeError(f"{name} must contain one JSON object")
    return value


def _resolved_mandatory(item: Mapping[str, Any], selected: frozenset[str]) -> bool:
    rule = item["mandatoryRule"]
    if rule == "ALWAYS":
        return True
    if rule == "NEVER":
        return False
    return bool(selected.intersection(item["affectedSkillRefs"]))


def _requirement_payload(
    item: Mapping[str, Any],
    selected: frozenset[str],
) -> dict[str, Any]:
    return {
        key: value
        for key, value in item.items()
        if key != "mandatoryRule"
    } | {"mandatory": _resolved_mandatory(item, selected)}


def _digest(payload: Mapping[str, Any]) -> str:
    canonical = json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True).encode()
    return hashlib.sha256(canonical).hexdigest()


def _contract_error(code: str) -> AdapterContractError:
    return AdapterContractError(code, "00000000-0000-0000-0000-000000000000")


def _skills_for_flags(flags: frozenset[str]) -> frozenset[str]:
    if flags <= {"CALENDAR"}:
        return frozenset({"CONTENT_STRATEGY_AND_CALENDAR"})
    if flags <= {"BASELINE", "MEASUREMENT"}:
        return frozenset({"MARKET_RESEARCH_AND_MATURITY", "CONTENT_STRATEGY_AND_CALENDAR"})
    return STABLE_SKILLS
