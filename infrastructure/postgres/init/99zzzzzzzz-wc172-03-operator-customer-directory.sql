-- Implements: work-contracts/WC-172-safe-to-charge-real-customers.md (Demo defect repairs: Operations Customers tab)
-- constitutional_basis: C-005, C-023, C-026, C-059, C-063
-- A Founder/operations read of who has signed in and who has registered. Identity rows are actor-scoped by forced row
-- security, so this adds one narrow, read-only capability: the latest registration per signed-in person, masked contact
-- details only, newest activity first, keyset-paged. No raw email, mobile, HMAC digest or actor subject leaves the function.

BEGIN;

DO $role$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'identity_operator_directory_owner') THEN
        CREATE ROLE identity_operator_directory_owner NOLOGIN NOSUPERUSER NOBYPASSRLS;
    END IF;
    IF EXISTS (
        SELECT 1 FROM pg_roles AS principal
        WHERE principal.rolname = 'identity_operator_directory_owner'
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
        RAISE EXCEPTION 'Operator directory principal must be an isolated non-login role';
    END IF;
    IF NOT pg_has_role(session_user, 'identity_operator_directory_owner', 'SET') THEN
        EXECUTE format('GRANT identity_operator_directory_owner TO %I', session_user);
        PERFORM set_config('waooaw.wc172_directory_granted', 'true', true);
    END IF;
END
$role$;

GRANT USAGE, CREATE ON SCHEMA identity TO identity_operator_directory_owner;
GRANT SELECT (registration_id, actor_issuer, actor_subject, state, display_name, masked_email, masked_mobile,
              email_hmac_domain, email_hmac_version, email_hmac_key,
              mobile_hmac_domain, mobile_hmac_version, mobile_hmac_key,
              created_at, updated_at, completed_at)
    ON identity.registrations TO identity_operator_directory_owner;

DROP POLICY IF EXISTS operator_directory_read ON identity.registrations;
CREATE POLICY operator_directory_read ON identity.registrations
    FOR SELECT TO identity_operator_directory_owner
    USING (true);

CREATE INDEX IF NOT EXISTS registrations_directory_page_idx
    ON identity.registrations (updated_at DESC, registration_id DESC);
CREATE INDEX IF NOT EXISTS registrations_directory_name_idx
    ON identity.registrations (lower(display_name) text_pattern_ops)
    WHERE display_name IS NOT NULL;
CREATE INDEX IF NOT EXISTS registrations_directory_email_key_idx
    ON identity.registrations (email_hmac_key) WHERE email_hmac_key IS NOT NULL;
CREATE INDEX IF NOT EXISTS registrations_directory_mobile_key_idx
    ON identity.registrations (mobile_hmac_key) WHERE mobile_hmac_key IS NOT NULL;

CREATE OR REPLACE FUNCTION identity.operator_customer_directory(
    p_name text,
    p_contact_domains text[],
    p_contact_versions text[],
    p_contact_digests text[],
    p_status text,
    p_after_at timestamptz,
    p_after_id uuid,
    p_limit integer
) RETURNS TABLE (
    registration_id uuid,
    display_name text,
    masked_email text,
    masked_mobile text,
    status text,
    registration_state text,
    first_seen_at timestamptz,
    last_active_at timestamptz,
    registered_at timestamptz
)
LANGUAGE plpgsql STABLE SECURITY DEFINER
SET search_path = pg_catalog
SET row_security = on
AS $function$
BEGIN
    IF (p_status IS NOT NULL AND p_status NOT IN ('LOGGED_IN_ONLY', 'REGISTRATION_STARTED', 'REGISTERED'))
       OR (p_name IS NOT NULL AND pg_catalog.length(p_name) > 120)
       OR ((p_after_at IS NULL) <> (p_after_id IS NULL))
       OR (p_contact_digests IS NOT NULL AND (
            p_contact_domains IS NULL OR p_contact_versions IS NULL
            OR pg_catalog.cardinality(p_contact_digests) NOT BETWEEN 1 AND 64
            OR pg_catalog.cardinality(p_contact_digests) <> pg_catalog.cardinality(p_contact_domains)
            OR pg_catalog.cardinality(p_contact_digests) <> pg_catalog.cardinality(p_contact_versions)
            OR EXISTS (
                SELECT 1
                FROM ROWS FROM (pg_catalog.unnest(p_contact_domains), pg_catalog.unnest(p_contact_versions),
                                pg_catalog.unnest(p_contact_digests)) AS candidate(domain, version, digest)
                WHERE candidate.domain IS NULL OR candidate.version IS NULL OR candidate.digest IS NULL
                   OR candidate.domain NOT IN ('email', 'mobile')
                   OR candidate.version !~ '^[A-Za-z0-9._-]{1,32}$'
                   OR candidate.digest !~ '^[a-f0-9]{32}$'
            )))
    THEN
        RAISE EXCEPTION 'Invalid directory filter' USING ERRCODE = '22023';
    END IF;
    RETURN QUERY
    SELECT page.registration_id, page.display_name::text, page.masked_email::text, page.masked_mobile::text,
           page.status, page.state::text, page.created_at, page.updated_at, page.completed_at
    FROM (
        SELECT r.registration_id, r.display_name, r.masked_email, r.masked_mobile, r.state, r.created_at,
               r.updated_at, r.completed_at,
               CASE WHEN r.state = 'Completed' THEN 'REGISTERED'
                    WHEN r.state IN ('Started', 'FederatedIdentityAccepted', 'Expired', 'Cancelled')
                        THEN 'LOGGED_IN_ONLY'
                    ELSE 'REGISTRATION_STARTED' END AS status
        FROM identity.registrations AS r
        WHERE NOT EXISTS (
                SELECT 1 FROM identity.registrations AS newer
                WHERE newer.actor_subject = r.actor_subject
                  AND newer.actor_issuer IS NOT DISTINCT FROM r.actor_issuer
                  AND (newer.created_at, newer.registration_id) > (r.created_at, r.registration_id))
          AND (p_name IS NULL OR pg_catalog.lower(r.display_name) LIKE pg_catalog.lower(p_name) || '%')
          AND (p_contact_digests IS NULL OR EXISTS (
                SELECT 1
                FROM ROWS FROM (pg_catalog.unnest(p_contact_domains), pg_catalog.unnest(p_contact_versions),
                                pg_catalog.unnest(p_contact_digests)) AS candidate(domain, version, digest)
                WHERE (candidate.domain = 'email' AND r.email_hmac_domain = 'email'
                       AND r.email_hmac_version = candidate.version AND r.email_hmac_key = candidate.digest)
                   OR (candidate.domain = 'mobile' AND r.mobile_hmac_domain = 'mobile'
                       AND r.mobile_hmac_version = candidate.version AND r.mobile_hmac_key = candidate.digest)))
          AND (p_after_at IS NULL OR (r.updated_at, r.registration_id) < (p_after_at, p_after_id))
    ) AS page
    WHERE p_status IS NULL OR page.status = p_status
    ORDER BY page.updated_at DESC, page.registration_id DESC
    LIMIT LEAST(GREATEST(coalesce(p_limit, 11), 1), 51);
END;
$function$;

ALTER FUNCTION identity.operator_customer_directory(text, text[], text[], text[], text, timestamptz, uuid, integer)
    OWNER TO identity_operator_directory_owner;
REVOKE CREATE ON SCHEMA identity FROM identity_operator_directory_owner;
REVOKE ALL ON FUNCTION identity.operator_customer_directory(text, text[], text[], text[], text, timestamptz, uuid, integer)
    FROM PUBLIC;
GRANT EXECUTE ON FUNCTION identity.operator_customer_directory(text, text[], text[], text[], text, timestamptz, uuid, integer)
    TO business_app;

DO $memberships$
BEGIN
    IF current_setting('waooaw.wc172_directory_granted', true) = 'true' THEN
        EXECUTE format('REVOKE identity_operator_directory_owner FROM %I', session_user);
    END IF;
END
$memberships$;

COMMIT;
