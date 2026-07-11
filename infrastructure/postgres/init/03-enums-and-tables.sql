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
    'PRE_AUTHORIZED',
    'PRODUCES_RECORD'       -- Intelligence skills: produce an artifact; customer confirms; no external action until confirmed (C-044, R-014-P2-01)
);

-- Approval mode for skill-level operating model (C-044, DP-015)
CREATE TYPE skill_approval_mode AS ENUM (
    'CUSTOMER_APPROVAL',    -- Customer explicitly approves every action
    'EXCEPTION_APPROVAL',   -- Customer pre-defines exceptions; routine actions auto-execute within calendar
    'SYNTHETIC_APPROVAL'    -- Skill generates approval from learned preference model (confidence-gated)
);

-- Approval type recorded in evidence records (C-044)
CREATE TYPE approval_evidence_type AS ENUM (
    'CUSTOMER_EXPLICIT',        -- Customer manually approved this action
    'CALENDAR_AUTHORIZED',      -- Action is within approved content calendar (EXCEPTION_APPROVAL mode)
    'SYNTHETIC',                -- Skill generated approval via preference model (SYNTHETIC_APPROVAL mode)
    'PRE_AUTHORIZED_CLASS'      -- Action is in a pre-authorized class (PRE_AUTHORIZED execution model)
);

-- Digital Marketing needs heat map status (Skill 1)
CREATE TYPE digital_marketing_need_status AS ENUM (
    'ACTIVE',
    'LATENT',
    'NOT_APPLICABLE'
);

-- Digital Marketing need state labels (Skill 1 — 8 need states)
CREATE TYPE digital_marketing_need_state AS ENUM (
    'VISIBILITY',
    'LEADS',
    'CONVERSION',
    'EFFICIENCY',
    'COMPETITION',
    'CONSISTENCY',
    'TRUST',
    'CLARITY'
);

-- Digital Marketing phase bundle (DP-014)
CREATE TYPE dm_phase_bundle AS ENUM (
    'CURTAIN_RAISER',
    'GROWTH_ENGINE',
    'MATURITY_PHASE'
);

