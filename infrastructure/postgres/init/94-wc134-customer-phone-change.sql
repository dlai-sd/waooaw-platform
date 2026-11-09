-- WC-134: customer-initiated verified phone replacement, never cross-owner transfer.
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '30s';
DO $membership$
BEGIN
    IF NOT pg_has_role(session_user, 'web_session_owner', 'SET') THEN
        EXECUTE format('GRANT web_session_owner TO %I', session_user);
        PERFORM set_config('waooaw.phone_change_owner_granted', 'true', true);
    END IF;
    IF NOT pg_has_role(session_user, 'identity_whatsapp_recognizer_owner', 'SET') THEN
        EXECUTE format('GRANT identity_whatsapp_recognizer_owner TO %I', session_user);
        PERFORM set_config('waooaw.phone_change_recognizer_granted', 'true', true);
    END IF;
END
$membership$;

CREATE TABLE IF NOT EXISTS identity.phone_changes (
    challenge_id UUID PRIMARY KEY REFERENCES identity.verification_challenges (challenge_id),
    registration_id UUID NOT NULL REFERENCES identity.registrations (registration_id),
    actor_issuer TEXT COLLATE "C" NOT NULL, actor_subject TEXT COLLATE "C" NOT NULL,
    account_id UUID NOT NULL, tenant_id UUID NOT NULL, membership_id UUID NOT NULL,
    previous_mobile_key TEXT NOT NULL, previous_mobile_version TEXT NOT NULL,
    destination_candidates JSONB NOT NULL CHECK (jsonb_typeof(destination_candidates) = 'object'),
    start_evidence_id UUID NOT NULL, completion_evidence_id UUID,
    created_at TIMESTAMPTZ NOT NULL, completed_at TIMESTAMPTZ,
    CHECK ((completed_at IS NULL) = (completion_evidence_id IS NULL))
);
ALTER TABLE identity.phone_changes OWNER TO web_session_owner;
ALTER TABLE identity.phone_changes ENABLE ROW LEVEL SECURITY;
ALTER TABLE identity.phone_changes FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS phone_change_actor_scope ON identity.phone_changes;
CREATE POLICY phone_change_actor_scope ON identity.phone_changes
TO business_app, web_session_owner
USING (
    actor_issuer = current_setting('app.identity_issuer', TRUE)
    AND actor_subject = current_setting('app.identity_subject', TRUE)
    AND tenant_id = nullif(current_setting('app.current_tenant_id', TRUE), '')::UUID
)
WITH CHECK (
    actor_issuer = current_setting('app.identity_issuer', TRUE)
    AND actor_subject = current_setting('app.identity_subject', TRUE)
    AND tenant_id = nullif(current_setting('app.current_tenant_id', TRUE), '')::UUID
);
REVOKE ALL ON identity.phone_changes FROM public, business_app;
GRANT SELECT, INSERT ON identity.phone_changes TO business_app;
GRANT UPDATE (completion_evidence_id, completed_at) ON identity.phone_changes TO business_app;
REVOKE DELETE ON identity.phone_changes FROM business_app;

GRANT CREATE ON SCHEMA identity TO identity_whatsapp_recognizer_owner;
GRANT SELECT (account_id) ON identity.registrations TO identity_whatsapp_recognizer_owner;
GRANT SELECT (challenge_id) ON identity.verification_challenges TO identity_whatsapp_recognizer_owner;
GRANT EXECUTE ON FUNCTION identity.resolve_customer_membership() TO identity_whatsapp_recognizer_owner;
GRANT SELECT (verified_mobile_proof_id, confirmed_at) ON identity.account_links TO identity_whatsapp_recognizer_owner;
DROP POLICY IF EXISTS phone_change_conflict_links ON identity.account_links;
CREATE POLICY phone_change_conflict_links ON identity.account_links FOR SELECT
TO identity_whatsapp_recognizer_owner USING (TRUE);

CREATE OR REPLACE FUNCTION identity.phone_change_conflicts(p_account UUID, p_candidates JSONB)
RETURNS BOOLEAN LANGUAGE plpgsql SECURITY DEFINER
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
ALTER FUNCTION identity.phone_change_conflicts(UUID, JSONB) OWNER TO identity_whatsapp_recognizer_owner;
REVOKE ALL ON FUNCTION identity.phone_change_conflicts(UUID, JSONB) FROM public;
GRANT EXECUTE ON FUNCTION identity.phone_change_conflicts(UUID, JSONB) TO business_app;
REVOKE CREATE ON SCHEMA identity FROM identity_whatsapp_recognizer_owner;

DO $membership$
BEGIN
    IF current_setting('waooaw.phone_change_owner_granted', true) = 'true' THEN
        EXECUTE format('REVOKE web_session_owner FROM %I', session_user);
    END IF;
    IF current_setting('waooaw.phone_change_recognizer_granted', true) = 'true' THEN
        EXECUTE format('REVOKE identity_whatsapp_recognizer_owner FROM %I', session_user);
    END IF;
END
$membership$;
COMMIT;
