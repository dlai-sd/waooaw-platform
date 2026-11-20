# Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C5-08
# Constitutional basis: C-059, C-088, C-089, C-091
"""Funding and margin dashboards: read-only aggregates over wallet entries and the effective packages.

Aggregates only. No name, phone number or e-mail is read: a lead is shown through a pseudonymous
reference (``lead_`` plus a digest prefix of the stored lead reference), a tenant through its opaque
identifier, and every other figure is a sum or a count. A table or role that is not (yet) readable
yields an empty section instead of a failed dashboard; the failure is logged, never shown.

Definitions used here: a *conversation* is a trial opened in the period (the point at which a
prospect starts talking to the agent), so cost per conversation is acquisition plus trial spend over
trials; cost per lead is acquisition spend over leads that consumed acquisition budget; a *hire* is a
trial relationship that opened a subscription account in the period. The cost of a component is the
mean settled amount per settlement against the unit cost of its recipe at current rates.
"""

from __future__ import annotations

import hashlib
import logging
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from typing import Any, Protocol

from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from markup.package_engine import SqlPackageReferenceData, ThreadRate, base_price_paise, project_package
from markup.package_models import PackageBody
from pricing.models import PricingKind, PricingVersion
from pricing.validators import minimum_margin_of

logger = logging.getLogger(__name__)

SCHEMA_VERSION = "1.0"
DEFAULT_PERIOD_DAYS = 30
SECTION_ROW_LIMIT = 500
COMPONENT_ROW_LIMIT = 200
ACCOUNT_CLASSES = ("ACQUISITION", "SETUP_GRANT", "TRIAL", "SUBSCRIPTION", "PLATFORM_FLOOR", "SIMULATION")
GRANT_KINDS = {"TRIAL": "TRIAL", "SETUP_GRANT": "SETUP"}
PERCENT = 100


@dataclass(frozen=True)
class Period:
    start: datetime
    end: datetime
    first_day: date
    last_day: date


def resolve_period(period_from: date | None, period_to: date | None, now: datetime) -> Period:
    last = period_to or now.astimezone(timezone.utc).date()
    first = period_from or last - timedelta(days=DEFAULT_PERIOD_DAYS - 1)
    return Period(
        start=datetime.combine(first, time.min, tzinfo=timezone.utc),
        end=datetime.combine(last + timedelta(days=1), time.min, tzinfo=timezone.utc),
        first_day=first,
        last_day=last,
    )


class LedgerReader(Protocol):
    """Row source of the funding dashboard; rows are plain mappings, empty when the source is unavailable."""

    async def spend_by_account_class(self, period: Period) -> list[Mapping[str, Any]]: ...
    async def spend_by_tenant(self, period: Period) -> list[Mapping[str, Any]]: ...
    async def spend_by_campaign(self, period: Period) -> list[Mapping[str, Any]]: ...
    async def spend_by_lead(self, period: Period) -> list[Mapping[str, Any]]: ...
    async def funnel(self, period: Period) -> Mapping[str, int]: ...
    async def grant_consumption(self, period: Period) -> list[Mapping[str, Any]]: ...
    async def settled_by_component(self, period: Period) -> list[Mapping[str, Any]]: ...
    async def lot_events(self, period: Period) -> Mapping[str, int]: ...
    async def breakers(self) -> list[Mapping[str, Any]]: ...


