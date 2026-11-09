"""WBE-owned component allowance reservation and immutable settlement."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal
from uuid import UUID, uuid4

from sqlalchemy import DateTime, String, Uuid, bindparam, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from skeleton.wbe_interfaces import IOfferingAllowanceService

_UUID = String(36).with_variant(Uuid(as_uuid=False), "postgresql")


def canonical_digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()


@dataclass(frozen=True)
class AllowanceIdentity:
    tenant_id: UUID
    relationship_id: UUID
    agent_instance_id: UUID
    professional_type: str
    professional_version: str
    skill_id: str
    skill_version: str
    work_item_id: UUID
    invocation_id: UUID
    component_id: str
    idempotency_key: UUID
    request_digest: str
    owner_evidence_id: UUID


@dataclass(frozen=True)
class AllowanceReceipt:
    reservation_id: UUID
    state: Literal["RESERVED", "SETTLED", "RELEASED"]
    maximum_units: int
    reserved_raw_paise: int
    reserved_marked_up_paise: int
    catalogue_thread_id: str
    provider_account_id: UUID
    rate_version: str
    replayed: bool = False


class AllowanceConflict(ValueError):
    pass


class AllowanceDenied(ValueError):
    pass


class OfferingAllowanceService(IOfferingAllowanceService):
    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    @staticmethod
    def _same(row: object, identity: AllowanceIdentity) -> bool:
        return all(
            str(getattr(row, name)) == str(value)
            for name, value in (
                ("tenant_id", identity.tenant_id),
                ("relationship_id", identity.relationship_id),
                ("agent_instance_id", identity.agent_instance_id),
                ("professional_type", identity.professional_type),
                ("professional_version", identity.professional_version),
                ("skill_id", identity.skill_id),
                ("skill_version", identity.skill_version),
                ("work_item_id", identity.work_item_id),
                ("invocation_id", identity.invocation_id),
                ("component_id", identity.component_id),
                ("request_digest", identity.request_digest),
                ("owner_evidence_id", identity.owner_evidence_id),
            )
        )

    @staticmethod
    def _receipt(row: object, replayed: bool = False) -> AllowanceReceipt:
        return AllowanceReceipt(
            reservation_id=UUID(str(row.reservation_id)),
            state=row.state,
            maximum_units=row.maximum_units,
            reserved_raw_paise=row.reserved_raw_paise,
            reserved_marked_up_paise=row.reserved_marked_up_paise,
            catalogue_thread_id=row.catalogue_thread_id,
            provider_account_id=UUID(str(row.provider_account_id)),
            rate_version=row.rate_version,
            replayed=replayed,
        )

    async def reserve(self, identity: AllowanceIdentity, maximum_units: int) -> AllowanceReceipt:
        if maximum_units <= 0 or len(identity.request_digest) != 64:
            raise AllowanceDenied("ALLOWANCE_REQUEST_INVALID")
        async with self._sessions() as session, session.begin():
            existing = (
                await session.execute(
                    text(
                        """SELECT * FROM business.offering_component_reservations
                           WHERE tenant_id=:tenant AND relationship_id=:relationship
                             AND idempotency_key=:idempotency FOR UPDATE"""
                    ),
                    {
                        "tenant": str(identity.tenant_id),
                        "relationship": str(identity.relationship_id),
                        "idempotency": str(identity.idempotency_key),
                    },
                )
            ).mappings().one_or_none()
            if existing is not None:
                if not self._same(existing, identity) or existing.maximum_units != maximum_units:
                    raise AllowanceConflict("ALLOWANCE_IDEMPOTENCY_CONFLICT")
                return self._receipt(existing, True)

            now = datetime.now(timezone.utc)
            resolved = (
                await session.execute(
                    text(
                        """
                        SELECT a.*, allocation.allocation_id, allocation.granted_units,
                               allocation.reserved_units, allocation.settled_units,
                               allocation.admission_fenced, tc.thread_id,
                               tc.provider_account_id, tc.raw_cost_inr_paise,
                               tc.marked_up_cost_paise, tc.updated_at,
                               trial_units.units_granted AS trial_units_granted,
                               trial_units.units_consumed AS trial_units_consumed
                        FROM business.relationship_commercial_authorities a
                        JOIN business.offering_component_allocations allocation
                          ON allocation.tenant_id=a.tenant_id
                         AND allocation.relationship_id=a.relationship_id
                         AND allocation.component_id=:component
                         AND :now >= allocation.period_start AND :now < allocation.period_end
                        JOIN institutional.thread_catalog tc
                          ON tc.thread_id=allocation.component_id
                        JOIN institutional.provider_accounts pa
                          ON pa.id=tc.provider_account_id AND pa.is_active=TRUE
                        LEFT JOIN institutional.bundle_profiles bundle
                          ON bundle.id=a.bundle_profile_id
                        LEFT JOIN business.trial_allocations trial ON trial.trial_id=a.trial_id
                        LEFT JOIN business.trial_free_unit_ledger trial_units
                          ON trial_units.trial_id=a.trial_id
                         AND trial_units.thread_type=allocation.component_id
                        WHERE a.tenant_id=:tenant AND a.relationship_id=:relationship
                          AND a.active=TRUE AND :now >= a.valid_from
                          AND (a.valid_until IS NULL OR :now < a.valid_until)
                          AND a.professional_type=:professional_type
                          AND a.professional_version=:professional_version
                          AND tc.status='ACTIVE' AND tc.founder_authorized_at IS NOT NULL
                          AND (
                            (a.authority_kind='ACCEPTED_OFFERING'
                              AND bundle.id IS NOT NULL AND bundle.is_active=TRUE
                              AND bundle.founder_authorized_at IS NOT NULL
                              AND bundle.agent_type=a.professional_type)
                            OR
                            (a.authority_kind='TRIAL' AND trial.status='ACTIVE'
                              AND trial.customer_id=a.customer_id
                              AND trial.agent_type=a.professional_type
                              AND trial.agent_version=a.professional_version
                              AND :now >= trial.started_at AND :now < trial.expires_at
                              AND trial_units.trial_id IS NOT NULL)
                          )
                        FOR UPDATE OF allocation
                        """
                    ),
                    {
                        "tenant": str(identity.tenant_id),
                        "relationship": str(identity.relationship_id),
                        "component": identity.component_id,
                        "professional_type": identity.professional_type,
                        "professional_version": identity.professional_version,
                        "now": now,
                    },
                )
            ).mappings().one_or_none()
            if resolved is None:
                raise AllowanceDenied("ALLOWANCE_AUTHORITY_UNAVAILABLE")
            if resolved.admission_fenced:
                raise AllowanceDenied("ALLOWANCE_ADMISSION_FENCED")
            available = resolved.granted_units - resolved.reserved_units - resolved.settled_units
            if resolved.trial_id is not None:
                trial_units = (
                    await session.execute(
                        text(
                            """SELECT units_granted,units_consumed
                               FROM business.trial_free_unit_ledger
                               WHERE trial_id=:trial AND thread_type=:component
                               FOR UPDATE"""
                        ),
                        {
                            "trial": str(resolved.trial_id),
                            "component": identity.component_id,
                        },
                    )
                ).mappings().one()
                available = min(
                    available,
                    trial_units.units_granted
                    - trial_units.units_consumed
                    - resolved.reserved_units,
                )
            if maximum_units > available:
                raise AllowanceDenied("ALLOWANCE_EXHAUSTED")

            reservation_id = uuid4()
            raw = maximum_units * resolved.raw_cost_inr_paise
            marked = maximum_units * resolved.marked_up_cost_paise
            rate_version = hashlib.sha256(
                f"{resolved.thread_id}:{resolved.provider_account_id}:"
                f"{resolved.raw_cost_inr_paise}:{resolved.marked_up_cost_paise}:"
                f"{resolved.updated_at.isoformat()}".encode()
            ).hexdigest()
            await session.execute(
                text(
                    """
                    INSERT INTO business.offering_component_reservations
                    (reservation_id,allocation_id,tenant_id,customer_id,relationship_id,
                     accepted_contract_id,contract_version,bundle_profile_id,trial_id,
                     agent_instance_id,professional_type,professional_version,skill_id,
                     skill_version,work_item_id,invocation_id,component_id,idempotency_key,
                     request_digest,owner_evidence_id,catalogue_thread_id,provider_account_id,
                     rate_version,raw_unit_cost_paise,marked_up_unit_cost_paise,maximum_units,
                     reserved_raw_paise,reserved_marked_up_paise,state,reserved_at)
                    VALUES
                    (:reservation,:allocation,:tenant,:customer,:relationship,
                     :contract,:contract_version,:bundle,:trial,:agent,:professional_type,
                     :professional_version,:skill,:skill_version,:work_item,:invocation,
                     :component,:idempotency,:request_digest,:evidence,:component,:provider,
                     :rate_version,:raw_unit,:marked_unit,:maximum,:raw,:marked,'RESERVED',:now)
                    """
                ),
                {
                    "reservation": str(reservation_id),
                    "allocation": str(resolved.allocation_id),
                    "tenant": str(identity.tenant_id),
                    "customer": str(resolved.customer_id),
                    "relationship": str(identity.relationship_id),
                    "contract": str(resolved.accepted_contract_id) if resolved.accepted_contract_id else None,
                    "contract_version": resolved.contract_version,
                    "bundle": str(resolved.bundle_profile_id) if resolved.bundle_profile_id else None,
                    "trial": str(resolved.trial_id) if resolved.trial_id else None,
                    "agent": str(identity.agent_instance_id),
                    "professional_type": identity.professional_type,
                    "professional_version": identity.professional_version,
                    "skill": identity.skill_id,
                    "skill_version": identity.skill_version,
                    "work_item": str(identity.work_item_id),
                    "invocation": str(identity.invocation_id),
                    "component": identity.component_id,
                    "idempotency": str(identity.idempotency_key),
                    "request_digest": identity.request_digest,
                    "evidence": str(identity.owner_evidence_id),
                    "provider": str(resolved.provider_account_id),
                    "rate_version": rate_version,
                    "raw_unit": resolved.raw_cost_inr_paise,
                    "marked_unit": resolved.marked_up_cost_paise,
                    "maximum": maximum_units,
                    "raw": raw,
                    "marked": marked,
                    "now": now,
                },
            )
            await session.execute(
                text(
                    """UPDATE business.offering_component_allocations
                       SET reserved_units=reserved_units+:units WHERE allocation_id=:allocation"""
                ),
                {"units": maximum_units, "allocation": str(resolved.allocation_id)},
            )
            return AllowanceReceipt(
                reservation_id, "RESERVED", maximum_units, raw, marked,
                identity.component_id, UUID(str(resolved.provider_account_id)), rate_version
            )

    async def settle(
        self,
        identity: AllowanceIdentity,
        reservation_id: UUID,
        actual_units: int,
        settlement_evidence_id: UUID,
    ) -> AllowanceReceipt:
        if actual_units < 0:
            raise AllowanceConflict("ALLOWANCE_USAGE_INVALID")
        async with self._sessions() as session, session.begin():
            row = await self._locked(session, identity, reservation_id)
            raw = actual_units * row.raw_unit_cost_paise
            marked = actual_units * row.marked_up_unit_cost_paise
            if row.state != "RESERVED":
                if (
                    row.state != "SETTLED"
                    or row.actual_units != actual_units
                    or str(row.settlement_evidence_id) != str(settlement_evidence_id)
                ):
                    raise AllowanceConflict("ALLOWANCE_SETTLEMENT_CONFLICT")
                return self._receipt(row, True)
            now = datetime.now(timezone.utc)
            await session.execute(
                text(
                    """INSERT INTO institutional.platform_cost_ledger
                       (id,provider_account_id,thread_type,customer_id,tenant_id,relationship_id,
                        agent_instance_id,skill_id,skill_version,work_item_id,invocation_id,
                        raw_cost_inr_paise,marked_up_cost_inr_paise,billing_period_start,
                        recorded_at,component_id,offering_reservation_id)
                       VALUES (:id,:provider,:component,:customer,:tenant,:relationship,:agent,
                        :skill,:skill_version,:work_item,:invocation,:raw,:marked,:period,:now,
                        :component,:reservation)"""
                ),
                {
                    "id": str(uuid4()), "provider": str(row.provider_account_id),
                    "component": row.component_id, "customer": str(row.customer_id),
                    "tenant": str(row.tenant_id), "relationship": str(row.relationship_id),
                    "agent": str(row.agent_instance_id), "skill": row.skill_id,
                    "skill_version": row.skill_version, "work_item": str(row.work_item_id),
                    "invocation": str(row.invocation_id), "raw": raw, "marked": marked,
                    "period": now.date().replace(day=1), "now": now,
                    "reservation": str(reservation_id),
                },
            )
            await session.execute(
                text(
                    """UPDATE business.offering_component_reservations
                       SET state='SETTLED',actual_units=:actual,actual_raw_paise=:raw,
                           actual_marked_up_paise=:marked,settled_at=:now,
                           settlement_evidence_id=:evidence
                       WHERE reservation_id=:reservation"""
                ),
                {
                    "actual": actual_units, "raw": raw, "marked": marked, "now": now,
                    "evidence": str(settlement_evidence_id), "reservation": str(reservation_id),
                },
            )
            await session.execute(
                text(
                    """UPDATE business.offering_component_allocations
                       SET reserved_units=reserved_units-:maximum,
                           settled_units=settled_units+:actual,
                           admission_fenced=admission_fenced OR :actual > :maximum
                       WHERE allocation_id=:allocation"""
                ),
                {
                    "maximum": row.maximum_units, "actual": actual_units,
                    "allocation": str(row.allocation_id),
                },
            )
            if row.trial_id is not None:
                await session.execute(
                    text(
                        """UPDATE business.trial_free_unit_ledger
                           SET units_consumed=units_consumed+:actual,updated_at=:now
                           WHERE trial_id=:trial AND thread_type=:component"""
                    ),
                    {
                        "actual": actual_units,
                        "now": now,
                        "trial": str(row.trial_id),
                        "component": row.component_id,
                    },
                )
            return AllowanceReceipt(
                reservation_id, "SETTLED", row.maximum_units,
                row.reserved_raw_paise, row.reserved_marked_up_paise,
                row.catalogue_thread_id, UUID(str(row.provider_account_id)), row.rate_version
            )

    async def release(
        self,
        identity: AllowanceIdentity,
        reservation_id: UUID,
        non_dispatch_evidence_id: UUID,
    ) -> AllowanceReceipt:
        async with self._sessions() as session, session.begin():
            row = await self._locked(session, identity, reservation_id)
            if row.state != "RESERVED":
                if row.state != "RELEASED" or str(row.non_dispatch_evidence_id) != str(non_dispatch_evidence_id):
                    raise AllowanceConflict("ALLOWANCE_RELEASE_CONFLICT")
                return self._receipt(row, True)
            now = datetime.now(timezone.utc)
            await session.execute(
                text(
                    """UPDATE business.offering_component_reservations
                       SET state='RELEASED',actual_units=0,actual_raw_paise=0,
                           actual_marked_up_paise=0,settled_at=:now,
                           non_dispatch_evidence_id=:evidence
                       WHERE reservation_id=:reservation"""
                ),
                {"now": now, "evidence": str(non_dispatch_evidence_id), "reservation": str(reservation_id)},
            )
            await session.execute(
                text(
                    """UPDATE business.offering_component_allocations
                       SET reserved_units=reserved_units-:maximum
                       WHERE allocation_id=:allocation"""
                ),
                {"maximum": row.maximum_units, "allocation": str(row.allocation_id)},
            )
            return AllowanceReceipt(
                reservation_id, "RELEASED", row.maximum_units,
                row.reserved_raw_paise, row.reserved_marked_up_paise,
                row.catalogue_thread_id, UUID(str(row.provider_account_id)), row.rate_version
            )

    async def reconcile(self, identity: AllowanceIdentity) -> AllowanceReceipt | None:
        async with self._sessions() as session:
            row = (
                await session.execute(
                    text(
                        """SELECT * FROM business.offering_component_reservations
                           WHERE tenant_id=:tenant AND relationship_id=:relationship
                             AND idempotency_key=:idempotency"""
                    ),
                    {
                        "tenant": str(identity.tenant_id),
                        "relationship": str(identity.relationship_id),
                        "idempotency": str(identity.idempotency_key),
                    },
                )
            ).mappings().one_or_none()
            if row is None:
                return None
            if not self._same(row, identity):
                raise AllowanceConflict("ALLOWANCE_IDEMPOTENCY_CONFLICT")
            return self._receipt(row, True)

    async def _locked(
        self, session: AsyncSession, identity: AllowanceIdentity, reservation_id: UUID
    ) -> object:
        row = (
            await session.execute(
                text(
                    """SELECT * FROM business.offering_component_reservations
                       WHERE reservation_id=:reservation FOR UPDATE"""
                ),
                {"reservation": str(reservation_id)},
            )
        ).mappings().one_or_none()
        if row is None or not self._same(row, identity):
            raise AllowanceDenied("ALLOWANCE_RESERVATION_NOT_FOUND")
        return row
