-- WC-134 R002/R007: minimal owner-indexed customer outbox discovery, not dispatch authority.
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '30s';
DO $membership$
BEGIN
    IF NOT pg_has_role(session_user, 'bp_owner', 'SET') THEN
        EXECUTE format('GRANT bp_owner TO %I', session_user);
        PERFORM set_config('waooaw.wc134_outbox_granted_bp_owner', 'true', true);
    END IF;
END
$membership$;

CREATE TABLE IF NOT EXISTS business.whatsapp_outbox_work (
    outbox_id UUID PRIMARY KEY REFERENCES business.conversation_outbox(outbox_id),
    service_tenant_id UUID NOT NULL,
    tenant_id UUID NOT NULL,
    environment TEXT NOT NULL,
    sender_hash CHAR(64) NOT NULL CHECK (sender_hash ~ '^[0-9a-f]{64}$'),
    binding_id UUID NOT NULL,
    due_at TIMESTAMPTZ NOT NULL,
    terminal BOOLEAN NOT NULL,
    FOREIGN KEY (tenant_id, binding_id)
        REFERENCES business.channel_bindings(tenant_id, binding_id)
);
ALTER TABLE business.whatsapp_outbox_work OWNER TO bp_owner;
ALTER TABLE business.whatsapp_outbox_work ENABLE ROW LEVEL SECURITY;
ALTER TABLE business.whatsapp_outbox_work FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS whatsapp_outbox_work_owner ON business.whatsapp_outbox_work;
CREATE POLICY whatsapp_outbox_work_owner ON business.whatsapp_outbox_work TO bp_owner
    USING (true) WITH CHECK (true);
REVOKE ALL ON business.whatsapp_outbox_work FROM PUBLIC, business_app;
CREATE INDEX IF NOT EXISTS whatsapp_outbox_work_due
    ON business.whatsapp_outbox_work(service_tenant_id, environment, due_at, outbox_id)
    WHERE NOT terminal;

CREATE OR REPLACE FUNCTION business.sync_whatsapp_outbox_work()
RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER
SET search_path = pg_catalog SET row_security = on
AS $function$
DECLARE route RECORD; binding RECORD; existing RECORD;
BEGIN
    SELECT * INTO existing FROM business.whatsapp_outbox_work WHERE outbox_id = NEW.outbox_id;
    IF existing IS NOT NULL AND TG_OP = 'UPDATE' THEN
        IF (NEW.outbox_id, NEW.tenant_id, NEW.environment, NEW.relationship_id,
            NEW.conversation_id, NEW.portal_context_id, NEW.recipient_binding_digest,
            NEW.aggregate_id, NEW.sequence, NEW.payload_digest, NEW.payload_reference,
            NEW.idempotency_key, NEW.operation_family, NEW.owner, NEW.purpose)
            IS DISTINCT FROM
            (OLD.outbox_id, OLD.tenant_id, OLD.environment, OLD.relationship_id,
            OLD.conversation_id, OLD.portal_context_id, OLD.recipient_binding_digest,
            OLD.aggregate_id, OLD.sequence, OLD.payload_digest, OLD.payload_reference,
            OLD.idempotency_key, OLD.operation_family, OLD.owner, OLD.purpose) THEN
            RAISE EXCEPTION 'Indexed WhatsApp outbox source is immutable' USING ERRCODE = '42501';
        END IF;
        UPDATE business.whatsapp_outbox_work SET
            due_at = CASE WHEN NEW.state IN ('LEASED', 'DISPATCHING')
                THEN greatest(NEW.next_attempt_at, coalesce(NEW.lease_expires_at, NEW.next_attempt_at))
                ELSE NEW.next_attempt_at END,
            terminal = NEW.state IN ('DELIVERED', 'BLOCKED')
                OR (NEW.state = 'PENDING' AND NEW.attempt_number >= 12)
        WHERE outbox_id = NEW.outbox_id;
        RETURN NEW;
    END IF;
    IF NEW.portal_context_id IS NOT NULL THEN RETURN NEW; END IF;
    -- A customer transaction may publish only its own canonical outbox coordinates.
    IF NEW.tenant_id IS DISTINCT FROM
        nullif(current_setting('app.current_tenant_id', true), '')::UUID THEN
        RETURN NEW;
    END IF;
    SELECT * INTO route FROM business.whatsapp_relationship_routes
        WHERE tenant_id = NEW.tenant_id AND sender_hash = NEW.recipient_binding_digest;
    IF route IS NULL OR route.service_tenant_id = NEW.tenant_id THEN RETURN NEW; END IF;
    SELECT * INTO binding FROM business.channel_bindings
        WHERE tenant_id = NEW.tenant_id AND binding_id = route.binding_id;
    IF binding IS NULL OR binding.channel <> 'WHATSAPP'
        OR binding.relationship_id IS DISTINCT FROM NEW.relationship_id
        OR binding.conversation_id IS DISTINCT FROM NEW.conversation_id::TEXT
        OR binding.external_subject_hash IS DISTINCT FROM NEW.recipient_binding_digest
        OR binding.participant_id IS DISTINCT FROM route.actor_id
        OR binding.bound_evidence_id IS DISTINCT FROM route.bound_evidence_id THEN
        RAISE EXCEPTION 'WhatsApp outbox directory requires exact attachment source' USING ERRCODE = '23514';
    END IF;
    INSERT INTO business.whatsapp_outbox_work
        (outbox_id, service_tenant_id, tenant_id, environment, sender_hash, binding_id, due_at, terminal)
    VALUES (NEW.outbox_id, route.service_tenant_id, NEW.tenant_id, NEW.environment,
        route.sender_hash, route.binding_id,
        CASE WHEN NEW.state IN ('LEASED', 'DISPATCHING')
            THEN greatest(NEW.next_attempt_at, coalesce(NEW.lease_expires_at, NEW.next_attempt_at))
            ELSE NEW.next_attempt_at END,
        NEW.state IN ('DELIVERED', 'BLOCKED') OR (NEW.state = 'PENDING' AND NEW.attempt_number >= 12));
    RETURN NEW;
