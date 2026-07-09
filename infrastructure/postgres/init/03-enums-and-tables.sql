-- 03-enums-and-tables.sql
-- Creates all enums and tables per ledger-design.md + evidence-schema.md.
-- EF Core migrations will manage schema changes after initial creation.
-- This file creates the baseline schema that EF Core migrates FROM.
-- Constitutional basis: ledger-design.md, evidence-schema.md, C-005, C-028, C-034

SET search_path TO constitutional, business, professional, public;

-- ─── Enums ───────────────────────────────────────────────────────────────────

-- Evidence state machine (C-028, evidence-schema.md)
-- ABANDONED added per evidence-schema.md specification
CREATE TYPE evidence_state AS ENUM (
    'PROPOSED',
    'AWAITING_APPROVAL',
    'APPROVED',
    'REJECTED',
    'EXECUTED',
    'ABANDONED'
);

-- Employment lifecycle states (C-034)
CREATE TYPE employment_state AS ENUM (
    'EVALUATION',
    'ACTIVE',
    'SUSPENDED',
    'TERMINATED'
);

-- Execution model for a professional's Decision Space
CREATE TYPE execution_model_type AS ENUM (
    'APPROVAL_GATE',
    'PRE_AUTHORIZED'
);

-- Approval request state (mirrors evidence_state for the business schema)
CREATE TYPE approval_state AS ENUM (
    'PENDING',
    'SCOPE_BOUNDARY_PENDING',
    'APPROVED',
    'REJECTED'
);

-- PAAS session state (evidence-schema.md + professional-runtime.md)
CREATE TYPE paas_session_state AS ENUM (
    'STARTING',
    'ACTIVE',
    'ENDED',
    'EMERGENCY_STOPPED',
    'INTERRUPTED'
);

-- ─── Constitutional Schema Tables ─────────────────────────────────────────────

SET search_path TO constitutional;

-- Constitutional Audit Ledger (C-005, C-007, C-023, C-028)
-- action_instance_id per evidence-schema.md — groups related state transitions
CREATE TABLE constitutional.evidence_records (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id                   UUID NOT NULL,
    contract_id                 UUID NOT NULL,
    professional_id             UUID NOT NULL,
    action_instance_id          UUID NOT NULL,   -- groups records for one logical action
    action_type                 VARCHAR(100) NOT NULL,
    state                       evidence_state NOT NULL,
    proposed_content            JSONB,
    executed_content            JSONB,
    is_scope_boundary           BOOLEAN NOT NULL DEFAULT FALSE,
    scope_boundary_name         VARCHAR(200),
    scope_boundary_acknowledgment TEXT,
    decision_space_version      INT NOT NULL,
    constitutional_basis        VARCHAR(500) NOT NULL CHECK (constitutional_basis <> ''),
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW()
    -- NO updated_at — append-only. C-027.
);

CREATE INDEX idx_evidence_tenant_contract ON constitutional.evidence_records(tenant_id, contract_id);
CREATE INDEX idx_evidence_action_instance ON constitutional.evidence_records(action_instance_id, created_at);

-- Authority License history (append-only per C-007)
CREATE TABLE constitutional.authority_licenses (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id               UUID NOT NULL,
    contract_id             UUID NOT NULL,
    professional_id         UUID NOT NULL,
    authority_level         INT NOT NULL,
    granted_by              UUID NOT NULL,
    constitutional_basis    VARCHAR(500) NOT NULL CHECK (constitutional_basis <> ''),
    evidence_ids            UUID[] NOT NULL,
    granted_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
    -- NO updated_at — append-only. C-027.
);

-- ─── Business Schema Tables ───────────────────────────────────────────────────

SET search_path TO business;

