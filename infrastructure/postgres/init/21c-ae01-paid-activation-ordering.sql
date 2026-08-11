-- Implements: work-contracts/WC-059-goal005-ae01-contract-payment-activation.md §WC059-06
-- constitutional_basis: C-002, C-023, C-059, C-088

ALTER TABLE business.payment_intents
    ADD COLUMN IF NOT EXISTS tenant_id UUID,
    ADD COLUMN IF NOT EXISTS relationship_id UUID,
    ADD COLUMN IF NOT EXISTS accepted_contract_id UUID,
    ADD COLUMN IF NOT EXISTS contract_version INTEGER,
    ADD COLUMN IF NOT EXISTS contract_hash VARCHAR(64),
    ADD COLUMN IF NOT EXISTS contract_acceptance_id UUID,
    ADD COLUMN IF NOT EXISTS payment_consent_evidence_id UUID,
    ADD COLUMN IF NOT EXISTS payment_evidence_id UUID,
    ADD COLUMN IF NOT EXISTS agent_type VARCHAR(64),
    ADD COLUMN IF NOT EXISTS bundle_tier VARCHAR(64),
    ADD COLUMN IF NOT EXISTS activation_intent_id UUID,
    ADD COLUMN IF NOT EXISTS activation_correlation_id UUID,
    ADD COLUMN IF NOT EXISTS outcome_subscription_id UUID;

ALTER TABLE business.payment_intents DROP CONSTRAINT IF EXISTS payment_intents_status_check;
ALTER TABLE business.payment_intents ADD CONSTRAINT payment_intents_status_check CHECK (
    status IN ('IN_PROGRESS', 'CAPTURED', 'ACTIVATION_IN_PROGRESS', 'ACTIVATED', 'FAILED', 'FAILED_RETRYABLE')
);
ALTER TABLE business.payment_intents DROP CONSTRAINT IF EXISTS payment_intents_relationship_material_check;
ALTER TABLE business.payment_intents ADD CONSTRAINT payment_intents_relationship_material_check CHECK (
    relationship_id IS NULL OR (
        tenant_id IS NOT NULL
        AND accepted_contract_id IS NOT NULL
        AND contract_version IS NOT NULL AND contract_version > 0
        AND contract_hash ~ '^[0-9a-f]{64}$'
        AND contract_acceptance_id IS NOT NULL
        AND payment_consent_evidence_id IS NOT NULL
        AND payment_evidence_id IS NOT NULL
        AND agent_type IS NOT NULL
        AND bundle_tier IS NOT NULL
    )
);
CREATE TABLE IF NOT EXISTS business.paid_subscriptions (
    subscription_id       UUID         PRIMARY KEY,
    organisation_id       UUID         NOT NULL REFERENCES business.organisations(id),
    agent_type            VARCHAR(64)  NOT NULL,
    bundle_tier           VARCHAR(64)  NOT NULL,
    razorpay_order_id     VARCHAR(128) NOT NULL,
    razorpay_payment_id   VARCHAR(128) NOT NULL UNIQUE,
    activated_at          TIMESTAMPTZ  NOT NULL
);

GRANT SELECT, INSERT, UPDATE ON business.payment_intents TO wbe_app;
GRANT SELECT, INSERT ON business.paid_subscriptions TO wbe_app;