-- Stores server-created Razorpay orders until signed payment confirmation arrives.
-- Constitutional basis: C-023 (Evidence First), C-059 (Implementation Traceability)

CREATE TABLE IF NOT EXISTS business.razorpay_checkout_orders (
    checkout_intent_id UUID PRIMARY KEY,
    razorpay_order_id VARCHAR(128) NOT NULL UNIQUE,
    tenant_id UUID NOT NULL,
    customer_id UUID NOT NULL,
    relationship_id UUID NOT NULL,
    accepted_contract_id UUID NOT NULL,
    contract_version INTEGER NOT NULL CHECK (contract_version > 0),
    contract_hash VARCHAR(64) NOT NULL CHECK (contract_hash ~ '^[0-9a-f]{64}$'),
    contract_acceptance_id UUID NOT NULL,
    payment_consent_evidence_id UUID NOT NULL,
    agent_type VARCHAR(64) NOT NULL,
    bundle_tier VARCHAR(64) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

GRANT SELECT, INSERT ON business.razorpay_checkout_orders TO wbe_app;
