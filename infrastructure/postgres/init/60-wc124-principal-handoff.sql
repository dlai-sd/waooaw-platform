-- WC-124 final ownership and least-privilege compatibility handoff.
-- Constitutional basis: C-005, C-026, C-059, C-063, C-080

BEGIN;

DO $bootstrap_memberships$
DECLARE
    owner_name text;
BEGIN
    FOREACH owner_name IN ARRAY ARRAY[
        'ce_owner',
        'bp_owner',
        'pr_owner',
        'air_owner',
        'billing_owner',
        'web_session_owner',
        'keycloak_owner',
        'temporal_owner'
    ]
    LOOP
        EXECUTE format('GRANT %I TO %I', owner_name, session_user);
    END LOOP;
END
$bootstrap_memberships$;

REVOKE ALL ON SCHEMA public FROM PUBLIC;

ALTER SCHEMA constitutional OWNER TO ce_owner;
ALTER SCHEMA audit_sink OWNER TO ce_owner;
ALTER SCHEMA business OWNER TO bp_owner;
ALTER SCHEMA professional OWNER TO pr_owner;
ALTER SCHEMA institutional OWNER TO bp_owner;
ALTER SCHEMA payload_store OWNER TO bp_owner;
ALTER SCHEMA domain_adapter OWNER TO bp_owner;
ALTER SCHEMA ai_runtime OWNER TO air_owner;
ALTER SCHEMA billing OWNER TO billing_owner;
ALTER SCHEMA identity OWNER TO web_session_owner;
ALTER SCHEMA web_session OWNER TO web_session_owner;
ALTER SCHEMA keycloak OWNER TO keycloak_owner;

DO $ownership$
DECLARE
    ownership record;
    database_object record;
BEGIN
    FOR ownership IN
        SELECT *
        FROM (
            VALUES
                ('constitutional', 'ce_owner'),
                ('audit_sink', 'ce_owner'),
                ('business', 'bp_owner'),
                ('professional', 'pr_owner'),
                ('institutional', 'bp_owner'),
                ('payload_store', 'bp_owner'),
                ('domain_adapter', 'bp_owner'),
                ('ai_runtime', 'air_owner'),
                ('billing', 'billing_owner'),
                ('identity', 'web_session_owner'),
                ('web_session', 'web_session_owner'),
                ('keycloak', 'keycloak_owner')
        ) AS accepted(schema_name, owner_name)
    LOOP
        FOR database_object IN
            SELECT c.relname, c.relkind
            FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = ownership.schema_name
              AND c.relkind IN ('r', 'p', 'S', 'v', 'm', 'f')
              AND (
                  c.relkind <> 'S'
                  OR NOT EXISTS (
                      SELECT 1
                      FROM pg_depend d
                      WHERE d.objid = c.oid
                        AND d.classid = 'pg_class'::regclass
                        AND d.refclassid = 'pg_class'::regclass
                        AND d.deptype IN ('a', 'i')
                  )
              )
        LOOP
            EXECUTE format(
                'ALTER %s %I.%I OWNER TO %I',
                CASE database_object.relkind
                    WHEN 'S' THEN 'SEQUENCE'
                    WHEN 'v' THEN 'VIEW'
                    WHEN 'm' THEN 'MATERIALIZED VIEW'
                    WHEN 'f' THEN 'FOREIGN TABLE'
                    ELSE 'TABLE'
                END,
                ownership.schema_name,
                database_object.relname,
                ownership.owner_name
            );
        END LOOP;

        FOR database_object IN
            SELECT p.oid::regprocedure AS routine_name, p.prokind
            FROM pg_proc p
            JOIN pg_namespace n ON n.oid = p.pronamespace
            WHERE n.nspname = ownership.schema_name
              AND p.prokind IN ('f', 'p')
        LOOP
            EXECUTE format(
                'ALTER %s %s OWNER TO %I',
                CASE database_object.prokind WHEN 'p' THEN 'PROCEDURE' ELSE 'FUNCTION' END,
                database_object.routine_name,
                ownership.owner_name
            );
        END LOOP;

        FOR database_object IN
            SELECT t.typname
            FROM pg_type t
            JOIN pg_namespace n ON n.oid = t.typnamespace
            WHERE n.nspname = ownership.schema_name
              AND t.typtype IN ('e', 'd')
        LOOP
            EXECUTE format(
                'ALTER TYPE %I.%I OWNER TO %I',
                ownership.schema_name,
                database_object.typname,
                ownership.owner_name
            );
        END LOOP;
    END LOOP;
