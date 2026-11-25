-- Implements: work-contracts/WC-170-real-agent-work-end-to-end.md WC170-R005, WC170-R006, WC170-R007, WC170-R008
-- Constitutional basis: C-005, C-023, C-026, C-059, C-063
-- WC-170: one append-only record store for the real-work projections (locked artifacts, customer decisions, the
-- execution timeline and outcome claims). A lock, a supersession, a decision and a reconciled outcome are each a new
-- row; nothing is updated or deleted, so no history is rewritten. Every row carries tenant and relationship ids and is
-- isolated by forced row-level security, the same way the workbench ledgers are.
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '30s';
SET LOCAL ROLE bp_owner;

CREATE TABLE IF NOT EXISTS business.real_work_records (
    tenant_id UUID NOT NULL,
    relationship_id UUID NOT NULL,
    sequence BIGINT NOT NULL CHECK (sequence >= 1),
    kind TEXT NOT NULL CHECK (kind IN (
        'ARTIFACT', 'ARTIFACT_SUBMITTED', 'ARTIFACT_LOCKED', 'ARTIFACT_SUPERSEDED', 'DECISION', 'TIMELINE', 'CLAIM')),
    record_id UUID NOT NULL,
    idempotency_key TEXT NOT NULL CHECK (length(idempotency_key) BETWEEN 1 AND 200),
    payload_digest CHAR(64) NOT NULL CHECK (payload_digest ~ '^[0-9a-f]{64}$'),
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (tenant_id, relationship_id, sequence),
    UNIQUE (tenant_id, relationship_id, kind, idempotency_key),
    UNIQUE (tenant_id, record_id)
);
ALTER TABLE business.real_work_records OWNER TO bp_owner;

CREATE OR REPLACE FUNCTION business.guard_real_work_records()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $guard$
BEGIN
    RAISE EXCEPTION 'real work records are append-only';
END
$guard$;

CREATE OR REPLACE TRIGGER real_work_records_guard
BEFORE UPDATE OR DELETE ON business.real_work_records
FOR EACH ROW EXECUTE FUNCTION business.guard_real_work_records();

ALTER TABLE business.real_work_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE business.real_work_records FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS real_work_records_tenant_isolation ON business.real_work_records;
CREATE POLICY real_work_records_tenant_isolation ON business.real_work_records
    USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', TRUE), '')::UUID)
    WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', TRUE), '')::UUID);

REVOKE ALL ON business.real_work_records FROM PUBLIC, business_app;
GRANT SELECT, INSERT ON business.real_work_records TO business_app;

COMMIT;
