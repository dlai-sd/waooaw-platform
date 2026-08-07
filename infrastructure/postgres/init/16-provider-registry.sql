-- 16-provider-registry.sql
-- Provider Registry — runtime-configurable platform routing table.
-- Implements: adr/ADR-042-provider-registry-constitutional-tool-gateway.md §1
-- constitutional_basis: C-031 (ADR on file), C-041 (tool authorization), C-003 (authority licensed)

-- provider_configs lives in the business schema (BP-owned, PR/AIR read-only via internal API)
CREATE TABLE IF NOT EXISTS business.provider_configs (
  id              UUID          PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id       UUID,                                              -- NULL = platform-level (e.g. OpenAI API key)
  provider_name   VARCHAR(64)   NOT NULL,
  auth_method     VARCHAR(32)   NOT NULL CHECK (auth_method IN ('OAUTH2', 'API_KEY', 'INTERNAL_JWT')),
  mcp_server_url  VARCHAR(512),                                      -- null for API_KEY providers
  scope_set       TEXT[]        NOT NULL DEFAULT '{}',
  vault_path_key  VARCHAR(256)  NOT NULL,
  active          BOOLEAN       NOT NULL DEFAULT true,
  created_at      TIMESTAMPTZ   NOT NULL DEFAULT now(),
  UNIQUE (tenant_id, provider_name)
);

-- Platform-level entries (tenant_id IS NULL) must also be unique by provider_name.
-- Standard UNIQUE allows multiple NULLs; this partial index enforces the platform-level constraint.
CREATE UNIQUE INDEX IF NOT EXISTS uidx_provider_configs_platform
  ON business.provider_configs (provider_name)
  WHERE tenant_id IS NULL;

CREATE INDEX IF NOT EXISTS idx_provider_configs_tenant
  ON business.provider_configs (tenant_id)
  WHERE tenant_id IS NOT NULL;

-- ─── Seed rows ────────────────────────────────────────────────────────────────
-- These are platform-default templates. tenant_id = NULL means they apply platform-wide.
-- Per-tenant overrides are inserted at onboarding time with a specific tenant_id.

-- Meta (Instagram + Facebook Pages) — OAUTH2 with customer delegation (C-003)
INSERT INTO business.provider_configs
  (tenant_id, provider_name, auth_method, mcp_server_url, scope_set, vault_path_key)
VALUES
  (NULL, 'meta', 'OAUTH2', NULL,
   ARRAY['pages_manage_posts', 'instagram_content_publish'],
   'providers/{tenant_id}/meta')
ON CONFLICT (provider_name) WHERE tenant_id IS NULL DO NOTHING;

-- OpenAI — platform-level API key (not per-tenant, ADR-042 §1)
INSERT INTO business.provider_configs
  (tenant_id, provider_name, auth_method, mcp_server_url, scope_set, vault_path_key)
VALUES
  (NULL, 'openai', 'API_KEY', NULL,
   ARRAY[]::TEXT[],
   'providers/platform/openai')
ON CONFLICT (provider_name) WHERE tenant_id IS NULL DO NOTHING;
