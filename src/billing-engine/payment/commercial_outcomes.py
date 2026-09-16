# Implements: work-contracts/WC-095-agent-employment-lifecycle-and-dma-customer-activation.md section 7.5
# Constitutional basis: C-023, C-059, C-088
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from payment.models import RelationshipCheckoutRequest, RelationshipCheckoutResult


class ZeroPriceCommercialOutcomeStore:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def record(
        self,
        request: RelationshipCheckoutRequest,
        outcome: RelationshipCheckoutResult,
    ) -> None:
        await self._db.execute(text("""
            INSERT INTO zero_price_commercial_outcomes (
                checkout_intent_id, tenant_id, customer_id, relationship_id,
                accepted_contract_id, contract_version, contract_hash,
                contract_acceptance_id, payment_consent_evidence_id,
                commercial_evidence_id, agent_type, bundle_tier, quote_version,
                promotion_version, outcome_reference)
            VALUES (
                :checkout_intent_id, :tenant_id, :customer_id, :relationship_id,
                :accepted_contract_id, :contract_version, :contract_hash,
                :contract_acceptance_id, :payment_consent_evidence_id,
                :commercial_evidence_id, :agent_type, :bundle_tier, :quote_version,
                :promotion_version, :outcome_reference)
            ON CONFLICT (checkout_intent_id) DO NOTHING
        """).bindparams(
            checkout_intent_id=request.checkout_intent_id,
            tenant_id=request.tenant_id,
            customer_id=request.customer_id,
            relationship_id=request.relationship_id,
            accepted_contract_id=request.contract_id,
            contract_version=request.contract_version,
            contract_hash=request.contract_hash,
            contract_acceptance_id=request.contract_acceptance_id,
            payment_consent_evidence_id=request.payment_consent_evidence_id,
            commercial_evidence_id=outcome.commercial_evidence_id,
            agent_type=request.agent_type,
            bundle_tier=request.bundle_tier,
            quote_version=request.quote_version,
            promotion_version=outcome.promotion_version,
            outcome_reference=outcome.commercial_outcome_reference,
        ))
        stored = (await self._db.execute(text("""
            SELECT tenant_id, customer_id, relationship_id, accepted_contract_id,
                contract_version, contract_hash, contract_acceptance_id,
                payment_consent_evidence_id, commercial_evidence_id, agent_type,
                bundle_tier, quote_version, promotion_version, outcome_reference
            FROM zero_price_commercial_outcomes
            WHERE checkout_intent_id = :checkout_intent_id
        """).bindparams(checkout_intent_id=request.checkout_intent_id))).one()
        expected = (
            str(request.tenant_id), str(request.customer_id), str(request.relationship_id),
            str(request.contract_id), request.contract_version, request.contract_hash,
            str(request.contract_acceptance_id), str(request.payment_consent_evidence_id),
            str(outcome.commercial_evidence_id), request.agent_type, request.bundle_tier,
            request.quote_version, outcome.promotion_version,
            outcome.commercial_outcome_reference,
        )
        if tuple(str(value) if index not in {4} else value for index, value in enumerate(stored)) != expected:
            await self._db.rollback()
            raise ValueError("zero-price checkout intent has divergent material")
        await self._db.commit()