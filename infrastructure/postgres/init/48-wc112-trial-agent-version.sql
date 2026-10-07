-- Implements: WC-112 R032, R053
-- Constitutional basis: C-059, C-088

ALTER TABLE business.trial_allocations
    ADD COLUMN IF NOT EXISTS agent_version VARCHAR(32) NOT NULL DEFAULT '1.0.0';

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conrelid = 'business.trial_allocations'::regclass
          AND conname = 'trial_one_per_agent'
    ) THEN
        ALTER TABLE business.trial_allocations
            DROP CONSTRAINT trial_one_per_agent;
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conrelid = 'business.trial_allocations'::regclass
          AND conname = 'trial_one_per_agent_version'
    ) THEN
        ALTER TABLE business.trial_allocations
            ADD CONSTRAINT trial_one_per_agent_version
            UNIQUE (customer_id, agent_type, agent_version);
    END IF;
END $$;

ALTER TABLE business.trial_allocations
    DROP CONSTRAINT IF EXISTS trial_allocations_agent_version_check;

ALTER TABLE business.trial_allocations
    ADD CONSTRAINT trial_allocations_agent_version_check
    CHECK (agent_version ~ '^[0-9]+\.[0-9]+\.[0-9]+$');

ALTER TABLE business.coupon_codes
    ADD COLUMN IF NOT EXISTS agent_version VARCHAR(32);

ALTER TABLE business.coupon_codes
    ALTER COLUMN agent_type TYPE VARCHAR(64);

ALTER TABLE business.coupon_codes
    DROP CONSTRAINT IF EXISTS coupon_codes_agent_version_check;

ALTER TABLE business.coupon_codes
    ADD CONSTRAINT coupon_codes_agent_version_check
    CHECK (agent_version IS NULL OR agent_version ~ '^[0-9]+\.[0-9]+\.[0-9]+$');

UPDATE business.coupon_codes
SET agent_type = 'DIGITAL_MARKETING_LOCAL_SERVICE',
    agent_version = '1.0.0'
WHERE code = 'DEMO100';

CREATE TABLE IF NOT EXISTS business.agent_trial_policies (
    agent_type VARCHAR(50) NOT NULL,
    agent_version VARCHAR(32) NOT NULL,
    duration_days SMALLINT NOT NULL CHECK (duration_days BETWEEN 1 AND 90),
    authorized_by TEXT NOT NULL CHECK (authorized_by = 'founder'),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (agent_type, agent_version)
);

GRANT SELECT ON business.agent_trial_policies TO wbe_app;
