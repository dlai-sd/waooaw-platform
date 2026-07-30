# Implements: architecture/reference/billing/wbe-component-spec.md full
# constitutional_basis: C-023, C-059, C-063, C-090
from __future__ import annotations

import asyncio
import json
import logging
from datetime import date, datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from wallet.exceptions import InsufficientFundsError
from wallet.models import BucketReservation, CustomerWallet, WalletBucket

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_CACHE_TTL_SECONDS = 30
_EVIDENCE_ACTION_RESERVE = "wallet.reserve"
_EVIDENCE_ACTION_RELEASE = "wallet.release"
_EVIDENCE_ACTION_ACTIVATE = "wallet.activate_subscription"
_EVIDENCE_ACTION_RENEW = "wallet.renew"


# ---------------------------------------------------------------------------
# WalletService
# ---------------------------------------------------------------------------


class WalletService:
    """
    Core wallet engine — get_balance, reserve, release, activate_subscription, renew.

    Constitutional obligations:
      C-088  — Billing profile gate before subscription activation.
      C-089  — Margin floor enforced at markup layer (not here), but reserve
               must check available_paise > 0.
      C-090  — Grandfather pricing on renew.
      C-038  — Pro-rata handled by caller; WalletService does not split periods.
      C-059  — Every mutation records evidence via ce_stub.
      C-063  — No PII in log statements (wallet_id / customer_id only, never name/email).
    """

    def __init__(
        self,
        db_session: AsyncSession,
        redis_client,          # redis.asyncio.Redis — ANN401 justified: redis typing varies
        ce_stub,               # gRPC stub (ConstitutionalEngineStub) — injected
    ) -> None:
        self._db = db_session
        self._redis = redis_client
        self._ce = ce_stub

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _bucket_cache_key(self, wallet_id: UUID, thread_type: str) -> str:
        return f"wbe:bucket:{wallet_id}:{thread_type}"

    def _wallet_cache_key(self, wallet_id: UUID) -> str:
        return f"wbe:wallet:{wallet_id}"

    async def _record_evidence(
        self,
        action: str,
        wallet_id: UUID,
        payload: dict,
    ) -> None:
        """Emit a C-059 evidence record via the CE gRPC stub."""
        try:
            evidence_payload = {
                "action": action,
                "wallet_id": str(wallet_id),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                **payload,
            }
            await self._ce.record_evidence(
                action=action,
                subject_id=str(wallet_id),
                payload=json.dumps(evidence_payload),
            )
        except asyncio.CancelledError:
            raise
        except (OSError, RuntimeError) as exc:
            # Evidence recording failure is logged but must not block the operation.
            # C-059: the failure itself is the evidence record.
            logger.error(
                "Evidence recording failed for action=%s wallet=%s",
                action,
                wallet_id,
                exc_info=True,
                extra={"context": {"action": action, "wallet_id": str(wallet_id)}},
            )
            _ = exc  # acknowledged

    # ------------------------------------------------------------------
    # get_bucket_balance  (SLA: ≤50ms p99 via Redis)
    # ------------------------------------------------------------------

    async def get_bucket_balance(
        self,
        wallet_id: UUID,
        thread_type: str,
    ) -> WalletBucket:
        """
        Return the WalletBucket for (wallet_id, thread_type).
        Attempts Redis cache first (30 s TTL); falls back to Postgres.
        Raises KeyError if the bucket does not exist.
        """
        cache_key = self._bucket_cache_key(wallet_id, thread_type)

        try:
            raw = await self._redis.get(cache_key)
            if raw is not None:
                data = json.loads(raw)
                # Reconstruct a lightweight bucket object from cached dict.
                bucket = WalletBucket(
                    id=UUID(data["id"]),
                    wallet_id=UUID(data["wallet_id"]),
                    thread_type=data["thread_type"],
                    available_paise=data["available_paise"],
                    reserved_paise=data["reserved_paise"],
                    updated_at=datetime.fromisoformat(data["updated_at"]),
                )
                logger.debug(
                    "bucket_balance cache_hit wallet=%s thread_type=%s",
                    wallet_id,
                    thread_type,
                )
                return bucket
        except asyncio.CancelledError:
            raise
        except (OSError, ValueError, KeyError) as exc:
            logger.warning(
                "Redis cache miss or decode error for wallet=%s thread_type=%s",
                wallet_id,
                thread_type,
                exc_info=True,
                extra={"context": {"wallet_id": str(wallet_id), "thread_type": thread_type}},
            )
            _ = exc  # fall through to DB

        stmt = (
            select(WalletBucket)
            .where(WalletBucket.wallet_id == wallet_id)
            .where(WalletBucket.thread_type == thread_type)
        )
        result = await self._db.execute(stmt)
        bucket = result.scalar_one_or_none()

        if bucket is None:
            raise KeyError(
                f"No bucket found for wallet_id={wallet_id} thread_type={thread_type}"
            )

        # Write back to cache — use set(key, value, ex=ttl) not setex()
        cache_data = json.dumps(
            {
                "id": str(bucket.id),
                "wallet_id": str(bucket.wallet_id),
                "thread_type": bucket.thread_type,
                "available_paise": bucket.available_paise,
                "reserved_paise": bucket.reserved_paise,
                "updated_at": bucket.updated_at.isoformat(),
            }
        )
        try:
            await self._redis.set(cache_key, cache_data, ex=_CACHE_TTL_SECONDS)
        except asyncio.CancelledError:
            raise
        except OSError as exc:
            logger.warning(
                "Redis write-back failed for wallet=%s thread_type=%s",
                wallet_id,
                thread_type,
                exc_info=True,
                extra={"context": {"wallet_id": str(wallet_id)}},
            )
            _ = exc  # non-fatal

        return bucket

    # ------------------------------------------------------------------
    # reserve  (idempotent via idempotency_key)
    # ------------------------------------------------------------------

    async def reserve(
        self,
        wallet_id: UUID,
        thread_type: str,
        amount_paise: int,
        idempotency_key: UUID,
    ) -> BucketReservation:
        """
        Reserve amount_paise from bucket (wallet_id, thread_type).

        Idempotent: if idempotency_key already exists → return existing reservation.
        Raises InsufficientFundsError if available_paise < amount_paise.
        Records C-059 evidence.
        """
        # 1. Idempotency check — attempt insert; on unique violation return existing row.
        try:
            bucket = await self.get_bucket_balance(wallet_id, thread_type)

            if bucket.available_paise < amount_paise:
                raise InsufficientFundsError(
                    f"Insufficient funds in wallet={wallet_id} thread_type={thread_type}: "
                    f"available={bucket.available_paise} requested={amount_paise}"
                )

            reservation = BucketReservation(
                id=uuid4(),
                bucket_id=bucket.id,
                wallet_id=wallet_id,
                thread_type=thread_type,
                amount_paise=amount_paise,
                idempotency_key=idempotency_key,
                status="RESERVED",
                created_at=datetime.now(timezone.utc),
            )
            self._db.add(reservation)

            # Deduct from bucket
            bucket.available_paise -= amount_paise
            bucket.reserved_paise += amount_paise
            bucket.updated_at = datetime.now(timezone.utc)

            await self._db.flush()
            await self._db.commit()

        except asyncio.CancelledError:
            raise
        except IntegrityError:
            # Unique constraint on idempotency_key — return existing reservation.
            await self._db.rollback()
            logger.info(
                "reserve idempotency hit idempotency_key=%s wallet=%s",
                idempotency_key,
                wallet_id,
            )
            stmt = select(BucketReservation).where(
                BucketReservation.idempotency_key == idempotency_key
            )
            result = await self._db.execute(stmt)
            existing = result.scalar_one()
            return existing
        except InsufficientFundsError:
            await self._db.rollback()
            raise
        except (ValueError, RuntimeError):
            await self._db.rollback()
            logger.error(
                "reserve failed wallet=%s thread_type=%s",
                wallet_id,
                thread_type,
                exc_info=True,
                extra={"context": {"wallet_id": str(wallet_id), "thread_type": thread_type}},
            )
            raise

        # Invalidate cache after mutation
        await self._invalidate_bucket_cache(wallet_id, thread_type)

        # C-059 evidence
        await self._record_evidence(
            _EVIDENCE_ACTION_RESERVE,
            wallet_id,
            {
                "reservation_id": str(reservation.id),
                "thread_type": thread_type,
                "amount_paise": amount_paise,
                "idempotency_key": str(idempotency_key),
            },
        )

        logger.info(
            "reserve success wallet=%s thread_type=%s amount_paise=%s reservation_id=%s",
            wallet_id,
            thread_type,
            amount_paise,
            reservation.id,
        )
        return reservation

    # ------------------------------------------------------------------
    # release
    # ------------------------------------------------------------------

    async def release(
        self,
        reservation_id: UUID,
        consumed: bool,
    ) -> None:
        """
        Release a reservation.

        If consumed=True  → amount stays debited (execution completed).
        If consumed=False → amount is returned to available_paise (execution aborted).
        Records C-059 evidence.
        """
        try:
            stmt = select(BucketReservation).where(BucketReservation.id == reservation_id)
            result = await self._db.execute(stmt)
            reservation = result.scalar_one_or_none()

            if reservation is None:
                raise KeyError(f"Reservation not found: reservation_id={reservation_id}")

            if reservation.status == "RELEASED":
                logger.info(
                    "release already completed reservation_id=%s", reservation_id
                )
                return

            bucket_stmt = select(WalletBucket).where(
                WalletBucket.id == reservation.bucket_id
            )
            bucket_result = await self._db.execute(bucket_stmt)
            bucket = bucket_result.scalar_one()

            if not consumed:
                # Return reserved amount to available
                bucket.available_paise += reservation.amount_paise

            bucket.reserved_paise -= reservation.amount_paise
            bucket.updated_at = datetime.now(timezone.utc)

            reservation.status = "RELEASED"
            reservation.released_at = datetime.now(timezone.utc)
            reservation.consumed = consumed

            await self._db.commit()

        except asyncio.CancelledError:
            raise
        except KeyError:
            raise
        except (ValueError, RuntimeError):
            await self._db.rollback()
            logger.error(
                "release failed reservation_id=%s",
                reservation_id,
                exc_info=True,
                extra={"context": {"reservation_id": str(reservation_id)}},
            )
            raise

        # Invalidate cache
        await self._invalidate_bucket_cache(reservation.wallet_id, reservation.thread_type)

        # C-059 evidence
        await self._record_evidence(
            _EVIDENCE_ACTION_RELEASE,
            reservation.wallet_id,
            {
                "reservation_id": str(reservation_id),
                "consumed": consumed,
                "amount_paise": reservation.amount_paise,
            },
        )

        logger.info(
            "release success reservation_id=%s consumed=%s",
            reservation_id,
            consumed,
        )

    # ------------------------------------------------------------------
    # activate_subscription  (C-088 billing profile gate)
    # ------------------------------------------------------------------

    async def activate_subscription(
        self,
        customer_id: UUID,
        agent_type: str,
        bundle_tier: str,
        razorpay_order_id: str,
        razorpay_payment_id: str,
    ) -> dict:
        """
        Activate a subscription for customer_id.

        C-088: billing_profiles.status MUST be FOUNDER_AUTHORIZED before activation.
        Flips customer mode before creating the subscription object to avoid the
        race condition where a second request sees mode=TRIAL after payment confirmed.

        Returns: dict with subscription_id, wallet_id, activated_at.
        """
        try:
            stmt = select(CustomerWallet).where(CustomerWallet.customer_id == customer_id)
            result = await self._db.execute(stmt)
            wallet = result.scalar_one_or_none()

            if wallet is None:
                raise KeyError(f"No wallet found for customer_id={customer_id}")

            # C-088: verify billing profile gate
            if wallet.billing_profile_status != "FOUNDER_AUTHORIZED":
                raise PermissionError(
                    f"C-088 violation: billing_profile_status="
                    f"{wallet.billing_profile_status} for customer_id={customer_id}"
                )

            # Flip mode BEFORE subscription object creation (race condition fix)
            wallet.customer_mode = "SUBSCRIBED"
            wallet.bundle_tier = bundle_tier
            wallet.agent_type = agent_type
            wallet.razorpay_order_id = razorpay_order_id
            wallet.razorpay_payment_id = razorpay_payment_id
            wallet.subscription_activated_at = datetime.now(timezone.utc)
            wallet.updated_at = datetime.now(timezone.utc)

            await self._db.flush()
            await self._db.commit()

        except asyncio.CancelledError:
            raise
        except (KeyError, PermissionError):
            raise
        except (ValueError, RuntimeError):
            await self._db.rollback()
            logger.error(
                "activate_subscription failed customer_id=%s bundle_tier=%s",
                customer_id,
                bundle_tier,
                exc_info=True,
                extra={"context": {"customer_id": str(customer_id), "bundle_tier": bundle_tier}},
            )
            raise

        # Invalidate wallet-level cache
        await self._invalidate_wallet_cache(customer_id)

        await self._record_evidence(
            _EVIDENCE_ACTION_ACTIVATE,
            customer_id,
            {
                "agent_type": agent_type,
                "bundle_tier": bundle_tier,
                "razorpay_order_id": razorpay_order_id,
                # razorpay_payment_id omitted — treat as PII-adjacent financial reference
            },
        )

        logger.info(
            "activate_subscription success customer_id=%s bundle_tier=%s",
            customer_id,
            bundle_tier,
        )

        return {
            "wallet_id": str(wallet.id),
            "customer_id": str(customer_id),
            "bundle_tier": bundle_tier,
            "activated_at": wallet.subscription_activated_at.isoformat(),
        }

    # ------------------------------------------------------------------
    # renew  (C-090 grandfather pricing)
    # ------------------------------------------------------------------

    async def renew(
        self,
        wallet_id: UUID,
        subscription_tier: str,
        new_period_start: date,
    ) -> dict:
        """
        Renew a subscription period for wallet_id.

        C-090 grandfather pricing logic:
          IF billing_profile.legacy_tier == subscription_tier
             AND date.today() <= billing_profile.grandfather_until:
              → apply legacy_price_inr
          ELSE:
              → apply standard_price_inr

        Raises ValueError if plan price > agreed price and C-090 window has expired.
        Records C-059 evidence.
        """
        try:
            stmt = select(CustomerWallet).where(CustomerWallet.id == wallet_id)
            result = await self._db.execute(stmt)
            wallet = result.scalar_one_or_none()

            if wallet is None:
                raise KeyError(f"No wallet found for wallet_id={wallet_id}")

            today = date.today()
            is_grandfathered = (
                wallet.legacy_tier == subscription_tier
                and wallet.grandfather_until is not None
                and today <= wallet.grandfather_until
            )

            if is_grandfathered:
                applied_price_inr = wallet.legacy_price_inr
                pricing_basis = "GRANDFATHER_C090"
            else:
                applied_price_inr = wallet.standard_price_inr
                pricing_basis = "STANDARD"

            # C-090 guard: reject if standard price has increased beyond agreed price
            # and grandfather window has lapsed.
            if (
                not is_grandfathered
                and wallet.agreed_price_inr is not None
                and applied_price_inr > wallet.agreed_price_inr
            ):
                raise ValueError(
                    f"C-090 violation: plan price {applied_price_inr} > agreed price "
                    f"{wallet.agreed_price_inr} and grandfather window has expired "
                    f"for wallet_id={wallet_id}"
                )

            wallet.subscription_tier = subscription_tier
            wallet.current_period_start = new_period_start
            wallet.applied_price_inr = applied_price_inr
            wallet.pricing_basis = pricing_basis
            wallet.updated_at = datetime.now(timezone.utc)

            await self._db.flush()
            await self._db.commit()

        except asyncio.CancelledError:
            raise
        except (KeyError, ValueError):
            raise
        except (OSError, RuntimeError):
            await self._db.rollback()
            logger.error(
                "renew failed wallet_id=%s subscription_tier=%s",
                wallet_id,
                subscription_tier,
                exc_info=True,
                extra={"context": {"wallet_id": str(wallet_id), "subscription_tier": subscription_tier}},
            )
            raise

        await self._invalidate_wallet_cache(wallet_id)

        await self._record_evidence(
            _EVIDENCE_ACTION_RENEW,
            wallet_id,
            {
                "subscription_tier": subscription_tier,
                "new_period_start": new_period_start.isoformat(),
                "applied_price_inr": str(applied_price_inr),
                "pricing_basis": pricing_basis,
            },
        )

        logger.info(
            "renew success wallet_id=%s subscription_tier=%s pricing_basis=%s",
            wallet_id,
            subscription_tier,
            pricing_basis,
        )

        return {
            "wallet_id": str(wallet_id),
            "subscription_tier": subscription_tier,
            "applied_price_inr": str(applied_price_inr),
            "pricing_basis": pricing_basis,
            "new_period_start": new_period_start.isoformat(),
        }

    # ------------------------------------------------------------------
    # Cache invalidation helpers
    # ------------------------------------------------------------------

    async def _invalidate_bucket_cache(self, wallet_id: UUID, thread_type: str) -> None:
        cache_key = self._bucket_cache_key(wallet_id, thread_type)
        try:
            await self._redis.delete(cache_key)
        except asyncio.CancelledError:
            raise
        except OSError as exc:
            logger.warning(
                "cache invalidation failed wallet=%s thread_type=%s",
                wallet_id,
                thread_type,
                exc_info=True,
                extra={"context": {"wallet_id": str(wallet_id), "thread_type": thread_type}},
            )
            _ = exc  # non-fatal

    async def _invalidate_wallet_cache(self, wallet_id: UUID) -> None:
        cache_key = self._wallet_cache_key(wallet_id)
        try:
            await self._redis.delete(cache_key)
        except asyncio.CancelledError:
            raise
        except OSError as exc:
            logger.warning(
                "wallet cache invalidation failed wallet=%s",
                wallet_id,
                exc_info=True,
                extra={"context": {"wallet_id": str(wallet_id)}},
            )
            _ = exc  # non-fatal