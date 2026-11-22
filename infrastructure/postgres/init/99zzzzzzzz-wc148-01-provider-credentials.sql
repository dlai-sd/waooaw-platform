-- Implements: work-contracts/WC-148-founder-provider-credential-registry-screen.md WC148-R001
-- Constitutional basis: C-023, C-059, C-063, C-083, C-084
-- WC-148: the provider registry gains a category, an optional agent type, an optional test endpoint and a
-- credential version history. The history records which Key Vault secret version each credential version is;
-- it never holds a secret value. At most one version per provider is ACTIVE. Seeded platform rows start with
-- no credential. Idempotent: Demo re-applies every init file at BP startup.
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '30s';

SELECT set_config(
  'waooaw.provider_credentials_was_forced',
  COALESCE((
    SELECT relforcerowsecurity::text
    FROM pg_class
    WHERE oid = to_regclass('business.provider_configs')
  ), 'false'),
  true
);

DO $provider_credentials_rls$
BEGIN
  IF current_setting('waooaw.provider_credentials_was_forced')::boolean THEN
    EXECUTE 'SET LOCAL ROLE bp_owner';
    EXECUTE 'ALTER TABLE business.provider_configs NO FORCE ROW LEVEL SECURITY';
    EXECUTE 'RESET ROLE';
  END IF;
END
$provider_credentials_rls$;

SET LOCAL ROLE bp_owner;

ALTER TABLE business.provider_configs
    ADD COLUMN IF NOT EXISTS display_name TEXT,
    ADD COLUMN IF NOT EXISTS category TEXT,
    ADD COLUMN IF NOT EXISTS agent_type_id TEXT,
    ADD COLUMN IF NOT EXISTS test_url TEXT,
    ADD COLUMN IF NOT EXISTS test_auth_scheme TEXT,
    ADD COLUMN IF NOT EXISTS test_auth_header TEXT,
    ADD COLUMN IF NOT EXISTS active_credential_version_id UUID;

DO $provider_credentials_checks$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid = 'business.provider_configs'::regclass
        AND conname = 'provider_configs_category_check') THEN
        ALTER TABLE business.provider_configs ADD CONSTRAINT provider_configs_category_check
            CHECK (category IS NULL OR category IN ('PLATFORM_LLM', 'AGENT_API'));
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid = 'business.provider_configs'::regclass
        AND conname = 'provider_configs_test_auth_scheme_check') THEN
        ALTER TABLE business.provider_configs ADD CONSTRAINT provider_configs_test_auth_scheme_check
            CHECK (test_auth_scheme IS NULL OR test_auth_scheme IN ('BEARER', 'X_API_KEY', 'X_GOOG_API_KEY', 'HEADER'));
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid = 'business.provider_configs'::regclass
        AND conname = 'provider_configs_test_url_https_check') THEN
        ALTER TABLE business.provider_configs ADD CONSTRAINT provider_configs_test_url_https_check
            CHECK (test_url IS NULL OR test_url LIKE 'https://%');
    END IF;
END
$provider_credentials_checks$;

CREATE TABLE IF NOT EXISTS business.provider_credential_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider_config_id UUID NOT NULL REFERENCES business.provider_configs (id),
    version_no INTEGER NOT NULL CHECK (version_no >= 1),
    vault_secret_name TEXT NOT NULL CHECK (vault_secret_name ~ '^[A-Za-z0-9-]{1,127}$'),
    vault_secret_version TEXT NOT NULL CHECK (vault_secret_version ~ '^[A-Za-z0-9]{1,64}$'),
    status TEXT NOT NULL CHECK (status IN ('ACTIVE', 'SUPERSEDED')),
    test_outcome TEXT NOT NULL CHECK (test_outcome IN ('PASSED', 'NOT_TESTABLE')),
    created_by_subject TEXT NOT NULL CHECK (length(created_by_subject) BETWEEN 1 AND 254),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    activated_at TIMESTAMPTZ,
    UNIQUE (provider_config_id, version_no)
);

CREATE UNIQUE INDEX IF NOT EXISTS uidx_provider_credential_versions_one_active
    ON business.provider_credential_versions (provider_config_id)
    WHERE status = 'ACTIVE';

