"""Package D multi-location, reputation, and strategy semantics."""

# Implements: architecture/reference/components/dma-demand-search-lifecycle-and-advanced-solution-contract.md §8.3, §8.4
# Constitutional basis: C-001, C-035, C-059, C-063, C-071

from __future__ import annotations

from dataclasses import dataclass

from contracts.cde.foundation import CdeDenied, CdeReason


@dataclass(frozen=True)
class LocationBinding:
    hierarchy_version: str
    approved_locations: frozenset[str]
    stopped_locations: frozenset[str]
    account_by_location: dict[str, str]

    def require_action(self, location_ref: str, account_ref: str) -> None:
        if location_ref not in self.approved_locations:
            raise CdeDenied(CdeReason.AUTHORITY_DENIED)
        if location_ref in self.stopped_locations:
            raise CdeDenied(CdeReason.STOPPED)
        if self.account_by_location.get(location_ref) != account_ref:
            raise CdeDenied(CdeReason.NOT_ACCESSIBLE)

    def aggregate(self, values: dict[str, int | None]) -> dict[str, object]:
        covered = {location: value for location, value in values.items() if value is not None}
        missing = sorted(self.approved_locations - covered.keys())
        return {"covered": covered, "missingLocations": missing}


CRISIS_CLASSES = frozenset(
    {
        "COMPLAINT",
        "LEGAL",
        "REGULATORY",
        "SAFETY",
        "DISCRIMINATION",
        "CLINICAL",
        "FINANCIAL",
        "APPARENT_MINOR",
        "EXTORTION",
        "MEDIA",
        "CRISIS",
    }
)


@dataclass(frozen=True)
class ReputationObservation:
    observation_ref: str
    source_ref: str
    classification: str
    evidence_ref: str

    @property
    def next_state(self) -> str:
        return "ESCALATED" if self.classification in CRISIS_CLASSES else "READY_FOR_REVIEW"


@dataclass(frozen=True)
class StrategyProposal:
    proposal_ref: str
    evidence_refs: tuple[str, ...]
    limitations: tuple[str, ...]
    successor_plan_required: bool = True
    authority_granted: bool = False
