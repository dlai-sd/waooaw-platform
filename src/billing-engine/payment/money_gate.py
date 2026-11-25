# Implements: work-contracts/WC-172-safe-to-charge-real-customers.md WC172-R010, WC172-R011
# Constitutional basis: C-007, C-023, C-059, C-066, C-088
"""The real-money gate and the guard every new charge passes.

``real_money_enabled`` is off everywhere. It can be turned on only in production, in LIVE mode, by the Founder's
step-up action, with a reason; every change is recorded with who and when in an append-only audit, and turning it off
needs no step-up so it is instantly reversible. A new charge is refused while a live gate is closed and, in every
environment, while an unresolved money discrepancy exists. The caller owns the transaction.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Final
from uuid import uuid4

from sqlalchemy import DateTime, bindparam, text
from sqlalchemy.ext.asyncio import AsyncSession

from wallet.entity_models import as_utc

_TS = DateTime(timezone=True)
GATE_KEY: Final = "REAL_MONEY"


class MoneyGateError(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class ChargeRefused(RuntimeError):
    """A new charge may not be created now; ``code`` says why."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class MoneyGateState:
    environment: str
    payment_mode: str
    enabled: bool
    changed_by: str | None
    changed_at: datetime | None
    reason: str | None

    def as_public(self) -> dict[str, object]:
        return {
            "environment": self.environment,
            "paymentMode": self.payment_mode,
            "realMoneyEnabled": self.enabled,
            "changedBy": self.changed_by,
            "changedAt": None if self.changed_at is None else as_utc(self.changed_at).isoformat().replace("+00:00", "Z"),
            "reason": self.reason,
        }


class MoneyGate:
    def __init__(
        self,
        session: AsyncSession,
        environment: str,
        payment_mode: str,
        *,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self._session = session
        self._environment = environment
        self._mode = payment_mode
        self._now = now or (lambda: datetime.now(timezone.utc))

    async def state(self) -> MoneyGateState:
        row = (
            await self._session.execute(
                text("SELECT enabled, changed_by, changed_at, reason FROM business.money_gate WHERE gate_key = :key"),
                {"key": GATE_KEY},
            )
        ).first()
        if row is None:
            return MoneyGateState(self._environment, self._mode, False, None, None, None)
        return MoneyGateState(
            self._environment, self._mode, bool(row[0]), str(row[1]), as_utc(row[2]), str(row[3])
        )

    async def set(self, enabled: bool, actor: str, step_up: bool, reason: str) -> MoneyGateState:
        reason = reason.strip()
        if not reason or not actor:
            raise MoneyGateError("MONEY_GATE_REASON_REQUIRED")
        if enabled:
            if self._environment != "production" or self._mode != "LIVE":
                raise MoneyGateError("MONEY_GATE_NOT_PRODUCTION")
            if not step_up:
                raise MoneyGateError("MONEY_GATE_STEP_UP_REQUIRED")
        now = as_utc(self._now())
        await self._session.execute(
            text(
                """
                INSERT INTO business.money_gate (gate_key, enabled, changed_by, changed_at, reason)
                VALUES (:key, :enabled, :actor, :now, :reason)
                ON CONFLICT (gate_key) DO UPDATE SET enabled = excluded.enabled, changed_by = excluded.changed_by,
                    changed_at = excluded.changed_at, reason = excluded.reason
                """
            ).bindparams(bindparam("now", type_=_TS)),
            {"key": GATE_KEY, "enabled": enabled, "actor": actor, "now": now, "reason": reason},
        )
        await self._session.execute(
            text(
                """
                INSERT INTO business.money_gate_audit
                (audit_id, enabled, environment, changed_by, step_up, reason, changed_at)
                VALUES (:id, :enabled, :environment, :actor, :step_up, :reason, :now)
                """
            ).bindparams(bindparam("now", type_=_TS)),
            {
                "id": str(uuid4()), "enabled": enabled, "environment": self._environment, "actor": actor,
                "step_up": step_up, "reason": reason, "now": now,
            },
        )
        return await self.state()

    async def require_charge_allowed(self) -> None:
        """Refuse a new charge: a live gate that is closed, a production service not in LIVE mode, or an open
        discrepancy in the books."""
        if (self._environment == "production") != (self._mode == "LIVE"):
            raise ChargeRefused("MONEY_MODE_INVALID")
        if self._mode == "LIVE" and not (await self.state()).enabled:
            raise ChargeRefused("REAL_MONEY_GATE_CLOSED")
        blocked = (
            await self._session.execute(text("SELECT 1 FROM business.money_discrepancies WHERE resolved_at IS NULL LIMIT 1"))
        ).first()
        if blocked is not None:
            raise ChargeRefused("MONEY_RECONCILIATION_BLOCKED")
