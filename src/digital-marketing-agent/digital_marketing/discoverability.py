"""Package D discoverability assessment and approved-change semantics."""

# Implements: architecture/reference/components/dma-demand-search-lifecycle-and-advanced-solution-contract.md §8.1
# Constitutional basis: C-035, C-059, C-063, C-071, C-080

from __future__ import annotations

from dataclasses import dataclass

from contracts.cde.foundation import CdeDenied, CdeReason


@dataclass(frozen=True)
class EvidenceFact:
    fact_type: str
    value: str | None
    source_ref: str
    observed_at: str
    freshness: str
    confidence: str
    limitations: tuple[str, ...]
    verified: bool

    def __post_init__(self) -> None:
        if not self.source_ref or not self.observed_at or not self.limitations:
            raise CdeDenied(CdeReason.INVALID_REQUEST)
        if self.value and not self.verified:
            raise CdeDenied(CdeReason.AUTHORITY_DENIED)


@dataclass(frozen=True)
class DiscoverabilityAssessmentVersion:
    assessment_id: str
    version: int
    business_ref: str
    site_ref: str
    location_refs: tuple[str, ...]
    facts: tuple[EvidenceFact, ...]
    correction_ref: str | None

    @property
    def coverage(self) -> str:
        return f"{sum(fact.value is not None for fact in self.facts)}/{len(self.facts)}"


@dataclass(frozen=True)
class ApprovedChangePackage:
    change_id: str
    target_ref: str
    before_version: str
    proposed_value_digest: str
    owner_ref: str | None
    approval_ref: str
    rollback_supported: bool

    @property
    def dispatch_state(self) -> str:
        return "APPROVED" if self.owner_ref else "MANUAL_DELIVERY_REQUIRED"

    def verified_result(self, *, receipt_ref: str | None, after_version: str | None) -> str:
        if not self.owner_ref:
            return "MANUAL_DELIVERY_REQUIRED"
        if not receipt_ref or not after_version:
            return "OUTCOME_UNKNOWN"
        return "VERIFIED"
