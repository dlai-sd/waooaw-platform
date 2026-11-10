-- WC-134 R006/R008: owner-managed work capabilities, not unscoped transcript inventory.
BEGIN;
DO $membership$
BEGIN
    IF NOT pg_has_role(session_user, 'bp_owner', 'SET') THEN
        EXECUTE format('GRANT bp_owner TO %I', session_user);
        PERFORM set_config('waooaw.wc134_runtime_directory_granted', 'true', true);
    END IF;
END
$membership$;
CREATE TABLE IF NOT EXISTS business.conversation_runtime_work (
    execution_id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    environment TEXT NOT NULL,
    actor_id UUID NOT NULL,
    actor_issuer TEXT NOT NULL,
    membership_id UUID NOT NULL,
    account_id UUID NOT NULL,
    due_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    terminal BOOLEAN NOT NULL DEFAULT false,
    FOREIGN KEY (tenant_id, execution_id)
        REFERENCES business.conversation_executions(tenant_id, execution_id) ON DELETE CASCADE
);
ALTER TABLE business.conversation_runtime_work OWNER TO bp_owner;
ALTER TABLE business.conversation_runtime_work ENABLE ROW LEVEL SECURITY;
ALTER TABLE business.conversation_runtime_work FORCE ROW LEVEL SECURITY;
-- Only the owner routines can enumerate this minimal, verified SEND capability directory.
DROP POLICY IF EXISTS runtime_work_owner ON business.conversation_runtime_work;
CREATE POLICY runtime_work_owner ON business.conversation_runtime_work TO bp_owner
    USING (true) WITH CHECK (true);
REVOKE ALL ON business.conversation_runtime_work FROM PUBLIC, business_app;
CREATE INDEX IF NOT EXISTS runtime_work_due
    ON business.conversation_runtime_work(environment, due_at, execution_id) WHERE NOT terminal;

CREATE OR REPLACE FUNCTION business.sync_conversation_runtime_work()
RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER
SET search_path = pg_catalog SET row_security = on
AS $function$
DECLARE membership RECORD; environment_ref TEXT;
BEGIN
    IF TG_OP = 'UPDATE' AND
        (NEW.tenant_id, NEW.execution_id, NEW.message_id, NEW.relationship_id, NEW.conversation_id,
         NEW.origin_channel_binding_id, NEW.origin_recipient_digest,
         NEW.runtime_actor_id, NEW.runtime_actor_issuer, NEW.runtime_membership_id, NEW.runtime_account_id)
        IS DISTINCT FROM
        (OLD.tenant_id, OLD.execution_id, OLD.message_id, OLD.relationship_id, OLD.conversation_id,
         OLD.origin_channel_binding_id, OLD.origin_recipient_digest,
         OLD.runtime_actor_id, OLD.runtime_actor_issuer, OLD.runtime_membership_id, OLD.runtime_account_id) THEN
        RAISE EXCEPTION 'Runtime source authority is immutable' USING ERRCODE = '42501';
    END IF;
    IF NEW.runtime_actor_issuer IS NULL OR NEW.runtime_membership_id IS NULL
        OR NEW.runtime_account_id IS NULL OR NEW.runtime_actor_id IS NULL THEN
        RETURN NEW;
    END IF;
    IF TG_OP = 'INSERT' THEN
        SELECT * INTO membership FROM identity.lock_conversation_runtime_membership(
            NEW.runtime_actor_issuer, NEW.runtime_actor_id, NEW.tenant_id, NEW.runtime_membership_id);
        IF membership IS NULL OR membership.account_id <> NEW.runtime_account_id THEN
            RAISE EXCEPTION 'Runtime work requires current Identity admission' USING ERRCODE = '42501';
        END IF;
        SELECT environment INTO environment_ref FROM business.conversation_messages
            WHERE tenant_id = NEW.tenant_id AND message_id = NEW.message_id;
        IF environment_ref IS NULL THEN
            RAISE EXCEPTION 'Runtime work requires canonical input' USING ERRCODE = '23514';
        END IF;
        INSERT INTO business.conversation_runtime_work
            (execution_id, tenant_id, environment, actor_id, actor_issuer, membership_id, account_id,
             due_at, terminal)
        VALUES (NEW.execution_id, NEW.tenant_id, environment_ref, NEW.runtime_actor_id,
            NEW.runtime_actor_issuer, NEW.runtime_membership_id, NEW.runtime_account_id,
            coalesce(NEW.runtime_next_attempt_at, now()),
            NEW.runtime_terminal OR NEW.processing_state IN ('STOPPED', 'CANCELLED'))
        ON CONFLICT (execution_id) DO NOTHING;
    ELSE
        UPDATE business.conversation_runtime_work
        SET due_at = coalesce(NEW.runtime_next_attempt_at, now()),
            terminal = NEW.runtime_terminal OR NEW.processing_state IN ('STOPPED', 'CANCELLED')
        WHERE execution_id = NEW.execution_id AND tenant_id = NEW.tenant_id;
    END IF;
    RETURN NEW;
END
$function$;
ALTER FUNCTION business.sync_conversation_runtime_work() OWNER TO bp_owner;
REVOKE ALL ON FUNCTION business.sync_conversation_runtime_work() FROM PUBLIC;
DROP TRIGGER IF EXISTS conversation_runtime_work_sync ON business.conversation_executions;
CREATE CONSTRAINT TRIGGER conversation_runtime_work_sync
    AFTER INSERT OR UPDATE ON business.conversation_executions
    DEFERRABLE INITIALLY DEFERRED FOR EACH ROW
    EXECUTE FUNCTION business.sync_conversation_runtime_work();

CREATE OR REPLACE FUNCTION business.claim_conversation_runtime_work(p_environment TEXT)
RETURNS TABLE (execution_id UUID, tenant_id UUID, authorized BOOLEAN)
LANGUAGE plpgsql SECURITY DEFINER
SET search_path = pg_catalog SET row_security = on
AS $function$
DECLARE candidate RECORD; membership RECORD;
BEGIN
    IF p_environment IS NULL OR length(p_environment) NOT BETWEEN 1 AND 64 THEN
        RAISE EXCEPTION 'Runtime environment is invalid' USING ERRCODE = '22023';
    END IF;
    SELECT work.* INTO candidate FROM business.conversation_runtime_work AS work
        WHERE work.environment = p_environment AND NOT work.terminal AND work.due_at <= now()
        ORDER BY work.due_at, work.execution_id
        LIMIT 1 FOR UPDATE SKIP LOCKED;
    IF candidate IS NULL THEN RETURN; END IF;
    SELECT * INTO membership FROM identity.lock_conversation_runtime_membership(
        candidate.actor_issuer, candidate.actor_id, candidate.tenant_id, candidate.membership_id);
    UPDATE business.conversation_runtime_work AS work
        SET due_at = now() + interval '45 seconds'
        WHERE work.execution_id = candidate.execution_id;
    RETURN QUERY SELECT candidate.execution_id, candidate.tenant_id,
        coalesce(membership.account_id = candidate.account_id, false);
END
$function$;
ALTER FUNCTION business.claim_conversation_runtime_work(TEXT) OWNER TO bp_owner;
REVOKE ALL ON FUNCTION business.claim_conversation_runtime_work(TEXT) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION business.claim_conversation_runtime_work(TEXT) TO business_app;
DO $membership$
BEGIN
    IF current_setting('waooaw.wc134_runtime_directory_granted', true) = 'true' THEN
        EXECUTE format('REVOKE bp_owner FROM %I', session_user);
    END IF;
END
$membership$;
COMMIT;
