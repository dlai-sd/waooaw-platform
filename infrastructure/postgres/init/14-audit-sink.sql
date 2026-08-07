-- 14-audit-sink.sql
-- Constitutional Audit Trail Sink — WORM evidence_records schema.
-- Implements: adr/ADR-044-constitutional-audit-trail-sink.md §2
-- constitutional_basis: C-059 (Traceability), C-078 (DPDPA), ADR-044

-- ─── Audit Sink Schema ───────────────────────────────────────────────────────

CREATE SCHEMA IF NOT EXISTS audit_sink;

CREATE TABLE IF NOT EXISTS audit_sink.evidence_records (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  decision_id         VARCHAR(64) NOT NULL UNIQUE,
  tenant_id           UUID NOT NULL,
  agent_id            VARCHAR(64) NOT NULL,
  agent_instance_id   VARCHAR(64) NOT NULL,
  action_type         VARCHAR(64) NOT NULL,
  tool_name           VARCHAR(128),
  args_hash           VARCHAR(128),
  payload_ref_id      UUID,
  credential_provider VARCHAR(64),
  vault_alias         VARCHAR(128),
  execution_status    VARCHAR(32) NOT NULL,
  constitutional_basis TEXT[] NOT NULL DEFAULT '{}',
  evidence_hash       VARCHAR(128) NOT NULL,
  recorded_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
  erasure_status      VARCHAR(32) NOT NULL DEFAULT 'NONE',
  erasure_timestamp   TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_audit_sink_tenant ON audit_sink.evidence_records (tenant_id);
CREATE INDEX IF NOT EXISTS idx_audit_sink_recorded_at ON audit_sink.evidence_records (recorded_at);

-- WORM: INSERT-only RLS — no UPDATE or DELETE policy for ce_service_role
-- Structural prohibition: absence of UPDATE/DELETE policy = those operations blocked.
ALTER TABLE audit_sink.evidence_records ENABLE ROW LEVEL SECURITY;

-- Only ce_service_role may insert; no policy grants UPDATE or DELETE.
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_roles WHERE rolname = 'ce_service_role'
  ) THEN
    CREATE ROLE ce_service_role;
  END IF;
END $$;

CREATE POLICY evidence_insert_only ON audit_sink.evidence_records
  FOR INSERT TO ce_service_role
  WITH CHECK (true);

GRANT USAGE ON SCHEMA audit_sink TO ce_service_role;
GRANT INSERT, SELECT ON audit_sink.evidence_records TO ce_service_role;
-- No UPDATE or DELETE granted — structural WORM enforcement.