END
$function$;
ALTER FUNCTION business.sync_whatsapp_outbox_work() OWNER TO bp_owner;
REVOKE ALL ON FUNCTION business.sync_whatsapp_outbox_work() FROM PUBLIC, business_app;
CREATE OR REPLACE TRIGGER whatsapp_outbox_work_sync AFTER INSERT OR UPDATE ON business.conversation_outbox
    FOR EACH ROW EXECUTE FUNCTION business.sync_whatsapp_outbox_work();

CREATE OR REPLACE FUNCTION business.claim_whatsapp_outbox_work(p_service_tenant UUID, p_environment TEXT)
RETURNS TABLE (outbox_id UUID, sender_hash TEXT)
LANGUAGE plpgsql SECURITY DEFINER
SET search_path = pg_catalog SET row_security = on
AS $function$
DECLARE candidate RECORD;
BEGIN
    IF p_service_tenant IS NULL OR p_service_tenant = '00000000-0000-0000-0000-000000000000'::UUID
        OR p_service_tenant IS DISTINCT FROM
            nullif(current_setting('app.current_tenant_id', true), '')::UUID
        OR p_environment IS NULL OR length(p_environment) NOT BETWEEN 1 AND 32 THEN
        RAISE EXCEPTION 'WhatsApp discovery scope is invalid' USING ERRCODE = '42501';
    END IF;
    SELECT work.* INTO candidate FROM business.whatsapp_outbox_work AS work
        WHERE work.service_tenant_id = p_service_tenant AND work.environment = p_environment
            AND NOT work.terminal AND work.due_at <= now()
        ORDER BY work.due_at, work.outbox_id LIMIT 1 FOR UPDATE SKIP LOCKED;
    IF candidate IS NULL THEN RETURN; END IF;
    UPDATE business.whatsapp_outbox_work SET due_at = now() + interval '45 seconds'
        WHERE whatsapp_outbox_work.outbox_id = candidate.outbox_id;
    RETURN QUERY SELECT candidate.outbox_id, candidate.sender_hash::TEXT;
END
$function$;
ALTER FUNCTION business.claim_whatsapp_outbox_work(UUID, TEXT) OWNER TO bp_owner;
REVOKE ALL ON FUNCTION business.claim_whatsapp_outbox_work(UUID, TEXT) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION business.claim_whatsapp_outbox_work(UUID, TEXT) TO business_app;
DO $membership$
BEGIN
    IF current_setting('waooaw.wc134_outbox_granted_bp_owner', true) = 'true' THEN
        EXECUTE format('REVOKE bp_owner FROM %I', session_user);
    END IF;
END
$membership$;
COMMIT;
