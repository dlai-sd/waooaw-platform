# Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C5-02
# Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C4-11
# Constitutional basis: C-059, C-088, C-089, C-091
"""Live-margin watch: recompute every in-force package at current rates (WC-136 C5-02).

A package breaches when its base price falls below its cost floor or below the minimum compliant base
price of the effective policy. ``recompute`` is run after every RATE authorization and daily
(``register_margin_watch_job``, the reconciliation scheduler pattern); it only reads and reports.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Literal, Protocol
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from pydantic import ValidationError

from markup.package_engine import PackageReferenceData, parse_package_body, project_package, thread_ids_of
from markup.package_models import PackageBody
from wallet.spend_events import record_live_margin_floor_breach
from pricing.engine import PricingRepository
from pricing.models import PricingKind, PricingVersion
from pricing.validators import minimum_margin_of

logger = logging.getLogger(__name__)

POLICY_SUBJECT_KEY = "policy:platform"
LIVE_MARGIN_METRIC = "waooaw_live_margin_floor_breach"
LIVE_MARGIN_JOB_ID = "wbe_live_margin_watch"
DEFAULT_JOB_HOUR = 3
DEFAULT_JOB_MINUTE = 30
_TZ_KOLKATA = ZoneInfo("Asia/Kolkata")

BreachReason = Literal["BELOW_COST_FLOOR", "BELOW_MINIMUM_MARGIN"]


@dataclass(frozen=True)
class MarginBreach:
    version_id: str
    subject_key: str
    agent_type: str
    agent_version: str
    package_code: str
    reason: BreachReason
    price_incl_gst_paise: int
    base_price_paise: int
    cost_floor_paise: int
    margin_pct: float | None
    minimum_margin_pct: float | None
    minimum_compliant_price_paise: int | None


class BreachReporter(Protocol):
    def report(self, breaches: Sequence[MarginBreach]) -> None: ...


class LoggingBreachReporter:
    """Emits the ``waooaw_live_margin_floor_breach`` event; no customer or personal data is involved."""

    def report(self, breaches: Sequence[MarginBreach]) -> None:
        record_live_margin_floor_breach(len(breaches))
        if breaches:
            logger.warning(
                LIVE_MARGIN_METRIC,
                extra={"breach_count": len(breaches), "breaches": [asdict(item) for item in breaches]},
            )
        else:
            logger.info(LIVE_MARGIN_METRIC, extra={"breach_count": 0, "breaches": []})


async def recompute(
    *,
    repository: PricingRepository,
    reference: PackageReferenceData,
    at: datetime,
    reporter: BreachReporter | None = None,
) -> list[MarginBreach]:
    """Recompute every in-force package at current rates and return those below floor or minimum margin."""
    policy = await repository.effective_at(PricingKind.POLICY, POLICY_SUBJECT_KEY, at)
    minimum_margin = minimum_margin_of(None if policy is None else policy.body)
    versions = await repository.list_in_force(PricingKind.PACKAGE, at)
    parsed: list[tuple[PricingVersion, PackageBody]] = []
    for version in versions:
        try:
            parsed.append((version, parse_package_body(version.body)))
        except ValidationError:
            logger.error("pricing_package_body_unreadable", extra={"context": "margin_watch"})
    rates = await reference.thread_rates(thread_ids_of([body for _, body in parsed]))
    breaches: list[MarginBreach] = []
    for version, body in parsed:
        projection = project_package(body, rates, minimum_margin)
        base = projection.base_price_paise
        minimum_base = projection.minimum_compliant_base_paise
        if base < projection.cost_floor_paise:
            reason: BreachReason = "BELOW_COST_FLOOR"
        elif minimum_base is not None and base < minimum_base:
            reason = "BELOW_MINIMUM_MARGIN"
        else:
            continue
        breaches.append(
            MarginBreach(
                version_id=str(version.version_id),
                subject_key=version.subject_key,
                agent_type=body.agent_type,
                agent_version=body.agent_version,
                package_code=body.package_code,
                reason=reason,
                price_incl_gst_paise=body.price_incl_gst_paise,
                base_price_paise=base,
                cost_floor_paise=projection.cost_floor_paise,
                margin_pct=projection.margin_pct,
                minimum_margin_pct=projection.minimum_margin_pct,
                minimum_compliant_price_paise=projection.minimum_compliant_price_paise,
            )
        )
    (reporter or LoggingBreachReporter()).report(breaches)
    return breaches


def register_margin_watch_job(
    scheduler: AsyncIOScheduler,
    job: Callable[[], Awaitable[object]],
    *,
    hour: int = DEFAULT_JOB_HOUR,
    minute: int = DEFAULT_JOB_MINUTE,
) -> None:
    """Register the daily live-margin recompute (Asia/Kolkata) on the existing WBE scheduler."""
    scheduler.add_job(
        job,
        trigger=CronTrigger(hour=hour, minute=minute, timezone=_TZ_KOLKATA),
        id=LIVE_MARGIN_JOB_ID,
        name=f"WBE Live Margin Watch ({hour:02d}:{minute:02d} IST)",
        replace_existing=True,
    )
