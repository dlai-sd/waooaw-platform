-- 13-customer-acquisition.sql
-- Implements: architecture/reference/billing/customer-acquisition-spec.md (GOAL-005 D-01)
-- Constitutional: C-088 (trial is a billing mode), C-089 (trial costs tracked), C-090 (trial→paid conversion), C-059 (traceability)
-- Authorization: BLOCKED — requires Founder FA (pricing decisions) before this migration runs
-- Note: Slot 12 is occupied by 12-billing-engine.sql.

-- --------------------------------------------------------------------------
-- DB Role: wbe_app already exists (created in 12-billing-engine.sql)
-- --------------------------------------------------------------------------
GRANT USAGE ON SCHEMA business TO wbe_app;

-- --------------------------------------------------------------------------
-- business.trial_allocations — one trial per customer per agent type
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS business.trial_allocations (
    trial_id            UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id         UUID            NOT NULL REFERENCES institutional.billing_profiles(customer_id),
    agent_type          VARCHAR(20)     NOT NULL CHECK (agent_type IN ('DMA','DPA','DCA','DSA')),
    started_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    expires_at          TIMESTAMPTZ     NOT NULL,
    status              VARCHAR(10)     NOT NULL DEFAULT 'ACTIVE'
                            CHECK (status IN ('ACTIVE','EXPIRED','CONVERTED')),
    converted_at        TIMESTAMPTZ,
    new_subscription_id UUID,
    CONSTRAINT trial_one_per_agent UNIQUE (customer_id, agent_type)
);

CREATE INDEX IF NOT EXISTS idx_trial_customer_status
    ON business.trial_allocations (customer_id, status);

-- --------------------------------------------------------------------------
-- business.trial_free_unit_ledger — per-thread-type quota tracking
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS business.trial_free_unit_ledger (
    id              SERIAL          PRIMARY KEY,
    trial_id        UUID            NOT NULL REFERENCES business.trial_allocations(trial_id) ON DELETE CASCADE,
    thread_type     VARCHAR(50)     NOT NULL,
    units_granted   INTEGER         NOT NULL CHECK (units_granted > 0),
    units_consumed  INTEGER         NOT NULL DEFAULT 0 CHECK (units_consumed >= 0),
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    CONSTRAINT trial_unit_not_exceed_granted CHECK (units_consumed <= units_granted),
    UNIQUE (trial_id, thread_type)
);

-- --------------------------------------------------------------------------
-- business.coupon_codes — discount + bonus credit codes
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS business.coupon_codes (
    coupon_id       UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    code            VARCHAR(20)     NOT NULL UNIQUE,
    discount_pct    SMALLINT        NOT NULL DEFAULT 0 CHECK (discount_pct BETWEEN 0 AND 100),
    bonus_credits   JSONB           NOT NULL DEFAULT '{}',
    agent_type      VARCHAR(20),                                     -- NULL = all agents
    min_tier        VARCHAR(20),                                     -- NULL = all tiers
    max_uses        INTEGER         CHECK (max_uses > 0),            -- NULL = unlimited
    uses_count      INTEGER         NOT NULL DEFAULT 0 CHECK (uses_count >= 0),
    valid_from      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    valid_until     TIMESTAMPTZ,
    created_by      TEXT            NOT NULL DEFAULT 'founder',
    active          BOOLEAN         NOT NULL DEFAULT TRUE
);

CREATE INDEX IF NOT EXISTS idx_coupon_active_code
    ON business.coupon_codes (code) WHERE active = TRUE;

-- --------------------------------------------------------------------------
-- business.referral_records — referral attribution + credit tracking
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS business.referral_records (
    referral_id             UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    referrer_customer_id    UUID        NOT NULL REFERENCES institutional.billing_profiles(customer_id),
    referee_customer_id     UUID        NOT NULL REFERENCES institutional.billing_profiles(customer_id),
    coupon_id               UUID        REFERENCES business.coupon_codes(coupon_id),
    referred_at             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    credit_status           VARCHAR(10) NOT NULL DEFAULT 'PENDING'
                                CHECK (credit_status IN ('PENDING','CREDITED')),
    credit_amount_paise     INTEGER     CHECK (credit_amount_paise > 0),
    credited_at             TIMESTAMPTZ,
    CONSTRAINT referral_one_per_pair UNIQUE (referrer_customer_id, referee_customer_id),
    CONSTRAINT no_self_referral CHECK (referrer_customer_id <> referee_customer_id)
);

CREATE INDEX IF NOT EXISTS idx_referral_referrer
    ON business.referral_records (referrer_customer_id, credit_status);

-- --------------------------------------------------------------------------
-- GRANT permissions
-- --------------------------------------------------------------------------
GRANT SELECT, INSERT, UPDATE ON business.trial_allocations TO wbe_app;
GRANT SELECT, INSERT, UPDATE ON business.trial_free_unit_ledger TO wbe_app;
GRANT SELECT, INSERT, UPDATE ON business.coupon_codes TO wbe_app;
GRANT SELECT, INSERT, UPDATE ON business.referral_records TO wbe_app;
GRANT USAGE ON SEQUENCE business.trial_free_unit_ledger_id_seq TO wbe_app;