-- Customer organisations
CREATE TABLE business.organisations (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id   UUID NOT NULL UNIQUE,
    name        VARCHAR(200) NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Employment contracts (C-034 four-state lifecycle)
CREATE TABLE business.employment_contracts (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id               UUID NOT NULL,
    professional_id         UUID NOT NULL,
    decision_space_id       UUID,
    state                   employment_state NOT NULL DEFAULT 'EVALUATION',
    authority_level         INT NOT NULL DEFAULT 1,
    goals                   JSONB NOT NULL DEFAULT '[]',
    review_cadence          JSONB NOT NULL DEFAULT '{"frequencyDays": 30}',
    lifecycle_type          VARCHAR(20) NOT NULL DEFAULT 'PERMANENT',  -- PERMANENT | SESSION_BOUND | TRIAL
    -- FR-002: Trial employment is full constitutional employment (all rights apply from day one)
    is_trial                BOOLEAN NOT NULL DEFAULT FALSE,
    trial_ends_at           TIMESTAMPTZ,            -- NULL for non-trial contracts
    trial_converted_at      TIMESTAMPTZ,            -- set when customer converts trial to paid
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    activated_at            TIMESTAMPTZ,
    suspended_at            TIMESTAMPTZ,
    terminated_at           TIMESTAMPTZ
);

-- Decision Spaces (C-030 — constitutional primitive)
CREATE TABLE business.decision_spaces (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id                   UUID NOT NULL,
    contract_id                 UUID NOT NULL REFERENCES business.employment_contracts(id),
    version                     INT NOT NULL DEFAULT 1,
    execution_model             execution_model_type NOT NULL,
    professional_type           VARCHAR(50) NOT NULL,
    authorized_actions          JSONB NOT NULL DEFAULT '[]',
    prohibited_actions          JSONB NOT NULL DEFAULT '[]',
    always_ask_actions          JSONB NOT NULL DEFAULT '[]',
    budget_constraints          JSONB,
    creative_standard_profile   JSONB,
    paas_parameters             JSONB,
    is_active                   BOOLEAN NOT NULL DEFAULT TRUE,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Add FK from contracts to decision_spaces after both tables exist
ALTER TABLE business.employment_contracts
    ADD CONSTRAINT fk_decision_space
    FOREIGN KEY (decision_space_id) REFERENCES business.decision_spaces(id);

-- Approval requests (business-facing view of evidence state machine)
CREATE TABLE business.approval_requests (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id               UUID NOT NULL,
    contract_id             UUID NOT NULL REFERENCES business.employment_contracts(id),
    evidence_record_id      UUID,
    action_instance_id      UUID NOT NULL,  -- matches evidence_records.action_instance_id
    state                   approval_state NOT NULL DEFAULT 'PENDING',
    proposed_content        JSONB NOT NULL,
    is_scope_boundary       BOOLEAN NOT NULL DEFAULT FALSE,
    scope_boundary_name     VARCHAR(200),
    customer_response       VARCHAR(10),
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    responded_at            TIMESTAMPTZ
);

-- PAAS sessions (GAP-004 resolution — tracks active sessions for Emergency Stop routing)
-- session_id = Temporal workflow ID (ADR-018)
CREATE TABLE business.paas_sessions (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id              UUID NOT NULL UNIQUE,  -- Temporal workflow ID
    tenant_id               UUID NOT NULL,
    contract_id             UUID NOT NULL REFERENCES business.employment_contracts(id),
    decision_space_version  INT NOT NULL,
    state                   paas_session_state NOT NULL DEFAULT 'STARTING',
    started_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ended_at                TIMESTAMPTZ,
    termination_reason      TEXT
);

CREATE INDEX idx_paas_sessions_contract ON business.paas_sessions(tenant_id, contract_id, state);

-- Professional Templates (IB-015 FR-001 — WAOOAW-managed Decision Space templates)
-- Stored under WAOOAW's own tenant_id. Readable by all tenants as catalogue.
CREATE TABLE business.professional_templates (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id                   UUID NOT NULL,  -- WAOOAW's org tenant_id
    name                        VARCHAR(200) NOT NULL,
    description                 TEXT,
    professional_type           VARCHAR(50) NOT NULL,
    decision_space_template     JSONB NOT NULL,
    lifecycle_type              VARCHAR(20) NOT NULL DEFAULT 'PERMANENT',
    is_published                BOOLEAN NOT NULL DEFAULT FALSE,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ─── Skill Tables (v0.8.0 — C-036) ──────────────────────────────────────────

-- Skill lifecycle state (C-036 — independently governable unit)
CREATE TYPE skill_state AS ENUM (
    'ACTIVE',
    'PAUSED',
    'TERMINATED'
);

-- Subscription billing event type (C-038 — pro-rata billing)
CREATE TYPE billing_event_type AS ENUM (
    'CONTRACT_ACTIVATED',
    'CONTRACT_SUSPENDED',
    'CONTRACT_TERMINATED',
    'TRIAL_STARTED',
    'TRIAL_CONVERTED',
    'TRIAL_EXPIRED',
    'SKILL_ACTIVATED',
    'SKILL_PAUSED',
    'SKILL_RESUMED',
    'SKILL_TERMINATED'
);

-- Professional Skills (C-036 — independently configurable, independently billable)
CREATE TABLE business.professional_skills (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id                   UUID NOT NULL,
    contract_id                 UUID NOT NULL REFERENCES business.employment_contracts(id),
    skill_type                  VARCHAR(100) NOT NULL,       -- INSTAGRAM_MARKETING, TRADE_EXECUTION, etc.
    name                        VARCHAR(200) NOT NULL,       -- human-readable skill name
    state                       skill_state NOT NULL DEFAULT 'ACTIVE',
    decision_space_subset       JSONB NOT NULL DEFAULT '{}', -- subset of parent Decision Space
    goals                       JSONB NOT NULL DEFAULT '[]', -- SkillGoal[] — business KPI targets (C-037)
    configuration               JSONB NOT NULL DEFAULT '{}', -- credentials, schedule, frequency (C-039)
    price_per_month             DECIMAL(10,2),               -- billing rate for this skill (C-038)
    activated_at                TIMESTAMPTZ,
    paused_at                   TIMESTAMPTZ,
    terminated_at               TIMESTAMPTZ,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_skills_contract ON business.professional_skills(tenant_id, contract_id, state);

-- Skill Performance Records (C-037 — business KPIs, not technical metrics)
CREATE TABLE business.skill_performance_records (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id                   UUID NOT NULL,
    contract_id                 UUID NOT NULL,
    skill_id                    UUID NOT NULL REFERENCES business.professional_skills(id),
    period_start                TIMESTAMPTZ NOT NULL,
    period_end                  TIMESTAMPTZ NOT NULL,
    -- Business KPI measurements (C-037 — primary metric)
    business_kpi_name           VARCHAR(100) NOT NULL,       -- "appointments_per_week", "daily_return_pct"
    business_kpi_target         DECIMAL(10,4),
    business_kpi_actual         DECIMAL(10,4),
    business_kpi_achieved       BOOLEAN,
    -- Supporting technical metrics (secondary — never surfaced as primary, AD-012)
    technical_metrics           JSONB,                       -- {engagement_rate, click_through, etc.}
    recorded_at                 TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Subscription Billing Events (C-038 — minute-level pro-rata precision, AD-014)
-- Append-only: billing events cannot be modified or deleted
CREATE TABLE business.subscription_billing_events (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id                   UUID NOT NULL,
    contract_id                 UUID NOT NULL REFERENCES business.employment_contracts(id),
    skill_id                    UUID REFERENCES business.professional_skills(id),  -- NULL = contract-level
    event_type                  billing_event_type NOT NULL,
    occurred_at                 TIMESTAMPTZ NOT NULL DEFAULT NOW(),  -- minute-level precision (AD-014)
    price_per_month             DECIMAL(10,2),                       -- rate at time of event
    notes                       TEXT
    -- NO updated_at — append-only billing ledger. C-038.
);

CREATE INDEX idx_billing_events_contract ON business.subscription_billing_events(tenant_id, contract_id, occurred_at);

-- Append-only rules for billing events (C-038 — billing is constitutional)
CREATE RULE no_update_billing_events AS
    ON UPDATE TO business.subscription_billing_events
    DO INSTEAD NOTHING;

CREATE RULE no_delete_billing_events AS
    ON DELETE TO business.subscription_billing_events
    DO INSTEAD NOTHING;

-- ─── Professional Schema Tables ───────────────────────────────────────────────

SET search_path TO professional;

-- Professional identities (platform-owned, not tenant-scoped)
CREATE TABLE professional.identities (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    professional_type   VARCHAR(50) NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Professional Experience Ledger (privacy-preserving — evidence_hash not raw evidence)
CREATE TABLE professional.experience_records (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    professional_id             UUID NOT NULL REFERENCES professional.identities(id),
    engagement_type             VARCHAR(50) NOT NULL,
    industry                    VARCHAR(50) NOT NULL,
    capability_demonstrated     VARCHAR(200) NOT NULL,
    evidence_hash               VARCHAR(64) NOT NULL,
    recorded_at                 TIMESTAMPTZ NOT NULL DEFAULT NOW()
    -- No tenant_id — professional-owned, not tenant-owned. C-005.
);

-- Creative Standard Profile embeddings (pgvector — for AI Runtime, IB-015 + GAP-005)
-- Requires pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE professional.creative_standard_embeddings (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    professional_id     UUID NOT NULL REFERENCES professional.identities(id),
    contract_id         UUID NOT NULL,  -- which customer's creative standard
    tenant_id           UUID NOT NULL,  -- the customer's tenant
    embedding           vector(1536),   -- OpenAI text-embedding-3-small dimension
    content_sample      TEXT NOT NULL,  -- the content this embedding represents
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_creative_embeddings_cosine
    ON professional.creative_standard_embeddings
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

-- ─── Institutional Schema (ADR-019, FR-003 — WAOOAW IP) ──────────────────────
-- Domain learning patterns. NOT customer data. No RLS needed — no customer access.

SET search_path TO institutional;

CREATE EXTENSION IF NOT EXISTS vector;  -- may already exist from professional schema

-- Domain knowledge chunks (Tier 1 RAG — WAOOAW IP)
-- Indexed knowledge about industry, regulations, best practices per professional type
CREATE TABLE institutional.domain_knowledge (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    professional_type       VARCHAR(50) NOT NULL,   -- DIGITAL_MARKETING_HEALTHCARE, TRADING_FO, etc.
    knowledge_category      VARCHAR(100) NOT NULL,  -- ALGORITHM_PATTERNS, REGULATION, BEST_PRACTICE, SEASONAL
    content                 TEXT NOT NULL,
    content_embedding       vector(1536),           -- for semantic retrieval
    region                  VARCHAR(50),            -- IN-PUNE, IN-MUMBAI, IN-ALL, etc.
    valid_from              DATE,
    valid_until             DATE,                   -- knowledge expires (e.g., algorithm updates)
    source                  VARCHAR(200),
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_domain_knowledge_embedding
    ON institutional.domain_knowledge
    USING ivfflat (content_embedding vector_cosine_ops)
    WITH (lists = 100);

CREATE INDEX idx_domain_knowledge_type ON institutional.domain_knowledge(professional_type, knowledge_category);

-- Platform intelligence (Tier 3 RAG — WAOOAW IP)
-- Aggregate patterns derived from cross-customer signals (anonymised, no customer identification)
CREATE TABLE institutional.platform_intelligence (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    professional_type       VARCHAR(50) NOT NULL,
    pattern_category        VARCHAR(100) NOT NULL,  -- POSTING_EFFECTIVENESS, TIMING, CONTENT_FORMAT
    pattern_description     TEXT NOT NULL,
    pattern_embedding       vector(1536),
    region                  VARCHAR(50),
    derived_from_count      INT NOT NULL DEFAULT 0, -- how many customer signals contributed (no PII)
    confidence_score        DECIMAL(3,2),           -- 0.00 to 1.00
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_updated_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_platform_intelligence_embedding
    ON institutional.platform_intelligence
    USING ivfflat (pattern_embedding vector_cosine_ops)
    WITH (lists = 100);

-- =============================================================================
-- AGRICULTURAL ADVISORY — Progressive Crop State Model (v0.11.0 — AS-005)
-- Constitutional Basis: C-039 (conversational continuity across sessions),
--                       C-040 (domain specialization — Progressive Crop State),
--                       AD-019 (RAG Tier 2 — Customer Intelligence)
-- =============================================================================

-- Farmer profile: one row per employment_contract_id (set once during onboarding, C-039)
-- Vocabulary Mandate (C-042): this table stores agronomic facts, never surfaced raw to customer
CREATE TABLE business.farmer_profiles (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    employment_contract_id  UUID NOT NULL REFERENCES business.employment_contracts(id),
    organisation_id         UUID NOT NULL REFERENCES business.organisations(id),  -- tenant isolation
    village_name            VARCHAR(200) NOT NULL,
    district                VARCHAR(100) NOT NULL,
    state                   VARCHAR(100) NOT NULL DEFAULT 'Maharashtra',
    latitude                DECIMAL(9,6),                          -- for 10km weather radius
    longitude               DECIMAL(9,6),
    total_acres             DECIMAL(8,2),
    irrigation_type         VARCHAR(50),                           -- RAINFED, BOREWELL, CANAL, DRIP
    soil_type               VARCHAR(50),                           -- BLACK_COTTON, RED, ALLUVIAL
    primary_language        VARCHAR(20) NOT NULL DEFAULT 'marathi', -- for Vocabulary Translation Layer
    whatsapp_number         VARCHAR(20),                            -- E.164 format
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_farmer_profile_contract UNIQUE (employment_contract_id)
);

CREATE INDEX idx_farmer_profiles_org ON business.farmer_profiles(organisation_id);
CREATE INDEX idx_farmer_profiles_location ON business.farmer_profiles(district, state);

-- Progressive Crop State Model: one row per active crop season per farmer
-- Updated conversationally across all interactions (C-039)
-- Evidence of crop state transitions stored here — used for PMFBY evidence chain (C-023)
CREATE TABLE business.agent_progressive_state (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    employment_contract_id  UUID NOT NULL REFERENCES business.employment_contracts(id),
    organisation_id         UUID NOT NULL REFERENCES business.organisations(id),
    professional_type       VARCHAR(50) NOT NULL,                  -- 'agricultural_advisor', etc.
    state_key               VARCHAR(200) NOT NULL,                 -- namespaced key: 'crop.kharif_2026.soybean.growth_stage'
    state_value             TEXT NOT NULL,                         -- JSON-encoded state
    state_value_embedding   vector(1536),                          -- for RAG Tier 2 similarity search
    season                  VARCHAR(50),                           -- KHARIF_2026, RABI_2026_27
    crop_name               VARCHAR(100),
    growth_stage            VARCHAR(100),                          -- SOWING, VEGETATIVE, FLOWERING, HARVEST
    last_observed_date      DATE,                                  -- date of last farmer check-in
    confidence_level        VARCHAR(20) DEFAULT 'OBSERVED',        -- OBSERVED, INFERRED, ASSUMED
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_progressive_state_contract ON business.agent_progressive_state(employment_contract_id);
CREATE INDEX idx_progressive_state_season ON business.agent_progressive_state(employment_contract_id, season);
CREATE INDEX idx_progressive_state_embedding
    ON business.agent_progressive_state
    USING ivfflat (state_value_embedding vector_cosine_ops)
    WITH (lists = 100)
    WHERE state_value_embedding IS NOT NULL;

-- Weather alert log: immutable record for PMFBY evidence chain (C-023, C-007)
-- Each alert sent to farmer is an append-only record; farmer acknowledgment appended as separate row
CREATE TABLE business.weather_alert_log (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    employment_contract_id  UUID NOT NULL REFERENCES business.employment_contracts(id),
    organisation_id         UUID NOT NULL REFERENCES business.organisations(id),
    alert_type              VARCHAR(50) NOT NULL,                  -- RAINFALL_EXCESS, DROUGHT, FROST, HEATWAVE, PEST_RISK
    severity                VARCHAR(20) NOT NULL,                  -- INFO, WARNING, CRITICAL
    crop_name               VARCHAR(100),
    alert_message_farmer    TEXT NOT NULL,                         -- farmer-vocabulary version (C-042)
    alert_message_technical TEXT,                                  -- raw meteorological data (CAL only)
    alert_issued_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    farmer_acknowledged_at  TIMESTAMPTZ,                           -- NULL if no acknowledgment yet
    adverse_event_confirmed_at TIMESTAMPTZ,                        -- NULL if event did not occur
    pmfby_evidence_exported_at TIMESTAMPTZ,                        -- NULL if not yet used for claim
    -- Evidence First: this record is the evidence chain link
    cal_event_id            UUID REFERENCES constitutional.evidence_records(id)
);

CREATE INDEX idx_weather_alert_contract ON business.weather_alert_log(employment_contract_id);
CREATE INDEX idx_weather_alert_issued ON business.weather_alert_log(alert_issued_at);
CREATE INDEX idx_weather_alert_pmfby ON business.weather_alert_log(pmfby_evidence_exported_at)
    WHERE pmfby_evidence_exported_at IS NOT NULL;

-- ─────────────────────────────────────────────────────────────────────────────
-- Digital Marketing Agent v2.0 tables (v0.14.0 — AS-001, AS-002, C-039, C-040, C-043, DP-014)
-- ─────────────────────────────────────────────────────────────────────────────

-- Customer profile from AI-native profiling conversation (Skill 0: CUSTOMER_PROFILING)
-- Captures registration fields + extended conversation fields.
-- All fields carry source attribution: where the data came from.
CREATE TABLE business.digital_marketing_profiles (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organisation_id             UUID NOT NULL REFERENCES business.organisations(id),
    -- Minimum viable profile fields (from registration)
    owner_name                  VARCHAR(255),
    business_name               VARCHAR(255),
    business_domain             VARCHAR(100),                  -- DENTAL_CLINIC, BEAUTY_ARTIST, FITNESS_STUDIO, etc.
    locality                    VARCHAR(255),
    city                        VARCHAR(100),
    prospective_customers       TEXT,
    aspiration                  TEXT,
    -- Extended profile fields (from profiling conversation)
    geo_scope_km                INTEGER,                       -- service area radius in km
    current_digital_channels    TEXT[],                        -- INSTAGRAM, FACEBOOK, GOOGLE_BUSINESS, WHATSAPP, WEBSITE
    monthly_enquiry_volume      INTEGER,                       -- approximate current monthly enquiries
    monthly_enquiry_target      INTEGER,                       -- target monthly enquiries
    team_size                   INTEGER,
    monthly_ad_spend_inr        INTEGER,                       -- current ad spend (0 = none)
    primary_competitor          VARCHAR(255),                  -- competitor name noted by customer
    biggest_pain_point          TEXT,
    -- Profile status
    profile_status              VARCHAR(20) NOT NULL DEFAULT 'INCOMPLETE', -- INCOMPLETE, MINIMUM_VIABLE, COMPLETE
    customer_confirmed_at       TIMESTAMPTZ,                   -- NULL until customer confirms profile summary
    -- Source attribution per field (JSON: {field_name: 'registration'|'conversation'|'inference'|'customer_correction'})
    field_sources               JSONB NOT NULL DEFAULT '{}',
    -- Tier 2 customer-private — never crosses tenant boundary (C-041, FR-003)
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_dm_profile_org UNIQUE (organisation_id)     -- one active profile per organisation
);

CREATE INDEX idx_dm_profile_org ON business.digital_marketing_profiles(organisation_id);
CREATE INDEX idx_dm_profile_status ON business.digital_marketing_profiles(profile_status);
CREATE INDEX idx_dm_profile_domain ON business.digital_marketing_profiles(business_domain);

-- Digital Marketing Maturity Score history (Skill 1: MARKET_RESEARCH)
-- Append-only — each assessment creates a new row; scores are never overwritten (C-007).
CREATE TABLE business.digital_marketing_maturity_scores (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organisation_id             UUID NOT NULL REFERENCES business.organisations(id),
    assessment_date             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- Score (1-7 fixed scale per spec)
    maturity_score              SMALLINT NOT NULL CHECK (maturity_score BETWEEN 1 AND 7),
    maturity_label              VARCHAR(50) NOT NULL,          -- NO_PRESENCE, MINIMAL_PRESENCE, OCCASIONAL, ACTIVE_INCONSISTENT, STRUCTURED, MANAGED, DIGITAL_FIRST
    -- Benchmark comparison
    industry_benchmark_avg      NUMERIC(3,1),                  -- average score for domain+city
    industry_benchmark_p80      NUMERIC(3,1),                  -- P80 (top 20%) score for domain+city
    benchmark_domain            VARCHAR(100),
    benchmark_city              VARCHAR(100),
    benchmark_sample_size       INTEGER,
    -- Per-axis scores (research axes from Market Research skill)
    axis_digital_footprint      SMALLINT CHECK (axis_digital_footprint BETWEEN 1 AND 7),
    axis_social_presence        SMALLINT CHECK (axis_social_presence BETWEEN 1 AND 7),
    axis_google_business        SMALLINT CHECK (axis_google_business BETWEEN 1 AND 7),
    axis_paid_advertising       SMALLINT CHECK (axis_paid_advertising BETWEEN 1 AND 7),
    axis_content_quality        SMALLINT CHECK (axis_content_quality BETWEEN 1 AND 7),
    axis_competitor_landscape   SMALLINT CHECK (axis_competitor_landscape BETWEEN 1 AND 7),
    axis_analytics              SMALLINT CHECK (axis_analytics BETWEEN 1 AND 7),
    -- Report artifact
    report_pdf_url              VARCHAR(1024),                 -- signed URL to stored Maturity Report PDF
    report_delivered_at         TIMESTAMPTZ,
    -- Recommended phase bundle based on this assessment
    recommended_bundle          VARCHAR(30),                   -- CURTAIN_RAISER, GROWTH_ENGINE, MATURITY_PHASE
    -- Evidence chain (C-023, C-007)
    cal_event_id                UUID REFERENCES constitutional.evidence_records(id),
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_dm_maturity_org ON business.digital_marketing_maturity_scores(organisation_id);
CREATE INDEX idx_dm_maturity_date ON business.digital_marketing_maturity_scores(organisation_id, assessment_date DESC);

-- Needs Heat Map: per-customer assessment of 8 need states (Skill 1 output, used by all skills)
-- One row per need state per assessment. Replaced on each 6-monthly refresh.
CREATE TABLE business.digital_marketing_needs_heatmap (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organisation_id             UUID NOT NULL REFERENCES business.organisations(id),
    maturity_score_id           UUID NOT NULL REFERENCES business.digital_marketing_maturity_scores(id),
    need_state                  VARCHAR(50) NOT NULL,          -- VISIBILITY, LEADS, CONVERSION, EFFICIENCY, COMPETITION, CONSISTENCY, TRUST, CLARITY
    status                      VARCHAR(20) NOT NULL,          -- ACTIVE, LATENT, NOT_APPLICABLE
    evidence_summary            TEXT,                          -- what the research found (cited)
    evidence_source_url         VARCHAR(1024),                 -- URL of the source data point
    evidence_retrieved_at       TIMESTAMPTZ,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_dm_heatmap_org ON business.digital_marketing_needs_heatmap(organisation_id);
CREATE INDEX idx_dm_heatmap_assessment ON business.digital_marketing_needs_heatmap(maturity_score_id);
CREATE UNIQUE INDEX idx_dm_heatmap_unique ON business.digital_marketing_needs_heatmap(maturity_score_id, need_state);

-- Competitor snapshots: customer-private competitive intelligence (Skill 13: COMPETITIVE_INTELLIGENCE)
-- NEVER aggregated into Tier 3 platform intelligence (C-041, FR-003).
-- Append-only — each monitoring run creates new rows; prior snapshots retained as history.
CREATE TABLE business.competitor_snapshots (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organisation_id             UUID NOT NULL REFERENCES business.organisations(id),
    competitor_name             VARCHAR(255) NOT NULL,         -- confirmed by customer (always-ask: COMPETITOR_NAMED_REPORT)
    competitor_confirmed_by_customer BOOLEAN NOT NULL DEFAULT FALSE,
    snapshot_date               TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- Monitored axes
    social_post_frequency       INTEGER,                       -- posts in last 30 days (public count)
    social_follower_count       INTEGER,
    google_review_count         INTEGER,
    google_review_rating        NUMERIC(2,1),
    google_last_update          DATE,
    meta_ads_active             BOOLEAN,
    meta_ads_count              INTEGER,
    website_url                 VARCHAR(1024),
    website_has_booking_cta     BOOLEAN,
    website_has_analytics       BOOLEAN,
    -- Change detection (for alerting)
    notable_changes             TEXT,                          -- summary of changes vs prior snapshot
    alert_sent_at               TIMESTAMPTZ,                   -- when customer was notified
    -- Source evidence
    data_sources                JSONB,                         -- {axis: 'source_url', ...}
    -- Customer-private: NEVER aggregated (C-041)
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_competitor_org ON business.competitor_snapshots(organisation_id);
CREATE INDEX idx_competitor_name ON business.competitor_snapshots(organisation_id, competitor_name);
CREATE INDEX idx_competitor_date ON business.competitor_snapshots(organisation_id, snapshot_date DESC);

-- Phase bundle subscriptions: tracks which bundle is active and upgrade history (DP-014)
-- Decision Space expansion events — each upgrade requires a new customer authorization (C-003).
CREATE TABLE business.dm_phase_bundle_subscriptions (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organisation_id             UUID NOT NULL REFERENCES business.organisations(id),
    employment_contract_id      UUID NOT NULL REFERENCES business.employment_contracts(id),
    bundle                      VARCHAR(30) NOT NULL,          -- CURTAIN_RAISER, GROWTH_ENGINE, MATURITY_PHASE
    activated_at                TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deactivated_at              TIMESTAMPTZ,                   -- NULL if currently active
    maturity_score_at_activation SMALLINT,                     -- score that triggered recommendation
    customer_authorization_event UUID REFERENCES constitutional.evidence_records(id),  -- C-003: expansion requires evidence
    activated_by                VARCHAR(50) NOT NULL DEFAULT 'CUSTOMER', -- CUSTOMER or AGENT_RECOMMENDATION
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_dm_bundle_org ON business.dm_phase_bundle_subscriptions(organisation_id);
CREATE INDEX idx_dm_bundle_active ON business.dm_phase_bundle_subscriptions(organisation_id, deactivated_at)
    WHERE deactivated_at IS NULL;