END
$ownership$;

GRANT constitutional_app TO ce_runtime;
GRANT business_app TO bp_runtime;
GRANT runtime_app TO pr_runtime;
GRANT ai_runtime_app TO air_runtime;
GRANT wbe_app TO billing_runtime;
GRANT ce_owner TO ce_migrator;
GRANT bp_owner TO bp_migrator;
GRANT pr_owner TO pr_migrator;
GRANT air_owner TO air_migrator;
GRANT billing_owner TO billing_migrator;
GRANT web_session_owner TO web_session_migrator;

GRANT USAGE ON SCHEMA constitutional TO ce_verifier;
GRANT SELECT ON ALL TABLES IN SCHEMA constitutional TO ce_verifier;
GRANT USAGE ON SCHEMA business, institutional TO bp_verifier;
GRANT SELECT ON ALL TABLES IN SCHEMA business, institutional TO bp_verifier;
GRANT USAGE ON SCHEMA professional TO pr_verifier;
GRANT SELECT ON ALL TABLES IN SCHEMA professional TO pr_verifier;
GRANT USAGE ON SCHEMA ai_runtime TO air_verifier;
GRANT SELECT ON ALL TABLES IN SCHEMA ai_runtime TO air_verifier;
GRANT USAGE ON SCHEMA billing TO billing_verifier;
GRANT SELECT ON ALL TABLES IN SCHEMA billing TO billing_verifier;
GRANT USAGE ON SCHEMA web_session TO web_session_verifier;
GRANT SELECT ON ALL TABLES IN SCHEMA web_session TO web_session_verifier;

DO $rls$
DECLARE
    relation record;
BEGIN
    FOR relation IN
        SELECT n.nspname AS schema_name, c.relname AS table_name
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE c.relkind = 'r'
          AND n.nspname IN (
              'constitutional',
              'business',
              'professional',
              'ai_runtime',
              'billing',
              'web_session'
          )
          AND EXISTS (
              SELECT 1
              FROM pg_attribute a
              WHERE a.attrelid = c.oid
                AND a.attname IN ('tenant_id', 'customer_id', 'organisation_id')
                AND NOT a.attisdropped
          )
    LOOP
        EXECUTE format(
            'ALTER TABLE %I.%I ENABLE ROW LEVEL SECURITY',
            relation.schema_name,
            relation.table_name
        );
        EXECUTE format(
            'ALTER TABLE %I.%I FORCE ROW LEVEL SECURITY',
            relation.schema_name,
            relation.table_name
        );
    END LOOP;
END
$rls$;

DO $databases$
DECLARE
    database_ownership record;
BEGIN
    FOR database_ownership IN
        SELECT *
        FROM (
            VALUES
                ('waooaw_application', 'bp_owner'),
                ('waooaw_keycloak', 'keycloak_owner'),
                ('waooaw_temporal', 'temporal_owner'),
                ('waooaw_temporal_visibility', 'temporal_owner')
        ) AS mapping(database_name, owner_name)
    LOOP
        IF EXISTS (SELECT 1 FROM pg_database WHERE datname = database_ownership.database_name) THEN
            EXECUTE format(
                'ALTER DATABASE %I OWNER TO %I',
                database_ownership.database_name,
                database_ownership.owner_name
            );
        END IF;
    END LOOP;
END
$databases$;

DO $bootstrap_memberships$
DECLARE
    owner_name text;
BEGIN
    FOREACH owner_name IN ARRAY ARRAY[
        'ce_owner',
        'bp_owner',
        'pr_owner',
        'air_owner',
        'billing_owner',
        'web_session_owner',
        'keycloak_owner',
        'temporal_owner'
    ]
    LOOP
        EXECUTE format('REVOKE %I FROM %I', owner_name, session_user);
    END LOOP;
END
$bootstrap_memberships$;

COMMIT;
