# Implements: work-contracts/WC-059-goal005-ae01-contract-payment-activation.md §WC059-06
# Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C4-10
# Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C5-07
# constitutional_basis: C-002, C-023, C-059, C-088
# Constitutional basis: C-059, C-038, C-088
from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from markup.package_engine import SqlPackageReferenceData
from payment.lifecycle import credit_paid_period
from payment.models import PaidActivationRequest, PaidActivationResult
from wallet import mirror
from wallet.service import WalletService


class PaidActivationService:
    def __init__(self, db: AsyncSession, wallet: WalletService) -> None:
        self._db = db
        self._wallet = wallet

    async def activate(self, request: PaidActivationRequest) -> PaidActivationResult:
        is_postgres = self._db.bind is not None and self._db.bind.dialect.name == "postgresql"
        lock = " FOR UPDATE" if is_postgres else ""
        database_uuid = (lambda value: value) if is_postgres else (lambda value: str(value))
        row = (await self._db.execute(text(
            "SELECT razorpay_order_id, customer_id, status, tenant_id, relationship_id, accepted_contract_id, contract_version, "
            "contract_acceptance_id, payment_evidence_id, agent_type, bundle_tier, "
            "activation_intent_id, activation_correlation_id, outcome_subscription_id "
            "FROM payment_intents WHERE razorpay_payment_id = :payment_reference" + lock
        ).bindparams(payment_reference=request.payment_reference))).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail={"code": "PAYMENT_CAPTURE_NOT_FOUND"})
        supplied = (
            str(request.tenant_id), str(request.relationship_id), str(request.accepted_contract_id), request.contract_version,
            str(request.contract_acceptance_id), str(request.payment_evidence_id),
        )
        stored = (
            str(row.tenant_id), str(row.relationship_id), str(row.accepted_contract_id), row.contract_version,
            str(row.contract_acceptance_id), str(row.payment_evidence_id),
        )
        if stored != supplied:
            raise HTTPException(status_code=409, detail={"code": "ACTIVATION_MATERIAL_CONFLICT"})
        if row.status == "ACTIVATED":
            if (str(row.activation_intent_id), str(row.activation_correlation_id)) != (
                str(request.activation_intent_id), str(request.correlation_id)
            ):
                raise HTTPException(status_code=409, detail={"code": "ACTIVATION_REPLAY_CONFLICT"})
            return PaidActivationResult(subscription_id=UUID(str(row.outcome_subscription_id)))
        if row.status not in {"CAPTURED", "FAILED_RETRYABLE", "ACTIVATION_IN_PROGRESS"}:
            raise HTTPException(status_code=409, detail={"code": "PAYMENT_NOT_ACTIVATION_ELIGIBLE"})
        if row.status == "ACTIVATION_IN_PROGRESS" and (
            str(row.activation_intent_id), str(row.activation_correlation_id)
        ) != (str(request.activation_intent_id), str(request.correlation_id)):
            raise HTTPException(status_code=409, detail={"code": "ACTIVATION_REPLAY_CONFLICT"})

        await self._db.execute(text(
            "UPDATE payment_intents SET status = 'ACTIVATION_IN_PROGRESS', "
            "activation_intent_id = :intent_id, activation_correlation_id = :correlation_id "
            "WHERE razorpay_payment_id = :payment_reference"
        ).bindparams(
            intent_id=database_uuid(request.activation_intent_id),
            correlation_id=database_uuid(request.correlation_id),
            payment_reference=request.payment_reference,
        ))
        try:
            outcome = await self._wallet.activate_subscription(
                customer_id=UUID(str(row.customer_id)),
                agent_type=row.agent_type,
                bundle_tier=row.bundle_tier,
                razorpay_order_id=row.razorpay_order_id,
                razorpay_payment_id=request.payment_reference,
                commit=False,
            )
            now = datetime.now(timezone.utc)
            database_time = now if is_postgres else now.isoformat()
            await self._db.execute(text(
                "UPDATE trial_allocations SET status = 'CONVERTED', converted_at = :now, "
                "new_subscription_id = :subscription_id WHERE customer_id = :customer_id AND status = 'ACTIVE'"
            ).bindparams(
                now=database_time, subscription_id=database_uuid(outcome.subscription_id),
                customer_id=database_uuid(row.customer_id),
            ))
            await self._db.execute(text(
                "UPDATE payment_intents SET status = 'ACTIVATED', activated_at = :now, "
                "outcome_subscription_id = :subscription_id WHERE razorpay_payment_id = :payment_reference"
            ).bindparams(
                now=database_time, subscription_id=database_uuid(outcome.subscription_id),
                payment_reference=request.payment_reference,
            ))
            authority = mirror.wallet_authority()
            await credit_paid_period(
                self._db,
                rates=SqlPackageReferenceData(self._db),
                tenant_id=UUID(str(row.tenant_id)),
                relationship_id=UUID(str(row.relationship_id)),
                customer_id=UUID(str(row.customer_id)),
                period_start=now,
                evidence_id=request.payment_evidence_id,
                authority=authority,
                coupon_code=await self._checkout_coupon(request.payment_reference) if authority != "LEGACY" else None,
            )
            await self._db.commit()
            return PaidActivationResult(subscription_id=outcome.subscription_id)
        except Exception:
            await self._db.rollback()
            await self._db.execute(text(
                "UPDATE payment_intents SET status = 'FAILED_RETRYABLE' "
                "WHERE razorpay_payment_id = :payment_reference AND status = 'ACTIVATION_IN_PROGRESS'"
            ).bindparams(payment_reference=request.payment_reference))
            await self._db.commit()
            raise

    async def _checkout_coupon(self, payment_reference: str) -> str | None:
        """The coupon code the customer checked out with, if any, for its redemption at hire (C5-07)."""
        row = (await self._db.execute(text(
            "SELECT o.coupon_code FROM pre_hire_checkout_orders o "
            "JOIN payment_intents p ON p.checkout_intent_id = o.checkout_intent_id "
            "WHERE p.razorpay_payment_id = :payment_reference"
        ).bindparams(payment_reference=payment_reference))).fetchone()
        return None if row is None or not row.coupon_code else str(row.coupon_code)