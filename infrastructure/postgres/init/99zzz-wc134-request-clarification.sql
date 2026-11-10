-- WC-134: durable question, exact source set and correlated response evidence.
BEGIN;
DO $membership$
BEGIN
    IF NOT pg_has_role(session_user, 'bp_owner', 'SET') THEN
        EXECUTE format('GRANT bp_owner TO %I', session_user);
        PERFORM set_config('waooaw.wc134_clarification_granted', 'true', true);
    END IF;
END
$membership$;

CREATE UNIQUE INDEX IF NOT EXISTS conversation_request_message_scope_key
ON business.conversation_messages (tenant_id, relationship_id, conversation_id, message_id);

CREATE TABLE IF NOT EXISTS business.conversation_request_questions (
    tenant_id UUID NOT NULL,
    relationship_id UUID NOT NULL,
    conversation_id UUID NOT NULL,
    question_id UUID NOT NULL,
    question_message_id UUID NOT NULL,
    environment TEXT NOT NULL CHECK (length(environment) BETWEEN 1 AND 32),
    actor_id UUID NOT NULL,
    actor_role TEXT NOT NULL CHECK (length(actor_role) BETWEEN 1 AND 64),
    relationship_version INTEGER NOT NULL CHECK (relationship_version >= 0),
    agent_instance_id UUID NOT NULL,
    channel_binding_id UUID NOT NULL,
    recipient_digest TEXT NOT NULL CHECK (recipient_digest ~ '^[0-9a-f]{64}$'),
    created_at TIMESTAMPTZ NOT NULL DEFAULT statement_timestamp(),
    frozen_at TIMESTAMPTZ,
    member_count INTEGER,
    PRIMARY KEY (tenant_id, question_id),
    UNIQUE (tenant_id, relationship_id, conversation_id, question_id),
    UNIQUE (tenant_id, question_message_id),
    CHECK (
        (frozen_at IS NULL AND member_count IS NULL)
        OR (frozen_at IS NOT NULL AND member_count IS NOT NULL AND member_count >= 2)
    ),
    FOREIGN KEY (tenant_id, relationship_id, conversation_id, question_message_id)
    REFERENCES business.conversation_messages (tenant_id, relationship_id, conversation_id, message_id)
);
ALTER TABLE business.conversation_request_questions OWNER TO bp_owner;
ALTER TABLE business.conversation_request_questions ENABLE ROW LEVEL SECURITY;
ALTER TABLE business.conversation_request_questions FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS conversation_request_questions_tenant ON business.conversation_request_questions;
CREATE POLICY conversation_request_questions_tenant ON business.conversation_request_questions
USING (tenant_id = nullif(current_setting('app.current_tenant_id', TRUE), '')::UUID)
WITH CHECK (tenant_id = nullif(current_setting('app.current_tenant_id', TRUE), '')::UUID);
REVOKE ALL ON business.conversation_request_questions FROM public, business_app;
GRANT SELECT ON business.conversation_request_questions TO business_app;
GRANT INSERT (
    tenant_id, relationship_id, conversation_id, question_id, question_message_id,
    environment, actor_id, actor_role, relationship_version, agent_instance_id,
    channel_binding_id, recipient_digest
)
ON business.conversation_request_questions TO business_app;
GRANT UPDATE (frozen_at, member_count) ON business.conversation_request_questions TO business_app;

CREATE TABLE IF NOT EXISTS business.conversation_request_question_members (
    tenant_id UUID NOT NULL,
    relationship_id UUID NOT NULL,
    conversation_id UUID NOT NULL,
    question_id UUID NOT NULL,
    message_id UUID NOT NULL,
    ordinal INTEGER NOT NULL CHECK (ordinal > 0),
    PRIMARY KEY (tenant_id, question_id, ordinal),
    UNIQUE (tenant_id, question_id, message_id),
    FOREIGN KEY (tenant_id, relationship_id, conversation_id, question_id)
    REFERENCES business.conversation_request_questions (tenant_id, relationship_id, conversation_id, question_id),
    FOREIGN KEY (tenant_id, relationship_id, conversation_id, message_id)
    REFERENCES business.conversation_pending_starts (tenant_id, relationship_id, conversation_id, message_id)
);
CREATE UNIQUE INDEX IF NOT EXISTS conversation_request_source_once
ON business.conversation_request_question_members (tenant_id, message_id);
ALTER TABLE business.conversation_request_question_members OWNER TO bp_owner;
ALTER TABLE business.conversation_request_question_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE business.conversation_request_question_members FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS conversation_request_question_members_tenant ON business.conversation_request_question_members;
CREATE POLICY conversation_request_question_members_tenant ON business.conversation_request_question_members
USING (tenant_id = nullif(current_setting('app.current_tenant_id', TRUE), '')::UUID)
WITH CHECK (tenant_id = nullif(current_setting('app.current_tenant_id', TRUE), '')::UUID);
REVOKE ALL ON business.conversation_request_question_members FROM public, business_app;
GRANT SELECT, INSERT ON business.conversation_request_question_members TO business_app;