class SqlLedgerReader:
    """Reads ``business.wallet_*`` and the provider breaker table through a savepoint per query."""

    def __init__(self, session: Any) -> None:
        self._session = session

    async def _rows(self, statement: str, params: Mapping[str, Any] | None = None) -> list[Mapping[str, Any]]:
        try:
            async with self._session.begin_nested():
                result = await self._session.execute(text(statement), dict(params or {}))
                return [dict(row._mapping) for row in result.fetchall()]
        except DBAPIError:
            logger.warning("pricing_dashboard_source_unavailable")
            return []

    @staticmethod
    def _bounds(period: Period) -> dict[str, datetime]:
        return {"start": period.start, "end": period.end}

    async def spend_by_account_class(self, period: Period) -> list[Mapping[str, Any]]:
        return await self._rows(
            """
            SELECT a.account_class AS account_class, COALESCE(SUM(e.amount_paise), 0) AS spent
            FROM business.wallet_entries e
            JOIN business.wallet_accounts a ON a.tenant_id = e.tenant_id AND a.account_id = e.account_id
            WHERE e.entry_kind = 'SETTLE' AND e.occurred_at >= :start AND e.occurred_at < :end
            GROUP BY a.account_class
            """,
            self._bounds(period),
        )

    async def spend_by_tenant(self, period: Period) -> list[Mapping[str, Any]]:
        return await self._rows(
            f"""
            SELECT e.tenant_id AS tenant_ref, SUM(e.amount_paise) AS spent
            FROM business.wallet_entries e
            WHERE e.entry_kind = 'SETTLE' AND e.occurred_at >= :start AND e.occurred_at < :end
            GROUP BY e.tenant_id ORDER BY spent DESC, e.tenant_id LIMIT {SECTION_ROW_LIMIT}
            """,
            self._bounds(period),
        )

    async def spend_by_campaign(self, period: Period) -> list[Mapping[str, Any]]:
        return await self._rows(
            f"""
            SELECT a.campaign_ref AS campaign_ref, SUM(e.amount_paise) AS spent
            FROM business.wallet_entries e
            JOIN business.wallet_accounts a ON a.tenant_id = e.tenant_id AND a.account_id = e.account_id
            WHERE e.entry_kind = 'SETTLE' AND a.campaign_ref IS NOT NULL
              AND e.occurred_at >= :start AND e.occurred_at < :end
            GROUP BY a.campaign_ref ORDER BY spent DESC, a.campaign_ref LIMIT {SECTION_ROW_LIMIT}
            """,
            self._bounds(period),
        )

    async def spend_by_lead(self, period: Period) -> list[Mapping[str, Any]]:
        return await self._rows(
            f"""
            SELECT a.lead_ref AS lead_ref, SUM(e.amount_paise) AS spent
            FROM business.wallet_entries e
            JOIN business.wallet_accounts a ON a.tenant_id = e.tenant_id AND a.account_id = e.account_id
            WHERE e.entry_kind = 'SETTLE' AND a.lead_ref IS NOT NULL
              AND e.occurred_at >= :start AND e.occurred_at < :end
            GROUP BY a.lead_ref ORDER BY spent DESC, a.lead_ref LIMIT {SECTION_ROW_LIMIT}
            """,
            self._bounds(period),
        )

    async def funnel(self, period: Period) -> Mapping[str, int]:
        rows = await self._rows(
            """
            SELECT
              (SELECT count(*) FROM business.wallet_accounts t
                WHERE t.account_class = 'TRIAL' AND t.created_at >= :start AND t.created_at < :end) AS trials,
              (SELECT count(DISTINCT s.relationship_id) FROM business.wallet_accounts s
                WHERE s.account_class = 'SUBSCRIPTION' AND s.created_at >= :start AND s.created_at < :end
                  AND EXISTS (SELECT 1 FROM business.wallet_accounts t
                              WHERE t.account_class = 'TRIAL' AND t.relationship_id = s.relationship_id)) AS hires,
              (SELECT count(DISTINCT a.lead_ref) FROM business.wallet_entries e
                JOIN business.wallet_accounts a ON a.tenant_id = e.tenant_id AND a.account_id = e.account_id
                WHERE e.entry_kind = 'SETTLE' AND a.account_class = 'ACQUISITION' AND a.lead_ref IS NOT NULL
                  AND e.occurred_at >= :start AND e.occurred_at < :end) AS leads
            """,
            self._bounds(period),
        )
        row = rows[0] if rows else {}
        return {key: int(row.get(key) or 0) for key in ("trials", "hires", "leads")}

    async def grant_consumption(self, period: Period) -> list[Mapping[str, Any]]:
        return await self._rows(
            """
            WITH granted AS (
                SELECT tenant_id, account_id, SUM(credited_paise) AS paise
                FROM business.wallet_lots WHERE lot_kind = 'GRANT' GROUP BY tenant_id, account_id),
            consumed AS (
                SELECT tenant_id, account_id, SUM(amount_paise) AS paise
                FROM business.wallet_entries WHERE entry_kind = 'SETTLE' GROUP BY tenant_id, account_id)
            SELECT a.account_class AS account_class, a.agent_type AS agent_type, a.agent_version AS agent_version,
                   COALESCE(SUM(c.paise), 0) AS consumed, COALESCE(SUM(g.paise), 0) AS granted
            FROM business.wallet_accounts a
            LEFT JOIN granted g ON g.tenant_id = a.tenant_id AND g.account_id = a.account_id
            LEFT JOIN consumed c ON c.tenant_id = a.tenant_id AND c.account_id = a.account_id
            WHERE a.account_class IN ('TRIAL', 'SETUP_GRANT') AND a.created_at >= :start AND a.created_at < :end
            GROUP BY a.account_class, a.agent_type, a.agent_version
            ORDER BY a.account_class, a.agent_type, a.agent_version
            """,
            self._bounds(period),
        )

    async def settled_by_component(self, period: Period) -> list[Mapping[str, Any]]:
        return await self._rows(
            f"""
            SELECT e.component_id AS component_id, count(*) AS settlements, SUM(e.amount_paise) AS settled
            FROM business.wallet_entries e
            WHERE e.entry_kind = 'SETTLE' AND e.component_id IS NOT NULL
              AND e.occurred_at >= :start AND e.occurred_at < :end
            GROUP BY e.component_id ORDER BY e.component_id LIMIT {COMPONENT_ROW_LIMIT}
            """,
            self._bounds(period),
        )

    async def lot_events(self, period: Period) -> Mapping[str, int]:
        rows = await self._rows(
            """
            SELECT
              (SELECT count(*) FROM business.wallet_lots l
                WHERE l.lot_kind = 'TOPUP_CREDIT' AND l.created_at >= :start AND l.created_at < :end) AS topups,
              (SELECT count(*) FROM business.wallet_lots l
                WHERE EXISTS (SELECT 1 FROM business.wallet_entries e
                              WHERE e.tenant_id = l.tenant_id AND e.lot_id = l.lot_id AND e.entry_kind = 'SETTLE'
                                AND e.occurred_at >= :start AND e.occurred_at < :end)
                  AND (SELECT COALESCE(SUM(e.amount_paise), 0) FROM business.wallet_entries e
                       WHERE e.tenant_id = l.tenant_id AND e.lot_id = l.lot_id AND e.entry_kind = 'SETTLE')
                      >= l.credited_paise) AS exhaustions
            """,
            self._bounds(period),
        )
        row = rows[0] if rows else {}
        return {"topups": int(row.get("topups") or 0), "exhaustions": int(row.get("exhaustions") or 0)}

    async def breakers(self) -> list[Mapping[str, Any]]:
        return await self._rows(
            "SELECT provider::text AS breaker, state FROM institutional.provider_circuit_breaker ORDER BY provider::text"
        )


