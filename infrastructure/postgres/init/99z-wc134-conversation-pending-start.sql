-- WC-134: tenant-scoped canonical sources awaiting conversation start.
BEGIN;
DO $membership$
BEGIN
    IF NOT pg_has_role(session_user, 'bp_owner', 'SET') THEN
        EXECUTE format('GRANT bp_owner TO %I', session_user);
        PERFORM set_config('waooaw.wc134_pending_start_granted', 'true', true);
    END IF;
END
$membership$;

CREATE UNIQUE INDEX IF NOT EXISTS conversation_pending_message_source_key
ON business.conversation_messages (tenant_id, relationship_id, conversation_id, message_id, evidence_record_id);
CREATE UNIQUE INDEX IF NOT EXISTS conversation_pending_execution_source_key
ON business.conversation_executions (tenant_id, relationship_id, conversation_id, message_id, execution_id);
CREATE UNIQUE INDEX IF NOT EXISTS conversation_pending_mandate_source_key
ON business.operational_mandate_snapshots
(tenant_id, relationship_id, actor_participant_id, idempotency_identity, constitutional_evidence_id, mandate_id);
CREATE UNIQUE INDEX IF NOT EXISTS conversation_pending_send_source_key
ON business.conversation_idempotency_outcomes
(tenant_id, relationship_id, actor_participant_id, operation_family, idempotency_key, message_id, execution_id);

CREATE TABLE IF NOT EXISTS business.conversation_pending_starts (
    tenant_id UUID NOT NULL,
    relationship_id UUID NOT NULL,
    conversation_id UUID NOT NULL,
    message_id UUID NOT NULL,
    execution_id UUID NOT NULL,
    actor_id UUID NOT NULL,
    operation_family TEXT NOT NULL DEFAULT 'SEND' CHECK (operation_family = 'SEND'),
    idempotency_key UUID NOT NULL,
    evidence_id UUID NOT NULL,
    mandate_id UUID NOT NULL,
    admitted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    due_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (tenant_id, message_id),
    UNIQUE (tenant_id, execution_id),
    UNIQUE (tenant_id, relationship_id, conversation_id, message_id),
    UNIQUE (tenant_id, relationship_id, actor_id, idempotency_key),
    CHECK (due_at > admitted_at),
    FOREIGN KEY (tenant_id, relationship_id, conversation_id, message_id, evidence_id)
    REFERENCES business.conversation_messages
    (tenant_id, relationship_id, conversation_id, message_id, evidence_record_id),
    FOREIGN KEY (tenant_id, relationship_id, conversation_id, message_id, execution_id)
    REFERENCES business.conversation_executions
    (tenant_id, relationship_id, conversation_id, message_id, execution_id),
    FOREIGN KEY (tenant_id, relationship_id, actor_id, idempotency_key, evidence_id, mandate_id)
    REFERENCES business.operational_mandate_snapshots
    (tenant_id, relationship_id, actor_participant_id, idempotency_identity, constitutional_evidence_id, mandate_id),
    FOREIGN KEY (tenant_id, relationship_id, actor_id, operation_family, idempotency_key, message_id, execution_id)
    REFERENCES business.conversation_idempotency_outcomes
    (tenant_id, relationship_id, actor_participant_id, operation_family, idempotency_key, message_id, execution_id)
);
ALTER TABLE business.conversation_pending_starts OWNER TO bp_owner;
ALTER TABLE business.conversation_pending_starts ENABLE ROW LEVEL SECURITY;
ALTER TABLE business.conversation_pending_starts FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS conversation_pending_starts_tenant ON business.conversation_pending_starts;
CREATE POLICY conversation_pending_starts_tenant ON business.conversation_pending_starts
USING (tenant_id = nullif(current_setting('app.current_tenant_id', TRUE), '')::UUID)
WITH CHECK (tenant_id = nullif(current_setting('app.current_tenant_id', TRUE), '')::UUID);
REVOKE ALL ON business.conversation_pending_starts FROM public, business_app;
GRANT SELECT, INSERT ON business.conversation_pending_starts TO business_app;
CREATE INDEX IF NOT EXISTS conversation_pending_starts_due
ON business.conversation_pending_starts (tenant_id, conversation_id, due_at, message_id);

CREATE TABLE IF NOT EXISTS business.conversation_batch_groups (
    tenant_id UUID NOT NULL,
    relationship_id UUID NOT NULL,
    conversation_id UUID NOT NULL,
    batch_id UUID NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT statement_timestamp(),
    frozen_at TIMESTAMPTZ,
    member_count INTEGER,
    CHECK (
        (frozen_at IS NULL AND member_count IS NULL)
        OR (frozen_at IS NOT NULL AND member_count IS NOT NULL AND member_count > 0)
    ),
    PRIMARY KEY (tenant_id, batch_id),
    UNIQUE (tenant_id, relationship_id, conversation_id, batch_id)
);
ALTER TABLE business.conversation_batch_groups OWNER TO bp_owner;
ALTER TABLE business.conversation_batch_groups ENABLE ROW LEVEL SECURITY;
ALTER TABLE business.conversation_batch_groups FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS conversation_batch_groups_tenant ON business.conversation_batch_groups;
CREATE POLICY conversation_batch_groups_tenant ON business.conversation_batch_groups
USING (tenant_id = nullif(current_setting('app.current_tenant_id', TRUE), '')::UUID)
WITH CHECK (tenant_id = nullif(current_setting('app.current_tenant_id', TRUE), '')::UUID);
REVOKE ALL ON business.conversation_batch_groups FROM public, business_app;
GRANT SELECT ON business.conversation_batch_groups TO business_app;
GRANT INSERT (tenant_id, relationship_id, conversation_id, batch_id)
ON business.conversation_batch_groups TO business_app;
GRANT UPDATE (frozen_at, member_count) ON business.conversation_batch_groups TO business_app;

