-- 15-payload-store.sql
-- Operational Payload Store — erasable customer data store.
-- Implements: adr/ADR-044-constitutional-audit-trail-sink.md §3
-- constitutional_basis: C-059 (Traceability), C-078 (DPDPA Right-to-Erasure), ADR-044

-- ─── Payload Store Schema ─────────────────────────────────────────────────────

CREATE SCHEMA IF NOT EXISTS payload_store;

CREATE TABLE IF NOT EXISTS payload_store.operational_payloads (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  payload_ref_id      UUID NOT NULL UNIQUE,
  tenant_id           UUID NOT NULL,
  agent_instance_id   VARCHAR(64) NOT NULL,
  action_type         VARCHAR(64) NOT NULL,
  payload_json        JSONB,
  payload_blob_ref    VARCHAR(512),
  pii_present         BOOLEAN NOT NULL DEFAULT false,
  created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
  erased_at           TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_payloads_agent_instance ON payload_store.operational_payloads (agent_instance_id);
CREATE INDEX IF NOT EXISTS idx_payloads_tenant ON payload_store.operational_payloads (tenant_id);
