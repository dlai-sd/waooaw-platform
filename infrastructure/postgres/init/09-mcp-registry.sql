-- ============================================================
-- 09-mcp-registry.sql — MCP Registry + Domain Capability Map
-- ============================================================
-- Constitutional basis: C-074 (On-the-Fly Capability Provisioning — RATIFIED),
--                       C-049 (Honest Limitation — customer informed of gaps),
--                       C-059 (Implementation Traceability)
--
-- PURPOSE:
--   Enables the platform to discover, provision, and monitor MCP servers dynamically.
--   When a new customer domain requires an MCP that isn't running, Platform Operations
--   reads this registry to determine: can it auto-provision? does it need customer
--   credentials? does it need a Founder action?
--
-- SCHEMA: institutional (WAOOAW IP — operational registry, not customer data)
-- ============================================================

SET search_path TO institutional, public;

-- ─── MCP Credential Type Enum ─────────────────────────────────────────────────
CREATE TYPE mcp_credential_type AS ENUM (
    'NONE',        -- No credentials needed — auto-provision immediately (Type 3)
    'CUSTOMER',    -- Requires customer's own account credentials (Type 1)
    'PLATFORM'     -- Requires WAOOAW platform credentials — check Key Vault (Type 2)
);

-- ─── MCP Status Enum ──────────────────────────────────────────────────────────
CREATE TYPE mcp_status AS ENUM (
    'NOT_PROVISIONED',    -- Never been started for this customer/environment
    'PROVISIONING',       -- Being spun up (async)
    'RUNNING',            -- Active and healthy
    'SUSPENDED',          -- Scaled to zero (idle > 24h) — resumes on next request
    'CREDENTIAL_PENDING', -- Waiting for customer to provide credentials
    'FOUNDER_ACTION',     -- Waiting for Founder to add platform credentials
    'ERROR'               -- Failed to provision — alert raised
);

-- ─── MCP Isolation Model ──────────────────────────────────────────────────────
CREATE TYPE mcp_isolation AS ENUM (
    'SHARED',        -- One instance serves all customers (platform-level MCPs)
    'PER_CUSTOMER'   -- One instance per customer (customer-credential MCPs)
);

-- ─── MCP Registry — master catalog of all MCP servers ────────────────────────
CREATE TABLE IF NOT EXISTS institutional.mcp_registry (
    mcp_id              VARCHAR(50)         PRIMARY KEY,  -- e.g., 'zomato-mcp', 'ga4-mcp'
    display_name        VARCHAR(100)        NOT NULL,
    description         TEXT                NOT NULL,

    -- Credential classification (determines provisioning path — C-074)
    credential_type     mcp_credential_type NOT NULL,
    isolation           mcp_isolation       NOT NULL DEFAULT 'SHARED',

    -- Container config
    docker_image        VARCHAR(300)        NOT NULL,
    default_port        INTEGER             NOT NULL,
    health_check_path   VARCHAR(100)        NOT NULL DEFAULT '/health',

    -- Credential details (for Platform Ops to collect or check)
    required_secret_names  VARCHAR[]        NOT NULL DEFAULT '{}',
    -- For CUSTOMER type: names of oauth-vault keys to collect from customer
    -- For PLATFORM type: names of Azure Key Vault secrets to check
    -- For NONE type: empty

    -- Customer credential collection instructions (Skill 1b uses this)
    customer_credential_instructions TEXT,  -- Step-by-step guide shown to customer in Skill 1b
    customer_credential_benefit TEXT,       -- "Why you need this" — shown to customer

    -- Founder action details (auto-populated if PLATFORM type and secret missing)
    founder_action_id   VARCHAR(20),        -- e.g., 'FA-021', 'FA-002' — pre-known FA items
    founder_action_description TEXT,        -- What Founder needs to do

    -- Applicable domains (empty = all domains)
    applicable_domains  VARCHAR[]           NOT NULL DEFAULT '{}',
    -- e.g., ['restaurant'] for zomato-mcp; ['dental_clinic'] for practo-mcp
    -- empty array = applies to all domains

    -- Third-party platform details
    third_party_platform VARCHAR(100),      -- e.g., 'Zomato', 'Meta', 'Google'
    third_party_sla_days INTEGER,           -- Known onboarding delay (e.g., Swiggy = 7)

    -- Metadata
    is_active           BOOLEAN             NOT NULL DEFAULT TRUE,
    added_at            TIMESTAMPTZ         NOT NULL DEFAULT NOW(),
    notes               TEXT
);

