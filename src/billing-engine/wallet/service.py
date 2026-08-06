# Implements: <spec-path> §<section>
# constitutional_basis: C-059 (Implementation Traceability)
from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import date, datetime, timezone
from uuid import UUID

import redis.asyncio as aioredis
from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from config import Settings
from wallet.models import (
    BucketBalance,
    BucketNotFoundError,
    BucketReservation,
    DuplicateReservationError,
    InsufficientBalanceError,
    RenewalResult,
    SubscriptionActivationResult,
)

logger = logging.getLogger(__name__)

settings: Settings = Settings()

_BILLING_HALTED_KEY: str = "wbe:billing_halted"


class WalletService:
    """
    One wallet, multiple bucket architecture per customer.
    Constitutional: C-091 (Thread Catalog), C-088 (Billing Profile gate).
    SLA: get_bucket_balance <=50ms p99 (Redis cache - ADR-034).
    """

    def __init__(
        self,
        db: AsyncSession,
        redis_client: aioredis.Redis,
    ) -> None:
        self._db: AsyncSession = db
        self._redis: aioredis.Redis = redis_client

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _check_billing_halted(self) -> None:
        """Raise HTTP 503 if the billing integrity halt flag is set in Redis."""
        try:
            halted: str | None = await self._redis.get(_BILLING_HALTED_KEY)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.error(
                "Redis check for billing halt failed - failing open for safety",
                exc_info=True,
                extra={"context": "check_billing_halted"},
            )
            raise HTTPException(
                status_code=503,
                detail={
                    "code": "BILLING_INTEGRITY_HALT",
                    "message": (
                        "Billing suspended pending reconciliation audit"
                    ),
                },
            ) from exc
        if halted is not None:
            raise HTTPException(
                status_code=503,
                detail={
                    "code": "BILLING_INTEGRITY_HALT",
                    "message": (
                        "Billing suspended pending reconciliation audit"
                    ),
                },
            )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def get_bucket_balance(
        self,
        customer_id: UUID,
        thread_type: str,
    ) -> BucketBalance:
        """Return the balance for a specific bucket. SLA: <=50ms p99."""
        result = await self._db.execute(
            text(
                """
                SELECT wb.id, wb.balance_paise, wb.thread_type,
                       wb.employment_contract_id
                FROM wallet_buckets wb
                JOIN employment_contracts ec ON ec.id = wb.employment_contract_id
                WHERE ec.customer_id = :customer_id
                  AND wb.thread_type = :thread_type
                  AND wb.is_active = TRUE
                LIMIT 1
                """
            ).bindparams(
                customer_id=str(customer_id),
                thread_type=thread_type,
            )
        )
        row = result.fetchone()
        if row is None:
            raise BucketNotFoundError(
                f"Bucket not found: customer={customer_id} thread_type={thread_type}"
            )
        return BucketBalance(
            bucket_id=row.id,
            customer_id=customer_id,
            thread_type=row.thread_type,
            balance_paise=row.balance_paise,
        )

    async def reserve(
        self,
        customer_id: UUID,
        thread_type: str,
        amount_paise: int,
        idempotency_key: UUID,
        redis_client: aioredis.Redis | None = None,
    ) -> BucketReservation:
        """
        Reserve funds from a wallet bucket.

        Checks wbe:billing_halted before any DB write (C-004).
        Raises InsufficientBalanceError -> HTTP 402.
        Raises DuplicateReservationError -> HTTP 409.

        Args:
            customer_id: UUID of the customer.
            thread_type: Type of thread (e.g., 'DMA', 'INFERENCE').
            amount_paise: Amount to reserve in paise.
            idempotency_key: UUID for idempotent reservation tracking.
            redis_client: Optional injected Redis client; defaults to self._redis.

        Returns:
            BucketReservation with reservation details.

        Raises:
            HTTPException(503): If billing_halted flag is set in Redis.
            DuplicateReservationError: If reservation already exists for this key.
            BucketNotFoundError: If bucket does not exist.
            InsufficientBalanceError: If balance < amount_paise.
        """
        # WC030-01b: use injected redis_client if provided, else fall back to self._redis
        effective_redis: aioredis.Redis = (
            redis_client if redis_client is not None else self._redis
        )

        # C-004: Check billing halt BEFORE any DB write
        try:
            halted: str | None = await effective_redis.get(_BILLING_HALTED_KEY)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.error(
                "Redis billing-halt check failed in reserve - blocking as safe default",
                exc_info=True,
                extra={"context": "reserve_billing_halt_check"},
            )
            raise HTTPException(
                status_code=503,
                detail={
                    "code": "BILLING_INTEGRITY_HALT",
                    "message": (
                        "Billing suspended pending reconciliation audit"
                    ),
                },
            ) from exc

        if halted is not None:
            raise HTTPException(
                status_code=503,
                detail={
                    "code": "BILLING_INTEGRITY_HALT",
                    "message": (
                        "Billing suspended pending reconciliation audit"
                    ),
                },
            )

        # Idempotency: check for existing reservation with this key
        existing = await self._db.execute(
            text(
                """
                SELECT br.id, br.reserved_paise, br.bucket_id, br.created_at
                FROM bucket_reservations br
                WHERE br.idempotency_key = :idem_key
                LIMIT 1
                """
            ).bindparams(idem_key=str(idempotency_key))
        )
        existing_row = existing.fetchone()
        if existing_row is not None:
            raise DuplicateReservationError(
                f"Reservation already exists for idempotency_key={idempotency_key}"
            )

        # Fetch the bucket with balance check
        bucket_result = await self._db.execute(
            text(
                """
                SELECT wb.id, wb.balance_paise, wb.employment_contract_id
                FROM wallet_buckets wb
                JOIN employment_contracts ec ON ec.id = wb.employment_contract_id
                WHERE ec.customer_id = :customer_id
                  AND wb.thread_type = :thread_type
                  AND wb.is_active = TRUE
                LIMIT 1
                """
            ).bindparams(
                customer_id=str(customer_id),
                thread_type=thread_type,
            )
        )
        bucket_row = bucket_result.fetchone()
        if bucket_row is None:
            raise BucketNotFoundError(
                f"Bucket not found: customer={customer_id} thread_type={thread_type}"
            )

        if bucket_row.balance_paise < amount_paise:
            raise InsufficientBalanceError(
                f"Insufficient balance: available={bucket_row.balance_paise} "
                f"requested={amount_paise}"
            )

        reservation_id: UUID = uuid.uuid4()
        now_utc: datetime = datetime.now(timezone.utc)

        # Deduct balance and insert reservation atomically
        await self._db.execute(
            text(
                """
                UPDATE wallet_buckets
                SET balance_paise = balance_paise - :amount
                WHERE id = :bucket_id
                """
            ).bindparams(amount=amount_paise, bucket_id=str(bucket_row.id))
        )

        await self._db.execute(
            text(
                """
                INSERT INTO bucket_reservations
                    (id, bucket_id, reserved_paise, idempotency_key,
                     consumed, created_at)
                VALUES
                    (:res_id, :bucket_id, :amount, :idem_key,
                     FALSE, :created_at)
                """
            ).bindparams(
                res_id=str(reservation_id),
                bucket_id=str(bucket_row.id),
                amount=amount_paise,
                idem_key=str(idempotency_key),
                created_at=now_utc,
            )
        )

        await self._db.commit()

        logger.info(
            "Reservation created: reservation_id=%s bucket_id=%s amount_paise=%s",
            reservation_id,
            bucket_row.id,
            amount_paise,
        )

        return BucketReservation(
            reservation_id=reservation_id,
            bucket_id=bucket_row.id,
            customer_id=customer_id,
            thread_type=thread_type,
            reserved_paise=amount_paise,
            idempotency_key=idempotency_key,
            created_at=now_utc,
        )

    async def release(
        self,
        reservation_id: UUID,
        consumed: bool,
    ) -> None:
        """
        Release a reservation. If consumed=False, refund the balance.
        If consumed=True, mark as consumed and record consumed_at.

        Args:
            reservation_id: UUID of the reservation to release.
            consumed: If True, mark consumed; if False, refund balance.

        Raises:
            ValueError: If reservation not found.
        """
        res_result = await self._db.execute(
            text(
                """
                SELECT br.id, br.reserved_paise, br.bucket_id, br.consumed
                FROM bucket_reservations br
                WHERE br.id = :res_id
                LIMIT 1
                """
            ).bindparams(res_id=str(reservation_id))
        )
        res_row = res_result.fetchone()
        if res_row is None:
            raise ValueError(f"Reservation not found: {reservation_id}")

        now_utc: datetime = datetime.now(timezone.utc)

        if consumed:
            await self._db.execute(
                text(
                    """
                    UPDATE bucket_reservations
                    SET consumed = TRUE, consumed_at = :now
                    WHERE id = :res_id
                    """
                ).bindparams(now=now_utc, res_id=str(reservation_id))
            )
        else:
            # Refund the balance
            await self._db.execute(
                text(
                    """
                    UPDATE wallet_buckets
                    SET balance_paise = balance_paise + :amount
                    WHERE id = :bucket_id
                    """
                ).bindparams(
                    amount=res_row.reserved_paise,
                    bucket_id=str(res_row.bucket_id),
                )
            )
            await self._db.execute(
                text(
                    """
                    DELETE FROM bucket_reservations
                    WHERE id = :res_id
                    """
                ).bindparams(res_id=str(reservation_id))
            )

        await self._db.commit()

        logger.info(
            "Reservation released: reservation_id=%s consumed=%s",
            reservation_id,
            consumed,
        )

    async def activate_subscription(
        self,
        customer_id: UUID,
        agent_type: str,
        bundle_tier: str,
        razorpay_order_id: str,
        razorpay_payment_id: str,
    ) -> SubscriptionActivationResult:
        """
        Activate a subscription for a customer.
        MUST check billing_profiles.status == FOUNDER_AUTHORIZED (C-088).
        MUST flip customer mode before subscription object creation.

        Args:
            customer_id: UUID of the customer.
            agent_type: Type of agent being subscribed to.
            bundle_tier: Subscription bundle tier.
            razorpay_order_id: Order ID from Razorpay.
            razorpay_payment_id: Payment ID from Razorpay.

        Returns:
            SubscriptionActivationResult with subscription details.

        Raises:
            HTTPException(403): If billing profile not founder-authorized.
        """
        # Check billing profile authorization
        bp_result = await self._db.execute(
            text(
                """
                SELECT bp.status, bp.customer_id
                FROM billing_profiles bp
                WHERE bp.customer_id = :customer_id
                LIMIT 1
                """
            ).bindparams(customer_id=str(customer_id))
        )
        bp_row = bp_result.fetchone()
        if bp_row is None or bp_row.status != "FOUNDER_AUTHORIZED":
            raise HTTPException(
                status_code=403,
                detail={
                    "code": "BILLING_PROFILE_NOT_AUTHORIZED",
                    "message": "Billing profile not founder-authorized",
                },
            )

        # Flip customer mode before subscription creation (race condition fix)
        await self._db.execute(
            text(
                """
                UPDATE customers
                SET mode = 'SUBSCRIBED'
                WHERE id = :customer_id
                """
            ).bindparams(customer_id=str(customer_id))
        )

        subscription_id: UUID = uuid.uuid4()
        now_utc: datetime = datetime.now(timezone.utc)

        await self._db.execute(
            text(
                """
                INSERT INTO subscriptions
                    (id, customer_id, agent_type, bundle_tier,
                     razorpay_order_id, razorpay_payment_id, activated_at)
                VALUES
                    (:sub_id, :customer_id, :agent_type, :bundle_tier,
                     :order_id, :payment_id, :activated_at)
                """
            ).bindparams(
                sub_id=str(subscription_id),
                customer_id=str(customer_id),
                agent_type=agent_type,
                bundle_tier=bundle_tier,
                order_id=razorpay_order_id,
                payment_id=razorpay_payment_id,
                activated_at=now_utc,
            )
        )

        await self._db.commit()

        logger.info(
            "Subscription activated: subscription_id=%s customer_id=%s agent_type=%s",
            subscription_id,
            customer_id,
            agent_type,
        )

        return SubscriptionActivationResult(
            subscription_id=subscription_id,
            customer_id=customer_id,
            agent_type=agent_type,
            bundle_tier=bundle_tier,
            activated_at=now_utc,
        )

    async def renew(
        self,
        customer_id: UUID,
        contract_id: UUID,
        new_period_start: date,
    ) -> RenewalResult:
        """
        Renew a subscription contract.
        MUST reject if plan price > agreed price without C-090 notice.

        Args:
            customer_id: UUID of the customer.
            contract_id: UUID of the employment contract to renew.
            new_period_start: Start date of the new renewal period.

        Returns:
            RenewalResult with renewal details.

        Raises:
            ValueError: If contract not found.
            HTTPException(422): If plan price > agreed price.
        """
        contract_result = await self._db.execute(
            text(
                """
                SELECT ec.id, ec.agreed_price_paise, ec.plan_price_paise,
                       ec.customer_id, ec.thread_type
                FROM employment_contracts ec
                WHERE ec.id = :contract_id
                  AND ec.customer_id = :customer_id
                LIMIT 1
                """
            ).bindparams(
                contract_id=str(contract_id),
                customer_id=str(customer_id),
            )
        )
        contract_row = contract_result.fetchone()
        if contract_row is None:
            raise ValueError(
                f"Contract not found: contract_id={contract_id} customer_id={customer_id}"
            )

        if contract_row.plan_price_paise > contract_row.agreed_price_paise:
            raise HTTPException(
                status_code=422,
                detail={
                    "code": "PRICE_INCREASE_WITHOUT_NOTICE",
                    "message": (
                        "Plan price exceeds agreed price - C-090 notice required"
                    ),
                },
            )

        now_utc: datetime = datetime.now(timezone.utc)

        await self._db.execute(
            text(
                """
                UPDATE employment_contracts
                SET period_start = :period_start,
                    renewed_at = :renewed_at
                WHERE id = :contract_id
                """
            ).bindparams(
                period_start=new_period_start,
                renewed_at=now_utc,
                contract_id=str(contract_id),
            )
        )

        await self._db.commit()

        logger.info(
            "Contract renewed: contract_id=%s customer_id=%s new_period_start=%s",
            contract_id,
            customer_id,
            new_period_start,
        )

        return RenewalResult(
            contract_id=contract_id,
            customer_id=customer_id,
            new_period_start=new_period_start,
            renewed_at=now_utc,
        )