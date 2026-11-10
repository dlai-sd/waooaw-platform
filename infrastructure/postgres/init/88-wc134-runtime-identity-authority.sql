-- WC-134 R006/R008: current Identity admission and commit fencing for original SEND actors.
BEGIN;
DO $membership$
BEGIN
    IF NOT pg_has_role(session_user, 'identity_resolver_owner', 'SET') THEN
        EXECUTE format('GRANT identity_resolver_owner TO %I', session_user);
        PERFORM set_config('waooaw.wc134_runtime_identity_granted', 'true', true);
    END IF;
END
$membership$;
GRANT CREATE ON SCHEMA identity TO identity_resolver_owner;
GRANT USAGE ON SCHEMA identity TO bp_owner, business_app;
GRANT UPDATE (status) ON identity.actor_bindings, identity.login_methods,
    identity.accounts, identity.memberships TO identity_resolver_owner;
GRANT UPDATE (identity_status) ON business.organisations TO identity_resolver_owner;

CREATE OR REPLACE FUNCTION identity.lock_conversation_runtime_membership(
    p_issuer TEXT, p_actor UUID, p_tenant UUID, p_membership UUID DEFAULT NULL
)
RETURNS TABLE (account_id UUID, membership_id UUID, roles TEXT[])
LANGUAGE plpgsql SECURITY DEFINER
SET search_path = pg_catalog
SET row_security = on
AS $function$
DECLARE
    old_issuer TEXT := current_setting('app.identity_issuer', true);
    old_subject TEXT := current_setting('app.identity_subject', true);
    selected RECORD;
BEGIN
    IF p_issuer IS NULL OR length(p_issuer) NOT BETWEEN 1 AND 2048
        OR p_actor IS NULL OR p_tenant IS NULL THEN
        RAISE EXCEPTION 'Runtime Identity context is invalid' USING ERRCODE = '42501';
    END IF;
    PERFORM set_config('app.identity_issuer', p_issuer, true);
    PERFORM set_config('app.identity_subject', p_actor::text, true);
    SELECT account.account_id, membership.membership_id, membership.roles INTO selected
    FROM identity.actor_bindings AS actor
    JOIN identity.login_methods AS login
        ON login.login_method_id = actor.login_method_id AND login.account_id = actor.account_id
    JOIN identity.accounts AS account ON account.account_id = actor.account_id
    JOIN identity.memberships AS membership ON membership.account_id = account.account_id
    JOIN business.organisations AS organisation ON organisation.tenant_id = membership.tenant_id
    WHERE actor.actor_issuer = p_issuer COLLATE "C" AND actor.actor_subject = p_actor::text COLLATE "C"
        AND actor.status = 'ACTIVE' AND login.status = 'ACTIVE' AND account.status = 'ACTIVE'
        AND membership.status = 'ACTIVE' AND membership.tenant_id = p_tenant
        AND (p_membership IS NULL OR membership.membership_id = p_membership)
        AND membership.roles IN (ARRAY['OWNER']::text[], ARRAY['MANAGER']::text[])
        AND organisation.identity_managed AND organisation.identity_status = 'ACTIVE'
    FOR SHARE OF actor, login, account, membership, organisation;
    PERFORM set_config('app.identity_issuer', coalesce(old_issuer, ''), true);
    PERFORM set_config('app.identity_subject', coalesce(old_subject, ''), true);
    IF selected IS NOT NULL THEN
        RETURN QUERY SELECT selected.account_id, selected.membership_id, selected.roles;
    END IF;
EXCEPTION WHEN OTHERS THEN
    PERFORM set_config('app.identity_issuer', coalesce(old_issuer, ''), true);
    PERFORM set_config('app.identity_subject', coalesce(old_subject, ''), true);
    RAISE;
END
$function$;
ALTER FUNCTION identity.lock_conversation_runtime_membership(TEXT, UUID, UUID, UUID)
    OWNER TO identity_resolver_owner;
REVOKE ALL ON FUNCTION identity.lock_conversation_runtime_membership(TEXT, UUID, UUID, UUID) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION identity.lock_conversation_runtime_membership(TEXT, UUID, UUID, UUID)
    TO business_app, bp_owner;
REVOKE CREATE ON SCHEMA identity FROM identity_resolver_owner;

ALTER TABLE business.conversation_executions
    ADD COLUMN IF NOT EXISTS runtime_actor_issuer TEXT,
    ADD COLUMN IF NOT EXISTS runtime_membership_id UUID,
    ADD COLUMN IF NOT EXISTS runtime_account_id UUID,
    ADD COLUMN IF NOT EXISTS runtime_actor_id UUID;
DO $constraint$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint
        WHERE conrelid = 'business.conversation_executions'::regclass
            AND conname = 'conversation_runtime_identity_complete') THEN
        ALTER TABLE business.conversation_executions
            ADD CONSTRAINT conversation_runtime_identity_complete CHECK (
                (runtime_actor_issuer IS NULL AND runtime_membership_id IS NULL
                    AND runtime_account_id IS NULL AND runtime_actor_id IS NULL)
                OR (runtime_actor_issuer IS NOT NULL AND length(runtime_actor_issuer) BETWEEN 1 AND 2048
                    AND runtime_membership_id IS NOT NULL AND runtime_account_id IS NOT NULL
                    AND runtime_actor_id IS NOT NULL));
    END IF;
END
$constraint$;
DO $membership$
BEGIN
    IF current_setting('waooaw.wc134_runtime_identity_granted', true) = 'true' THEN
        EXECUTE format('REVOKE identity_resolver_owner FROM %I', session_user);
    END IF;
END
$membership$;
COMMIT;
