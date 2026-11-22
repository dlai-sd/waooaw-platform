-- Implements: work-contracts/WC-149-paid-provider-consumption-and-customer-account-connection.md WC149-R001, WC149-R007
-- Constitutional basis: C-005, C-023, C-026, C-059, C-063, C-083, C-084
-- WC-149: (1) the registry learns how to test a provider that has no read-only endpoint (Sarvam: an empty POST) and
-- the Meta app credential (app id and secret as JSON); (2) a customer's connected marketing account gets a
-- tenant-isolated record and single-use OAuth state records. Neither table holds a token or secret value: the
-- connection names the Key Vault secret (customer-connection-<id>) and its version. Idempotent: Demo re-applies every
-- init file at BP startup, and a database that already ran WC-148's seed is upgraded in place.
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '30s';

SELECT set_config(
  'waooaw.provider_connections_was_forced',
  COALESCE((
    SELECT relforcerowsecurity::text
    FROM pg_class
    WHERE oid = to_regclass('business.provider_configs')
  ), 'false'),
  true
);

DO $provider_connections_rls$
BEGIN
  IF current_setting('waooaw.provider_connections_was_forced')::boolean THEN
    EXECUTE 'SET LOCAL ROLE bp_owner';
    EXECUTE 'ALTER TABLE business.provider_configs NO FORCE ROW LEVEL SECURITY';
    EXECUTE 'RESET ROLE';
  END IF;
END
$provider_connections_rls$;

SET LOCAL ROLE bp_owner;

ALTER TABLE business.provider_configs
    ADD COLUMN IF NOT EXISTS test_method TEXT;

DO $provider_connections_checks$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid = 'business.provider_configs'::regclass
        AND conname = 'provider_configs_test_method_check') THEN
        ALTER TABLE business.provider_configs ADD CONSTRAINT provider_configs_test_method_check
            CHECK (test_method IS NULL OR test_method IN ('GET', 'POST_EMPTY_JSON'));
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid = 'business.provider_configs'::regclass
        AND conname = 'provider_configs_test_auth_scheme_check'
        AND pg_get_constraintdef(oid) LIKE '%META_APP%') THEN
        ALTER TABLE business.provider_configs DROP CONSTRAINT IF EXISTS provider_configs_test_auth_scheme_check;
        ALTER TABLE business.provider_configs ADD CONSTRAINT provider_configs_test_auth_scheme_check
            CHECK (test_auth_scheme IS NULL OR test_auth_scheme IN
                ('BEARER', 'X_API_KEY', 'X_GOOG_API_KEY', 'HEADER', 'SUBSCRIPTION_KEY', 'META_APP'));
    END IF;
END
$provider_connections_checks$;

-- Sarvam: an empty-body POST to chat completions answers 400/422 for a valid key and 403 for an invalid one
-- (a GET to /v1/models answers 200 for any key). Set once, only while the WC-148 seed's empty value is untouched.
UPDATE business.provider_configs
SET test_url = 'https://api.sarvam.ai/v1/chat/completions',
    test_auth_scheme = 'SUBSCRIPTION_KEY',
    test_method = 'POST_EMPTY_JSON'
WHERE tenant_id IS NULL AND provider_name = 'sarvam' AND auth_method = 'API_KEY'
  AND test_url IS NULL AND test_auth_scheme IS NULL;

-- Meta: the Founder enters the developer app id and secret (JSON) on the provider screen. The row stays OAUTH2
-- with its tenant-templated vault path for existing registry readers; the Founder credential lives in the
-- provider-meta secret like every other provider credential. Set once, without overwriting Founder changes.
UPDATE business.provider_configs
SET display_name = 'Meta (Facebook and Instagram)',
    category = 'AGENT_API',
    test_url = 'https://graph.facebook.com/oauth/access_token',
    test_auth_scheme = 'META_APP'
WHERE tenant_id IS NULL AND provider_name = 'meta' AND auth_method = 'OAUTH2'
  AND category IS NULL AND display_name IS NULL AND test_url IS NULL;

