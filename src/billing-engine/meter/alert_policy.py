# Implements: <spec-path> §<section>
# constitutional_basis: C-059 (Implementation Traceability)
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class AlertAction(StrEnum):
    """Alert action types per §2.3a threshold ladder."""

    LOG = "LOG"
    NOTIFY = "NOTIFY"
    FA = "FA"
    BLOCK = "BLOCK"


class AlertScope(StrEnum):
    """Alert scope levels: customer bucket, agency sub-wallet, or procurement runway."""

    CUSTOMER_BUCKET = "CUSTOMER_BUCKET"
    AGENCY = "AGENCY"
    PROCUREMENT = "PROCUREMENT"


@dataclass(frozen=True)
class ThresholdRule:
    """
    A single threshold rule in the section 2.3a ladder.

    Constitutional: C-051 (resource transparency), C-043 (budget ceiling).

    consumed_pct_trigger: float in [0.0, 1.0] - fires when pct_consumed >= this value.
    action: AlertAction - what to do when the threshold is breached.
    bypass_quiet_hours: bool - if True, alert fires even during quiet hours (23:00-06:00 IST).
    """

    name: str
    consumed_pct_trigger: float
    action: AlertAction
    bypass_quiet_hours: bool = False


@dataclass(frozen=True)
class ThresholdPolicy:
    """
    Full threshold ladder for a given scope.

    Constitutional: C-049 (honest limitation — escalating alerts), C-051 (transparency).

    quiet_hours_start_ist: int - hour (24h) when quiet window begins (default 23).
    quiet_hours_end_ist: int  - hour (24h) when quiet window ends   (default  6).
    Thresholds are evaluated in list order; first match fires.
    """

    scope: AlertScope
    thresholds: list[ThresholdRule]
    quiet_hours_start_ist: int = 23
    quiet_hours_end_ist: int = 6


# ---------------------------------------------------------------------------
# Section 2.3a Scope 1 - Customer Bucket
# Ladder: WARN_30 (70% consumed) -> WARN_10 (90%) -> BLOCK (100%)
# 70% consumed means 30% remaining; 90% consumed means 10% remaining.
# BLOCK bypasses quiet hours so billing halt is never silently deferred.
# Constitutional: C-043 (budget ceiling enforcement), C-049 (honest limitation).
# ---------------------------------------------------------------------------
CUSTOMER_BUCKET_POLICY: ThresholdPolicy = ThresholdPolicy(
    scope=AlertScope.CUSTOMER_BUCKET,
    thresholds=[
        ThresholdRule(
            name="WARN_30",
            consumed_pct_trigger=0.70,
            action=AlertAction.NOTIFY,
            bypass_quiet_hours=False,
        ),
        ThresholdRule(
            name="WARN_10",
            consumed_pct_trigger=0.90,
            action=AlertAction.NOTIFY,
            bypass_quiet_hours=False,
        ),
        ThresholdRule(
            name="AD_WALLET_BELOW_MINIMUM",
            consumed_pct_trigger=1.00,
            action=AlertAction.BLOCK,
            bypass_quiet_hours=True,
        ),
    ],
)

# ---------------------------------------------------------------------------
# Section 2.3a Scope 2 - Agency Sub-Wallet
# Agency budgets have a softer ladder: LOG at 50%, NOTIFY at 75%, FA at 90%.
# A NULL agency quota produces no alert (handled in MeterService.check_thresholds).
# Constitutional: C-049 (honest limitation at agency level), C-051 (transparency).
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
            name="AGENCY_WARN_75",
            consumed_pct_trigger=0.75,
            action=AlertAction.NOTIFY,
            bypass_quiet_hours=False,
        ),
        ThresholdRule(
            name="AGENCY_CRITICAL_90",
            consumed_pct_trigger=0.90,
            action=AlertAction.FA,
            bypass_quiet_hours=True,
        ),
    ],
)

# ---------------------------------------------------------------------------
# Section 2.3a Scope 3 - WAOOAW Procurement Runway
# Expressed in days_remaining, not pct_consumed.
# Sentinel: consumed_pct_trigger is unused for runway rules; MeterService uses
# the days_remaining comparison directly. We encode the day thresholds in the
# rule name: RUNWAY_P2 (≤30d), RUNWAY_P1 (≤14d), RUNWAY_P0 (≤7d),
# RUNWAY_CRITICAL (≤3d), RUNWAY_EMERGENCY (≤1d).
# Constitutional: C-043 (procurement runway ceiling), C-051 (transparency on provider availability).
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class RunwayThresholdRule(ThresholdRule):
    """
    Extension of ThresholdRule for Scope 3 (Procurement Runway).

    days_trigger: int - fires when provider runway days_remaining <= this value.
    consumed_pct_trigger is set to 0.0 and ignored by MeterService for runway rules.
    """

    days_trigger: int = 0


PROCUREMENT_POLICY: ThresholdPolicy = ThresholdPolicy(
    scope=AlertScope.PROCUREMENT,
    thresholds=[
        RunwayThresholdRule(
            name="RUNWAY_P2",
            consumed_pct_trigger=0.0,
            action=AlertAction.LOG,
            bypass_quiet_hours=False,
            days_trigger=30,
        ),
        RunwayThresholdRule(
            name="RUNWAY_P1",
            consumed_pct_trigger=0.0,
            action=AlertAction.NOTIFY,
            bypass_quiet_hours=False,
            days_trigger=14,
        ),
        RunwayThresholdRule(
            name="RUNWAY_P0",
            consumed_pct_trigger=0.0,
            action=AlertAction.FA,
            bypass_quiet_hours=True,
            days_trigger=7,
        ),
        RunwayThresholdRule(
            name="RUNWAY_CRITICAL",
            consumed_pct_trigger=0.0,
            action=AlertAction.FA,
            bypass_quiet_hours=True,
            days_trigger=3,
        ),
        RunwayThresholdRule(
            name="RUNWAY_EMERGENCY",
            consumed_pct_trigger=0.0,
            action=AlertAction.BLOCK,
            bypass_quiet_hours=True,
            days_trigger=1,
        ),
    ],
)