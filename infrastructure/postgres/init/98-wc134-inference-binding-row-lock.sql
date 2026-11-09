-- Implements: WC-134 governed generation source validation.
-- constitutional_basis: C-023, C-026, C-059
BEGIN;

DO $membership$
BEGIN
    IF NOT pg_has_role(session_user, 'bp_owner', 'SET') THEN
        EXECUTE format('GRANT bp_owner TO %I', session_user);
        PERFORM set_config('waooaw.wc134_inference_lock_granted', 'true', true);
    END IF;
END
$membership$;
GRANT CREATE ON SCHEMA business TO bp_owner;

CREATE OR REPLACE FUNCTION business.lock_conversation_inference_bindings(
    p_tenant UUID, p_relationship UUID
) RETURNS SETOF business.CONVERSATION_INFERENCE_BINDINGS
LANGUAGE plpgsql SECURITY DEFINER
SET search_path = pg_catalog SET row_security = on
AS $function$
BEGIN
    IF p_tenant IS NULL OR p_relationship IS NULL
        OR p_tenant IS DISTINCT FROM
            NULLIF(current_setting('app.current_tenant_id', TRUE), '')::UUID
    THEN
        RAISE EXCEPTION 'inference binding tenant authority required' USING ERRCODE = '42501';
    END IF;
    RETURN QUERY
    SELECT binding.*
    FROM business.conversation_inference_bindings AS binding
    WHERE binding.tenant_id = p_tenant
        AND binding.relationship_id = p_relationship
        AND binding.active
    ORDER BY binding.binding_id
    FOR SHARE;
END;
$function$;
ALTER FUNCTION business.lock_conversation_inference_bindings(UUID, UUID) OWNER TO bp_owner;
REVOKE ALL ON FUNCTION business.lock_conversation_inference_bindings(UUID, UUID) FROM public;
GRANT EXECUTE ON FUNCTION business.lock_conversation_inference_bindings(UUID, UUID) TO business_app;

DO $membership$
BEGIN
    IF current_setting('waooaw.wc134_inference_lock_granted', TRUE) = 'true' THEN
        EXECUTE format('REVOKE bp_owner FROM %I', session_user);
    END IF;
END
$membership$;
COMMIT;