def pseudonymous_lead_ref(lead_ref: str) -> str:
    return "lead_" + hashlib.sha256(lead_ref.encode("utf-8")).hexdigest()[:32]


def _paise(value: Any) -> int:
    return int(value or 0)


def _ratio_paise(total: int, count: int) -> int:
    return 0 if count <= 0 else round(total / count)


def _percent(value: float | None) -> float:
    return 0.0 if value is None else float(value)


@dataclass(frozen=True)
class PackageView:
    version: PricingVersion
    body: PackageBody


def parse_packages(versions: Sequence[PricingVersion]) -> list[PackageView]:
    views: list[PackageView] = []
    for version in versions:
        try:
            views.append(PackageView(version, PackageBody.model_validate(version.body)))
        except ValueError:
            logger.error("pricing_package_body_unreadable", extra={"pricing_subject": version.subject_key})
    return sorted(views, key=lambda item: item.version.subject_key)


def margin_packages(
    packages: Sequence[PackageView], rates: Mapping[str, ThreadRate], minimum_margin_pct: float | None
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in packages:
        projection = project_package(item.body, rates, minimum_margin_pct)
        rows.append(
            {
                "packageVersionId": str(item.version.version_id),
                "subjectKey": item.version.subject_key,
                "priceInclGstPaise": projection.price_incl_gst_paise,
                "basePricePaise": projection.base_price_paise,
                "costFloorPaise": projection.cost_floor_paise,
                "marginPercent": _percent(projection.margin_pct),
                "minimumMarginPercent": _percent(projection.minimum_margin_pct),
            }
        )
    return rows[:COMPONENT_ROW_LIMIT]


def _tolerance_state(recipe: int, actual: int, policy: Mapping[str, Any] | None) -> str:
    tolerance = (policy or {}).get("costToleranceFraction")
    alert = (policy or {}).get("costAlertFraction")
    if recipe <= 0 or not isinstance(tolerance, int | float) or not isinstance(alert, int | float):
        return "WITHIN_TOLERANCE"
    deviation = (actual - recipe) / recipe
    if deviation > tolerance:
        return "EXCEEDED"
    if deviation > alert:
        return "ALERT"
    return "WITHIN_TOLERANCE"


def component_costs(
    packages: Sequence[PackageView],
    rates: Mapping[str, ThreadRate],
    settled: Sequence[Mapping[str, Any]],
    policy: Mapping[str, Any] | None,
) -> list[dict[str, Any]]:
    """Recipe unit cost against the mean settled amount per settlement, for every component with usage."""
    recipe: dict[str, tuple[int, float]] = {}
    for item in packages:
        projection = project_package(item.body, rates, None)
        unit_costs = {cost.component_id: cost.unit_cost_paise for cost in projection.component_costs}
        for component in item.body.components:
            if component.component_id in recipe:
                continue
            base = base_price_paise(component.price_allocation_paise, item.body.gst_rate_percent)
            recipe[component.component_id] = (
                unit_costs.get(component.component_id, 0),
                base / component.quantity if component.quantity else 0.0,
            )
    rows: list[dict[str, Any]] = []
    for entry in settled:
        component_id = str(entry["component_id"])
        count = _paise(entry.get("settlements"))
        if count <= 0 or component_id not in recipe:
            continue
        actual = round(_paise(entry.get("settled")) / count)
        unit_cost, unit_revenue = recipe[component_id]
        implied = 0.0 if unit_revenue <= 0 else round(PERCENT * (unit_revenue - actual) / unit_revenue, 2)
        rows.append(
            {
                "componentId": component_id,
                "recipeCostPaise": unit_cost,
                "actualCostPaise": actual,
                "impliedMarginPercent": implied,
                "toleranceState": _tolerance_state(unit_cost, actual, policy),
            }
        )
    return rows[:COMPONENT_ROW_LIMIT]


def _period_fields(period: Period) -> dict[str, str]:
    return {"periodFrom": period.first_day.isoformat(), "periodTo": period.last_day.isoformat()}


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


async def build_funding(
    reader: LedgerReader,
    *,
    period: Period,
    now: datetime,
    components: list[dict[str, Any]],
    live_margin_breaches: int,
) -> dict[str, Any]:
    by_class = {str(row["account_class"]): _paise(row.get("spent")) for row in await reader.spend_by_account_class(period)}
    funnel = await reader.funnel(period)
    lot_events = await reader.lot_events(period)
    trials, hires, leads = funnel["trials"], funnel["hires"], funnel["leads"]
    acquisition = by_class.get("ACQUISITION", 0)
    return {
        "schemaVersion": SCHEMA_VERSION,
        "generatedAt": _iso(now),
        **_period_fields(period),
        "spendByAccountClass": [{"accountClass": name, "spentPaise": by_class.get(name, 0)} for name in ACCOUNT_CLASSES],
        "spendByTenant": [
            {"tenantRef": str(row["tenant_ref"]), "spentPaise": _paise(row.get("spent"))}
            for row in await reader.spend_by_tenant(period)
        ],
        "spendByCampaign": [
            {"campaignRef": str(row["campaign_ref"])[:200], "spentPaise": _paise(row.get("spent"))}
            for row in await reader.spend_by_campaign(period)
        ],
        "leadSpend": [
            {"leadRef": pseudonymous_lead_ref(str(row["lead_ref"])), "spentPaise": _paise(row.get("spent"))}
            for row in await reader.spend_by_lead(period)
        ],
        "costPerLeadPaise": _ratio_paise(acquisition, leads),
        "costPerConversationPaise": _ratio_paise(acquisition + by_class.get("TRIAL", 0), trials),
        "trialToHire": {
            "trials": trials,
            "hires": hires,
            "conversionPercent": 0.0 if trials <= 0 else min(float(PERCENT), round(PERCENT * hires / trials, 2)),
        },
        "grantConsumption": [
            {
                "grantKind": GRANT_KINDS[str(row["account_class"])],
                "agentType": str(row["agent_type"]),
                "agentVersion": str(row["agent_version"]),
                "consumedPaise": _paise(row.get("consumed")),
                "grantedPaise": _paise(row.get("granted")),
            }
            for row in await reader.grant_consumption(period)
            if str(row["account_class"]) in GRANT_KINDS
        ],
        "componentCost": components,
        "events": [
            {"eventKind": "EXHAUSTION", "count": lot_events["exhaustions"]},
            {"eventKind": "TOPUP", "count": lot_events["topups"]},
        ],
        "breakers": [
            {"breaker": str(row["breaker"])[:120], "state": str(row["state"])}
            for row in await reader.breakers()
            if str(row["state"]) in ("CLOSED", "OPEN", "HALF_OPEN")
        ],
        "liveMarginBreaches": live_margin_breaches,
    }


async def _pricing_context(
    session: Any, service: Any, now: datetime, reference_factory: Callable[[Any], Any]
) -> tuple[list[PackageView], dict[str, ThreadRate], Mapping[str, Any] | None, float | None]:
    packages = parse_packages(await service.effective_versions(PricingKind.PACKAGE, now))
    thread_ids = sorted({entry.thread_id for item in packages for c in item.body.components for entry in c.recipe})
    rates = dict(await reference_factory(session).thread_rates(thread_ids))
    policy = await service.effective_version(PricingKind.POLICY, "policy:platform", now)
    policy_body = None if policy is None else policy.body
    return packages, rates, policy_body, minimum_margin_of(policy_body)


async def funding_dashboard(
    session: Any,
    service: Any,
    *,
    period_from: date | None,
    period_to: date | None,
    now: datetime,
    reader_factory: Callable[[Any], LedgerReader] = SqlLedgerReader,
    reference_factory: Callable[[Any], Any] = SqlPackageReferenceData,
) -> dict[str, Any]:
    period = resolve_period(period_from, period_to, now)
    reader = reader_factory(session)
    packages, rates, policy_body, _ = await _pricing_context(session, service, now, reference_factory)
    components = component_costs(packages, rates, await reader.settled_by_component(period), policy_body)
    breaches = await service.live_margin(now)
    return await build_funding(reader, period=period, now=now, components=components, live_margin_breaches=len(breaches))


async def margin_dashboard(
    session: Any,
    service: Any,
    *,
    period_from: date | None,
    period_to: date | None,
    now: datetime,
    reader_factory: Callable[[Any], LedgerReader] = SqlLedgerReader,
    reference_factory: Callable[[Any], Any] = SqlPackageReferenceData,
) -> dict[str, Any]:
    period = resolve_period(period_from, period_to, now)
    reader = reader_factory(session)
    packages, rates, policy_body, minimum = await _pricing_context(session, service, now, reference_factory)
    return {
        "schemaVersion": SCHEMA_VERSION,
        "generatedAt": _iso(now),
        **_period_fields(period),
        "packages": margin_packages(packages, rates, minimum),
        "componentCost": component_costs(packages, rates, await reader.settled_by_component(period), policy_body),
        "liveMarginBreaches": len(await service.live_margin(now)),
    }
