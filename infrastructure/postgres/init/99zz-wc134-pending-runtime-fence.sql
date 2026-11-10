-- WC-134: pending starts are not runtime-event work.
BEGIN;
DO $membership$
BEGIN
    IF NOT pg_has_role(session_user, 'bp_owner', 'SET') THEN
        EXECUTE format('GRANT bp_owner TO %I', session_user);
        PERFORM set_config('waooaw.wc134_pending_runtime_granted', 'true', true);
    END IF;
END
$membership$;

CREATE OR REPLACE FUNCTION business.runtime_work_has_pending_start(
    p_tenant UUID, p_execution UUID
)
RETURNS BOOLEAN LANGUAGE plpgsql
SET search_path = pg_catalog SET row_security = on
AS $function$
DECLARE previous_tenant TEXT; pending BOOLEAN;
BEGIN
    previous_tenant := current_setting('app.current_tenant_id', true);
    PERFORM set_config('app.current_tenant_id', p_tenant::text, true);
    SELECT EXISTS (
        SELECT 1 FROM business.conversation_pending_starts
        WHERE tenant_id = p_tenant AND execution_id = p_execution
    ) INTO pending;
    PERFORM set_config('app.current_tenant_id', coalesce(previous_tenant, ''), true);
    RETURN pending;
END
$function$;
ALTER FUNCTION business.runtime_work_has_pending_start(UUID, UUID) OWNER TO bp_owner;
REVOKE ALL ON FUNCTION business.runtime_work_has_pending_start(UUID, UUID) FROM public, business_app;

CREATE OR REPLACE FUNCTION business.claim_conversation_runtime_work(p_environment TEXT)
RETURNS TABLE (execution_id UUID, tenant_id UUID, authorized BOOLEAN)
LANGUAGE plpgsql SECURITY DEFINER
SET search_path = pg_catalog SET row_security = on
AS $function$
DECLARE candidate RECORD; membership RECORD;
BEGIN
    IF p_environment IS NULL OR length(p_environment) NOT BETWEEN 1 AND 64 THEN
        RAISE EXCEPTION 'Runtime environment is invalid' USING ERRCODE = '22023';
    END IF;
    SELECT work.* INTO candidate FROM business.conversation_runtime_work AS work
        WHERE work.environment = p_environment AND NOT work.terminal AND work.due_at <= now()
            AND NOT business.runtime_work_has_pending_start(work.tenant_id, work.execution_id)
        ORDER BY work.due_at, work.execution_id
        LIMIT 1 FOR UPDATE SKIP LOCKED;
    IF candidate IS NULL THEN RETURN; END IF;
    SELECT * INTO membership FROM identity.lock_conversation_runtime_membership(
        candidate.actor_issuer, candidate.actor_id, candidate.tenant_id, candidate.membership_id);
    UPDATE business.conversation_runtime_work AS work
        SET due_at = now() + interval '45 seconds'
        WHERE work.execution_id = candidate.execution_id;
    RETURN QUERY SELECT candidate.execution_id, candidate.tenant_id,
        coalesce(membership.account_id = candidate.account_id, false);
END
$function$;
ALTER FUNCTION business.claim_conversation_runtime_work(TEXT) OWNER TO bp_owner;
REVOKE ALL ON FUNCTION business.claim_conversation_runtime_work(TEXT) FROM public;
GRANT EXECUTE ON FUNCTION business.claim_conversation_runtime_work(TEXT) TO business_app;

DO $membership$
BEGIN
    IF current_setting('waooaw.wc134_pending_runtime_granted', true) = 'true' THEN
        EXECUTE format('REVOKE bp_owner FROM %I', session_user);
    END IF;
END
$membership$;
COMMIT;