CREATE TABLE IF NOT EXISTS business.conversation_batch_members (
    tenant_id UUID NOT NULL,
    relationship_id UUID NOT NULL,
    conversation_id UUID NOT NULL,
    batch_id UUID NOT NULL,
    message_id UUID NOT NULL,
    ordinal INTEGER NOT NULL CHECK (ordinal > 0),
    PRIMARY KEY (tenant_id, batch_id, ordinal),
    UNIQUE (tenant_id, message_id),
    FOREIGN KEY (tenant_id, relationship_id, conversation_id, batch_id)
    REFERENCES business.conversation_batch_groups (tenant_id, relationship_id, conversation_id, batch_id),
    FOREIGN KEY (tenant_id, relationship_id, conversation_id, message_id)
    REFERENCES business.conversation_pending_starts (tenant_id, relationship_id, conversation_id, message_id)
);
ALTER TABLE business.conversation_batch_members OWNER TO bp_owner;
ALTER TABLE business.conversation_batch_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE business.conversation_batch_members FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS conversation_batch_members_tenant ON business.conversation_batch_members;
CREATE POLICY conversation_batch_members_tenant ON business.conversation_batch_members
USING (tenant_id = nullif(current_setting('app.current_tenant_id', TRUE), '')::UUID)
WITH CHECK (tenant_id = nullif(current_setting('app.current_tenant_id', TRUE), '')::UUID);
REVOKE ALL ON business.conversation_batch_members FROM public, business_app;
GRANT SELECT, INSERT ON business.conversation_batch_members TO business_app;

CREATE OR REPLACE FUNCTION business.guard_conversation_batch_member()
RETURNS TRIGGER LANGUAGE plpgsql SET search_path = pg_catalog SET row_security = on
AS $function$
DECLARE frozen TIMESTAMPTZ;
BEGIN
    SELECT g.frozen_at INTO frozen
    FROM business.conversation_batch_groups AS g
    WHERE g.tenant_id = NEW.tenant_id
        AND g.relationship_id = NEW.relationship_id
        AND g.conversation_id = NEW.conversation_id
        AND g.batch_id = NEW.batch_id
    FOR UPDATE;
    IF NOT FOUND OR frozen IS NOT NULL THEN
        RAISE EXCEPTION 'Batch membership is unavailable or frozen' USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END
$function$;
DROP TRIGGER IF EXISTS conversation_batch_member_guard ON business.conversation_batch_members;
CREATE TRIGGER conversation_batch_member_guard BEFORE INSERT ON business.conversation_batch_members
FOR EACH ROW EXECUTE FUNCTION business.guard_conversation_batch_member();

CREATE OR REPLACE FUNCTION business.guard_conversation_batch_freeze()
RETURNS TRIGGER LANGUAGE plpgsql SET search_path = pg_catalog SET row_security = on
AS $function$
DECLARE actual_count BIGINT; lowest INTEGER; highest INTEGER; first_offset BIGINT; last_offset BIGINT;
BEGIN
    IF OLD.frozen_at IS NOT NULL OR NEW.frozen_at IS NULL OR NEW.member_count IS NULL THEN
        RAISE EXCEPTION 'Batch freeze cannot be reversed or changed' USING ERRCODE = '23514';
    END IF;
    SELECT count(*), min(m.ordinal), max(m.ordinal),
        min(c.sequence - m.ordinal), max(c.sequence - m.ordinal)
    INTO actual_count, lowest, highest, first_offset, last_offset
    FROM business.conversation_batch_members AS m
    JOIN business.conversation_messages AS c
        ON c.tenant_id = m.tenant_id AND c.message_id = m.message_id
    WHERE m.tenant_id = NEW.tenant_id AND m.batch_id = NEW.batch_id;
    IF actual_count <> NEW.member_count OR lowest <> 1 OR highest <> NEW.member_count
        OR first_offset <> last_offset THEN
        RAISE EXCEPTION 'Batch membership must be complete and contiguous' USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END
$function$;
DROP TRIGGER IF EXISTS conversation_batch_freeze_guard ON business.conversation_batch_groups;
CREATE TRIGGER conversation_batch_freeze_guard BEFORE UPDATE ON business.conversation_batch_groups
FOR EACH ROW EXECUTE FUNCTION business.guard_conversation_batch_freeze();

CREATE OR REPLACE FUNCTION business.require_conversation_batch_frozen()
RETURNS TRIGGER LANGUAGE plpgsql SET search_path = pg_catalog SET row_security = on
AS $function$
DECLARE frozen TIMESTAMPTZ;
BEGIN
    SELECT g.frozen_at INTO frozen
    FROM business.conversation_batch_groups AS g
    WHERE g.tenant_id = NEW.tenant_id AND g.batch_id = NEW.batch_id;
    IF NOT FOUND OR frozen IS NULL THEN
        RAISE EXCEPTION 'Batch creation requires an atomic freeze' USING ERRCODE = '23514';
    END IF;
    RETURN NULL;
END
$function$;
DROP TRIGGER IF EXISTS conversation_batch_requires_freeze ON business.conversation_batch_groups;
CREATE CONSTRAINT TRIGGER conversation_batch_requires_freeze
AFTER INSERT OR UPDATE ON business.conversation_batch_groups
DEFERRABLE INITIALLY DEFERRED FOR EACH ROW
EXECUTE FUNCTION business.require_conversation_batch_frozen();

DO $membership$
BEGIN
    IF current_setting('waooaw.wc134_pending_start_granted', true) = 'true' THEN
        EXECUTE format('REVOKE bp_owner FROM %I', session_user);
    END IF;
END
$membership$;
COMMIT;