-- ─── Seed: all known MCPs with their credential types ─────────────────────────

INSERT INTO institutional.mcp_registry VALUES
-- TYPE 3 — No credentials, auto-provision immediately
('web-search-mcp',          'Web Search',              'Public web search for market research',
 'NONE', 'SHARED', 'python:3.12-slim', 8113, '/health', '{}', NULL, NULL, NULL, NULL, '{}', NULL, NULL, TRUE, NOW(), NULL),

('web-scan-mcp',            'Website Scanner',         'Scan public websites for SEO and pixel signals',
 'NONE', 'SHARED', 'python:3.12-slim', 8117, '/health', '{}', NULL, NULL, NULL, NULL, '{}', NULL, NULL, TRUE, NOW(), NULL),

('google-places-mcp',       'Google Places',           'Read public Google Business Profile data',
 'NONE', 'SHARED', 'python:3.12-slim', 8114, '/health', '{}', NULL, NULL, NULL, NULL, '{}', NULL, NULL, TRUE, NOW(), NULL),

('social-profile-mcp',      'Social Profile Scanner',  'Read public social media profiles',
 'NONE', 'SHARED', 'python:3.12-slim', 8115, '/health', '{}', NULL, NULL, NULL, NULL, '{}', NULL, NULL, TRUE, NOW(), NULL),

('meta-ad-library-mcp',     'Meta Ad Library',         'Read public Meta Ad Library data',
 'NONE', 'SHARED', 'python:3.12-slim', 8116, '/health', '{}', NULL, NULL, NULL, NULL, '{}', NULL, NULL, TRUE, NOW(), NULL),

('scheduling-mcp',          'Content Scheduler',       'Internal content calendar management',
 'NONE', 'SHARED', 'python:3.12-slim', 8105, '/health', '{}', NULL, NULL, NULL, NULL, '{}', NULL, NULL, TRUE, NOW(), NULL),

-- TYPE 1 — Customer credentials, collected during Skill 1b
('zomato-mcp',              'Zomato Partner',          'Manage Zomato listing, menu, reviews',
 'CUSTOMER', 'PER_CUSTOMER', 'python:3.12-slim', 8149, '/health',
 '{"ZOMATO_PARTNER_TOKEN_{customer_id}"}',
 'Steps (2 min): Go to restaurant.zomato.com → Settings → API Access → Generate token → Share here (encrypted immediately)',
 'I can manage your Zomato listing, update your menu instantly, and respond to all reviews from here — no need to log in separately.',
 NULL, NULL, '{restaurant}', 'Zomato', NULL, TRUE, NOW(), NULL),

('swiggy-mcp',              'Swiggy Merchant',         'Manage Swiggy listing and delivery analytics',
 'CUSTOMER', 'PER_CUSTOMER', 'python:3.12-slim', 8150, '/health',
 '{"SWIGGY_MERCHANT_TOKEN_{customer_id}"}',
 'Swiggy requires a 7-14 day merchant registration. I will guide you through the process. You need: FSSAI license, PAN, bank details.',
 'Once registered, I manage your Swiggy menu, pricing, and delivery analytics automatically.',
 NULL, NULL, '{restaurant}', 'Swiggy', 14, TRUE, NOW(), NULL),

('booking-mcp-practo',      'Practo Booking',          'Practo appointment booking integration',
 'CUSTOMER', 'PER_CUSTOMER', 'python:3.12-slim', 8146, '/health',
 '{"PRACTO_DOCTOR_TOKEN_{customer_id}"}',
 'Log in to your Practo Doctor account → Profile → API Integration → Copy your token',
 'I can check appointment availability and help patients book directly from Instagram DMs and WhatsApp.',
 NULL, NULL, '{dental_clinic,medical_clinic}', 'Practo', NULL, TRUE, NOW(), NULL),

('booking-mcp-fresha',      'Fresha Booking',          'Fresha appointment booking for beauty businesses',
 'CUSTOMER', 'PER_CUSTOMER', 'python:3.12-slim', 8146, '/health',
 '{"FRESHA_API_KEY_{customer_id}"}',
 'Fresha dashboard → Settings → Integrations → API key → Copy here',
 'Clients can book directly from your Instagram DMs — I check availability and confirm instantly.',
 NULL, NULL, '{beauty_artist,beauty_salon}', 'Fresha', NULL, TRUE, NOW(), NULL),

