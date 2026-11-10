-- Implements: WC-134 R002/R005/R006/R008; current Identity authority and phone proof.
-- constitutional_basis: C-023, C-026, C-059

BEGIN;

DROP POLICY IF EXISTS resolver_actor_row_lock ON business.organisations;
-- PostgreSQL row-lock reads need an UPDATE policy; actual mutation remains denied.
CREATE POLICY resolver_actor_row_lock ON business.organisations
FOR UPDATE TO identity_resolver_owner
USING (
    identity_managed
    AND identity_status = 'ACTIVE'
    AND EXISTS (
        SELECT 1
        FROM identity.memberships AS membership
        INNER JOIN identity.actor_bindings AS actor
            ON membership.account_id = actor.account_id
        WHERE
            membership.tenant_id = organisations.tenant_id
            AND actor.actor_issuer
            = NULLIF(pg_catalog.current_setting('app.identity_issuer', TRUE), '')
            AND actor.actor_subject
            = NULLIF(pg_catalog.current_setting('app.identity_subject', TRUE), '')
            AND actor.status = 'ACTIVE'
            AND membership.status = 'ACTIVE'
            AND membership.roles IN (ARRAY['OWNER']::text[], ARRAY['MANAGER']::text[])
    )
)
WITH CHECK (FALSE);

GRANT SELECT, INSERT ON identity.account_links TO business_app;
GRANT UPDATE (
    state, approval_evidence_id, cancellation_evidence_id, confirmation_evidence_id,
    confirmation_message_digest, confirmed_phone_subject_hash, confirmed_at, updated_at
) ON identity.account_links TO business_app;

DO $role$
BEGIN
    IF NOT pg_has_role(session_user, 'identity_resolver_owner', 'SET') THEN
        EXECUTE format('GRANT identity_resolver_owner TO %I', session_user);
        PERFORM set_config('waooaw.wc134_phone_guard_migration_granted', 'true', true);
    END IF;
    IF NOT pg_has_role(session_user, 'identity_whatsapp_recognizer_owner', 'SET') THEN
        EXECUTE format('GRANT identity_whatsapp_recognizer_owner TO %I', session_user);
        PERFORM set_config('waooaw.wc134_phone_hmac_migration_granted', 'true', true);
    END IF;
END
$role$;
GRANT CREATE ON SCHEMA identity TO identity_whatsapp_recognizer_owner;
GRANT CREATE ON SCHEMA identity TO identity_resolver_owner;

CREATE OR REPLACE FUNCTION identity.guard_registration_identity() RETURNS trigger
LANGUAGE plpgsql SECURITY INVOKER SET search_path = pg_catalog AS $guard$
BEGIN
    IF TG_OP = 'UPDATE' THEN
        IF OLD.state = 'Completed' THEN
            IF (to_jsonb(NEW) - ARRAY[
                    'mobile_hmac_key', 'mobile_hmac_version', 'mobile_hmac_domain',
                    'masked_mobile', 'mobile_verified', 'updated_at'])
                IS DISTINCT FROM (to_jsonb(OLD) - ARRAY[
                    'mobile_hmac_key', 'mobile_hmac_version', 'mobile_hmac_domain',
                    'masked_mobile', 'mobile_verified', 'updated_at'])
                OR OLD.mobile_verified IS DISTINCT FROM true OR NEW.mobile_verified IS DISTINCT FROM true
                OR NEW.mobile_hmac_domain IS DISTINCT FROM 'mobile'
                OR NOT EXISTS (
                    SELECT 1 FROM identity.phone_changes AS change
                    JOIN identity.verification_challenges AS proof
                      ON proof.challenge_id = change.challenge_id
                    WHERE change.registration_id = NEW.registration_id
                      AND change.account_id = NEW.account_id
                      AND change.actor_issuer = NEW.actor_issuer
                      AND change.actor_subject = NEW.actor_subject
                      AND change.previous_mobile_key = OLD.mobile_hmac_key
                      AND change.previous_mobile_version = OLD.mobile_hmac_version
                      AND change.destination_candidates ->> NEW.mobile_hmac_version = NEW.mobile_hmac_key
                      AND change.completion_evidence_id IS NOT NULL
                      AND change.completed_at IS NOT NULL
                      AND change.completed_at = proof.verified_at
                      AND proof.registration_id = NEW.registration_id
                      AND proof.actor_subject = NEW.actor_subject
                      AND proof.purpose = 'Mobile' AND proof.state = 'Consumed'
                      AND proof.delivery_state = 'SUBMITTED'
                      AND proof.expires_at > clock_timestamp()
                      AND proof.destination_hmac_domain = 'mobile'
                      AND proof.destination_hmac_version = NEW.mobile_hmac_version
                      AND proof.destination_hmac_key = NEW.mobile_hmac_key
                      AND proof.masked_destination = NEW.masked_mobile
                      AND EXISTS (
                          SELECT 1 FROM identity.resolve_customer_membership() AS membership
                          WHERE membership.account_id = change.account_id
                            AND membership.membership_id = change.membership_id
                            AND membership.roles = ARRAY['OWNER']::TEXT[]
                      )
                ) THEN
                RAISE EXCEPTION 'immutable registration identity' USING ERRCODE = '23514';
            END IF;
        ELSIF ROW(NEW.registration_id, NEW.actor_issuer, NEW.actor_subject, NEW.created_at)
           IS DISTINCT FROM ROW(OLD.registration_id, OLD.actor_issuer, OLD.actor_subject, OLD.created_at) THEN
            RAISE EXCEPTION 'immutable registration identity' USING ERRCODE = '23514';
        END IF;
    END IF;
    IF NEW.state <> 'Completed' AND (NEW.account_id IS NOT NULL OR NEW.actor_binding_id IS NOT NULL
       OR NEW.origin_registration_id IS NOT NULL OR NEW.completed_at IS NOT NULL OR NEW.completion_outcome IS NOT NULL
       OR NEW.completion_profile_snapshot IS NOT NULL OR NEW.completion_status_code IS NOT NULL OR NEW.completion_response_body IS NOT NULL) THEN
        RAISE EXCEPTION 'incomplete association' USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END;
