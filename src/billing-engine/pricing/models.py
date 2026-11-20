# Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C5-01
# Constitutional basis: C-059, C-088, C-089, C-090, C-091
"""Pricing engine types: versions, actors, version bodies and the Appendix B.5 error codes (WC-136).

Version bodies are stored as camelCase JSON. Money is integer paise; a customer price is GST-inclusive.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Literal
from uuid import UUID

from pydantic import ConfigDict, Field, model_validator

from markup.package_models import CamelModel, Violation

__all__ = [
    "ActorContext",
    "BudgetBody",
    "CouponBody",
    "EffectiveRole",
    "GrantBody",
    "PackageComponentNotAvailable",
    "PolicyBody",
    "PricingBelowFloor",
    "PricingCeilingAboveMaximum",
    "PricingDraftInvalid",
    "PricingError",
    "PricingEvent",
    "PricingForbidden",
    "PricingIllegalTransition",
    "PricingKind",
    "PricingNeedsSecondConfirmation",
    "PricingStepUpRequired",
    "PricingUnavailable",
    "PricingVersion",
    "PricingVersionNotFound",
    "RateBody",
    "RecipeThreadNotAuthorized",
    "VersionState",
    "Violation",
    "body_digest",
    "error_for_violations",
]

PERCENT_MAXIMUM = 999.99
MAXIMUM_BODY_DAYS = 366


class PricingKind(str, Enum):
    RATE = "RATE"
    PACKAGE = "PACKAGE"
    POLICY = "POLICY"
    GRANT = "GRANT"
    BUDGET = "BUDGET"
    COUPON = "COUPON"


class VersionState(str, Enum):
    DRAFT = "DRAFT"
    SIMULATED = "SIMULATED"
    SUBMITTED = "SUBMITTED"
    AUTHORIZED = "AUTHORIZED"
    EFFECTIVE = "EFFECTIVE"
    SUPERSEDED = "SUPERSEDED"
    DISCARDED = "DISCARDED"


class EffectiveRole(str, Enum):
    PRICING_ADMIN = "PRICING_ADMIN"
    FOUNDER = "FOUNDER"


@dataclass(frozen=True)
class ActorContext:
    """Identity taken from the verified delegated context (ADR-046), never from a request body."""

    actor_id: str
    effective_role: EffectiveRole
    step_up: bool = False


@dataclass(frozen=True)
class PricingVersion:
    version_id: UUID
    kind: PricingKind
    subject_key: str
    version_no: int
    state: VersionState
    body: dict[str, Any]
    body_digest: str
    seed: bool
    effective_from: datetime | None
    supersedes: UUID | None
    created_by: str
    created_at: datetime
    authorized_by: str | None
    authorized_at: datetime | None
    evidence_id: UUID | None
    needs_second_confirmation: bool
    second_confirmed_by: str | None


@dataclass(frozen=True)
class PricingEvent:
    event_id: UUID
    version_id: UUID
    from_state: VersionState | None
    to_state: VersionState
    direction: Literal["NORMAL", "SAFETY"]
    actor: str
    occurred_at: datetime
    reason: str | None


def body_digest(body: Mapping[str, Any]) -> str:
    """SHA-256 over the canonical JSON form of a version body."""
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class RateBody(CamelModel):
    thread_id: str = Field(min_length=1, max_length=50)
    provider: str | None = Field(default=None, min_length=1, max_length=100)
    unit: str | None = Field(default=None, min_length=1, max_length=100)
    raw_cost_paise: int = Field(ge=0)
    fx_buffer_pct: float = Field(ge=0, le=PERCENT_MAXIMUM)
    ops_overhead_pct: float = Field(ge=0, le=PERCENT_MAXIMUM)
    risk_premium_pct: float = Field(ge=0, le=PERCENT_MAXIMUM)


class PolicyBody(CamelModel):
    """Platform policy; annotation keys with text values (for example a seed marker) are tolerated."""

    model_config = ConfigDict(extra="allow")

    minimum_margin_pct: float = Field(ge=0, lt=100)
    payment_grace_days: int = Field(ge=0, le=MAXIMUM_BODY_DAYS)
    sunset_notice_days: int = Field(ge=0, le=MAXIMUM_BODY_DAYS)
    cost_tolerance_fraction: float = Field(ge=0, le=1)
    cost_alert_fraction: float = Field(ge=0, le=1)
    upgrade_timing: Literal["IMMEDIATE", "AT_RENEWAL"]
    downgrade_timing: Literal["IMMEDIATE", "AT_RENEWAL"]
    change_size_guard_percent: float = Field(gt=0, le=1000)
    price_multiple_guard: float = Field(gt=0, le=1000)


class GrantBody(CamelModel):
    grant_kind: Literal["TRIAL", "SETUP"]
    agent_type: str = Field(min_length=1, max_length=50)
    agent_version: str = Field(min_length=1, max_length=32)
    thread_units: dict[str, int] | None = None
    amount_paise: int | None = Field(default=None, ge=1)
    duration_days: int = Field(ge=1, le=MAXIMUM_BODY_DAYS)
    disabled: bool = False

    @model_validator(mode="after")
    def _exactly_one_allowance(self) -> GrantBody:
        has_units = bool(self.thread_units)
        has_paise = self.amount_paise is not None
        if has_units == has_paise:
            raise ValueError("a grant carries either threadUnits or amountPaise")
        if self.thread_units and any(units < 1 for units in self.thread_units.values()):
            raise ValueError("threadUnits values must be at least 1")
        return self


BudgetScope = Literal["ENVIRONMENT_CEILING", "ACQUISITION_TENANT", "ACQUISITION_CAMPAIGN", "ACQUISITION_LEAD", "SIMULATION"]


class BudgetBody(CamelModel):
    scope: BudgetScope
    reference: str = Field(min_length=1, max_length=100, pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")
    maximum_paise: int = Field(ge=0)
    per_visitor_messages: int | None = Field(default=None, ge=1)
    per_day_new_sessions: int | None = Field(default=None, ge=1)


class CouponBody(CamelModel):
    code: str = Field(pattern=r"^[A-Z0-9][A-Z0-9_-]{2,31}$")
    agent_type: str = Field(min_length=1, max_length=50)
    agent_version: str = Field(min_length=1, max_length=32)
    percent_off: int | None = Field(default=None, ge=1, le=100)
    amount_paise: int | None = Field(default=None, ge=1)
    cap_paise: int | None = Field(default=None, ge=1)
    expires_at: datetime
    reason: str = Field(min_length=1, max_length=500)
    max_redemptions: int = Field(ge=1)

    @model_validator(mode="after")
    def _exactly_one_discount(self) -> CouponBody:
        if (self.percent_off is None) == (self.amount_paise is None):
            raise ValueError("a coupon carries either percentOff or amountPaise")
        if self.expires_at.tzinfo is None:
            raise ValueError("expiresAt must carry a UTC offset")
        return self


class PricingError(Exception):
    """Base class; ``code`` and ``status_code`` follow WC-136 Appendix B.5."""

    code = "PRICING_UNAVAILABLE"
    status_code = 503

    def __init__(self, message: str, *, details: Mapping[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details: dict[str, Any] = dict(details or {})


class PricingForbidden(PricingError):
    code = "PRICING_FORBIDDEN"
    status_code = 403


class PricingStepUpRequired(PricingError):
    code = "PRICING_STEP_UP_REQUIRED"
    status_code = 403


class PricingNeedsSecondConfirmation(PricingError):
    code = "PRICING_NEEDS_SECOND_CONFIRMATION"
    status_code = 409


class PricingIllegalTransition(PricingError):
    code = "PRICING_ILLEGAL_TRANSITION"
    status_code = 409


class PricingVersionNotFound(PricingError):
    code = "PRICING_VERSION_NOT_FOUND"
    status_code = 404


class PricingUnavailable(PricingError):
    code = "PRICING_UNAVAILABLE"
    status_code = 503


class PricingDraftInvalid(PricingError):
    code = "PRICING_DRAFT_INVALID"
    status_code = 422

    def __init__(self, violations: Sequence[Violation], *, message: str = "The pricing draft is invalid.") -> None:
        super().__init__(message, details={"violations": [item.model_dump(by_alias=True) for item in violations]})
        self.violations: list[Violation] = list(violations)


class PricingBelowFloor(PricingDraftInvalid):
    code = "PRICING_BELOW_FLOOR"

    @property
    def minimum_compliant_price_paise(self) -> int | None:
        for item in self.violations:
            value = item.details.get("minimumCompliantPricePaise")
            if isinstance(value, int):
                return value
        return None


class PricingCeilingAboveMaximum(PricingDraftInvalid):
    code = "PRICING_CEILING_ABOVE_MAXIMUM"


class PackageComponentNotAvailable(PricingDraftInvalid):
    code = "PACKAGE_COMPONENT_NOT_AVAILABLE"


class RecipeThreadNotAuthorized(PricingDraftInvalid):
    code = "RECIPE_THREAD_NOT_AUTHORIZED"


_DEDICATED_VIOLATION_ERRORS: dict[str, type[PricingDraftInvalid]] = {
    "PRICING_BELOW_FLOOR": PricingBelowFloor,
    "PRICING_CEILING_ABOVE_MAXIMUM": PricingCeilingAboveMaximum,
    "PACKAGE_COMPONENT_NOT_AVAILABLE": PackageComponentNotAvailable,
    "RECIPE_THREAD_NOT_AUTHORIZED": RecipeThreadNotAuthorized,
}


def error_for_violations(violations: Sequence[Violation]) -> PricingDraftInvalid:
    """The dedicated Appendix B.5 error when every violation is of one dedicated code, else the generic one."""
    codes = {item.code for item in violations}
    if len(codes) == 1:
        dedicated = _DEDICATED_VIOLATION_ERRORS.get(next(iter(codes)))
        if dedicated is not None:
            return dedicated(violations)
    return PricingDraftInvalid(violations)