CREATE TABLE IF NOT EXISTS business.customer_provider_connections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    provider TEXT NOT NULL CHECK (provider IN ('meta')),
    status TEXT NOT NULL CHECK (status IN ('CONNECTED', 'NEEDS_REPAIR', 'REVOKED')),
    account_id TEXT NOT NULL CHECK (account_id ~ '^[0-9]{1,40}$'),
    account_name TEXT NOT NULL CHECK (length(account_name) BETWEEN 1 AND 200),
    scopes TEXT[] NOT NULL DEFAULT '{}',
    secret_name TEXT NOT NULL CHECK (secret_name ~ '^customer-connection-[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'),
    secret_version TEXT NOT NULL CHECK (secret_version ~ '^[A-Za-z0-9]{1,64}$'),
    expires_at TIMESTAMPTZ,
    connected_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    revoked_at TIMESTAMPTZ,
    created_by UUID NOT NULL,
    CHECK ((status = 'REVOKED') = (revoked_at IS NOT NULL))
);
ALTER TABLE business.customer_provider_connections OWNER TO bp_owner;

-- One live connection per provider account for a tenant; a revoked one is history and a new connection is a new row.
CREATE UNIQUE INDEX IF NOT EXISTS uidx_customer_provider_connections_live
    ON business.customer_provider_connections (tenant_id, provider, account_id)
    WHERE status <> 'REVOKED';
CREATE INDEX IF NOT EXISTS idx_customer_provider_connections_tenant
    ON business.customer_provider_connections (tenant_id, connected_at DESC);

CREATE TABLE IF NOT EXISTS business.provider_connection_states (
    state_hash TEXT PRIMARY KEY CHECK (state_hash ~ '^[0-9a-f]{64}$'),
    tenant_id UUID NOT NULL,
    actor_id UUID NOT NULL,
    provider TEXT NOT NULL CHECK (provider IN ('meta')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at TIMESTAMPTZ NOT NULL,
    consumed_at TIMESTAMPTZ,
    CHECK (expires_at > created_at)
);
ALTER TABLE business.provider_connection_states OWNER TO bp_owner;
CREATE INDEX IF NOT EXISTS idx_provider_connection_states_expiry
    ON business.provider_connection_states (expires_at);

ALTER TABLE business.customer_provider_connections ENABLE ROW LEVEL SECURITY;
ALTER TABLE business.customer_provider_connections FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS customer_provider_connections_tenant_isolation ON business.customer_provider_connections;
CREATE POLICY customer_provider_connections_tenant_isolation ON business.customer_provider_connections TO business_app
    USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', TRUE), '')::UUID)
    WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', TRUE), '')::UUID);
DROP POLICY IF EXISTS customer_provider_connections_owner ON business.customer_provider_connections;
CREATE POLICY customer_provider_connections_owner ON business.customer_provider_connections TO bp_owner
    USING (true) WITH CHECK (true);

ALTER TABLE business.provider_connection_states ENABLE ROW LEVEL SECURITY;
ALTER TABLE business.provider_connection_states FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS provider_connection_states_tenant_isolation ON business.provider_connection_states;
CREATE POLICY provider_connection_states_tenant_isolation ON business.provider_connection_states TO business_app
    USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', TRUE), '')::UUID)
    WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', TRUE), '')::UUID);
DROP POLICY IF EXISTS provider_connection_states_owner ON business.provider_connection_states;
CREATE POLICY provider_connection_states_owner ON business.provider_connection_states TO bp_owner
    USING (true) WITH CHECK (true);

REVOKE ALL ON business.customer_provider_connections FROM PUBLIC, business_app;
GRANT SELECT, INSERT ON business.customer_provider_connections TO business_app;
GRANT UPDATE (status, account_name, scopes, secret_version, expires_at, connected_at, revoked_at, created_by)
    ON business.customer_provider_connections TO business_app;
REVOKE ALL ON business.provider_connection_states FROM PUBLIC, business_app;
GRANT SELECT, INSERT ON business.provider_connection_states TO business_app;
GRANT UPDATE (consumed_at) ON business.provider_connection_states TO business_app;

RESET ROLE;

DO $provider_connections_rls$
BEGIN
  IF current_setting('waooaw.provider_connections_was_forced')::boolean THEN
    EXECUTE 'SET LOCAL ROLE bp_owner';
    EXECUTE 'ALTER TABLE business.provider_configs FORCE ROW LEVEL SECURITY';
    EXECUTE 'RESET ROLE';
  END IF;
END
$provider_connections_rls$;

COMMIT;
