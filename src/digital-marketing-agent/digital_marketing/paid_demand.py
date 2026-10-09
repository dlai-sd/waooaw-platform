"""Package C paid-demand and first-party-audience semantics."""

# Implements: architecture/reference/components/dma-demand-search-lifecycle-and-advanced-solution-contract.md §7
# Constitutional basis: C-001, C-041, C-043, C-056, C-059, C-063, C-080, ADR-026

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum

from contracts.cde.foundation import CdeDenied, CdeReason


class CampaignState(StrEnum):
    DRAFT = "DRAFT"
    READY_FOR_REVIEW = "READY_FOR_REVIEW"
    APPROVED = "APPROVED"
    READINESS_PENDING = "READINESS_PENDING"
    READY = "READY"
    DISPATCHING = "DISPATCHING"
    ACTIVE = "ACTIVE"
    PAUSE_PENDING = "PAUSE_PENDING"
    PAUSED = "PAUSED"
    RECONCILING = "RECONCILING"
    FAILED = "FAILED"
    OUTCOME_UNKNOWN = "OUTCOME_UNKNOWN"
    SUPERSEDED = "SUPERSEDED"


@dataclass(frozen=True)
class PaidCampaignVersion:
    campaign_id: str
    version: int
    state: CampaignState
    plan_ref: str
    creative_ref: str
    rights_ref: str
    objective: str
    account_ref: str
    account_model: str
    budget_ref: str
    approval_ref: str | None
    capability_ref: str
    authority_ref: str
    audience_basis: str

    def __post_init__(self) -> None:
        required = (
            self.plan_ref,
            self.creative_ref,
            self.rights_ref,
            self.objective,
            self.account_ref,
            self.budget_ref,
            self.capability_ref,
            self.authority_ref,
        )
        if not all(required):
            raise CdeDenied(CdeReason.INVALID_REQUEST)
        if self.account_model != "WAOOAW_MANAGED":
            raise CdeDenied(CdeReason.ACCOUNT_UNSUPPORTED)

    def transition(self, target: CampaignState, *, provider_verified: bool = False) -> PaidCampaignVersion:
        legal = {
            CampaignState.DRAFT: {CampaignState.READY_FOR_REVIEW},
            CampaignState.READY_FOR_REVIEW: {CampaignState.APPROVED},
            CampaignState.APPROVED: {CampaignState.READINESS_PENDING, CampaignState.SUPERSEDED},
            CampaignState.READINESS_PENDING: {CampaignState.READY, CampaignState.FAILED},
            CampaignState.READY: {CampaignState.DISPATCHING, CampaignState.PAUSED},
            CampaignState.DISPATCHING: {
                CampaignState.ACTIVE,
                CampaignState.RECONCILING,
                CampaignState.FAILED,
            },
            CampaignState.ACTIVE: {
                CampaignState.PAUSE_PENDING,
                CampaignState.RECONCILING,
            },
            CampaignState.PAUSE_PENDING: {CampaignState.PAUSED, CampaignState.RECONCILING},
            CampaignState.RECONCILING: {
                CampaignState.ACTIVE,
                CampaignState.PAUSED,
                CampaignState.FAILED,
                CampaignState.OUTCOME_UNKNOWN,
            },
            CampaignState.PAUSED: set(),
            CampaignState.FAILED: set(),
            CampaignState.OUTCOME_UNKNOWN: set(),
            CampaignState.SUPERSEDED: set(),
        }
        if target not in legal[self.state]:
            raise CdeDenied(CdeReason.VERSION_CONFLICT)
        if target is CampaignState.APPROVED and not self.approval_ref:
            raise CdeDenied(CdeReason.AUTHORITY_DENIED)
        if target is CampaignState.ACTIVE and not provider_verified:
            raise CdeDenied(CdeReason.RECONCILIATION_REQUIRED)
        return replace(self, state=target)

    def material_successor(self, **changes: str) -> PaidCampaignVersion:
        protected = {
            "objective",
            "account_ref",
            "budget_ref",
            "creative_ref",
            "rights_ref",
            "audience_basis",
        }
        if not protected.intersection(changes):
            raise CdeDenied(CdeReason.INVALID_REQUEST)
        values = {name: value for name, value in changes.items() if name in protected}
        return replace(
            self,
            **values,
            version=self.version + 1,
            state=CampaignState.DRAFT,
            approval_ref=None,
        )


