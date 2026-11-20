# Implements: work-contracts/WC-031-goal005-wbe-trial-promotions.md §WC031-01
# Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C3-02
# Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C3-03
# Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C4-04
# constitutional_basis: C-088 (trial is a billing mode), C-089 (trial costs tracked),
#                       C-090 (grandfather on conversion), C-019 (informed consent — phone verified),
#                       C-059 (Traceability)
from __future__ import annotations

import logging
import re
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy import DateTime, String, bindparam, text
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from config import Settings
from trial.models import ConvertResult, TrialStartResult, TrialStatus
from wallet import metrics
from wallet.platform_accounts import PlatformAccounts, PlatformGrant, effective_grant

logger = logging.getLogger(__name__)

_GRANDFATHER_DAYS = 14
_DEFAULT_TRIAL_DURATION_DAYS = 14
_UUID_BIND_TYPE = String(36).with_variant(postgresql.UUID(as_uuid=False), "postgresql")
_IDENTITY_HASH = re.compile(r"^[0-9a-f]{64}$")
_BINDING_MODES = ("OFF", "RECORD", "ENFORCE")
_WALLET_AUTHORITIES = ("LEGACY", "SHADOW", "WALLET")


class TrialService:
    """
    WBE sub-component 6: Trial Engine.

    Constitutional obligations:
      C-088 — trial is a billing mode; treated identically to paid for cost tracking.
      C-089 — trial costs tracked in trial_free_unit_ledger.
      C-090 — trial→paid conversion within 14 days activates grandfather pricing.
      C-019 — phone_verified=True required before trial (informed consent gate).
      C-059 — full traceability on every operation.

    Trial status lives only in PostgreSQL (trial_allocations); there is no customer-level mode flag.
    """

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        settings: Settings,
    ) -> None:
        self._session_factory = session_factory
        self._settings = settings

    def _setting(self, name: str, allowed: tuple[str, ...], default: str) -> str:
        value = getattr(self._settings, name, default)
        return value if isinstance(value, str) and value in allowed else default

    async def _lookup_trial_grant(self, agent_type: str, agent_version: str) -> PlatformGrant | None:
        """The EFFECTIVE trial grant for the exact version; unavailable pricing means the settings fallback."""
        try:
            async with self._session_factory() as session:
                return await effective_grant(session, "TRIAL", agent_type, agent_version)
        except SQLAlchemyError:
            logger.warning("Trial grant lookup unavailable; using settings fallback", exc_info=True)
            return None

    # ------------------------------------------------------------------
    # start_trial
    # ------------------------------------------------------------------

    async def start_trial(
        self,
        customer_id: uuid.UUID,
        agent_type: str,
        phone_verified: bool,
        agent_version: str = "1.0.0",
        identity_subject_hash: str | None = None,
        tenant_id: uuid.UUID | None = None,
        relationship_id: uuid.UUID | None = None,
    ) -> TrialStartResult:
        """
        Start a trial for the given customer and exact agent version.

        C-019: phone_verified=True is required before trial starts.
        C-088: inserts wallet_buckets + trial_free_unit_ledger in ONE transaction.
        C3-03: the verified identity (a hash, never the number) is bound per agent type and version
        according to TRIAL_IDENTITY_BINDING_MODE (OFF, RECORD, ENFORCE).
        C4-04: with WALLET_AUTHORITY SHADOW or WALLET and a relationship, the trial grant is also
        credited to the relationship's TRIAL wallet account in the same transaction.
        """
        if not phone_verified:
            raise HTTPException(
                status_code=422,
                detail={"code": "PHONE_NOT_VERIFIED", "message": "Phone verification required to start trial"},
            )
        if identity_subject_hash is not None and not _IDENTITY_HASH.fullmatch(identity_subject_hash):
            raise HTTPException(
                status_code=422,
                detail={"code": "IDENTITY_HASH_INVALID", "message": "identity_subject_hash must be 64 lowercase hex characters"},
            )

        free_units_map: dict[str, dict[str, int]] = getattr(self._settings, "TRIAL_FREE_UNITS", {})
        agent_free_units: dict[str, int] | None = free_units_map.get(agent_type) if free_units_map else None
        if not agent_free_units:
            raise HTTPException(
                status_code=422,
                detail={"code": "TRIAL_CONFIG_MISSING", "message": f"No trial configuration for agent_type={agent_type}"},
            )

        binding_mode = self._setting("TRIAL_IDENTITY_BINDING_MODE", _BINDING_MODES, "RECORD")
        wallet_mode = self._setting("WALLET_AUTHORITY", _WALLET_AUTHORITIES, "LEGACY")
        credit_wallet = wallet_mode != "LEGACY" and tenant_id is not None and relationship_id is not None
        grant = await self._lookup_trial_grant(agent_type, agent_version) if credit_wallet else None

        async with self._session_factory() as session:
            # C-088: one trial per customer per exact agent version (UNIQUE constraint)
            existing = await session.execute(
                text(
                    "SELECT trial_id FROM trial_allocations WHERE customer_id = :cid AND agent_type = :at AND agent_version = :av"
                ).bindparams(
                    bindparam("cid", str(customer_id), type_=_UUID_BIND_TYPE),
                    at=agent_type,
                    av=agent_version,
                )
            )
            if existing.fetchone():
                raise HTTPException(
                    status_code=409,
                    detail={
                        "code": "TRIAL_ALREADY_USED",
                        "message": "A trial for this agent type already exists for this customer",
                    },
                )

            duration_result = await session.execute(
                text("SELECT duration_days FROM agent_trial_policies WHERE agent_type = :at AND agent_version = :av").bindparams(
                    at=agent_type, av=agent_version
                )
            )
            duration_days = duration_result.scalar_one_or_none() or _DEFAULT_TRIAL_DURATION_DAYS
            trial_id = uuid.uuid4()
            now = datetime.now(tz=timezone.utc)
            expires_at = now + timedelta(days=duration_days)
            # Shared employment_contract_id for all trial buckets (trial-specific EC)
            trial_ec_id = uuid.uuid4()

            try:
                await session.execute(
                    text(
                        "INSERT INTO trial_allocations "
                        "(trial_id, customer_id, agent_type, agent_version, started_at, expires_at, status) "
                        "VALUES (:trial_id, :cid, :at, :av, :started_at, :expires_at, 'ACTIVE')"
                    ).bindparams(
                        bindparam("trial_id", str(trial_id), type_=_UUID_BIND_TYPE),
                        bindparam("cid", str(customer_id), type_=_UUID_BIND_TYPE),
                        bindparam("started_at", now, type_=DateTime(timezone=True)),
                        bindparam("expires_at", expires_at, type_=DateTime(timezone=True)),
                        at=agent_type,
                        av=agent_version,
                    )
                )
            except IntegrityError as error:
                await session.rollback()
                constraint_name = getattr(getattr(error.orig, "diag", None), "constraint_name", None)
                sqlstate = getattr(error.orig, "sqlstate", None) or getattr(error.orig, "pgcode", None)
                if constraint_name != "trial_one_per_agent_version" and sqlstate != "23505":
                    raise
                raise HTTPException(
                    status_code=409,
                    detail={
                        "code": "TRIAL_ALREADY_USED",
                        "message": "A trial for this agent version already exists for this customer",
                    },
                ) from error

            if identity_subject_hash is not None and binding_mode != "OFF":
                claimed = await session.execute(
                    text(
                        "INSERT INTO trial_identity_claims "
                        "(identity_subject_hash, agent_type, agent_version, trial_id, claimed_at) "
                        "VALUES (:hash, :at, :av, :trial_id, :claimed_at) "
                        "ON CONFLICT (identity_subject_hash, agent_type, agent_version) DO NOTHING"
                    ).bindparams(
                        bindparam("trial_id", str(trial_id), type_=_UUID_BIND_TYPE),
                        bindparam("claimed_at", now, type_=DateTime(timezone=True)),
                        hash=identity_subject_hash,
                        at=agent_type,
                        av=agent_version,
                    )
                )
                if claimed.rowcount == 0:
                    if binding_mode == "ENFORCE":
                        await session.rollback()
                        raise HTTPException(
                            status_code=409,
                            detail={
                                "code": "TRIAL_ALREADY_USED_BY_IDENTITY",
                                "message": "This verified identity already used the trial of this agent version",
                            },
                        )
                    logger.warning(
                        "Trial identity already claimed; RECORD mode keeps the first claim: agent_type=%s agent_version=%s",
                        agent_type,
                        agent_version,
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
                        bindparam("id", str(bucket_id), type_=_UUID_BIND_TYPE),
                        bindparam("cid", str(customer_id), type_=_UUID_BIND_TYPE),
                        bindparam("ec_id", str(trial_ec_id), type_=_UUID_BIND_TYPE),
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
                        bindparam("trial_id", str(trial_id), type_=_UUID_BIND_TYPE),
                        bindparam("now", now, type_=DateTime(timezone=True)),
                        thread_type=thread_type,
                        units=units,
                    )
                )

            if credit_wallet:
                await self._credit_wallet(
                    session,
                    wallet_mode,
                    tenant_id,
                    relationship_id,
                    agent_type,
                    agent_version,
                    trial_id,
                    now,
                    expires_at,
                    grant,
                    agent_free_units,
                )

            await session.commit()

        logger.info(
            "Trial started: agent_type=%s agent_version=%s expires_at=%s",
            agent_type,
            agent_version,
            expires_at.isoformat(),
        )
        return TrialStartResult(
            trial_id=trial_id,
            started_at=now,
            expires_at=expires_at,
            free_unit_caps=agent_free_units,
            wallet_bucket_ids=bucket_ids,
        )

    async def _credit_wallet(
        self,
        session: AsyncSession,
        wallet_mode: str,
        tenant_id: uuid.UUID,
        relationship_id: uuid.UUID,
        agent_type: str,
        agent_version: str,
        trial_id: uuid.UUID,
        started_at: datetime,
        expires_at: datetime,
        grant: PlatformGrant | None,
        fallback_units: dict[str, int],
    ) -> None:
        """SHADOW never fails the legacy trial; WALLET makes the credit part of the same transaction."""
        accounts = PlatformAccounts(session)

        async def credit() -> None:
            await accounts.credit_trial_grant(
                tenant_id,
                relationship_id,
                agent_type,
                agent_version,
                trial_id,
                started_at,
                expires_at,
                grant=grant,
                fallback_units=fallback_units,
            )

        if wallet_mode == "WALLET":
            await credit()
            return
        try:
            async with session.begin_nested():
                await credit()
        except Exception:
            logger.error("Trial wallet credit failed in SHADOW mode; legacy trial continues", exc_info=True)
            metrics.count("wbe.wallet.shadow_failure", operation="trial_credit")

    # ------------------------------------------------------------------
    # check_expiry  (called by WC-033 Temporal saga)
    # ------------------------------------------------------------------

    async def check_expiry(self, trial_id: uuid.UUID) -> str:
        """Mark trial as EXPIRED. Status is only in PostgreSQL; there is no customer-mode flag to clear."""
        async with self._session_factory() as session:
            result = await session.execute(
                text("SELECT customer_id, status FROM trial_allocations WHERE trial_id = :trial_id").bindparams(
                    bindparam("trial_id", str(trial_id), type_=_UUID_BIND_TYPE)
                )
            )
            row = result.fetchone()
            if row is None:
                raise HTTPException(status_code=404, detail={"code": "TRIAL_NOT_FOUND"})
            if row[1] != "ACTIVE":
                return str(row[1])  # already expired or converted — idempotent

            await session.execute(
                text("UPDATE trial_allocations SET status = 'EXPIRED' WHERE trial_id = :trial_id").bindparams(
                    bindparam("trial_id", str(trial_id), type_=_UUID_BIND_TYPE)
                )
            )
            await session.commit()

        logger.info("Trial expired")
        return "EXPIRED"

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
                    "SELECT customer_id, agent_type, started_at, status FROM trial_allocations WHERE trial_id = :trial_id"
                ).bindparams(bindparam("trial_id", str(trial_id), type_=_UUID_BIND_TYPE))
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
                    bindparam("sub_id", str(new_subscription_id), type_=_UUID_BIND_TYPE),
                    bindparam("trial_id", str(trial_id), type_=_UUID_BIND_TYPE),
                    bindparam("converted_at", converted_at, type_=DateTime(timezone=True)),
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

        logger.info(
            "Trial converted: grandfather_applied=%s",
            grandfather_applied,
        )
        return ConvertResult(
            new_subscription_id=new_subscription_id,
            grandfather_applied=grandfather_applied,
        )

    # ------------------------------------------------------------------
    # get_status
    # ------------------------------------------------------------------

    async def get_status(
        self,
        customer_id: uuid.UUID,
        trial_id: uuid.UUID | None = None,
        agent_type: str | None = None,
        agent_version: str | None = None,
    ) -> TrialStatus | None:
        """Return an exact trial status, or the customer's most recent trial when unspecified."""
        async with self._session_factory() as session:
            parameters: dict[str, object] = {"cid": str(customer_id)}
            if trial_id is not None:
                parameters["trial_id"] = str(trial_id)
                query = text(
                    "SELECT trial_id, agent_type, agent_version, started_at, expires_at, status "
                    "FROM trial_allocations WHERE customer_id = :cid AND trial_id = :trial_id "
                    "ORDER BY started_at DESC LIMIT 1"
                ).bindparams(
                    bindparam("cid", type_=_UUID_BIND_TYPE),
                    bindparam("trial_id", type_=_UUID_BIND_TYPE),
                )
            elif agent_type is not None and agent_version is not None:
                parameters["agent_type"] = agent_type
                parameters["agent_version"] = agent_version
                query = text(
                    "SELECT trial_id, agent_type, agent_version, started_at, expires_at, status "
                    "FROM trial_allocations WHERE customer_id = :cid "
                    "AND agent_type = :agent_type AND agent_version = :agent_version "
                    "ORDER BY started_at DESC LIMIT 1"
                ).bindparams(bindparam("cid", type_=_UUID_BIND_TYPE))
            elif agent_type is not None or agent_version is not None:
                raise ValueError("agent_type and agent_version must be provided together")
            else:
                query = text(
                    "SELECT trial_id, agent_type, agent_version, started_at, expires_at, status "
                    "FROM trial_allocations WHERE customer_id = :cid "
                    "ORDER BY started_at DESC LIMIT 1"
                ).bindparams(bindparam("cid", type_=_UUID_BIND_TYPE))
            result = await session.execute(query, parameters)
            row = result.fetchone()
            if row is None:
                return None

            trial_id = uuid.UUID(str(row[0]))
            ledger = await session.execute(
                text(
                    "SELECT thread_type, units_granted, units_consumed FROM trial_free_unit_ledger WHERE trial_id = :trial_id"
                ).bindparams(bindparam("trial_id", str(trial_id), type_=_UUID_BIND_TYPE))
            )
            units_consumed: dict[str, int] = {}
            units_remaining: dict[str, int] = {}
            for ledger_row in ledger.fetchall():
                units_consumed[ledger_row[0]] = ledger_row[2]
                units_remaining[ledger_row[0]] = ledger_row[1] - ledger_row[2]

            started_at = datetime.fromisoformat(str(row[3]).replace("Z", "+00:00"))
            expires_at = datetime.fromisoformat(str(row[4]).replace("Z", "+00:00"))
            if started_at.tzinfo is None:
                started_at = started_at.replace(tzinfo=timezone.utc)
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            status = row[5]
            if status == "ACTIVE" and expires_at <= datetime.now(tz=timezone.utc):
                await session.execute(
                    text(
                        "UPDATE trial_allocations SET status = 'EXPIRED' WHERE trial_id = :trial_id AND status = 'ACTIVE'"
                    ).bindparams(bindparam("trial_id", str(trial_id), type_=_UUID_BIND_TYPE))
                )
                await session.commit()
                status = "EXPIRED"

            return TrialStatus(
                trial_id=trial_id,
                agent_type=row[1],
                agent_version=row[2],
                started_at=started_at,
                expires_at=expires_at,
                status=status,
                units_consumed=units_consumed,
                units_remaining=units_remaining,
            )