('instagram-mcp',           'Instagram Business',      'Publish and manage Instagram content',
 'CUSTOMER', 'PER_CUSTOMER', 'python:3.12-slim', 8106, '/health',
 '{"INSTAGRAM_ACCESS_TOKEN_{customer_id}"}',
 'Connect your Instagram Business account via secure login (OAuth — you approve access, revoke anytime)',
 'I can post content, read your insights, and reply to comments — all from here, no manual posting needed.',
 NULL, NULL, '{}', 'Instagram / Meta', NULL, TRUE, NOW(), NULL),

('facebook-mcp',            'Facebook Business Page',  'Manage Facebook page content and events',
 'CUSTOMER', 'PER_CUSTOMER', 'python:3.12-slim', 8107, '/health',
 '{"FACEBOOK_PAGE_TOKEN_{customer_id}"}',
 'Connect your Facebook Business Page (OAuth — one click, you approve)',
 'I can post updates, create events, and set up Messenger automation — your Facebook becomes active again.',
 NULL, NULL, '{}', 'Facebook / Meta', NULL, TRUE, NOW(), NULL),

('google-business-mcp',     'Google Business Profile', 'Manage GBP posts, reviews, Q&A',
 'CUSTOMER', 'PER_CUSTOMER', 'python:3.12-slim', 8108, '/health',
 '{"GBP_ACCESS_TOKEN_{customer_id}"}',
 'Connect your Google Business Profile (Google OAuth — one click)',
 'I can post updates, respond to reviews within 24h, and seed your Q&A — all automatically.',
 NULL, NULL, '{}', 'Google', NULL, TRUE, NOW(), NULL),

-- TYPE 2 — Platform credentials, check Key Vault
('ga4-mcp',                 'Google Analytics 4',      'Cross-channel attribution and conversion tracking',
 'PLATFORM', 'SHARED', 'python:3.12-slim', 8142, '/health',
 '{"google-vertex-sa-key", "google-vertex-project-id"}',
 NULL, NULL,
 'FA-021', 'Create GCP project + enable Analytics API + Service Account key → Azure Key Vault',
 '{}', 'Google', NULL, TRUE, NOW(), NULL),

('youtube-mcp',             'YouTube Operations',      'Upload Shorts, videos, manage YouTube channel analytics',
 'PLATFORM', 'SHARED', 'python:3.12-slim', 8141, '/health',
 '{"google-vertex-sa-key", "google-vertex-project-id"}',
 NULL, NULL,
 'FA-021', 'Same GCP credentials as GA4 — FA-021 covers both',
 '{}', 'Google', NULL, TRUE, NOW(), NULL),

('meta-ads-mcp',            'Meta Ads Manager',        'Create and manage Meta paid advertising campaigns',
 'PLATFORM', 'SHARED', 'python:3.12-slim', 8120, '/health',
 '{"META_BM_ACCESS_TOKEN", "META_APP_SECRET"}',
 NULL, NULL,
 'FA-002', 'Meta Business Manager verification (2-4 weeks) + Business Manager access token',
 '{}', 'Meta', 28, TRUE, NOW(), NULL),

('whatsapp-business-mcp',   'WhatsApp Business API',   'WAOOAW WABA for customer broadcasts',
 'PLATFORM', 'SHARED', 'python:3.12-slim', 8104, '/health',
 '{"WABA_ACCESS_TOKEN", "WABA_PHONE_NUMBER_ID"}',
 NULL, NULL,
 'FA-009', 'WAOOAW WhatsApp Business Account (after FA-002 Meta BM verified)',
 '{}', 'Meta', 14, TRUE, NOW(), NULL);

-- ─── Domain Capability Map — which MCPs each domain requires ─────────────────
CREATE TABLE IF NOT EXISTS institutional.domain_capability_map (
    domain              VARCHAR(50)     NOT NULL,
    mcp_id              VARCHAR(50)     NOT NULL REFERENCES institutional.mcp_registry(mcp_id),
    priority            VARCHAR(10)     NOT NULL CHECK (priority IN ('P0', 'P1', 'P2')),
    -- P0: required for core value prop; P1: significantly improves results; P2: enhancement
    skill_requires      INTEGER[],      -- Skill numbers that use this MCP
    is_blocking         BOOLEAN         NOT NULL DEFAULT FALSE,
    -- TRUE: agent cannot meaningfully serve this domain without this MCP
    
    PRIMARY KEY (domain, mcp_id)
);