CREATE OR REPLACE FUNCTION business.guard_request_question_member()
RETURNS TRIGGER LANGUAGE plpgsql SET search_path = pg_catalog SET row_security = on
AS $function$
DECLARE frozen TIMESTAMPTZ;
BEGIN
    SELECT frozen_at INTO frozen FROM business.conversation_request_questions
    WHERE tenant_id = NEW.tenant_id AND question_id = NEW.question_id
    FOR UPDATE;
    IF NOT FOUND OR frozen IS NOT NULL THEN
        RAISE EXCEPTION 'Question membership is unavailable or frozen' USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END
$function$;
DROP TRIGGER IF EXISTS request_question_member_guard ON business.conversation_request_question_members;
CREATE TRIGGER request_question_member_guard BEFORE INSERT ON business.conversation_request_question_members
FOR EACH ROW EXECUTE FUNCTION business.guard_request_question_member();

CREATE OR REPLACE FUNCTION business.guard_request_question_freeze()
RETURNS TRIGGER LANGUAGE plpgsql SET search_path = pg_catalog SET row_security = on
AS $function$
DECLARE
    actual_count BIGINT; lowest INTEGER; highest INTEGER; first_offset BIGINT; last_offset BIGINT;
    bad_scope BIGINT; last_source BIGINT; question_sequence BIGINT;
BEGIN
    IF OLD.frozen_at IS NOT NULL OR NEW.frozen_at IS NULL OR NEW.member_count IS NULL THEN
        RAISE EXCEPTION 'Question freeze cannot be reversed or changed' USING ERRCODE = '23514';
    END IF;
    SELECT count(*), min(member.ordinal), max(member.ordinal),
        min(message.sequence - member.ordinal), max(message.sequence - member.ordinal),
        max(message.sequence),
        count(*) FILTER (WHERE message.environment IS DISTINCT FROM NEW.environment
            OR pending.actor_id IS DISTINCT FROM NEW.actor_id
            OR mandate.agent_instance_id IS DISTINCT FROM NEW.agent_instance_id
            OR mandate.deadline <= statement_timestamp()
            OR execution.origin_channel_binding_id IS DISTINCT FROM NEW.channel_binding_id
            OR execution.origin_recipient_digest IS DISTINCT FROM NEW.recipient_digest
            OR message.actor IS DISTINCT FROM 'CUSTOMER'
            OR message.channel IS DISTINCT FROM 'WHATSAPP'
            OR message.evidence_state IS DISTINCT FROM 'RECORDED')
    INTO actual_count, lowest, highest, first_offset, last_offset, last_source, bad_scope
    FROM business.conversation_request_question_members AS member
    JOIN business.conversation_pending_starts AS pending
        ON pending.tenant_id = member.tenant_id AND pending.message_id = member.message_id
    JOIN business.conversation_messages AS message
        ON message.tenant_id = pending.tenant_id AND message.message_id = pending.message_id
    JOIN business.conversation_executions AS execution
        ON execution.tenant_id = pending.tenant_id AND execution.execution_id = pending.execution_id
    JOIN business.operational_mandate_snapshots AS mandate
        ON mandate.tenant_id = pending.tenant_id AND mandate.mandate_id = pending.mandate_id
    WHERE member.tenant_id = NEW.tenant_id AND member.question_id = NEW.question_id;
    SELECT sequence INTO question_sequence FROM business.conversation_messages
    WHERE tenant_id = NEW.tenant_id AND relationship_id = NEW.relationship_id
        AND conversation_id = NEW.conversation_id AND message_id = NEW.question_message_id
        AND environment = NEW.environment AND actor = 'SYSTEM' AND channel = 'WHATSAPP'
        AND dialogue_act = 'ASK';
    IF actual_count <> NEW.member_count OR lowest <> 1 OR highest <> NEW.member_count
        OR first_offset <> last_offset OR bad_scope <> 0 OR question_sequence IS NULL
        OR question_sequence <= last_source THEN
        RAISE EXCEPTION 'Question requires a contiguous source set and matching canonical scope'
            USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END
