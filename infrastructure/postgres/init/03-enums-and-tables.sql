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
