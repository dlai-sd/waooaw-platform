"""Generic conversational-employment semantics for every admitted adapter."""

# Implements: architecture/reference/components/conversational-employment-solution-contract.md §4.5 Domain-adapter operations
# Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C2-01
# Constitutional basis: C-023, C-035, C-059, C-063, C-079, ADR-051
# IB: N/A - Founder-assigned WC-115, WC-136

from __future__ import annotations

from datetime import datetime
from typing import Literal, Protocol
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class EmploymentModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=lambda value: value.split("_")[0]
        + "".join(part.title() for part in value.split("_")[1:]),
        populate_by_name=True,
        extra="forbid",
    )


class ImmutableContractReference(EmploymentModel):
    contract_ref: str = Field(min_length=1, max_length=240)
    contract_version: str = Field(min_length=1, max_length=64)
    contract_digest: str = Field(pattern=r"^[a-f0-9]{64}$")


class GovernanceReferences(EmploymentModel):
    agent_specification: ImmutableContractReference
    prompt_policy: ImmutableContractReference
    tool_profile: ImmutableContractReference
    decision_consequence_map: ImmutableContractReference


class InductionManifest(EmploymentModel):
    requirement_set_version: str = Field(min_length=1, max_length=64)
    mandatory_context: tuple[str, ...] = Field(min_length=1)
    optional_context: tuple[str, ...] = ()
    dependency_types: tuple[str, ...] = Field(min_length=1)
    readiness_rules: tuple[str, ...] = Field(min_length=1)
    domain_summary_adapter: ImmutableContractReference


class PlanningManifest(EmploymentModel):
    supported_goal_types: tuple[str, ...] = Field(min_length=1)
    milestone_types: tuple[str, ...] = Field(min_length=1)
    calendar_constraints: tuple[str, ...] = Field(min_length=1)
    material_change_rules: tuple[str, ...] = Field(min_length=1)
    performance_measure_types: tuple[str, ...] = Field(min_length=1)
    plan_adapter: ImmutableContractReference


class OperationsManifest(EmploymentModel):
    operating_cycle_types: tuple[str, ...] = Field(min_length=1)
    work_item_types: tuple[str, ...] = Field(min_length=1)
    reassessment_triggers: tuple[str, ...] = Field(min_length=1)
    outcome_adapter: ImmutableContractReference
    billing_profile: ImmutableContractReference
    degradation_profile: ImmutableContractReference
    shorter_missed_review_threshold: int | None = Field(default=None, ge=1, le=2)


class ConformanceScenario(EmploymentModel):
    scenario_id: str = Field(min_length=1, max_length=160)
    evidence_ref: str = Field(min_length=1, max_length=240)
    result: Literal["PASS"]
    validated_protocol_version: Literal["1.0-candidate"]
    validated_manifest_version: str = Field(min_length=1, max_length=64)
    validated_at: datetime | None = None
    limitation_refs: tuple[str, ...] = ()


ExperienceBlockType = Literal["TEXT", "CHOICES", "LIST", "LINK", "STATUS", "METRIC", "PLAN", "DECISION", "FORM", "EVIDENCE", "DOMAIN"]


class ExperienceMeasure(EmploymentModel):
    measure_id: str = Field(min_length=1, max_length=160)
    unit: str = Field(min_length=1, max_length=160)
    evidence_source: str = Field(min_length=1, max_length=160)
    freshness_seconds: int = Field(ge=1)


class ExperienceGoalType(EmploymentModel):
    goal_type_id: str = Field(min_length=1, max_length=160)
    parameters: tuple[str, ...]
    measures: tuple[ExperienceMeasure, ...] = Field(min_length=1)
    constraints: tuple[str, ...]
    starters: tuple[str, ...]


class ExperiencePlan(EmploymentModel):
    milestone_types: tuple[str, ...] = Field(min_length=1)
    calendar_windows: tuple[str, ...]


class ExperienceCadence(EmploymentModel):
    skill_id: str = Field(min_length=1, max_length=160)
    trigger: str = Field(min_length=1, max_length=160)
    window: str = Field(min_length=1, max_length=160)


class ExperienceApprovalMode(EmploymentModel):
    mode: str = Field(min_length=1, max_length=160)
    escalation: str = Field(min_length=1, max_length=160)


class ExperienceOperate(EmploymentModel):
    work_item_types: tuple[str, ...] = Field(min_length=1)
    cadence: tuple[ExperienceCadence, ...] = Field(min_length=1)
    approval_modes: tuple[ExperienceApprovalMode, ...] = Field(min_length=1)


class ExperienceTile(EmploymentModel):
    tile_id: str = Field(min_length=1, max_length=160)
    measure_id: str = Field(min_length=1, max_length=160)
    block_type: Literal["STATUS", "METRIC", "PLAN", "DECISION", "EVIDENCE", "DOMAIN"]
    audiences: tuple[Literal["customer_owner", "delegate", "beneficiary", "steward"], ...] = Field(min_length=1)


