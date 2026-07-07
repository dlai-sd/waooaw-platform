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
