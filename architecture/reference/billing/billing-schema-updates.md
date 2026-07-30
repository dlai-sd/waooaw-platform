# Billing Schema Update Specification — GOAL-004 D-08

**Authority:** Chief Data Architect (INST-006) — GOAL-004 D-08
**WBE Component Spec:** architecture/reference/billing/wbe-component-spec.md
**Architecture Decision:** ADR-034, ADR-022 Amendment 1, ADR-011 (EF Core Migrations)
**Constitutional Basis:** C-007 (Audit Ledger append-only), C-038 (Pro-rata billing),
C-088, C-089, C-090, C-091
**Status:** APPROVED — 2026-07-30
**Migration File:** infrastructure/postgres/init/11-billing-engine.sql (new)

---

## Migration Strategy

All changes are **additive only** (ADR-011 — no destructive migrations on constitutional schema).

Existing tables (`ad_spend_wallets`, `ad_spend_ledger`, `subscription_billing_events`,
`gst_invoices`) are preserved. New tables are added alongside them. Migration from old
to new wallet model is a background data migration job (not a schema migration) run
after WBE is deployed and validated.

Migration order: `11-billing-engine.sql` runs after all existing `01-10-*.sql` files.

---

## New Tables

### institutional.thread_catalog

```sql
CREATE TABLE institutional.thread_catalog (
    thread_id               VARCHAR(50)         PRIMARY KEY,
    display_name            VARCHAR(100)        NOT NULL,
    provider                VARCHAR(100)        NOT NULL,
    unit_description        VARCHAR(100)        NOT NULL,   -- "Per 1K tokens", "Per clip"
    raw_cost_inr_paise      INTEGER             NOT NULL DEFAULT 0,
    fx_buffer_pct           NUMERIC(5,2)        NOT NULL DEFAULT 0,
    operational_overhead_pct NUMERIC(5,2)       NOT NULL DEFAULT 0,
    risk_premium_pct        NUMERIC(5,2)        NOT NULL DEFAULT 0,
    total_markup_pct        NUMERIC(5,2)        GENERATED ALWAYS AS
                            (fx_buffer_pct + operational_overhead_pct + risk_premium_pct)
                            STORED,
    marked_up_cost_paise    INTEGER             GENERATED ALWAYS AS
                            (raw_cost_inr_paise + ROUND(raw_cost_inr_paise *
                             (fx_buffer_pct + operational_overhead_pct + risk_premium_pct) / 100))
                            STORED,
    is_platform_thread      BOOLEAN             NOT NULL DEFAULT FALSE,
    applicable_agents       VARCHAR(50)[]       NOT NULL DEFAULT '{}', -- empty = all agents
    status                  VARCHAR(20)         NOT NULL DEFAULT 'ACTIVE',
                                                -- ACTIVE | DEPRECATED | PENDING_FOUNDER_AUTH
    founder_authorized_at   TIMESTAMPTZ,
    founder_authorized_by   VARCHAR(100),
    last_reviewed_at        TIMESTAMPTZ,
    fx_baseline_inr_per_usd NUMERIC(8,2),       -- exchange rate used for this entry
    notes                   TEXT,
    created_at              TIMESTAMPTZ         NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ         NOT NULL DEFAULT NOW()
);

-- Append-only audit: no DELETE, no UPDATE to cost fields without new authorized entry
CREATE RULE no_delete_thread_catalog AS
    ON DELETE TO institutional.thread_catalog DO INSTEAD NOTHING;
```

### institutional.bundle_profiles

```sql
CREATE TABLE institutional.bundle_profiles (
    id                      UUID                PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_type              VARCHAR(50)         NOT NULL,   -- "dma_v3", "trading_v1"
    bundle_tier             VARCHAR(20)         NOT NULL,   -- "starter", "runner", "winner"
    bundle_version          INTEGER             NOT NULL DEFAULT 1,
    display_name            VARCHAR(100)        NOT NULL,
    thread_rations          JSONB               NOT NULL,   -- {thread_id: quantity}
    infrastructure_share_paise INTEGER          NOT NULL DEFAULT 18000,
    cost_floor_paise        INTEGER             NOT NULL,   -- computed by WBE at profile activation
    minimum_margin_pct      NUMERIC(5,2),                  -- if NULL: use platform default
    available_topups        JSONB               NOT NULL DEFAULT '[]', -- list of topup_type strings
    trial_substitutions     JSONB               NOT NULL DEFAULT '{}', -- {thread_id: substitute_thread_id}
    status                  VARCHAR(20)         NOT NULL DEFAULT 'PENDING_FOUNDER_AUTH',
    founder_authorized_at   TIMESTAMPTZ,
    is_active               BOOLEAN             NOT NULL DEFAULT FALSE,
    created_at              TIMESTAMPTZ         NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_bundle_profile UNIQUE (agent_type, bundle_tier, bundle_version)
);

CREATE INDEX idx_bundle_profiles_active ON institutional.bundle_profiles(agent_type, bundle_tier)
    WHERE is_active = TRUE;
```