-- Seed domain capability map
INSERT INTO institutional.domain_capability_map VALUES
-- Restaurant
('restaurant', 'web-search-mcp',       'P0', '{1}',        FALSE),
('restaurant', 'google-places-mcp',    'P0', '{1,6}',      FALSE),
('restaurant', 'social-profile-mcp',   'P1', '{1}',        FALSE),
('restaurant', 'meta-ad-library-mcp',  'P1', '{1,2}',      FALSE),
('restaurant', 'google-business-mcp',  'P0', '{1,6}',      TRUE),  -- GBP is essential
('restaurant', 'instagram-mcp',        'P0', '{4}',        TRUE),
('restaurant', 'facebook-mcp',         'P1', '{5}',        FALSE),
('restaurant', 'scheduling-mcp',       'P0', '{2,4,5}',    TRUE),
('restaurant', 'zomato-mcp',           'P0', '{1,9,14}',   FALSE), -- P0 but not blocking day-1
('restaurant', 'swiggy-mcp',           'P0', '{1,9}',      FALSE),
('restaurant', 'whatsapp-business-mcp','P1', '{7,7b,16}',  FALSE),
('restaurant', 'ga4-mcp',             'P1', '{9}',         FALSE),

-- Dental clinic
('dental_clinic', 'web-search-mcp',       'P0', '{1}',     FALSE),
('dental_clinic', 'google-places-mcp',    'P0', '{1,6}',   FALSE),
('dental_clinic', 'google-business-mcp',  'P0', '{6}',     TRUE),
('dental_clinic', 'instagram-mcp',        'P0', '{4}',     TRUE),
('dental_clinic', 'facebook-mcp',         'P1', '{5}',     FALSE),
('dental_clinic', 'whatsapp-business-mcp','P0', '{7,16}',  FALSE),
('dental_clinic', 'booking-mcp-practo',   'P0', '{7b,16}', FALSE),
('dental_clinic', 'scheduling-mcp',       'P0', '{2,4}',   TRUE),
('dental_clinic', 'ga4-mcp',             'P1', '{9}',      FALSE),

-- Beauty artist
('beauty_artist', 'web-search-mcp',       'P0', '{1}',     FALSE),
('beauty_artist', 'instagram-mcp',        'P0', '{4}',     TRUE),
('beauty_artist', 'google-business-mcp',  'P0', '{6}',     FALSE),
('beauty_artist', 'whatsapp-business-mcp','P0', '{7}',     FALSE),
('beauty_artist', 'booking-mcp-fresha',   'P0', '{7b,16}', FALSE),
('beauty_artist', 'scheduling-mcp',       'P0', '{2,4}',   TRUE),

-- Digital marketing agency
('digital_marketing_agency', 'web-search-mcp',     'P0', '{1}',   FALSE),
('digital_marketing_agency', 'google-places-mcp',  'P0', '{1}',   FALSE),
('digital_marketing_agency', 'google-business-mcp','P0', '{6}',   FALSE),
('digital_marketing_agency', 'instagram-mcp',      'P0', '{4}',   FALSE),
('digital_marketing_agency', 'facebook-mcp',       'P1', '{5}',   FALSE),
('digital_marketing_agency', 'ga4-mcp',           'P0', '{9}',    FALSE),
('digital_marketing_agency', 'meta-ads-mcp',       'P0', '{11}',  FALSE),
('digital_marketing_agency', 'scheduling-mcp',     'P0', '{2,4}', TRUE);

-- ─── Customer MCP Provision Status ────────────────────────────────────────────
-- Tracks per-customer MCP provisioning state for Type 1 (customer-credential) MCPs

