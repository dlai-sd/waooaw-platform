-- 12-billing-engine.sql
-- Implements: architecture/reference/billing/billing-schema-updates.md (D-08)
-- Constitutional: C-007 (Audit Ledger append-only), C-038 (Pro-rata), C-088, C-089, C-090, C-091
-- Authorization: FA-027 (Yogesh Khandge, 2026-07-30)
-- Note: Slot 11 is occupied by 11-platform-registry.sql (GOAL-PLATFORM-REGISTRY).

-- --------------------------------------------------------------------------
-- DB Role: wbe_app
-- --------------------------------------------------------------------------
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'wbe_app') THEN
        CREATE ROLE wbe_app LOGIN PASSWORD 'changeme';
    END IF;
END
$$;

GRANT USAGE ON SCHEMA business, institutional TO wbe_app;

-- --------------------------------------------------------------------------
-- institutional.thread_catalog (C-091 — Thread Catalog Sovereignty)
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS institutional.thread_catalog (
    thread_id                VARCHAR(50)         PRIMARY KEY,
    display_name             VARCHAR(100)        NOT NULL,
    provider                 VARCHAR(100)        NOT NULL,
    unit_description         VARCHAR(100)        NOT NULL,
    raw_cost_inr_paise       INTEGER             NOT NULL DEFAULT 0,
    fx_buffer_pct            NUMERIC(5,2)        NOT NULL DEFAULT 0,
    operational_overhead_pct NUMERIC(5,2)        NOT NULL DEFAULT 0,
    risk_premium_pct         NUMERIC(5,2)        NOT NULL DEFAULT 0,
    total_markup_pct         NUMERIC(5,2)        GENERATED ALWAYS AS
                             (fx_buffer_pct + operational_overhead_pct + risk_premium_pct) STORED,
    marked_up_cost_paise     INTEGER             GENERATED ALWAYS AS
                             (raw_cost_inr_paise + ROUND(raw_cost_inr_paise *
                              (fx_buffer_pct + operational_overhead_pct + risk_premium_pct) / 100)) STORED,
    is_platform_thread       BOOLEAN             NOT NULL DEFAULT FALSE,
    applicable_agents        VARCHAR(50)[]       NOT NULL DEFAULT '{}',
    status                   VARCHAR(20)         NOT NULL DEFAULT 'ACTIVE',
    founder_authorized_at    TIMESTAMPTZ,
    founder_authorized_by    VARCHAR(100),
    last_reviewed_at         TIMESTAMPTZ,
    fx_baseline_inr_per_usd  NUMERIC(8,2),
    notes                    TEXT,
    created_at               TIMESTAMPTZ         NOT NULL DEFAULT NOW(),
    updated_at               TIMESTAMPTZ         NOT NULL DEFAULT NOW()
);

CREATE RULE no_delete_thread_catalog AS
    ON DELETE TO institutional.thread_catalog DO INSTEAD NOTHING;

-- --------------------------------------------------------------------------
-- institutional.bundle_profiles
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS institutional.bundle_profiles (
    id                       UUID                PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_type               VARCHAR(50)         NOT NULL,
    bundle_tier              VARCHAR(20)         NOT NULL,
    bundle_version           INTEGER             NOT NULL DEFAULT 1,
    display_name             VARCHAR(100)        NOT NULL,
    thread_rations           JSONB               NOT NULL,
    infrastructure_share_paise INTEGER           NOT NULL DEFAULT 18000,
    cost_floor_paise         INTEGER             NOT NULL,
    minimum_margin_pct       NUMERIC(5,2),
    available_topups         JSONB               NOT NULL DEFAULT '[]',
    trial_substitutions      JSONB               NOT NULL DEFAULT '{}',
    status                   VARCHAR(20)         NOT NULL DEFAULT 'PENDING_FOUNDER_AUTH',
    founder_authorized_at    TIMESTAMPTZ,
    is_active                BOOLEAN             NOT NULL DEFAULT FALSE,
    created_at               TIMESTAMPTZ         NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_bundle_profile UNIQUE (agent_type, bundle_tier, bundle_version)
);

