-- Stores payment outcomes created after Marketplace consent and before Hire setup.
-- Constitutional basis: C-002 (idempotency), C-023 (Evidence First), C-059 (traceability)

CREATE TABLE IF NOT EXISTS business.pre_hire_checkout_orders (
    checkout_intent_id UUID PRIMARY KEY,
    customer_id UUID NOT NULL,
    professional_type VARCHAR(64) NOT NULL,
    professional_version VARCHAR(32) NOT NULL,
    disclosure_revision VARCHAR(32) NOT NULL,
    terms_version VARCHAR(32) NOT NULL,
    cadence VARCHAR(32) NOT NULL,
    list_price_inr_paise BIGINT NOT NULL CHECK (list_price_inr_paise > 0),
    discount_inr_paise BIGINT NOT NULL CHECK (discount_inr_paise >= 0),
    tax_inr_paise BIGINT NOT NULL CHECK (tax_inr_paise >= 0),
    payable_inr_paise BIGINT NOT NULL CHECK (payable_inr_paise >= 0),
    coupon_code VARCHAR(64),
    razorpay_order_id VARCHAR(128) UNIQUE,
    razorpay_payment_id VARCHAR(128) UNIQUE,
    commercial_evidence_id UUID,
    relationship_id UUID UNIQUE,
    contract_checkout_intent_id UUID UNIQUE,
    status VARCHAR(32) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT pre_hire_checkout_amounts_match CHECK (
        discount_inr_paise <= list_price_inr_paise
        AND payable_inr_paise = list_price_inr_paise - discount_inr_paise
    ),
    CONSTRAINT pre_hire_checkout_status_check CHECK (
        status IN ('CREATING', 'AWAITING_PROVIDER', 'CAPTURED', 'FULLY_DISCOUNTED', 'UNRESOLVED')
    )
);

ALTER TABLE business.pre_hire_checkout_orders
    ADD COLUMN IF NOT EXISTS contract_checkout_intent_id UUID UNIQUE;

CREATE INDEX IF NOT EXISTS idx_pre_hire_checkout_customer
    ON business.pre_hire_checkout_orders(customer_id, created_at DESC);

GRANT SELECT, INSERT, UPDATE ON business.pre_hire_checkout_orders TO wbe_app;