### institutional.billing_profiles

```sql
CREATE TABLE institutional.billing_profiles (
    agent_type              VARCHAR(50)         PRIMARY KEY,
    wbe_registry_id         VARCHAR(50)         NOT NULL UNIQUE,
    platform_threads        VARCHAR(50)[]       NOT NULL,
    agent_specific_threads  VARCHAR(50)[]       NOT NULL DEFAULT '{}',
    minimum_wallet_requirements JSONB           NOT NULL DEFAULT '{}',
    -- {"ad_spend": {"starter": 200000, "runner": 300000, "winner": 500000}}
    constitutional_obligations TEXT[]           NOT NULL DEFAULT '{}',
    -- ["C-056 ad spend segregation", "C-060 minor student protection"]
    status                  VARCHAR(20)         NOT NULL DEFAULT 'PENDING_FOUNDER_AUTH',
    founder_authorized_at   TIMESTAMPTZ,
    founder_authorized_by   VARCHAR(100),
    notes                   TEXT,
    created_at              TIMESTAMPTZ         NOT NULL DEFAULT NOW()
);
```

### business.customer_wallets

```sql
CREATE TABLE business.customer_wallets (
    id                      UUID                PRIMARY KEY DEFAULT gen_random_uuid(),
    organisation_id         UUID                NOT NULL REFERENCES business.organisations(id),
    created_at              TIMESTAMPTZ         NOT NULL DEFAULT NOW(),
    billing_entity_type     VARCHAR(20)         NOT NULL DEFAULT 'DIRECT',
                                                -- DIRECT | AGENCY | RESELLER | CHILD
    parent_wallet_id        UUID                REFERENCES business.customer_wallets(id),
    -- NULL for DIRECT customers; FK for agency CHILD wallets
    CONSTRAINT uq_wallet_org UNIQUE (organisation_id)
);

CREATE INDEX idx_wallet_org ON business.customer_wallets(organisation_id);
CREATE INDEX idx_wallet_parent ON business.customer_wallets(parent_wallet_id)
    WHERE parent_wallet_id IS NOT NULL;
```

### business.wallet_buckets

```sql
CREATE TABLE business.wallet_buckets (
    id                      UUID                PRIMARY KEY DEFAULT gen_random_uuid(),
    wallet_id               UUID                NOT NULL REFERENCES business.customer_wallets(id),
    thread_type             VARCHAR(50)         NOT NULL REFERENCES institutional.thread_catalog(thread_id),
    balance_paise           INTEGER             NOT NULL DEFAULT 0 CHECK (balance_paise >= 0),
    reserved_paise          INTEGER             NOT NULL DEFAULT 0 CHECK (reserved_paise >= 0),
    period_start            DATE                NOT NULL,
    period_end              DATE                NOT NULL,
    pacing_mode             VARCHAR(10)         NOT NULL DEFAULT 'SPREAD', -- SPREAD | BURST
    weekly_sub_limit_paise  INTEGER,            -- NULL if BURST mode or no sub-limit
    spending_quota_paise    INTEGER,            -- NULL = no limit (agency sub-wallet quota)
    employment_contract_id  UUID                REFERENCES business.employment_contracts(id),
    created_at              TIMESTAMPTZ         NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ         NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_bucket_wallet_thread_period UNIQUE (wallet_id, thread_type, period_start)
);

CREATE INDEX idx_bucket_wallet ON business.wallet_buckets(wallet_id, thread_type);
CREATE INDEX idx_bucket_period ON business.wallet_buckets(period_start, period_end);

-- RLS: customers see only their own buckets
ALTER TABLE business.wallet_buckets ENABLE ROW LEVEL SECURITY;
CREATE POLICY wallet_buckets_tenant_isolation ON business.wallet_buckets
    USING (wallet_id IN (
        SELECT id FROM business.customer_wallets
        WHERE organisation_id = current_setting('app.tenant_id')::uuid
    ));
GRANT SELECT ON business.wallet_buckets TO business_app;
GRANT SELECT, INSERT, UPDATE ON business.wallet_buckets TO wbe_app;
```

### business.bucket_reservations