$guard$;
ALTER FUNCTION identity.guard_registration_identity() OWNER TO identity_resolver_owner;
REVOKE CREATE ON SCHEMA identity FROM identity_resolver_owner;

CREATE OR REPLACE FUNCTION identity.phone_change_conflicts(p_account uuid, p_candidates jsonb)
RETURNS boolean LANGUAGE plpgsql SECURITY DEFINER
SET search_path = pg_catalog SET row_security = on
AS $function$
BEGIN
    IF p_account IS NULL OR jsonb_typeof(p_candidates) IS DISTINCT FROM 'object' THEN
        RAISE EXCEPTION 'Phone change input denied' USING ERRCODE = '42501';
    END IF;
    IF p_candidates = '{}'::JSONB OR EXISTS (
            SELECT 1 FROM jsonb_each_text(p_candidates) c
            WHERE c.value IS NULL OR c.value !~ '^[0-9a-f]{32}$' OR length(c.key) NOT BETWEEN 1 AND 32)
        OR NOT EXISTS (SELECT 1 FROM identity.resolve_customer_membership() m
            WHERE m.account_id = p_account AND m.roles = ARRAY['OWNER']::TEXT[]) THEN
        RAISE EXCEPTION 'Phone change authority denied' USING ERRCODE = '42501';
    END IF;
    RETURN EXISTS (
        SELECT 1 FROM identity.registrations r
        JOIN jsonb_each_text(p_candidates) c ON c.key = r.mobile_hmac_version AND c.value = r.mobile_hmac_key
        WHERE r.mobile_verified AND r.mobile_hmac_domain = 'mobile'
            AND r.state = 'Completed' AND r.account_id IS DISTINCT FROM p_account
    ) OR EXISTS (
        SELECT 1 FROM identity.account_links l
        JOIN identity.verification_challenges v ON v.challenge_id = l.verified_mobile_proof_id
        JOIN identity.registrations r ON r.registration_id = v.registration_id
        JOIN jsonb_each_text(p_candidates) c ON c.key = v.destination_hmac_version AND c.value = v.destination_hmac_key
        WHERE l.confirmed_at IS NOT NULL AND r.account_id IS DISTINCT FROM p_account
    );
END
$function$;
ALTER FUNCTION identity.phone_change_conflicts(uuid, jsonb) OWNER TO identity_whatsapp_recognizer_owner;
REVOKE ALL ON FUNCTION identity.phone_change_conflicts(uuid, jsonb) FROM public;
GRANT EXECUTE ON FUNCTION identity.phone_change_conflicts(uuid, jsonb) TO business_app;
REVOKE CREATE ON SCHEMA identity FROM identity_whatsapp_recognizer_owner;
DO $role$
BEGIN
    IF current_setting('waooaw.wc134_phone_guard_migration_granted', true) = 'true' THEN
        EXECUTE format('REVOKE identity_resolver_owner FROM %I', session_user);
    END IF;
    IF current_setting('waooaw.wc134_phone_hmac_migration_granted', true) = 'true' THEN
        EXECUTE format('REVOKE identity_whatsapp_recognizer_owner FROM %I', session_user);
    END IF;
END
$role$;

COMMIT;
