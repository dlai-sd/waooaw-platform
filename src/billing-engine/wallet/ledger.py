# Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C4-02
# Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C4-11
# Constitutional basis: C-059, C-088, C-089, C-063
"""WBE Wallet ledger: credit, reserve, settle, release, expire and balance over lots (WC-136 C4-02).

The ledger works inside a caller-owned database session and never commits: the caller owns the
transaction, so wallet writes commit or roll back together with the work they pay for. Every
operation is idempotent on (tenant_id, idempotency_key, entry_kind) and refuses a changed payload
with WALLET_IDEMPOTENCY_CONFLICT. Money is integer paise; timestamps are UTC.

Lot availability is credited minus open (RESERVED/UNKNOWN) reservations minus settled actuals minus
expired value; the SQL function business.wallet_available computes the same quantity.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from datetime import datetime, timezone
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from sqlalchemy import DateTime, bindparam, text
from sqlalchemy.ext.asyncio import AsyncSession

from wallet import spend_events
from wallet.entity_models import (
    ACCOUNT_CLASSES,
    DEFAULT_SOURCE_KIND,
    GRANT_SOURCE_KIND_BY_ACCOUNT_CLASS,
    LOT_KINDS,
    SOURCE_KINDS,
    ReservationIdentity,
    WalletAccount,
    WalletBalance,
    WalletCreditReceipt,
    WalletError,
    WalletExpiryReceipt,
    WalletReservationReceipt,
    as_json_object,
    as_utc,
    canonical_digest,
    utc_iso,
)

_TS = DateTime(timezone=True)
_NIL_UUID = "00000000-0000-0000-0000-000000000000"

_LOT_COLUMNS = """
    l.lot_id, l.credited_paise, l.valid_from, l.valid_until,
    COALESCE((SELECT SUM(r.reserved_paise) FROM business.wallet_reservations r
              WHERE r.tenant_id = l.tenant_id AND r.lot_id = l.lot_id
                AND r.state IN ('RESERVED', 'UNKNOWN')), 0) AS reserved_paise,
    COALESCE((SELECT SUM(r.actual_paise) FROM business.wallet_reservations r
              WHERE r.tenant_id = l.tenant_id AND r.lot_id = l.lot_id
                AND r.state = 'SETTLED'), 0) AS settled_paise,
    COALESCE((SELECT SUM(e.amount_paise) FROM business.wallet_entries e
              WHERE e.tenant_id = l.tenant_id AND e.lot_id = l.lot_id
                AND e.entry_kind = 'EXPIRE'), 0) AS expired_paise
"""
_ACTIVE_LOTS = f"""
    SELECT {_LOT_COLUMNS}
    FROM business.wallet_lots l
    WHERE l.tenant_id = :tenant AND l.account_id = :account
      AND l.valid_from <= :at AND l.valid_until > :at
    ORDER BY l.valid_until, l.created_at, l.lot_id
"""
_EXPIRED_LOTS = f"""
    SELECT {_LOT_COLUMNS}
    FROM business.wallet_lots l
    WHERE l.tenant_id = :tenant AND l.account_id = :account AND l.valid_until <= :at
    ORDER BY l.valid_until, l.created_at, l.lot_id
