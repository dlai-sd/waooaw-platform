-- 11-platform-registry.sql
-- Implements: architecture/reference/platform-component-registry.yaml
-- Constitutional: C-095 (Component Manifest Obligation), ADR-035 (PAC Standard), ADR-036 (EA Skeleton Standard)
-- Purpose: persist signal schema versions + runtime platform component registry

-- --------------------------------------------------------------------------
-- Table: institutional.platform_signal_schemas
-- Machine-readable record of every signal schema version ever released.
-- Gap Scanner and Blueprint Assurance compare against this at scan time.
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS institutional.platform_signal_schemas (
    id               BIGSERIAL PRIMARY KEY,
    signal_name      TEXT        NOT NULL,
    component_id     TEXT        NOT NULL,
    schema_version   TEXT        NOT NULL,
    json_schema      JSONB       NOT NULL,
    released_date    DATE        NOT NULL,
    deprecation_date DATE,
    is_latest        BOOLEAN     NOT NULL DEFAULT TRUE,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_signal_version UNIQUE (signal_name, schema_version),
    CONSTRAINT chk_schema_version CHECK (schema_version ~ '^\d+\.\d+$')
);

-- Append-only guard: signal schemas are immutable records of history.
CREATE OR REPLACE RULE no_update_signal_schemas AS
    ON UPDATE TO institutional.platform_signal_schemas
    DO INSTEAD NOTHING;

-- --------------------------------------------------------------------------
-- Table: institutional.platform_components
-- Runtime registry mirror of platform-component-registry.yaml.
-- Enables Steward and Gap Scanner to query platform state without YAML reads.
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS institutional.platform_components (
    id                BIGSERIAL   PRIMARY KEY,
    component_id      TEXT        NOT NULL UNIQUE,
    display_name      TEXT        NOT NULL,
    language          TEXT        NOT NULL CHECK (language IN ('python', 'dotnet')),
    status            TEXT        NOT NULL CHECK (status IN ('LIVE', 'SPEC_APPROVED', 'ARCHIVED')),
    skeleton_path     TEXT,
    manifest_path     TEXT,
    emits_signals     BOOLEAN     NOT NULL DEFAULT FALSE,
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- --------------------------------------------------------------------------
-- Seed: WBE signal channels at v1.0 (ADR-035, wbe-signal-schema.yaml)
-- --------------------------------------------------------------------------
INSERT INTO institutional.platform_signal_schemas
    (signal_name, component_id, schema_version, json_schema, released_date, is_latest)
VALUES
    ('bucket-at-50pct', 'billing-engine', '1.0',
     '{"type":"object","required":["tenant_id","agent_id","balance_pct","balance_units","currency","signal_ts"],"properties":{"tenant_id":{"type":"string"},"agent_id":{"type":"string"},"balance_pct":{"type":"number"},"balance_units":{"type":"integer"},"currency":{"type":"string"},"signal_ts":{"type":"string","format":"date-time"}}}',
     '2026-07-30', TRUE),

    ('bucket-at-60pct', 'billing-engine', '1.0',
     '{"type":"object","required":["tenant_id","agent_id","balance_pct","balance_units","currency","signal_ts"],"properties":{"tenant_id":{"type":"string"},"agent_id":{"type":"string"},"balance_pct":{"type":"number"},"balance_units":{"type":"integer"},"currency":{"type":"string"},"signal_ts":{"type":"string","format":"date-time"}}}',
     '2026-07-30', TRUE),

    ('bucket-at-85pct', 'billing-engine', '1.0',
     '{"type":"object","required":["tenant_id","agent_id","balance_pct","balance_units","currency","signal_ts"],"properties":{"tenant_id":{"type":"string"},"agent_id":{"type":"string"},"balance_pct":{"type":"number"},"balance_units":{"type":"integer"},"currency":{"type":"string"},"signal_ts":{"type":"string","format":"date-time"}}}',
     '2026-07-30', TRUE),

    ('bucket-empty', 'billing-engine', '1.0',
     '{"type":"object","required":["tenant_id","agent_id","balance_units","suspended_at","signal_ts"],"properties":{"tenant_id":{"type":"string"},"agent_id":{"type":"string"},"balance_units":{"type":"integer"},"suspended_at":{"type":"string","format":"date-time"},"signal_ts":{"type":"string","format":"date-time"}}}',
     '2026-07-30', TRUE),

    ('topup-applied', 'billing-engine', '1.0',
     '{"type":"object","required":["tenant_id","agent_id","amount","currency","new_balance_units","signal_ts"],"properties":{"tenant_id":{"type":"string"},"agent_id":{"type":"string"},"amount":{"type":"number"},"currency":{"type":"string"},"new_balance_units":{"type":"integer"},"signal_ts":{"type":"string","format":"date-time"}}}',
     '2026-07-30', TRUE),

    ('subscription-renewed', 'billing-engine', '1.0',
     '{"type":"object","required":["tenant_id","plan_id","renewed_at","next_renewal_at","signal_ts"],"properties":{"tenant_id":{"type":"string"},"plan_id":{"type":"string"},"renewed_at":{"type":"string","format":"date-time"},"next_renewal_at":{"type":"string","format":"date-time"},"signal_ts":{"type":"string","format":"date-time"}}}',
     '2026-07-30', TRUE)
ON CONFLICT (signal_name, schema_version) DO NOTHING;

-- --------------------------------------------------------------------------
-- Seed: platform component registry (mirrors platform-component-registry.yaml)
-- --------------------------------------------------------------------------
INSERT INTO institutional.platform_components
    (component_id, display_name, language, status, skeleton_path, manifest_path, emits_signals)
VALUES
    ('constitutional-engine', 'Constitutional Engine', 'dotnet', 'LIVE',
     'src/constitutional-engine/skeleton',
     'architecture/reference/components/manifest/ce.yaml', FALSE),

    ('business-platform', 'Business Platform', 'dotnet', 'LIVE',
     'src/business-platform/skeleton',
     'architecture/reference/components/manifest/bp.yaml', FALSE),

    ('professional-runtime', 'Professional Runtime', 'python', 'LIVE',
     'src/professional-runtime/skeleton',
     'architecture/reference/components/manifest/pr.yaml', FALSE),

    ('ai-runtime', 'AI Runtime', 'python', 'LIVE',
     'src/ai-runtime/skeleton',
     'architecture/reference/components/manifest/air.yaml', FALSE),

    ('billing-engine', 'Wallet & Billing Engine (WBE)', 'python', 'SPEC_APPROVED',
     'src/billing-engine/skeleton',
     'architecture/reference/components/manifest/wbe.yaml', TRUE)
ON CONFLICT (component_id) DO UPDATE SET
    status       = EXCLUDED.status,
    emits_signals= EXCLUDED.emits_signals,
    updated_at   = NOW();

-- --------------------------------------------------------------------------
-- Index: fast lookup by component and by is_latest
-- --------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_signal_schemas_component
    ON institutional.platform_signal_schemas (component_id, is_latest);

CREATE INDEX IF NOT EXISTS idx_platform_components_status
    ON institutional.platform_components (status);
