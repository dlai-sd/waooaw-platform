-- WC-134: owner-controlled durable conversation batch claims and dispatch fencing.
BEGIN;
DO $membership$
BEGIN
    IF NOT pg_has_role(session_user, 'bp_owner', 'SET') THEN
        EXECUTE format('GRANT bp_owner TO %I', session_user);
        PERFORM set_config('waooaw.wc134_batch_dispatch_granted', 'true', true);
    END IF;
END
$membership$;

ALTER TABLE business.conversation_pending_starts
    ADD COLUMN IF NOT EXISTS work_item_id UUID,
    ADD COLUMN IF NOT EXISTS work_item_revision INTEGER,
    ADD COLUMN IF NOT EXISTS work_item_owner TEXT,
    ADD COLUMN IF NOT EXISTS work_item_invocation_id UUID,
    ADD COLUMN IF NOT EXISTS dispatch_state TEXT NOT NULL DEFAULT 'WAITING';
ALTER TABLE business.conversation_pending_starts
    DROP CONSTRAINT IF EXISTS conversation_pending_work_item_complete;
ALTER TABLE business.conversation_pending_starts
    ADD CONSTRAINT conversation_pending_work_item_complete CHECK (
        (work_item_id IS NULL AND work_item_revision IS NULL AND work_item_owner IS NULL
            AND work_item_invocation_id IS NULL)
        OR (
            work_item_id IS NOT NULL
            AND work_item_revision > 0
            AND work_item_owner = 'professional-runtime'
            AND work_item_invocation_id IS NOT NULL
        )
    );
ALTER TABLE business.conversation_pending_starts
    DROP CONSTRAINT IF EXISTS conversation_pending_dispatch_state_valid;
ALTER TABLE business.conversation_pending_starts
    ADD CONSTRAINT conversation_pending_dispatch_state_valid
    CHECK (dispatch_state = 'WAITING');

ALTER TABLE business.conversation_batch_groups
    ADD COLUMN IF NOT EXISTS dispatch_state TEXT,
    ADD COLUMN IF NOT EXISTS due_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS work_item_id UUID,
    ADD COLUMN IF NOT EXISTS work_item_revision INTEGER,
    ADD COLUMN IF NOT EXISTS source_list_digest TEXT,
    ADD COLUMN IF NOT EXISTS request_digest TEXT,
    ADD COLUMN IF NOT EXISTS runtime_execution_id UUID,
    ADD COLUMN IF NOT EXISTS lease_owner UUID,
    ADD COLUMN IF NOT EXISTS lease_token BIGINT,
    ADD COLUMN IF NOT EXISTS lease_expires_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS last_failure_code TEXT,
    ADD COLUMN IF NOT EXISTS dispatch_intent_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS started_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS terminal_at TIMESTAMPTZ;
ALTER TABLE business.conversation_batch_groups
    DROP CONSTRAINT IF EXISTS conversation_batch_dispatch_state_valid;
ALTER TABLE business.conversation_batch_groups
    ADD CONSTRAINT conversation_batch_dispatch_state_valid CHECK (
        dispatch_state IS NULL OR dispatch_state IN (
            'CLAIMED', 'DISPATCHING', 'STARTED', 'UNRESOLVED',
            'COMPLETED', 'FAILED', 'DENIED', 'STOPPED'
        )
    );
ALTER TABLE business.conversation_batch_groups
    DROP CONSTRAINT IF EXISTS conversation_batch_dispatch_binding_complete;
ALTER TABLE business.conversation_batch_groups
    ADD CONSTRAINT conversation_batch_dispatch_binding_complete CHECK (
        dispatch_state IS NULL OR (
            due_at IS NOT NULL
            AND work_item_id IS NOT NULL
            AND work_item_revision > 0
            AND lease_owner IS NOT NULL
            AND lease_token > 0
            AND lease_expires_at IS NOT NULL
        )
    );
ALTER TABLE business.conversation_batch_groups
    DROP CONSTRAINT IF EXISTS conversation_batch_dispatch_intent_complete;
ALTER TABLE business.conversation_batch_groups
    ADD CONSTRAINT conversation_batch_dispatch_intent_complete CHECK (
        dispatch_state NOT IN ('DISPATCHING', 'STARTED', 'UNRESOLVED', 'COMPLETED', 'FAILED')
        OR (
            frozen_at IS NOT NULL
            AND source_list_digest ~ '^sha256:[0-9a-f]{64}$'
            AND request_digest ~ '^sha256:[0-9a-f]{64}$'
            AND runtime_execution_id IS NOT NULL
            AND dispatch_intent_at IS NOT NULL
        )
    );
