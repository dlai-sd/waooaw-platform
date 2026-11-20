# Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C4-03
# Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C4-11
# Constitutional basis: C-059, C-088, C-089, C-063
"""Parity of the component allowance tables against the Wallet (WC-136 C4-03).

For every (relationship, component) the allowance reservations and the wallet reservations that
mirror them are compared in paise: what is still held (RESERVED, and UNKNOWN on the wallet side)
and what is settled. A nonzero difference is a dropped or divergent mirror write. Reading parity
never writes; ``report_parity`` additionally raises the metric and the log line. Only counts and
identifiers are logged.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from wallet import metrics, spend_events

logger = logging.getLogger(__name__)

DEFAULT_PARITY_LIMIT = 500

_ALLOWANCE_SQL = """
    SELECT r.relationship_id, r.component_id,
           COALESCE(SUM(CASE WHEN r.state = 'RESERVED'
                             THEN r.reserved_marked_up_paise ELSE 0 END), 0) AS open_paise,
           COALESCE(SUM(CASE WHEN r.state = 'SETTLED'
                             THEN r.actual_marked_up_paise ELSE 0 END), 0) AS settled_paise
    FROM business.offering_component_reservations r
    WHERE r.tenant_id = :tenant{relationship_filter}
    GROUP BY r.relationship_id, r.component_id
"""
_WALLET_SQL = """
    SELECT a.relationship_id, w.component_id,
           COALESCE(SUM(CASE WHEN w.state IN ('RESERVED', 'UNKNOWN')
                             THEN w.reserved_paise ELSE 0 END), 0) AS open_paise,
           COALESCE(SUM(CASE WHEN w.state = 'SETTLED'
                             THEN w.actual_paise ELSE 0 END), 0) AS settled_paise
    FROM business.wallet_reservations w
    JOIN business.wallet_accounts a
      ON a.tenant_id = w.tenant_id AND a.account_id = w.account_id
    WHERE w.tenant_id = :tenant
      AND a.account_class IN ('SUBSCRIPTION', 'TRIAL'){relationship_filter}
      AND w.reservation_id IN (
          SELECT o.reservation_id FROM business.offering_component_reservations o
          WHERE o.tenant_id = :tenant)
    GROUP BY a.relationship_id, w.component_id
"""
_ALLOWANCE_FILTER = " AND r.relationship_id = :relationship"
_WALLET_FILTER = " AND a.relationship_id = :relationship"


@dataclass(frozen=True)
class ParityRow:
    relationship_id: UUID
    component_id: str
    allowance_open_paise: int
    allowance_settled_paise: int
    wallet_open_paise: int
    wallet_settled_paise: int

    @property
    def open_difference_paise(self) -> int:
        return self.allowance_open_paise - self.wallet_open_paise

    @property
    def settled_difference_paise(self) -> int:
        return self.allowance_settled_paise - self.wallet_settled_paise

    @property
    def matches(self) -> bool:
        return self.open_difference_paise == 0 and self.settled_difference_paise == 0


@dataclass(frozen=True)
class ParityReport:
    tenant_id: UUID
    checked_at: datetime
    rows: tuple[ParityRow, ...]
    compared: int
    truncated: bool = False

    @property
    def differences(self) -> tuple[ParityRow, ...]:
        return tuple(row for row in self.rows if not row.matches)

    @property
    def clean(self) -> bool:
        return not self.differences


async def compute_parity(
    session: AsyncSession,
    tenant_id: UUID,
    relationship_id: UUID | None = None,
    *,
    limit: int = DEFAULT_PARITY_LIMIT,
    now: datetime | None = None,
) -> ParityReport:
    """Compare allowance and wallet paise per relationship and component; differing rows come first."""
    params: dict[str, str] = {"tenant": str(tenant_id)}
    allowance_filter = wallet_filter = ""
    if relationship_id is not None:
        params["relationship"] = str(relationship_id)
        allowance_filter, wallet_filter = _ALLOWANCE_FILTER, _WALLET_FILTER
    allowance = (
        await session.execute(text(_ALLOWANCE_SQL.format(relationship_filter=allowance_filter)), params)
    ).mappings().all()
    wallet = (
        await session.execute(text(_WALLET_SQL.format(relationship_filter=wallet_filter)), params)
    ).mappings().all()

    keyed: dict[tuple[str, str], list[int]] = {}
    for row in allowance:
        key = (str(row["relationship_id"]), row["component_id"])
        keyed[key] = [int(row["open_paise"]), int(row["settled_paise"]), 0, 0]
    for row in wallet:
        key = (str(row["relationship_id"]), row["component_id"])
        values = keyed.setdefault(key, [0, 0, 0, 0])
        values[2], values[3] = int(row["open_paise"]), int(row["settled_paise"])

    rows = [ParityRow(UUID(rel), component, *values) for (rel, component), values in keyed.items()]
    rows.sort(key=lambda r: (r.matches, str(r.relationship_id), r.component_id))
    bounded = max(1, limit)
    return ParityReport(
        tenant_id=tenant_id,
        checked_at=now or datetime.now(timezone.utc),
        rows=tuple(rows[:bounded]),
        compared=len(rows),
        truncated=len(rows) > bounded,
    )


async def report_parity(
    session: AsyncSession,
    tenant_id: UUID,
    relationship_id: UUID | None = None,
    *,
    limit: int = DEFAULT_PARITY_LIMIT,
) -> ParityReport:
    """Compute parity and, when it differs, raise the metric and the log line; never raises on a difference."""
    report = await compute_parity(session, tenant_id, relationship_id, limit=limit)
    differing = len(report.differences)
    if differing:
        metrics.count("wbe.wallet.parity_difference", differing)
        spend_events.record_parity_difference(differing)
        logger.warning(
            "wallet parity differs tenant=%s differing=%d compared=%d",
            tenant_id,
            differing,
            report.compared,
        )
    return report
