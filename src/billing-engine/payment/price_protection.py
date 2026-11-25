# Implements: work-contracts/WC-172-safe-to-charge-real-customers.md WC172-R005
# Implements: adr/ADR-022-payment-processing-razorpay-india.md Amendment 1.4 (C-090)
# Constitutional basis: C-059, C-088, C-090
"""Price protection: a hire renews at its locked price; a catalogue price change reaches it only after 30 days'
notice and the customer's acknowledgement (D3).

A hire is pinned to the package version it was accepted on, so a new catalogue price is a new package version the
hire does not move to by itself. The billing engine records the notice (with its evidence), the customer's
acknowledgement, and only then lets a renewal use the new version. Without both, the old price continues. Services
work in the caller's session and never commit.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from typing import Final
from uuid import NAMESPACE_URL, UUID, uuid5

from sqlalchemy import DateTime, bindparam, text
from sqlalchemy.ext.asyncio import AsyncSession

from payment.lifecycle_policy import price_change_effective_from
from wallet.entity_models import as_utc

_TS = DateTime(timezone=True)

NOTICE_NOT_FOUND: Final = "PRICE_CHANGE_NOTICE_NOT_FOUND"
NOTICE_PENDING: Final = "PRICE_CHANGE_NOTICE_PENDING"
NOT_ACKNOWLEDGED: Final = "PRICE_CHANGE_NOT_ACKNOWLEDGED"
NOT_A_CHANGE: Final = "PRICE_CHANGE_UNCHANGED"
EVIDENCE_REQUIRED: Final = "PRICE_CHANGE_EVIDENCE_REQUIRED"


class PriceProtectionError(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _stmt(sql: str, *datetime_params: str):
    statement = text(sql)
    if datetime_params:
        statement = statement.bindparams(*[bindparam(name, type_=_TS) for name in datetime_params])
    return statement


class PriceProtection:
    def __init__(self, session: AsyncSession, *, now: Callable[[], datetime] | None = None) -> None:
        self._session = session
        self._now = now or (lambda: datetime.now(timezone.utc))

    async def notify(
        self,
        tenant_id: UUID,
        relationship_id: UUID,
        from_package_version_id: UUID,
        to_package_version_id: UUID,
        current_price_paise: int,
        new_price_paise: int,
        notice_evidence_id: UUID,
    ) -> UUID:
        """Record the notice that starts the 30 days; a repeat for the same target returns the same notice."""
        if notice_evidence_id == UUID(int=0):
            raise PriceProtectionError(EVIDENCE_REQUIRED)
        if from_package_version_id == to_package_version_id or current_price_paise == new_price_paise:
            raise PriceProtectionError(NOT_A_CHANGE)
        notice_id = uuid5(NAMESPACE_URL, f"price-change:{tenant_id}:{relationship_id}:{to_package_version_id}")
        now = self._now()
        await self._session.execute(
            _stmt(
                """
                INSERT INTO business.relationship_price_notices
                (notice_id, tenant_id, relationship_id, from_package_version_id, to_package_version_id,
                 current_price_paise, new_price_paise, notified_at, effective_from, status, notice_evidence_id)
                VALUES (:id, :tenant, :relationship, :from_version, :to_version, :current, :new, :now, :effective,
                        'NOTIFIED', :evidence)
                ON CONFLICT DO NOTHING
                """,
                "now",
                "effective",
            ),
            {
                "id": str(notice_id),
                "tenant": str(tenant_id),
                "relationship": str(relationship_id),
                "from_version": str(from_package_version_id),
                "to_version": str(to_package_version_id),
                "current": current_price_paise,
                "new": new_price_paise,
                "now": as_utc(now),
                "effective": price_change_effective_from(now),
                "evidence": str(notice_evidence_id),
            },
        )
        return notice_id

    async def acknowledge(self, tenant_id: UUID, relationship_id: UUID, notice_id: UUID, actor: str) -> None:
        row = (
            await self._session.execute(
                text(
                    "SELECT status FROM business.relationship_price_notices "
                    "WHERE notice_id = :id AND tenant_id = :tenant AND relationship_id = :relationship"
                ),
                {"id": str(notice_id), "tenant": str(tenant_id), "relationship": str(relationship_id)},
            )
        ).first()
        if row is None or row[0] == "WITHDRAWN":
            raise PriceProtectionError(NOTICE_NOT_FOUND)
        if row[0] == "ACKNOWLEDGED":
            return
        await self._session.execute(
            _stmt(
                """
                UPDATE business.relationship_price_notices
                SET status = 'ACKNOWLEDGED', acknowledged_at = :now, acknowledged_by = :actor
                WHERE notice_id = :id
                """,
                "now",
            ),
            {"now": as_utc(self._now()), "actor": actor, "id": str(notice_id)},
        )

    async def applicable_version(
        self, tenant_id: UUID, relationship_id: UUID, current_version_id: UUID, renewal_starts_at: datetime
    ) -> UUID | None:
        """The package version a renewal starting at ``renewal_starts_at`` may use instead of the locked one:
        only a notified change that the customer acknowledged and whose 30 days have run."""
        row = (
            await self._session.execute(
                _stmt(
                    """
                    SELECT to_package_version_id FROM business.relationship_price_notices
                    WHERE tenant_id = :tenant AND relationship_id = :relationship
                      AND from_package_version_id = :current AND status = 'ACKNOWLEDGED'
                      AND effective_from <= :starts
                    ORDER BY effective_from DESC LIMIT 1
                    """,
                    "starts",
                ),
                {
                    "tenant": str(tenant_id),
                    "relationship": str(relationship_id),
                    "current": str(current_version_id),
                    "starts": as_utc(renewal_starts_at),
                },
            )
        ).first()
        return None if row is None else UUID(str(row[0]))

    async def require_change_allowed(self, tenant_id: UUID, relationship_id: UUID, notice_id: UUID) -> None:
        """The plan update of a locked hire is refused until the notice has run its 30 days and been acknowledged."""
        row = (
            await self._session.execute(
                text(
                    "SELECT status, effective_from FROM business.relationship_price_notices "
                    "WHERE notice_id = :id AND tenant_id = :tenant AND relationship_id = :relationship"
                ),
                {"id": str(notice_id), "tenant": str(tenant_id), "relationship": str(relationship_id)},
            )
        ).first()
        if row is None or row[0] == "WITHDRAWN":
            raise PriceProtectionError(NOTICE_NOT_FOUND)
        if row[0] != "ACKNOWLEDGED":
            raise PriceProtectionError(NOT_ACKNOWLEDGED)
        if as_utc(row[1]) > as_utc(self._now()):
            raise PriceProtectionError(NOTICE_PENDING)