$function$;
DROP TRIGGER IF EXISTS request_question_freeze_guard ON business.conversation_request_questions;
CREATE TRIGGER request_question_freeze_guard BEFORE UPDATE ON business.conversation_request_questions
FOR EACH ROW EXECUTE FUNCTION business.guard_request_question_freeze();

CREATE OR REPLACE FUNCTION business.require_request_question_frozen()
RETURNS TRIGGER LANGUAGE plpgsql SET search_path = pg_catalog SET row_security = on
AS $function$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM business.conversation_request_questions
        WHERE tenant_id = NEW.tenant_id AND question_id = NEW.question_id AND frozen_at IS NOT NULL
    ) THEN
        RAISE EXCEPTION 'Question creation requires an atomic freeze' USING ERRCODE = '23514';
    END IF;
    RETURN NULL;
END
$function$;
DROP TRIGGER IF EXISTS request_question_requires_freeze ON business.conversation_request_questions;
CREATE CONSTRAINT TRIGGER request_question_requires_freeze
AFTER INSERT OR UPDATE ON business.conversation_request_questions
DEFERRABLE INITIALLY DEFERRED FOR EACH ROW
EXECUTE FUNCTION business.require_request_question_frozen();

CREATE TABLE IF NOT EXISTS business.conversation_request_answers (
    tenant_id UUID NOT NULL,
    relationship_id UUID NOT NULL,
    conversation_id UUID NOT NULL,
    question_id UUID NOT NULL,
    answer_id UUID NOT NULL,
    response_claim_id UUID NOT NULL,
    response_payload_digest TEXT NOT NULL CHECK (response_payload_digest ~ '^[0-9a-f]{64}$'),
    question_provider_digest TEXT NOT NULL CHECK (question_provider_digest ~ '^[0-9a-f]{64}$'),
    decision TEXT NOT NULL CHECK (decision IN ('UNCLEAR', 'ONE', 'SEPARATE')),
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT statement_timestamp(),
    PRIMARY KEY (tenant_id, answer_id),
    UNIQUE (response_claim_id),
    FOREIGN KEY (tenant_id, relationship_id, conversation_id, question_id)
    REFERENCES business.conversation_request_questions (tenant_id, relationship_id, conversation_id, question_id),
    FOREIGN KEY (response_claim_id) REFERENCES business.provider_event_claims (claim_id)
);
CREATE UNIQUE INDEX IF NOT EXISTS conversation_request_one_decision
ON business.conversation_request_answers (tenant_id, question_id)
WHERE decision IN ('ONE', 'SEPARATE');
ALTER TABLE business.conversation_request_answers OWNER TO bp_owner;
ALTER TABLE business.conversation_request_answers ENABLE ROW LEVEL SECURITY;
ALTER TABLE business.conversation_request_answers FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS conversation_request_answers_tenant ON business.conversation_request_answers;
CREATE POLICY conversation_request_answers_tenant ON business.conversation_request_answers
USING (tenant_id = nullif(current_setting('app.current_tenant_id', TRUE), '')::UUID)
WITH CHECK (tenant_id = nullif(current_setting('app.current_tenant_id', TRUE), '')::UUID);
REVOKE ALL ON business.conversation_request_answers FROM public, business_app;
GRANT SELECT ON business.conversation_request_answers TO business_app;
GRANT SELECT ON business.provider_event_claims,
business.conversation_delivery_observations,
business.relationship_emergency_stop_latches
TO bp_owner;
GRANT INSERT ON business.conversation_request_answers TO bp_owner;
GRANT UPDATE ON business.provider_event_claims TO bp_owner;