```sql
CREATE TABLE business.bucket_reservations (
    id                      UUID                PRIMARY KEY, -- = idempotency_key from caller
    bucket_id               UUID                NOT NULL REFERENCES business.wallet_buckets(id),
    reserved_paise          INTEGER             NOT NULL CHECK (reserved_paise > 0),
    reserved_at             TIMESTAMPTZ         NOT NULL DEFAULT NOW(),
    consumed                BOOLEAN,            -- NULL=in-flight; TRUE=consumed; FALSE=released
    consumed_at             TIMESTAMPTZ,
    expires_at              TIMESTAMPTZ         NOT NULL DEFAULT (NOW() + INTERVAL '5 minutes'),
    -- Expired reservations are auto-released by WBE reconciliation job
    thread_type             VARCHAR(50)         NOT NULL,
    customer_id             UUID                NOT NULL   -- denormalized for fast audit
);

CREATE INDEX idx_reservation_bucket ON business.bucket_reservations(bucket_id)
    WHERE consumed IS NULL;
CREATE INDEX idx_reservation_expires ON business.bucket_reservations(expires_at)
    WHERE consumed IS NULL;

-- Append-only: consumed/released state transitions only, no DELETE
CREATE RULE no_delete_reservations AS
    ON DELETE TO business.bucket_reservations DO INSTEAD NOTHING;
```

### business.topup_orders

```sql
CREATE TABLE business.topup_orders (
    id                      UUID                PRIMARY KEY DEFAULT gen_random_uuid(),
    organisation_id         UUID                NOT NULL REFERENCES business.organisations(id),
    employment_contract_id  UUID                NOT NULL REFERENCES business.employment_contracts(id),
    topup_type              VARCHAR(50)         NOT NULL,   -- "unit_llm_mid_30", "event_diwali_pack"
    thread_type             VARCHAR(50),                    -- NULL for packs (covers multiple threads)
    quantity                INTEGER             NOT NULL DEFAULT 1,
    amount_paise            INTEGER             NOT NULL,
    gst_amount_paise        INTEGER             NOT NULL,
    razorpay_payment_id     VARCHAR(100),
    razorpay_order_id       VARCHAR(100),
    status                  VARCHAR(20)         NOT NULL DEFAULT 'PENDING',
                                                -- PENDING | CAPTURED | APPLIED | FAILED
    created_at              TIMESTAMPTZ         NOT NULL DEFAULT NOW(),
    captured_at             TIMESTAMPTZ,
    applied_at              TIMESTAMPTZ
    -- Append-only: no UPDATE after status=APPLIED
);

CREATE INDEX idx_topup_org ON business.topup_orders(organisation_id, created_at DESC);
```

### business.pacing_preferences

```sql
CREATE TABLE business.pacing_preferences (
    id                      UUID                PRIMARY KEY DEFAULT gen_random_uuid(),
    organisation_id         UUID                NOT NULL REFERENCES business.organisations(id),
    employment_contract_id  UUID                NOT NULL REFERENCES business.employment_contracts(id),
    thread_type             VARCHAR(50)         NOT NULL,
    period_start            DATE                NOT NULL,
    pacing_mode             VARCHAR(10)         NOT NULL,   -- SPREAD | BURST
    stamped_at              TIMESTAMPTZ         NOT NULL DEFAULT NOW(),
    stamped_via             VARCHAR(20)         NOT NULL DEFAULT 'WHATSAPP',
    CONSTRAINT uq_pacing_pref UNIQUE (employment_contract_id, thread_type, period_start)
);
```

### institutional.provider_accounts

```sql
CREATE TABLE institutional.provider_accounts (
    id                      UUID                PRIMARY KEY DEFAULT gen_random_uuid(),
    provider_name           VARCHAR(50)         NOT NULL UNIQUE,
                                                -- "kling_ai", "heygen", "vertex_ai", etc.
    display_name            VARCHAR(100)        NOT NULL,
    balance_paise           INTEGER             NOT NULL DEFAULT 0,
    currency                VARCHAR(3)          NOT NULL DEFAULT 'INR', -- INR | USD
    last_balance_update_at  TIMESTAMPTZ,
    daily_burn_rate_paise   INTEGER,            -- computed from 7-day average
    low_balance_threshold_days INTEGER          NOT NULL DEFAULT 7,
    founder_action_template VARCHAR(100),       -- FA reference for top-up (e.g. "FA-012")
    last_fa_triggered_at    TIMESTAMPTZ,
    notes                   TEXT,
    is_active               BOOLEAN             NOT NULL DEFAULT TRUE,
    created_at              TIMESTAMPTZ         NOT NULL DEFAULT NOW()
);
```

