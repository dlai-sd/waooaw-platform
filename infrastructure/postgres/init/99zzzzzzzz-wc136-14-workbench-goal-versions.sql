-- Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C6-02
-- Constitutional basis: C-005, C-023, C-026, C-059, C-063
-- WC-136: every goal version the workbench writes is kept, append-only, so the goal's version list shows what each
-- earlier version held, who revised it and why. A goal revised before this table existed shows its first recorded
-- version from the revision that followed.
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '30s';
SET LOCAL ROLE bp_owner;

CREATE TABLE IF NOT EXISTS business.workbench_goal_versions (
    tenant_id UUID NOT NULL,
    relationship_id UUID NOT NULL,
    goal_id UUID NOT NULL,
    version_no INTEGER NOT NULL CHECK (version_no >= 1),
    revised_at TIMESTAMPTZ NOT NULL,
    revised_by TEXT NOT NULL CHECK (length(revised_by) BETWEEN 1 AND 64),
    reason TEXT CHECK (reason IS NULL OR length(reason) BETWEEN 1 AND 500),
    title TEXT NOT NULL CHECK (length(title) BETWEEN 1 AND 240),
    parameters JSONB NOT NULL,
    PRIMARY KEY (tenant_id, goal_id, version_no)
);
ALTER TABLE business.workbench_goal_versions OWNER TO bp_owner;
CREATE INDEX IF NOT EXISTS workbench_goal_versions_relationship_idx
    ON business.workbench_goal_versions (tenant_id, relationship_id);

CREATE OR REPLACE FUNCTION business.guard_workbench_goal_versions()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $guard$
BEGIN
    RAISE EXCEPTION 'workbench goal versions are append-only';
END
$guard$;

CREATE OR REPLACE TRIGGER workbench_goal_versions_guard
BEFORE UPDATE OR DELETE ON business.workbench_goal_versions
FOR EACH ROW EXECUTE FUNCTION business.guard_workbench_goal_versions();

ALTER TABLE business.workbench_goal_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE business.workbench_goal_versions FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS workbench_goal_versions_tenant_isolation ON business.workbench_goal_versions;
CREATE POLICY workbench_goal_versions_tenant_isolation ON business.workbench_goal_versions
    USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', TRUE), '')::UUID)
    WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', TRUE), '')::UUID);

REVOKE ALL ON business.workbench_goal_versions FROM PUBLIC, business_app;
GRANT SELECT, INSERT ON business.workbench_goal_versions TO business_app;

COMMIT;
