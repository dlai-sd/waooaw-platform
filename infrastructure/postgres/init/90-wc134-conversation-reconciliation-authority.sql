-- Implements: conversation-core.md section 4.2; WC-134 fresh-owner read-only recovery.
BEGIN;
DO $membership$
BEGIN
    IF NOT pg_has_role(session_user, 'bp_owner', 'SET') THEN
        EXECUTE format('GRANT bp_owner TO %I', session_user);
        PERFORM set_config('waooaw.wc134_reconciliation_granted_bp_owner', 'true', true);
    END IF;
END
$membership$;
ALTER TABLE business.conversation_executions
    ADD COLUMN IF NOT EXISTS projection_version BIGINT NOT NULL DEFAULT 0
        CHECK (projection_version >= 0);
GRANT UPDATE (projection_version) ON business.conversation_executions TO business_app;
CREATE TABLE IF NOT EXISTS business.conversation_reconciliation_authorities (
    authority_id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    relationship_id UUID NOT NULL,
    execution_id UUID NOT NULL,
    requester_id UUID NOT NULL,
    issuer TEXT NOT NULL,
    account_id UUID NOT NULL,
    membership_id UUID NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('OWNER', 'MANAGER')),
    decision_space_snapshot_id UUID NOT NULL,
    decision_space_version INTEGER NOT NULL CHECK (decision_space_version > 0),
    evidence_id UUID NOT NULL,
    source_digest TEXT NOT NULL CHECK (source_digest ~ '^sha256:[0-9a-f]{64}$'),
    idempotency_key UUID NOT NULL,
    request_digest TEXT NOT NULL CHECK (request_digest ~ '^sha256:[0-9a-f]{64}$'),
    expected_projection_version BIGINT NOT NULL CHECK (expected_projection_version >= 0),
    created_at TIMESTAMPTZ NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    original_request_digest TEXT CHECK (original_request_digest ~ '^sha256:[0-9a-f]{64}$'),
    result_digest TEXT CHECK (result_digest ~ '^sha256:[0-9a-f]{64}$'),
    response_json JSONB,
    CHECK (expires_at > created_at AND expires_at <= created_at + interval '5 minutes'),
    CHECK ((result_digest IS NULL AND original_request_digest IS NULL AND response_json IS NULL)
        OR (result_digest IS NOT NULL AND original_request_digest IS NOT NULL AND response_json IS NOT NULL)),
    UNIQUE (tenant_id, execution_id, requester_id, idempotency_key),
    FOREIGN KEY (tenant_id, execution_id)
        REFERENCES business.conversation_executions(tenant_id, execution_id) ON DELETE CASCADE
);
ALTER TABLE business.conversation_reconciliation_authorities OWNER TO bp_owner;
ALTER TABLE business.conversation_reconciliation_authorities ENABLE ROW LEVEL SECURITY;
ALTER TABLE business.conversation_reconciliation_authorities FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS reconciliation_authority_tenant ON business.conversation_reconciliation_authorities;
CREATE POLICY reconciliation_authority_tenant ON business.conversation_reconciliation_authorities
    USING (tenant_id = nullif(current_setting('app.current_tenant_id', true), '')::uuid)
    WITH CHECK (tenant_id = nullif(current_setting('app.current_tenant_id', true), '')::uuid);
GRANT SELECT, INSERT ON business.conversation_reconciliation_authorities TO business_app;
GRANT UPDATE (original_request_digest, result_digest, response_json)
    ON business.conversation_reconciliation_authorities TO business_app;
DO $membership$
BEGIN
    IF current_setting('waooaw.wc134_reconciliation_granted_bp_owner', true) = 'true' THEN
        EXECUTE format('REVOKE bp_owner FROM %I', session_user);
    END IF;
END
$membership$;
COMMIT;