### institutional.platform_cost_ledger

```sql
CREATE TABLE institutional.platform_cost_ledger (
    id                      UUID                PRIMARY KEY DEFAULT gen_random_uuid(),
    provider_account_id     UUID                NOT NULL REFERENCES institutional.provider_accounts(id),
    thread_type             VARCHAR(50)         NOT NULL,
    customer_id             UUID,               -- NULL for non-attributable platform costs
    agent_type              VARCHAR(50),
    employment_contract_id  UUID,
    bucket_reservation_id   UUID,               -- FK to bucket_reservations (traceability)
    raw_cost_usd_cents      INTEGER,            -- NULL for INR-billed providers
    raw_cost_inr_paise      INTEGER             NOT NULL,
    fx_rate_inr_per_usd     NUMERIC(8,2),       -- NULL for INR-billed
    marked_up_cost_inr_paise INTEGER            NOT NULL,
    billing_period_start    DATE                NOT NULL,
    recorded_at             TIMESTAMPTZ         NOT NULL DEFAULT NOW(),
    -- Append-only: no UPDATE, no DELETE (C-007)
    CONSTRAINT chk_cost_positive CHECK (raw_cost_inr_paise >= 0)
);

CREATE INDEX idx_cost_ledger_period ON institutional.platform_cost_ledger
    (billing_period_start, agent_type);
CREATE INDEX idx_cost_ledger_customer ON institutional.platform_cost_ledger
    (customer_id, billing_period_start)
    WHERE customer_id IS NOT NULL;

CREATE RULE no_update_cost_ledger AS
    ON UPDATE TO institutional.platform_cost_ledger DO INSTEAD NOTHING;
CREATE RULE no_delete_cost_ledger AS
    ON DELETE TO institutional.platform_cost_ledger DO INSTEAD NOTHING;
```

### business.price_change_notices (C-090 enforcement)

```sql
CREATE TABLE business.price_change_notices (
    id                      UUID                PRIMARY KEY DEFAULT gen_random_uuid(),
    organisation_id         UUID                NOT NULL REFERENCES business.organisations(id),
    employment_contract_id  UUID                NOT NULL REFERENCES business.employment_contracts(id),
    old_price_paise         INTEGER             NOT NULL,
    new_price_paise         INTEGER             NOT NULL,
    effective_date          DATE                NOT NULL,   -- must be ≥ notice_sent_at + 30 days
    notice_sent_at          TIMESTAMPTZ         NOT NULL DEFAULT NOW(),
    notice_channel          VARCHAR(20)         NOT NULL DEFAULT 'WHATSAPP',
    whatsapp_delivery_confirmed_at TIMESTAMPTZ,
    acknowledgment_at       TIMESTAMPTZ,        -- NULL until confirmed; set on delivery+silence
    customer_cancelled_at   TIMESTAMPTZ,        -- set if customer cancels in response to notice
    -- Append-only: no UPDATE, no DELETE (C-090 constitutional act)
    CONSTRAINT chk_notice_30_days CHECK (effective_date >= (notice_sent_at::date + 30))
);

CREATE RULE no_update_price_change_notices AS
    ON UPDATE TO business.price_change_notices DO INSTEAD NOTHING;
CREATE RULE no_delete_price_change_notices AS
    ON DELETE TO business.price_change_notices DO INSTEAD NOTHING;
```

### institutional.pricing_floor_log (C-089 enforcement audit)

```sql
CREATE TABLE institutional.pricing_floor_log (
    id                      UUID                PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_type              VARCHAR(50)         NOT NULL,
    bundle_tier             VARCHAR(20)         NOT NULL,
    proposed_price_paise    INTEGER             NOT NULL,
    cost_floor_paise        INTEGER             NOT NULL,
    constitutional_minimum_margin_pct NUMERIC(5,2) NOT NULL,
    minimum_compliant_price_paise INTEGER        NOT NULL,
    outcome                 VARCHAR(10)         NOT NULL,   -- ACCEPTED | REJECTED
    evaluated_at            TIMESTAMPTZ         NOT NULL DEFAULT NOW(),
    evaluated_by            VARCHAR(50)         NOT NULL DEFAULT 'WBE_MARKUP_ENGINE'
    -- Append-only (C-089 audit trail)
);
```

---

## Amendments to Existing Tables

