"""Declaration-driven employment semantics: an agent that supplies only its manifest and requirement set."""

# Implements: work-contracts/WC-174-agent-operation-modes-calendar-and-dma-journey.md WC174-R004, R035
# Constitutional basis: C-023, C-035, C-059, C-063, C-079

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from .adapter import AdapterContractError
from .employment import (
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

_NO_CORRELATION = "00000000-0000-0000-0000-000000000000"


def _error(code: str) -> AdapterContractError:
    return AdapterContractError(code, _NO_CORRELATION)


class DeclarativeEmploymentSemantics:
    """
    Answers the six domain-adapter operations from the declaration alone. It is conservative: it admits only what the
    manifest names, treats a protected change as material and says UNKNOWN where it has no evidence. A second agent that
    needs richer domain meaning writes its own semantics; the platform asks the same six operations either way.
    """

    def __init__(
        self,
        manifest_path: Path,
        requirements_path: Path,
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._manifest = EmploymentInterfaceManifest.model_validate(json.loads(manifest_path.read_text(encoding="utf-8")))
        self._requirements = json.loads(requirements_path.read_text(encoding="utf-8"))
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def manifest(self, agent_type: str, agent_version: str, manifest_version: str) -> EmploymentInterfaceManifest:
        if (
            agent_type != self._manifest.agent_type
            or agent_version != self._manifest.agent_version
            or manifest_version != self._manifest.manifest_version
        ):
            raise _error("DOMAIN_EMPLOYMENT_VERSION_UNSUPPORTED")
        return self._manifest

    def induction_requirements(self, relationship_id: UUID, manifest_version: str) -> InductionRequirementSet:
        if manifest_version != self._manifest.manifest_version:
            raise _error("DOMAIN_EMPLOYMENT_VERSION_UNSUPPORTED")
        requirements = tuple(
            DomainRequirement(
                requirement_ref=item["requirementRef"],
                label=item["label"],
                mandatory=item["mandatoryRule"] == "ALWAYS",
                dependency_type=item["dependencyType"],
                affected_skill_refs=tuple(item["affectedSkillRefs"]),
                confirmation_class=item.get("confirmationClass"),
            )
            for item in self._requirements["requirements"]
        )
        return InductionRequirementSet(
            manifest_version=self._manifest.manifest_version,
            requirement_set_version=self._requirements["requirementSetVersion"],
            requirements=requirements,
            produced_at=self._clock(),
        )

    def validate_plan(
        self, relationship_id: UUID, idempotency_key: UUID, request: PlanValidationRequest
    ) -> PlanValidationAssessment:
        unmet: list[str] = []
        if request.goal_type not in self._manifest.planning.supported_goal_types:
            unmet.append("GOAL_TYPE_NOT_DECLARED")
        if not set(request.milestone_types) <= set(self._manifest.planning.milestone_types):
            unmet.append("MILESTONE_TYPE_NOT_DECLARED")
        return PlanValidationAssessment(
            assessment_version="1.0.0",
            state="INVALID" if unmet else "VALID",
            unmet_domain_conditions=tuple(unmet),
            limitations=(),
            produced_at=self._clock(),
        )

    def classify_material_change(
        self, relationship_id: UUID, idempotency_key: UUID, request: MaterialChangeRequest
    ) -> MaterialChangeAssessment:
        protected = bool(request.protected_category_flags)
        return MaterialChangeAssessment(
            classification="MATERIAL" if protected else "NON_MATERIAL",
            reasons=("PROTECTED_CHANGE_IS_MATERIAL",) if protected else ("NO_PROTECTED_CATEGORY",),
            affected_skill_refs=(),
            affected_work_refs=(),
            renewed_agreement_required=protected,
        )

    def evaluate_dependency_isolation(
        self, relationship_id: UUID, idempotency_key: UUID, request: DependencyIsolationRequest
    ) -> DependencyIsolationAssessment:
        return DependencyIsolationAssessment(
            isolation="UNKNOWN",
            affected_skill_refs=request.candidate_affected_skill_refs,
            dependent_work_refs=(),
            rationale="The declaration alone cannot prove the loss is bounded.",
        )

    def performance_assessment(self, relationship_id: UUID, review_period_ref: str) -> PerformanceAssessment:
        return PerformanceAssessment(
            assessment_version="1.0.0",
            review_period_ref=review_period_ref,
            outcome_label="Not measured",
            outcome_state="UNKNOWN",
            attribution_basis="No measured outcome source is declared.",
            attribution_confidence=0,
            agent_performance_state="UNKNOWN",
            missed_review_periods=0,
            evidence_refs=(),
            limitations=("The fixture measures nothing.",),
            produced_at=self._clock(),
        )
