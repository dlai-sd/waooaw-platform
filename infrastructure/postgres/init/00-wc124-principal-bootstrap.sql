-- WC-124 logical principal floor. Authentication secrets are generated out of band.
-- Constitutional basis: C-026, C-059, C-063, C-080

DO $roles$
DECLARE
    role_name text;
BEGIN
    FOREACH role_name IN ARRAY ARRAY[
        'keycloak_owner', 'keycloak_verifier',
        'temporal_owner', 'temporal_verifier',
        'ce_owner', 'ce_verifier',
        'bp_owner', 'bp_verifier',
        'pr_owner', 'pr_verifier',
        'air_owner', 'air_verifier',
        'billing_owner', 'billing_verifier',
        'web_session_owner', 'web_session_verifier',
        'constitutional_app', 'business_app', 'runtime_app', 'ai_runtime_app',
        'wbe_app', 'domain_adapter_app'
    ]
    LOOP
        IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = role_name) THEN
            EXECUTE format(
                'CREATE ROLE %I NOLOGIN NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE NOINHERIT',
                role_name
            );
        END IF;
    END LOOP;

    FOREACH role_name IN ARRAY ARRAY[
        'keycloak_migrator', 'keycloak_runtime',
        'temporal_migrator', 'temporal_runtime',
        'ce_migrator', 'ce_runtime',
        'bp_migrator', 'bp_runtime',
        'pr_migrator', 'pr_runtime',
        'air_migrator', 'air_runtime',
        'billing_migrator', 'billing_runtime',
        'web_session_migrator', 'web_session_app',
        'pgbouncer_auth', 'recovery_verifier_ephemeral'
    ]
    LOOP
        IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = role_name) THEN
            EXECUTE format(
                'CREATE ROLE %I LOGIN NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE INHERIT',
                role_name
            );
        END IF;
    END LOOP;
END
$roles$;