-- Digital Marketing profile status
CREATE TYPE dm_profile_status AS ENUM (
    'INCOMPLETE',
    'MINIMUM_VIABLE',
    'COMPLETE'
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
    -- Registration contact fields (GAP-004: phone required for WhatsApp delivery; GAP-005: TRAI opt-in)
    phone_number_whatsapp VARCHAR(20),           -- +91XXXXXXXXXX; required before WhatsApp delivery
    whatsapp_opt_in       BOOLEAN NOT NULL DEFAULT FALSE,   -- TRAI compliance (C-045)
    -- India business identity (ADR-022: GST B2B invoicing; optional)
    gstin                 VARCHAR(15),            -- 15-char GSTIN for B2B customers claiming input credit
    -- Business domain (links to business_domain_taxonomy lookup)
    business_domain       VARCHAR(50),            -- FK to business_domain_taxonomy.domain_code
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
    terminated_at           TIMESTAMPTZ,
    -- Re-hire continuity (GAP-025, CD-003): link new contract to prior terminated contract
    -- Prior Tier 2 RAG, skill configs, and synthetic approval history are accessible via this FK
    previous_contract_id    UUID,                   -- set on re-hire; FK added after table creation
    -- Payment integration (ADR-022: Razorpay)
    razorpay_subscription_id VARCHAR(100)            -- Razorpay subscription ID; set when trial converts to paid
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

-- Add self-referencing FK for re-hire continuity (GAP-025)
ALTER TABLE business.employment_contracts
    ADD CONSTRAINT fk_previous_contract
    FOREIGN KEY (previous_contract_id) REFERENCES business.employment_contracts(id);

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
    profile_status              dm_profile_status NOT NULL DEFAULT 'INCOMPLETE',
    customer_confirmed_at       TIMESTAMPTZ,                   -- NULL until customer confirms profile summary
    -- Source attribution per field (JSON: {field_name: 'registration'|'conversation'|'inference'|'customer_correction'})
    field_sources               JSONB NOT NULL DEFAULT '{}',
    -- Tier 2 customer-private — never crosses tenant boundary (C-041, FR-003)
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- Profiling conversation resume support (GAP-006: mobile users may close browser mid-conversation)
    profiling_session_id        UUID,                          -- current or last active chat session ID
    last_exchange_index         INTEGER NOT NULL DEFAULT 0,    -- last completed exchange in profiling flow
    resume_token                VARCHAR(64),                   -- signed token sent via SMS/WhatsApp for resume link
    resume_token_expires_at     TIMESTAMPTZ,
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
    need_state                  digital_marketing_need_state NOT NULL,
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
    bundle                      dm_phase_bundle NOT NULL,
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

-- ─────────────────────────────────────────────────────────────────────────────
-- Synthetic Approval + Self-Governance tables (v0.16.0 — C-044, AD-017, DP-015)
-- ─────────────────────────────────────────────────────────────────────────────

-- Skill runtime configuration per employment contract (Section 3.14 of agent spec)
-- One row per skill per employment contract. Updated when customer changes approval mode.
CREATE TABLE business.skill_runtime_configurations (
    id                              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    employment_contract_id          UUID NOT NULL REFERENCES business.employment_contracts(id),
    skill_type                      VARCHAR(100) NOT NULL,
    -- Approval model (C-044)
    approval_mode                   skill_approval_mode NOT NULL DEFAULT 'CUSTOMER_APPROVAL',
    synthetic_confidence_threshold  NUMERIC(3,2) NOT NULL DEFAULT 0.90 CHECK (synthetic_confidence_threshold BETWEEN 0.50 AND 1.00),
    synthetic_min_history           INTEGER NOT NULL DEFAULT 20,
    override_window_hours           INTEGER NOT NULL DEFAULT 24,
    -- Self-governance
    goal_miss_escalation_months     INTEGER NOT NULL DEFAULT 2,
    mid_month_pace_threshold        NUMERIC(3,2) NOT NULL DEFAULT 0.60,
    -- Delivery channels (C-044 notification requirement)
    delivery_channels               TEXT[] NOT NULL DEFAULT ARRAY['WHATSAPP_VOICE','WHATSAPP_TEXT','PORTAL','EMAIL_PDF','PUSH'],
    -- API budget
    monthly_llm_budget              INTEGER NOT NULL DEFAULT 60,
    monthly_external_api_budget     INTEGER NOT NULL DEFAULT 200,
    -- Approval mode upgrade history (C-003: each upgrade is a Decision Space amendment)
    mode_upgrade_authorization_event UUID REFERENCES constitutional.evidence_records(id),
    -- Audit
    created_at                      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- Synthetic approval model freshness (GAP-023, DP-015: stale model on resume → downgrade mode)
    synthetic_model_last_calibrated TIMESTAMPTZ,               -- timestamp of last successful synthetic approval
    stale_after_days                INTEGER NOT NULL DEFAULT 21, -- days without calibration → model considered stale
    -- Override rate tracking (DP-015: >10% override rate → auto-propose downgrade)
    override_count_30d              INTEGER NOT NULL DEFAULT 0,  -- overrides in last 30 days (updated by trigger)
    synthetic_approval_count_30d    INTEGER NOT NULL DEFAULT 0,  -- synthetic approvals in last 30 days
    CONSTRAINT uq_skill_config UNIQUE (employment_contract_id, skill_type)
);

CREATE INDEX idx_skill_config_contract ON business.skill_runtime_configurations(employment_contract_id);
CREATE INDEX idx_skill_config_mode ON business.skill_runtime_configurations(approval_mode);

-- Synthetic approval evidence extension (C-044, AD-017)
-- Supplements constitutional.evidence_records for SYNTHETIC approval events.
-- Each row extends one evidence_record of type SYNTHETIC_APPROVAL.
CREATE TABLE business.synthetic_approval_records (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    evidence_record_id          UUID NOT NULL REFERENCES constitutional.evidence_records(id),
    employment_contract_id      UUID NOT NULL REFERENCES business.employment_contracts(id),
    organisation_id             UUID NOT NULL REFERENCES business.organisations(id),
    skill_type                  VARCHAR(100) NOT NULL,
    -- Confidence evidence (AD-017: must be recorded)
    confidence_score            NUMERIC(4,3) NOT NULL CHECK (confidence_score BETWEEN 0 AND 1),
    basis_approval_count        INTEGER NOT NULL,              -- number of prior approvals used for inference
    basis_approval_ids          UUID[],                        -- top-N similar prior approval evidence_record IDs
    action_description          TEXT NOT NULL,                 -- plain language description of synthetically approved action
    action_type                 VARCHAR(100) NOT NULL,         -- the actionType from Decision Space
    -- Override window management (C-001: unconditional override right)
    override_deadline           TIMESTAMPTZ NOT NULL,
    customer_notified_at        TIMESTAMPTZ,                   -- NULL until notification confirmed delivered
    overridden_at               TIMESTAMPTZ,                   -- NULL if not overridden
    override_reason             TEXT,
    -- Sealed: override window expired without override
    sealed_at                   TIMESTAMPTZ,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_synthetic_org ON business.synthetic_approval_records(organisation_id);
CREATE INDEX idx_synthetic_skill ON business.synthetic_approval_records(employment_contract_id, skill_type);
CREATE INDEX idx_synthetic_override_window ON business.synthetic_approval_records(override_deadline)
    WHERE sealed_at IS NULL AND overridden_at IS NULL;

-- Skill self-governance log (Section 3.14.4 of agent spec — DP-015)
-- Records autonomous corrections, escalations, and customer responses.
-- Append-only: one row per governance event per skill per month.
CREATE TABLE business.skill_self_governance_log (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    employment_contract_id      UUID NOT NULL REFERENCES business.employment_contracts(id),
    organisation_id             UUID NOT NULL REFERENCES business.organisations(id),
    skill_type                  VARCHAR(100) NOT NULL,
    log_month                   DATE NOT NULL,                 -- first day of the month this entry covers
    event_type                  VARCHAR(50) NOT NULL,          -- PACE_CHECK, MID_MONTH_CORRECTION, MONTH_END_NARRATIVE, ESCALATION, CUSTOMER_RESPONSE
    -- KPI tracking
    goal_target                 NUMERIC,
    goal_actual                 NUMERIC,
    goal_unit                   VARCHAR(50),                   -- 'enquiries', 'impressions', 'CPL', etc.
    -- Autonomous action
    root_cause_diagnosis        TEXT,
    autonomous_correction_taken TEXT,
    correction_result           TEXT,                          -- what happened after the correction
    -- Escalation
    escalation_triggered        BOOLEAN NOT NULL DEFAULT FALSE,
    escalation_sent_at          TIMESTAMPTZ,
    corrective_options_offered  JSONB,                         -- [{option, description, recommendation: bool}]
    customer_selected_option    TEXT,
    customer_responded_at       TIMESTAMPTZ,
    -- API usage for this cycle
    llm_calls_used              INTEGER DEFAULT 0,
    external_api_calls_used     INTEGER DEFAULT 0,
    -- Evidence chain
    cal_event_id                UUID REFERENCES constitutional.evidence_records(id),
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_governance_log_contract ON business.skill_self_governance_log(employment_contract_id);
CREATE INDEX idx_governance_log_skill_month ON business.skill_self_governance_log(employment_contract_id, skill_type, log_month);
CREATE INDEX idx_governance_log_escalation ON business.skill_self_governance_log(organisation_id, escalation_triggered)
    WHERE escalation_triggered = TRUE;

-- ─────────────────────────────────────────────────────────────────────────────
-- P2 tables (v0.19.0 — ADR-022, GAP-003, GAP-024, GAP-025)
-- ─────────────────────────────────────────────────────────────────────────────

-- Business Domain Taxonomy — lookup table for all supported business types.
-- Drives registration dropdown, agent type mapping, and Tier 1 RAG domain selection.
-- Not tenant-scoped — platform-wide catalogue (same pattern as professional_templates).
CREATE TABLE business.business_domain_taxonomy (
    domain_code         VARCHAR(50) PRIMARY KEY,   -- DENTAL_CLINIC, FITNESS_STUDIO, etc.
    display_name        VARCHAR(100) NOT NULL,      -- shown in portal dropdown
    agent_type          VARCHAR(100),               -- DIGITAL_MARKETING_HEALTHCARE for all current domains
    tier1_rag_key       VARCHAR(100),               -- key for Tier 1 RAG domain knowledge lookup
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    sort_order          INTEGER NOT NULL DEFAULT 0
);

-- Seed data — initial domain taxonomy
INSERT INTO business.business_domain_taxonomy (domain_code, display_name, agent_type, tier1_rag_key, sort_order) VALUES
    ('DENTAL_CLINIC',        'Dental Clinic',                   'DIGITAL_MARKETING_HEALTHCARE', 'dental_india',        10),
    ('BEAUTY_ARTIST',        'Beauty Artist / Salon',           'DIGITAL_MARKETING_HEALTHCARE', 'beauty_india',        20),
    ('FITNESS_STUDIO',       'Fitness Studio / Gym',            'DIGITAL_MARKETING_HEALTHCARE', 'fitness_india',       30),
    ('MEDICAL_CLINIC',       'Medical Clinic / Hospital',       'DIGITAL_MARKETING_HEALTHCARE', 'medical_india',       40),
    ('YOGA_STUDIO',          'Yoga / Wellness Studio',          'DIGITAL_MARKETING_HEALTHCARE', 'wellness_india',      50),
    ('PHARMACY',             'Pharmacy / Medical Store',        'DIGITAL_MARKETING_HEALTHCARE', 'pharmacy_india',      60),
    ('RESTAURANT',           'Restaurant / Cloud Kitchen',      NULL,                           NULL,                  70),  -- future agent
    ('RETAIL_SHOP',          'Retail / Boutique Shop',          NULL,                           NULL,                  80),  -- future agent
    ('OTHER',                'Other Business',                  NULL,                           NULL,                  999);

-- Payment Transactions — every Razorpay payment event (ADR-022).
-- Append-only: each payment event is a new row. Never updated. C-007.
CREATE TABLE business.payment_transactions (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organisation_id             UUID NOT NULL REFERENCES business.organisations(id),
    employment_contract_id      UUID NOT NULL REFERENCES business.employment_contracts(id),
    -- Razorpay identifiers
    razorpay_payment_id         VARCHAR(100),                  -- rzp_live_XXXXXXXXXX
    razorpay_subscription_id    VARCHAR(100),
    razorpay_invoice_id         VARCHAR(100),
    -- Payment details
    event_type                  VARCHAR(50) NOT NULL,          -- payment.captured | payment.failed | subscription.charged | subscription.halted | refund.created
    amount_inr_paise            BIGINT NOT NULL,               -- in paise (100 paise = ₹1)
    currency                    VARCHAR(3) NOT NULL DEFAULT 'INR',
    status                      VARCHAR(30) NOT NULL,          -- captured | failed | refunded
    -- Billing period this payment covers
    billing_period_start        DATE,
    billing_period_end          DATE,
    -- Grace period tracking (ADR-022: 3-day grace on payment failure)
    grace_period_ends_at        TIMESTAMPTZ,                   -- set on payment.failed; skills suspended after this
    -- Evidence chain
    cal_event_id                UUID REFERENCES constitutional.evidence_records(id),
    -- Razorpay webhook payload (for dispute resolution)
    raw_webhook_payload         JSONB,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_payment_org ON business.payment_transactions(organisation_id);
CREATE INDEX idx_payment_contract ON business.payment_transactions(employment_contract_id);
CREATE INDEX idx_payment_razorpay ON business.payment_transactions(razorpay_payment_id) WHERE razorpay_payment_id IS NOT NULL;
CREATE INDEX idx_payment_grace ON business.payment_transactions(grace_period_ends_at) WHERE grace_period_ends_at IS NOT NULL;

-- GST Invoices — GST-compliant invoice records (ADR-022, India GST Act).
-- One invoice per billing period per contract. Append-only per C-007.
CREATE TABLE business.gst_invoices (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organisation_id             UUID NOT NULL REFERENCES business.organisations(id),
    employment_contract_id      UUID NOT NULL REFERENCES business.employment_contracts(id),
    payment_transaction_id      UUID REFERENCES business.payment_transactions(id),
    -- Invoice identity
    invoice_number              VARCHAR(30) NOT NULL UNIQUE,   -- WAOOAW/2026-27/000001 format
    invoice_date                DATE NOT NULL DEFAULT CURRENT_DATE,
    -- WAOOAW entity
    waooaw_gstin                VARCHAR(15) NOT NULL,          -- WAOOAW's GSTIN (from env var)
    hsn_sac_code                VARCHAR(10) NOT NULL DEFAULT '9984',  -- Online Information Services
    -- Customer entity
    customer_name               VARCHAR(200) NOT NULL,
    customer_gstin              VARCHAR(15),                   -- NULL for B2C customers
    customer_address            TEXT,                          -- required for B2B invoices
    -- Amounts (all in paise)
    taxable_amount_paise        BIGINT NOT NULL,               -- base price excl. GST
    cgst_rate                   NUMERIC(4,2) NOT NULL DEFAULT 9.00,  -- 9% CGST (same state)
    sgst_rate                   NUMERIC(4,2) NOT NULL DEFAULT 9.00,  -- 9% SGST (same state)
    igst_rate                   NUMERIC(4,2) NOT NULL DEFAULT 0.00,  -- 18% IGST (inter-state, if applicable)
    cgst_amount_paise           BIGINT NOT NULL,
    sgst_amount_paise           BIGINT NOT NULL,
    igst_amount_paise           BIGINT NOT NULL DEFAULT 0,
    total_amount_paise          BIGINT NOT NULL,
    -- Billing period
    billing_period_start        DATE NOT NULL,
    billing_period_end          DATE NOT NULL,
    bundle                      dm_phase_bundle NOT NULL,
    -- PDF artifact
    pdf_url                     VARCHAR(1024),                 -- signed URL to stored PDF; refreshed on access
    -- Cancellation (for credit notes)
    cancelled_at                TIMESTAMPTZ,
    credit_note_id              UUID,                          -- FK to self if this is a replacement invoice
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_gst_invoice_org ON business.gst_invoices(organisation_id);
CREATE INDEX idx_gst_invoice_number ON business.gst_invoices(invoice_number);
CREATE INDEX idx_gst_invoice_period ON business.gst_invoices(employment_contract_id, billing_period_start);

-- Invoice number sequence — ensures sequential numbering within financial year.
-- Financial year runs April-March in India.
CREATE SEQUENCE business.invoice_number_seq START 1;

-- Data retention tracking (GAP-024, CD-003: Pause creates preservation obligation).
-- Tracks when Tier 2 customer data may be deleted after contract termination.
-- Records when customer exercised data export right (ART-IX).
CREATE TABLE business.data_retention_records (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organisation_id             UUID NOT NULL REFERENCES business.organisations(id),
    employment_contract_id      UUID NOT NULL REFERENCES business.employment_contracts(id),
    -- Retention policy
    contract_terminated_at      TIMESTAMPTZ NOT NULL,
    tier2_data_retain_until     TIMESTAMPTZ NOT NULL,          -- terminate_at + 180 days default; customer can request deletion earlier
    -- Export history (ART-IX: customer right to their own evidence records)
    evidence_export_requested_at TIMESTAMPTZ,
    evidence_export_delivered_at TIMESTAMPTZ,
    evidence_export_url          VARCHAR(1024),                -- signed URL; expires after 7 days
    -- Deletion
    deletion_requested_at       TIMESTAMPTZ,                   -- customer requested early deletion (India PDPB)
    deletion_completed_at       TIMESTAMPTZ,                   -- NULL until deletion executed
    deletion_scope              TEXT[],                        -- which data categories were deleted
    CONSTRAINT uq_retention_contract UNIQUE (employment_contract_id)
);

CREATE INDEX idx_retention_org ON business.data_retention_records(organisation_id);
CREATE INDEX idx_retention_expire ON business.data_retention_records(tier2_data_retain_until)
    WHERE deletion_completed_at IS NULL;

-- ─────────────────────────────────────────────────────────────────────────────
-- AI Agent Execution Layer tables (v0.20.0 — C-045, C-046, C-047, AD-018, AD-019)
-- ─────────────────────────────────────────────────────────────────────────────

-- Agent Prompt Versions — the approved prompt registry (C-045, AD-018, DP-016)
-- Governs which prompt version is active for each (skill_type, pipeline_step) combination.
-- AI Runtime refuses to execute inferences for combinations with no active version.
-- NOT tenant-scoped — platform-wide governance artifact.
CREATE TABLE institutional.agent_prompt_versions (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    prompt_id               VARCHAR(150) NOT NULL,         -- e.g., DMA/INSTAGRAM_MARKETING/CAPTION
    version                 VARCHAR(20) NOT NULL,          -- semver: 1.0.0
    skill_type              VARCHAR(100) NOT NULL,
    pipeline_step           VARCHAR(100) NOT NULL,
    agent_type              VARCHAR(100) NOT NULL,         -- DIGITAL_MARKETING_HEALTHCARE, PLATFORM_OPERATIONS, CE, etc.
    -- Content reference (prompt content lives in architecture/reference/prompts/)
    prompt_file_path        VARCHAR(500) NOT NULL,         -- relative path in repo
    prompt_file_hash        VARCHAR(64),                   -- SHA-256 of prompt content at approval time
    -- Constitutional governance (C-045)
    constitutional_basis    TEXT NOT NULL,
    change_type             VARCHAR(30) NOT NULL,          -- BREAKING | BEHAVIOURAL | PHRASING_ONLY | STRATEGIC | CLASSIFICATION | USAGE_SUMMARY
    -- Token Economy (AD-022 — C-051)
    minimum_model_tier      VARCHAR(20) NOT NULL DEFAULT 'MID_TIER'
                            CHECK (minimum_model_tier IN ('FRONTIER', 'MID_TIER', 'LOCAL', 'FREE_BATCH')),
    -- Review record
    reviewed_by             VARCHAR(100) NOT NULL,         -- e.g., "Enterprise Architect"
    reviewed_at             TIMESTAMPTZ NOT NULL,
    approved_by             VARCHAR(100),                  -- Founder for BEHAVIOURAL/BREAKING changes
    approved_at             TIMESTAMPTZ,
    -- Activation
    is_active               BOOLEAN NOT NULL DEFAULT FALSE,
    activated_at            TIMESTAMPTZ,
    deactivated_at          TIMESTAMPTZ,
    -- Audit
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_prompt_version UNIQUE (prompt_id, version),
    CONSTRAINT uq_active_prompt UNIQUE (skill_type, pipeline_step, agent_type, is_active)
        DEFERRABLE INITIALLY DEFERRED   -- allows atomic version swap
);

CREATE INDEX idx_prompt_active ON institutional.agent_prompt_versions(skill_type, pipeline_step, agent_type) WHERE is_active = TRUE;
CREATE INDEX idx_prompt_tier ON institutional.agent_prompt_versions(minimum_model_tier) WHERE is_active = TRUE;

-- Seed active prompts (v1.0.0 — all from digital-marketing-agent-prompts.md)
INSERT INTO institutional.agent_prompt_versions
    (prompt_id, version, skill_type, pipeline_step, agent_type, prompt_file_path, constitutional_basis, change_type, reviewed_by, reviewed_at, is_active, activated_at)
VALUES
    ('DMA/CUSTOMER_PROFILING/NEXT_QUESTION', '1.0.0', 'CUSTOMER_PROFILING', 'NEXT_QUESTION', 'DIGITAL_MARKETING_HEALTHCARE', 'architecture/reference/prompts/digital-marketing-agent-prompts.md', 'C-039; C-044', 'BEHAVIOURAL', 'Enterprise Architect', NOW(), TRUE, NOW()),
    ('DMA/MARKET_RESEARCH/SCORE_AXIS', '1.0.0', 'MARKET_RESEARCH', 'SCORE_AXIS', 'DIGITAL_MARKETING_HEALTHCARE', 'architecture/reference/prompts/digital-marketing-agent-prompts.md', 'C-037; C-002', 'BEHAVIOURAL', 'Enterprise Architect', NOW(), TRUE, NOW()),
    ('DMA/INSTAGRAM_MARKETING/CAPTION', '1.0.0', 'INSTAGRAM_MARKETING', 'CAPTION', 'DIGITAL_MARKETING_HEALTHCARE', 'architecture/reference/prompts/digital-marketing-agent-prompts.md', 'C-036; C-040; C-041', 'BEHAVIOURAL', 'Enterprise Architect', NOW(), TRUE, NOW()),
    ('DMA/SYNTHETIC_APPROVAL/CONFIDENCE', '1.0.0', 'SYNTHETIC_APPROVAL', 'CONFIDENCE_ASSESSMENT', 'DIGITAL_MARKETING_HEALTHCARE', 'architecture/reference/prompts/digital-marketing-agent-prompts.md', 'C-044; AD-017', 'BEHAVIOURAL', 'Enterprise Architect', NOW(), TRUE, NOW()),
    ('DMA/SELF_GOVERNANCE/DIAGNOSIS', '1.0.0', 'SELF_GOVERNANCE', 'DIAGNOSIS', 'DIGITAL_MARKETING_HEALTHCARE', 'architecture/reference/prompts/digital-marketing-agent-prompts.md', 'C-037; DP-015', 'BEHAVIOURAL', 'Enterprise Architect', NOW(), FALSE, NULL),
    ('DMA/SELF_GOVERNANCE/DIAGNOSIS', '1.1.0', 'SELF_GOVERNANCE', 'DIAGNOSIS', 'DIGITAL_MARKETING_HEALTHCARE', 'architecture/reference/prompts/digital-marketing-agent-prompts.md', 'C-037; C-048; C-049; DP-015', 'BEHAVIOURAL', 'Enterprise Architect', NOW(), TRUE, NOW()),
    ('CE/EVALUATE_POLICY/CONSTITUTIONAL', '1.0.0', 'EVALUATE_POLICY', 'CONSTITUTIONAL_REASONING', 'CONSTITUTIONAL_ENGINE', 'architecture/reference/prompts/digital-marketing-agent-prompts.md', 'C-003; C-023; AD-008', 'BREAKING', 'Enterprise Architect', NOW(), TRUE, NOW()),
    ('PLATFORM_OPS/L1/HEALTH_CHECK', '1.0.0', 'PLATFORM_HEALTH_MONITORING', 'HEALTH_CHECK', 'PLATFORM_OPERATIONS', 'architecture/reference/prompts/digital-marketing-agent-prompts.md', 'C-046; C-037', 'BEHAVIOURAL', 'Enterprise Architect', NOW(), TRUE, NOW()),
    -- 9 additional DMA prompts (v0.21.0)
    ('DMA/CUSTOMER_PROFILING/OPENING_MESSAGE', '1.0.0', 'CUSTOMER_PROFILING', 'OPENING_MESSAGE', 'DIGITAL_MARKETING_HEALTHCARE', 'architecture/reference/prompts/digital-marketing-agent-prompts.md', 'C-039; C-044', 'BEHAVIOURAL', 'Enterprise Architect', NOW(), TRUE, NOW()),
    ('DMA/CUSTOMER_PROFILING/INFERENCE_CONFIRM', '1.0.0', 'CUSTOMER_PROFILING', 'INFERENCE_CONFIRM', 'DIGITAL_MARKETING_HEALTHCARE', 'architecture/reference/prompts/digital-marketing-agent-prompts.md', 'C-039; C-002', 'BEHAVIOURAL', 'Enterprise Architect', NOW(), TRUE, NOW()),
    ('DMA/MARKET_RESEARCH/NEEDS_HEATMAP', '1.0.0', 'MARKET_RESEARCH', 'NEEDS_HEATMAP', 'DIGITAL_MARKETING_HEALTHCARE', 'architecture/reference/prompts/digital-marketing-agent-prompts.md', 'C-037; C-002', 'BEHAVIOURAL', 'Enterprise Architect', NOW(), TRUE, NOW()),
    ('DMA/MARKET_RESEARCH/MATURITY_REPORT', '1.0.0', 'MARKET_RESEARCH', 'MATURITY_REPORT', 'DIGITAL_MARKETING_HEALTHCARE', 'architecture/reference/prompts/digital-marketing-agent-prompts.md', 'C-037; C-039; C-002', 'BEHAVIOURAL', 'Enterprise Architect', NOW(), TRUE, NOW()),
    ('DMA/CONTENT_STRATEGY/MONTHLY_PLAN', '1.0.0', 'CONTENT_STRATEGY', 'MONTHLY_PLAN', 'DIGITAL_MARKETING_HEALTHCARE', 'architecture/reference/prompts/digital-marketing-agent-prompts.md', 'C-036; C-039; C-040', 'BEHAVIOURAL', 'Enterprise Architect', NOW(), TRUE, NOW()),
    ('DMA/INSTAGRAM_MARKETING/HASHTAGS', '1.0.0', 'INSTAGRAM_MARKETING', 'HASHTAGS', 'DIGITAL_MARKETING_HEALTHCARE', 'architecture/reference/prompts/digital-marketing-agent-prompts.md', 'C-036; C-040', 'PHRASING_ONLY', 'Enterprise Architect', NOW(), TRUE, NOW()),
    ('DMA/SELF_GOVERNANCE/ESCALATION', '1.0.0', 'SELF_GOVERNANCE', 'ESCALATION', 'DIGITAL_MARKETING_HEALTHCARE', 'architecture/reference/prompts/digital-marketing-agent-prompts.md', 'C-037; DP-015', 'BEHAVIOURAL', 'Enterprise Architect', NOW(), TRUE, NOW()),
    ('DMA/PERFORMANCE_NARRATIVE/MONTHLY', '1.0.0', 'PERFORMANCE_ANALYTICS', 'MONTHLY_NARRATIVE', 'DIGITAL_MARKETING_HEALTHCARE', 'architecture/reference/prompts/digital-marketing-agent-prompts.md', 'C-037; C-039; DP-011', 'BEHAVIOURAL', 'Enterprise Architect', NOW(), TRUE, NOW()),
    ('PLATFORM_OPS/L2/INCIDENT_DIAGNOSIS', '1.0.0', 'INCIDENT_RESOLUTION', 'DIAGNOSIS', 'PLATFORM_OPERATIONS', 'architecture/reference/prompts/digital-marketing-agent-prompts.md', 'C-046; C-001', 'BEHAVIOURAL', 'Enterprise Architect', NOW(), TRUE, NOW()),
    -- Trading Agent prompts (v0.21.0)
    ('TRADING/MARKET_ANALYSIS/TRADE_SETUP', '1.0.0', 'MARKET_TECHNICAL_ANALYSIS', 'TRADE_SETUP', 'TRADING_FO_CRYPTO', 'architecture/reference/prompts/trading-agri-agent-prompts.md', 'C-036; C-040; C-041', 'BEHAVIOURAL', 'Enterprise Architect', NOW(), TRUE, NOW()),
    ('TRADING/RISK_MANAGEMENT/LOSS_LIMIT_ALERT', '1.0.0', 'RISK_MANAGEMENT', 'LOSS_LIMIT_ALERT', 'TRADING_FO_CRYPTO', 'architecture/reference/prompts/trading-agri-agent-prompts.md', 'C-036; C-001; C-023', 'BREAKING', 'Enterprise Architect', NOW(), TRUE, NOW()),
    ('TRADING/PERFORMANCE/SESSION_REPORT', '1.0.0', 'TRADING_PERFORMANCE_ANALYTICS', 'SESSION_REPORT', 'TRADING_FO_CRYPTO', 'architecture/reference/prompts/trading-agri-agent-prompts.md', 'C-037; C-039; DP-011', 'BEHAVIOURAL', 'Enterprise Architect', NOW(), TRUE, NOW()),
    -- Agricultural Advisor prompts (v0.21.0)
    ('AGRI/WEATHER_ADVISORY/FARMER_ALERT', '1.0.0', 'WEATHER_ADVISORY_FARMER', 'FARMER_ALERT', 'AGRICULTURAL_ADVISOR_INDIA', 'architecture/reference/prompts/trading-agri-agent-prompts.md', 'C-042; C-040; C-039', 'BREAKING', 'Enterprise Architect', NOW(), TRUE, NOW()),
    ('AGRI/CROP_HEALTH/MORNING_CHECKIN', '1.0.0', 'CROP_HEALTH_CONVERSATIONAL', 'MORNING_CHECKIN', 'AGRICULTURAL_ADVISOR_INDIA', 'architecture/reference/prompts/trading-agri-agent-prompts.md', 'C-042; C-039', 'BEHAVIOURAL', 'Enterprise Architect', NOW(), TRUE, NOW()),
    ('AGRI/MANDI_PRICE/SELL_TIMING', '1.0.0', 'MANDI_PRICE_INTELLIGENCE', 'SELL_TIMING', 'AGRICULTURAL_ADVISOR_INDIA', 'architecture/reference/prompts/trading-agri-agent-prompts.md', 'C-042; C-037; C-039', 'BEHAVIOURAL', 'Enterprise Architect', NOW(), TRUE, NOW()),
    ('AGRI/CROP_PLANNING/NEXT_SEASON', '1.0.0', 'CROP_SEASON_PLANNING', 'NEXT_SEASON', 'AGRICULTURAL_ADVISOR_INDIA', 'architecture/reference/prompts/trading-agri-agent-prompts.md', 'C-042; C-037; C-039', 'BEHAVIOURAL', 'Enterprise Architect', NOW(), TRUE, NOW()),
    -- Trading Agent new prompts (v0.29.0 — Track A P1 fix)
    ('TRADING/ONBOARDING/PROFILE_SETUP', '1.0.0', 'ONBOARDING', 'PROFILE_SETUP', 'TRADING_FO_CRYPTO', 'architecture/reference/prompts/trading-agri-agent-prompts.md', 'C-039; AD-013; C-023', 'BEHAVIOURAL', 'Enterprise Architect', NOW(), TRUE, NOW()),
    ('TRADING/EXECUTION/ESCALATION_DECISION', '1.0.0', 'FO_TRADE_EXECUTION', 'ESCALATION_DECISION', 'TRADING_FO_CRYPTO', 'architecture/reference/prompts/trading-agri-agent-prompts.md', 'C-036; C-001; C-023', 'BREAKING', 'Enterprise Architect', NOW(), TRUE, NOW()),
    ('TRADING/CRYPTO/REBALANCE_DECISION', '1.0.0', 'CRYPTO_POSITION_MANAGEMENT', 'REBALANCE_DECISION', 'TRADING_FO_CRYPTO', 'architecture/reference/prompts/trading-agri-agent-prompts.md', 'C-036; C-043; C-041', 'BEHAVIOURAL', 'Enterprise Architect', NOW(), TRUE, NOW()),
    -- Agricultural Advisor new prompts (v0.29.0 — Track A P1 fix)
    ('AGRI/ONBOARDING/OPENING_MESSAGE', '1.0.0', 'WHATSAPP_PHONE_IDENTITY', 'OPENING_MESSAGE', 'AGRICULTURAL_ADVISOR_INDIA', 'architecture/reference/prompts/trading-agri-agent-prompts.md', 'C-042; C-039; ADR-023', 'BEHAVIOURAL', 'Enterprise Architect', NOW(), TRUE, NOW()),
    ('AGRI/ONBOARDING/INFERENCE_CONFIRM', '1.0.0', 'WHATSAPP_PHONE_IDENTITY', 'INFERENCE_CONFIRM', 'AGRICULTURAL_ADVISOR_INDIA', 'architecture/reference/prompts/trading-agri-agent-prompts.md', 'C-039; C-023; ADR-023', 'BEHAVIOURAL', 'Enterprise Architect', NOW(), TRUE, NOW()),
    ('AGRI/HINT_SYSTEM/WEEKLY_HINT', '1.0.0', 'AGRICULTURAL_HINT_SYSTEM', 'WEEKLY_HINT', 'AGRICULTURAL_ADVISOR_INDIA', 'architecture/reference/prompts/trading-agri-agent-prompts.md', 'C-042; C-037; C-039', 'BEHAVIOURAL', 'Enterprise Architect', NOW(), TRUE, NOW()),
    -- Self-Governance Diagnosis prompts (v0.30.0 — R017-01 P1 fix)
    ('TRADING/SELF_GOVERNANCE/DIAGNOSIS', '1.0.0', 'TRADING_PERFORMANCE_ANALYTICS', 'SELF_GOVERNANCE_DIAGNOSIS', 'TRADING_FO_CRYPTO', 'architecture/reference/prompts/trading-agri-agent-prompts.md', 'C-037; C-048; C-049; C-043; DP-015', 'BEHAVIOURAL', 'Enterprise Architect', NOW(), TRUE, NOW()),
    ('AGRI/SELF_GOVERNANCE/DIAGNOSIS', '1.0.0', 'AGRICULTURAL_SELF_GOVERNANCE', 'SELF_GOVERNANCE_DIAGNOSIS', 'AGRICULTURAL_ADVISOR_INDIA', 'architecture/reference/prompts/trading-agri-agent-prompts.md', 'C-037; C-042; C-048; C-049; DP-015', 'BEHAVIOURAL', 'Enterprise Architect', NOW(), TRUE, NOW()),
    -- Strategic Cognition Layer prompts (v0.31.0 — C-050)
    ('DMA/STRATEGIC/SKILL_ACTIVATION_PLAN', '1.0.0', 'STRATEGIC_COGNITION', 'SKILL_ACTIVATION_PLAN', 'DIGITAL_MARKETING_HEALTHCARE', 'architecture/reference/prompts/digital-marketing-agent-prompts.md', 'C-050; C-036; C-037; C-048; C-049; DP-019; AD-021', 'BEHAVIOURAL', 'Enterprise Architect', NOW(), TRUE, NOW()),
    ('DMA/STRATEGIC/PERFORMANCE_ASSESSMENT', '1.0.0', 'STRATEGIC_COGNITION', 'PERFORMANCE_ASSESSMENT', 'DIGITAL_MARKETING_HEALTHCARE', 'architecture/reference/prompts/digital-marketing-agent-prompts.md', 'C-050; C-037; C-048; C-049; DP-015; DP-019', 'BEHAVIOURAL', 'Enterprise Architect', NOW(), TRUE, NOW()),
    ('TRADING/STRATEGIC/SESSION_PREP', '1.0.0', 'STRATEGIC_COGNITION', 'SESSION_PREP', 'TRADING_FO_CRYPTO', 'architecture/reference/prompts/trading-agri-agent-prompts.md', 'C-050; C-036; C-043; C-048; C-049; AD-021', 'BEHAVIOURAL', 'Enterprise Architect', NOW(), TRUE, NOW()),
    ('TRADING/STRATEGIC/MONTHLY_PORTFOLIO_ASSESSMENT', '1.0.0', 'STRATEGIC_COGNITION', 'MONTHLY_PORTFOLIO_ASSESSMENT', 'TRADING_FO_CRYPTO', 'architecture/reference/prompts/trading-agri-agent-prompts.md', 'C-050; C-037; C-043; C-048; C-049; DP-019', 'BEHAVIOURAL', 'Enterprise Architect', NOW(), TRUE, NOW()),
    ('AGRI/STRATEGIC/SEASONAL_ADVISORY_PLAN', '1.0.0', 'STRATEGIC_COGNITION', 'SEASONAL_ADVISORY_PLAN', 'AGRICULTURAL_ADVISOR_INDIA', 'architecture/reference/prompts/trading-agri-agent-prompts.md', 'C-050; C-042; C-036; C-037; C-048; C-049; DP-019; AD-021', 'BEHAVIOURAL', 'Enterprise Architect', NOW(), TRUE, NOW()),
    ('AGRI/STRATEGIC/ADVISORY_EFFECTIVENESS_REVIEW', '1.0.0', 'STRATEGIC_COGNITION', 'ADVISORY_EFFECTIVENESS_REVIEW', 'AGRICULTURAL_ADVISOR_INDIA', 'architecture/reference/prompts/trading-agri-agent-prompts.md', 'C-050; C-042; C-037; C-048; C-049; DP-019', 'BEHAVIOURAL', 'Enterprise Architect', NOW(), TRUE, NOW()),
    -- Token Economy Layer prompts (v0.32.0 — C-051, ADR-024)
    ('DMA/TOKEN_ECONOMY/USAGE_SUMMARY', '1.0.0', 'TOKEN_ECONOMY', 'USAGE_SUMMARY', 'DIGITAL_MARKETING_HEALTHCARE', 'architecture/reference/prompts/digital-marketing-agent-prompts.md', 'C-051; C-038; DP-020', 'USAGE_SUMMARY', 'Enterprise Architect', NOW(), TRUE, NOW()),
    ('TRADING/TOKEN_ECONOMY/USAGE_SUMMARY', '1.0.0', 'TOKEN_ECONOMY', 'USAGE_SUMMARY', 'TRADING_FO_CRYPTO', 'architecture/reference/prompts/trading-agri-agent-prompts.md', 'C-051; C-038; DP-020', 'USAGE_SUMMARY', 'Enterprise Architect', NOW(), TRUE, NOW()),
    ('AGRI/TOKEN_ECONOMY/USAGE_SUMMARY', '1.0.0', 'TOKEN_ECONOMY', 'USAGE_SUMMARY', 'AGRICULTURAL_ADVISOR_INDIA', 'architecture/reference/prompts/trading-agri-agent-prompts.md', 'C-051; C-042; C-038; DP-020', 'USAGE_SUMMARY', 'Enterprise Architect', NOW(), TRUE, NOW()),
    -- Off-Topic Boundary Standard (v0.33.0 — Section 3.17)
    ('PLATFORM/BOUNDARY/OFF_TOPIC_REDIRECT', '1.0.0', 'BOUNDARY', 'OFF_TOPIC_REDIRECT', 'PLATFORM_INTERNAL', 'architecture/reference/prompts/trading-agri-agent-prompts.md', 'C-036; C-037; C-048', 'BEHAVIOURAL', 'Enterprise Architect', NOW(), TRUE, NOW()),
    ('PLATFORM/TOKEN_ECONOMY/MESSAGE_CLASSIFIER', '1.0.0', 'TOKEN_ECONOMY', 'MESSAGE_CLASSIFIER', 'PLATFORM_INTERNAL', 'architecture/reference/prompts/trading-agri-agent-prompts.md', 'C-051; AD-022; DP-020', 'CLASSIFICATION', 'Enterprise Architect', NOW(), TRUE, NOW());

-- Agent Reasoning Traces — primary AI audit artifact (C-047, AD-008, AD-019)
-- See architecture/reference/agent-reasoning-trace.md for full spec.
-- Schema: institutional (WAOOAW IP — not tenant-scoped; queryable by platform ops)
CREATE TABLE institutional.agent_reasoning_traces (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    action_instance_id      UUID,                          -- links to constitutional.evidence_records
    contract_id             UUID NOT NULL,
    organisation_id         UUID NOT NULL,
    skill_type              VARCHAR(100) NOT NULL,
    pipeline_step           VARCHAR(100) NOT NULL,
    prompt_id               VARCHAR(150) NOT NULL,
    prompt_version          VARCHAR(20) NOT NULL,
    context_summary         JSONB NOT NULL DEFAULT '{}',
    reasoning_chain         TEXT NOT NULL,
    decision                JSONB NOT NULL,
    confidence_score        NUMERIC(4,3) NOT NULL CHECK (confidence_score BETWEEN 0 AND 1),
    constitutional_basis    TEXT NOT NULL,
    llm_model               VARCHAR(50) NOT NULL,
    llm_provider            VARCHAR(30) NOT NULL,
    tokens_input            INTEGER NOT NULL DEFAULT 0,
    tokens_output           INTEGER NOT NULL DEFAULT 0,
    latency_ms              INTEGER NOT NULL DEFAULT 0,
    outcome_action_taken    VARCHAR(100),
    outcome_evidence_id     UUID,
    customer_override       BOOLEAN,
    override_reason         TEXT,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_reasoning_contract ON institutional.agent_reasoning_traces(contract_id, created_at DESC);
CREATE INDEX idx_reasoning_skill ON institutional.agent_reasoning_traces(skill_type, pipeline_step);
CREATE INDEX idx_reasoning_confidence ON institutional.agent_reasoning_traces(confidence_score) WHERE confidence_score < 0.80;
CREATE INDEX idx_reasoning_prompt ON institutional.agent_reasoning_traces(prompt_id, prompt_version);
CREATE INDEX idx_reasoning_override ON institutional.agent_reasoning_traces(customer_override) WHERE customer_override = TRUE;

-- Agent Capability Registry — each agent registers its live capabilities (C-047, C-046)
-- Updated by AI Runtime on every execution loop heartbeat.
-- Read by Platform Operations Agent for health monitoring and intelligent routing.
CREATE TABLE institutional.agent_capability_registry (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id                VARCHAR(200) NOT NULL,          -- PROFESSIONAL_TYPE/contract_id/skill_type
    professional_type       VARCHAR(100) NOT NULL,
    contract_id             UUID NOT NULL,
    organisation_id         UUID NOT NULL,
    skill_type              VARCHAR(100) NOT NULL,
    -- Current state
    approval_mode           skill_approval_mode NOT NULL DEFAULT 'CUSTOMER_APPROVAL',
    status                  VARCHAR(20) NOT NULL DEFAULT 'HEALTHY',  -- HEALTHY|DEGRADED|BLOCKED|PAUSED
    last_heartbeat          TIMESTAMPTZ,
    last_execution          TIMESTAMPTZ,
    decision_space_version  INTEGER NOT NULL DEFAULT 1,
    -- Health signals
    confidence_30d_avg      NUMERIC(4,3),
    override_rate_30d       NUMERIC(4,3),
    api_budget_used         INTEGER NOT NULL DEFAULT 0,
    api_budget_total        INTEGER NOT NULL DEFAULT 60,
    -- Pending items
    pending_approvals       INTEGER NOT NULL DEFAULT 0,
    pending_messages        INTEGER NOT NULL DEFAULT 0,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_agent_capability UNIQUE (contract_id, skill_type)
);

CREATE INDEX idx_capability_contract ON institutional.agent_capability_registry(contract_id);
CREATE INDEX idx_capability_type ON institutional.agent_capability_registry(professional_type);
CREATE INDEX idx_capability_status ON institutional.agent_capability_registry(status) WHERE status != 'HEALTHY';

-- Agent Messages — agent-to-agent communication bus (Platform Operations Agent ↔ skill agents)
-- Asynchronous: sending agent writes; receiving agent reads on next heartbeat.
CREATE TABLE institutional.agent_messages (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    from_agent              VARCHAR(200) NOT NULL,
    to_agent                VARCHAR(200) NOT NULL,
    message_type            VARCHAR(50) NOT NULL,          -- HEALTH_ALERT|PAUSE_REQUEST|RESUME_SIGNAL|CONSTITUTIONAL_ALERT|CONFIGURATION_UPDATE
    priority                VARCHAR(20) NOT NULL DEFAULT 'ROUTINE',  -- ROUTINE|URGENT|CRITICAL
    payload                 JSONB NOT NULL,
    constitutional_basis    TEXT,
    requires_acknowledgement BOOLEAN NOT NULL DEFAULT FALSE,
    acknowledged_at         TIMESTAMPTZ,
    expires_at              TIMESTAMPTZ,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_messages_to ON institutional.agent_messages(to_agent, created_at DESC) WHERE acknowledged_at IS NULL;
CREATE INDEX idx_messages_priority ON institutional.agent_messages(priority, created_at DESC) WHERE acknowledged_at IS NULL;

-- Platform Operations Events — audit trail for all platform operations (C-046)
CREATE TABLE institutional.platform_operations_events (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tier                    VARCHAR(5) NOT NULL,           -- L1|L2|L3
    event_type              VARCHAR(100) NOT NULL,
    status                  VARCHAR(30) NOT NULL,          -- DETECTED|RESOLVING|RESOLVED|ESCALATED
    affected_contract_id    UUID,
    affected_organisation_id UUID,
    description             TEXT NOT NULL,
    resolution              TEXT,
    escalation_reason       TEXT,
    reasoning_trace_id      UUID REFERENCES institutional.agent_reasoning_traces(id),
    cal_event_id            UUID REFERENCES constitutional.evidence_records(id),
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved_at             TIMESTAMPTZ
);

CREATE INDEX idx_ops_events_tier ON institutional.platform_operations_events(tier, status);
CREATE INDEX idx_ops_events_contract ON institutional.platform_operations_events(affected_contract_id) WHERE affected_contract_id IS NOT NULL;

-- Agent Health Scores — rolling health metrics per agent/skill (12.1 capability)
CREATE TABLE institutional.agent_health_scores (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    contract_id             UUID NOT NULL,
    organisation_id         UUID NOT NULL,
    skill_type              VARCHAR(100) NOT NULL,
    period_start            DATE NOT NULL,
    period_end              DATE NOT NULL,
    -- Inference quality
    total_inferences        INTEGER NOT NULL DEFAULT 0,
    avg_confidence          NUMERIC(4,3),
    p10_confidence          NUMERIC(4,3),
    inference_blocked_count INTEGER NOT NULL DEFAULT 0,
    -- Constitutional compliance
    ce_deny_count           INTEGER NOT NULL DEFAULT 0,
    ce_escalate_count       INTEGER NOT NULL DEFAULT 0,
    constitutional_violations INTEGER NOT NULL DEFAULT 0,
    -- Approval quality
    customer_override_count INTEGER NOT NULL DEFAULT 0,
    synthetic_approval_count INTEGER NOT NULL DEFAULT 0,
    override_rate           NUMERIC(4,3),
    -- KPI performance
    goal_achievement_pct    NUMERIC(5,2),
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_health_score UNIQUE (contract_id, skill_type, period_start)
);

CREATE INDEX idx_health_contract ON institutional.agent_health_scores(contract_id, period_start DESC);

-- ─────────────────────────────────────────────────────────────────────────────
-- Simulation gap fixes (v0.21.0 — Simulation 005 + 006)
-- ─────────────────────────────────────────────────────────────────────────────

-- GAP-A003: PMFBY adverse event confirmation needs IMD warning ID linkage
ALTER TABLE business.weather_alert_log
    ADD COLUMN imd_warning_id      VARCHAR(100),   -- IMD district warning reference ID
    ADD COLUMN imd_warning_date    DATE,            -- date of IMD warning (for PMFBY cross-reference)
    ADD COLUMN stt_confidence      NUMERIC(3,2);   -- STT confidence score if alert was generated from voice input (AD-020)

-- GAP-A001: farmer WhatsApp contact and language fields
ALTER TABLE business.farmer_profiles
    ADD COLUMN IF NOT EXISTS phone_number_whatsapp VARCHAR(20),  -- +91XXXXXXXXXX
    ADD COLUMN IF NOT EXISTS whatsapp_opt_in       BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS primary_language      VARCHAR(30),  -- MARATHI|HINDI|TELUGU|TAMIL|KANNADA|PUNJABI
    ADD COLUMN IF NOT EXISTS onboarding_channel    VARCHAR(20) NOT NULL DEFAULT 'WHATSAPP';  -- WHATSAPP|PORTAL

-- GAP-T002: Trading profile (structured profile for trading customers)
-- Equivalent of digital_marketing_profiles for the trading agent
CREATE TABLE IF NOT EXISTS business.trading_profiles (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organisation_id             UUID NOT NULL REFERENCES business.organisations(id),
    -- Capital allocation
    fo_capital_inr              BIGINT,            -- F&O capital in paise
    crypto_capital_inr          BIGINT,            -- Crypto capital in paise
    -- Risk parameters (confirmed at onboarding)
    daily_loss_limit_pct        NUMERIC(4,2),      -- percentage of F&O capital
    daily_loss_limit_inr        BIGINT,            -- absolute amount in paise
    max_position_pct            NUMERIC(4,2),      -- percentage per trade
    strategy_type               VARCHAR(30),        -- DIRECTIONAL|VOLATILITY|HYBRID
    session_start_ist           TIME,
    session_end_ist             TIME,
    session_auto_start          BOOLEAN NOT NULL DEFAULT FALSE,  -- GAP-T005: explicit customer choice
    -- Instruments approved
    approved_instruments        TEXT[],             -- NIFTY|BANKNIFTY|CRYPTO_BTC|CRYPTO_ETH
    approved_exchanges          TEXT[],             -- ZERODHA|UPSTOX|COINDCX|WAZIRX
    -- Profile status
    profile_status              dm_profile_status NOT NULL DEFAULT 'INCOMPLETE',
    customer_confirmed_at       TIMESTAMPTZ,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_trading_profile_org UNIQUE (organisation_id)
);

CREATE INDEX idx_trading_profile_org ON business.trading_profiles(organisation_id);

-- GAP-T006: Trading session records for slippage tracking
CREATE TABLE business.trading_session_records (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    employment_contract_id      UUID NOT NULL REFERENCES business.employment_contracts(id),
    organisation_id             UUID NOT NULL REFERENCES business.organisations(id),
    session_date                DATE NOT NULL,
    session_started_at          TIMESTAMPTZ NOT NULL,
    session_ended_at            TIMESTAMPTZ,
    end_reason                  VARCHAR(50),        -- NORMAL|LOSS_LIMIT|SESSION_WINDOW|EMERGENCY_STOP
    -- P&L
    session_pnl_inr_paise       BIGINT NOT NULL DEFAULT 0,
    trades_executed             INTEGER NOT NULL DEFAULT 0,
    trades_won                  INTEGER NOT NULL DEFAULT 0,
    total_slippage_inr_paise    BIGINT NOT NULL DEFAULT 0,
    -- Constitutional evidence
    cal_event_id                UUID REFERENCES constitutional.evidence_records(id),
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_trading_session_contract ON business.trading_session_records(employment_contract_id);
CREATE INDEX idx_trading_session_date ON business.trading_session_records(organisation_id, session_date DESC);

-- ─────────────────────────────────────────────────────────────────────────────
-- Strategic Cognition Layer (v0.31.0 — C-050, AD-021, DP-019)
-- Persists the agent's current strategic plan and last portfolio assessment.
-- One row per employment contract — updated on each re-plan.
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE business.agent_strategic_state (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organisation_id             UUID NOT NULL REFERENCES business.organisations(id),
    employment_contract_id      UUID NOT NULL REFERENCES business.employment_contracts(id),
    professional_type           VARCHAR(100) NOT NULL,
    plan_version                INTEGER NOT NULL DEFAULT 1,     -- increments on each re-plan
    skill_activation_plan       JSONB NOT NULL,                 -- full SKILL_ACTIVATION_PLAN prompt output
    last_performance_assessment JSONB,                         -- full PERFORMANCE_ASSESSMENT prompt output
    active_skills               TEXT[] NOT NULL,               -- currently active skill IDs
    deferred_skills             JSONB,                         -- [{skill_id, reason, revisit_trigger}]
    portfolio_health            VARCHAR(50),                   -- from last assessment
    strategic_intent            TEXT,                          -- c050_strategic_intent from current plan
    last_plan_date              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_assessment_date        TIMESTAMPTZ,
    reasoning_trace_id          UUID REFERENCES institutional.agent_reasoning_traces(id),
    tenant_id                   UUID NOT NULL,                 -- RLS discriminator
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_strategic_state_contract UNIQUE (employment_contract_id)
);
CREATE INDEX idx_strategic_state_org ON business.agent_strategic_state(organisation_id);
CREATE INDEX idx_strategic_state_contract ON business.agent_strategic_state(employment_contract_id);

-- ─────────────────────────────────────────────────────────────────────────────
-- Token Economy Layer (v0.32.0 — C-051, ADR-024)
-- ─────────────────────────────────────────────────────────────────────────────

-- Customer usage unit tracking — one row per customer per billing period
-- Tracks remaining advisory capacity in customer-meaningful units (not tokens)
CREATE TABLE business.customer_usage_units (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organisation_id             UUID NOT NULL REFERENCES business.organisations(id),
    employment_contract_id      UUID NOT NULL REFERENCES business.employment_contracts(id),
    professional_type           VARCHAR(100) NOT NULL,
    billing_period_start        DATE NOT NULL,
    billing_period_end          DATE NOT NULL,
    -- Agricultural Advisor units
    advisory_days_included      SMALLINT,                  -- total days of advisory included in plan
    advisory_days_used          SMALLINT NOT NULL DEFAULT 0,
    advisory_days_rollover      SMALLINT NOT NULL DEFAULT 0,    -- from previous period (25% max)
    crop_questions_included     SMALLINT,
    crop_questions_used         SMALLINT NOT NULL DEFAULT 0,
    seasonal_plans_included     SMALLINT,
    seasonal_plans_used         SMALLINT NOT NULL DEFAULT 0,
    -- DMA units
    content_creations_included  SMALLINT,
    content_creations_used      SMALLINT NOT NULL DEFAULT 0,
    content_creations_rollover  SMALLINT NOT NULL DEFAULT 0,
    quick_edits_included        SMALLINT,
    quick_edits_used            SMALLINT NOT NULL DEFAULT 0,
    quick_edits_rollover        SMALLINT NOT NULL DEFAULT 0,
    research_queries_included   SMALLINT,
    research_queries_used       SMALLINT NOT NULL DEFAULT 0,
    strategy_sessions_included  SMALLINT,
    strategy_sessions_used      SMALLINT NOT NULL DEFAULT 0,
    -- Trading units (session-based, no hard unit limit — monitored only)
    sessions_executed           SMALLINT NOT NULL DEFAULT 0,
    sessions_deferred           SMALLINT NOT NULL DEFAULT 0,   -- SESSION_DEFERRED count
    -- General
    last_threshold_alert_pct    SMALLINT,                   -- last alert sent at this % remaining
    tenant_id                   UUID NOT NULL,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_usage_units_contract_period UNIQUE (employment_contract_id, billing_period_start)
);
CREATE INDEX idx_usage_units_org ON business.customer_usage_units(organisation_id);
CREATE INDEX idx_usage_units_period ON business.customer_usage_units(billing_period_start, professional_type);

-- Message classification log — Token Economy Gate audit trail
-- Every incoming message classification decision is logged here
CREATE TABLE institutional.message_classification_log (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organisation_id             UUID NOT NULL,                 -- tenant (not FK — pre-auth messages included)
    professional_type           VARCHAR(100),
    message_source              VARCHAR(20) NOT NULL,          -- WHATSAPP | PORTAL | API
    message_hash                VARCHAR(64),                   -- SHA-256 of message content (not stored raw)
    classification              VARCHAR(50) NOT NULL,          -- ACKNOWLEDGMENT | PRICE_QUERY | ACTIONABLE_ADVISORY | etc.
    confidence                  DECIMAL(4,3),                  -- 0.000-1.000
    path_taken                  VARCHAR(30) NOT NULL,          -- ZERO_COST | LOW_COST | STANDARD | PREMIUM | EMERGENCY
    response_type               VARCHAR(30) NOT NULL,          -- TEMPLATE | CACHE | MCP_DIRECT | LLM_DISPATCH | CE_EMERGENCY
    llm_dispatched              BOOLEAN NOT NULL DEFAULT FALSE,
    cache_hit                   BOOLEAN NOT NULL DEFAULT FALSE,
    model_tier_used             VARCHAR(20),                   -- FRONTIER | MID_TIER | LOCAL | FREE_BATCH | null (no LLM)
    cost_inr_paise              INTEGER NOT NULL DEFAULT 0,    -- ₹0.00 = 0 paise
    classified_at               TIMESTAMPTZ NOT NULL DEFAULT NOW()
    -- Note: no tenant_id RLS — classification happens before tenant is confirmed (emergency path)
    -- Access controlled by DB role grants only (ai_runtime_app INSERT, business_app SELECT)
);
CREATE INDEX idx_classification_org ON institutional.message_classification_log(organisation_id, classified_at DESC);
CREATE INDEX idx_classification_path ON institutional.message_classification_log(path_taken, classified_at DESC);
CREATE INDEX idx_classification_llm ON institutional.message_classification_log(llm_dispatched, model_tier_used);

-- Prompt cache metadata — tracks cache entries for analytics and invalidation management
-- The actual cached responses live in Redis/pgvector; this table tracks governance
CREATE TABLE institutional.prompt_cache_metadata (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cache_key_hash              VARCHAR(64) NOT NULL UNIQUE,   -- SHA-256 of cache key components
    prompt_id                   VARCHAR(150) NOT NULL,
    professional_type           VARCHAR(100) NOT NULL,
    cache_key_components        JSONB NOT NULL,                -- {crop, district_bucket, stage_bucket, etc.} — NEVER customer fields
    similarity_threshold        DECIMAL(4,3) NOT NULL,
    model_tier_used             VARCHAR(20) NOT NULL,
    hit_count                   INTEGER NOT NULL DEFAULT 0,
    last_hit_at                 TIMESTAMPTZ,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at                  TIMESTAMPTZ NOT NULL,
    invalidated_at              TIMESTAMPTZ,                   -- set when cache entry invalidated before TTL
    invalidation_reason         VARCHAR(100)                   -- OUTBREAK_ALERT | NEW_MSP | NEW_SEASONAL_DATA | TTL_EXPIRED
);
CREATE INDEX idx_cache_prompt ON institutional.prompt_cache_metadata(prompt_id, expires_at);
CREATE INDEX idx_cache_hits ON institutional.prompt_cache_metadata(hit_count DESC) WHERE invalidated_at IS NULL;

-- Billing preference enum (ADR-022: SEPARATE or COMBINED for customers with multiple agents)
CREATE TYPE billing_preference_type AS ENUM (
    'SEPARATE',   -- one invoice per agent, one Razorpay subscription per agent
    'COMBINED'    -- one consolidated invoice for all agents (default for 2+ agents); each agent still has own Razorpay subscription
);

-- Add billing_preference to organisations
ALTER TABLE business.organisations
    ADD COLUMN billing_preference billing_preference_type NOT NULL DEFAULT 'COMBINED',
    ADD COLUMN combined_billing_anchor_day SMALLINT DEFAULT 1 CHECK (combined_billing_anchor_day BETWEEN 1 AND 28);
    -- billing_anchor_day: day of month for consolidated invoice generation (default 1st)

-- Add consolidation_group_id to gst_invoices (for COMBINED billing)
-- When billing_preference = COMBINED: all invoices in the same period share a consolidation_group_id.
-- The "parent" invoice (the one displayed to the customer) has is_consolidated_parent = TRUE.
-- Child invoices (per-agent) are the detail records.
ALTER TABLE business.gst_invoices
    ADD COLUMN consolidation_group_id UUID,      -- NULL for SEPARATE billing; shared UUID for COMBINED group
    ADD COLUMN is_consolidated_parent BOOLEAN NOT NULL DEFAULT FALSE, -- TRUE only for the summary invoice in a COMBINED group
    ADD COLUMN parent_invoice_id UUID REFERENCES business.gst_invoices(id); -- child invoices reference the parent

CREATE INDEX idx_gst_invoice_consolidation ON business.gst_invoices(consolidation_group_id) WHERE consolidation_group_id IS NOT NULL;

-- Subscription tiers lookup — maps agent professional_type + tier_id to Razorpay plan ID and pricing
-- Not tenant-scoped — platform catalogue (same pattern as professional_templates)
CREATE TABLE business.subscription_tiers (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    professional_type           VARCHAR(100) NOT NULL,             -- DIGITAL_MARKETING_HEALTHCARE, TRADING_FO_CRYPTO, AGRICULTURAL_ADVISOR_INDIA
    tier_id                     VARCHAR(50) NOT NULL,              -- CURTAIN_RAISER, TRADING_FO_ONLY, AGRICULTURAL_ADVISOR, etc.
    display_name                VARCHAR(100) NOT NULL,
    monthly_price_inr_paise     BIGINT NOT NULL,                   -- all-inclusive (incl. GST)
    base_amount_paise           BIGINT NOT NULL,
    gst_amount_paise            BIGINT NOT NULL,
    gst_sac_code                VARCHAR(10) NOT NULL DEFAULT '9984',
    razorpay_plan_id            VARCHAR(100),                      -- set when Razorpay plans are created in production
    is_active                   BOOLEAN NOT NULL DEFAULT TRUE,
    sort_order                  INTEGER NOT NULL DEFAULT 0,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_subscription_tier UNIQUE (professional_type, tier_id)
);

-- Seed subscription tiers (v0.25.0)
INSERT INTO business.subscription_tiers (professional_type, tier_id, display_name, monthly_price_inr_paise, base_amount_paise, gst_amount_paise, razorpay_plan_id, sort_order) VALUES
    ('DIGITAL_MARKETING_HEALTHCARE', 'CURTAIN_RAISER',    'Curtain Raiser',            149900, 127034, 22866, 'plan_dma_curtain_raiser',   10),
    ('DIGITAL_MARKETING_HEALTHCARE', 'GROWTH_ENGINE',     'Growth Engine',             249900, 211864, 38036, 'plan_dma_growth_engine',    20),
    ('DIGITAL_MARKETING_HEALTHCARE', 'MATURITY_PHASE',    'Maturity Phase',            399900, 338898, 61002, 'plan_dma_maturity_phase',   30),
    ('TRADING_FO_CRYPTO',           'TRADING_FO_ONLY',   'F&O Professional',          199900, 169407, 30493, 'plan_trading_fo_only',      10),
    ('TRADING_FO_CRYPTO',           'TRADING_FO_CRYPTO', 'F&O + Crypto Professional', 249900, 211864, 38036, 'plan_trading_fo_crypto',    20),
    ('AGRICULTURAL_ADVISOR_INDIA',  'AGRICULTURAL',      'Agricultural Advisor',       20000,  16949,  3051, 'plan_agricultural_advisor', 10);
