-- ============================================================
-- 07-agent-prompts.sql — professional.agent_prompts table
-- ============================================================
-- Constitutional basis: C-045 (LLM inference is professional judgment),
--                       C-059 (Implementation Traceability — prompt version traces to Git sha),
--                       C-069 (Platform Self-Improvement Obligation),
--                       ADR-028 (Steward/Customer LLM tier separation)
--
-- PURPOSE:
--   Prompts are version-controlled in architecture/reference/prompts/*.md (Git source of truth).
--   This table is the runtime representation: seeded from .md files by seed-prompts.py during
--   CI/CD. The AI Runtime reads prompt_text from here at request time — never from the container
--   image. Prompt content is encrypted at rest via Azure PostgreSQL Transparent Data Encryption.
--
-- SCHEMA: professional (Professional Experience Ledger — WAOOAW IP, not customer data)
--
-- PIPELINE:
--   .md file in Git → CI merge trigger → seed-prompts.py → INSERT here
--   AI Runtime → SELECT WHERE is_active=true → LLM dispatch
--   Rollback → UPDATE SET is_active=false (new), is_active=true (previous)
--
-- GAP CLOSED: G-INSTINCT-07 (no agent_prompts table), G-STEWARD-02 (DB migration missing)
-- ============================================================

SET search_path TO professional, public;

-- ─── Enums ───────────────────────────────────────────────────────────────────

-- Agent types — must stay in sync with AGENT-AUTHORING-GUIDE and acceptance scenarios
CREATE TYPE agent_type AS ENUM (
    'DMA',                      -- WaooaW Expert Digital Marketing Agent
    'TRADING',                  -- WaooaW Expert Trading Advisor
    'AGRICULTURAL',             -- WaooaW Expert Agricultural Advisor
    'PRIVATE_TUTOR',            -- WaooaW Expert Private Tutor
    'PLATFORM_IT_EXPERT',       -- Internal: WAOOAW AI Agent — Platform IT Expert
    'STEWARD_ASSISTANT',        -- Internal: WAOOAW AI Agent — Steward Assistant (C-068)
    'SELF_IMPROVEMENT_ANALYST', -- Internal: WAOOAW AI Agent — Self-Improvement Analyst (C-069)
    'QA',                       -- Internal: WAOOAW AI Agent — QA
    'PLATFORM_OPERATIONS'       -- Internal: WAOOAW AI Agent — Platform Operations
);

-- Simulation grade — matches acceptance scenario grading in AGENT-AUTHORING-GUIDE
CREATE TYPE simulation_grade AS ENUM (
    'A',    -- All acceptance criteria met, zero constitutional violations
    'B',    -- Minor deviations, no constitutional violations, improvement recommended
    'C',    -- Significant deviations or performance degradation — must be fixed before production
    'FAIL'  -- Constitutional violation detected — blocked from production by CI gate
);

-- Minimum model tier required for this prompt (ADR-024, ADR-028)
CREATE TYPE prompt_model_tier AS ENUM (
    'LOCAL',        -- Ollama Llama 3.2 — classification and low-stakes text
    'MID_TIER',     -- Azure OpenAI gpt-4o-mini — standard advisory
    'FRONTIER'      -- Azure OpenAI gpt-4o (or configured STEWARD_FRONTIER_MODEL) — strategy + constitutional
);

-- ─── Core Table ──────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS professional.agent_prompts (
    -- Identity
    id                      UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_type              agent_type  NOT NULL,
    skill_id                INTEGER     NOT NULL,           -- Matches skill number in agent spec (e.g., DMA Skill 3 = 3)
    skill_name              VARCHAR(120) NOT NULL,          -- Human-readable: "Instagram Content Creation"
    prompt_role             VARCHAR(30) NOT NULL            -- 'system' | 'user_template' | 'context_injection'
                            CHECK (prompt_role IN ('system', 'user_template', 'context_injection')),

    -- Content (encrypted at rest by Azure PostgreSQL TDE)
    prompt_text             TEXT        NOT NULL,           -- The actual prompt. Never in container image.
    prompt_variables        JSONB       NOT NULL DEFAULT '[]', -- Variable names injected at runtime: ["customer_name", "budget"]

    -- Version control (C-059 — traces every runtime call to exact Git commit)
    version                 INTEGER     NOT NULL DEFAULT 1,
    git_sha                 VARCHAR(40) NOT NULL,           -- Full 40-char Git commit SHA
    git_branch              VARCHAR(200),                   -- Branch prompt was merged from (informational)
    md_source_path          VARCHAR(300) NOT NULL,          -- e.g., architecture/reference/prompts/dma-agent-prompts.md

    -- Quality gate (C-069 — simulation grade must be captured at seed time)
    simulation_grade        simulation_grade NOT NULL,
    simulation_run_id       UUID,                          -- References simulation run that produced this grade
    simulation_acceptance_scenario VARCHAR(20),            -- e.g., 'AS-001', 'AS-003'

    -- LLM routing (ADR-028)
    minimum_model_tier      prompt_model_tier NOT NULL DEFAULT 'MID_TIER',

    -- Lifecycle
    is_active               BOOLEAN     NOT NULL DEFAULT FALSE, -- Only ONE row per (agent_type, skill_id, prompt_role) is TRUE
    seeded_at               TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    retired_at              TIMESTAMPTZ,                    -- Set when a newer version becomes active
    retired_by_sha          VARCHAR(40),                    -- Git SHA that retired this version

    -- Audit (C-023 Evidence First)
    seeded_by_pipeline_run  VARCHAR(200),                  -- GitHub Actions run URL
    constitutional_basis    VARCHAR(500) NOT NULL           -- e.g., 'C-045, C-047, C-048'
);

-- Constraint: only one active prompt per (agent_type, skill_id, prompt_role)
CREATE UNIQUE INDEX IF NOT EXISTS idx_agent_prompts_active_singleton
    ON professional.agent_prompts (agent_type, skill_id, prompt_role)
    WHERE is_active = TRUE;

-- Performance: AI Runtime hot path — fetch active prompt by agent + skill
CREATE INDEX IF NOT EXISTS idx_agent_prompts_active_lookup
    ON professional.agent_prompts (agent_type, skill_id, prompt_role, is_active);

-- Version history lookup
CREATE INDEX IF NOT EXISTS idx_agent_prompts_version_history
    ON professional.agent_prompts (agent_type, skill_id, version DESC);

-- Git SHA traceability (C-059)
CREATE INDEX IF NOT EXISTS idx_agent_prompts_sha
    ON professional.agent_prompts (git_sha);

COMMENT ON TABLE professional.agent_prompts IS
    'Runtime prompt store. Seeded from Git .md files by seed-prompts.py during CI/CD. '
    'Never baked into container images. AI Runtime reads at request time. '
    'ADR-028: prompt_text encrypted at rest (Azure PostgreSQL TDE). '
    'C-059: git_sha traces every runtime call to exact commit.';

-- ─── Improvement Proposals Table (C-069 — Self-Improvement Analyst output) ──

CREATE TABLE IF NOT EXISTS professional.improvement_proposals (
    id                      UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_type              agent_type  NOT NULL,
    skill_id                INTEGER     NOT NULL,
    skill_name              VARCHAR(120) NOT NULL,

    -- Trigger evidence (C-023 — evidence before action)
    trigger_type            VARCHAR(50) NOT NULL            -- 'C049_ESCALATION_CLUSTER' | 'GRADE_DEGRADATION' | 'CCT_FAILURE' | 'C048_DETECTION'
                            CHECK (trigger_type IN ('C049_ESCALATION_CLUSTER', 'GRADE_DEGRADATION', 'CCT_FAILURE', 'C048_DETECTION')),
    evidence_window_start   TIMESTAMPTZ NOT NULL,
    evidence_window_end     TIMESTAMPTZ NOT NULL,
    evidence_count          INTEGER     NOT NULL,           -- e.g., number of C-049 escalations observed
    evidence_audit_record_ids UUID[]    NOT NULL DEFAULT '{}', -- References constitutional.audit_records

    -- Proposal content
    failure_pattern_summary TEXT        NOT NULL,           -- What pattern was detected
    improvement_hypothesis  TEXT        NOT NULL,           -- What the Self-Improvement Analyst recommends
    proposed_prompt_change  TEXT,                          -- Draft prompt text, if applicable

    -- GitHub traceability (C-059)
    github_issue_url        VARCHAR(300),                  -- Created by Self-Improvement Analyst via GitHub API
    github_issue_number     INTEGER,

    -- Lifecycle
    status                  VARCHAR(30) NOT NULL DEFAULT 'PENDING_SUJAY_REVIEW'
                            CHECK (status IN (
                                'PENDING_SUJAY_REVIEW',
                                'SUJAY_APPROVED',
                                'SUJAY_REJECTED',
                                'IMPLEMENTED',
                                'SUPERSEDED'
                            )),
    detected_at             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    notified_sujay_at       TIMESTAMPTZ,                   -- When Steward Assistant sent notification
    resolved_at             TIMESTAMPTZ,
    resolved_by_prompt_id   UUID REFERENCES professional.agent_prompts(id)
);

CREATE INDEX IF NOT EXISTS idx_improvement_proposals_pending
    ON professional.improvement_proposals (status, agent_type)
    WHERE status = 'PENDING_SUJAY_REVIEW';

CREATE INDEX IF NOT EXISTS idx_improvement_proposals_by_agent
    ON professional.improvement_proposals (agent_type, skill_id, detected_at DESC);

COMMENT ON TABLE professional.improvement_proposals IS
    'Self-improvement proposals raised by WAOOAW AI Agent — Self-Improvement Analyst (C-069). '
    'Each row is backed by audit_record evidence. Only PENDING_SUJAY_REVIEW rows are actionable. '
    'Sujay reviews via Steward Assistant chat — never directly touches this table.';

-- ─── Trust Ledger Table (G-INSTINCT-08 — trust data structure) ───────────────

CREATE TABLE IF NOT EXISTS professional.trust_ledger (
    id                          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_type                  agent_type  NOT NULL,
    customer_id                 UUID        NOT NULL,       -- References business.customers — no FK to preserve portability
    period_start                DATE        NOT NULL,
    period_end                  DATE        NOT NULL,       -- Typically 30-day rolling window

    -- Evidence counts (all sourced from constitutional.audit_records)
    sessions_completed          INTEGER     NOT NULL DEFAULT 0,
    c048_violations             INTEGER     NOT NULL DEFAULT 0,  -- Information exploitation events
    c049_escalations            INTEGER     NOT NULL DEFAULT 0,  -- Honest limitation disclosures
    emergency_stops_triggered   INTEGER     NOT NULL DEFAULT 0,
    grade_a_simulations         INTEGER     NOT NULL DEFAULT 0,
    grade_b_simulations         INTEGER     NOT NULL DEFAULT 0,
    grade_c_simulations         INTEGER     NOT NULL DEFAULT 0,
    customer_satisfaction_signals INTEGER   NOT NULL DEFAULT 0,  -- Positive explicit feedback signals

    -- Computed trust score: 0.00 (no trust) to 1.00 (full trust)
    -- Formula: (grade_a / total_sessions) * 0.6
    --          - (c048_violations * 0.2)
    --          - (c049_escalations / sessions_completed * 0.1)
    --          + (customer_satisfaction_signals / sessions_completed * 0.1)
    --          clamped to [0.00, 1.00]
    computed_trust_score        DECIMAL(3,2) NOT NULL DEFAULT 0.00
                                CHECK (computed_trust_score >= 0.00 AND computed_trust_score <= 1.00),

    -- Autonomy tier earned by this agent for this customer (C-066 + G-INSTINCT-09)
    -- Starts at Tier 1 (Sujay approval for non-constitutional actions).
    -- After 30 sessions with trust_score >= 0.95: earns Tier 0 within this customer scope.
    -- C-048 violation resets to Tier 1 immediately. C-066 absolute tiers never lowered below.
    authorized_autonomy_tier    INTEGER     NOT NULL DEFAULT 1
                                CHECK (authorized_autonomy_tier IN (0, 1, 2)),

    -- Audit
    computed_at                 TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    computation_run_id          UUID        -- References the Temporal workflow run that computed this

    CONSTRAINT trust_ledger_period_check CHECK (period_end > period_start)
);

-- Only one trust record per (agent, customer, period)
CREATE UNIQUE INDEX IF NOT EXISTS idx_trust_ledger_period
    ON professional.trust_ledger (agent_type, customer_id, period_start, period_end);

-- Customer dashboard query: current trust for a customer's agents
CREATE INDEX IF NOT EXISTS idx_trust_ledger_customer_current
    ON professional.trust_ledger (customer_id, agent_type, period_end DESC);

COMMENT ON TABLE professional.trust_ledger IS
    'Trust score per agent-customer relationship, computed over rolling 30-day windows. '
    'Source of truth for autonomy tier decisions (G-INSTINCT-09). '
    'Computed by WAOOAW AI Agent — Platform Operations nightly Temporal workflow. '
    'C-002: trust is earned through observable evidence — this table IS that evidence.';
