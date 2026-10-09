"""Evidence-based B2 observation and improvement proposal contracts."""

# Implements: architecture/reference/components/dma-content-and-social-publication-solution-contract.md §9
# Constitutional basis: C-023, C-035, C-059, C-063, C-070, C-071, C-078, C-079

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum


class ObservationState(StrEnum):
    AVAILABLE = "AVAILABLE"
    PARTIAL = "PARTIAL"
    STALE = "STALE"
    UNAVAILABLE = "UNAVAILABLE"
    DISPUTED = "DISPUTED"


@dataclass(frozen=True)
class MetricObservation:
    provider_metric_name: str
    canonical_metric_name: str
    mapping_version: str
    value: Decimal | None
    unit: str
    state: ObservationState
    limitation_codes: tuple[str, ...]


@dataclass(frozen=True)
class ObservationSnapshot:
    snapshot_ref: str
    tenant_ref: str
    relationship_ref: str
    channel: str
    account_ref: str
    publication_ref: str
    provider_api_version: str
    window_start: str
    window_end: str
    collected_at: str
    freshness: str
    coverage: str
    confidence: str
    attribution_method: str
    attribution_window: str
    attribution_sources: tuple[str, ...]
    attribution_exclusions: tuple[str, ...]
    attribution_ambiguity: tuple[str, ...]
    metrics: tuple[MetricObservation, ...]


@dataclass(frozen=True)
class ImprovementProposal:
    proposal_ref: str
    snapshot_ref: str
    successor_plan_required: bool
    successor_draft_required: bool
    customer_review_required: bool
    publication_authorized: bool = False
    spend_authorized: bool = False


def propose_improvement(snapshot: ObservationSnapshot, proposal_ref: str) -> ImprovementProposal:
    if not snapshot.metrics or all(metric.state is ObservationState.UNAVAILABLE for metric in snapshot.metrics):
        raise ValueError("MEASUREMENT_UNAVAILABLE")
    if any(metric.value is None and metric.state is ObservationState.AVAILABLE for metric in snapshot.metrics):
        raise ValueError("AVAILABLE_METRIC_VALUE_REQUIRED")
    return ImprovementProposal(
        proposal_ref=proposal_ref,
        snapshot_ref=snapshot.snapshot_ref,
        successor_plan_required=True,
        successor_draft_required=True,
        customer_review_required=True,
    )
