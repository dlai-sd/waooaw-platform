# Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C4-09
# Constitutional basis: C-059, C-088, C-089, C-063
"""Durable commercial projection and commercial command records of a relationship (WC-136 C4-09).

The projection is built from the relationship's own stored truth: its component units, its subscription
wallet and its period. It is written in business language only (units, cover and dates, never money or
cost). Zero is a value, not an absence: a spent allowance reads "0 units left", never "unavailable".
Everything here works in the caller's session and never commits.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Final
from uuid import UUID

from sqlalchemy import DateTime, bindparam, text
from sqlalchemy.ext.asyncio import AsyncSession

from meter.component_units import ComponentUnitService
from payment.lifecycle import PackageResolver, PackageSource, PeriodStore
from wallet.entity_models import as_utc
from wallet.ledger import WalletLedger

PROJECTION_VALIDITY_SECONDS: Final = 300
_TS = DateTime(timezone=True)
_PERCENT_BASE: Final = 100
_RESTRICTED: Final = {
    "SUSPENDED": "Work is stopped until the renewal is paid",
    "TERMINATED": "The relationship has ended; no further work is done",
    "LAPSED": "The period has ended; renew to continue",
}


def _stmt(sql: str, *datetime_params: str):
    statement = text(sql)
    if datetime_params:
        statement = statement.bindparams(*[bindparam(name, type_=_TS) for name in datetime_params])
    return statement


def _json_value(value: object) -> dict[str, Any]:
    loaded = json.loads(value) if isinstance(value, (str, bytes)) else value
    return dict(loaded)


@dataclass(frozen=True)
class StoredProjection:
    projection_version: str
    body: dict[str, Any]
    produced_at: datetime
    valid_until: datetime | None


@dataclass(frozen=True)
class StoredCommandRecord:
    command_id: UUID
    request_digest: str
    command_kind: str
    status: str
    receipt: dict[str, Any]
    outcome: dict[str, Any]


class CommercialRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def latest_projection(self, tenant_id: UUID, relationship_id: UUID) -> StoredProjection | None:
        row = (
            await self._session.execute(
                text(
                    """
                    SELECT projection_version, body, produced_at, valid_until
                    FROM business.commercial_projections
                    WHERE tenant_id = :tenant AND relationship_id = :relationship
                    ORDER BY produced_at DESC LIMIT 1
                    """
                ),
                {"tenant": str(tenant_id), "relationship": str(relationship_id)},
            )
        ).mappings().first()
        if row is None:
            return None
        return StoredProjection(
            row["projection_version"],
            _json_value(row["body"]),
            as_utc(row["produced_at"]),
            None if row["valid_until"] is None else as_utc(row["valid_until"]),
        )

    async def save_projection(
        self,
        tenant_id: UUID,
        relationship_id: UUID,
        version: str,
        body: dict[str, Any],
        produced_at: datetime,
        valid_until: datetime | None,
    ) -> None:
        """Insert the projection of this version; an identical state keeps its first record."""
        await self._session.execute(
            _stmt(
                """
                INSERT INTO business.commercial_projections
                (tenant_id, relationship_id, projection_version, body, produced_at, valid_until)
                VALUES (:tenant, :relationship, :version, :body, :produced, :valid)
                ON CONFLICT DO NOTHING
                """,
                "produced",
                "valid",
            ),
            {
                "tenant": str(tenant_id),
                "relationship": str(relationship_id),
                "version": version,
                "body": json.dumps(body, sort_keys=True),
                "produced": as_utc(produced_at),
                "valid": None if valid_until is None else as_utc(valid_until),
            },
        )

    async def find_command(
        self, tenant_id: UUID, relationship_id: UUID, idempotency_key: str
    ) -> StoredCommandRecord | None:
        return await self._command(
            "tenant_id = :tenant AND relationship_id = :relationship AND idempotency_key = :key",
            {"tenant": str(tenant_id), "relationship": str(relationship_id), "key": idempotency_key},
        )

    async def get_command(
        self, tenant_id: UUID, relationship_id: UUID, command_id: UUID
    ) -> StoredCommandRecord | None:
        return await self._command(
            "tenant_id = :tenant AND relationship_id = :relationship AND command_id = :command",
            {"tenant": str(tenant_id), "relationship": str(relationship_id), "command": str(command_id)},
        )

    async def _command(self, where: str, params: dict[str, str]) -> StoredCommandRecord | None:
        row = (
            await self._session.execute(
                text(
                    "SELECT command_id, request_digest, command_kind, status, receipt, outcome "
                    f"FROM business.commercial_commands WHERE {where}"
                ),
                params,
            )
        ).mappings().first()
        if row is None:
            return None
        return StoredCommandRecord(
            UUID(str(row["command_id"])),
            row["request_digest"],
            row["command_kind"],
            row["status"],
            _json_value(row["receipt"]),
            _json_value(row["outcome"]),
        )

    async def insert_command(
        self,
        command_id: UUID,
        tenant_id: UUID,
        relationship_id: UUID,
        idempotency_key: str,
        request_digest: str,
        command_kind: str,
        status: str,
        receipt: dict[str, Any],
        outcome: dict[str, Any],
        accepted_at: datetime,
        resolved_at: datetime | None,
    ) -> None:
        await self._session.execute(
            _stmt(
                """
                INSERT INTO business.commercial_commands
                (command_id, tenant_id, relationship_id, idempotency_key, request_digest, command_kind,
                 status, receipt, outcome, accepted_at, resolved_at)
                VALUES (:command, :tenant, :relationship, :key, :digest, :kind, :status, :receipt, :outcome,
                        :accepted, :resolved)
                """,
                "accepted",
                "resolved",
            ),
            {
                "command": str(command_id),
                "tenant": str(tenant_id),
                "relationship": str(relationship_id),
                "key": idempotency_key,
                "digest": request_digest,
                "kind": command_kind,
                "status": status,
                "receipt": json.dumps(receipt, sort_keys=True),
                "outcome": json.dumps(outcome, sort_keys=True),
                "accepted": as_utc(accepted_at),
                "resolved": None if resolved_at is None else as_utc(resolved_at),
            },
        )


def binding_key(actor_subject: str, tenant_id: str, relationship_id: str, key: str) -> str:
    """The stored idempotency key: the caller's key bound to its actor, tenant and relationship."""
    return hashlib.sha256("\x1f".join((actor_subject, tenant_id, relationship_id, key)).encode()).hexdigest()