CREATE UNIQUE INDEX IF NOT EXISTS conversation_batch_runtime_execution_key
ON business.conversation_batch_groups (runtime_execution_id)
WHERE runtime_execution_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS conversation_batch_dispatch_due
ON business.conversation_batch_groups (dispatch_state, lease_expires_at, due_at, batch_id)
WHERE dispatch_state IN ('CLAIMED', 'DISPATCHING', 'UNRESOLVED');
GRANT INSERT (
    dispatch_state, due_at, work_item_id, work_item_revision,
    lease_owner, lease_token, lease_expires_at
) ON business.conversation_batch_groups TO business_app;

CREATE TABLE IF NOT EXISTS business.conversation_batch_claims (
    claim_id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    relationship_id UUID NOT NULL,
    conversation_id UUID NOT NULL,
    first_message_id UUID NOT NULL,
    worker_id UUID NOT NULL,
    fencing_token BIGINT NOT NULL CHECK (fencing_token > 0),
    state TEXT NOT NULL CHECK (state IN ('CLAIMED', 'CONSUMED', 'DENIED')),
    lease_expires_at TIMESTAMPTZ NOT NULL,
    claimed_at TIMESTAMPTZ NOT NULL DEFAULT statement_timestamp(),
    completed_at TIMESTAMPTZ,
    failure_code TEXT,
    UNIQUE (tenant_id, first_message_id),
    FOREIGN KEY (tenant_id, relationship_id, conversation_id, first_message_id)
        REFERENCES business.conversation_pending_starts
        (tenant_id, relationship_id, conversation_id, message_id)
);
ALTER TABLE business.conversation_batch_claims OWNER TO bp_owner;
ALTER TABLE business.conversation_batch_claims ENABLE ROW LEVEL SECURITY;
ALTER TABLE business.conversation_batch_claims FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS conversation_batch_claims_owner ON business.conversation_batch_claims;
CREATE POLICY conversation_batch_claims_owner ON business.conversation_batch_claims
TO bp_owner USING (true) WITH CHECK (true);
REVOKE ALL ON business.conversation_batch_claims FROM PUBLIC, business_app;
CREATE INDEX IF NOT EXISTS conversation_batch_claims_recovery
ON business.conversation_batch_claims (state, lease_expires_at, claim_id)
WHERE state = 'CLAIMED';