CREATE OR REPLACE FUNCTION business.record_conversation_request_answer(
    p_environment TEXT,
    p_app_binding_digest TEXT,
    p_event_identity TEXT,
    p_payload_digest TEXT,
    p_lease_owner UUID,
    p_tenant_id UUID,
    p_relationship_id UUID,
    p_conversation_id UUID,
    p_actor_id UUID,
    p_actor_role TEXT,
    p_relationship_version INTEGER,
    p_channel_binding_id UUID,
    p_recipient_digest TEXT,
    p_question_provider_digest TEXT,
    p_decision TEXT
)
RETURNS TABLE (question_id UUID, decision TEXT, result_status TEXT)
LANGUAGE plpgsql SECURITY DEFINER
SET search_path = pg_catalog SET row_security = on
AS $function$
DECLARE
    previous_tenant TEXT;
    event_claim RECORD;
    matches UUID[];
    selected_question UUID;
    selected_decision TEXT;
    answer_identifier UUID := gen_random_uuid();
    result_payload JSONB;
BEGIN
    IF p_decision IS NULL OR p_decision NOT IN ('UNCLEAR', 'ONE', 'SEPARATE')
        OR p_environment IS NULL OR length(p_environment) NOT BETWEEN 1 AND 32
        OR p_app_binding_digest IS NULL OR p_app_binding_digest !~ '^[0-9a-f]{64}$'
        OR p_payload_digest IS NULL OR p_payload_digest !~ '^[0-9a-f]{64}$'
        OR p_question_provider_digest IS NULL OR p_question_provider_digest !~ '^[0-9a-f]{64}$'
        OR p_recipient_digest IS NULL OR p_recipient_digest !~ '^[0-9a-f]{64}$'
        OR p_event_identity IS NULL OR length(p_event_identity) NOT BETWEEN 1 AND 256
        OR p_lease_owner IS NULL OR p_tenant_id IS NULL OR p_relationship_id IS NULL
        OR p_conversation_id IS NULL OR p_actor_id IS NULL OR p_channel_binding_id IS NULL
        OR p_actor_role IS NULL OR length(p_actor_role) NOT BETWEEN 1 AND 64
        OR p_relationship_version IS NULL OR p_relationship_version < 0 THEN
        RAISE EXCEPTION 'Clarification response identity is invalid' USING ERRCODE = '22023';
    END IF;

    previous_tenant := current_setting('app.current_tenant_id', true);
    PERFORM set_config('app.current_tenant_id', p_tenant_id::text, true);

    SELECT claim_id, payload_digest, lease_owner, lease_expires_at, state, result_json
    INTO event_claim
    FROM business.provider_event_claims
    WHERE environment = p_environment AND provider = 'WHATSAPP'
        AND app_binding_digest = p_app_binding_digest AND event_identity = p_event_identity
    FOR UPDATE;
    IF NOT FOUND OR event_claim.payload_digest IS DISTINCT FROM p_payload_digest
        OR event_claim.lease_owner IS DISTINCT FROM p_lease_owner
        OR event_claim.state <> 'CLAIMED'
        OR event_claim.lease_expires_at <= statement_timestamp() THEN
        RAISE EXCEPTION 'Clarification response claim is not owned' USING ERRCODE = '42501';
    END IF;

    IF EXISTS (
        SELECT 1 FROM business.relationship_emergency_stop_latches AS stop
        WHERE stop.environment = p_environment AND stop.tenant_id = p_tenant_id
            AND stop.relationship_id = p_relationship_id
            AND stop.state IN ('LATCHED', 'EVIDENCE_CONFIRMED')
    ) THEN
        RAISE EXCEPTION 'Clarification response is blocked by Stop' USING ERRCODE = '42501';
    END IF;

    SELECT array_agg(DISTINCT question.question_id)
    INTO matches
    FROM business.conversation_request_questions AS question
    JOIN business.conversation_delivery_observations AS observation
        ON observation.environment = question.environment
        AND observation.tenant_id = question.tenant_id
        AND observation.relationship_id = question.relationship_id
        AND observation.message_id = question.question_message_id
        AND observation.provider = 'WHATSAPP'
        AND observation.provider_reference_digest = p_question_provider_digest
        AND observation.delivery_state IN ('PROVIDER_ACCEPTED', 'DELIVERED', 'READ')
    WHERE question.environment = p_environment
        AND question.tenant_id = p_tenant_id
        AND question.frozen_at IS NOT NULL
        AND question.member_count >= 2
        AND (SELECT count(*) FROM business.conversation_request_question_members AS member
        WHERE member.tenant_id = question.tenant_id
            AND member.question_id = question.question_id
        ) = question.member_count;

    IF coalesce(cardinality(matches), 0) = 0 THEN
        PERFORM set_config('app.current_tenant_id', coalesce(previous_tenant, ''), true);
        RETURN;
    END IF;
    IF cardinality(matches) <> 1 THEN
        RAISE EXCEPTION 'Clarification question reference is ambiguous' USING ERRCODE = '23514';
    END IF;
    selected_question := matches[1];

    PERFORM question.question_id
    FROM business.conversation_request_questions AS question
    WHERE question.tenant_id = p_tenant_id AND question.question_id = selected_question
        AND question.relationship_id = p_relationship_id
        AND question.conversation_id = p_conversation_id
        AND question.actor_id = p_actor_id AND question.actor_role = p_actor_role
        AND question.relationship_version = p_relationship_version
        AND question.channel_binding_id = p_channel_binding_id
        AND question.recipient_digest = p_recipient_digest
    FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Clarification response route or actor changed' USING ERRCODE = '42501';
    END IF;
    IF EXISTS (
        SELECT 1 FROM business.conversation_request_answers AS prior
        WHERE prior.tenant_id = p_tenant_id AND prior.question_id = selected_question
            AND prior.decision IN ('ONE', 'SEPARATE')
    ) THEN
        selected_decision := 'UNCLEAR';
        result_payload := jsonb_build_object(
            'messageId', p_event_identity,
            'status', 'CLARIFICATION_ALREADY_RESOLVED',
            'journeyStage', 'CLARIFICATION',
            'reply', '',
            'replayed', FALSE,
            'internalTenantToken', ''
        );
    ELSE
        selected_decision := p_decision;
        INSERT INTO business.conversation_request_answers (
            tenant_id, relationship_id, conversation_id, question_id, answer_id, response_claim_id,
            response_payload_digest, question_provider_digest, decision
        )
        VALUES (
            p_tenant_id, p_relationship_id, p_conversation_id, selected_question,
            answer_identifier, event_claim.claim_id, p_payload_digest, p_question_provider_digest,
            selected_decision
        );
        result_payload := jsonb_build_object(
            'messageId', p_event_identity,
            'status', 'CLARIFICATION_RECORDED',
            'journeyStage', 'CLARIFICATION',
            'reply', '',
            'replayed', FALSE,
            'internalTenantToken', ''
        );
    END IF;
    UPDATE business.provider_event_claims
    SET state = 'ACCEPTED',
        result_json = result_payload,
        terminal_at = statement_timestamp(),
        expires_at = statement_timestamp() + interval '30 days',
        lease_owner = NULL,
        lease_expires_at = NULL
    WHERE claim_id = event_claim.claim_id;

    PERFORM set_config('app.current_tenant_id', coalesce(previous_tenant, ''), true);
    RETURN QUERY SELECT selected_question, selected_decision, result_payload ->> 'status';
END
$function$;
ALTER FUNCTION business.record_conversation_request_answer(
    TEXT, TEXT, TEXT, TEXT, UUID, UUID, UUID, UUID, UUID, TEXT, INTEGER, UUID, TEXT, TEXT, TEXT
) OWNER TO bp_owner;
REVOKE ALL ON FUNCTION business.record_conversation_request_answer(
    TEXT, TEXT, TEXT, TEXT, UUID, UUID, UUID, UUID, UUID, TEXT, INTEGER, UUID, TEXT, TEXT, TEXT
) FROM public, business_app;
GRANT EXECUTE ON FUNCTION business.record_conversation_request_answer(
    TEXT, TEXT, TEXT, TEXT, UUID, UUID, UUID, UUID, UUID, TEXT, INTEGER, UUID, TEXT, TEXT, TEXT
) TO business_app;

DO $membership$
BEGIN
    IF current_setting('waooaw.wc134_clarification_granted', true) = 'true' THEN
        EXECUTE format('REVOKE bp_owner FROM %I', session_user);
    END IF;
END
$membership$;
COMMIT;