"""


def _stmt(sql: str, *datetime_params: str):
    statement = text(sql)
    if datetime_params:
        statement = statement.bindparams(*[bindparam(name, type_=_TS) for name in datetime_params])
    return statement


def _lot_view(row: Mapping[str, Any]) -> dict[str, Any]:
    credited = int(row["credited_paise"])
    reserved = int(row["reserved_paise"])
    settled = int(row["settled_paise"])
    expired = int(row["expired_paise"])
    return {
        "lot_id": UUID(str(row["lot_id"])),
        "credited": credited,
        "reserved": reserved,
        "settled": settled,
        "expired": expired,
        "available": credited - reserved - settled - expired,
        "valid_from": as_utc(row["valid_from"]),
        "valid_until": as_utc(row["valid_until"]),
    }


def _account_from(row: Mapping[str, Any]) -> WalletAccount:
    def _uuid(name: str) -> UUID | None:
        return UUID(str(row[name])) if row[name] is not None else None

    return WalletAccount(
        account_id=UUID(str(row["account_id"])),
        tenant_id=UUID(str(row["tenant_id"])),
        owner_kind=row["owner_kind"],
        owner_ref=_uuid("owner_ref"),
        account_class=row["account_class"],
        scope_kind=row["scope_kind"],
        relationship_id=_uuid("relationship_id"),
        skill_id=row["skill_id"],
        campaign_ref=row["campaign_ref"],
        lead_ref=row["lead_ref"],
        environment=row["environment"],
        agent_type=row["agent_type"],
        agent_version=row["agent_version"],
        status=row["status"],
        created_at=as_utc(row["created_at"]),
    )


class WalletLedger:
    def __init__(
        self,
        session: AsyncSession,
        *,
        overrun_tolerance_paise: int = 0,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        if overrun_tolerance_paise < 0:
            raise WalletError("WALLET_AMOUNT_INVALID")
        self._session = session
        self._tolerance = overrun_tolerance_paise
        self._now = now or (lambda: datetime.now(timezone.utc))

    # ------------------------------------------------------------------ accounts

    async def open_account(
        self,
        tenant_id: UUID,
        account_class: str,
        *,
        owner_ref: UUID | None = None,
        relationship_id: UUID | None = None,
        skill_id: str | None = None,
        campaign_ref: str | None = None,
        lead_ref: str | None = None,
        environment: str | None = None,
        agent_type: str | None = None,
        agent_version: str | None = None,
    ) -> WalletAccount:
        """Open the account for this key, or return the existing one (idempotent by account key)."""
        if account_class not in ACCOUNT_CLASSES:
            raise WalletError("WALLET_ACCOUNT_INVALID", "account_class")
        if account_class == "SUBSCRIPTION":
            owner_kind, scope_kind = "CUSTOMER", "RELATIONSHIP"
            valid = owner_ref is not None and relationship_id is not None
        elif account_class in ("TRIAL", "SETUP_GRANT"):
            owner_kind, scope_kind = "PLATFORM", "RELATIONSHIP"
            valid = (
                owner_ref is None
                and relationship_id is not None
                and bool(agent_type)
                and bool(agent_version)
            )
        elif account_class == "ACQUISITION":
            owner_kind, scope_kind = "PLATFORM", "MARKETPLACE"
            valid = owner_ref is None
        else:
            owner_kind, scope_kind = "PLATFORM", "ENVIRONMENT"
            valid = owner_ref is None and bool(environment)
        if not valid:
            raise WalletError("WALLET_ACCOUNT_INVALID", account_class)

        existing = await self.find_account(
            tenant_id,
            account_class,
            relationship_id=relationship_id,
            skill_id=skill_id,
            campaign_ref=campaign_ref,
            lead_ref=lead_ref,
            environment=environment,
        )
        if existing is not None:
            return existing
        await self._session.execute(
            _stmt(
                """
                INSERT INTO business.wallet_accounts
                (account_id, tenant_id, owner_kind, owner_ref, account_class, scope_kind,
                 relationship_id, skill_id, campaign_ref, lead_ref, environment, agent_type,
                 agent_version, status, created_at)
                VALUES (:account, :tenant, :owner_kind, :owner_ref, :account_class, :scope_kind,
                        :relationship, :skill, :campaign, :lead, :environment, :agent_type,
                        :agent_version, 'ACTIVE', :now)
                ON CONFLICT DO NOTHING
                """,
                "now",
            ),
            {
                "account": str(uuid4()),
                "tenant": str(tenant_id),
                "owner_kind": owner_kind,
                "owner_ref": str(owner_ref) if owner_ref is not None else None,
                "account_class": account_class,
                "scope_kind": scope_kind,
                "relationship": str(relationship_id) if relationship_id is not None else None,
                "skill": skill_id,
                "campaign": campaign_ref,
                "lead": lead_ref,
                "environment": environment,
                "agent_type": agent_type,
                "agent_version": agent_version,
                "now": self._now(),
            },
        )
        created = await self.find_account(
            tenant_id,
            account_class,
            relationship_id=relationship_id,
            skill_id=skill_id,
            campaign_ref=campaign_ref,
            lead_ref=lead_ref,
            environment=environment,
        )
        if created is None:
            raise WalletError("WALLET_ACCOUNT_INVALID", "account not readable after open")
        return created

    async def find_account(
        self,
        tenant_id: UUID,
        account_class: str,
        *,
        relationship_id: UUID | None = None,
        skill_id: str | None = None,
        campaign_ref: str | None = None,
        lead_ref: str | None = None,
        environment: str | None = None,
    ) -> WalletAccount | None:
        row = (
            await self._session.execute(
                text(
                    """
                    SELECT * FROM business.wallet_accounts
                    WHERE tenant_id = :tenant AND account_class = :account_class
                      AND COALESCE(relationship_id, :nil) = :relationship
                      AND COALESCE(skill_id, '') = :skill
                      AND COALESCE(campaign_ref, '') = :campaign
                      AND COALESCE(lead_ref, '') = :lead
                      AND COALESCE(environment, '') = :environment
                    """
                ),
                {
                    "tenant": str(tenant_id),
                    "account_class": account_class,
                    "nil": _NIL_UUID,
                    "relationship": str(relationship_id) if relationship_id is not None else _NIL_UUID,
                    "skill": skill_id or "",
                    "campaign": campaign_ref or "",
                    "lead": lead_ref or "",
                    "environment": environment or "",
                },
            )
        ).mappings().one_or_none()
        return _account_from(row) if row is not None else None

    async def get_account(self, tenant_id: UUID, account_id: UUID) -> WalletAccount | None:
        row = (
            await self._session.execute(
                text(
                    "SELECT * FROM business.wallet_accounts "
                    "WHERE tenant_id = :tenant AND account_id = :account"
                ),
                {"tenant": str(tenant_id), "account": str(account_id)},
            )
        ).mappings().one_or_none()
        return _account_from(row) if row is not None else None

    # ------------------------------------------------------------------ credit

    async def credit(
        self,
        account: WalletAccount,
        lot_kind: str,
        paise: int,
        valid_from: datetime,
        valid_until: datetime,
        source_ref: str,
        pinned_versions: Mapping[str, object],
        idempotency_key: UUID,
        *,
        source_kind: str | None = None,
        evidence_id: UUID | None = None,
    ) -> WalletCreditReceipt:
        if lot_kind not in LOT_KINDS or paise <= 0 or not source_ref:
            raise WalletError("WALLET_AMOUNT_INVALID")
        valid_from, valid_until = as_utc(valid_from), as_utc(valid_until)
        if valid_until <= valid_from:
            raise WalletError("WALLET_AMOUNT_INVALID", "validity window")
        resolved_source = source_kind or DEFAULT_SOURCE_KIND.get(lot_kind) or (
            GRANT_SOURCE_KIND_BY_ACCOUNT_CLASS.get(account.account_class)
        )
        if resolved_source not in SOURCE_KINDS:
            raise WalletError("WALLET_ACCOUNT_INVALID", "source_kind")
        evidence = evidence_id or idempotency_key
        pinned = dict(pinned_versions)
        digest = canonical_digest(
            {
                "op": "credit",
                "account": str(account.account_id),
                "lot_kind": lot_kind,
                "source_kind": resolved_source,
                "paise": paise,
                "valid_from": utc_iso(valid_from),
                "valid_until": utc_iso(valid_until),
                "source_ref": source_ref,
                "pinned_versions": pinned,
                "evidence": str(evidence),
            }
        )
        await self._lock_account(account.tenant_id, account.account_id, require_active=False)
        entry = await self._entry(account.tenant_id, idempotency_key, "CREDIT")
        if entry is not None:
            self._require_same_digest(entry, digest)
            lot = (
                await self._session.execute(
                    text(
                        "SELECT * FROM business.wallet_lots "
                        "WHERE tenant_id = :tenant AND lot_id = :lot"
                    ),
                    {"tenant": str(account.tenant_id), "lot": str(entry["lot_id"])},
                )
            ).mappings().one()
            return WalletCreditReceipt(
                lot_id=UUID(str(lot["lot_id"])),
                account_id=account.account_id,
                lot_kind=lot["lot_kind"],
                source_kind=lot["source_kind"],
                credited_paise=int(lot["credited_paise"]),
                valid_from=as_utc(lot["valid_from"]),
                valid_until=as_utc(lot["valid_until"]),
                replayed=True,
            )
        await self._require_active(account.tenant_id, account.account_id)
        now = self._now()
        lot_id = uuid4()
        await self._session.execute(
            _stmt(
                """
                INSERT INTO business.wallet_lots
                (lot_id, tenant_id, account_id, lot_kind, credited_paise, valid_from, valid_until,
                 source_kind, source_ref, pinned_versions, evidence_id, created_at)
                VALUES (:lot, :tenant, :account, :lot_kind, :paise, :valid_from, :valid_until,
                        :source_kind, :source_ref, :pinned, :evidence, :now)
                """,
                "valid_from",
                "valid_until",
                "now",
            ),
            {
                "lot": str(lot_id),
                "tenant": str(account.tenant_id),
                "account": str(account.account_id),
                "lot_kind": lot_kind,
                "paise": paise,
                "valid_from": valid_from,
                "valid_until": valid_until,
                "source_kind": resolved_source,
                "source_ref": source_ref,
                "pinned": json.dumps(pinned, sort_keys=True),
                "evidence": str(evidence),
                "now": now,
            },
        )
        await self._insert_entry(
            tenant_id=account.tenant_id,
            account_id=account.account_id,
            lot_id=lot_id,
            kind="CREDIT",
            amount=paise,
            reservation_id=None,
            idempotency_key=idempotency_key,
            digest=digest,
            component_id=None,
            invocation_id=None,
            evidence_id=evidence,
            at=now,
        )
        return WalletCreditReceipt(
            lot_id=lot_id,
            account_id=account.account_id,
            lot_kind=lot_kind,
            source_kind=resolved_source,
            credited_paise=paise,
            valid_from=valid_from,
            valid_until=valid_until,
        )

    # ------------------------------------------------------------------ reserve

    async def reserve(
        self,
        account: WalletAccount,
        component_id: str,
        paise: int,
        expires_at: datetime,
        identity: ReservationIdentity,
        idempotency_key: UUID,
    ) -> WalletReservationReceipt:
        """Hold paise on the unexpired lot that expires first and can cover the whole amount."""
        if paise <= 0 or not component_id:
            raise WalletError("WALLET_AMOUNT_INVALID")
        expires_at = as_utc(expires_at)
        pinned = dict(identity.pinned_versions)
        digest = canonical_digest(
            {
                "op": "reserve",
                "account": str(account.account_id),
                "component": component_id,
                "paise": paise,
                "expires_at": utc_iso(expires_at),
                "pinned_versions": pinned,
                "invocation": str(identity.invocation_id) if identity.invocation_id else None,
                "evidence": str(identity.evidence_id) if identity.evidence_id else None,
            }
        )
        await self._lock_account(account.tenant_id, account.account_id, require_active=False)
        entry = await self._entry(account.tenant_id, idempotency_key, "RESERVE")
        if entry is not None:
            self._require_same_digest(entry, digest)
            row = await self._reservation_row(account.tenant_id, idempotency_key)
            return self._reservation_receipt(row, replayed=True)
        await self._require_active(account.tenant_id, account.account_id)
        now = self._now()
        if await self._fenced(account.tenant_id, account.account_id):
            self._deny(account, component_id, paise, "OVERRUN_FENCE")
            raise WalletError("WALLET_INSUFFICIENT", "OVERRUN_FENCE")
        lots = await self._lots(account.tenant_id, account.account_id, now)
        chosen = next((lot for lot in lots if lot["available"] >= paise), None)
        if chosen is None:
            self._deny(account, component_id, paise, "BALANCE")
            raise WalletError("WALLET_INSUFFICIENT", "BALANCE")
        await self._session.execute(
            _stmt(
                """
                INSERT INTO business.wallet_reservations
                (reservation_id, tenant_id, account_id, lot_id, component_id, reserved_paise,
                 actual_paise, state, pinned_account_class, pinned_versions, expires_at,
                 created_at, resolved_at)
                VALUES (:reservation, :tenant, :account, :lot, :component, :paise, NULL,
                        'RESERVED', :account_class, :pinned, :expires_at, :now, NULL)
                """,
                "expires_at",
                "now",
            ),
            {
                "reservation": str(idempotency_key),
                "tenant": str(account.tenant_id),
                "account": str(account.account_id),
                "lot": str(chosen["lot_id"]),
                "component": component_id,
                "paise": paise,
                "account_class": account.account_class,
                "pinned": json.dumps(pinned, sort_keys=True),
                "expires_at": expires_at,
                "now": now,
            },
        )
        await self._insert_entry(
            tenant_id=account.tenant_id,
            account_id=account.account_id,
            lot_id=chosen["lot_id"],
            kind="RESERVE",
            amount=paise,
            reservation_id=idempotency_key,
            idempotency_key=idempotency_key,
            digest=digest,
            component_id=component_id,
            invocation_id=identity.invocation_id,
            evidence_id=identity.evidence_id,
            at=now,
        )
        spend_events.emit_spend_event(
            spend_events.SPEND_RESERVED,
            account_class=account.account_class,
            tenant_id=account.tenant_id,
            paise=paise,
            relationship_id=account.relationship_id,
            skill_id=account.skill_id,
            component_id=component_id,
            campaign_ref=account.campaign_ref,
            lead_ref=account.lead_ref,
        )
        return WalletReservationReceipt(
            reservation_id=idempotency_key,
            account_id=account.account_id,
            lot_id=chosen["lot_id"],
            component_id=component_id,
            state="RESERVED",
            reserved_paise=paise,
            actual_paise=None,
            pinned_account_class=account.account_class,
            pinned_versions=pinned,
        )

    # ------------------------------------------------------------------ settle / release / unknown

    async def settle(
        self,
        tenant_id: UUID,
        reservation_id: UUID,
        actual_paise: int,
        evidence_id: UUID,
    ) -> WalletReservationReceipt:
        """Record the actual cost; an overrun is kept as an ADJUST entry and may fence admission."""
        if actual_paise <= 0:
            raise WalletError("WALLET_AMOUNT_INVALID")
        digest = canonical_digest(
            {
                "op": "settle",
                "reservation": str(reservation_id),
                "actual": actual_paise,
                "evidence": str(evidence_id),
            }
        )
        row = await self._locked_reservation(tenant_id, reservation_id)
        entry = await self._entry(tenant_id, reservation_id, "SETTLE")
        if entry is not None:
            self._require_same_digest(entry, digest)
            return self._reservation_receipt(row, replayed=True)
        if row["state"] not in ("RESERVED", "UNKNOWN"):
            raise WalletError("WALLET_IDEMPOTENCY_CONFLICT", "reservation already resolved")
        reserved = int(row["reserved_paise"])
        covered = min(actual_paise, reserved)
        overrun = max(0, actual_paise - reserved)
        now = self._now()
        await self._resolve(tenant_id, reservation_id, "SETTLED", actual_paise, now)
        await self._insert_entry(
            tenant_id=tenant_id,
            account_id=UUID(str(row["account_id"])),
            lot_id=UUID(str(row["lot_id"])),
            kind="SETTLE",
            amount=covered,
            reservation_id=reservation_id,
            idempotency_key=reservation_id,
            digest=digest,
            component_id=row["component_id"],
            invocation_id=None,
            evidence_id=evidence_id,
            at=now,
        )
        if overrun > 0:
            await self._insert_entry(
                tenant_id=tenant_id,
                account_id=UUID(str(row["account_id"])),
                lot_id=UUID(str(row["lot_id"])),
                kind="ADJUST",
                amount=overrun,
                reservation_id=reservation_id,
                idempotency_key=reservation_id,
                digest=digest,
                component_id=row["component_id"],
                invocation_id=None,
                evidence_id=evidence_id,
                at=now,
            )
        await self._observe(spend_events.SPEND_SETTLED, tenant_id, row, actual_paise, "OVERRUN" if overrun else "OK")
        return self._reservation_receipt(
            await self._reservation_row(tenant_id, reservation_id), replayed=False
        )

    async def release(
        self,
        tenant_id: UUID,
        reservation_id: UUID,
        non_dispatch_evidence_id: UUID,
    ) -> WalletReservationReceipt:
        """Return a hold that was provably never dispatched."""
        digest = canonical_digest(
            {
                "op": "release",
                "reservation": str(reservation_id),
                "evidence": str(non_dispatch_evidence_id),
            }
        )
        row = await self._locked_reservation(tenant_id, reservation_id)
        entry = await self._entry(tenant_id, reservation_id, "RELEASE")
        if entry is not None:
            self._require_same_digest(entry, digest)
            return self._reservation_receipt(row, replayed=True)
        if row["state"] not in ("RESERVED", "UNKNOWN"):
            raise WalletError("WALLET_IDEMPOTENCY_CONFLICT", "reservation already resolved")
        now = self._now()
        await self._resolve(tenant_id, reservation_id, "RELEASED", 0, now)
        await self._insert_entry(
            tenant_id=tenant_id,
            account_id=UUID(str(row["account_id"])),
            lot_id=UUID(str(row["lot_id"])),
            kind="RELEASE",
            amount=int(row["reserved_paise"]),
            reservation_id=reservation_id,
            idempotency_key=reservation_id,
            digest=digest,
            component_id=row["component_id"],
            invocation_id=None,
            evidence_id=non_dispatch_evidence_id,
            at=now,
        )
        await self._observe(
            spend_events.SPEND_RELEASED, tenant_id, row, int(row["reserved_paise"]), "NOT_DISPATCHED"
        )
        return self._reservation_receipt(
            await self._reservation_row(tenant_id, reservation_id), replayed=False
        )

    async def mark_unknown(self, tenant_id: UUID, reservation_id: UUID) -> WalletReservationReceipt:
        """An unknown outcome keeps the hold: UNKNOWN reservations still reduce availability."""
        row = await self._locked_reservation(tenant_id, reservation_id)
        if row["state"] == "UNKNOWN":
            return self._reservation_receipt(row, replayed=True)
        if row["state"] != "RESERVED":
            raise WalletError("WALLET_IDEMPOTENCY_CONFLICT", "reservation already resolved")
        await self._session.execute(
            text(
                "UPDATE business.wallet_reservations SET state = 'UNKNOWN' "
                "WHERE tenant_id = :tenant AND reservation_id = :reservation AND state = 'RESERVED'"
            ),
            {"tenant": str(tenant_id), "reservation": str(reservation_id)},
        )
        return self._reservation_receipt(
            await self._reservation_row(tenant_id, reservation_id), replayed=False
        )

    async def get_reservation(
        self, tenant_id: UUID, reservation_id: UUID
    ) -> WalletReservationReceipt | None:
        row = (
            await self._session.execute(
                text(
                    "SELECT * FROM business.wallet_reservations "
                    "WHERE tenant_id = :tenant AND reservation_id = :reservation"
                ),
                {"tenant": str(tenant_id), "reservation": str(reservation_id)},
            )
        ).mappings().one_or_none()
        return self._reservation_receipt(row, replayed=False) if row is not None else None

    # ------------------------------------------------------------------ expire / balance

    async def expire(self, account: WalletAccount, at: datetime) -> list[WalletExpiryReceipt]:
        """Write EXPIRE entries for the unspent value of lots past valid_until; never rolled over."""
        at = as_utc(at)
        await self._lock_account(account.tenant_id, account.account_id, require_active=False)
        written: list[WalletExpiryReceipt] = []
        for lot in await self._lots(account.tenant_id, account.account_id, at, expired=True):
            if lot["available"] <= 0:
                continue
            previous = (
                await self._session.execute(
                    text(
                        "SELECT COUNT(*) FROM business.wallet_entries "
                        "WHERE tenant_id = :tenant AND lot_id = :lot AND entry_kind = 'EXPIRE'"
                    ),
                    {"tenant": str(account.tenant_id), "lot": str(lot["lot_id"])},
                )
            ).scalar_one()
            key = uuid5(NAMESPACE_URL, f"wallet-expire:{lot['lot_id']}:{int(previous)}")
            await self._insert_entry(
                tenant_id=account.tenant_id,
                account_id=account.account_id,
                lot_id=lot["lot_id"],
                kind="EXPIRE",
                amount=lot["available"],
                reservation_id=None,
                idempotency_key=key,
                digest=canonical_digest(
                    {"op": "expire", "lot": str(lot["lot_id"]), "paise": lot["available"]}
                ),
                component_id=None,
                invocation_id=None,
                evidence_id=None,
                at=self._now(),
            )
            written.append(WalletExpiryReceipt(lot["lot_id"], lot["available"]))
        return written

    async def balance(self, account: WalletAccount, at: datetime) -> WalletBalance:
        at = as_utc(at)
        lots = await self._lots(account.tenant_id, account.account_id, at)
        return WalletBalance(
            account_id=account.account_id,
            at=at,
            available_paise=sum(lot["available"] for lot in lots),
            credited_paise=sum(lot["credited"] for lot in lots),
            reserved_paise=sum(lot["reserved"] for lot in lots),
            settled_paise=sum(lot["settled"] for lot in lots),
            expired_paise=sum(lot["expired"] for lot in lots),
        )

    # ------------------------------------------------------------------ internals

    def _is_postgres(self) -> bool:
        return self._session.get_bind().dialect.name == "postgresql"

    async def _lock_account(self, tenant_id: UUID, account_id: UUID, *, require_active: bool) -> None:
        lock = " FOR UPDATE" if self._is_postgres() else ""
        row = (
            await self._session.execute(
                text(
                    "SELECT status FROM business.wallet_accounts "
                    f"WHERE tenant_id = :tenant AND account_id = :account{lock}"
                ),
                {"tenant": str(tenant_id), "account": str(account_id)},
            )
        ).mappings().one_or_none()
        if row is None:
            raise WalletError("WALLET_ACCOUNT_UNKNOWN")
        if require_active and row["status"] != "ACTIVE":
            raise WalletError("WALLET_ACCOUNT_CLOSED")

    async def _require_active(self, tenant_id: UUID, account_id: UUID) -> None:
        await self._lock_account(tenant_id, account_id, require_active=True)

    async def _entry(
        self, tenant_id: UUID, idempotency_key: UUID, kind: str
    ) -> Mapping[str, Any] | None:
        return (
            await self._session.execute(
                text(
                    "SELECT * FROM business.wallet_entries "
                    "WHERE tenant_id = :tenant AND idempotency_key = :key AND entry_kind = :kind"
                ),
                {"tenant": str(tenant_id), "key": str(idempotency_key), "kind": kind},
            )
        ).mappings().one_or_none()

    @staticmethod
    def _require_same_digest(entry: Mapping[str, Any], digest: str) -> None:
        if entry["request_digest"] != digest:
            raise WalletError("WALLET_IDEMPOTENCY_CONFLICT")

    async def _insert_entry(
        self,
        *,
        tenant_id: UUID,
        account_id: UUID,
        lot_id: UUID | None,
        kind: str,
        amount: int,
        reservation_id: UUID | None,
        idempotency_key: UUID,
        digest: str,
        component_id: str | None,
        invocation_id: UUID | None,
        evidence_id: UUID | None,
        at: datetime,
    ) -> None:
        await self._session.execute(
            _stmt(
                """
                INSERT INTO business.wallet_entries
                (entry_id, tenant_id, account_id, lot_id, entry_kind, amount_paise, reservation_id,
                 idempotency_key, request_digest, component_id, invocation_id, evidence_id,
                 occurred_at)
                VALUES (:entry, :tenant, :account, :lot, :kind, :amount, :reservation,
                        :key, :digest, :component, :invocation, :evidence, :at)
                """,
                "at",
            ),
            {
                "entry": str(uuid4()),
                "tenant": str(tenant_id),
                "account": str(account_id),
                "lot": str(lot_id) if lot_id is not None else None,
                "kind": kind,
                "amount": amount,
                "reservation": str(reservation_id) if reservation_id is not None else None,
                "key": str(idempotency_key),
                "digest": digest,
                "component": component_id,
                "invocation": str(invocation_id) if invocation_id is not None else None,
                "evidence": str(evidence_id) if evidence_id is not None else None,
                "at": at,
            },
        )

    async def _lots(
        self, tenant_id: UUID, account_id: UUID, at: datetime, *, expired: bool = False
    ) -> list[dict[str, Any]]:
        rows = (
            await self._session.execute(
                _stmt(_EXPIRED_LOTS if expired else _ACTIVE_LOTS, "at"),
                {"tenant": str(tenant_id), "account": str(account_id), "at": at},
            )
        ).mappings().all()
        return [_lot_view(row) for row in rows]

    async def _fenced(self, tenant_id: UUID, account_id: UUID) -> bool:
        """An overrun beyond tolerance fences admission until a later CREDIT arrives."""
        row = (
            await self._session.execute(
                text(
                    """
                    SELECT 1 FROM business.wallet_entries a
                    WHERE a.tenant_id = :tenant AND a.account_id = :account
                      AND a.entry_kind = 'ADJUST' AND a.amount_paise > :tolerance
                      AND NOT EXISTS (
                        SELECT 1 FROM business.wallet_entries c
                        WHERE c.tenant_id = a.tenant_id AND c.account_id = a.account_id
                          AND c.entry_kind = 'CREDIT' AND c.occurred_at > a.occurred_at)
                    LIMIT 1
                    """
                ),
                {"tenant": str(tenant_id), "account": str(account_id), "tolerance": self._tolerance},
            )
        ).first()
        return row is not None

    async def _reservation_row(self, tenant_id: UUID, reservation_id: UUID) -> Mapping[str, Any]:
        row = (
            await self._session.execute(
                text(
                    "SELECT * FROM business.wallet_reservations "
                    "WHERE tenant_id = :tenant AND reservation_id = :reservation"
                ),
                {"tenant": str(tenant_id), "reservation": str(reservation_id)},
            )
        ).mappings().one_or_none()
        if row is None:
            raise WalletError("WALLET_RESERVATION_UNKNOWN")
        return row

    async def _locked_reservation(self, tenant_id: UUID, reservation_id: UUID) -> Mapping[str, Any]:
        row = await self._reservation_row(tenant_id, reservation_id)
        await self._lock_account(tenant_id, UUID(str(row["account_id"])), require_active=False)
        return await self._reservation_row(tenant_id, reservation_id)

    @staticmethod
    def _deny(account: WalletAccount, component_id: str, paise: int, reason: str) -> None:
        spend_events.emit_spend_event(
            spend_events.SPEND_DENIED,
            account_class=account.account_class,
            tenant_id=account.tenant_id,
            paise=paise,
            reason_code=f"WALLET_INSUFFICIENT_{reason}",
            relationship_id=account.relationship_id,
            skill_id=account.skill_id,
            component_id=component_id,
            campaign_ref=account.campaign_ref,
            lead_ref=account.lead_ref,
        )

    async def _observe(self, event: str, tenant_id: UUID, row: Mapping[str, Any], paise: int, reason: str) -> None:
        attribution = (
            await self._session.execute(
                text(
                    "SELECT relationship_id, skill_id, campaign_ref, lead_ref FROM business.wallet_accounts "
                    "WHERE tenant_id = :tenant AND account_id = :account"
                ),
                {"tenant": str(tenant_id), "account": str(row["account_id"])},
            )
        ).mappings().one_or_none()
        spend_events.emit_spend_event(
            event,
            account_class=str(row["pinned_account_class"]),
            tenant_id=tenant_id,
            paise=paise,
            reason_code=reason,
            relationship_id=None if attribution is None else attribution["relationship_id"],
            skill_id=None if attribution is None else attribution["skill_id"],
            component_id=row["component_id"],
            campaign_ref=None if attribution is None else attribution["campaign_ref"],
            lead_ref=None if attribution is None else attribution["lead_ref"],
        )

    async def _resolve(
        self, tenant_id: UUID, reservation_id: UUID, state: str, actual: int, at: datetime
    ) -> None:
        result = await self._session.execute(
            _stmt(
                """
                UPDATE business.wallet_reservations
                SET state = :state, actual_paise = :actual, resolved_at = :at
                WHERE tenant_id = :tenant AND reservation_id = :reservation
                  AND state IN ('RESERVED', 'UNKNOWN')
                """,
                "at",
            ),
            {
                "state": state,
                "actual": actual,
                "at": at,
                "tenant": str(tenant_id),
                "reservation": str(reservation_id),
            },
        )
        if result.rowcount != 1:
            raise WalletError("WALLET_IDEMPOTENCY_CONFLICT", "reservation already resolved")

    def _reservation_receipt(
        self, row: Mapping[str, Any], *, replayed: bool
    ) -> WalletReservationReceipt:
        reserved = int(row["reserved_paise"])
        actual = int(row["actual_paise"]) if row["actual_paise"] is not None else None
        overrun = max(0, actual - reserved) if actual is not None else 0
        return WalletReservationReceipt(
            reservation_id=UUID(str(row["reservation_id"])),
            account_id=UUID(str(row["account_id"])),
            lot_id=UUID(str(row["lot_id"])),
            component_id=row["component_id"],
            state=row["state"],
            reserved_paise=reserved,
            actual_paise=actual,
            pinned_account_class=row["pinned_account_class"],
            pinned_versions=as_json_object(row["pinned_versions"]),
            overrun_paise=overrun,
            fenced=overrun > self._tolerance,
            replayed=replayed,
        )
