# Implements: work-contracts/WC-095-agent-employment-lifecycle-and-dma-customer-activation.md section 7.5
# Constitutional basis: C-023, C-059, C-088
from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from payment.models import PaidActivationResult, ZeroPriceActivationRequest
from wallet.service import WalletService


class ZeroPriceActivationService:
    def __init__(self, db: AsyncSession, wallet: WalletService) -> None:
        self._db = db
        self._wallet = wallet

    async def activate(self, request: ZeroPriceActivationRequest) -> PaidActivationResult:
        is_postgres = self._db.bind is not None and self._db.bind.dialect.name == "postgresql"
        database_uuid = (lambda value: value) if is_postgres else (lambda value: str(value))
        select_outcome = text("""
            SELECT customer_id, status, tenant_id, relationship_id, accepted_contract_id,
                contract_version, contract_acceptance_id, commercial_evidence_id,
                agent_type, bundle_tier, activation_intent_id,
                activation_correlation_id, outcome_subscription_id
            FROM zero_price_commercial_outcomes
            WHERE outcome_reference = :outcome_reference
            FOR UPDATE
        """) if is_postgres else text("""
            SELECT customer_id, status, tenant_id, relationship_id, accepted_contract_id,
                contract_version, contract_acceptance_id, commercial_evidence_id,
                agent_type, bundle_tier, activation_intent_id,
                activation_correlation_id, outcome_subscription_id
            FROM zero_price_commercial_outcomes
            WHERE outcome_reference = :outcome_reference
        """)
        row = (await self._db.execute(select_outcome.bindparams(
            outcome_reference=request.commercial_outcome_reference,
        ))).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail={"code": "ZERO_PRICE_OUTCOME_NOT_FOUND"})
        supplied = (
            str(request.tenant_id), str(request.relationship_id),
            str(request.accepted_contract_id), request.contract_version,
            str(request.contract_acceptance_id), str(request.commercial_evidence_id),
        )
        stored = (
            str(row.tenant_id), str(row.relationship_id), str(row.accepted_contract_id),
            row.contract_version, str(row.contract_acceptance_id),
            str(row.commercial_evidence_id),
        )
        if stored != supplied:
            raise HTTPException(status_code=409, detail={"code": "ACTIVATION_MATERIAL_CONFLICT"})
        if row.status == "ACTIVATED":
            if (str(row.activation_intent_id), str(row.activation_correlation_id)) != (
                str(request.activation_intent_id), str(request.correlation_id)
            ):
                raise HTTPException(status_code=409, detail={"code": "ACTIVATION_REPLAY_CONFLICT"})
            return PaidActivationResult(subscription_id=UUID(str(row.outcome_subscription_id)))
        if row.status not in {"ZERO_PRICE_SATISFIED", "FAILED_RETRYABLE", "ACTIVATION_IN_PROGRESS"}:
            raise HTTPException(status_code=409, detail={"code": "OUTCOME_NOT_ACTIVATION_ELIGIBLE"})
        if row.status == "ACTIVATION_IN_PROGRESS" and (
            str(row.activation_intent_id), str(row.activation_correlation_id)
        ) != (str(request.activation_intent_id), str(request.correlation_id)):
            raise HTTPException(status_code=409, detail={"code": "ACTIVATION_REPLAY_CONFLICT"})

        await self._db.execute(text("""
            UPDATE zero_price_commercial_outcomes
            SET status = 'ACTIVATION_IN_PROGRESS', activation_intent_id = :intent_id,
                activation_correlation_id = :correlation_id
            WHERE outcome_reference = :outcome_reference
        """).bindparams(
            intent_id=database_uuid(request.activation_intent_id),
            correlation_id=database_uuid(request.correlation_id),
            outcome_reference=request.commercial_outcome_reference,
        ))
        try:
            outcome = await self._wallet.activate_zero_price_subscription(
                customer_id=UUID(str(row.customer_id)),
                agent_type=row.agent_type,
                bundle_tier=row.bundle_tier,
                commercial_outcome_reference=request.commercial_outcome_reference,
                commit=False,
            )
            now = datetime.now(timezone.utc)
            database_time = now if is_postgres else now.isoformat()
            await self._db.execute(text("""
                UPDATE trial_allocations
                SET status = 'CONVERTED', converted_at = :now,
                    new_subscription_id = :subscription_id
                WHERE customer_id = :customer_id AND status = 'ACTIVE'
            """).bindparams(
                now=database_time,
                subscription_id=database_uuid(outcome.subscription_id),
                customer_id=database_uuid(row.customer_id),
            ))
            await self._db.execute(text("""
                UPDATE zero_price_commercial_outcomes
                SET status = 'ACTIVATED', activated_at = :now,
                    outcome_subscription_id = :subscription_id
                WHERE outcome_reference = :outcome_reference
            """).bindparams(
                now=database_time,
                subscription_id=database_uuid(outcome.subscription_id),
                outcome_reference=request.commercial_outcome_reference,
            ))
            await self._db.commit()
            return PaidActivationResult(subscription_id=outcome.subscription_id)
        except Exception:
            await self._db.rollback()
            await self._db.execute(text("""
                UPDATE zero_price_commercial_outcomes
                SET status = 'FAILED_RETRYABLE'
                WHERE outcome_reference = :outcome_reference
                    AND status = 'ACTIVATION_IN_PROGRESS'
            """).bindparams(outcome_reference=request.commercial_outcome_reference))
            await self._db.commit()
            raise