def request_digest(body: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(body, separators=(",", ":"), sort_keys=True).encode()).hexdigest()


def _label(component_id: str) -> str:
    return component_id.replace("_", " ").capitalize()


class ProjectionBuilder:
    """Builds the camelCase projection body from the relationship's stored period, units and wallet."""

    def __init__(
        self,
        session: AsyncSession,
        *,
        now: Callable[[], datetime] | None = None,
        validity_seconds: int = PROJECTION_VALIDITY_SECONDS,
        packages: PackageSource | None = None,
    ) -> None:
        self._session = session
        self._now = now or (lambda: datetime.now(timezone.utc))
        self._validity = validity_seconds
        self._periods = PeriodStore(session)
        self._units = ComponentUnitService(session, now=self._now)
        self._ledger = WalletLedger(session, now=self._now)
        self._packages = packages or PackageResolver(session)

    async def build(self, tenant_id: UUID, relationship_id: UUID) -> dict[str, Any] | None:
        """The projection, or None when the relationship has no stored commercial period."""
        at = as_utc(self._now())
        period = await self._periods.current(tenant_id, relationship_id, at)
        if period is None:
            return None
        balances = await self._units.balances(tenant_id, relationship_id, at)
        counted = [item for item in balances if item.kind != "TIME_ACCESS"]
        total = sum(item.quantity for item in counted)
        used = sum(item.used for item in counted)
        released = sum(item.released for item in counted)
        remaining = max(0, total - used)

        cover_percent = 0
        account = await self._ledger.find_account(tenant_id, "SUBSCRIPTION", relationship_id=relationship_id)
        if account is not None:
            balance = await self._ledger.balance(account, at)
            if balance.credited_paise > 0:
                cover_percent = _PERCENT_BASE * max(0, balance.available_paise) // balance.credited_paise
        package = await self._packages.by_version(period.package_version_id)
        top_up = package is not None and any(item.topup_allowed for item in package.body.components)

        restriction = _RESTRICTED.get(period.status)
        if period.status == "PAUSED":
            restriction = "Paused; the unelapsed fee was returned"
        body: dict[str, Any] = {
            "schemaVersion": "1.0",
            "relationshipId": str(relationship_id),
            "currencyState": "BLOCKED" if period.status in _RESTRICTED else "CURRENT",
            "actuals": f"{used} of {total} units used",
            "allowance": f"{remaining} units left this period",
            "budget": f"{cover_percent}% of the period's cost cover remains",
            "forecast": f"{released} of {total} units are open so far",
            "thresholds": "Limit reached" if remaining == 0 or cover_percent == 0 else "No limit reached",
            "assumptions": f"Period ends {period.period_end.date().isoformat()}",
            "commercialConsequences": restriction or "No current restriction",
            "wallet": {
                "periodEnd": period.period_end.isoformat(),
                "components": [
                    {
                        "componentId": item.component_id,
                        "label": _label(item.component_id),
                        "remaining": item.remaining,
                        "quantity": item.quantity,
                    }
                    for item in balances
                ],
                "topUpAvailable": top_up,
            },
        }
        body["projectionVersion"] = hashlib.sha256(
            json.dumps(body, separators=(",", ":"), sort_keys=True).encode()
        ).hexdigest()[:32]
        body["producedAt"] = at.isoformat()
        body["validUntil"] = (at + timedelta(seconds=self._validity)).isoformat()
        return body
