"""Package C lead intake, progression, handoff, and conversion semantics."""

# Implements: architecture/reference/components/dma-demand-search-lifecycle-and-advanced-solution-contract.md §7.5
# Constitutional basis: C-001, C-041, C-059, C-063, C-078, C-080

from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass, replace
from enum import StrEnum

from contracts.cde.foundation import CdeDenied, CdeReason


class LeadState(StrEnum):
    CAPTURED = "CAPTURED"
    SPAM = "SPAM"
    INVALID = "INVALID"
    DUPLICATE = "DUPLICATE"
    EXISTING_CUSTOMER = "EXISTING_CUSTOMER"
    SUPPRESSED = "SUPPRESSED"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    QUALIFICATION_PENDING = "QUALIFICATION_PENDING"
    QUALIFIED = "QUALIFIED"
    UNQUALIFIED = "UNQUALIFIED"
    NEEDS_INPUT = "NEEDS_INPUT"
    HUMAN_TAKEOVER = "HUMAN_TAKEOVER"
    ROUTING_PENDING = "ROUTING_PENDING"
    ROUTED = "ROUTED"
    BOOKING_PENDING = "BOOKING_PENDING"
    BOOKED = "BOOKED"
    HANDED_OFF = "HANDED_OFF"
    NURTURING = "NURTURING"
    WON = "WON"
    LOST = "LOST"
    NO_RESPONSE = "NO_RESPONSE"
    UNKNOWN_OUTCOME = "UNKNOWN_OUTCOME"


TAKEOVER_CLASSES = frozenset(
    {
        "SENSITIVE",
        "DISPUTED",
        "HIGH_VALUE",
        "COMPLAINT",
        "APPARENT_MINOR",
        "UNSUPPORTED",
        "OUTSIDE_AUTHORITY",
    }
)
PROHIBITED_COMMITMENTS = frozenset(
    {"PRICE", "LEGAL", "CLINICAL", "INVENTORY", "ELIGIBILITY", "CREDIT", "SERVICE_GUARANTEE"}
)


@dataclass(frozen=True)
class LeadCaseVersion:
    lead_id: str
    version: int
    state: LeadState
    tenant_ref: str
    relationship_ref: str
    source_ref: str
    campaign_ref: str | None
    purpose: str
    consent_ref: str
    suppression_ref: str
    rule_version: str
    classification: str | None = None

    def transition(self, target: LeadState) -> LeadCaseVersion:
        if self.classification in TAKEOVER_CLASSES and target is not LeadState.HUMAN_TAKEOVER:
            raise CdeDenied(CdeReason.AUTHORITY_DENIED)
        legal = {
            LeadState.CAPTURED: {
                LeadState.SPAM,
                LeadState.INVALID,
                LeadState.DUPLICATE,
                LeadState.EXISTING_CUSTOMER,
                LeadState.SUPPRESSED,
                LeadState.ACKNOWLEDGED,
            },
            LeadState.ACKNOWLEDGED: {
                LeadState.QUALIFICATION_PENDING,
                LeadState.HUMAN_TAKEOVER,
                LeadState.SUPPRESSED,
            },
            LeadState.QUALIFICATION_PENDING: {
                LeadState.QUALIFIED,
                LeadState.UNQUALIFIED,
                LeadState.NEEDS_INPUT,
                LeadState.HUMAN_TAKEOVER,
            },
            LeadState.QUALIFIED: {
                LeadState.ROUTING_PENDING,
                LeadState.BOOKING_PENDING,
                LeadState.NURTURING,
                LeadState.HUMAN_TAKEOVER,
            },
            LeadState.ROUTING_PENDING: {
                LeadState.ROUTED,
                LeadState.BOOKING_PENDING,
                LeadState.UNKNOWN_OUTCOME,
            },
            LeadState.BOOKING_PENDING: {
                LeadState.BOOKED,
                LeadState.HANDED_OFF,
                LeadState.UNKNOWN_OUTCOME,
            },
            LeadState.ROUTED: {
                LeadState.WON,
                LeadState.LOST,
                LeadState.NO_RESPONSE,
                LeadState.UNKNOWN_OUTCOME,
                LeadState.SUPPRESSED,
            },
            LeadState.BOOKED: {
                LeadState.WON,
                LeadState.LOST,
                LeadState.NO_RESPONSE,
                LeadState.UNKNOWN_OUTCOME,
                LeadState.SUPPRESSED,
            },
            LeadState.HANDED_OFF: {
                LeadState.WON,
                LeadState.LOST,
                LeadState.NO_RESPONSE,
                LeadState.UNKNOWN_OUTCOME,
                LeadState.SUPPRESSED,
            },
            LeadState.NURTURING: {
                LeadState.WON,
                LeadState.LOST,
                LeadState.NO_RESPONSE,
                LeadState.SUPPRESSED,
            },
        }
        if target not in legal.get(self.state, set()):
            raise CdeDenied(CdeReason.VERSION_CONFLICT)
        if target is LeadState.SUPPRESSED and not self.suppression_ref:
            raise CdeDenied(CdeReason.SUPPRESSED)
        return replace(self, version=self.version + 1, state=target)


class WebhookInbox:
    def __init__(self, secret: bytes) -> None:
        self._secret = secret
        self._events: dict[str, str] = {}

    def accept(self, *, event_id: str, purpose: str, payload_digest: str, signature: str) -> bool:
        expected = hmac.new(
            self._secret,
            f"{event_id}:{purpose}:{payload_digest}".encode(),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(signature, expected):
            raise CdeDenied(CdeReason.AUTHORITY_DENIED)
        prior = self._events.get(event_id)
        if prior is not None and prior != payload_digest:
            raise CdeDenied(CdeReason.IDEMPOTENCY_CONFLICT)
        self._events[event_id] = payload_digest
        return prior is None


def require_contact_allowed(*, consent_current: bool, suppressed: bool, commitment: str | None) -> None:
    if suppressed:
        raise CdeDenied(CdeReason.SUPPRESSED)
    if not consent_current:
        raise CdeDenied(CdeReason.CONSENT_REQUIRED)
    if commitment in PROHIBITED_COMMITMENTS:
        raise CdeDenied(CdeReason.AUTHORITY_DENIED)


@dataclass(frozen=True)
class ConversionObservation:
    observation_id: str
    outcome_type: str
    source: str
    method: str
    window: str
    mapping_version: str
    confidence: str
    coverage: str
    correction_ref: str | None
    limitations: tuple[str, ...]

    def __post_init__(self) -> None:
        outcome_types = {
            "ENGAGEMENT",
            "LEAD",
            "BOOKING",
            "CONVERSION",
            "REVENUE",
            "CUSTOMER_OUTCOME",
            "DMA_PERFORMANCE",
        }
        if self.outcome_type not in outcome_types or not self.limitations:
            raise CdeDenied(CdeReason.INVALID_REQUEST)
