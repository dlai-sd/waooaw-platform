-- WC-124 final ownership and least-privilege compatibility handoff.
-- Constitutional basis: C-005, C-026, C-059, C-063, C-080

REVOKE ALL ON SCHEMA public FROM PUBLIC;

ALTER SCHEMA constitutional OWNER TO ce_owner;
ALTER SCHEMA business OWNER TO bp_owner;
ALTER SCHEMA professional OWNER TO pr_owner;
ALTER SCHEMA institutional OWNER TO bp_owner;
ALTER SCHEMA ai_runtime OWNER TO air_owner;
ALTER SCHEMA billing OWNER TO billing_owner;
ALTER SCHEMA web_session OWNER TO web_session_owner;

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
