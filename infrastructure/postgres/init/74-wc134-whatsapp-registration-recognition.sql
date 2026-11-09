-- WC-134 R005: index-bound registration recognition without actor/tenant disclosure.
-- constitutional_basis: C-023, C-026, C-059, C-063
-- This boolean capability does not resolve a session, membership, account or relationship.

BEGIN;

DO $role$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'identity_whatsapp_recognizer_owner') THEN
        CREATE ROLE identity_whatsapp_recognizer_owner NOLOGIN NOSUPERUSER NOBYPASSRLS;
    END IF;
    IF EXISTS (
        SELECT 1 FROM pg_roles AS principal
        WHERE principal.rolname = 'identity_whatsapp_recognizer_owner'
          AND (principal.rolcanlogin OR principal.rolsuper OR principal.rolbypassrls
               OR principal.rolcreaterole OR principal.rolcreatedb OR principal.rolreplication
               OR EXISTS (SELECT 1 FROM pg_auth_members WHERE member = principal.oid)
               OR EXISTS (
                   SELECT 1
                   FROM pg_auth_members AS membership
                   JOIN pg_roles AS grantee ON grantee.oid = membership.member
                   WHERE membership.roleid = principal.oid AND grantee.rolname <> session_user
               ))
    ) THEN
        RAISE EXCEPTION 'WhatsApp recognition principal must be an isolated non-login role';
    END IF;
    IF NOT pg_has_role(session_user, 'identity_whatsapp_recognizer_owner', 'SET') THEN
        EXECUTE format('GRANT identity_whatsapp_recognizer_owner TO %I', session_user);
        PERFORM set_config('waooaw.wc134_recognizer_granted', 'true', true);
    END IF;
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'web_session_owner') THEN
        IF NOT pg_has_role(session_user, 'web_session_owner', 'SET') THEN
            EXECUTE format('GRANT web_session_owner TO %I', session_user);
            PERFORM set_config('waooaw.wc134_recognition_schema_granted', 'true', true);
        END IF;
    END IF;
END
$role$;

GRANT USAGE, CREATE ON SCHEMA identity TO identity_whatsapp_recognizer_owner;
GRANT SELECT (registration_id, state, account_id, mobile_verified,
              mobile_hmac_domain, mobile_hmac_version, mobile_hmac_key)
    ON identity.registrations TO identity_whatsapp_recognizer_owner;
GRANT SELECT (registration_id, purpose, state, delivery_state, verified_at,
              destination_hmac_domain, destination_hmac_version, destination_hmac_key)
    ON identity.verification_challenges TO identity_whatsapp_recognizer_owner;

DROP POLICY IF EXISTS whatsapp_verified_registration_recognition ON identity.registrations;
CREATE POLICY whatsapp_verified_registration_recognition ON identity.registrations
    FOR SELECT TO identity_whatsapp_recognizer_owner
    USING (state = 'Completed' AND mobile_verified AND account_id IS NOT NULL);

DROP POLICY IF EXISTS whatsapp_verified_proof_recognition ON identity.verification_challenges;
CREATE POLICY whatsapp_verified_proof_recognition ON identity.verification_challenges
    FOR SELECT TO identity_whatsapp_recognizer_owner
    USING (purpose = 'Mobile' AND state = 'Consumed' AND delivery_state = 'SUBMITTED'
           AND verified_at IS NOT NULL);

CREATE OR REPLACE FUNCTION identity.has_verified_whatsapp_registration(
    versions text[], digests text[]
) RETURNS boolean
LANGUAGE plpgsql STABLE SECURITY DEFINER
SET search_path = pg_catalog
SET row_security = on
AS $function$
BEGIN
    IF versions IS NULL OR digests IS NULL
       OR pg_catalog.cardinality(versions) NOT BETWEEN 1 AND 64
       OR pg_catalog.cardinality(versions) <> pg_catalog.cardinality(digests)
       OR pg_catalog.array_ndims(versions) <> 1
       OR pg_catalog.array_ndims(digests) <> 1
       OR EXISTS (
           SELECT 1
           FROM ROWS FROM (pg_catalog.unnest(versions), pg_catalog.unnest(digests))
               AS candidate(version, digest)
           WHERE candidate.version IS NULL OR candidate.digest IS NULL
              OR candidate.version !~ '^[A-Za-z0-9._-]{1,32}$'
              OR candidate.digest !~ '^[a-f0-9]{32}$'
       )
    THEN
        RAISE EXCEPTION 'Invalid WhatsApp recognition candidates' USING ERRCODE = '22023';
    END IF;
    RETURN EXISTS (
        SELECT 1
        FROM ROWS FROM (pg_catalog.unnest(versions), pg_catalog.unnest(digests))
            AS candidate(version, digest)
        JOIN identity.registrations AS registration
          ON registration.mobile_hmac_domain = 'mobile'
         AND registration.mobile_hmac_version = candidate.version
         AND registration.mobile_hmac_key = candidate.digest
        WHERE registration.state = 'Completed'
          AND registration.mobile_verified
          AND registration.account_id IS NOT NULL
          AND EXISTS (
              SELECT 1
              FROM identity.verification_challenges AS challenge
              WHERE challenge.registration_id = registration.registration_id
                AND challenge.purpose = 'Mobile'
                AND challenge.state = 'Consumed'
                AND challenge.delivery_state = 'SUBMITTED'
                AND challenge.verified_at IS NOT NULL
                AND challenge.destination_hmac_domain = registration.mobile_hmac_domain
                AND challenge.destination_hmac_version = registration.mobile_hmac_version
                AND challenge.destination_hmac_key = registration.mobile_hmac_key
          )
    );
END;
$function$;

ALTER FUNCTION identity.has_verified_whatsapp_registration(text[], text[])
    OWNER TO identity_whatsapp_recognizer_owner;
REVOKE CREATE ON SCHEMA identity FROM identity_whatsapp_recognizer_owner;
REVOKE ALL ON FUNCTION identity.has_verified_whatsapp_registration(text[], text[]) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION identity.has_verified_whatsapp_registration(text[], text[]) TO business_app;

DO $memberships$
BEGIN
    IF current_setting('waooaw.wc134_recognizer_granted', true) = 'true' THEN
        EXECUTE format('REVOKE identity_whatsapp_recognizer_owner FROM %I', session_user);
    END IF;
    IF current_setting('waooaw.wc134_recognition_schema_granted', true) = 'true' THEN
        EXECUTE format('REVOKE web_session_owner FROM %I', session_user);
    END IF;
END
$memberships$;

COMMIT;
