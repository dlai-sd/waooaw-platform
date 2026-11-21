# Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C4-13
# Constitutional basis: C-059, C-063, C-088
"""Customer-safe catalogue of the packages on sale for one agent version (WC-136 C4-13).

Only a package version that is EFFECTIVE and activated for sale is listed. The listing carries the price
including GST, its base and GST parts, the billing period and the components (identifier, quantity,
cadence, selectable maximum). Recipes, thread rates, costs, margins and provider units are never read
into the result, so they cannot leak through it.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from markup.package_engine import base_price_paise, parse_package_body
from pricing.models import PricingKind, VersionState
from pricing.repository import SqlPricingRepository

MAX_PAGE = 100

_FOR_SALE_SQL = text(
    """
    SELECT p.package_version_id, p.bundle_tier
    FROM institutional.bundle_profiles p
    WHERE p.agent_type = :agent_type AND p.agent_version = :agent_version
      AND p.is_active = TRUE AND p.package_version_id IS NOT NULL
      AND (
        CAST(:tier AS TEXT) IS NULL
        OR p.bundle_tier > CAST(:tier AS TEXT)
        OR (p.bundle_tier = CAST(:tier AS TEXT) AND CAST(p.package_version_id AS TEXT) > CAST(:version AS TEXT))
      )
    ORDER BY p.bundle_tier, CAST(p.package_version_id AS TEXT)
    LIMIT :limit
    """
)


class CatalogCursorError(ValueError):
    """The continuation token is not one this catalogue issued."""


def _split_cursor(after: str | None) -> tuple[str | None, str | None]:
    if after is None:
        return None, None
    tier, separator, version = after.partition("|")
    try:
        UUID(version)
    except ValueError:
        raise CatalogCursorError("CATALOG_CURSOR_INVALID") from None
    if not separator or not tier:
        raise CatalogCursorError("CATALOG_CURSOR_INVALID")
    return tier, version


@dataclass(frozen=True)
class CatalogComponent:
    component_id: str
    quantity: int
    cadence: str
    selectable_maximum: int | None


@dataclass(frozen=True)
class CatalogPackage:
    package_id: UUID
    package_code: str
    display_name: str
    agent_type: str
    agent_version: str
    billing_period_days: int
    price_incl_gst_paise: int
    base_price_paise: int
    gst_paise: int
    gst_rate_percent: int
    components: tuple[CatalogComponent, ...]


@dataclass(frozen=True)
class CatalogPage:
    items: tuple[CatalogPackage, ...]
    next_cursor: str | None


class PackageCatalog:
    def __init__(self, session: AsyncSession, *, repository: SqlPricingRepository | None = None, now=None) -> None:
        self._session = session
        self._repository = repository or SqlPricingRepository(session)
        self._now = now or (lambda: datetime.now(timezone.utc))

    async def list_for_sale(
        self, agent_type: str, agent_version: str, *, after: str | None = None, limit: int = MAX_PAGE
    ) -> CatalogPage:
        page_size = max(1, min(limit, MAX_PAGE))
        tier, version = _split_cursor(after)
        rows = (
            await self._session.execute(
                _FOR_SALE_SQL,
                {
                    "agent_type": agent_type,
                    "agent_version": agent_version,
                    "tier": tier,
                    "version": version,
                    "limit": page_size + 1,
                },
            )
        ).all()
        at = self._now()
        items: list[CatalogPackage] = []
        for row in rows[:page_size]:
            version = await self._repository.get(UUID(str(row[0])))
            if (
                version is None
                or version.kind is not PricingKind.PACKAGE
                or version.state is not VersionState.EFFECTIVE
                or version.effective_from is None
                or version.effective_from > at
            ):
                continue
            body = parse_package_body(version.body)
            base = base_price_paise(body.price_incl_gst_paise, body.gst_rate_percent)
            items.append(
                CatalogPackage(
                    package_id=version.version_id,
                    package_code=body.package_code,
                    display_name=body.display_name,
                    agent_type=body.agent_type,
                    agent_version=body.agent_version,
                    billing_period_days=body.billing_period_days,
                    price_incl_gst_paise=body.price_incl_gst_paise,
                    base_price_paise=base,
                    gst_paise=body.price_incl_gst_paise - base,
                    gst_rate_percent=body.gst_rate_percent,
                    components=tuple(
                        CatalogComponent(c.component_id, c.quantity, c.cadence, c.selectable_maximum)
                        for c in body.components
                    ),
                )
            )
        last = rows[page_size - 1] if len(rows) > page_size else None
        next_cursor = None if last is None else f"{last[1]}|{last[0]}"
        return CatalogPage(tuple(items), next_cursor)
