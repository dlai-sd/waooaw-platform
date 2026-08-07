-- Implements: work-contracts/WC-042-wbe-s7-onboarding-payment-renewal-saga.md §WC042-02
-- constitutional_basis: C-059, C-002 (idempotency), C-090 (grandfather pricing)

-- payment_intents: idempotency record for Razorpay payment.captured webhook events.
-- Prevents double-activation on webhook retries. INSERT-only after ACTIVATED status.
CREATE TABLE IF NOT EXISTS business.payment_intents (
    razorpay_payment_id  VARCHAR(64)  PRIMARY KEY,
    razorpay_order_id    VARCHAR(64)  NOT NULL,
    customer_id          UUID         NOT NULL,
    status               VARCHAR(20)  NOT NULL DEFAULT 'IN_PROGRESS',
    created_at           TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    activated_at         TIMESTAMPTZ,
    CONSTRAINT payment_intents_status_check CHECK (status IN ('IN_PROGRESS', 'ACTIVATED', 'FAILED'))
);

CREATE INDEX IF NOT EXISTS idx_payment_intents_customer ON business.payment_intents(customer_id);

GRANT SELECT, INSERT, UPDATE ON business.payment_intents TO wbe_app;

-- Seed 100% discount coupons for demo and UAT environments. FA-029.
-- These coupons are valid indefinitely in lower environments only (WAOOAW_ENVIRONMENT gate in code).
INSERT INTO business.coupon_codes
    (coupon_id, code, discount_pct, bonus_credits_paise, agent_type, min_bundle_tier,
     max_uses, uses_count, valid_from, valid_until, is_active)
VALUES
    (gen_random_uuid(), 'DEMOWAOOAW', 100, 0, NULL, NULL,
     999999, 0, NOW(), '2099-12-31'::TIMESTAMPTZ, TRUE),
    (gen_random_uuid(), 'UATWAOOAW', 100, 0, NULL, NULL,
     999999, 0, NOW(), '2099-12-31'::TIMESTAMPTZ, TRUE)
ON CONFLICT (code) DO NOTHING;
