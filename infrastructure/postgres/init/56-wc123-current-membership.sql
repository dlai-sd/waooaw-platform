-- WC-123 current multi-tenant membership authority.

BEGIN;

GRANT CREATE ON SCHEMA identity TO identity_resolver_owner;

DO $idempotent$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'memberships_account_tenant_unique' AND conrelid = 'identity.memberships'::regclass) THEN
        ALTER TABLE identity.memberships
            DROP CONSTRAINT IF EXISTS memberships_account_id_key,
            DROP CONSTRAINT IF EXISTS memberships_account_id_tenant_id_fkey,
            DROP CONSTRAINT IF EXISTS memberships_roles_check,
            DROP CONSTRAINT IF EXISTS memberships_status_check,
            ADD CONSTRAINT memberships_account_fk
                FOREIGN KEY (account_id) REFERENCES identity.accounts(account_id) ON DELETE RESTRICT,
            ADD CONSTRAINT memberships_tenant_fk
                FOREIGN KEY (tenant_id) REFERENCES business.organisations(tenant_id) ON DELETE RESTRICT,
            ADD CONSTRAINT memberships_roles_check
                CHECK (
                    cardinality(roles) = 1
                    AND roles[1] IN ('OWNER', 'MANAGER', 'VIEWER')
                ),
            ADD CONSTRAINT memberships_account_tenant_unique UNIQUE (account_id, tenant_id);
    END IF;
END
$idempotent$;

UPDATE identity.memberships SET status = 'SUSPENDED' WHERE status = 'INACTIVE';

DO $idempotent$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'memberships_status_check' AND conrelid = 'identity.memberships'::regclass) THEN
        ALTER TABLE identity.memberships
            ADD CONSTRAINT memberships_status_check
                CHECK (status IN ('ACTIVE', 'SUSPENDED', 'REMOVED'));
    END IF;
END
$idempotent$;

DROP POLICY resolver_actor_scope ON business.organisations;
DROP POLICY IF EXISTS resolver_actor_scope ON business.organisations;
CREATE POLICY resolver_actor_scope ON business.organisations
FOR SELECT TO identity_resolver_owner
USING (
    identity_managed
    AND identity_status = 'ACTIVE'
    AND EXISTS (
        SELECT 1
        FROM identity.memberships AS membership
        JOIN identity.actor_bindings AS actor
          ON actor.account_id = membership.account_id
        WHERE membership.tenant_id = organisations.tenant_id
          AND actor.actor_issuer =
              NULLIF(pg_catalog.current_setting('app.identity_issuer', true), '') COLLATE "C"
          AND actor.actor_subject =
              NULLIF(pg_catalog.current_setting('app.identity_subject', true), '') COLLATE "C"
          AND actor.status = 'ACTIVE'
    )
);

CREATE OR REPLACE FUNCTION identity.list_customer_memberships()
RETURNS TABLE (
    account_id uuid,
    tenant_id uuid,
    membership_id uuid,
    roles text[],
    membership_status varchar
)
LANGUAGE sql STABLE SECURITY DEFINER
SET search_path = pg_catalog
SET row_security = on
AS $function$
    SELECT account.account_id,
           membership.tenant_id,
           membership.membership_id,
           membership.roles,
           membership.status
    FROM identity.actor_bindings AS actor
    JOIN identity.login_methods AS login
      ON login.login_method_id = actor.login_method_id
     AND login.account_id = actor.account_id
    JOIN identity.accounts AS account ON account.account_id = actor.account_id
    JOIN identity.memberships AS membership ON membership.account_id = account.account_id
    JOIN business.organisations AS organisation ON organisation.tenant_id = membership.tenant_id
    WHERE actor.actor_issuer =
              NULLIF(pg_catalog.current_setting('app.identity_issuer', true), '') COLLATE "C"
      AND actor.actor_subject =
              NULLIF(pg_catalog.current_setting('app.identity_subject', true), '') COLLATE "C"
      AND actor.status = 'ACTIVE'
      AND login.status = 'ACTIVE'
      AND account.status = 'ACTIVE'
      AND organisation.identity_managed
    ORDER BY membership.membership_id
    LIMIT 100
$function$;

CREATE OR REPLACE FUNCTION identity.resolve_customer_membership()
RETURNS TABLE (account_id uuid, tenant_id uuid, membership_id uuid, roles text[])
LANGUAGE sql STABLE SECURITY DEFINER
SET search_path = pg_catalog
SET row_security = on
AS $function$
    WITH current_memberships AS MATERIALIZED (
        SELECT *
        FROM identity.list_customer_memberships()
        WHERE membership_status = 'ACTIVE'
    )
    SELECT membership.account_id,
           membership.tenant_id,
           membership.membership_id,
           membership.roles
    FROM current_memberships AS membership
    WHERE (
        NULLIF(pg_catalog.current_setting('app.current_membership_id', true), '') IS NOT NULL
        AND membership.membership_id =
            NULLIF(pg_catalog.current_setting('app.current_membership_id', true), '')::uuid
    )
    OR (
        NULLIF(pg_catalog.current_setting('app.current_membership_id', true), '') IS NULL
        AND (SELECT count(*) FROM current_memberships) = 1
    )
$function$;

ALTER FUNCTION identity.list_customer_memberships() OWNER TO identity_resolver_owner;
ALTER FUNCTION identity.resolve_customer_membership() OWNER TO identity_resolver_owner;
REVOKE ALL ON FUNCTION identity.list_customer_memberships() FROM PUBLIC;
REVOKE ALL ON FUNCTION identity.resolve_customer_membership() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION identity.list_customer_memberships()
    TO business_app, constitutional_app, runtime_app, wbe_app;
GRANT EXECUTE ON FUNCTION identity.resolve_customer_membership()
    TO business_app, constitutional_app, runtime_app, wbe_app;

REVOKE CREATE ON SCHEMA identity FROM identity_resolver_owner;

COMMIT;