```sql
-- business.organisations: agency-ready columns
ALTER TABLE business.organisations
    ADD COLUMN IF NOT EXISTS billing_entity_type VARCHAR(20) NOT NULL DEFAULT 'DIRECT',
    ADD COLUMN IF NOT EXISTS parent_organisation_id UUID REFERENCES business.organisations(id);

-- business.employment_contracts: grandfather pricing
ALTER TABLE business.employment_contracts
    ADD COLUMN IF NOT EXISTS agreed_monthly_price_paise INTEGER,
    ADD COLUMN IF NOT EXISTS price_change_notice_sent_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS price_change_effective_date DATE;

-- business.subscription_tiers: bundle version + cost floor
ALTER TABLE business.subscription_tiers
    ADD COLUMN IF NOT EXISTS bundle_version INTEGER NOT NULL DEFAULT 1,
    ADD COLUMN IF NOT EXISTS cost_floor_paise INTEGER,
    ADD COLUMN IF NOT EXISTS billing_profile_agent_type VARCHAR(50);
```

---

## DB Role: wbe_app

```sql
CREATE ROLE wbe_app LOGIN PASSWORD '${WBE_DB_PASSWORD}';

GRANT USAGE ON SCHEMA business, institutional TO wbe_app;

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
GRANT UPDATE ON business.employment_contracts TO wbe_app; -- for mode flip + price change
```

---

## Seed Data (run after migration)

```sql
-- Seed billing profiles (constitutional gate — C-088)
INSERT INTO institutional.billing_profiles VALUES
('dma_v3',  'dma_v3',  ARRAY['llm_local','llm_mid_gemini','llm_frontier_gemini','whatsapp_window','infra_share'],
 ARRAY['video_kling_clip','video_heygen_minute','voice_elevenlabs_monthly','image_gen_per_image','ad_spend_meta','ad_spend_google'],
 '{"ad_spend": {"starter": 200000, "runner": 300000, "winner": 500000}}'::jsonb,
 ARRAY['C-056 ad spend transparency', 'C-043 financial spend ceiling'],
 'FOUNDER_AUTHORIZED', NOW(), 'Yogesh Khandge', NULL, NOW()),

('trading_v1', 'trading_v1', ARRAY['llm_local','llm_mid_gemini','llm_frontier_gemini','whatsapp_window','infra_share'],
 ARRAY['market_data_zerodha','market_data_zerodha_call','charting_per_chart'],
 '{}'::jsonb, ARRAY['C-043 daily loss limit as constitutional floor'],
 'FOUNDER_AUTHORIZED', NOW(), 'Yogesh Khandge', NULL, NOW()),

('agricultural_v2', 'agricultural_v2', ARRAY['llm_local','llm_mid_sarvam','llm_mid_gemini','whatsapp_window','infra_share'],
 ARRAY['climate_data_imd','crop_prices_agmarknet','scheme_data_pm_kisan','soil_data_icar'],
 '{}'::jsonb, ARRAY['C-042 vocabulary mandate — language quality cannot be compromised for cost'],
 'FOUNDER_AUTHORIZED', NOW(), 'Yogesh Khandge', NULL, NOW()),

('private_tutor_v1', 'private_tutor_v1', ARRAY['llm_local','llm_mid_gemini','llm_frontier_gemini','whatsapp_window','infra_share'],
 ARRAY['syllabus_cbse','syllabus_state_boards','image_whiteboard'],
 '{}'::jsonb, ARRAY['C-060 minor student protection — billing NEVER surfaced to student'],
 'FOUNDER_AUTHORIZED', NOW(), 'Yogesh Khandge', NULL, NOW());

-- Seed provider accounts
INSERT INTO institutional.provider_accounts (provider_name, display_name, currency, low_balance_threshold_days, founder_action_template)
VALUES
('kling_ai',        'Kling AI (Video Generation)',    'USD', 7, 'FA-012'),
('heygen',          'HeyGen (Avatar Video)',           'USD', 7, 'FA-013'),
('elevenlabs',      'ElevenLabs (Voice Synthesis)',    'USD', 7, 'FA-014'),
('runway_ml',       'Runway ML (Premium Video)',       'USD', 7, 'FA-015'),
('vertex_ai',       'Google Vertex AI (LLM)',          'USD', 14, 'FA-021'),
('sarvam_ai',       'Sarvam AI (Indian Languages)',    'USD', 7, 'FA-022'),
('whatsapp_bsp',    'WhatsApp BSP (Exotel/360Dialog)', 'INR', 7, NULL),
('meta_mbm',        'Meta Business Manager',           'INR', 14, 'FA-002'),
('google_mcc',      'Google Ads MCC',                  'INR', 14, 'FA-T3-1');
```
