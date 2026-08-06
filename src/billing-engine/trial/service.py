# Implements: work-contracts/WC-031-goal005-wbe-trial-promotions.md §WC031-01
# constitutional_basis: C-088 (trial is a billing mode), C-089 (trial costs tracked),
#                       C-090 (grandfather on conversion), C-019 (informed consent — phone verified),
#                       C-059 (Traceability)
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone

import redis.asyncio as aioredis
from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from config import Settings
from trial.models import ConvertResult, TrialStartResult, TrialStatus

logger = logging.getLogger(__name__)

_GRANDFATHER_DAYS = 14


class TrialService:
    """
    WBE sub-component 6: Trial Engine.

    Constitutional obligations:
      C-088 — trial is a billing mode; treated identically to paid for cost tracking.
      C-089 — trial costs tracked in trial_free_unit_ledger.
      C-090 — trial→paid conversion within 14 days activates grandfather pricing.
      C-019 — phone_verified=True required before trial (informed consent gate).
      C-059 — full traceability on every operation.
    """

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        redis_client: aioredis.Redis,
        settings: Settings,
    ) -> None:
        self._session_factory = session_factory
        self._redis = redis_client
        self._settings = settings

    # ------------------------------------------------------------------
    # start_trial
    # ------------------------------------------------------------------

    async def start_trial(
        self,
        customer_id: uuid.UUID,
        agent_type: str,
        phone_verified: bool,
    ) -> TrialStartResult:
        """
        Start a trial for the given customer and agent type.

        C-019: phone_verified=True is required before trial starts.
        C-088: inserts wallet_buckets + trial_free_unit_ledger in ONE transaction.
        Redis key wbe:customer:{id}:mode = "TRIAL" is set AFTER commit (non-transactional).
        """
        if not phone_verified:
            raise HTTPException(
                status_code=422,
                detail={"code": "PHONE_NOT_VERIFIED", "message": "Phone verification required to start trial"},
            )

        free_units_map: dict[str, dict[str, int]] = getattr(self._settings, "TRIAL_FREE_UNITS", {})
        agent_free_units: dict[str, int] | None = free_units_map.get(agent_type) if free_units_map else None
        if not agent_free_units:
            raise HTTPException(
                status_code=422,
                detail={"code": "TRIAL_CONFIG_MISSING", "message": f"No trial configuration for agent_type={agent_type}"},
            )

        duration_days: int = getattr(self._settings, "TRIAL_DURATION_DAYS", _GRANDFATHER_DAYS)

        async with self._session_factory() as session:
            # C-088: one trial per customer per agent_type (UNIQUE constraint)
            existing = await session.execute(
                text(
                    "SELECT trial_id FROM trial_allocations "
                    "WHERE customer_id = :cid AND agent_type = :at"
                ).bindparams(cid=str(customer_id), at=agent_type)
            )
            if existing.fetchone():
                raise HTTPException(
                    status_code=409,
                    detail={"code": "TRIAL_ALREADY_USED", "message": "A trial for this agent type already exists for this customer"},
                )

            trial_id = uuid.uuid4()
            now = datetime.now(tz=timezone.utc)
            expires_at = now + timedelta(days=duration_days)
            # Shared employment_contract_id for all trial buckets (trial-specific EC)
            trial_ec_id = uuid.uuid4()

            await session.execute(
                text(
                    "INSERT INTO trial_allocations "
                    "(trial_id, customer_id, agent_type, started_at, expires_at, status) "
                    "VALUES (:trial_id, :cid, :at, :started_at, :expires_at, 'ACTIVE')"
                ).bindparams(
                    trial_id=str(trial_id),
                    cid=str(customer_id),
                    at=agent_type,
                    started_at=now.isoformat(),
                    expires_at=expires_at.isoformat(),
                )
            )

            bucket_ids: list[uuid.UUID] = []
            for thread_type, units in agent_free_units.items():
                bucket_id = uuid.uuid4()
                await session.execute(
                    text(
                        "INSERT INTO wallet_buckets "
                        "(id, customer_id, employment_contract_id, thread_type, balance_paise, is_active) "
                        "VALUES (:id, :cid, :ec_id, :thread_type, :balance, 1)"
                    ).bindparams(
                        id=str(bucket_id),
                        cid=str(customer_id),
                        ec_id=str(trial_ec_id),
                        thread_type=thread_type,
                        balance=units * 100,  # 1 rupee per unit as nominal trial credit
                    )
                )
                bucket_ids.append(bucket_id)

                await session.execute(
                    text(
                        "INSERT INTO trial_free_unit_ledger "
                        "(trial_id, thread_type, units_granted, units_consumed, updated_at) "
                        "VALUES (:trial_id, :thread_type, :units, 0, :now)"
                    ).bindparams(
                        trial_id=str(trial_id),
                        thread_type=thread_type,
                        units=units,
                        now=now.isoformat(),
                    )
                )

            await session.commit()

        # Set Redis customer mode AFTER commit (not transactional — on failure, log and continue)
        ttl = max(1, int((expires_at - datetime.now(tz=timezone.utc)).total_seconds()))
        try:
            await self._redis.set(f"wbe:customer:{customer_id}:mode", "TRIAL", ex=ttl)
        except Exception:
            logger.error("Failed to set trial Redis key for customer_id=%s", customer_id, exc_info=True)

        logger.info(
            "Trial started: trial_id=%s customer_id=%s agent_type=%s expires_at=%s",
            trial_id, customer_id, agent_type, expires_at.isoformat(),
        )
        return TrialStartResult(
            trial_id=trial_id,
            expires_at=expires_at,
            free_unit_caps=agent_free_units,
            wallet_bucket_ids=bucket_ids,
        )

    # ------------------------------------------------------------------
    # check_expiry  (called by WC-033 Temporal saga)
    # ------------------------------------------------------------------

    async def check_expiry(self, trial_id: uuid.UUID) -> None:
        """Mark trial as EXPIRED and clear Redis customer_mode key."""
        async with self._session_factory() as session:
            result = await session.execute(
                text(
                    "SELECT customer_id, status FROM trial_allocations WHERE trial_id = :trial_id"
                ).bindparams(trial_id=str(trial_id))
            )
            row = result.fetchone()
            if row is None:
                raise HTTPException(status_code=404, detail={"code": "TRIAL_NOT_FOUND"})
            if row[1] != "ACTIVE":
                return  # already expired or converted — idempotent

            await session.execute(
                text(
                    "UPDATE trial_allocations SET status = 'EXPIRED' WHERE trial_id = :trial_id"
                ).bindparams(trial_id=str(trial_id))
            )
            await session.commit()
            customer_id = row[0]

        try:
            await self._redis.delete(f"wbe:customer:{customer_id}:mode")
        except Exception:
            logger.error("Failed to clear trial Redis key for trial_id=%s", trial_id, exc_info=True)

        logger.info("Trial expired: trial_id=%s customer_id=%s", trial_id, customer_id)

    # ------------------------------------------------------------------
    # convert_to_paid  (called by WC-033 Temporal saga on payment)
    # ------------------------------------------------------------------

    async def convert_to_paid(
        self,
        trial_id: uuid.UUID,
        payment_reference: str,
        bundle_tier: str = "STANDARD",
        wallet_service: object | None = None,
    ) -> ConvertResult:
        """
        Convert an active trial to a paid subscription.

        C-090: grandfather pricing applies if conversion is within 14 days of trial start.
        WalletService.activate_subscription is called to create the paid subscription.
        wallet_service may be injected for testing; production wires it from DI.
        """
        async with self._session_factory() as session:
            result = await session.execute(
                text(
                    "SELECT customer_id, agent_type, started_at, status "
                    "FROM trial_allocations WHERE trial_id = :trial_id"
                ).bindparams(trial_id=str(trial_id))
            )
            row = result.fetchone()
            if row is None:
                raise HTTPException(status_code=404, detail={"code": "TRIAL_NOT_FOUND"})
            if row[3] != "ACTIVE":
                raise HTTPException(
                    status_code=409,
                    detail={"code": "TRIAL_NOT_ACTIVE", "message": f"Trial status is {row[3]}"},
                )

            customer_id = uuid.UUID(str(row[0]))
            agent_type: str = row[1]
            started_at = datetime.fromisoformat(str(row[2]).replace("Z", "+00:00"))
            converted_at = datetime.now(tz=timezone.utc)

            # C-090: grandfather applies when conversion within _GRANDFATHER_DAYS of trial start
            if started_at.tzinfo is None:
                started_at = started_at.replace(tzinfo=timezone.utc)
            elapsed_days = (converted_at - started_at).days
            grandfather_applied = elapsed_days <= _GRANDFATHER_DAYS

            new_subscription_id = uuid.uuid4()

            await session.execute(
                text(
                    "UPDATE trial_allocations "
                    "SET status = 'CONVERTED', converted_at = :converted_at, new_subscription_id = :sub_id "
                    "WHERE trial_id = :trial_id AND status = 'ACTIVE'"
                ).bindparams(
                    converted_at=converted_at.isoformat(),
                    sub_id=str(new_subscription_id),
                    trial_id=str(trial_id),
                )
            )
            await session.commit()

        # Activate paid subscription (WalletService call — mocked in tests)
        if wallet_service is not None:
            await wallet_service.activate_subscription(
                customer_id=customer_id,
                agent_type=agent_type,
                bundle_tier=bundle_tier,
                razorpay_order_id=payment_reference,
                razorpay_payment_id=payment_reference,
            )

        # Update Redis mode to ACTIVE
        try:
            await self._redis.set(f"wbe:customer:{customer_id}:mode", "ACTIVE")
        except Exception:
            logger.error("Failed to set ACTIVE Redis key for customer_id=%s", customer_id, exc_info=True)

        logger.info(
            "Trial converted: trial_id=%s customer_id=%s grandfather_applied=%s",
            trial_id, customer_id, grandfather_applied,
        )
        return ConvertResult(
            new_subscription_id=new_subscription_id,
            grandfather_applied=grandfather_applied,
        )

    # ------------------------------------------------------------------
    # get_status
    # ------------------------------------------------------------------

    async def get_status(self, customer_id: uuid.UUID) -> TrialStatus | None:
        """Return the most recent trial status for a customer, or None if no trial exists."""
        async with self._session_factory() as session:
            result = await session.execute(
                text(
                    "SELECT trial_id, agent_type, started_at, expires_at, status "
                    "FROM trial_allocations "
                    "WHERE customer_id = :cid "
                    "ORDER BY started_at DESC LIMIT 1"
                ).bindparams(cid=str(customer_id))
            )
            row = result.fetchone()
            if row is None:
                return None

            trial_id = uuid.UUID(str(row[0]))
            ledger = await session.execute(
                text(
                    "SELECT thread_type, units_granted, units_consumed "
                    "FROM trial_free_unit_ledger WHERE trial_id = :trial_id"
                ).bindparams(trial_id=str(trial_id))
            )
            units_consumed: dict[str, int] = {}
            units_remaining: dict[str, int] = {}
            for ledger_row in ledger.fetchall():
                units_consumed[ledger_row[0]] = ledger_row[2]
                units_remaining[ledger_row[0]] = ledger_row[1] - ledger_row[2]

            started_at = datetime.fromisoformat(str(row[2]).replace("Z", "+00:00"))
            expires_at = datetime.fromisoformat(str(row[3]).replace("Z", "+00:00"))
            if started_at.tzinfo is None:
                started_at = started_at.replace(tzinfo=timezone.utc)
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)

            return TrialStatus(
                trial_id=trial_id,
                agent_type=row[1],
                started_at=started_at,
                expires_at=expires_at,
                status=row[4],
                units_consumed=units_consumed,
                units_remaining=units_remaining,
            )
