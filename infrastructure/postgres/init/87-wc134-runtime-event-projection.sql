-- WC-134 R006/R007: atomically checkpoint runtime projection without duplicating transcript payloads.
BEGIN;
DO $membership$
BEGIN
    IF NOT pg_has_role(session_user, 'bp_owner', 'SET') THEN
        EXECUTE format('GRANT bp_owner TO %I', session_user);
        PERFORM set_config('waooaw.wc134_runtime_granted_bp_owner', 'true', true);
    END IF;
END
$membership$;

ALTER TABLE business.conversation_executions
    ADD COLUMN IF NOT EXISTS runtime_sequence BIGINT NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS runtime_reply_message_id UUID,
    ADD COLUMN IF NOT EXISTS runtime_next_attempt_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS runtime_terminal BOOLEAN NOT NULL DEFAULT false,
    ADD COLUMN IF NOT EXISTS origin_channel_binding_id UUID,
    ADD COLUMN IF NOT EXISTS origin_recipient_digest CHAR(64);
DO $constraints$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint
        WHERE conrelid = 'business.conversation_executions'::regclass
            AND conname = 'conversation_runtime_source_valid') THEN
        ALTER TABLE business.conversation_executions
            ADD CONSTRAINT conversation_runtime_source_valid CHECK (
                runtime_sequence >= 0
                AND ((origin_channel_binding_id IS NULL AND origin_recipient_digest IS NULL)
                    OR (origin_channel_binding_id IS NOT NULL AND origin_recipient_digest IS NOT NULL
                        AND origin_recipient_digest ~ '^[0-9a-f]{64}$')));
    END IF;
END
$constraints$;
CREATE UNIQUE INDEX IF NOT EXISTS conversation_execution_tenant_identity
    ON business.conversation_executions(tenant_id, execution_id);
CREATE TABLE IF NOT EXISTS business.conversation_runtime_event_receipts (
    tenant_id UUID NOT NULL,
    execution_id UUID NOT NULL,
    sequence BIGINT NOT NULL CHECK (sequence > 0),
    event_digest CHAR(64) NOT NULL CHECK (event_digest ~ '^[0-9a-f]{64}$'),
    recorded_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (tenant_id, execution_id, sequence),
    CONSTRAINT runtime_event_receipts_execution_scope_fk FOREIGN KEY (tenant_id, execution_id)
        REFERENCES business.conversation_executions(tenant_id, execution_id) ON DELETE CASCADE
);
ALTER TABLE business.conversation_runtime_event_receipts
    DROP CONSTRAINT IF EXISTS conversation_runtime_event_receipts_execution_id_fkey;
DO $constraints$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint
        WHERE conrelid = 'business.conversation_runtime_event_receipts'::regclass
            AND conname = 'runtime_event_receipts_execution_scope_fk') THEN
        ALTER TABLE business.conversation_runtime_event_receipts
            ADD CONSTRAINT runtime_event_receipts_execution_scope_fk FOREIGN KEY (tenant_id, execution_id)
                REFERENCES business.conversation_executions(tenant_id, execution_id) ON DELETE CASCADE;
    END IF;
END
$constraints$;
ALTER TABLE business.conversation_runtime_event_receipts OWNER TO bp_owner;
ALTER TABLE business.conversation_runtime_event_receipts ENABLE ROW LEVEL SECURITY;
ALTER TABLE business.conversation_runtime_event_receipts FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS runtime_event_receipts_tenant ON business.conversation_runtime_event_receipts;
CREATE POLICY runtime_event_receipts_tenant ON business.conversation_runtime_event_receipts
    USING (tenant_id = nullif(current_setting('app.current_tenant_id', true), '')::uuid)
    WITH CHECK (tenant_id = nullif(current_setting('app.current_tenant_id', true), '')::uuid);
GRANT SELECT, INSERT ON business.conversation_runtime_event_receipts TO business_app;
GRANT UPDATE (runtime_sequence, runtime_reply_message_id, runtime_next_attempt_at, runtime_terminal)
    ON business.conversation_executions TO business_app;
GRANT USAGE ON SCHEMA ai_runtime, constitutional TO business_app;
GRANT EXECUTE ON FUNCTION ai_runtime.lock_employment_dispatch(UUID, TEXT),
    ai_runtime.employment_dispatch_relationship_key(TEXT) TO business_app;
GRANT SELECT ON constitutional.employment_dispatch_stops TO business_app;
CREATE INDEX IF NOT EXISTS conversation_runtime_recovery_due
    ON business.conversation_executions(tenant_id, runtime_next_attempt_at, created_at)
    WHERE NOT runtime_terminal;
DO $membership$
BEGIN
    IF current_setting('waooaw.wc134_runtime_granted_bp_owner', true) = 'true' THEN
        EXECUTE format('REVOKE bp_owner FROM %I', session_user);
    END IF;
END
$membership$;
COMMIT;
