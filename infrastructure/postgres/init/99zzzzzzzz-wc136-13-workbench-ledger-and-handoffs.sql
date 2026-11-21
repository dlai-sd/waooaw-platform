-- Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C6-02, C6-03
-- Constitutional basis: C-005, C-023, C-026, C-059, C-063
-- WC-136: the workbench keeps every command receipt by tenant, relationship, participant and idempotency key, and
-- every web handoff by the hash of its token. Both live in the database so any replica answers a retry or a
-- redemption the same way. A handoff token itself is never stored; a redemption is a single atomic update.
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '30s';
SET LOCAL ROLE bp_owner;

CREATE TABLE IF NOT EXISTS business.workbench_command_ledger (
    tenant_id UUID NOT NULL,
    relationship_id UUID NOT NULL,
    participant_id UUID NOT NULL,
    idempotency_key UUID NOT NULL,
    request_digest CHAR(64) NOT NULL CHECK (request_digest ~ '^[a-f0-9]{64}$'),
    state TEXT NOT NULL CHECK (state IN ('IN_PROGRESS', 'COMPLETED')),
    result_json JSONB,
    created_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ,
    lease_expires_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (tenant_id, relationship_id, participant_id, idempotency_key),
    CONSTRAINT workbench_command_ledger_result_check
        CHECK ((state = 'COMPLETED') = (result_json IS NOT NULL))
);
ALTER TABLE business.workbench_command_ledger OWNER TO bp_owner;
CREATE INDEX IF NOT EXISTS workbench_command_ledger_retention_idx
    ON business.workbench_command_ledger (tenant_id, created_at);

CREATE TABLE IF NOT EXISTS business.workbench_handoffs (
    handoff_ref UUID PRIMARY KEY,
    token_hash CHAR(64) NOT NULL UNIQUE CHECK (token_hash ~ '^[a-f0-9]{64}$'),
    tenant_id UUID NOT NULL,
    relationship_id UUID NOT NULL,
    participant_id UUID NOT NULL,
    purpose TEXT NOT NULL CHECK (purpose IN ('WEB_WORKBENCH', 'APPROVAL', 'PAYMENT', 'EVIDENCE')),
    context_ref TEXT CHECK (context_ref IS NULL OR length(context_ref) BETWEEN 1 AND 128),
    created_at TIMESTAMPTZ NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    consumed_at TIMESTAMPTZ,
    CONSTRAINT workbench_handoffs_expiry_check CHECK (expires_at > created_at)
);
ALTER TABLE business.workbench_handoffs OWNER TO bp_owner;
CREATE INDEX IF NOT EXISTS workbench_handoffs_retention_idx
    ON business.workbench_handoffs (tenant_id, expires_at);

CREATE OR REPLACE FUNCTION business.guard_workbench_command_ledger()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $guard$
BEGIN
    IF TG_OP = 'DELETE' THEN
        IF OLD.state = 'IN_PROGRESS' OR OLD.created_at < now() - INTERVAL '24 hours' THEN
            RETURN OLD;
        END IF;
        RAISE EXCEPTION 'a completed workbench command receipt is kept for 24 hours';
    END IF;
    IF NEW.tenant_id IS DISTINCT FROM OLD.tenant_id
        OR NEW.relationship_id IS DISTINCT FROM OLD.relationship_id
        OR NEW.participant_id IS DISTINCT FROM OLD.participant_id
        OR NEW.idempotency_key IS DISTINCT FROM OLD.idempotency_key
        OR NEW.request_digest IS DISTINCT FROM OLD.request_digest
        OR NEW.created_at IS DISTINCT FROM OLD.created_at THEN
        RAISE EXCEPTION 'workbench command ledger identity is immutable';
    END IF;
    IF OLD.state = 'COMPLETED' THEN
        RAISE EXCEPTION 'a completed workbench command receipt is immutable';
    END IF;
    RETURN NEW;
END
$guard$;

CREATE OR REPLACE TRIGGER workbench_command_ledger_guard
BEFORE UPDATE OR DELETE ON business.workbench_command_ledger
FOR EACH ROW EXECUTE FUNCTION business.guard_workbench_command_ledger();

CREATE OR REPLACE FUNCTION business.guard_workbench_handoffs()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $guard$
BEGIN
    IF TG_OP = 'DELETE' THEN
        IF OLD.expires_at < now() - INTERVAL '1 hour' THEN
            RETURN OLD;
        END IF;
        RAISE EXCEPTION 'a workbench handoff is kept until an hour after it expires';
    END IF;
    IF NEW.handoff_ref IS DISTINCT FROM OLD.handoff_ref
        OR NEW.token_hash IS DISTINCT FROM OLD.token_hash
        OR NEW.tenant_id IS DISTINCT FROM OLD.tenant_id
        OR NEW.relationship_id IS DISTINCT FROM OLD.relationship_id
        OR NEW.participant_id IS DISTINCT FROM OLD.participant_id
        OR NEW.purpose IS DISTINCT FROM OLD.purpose
        OR NEW.context_ref IS DISTINCT FROM OLD.context_ref
        OR NEW.created_at IS DISTINCT FROM OLD.created_at
        OR NEW.expires_at IS DISTINCT FROM OLD.expires_at THEN
        RAISE EXCEPTION 'workbench handoff identity is immutable';
    END IF;
    IF OLD.consumed_at IS NOT NULL THEN
        RAISE EXCEPTION 'a workbench handoff is single use';
    END IF;
    RETURN NEW;
END
$guard$;

CREATE OR REPLACE TRIGGER workbench_handoffs_guard
BEFORE UPDATE OR DELETE ON business.workbench_handoffs
FOR EACH ROW EXECUTE FUNCTION business.guard_workbench_handoffs();

ALTER TABLE business.workbench_command_ledger ENABLE ROW LEVEL SECURITY;
ALTER TABLE business.workbench_command_ledger FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS workbench_command_ledger_tenant_isolation ON business.workbench_command_ledger;
CREATE POLICY workbench_command_ledger_tenant_isolation ON business.workbench_command_ledger
    USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', TRUE), '')::UUID)
    WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', TRUE), '')::UUID);

ALTER TABLE business.workbench_handoffs ENABLE ROW LEVEL SECURITY;
ALTER TABLE business.workbench_handoffs FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS workbench_handoffs_tenant_isolation ON business.workbench_handoffs;
CREATE POLICY workbench_handoffs_tenant_isolation ON business.workbench_handoffs
    USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', TRUE), '')::UUID)
    WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', TRUE), '')::UUID);

REVOKE ALL ON business.workbench_command_ledger FROM PUBLIC, business_app;
GRANT SELECT, INSERT, DELETE ON business.workbench_command_ledger TO business_app;
GRANT UPDATE (state, result_json, completed_at, lease_expires_at)
    ON business.workbench_command_ledger TO business_app;

REVOKE ALL ON business.workbench_handoffs FROM PUBLIC, business_app;
GRANT SELECT, INSERT, DELETE ON business.workbench_handoffs TO business_app;
GRANT UPDATE (consumed_at) ON business.workbench_handoffs TO business_app;

COMMIT;