CREATE OR REPLACE FUNCTION business.claim_conversation_batch(
    p_environment TEXT,
    p_worker_id UUID,
    p_lease_seconds INTEGER
)
RETURNS TABLE (
    claim_id UUID,
    tenant_id UUID,
    relationship_id UUID,
    conversation_id UUID,
    first_message_id UUID,
    fencing_token BIGINT,
    lease_expires_at TIMESTAMPTZ,
    authorized BOOLEAN
)
LANGUAGE plpgsql SECURITY DEFINER
SET search_path = pg_catalog SET row_security = on
AS $function$
DECLARE candidate RECORD; membership RECORD; claimed RECORD;
BEGIN
    IF p_environment IS NULL OR length(p_environment) NOT BETWEEN 1 AND 64
        OR p_worker_id IS NULL OR p_lease_seconds NOT BETWEEN 5 AND 300 THEN
        RAISE EXCEPTION 'Batch claim parameters are invalid' USING ERRCODE = '22023';
    END IF;

    SELECT c.* INTO claimed
    FROM business.conversation_batch_claims AS c
    JOIN business.conversation_messages AS message
      ON message.tenant_id = c.tenant_id AND message.message_id = c.first_message_id
    WHERE c.state = 'CLAIMED' AND c.lease_expires_at <= statement_timestamp()
      AND message.environment = p_environment
    ORDER BY c.lease_expires_at, c.claim_id
    LIMIT 1 FOR UPDATE OF c SKIP LOCKED;

    IF claimed IS NULL THEN
        SELECT pending.*, execution.runtime_actor_issuer, execution.runtime_membership_id,
               execution.runtime_account_id
        INTO candidate
        FROM business.conversation_pending_starts AS pending
        JOIN business.conversation_messages AS message
          ON message.tenant_id = pending.tenant_id AND message.message_id = pending.message_id
        JOIN business.conversation_executions AS execution
          ON execution.tenant_id = pending.tenant_id
         AND execution.execution_id = pending.execution_id
        WHERE message.environment = p_environment
          AND pending.due_at <= statement_timestamp()
          AND pending.work_item_id IS NOT NULL
          AND NOT EXISTS (
              SELECT 1 FROM business.conversation_batch_members AS member
              WHERE member.tenant_id = pending.tenant_id
                AND member.message_id = pending.message_id
          )
          AND NOT EXISTS (
              SELECT 1 FROM business.conversation_batch_claims AS existing
              WHERE existing.tenant_id = pending.tenant_id
                AND existing.first_message_id = pending.message_id
          )
        ORDER BY pending.due_at, pending.message_id
        LIMIT 1 FOR UPDATE OF pending SKIP LOCKED;
        IF candidate IS NULL THEN RETURN; END IF;
        INSERT INTO business.conversation_batch_claims (
            claim_id, tenant_id, relationship_id, conversation_id, first_message_id,
            worker_id, fencing_token, state, lease_expires_at
        ) VALUES (
            gen_random_uuid(), candidate.tenant_id, candidate.relationship_id,
            candidate.conversation_id, candidate.message_id, p_worker_id, 1, 'CLAIMED',
            statement_timestamp() + make_interval(secs => p_lease_seconds)
        ) RETURNING * INTO claimed;
    ELSE
        UPDATE business.conversation_batch_claims
        SET worker_id = p_worker_id,
            fencing_token = fencing_token + 1,
            lease_expires_at = statement_timestamp() + make_interval(secs => p_lease_seconds),
            failure_code = NULL
        WHERE conversation_batch_claims.claim_id = claimed.claim_id
        RETURNING * INTO claimed;
        SELECT pending.*, execution.runtime_actor_issuer, execution.runtime_membership_id,
               execution.runtime_account_id
        INTO candidate
        FROM business.conversation_pending_starts AS pending
        JOIN business.conversation_executions AS execution
          ON execution.tenant_id = pending.tenant_id
         AND execution.execution_id = pending.execution_id
        WHERE pending.tenant_id = claimed.tenant_id
          AND pending.message_id = claimed.first_message_id;
    END IF;

    IF candidate.runtime_actor_issuer IS NOT NULL
        AND candidate.runtime_membership_id IS NOT NULL
        AND candidate.runtime_account_id IS NOT NULL THEN
        SELECT * INTO membership FROM identity.lock_conversation_runtime_membership(
            candidate.runtime_actor_issuer, candidate.actor_id, candidate.tenant_id,
            candidate.runtime_membership_id
        );
    END IF;
    RETURN QUERY SELECT claimed.claim_id, claimed.tenant_id, claimed.relationship_id,
        claimed.conversation_id, claimed.first_message_id, claimed.fencing_token,
        claimed.lease_expires_at,
        coalesce(membership.account_id = candidate.runtime_account_id, false);
END
$function$;
ALTER FUNCTION business.claim_conversation_batch(TEXT, UUID, INTEGER) OWNER TO bp_owner;
REVOKE ALL ON FUNCTION business.claim_conversation_batch(TEXT, UUID, INTEGER) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION business.claim_conversation_batch(TEXT, UUID, INTEGER) TO business_app;

