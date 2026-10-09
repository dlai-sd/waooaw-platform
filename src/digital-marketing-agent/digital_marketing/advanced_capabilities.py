"""Package E institutional, experiment, aggregate, and crisis semantics."""

# Implements: architecture/reference/components/dma-demand-search-lifecycle-and-advanced-solution-contract.md §9
# Constitutional basis: C-001, C-035, C-059, C-063, C-078, C-080

from __future__ import annotations

from dataclasses import dataclass

from contracts.cde.foundation import CdeDenied, CdeReason


@dataclass(frozen=True)
class InstitutionalBoundary:
    organisation: str
    relationship_ref: str
    instance_ref: str
    decision_space: str
    budget_ref: str
    credential_ref: str
    stop_scope_ref: str

    def __post_init__(self) -> None:
        if self.organisation != "WAOOAW_INSTITUTIONAL":
            raise CdeDenied(CdeReason.AUTHORITY_DENIED)
        if self.decision_space != "WAOOAW_INSTITUTIONAL_MARKETING":
            raise CdeDenied(CdeReason.AUTHORITY_DENIED)
        values = (
            self.relationship_ref,
            self.instance_ref,
            self.budget_ref,
            self.credential_ref,
            self.stop_scope_ref,
        )
        if any(value.startswith("customer:") for value in values):
            raise CdeDenied(CdeReason.NOT_ACCESSIBLE)


@dataclass(frozen=True)
class ExperimentEnvelope:
    experiment_ref: str
    hypothesis: str
    variants: frozenset[str]
    budget_minor: int
    audience_ref: str
    geography: frozenset[str]
    guardrails: frozenset[str]
    duration_days: int
    statistical_method: str
    stop_loss_minor: int

    def require_candidate(
        self,
        *,
        variant: str,
        budget_minor: int,
        audience_ref: str,
        geography: frozenset[str],
        guardrails_clear: bool,
    ) -> None:
        if (
            variant not in self.variants
            or budget_minor > self.budget_minor
            or budget_minor > self.stop_loss_minor
            or audience_ref != self.audience_ref
            or not geography <= self.geography
            or not guardrails_clear
        ):
            raise CdeDenied(CdeReason.AUTHORITY_DENIED)


@dataclass(frozen=True)
class AggregateIntelligenceRequest:
    owner_ref: str | None
    cohort_size: int
    minimum_cohort_size: int
    smallest_cell_size: int
    minimum_cell_size: int
    lineage_ref: str
    confidence: str
    limitations: tuple[str, ...]
    contains_raw_records: bool = False
    identifies_customers: bool = False
    ranks_customers: bool = False

    def require_safe(self) -> None:
        if not self.owner_ref:
            raise CdeDenied(CdeReason.NOT_CONFIGURED)
        if self.cohort_size < self.minimum_cohort_size or self.smallest_cell_size < self.minimum_cell_size:
            raise CdeDenied(CdeReason.NOT_ACCESSIBLE)
        if self.contains_raw_records or self.identifies_customers or self.ranks_customers:
            raise CdeDenied(CdeReason.AUTHORITY_DENIED)
        if not self.lineage_ref or not self.limitations:
            raise CdeDenied(CdeReason.INVALID_REQUEST)


CRISIS_TYPES = frozenset(
    {
        "REVIEW_BOMB",
        "EXTORTION",
        "LEGAL",
        "REGULATORY",
        "SAFETY",
        "MEDIA",
        "DATA_BREACH",
        "PUBLIC_HARM",
    }
)


@dataclass(frozen=True)
class CrisisSignal:
    signal_ref: str
    crisis_type: str
    source_evidence_ref: str
    severity: str
    escalation_ref: str
    approval_ref: str | None = None

    @property
    def publication_allowed(self) -> bool:
        return False

    def require_known_type(self) -> None:
        if self.crisis_type not in CRISIS_TYPES or not self.escalation_ref:
            raise CdeDenied(CdeReason.INVALID_REQUEST)
