#!/bin/sh
set -eu

: "${DATABASE_URL:?DATABASE_URL is required}"
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 <<'SQL'
DO $$
DECLARE
    missing_schemas text[];
    missing_roles text[];
BEGIN
    SELECT array_agg(required_schema ORDER BY required_schema)
      INTO missing_schemas
      FROM unnest(ARRAY['business', 'constitutional', 'institutional', 'keycloak', 'professional']) required_schema
     WHERE to_regnamespace(required_schema) IS NULL;
    IF missing_schemas IS NOT NULL THEN
        RAISE EXCEPTION 'missing schemas: %', missing_schemas;
    END IF;

    SELECT array_agg(required_role ORDER BY required_role)
      INTO missing_roles
      FROM unnest(ARRAY['ai_runtime_app', 'business_app', 'constitutional_app', 'runtime_app', 'wbe_app']) required_role
     WHERE NOT EXISTS (SELECT FROM pg_roles WHERE rolname = required_role);
    IF missing_roles IS NOT NULL THEN
        RAISE EXCEPTION 'missing roles: %', missing_roles;
    END IF;

    IF to_regclass('business.my_agents_selection_flash') IS NULL THEN
        RAISE EXCEPTION 'final migration object is missing';
    END IF;
    IF NOT EXISTS (
        SELECT 1
          FROM pg_class relation
          JOIN pg_namespace namespace ON namespace.oid = relation.relnamespace
         WHERE namespace.nspname = 'business'
           AND relation.relname = 'organisations'
           AND relation.relrowsecurity
    ) THEN
        RAISE EXCEPTION 'business.organisations RLS is not enabled';
    END IF;
    IF NOT has_table_privilege('constitutional_app', 'constitutional.evidence_records', 'SELECT, INSERT')
       OR has_table_privilege('constitutional_app', 'constitutional.evidence_records', 'UPDATE, DELETE') THEN
        RAISE EXCEPTION 'constitutional evidence grants violate append-only policy';
    END IF;
    IF (
        SELECT count(*)
          FROM pg_rules
         WHERE schemaname IN ('constitutional', 'professional')
           AND rulename IN (
               'no_update_evidence_records',
               'no_delete_evidence_records',
               'no_update_authority_licenses',
               'no_delete_authority_licenses',
               'no_update_experience_records',
               'no_delete_experience_records'
           )
    ) <> 6 THEN
        RAISE EXCEPTION 'append-only rule inventory is incomplete';
    END IF;
END
$$;
SQL