class ExperienceNarrative(EmploymentModel):
    narrative_id: str = Field(min_length=1, max_length=160)
    cadence: str = Field(min_length=1, max_length=160)
    channels: tuple[str, ...] = Field(min_length=1)
    structure: tuple[str, ...] = Field(min_length=1)


class ExperienceAlert(EmploymentModel):
    signal: str = Field(min_length=1, max_length=160)
    threshold: str = Field(min_length=1, max_length=160)
    severity: Literal["INFO", "WARNING", "CRITICAL"]
    channels: tuple[str, ...] = Field(min_length=1)


class ExperienceMonitor(EmploymentModel):
    tiles: tuple[ExperienceTile, ...] = Field(min_length=1)
    narratives: tuple[ExperienceNarrative, ...]
    alerts: tuple[ExperienceAlert, ...]


class ExperienceDomainBlock(EmploymentModel):
    block_id: str = Field(min_length=1, max_length=160)
    version: int = Field(ge=1)
    fallback_blocks: tuple[Literal["TEXT", "CHOICES", "LIST", "LINK"], ...] = Field(min_length=1)


class ExperienceSelectableDimension(EmploymentModel):
    kind: str = Field(min_length=1, max_length=160)
    maximum: int = Field(ge=1)


class ExperienceComponent(EmploymentModel):
    component_id: str = Field(min_length=1, max_length=160)
    label: str = Field(min_length=1, max_length=240)
    unit: str = Field(min_length=1, max_length=160)
    kind: Literal["COUNTED", "SELECTED", "TIME_ACCESS", "CAPACITY"]
    skill_id: str | None = Field(default=None, min_length=1, max_length=160)
    counted_on: str = Field(min_length=1, max_length=160)
    selectable_dimension: ExperienceSelectableDimension | None = None
    availability: Literal["AVAILABLE", "DEFAULT_OFF", "UNAVAILABLE"]
    activation_authority: str | None = Field(default=None, min_length=1, max_length=160)

    @model_validator(mode="after")
    def _selected_components_declare_their_dimension(self) -> ExperienceComponent:
        if self.kind == "SELECTED" and self.selectable_dimension is None:
            raise ValueError("a SELECTED component must declare its selectable dimension")
        return self


class ExperienceChannelSupport(EmploymentModel):
    web: tuple[ExperienceBlockType, ...]
    whatsapp: tuple[ExperienceBlockType, ...]
    mobile: tuple[ExperienceBlockType, ...]


