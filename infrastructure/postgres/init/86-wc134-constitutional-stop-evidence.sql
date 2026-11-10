-- WC-134: persist tenant-scoped CE Stop evidence alongside the shared dispatch fence.
BEGIN;
DO $membership$
BEGIN
    IF NOT pg_has_role(session_user, 'ce_owner', 'SET') THEN
        EXECUTE format('GRANT ce_owner TO %I', session_user);
        PERFORM set_config('waooaw.wc134_stop_evidence_granted', 'true', true);
    END IF;
END
$membership$;
CREATE TABLE IF NOT EXISTS constitutional.emergency_stop_events (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    contract_id UUID NOT NULL,
    initiated_by_user_id TEXT NOT NULL,
    affected_session_ids TEXT[] NOT NULL,
    triggered_at TIMESTAMPTZ NOT NULL,
    temporal_signalled_at TIMESTAMPTZ,
    stop_source TEXT NOT NULL
);
ALTER TABLE constitutional.emergency_stop_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE constitutional.emergency_stop_events FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS emergency_stop_events_tenant ON constitutional.emergency_stop_events;
CREATE POLICY emergency_stop_events_tenant ON constitutional.emergency_stop_events
    USING (tenant_id = nullif(current_setting('app.current_tenant_id', true), '')::uuid)
    WITH CHECK (tenant_id = nullif(current_setting('app.current_tenant_id', true), '')::uuid);
GRANT SELECT, INSERT ON constitutional.emergency_stop_events TO constitutional_app;
GRANT UPDATE (temporal_signalled_at) ON constitutional.emergency_stop_events TO constitutional_app;
CREATE INDEX IF NOT EXISTS emergency_stop_events_scope
    ON constitutional.emergency_stop_events (tenant_id, contract_id, triggered_at);
ALTER TABLE constitutional.emergency_stop_events OWNER TO ce_owner;
DO $membership$
BEGIN
    IF current_setting('waooaw.wc134_stop_evidence_granted', true) = 'true' THEN
        EXECUTE format('REVOKE ce_owner FROM %I', session_user);
    END IF;
END
$membership$;
COMMIT;
