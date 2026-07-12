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

-- Prompt seeds: Signal Intelligence Layer (C-053) + Skill Intelligence Router (C-054) — v0.35.0/v0.36.0
INSERT INTO institutional.agent_prompt_versions
    (prompt_id, version, skill_type, pipeline_step, agent_type, prompt_file_path, constitutional_basis, change_type, minimum_model_tier, reviewed_by, reviewed_at, is_active, activated_at)
VALUES
    ('DMA/ROUTING/SKILL_INTENT_ROUTER', '1.0.0', 'SKILL_ROUTING', 'INTENT_CLASSIFICATION', 'DIGITAL_MARKETING_HEALTHCARE', 'architecture/reference/prompts/README.md', 'C-054; AD-027; DP-023', 'CLASSIFICATION', 'LOCAL', 'Enterprise Architect', NOW(), TRUE, NOW()),
    ('AGRI/ROUTING/SKILL_INTENT_ROUTER', '1.0.0', 'SKILL_ROUTING', 'INTENT_CLASSIFICATION', 'AGRICULTURAL_ADVISOR_INDIA', 'architecture/reference/prompts/README.md', 'C-054; AD-027; DP-023', 'CLASSIFICATION', 'LOCAL', 'Enterprise Architect', NOW(), TRUE, NOW()),
    ('TRADING/ROUTING/SKILL_INTENT_ROUTER', '1.0.0', 'SKILL_ROUTING', 'INTENT_CLASSIFICATION', 'TRADING_FO_CRYPTO', 'architecture/reference/prompts/README.md', 'C-054; AD-027; DP-023', 'CLASSIFICATION', 'LOCAL', 'Enterprise Architect', NOW(), TRUE, NOW()),
    ('DMA/SIGNAL/PROACTIVE_ALERT', '1.0.0', 'SIGNAL_INTELLIGENCE', 'PROACTIVE_ALERT', 'DIGITAL_MARKETING_HEALTHCARE', 'architecture/reference/prompts/README.md', 'C-053; AD-026; DP-022', 'BEHAVIOURAL', 'MID_TIER', 'Enterprise Architect', NOW(), TRUE, NOW()),
    ('AGRI/SIGNAL/PROACTIVE_ALERT', '1.0.0', 'SIGNAL_INTELLIGENCE', 'PROACTIVE_ALERT', 'AGRICULTURAL_ADVISOR_INDIA', 'architecture/reference/prompts/README.md', 'C-053; C-042; AD-026; DP-022', 'BEHAVIOURAL', 'MID_TIER', 'Enterprise Architect', NOW(), TRUE, NOW()),
    ('TRADING/SIGNAL/PROACTIVE_ALERT', '1.0.0', 'SIGNAL_INTELLIGENCE', 'PROACTIVE_ALERT', 'TRADING_FO_CRYPTO', 'architecture/reference/prompts/README.md', 'C-053; AD-026; DP-022', 'BEHAVIOURAL', 'MID_TIER', 'Enterprise Architect', NOW(), TRUE, NOW()),
    ('PLATFORM/SIGNAL/ADVISORY_BUNDLE', '1.0.0', 'SIGNAL_INTELLIGENCE', 'ADVISORY_BUNDLE', 'PLATFORM_INTERNAL', 'architecture/reference/prompts/README.md', 'C-053; AD-026', 'BEHAVIOURAL', 'MID_TIER', 'Enterprise Architect', NOW(), TRUE, NOW());

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
-- Agent Memory Layer (v0.34.0 — C-052, AD-025, DP-021)
-- ─────────────────────────────────────────────────────────────────────────────

-- Creative Fingerprint — per customer, per professional type (DMA and future content agents)
-- Stores the living profile that guarantees content uniqueness (DP-021)
CREATE TABLE business.customer_creative_fingerprints (
    id                              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organisation_id                 UUID NOT NULL REFERENCES business.organisations(id),
    employment_contract_id          UUID NOT NULL REFERENCES business.employment_contracts(id),
    professional_type               VARCHAR(100) NOT NULL,
    -- Brand Voice Profile (pgvector embedding of approved content style)
    voice_embedding                 vector(1536),                  -- text-embedding-3-small dimension
    voice_embedding_updated_at      TIMESTAMPTZ,
    -- Content Performance DNA (JSONB: performance by content_type, theme, cta)
    performance_dna                 JSONB NOT NULL DEFAULT '{}',
    -- Competitor Differentiation Profile (pgvector embedding of competitor content to avoid)
    competitor_exclusion_embedding  vector(1536),
    competitor_embedding_refreshed_at TIMESTAMPTZ,
    -- Approval Pattern Profile (JSONB: approval rates by content_type, rejection reasons)
    approval_pattern                JSONB NOT NULL DEFAULT '{}',
    -- Hyper-Local Identity (JSONB: neighbourhood references, local events, staff stories)
    local_identity                  JSONB NOT NULL DEFAULT '{}',
    -- Uniqueness tracking
    last_uniqueness_score           DECIMAL(4,3),                  -- most recent content's uniqueness_score
    total_approvals                 INTEGER NOT NULL DEFAULT 0,
    total_rejections                INTEGER NOT NULL DEFAULT 0,
    -- Audit
    tenant_id                       UUID NOT NULL,
    created_at                      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_fingerprint_contract UNIQUE (employment_contract_id)
);
CREATE INDEX idx_fingerprint_org ON business.customer_creative_fingerprints(organisation_id);
CREATE INDEX idx_fingerprint_voice ON business.customer_creative_fingerprints USING ivfflat (voice_embedding vector_cosine_ops) WHERE voice_embedding IS NOT NULL;
CREATE INDEX idx_fingerprint_competitor ON business.customer_creative_fingerprints USING ivfflat (competitor_exclusion_embedding vector_cosine_ops) WHERE competitor_exclusion_embedding IS NOT NULL;

