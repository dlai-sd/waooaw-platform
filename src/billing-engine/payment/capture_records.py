# Implements: work-contracts/WC-176-customer-journeys-registration-trial-hire-and-pages.md WC176-R015
# Constitutional basis: C-023, C-059, C-063
"""Durable record of what Razorpay told us, so a captured payment is never lost.

Every verified provider event is recorded once (``razorpay_webhook_events``) and every captured payment is recorded
before anything is done with it (``razorpay_captures``). A replay of an event is acknowledged without being repeated;
a capture whose completion failed stays RECEIVED until the reconciliation completes it or marks it REFUND_DUE.
Nothing here is ever deleted.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping
from datetime import datetime, timezone
from typing import Any, Final

from sqlalchemy import DateTime, bindparam, text
from sqlalchemy.sql.elements import TextClause
from sqlalchemy.ext.asyncio import AsyncSession

from wallet.entity_models import as_utc

_TS = DateTime(timezone=True)

RECEIVED: Final = "RECEIVED"
COMPLETED: Final = "COMPLETED"
REFUND_DUE: Final = "REFUND_DUE"
REFUNDED: Final = "REFUNDED"
SOURCE_WEBHOOK: Final = "WEBHOOK"
SOURCE_RECONCILIATION: Final = "RECONCILIATION"


def _stmt(sql: str, *datetime_params: str) -> TextClause:
    statement = text(sql)
    if datetime_params:
        statement = statement.bindparams(*[bindparam(name, type_=_TS) for name in datetime_params])
    return statement


def event_id_of(header_event_id: str, body: bytes) -> str:
    """The provider's event id, or a digest of the signed body when the header is absent."""
    supplied = header_event_id.strip()
    return supplied[:200] if supplied else hashlib.sha256(body).hexdigest()


def notes_of(payment: Mapping[str, Any]) -> dict[str, Any]:
    """Razorpay sends an empty list instead of an empty object when a payment has no notes."""
    notes = payment.get("notes")
    return dict(notes) if isinstance(notes, Mapping) else {}


class CaptureLedger:
    def __init__(self, session: AsyncSession, *, now: Callable[[], datetime] | None = None) -> None:
        self._session = session
        self._now = now or (lambda: datetime.now(timezone.utc))

    async def begin_event(self, event_id: str, event_type: str, payment_id: str | None, body: bytes) -> bool:
        """Record a verified event. False when the same event was already fully processed (a replay)."""
        await self._session.execute(
            _stmt(
                "INSERT INTO razorpay_webhook_events (event_id, event_type, payment_id, payload_digest, received_at) "
                "VALUES (:id, :type, :payment, :digest, :now) ON CONFLICT (event_id) DO NOTHING",
                "now",
            ),
            {
                "id": event_id,
                "type": event_type[:100],
                "payment": payment_id or None,
                "digest": hashlib.sha256(body).hexdigest(),
                "now": as_utc(self._now()),
            },
        )
        row = (
            await self._session.execute(
                text("SELECT processed_at FROM razorpay_webhook_events WHERE event_id = :id"), {"id": event_id}
            )
        ).first()
        await self._session.commit()
        return row is None or row[0] is None

    async def finish_event(self, event_id: str, outcome: str) -> None:
        await self._session.execute(
            _stmt(
                "UPDATE razorpay_webhook_events SET processed_at = :now, outcome = :outcome "
                "WHERE event_id = :id AND processed_at IS NULL",
                "now",
            ),
            {"id": event_id, "outcome": outcome[:100], "now": as_utc(self._now())},
        )
        await self._session.commit()

    async def record_capture(self, payment: Mapping[str, Any], source: str) -> bool:
        """Durably record a captured payment. False when it was already recorded."""
        amount = payment.get("amount")
        if not isinstance(amount, int) or isinstance(amount, bool) or amount <= 0:
            return False
        result = await self._session.execute(
            _stmt(
                "INSERT INTO razorpay_captures (payment_id, order_id, amount_paise, currency, notes, source, status, "
                "first_seen_at) VALUES (:id, :order, :amount, 'INR', :notes, :source, 'RECEIVED', :now) "
                "ON CONFLICT (payment_id) DO NOTHING",
                "now",
            ),
            {
                "id": str(payment["id"]),
                "order": str(payment.get("order_id") or ""),
                "amount": amount,
                "notes": json.dumps(notes_of(payment), sort_keys=True),
                "source": source,
                "now": as_utc(self._now()),
            },
        )
        await self._session.commit()
        return bool(result.rowcount)

    async def mark_completed(self, payment_id: str) -> None:
        await self._session.execute(
            _stmt(
                "UPDATE razorpay_captures SET status = 'COMPLETED', completed_at = :now, last_error = NULL "
                "WHERE payment_id = :id AND status = 'RECEIVED'",
                "now",
            ),
            {"id": payment_id, "now": as_utc(self._now())},
        )
        await self._session.commit()

    async def mark_failed(self, payment_id: str, code: str) -> None:
        await self._session.rollback()
        await self._session.execute(
            text(
                "UPDATE razorpay_captures SET attempts = attempts + 1, last_error = :code "
                "WHERE payment_id = :id AND status = 'RECEIVED'"
            ),
            {"id": payment_id, "code": code[:200]},
        )
        await self._session.commit()

    async def mark_refund_due(self, payment_id: str, reason: str) -> None:
        await self._session.execute(
            _stmt(
                "UPDATE razorpay_captures SET status = 'REFUND_DUE', refund_due_at = :now, last_error = :reason "
                "WHERE payment_id = :id AND status IN ('RECEIVED', 'COMPLETED')",
                "now",
            ),
            {"id": payment_id, "reason": reason[:200], "now": as_utc(self._now())},
        )
        await self._session.commit()

    async def mark_refunded(self, payment_id: str, refund_id: str, refund_paise: int) -> bool:
        """A full refund closes the capture; a partial refund leaves it as it was."""
        result = await self._session.execute(
            text(
                "UPDATE razorpay_captures SET status = 'REFUNDED', refund_reference = :refund "
                "WHERE payment_id = :id AND amount_paise = :amount AND status <> 'REFUNDED'"
            ),
            {"id": payment_id, "refund": refund_id[:200], "amount": refund_paise},
        )
        await self._session.commit()
        return bool(result.rowcount)

    async def captures_with_status(self, status: str, limit: int) -> list[dict[str, Any]]:
        rows = (
            (
                await self._session.execute(
                    text(
                        "SELECT payment_id, order_id, amount_paise, notes, first_seen_at, completed_at "
                        "FROM razorpay_captures WHERE status = :status ORDER BY first_seen_at LIMIT :limit"
                    ),
                    {"status": status, "limit": limit},
                )
            )
            .mappings()
            .all()
        )
        return [
            {
                "id": str(row["payment_id"]),
                "order_id": str(row["order_id"]),
                "amount": int(row["amount_paise"]),
                "notes": json.loads(row["notes"]) if isinstance(row["notes"], (str, bytes)) else dict(row["notes"] or {}),
                "first_seen_at": as_utc(row["first_seen_at"]),
                "completed_at": None if row["completed_at"] is None else as_utc(row["completed_at"]),
            }
            for row in rows
        ]

    async def known(self, payment_id: str) -> bool:
        row = (
            await self._session.execute(text("SELECT 1 FROM razorpay_captures WHERE payment_id = :id"), {"id": payment_id})
        ).first()
        return row is not None