CREATE INDEX IF NOT EXISTS idx_bundle_profiles_active
    ON institutional.bundle_profiles(agent_type, bundle_tier)
    WHERE is_active = TRUE;

-- --------------------------------------------------------------------------
-- institutional.billing_profiles (C-088 — Agent Billing Profile Requirement)
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS institutional.billing_profiles (
    agent_type                  VARCHAR(50)     PRIMARY KEY,
    wbe_registry_id             VARCHAR(50)     NOT NULL UNIQUE,
    platform_threads            VARCHAR(50)[]   NOT NULL,
    agent_specific_threads      VARCHAR(50)[]   NOT NULL DEFAULT '{}',
    minimum_wallet_requirements JSONB           NOT NULL DEFAULT '{}',
    constitutional_obligations  TEXT[]          NOT NULL DEFAULT '{}',
    status                      VARCHAR(20)     NOT NULL DEFAULT 'PENDING_FOUNDER_AUTH',
    founder_authorized_at       TIMESTAMPTZ,
    founder_authorized_by       VARCHAR(100),
    notes                       TEXT,
    created_at                  TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

-- --------------------------------------------------------------------------
-- business.customer_wallets
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS business.customer_wallets (
    id                  UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    organisation_id     UUID            NOT NULL REFERENCES business.organisations(id),
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    billing_entity_type VARCHAR(20)     NOT NULL DEFAULT 'DIRECT',
    parent_wallet_id    UUID            REFERENCES business.customer_wallets(id),
    CONSTRAINT uq_wallet_org UNIQUE (organisation_id)
);

CREATE INDEX IF NOT EXISTS idx_wallet_org ON business.customer_wallets(organisation_id);
CREATE INDEX IF NOT EXISTS idx_wallet_parent ON business.customer_wallets(parent_wallet_id)
    WHERE parent_wallet_id IS NOT NULL;

-- --------------------------------------------------------------------------
-- business.wallet_buckets
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS business.wallet_buckets (
    id                      UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    wallet_id               UUID        NOT NULL REFERENCES business.customer_wallets(id),
    thread_type             VARCHAR(50) NOT NULL REFERENCES institutional.thread_catalog(thread_id),
    balance_paise           INTEGER     NOT NULL DEFAULT 0 CHECK (balance_paise >= 0),
    reserved_paise          INTEGER     NOT NULL DEFAULT 0 CHECK (reserved_paise >= 0),
    period_start            DATE        NOT NULL,
    period_end              DATE        NOT NULL,
    pacing_mode             VARCHAR(10) NOT NULL DEFAULT 'SPREAD',
    weekly_sub_limit_paise  INTEGER,
    spending_quota_paise    INTEGER,
    employment_contract_id  UUID        REFERENCES business.employment_contracts(id),
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_bucket_wallet_thread_period UNIQUE (wallet_id, thread_type, period_start)
);

CREATE INDEX IF NOT EXISTS idx_bucket_wallet ON business.wallet_buckets(wallet_id, thread_type);
CREATE INDEX IF NOT EXISTS idx_bucket_period ON business.wallet_buckets(period_start, period_end);

ALTER TABLE business.wallet_buckets ENABLE ROW LEVEL SECURITY;
CREATE POLICY wallet_buckets_tenant_isolation ON business.wallet_buckets
    USING (wallet_id IN (
        SELECT id FROM business.customer_wallets
        WHERE organisation_id = current_setting('app.tenant_id')::uuid
    ));
GRANT SELECT ON business.wallet_buckets TO business_app;
GRANT SELECT, INSERT, UPDATE ON business.wallet_buckets TO wbe_app;

-- --------------------------------------------------------------------------
-- business.bucket_reservations (append-only, idempotent)
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS business.bucket_reservations (
    id              UUID        PRIMARY KEY,
    bucket_id       UUID        NOT NULL REFERENCES business.wallet_buckets(id),
    reserved_paise  INTEGER     NOT NULL CHECK (reserved_paise > 0),
    reserved_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    consumed        BOOLEAN,
    consumed_at     TIMESTAMPTZ,
    expires_at      TIMESTAMPTZ NOT NULL DEFAULT (NOW() + INTERVAL '5 minutes'),
    thread_type     VARCHAR(50) NOT NULL,
    customer_id     UUID        NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_reservation_bucket
    ON business.bucket_reservations(bucket_id) WHERE consumed IS NULL;
CREATE INDEX IF NOT EXISTS idx_reservation_expires
    ON business.bucket_reservations(expires_at) WHERE consumed IS NULL;

CREATE RULE no_delete_reservations AS
    ON DELETE TO business.bucket_reservations DO INSTEAD NOTHING;

-- --------------------------------------------------------------------------
-- business.topup_orders
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS business.topup_orders (
    id                      UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    organisation_id         UUID        NOT NULL REFERENCES business.organisations(id),
    employment_contract_id  UUID        NOT NULL REFERENCES business.employment_contracts(id),
    topup_type              VARCHAR(50) NOT NULL,
    thread_type             VARCHAR(50),
    quantity                INTEGER     NOT NULL DEFAULT 1,
    amount_paise            INTEGER     NOT NULL,
    gst_amount_paise        INTEGER     NOT NULL,
    razorpay_payment_id     VARCHAR(100),
    razorpay_order_id       VARCHAR(100),
    status                  VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    captured_at             TIMESTAMPTZ,
    applied_at              TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_topup_org ON business.topup_orders(organisation_id, created_at DESC);

-- --------------------------------------------------------------------------
-- business.pacing_preferences
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS business.pacing_preferences (
    id                      UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    organisation_id         UUID        NOT NULL REFERENCES business.organisations(id),
    employment_contract_id  UUID        NOT NULL REFERENCES business.employment_contracts(id),
    thread_type             VARCHAR(50) NOT NULL,
    period_start            DATE        NOT NULL,
    pacing_mode             VARCHAR(10) NOT NULL,
    stamped_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    stamped_via             VARCHAR(20) NOT NULL DEFAULT 'WHATSAPP',
    CONSTRAINT uq_pacing_pref UNIQUE (employment_contract_id, thread_type, period_start)
);

-- --------------------------------------------------------------------------
-- business.price_change_notices (C-090 — Grandfather Pricing Protection)
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS business.price_change_notices (
    id                                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    organisation_id                     UUID        NOT NULL REFERENCES business.organisations(id),
    employment_contract_id              UUID        NOT NULL REFERENCES business.employment_contracts(id),
    old_price_paise                     INTEGER     NOT NULL,
    new_price_paise                     INTEGER     NOT NULL,
    effective_date                      DATE        NOT NULL,
    notice_sent_at                      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    notice_channel                      VARCHAR(20) NOT NULL DEFAULT 'WHATSAPP',
    whatsapp_delivery_confirmed_at      TIMESTAMPTZ,
    acknowledgment_at                   TIMESTAMPTZ,
    customer_cancelled_at               TIMESTAMPTZ,
    CONSTRAINT chk_notice_30_days CHECK (effective_date >= (notice_sent_at::date + 30))
);

CREATE RULE no_update_price_change_notices AS
    ON UPDATE TO business.price_change_notices DO INSTEAD NOTHING;
CREATE RULE no_delete_price_change_notices AS
    ON DELETE TO business.price_change_notices DO INSTEAD NOTHING;

-- --------------------------------------------------------------------------
-- institutional.pricing_floor_log (C-089 — Constitutional Minimum Margin)
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS institutional.pricing_floor_log (
    id                                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_type                          VARCHAR(50) NOT NULL,
    bundle_tier                         VARCHAR(20) NOT NULL,
    proposed_price_paise                INTEGER     NOT NULL,
    cost_floor_paise                    INTEGER     NOT NULL,
    constitutional_minimum_margin_pct   NUMERIC(5,2) NOT NULL,
    minimum_compliant_price_paise       INTEGER     NOT NULL,
    outcome                             VARCHAR(10) NOT NULL,
    evaluated_at                        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    evaluated_by                        VARCHAR(50) NOT NULL DEFAULT 'WBE_MARKUP_ENGINE'
);

-- --------------------------------------------------------------------------
-- institutional.provider_accounts
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS institutional.provider_accounts (
    id                          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    provider_name               VARCHAR(50) NOT NULL UNIQUE,
    display_name                VARCHAR(100) NOT NULL,
    balance_paise               INTEGER     NOT NULL DEFAULT 0,
    currency                    VARCHAR(3)  NOT NULL DEFAULT 'INR',
    last_balance_update_at      TIMESTAMPTZ,
    daily_burn_rate_paise       INTEGER,
    low_balance_threshold_days  INTEGER     NOT NULL DEFAULT 7,
    founder_action_template     VARCHAR(100),
    last_fa_triggered_at        TIMESTAMPTZ,
    notes                       TEXT,
    is_active                   BOOLEAN     NOT NULL DEFAULT TRUE,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- --------------------------------------------------------------------------
-- institutional.platform_cost_ledger (C-007 — append-only)
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS institutional.platform_cost_ledger (
    id                          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    provider_account_id         UUID        NOT NULL REFERENCES institutional.provider_accounts(id),
    thread_type                 VARCHAR(50) NOT NULL,
    customer_id                 UUID,
    agent_type                  VARCHAR(50),
    employment_contract_id      UUID,
    bucket_reservation_id       UUID,
    raw_cost_usd_cents          INTEGER,
    raw_cost_inr_paise          INTEGER     NOT NULL,
    fx_rate_inr_per_usd         NUMERIC(8,2),
    marked_up_cost_inr_paise    INTEGER     NOT NULL,
    billing_period_start        DATE        NOT NULL,
    recorded_at                 TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_cost_positive CHECK (raw_cost_inr_paise >= 0)
);

CREATE INDEX IF NOT EXISTS idx_cost_ledger_period
    ON institutional.platform_cost_ledger (billing_period_start, agent_type);
CREATE INDEX IF NOT EXISTS idx_cost_ledger_customer
    ON institutional.platform_cost_ledger (customer_id, billing_period_start)
    WHERE customer_id IS NOT NULL;

CREATE RULE no_update_cost_ledger AS
    ON UPDATE TO institutional.platform_cost_ledger DO INSTEAD NOTHING;
CREATE RULE no_delete_cost_ledger AS
    ON DELETE TO institutional.platform_cost_ledger DO INSTEAD NOTHING;

-- --------------------------------------------------------------------------
-- Amendments to existing tables (additive only — ADR-011)
-- --------------------------------------------------------------------------
ALTER TABLE business.organisations
    ADD COLUMN IF NOT EXISTS billing_entity_type        VARCHAR(20) NOT NULL DEFAULT 'DIRECT',
    ADD COLUMN IF NOT EXISTS parent_organisation_id     UUID REFERENCES business.organisations(id);

ALTER TABLE business.employment_contracts
    ADD COLUMN IF NOT EXISTS agreed_monthly_price_paise     INTEGER,
    ADD COLUMN IF NOT EXISTS price_change_notice_sent_at    TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS price_change_effective_date    DATE;

ALTER TABLE business.subscription_tiers
    ADD COLUMN IF NOT EXISTS bundle_version                 INTEGER NOT NULL DEFAULT 1,
    ADD COLUMN IF NOT EXISTS cost_floor_paise               INTEGER,
    ADD COLUMN IF NOT EXISTS billing_profile_agent_type     VARCHAR(50);

-- --------------------------------------------------------------------------
-- Grants
-- --------------------------------------------------------------------------
GRANT SELECT, INSERT, UPDATE ON business.customer_wallets TO wbe_app;
GRANT SELECT, INSERT, UPDATE ON business.wallet_buckets TO wbe_app;
GRANT SELECT, INSERT, UPDATE ON business.bucket_reservations TO wbe_app;
GRANT SELECT, INSERT ON business.topup_orders TO wbe_app;
GRANT SELECT, INSERT ON business.pacing_preferences TO wbe_app;
GRANT SELECT, INSERT ON business.price_change_notices TO wbe_app;
GRANT SELECT ON business.organisations TO wbe_app;
GRANT SELECT ON business.employment_contracts TO wbe_app;
GRANT SELECT ON business.subscription_tiers TO wbe_app;
GRANT SELECT ON institutional.thread_catalog TO wbe_app;
GRANT SELECT ON institutional.bundle_profiles TO wbe_app;
GRANT SELECT ON institutional.billing_profiles TO wbe_app;
GRANT SELECT, INSERT, UPDATE ON institutional.provider_accounts TO wbe_app;
GRANT SELECT, INSERT ON institutional.platform_cost_ledger TO wbe_app;
GRANT SELECT, INSERT ON institutional.pricing_floor_log TO wbe_app;
GRANT UPDATE ON business.employment_contracts TO wbe_app;

-- --------------------------------------------------------------------------
-- Seed: Thread Catalog (D-06 — all 24 thread entries)
-- --------------------------------------------------------------------------
INSERT INTO institutional.thread_catalog
    (thread_id, display_name, provider, unit_description,
     raw_cost_inr_paise, fx_buffer_pct, operational_overhead_pct, risk_premium_pct,
     is_platform_thread, applicable_agents, status, founder_authorized_at,
     founder_authorized_by, fx_baseline_inr_per_usd)
VALUES
-- Platform threads
('llm_local',           'Local LLM (Ollama)',         'Self-hosted',         'Per message classified',     0, 0,   0,  0, TRUE, '{}',                    'ACTIVE', NOW(), 'Yogesh Khandge', NULL),
('llm_mid_gemini',      'Gemini 2.0 Flash',           'Google Vertex AI',    'Per 1K tokens (in+out)',     2, 5.0, 8.0,3.0,TRUE, '{}',                    'ACTIVE', NOW(), 'Yogesh Khandge', 87.00),
('llm_mid_sarvam',      'Sarvam Saaras',              'Sarvam AI',           'Per 1K tokens',              2, 0,   8.0,5.0,TRUE, '{"agricultural_v2"}',   'ACTIVE', NOW(), 'Yogesh Khandge', NULL),
('llm_frontier_gemini', 'Gemini 2.5 Pro',             'Google Vertex AI',    'Per 1K tokens (in+out)',    18, 5.0, 8.0,3.0,TRUE, '{}',                    'ACTIVE', NOW(), 'Yogesh Khandge', 87.00),
('llm_frontier_gpt4o',  'GPT-4o',                     'Azure OpenAI UAE',    'Per 1K tokens',             22, 0,   8.0,5.0,TRUE, '{}',                    'ACTIVE', NOW(), 'Yogesh Khandge', NULL),
('whatsapp_window',     'WhatsApp (Exotel/360Dialog)', 'Exotel / 360Dialog', 'Per 24-hour window',        60, 0,  17.0,0,   TRUE, '{}',                    'ACTIVE', NOW(), 'Yogesh Khandge', NULL),
('infra_share',         'Platform Infrastructure',     'Azure',              'Per customer/month',     15000, 0,  20.0,0,   TRUE, '{}',                    'ACTIVE', NOW(), 'Yogesh Khandge', NULL),
-- DMA-specific threads
('video_kling_clip',    'Kling AI Video Clip',         'Kling AI',           'Per 5-second clip',       1500, 5.0, 5.0,5.0,FALSE,'{"dma_v3"}',            'PENDING_FOUNDER_AUTH', NULL, NULL, 87.00),
('video_heygen_minute', 'HeyGen Avatar Minute',        'HeyGen',             'Per minute avatar video', 1250, 5.0, 5.0,5.0,FALSE,'{"dma_v3"}',            'PENDING_FOUNDER_AUTH', NULL, NULL, 87.00),
('video_heygen_monthly','HeyGen Monthly Platform',     'HeyGen',             'Monthly (1 seat)',      250000, 5.0, 5.0,0,   FALSE,'{"dma_v3"}',            'PENDING_FOUNDER_AUTH', NULL, NULL, 87.00),
('voice_elevenlabs_monthly','ElevenLabs Voice Monthly','ElevenLabs',         'Monthly Starter 30K chars',50000,5.0,5.0,0,  FALSE,'{"dma_v3"}',            'PENDING_FOUNDER_AUTH', NULL, NULL, 87.00),
('video_runway_credit', 'Runway ML Credit',            'Runway ML',          'Per generation credit',   2500, 5.0, 5.0,5.0,FALSE,'{"dma_v3"}',            'PENDING_FOUNDER_AUTH', NULL, NULL, 87.00),
('image_gen_per_image', 'Image Generation',            'Kling AI / SD',      'Per image',               200,  5.0, 5.0,5.0,FALSE,'{"dma_v3"}',            'ACTIVE', NOW(), 'Yogesh Khandge', 87.00),
('ad_spend_meta',       'Meta Ads (pass-through)',     'Meta Ads',           'INR paise (pass-through)',  0, 0, 0, 0,     FALSE,'{"dma_v3"}',            'ACTIVE', NOW(), 'Yogesh Khandge', NULL),
('ad_spend_google',     'Google Ads (pass-through)',   'Google Ads',         'INR paise (pass-through)',  0, 0, 0, 0,     FALSE,'{"dma_v3"}',            'ACTIVE', NOW(), 'Yogesh Khandge', NULL),
-- Trading-specific threads
('market_data_zerodha', 'Zerodha Kite Connect Monthly','Zerodha',            'Monthly subscription',  200000, 0, 10.0,0,  FALSE,'{"trading_v1"}',         'ACTIVE', NOW(), 'Yogesh Khandge', NULL),
('market_data_zerodha_call','Zerodha API Call',        'Zerodha',            'Per API call (amortised)',20,  0, 10.0,0,   FALSE,'{"trading_v1"}',         'ACTIVE', NOW(), 'Yogesh Khandge', NULL),
('charting_per_chart',  'Chart Render',                'TradingView/in-house','Per chart render',         50, 0, 15.0,0,  FALSE,'{"trading_v1"}',         'ACTIVE', NOW(), 'Yogesh Khandge', NULL),
-- Agricultural-specific threads (all free gov portals)
('climate_data_imd',   'IMD Weather Data',             'India Met Dept',     'Per API call',              0, 0, 0, 0,     FALSE,'{"agricultural_v2"}',   'ACTIVE', NOW(), 'Yogesh Khandge', NULL),
('crop_prices_agmarknet','Agmarknet Crop Prices',      'Agmarknet',          'Per query',                 0, 0, 0, 0,     FALSE,'{"agricultural_v2"}',   'ACTIVE', NOW(), 'Yogesh Khandge', NULL),
('scheme_data_pm_kisan','PM-KISAN/NABARD Scheme Data', 'Govt. Portal',       'Per query',                 0, 0, 0, 0,     FALSE,'{"agricultural_v2"}',   'ACTIVE', NOW(), 'Yogesh Khandge', NULL),
('soil_data_icar',     'ICAR Soil Data',               'ICAR',               'Per query',                 0, 0, 0, 0,     FALSE,'{"agricultural_v2"}',   'ACTIVE', NOW(), 'Yogesh Khandge', NULL),
-- Private Tutor-specific threads
('syllabus_cbse',      'CBSE Syllabus Data',           'CBSE (maintained)',  'Monthly maintenance cost', 500, 0, 10.0,0,  FALSE,'{"private_tutor_v1"}', 'ACTIVE', NOW(), 'Yogesh Khandge', NULL),
('syllabus_state_boards','State Board Syllabus',       'State portals',      'Monthly maintenance cost',1000, 0, 10.0,0,  FALSE,'{"private_tutor_v1"}', 'ACTIVE', NOW(), 'Yogesh Khandge', NULL),
('image_whiteboard',   'Whiteboard Diagram',            'In-house / SD',     'Per diagram render',       200,  0, 15.0,0,  FALSE,'{"private_tutor_v1"}', 'ACTIVE', NOW(), 'Yogesh Khandge', NULL)
ON CONFLICT (thread_id) DO NOTHING;

-- --------------------------------------------------------------------------
-- Seed: Billing Profiles (C-088 — four agent types)
-- --------------------------------------------------------------------------
INSERT INTO institutional.billing_profiles
    (agent_type, wbe_registry_id, platform_threads, agent_specific_threads,
     minimum_wallet_requirements, constitutional_obligations,
     status, founder_authorized_at, founder_authorized_by)
VALUES
('dma_v3', 'dma_v3',
 ARRAY['llm_local','llm_mid_gemini','llm_frontier_gemini','whatsapp_window','infra_share'],
 ARRAY['video_kling_clip','video_heygen_minute','voice_elevenlabs_monthly','image_gen_per_image','ad_spend_meta','ad_spend_google'],
 '{"ad_spend": {"starter": 200000, "runner": 300000, "winner": 500000}}'::jsonb,
 ARRAY['C-056 ad spend transparency', 'C-043 financial spend ceiling'],
 'FOUNDER_AUTHORIZED', NOW(), 'Yogesh Khandge'),

('trading_v1', 'trading_v1',
 ARRAY['llm_local','llm_mid_gemini','llm_frontier_gemini','whatsapp_window','infra_share'],
 ARRAY['market_data_zerodha','market_data_zerodha_call','charting_per_chart'],
 '{}'::jsonb,
 ARRAY['C-043 daily loss limit as constitutional floor'],
 'FOUNDER_AUTHORIZED', NOW(), 'Yogesh Khandge'),

('agricultural_v2', 'agricultural_v2',
 ARRAY['llm_local','llm_mid_sarvam','llm_mid_gemini','whatsapp_window','infra_share'],
 ARRAY['climate_data_imd','crop_prices_agmarknet','scheme_data_pm_kisan','soil_data_icar'],
 '{}'::jsonb,
 ARRAY['C-042 vocabulary mandate — language quality cannot be compromised for cost'],
 'FOUNDER_AUTHORIZED', NOW(), 'Yogesh Khandge'),

('private_tutor_v1', 'private_tutor_v1',
 ARRAY['llm_local','llm_mid_gemini','llm_frontier_gemini','whatsapp_window','infra_share'],
 ARRAY['syllabus_cbse','syllabus_state_boards','image_whiteboard'],
 '{}'::jsonb,
 ARRAY['C-060 minor student protection — billing NEVER surfaced to student'],
 'FOUNDER_AUTHORIZED', NOW(), 'Yogesh Khandge')
ON CONFLICT (agent_type) DO NOTHING;

-- --------------------------------------------------------------------------
-- Seed: Provider Accounts
-- --------------------------------------------------------------------------
INSERT INTO institutional.provider_accounts
    (provider_name, display_name, currency, low_balance_threshold_days, founder_action_template)
VALUES
('kling_ai',      'Kling AI (Video Generation)',     'USD', 7,  'FA-012'),
('heygen',        'HeyGen (Avatar Video)',            'USD', 7,  'FA-013'),
('elevenlabs',    'ElevenLabs (Voice Synthesis)',     'USD', 7,  'FA-014'),
('runway_ml',     'Runway ML (Premium Video)',        'USD', 7,  'FA-015'),
('vertex_ai',     'Google Vertex AI (LLM)',           'USD', 14, 'FA-021'),
('sarvam_ai',     'Sarvam AI (Indian Languages)',     'USD', 7,  'FA-022'),
('whatsapp_bsp',  'WhatsApp BSP (Exotel/360Dialog)',  'INR', 7,  NULL),
('meta_mbm',      'Meta Business Manager',            'INR', 14, 'FA-002'),
('google_mcc',    'Google Ads MCC',                   'INR', 14, NULL)
ON CONFLICT (provider_name) DO NOTHING;

-- ---------------------------------------------------------------------------
-- institutional.meter_alert_log (Amendment WC-028 — deduplication for §2.3a)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS institutional.meter_alert_log (
    id              BIGSERIAL       PRIMARY KEY,
    customer_id     UUID            NOT NULL,
    bucket_type     VARCHAR(50)     NOT NULL,
    threshold_name  VARCHAR(30)     NOT NULL,
    period_id       VARCHAR(7)      NOT NULL,  -- YYYY-MM billing month
    fired_at        TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_alert_dedup UNIQUE (customer_id, bucket_type, threshold_name, period_id)
);

CREATE INDEX IF NOT EXISTS idx_alert_log_customer
    ON institutional.meter_alert_log (customer_id, period_id);

GRANT SELECT, INSERT, DELETE ON institutional.meter_alert_log TO wbe_app;
GRANT USAGE, SELECT ON SEQUENCE institutional.meter_alert_log_id_seq TO wbe_app;