-- Tier 3 temporal fence — tracks when session data becomes eligible for Tier 3 aggregation
-- Enforces the 24-hour lag requirement of AD-025
CREATE TABLE institutional.tier3_eligibility_log (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    employment_contract_id      UUID NOT NULL,
    professional_type           VARCHAR(100) NOT NULL,
    session_id                  UUID NOT NULL,                     -- The session whose data is being tracked
    session_closed_at           TIMESTAMPTZ NOT NULL,
    anonymized_at               TIMESTAMPTZ,
    eligible_for_tier3_at       TIMESTAMPTZ GENERATED ALWAYS AS (session_closed_at + INTERVAL '24 hours') STORED,
    tier3_written_at            TIMESTAMPTZ,                      -- When data was actually written to Tier 3
    data_categories             TEXT[],                           -- e.g., ['performance_pattern', 'strategy_effectiveness']
    is_trading_session          BOOLEAN NOT NULL DEFAULT FALSE,    -- Trading sessions: position data NEVER written to Tier 3
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_tier3_eligible ON institutional.tier3_eligibility_log(eligible_for_tier3_at) WHERE tier3_written_at IS NULL;
CREATE INDEX idx_tier3_trading ON institutional.tier3_eligibility_log(is_trading_session, eligible_for_tier3_at);

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

-- ============================================================
-- Signal Intelligence Layer tables (v0.35.0 — C-053, AD-026, DP-022)
-- ============================================================

-- signal_materiality_events: platform-level signal detection log (no customer PII)
CREATE TABLE institutional.signal_materiality_events (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_type                  VARCHAR(100) NOT NULL,
    signal_type                 VARCHAR(100) NOT NULL,
    signal_feed_id              VARCHAR(100) NOT NULL,
    materiality_score           DECIMAL(4,3) NOT NULL,
    urgency_class               VARCHAR(20) NOT NULL CHECK (urgency_class IN ('CRITICAL','HIGH','ADVISORY','BELOW_THRESHOLD')),
    customers_matched           INTEGER NOT NULL DEFAULT 0,
    customers_notified          INTEGER NOT NULL DEFAULT 0,
    customers_deferred          INTEGER NOT NULL DEFAULT 0,
    customers_budget_blocked    INTEGER NOT NULL DEFAULT 0,
    signal_payload_hash         VARCHAR(64) NOT NULL,
    signal_region               VARCHAR(200),
    detected_at                 TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    workflow_run_id             VARCHAR(200)
);
CREATE INDEX idx_signal_events_type    ON institutional.signal_materiality_events(agent_type, signal_type, detected_at DESC);
CREATE INDEX idx_signal_events_urgency ON institutional.signal_materiality_events(urgency_class, detected_at DESC);

-- skill_gap_signals: accumulates unserved customer intents → feeds Section 3.20 governance loop
CREATE TABLE institutional.skill_gap_signals (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_type                  VARCHAR(100) NOT NULL,
    unserviced_intent           TEXT NOT NULL,
    intent_classification       VARCHAR(100),
    organisation_id             UUID NOT NULL REFERENCES business.organisations(id),
    employment_contract_id      UUID NOT NULL REFERENCES business.employment_contracts(id),
    gap_frequency_for_customer  INTEGER NOT NULL DEFAULT 1,
    similar_intent_hash         VARCHAR(64) NOT NULL,
    candidate_skill_type        VARCHAR(100),
    adjacent_routing_applied    BOOLEAN NOT NULL DEFAULT FALSE,
    skill_proposal_raised       BOOLEAN NOT NULL DEFAULT FALSE,
    skill_proposal_issue_id     INTEGER,
    detected_at                 TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_skill_gap_agent     ON institutional.skill_gap_signals(agent_type, similar_intent_hash);
CREATE INDEX idx_skill_gap_frequency ON institutional.skill_gap_signals(agent_type, detected_at DESC) WHERE skill_proposal_raised = FALSE;

-- ============================================================
-- Skill Intelligence Router tables (v0.35.0 — C-054, AD-027, DP-023)
-- ============================================================

-- agent_skill_graph: materialized SCM declarations per customer's active skills (pgvector routing index)
CREATE TABLE business.agent_skill_graph (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organisation_id             UUID NOT NULL REFERENCES business.organisations(id),
    employment_contract_id      UUID NOT NULL REFERENCES business.employment_contracts(id),
    skill_id                    VARCHAR(100) NOT NULL,
    skill_version               VARCHAR(20) NOT NULL,
    intent_signatures_embedding VECTOR(1536),
    servable_request_types      JSONB NOT NULL,
    unservable_request_types    JSONB,
    output_contributions        JSONB,
    collaboration_affinities    JSONB,
    activation_state            JSONB NOT NULL,
    is_active                   BOOLEAN NOT NULL DEFAULT TRUE,
    last_updated_at             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    tenant_id                   UUID NOT NULL,
    CONSTRAINT uq_skill_graph_entry UNIQUE (employment_contract_id, skill_id)
);
CREATE INDEX idx_skill_graph_contract  ON business.agent_skill_graph(employment_contract_id) WHERE is_active = TRUE;
CREATE INDEX idx_skill_graph_embedding ON business.agent_skill_graph USING ivfflat (intent_signatures_embedding vector_cosine_ops) WITH (lists = 100);

-- ============================================================
-- Campaign Theme Engine tables (v0.39.0 — C-055, AD-028, DP-024)
-- ============================================================

-- Campaign approval mode enum
CREATE TYPE campaign_approval_mode AS ENUM (
    'POST_APPROVAL',       -- customer approves every piece individually
    'CAMPAIGN_APPROVAL',   -- customer approves campaign brief; SCR gates content; weekly digest
    'CAMPAIGN_AUTO'        -- customer approves campaign brief; full auto within SCR
);

-- Campaign status enum
CREATE TYPE campaign_status AS ENUM (
    'DRAFT',             -- proposed by agent, not yet customer-approved
    'CUSTOMER_APPROVED', -- customer approved the brief
    'ACTIVE',            -- campaign is currently running (within campaign_window)
    'PAUSED',            -- temporarily suspended
    'COMPLETE',          -- campaign window elapsed
    'CANCELLED'          -- cancelled before completion
);

-- SCR check result enum
CREATE TYPE scr_check_result AS ENUM (
    'PASS', 'FAIL', 'NOT_RUN'
);

-- content_campaigns: Level 1 — master campaign record (one per campaign period per customer)
CREATE TABLE business.content_campaigns (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organisation_id             UUID NOT NULL REFERENCES business.organisations(id),
    employment_contract_id      UUID NOT NULL REFERENCES business.employment_contracts(id),
    professional_type           VARCHAR(100) NOT NULL DEFAULT 'DIGITAL_MARKETING_HEALTHCARE',
    master_theme                VARCHAR(300) NOT NULL,
    campaign_window_start       DATE NOT NULL,
    campaign_window_end         DATE NOT NULL,
    target_outcome              TEXT NOT NULL,
    target_audience             TEXT NOT NULL,
    platform_mix                TEXT[] NOT NULL,
    content_cadence             JSONB NOT NULL,
    theme_sequence              JSONB,                       -- EA fix R6-EA: allow NULL for DRAFT state; NOT NULL enforced at ACTIVE transition
    approval_mode               campaign_approval_mode NOT NULL DEFAULT 'POST_APPROVAL',
    status                      campaign_status NOT NULL DEFAULT 'DRAFT',
    proposed_at                 TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    approved_at                 TIMESTAMPTZ,
    completed_at                TIMESTAMPTZ,
    reasoning_trace_id          UUID REFERENCES institutional.agent_reasoning_traces(id),
    tenant_id                   UUID NOT NULL,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_campaigns_contract  ON business.content_campaigns(employment_contract_id, status);
CREATE INDEX idx_campaigns_window    ON business.content_campaigns(campaign_window_start, campaign_window_end);

-- campaign_weekly_themes: Level 2 — weekly sub-theme cascade
CREATE TABLE business.campaign_weekly_themes (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id                 UUID NOT NULL REFERENCES business.content_campaigns(id),
    organisation_id             UUID NOT NULL REFERENCES business.organisations(id),
    week_number                 SMALLINT NOT NULL CHECK (week_number BETWEEN 1 AND 12),
    sub_theme                   VARCHAR(300) NOT NULL,
    narrative_hook              TEXT NOT NULL,
    emotional_target            TEXT NOT NULL,
    platform_execution_notes    JSONB,
    week_start_date             DATE NOT NULL,
    status                      VARCHAR(20) NOT NULL DEFAULT 'GENERATED' CHECK (status IN ('GENERATED','ACTIVE','COMPLETE')),
    tenant_id                   UUID NOT NULL,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_campaign_week UNIQUE (campaign_id, week_number)
);
CREATE INDEX idx_weekly_themes_campaign ON business.campaign_weekly_themes(campaign_id);

-- campaign_content_items: Level 3 — individual content pieces per platform per week
CREATE TYPE content_scr_status AS ENUM (
    'PENDING', 'SCR_PASSED', 'SCR_FAILED', 'COMPLIANCE_VIOLATION',
    'CUSTOMER_APPROVED', 'CUSTOMER_REJECTED', 'PUBLISHED', 'PUBLISH_FAILED'
);

CREATE TABLE business.campaign_content_items (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id                 UUID NOT NULL REFERENCES business.content_campaigns(id),
    weekly_theme_id             UUID NOT NULL REFERENCES business.campaign_weekly_themes(id),
    organisation_id             UUID NOT NULL REFERENCES business.organisations(id),
    platform                    VARCHAR(50) NOT NULL,
    content_body                JSONB NOT NULL,
    audio_script                TEXT,
    visual_storyboard           JSONB,
    scheduled_at                TIMESTAMPTZ NOT NULL,
    published_at                TIMESTAMPTZ,
    platform_post_id            VARCHAR(200),
    scr_status                  content_scr_status NOT NULL DEFAULT 'PENDING',
    regeneration_attempts       SMALLINT NOT NULL DEFAULT 0,
    approval_mode               campaign_approval_mode NOT NULL,
    tenant_id                   UUID NOT NULL,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_content_items_campaign  ON business.campaign_content_items(campaign_id);
CREATE INDEX idx_content_items_schedule  ON business.campaign_content_items(scheduled_at) WHERE scr_status IN ('SCR_PASSED','CUSTOMER_APPROVED');
CREATE INDEX idx_content_items_status    ON business.campaign_content_items(scr_status, organisation_id);

-- scr_review_records: SCR check results per content item (constitutional audit artifact — INSERT only)
CREATE TABLE business.scr_review_records (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content_item_id             UUID NOT NULL REFERENCES business.campaign_content_items(id),
    organisation_id             UUID NOT NULL REFERENCES business.organisations(id),
    regeneration_attempt        SMALLINT NOT NULL DEFAULT 0,
    check_1_theme_fidelity      scr_check_result NOT NULL DEFAULT 'NOT_RUN',
    check_1_score               DECIMAL(4,3),
    check_2_brand_voice         scr_check_result NOT NULL DEFAULT 'NOT_RUN',
    check_2_score               DECIMAL(4,3),
    check_3_compliance          scr_check_result NOT NULL DEFAULT 'NOT_RUN',
    check_3_violations          JSONB,
    check_4_uniqueness          scr_check_result NOT NULL DEFAULT 'NOT_RUN',
    check_4_competitor_sim      DECIMAL(4,3),
    check_4_own_recency_sim     DECIMAL(4,3),
    check_5_quality             scr_check_result NOT NULL DEFAULT 'NOT_RUN',
    check_5_score               DECIMAL(4,3),
    overall_result              VARCHAR(20) NOT NULL DEFAULT 'PENDING' CHECK (overall_result IN ('PENDING','PASSED','FAILED','COMPLIANCE_VIOLATION')),
    reviewed_at                 TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    tenant_id                   UUID NOT NULL
);
CREATE INDEX idx_scr_records_item ON business.scr_review_records(content_item_id);
CREATE INDEX idx_scr_records_org  ON business.scr_review_records(organisation_id, reviewed_at DESC);
-- ============================================================

-- Campaign approval mode enum
CREATE TYPE campaign_approval_mode AS ENUM (
    'POST_APPROVAL',       -- customer approves every piece individually
    'CAMPAIGN_APPROVAL',   -- customer approves campaign brief; SCR gates content; weekly digest
    'CAMPAIGN_AUTO'        -- customer approves campaign brief; full auto within SCR
);

-- Campaign status enum
CREATE TYPE campaign_status AS ENUM (
    'DRAFT',             -- proposed by agent, not yet customer-approved
    'CUSTOMER_APPROVED', -- customer approved the brief
    'ACTIVE',            -- campaign is currently running (within campaign_window)
    'PAUSED',            -- temporarily suspended
    'COMPLETE',          -- campaign window elapsed
    'CANCELLED'          -- cancelled before completion
);

-- SCR check result enum
CREATE TYPE scr_check_result AS ENUM (
    'PASS', 'FAIL', 'NOT_RUN'
);

-- content_campaigns: Level 1 — master campaign record (one per campaign period per customer)
CREATE TABLE business.content_campaigns (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organisation_id             UUID NOT NULL REFERENCES business.organisations(id),
    employment_contract_id      UUID NOT NULL REFERENCES business.employment_contracts(id),
    professional_type           VARCHAR(100) NOT NULL DEFAULT 'DIGITAL_MARKETING_HEALTHCARE',
    master_theme                VARCHAR(300) NOT NULL,         -- "Dental Preventive Care Series"
    campaign_window_start       DATE NOT NULL,
    campaign_window_end         DATE NOT NULL,
    target_outcome              TEXT NOT NULL,                 -- customer language: "+15 preventive bookings"
    target_audience             TEXT NOT NULL,                 -- specific description of who this reaches
    platform_mix                TEXT[] NOT NULL,              -- ['INSTAGRAM','GBP','WHATSAPP','YOUTUBE_SHORT']
    content_cadence             JSONB NOT NULL,               -- {platform: frequency_string}
    theme_sequence              JSONB NOT NULL,               -- [{week_number, sub_theme, narrative_hook, emotional_target}]
    approval_mode               campaign_approval_mode NOT NULL DEFAULT 'POST_APPROVAL',
    status                      campaign_status NOT NULL DEFAULT 'DRAFT',
    proposed_at                 TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    approved_at                 TIMESTAMPTZ,                  -- NULL until customer approves
    completed_at                TIMESTAMPTZ,
    reasoning_trace_id          UUID REFERENCES institutional.agent_reasoning_traces(id),
    tenant_id                   UUID NOT NULL,               -- RLS discriminator
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_campaigns_contract  ON business.content_campaigns(employment_contract_id, status);
CREATE INDEX idx_campaigns_window    ON business.content_campaigns(campaign_window_start, campaign_window_end);

-- campaign_weekly_themes: Level 2 — weekly sub-theme cascade
CREATE TABLE business.campaign_weekly_themes (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id                 UUID NOT NULL REFERENCES business.content_campaigns(id),
    organisation_id             UUID NOT NULL REFERENCES business.organisations(id),
    week_number                 SMALLINT NOT NULL CHECK (week_number BETWEEN 1 AND 12),
    sub_theme                   VARCHAR(300) NOT NULL,        -- "Prevention is cheaper than cure"
    narrative_hook              TEXT NOT NULL,                -- "Cost anxiety: ₹500 checkup vs ₹15,000 root canal"
    emotional_target            TEXT NOT NULL,                -- "Relief + motivation to book now"
    platform_execution_notes    JSONB,                       -- {platform: "note for this platform this week"}
    week_start_date             DATE NOT NULL,
    status                      VARCHAR(20) NOT NULL DEFAULT 'GENERATED' CHECK (status IN ('GENERATED','ACTIVE','COMPLETE')),
    tenant_id                   UUID NOT NULL,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_campaign_week UNIQUE (campaign_id, week_number)
);
CREATE INDEX idx_weekly_themes_campaign ON business.campaign_weekly_themes(campaign_id);

-- campaign_content_items: Level 3 — individual content pieces per platform per week
CREATE TYPE content_scr_status AS ENUM (
    'PENDING',             -- awaiting SCR review
    'SCR_PASSED',          -- all 5 SCR checks passed → eligible for auto-publish
    'SCR_FAILED',          -- failed checks after max regeneration → routed to customer
    'COMPLIANCE_VIOLATION',-- SCR Check 3 (compliance) failed → always routes to customer
    'CUSTOMER_APPROVED',   -- customer explicitly approved (after SCR_FAILED or POST_APPROVAL mode)
    'CUSTOMER_REJECTED',   -- customer rejected, returned for regeneration
    'PUBLISHED',           -- published to platform
    'PUBLISH_FAILED'       -- scheduling-mcp returned error
);

CREATE TABLE business.campaign_content_items (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id                 UUID NOT NULL REFERENCES business.content_campaigns(id),
    weekly_theme_id             UUID NOT NULL REFERENCES business.campaign_weekly_themes(id),
    organisation_id             UUID NOT NULL REFERENCES business.organisations(id),
    platform                    VARCHAR(50) NOT NULL,         -- INSTAGRAM_POST, YOUTUBE_SHORT, GBP_POST, etc.
    content_body                JSONB NOT NULL,              -- {caption, image_prompt, hashtags, cta, alt_text}
    audio_script                TEXT,                        -- voice script for video/audio platforms
    visual_storyboard           JSONB,                       -- scene-by-scene for video content
    scheduled_at                TIMESTAMPTZ NOT NULL,
    published_at                TIMESTAMPTZ,
    platform_post_id            VARCHAR(200),                -- external ID from platform API
    scr_status                  content_scr_status NOT NULL DEFAULT 'PENDING',
    regeneration_attempts       SMALLINT NOT NULL DEFAULT 0,
    approval_mode               campaign_approval_mode NOT NULL,
    tenant_id                   UUID NOT NULL,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_content_items_campaign  ON business.campaign_content_items(campaign_id);
CREATE INDEX idx_content_items_schedule  ON business.campaign_content_items(scheduled_at) WHERE scr_status IN ('SCR_PASSED','CUSTOMER_APPROVED');
CREATE INDEX idx_content_items_status    ON business.campaign_content_items(scr_status, organisation_id);

-- scr_review_records: SCR check results per content item (one row per review run)
CREATE TABLE business.scr_review_records (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content_item_id             UUID NOT NULL REFERENCES business.campaign_content_items(id),
    organisation_id             UUID NOT NULL REFERENCES business.organisations(id),
    regeneration_attempt        SMALLINT NOT NULL DEFAULT 0,
    check_1_theme_fidelity      scr_check_result NOT NULL DEFAULT 'NOT_RUN',
    check_1_score               DECIMAL(4,3),
    check_2_brand_voice         scr_check_result NOT NULL DEFAULT 'NOT_RUN',
    check_2_score               DECIMAL(4,3),
    check_3_compliance          scr_check_result NOT NULL DEFAULT 'NOT_RUN',
    check_3_violations          JSONB,                       -- list of compliance violations (if any)
    check_4_uniqueness          scr_check_result NOT NULL DEFAULT 'NOT_RUN',
    check_4_competitor_sim      DECIMAL(4,3),
    check_4_own_recency_sim     DECIMAL(4,3),
    check_5_quality             scr_check_result NOT NULL DEFAULT 'NOT_RUN',
    check_5_score               DECIMAL(4,3),
    overall_result              VARCHAR(20) NOT NULL DEFAULT 'PENDING' CHECK (overall_result IN ('PENDING','PASSED','FAILED','COMPLIANCE_VIOLATION')),
    reviewed_at                 TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    tenant_id                   UUID NOT NULL
);
CREATE INDEX idx_scr_records_item ON business.scr_review_records(content_item_id);
CREATE INDEX idx_scr_records_org  ON business.scr_review_records(organisation_id, reviewed_at DESC);

-- Prompt seeds: Campaign Theme Engine (C-055) + Platform Intelligence (DP-024) — v0.39.0
INSERT INTO institutional.agent_prompt_versions
    (prompt_id, version, skill_type, pipeline_step, agent_type, prompt_file_path, constitutional_basis, change_type, minimum_model_tier, reviewed_by, reviewed_at, is_active, activated_at)
VALUES
    ('DMA/CAMPAIGN/MASTER_THEME_PROPOSAL', '1.0.0', 'CONTENT_STRATEGY', 'MASTER_THEME_PROPOSAL', 'DIGITAL_MARKETING_HEALTHCARE', 'architecture/reference/prompts/README.md', 'C-055; C-036; C-037; C-050; AD-028; DP-024', 'BREAKING', 'FRONTIER', 'Enterprise Architect', NOW(), TRUE, NOW()),
    ('DMA/CAMPAIGN/WEEKLY_THEME_CASCADE', '1.0.0', 'CONTENT_STRATEGY', 'WEEKLY_THEME_CASCADE', 'DIGITAL_MARKETING_HEALTHCARE', 'architecture/reference/prompts/README.md', 'C-055; C-036; AD-028', 'BEHAVIOURAL', 'MID_TIER', 'Enterprise Architect', NOW(), TRUE, NOW()),
    ('DMA/CAMPAIGN/PLATFORM_CONTENT_VARIANT', '1.0.0', 'CONTENT_STRATEGY', 'PLATFORM_CONTENT_VARIANT', 'DIGITAL_MARKETING_HEALTHCARE', 'architecture/reference/prompts/README.md', 'C-055; C-036; C-052; AD-028; DP-024', 'BEHAVIOURAL', 'MID_TIER', 'Enterprise Architect', NOW(), TRUE, NOW()),
    ('DMA/CAMPAIGN/SCR_QUALITY_CHECK', '1.0.0', 'SYNTHETIC_CONTENT_REVIEW', 'SCR_QUALITY_CHECK', 'DIGITAL_MARKETING_HEALTHCARE', 'architecture/reference/prompts/README.md', 'C-055; C-052; DP-021', 'BEHAVIOURAL', 'MID_TIER', 'Enterprise Architect', NOW(), TRUE, NOW()),
    ('DMA/CAMPAIGN/CAMPAIGN_DIGEST', '1.0.0', 'CONTENT_STRATEGY', 'CAMPAIGN_DIGEST', 'DIGITAL_MARKETING_HEALTHCARE', 'architecture/reference/prompts/README.md', 'C-055; C-037; C-051', 'BEHAVIOURAL', 'MID_TIER', 'Enterprise Architect', NOW(), TRUE, NOW()),
    ('DMA/PLATFORM/PLATFORM_INTELLIGENCE_RESEARCH', '1.0.0', 'MARKET_RESEARCH', 'PLATFORM_INTELLIGENCE_RESEARCH', 'DIGITAL_MARKETING_HEALTHCARE', 'architecture/reference/prompts/README.md', 'C-036; C-037; DP-024', 'BEHAVIOURAL', 'MID_TIER', 'Enterprise Architect', NOW(), TRUE, NOW());

-- ============================================================
-- Simulation Gap Bridges (v0.40.0)
-- GAP-T015: Trading session records + slippage tracking
-- GAP-A013: Farmer price target
-- GAP-A011: IMD warning ID for PMFBY evidence chain
-- GAP-D006: SIR multi-skill evidence attribution (parent_request_id)
-- ============================================================

-- trading_session_records: per-session summary for trading agent (GAP-T015)
CREATE TABLE business.trading_session_records (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organisation_id             UUID NOT NULL REFERENCES business.organisations(id),
    employment_contract_id      UUID NOT NULL REFERENCES business.employment_contracts(id),
    session_date                DATE NOT NULL,
    session_start_at            TIMESTAMPTZ NOT NULL,
    session_end_at              TIMESTAMPTZ,
    session_type                VARCHAR(20) NOT NULL DEFAULT 'PAAS' CHECK (session_type IN ('PAAS', 'CRYPTO_ADVISORY')),
    trades_executed             SMALLINT NOT NULL DEFAULT 0,
    gross_pnl_inr               NUMERIC(12,2) NOT NULL DEFAULT 0,
    net_pnl_inr                 NUMERIC(12,2) NOT NULL DEFAULT 0,
    slippage_total_inr          NUMERIC(10,2) NOT NULL DEFAULT 0,   -- GAP-T015: intended vs actual fill
    slippage_pct_of_gross       NUMERIC(5,3),                        -- slippage as % of gross P&L
    worst_slippage_trade_id     UUID,                                -- references agent_evidence_records
    daily_loss_limit_utilization NUMERIC(5,3) NOT NULL DEFAULT 0,   -- 0.0 to 1.0
    daily_loss_limit_hit        BOOLEAN NOT NULL DEFAULT FALSE,
    pending_orders_cancelled    SMALLINT NOT NULL DEFAULT 0,         -- GAP-T014: orders cancelled at limit
    vix_at_session_start        NUMERIC(6,2),
    vix_regime                  VARCHAR(20) CHECK (vix_regime IN ('LOW','MEDIUM','ELEVATED','HIGH')),
    position_size_reduction_pct NUMERIC(5,2),                        -- GAP-T011: volatility regime response
    session_status              VARCHAR(20) NOT NULL DEFAULT 'ACTIVE' CHECK (session_status IN ('ACTIVE','COMPLETED','EMERGENCY_STOPPED','LOSS_LIMIT_HIT')),
    emergency_stop_at           TIMESTAMPTZ,
    evidence_record_count       SMALLINT NOT NULL DEFAULT 0,
    reasoning_trace_id          UUID REFERENCES institutional.agent_reasoning_traces(id),
    tenant_id                   UUID NOT NULL,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_trading_session_contract ON business.trading_session_records(employment_contract_id, session_date DESC);
CREATE INDEX idx_trading_session_date     ON business.trading_session_records(session_date DESC);

-- farmer_profiles: add stated_price_target (GAP-A013)
-- Note: farmer_profiles table created in earlier migration; adding column here
ALTER TABLE business.farmer_profiles
    ADD COLUMN IF NOT EXISTS stated_price_target_inr_per_quintal NUMERIC(8,2),
    ADD COLUMN IF NOT EXISTS price_target_updated_at TIMESTAMPTZ;

-- weather_alert_log: add IMD warning reference (GAP-A011)
-- Note: weather_alert_log table created in agricultural advisor spec; adding column here
ALTER TABLE business.weather_alert_log
    ADD COLUMN IF NOT EXISTS imd_warning_id VARCHAR(100),
    ADD COLUMN IF NOT EXISTS imd_warning_fetched_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS imd_warning_confirmed BOOLEAN NOT NULL DEFAULT FALSE;
CREATE INDEX IF NOT EXISTS idx_weather_alert_imd ON business.weather_alert_log(imd_warning_id) WHERE imd_warning_id IS NOT NULL;

-- agent_evidence_records: add parent_request_id for SIR multi-skill attribution (GAP-D006)
-- Groups all evidence records from a single customer request that triggered SIR multi-skill orchestration
ALTER TABLE institutional.agent_evidence_records
    ADD COLUMN IF NOT EXISTS parent_request_id UUID,
    ADD COLUMN IF NOT EXISTS sir_skill_position SMALLINT;  -- position in SIR execution sequence (1, 2, 3...)
CREATE INDEX IF NOT EXISTS idx_evidence_parent_request ON institutional.agent_evidence_records(parent_request_id) WHERE parent_request_id IS NOT NULL;

-- signal_bundling_log: tracks multi-signal bundling decisions (GAP-A010)
CREATE TABLE institutional.signal_bundling_log (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organisation_id             UUID NOT NULL REFERENCES business.organisations(id),
    bundle_session_id           UUID NOT NULL,              -- all signals in same bundle share this ID
    signal_type                 VARCHAR(100) NOT NULL,
    urgency_class               VARCHAR(20) NOT NULL,
    bundled_with                UUID[],                     -- other signal IDs in the same bundle
    bundling_decision           VARCHAR(30) NOT NULL CHECK (bundling_decision IN ('IMMEDIATE_SOLO','HELD_FOR_BUNDLE','DEFERRED_TO_HEARTBEAT')),
    hold_until                  TIMESTAMPTZ,
    delivered_at                TIMESTAMPTZ,
    bundle_message_sent         BOOLEAN NOT NULL DEFAULT FALSE,
    logged_at                   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_signal_bundle_org ON institutional.signal_bundling_log(organisation_id, logged_at DESC);

-- ============================================================
-- Centralized Ad Account Management (v0.43.0 — C-056, ADR-026)
-- ============================================================

-- connection_model enum: WAOOAW_MANAGED (default) | CUSTOMER_OWNED (pending Founder auth)
CREATE TYPE ads_connection_model AS ENUM (
    'WAOOAW_MANAGED',   -- WAOOAW MBM + Google MCC (default, ADR-026)
    'CUSTOMER_OWNED'    -- per-customer OAuth (PENDING_FOUNDER_AUTHORIZATION)
);

-- customer_ad_accounts: sub-accounts under WAOOAW's MBM and Google MCC (per customer)
CREATE TABLE business.customer_ad_accounts (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organisation_id             UUID NOT NULL REFERENCES business.organisations(id),
    employment_contract_id      UUID NOT NULL REFERENCES business.employment_contracts(id),
    connection_model            ads_connection_model NOT NULL DEFAULT 'WAOOAW_MANAGED',

    -- WAOOAW_MANAGED fields (populated for WAOOAW_MANAGED model)
    meta_sub_account_id         VARCHAR(100),          -- customer's sub-account ID in WAOOAW's Meta MBM
    meta_page_id                VARCHAR(100),          -- customer's Facebook Page ID (granted to WAOOAW's MBM)
    meta_page_access_granted_at TIMESTAMPTZ,           -- when customer granted their Page to WAOOAW's MBM
    google_ads_client_id        VARCHAR(100),          -- customer's client account ID in WAOOAW's MCC
    google_analytics_property   VARCHAR(100),          -- linked GA4 property

    -- Management fee configuration (C-056 — fixed at contract formation)
    management_fee_pct          NUMERIC(4,2) NOT NULL DEFAULT 10.00,  -- 10%
    minimum_monthly_spend_inr   INTEGER NOT NULL DEFAULT 200000,       -- ₹2,000 in paise

    -- CUSTOMER_OWNED fields (populated only for CUSTOMER_OWNED model)
    customer_meta_bm_id         VARCHAR(100),          -- customer's own Meta Business Manager ID
    customer_google_ads_id      VARCHAR(100),          -- customer's own Google Ads account ID

    status                      VARCHAR(20) NOT NULL DEFAULT 'SETUP_PENDING'
                                CHECK (status IN ('SETUP_PENDING','ACTIVE','SUSPENDED','TERMINATING','TRANSFERRED','DELETED')),
    activated_at                TIMESTAMPTZ,
    terminated_at               TIMESTAMPTZ,
    transfer_target_bm_id       VARCHAR(100),          -- for TRANSFER at termination
    tenant_id                   UUID NOT NULL,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_ad_account_contract UNIQUE (employment_contract_id)
);
CREATE INDEX idx_ad_accounts_org ON business.customer_ad_accounts(organisation_id, status);

-- ad_spend_wallets: per-customer prepaid Ad Spend Wallet (C-056 segregation)
CREATE TABLE business.ad_spend_wallets (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organisation_id             UUID NOT NULL REFERENCES business.organisations(id),
    employment_contract_id      UUID NOT NULL REFERENCES business.employment_contracts(id),
    ad_account_id               UUID NOT NULL REFERENCES business.customer_ad_accounts(id),

    -- Balance tracking (all values in INR paise for precision)
    funded_balance_paise        BIGINT NOT NULL DEFAULT 0,   -- total topped up, not yet charged
    spent_balance_paise         BIGINT NOT NULL DEFAULT 0,   -- confirmed charged to Meta/Google
    pending_spend_paise         BIGINT NOT NULL DEFAULT 0,   -- committed to campaigns, not yet billed
    management_fee_charged_paise BIGINT NOT NULL DEFAULT 0,  -- total management fee deducted
    credits_received_paise      BIGINT NOT NULL DEFAULT 0,   -- Meta/Google credits passed through

    -- available = funded - spent - pending
    monthly_budget_cap_paise    BIGINT NOT NULL,             -- C-043 Constitutional Floor
    current_month               DATE NOT NULL DEFAULT DATE_TRUNC('month', NOW()),

    last_topup_at               TIMESTAMPTZ,
    last_charge_at              TIMESTAMPTZ,
    low_balance_alert_sent_at   TIMESTAMPTZ,                 -- tracks when LOW_BALANCE SIL signal last fired
    tenant_id                   UUID NOT NULL,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_wallet_contract UNIQUE (employment_contract_id)
);
CREATE INDEX idx_ad_wallets_org ON business.ad_spend_wallets(organisation_id);

-- ad_spend_ledger: complete audit trail of every ad spend event (C-056 evidentiary record)
-- This table is append-only — no UPDATE or DELETE (same immutability as evidence_records)
CREATE TYPE ad_spend_transaction_type AS ENUM (
    'TOPUP',            -- customer funded the wallet via Razorpay
    'CHARGE',           -- Meta/Google billed WAOOAW for this customer's campaigns
    'MANAGEMENT_FEE',   -- WAOOAW's 10% management fee on the CHARGE
    'CREDIT',           -- Meta/Google issued a promotional credit → passed to customer
    'REFUND',           -- Razorpay refund of unused wallet balance (at termination)
    'ADJUSTMENT'        -- WAOOAW manually corrects an error (requires constitutional evidence record)
);

CREATE TABLE business.ad_spend_ledger (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organisation_id             UUID NOT NULL REFERENCES business.organisations(id),
    employment_contract_id      UUID NOT NULL REFERENCES business.employment_contracts(id),
    wallet_id                   UUID NOT NULL REFERENCES business.ad_spend_wallets(id),

    transaction_type            ad_spend_transaction_type NOT NULL,
    amount_paise                BIGINT NOT NULL,           -- always positive; direction determined by type
    platform                    VARCHAR(20) CHECK (platform IN ('META','GOOGLE','WAOOAW','RAZORPAY')),
    external_campaign_id        VARCHAR(200),              -- Meta/Google campaign ID (for CHARGE records)
    external_invoice_id         VARCHAR(200),              -- Meta/Google billing invoice reference
    razorpay_payment_id         VARCHAR(100),              -- for TOPUP and REFUND records
    management_fee_basis_paise  BIGINT,                    -- for MANAGEMENT_FEE rows: the CHARGE amount this fee is based on
    evidence_record_id          UUID,                      -- CE evidence record ID (C-023 — Evidence First)
    description                 TEXT,                      -- human-readable description for invoice
    billing_month               DATE NOT NULL DEFAULT DATE_TRUNC('month', NOW()),
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW()
    -- NOTE: No updated_at, no tenant_id needed — this is immutable financial audit record
);
CREATE INDEX idx_ad_ledger_wallet    ON business.ad_spend_ledger(wallet_id, billing_month DESC);
CREATE INDEX idx_ad_ledger_org       ON business.ad_spend_ledger(organisation_id, billing_month DESC);
CREATE INDEX idx_ad_ledger_type      ON business.ad_spend_ledger(transaction_type, billing_month DESC);
CREATE INDEX idx_ad_ledger_campaign  ON business.ad_spend_ledger(external_campaign_id) WHERE external_campaign_id IS NOT NULL;

-- ============================================================
-- DMA Performance Portfolio — Tier 3 Agency Track Record (v0.44.0 — C-057)
-- Anonymized aggregate performance register — no individual customer data
-- Used in onboarding conversations and portal agency pitch
-- ============================================================

CREATE TABLE institutional.dma_performance_portfolio (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    professional_type           VARCHAR(100) NOT NULL DEFAULT 'DIGITAL_MARKETING_HEALTHCARE',
    business_domain             VARCHAR(100) NOT NULL,    -- DENTAL_CLINIC, BEAUTY_ARTIST, etc.
    city_tier                   VARCHAR(10) NOT NULL CHECK (city_tier IN ('TIER_1','TIER_2','TIER_3')),
    cohort_size                 INTEGER NOT NULL,          -- number of active customers in cohort
    avg_enquiry_increase_pct    NUMERIC(5,2),              -- avg % increase in enquiry signals vs baseline
    content_adherence_rate      NUMERIC(5,2),              -- avg % content calendar adherence
    avg_maturity_score_change   NUMERIC(4,2),              -- avg maturity score gain in 3 months
    avg_time_to_first_result_days INTEGER,                 -- days until first measurable KPI signal
    avg_cpl_inr                 NUMERIC(8,2),              -- avg cost per lead (Skill 11 customers only)
    avg_campaign_roas           NUMERIC(6,2),              -- avg ROAS for Skill 11 customers
    portfolio_claim_approved    BOOLEAN NOT NULL DEFAULT FALSE,  -- must be EA-approved before portal use
    data_quality_score          NUMERIC(3,2),              -- how many customers have complete KPI data
    portfolio_period            DATE NOT NULL,             -- which month this snapshot covers
    computed_at                 TIMESTAMPTZ NOT NULL DEFAULT NOW()
    -- C-052: This table contains NO individual customer data — only cohort aggregates.
    -- C-002: portfolio_claim_approved = TRUE required before any claim is shown in portal or agent conversation.
);
CREATE INDEX idx_portfolio_domain ON institutional.dma_performance_portfolio(professional_type, business_domain, city_tier, portfolio_period DESC);
-- Note: no RLS — institutional table. No PII. Accessible by ai_runtime (onboarding RAG) and business_app (portal display).
GRANT SELECT, INSERT, UPDATE ON institutional.dma_performance_portfolio TO ai_runtime_app;
GRANT SELECT                 ON institutional.dma_performance_portfolio TO business_app;

-- Prompt seeds: AI Agency Onboarding + Portfolio (C-057) — v0.44.0
INSERT INTO institutional.agent_prompt_versions
    (prompt_id, version, skill_type, pipeline_step, agent_type, prompt_file_path, constitutional_basis, change_type, minimum_model_tier, reviewed_by, reviewed_at, is_active, activated_at)
VALUES
    ('DMA/ONBOARDING/PROFESSIONAL_INTAKE_OPENING', '1.0.0', 'CUSTOMER_PROFILING', 'PROFESSIONAL_INTAKE_OPENING', 'DIGITAL_MARKETING_HEALTHCARE', 'architecture/reference/prompts/README.md', 'C-057; C-036; C-037; C-040', 'BEHAVIOURAL', 'FRONTIER', 'Enterprise Architect', NOW(), TRUE, NOW()),
    ('DMA/ONBOARDING/COMPETITIVE_POSITIONING', '1.0.0', 'CUSTOMER_PROFILING', 'COMPETITIVE_POSITIONING', 'DIGITAL_MARKETING_HEALTHCARE', 'architecture/reference/prompts/README.md', 'C-057; C-049; C-002', 'BEHAVIOURAL', 'MID_TIER', 'Enterprise Architect', NOW(), TRUE, NOW()),
    ('DMA/PORTFOLIO/PORTFOLIO_CLAIM_GENERATION', '1.0.0', 'MARKET_RESEARCH', 'PORTFOLIO_CLAIM_GENERATION', 'DIGITAL_MARKETING_HEALTHCARE', 'architecture/reference/prompts/README.md', 'C-057; C-002; C-052', 'BEHAVIOURAL', 'MID_TIER', 'Enterprise Architect', NOW(), TRUE, NOW());

-- ============================================================
-- DMA Skill Deepening Tables (v0.45.0 — P0: Review gen, Blog, Patient reactivation)
-- ============================================================

-- review_requests: tracks review request messages sent to patients (Skill 6+7)
CREATE TABLE business.review_requests (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organisation_id             UUID NOT NULL REFERENCES business.organisations(id),
    employment_contract_id      UUID NOT NULL REFERENCES business.employment_contracts(id),
    patient_identifier          VARCHAR(200) NOT NULL,    -- hashed phone or patient_id — no plain PII
    trigger_type                VARCHAR(30) NOT NULL CHECK (trigger_type IN ('POST_APPOINTMENT','TREATMENT_COMPLETE','WELCOME_DAY3')),
    channel                     VARCHAR(20) NOT NULL DEFAULT 'WHATSAPP',
    message_template_id         VARCHAR(100) NOT NULL,    -- which HSM template was used
    sent_at                     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    review_detected_at          TIMESTAMPTZ,              -- NULL until Google review detected
    review_detected             BOOLEAN NOT NULL DEFAULT FALSE,
    next_eligible_at            TIMESTAMPTZ NOT NULL,     -- 3 months from sent_at (rate limiting)
    opted_out                   BOOLEAN NOT NULL DEFAULT FALSE,
    evidence_record_id          UUID,
    tenant_id                   UUID NOT NULL,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_review_requests_org ON business.review_requests(organisation_id, sent_at DESC);
CREATE INDEX idx_review_requests_patient ON business.review_requests(organisation_id, patient_identifier, next_eligible_at);

-- blog_posts: tracks blog content from draft to published to performance (Skill 10)
CREATE TYPE blog_post_status AS ENUM (
    'DRAFT',          -- agent generated, not yet reviewed
    'CUSTOMER_REVIEW', -- awaiting customer approval
    'APPROVED',        -- customer approved, ready to publish
    'PUBLISHED',       -- live on website
    'REJECTED'         -- customer rejected; return for revision
);

CREATE TABLE business.blog_posts (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organisation_id             UUID NOT NULL REFERENCES business.organisations(id),
    employment_contract_id      UUID NOT NULL REFERENCES business.employment_contracts(id),
    title                       VARCHAR(300) NOT NULL,
    slug                        VARCHAR(300),              -- URL slug (generated at draft; confirmed at publish)
    primary_keyword             VARCHAR(200) NOT NULL,
    secondary_keywords          TEXT[],
    content_pillar              VARCHAR(20) CHECK (content_pillar IN ('EDUCATIONAL','COMMERCIAL','LOCAL','TRUST')),
    word_count                  INTEGER,
    status                      blog_post_status NOT NULL DEFAULT 'DRAFT',
    draft_content               TEXT,                      -- full blog post text (Markdown)
    published_url               VARCHAR(500),              -- set when PUBLISHED
    cms_post_id                 VARCHAR(200),              -- WordPress post ID or equivalent
    search_impressions_mtd      INTEGER,                   -- Google Search Console: current month
    search_clicks_mtd           INTEGER,                   -- Google Search Console: current month
    avg_position_mtd            NUMERIC(5,2),              -- average ranking position
    drafted_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    approved_at                 TIMESTAMPTZ,
    published_at                TIMESTAMPTZ,
    evidence_record_id          UUID,
    tenant_id                   UUID NOT NULL
);
CREATE INDEX idx_blog_posts_org ON business.blog_posts(organisation_id, status);
CREATE INDEX idx_blog_posts_published ON business.blog_posts(organisation_id, published_at DESC) WHERE status = 'PUBLISHED';

-- patient_reactivation_log: tracks dormant patient outreach (Skill 7)
CREATE TABLE business.patient_reactivation_log (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organisation_id             UUID NOT NULL REFERENCES business.organisations(id),
    employment_contract_id      UUID NOT NULL REFERENCES business.employment_contracts(id),
    patient_identifier          VARCHAR(200) NOT NULL,    -- hashed phone — no plain PII
    last_appointment_date       DATE,                     -- from clinic data or customer input
    days_since_last_visit       INTEGER,                  -- computed at time of outreach
    reactivation_sent_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    responded                   BOOLEAN NOT NULL DEFAULT FALSE,
    booked_appointment          BOOLEAN NOT NULL DEFAULT FALSE,
    response_at                 TIMESTAMPTZ,
    follow_up_sent_at           TIMESTAMPTZ,              -- second contact if no response in 7 days
    archived_at                 TIMESTAMPTZ,              -- after 2 contacts with no response
    campaign_id                 UUID,                     -- which reactivation campaign this belongs to
    evidence_record_id          UUID,
    tenant_id                   UUID NOT NULL
);
CREATE INDEX idx_reactivation_org ON business.patient_reactivation_log(organisation_id, reactivation_sent_at DESC);
