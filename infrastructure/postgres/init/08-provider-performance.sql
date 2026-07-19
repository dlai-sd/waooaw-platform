-- ============================================================
-- 08-provider-performance.sql — institutional.provider_performance
-- ============================================================
-- Constitutional basis: C-069 (Platform Self-Improvement — platform must use
--                                evidence to improve its own provider choices),
--                       C-051 (Resource Transparency — cost must be traceable),
--                       ADR-029 (Multi-provider LLM strategy)
--
-- PURPOSE:
--   Records per-provider, per-tier performance metrics after every LLM dispatch.
--   The Provider Selection Engine (PSE) reads this table to rank providers
--   in real time. The Self-Improvement Analyst reads it for weekly Steward reports.
--
-- SCHEMA: institutional (WAOOAW IP — not customer data, not subject to RLS)
--
-- WRITE PATH: AI Runtime → after every LLM call → INSERT one row
-- READ PATH:  PSE → rolling 1h/10min aggregate queries → provider ranking
--             Self-Improvement Analyst → nightly scan → Steward weekly digest
--             OTel exporter → Azure Monitor / Jaeger for dashboards
--
-- GAP CLOSED: ADR-029 Decision 2 (Provider Selection Engine)
-- ============================================================

SET search_path TO institutional, public;

-- ─── Enums ───────────────────────────────────────────────────────────────────

CREATE TYPE llm_provider AS ENUM (
    'ollama_llama3',          -- LOCAL: Ollama + Llama 3.2 3B (classification gate)
    'ollama_ai4bharat',       -- LOCAL: AI4Bharat IndicBERT (Indian language tasks)
    'google_gemini_flash',    -- MID_TIER: Gemini 2.0 Flash (Vertex AI asia-south1)
    'sarvam_saaras',          -- MID_TIER: Sarvam AI Saaras (Agricultural agent override)
    'azure_gpt4o_mini',       -- MID_TIER fallback: Azure OpenAI GPT-4o-mini (UAE North)
    'google_gemini_pro',      -- FRONTIER: Gemini 2.5 Pro (Vertex AI asia-south1)
    'azure_gpt4o'             -- FRONTIER fallback: Azure OpenAI GPT-4o (UAE North)
);

CREATE TYPE llm_dispatch_outcome AS ENUM (
    'SUCCESS',         -- Response received, used by agent
    'RATE_LIMITED',    -- Provider returned 429 — fallback triggered
    'TIMEOUT',         -- Provider exceeded latency threshold — fallback triggered
    'ERROR',           -- Provider returned 5xx — fallback triggered
    'CIRCUIT_OPEN',    -- PSE circuit-breaker was open — provider not attempted
    'FALLBACK_USED'    -- This row IS the fallback call (primary failed)
);

-- ─── Raw Dispatch Events ─────────────────────────────────────────────────────
-- One row per LLM call. High-volume table — partitioned by month.

CREATE TABLE IF NOT EXISTS institutional.provider_dispatch_events (
    id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Request context (anonymised — no customer PII)
    session_id          UUID        NOT NULL,           -- Temporal workflow ID
    agent_type          VARCHAR(50) NOT NULL,           -- e.g., 'DMA', 'AGRICULTURAL'
    skill_id            INTEGER,                        -- Skill that triggered this call
    message_category    VARCHAR(50),                    -- ADR-024 category: ACTIONABLE_ADVISORY etc.
    message_language    VARCHAR(10),                    -- BCP-47: 'hi', 'mr', 'en', etc.
    plan_tier           VARCHAR(20) NOT NULL DEFAULT 'essential', -- Customer plan tier (ADR-028)
    is_steward_session  BOOLEAN     NOT NULL DEFAULT FALSE,

    -- Provider selection
    provider            llm_provider NOT NULL,
    model_version       VARCHAR(100),                  -- e.g., 'gemini-2.0-flash-001'
    tier_requested      VARCHAR(20) NOT NULL,          -- 'LOCAL' | 'MID_TIER' | 'FRONTIER'
    was_fallback        BOOLEAN     NOT NULL DEFAULT FALSE,
    fallback_reason     VARCHAR(200),                  -- Why primary was skipped (PSE rule ID)
    pse_rule_applied    VARCHAR(20),                   -- Winning rule: PSE-R01 to PSE-R08
    composite_score     DECIMAL(5,4),                  -- PSE score at selection time

    -- Performance metrics
    outcome             llm_dispatch_outcome NOT NULL,
    latency_ms          INTEGER,                       -- NULL if circuit-open (not attempted)
    input_tokens        INTEGER,
    output_tokens       INTEGER,
    cost_inr            DECIMAL(8,4),                  -- Computed cost in INR

    -- Quality (populated post-call when available)
    c049_escalated      BOOLEAN     NOT NULL DEFAULT FALSE,  -- Did this call trigger C-049?
    prompt_sha          VARCHAR(40),                   -- Links to professional.agent_prompts

    -- Data residency audit (DPDPA)
    data_region         VARCHAR(30) NOT NULL,          -- 'india', 'uae', 'on-premise'
    pii_in_request      BOOLEAN     NOT NULL DEFAULT FALSE,  -- Was PII present in request?

    dispatched_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
) PARTITION BY RANGE (dispatched_at);

-- Monthly partitions (created by migration at deploy time; add new partitions monthly)
CREATE TABLE IF NOT EXISTS institutional.provider_dispatch_events_2026_07
    PARTITION OF institutional.provider_dispatch_events
    FOR VALUES FROM ('2026-07-01') TO ('2026-08-01');

