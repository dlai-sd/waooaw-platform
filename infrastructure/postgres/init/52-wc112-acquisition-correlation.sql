-- Implements: WC-112 R003
-- Constitutional basis: C-023, C-059, C-063

ALTER TABLE business.pre_hire_checkout_orders
    ADD COLUMN IF NOT EXISTS correlation_id UUID;

UPDATE business.pre_hire_checkout_orders
SET correlation_id = checkout_intent_id
WHERE correlation_id IS NULL;

ALTER TABLE business.pre_hire_checkout_orders
    ALTER COLUMN correlation_id SET NOT NULL;

CREATE INDEX IF NOT EXISTS idx_pre_hire_checkout_correlation
    ON business.pre_hire_checkout_orders (correlation_id);
