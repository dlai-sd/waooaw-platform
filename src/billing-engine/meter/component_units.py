# Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C4-08
# Constitutional basis: C-059, C-088, C-089, C-063
"""Component units of a relationship: the four kinds, pacing and the cost tolerance (WC-136 C4-08).

Components are the customer-facing limit; the wallet is the cost guard. Counting a unit and settling
its wallet cost are separate operations: this service only counts units and never touches the wallet.
It works in a caller-owned session and never commits. Every write is idempotent on
(tenant_id, relationship_id, idempotency_key); a COUNTED unit is also unique per completion evidence id,
so a confirmed outcome counts once however often it is delivered.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from fractions import Fraction
from typing import Final
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from sqlalchemy import DateTime, bindparam, text
from sqlalchemy.ext.asyncio import AsyncSession

from markup.package_models import PackageBody, PackageComponent
from wallet.entity_models import as_utc

DAYS_PER_WEEK: Final = 7
_TS = DateTime(timezone=True)

COMPONENT_NOT_YET_RELEASED: Final = "COMPONENT_NOT_YET_RELEASED"
COMPONENT_EXHAUSTED: Final = "COMPONENT_EXHAUSTED"
COMPONENT_UNKNOWN: Final = "COMPONENT_UNKNOWN"
COMPONENT_KIND_MISMATCH: Final = "COMPONENT_KIND_MISMATCH"
COMPONENT_OUTCOME_NOT_COMPLETED: Final = "COMPONENT_OUTCOME_NOT_COMPLETED"
COMPONENT_CONNECTION_REQUIRED: Final = "COMPONENT_CONNECTION_REQUIRED"
COMPONENT_SLOTS_FULL: Final = "COMPONENT_SLOTS_FULL"
COMPONENT_SWAP_LIMIT: Final = "COMPONENT_SWAP_LIMIT"
COMPONENT_ITEM_UNKNOWN: Final = "COMPONENT_ITEM_UNKNOWN"
COMPONENT_IDEMPOTENCY_CONFLICT: Final = "COMPONENT_IDEMPOTENCY_CONFLICT"


class ComponentUnitError(ValueError):
    """A typed refusal; ``str(error)`` is the stable code the caller renders or defers on."""

    def __init__(self, code: str, detail: str | None = None) -> None:
        super().__init__(code)
        self.code = code
        self.detail = detail


@dataclass(frozen=True)
class ComponentPeriod:
    tenant_id: UUID
    relationship_id: UUID
    agent_instance_id: UUID
    package_version_id: UUID
    component_id: str
    kind: str
    period_start: datetime
    period_end: datetime
    quantity: int
    released_cadence: str | None


@dataclass(frozen=True)
class ComponentBalance:
    component_id: str
    kind: str
    quantity: int
    used: int
    remaining: int
    released: int
    period_start: datetime
    period_end: datetime


@dataclass(frozen=True)
class ComponentUnitReceipt:
    component_id: str
    kind: str
    entry_id: UUID
    quantity: int
    used: int
    remaining: int
    released: int
    replayed: bool


def released_units(
    quantity: int, cadence: str | None, period_start: datetime, period_end: datetime, at: datetime
) -> int:
    """Units released at ``at`` on the declared cadence.

    Pacing is floor(quantity * elapsed / period) on whole elapsed days, so a unit opens at the first day
    boundary at or after its exact fractional time; WEEKLY steps on whole elapsed weeks; UPFRONT releases all.
    """
    start, end, now = as_utc(period_start), as_utc(period_end), as_utc(at)
    if now < start:
        return 0
    if now >= end or cadence == "UPFRONT":
        return quantity
    period_days = max(1, (end - start).days + (1 if (end - start).seconds else 0))
    elapsed_days = (now - start).days
    if cadence == "WEEKLY":
        elapsed_days = elapsed_days - elapsed_days % DAYS_PER_WEEK
    return min(quantity, quantity * elapsed_days // period_days)


def cost_tolerance_verdict(
    actual_paise: int, recipe_paise: int, tolerance_fraction: float | str, alert_fraction: float | str
) -> str:
    """WITHIN, ALERT (above the alert fraction) or OVER_TOLERANCE (the cheaper path applies).

    The fractions come from the effective POLICY version (costToleranceFraction, costAlertFraction).
    """
    if actual_paise < 0 or recipe_paise < 0:
        raise ComponentUnitError("COMPONENT_COST_INVALID")
    tolerance = Fraction(str(tolerance_fraction))
    alert = Fraction(str(alert_fraction))
    if actual_paise > recipe_paise * (1 + tolerance):
        return "OVER_TOLERANCE"
    if actual_paise > recipe_paise * (1 + alert):
        return "ALERT"
    return "WITHIN"


def initial_quantity(component: PackageComponent) -> int:
    """The unit capacity of a component: a SELECTED component is capped by its selectable maximum."""
    if component.kind == "SELECTED" and component.selectable_maximum is not None:
        return min(component.quantity, component.selectable_maximum)
    return component.quantity


def _stmt(sql: str, *datetime_params: str):
    statement = text(sql)
    if datetime_params:
        statement = statement.bindparams(*[bindparam(name, type_=_TS) for name in datetime_params])
    return statement


class ComponentUnitService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        swaps_per_period: int = 0,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        if swaps_per_period < 0:
            raise ComponentUnitError("COMPONENT_SWAP_LIMIT", "swaps_per_period")
        self._session = session
        self._swaps = swaps_per_period
        self._now = now or (lambda: datetime.now(timezone.utc))

    async def open_period(
        self,
        tenant_id: UUID,
        relationship_id: UUID,
        agent_instance_id: UUID,
        package_version_id: UUID,
        package: PackageBody,
        period_start: datetime,
        period_end: datetime,
    ) -> list[ComponentPeriod]:
        """Open one row per package component for the period; replaying the same period writes nothing."""
        for component in package.components:
            await self._session.execute(
                _stmt(
                    """
                    INSERT INTO business.component_units
                    (tenant_id, relationship_id, agent_instance_id, package_version_id, component_id,
                     kind, period_start, period_end, quantity, released_cadence)
                    VALUES (:tenant, :relationship, :instance, :package, :component, :kind,
                            :start, :end, :quantity, :cadence)
                    ON CONFLICT DO NOTHING
                    """,
                    "start",
                    "end",
                ),
                {
                    "tenant": str(tenant_id),
                    "relationship": str(relationship_id),
                    "instance": str(agent_instance_id),
                    "package": str(package_version_id),
                    "component": component.component_id,
                    "kind": component.kind,
                    "start": as_utc(period_start),
                    "end": as_utc(period_end),
                    "quantity": initial_quantity(component),
                    "cadence": component.cadence,
                },
            )
        rows = await self._periods(tenant_id, relationship_id, as_utc(period_start))
        return [row for row in rows if row.period_start == as_utc(period_start)]

    async def consume(
        self,
        tenant_id: UUID,
        relationship_id: UUID,
        component_id: str,
        completion_evidence_id: UUID,
        idempotency_key: UUID,
        *,
        outcome: str = "COMPLETED",
        paced: bool = True,
    ) -> ComponentUnitReceipt:
        """Count one unit of a COUNTED component for an owner-confirmed COMPLETED outcome.

        ``paced=False`` counts against the whole period quantity instead of the released amount; it is
        for allowances that are not spread over the period, such as the included proactive messages.
        """
        period = await self._current(tenant_id, relationship_id, component_id, "COUNTED")
        if outcome != "COMPLETED":
            raise ComponentUnitError(COMPONENT_OUTCOME_NOT_COMPLETED)
        await self._lock(tenant_id, relationship_id, component_id)
        replay = await self._replay(
            tenant_id, relationship_id, component_id, idempotency_key, "CONSUME", completion_evidence_id
        )
        if replay is not None:
            return await self._receipt(period, replay, replayed=True)
        used = await self._used(period)
        now = self._now()
        released = released_units(period.quantity, period.released_cadence, period.period_start, period.period_end, now)
        if used >= period.quantity:
            raise ComponentUnitError(COMPONENT_EXHAUSTED)
        if paced and used >= released:
            raise ComponentUnitError(COMPONENT_NOT_YET_RELEASED)
        entry_id = await self._insert(
            period, "CONSUME", idempotency_key, now, units=1, completion_evidence_id=completion_evidence_id
        )
        return await self._receipt(period, entry_id, replayed=False)

    async def select(
        self,
        tenant_id: UUID,
        relationship_id: UUID,
        component_id: str,
        item_ref: str,
        connection_proof: UUID | None,
        idempotency_key: UUID,
    ) -> ComponentUnitReceipt:
        """Occupy a slot with a connected item; a failed or missing connection occupies nothing."""
        period = await self._current(tenant_id, relationship_id, component_id, "SELECTED")
        if connection_proof is None:
            raise ComponentUnitError(COMPONENT_CONNECTION_REQUIRED)
        await self._lock(tenant_id, relationship_id, component_id)
        replay = await self._replay(
            tenant_id, relationship_id, component_id, idempotency_key, "SELECT", connection_proof, item_ref
        )
        if replay is not None:
            return await self._receipt(period, replay, replayed=True)
        active, _ = await self._selection(period)
        if item_ref in active:
            raise ComponentUnitError(COMPONENT_IDEMPOTENCY_CONFLICT, "item already selected")
        if len(active) >= period.quantity:
            raise ComponentUnitError(COMPONENT_SLOTS_FULL)
        entry_id = await self._insert(
            period, "SELECT", idempotency_key, self._now(), units=1, item_ref=item_ref,
            completion_evidence_id=connection_proof,
        )
        return await self._receipt(period, entry_id, replayed=False)

    async def swap(
        self,
        tenant_id: UUID,
        relationship_id: UUID,
        component_id: str,
        old_item_ref: str,
        new_item_ref: str,
        connection_proof: UUID | None,
        idempotency_key: UUID,
    ) -> ComponentUnitReceipt:
        """Replace a selected item with a newly connected one, within the swaps allowed per period."""
        period = await self._current(tenant_id, relationship_id, component_id, "SELECTED")
        if connection_proof is None:
            raise ComponentUnitError(COMPONENT_CONNECTION_REQUIRED)
        await self._lock(tenant_id, relationship_id, component_id)
        replay = await self._replay(
            tenant_id, relationship_id, component_id, idempotency_key, "SWAP", connection_proof, new_item_ref
        )
        if replay is not None:
            return await self._receipt(period, replay, replayed=True)
        active, swaps = await self._selection(period)
        if old_item_ref not in active:
            raise ComponentUnitError(COMPONENT_ITEM_UNKNOWN)
        if new_item_ref in active:
            raise ComponentUnitError(COMPONENT_IDEMPOTENCY_CONFLICT, "item already selected")
        if swaps >= self._swaps:
            raise ComponentUnitError(COMPONENT_SWAP_LIMIT)
        now = self._now()
        await self._insert(
            period, "DESELECT", uuid5(NAMESPACE_URL, f"deselect:{idempotency_key}"), now, units=-1,
            item_ref=old_item_ref,
        )
        entry_id = await self._insert(
            period, "SWAP", idempotency_key, now, units=1, item_ref=new_item_ref,
            completion_evidence_id=connection_proof,
        )
        return await self._receipt(period, entry_id, replayed=False)

    async def deselect(
        self, tenant_id: UUID, relationship_id: UUID, component_id: str, item_ref: str, idempotency_key: UUID
    ) -> ComponentUnitReceipt:
        period = await self._current(tenant_id, relationship_id, component_id, "SELECTED")
        await self._lock(tenant_id, relationship_id, component_id)
        replay = await self._replay(
            tenant_id, relationship_id, component_id, idempotency_key, "DESELECT", None, item_ref
        )
        if replay is not None:
            return await self._receipt(period, replay, replayed=True)
        active, _ = await self._selection(period)
        if item_ref not in active:
            raise ComponentUnitError(COMPONENT_ITEM_UNKNOWN)
        entry_id = await self._insert(
            period, "DESELECT", idempotency_key, self._now(), units=-1, item_ref=item_ref
        )
        return await self._receipt(period, entry_id, replayed=False)

    async def record_access(
        self, tenant_id: UUID, relationship_id: UUID, component_id: str, idempotency_key: UUID
    ) -> ComponentUnitReceipt:
        """TIME_ACCESS consumes nothing per use; the use is recorded for the period."""
        period = await self._current(tenant_id, relationship_id, component_id, "TIME_ACCESS")
        await self._lock(tenant_id, relationship_id, component_id)
        replay = await self._replay(tenant_id, relationship_id, component_id, idempotency_key, "CONSUME", None)
        if replay is not None:
            return await self._receipt(period, replay, replayed=True)
        entry_id = await self._insert(period, "CONSUME", idempotency_key, self._now(), units=0)
        return await self._receipt(period, entry_id, replayed=False)

    async def close(
        self,
        tenant_id: UUID,
        relationship_id: UUID,
        component_id: str,
        session_ref: str,
        idempotency_key: UUID,
    ) -> ComponentUnitReceipt:
        """CAPACITY counts one unit when its session closes; a session counts once."""
        period = await self._current(tenant_id, relationship_id, component_id, "CAPACITY")
        await self._lock(tenant_id, relationship_id, component_id)
        replay = await self._replay(
            tenant_id, relationship_id, component_id, idempotency_key, "CLOSE", None, session_ref
        )
        if replay is not None:
            return await self._receipt(period, replay, replayed=True)
        if await self._used(period) >= period.quantity:
            raise ComponentUnitError(COMPONENT_EXHAUSTED)
        entry_id = await self._insert(
            period, "CLOSE", idempotency_key, self._now(), units=1, item_ref=session_ref
        )
        return await self._receipt(period, entry_id, replayed=False)

    async def available_units(
        self, tenant_id: UUID, relationship_id: UUID, component_id: str, at: datetime | None = None
    ) -> int:
        """Units still open to consume now: released by pacing minus already counted."""
        moment = at or self._now()
        period = await self._current(tenant_id, relationship_id, component_id, None, at=moment)
        released = released_units(period.quantity, period.released_cadence, period.period_start, period.period_end, moment)
        if period.kind != "COUNTED":
            released = period.quantity
        return max(0, released - await self._used(period))

    async def balances(
        self, tenant_id: UUID, relationship_id: UUID, at: datetime | None = None
    ) -> list[ComponentBalance]:
        """Every component of the period in force at ``at``, in business terms (never cost)."""
        moment = at or self._now()
        result: list[ComponentBalance] = []
        for period in await self._periods(tenant_id, relationship_id, None, at=moment):
            used = await self._used(period)
            released = (
                released_units(period.quantity, period.released_cadence, period.period_start, period.period_end, moment)
                if period.kind == "COUNTED"
                else period.quantity
            )
            result.append(
                ComponentBalance(
                    component_id=period.component_id,
                    kind=period.kind,
                    quantity=period.quantity,
                    used=used,
                    remaining=max(0, period.quantity - used) if period.kind != "TIME_ACCESS" else period.quantity,
                    released=released,
                    period_start=period.period_start,
                    period_end=period.period_end,
                )
            )
        return sorted(result, key=lambda item: item.component_id)

    # ------------------------------------------------------------------ internals

    async def _lock(self, tenant_id: UUID, relationship_id: UUID, component_id: str) -> None:
        bind = self._session.bind
        if bind is not None and bind.dialect.name == "postgresql":
            await self._session.execute(
                text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
                {"key": f"component-units:{tenant_id}:{relationship_id}:{component_id}"},
            )

    async def _periods(
        self,
        tenant_id: UUID,
        relationship_id: UUID,
        period_start: datetime | None,
        *,
        at: datetime | None = None,
        component_id: str | None = None,
    ) -> list[ComponentPeriod]:
        clauses = ["tenant_id = :tenant", "relationship_id = :relationship"]
        params: dict[str, object] = {"tenant": str(tenant_id), "relationship": str(relationship_id)}
        datetime_params: list[str] = []
        if period_start is not None:
            clauses.append("period_start = :start")
            params["start"] = period_start
            datetime_params.append("start")
        if at is not None:
            clauses.append("period_start <= :at AND period_end > :at")
            params["at"] = as_utc(at)
            datetime_params.append("at")
        if component_id is not None:
            clauses.append("component_id = :component")
            params["component"] = component_id
        rows = (
            await self._session.execute(
                _stmt(
                    "SELECT * FROM business.component_units WHERE " + " AND ".join(clauses)
                    + " ORDER BY period_start DESC, component_id",
                    *datetime_params,
                ),
                params,
            )
        ).mappings().all()
        return [
            ComponentPeriod(
                tenant_id=UUID(str(row["tenant_id"])),
                relationship_id=UUID(str(row["relationship_id"])),
                agent_instance_id=UUID(str(row["agent_instance_id"])),
                package_version_id=UUID(str(row["package_version_id"])),
                component_id=row["component_id"],
                kind=row["kind"],
                period_start=as_utc(row["period_start"]),
                period_end=as_utc(row["period_end"]),
                quantity=int(row["quantity"]),
                released_cadence=row["released_cadence"],
            )
            for row in rows
        ]

    async def _current(
        self,
        tenant_id: UUID,
        relationship_id: UUID,
        component_id: str,
        expected_kind: str | None,
        *,
        at: datetime | None = None,
    ) -> ComponentPeriod:
        found = await self._periods(
            tenant_id, relationship_id, None, at=at or self._now(), component_id=component_id
        )
        if not found:
            raise ComponentUnitError(COMPONENT_UNKNOWN)
        period = found[0]
        if expected_kind is not None and period.kind != expected_kind:
            raise ComponentUnitError(COMPONENT_KIND_MISMATCH, period.kind)
        return period

    async def _used(self, period: ComponentPeriod) -> int:
        value = (
            await self._session.execute(
                _stmt(
                    """
                    SELECT COALESCE(SUM(units), 0) FROM business.component_unit_entries
                    WHERE tenant_id = :tenant AND relationship_id = :relationship
                      AND component_id = :component AND period_start = :start
                    """,
                    "start",
                ),
                {
                    "tenant": str(period.tenant_id),
                    "relationship": str(period.relationship_id),
                    "component": period.component_id,
                    "start": period.period_start,
                },
            )
        ).scalar_one()
        return int(value)

    async def _selection(self, period: ComponentPeriod) -> tuple[set[str], int]:
        rows = (
            await self._session.execute(
                _stmt(
                    """
                    SELECT entry_kind, item_ref FROM business.component_unit_entries
                    WHERE tenant_id = :tenant AND relationship_id = :relationship
                      AND component_id = :component AND period_start = :start
                    AND entry_kind IN ('SELECT', 'SWAP', 'DESELECT')
                    """,
                    "start",
                ),
                {
                    "tenant": str(period.tenant_id),
                    "relationship": str(period.relationship_id),
                    "component": period.component_id,
                    "start": period.period_start,
                },
            )
        ).all()
        net: dict[str, int] = {}
        swaps = 0
        for kind, item in rows:
            net[item] = net.get(item, 0) + (-1 if kind == "DESELECT" else 1)
            swaps += 1 if kind == "SWAP" else 0
        return {item for item, count in net.items() if count > 0}, swaps

    async def _replay(
        self,
        tenant_id: UUID,
        relationship_id: UUID,
        component_id: str,
        idempotency_key: UUID,
        entry_kind: str,
        evidence_id: UUID | None,
        item_ref: str | None = None,
    ) -> UUID | None:
        """The earlier entry of this request, found by key or by evidence; a changed request conflicts."""
        evidence_clause = (
            " OR (component_id = :component AND completion_evidence_id = :evidence)"
            if evidence_id is not None
            else ""
        )
        params: dict[str, object] = {
            "tenant": str(tenant_id),
            "relationship": str(relationship_id),
            "key": str(idempotency_key),
        }
        if evidence_id is not None:
            params["component"] = component_id
            params["evidence"] = str(evidence_id)
        row = (
            await self._session.execute(
                text(
                    f"""
                    SELECT entry_id, component_id, entry_kind, completion_evidence_id, item_ref
                    FROM business.component_unit_entries
                    WHERE tenant_id = :tenant AND relationship_id = :relationship
                      AND (idempotency_key = :key{evidence_clause})
                    ORDER BY CASE WHEN idempotency_key = :key THEN 0 ELSE 1 END
                    LIMIT 1
                    """
                ),
                params,
            )
        ).mappings().one_or_none()
        if row is None:
            return None
        same = (
            row["component_id"] == component_id
            and row["entry_kind"] == entry_kind
            and (evidence_id is None or str(row["completion_evidence_id"]) == str(evidence_id))
            and (item_ref is None or row["item_ref"] == item_ref)
        )
        if not same:
            raise ComponentUnitError(COMPONENT_IDEMPOTENCY_CONFLICT)
        return UUID(str(row["entry_id"]))

    async def _insert(
        self,
        period: ComponentPeriod,
        entry_kind: str,
        idempotency_key: UUID,
        at: datetime,
        *,
        units: int,
        item_ref: str | None = None,
        completion_evidence_id: UUID | None = None,
    ) -> UUID:
        entry_id = uuid4()
        await self._session.execute(
            _stmt(
                """
                INSERT INTO business.component_unit_entries
                (entry_id, tenant_id, relationship_id, component_id, period_start, entry_kind, units,
                 item_ref, completion_evidence_id, idempotency_key, occurred_at)
                VALUES (:entry, :tenant, :relationship, :component, :start, :kind, :units, :item,
                        :evidence, :key, :at)
                """,
                "start",
                "at",
            ),
            {
                "entry": str(entry_id),
                "tenant": str(period.tenant_id),
                "relationship": str(period.relationship_id),
                "component": period.component_id,
                "start": period.period_start,
                "kind": entry_kind,
                "units": units,
                "item": item_ref,
                "evidence": str(completion_evidence_id) if completion_evidence_id is not None else None,
                "key": str(idempotency_key),
                "at": as_utc(at),
            },
        )
        return entry_id

    async def _receipt(self, period: ComponentPeriod, entry_id: UUID, *, replayed: bool) -> ComponentUnitReceipt:
        used = await self._used(period)
        released = (
            released_units(period.quantity, period.released_cadence, period.period_start, period.period_end, self._now())
            if period.kind == "COUNTED"
            else period.quantity
        )
        return ComponentUnitReceipt(
            component_id=period.component_id,
            kind=period.kind,
            entry_id=entry_id,
            quantity=period.quantity,
            used=used,
            remaining=max(0, period.quantity - used) if period.kind != "TIME_ACCESS" else period.quantity,
            released=released,
            replayed=replayed,
        )