CREATE TABLE IF NOT EXISTS institutional.provider_dispatch_events_2026_08
    PARTITION OF institutional.provider_dispatch_events
    FOR VALUES FROM ('2026-08-01') TO ('2026-09-01');

-- Performance indexes (PSE reads these hot)
CREATE INDEX IF NOT EXISTS idx_pde_provider_recent
    ON institutional.provider_dispatch_events (provider, dispatched_at DESC)
    WHERE outcome != 'CIRCUIT_OPEN';

CREATE INDEX IF NOT EXISTS idx_pde_agent_skill_recent
    ON institutional.provider_dispatch_events (agent_type, skill_id, dispatched_at DESC);

CREATE INDEX IF NOT EXISTS idx_pde_language_provider
    ON institutional.provider_dispatch_events (message_language, provider, tier_requested)
    WHERE dispatched_at > NOW() - INTERVAL '7 days';

COMMENT ON TABLE institutional.provider_dispatch_events IS
    'Raw LLM dispatch events. One row per call. Partitioned monthly. '
    'PSE reads rolling 1h/10min aggregates. Self-Improvement Analyst reads weekly. '
    'ADR-029: source of truth for conscious provider selection.';

-- ─── Materialized View: PSE Real-Time Aggregate (1h rolling window) ──────────
-- PSE reads this view (not the raw table) for sub-millisecond provider ranking.
-- Refreshed every 5 minutes by a Temporal scheduled activity.

CREATE MATERIALIZED VIEW IF NOT EXISTS institutional.pse_provider_ranking AS
SELECT
    provider,
    tier_requested,
    message_language,
    COUNT(*)                                           AS total_calls,
    ROUND(AVG(latency_ms))::INTEGER                    AS avg_latency_ms,
    PERCENTILE_CONT(0.99) WITHIN GROUP
        (ORDER BY latency_ms)::INTEGER                 AS p99_latency_ms,
    ROUND(
        SUM(CASE WHEN outcome = 'SUCCESS' THEN 1 ELSE 0 END)::NUMERIC
        / NULLIF(COUNT(*), 0) * 100, 2
    )                                                  AS success_rate_pct,
    ROUND(AVG(cost_inr), 5)                            AS avg_cost_inr,
    SUM(CASE WHEN c049_escalated THEN 1 ELSE 0 END)   AS c049_escalations,
    SUM(CASE WHEN outcome = 'RATE_LIMITED' THEN 1 ELSE 0 END) AS rate_limit_events,
    MAX(dispatched_at)                                 AS last_call_at,
    -- PSE composite score (ADR-029 Decision 2)
    -- Refreshed during materialized view refresh
    ROUND(
        (SUM(CASE WHEN outcome = 'SUCCESS' THEN 1.0 ELSE 0 END) / NULLIF(COUNT(*), 0)) * 0.50
        + (1.0 - LEAST(PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY latency_ms) / 5000.0, 1.0)) * 0.25
        + (1.0 - LEAST(AVG(cost_inr) / 1.0, 1.0)) * 0.15
        + (1.0 - SUM(CASE WHEN c049_escalated THEN 1.0 ELSE 0 END) / NULLIF(COUNT(*), 0)) * 0.10
    , 4) AS composite_score
FROM institutional.provider_dispatch_events
WHERE dispatched_at > NOW() - INTERVAL '1 hour'
GROUP BY provider, tier_requested, message_language
WITH DATA;

CREATE UNIQUE INDEX IF NOT EXISTS idx_pse_ranking_pk
    ON institutional.pse_provider_ranking (provider, tier_requested, message_language);

COMMENT ON MATERIALIZED VIEW institutional.pse_provider_ranking IS
    'PSE reads this for real-time provider ranking. Refreshed every 5 min by Temporal. '
    'composite_score drives provider selection in Layer B of ADR-029 PSE.';

-- ─── Provider Circuit Breaker State ──────────────────────────────────────────

CREATE TABLE IF NOT EXISTS institutional.provider_circuit_breaker (
    provider                llm_provider PRIMARY KEY,
    state                   VARCHAR(10) NOT NULL DEFAULT 'CLOSED'
                            CHECK (state IN ('CLOSED', 'OPEN', 'HALF_OPEN')),
    opened_at               TIMESTAMPTZ,
    opens_for_seconds       INTEGER DEFAULT 120,        -- PSE-R07: 120s circuit-open window
    failure_count           INTEGER NOT NULL DEFAULT 0,
    last_failure_at         TIMESTAMPTZ,
    last_success_at         TIMESTAMPTZ,
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Seed initial state (all circuits CLOSED)
INSERT INTO institutional.provider_circuit_breaker (provider, state) VALUES
    ('ollama_llama3', 'CLOSED'),
    ('ollama_ai4bharat', 'CLOSED'),
    ('google_gemini_flash', 'CLOSED'),
    ('sarvam_saaras', 'CLOSED'),
    ('azure_gpt4o_mini', 'CLOSED'),
    ('google_gemini_pro', 'CLOSED'),
    ('azure_gpt4o', 'CLOSED')
ON CONFLICT (provider) DO NOTHING;

COMMENT ON TABLE institutional.provider_circuit_breaker IS
    'PSE-R07: circuit breaker state per provider. PSE checks this before dispatch. '
    'AI Runtime updates this table after rate-limit or error outcomes.';