CREATE TABLE IF NOT EXISTS institutional.customer_mcp_status (
    customer_id         UUID            NOT NULL,
    mcp_id              VARCHAR(50)     NOT NULL REFERENCES institutional.mcp_registry(mcp_id),
    status              mcp_status      NOT NULL DEFAULT 'NOT_PROVISIONED',
    container_url       VARCHAR(300),   -- The running MCP endpoint for this customer
    credential_collected_at TIMESTAMPTZ,
    provisioned_at      TIMESTAMPTZ,
    suspended_at        TIMESTAMPTZ,
    last_called_at      TIMESTAMPTZ,
    error_message       TEXT,
    -- Founder action tracking
    founder_action_id   VARCHAR(20),    -- e.g., 'FA-AUTO-20260719-001'
    founder_notified_at TIMESTAMPTZ,
    customer_notified_at TIMESTAMPTZ,
    sla_deadline        TIMESTAMPTZ,    -- provisioned_at must be before this

    PRIMARY KEY (customer_id, mcp_id),
    CONSTRAINT sla_24h CHECK (
        sla_deadline IS NULL OR
        provisioned_at IS NULL OR
        provisioned_at <= sla_deadline
    )
);

CREATE INDEX IF NOT EXISTS idx_customer_mcp_pending
    ON institutional.customer_mcp_status (status, sla_deadline)
    WHERE status IN ('CREDENTIAL_PENDING', 'FOUNDER_ACTION', 'PROVISIONING');

CREATE INDEX IF NOT EXISTS idx_customer_mcp_idle
    ON institutional.customer_mcp_status (last_called_at, status)
    WHERE status = 'RUNNING';

COMMENT ON TABLE institutional.customer_mcp_status IS
    'Per-customer MCP provisioning state. C-074: tracks credential collection,
     provisioning, suspension, and SLA compliance. Platform Operations reads this
     to auto-provision, send Founder alerts, and notify customers.';

-- ─── Persistence Layer: ARM Resource ID + Docker Container ID ────────────────
-- Stores the physical handle to the running container/app.
-- Reconciliation uses this to verify the container still exists, not just health-check.

ALTER TABLE institutional.customer_mcp_status
    ADD COLUMN IF NOT EXISTS arm_resource_id    VARCHAR(500),   -- Azure Container Apps ARM resource path
    ADD COLUMN IF NOT EXISTS docker_container_id VARCHAR(64),   -- Docker container ID (dev only)
    ADD COLUMN IF NOT EXISTS last_health_check   TIMESTAMPTZ,   -- Last successful /health response
    ADD COLUMN IF NOT EXISTS restart_policy      VARCHAR(20)    -- 'unless-stopped' for Docker; 'arm-persistent' for Azure
                             DEFAULT 'unless-stopped',
    ADD COLUMN IF NOT EXISTS reconciliation_count INTEGER NOT NULL DEFAULT 0;
    -- Incremented each time the reconciliation loop re-provisioned this MCP

-- ─── MCP Health Check Log ─────────────────────────────────────────────────────
-- Append-only log of every health check probe result.
-- Partitioned monthly to prevent unbounded growth.
-- Used by: Platform Operations periodic health probe (every 5 min)
--          Reconciliation workflow (checks last_N_failures to decide re-provision threshold)

CREATE TABLE IF NOT EXISTS institutional.mcp_health_check_log (
    id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id         UUID        NOT NULL,
    mcp_id              VARCHAR(50) NOT NULL,
    status              VARCHAR(10) NOT NULL CHECK (status IN ('OK', 'FAIL', 'TIMEOUT', 'NO_RESPONSE')),
    http_status_code    INTEGER,            -- e.g., 200, 503, NULL if timeout
    latency_ms          INTEGER,            -- Response latency in ms
    error_reason        TEXT,               -- e.g., 'connection_refused', 'health_check_timeout'
    checked_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    was_reprovisioned   BOOLEAN     NOT NULL DEFAULT FALSE  -- Did this FAIL trigger re-provision?
) PARTITION BY RANGE (checked_at);

CREATE TABLE IF NOT EXISTS institutional.mcp_health_check_log_2026_07
    PARTITION OF institutional.mcp_health_check_log
    FOR VALUES FROM ('2026-07-01') TO ('2026-08-01');

CREATE TABLE IF NOT EXISTS institutional.mcp_health_check_log_2026_08
    PARTITION OF institutional.mcp_health_check_log
    FOR VALUES FROM ('2026-08-01') TO ('2026-09-01');

-- Indexes for reconciliation decisions
CREATE INDEX IF NOT EXISTS idx_health_log_recent_failures
    ON institutional.mcp_health_check_log (customer_id, mcp_id, checked_at DESC)
    WHERE status != 'OK';