DO $provider_credentials_fk$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid = 'business.provider_configs'::regclass
        AND conname = 'provider_configs_active_credential_version_fk') THEN
        ALTER TABLE business.provider_configs ADD CONSTRAINT provider_configs_active_credential_version_fk
            FOREIGN KEY (active_credential_version_id) REFERENCES business.provider_credential_versions (id);
    END IF;
END
$provider_credentials_fk$;

-- A recorded version never changes which Key Vault secret version it names and is never deleted;
-- only its status and activation time move when it is superseded or re-activated.
CREATE OR REPLACE FUNCTION business.protect_provider_credential_version() RETURNS TRIGGER
LANGUAGE plpgsql SET search_path = pg_catalog AS $body$
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'Provider credential versions are append-only' USING ERRCODE = '23514';
    END IF;
    IF ROW(OLD.id, OLD.provider_config_id, OLD.version_no, OLD.vault_secret_name, OLD.vault_secret_version,
           OLD.test_outcome, OLD.created_by_subject, OLD.created_at)
       IS DISTINCT FROM
       ROW(NEW.id, NEW.provider_config_id, NEW.version_no, NEW.vault_secret_name, NEW.vault_secret_version,
           NEW.test_outcome, NEW.created_by_subject, NEW.created_at) THEN
        RAISE EXCEPTION 'Provider credential version identity is immutable' USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END
$body$;

DROP TRIGGER IF EXISTS provider_credential_versions_protect ON business.provider_credential_versions;
CREATE TRIGGER provider_credential_versions_protect
    BEFORE UPDATE OR DELETE ON business.provider_credential_versions
    FOR EACH ROW EXECUTE FUNCTION business.protect_provider_credential_version();

REVOKE ALL ON business.provider_credential_versions FROM PUBLIC;
GRANT SELECT, INSERT ON business.provider_credential_versions TO business_app;
GRANT UPDATE (status, activated_at) ON business.provider_credential_versions TO business_app;

-- Platform rows for the providers WAOOAW routes to. No credential is seeded: the Founder enters it.
INSERT INTO business.provider_configs
    (tenant_id, provider_name, auth_method, mcp_server_url, scope_set, vault_path_key,
     display_name, category, test_url, test_auth_scheme)
VALUES
    (NULL, 'openai', 'API_KEY', NULL, ARRAY[]::TEXT[], 'providers/platform/openai',
     'OpenAI', 'PLATFORM_LLM', 'https://api.openai.com/v1/models', 'BEARER'),
    (NULL, 'anthropic', 'API_KEY', NULL, ARRAY[]::TEXT[], 'providers/platform/anthropic',
     'Anthropic', 'PLATFORM_LLM', 'https://api.anthropic.com/v1/models', 'X_API_KEY'),
    (NULL, 'google', 'API_KEY', NULL, ARRAY[]::TEXT[], 'providers/platform/google',
     'Google', 'PLATFORM_LLM', 'https://generativelanguage.googleapis.com/v1beta/models', 'X_GOOG_API_KEY'),
    (NULL, 'sarvam', 'API_KEY', NULL, ARRAY[]::TEXT[], 'providers/platform/sarvam',
     'Sarvam', 'PLATFORM_LLM', NULL, NULL)
ON CONFLICT (provider_name) WHERE tenant_id IS NULL DO NOTHING;

-- openai already exists from the original registry seed; give it its WC-148 settings once, without
-- overwriting anything the Founder has since changed.
UPDATE business.provider_configs
SET display_name = 'OpenAI',
    category = 'PLATFORM_LLM',
    test_url = 'https://api.openai.com/v1/models',
    test_auth_scheme = 'BEARER'
WHERE tenant_id IS NULL AND provider_name = 'openai' AND auth_method = 'API_KEY'
  AND category IS NULL AND display_name IS NULL;

RESET ROLE;

DO $provider_credentials_rls$
BEGIN
  IF current_setting('waooaw.provider_credentials_was_forced')::boolean THEN
    EXECUTE 'SET LOCAL ROLE bp_owner';
    EXECUTE 'ALTER TABLE business.provider_configs FORCE ROW LEVEL SECURITY';
    EXECUTE 'RESET ROLE';
  END IF;
END
$provider_credentials_rls$;

COMMIT;