class ExperienceManifest(EmploymentModel):
    contract_version: str = Field(min_length=1, max_length=64)
    vocabulary_ref: ImmutableContractReference
    component_catalogue_ref: ImmutableContractReference | None = None
    goal_types: tuple[ExperienceGoalType, ...] = Field(min_length=1)
    plan: ExperiencePlan
    operate: ExperienceOperate
    monitor: ExperienceMonitor
    domain_blocks: tuple[ExperienceDomainBlock, ...]
    components: tuple[ExperienceComponent, ...]
    audiences: tuple[Literal["customer_owner", "delegate", "beneficiary", "steward"], ...] = Field(min_length=1)
    modalities: tuple[Literal["text", "voice"], ...] = Field(min_length=1)
    channel_support: ExperienceChannelSupport
    conformance_scenarios: tuple[str, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _components_are_unique_and_bound_to_declared_skills(self) -> ExperienceManifest:
        component_ids = [component.component_id for component in self.components]
        if len(component_ids) != len(set(component_ids)):
            raise ValueError("component ids must be unique")
        operated_skills = {entry.skill_id for entry in self.operate.cadence}
        for component in self.components:
            if component.skill_id is not None and component.skill_id not in operated_skills:
                raise ValueError(f"component {component.component_id} references a skill that is not operated")
        return self


class EmploymentInterfaceManifest(EmploymentModel):
    schema_version: Literal["1.0"] = "1.0"
    protocol_version: Literal["1.0-candidate"] = "1.0-candidate"
    agent_type: str = Field(min_length=1, max_length=100)
    agent_version: str = Field(min_length=1, max_length=64)
    manifest_version: str = Field(min_length=1, max_length=64)
    governance: GovernanceReferences
    induction: InductionManifest
    planning: PlanningManifest
    operations: OperationsManifest
    experience: ExperienceManifest | None = None
    conformance_scenarios: tuple[ConformanceScenario, ...] = Field(min_length=1)


class DomainRequirement(EmploymentModel):
    requirement_ref: str = Field(min_length=1, max_length=128)
    label: str = Field(min_length=1, max_length=240)
    description: str | None = Field(default=None, max_length=1000)
    mandatory: bool
    dependency_type: str = Field(min_length=1, max_length=100)
    affected_skill_refs: tuple[str, ...] = Field(min_length=1)
    confirmation_class: Literal["CUSTOMER", "AUTHORITY_SOURCE", "OWNER_BOUND_ASSUMPTION"] | None = None


class InductionRequirementSet(EmploymentModel):
    schema_version: Literal["1.0"] = "1.0"
    manifest_version: str = Field(min_length=1, max_length=64)
    requirement_set_version: str = Field(min_length=1, max_length=64)
    requirements: tuple[DomainRequirement, ...] = Field(min_length=1)
    produced_at: datetime


class PlanValidationRequest(EmploymentModel):
    schema_version: Literal["1.0"]
    manifest_version: str = Field(min_length=1, max_length=64)
    requirement_set_version: str = Field(min_length=1, max_length=64)
    plan_version: str = Field(min_length=1, max_length=64)
    goal_type: str = Field(min_length=1, max_length=100)
    skill_refs: tuple[str, ...] = Field(min_length=1)
    milestone_types: tuple[str, ...]
    source_version: str = Field(min_length=1, max_length=128)


class PlanValidationAssessment(EmploymentModel):
    schema_version: Literal["1.0"] = "1.0"
    assessment_version: str = Field(min_length=1, max_length=64)
    state: Literal["VALID", "INVALID", "PARTIAL", "UNKNOWN"]
    unmet_domain_conditions: tuple[str, ...]
    limitations: tuple[str, ...]
    produced_at: datetime


class MaterialChangeRequest(EmploymentModel):
    schema_version: Literal["1.0"]
    manifest_version: str = Field(min_length=1, max_length=64)
    current_plan_version: str = Field(min_length=1, max_length=64)
    candidate_patch_ref: UUID
    protected_category_flags: tuple[
        Literal["OUTCOME", "BASELINE", "TARGET", "BUDGET", "AUTHORITY", "CALENDAR", "SKILL_SET", "CREDENTIAL", "SAFETY", "MEASUREMENT"],
        ...,
    ]


class MaterialChangeAssessment(EmploymentModel):
    schema_version: Literal["1.0"] = "1.0"
    classification: Literal["NON_MATERIAL", "MATERIAL", "UNKNOWN"]
    reasons: tuple[str, ...] = Field(min_length=1)
    affected_skill_refs: tuple[str, ...]
    affected_work_refs: tuple[str, ...]
    renewed_agreement_required: bool


class DependencyIsolationRequest(EmploymentModel):
    schema_version: Literal["1.0"]
    manifest_version: str = Field(min_length=1, max_length=64)
    dependency_ref: str = Field(min_length=1, max_length=128)
    dependency_state: Literal["READY", "LOST", "EXPIRED", "REVOKED", "UNAVAILABLE", "UNKNOWN"]
    candidate_affected_skill_refs: tuple[str, ...] = Field(min_length=1)


class DependencyIsolationAssessment(EmploymentModel):
    schema_version: Literal["1.0"] = "1.0"
    isolation: Literal["PROVEN_BOUNDED", "NOT_BOUNDED", "UNKNOWN"]
    affected_skill_refs: tuple[str, ...] = Field(min_length=1)
    dependent_work_refs: tuple[str, ...]
    rationale: str = Field(min_length=1, max_length=1000)


class PerformanceAssessment(EmploymentModel):
    schema_version: Literal["1.0"] = "1.0"
    assessment_version: str = Field(min_length=1, max_length=64)
    review_period_ref: str = Field(min_length=1, max_length=128)
    outcome_label: str = Field(min_length=1, max_length=240)
    outcome_state: Literal["ACHIEVED", "MISSED", "PARTIAL", "UNKNOWN", "UNAVAILABLE", "DISPUTED"]
    observed_value: str | None = Field(default=None, max_length=240)
    attribution_basis: str = Field(min_length=1, max_length=1000)
    attribution_confidence: float = Field(ge=0, le=1)
    agent_performance_state: Literal["MEETING", "NOT_MEETING", "UNKNOWN", "UNAVAILABLE"]
    missed_review_periods: int = Field(ge=0)
    diagnosis_required: bool | None = None
    corrective_proposal_required: bool | None = None
    evidence_refs: tuple[str, ...]
    limitations: tuple[str, ...]
    produced_at: datetime


class EmploymentDomainSemantics(Protocol):
    def manifest(
        self, agent_type: str, agent_version: str, manifest_version: str
    ) -> EmploymentInterfaceManifest: ...

    def induction_requirements(
        self, relationship_id: UUID, manifest_version: str
    ) -> InductionRequirementSet: ...

    def validate_plan(
        self, relationship_id: UUID, idempotency_key: UUID, request: PlanValidationRequest
    ) -> PlanValidationAssessment: ...

    def classify_material_change(
        self, relationship_id: UUID, idempotency_key: UUID, request: MaterialChangeRequest
    ) -> MaterialChangeAssessment: ...

    def evaluate_dependency_isolation(
        self, relationship_id: UUID, idempotency_key: UUID, request: DependencyIsolationRequest
    ) -> DependencyIsolationAssessment: ...

    def performance_assessment(self, relationship_id: UUID, review_period_ref: str) -> PerformanceAssessment: ...
