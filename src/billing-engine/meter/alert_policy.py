# Implements: work-contracts/WC-028-*.md §WC028-01b:alert_policy.py
# constitutional_basis: C-059 (Implementation Traceability)
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class AlertAction(StrEnum):
    """Alert action types per section 2.3a threshold ladder."""

    LOG = "LOG"
    NOTIFY = "NOTIFY"
    FA = "FA"
    BLOCK = "BLOCK"


class AlertScope(StrEnum):
    """Three scopes for threshold monitoring."""

    CUSTOMER_BUCKET = "CUSTOMER_BUCKET"
    AGENCY = "AGENCY"
    PROCUREMENT = "PROCUREMENT"


@dataclass(frozen=True)
class ThresholdRule:
    """One rung on the section 2.3a threshold ladder."""

    name: str
    consumed_pct_trigger: float  # 0.0-1.0  (e.g. 0.70 means 70% consumed)
    action: AlertAction
    bypass_quiet_hours: bool = False


@dataclass(frozen=True)
class RunwayThresholdRule:
    """Procurement scope: triggers on days_remaining <= threshold."""

    name: str
    days_remaining_trigger: float  # e.g. 30.0
    action: AlertAction
    bypass_quiet_hours: bool = False


@dataclass
class ThresholdPolicy:
    """Ordered list of ThresholdRules for one scope."""

    scope: AlertScope
    thresholds: list[ThresholdRule] = field(default_factory=list)
    runway_thresholds: list[RunwayThresholdRule] = field(default_factory=list)
    quiet_hours_start_ist: int = 23
    quiet_hours_end_ist: int = 6


# ---------------------------------------------------------------------------
# Section 2.3a Scope 1 -- Customer Bucket
# ---------------------------------------------------------------------------
CUSTOMER_BUCKET_POLICY: ThresholdPolicy = ThresholdPolicy(
    scope=AlertScope.CUSTOMER_BUCKET,
    thresholds=[
        ThresholdRule(
            name="WARN_30",
            consumed_pct_trigger=0.70,  # 30% remaining -> 70% consumed
            action=AlertAction.NOTIFY,
            bypass_quiet_hours=False,
        ),
        ThresholdRule(
            name="WARN_20",
            consumed_pct_trigger=0.80,
            action=AlertAction.NOTIFY,
            bypass_quiet_hours=False,
        ),
        ThresholdRule(
            name="WARN_10",
            consumed_pct_trigger=0.90,
            action=AlertAction.NOTIFY,
            bypass_quiet_hours=True,
        ),
        ThresholdRule(
            name="AD_WALLET_BELOW_MINIMUM",
            consumed_pct_trigger=1.00,  # balance reaches zero
            action=AlertAction.BLOCK,
            bypass_quiet_hours=True,
        ),
    ],
)

# ---------------------------------------------------------------------------
# Section 2.3a Scope 2 -- Agency Sub-wallet
# ---------------------------------------------------------------------------
AGENCY_POLICY: ThresholdPolicy = ThresholdPolicy(
    scope=AlertScope.AGENCY,
    thresholds=[
        ThresholdRule(
            name="AGENCY_WARN_50",
            consumed_pct_trigger=0.50,
            action=AlertAction.LOG,
            bypass_quiet_hours=False,
        ),
        ThresholdRule(
            name="AGENCY_WARN_80",
            consumed_pct_trigger=0.80,
            action=AlertAction.NOTIFY,
            bypass_quiet_hours=False,
        ),
        ThresholdRule(
            name="AGENCY_CRITICAL",
            consumed_pct_trigger=0.95,
            action=AlertAction.FA,
            bypass_quiet_hours=True,
        ),
    ],
)

# ---------------------------------------------------------------------------
# Section 2.3a Scope 3 -- WAOOAW Procurement Runway
# ---------------------------------------------------------------------------
PROCUREMENT_POLICY: ThresholdPolicy = ThresholdPolicy(
    scope=AlertScope.PROCUREMENT,
    runway_thresholds=[
        RunwayThresholdRule(
            name="RUNWAY_P2",
            days_remaining_trigger=30.0,
            action=AlertAction.LOG,
            bypass_quiet_hours=False,
        ),
        RunwayThresholdRule(
            name="RUNWAY_P1",
            days_remaining_trigger=14.0,
            action=AlertAction.NOTIFY,
            bypass_quiet_hours=False,
        ),
        RunwayThresholdRule(
            name="RUNWAY_P0",
            days_remaining_trigger=7.0,
            action=AlertAction.FA,
            bypass_quiet_hours=True,
        ),
        RunwayThresholdRule(
            name="RUNWAY_CRITICAL",
            days_remaining_trigger=3.0,
            action=AlertAction.FA,
            bypass_quiet_hours=True,
        ),
        RunwayThresholdRule(
            name="RUNWAY_EMERGENCY",
            days_remaining_trigger=1.0,
            action=AlertAction.BLOCK,
            bypass_quiet_hours=True,
        ),
    ],
)