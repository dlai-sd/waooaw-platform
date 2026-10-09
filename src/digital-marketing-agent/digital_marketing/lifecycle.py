"""Package D lifecycle, dispatch, and suppression semantics."""

# Implements: architecture/reference/components/dma-demand-search-lifecycle-and-advanced-solution-contract.md §8.2
# Constitutional basis: C-001, C-041, C-059, C-063, C-071, C-080

from __future__ import annotations

from dataclasses import dataclass

from contracts.cde.foundation import CdeDenied, CdeReason


@dataclass(frozen=True)
class LifecycleSequenceVersion:
    sequence_id: str
    version: int
    purpose: str
    lawful_basis_ref: str
    sender_ref: str
    sender_ready: bool
    segment_ref: str
    template_ref: str
    cadence_ref: str
    trigger_ref: str
    expires_at: str
    approval_ref: str
    suppression_policy_ref: str
    contact_source: str

    def require_ready(self) -> None:
        if self.contact_source in {"PURCHASED", "SCRAPED", "UNSUBSTANTIATED", "CROSS_PURPOSE"}:
            raise CdeDenied(CdeReason.CONSENT_REQUIRED)
        if not self.lawful_basis_ref:
            raise CdeDenied(CdeReason.CONSENT_REQUIRED)
        if not self.sender_ready:
            raise CdeDenied(CdeReason.NOT_CONFIGURED)


class SuppressionRegistry:
    def __init__(self) -> None:
        self._suppressed: dict[str, str] = {}
        self._fenced_scopes: set[str] = set()

    def suppress(self, contact_ref: str, reason: str) -> None:
        self._suppressed[contact_ref] = reason

    def fence(self, scope_ref: str) -> None:
        self._fenced_scopes.add(scope_ref)

    def require_dispatch(self, *, contact_ref: str, scope_ref: str) -> None:
        if contact_ref in self._suppressed or scope_ref in self._fenced_scopes:
            raise CdeDenied(CdeReason.SUPPRESSED)
