-- 06-performance-indexes.sql
-- Cloud Architecture Optimization O-01: Replace IVFFlat with HNSW for all pgvector indexes.
-- Constitutional basis: ADR-027 (Cloud Architecture Optimization)
-- Implements: architecture/reference/components/data-architecture.md §pgvector indexes
-- Constitutional basis: C-059 (Implementation Traceability)
--
-- Why HNSW over IVFFlat:
--   IVFFlat requires training data (minimum 4× lists count to be effective).
--   At MVI with < 1,000 embeddings, IVFFlat with lists=100 degrades to full-scan quality
--   but with higher overhead. HNSW works at ALL data sizes without training.
--   HNSW parameters: m=16 (graph connections), ef_construction=64 (build quality).
--   Query performance: ef_search=40 (can be tuned per query; higher = more accurate, slower).
--
-- IMPORTANT: These indexes replace the IVFFlat indexes in 03-enums-and-tables.sql.
-- This file runs AFTER 03-enums-and-tables.sql in the init sequence.

SET search_path TO constitutional, business, professional, institutional, public;

-- ─── Drop existing IVFFlat indexes ───────────────────────────────────────────
-- IVFFlat indexes created in 03-enums-and-tables.sql are replaced below.

DROP INDEX IF EXISTS professional.idx_creative_embeddings_cosine;
DROP INDEX IF EXISTS institutional.idx_domain_knowledge_embedding;
DROP INDEX IF EXISTS institutional.idx_platform_intelligence_embedding;  -- if exists
DROP INDEX IF EXISTS business.idx_fingerprint_voice;
DROP INDEX IF EXISTS business.idx_fingerprint_competitor;
DROP INDEX IF EXISTS business.idx_skill_graph_embedding;
DROP INDEX IF EXISTS constitutional.idx_state_value_embedding;           -- if exists

-- ─── HNSW indexes — professional schema ──────────────────────────────────────

-- Creative Standard Embeddings (DMA Skill 8 — Digital Twin fingerprinting)
CREATE INDEX idx_creative_embeddings_hnsw
    ON professional.creative_standard_embeddings
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- ─── HNSW indexes — institutional schema ─────────────────────────────────────

-- Domain Knowledge (Tier 1 RAG — agent knowledge base)
CREATE INDEX idx_domain_knowledge_hnsw
    ON institutional.domain_knowledge
    USING hnsw (content_embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- Platform Intelligence (Tier 3 RAG — aggregate cross-customer patterns)
-- NOTE: Tier 3 is read-heavy and large → HNSW is critical here
CREATE INDEX idx_platform_intelligence_hnsw
    ON institutional.platform_intelligence_patterns
    USING hnsw (pattern_embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64)
    WHERE pattern_embedding IS NOT NULL;

-- ─── HNSW indexes — business schema ──────────────────────────────────────────

-- Customer Creative Fingerprints (DMA uniqueness enforcement — C-052)
-- These are queried on every content generation to enforce brand uniqueness
CREATE INDEX idx_fingerprint_voice_hnsw
    ON business.customer_creative_fingerprints
    USING hnsw (voice_embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64)
    WHERE voice_embedding IS NOT NULL;

CREATE INDEX idx_fingerprint_competitor_hnsw
    ON business.customer_creative_fingerprints
    USING hnsw (competitor_exclusion_embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64)
    WHERE competitor_exclusion_embedding IS NOT NULL;

-- Agent Skill Graph (SIR intent routing — C-054)
-- Queried on every agent request to route to the right skill
CREATE INDEX idx_skill_graph_hnsw
    ON business.agent_skill_graph
    USING hnsw (intent_signatures_embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64)
    WHERE intent_signatures_embedding IS NOT NULL;

-- ─── Query hint for HNSW ef_search (tune at query time) ──────────────────────
-- Set in AI Runtime before RAG similarity queries:
--   SET LOCAL hnsw.ef_search = 40;  -- default; increase for higher accuracy
--   SET LOCAL hnsw.ef_search = 80;  -- for FRONTIER model RAG (worth the extra latency)
--   SET LOCAL hnsw.ef_search = 20;  -- for LOCAL model RAG (speed over precision)

-- ─── Standard B-tree performance indexes ─────────────────────────────────────
-- Additional indexes for common query patterns identified in architecture review.

-- Audit Ledger: most common query pattern = by organisation + time range
CREATE INDEX IF NOT EXISTS idx_evidence_org_time
    ON constitutional.evidence_records (organisation_id, created_at DESC);

-- PAAS sessions: active session lookup (trading agent — latency critical)
CREATE INDEX IF NOT EXISTS idx_paas_active
    ON business.paas_sessions (organisation_id, state)
    WHERE state = 'ACTIVE';

-- Signal materiality events: SIL polling query
CREATE INDEX IF NOT EXISTS idx_signal_events_org_time
    ON business.signal_materiality_events (organisation_id, detected_at DESC)
    WHERE processed = FALSE;

-- Campaign content items: SCR gate query
CREATE INDEX IF NOT EXISTS idx_content_scr_pending
    ON business.campaign_content_items (organisation_id, scr_status)
    WHERE scr_status = 'PENDING';

-- Customer NPS scores: monthly report query
CREATE INDEX IF NOT EXISTS idx_nps_org_date
    ON business.customer_nps_scores (organisation_id, scored_at DESC);
-- Validated: WC-011 Sprint 011 (infrastructure check only)