CREATE OR REPLACE FUNCTION business.claim_conversation_batch_recovery(
    p_environment TEXT,
    p_worker_id UUID,
    p_lease_seconds INTEGER
)
RETURNS TABLE (
    batch_id UUID,
    tenant_id UUID,
    relationship_id UUID,
    conversation_id UUID,
    first_message_id UUID,
    dispatch_state TEXT,
    fencing_token BIGINT,
    lease_expires_at TIMESTAMPTZ,
    authorized BOOLEAN
)
LANGUAGE plpgsql SECURITY DEFINER
SET search_path = pg_catalog SET row_security = on
AS $function$
DECLARE candidate RECORD; membership RECORD;
BEGIN
    IF p_environment IS NULL OR length(p_environment) NOT BETWEEN 1 AND 64
        OR p_worker_id IS NULL OR p_lease_seconds NOT BETWEEN 5 AND 300 THEN
        RAISE EXCEPTION 'Batch recovery parameters are invalid' USING ERRCODE = '22023';
    END IF;
    SELECT batch.*, member.message_id AS first_source,
           execution.runtime_actor_issuer, execution.runtime_membership_id,
           execution.runtime_account_id, pending.actor_id
    INTO candidate
    FROM business.conversation_batch_groups AS batch
    JOIN business.conversation_batch_members AS member
      ON member.tenant_id = batch.tenant_id AND member.batch_id = batch.batch_id
     AND member.ordinal = 1
    JOIN business.conversation_pending_starts AS pending
      ON pending.tenant_id = member.tenant_id AND pending.message_id = member.message_id
    JOIN business.conversation_messages AS message
      ON message.tenant_id = pending.tenant_id AND message.message_id = pending.message_id
    JOIN business.conversation_executions AS execution
      ON execution.tenant_id = pending.tenant_id AND execution.execution_id = pending.execution_id
    WHERE batch.dispatch_state IN ('DISPATCHING', 'UNRESOLVED')
      AND batch.lease_expires_at <= statement_timestamp()
      AND message.environment = p_environment
    ORDER BY batch.lease_expires_at, batch.batch_id
    LIMIT 1 FOR UPDATE OF batch SKIP LOCKED;
    IF candidate IS NULL THEN RETURN; END IF;
    UPDATE business.conversation_batch_groups AS batch
    SET lease_owner = p_worker_id, lease_token = batch.lease_token + 1,
        lease_expires_at = statement_timestamp() + make_interval(secs => p_lease_seconds)
    WHERE batch.tenant_id = candidate.tenant_id AND batch.batch_id = candidate.batch_id
    RETURNING batch.lease_token, batch.lease_expires_at
    INTO candidate.lease_token, candidate.lease_expires_at;
    SELECT * INTO membership FROM identity.lock_conversation_runtime_membership(
        candidate.runtime_actor_issuer, candidate.actor_id, candidate.tenant_id,
        candidate.runtime_membership_id
    );
    RETURN QUERY SELECT candidate.batch_id, candidate.tenant_id, candidate.relationship_id,
        candidate.conversation_id, candidate.first_source, candidate.dispatch_state,
        candidate.lease_token, candidate.lease_expires_at,
        coalesce(membership.account_id = candidate.runtime_account_id, false);
END
$function$;
ALTER FUNCTION business.claim_conversation_batch_recovery(TEXT, UUID, INTEGER) OWNER TO bp_owner;
REVOKE ALL ON FUNCTION business.claim_conversation_batch_recovery(TEXT, UUID, INTEGER) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION business.claim_conversation_batch_recovery(TEXT, UUID, INTEGER)
TO business_app;

CREATE OR REPLACE FUNCTION business.finish_conversation_batch_claim(
    p_claim_id UUID,
    p_worker_id UUID,
    p_fencing_token BIGINT,
    p_state TEXT,
    p_failure_code TEXT DEFAULT NULL
)
RETURNS BOOLEAN
LANGUAGE plpgsql SECURITY DEFINER
SET search_path = pg_catalog SET row_security = on
AS $function$
DECLARE changed INTEGER;
BEGIN
    IF p_state NOT IN ('CONSUMED', 'DENIED') THEN
        RAISE EXCEPTION 'Batch claim terminal state is invalid' USING ERRCODE = '22023';
    END IF;
    UPDATE business.conversation_batch_claims
    SET state = p_state, completed_at = statement_timestamp(),
        failure_code = left(p_failure_code, 100)
    WHERE claim_id = p_claim_id AND worker_id = p_worker_id
      AND fencing_token = p_fencing_token AND state = 'CLAIMED'
      AND lease_expires_at > statement_timestamp();
    GET DIAGNOSTICS changed = ROW_COUNT;
    RETURN changed = 1;
END
$function$;
ALTER FUNCTION business.finish_conversation_batch_claim(UUID, UUID, BIGINT, TEXT, TEXT) OWNER TO bp_owner;
REVOKE ALL ON FUNCTION business.finish_conversation_batch_claim(UUID, UUID, BIGINT, TEXT, TEXT) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION business.finish_conversation_batch_claim(UUID, UUID, BIGINT, TEXT, TEXT)
TO business_app;

CREATE OR REPLACE FUNCTION business.complete_individual_pending_start(
    p_claim_id UUID,
    p_worker_id UUID,
    p_fencing_token BIGINT
)
RETURNS BOOLEAN
LANGUAGE plpgsql SECURITY DEFINER
SET search_path = pg_catalog SET row_security = on
AS $function$
DECLARE claimed RECORD; changed INTEGER;
BEGIN
    SELECT * INTO claimed FROM business.conversation_batch_claims
    WHERE claim_id = p_claim_id AND worker_id = p_worker_id
      AND fencing_token = p_fencing_token AND state = 'CLAIMED'
      AND lease_expires_at > statement_timestamp()
    FOR UPDATE;
    IF claimed IS NULL THEN RETURN false; END IF;
    DELETE FROM business.conversation_pending_starts
    WHERE tenant_id = claimed.tenant_id AND message_id = claimed.first_message_id
      AND NOT EXISTS (
          SELECT 1 FROM business.conversation_batch_members AS member
          WHERE member.tenant_id = claimed.tenant_id
            AND member.message_id = claimed.first_message_id
      );
    GET DIAGNOSTICS changed = ROW_COUNT;
    IF changed <> 1 THEN RETURN false; END IF;
    UPDATE business.conversation_batch_claims
    SET state = 'CONSUMED', completed_at = statement_timestamp()
    WHERE claim_id = p_claim_id;
    RETURN true;
