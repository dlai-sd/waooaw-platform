# Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C4-03
# Constitutional basis: C-059, C-088, C-089, C-063
"""Mirror of the component allowance tables into the Wallet (WC-136 C4-03).

``WalletMirror.sync_reservation`` brings the wallet in line with one allowance reservation: the
SUBSCRIPTION or TRIAL account of the relationship (chosen by ``authority_kind``) gets a lot that
represents the allocation, a reservation held for the allowance reservation, and the settlement
or release that the allowance row records. The wallet reservation id is the allowance reservation
id, so every operation is idempotent and a replay writes nothing new. The mirror runs in the
caller's session, hence in the same database transaction as the allowance write, and never commits.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final
from uuid import NAMESPACE_URL, UUID, uuid5

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from wallet.entity_models import (
    ReservationIdentity,
    WalletAccount,
    WalletError,
    as_utc,
)
from wallet.ledger import WalletLedger

WALLET_AUTHORITIES: Final = ("LEGACY", "SHADOW", "WALLET")
ALLOCATION_LOT_PREFIX: Final = "allocation:"
TRIAL_LOT_PREFIX: Final = "trial:"

_RESERVATION_SQL = text(
    """
    SELECT r.reservation_id, r.customer_id, r.relationship_id, r.allocation_id, r.component_id,
           r.professional_type, r.professional_version, r.invocation_id, r.owner_evidence_id,
           r.rate_version, r.marked_up_unit_cost_paise, r.reserved_marked_up_paise,
           r.actual_marked_up_paise, r.state, r.settlement_evidence_id, r.non_dispatch_evidence_id,
           al.granted_units, al.period_start, al.period_end, al.authority_evidence_id,
           au.authority_kind
    FROM business.offering_component_reservations r
    JOIN business.offering_component_allocations al
      ON al.tenant_id = r.tenant_id AND al.allocation_id = r.allocation_id
    JOIN business.relationship_commercial_authorities au
      ON au.tenant_id = r.tenant_id AND au.relationship_id = r.relationship_id
    WHERE r.tenant_id = :tenant AND r.reservation_id = :reservation
    """
)
_LOT_BY_REF_SQL = text(
    """
    SELECT lot_id FROM business.wallet_lots
    WHERE tenant_id = :tenant AND account_id = :account AND source_ref = :source_ref
    LIMIT 1
    """
)
_TRIAL_GRANT_LOT_SQL = text(
    """
    SELECT lot_id FROM business.wallet_lots
    WHERE tenant_id = :tenant AND account_id = :account
      AND source_kind = 'TRIAL_GRANT' AND source_ref LIKE :prefix
    LIMIT 1
    """
)


def wallet_authority(settings: object | None = None) -> str:
    """The configured convergence mode; anything unreadable is LEGACY, which writes no wallet rows."""
    if settings is None:
        from config import settings as loaded

        settings = loaded
    value = getattr(settings, "WALLET_AUTHORITY", "LEGACY")
    return value if isinstance(value, str) and value in WALLET_AUTHORITIES else "LEGACY"


def wallet_overrun_tolerance(settings: object | None = None) -> int:
    if settings is None:
        from config import settings as loaded

        settings = loaded
    value = getattr(settings, "WALLET_OVERRUN_TOLERANCE_PAISE", 0)
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else 0


@dataclass(frozen=True)
class MirrorOutcome:
    reservation_id: UUID
    skipped: bool
    account_id: UUID | None = None
    wallet_state: str | None = None
    detail: str | None = None


class WalletMirror:
    def __init__(self, session: AsyncSession, *, ledger: WalletLedger | None = None) -> None:
        self._session = session
        self._ledger = ledger or WalletLedger(session)

    @property
    def ledger(self) -> WalletLedger:
        return self._ledger

    async def sync_reservation(self, tenant_id: UUID, reservation_id: UUID) -> MirrorOutcome:
        """Write the wallet operations that correspond to the current state of the allowance row."""
        row = (
            await self._session.execute(
                _RESERVATION_SQL, {"tenant": str(tenant_id), "reservation": str(reservation_id)}
            )
        ).mappings().one_or_none()
        if row is None:
            raise WalletError("WALLET_RESERVATION_UNKNOWN", "allowance reservation")
        reserved = int(row["reserved_marked_up_paise"])
        if reserved <= 0:
            # Nothing is held for a zero-priced component; the wallet cannot represent a zero hold.
            return MirrorOutcome(reservation_id, True, detail="ZERO_PRICED")

        account = await self._account(tenant_id, row)
        await self._ensure_allocation_lot(tenant_id, account, row)
        period_end = as_utc(row["period_end"])
        pinned = {
            "allocation_id": str(row["allocation_id"]),
            "authority_kind": row["authority_kind"],
            "professional_type": row["professional_type"],
            "professional_version": row["professional_version"],
            "rate_version": row["rate_version"],
        }
        receipt = await self._ledger.reserve(
            account,
            row["component_id"],
            reserved,
            period_end,
            ReservationIdentity(
                pinned_versions=pinned,
                invocation_id=UUID(str(row["invocation_id"])),
                evidence_id=UUID(str(row["owner_evidence_id"])),
            ),
            reservation_id,
        )
        if row["state"] == "SETTLED":
            actual = int(row["actual_marked_up_paise"] or 0)
            evidence = UUID(str(row["settlement_evidence_id"]))
            if actual > 0:
                receipt = await self._ledger.settle(tenant_id, reservation_id, actual, evidence)
            else:
                receipt = await self._ledger.release(tenant_id, reservation_id, evidence)
        elif row["state"] == "RELEASED":
            receipt = await self._ledger.release(
                tenant_id, reservation_id, UUID(str(row["non_dispatch_evidence_id"]))
            )
        return MirrorOutcome(
            reservation_id, False, account_id=receipt.account_id, wallet_state=receipt.state
        )

    async def _account(self, tenant_id: UUID, row: object) -> WalletAccount:
        relationship_id = UUID(str(row["relationship_id"]))
        if row["authority_kind"] == "ACCEPTED_OFFERING":
            return await self._ledger.open_account(
                tenant_id,
                "SUBSCRIPTION",
                owner_ref=UUID(str(row["customer_id"])),
                relationship_id=relationship_id,
            )
        if row["authority_kind"] == "TRIAL":
            return await self._ledger.open_account(
                tenant_id,
                "TRIAL",
                relationship_id=relationship_id,
                agent_type=row["professional_type"],
                agent_version=row["professional_version"],
            )
        raise WalletError("WALLET_ACCOUNT_INVALID", "authority_kind")

    async def _ensure_allocation_lot(
        self, tenant_id: UUID, account: WalletAccount, row: object
    ) -> None:
        """Credit the allocation once; a later rate change never rewrites or duplicates the lot."""
        paise = int(row["granted_units"]) * int(row["marked_up_unit_cost_paise"])
        if paise <= 0:
            return
        source_ref = f"{ALLOCATION_LOT_PREFIX}{row['allocation_id']}"
        keys = {"tenant": str(tenant_id), "account": str(account.account_id)}
        existing = await self._session.execute(_LOT_BY_REF_SQL, {**keys, "source_ref": source_ref})
        if existing.first() is not None:
            return
        is_trial = account.account_class == "TRIAL"
        if is_trial:
            # A trial grant credited at trial start already funds the account; do not double it.
            granted = await self._session.execute(
                _TRIAL_GRANT_LOT_SQL, {**keys, "prefix": f"{TRIAL_LOT_PREFIX}%"}
            )
            if granted.first() is not None:
                return
        await self._ledger.credit(
            account,
            "GRANT" if is_trial else "PERIOD_CREDIT",
            paise,
            as_utc(row["period_start"]),
            as_utc(row["period_end"]),
            source_ref,
            {"allocation_id": str(row["allocation_id"]), "authority_kind": row["authority_kind"]},
            uuid5(NAMESPACE_URL, f"wbe-wallet-mirror:{tenant_id}:{row['allocation_id']}"),
            evidence_id=UUID(str(row["authority_evidence_id"])),
        )
