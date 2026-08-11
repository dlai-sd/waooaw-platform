# Implements: adr/ADR-022-payment-processing-razorpay-india.md §Amendment 1.2
# constitutional_basis: C-059, C-023 (Evidence First — payment is evidence event)
"""WebhookHandler — processes Razorpay payment.captured event.

On payment.captured:
  1. Verify HMAC signature (skip in demo/UAT bypass flow)
  2. Idempotency check — payment_intents table prevents double-activation
  3. Call wallet.activate_subscription() — mode flip precedes subscription creation (S-09)
  4. Mark payment_intent as ACTIVATED
"""
from __future__ import annotations

import logging
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from config import Settings
from payment.models import PaymentCapturedEvent, PaymentCaptureResult
from payment.razorpay_client import RazorpayClient
from wallet.models import SubscriptionActivationResult
from wallet.service import WalletService

logger = logging.getLogger(__name__)


class WebhookHandler:
    """Handles Razorpay webhook events with idempotency and signature verification."""

    def __init__(
        self,
        db: AsyncSession,
        wallet_service: WalletService,
        razorpay_client: RazorpayClient | None = None,
        settings: Settings | None = None,
    ) -> None:
        self._db = db
        self._wallet = wallet_service
        self._settings: Settings = settings or Settings()
        self._razorpay: RazorpayClient = razorpay_client or RazorpayClient(self._settings)

    async def handle_payment_captured(
        self,
        event: PaymentCapturedEvent,
        is_bypass: bool = False,
    ) -> SubscriptionActivationResult | PaymentCaptureResult:
        """Process payment.captured — idempotent, HMAC-verified, atomically activates wallet.

        Bypass orders (demo/UAT coupons) skip signature verification. FA-029.
        """
        if not is_bypass:
            valid = self._razorpay.verify_payment_signature(
                order_id=event.razorpay_order_id,
                payment_id=event.razorpay_payment_id,
                signature=event.razorpay_signature,
            )
            if not valid:
                logger.warning(
                    "Invalid Razorpay signature: order_id=%s payment_id=%s",
                    event.razorpay_order_id, event.razorpay_payment_id,
                )
                raise HTTPException(status_code=400, detail={"code": "INVALID_SIGNATURE"})

        if event.relationship_id is not None:
            if any(value is None for value in (
                event.accepted_contract_id,
                event.contract_acceptance_id,
                event.payment_consent_evidence_id,
                event.payment_evidence_id,
            )):
                raise HTTPException(status_code=400, detail={"code": "INCOMPLETE_CONTRACT_LINK"})
            await self._db.execute(
                text(
                    "INSERT INTO payment_intents "
                    "(razorpay_order_id, razorpay_payment_id, customer_id, status, relationship_id, "
                    "accepted_contract_id, contract_acceptance_id, payment_consent_evidence_id, "
                    "payment_evidence_id, agent_type, bundle_tier) "
                    "VALUES (:oid, :pid, :cid, 'CAPTURED', :rid, :contract_id, :acceptance_id, "
                    ":consent_id, :evidence_id, :agent_type, :bundle_tier) "
                    "ON CONFLICT (razorpay_payment_id) DO NOTHING"
                ).bindparams(
                    oid=event.razorpay_order_id, pid=event.razorpay_payment_id,
                    cid=str(event.customer_id), rid=str(event.relationship_id),
                    contract_id=str(event.accepted_contract_id),
                    acceptance_id=str(event.contract_acceptance_id),
                    consent_id=str(event.payment_consent_evidence_id),
                    evidence_id=str(event.payment_evidence_id), agent_type=event.agent_type,
                    bundle_tier=event.bundle_tier,
                )
            )
            await self._db.commit()
            stored = (await self._db.execute(text(
                "SELECT relationship_id, accepted_contract_id, contract_acceptance_id, "
                "payment_consent_evidence_id, payment_evidence_id, status FROM payment_intents "
                "WHERE razorpay_payment_id = :pid"
            ).bindparams(pid=event.razorpay_payment_id))).fetchone()
            expected = tuple(str(value) for value in (
                event.relationship_id, event.accepted_contract_id, event.contract_acceptance_id,
                event.payment_consent_evidence_id,
            ))
            if stored is None or tuple(stored[index] for index in range(4)) != expected:
                raise HTTPException(status_code=409, detail={"code": "PAYMENT_CAPTURE_CONFLICT"})
            return PaymentCaptureResult(
                payment_reference=event.razorpay_payment_id,
                payment_evidence_id=UUID(str(stored.payment_evidence_id)),
                status=stored.status,
            )

        # Idempotency: reject if already processed
        existing = await self._db.execute(
            text(
                "SELECT razorpay_payment_id, status FROM payment_intents "
                "WHERE razorpay_payment_id = :pid LIMIT 1"
            ).bindparams(pid=event.razorpay_payment_id)
        )
        row = existing.fetchone()
        if row is not None and row.status == "ACTIVATED":
            logger.info("Idempotent: payment already activated. payment_id=%s", event.razorpay_payment_id)
            # Return existing result without error — webhook replay handled gracefully
            result_row = await self._db.execute(
                text(
                    "SELECT subscription_id AS id FROM paid_subscriptions WHERE organisation_id = :cid "
                    "AND razorpay_payment_id = :pid LIMIT 1"
                ).bindparams(cid=str(event.customer_id), pid=event.razorpay_payment_id)
            )
            sub_row = result_row.fetchone()
            return SubscriptionActivationResult(
                subscription_id=sub_row.id if sub_row else UUID(int=0),
                customer_id=event.customer_id,
                agent_type=event.agent_type,
                bundle_tier=event.bundle_tier,
                activated_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
            )

        # Record payment_intent as IN_PROGRESS before any state mutation (C-023)
        await self._db.execute(
            text(
                "INSERT INTO payment_intents "
                "(razorpay_order_id, razorpay_payment_id, customer_id, status) "
                "VALUES (:oid, :pid, :cid, 'IN_PROGRESS') "
                "ON CONFLICT (razorpay_payment_id) DO NOTHING"
            ).bindparams(
                oid=event.razorpay_order_id,
                pid=event.razorpay_payment_id,
                cid=str(event.customer_id),
            )
        )
        await self._db.commit()

        # Activate subscription — mode flip happens BEFORE subscription insert (S-09)
        result = await self._wallet.activate_subscription(
            customer_id=event.customer_id,
            agent_type=event.agent_type,
            bundle_tier=event.bundle_tier,
            razorpay_order_id=event.razorpay_order_id,
            razorpay_payment_id=event.razorpay_payment_id,
        )

        # Mark payment_intent as ACTIVATED
        await self._db.execute(
            text(
                "UPDATE payment_intents SET status = 'ACTIVATED' "
                "WHERE razorpay_payment_id = :pid"
            ).bindparams(pid=event.razorpay_payment_id)
        )
        await self._db.commit()

        logger.info(
            "payment.captured processed: order_id=%s payment_id=%s customer_id=%s",
            event.razorpay_order_id, event.razorpay_payment_id, event.customer_id,
        )
        return result