END
$function$;
ALTER FUNCTION business.complete_individual_pending_start(UUID, UUID, BIGINT) OWNER TO bp_owner;
REVOKE ALL ON FUNCTION business.complete_individual_pending_start(UUID, UUID, BIGINT) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION business.complete_individual_pending_start(UUID, UUID, BIGINT)
TO business_app;

CREATE OR REPLACE FUNCTION business.transition_conversation_batch(
    p_tenant_id UUID,
    p_batch_id UUID,
    p_worker_id UUID,
    p_fencing_token BIGINT,
    p_expected_state TEXT,
    p_new_state TEXT,
    p_source_list_digest TEXT DEFAULT NULL,
    p_request_digest TEXT DEFAULT NULL,
    p_runtime_execution_id UUID DEFAULT NULL,
    p_failure_code TEXT DEFAULT NULL
)
RETURNS BOOLEAN
LANGUAGE plpgsql SECURITY DEFINER
SET search_path = pg_catalog SET row_security = on
AS $function$
DECLARE changed INTEGER;
BEGIN
    IF (p_expected_state, p_new_state) NOT IN (
        ('CLAIMED', 'DISPATCHING'), ('CLAIMED', 'DENIED'), ('CLAIMED', 'STOPPED'),
        ('DISPATCHING', 'STARTED'), ('DISPATCHING', 'UNRESOLVED'),
        ('UNRESOLVED', 'STARTED'), ('STARTED', 'COMPLETED'), ('STARTED', 'FAILED')
    ) THEN
        RAISE EXCEPTION 'Illegal conversation batch transition' USING ERRCODE = '23514';
    END IF;
    UPDATE business.conversation_batch_groups
    SET dispatch_state = p_new_state,
        source_list_digest = coalesce(source_list_digest, p_source_list_digest),
        request_digest = coalesce(request_digest, p_request_digest),
        runtime_execution_id = coalesce(runtime_execution_id, p_runtime_execution_id),
        dispatch_intent_at = CASE WHEN p_new_state = 'DISPATCHING'
            THEN statement_timestamp() ELSE dispatch_intent_at END,
        started_at = CASE WHEN p_new_state = 'STARTED'
            THEN statement_timestamp() ELSE started_at END,
        terminal_at = CASE WHEN p_new_state IN ('COMPLETED', 'FAILED', 'DENIED', 'STOPPED')
            THEN statement_timestamp() ELSE terminal_at END,
        last_failure_code = left(p_failure_code, 100)
    WHERE tenant_id = p_tenant_id AND batch_id = p_batch_id
      AND lease_owner = p_worker_id AND lease_token = p_fencing_token
      AND dispatch_state = p_expected_state AND lease_expires_at > statement_timestamp()
      AND (
        p_new_state <> 'DISPATCHING'
        OR (
            p_source_list_digest ~ '^sha256:[0-9a-f]{64}$'
            AND p_request_digest ~ '^sha256:[0-9a-f]{64}$'
            AND p_runtime_execution_id IS NOT NULL
        )
      );
    GET DIAGNOSTICS changed = ROW_COUNT;
    RETURN changed = 1;
END
$function$;
ALTER FUNCTION business.transition_conversation_batch(
    UUID, UUID, UUID, BIGINT, TEXT, TEXT, TEXT, TEXT, UUID, TEXT
) OWNER TO bp_owner;
REVOKE ALL ON FUNCTION business.transition_conversation_batch(
    UUID, UUID, UUID, BIGINT, TEXT, TEXT, TEXT, TEXT, UUID, TEXT
) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION business.transition_conversation_batch(
    UUID, UUID, UUID, BIGINT, TEXT, TEXT, TEXT, TEXT, UUID, TEXT
) TO business_app;

DO $membership$
BEGIN
    IF current_setting('waooaw.wc134_batch_dispatch_granted', true) = 'true' THEN
        EXECUTE format('REVOKE bp_owner FROM %I', session_user);
    END IF;
END
$membership$;
COMMIT;