@dataclass(frozen=True)
class SpendReadiness:
    state: str
    reservation_ref: str
    provider_amount_minor: int
    wbe_amount_minor: int
    tolerance_minor: int

    def require_dispatch(self) -> None:
        if self.state != "AVAILABLE" or not self.reservation_ref:
            raise CdeDenied(CdeReason.BUDGET_UNAVAILABLE)
        if abs(self.provider_amount_minor - self.wbe_amount_minor) > self.tolerance_minor:
            raise CdeDenied(CdeReason.RECONCILIATION_REQUIRED)


class AudienceState(StrEnum):
    PROPOSED = "PROPOSED"
    RIGHTS_REVIEW = "RIGHTS_REVIEW"
    ELIGIBILITY_REVIEW = "ELIGIBILITY_REVIEW"
    READY_FOR_APPROVAL = "READY_FOR_APPROVAL"
    APPROVED = "APPROVED"
    PREPARING = "PREPARING"
    UPLOAD_PENDING = "UPLOAD_PENDING"
    ACTIVE = "ACTIVE"
    DELETE_PENDING = "DELETE_PENDING"
    DELETED = "DELETED"
    FAILED = "FAILED"
    OUTCOME_UNKNOWN = "OUTCOME_UNKNOWN"


@dataclass(frozen=True)
class AudienceActivationVersion:
    audience_id: str
    version: int
    state: AudienceState
    lawful_basis_ref: str
    purpose: str
    provider: str
    account_ref: str
    suppression_ref: str
    retention_policy_ref: str
    deletion_policy_ref: str
    provider_policy_ref: str
    raw_identifiers: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.raw_identifiers:
            raise CdeDenied(CdeReason.INVALID_REQUEST)
        if not all(
            (
                self.lawful_basis_ref,
                self.purpose,
                self.provider,
                self.account_ref,
                self.suppression_ref,
                self.retention_policy_ref,
                self.deletion_policy_ref,
                self.provider_policy_ref,
            )
        ):
            raise CdeDenied(CdeReason.CONSENT_REQUIRED)

    def transition(self, target: AudienceState, *, verified: bool = False) -> AudienceActivationVersion:
        legal = {
            AudienceState.PROPOSED: {AudienceState.RIGHTS_REVIEW},
            AudienceState.RIGHTS_REVIEW: {AudienceState.ELIGIBILITY_REVIEW, AudienceState.FAILED},
            AudienceState.ELIGIBILITY_REVIEW: {AudienceState.READY_FOR_APPROVAL, AudienceState.FAILED},
            AudienceState.READY_FOR_APPROVAL: {AudienceState.APPROVED, AudienceState.FAILED},
            AudienceState.APPROVED: {AudienceState.PREPARING},
            AudienceState.PREPARING: {AudienceState.UPLOAD_PENDING, AudienceState.FAILED},
            AudienceState.UPLOAD_PENDING: {
                AudienceState.ACTIVE,
                AudienceState.FAILED,
                AudienceState.OUTCOME_UNKNOWN,
            },
            AudienceState.ACTIVE: {AudienceState.DELETE_PENDING},
            AudienceState.DELETE_PENDING: {AudienceState.DELETED, AudienceState.OUTCOME_UNKNOWN},
            AudienceState.DELETED: set(),
            AudienceState.FAILED: set(),
            AudienceState.OUTCOME_UNKNOWN: set(),
        }
        if target not in legal[self.state]:
            raise CdeDenied(CdeReason.VERSION_CONFLICT)
        if target in {AudienceState.ACTIVE, AudienceState.DELETED} and not verified:
            raise CdeDenied(CdeReason.RECONCILIATION_REQUIRED)
        return replace(self, state=target)