CREATE INDEX IF NOT EXISTS idx_health_log_customer_mcp
    ON institutional.mcp_health_check_log (customer_id, mcp_id, checked_at DESC);

COMMENT ON TABLE institutional.mcp_health_check_log IS
    'Append-only health probe log. C-074: source of truth for MCP availability history.
     Reconciliation reads last-5-failures to decide re-provision threshold.
     Partitioned monthly for performance.';

-- ─── Reconciliation Run Log ───────────────────────────────────────────────────
-- Records every startup reconciliation and periodic health sweep.
-- Enables audit trail for SLA compliance verification.

CREATE TABLE IF NOT EXISTS institutional.mcp_reconciliation_log (
    id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    run_type            VARCHAR(20) NOT NULL CHECK (run_type IN ('STARTUP', 'PERIODIC', 'MANUAL')),
    started_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at        TIMESTAMPTZ,
    mcps_checked        INTEGER     NOT NULL DEFAULT 0,
    mcps_healthy        INTEGER     NOT NULL DEFAULT 0,
    mcps_reprovisioned  INTEGER     NOT NULL DEFAULT 0,
    mcps_failed         INTEGER     NOT NULL DEFAULT 0,   -- Failed to re-provision after 3 attempts
    temporal_workflow_id VARCHAR(200),
    constitutional_basis VARCHAR(10) NOT NULL DEFAULT 'C-074'
);

COMMENT ON TABLE institutional.mcp_reconciliation_log IS
    'Records every reconciliation run. C-074 SLA audit trail.
     Failed reconciliations (mcps_failed > 0) trigger Steward notification.';

-- ─── Suspension Management ────────────────────────────────────────────────────
-- View: MCPs that have been idle for > 24h and should be suspended (scale-to-zero)
-- Platform Operations reads this view on its daily 02:00 IST maintenance run.

CREATE MATERIALIZED VIEW IF NOT EXISTS institutional.mcps_eligible_for_suspension AS
SELECT
    cms.customer_id,
    cms.mcp_id,
    mr.display_name,
    cms.container_url,
    cms.last_called_at,
    EXTRACT(EPOCH FROM (NOW() - cms.last_called_at)) / 3600 AS hours_idle
FROM institutional.customer_mcp_status cms
JOIN institutional.mcp_registry mr ON mr.mcp_id = cms.mcp_id
WHERE cms.status = 'RUNNING'
  AND cms.last_called_at < NOW() - INTERVAL '24 hours'
  AND mr.isolation = 'PER_CUSTOMER'  -- Only suspend per-customer MCPs; shared MCPs stay up
WITH DATA;

CREATE UNIQUE INDEX IF NOT EXISTS idx_suspension_eligible_pk
    ON institutional.mcps_eligible_for_suspension (customer_id, mcp_id);

COMMENT ON MATERIALIZED VIEW institutional.mcps_eligible_for_suspension IS
    'MCPs idle > 24h eligible for scale-to-zero. Refreshed by Platform Operations nightly.
     Suspension = 0 replicas on Container Apps (cost: ₹0). Resume on next request.
     ADR-027 O-07: scale-to-zero for cost optimisation.';

-- ─── Recovery SLA View ────────────────────────────────────────────────────────
-- SLA breach detection: any MCP that has been in ERROR state for > 1h is a breach.

CREATE VIEW institutional.mcp_sla_breaches AS
SELECT
    cms.customer_id,
    cms.mcp_id,
    mr.display_name,
    cms.status,
    cms.sla_deadline,
    cms.customer_notified_at,
    cms.founder_notified_at,
    EXTRACT(EPOCH FROM (NOW() - cms.sla_deadline)) / 3600 AS hours_overdue
FROM institutional.customer_mcp_status cms
JOIN institutional.mcp_registry mr ON mr.mcp_id = cms.mcp_id
WHERE cms.status IN ('ERROR', 'FOUNDER_ACTION')
  AND cms.sla_deadline IS NOT NULL
  AND NOW() > cms.sla_deadline;

COMMENT ON VIEW institutional.mcp_sla_breaches IS
    'C-074: SLA breach detection. Platform Operations checks this every 5 min.
     Any row = immediate Steward notification + constitutional incident.';

