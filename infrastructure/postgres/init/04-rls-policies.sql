-- 04-rls-policies.sql
-- Row-Level Security policies for all tenant-scoped tables.
-- Constitutional basis: C-005 (Three-Ledger isolation), C-026 (DB-level enforcement),
--                       AD-004 (multi-tenant isolation — HARD constraint)
-- Session variable app.tenant_id is set by each service's JWT middleware.

-- ─── Enable RLS on all tenant-scoped tables ──────────────────────────────────

ALTER TABLE constitutional.evidence_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE constitutional.authority_licenses ENABLE ROW LEVEL SECURITY;
ALTER TABLE business.employment_contracts ENABLE ROW LEVEL SECURITY;
ALTER TABLE business.decision_spaces ENABLE ROW LEVEL SECURITY;
ALTER TABLE business.approval_requests ENABLE ROW LEVEL SECURITY;
ALTER TABLE business.paas_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE business.organisations ENABLE ROW LEVEL SECURITY;

-- Professional templates are NOT tenant-scoped — they are a public catalogue.
-- No RLS on professional_templates: all authenticated tenants can read published templates.
-- Write access is restricted by DB permissions (only WAOOAW's business_app can insert).

-- ─── RLS Policies ────────────────────────────────────────────────────────────
-- Policy: tenant_id must match the session variable set by the JWT middleware.
-- The session variable is set via: SET LOCAL app.tenant_id = '{tenant_id_from_jwt}'
-- at the start of every DB connection, before any query executes.

-- Constitutional schema
CREATE POLICY tenant_isolation ON constitutional.evidence_records
    USING (tenant_id = current_setting('app.tenant_id', TRUE)::UUID);

CREATE POLICY tenant_isolation ON constitutional.authority_licenses
    USING (tenant_id = current_setting('app.tenant_id', TRUE)::UUID);

-- Business schema
CREATE POLICY tenant_isolation ON business.organisations
    USING (tenant_id = current_setting('app.tenant_id', TRUE)::UUID);

CREATE POLICY tenant_isolation ON business.employment_contracts
    USING (tenant_id = current_setting('app.tenant_id', TRUE)::UUID);

CREATE POLICY tenant_isolation ON business.decision_spaces
    USING (tenant_id = current_setting('app.tenant_id', TRUE)::UUID);

CREATE POLICY tenant_isolation ON business.approval_requests
    USING (tenant_id = current_setting('app.tenant_id', TRUE)::UUID);

CREATE POLICY tenant_isolation ON business.paas_sessions
    USING (tenant_id = current_setting('app.tenant_id', TRUE)::UUID);

-- ─── Notes for the Runtime Professional ──────────────────────────────────────
-- 1. The RLS policies use current_setting('app.tenant_id', TRUE).
--    The TRUE parameter means: return NULL if the setting is not set (not an error).
--    This prevents a crash on DB connections where SET LOCAL has not been called.
--    However, a NULL tenant_id means 0 rows returned — the RLS is still safe.
--
-- 2. EF Core sets the tenant_id via an interceptor on DbContext.
--    See security-architecture.md "JWT Validation" section for the pattern.
--
-- 3. professional.identities and professional.experience_records have NO RLS.
--    They are not tenant-scoped — professional-owned, portable. C-005.
--
-- 4. professional.creative_standard_embeddings DOES have tenant_id (which customer's
--    Creative Standard this represents). Apply RLS here too.

ALTER TABLE professional.creative_standard_embeddings ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON professional.creative_standard_embeddings
    USING (tenant_id = current_setting('app.tenant_id', TRUE)::UUID);

-- ─── DMA v2.0 + Synthetic Approval tables (v0.18.0) ─────────────────────────
-- All new tenant-scoped tables require RLS before any query can execute (AD-004).
-- organisation_id is the tenant discriminator for DMA tables (not tenant_id).
-- The session variable app.tenant_id maps to organisations.id via the JWT middleware.

ALTER TABLE business.digital_marketing_profiles      ENABLE ROW LEVEL SECURITY;
ALTER TABLE business.digital_marketing_maturity_scores ENABLE ROW LEVEL SECURITY;
ALTER TABLE business.digital_marketing_needs_heatmap ENABLE ROW LEVEL SECURITY;
ALTER TABLE business.competitor_snapshots            ENABLE ROW LEVEL SECURITY;
ALTER TABLE business.dm_phase_bundle_subscriptions   ENABLE ROW LEVEL SECURITY;
ALTER TABLE business.skill_runtime_configurations    ENABLE ROW LEVEL SECURITY;
ALTER TABLE business.synthetic_approval_records      ENABLE ROW LEVEL SECURITY;
ALTER TABLE business.skill_self_governance_log       ENABLE ROW LEVEL SECURITY;

-- DMA tables use organisation_id as the tenant discriminator.
-- The JWT tenant_id maps to organisations.id.
-- Developer note: ensure app.tenant_id session variable is set before any query.

CREATE POLICY tenant_isolation ON business.digital_marketing_profiles
    USING (organisation_id = current_setting('app.tenant_id', TRUE)::UUID);

CREATE POLICY tenant_isolation ON business.digital_marketing_maturity_scores
    USING (organisation_id = current_setting('app.tenant_id', TRUE)::UUID);

CREATE POLICY tenant_isolation ON business.digital_marketing_needs_heatmap
    USING (organisation_id = current_setting('app.tenant_id', TRUE)::UUID);

CREATE POLICY tenant_isolation ON business.competitor_snapshots
    USING (organisation_id = current_setting('app.tenant_id', TRUE)::UUID);

CREATE POLICY tenant_isolation ON business.dm_phase_bundle_subscriptions
    USING (organisation_id = current_setting('app.tenant_id', TRUE)::UUID);

-- skill_runtime_configurations: tenant via employment_contract_id -> organisation_id join
-- Simpler: use organisation_id direct lookup via the employment_contracts join.
-- Implementation note: BP must enforce tenant isolation in application layer for this table
-- (RLS via JOIN is complex; application-level enforcement is acceptable per AD-004 note).
-- The table does not contain directly personal data — it contains configuration only.
-- Still enable RLS with a function-based policy for defence in depth:
CREATE POLICY tenant_isolation ON business.skill_runtime_configurations
    USING (
        employment_contract_id IN (
            SELECT id FROM business.employment_contracts
            WHERE tenant_id = current_setting('app.tenant_id', TRUE)::UUID
        )
    );

CREATE POLICY tenant_isolation ON business.synthetic_approval_records
    USING (organisation_id = current_setting('app.tenant_id', TRUE)::UUID);

CREATE POLICY tenant_isolation ON business.skill_self_governance_log
    USING (organisation_id = current_setting('app.tenant_id', TRUE)::UUID);

-- Grant DML permissions to the application role (business_app role executes business schema queries)
GRANT SELECT, INSERT, UPDATE ON business.digital_marketing_profiles      TO business_app;
GRANT SELECT, INSERT          ON business.digital_marketing_maturity_scores TO business_app;
GRANT SELECT, INSERT          ON business.digital_marketing_needs_heatmap TO business_app;
GRANT SELECT, INSERT          ON business.competitor_snapshots            TO business_app;
GRANT SELECT, INSERT, UPDATE  ON business.dm_phase_bundle_subscriptions   TO business_app;
GRANT SELECT, INSERT, UPDATE  ON business.skill_runtime_configurations    TO business_app;
GRANT SELECT, INSERT, UPDATE  ON business.synthetic_approval_records      TO business_app;
GRANT SELECT, INSERT          ON business.skill_self_governance_log       TO business_app;

-- ─── P2 tables (v0.19.0) ────────────────────────────────────────────────────
ALTER TABLE business.payment_transactions   ENABLE ROW LEVEL SECURITY;
ALTER TABLE business.gst_invoices           ENABLE ROW LEVEL SECURITY;
ALTER TABLE business.data_retention_records ENABLE ROW LEVEL SECURITY;

-- business_domain_taxonomy is NOT tenant-scoped (platform catalogue — public read)
-- No RLS on business_domain_taxonomy.

CREATE POLICY tenant_isolation ON business.payment_transactions
    USING (organisation_id = current_setting('app.tenant_id', TRUE)::UUID);

CREATE POLICY tenant_isolation ON business.gst_invoices
    USING (organisation_id = current_setting('app.tenant_id', TRUE)::UUID);

CREATE POLICY tenant_isolation ON business.data_retention_records
    USING (organisation_id = current_setting('app.tenant_id', TRUE)::UUID);

GRANT SELECT, INSERT ON business.payment_transactions   TO business_app;
GRANT SELECT, INSERT ON business.gst_invoices           TO business_app;
GRANT SELECT, INSERT, UPDATE ON business.data_retention_records TO business_app;
GRANT SELECT ON business.business_domain_taxonomy       TO business_app;  -- public catalogue read

-- ─── AI Agent Execution Layer tables (v0.20.0) ───────────────────────────────
-- institutional schema tables are WAOOAW-wide (not tenant-scoped).
-- Access is controlled by DB role permissions, not RLS (no tenant_id discriminator).
-- Only platform-internal services (ai-runtime, business-platform) may write.
-- Reads are restricted by service-level DB roles.

-- No RLS on institutional tables — they are platform-wide.
-- Access control via DB role grants only:

GRANT SELECT, INSERT, UPDATE ON institutional.agent_prompt_versions    TO business_app;
GRANT SELECT, INSERT, UPDATE ON institutional.agent_reasoning_traces   TO ai_runtime_app;
GRANT SELECT                 ON institutional.agent_reasoning_traces   TO business_app;
GRANT SELECT, INSERT, UPDATE ON institutional.agent_capability_registry TO ai_runtime_app;
GRANT SELECT                 ON institutional.agent_capability_registry TO business_app;
GRANT SELECT, INSERT, UPDATE ON institutional.agent_messages           TO ai_runtime_app;
GRANT SELECT                 ON institutional.agent_messages           TO business_app;
GRANT SELECT, INSERT, UPDATE ON institutional.platform_operations_events TO business_app;
GRANT SELECT, INSERT, UPDATE ON institutional.agent_health_scores      TO business_app;

-- Developer note: The institutional schema requires two DB roles:
-- business_app: Business Platform service account
-- ai_runtime_app: AI Runtime service account
-- Both must be created in 02-users-and-roles.sql (or equivalent init script)

-- ─── WhatsApp Phone Identity tables (ADR-023) ────────────────────────────────
-- phone_identity_sessions: NOT tenant-scoped (pre-tenant identity) — no RLS
-- Access controlled by DB role grants only (phone-identity-service has its own role)

ALTER TABLE business.whatsapp_trai_optins ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON business.whatsapp_trai_optins
    USING (organisation_id = current_setting('app.tenant_id', TRUE)::UUID);

-- phone_identity_sessions: no RLS (pre-tenant, phone-identity-service-only access)
GRANT SELECT, INSERT, UPDATE ON business.phone_identity_sessions   TO business_app;
GRANT SELECT, INSERT          ON business.whatsapp_trai_optins      TO business_app;

-- agent_strategic_state: tenant-scoped RLS (v0.31.0 — C-050 Strategic Cognition Layer)
ALTER TABLE business.agent_strategic_state ENABLE ROW LEVEL SECURITY;
CREATE POLICY agent_strategic_state_tenant_isolation ON business.agent_strategic_state
    FOR ALL
    TO business_app, ai_runtime_app
    USING (tenant_id = current_setting('app.tenant_id', TRUE)::UUID);
GRANT SELECT, INSERT, UPDATE ON business.agent_strategic_state TO ai_runtime_app;
GRANT SELECT                 ON business.agent_strategic_state TO business_app;

-- Token Economy Layer tables (v0.32.0 — C-051, ADR-024)

-- customer_usage_units: tenant-scoped RLS (customer cannot see other customers' budgets)
ALTER TABLE business.customer_usage_units ENABLE ROW LEVEL SECURITY;
CREATE POLICY customer_usage_units_tenant_isolation ON business.customer_usage_units
    FOR ALL
    TO business_app, ai_runtime_app
    USING (tenant_id = current_setting('app.tenant_id', TRUE)::UUID);
GRANT SELECT, INSERT, UPDATE ON business.customer_usage_units TO ai_runtime_app;
GRANT SELECT                 ON business.customer_usage_units TO business_app;

-- message_classification_log: no RLS (institutional — platform-wide, no customer data)
-- Access controlled by DB role grants only
GRANT SELECT, INSERT ON institutional.message_classification_log TO ai_runtime_app;
GRANT SELECT         ON institutional.message_classification_log TO business_app;

-- prompt_cache_metadata: no RLS (institutional — platform-wide, cache keys never contain customer data)
GRANT SELECT, INSERT, UPDATE ON institutional.prompt_cache_metadata TO ai_runtime_app;
GRANT SELECT                 ON institutional.prompt_cache_metadata TO business_app;

-- Agent Memory Layer tables (v0.34.0 — C-052, AD-025, DP-021)

-- customer_creative_fingerprints: tenant-scoped RLS (Creative Fingerprint is strictly customer-private — C-034)
ALTER TABLE business.customer_creative_fingerprints ENABLE ROW LEVEL SECURITY;
CREATE POLICY creative_fingerprint_tenant_isolation ON business.customer_creative_fingerprints
    FOR ALL
    TO business_app, ai_runtime_app
    USING (tenant_id = current_setting('app.tenant_id', TRUE)::UUID);
GRANT SELECT, INSERT, UPDATE ON business.customer_creative_fingerprints TO ai_runtime_app;
GRANT SELECT                 ON business.customer_creative_fingerprints TO business_app;

-- tier3_eligibility_log: no RLS (institutional — platform-wide audit of Tier 3 data flow)
-- Contains no customer-identifying data — only employment_contract_id and timing
GRANT SELECT, INSERT, UPDATE ON institutional.tier3_eligibility_log TO ai_runtime_app;
GRANT SELECT                 ON institutional.tier3_eligibility_log TO business_app;

-- Developer note: phone-identity-service needs its own DB role with limited permissions:
-- CREATE ROLE phone_identity_app LOGIN;
-- GRANT SELECT, INSERT, UPDATE ON business.phone_identity_sessions TO phone_identity_app;
-- GRANT SELECT, INSERT ON business.whatsapp_trai_optins TO phone_identity_app;
-- GRANT SELECT ON business.farmer_profiles TO phone_identity_app;  -- phone lookup only
-- GRANT SELECT, INSERT ON business.organisations TO phone_identity_app;  -- auto-register

-- Signal Intelligence Layer RLS (v0.35.0 — C-053, C-054)

-- signal_materiality_events: no RLS — institutional, no customer PII; platform-level log
GRANT SELECT, INSERT ON institutional.signal_materiality_events TO ai_runtime_app;
GRANT SELECT         ON institutional.signal_materiality_events TO business_app;

-- skill_gap_signals: tenant-scoped for INSERT (customer org owns gap events); platform-wide SELECT for PO analytics
ALTER TABLE institutional.skill_gap_signals ENABLE ROW LEVEL SECURITY;
CREATE POLICY skill_gap_signals_tenant_isolation ON institutional.skill_gap_signals
    FOR INSERT
    TO ai_runtime_app
    WITH CHECK (organisation_id = current_setting('app.tenant_id', TRUE)::UUID);
GRANT SELECT, INSERT ON institutional.skill_gap_signals TO ai_runtime_app;
GRANT SELECT         ON institutional.skill_gap_signals TO business_app;

-- agent_skill_graph: tenant-scoped RLS (each customer's skill graph is private — C-034)
ALTER TABLE business.agent_skill_graph ENABLE ROW LEVEL SECURITY;
CREATE POLICY agent_skill_graph_tenant_isolation ON business.agent_skill_graph
    FOR ALL TO business_app, ai_runtime_app
    USING (tenant_id = current_setting('app.tenant_id', TRUE)::UUID);
GRANT SELECT, INSERT, UPDATE ON business.agent_skill_graph TO ai_runtime_app;
GRANT SELECT                 ON business.agent_skill_graph TO business_app;

-- Campaign Theme Engine RLS (v0.39.0 — C-055, AD-028)
-- All 4 campaign tables are tenant-scoped — campaign data is strictly customer-private (C-034)

ALTER TABLE business.content_campaigns ENABLE ROW LEVEL SECURITY;
CREATE POLICY content_campaigns_tenant_isolation ON business.content_campaigns
    FOR ALL TO business_app, ai_runtime_app
    USING (tenant_id = current_setting('app.tenant_id', TRUE)::UUID);
GRANT SELECT, INSERT, UPDATE ON business.content_campaigns TO ai_runtime_app;
GRANT SELECT, INSERT         ON business.content_campaigns TO business_app;

ALTER TABLE business.campaign_weekly_themes ENABLE ROW LEVEL SECURITY;
CREATE POLICY campaign_weekly_themes_tenant_isolation ON business.campaign_weekly_themes
    FOR ALL TO business_app, ai_runtime_app
    USING (tenant_id = current_setting('app.tenant_id', TRUE)::UUID);
GRANT SELECT, INSERT, UPDATE ON business.campaign_weekly_themes TO ai_runtime_app;
GRANT SELECT                 ON business.campaign_weekly_themes TO business_app;

ALTER TABLE business.campaign_content_items ENABLE ROW LEVEL SECURITY;
CREATE POLICY campaign_content_items_tenant_isolation ON business.campaign_content_items
    FOR ALL TO business_app, ai_runtime_app
    USING (tenant_id = current_setting('app.tenant_id', TRUE)::UUID);
GRANT SELECT, INSERT, UPDATE ON business.campaign_content_items TO ai_runtime_app;
GRANT SELECT, UPDATE         ON business.campaign_content_items TO business_app;

ALTER TABLE business.scr_review_records ENABLE ROW LEVEL SECURITY;
CREATE POLICY scr_review_records_tenant_isolation ON business.scr_review_records
    FOR ALL TO business_app, ai_runtime_app
    USING (tenant_id = current_setting('app.tenant_id', TRUE)::UUID);
GRANT SELECT, INSERT ON business.scr_review_records TO ai_runtime_app;
GRANT SELECT         ON business.scr_review_records TO business_app;
-- SCR records are constitutional audit artifacts — INSERT only, never UPDATE or DELETE

-- signal_materiality_events: no RLS — institutional, no customer PII; platform-level log
GRANT SELECT, INSERT ON institutional.signal_materiality_events TO ai_runtime_app;
GRANT SELECT         ON institutional.signal_materiality_events TO business_app;

-- skill_gap_signals: tenant-scoped for INSERT (customer org owns gap events); platform-wide SELECT for PO analytics
-- Note: Gap signals reference organisation_id but are aggregated cross-customer for proposal analysis
-- ai_runtime_app inserts per-customer; business_app reads aggregate counts (PO dashboard)
ALTER TABLE institutional.skill_gap_signals ENABLE ROW LEVEL SECURITY;
CREATE POLICY skill_gap_signals_tenant_isolation ON institutional.skill_gap_signals
    FOR INSERT
    TO ai_runtime_app
    WITH CHECK (organisation_id = current_setting('app.tenant_id', TRUE)::UUID);
-- SELECT is unrestricted at DB level for PO analytics (business_app role); application layer enforces count-only aggregation (no raw intents exposed)
GRANT SELECT, INSERT ON institutional.skill_gap_signals TO ai_runtime_app;
GRANT SELECT         ON institutional.skill_gap_signals TO business_app;

-- agent_skill_graph: tenant-scoped RLS (each customer's skill graph is private — C-034)
ALTER TABLE business.agent_skill_graph ENABLE ROW LEVEL SECURITY;
CREATE POLICY agent_skill_graph_tenant_isolation ON business.agent_skill_graph
    FOR ALL
    TO business_app, ai_runtime_app
    USING (tenant_id = current_setting('app.tenant_id', TRUE)::UUID);
GRANT SELECT, INSERT, UPDATE ON business.agent_skill_graph TO ai_runtime_app;
GRANT SELECT                 ON business.agent_skill_graph TO business_app;
=======
-- Campaign Theme Engine RLS (v0.39.0 — C-055, AD-028)
-- All 4 campaign tables are tenant-scoped — campaign data is strictly customer-private (C-034)

ALTER TABLE business.content_campaigns ENABLE ROW LEVEL SECURITY;
CREATE POLICY content_campaigns_tenant_isolation ON business.content_campaigns
    FOR ALL TO business_app, ai_runtime_app
    USING (tenant_id = current_setting('app.tenant_id', TRUE)::UUID);
GRANT SELECT, INSERT, UPDATE ON business.content_campaigns TO ai_runtime_app;
GRANT SELECT, INSERT         ON business.content_campaigns TO business_app;

ALTER TABLE business.campaign_weekly_themes ENABLE ROW LEVEL SECURITY;
CREATE POLICY campaign_weekly_themes_tenant_isolation ON business.campaign_weekly_themes
    FOR ALL TO business_app, ai_runtime_app
    USING (tenant_id = current_setting('app.tenant_id', TRUE)::UUID);
GRANT SELECT, INSERT, UPDATE ON business.campaign_weekly_themes TO ai_runtime_app;
GRANT SELECT                 ON business.campaign_weekly_themes TO business_app;

ALTER TABLE business.campaign_content_items ENABLE ROW LEVEL SECURITY;
CREATE POLICY campaign_content_items_tenant_isolation ON business.campaign_content_items
    FOR ALL TO business_app, ai_runtime_app
    USING (tenant_id = current_setting('app.tenant_id', TRUE)::UUID);
GRANT SELECT, INSERT, UPDATE ON business.campaign_content_items TO ai_runtime_app;
GRANT SELECT, UPDATE         ON business.campaign_content_items TO business_app;
-- business_app UPDATE: customer approval/rejection actions update scr_status column only

ALTER TABLE business.scr_review_records ENABLE ROW LEVEL SECURITY;
CREATE POLICY scr_review_records_tenant_isolation ON business.scr_review_records
    FOR ALL TO business_app, ai_runtime_app
    USING (tenant_id = current_setting('app.tenant_id', TRUE)::UUID);
GRANT SELECT, INSERT ON business.scr_review_records TO ai_runtime_app;
GRANT SELECT         ON business.scr_review_records TO business_app;
-- Note: SCR records are constitutional audit artifacts — INSERT only after creation, never UPDATE or DELETE
>>>>>>> 699f049 (constitutional(dma): C-055 Campaign Theme Engine + SCR + Platform Intelligence (DMA v2.5, v0.39.0))

-- Simulation gap bridge RLS (v0.40.0)

-- trading_session_records: tenant-scoped (C-034)
ALTER TABLE business.trading_session_records ENABLE ROW LEVEL SECURITY;
CREATE POLICY trading_session_records_tenant_isolation ON business.trading_session_records
    FOR ALL TO business_app, ai_runtime_app
    USING (tenant_id = current_setting('app.tenant_id', TRUE)::UUID);
GRANT SELECT, INSERT, UPDATE ON business.trading_session_records TO ai_runtime_app;
GRANT SELECT                 ON business.trading_session_records TO business_app;

-- signal_bundling_log: institutional — no RLS; no customer PII in bundling decisions
GRANT SELECT, INSERT ON institutional.signal_bundling_log TO ai_runtime_app;
GRANT SELECT         ON institutional.signal_bundling_log TO business_app;
