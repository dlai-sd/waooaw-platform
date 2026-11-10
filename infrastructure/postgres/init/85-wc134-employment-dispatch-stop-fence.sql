-- WC-134: shared tenant/relationship admission and result fence.
BEGIN;

DO $memberships$
DECLARE principal TEXT;
BEGIN
    FOREACH principal IN ARRAY ARRAY['ce_owner', 'air_owner', 'bp_owner']
    LOOP
        IF NOT pg_has_role(session_user, principal, 'SET') THEN
            EXECUTE format('GRANT %I TO %I', principal, session_user);
            PERFORM set_config('waooaw.wc134_dispatch_granted_' || principal, 'true', true);
        END IF;
    END LOOP;
END
$memberships$;

CREATE TABLE IF NOT EXISTS constitutional.employment_dispatch_stops (
    tenant_id UUID NOT NULL,
    relationship_ref TEXT NOT NULL,
    stopped_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, relationship_ref)
);
ALTER TABLE constitutional.employment_dispatch_stops ENABLE ROW LEVEL SECURITY;
ALTER TABLE constitutional.employment_dispatch_stops FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS employment_dispatch_stops_tenant ON constitutional.employment_dispatch_stops;
CREATE POLICY employment_dispatch_stops_tenant ON constitutional.employment_dispatch_stops
USING (tenant_id = nullif(current_setting('app.current_tenant_id', TRUE), '')::UUID)
WITH CHECK (tenant_id = nullif(current_setting('app.current_tenant_id', TRUE), '')::UUID);
GRANT SELECT ON constitutional.employment_dispatch_stops TO ai_runtime_app, constitutional_app;
GRANT INSERT ON constitutional.employment_dispatch_stops TO constitutional_app, bp_owner;
GRANT USAGE ON SCHEMA constitutional TO ai_runtime_app, bp_owner;
GRANT USAGE ON SCHEMA ai_runtime TO ai_runtime_app, constitutional_app, bp_owner;

CREATE OR REPLACE FUNCTION ai_runtime.employment_dispatch_relationship_key(p_relationship TEXT)
RETURNS TEXT LANGUAGE sql IMMUTABLE SET search_path = pg_catalog AS $$
    SELECT CASE
        WHEN p_relationship ~* '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
        THEN p_relationship::uuid::text ELSE p_relationship END
$$;
REVOKE ALL ON FUNCTION ai_runtime.employment_dispatch_relationship_key(TEXT) FROM public;
GRANT EXECUTE ON FUNCTION ai_runtime.employment_dispatch_relationship_key(TEXT)
TO ai_runtime_app, constitutional_app, bp_owner;

CREATE OR REPLACE FUNCTION ai_runtime.lock_employment_dispatch(p_tenant UUID, p_relationship TEXT)
RETURNS VOID LANGUAGE plpgsql SET search_path = pg_catalog AS $$
BEGIN
    IF p_tenant IS DISTINCT FROM nullif(current_setting('app.current_tenant_id', true), '')::uuid THEN
        RAISE EXCEPTION 'Dispatch tenant context mismatch' USING ERRCODE = '42501';
    END IF;
    PERFORM pg_advisory_xact_lock(hashtextextended(
        'wc134-dispatch:' || p_tenant::text || ':' ||
        ai_runtime.employment_dispatch_relationship_key(p_relationship), 0));
END
$$;
REVOKE ALL ON FUNCTION ai_runtime.lock_employment_dispatch(UUID, TEXT) FROM public;
GRANT EXECUTE ON FUNCTION ai_runtime.lock_employment_dispatch(UUID, TEXT)
TO ai_runtime_app, constitutional_app, bp_owner;

CREATE OR REPLACE FUNCTION business.fence_employment_dispatch_on_stop()
RETURNS TRIGGER LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog AS $$
BEGIN
    PERFORM ai_runtime.lock_employment_dispatch(NEW.tenant_id, NEW.relationship_id::text);
    INSERT INTO constitutional.employment_dispatch_stops (tenant_id, relationship_ref)
    VALUES (NEW.tenant_id, NEW.relationship_id::text) ON CONFLICT DO NOTHING;
    RETURN NEW;
END
$$;
ALTER FUNCTION business.fence_employment_dispatch_on_stop() OWNER TO bp_owner;
REVOKE ALL ON FUNCTION business.fence_employment_dispatch_on_stop() FROM public;
CREATE OR REPLACE TRIGGER employment_dispatch_stop_fence
BEFORE INSERT ON business.relationship_emergency_stop_latches
FOR EACH ROW EXECUTE FUNCTION business.fence_employment_dispatch_on_stop();

-- Existing latched relationships must remain fenced after upgrade.
-- The migration principal needs a transaction-local policy to enumerate forced-RLS scopes.
DO $backfill_policy$
BEGIN
    EXECUTE format(
        'DROP POLICY IF EXISTS wc134_dispatch_stop_backfill ON business.relationship_emergency_stop_latches');
    EXECUTE format(
        'CREATE POLICY wc134_dispatch_stop_backfill ON business.relationship_emergency_stop_latches FOR SELECT TO %I USING (true)',
        session_user);
END
$backfill_policy$;
DO $$
DECLARE scope RECORD;
BEGIN
    FOR scope IN SELECT tenant_id, relationship_id
        FROM business.relationship_emergency_stop_latches
    LOOP
        PERFORM set_config('app.current_tenant_id', scope.tenant_id::text, true);
        INSERT INTO constitutional.employment_dispatch_stops (tenant_id, relationship_ref)
        VALUES (scope.tenant_id, scope.relationship_id::text) ON CONFLICT DO NOTHING;
    END LOOP;
END
$$;
DROP POLICY wc134_dispatch_stop_backfill ON business.relationship_emergency_stop_latches;

ALTER TABLE constitutional.employment_dispatch_stops OWNER TO ce_owner;
ALTER FUNCTION ai_runtime.employment_dispatch_relationship_key(TEXT) OWNER TO air_owner;
ALTER FUNCTION ai_runtime.lock_employment_dispatch(UUID, TEXT) OWNER TO air_owner;

DO $memberships$
DECLARE principal TEXT;
BEGIN
    FOREACH principal IN ARRAY ARRAY['ce_owner', 'air_owner', 'bp_owner']
    LOOP
        IF current_setting('waooaw.wc134_dispatch_granted_' || principal, true) = 'true' THEN
            EXECUTE format('REVOKE %I FROM %I', principal, session_user);
        END IF;
    END LOOP;
END
$memberships$;

COMMIT;
