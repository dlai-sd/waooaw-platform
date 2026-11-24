-- Implements: work-contracts/WC-168-operator-console-works-on-demo.md WC168-R003, WC168-R004, WC168-R005
-- Constitutional basis: C-009, C-023, C-063, C-065
-- WC-168: the Founder Providers screen failed on Demo with "42501 permission denied for table provider_configs".
-- A Founder-authorized read-only catalog query of 2026-11-24 (scripts/wc168_demo_db_catalog_read.sh) proved two causes:
--   1. provider_configs gave no privilege to business_app (its access list held only bp_owner and bp_verifier), while its
--      sibling provider tables were granted explicitly.
--   2. The principal handoff enables and forces row level security on every table with a tenant column, and
--      provider_configs has no policy, so even with the grant the application would see no rows.
-- This file grants exactly what the code does and adds the matching policies. The application reads platform rows
-- (tenant_id IS NULL) and its own tenant's rows, inserts platform rows through the Founder provider screen, and updates only
-- the active credential version of a platform row. It never deletes. Every statement is idempotent.
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '30s';
SET LOCAL ROLE bp_owner;

GRANT SELECT, INSERT ON business.provider_configs TO business_app;
GRANT UPDATE (active_credential_version_id) ON business.provider_configs TO business_app;

DROP POLICY IF EXISTS provider_configs_read ON business.provider_configs;
CREATE POLICY provider_configs_read ON business.provider_configs FOR SELECT TO business_app
    USING (tenant_id IS NULL OR tenant_id = NULLIF(current_setting('app.current_tenant_id', TRUE), '')::UUID);

DROP POLICY IF EXISTS provider_configs_platform_insert ON business.provider_configs;
CREATE POLICY provider_configs_platform_insert ON business.provider_configs FOR INSERT TO business_app
    WITH CHECK (tenant_id IS NULL);

DROP POLICY IF EXISTS provider_configs_platform_update ON business.provider_configs;
CREATE POLICY provider_configs_platform_update ON business.provider_configs FOR UPDATE TO business_app
    USING (tenant_id IS NULL) WITH CHECK (tenant_id IS NULL);

DROP POLICY IF EXISTS provider_configs_owner ON business.provider_configs;
CREATE POLICY provider_configs_owner ON business.provider_configs TO bp_owner
    USING (true) WITH CHECK (true);

COMMIT;
