-- Implements: work-contracts/WC-174-agent-operation-modes-calendar-and-dma-journey.md WC174-R005, R030, R032, R036
-- Constitutional basis: C-005, C-023, C-026, C-059, C-063
-- WC-174: agent-neutral records of Agent Operation (calendar events, plan nodes, content, goals, platform answers),
-- each kept as versions that are never deleted, one state row per relationship, the Founder's shared settings and
-- content-free counters. No table, column or policy here names an agent.
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '30s';
SET LOCAL ROLE bp_owner;

CREATE TABLE IF NOT EXISTS business.agent_operation_items (
    tenant_id UUID NOT NULL,
    relationship_id UUID NOT NULL,
    item_id UUID NOT NULL,
    kind TEXT NOT NULL CHECK (kind IN (
        'EVENT', 'PLACEHOLDER', 'PLAN_NODE', 'CONTENT', 'SLOT', 'NOTE', 'GOAL',
        'PROFILE_LABEL', 'PRESENCE', 'FINDING', 'DIGEST')),
    version_no INTEGER NOT NULL CHECK (version_no >= 1),
    doc JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (tenant_id, relationship_id, item_id)
);
ALTER TABLE business.agent_operation_items OWNER TO bp_owner;
CREATE INDEX IF NOT EXISTS agent_operation_items_relationship_idx
    ON business.agent_operation_items (tenant_id, relationship_id, kind);

CREATE TABLE IF NOT EXISTS business.agent_operation_item_versions (
    tenant_id UUID NOT NULL,
    relationship_id UUID NOT NULL,
    item_id UUID NOT NULL,
    version_no INTEGER NOT NULL CHECK (version_no >= 1),
    doc JSONB NOT NULL,
    recorded_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (tenant_id, item_id, version_no)
);
ALTER TABLE business.agent_operation_item_versions OWNER TO bp_owner;

CREATE OR REPLACE FUNCTION business.guard_agent_operation_item_versions()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $guard$
BEGIN
    RAISE EXCEPTION 'agent operation item versions are append-only';
END
$guard$;

CREATE OR REPLACE TRIGGER agent_operation_item_versions_guard
BEFORE UPDATE OR DELETE ON business.agent_operation_item_versions
FOR EACH ROW EXECUTE FUNCTION business.guard_agent_operation_item_versions();

CREATE TABLE IF NOT EXISTS business.agent_operation_state (
    tenant_id UUID NOT NULL,
    relationship_id UUID NOT NULL,
    doc JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (tenant_id, relationship_id)
);
ALTER TABLE business.agent_operation_state OWNER TO bp_owner;

-- Founder-set values shared by every relationship (chat allowance, connector switches). No tenant data.
CREATE TABLE IF NOT EXISTS business.agent_operation_settings (
    setting_key TEXT PRIMARY KEY CHECK (length(setting_key) BETWEEN 1 AND 64),
    doc JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    updated_by TEXT NOT NULL CHECK (length(updated_by) BETWEEN 1 AND 128)
);
ALTER TABLE business.agent_operation_settings OWNER TO bp_owner;

-- How outcomes were reached and what needs attention, as counts only: a hashed relationship reference, no content.
CREATE TABLE IF NOT EXISTS business.agent_operation_counters (
    day DATE NOT NULL,
    relationship_ref TEXT NOT NULL CHECK (length(relationship_ref) BETWEEN 8 AND 64),
    metric TEXT NOT NULL CHECK (metric IN (
        'ROUTE_ASKED', 'ROUTE_ACCEPTED', 'ROUTE_TOOL', 'PUBLISHED', 'PUBLISH_FAILED', 'CONNECTION_REPAIR')),
    total INTEGER NOT NULL CHECK (total >= 0),
    PRIMARY KEY (day, relationship_ref, metric)
);
ALTER TABLE business.agent_operation_counters OWNER TO bp_owner;

ALTER TABLE business.agent_operation_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE business.agent_operation_items FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS agent_operation_items_tenant_isolation ON business.agent_operation_items;
CREATE POLICY agent_operation_items_tenant_isolation ON business.agent_operation_items
    USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', TRUE), '')::UUID)
    WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', TRUE), '')::UUID);

ALTER TABLE business.agent_operation_item_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE business.agent_operation_item_versions FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS agent_operation_item_versions_tenant_isolation ON business.agent_operation_item_versions;
CREATE POLICY agent_operation_item_versions_tenant_isolation ON business.agent_operation_item_versions
    USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', TRUE), '')::UUID)
    WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', TRUE), '')::UUID);

ALTER TABLE business.agent_operation_state ENABLE ROW LEVEL SECURITY;
ALTER TABLE business.agent_operation_state FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS agent_operation_state_tenant_isolation ON business.agent_operation_state;
CREATE POLICY agent_operation_state_tenant_isolation ON business.agent_operation_state
    USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', TRUE), '')::UUID)
    WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', TRUE), '')::UUID);

REVOKE ALL ON business.agent_operation_items FROM PUBLIC, business_app;
GRANT SELECT, INSERT, UPDATE ON business.agent_operation_items TO business_app;
REVOKE ALL ON business.agent_operation_item_versions FROM PUBLIC, business_app;
GRANT SELECT, INSERT ON business.agent_operation_item_versions TO business_app;
REVOKE ALL ON business.agent_operation_state FROM PUBLIC, business_app;
GRANT SELECT, INSERT, UPDATE ON business.agent_operation_state TO business_app;
REVOKE ALL ON business.agent_operation_settings FROM PUBLIC, business_app;
GRANT SELECT, INSERT, UPDATE ON business.agent_operation_settings TO business_app;
REVOKE ALL ON business.agent_operation_counters FROM PUBLIC, business_app;
GRANT SELECT, INSERT, UPDATE ON business.agent_operation_counters TO business_app;

COMMIT;
