-- Implements: work-contracts/WC-095-agent-employment-lifecycle-and-dma-customer-activation.md section 7.5
-- Constitutional basis: C-023, C-059, C-088

CREATE TABLE IF NOT EXISTS business.zero_price_commercial_outcomes (
    checkout_intent_id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    customer_id UUID NOT NULL REFERENCES business.organisations (id),
    relationship_id UUID NOT NULL,
    accepted_contract_id UUID NOT NULL,
    contract_version INTEGER NOT NULL CHECK (contract_version > 0),
    contract_hash VARCHAR(64) NOT NULL CHECK (contract_hash ~ '^[0-9a-f]{64}$'),
    contract_acceptance_id UUID NOT NULL,
    payment_consent_evidence_id UUID NOT NULL,
    commercial_evidence_id UUID NOT NULL UNIQUE,
    agent_type VARCHAR(64) NOT NULL,
    bundle_tier VARCHAR(64) NOT NULL,
    quote_version VARCHAR(128) NOT NULL,
    promotion_version VARCHAR(128) NOT NULL,
    outcome_reference VARCHAR(128) NOT NULL UNIQUE,
    status VARCHAR(32) NOT NULL DEFAULT 'ZERO_PRICE_SATISFIED' CHECK (
        status IN ('ZERO_PRICE_SATISFIED', 'ACTIVATION_IN_PROGRESS', 'ACTIVATED', 'FAILED_RETRYABLE')
    ),
    activation_intent_id UUID,
    activation_correlation_id UUID,
    outcome_subscription_id UUID,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    activated_at TIMESTAMPTZ,
    CONSTRAINT zero_price_relationship_fk FOREIGN KEY (tenant_id, relationship_id)
    REFERENCES business.employment_relationships (tenant_id, relationship_id),
    CONSTRAINT zero_price_activation_material_check CHECK (
        (
            status = 'ZERO_PRICE_SATISFIED'
            AND activation_intent_id IS NULL
            AND activation_correlation_id IS NULL
            AND outcome_subscription_id IS NULL
            AND activated_at IS NULL
        )
        OR (
            status IN ('ACTIVATION_IN_PROGRESS', 'FAILED_RETRYABLE')
            AND activation_intent_id IS NOT NULL
            AND activation_correlation_id IS NOT NULL
            AND outcome_subscription_id IS NULL
            AND activated_at IS NULL
        )
        OR (
            status = 'ACTIVATED'
            AND activation_intent_id IS NOT NULL
            AND activation_correlation_id IS NOT NULL
            AND outcome_subscription_id IS NOT NULL
            AND activated_at IS NOT NULL
        )
    )
);

ALTER TABLE business.paid_subscriptions
ADD COLUMN IF NOT EXISTS commercial_outcome_kind VARCHAR(32),
ADD COLUMN IF NOT EXISTS commercial_outcome_reference VARCHAR(128);
ALTER TABLE business.paid_subscriptions
ALTER COLUMN razorpay_order_id DROP NOT NULL,
ALTER COLUMN razorpay_payment_id DROP NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS paid_subscriptions_commercial_outcome_uidx
ON business.paid_subscriptions (commercial_outcome_reference)
WHERE commercial_outcome_reference IS NOT NULL;
ALTER TABLE business.paid_subscriptions
DROP CONSTRAINT IF EXISTS paid_subscriptions_outcome_source_check;
ALTER TABLE business.paid_subscriptions
ADD CONSTRAINT paid_subscriptions_outcome_source_check CHECK (
    (
        commercial_outcome_kind IS NULL
        AND razorpay_order_id IS NOT NULL
        AND razorpay_payment_id IS NOT NULL
    )
    OR (
        commercial_outcome_kind = 'ZERO_PRICE_SATISFIED'
        AND commercial_outcome_reference IS NOT NULL
        AND razorpay_order_id IS NULL
        AND razorpay_payment_id IS NULL
    )
);

CREATE OR REPLACE FUNCTION business.protect_zero_price_commercial_outcome()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'zero-price commercial outcomes cannot be deleted';
    END IF;
    IF ROW(
        OLD.checkout_intent_id, OLD.tenant_id, OLD.customer_id, OLD.relationship_id,
        OLD.accepted_contract_id, OLD.contract_version, OLD.contract_hash,
        OLD.contract_acceptance_id, OLD.payment_consent_evidence_id,
        OLD.commercial_evidence_id, OLD.agent_type, OLD.bundle_tier,
        OLD.quote_version, OLD.promotion_version, OLD.outcome_reference, OLD.created_at
    ) IS DISTINCT FROM ROW(
        NEW.checkout_intent_id, NEW.tenant_id, NEW.customer_id, NEW.relationship_id,
        NEW.accepted_contract_id, NEW.contract_version, NEW.contract_hash,
        NEW.contract_acceptance_id, NEW.payment_consent_evidence_id,
        NEW.commercial_evidence_id, NEW.agent_type, NEW.bundle_tier,
        NEW.quote_version, NEW.promotion_version, NEW.outcome_reference, NEW.created_at
    ) THEN
        RAISE EXCEPTION 'zero-price commercial outcome identity is immutable';
    END IF;
    IF OLD.status = 'ACTIVATED' AND NEW IS DISTINCT FROM OLD THEN
        RAISE EXCEPTION 'activated zero-price commercial outcomes are immutable';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS protect_zero_price_commercial_outcome
ON business.zero_price_commercial_outcomes;
CREATE TRIGGER protect_zero_price_commercial_outcome
BEFORE UPDATE OR DELETE ON business.zero_price_commercial_outcomes
FOR EACH ROW EXECUTE FUNCTION business.protect_zero_price_commercial_outcome();

GRANT SELECT, INSERT, UPDATE ON business.zero_price_commercial_outcomes TO wbe_app;
