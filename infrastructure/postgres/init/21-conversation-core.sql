-- Implements: architecture/reference/components/conversation-core.md § Durable Conversation Projection
-- constitutional_basis: C-005, C-023, C-026, C-059, C-063

CREATE TABLE IF NOT EXISTS business.conversations (
    conversation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    relationship_id UUID NOT NULL,
    next_message_sequence BIGINT NOT NULL DEFAULT 1,
    next_event_sequence BIGINT NOT NULL DEFAULT 1,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT conversations_relationship_unique UNIQUE (tenant_id, relationship_id),
    CONSTRAINT conversations_relationship_fk FOREIGN KEY (tenant_id, relationship_id)
    REFERENCES business.employment_relationships (tenant_id, relationship_id),
    CONSTRAINT conversations_message_sequence_check CHECK (next_message_sequence >= 1),
    CONSTRAINT conversations_event_sequence_check CHECK (next_event_sequence >= 1)
);

CREATE TABLE IF NOT EXISTS business.conversation_messages (
    message_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    conversation_id UUID NOT NULL,
    relationship_id UUID NOT NULL,
    sequence BIGINT NOT NULL, -- noqa: RF04
    schema_version VARCHAR(16) NOT NULL DEFAULT '1.0',
    actor VARCHAR(16) NOT NULL,
    channel VARCHAR(16) NOT NULL,
    content_json JSONB NOT NULL,
    cards_json JSONB NOT NULL DEFAULT '[]'::JSONB,
    delivery_state VARCHAR(16) NOT NULL,
    processing_state VARCHAR(16) NOT NULL,
    evidence_state VARCHAR(16) NOT NULL,
    evidence_record_id UUID,
    partial BOOLEAN NOT NULL DEFAULT FALSE, -- noqa: RF04
    completion_reason VARCHAR(32),
    retry_of_message_id UUID,
    client_message_id UUID,
    accepted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ,
    CONSTRAINT conversation_messages_sequence_unique UNIQUE (tenant_id, relationship_id, sequence),
    CONSTRAINT conversation_messages_client_unique UNIQUE (tenant_id, relationship_id, client_message_id),
    CONSTRAINT conversation_messages_conversation_fk FOREIGN KEY (conversation_id)
    REFERENCES business.conversations (conversation_id),
    CONSTRAINT conversation_messages_relationship_fk FOREIGN KEY (tenant_id, relationship_id)
    REFERENCES business.employment_relationships (tenant_id, relationship_id),
    CONSTRAINT conversation_messages_retry_fk FOREIGN KEY (retry_of_message_id)
    REFERENCES business.conversation_messages (message_id),
    CONSTRAINT conversation_messages_sequence_check CHECK (sequence >= 1),
    CONSTRAINT conversation_messages_schema_check CHECK (schema_version = '1.0'),
    CONSTRAINT conversation_messages_actor_check CHECK (actor IN ('CUSTOMER', 'PROFESSIONAL', 'SYSTEM')),
    CONSTRAINT conversation_messages_channel_check CHECK (channel IN ('WEB', 'WHATSAPP', 'SYSTEM')),
    CONSTRAINT conversation_messages_delivery_check CHECK (delivery_state IN ('ACCEPTED', 'FAILED', 'UNRESOLVED')),
    CONSTRAINT conversation_messages_processing_check CHECK (
        processing_state IN ('NOT_STARTED', 'QUEUED', 'RUNNING', 'COMPLETED', 'FAILED', 'CANCELLED', 'STOPPED')
    ),
    CONSTRAINT conversation_messages_evidence_check CHECK (
        (evidence_state = 'RECORDED' AND evidence_record_id IS NOT NULL)
        OR (evidence_state IN ('NOT_APPLICABLE', 'PENDING', 'FAILED') AND evidence_record_id IS NULL)
    ),
    CONSTRAINT conversation_messages_completion_check CHECK (
        completion_reason IS NULL
        OR completion_reason IN ('COMPLETE', 'PARTIAL_FAILURE', 'CANCELLED', 'EMERGENCY_STOPPED')
    )
);

CREATE TABLE IF NOT EXISTS business.conversation_executions (
    execution_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    conversation_id UUID NOT NULL,
    relationship_id UUID NOT NULL,
    message_id UUID NOT NULL,
    processing_state VARCHAR(16) NOT NULL DEFAULT 'QUEUED',
    partial BOOLEAN NOT NULL DEFAULT FALSE, -- noqa: RF04
    completion_reason VARCHAR(32),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT conversation_executions_message_unique UNIQUE (tenant_id, relationship_id, message_id),
    CONSTRAINT conversation_executions_message_fk FOREIGN KEY (message_id)
    REFERENCES business.conversation_messages (message_id),
    CONSTRAINT conversation_executions_state_check CHECK (
        processing_state IN ('QUEUED', 'RUNNING', 'COMPLETED', 'FAILED', 'CANCELLED', 'STOPPED')
    ),
    CONSTRAINT conversation_executions_completion_check CHECK (
        completion_reason IS NULL
        OR completion_reason IN ('COMPLETE', 'PARTIAL_FAILURE', 'CANCELLED', 'EMERGENCY_STOPPED')
    )
);

CREATE TABLE IF NOT EXISTS business.conversation_idempotency_outcomes (
    idempotency_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    relationship_id UUID NOT NULL,
    actor_participant_id UUID NOT NULL,
    operation_family VARCHAR(32) NOT NULL,
    idempotency_key UUID NOT NULL,
    request_hash CHAR(64) NOT NULL,
    message_id UUID,
    execution_id UUID,
    outcome VARCHAR(16) NOT NULL,
    response_json JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT conversation_idempotency_scope_unique
    UNIQUE (tenant_id, relationship_id, actor_participant_id, operation_family, idempotency_key),
    CONSTRAINT conversation_idempotency_relationship_fk FOREIGN KEY (tenant_id, relationship_id)
    REFERENCES business.employment_relationships (tenant_id, relationship_id),
    CONSTRAINT conversation_idempotency_hash_check CHECK (request_hash ~ '^[0-9a-f]{64}$'),
    CONSTRAINT conversation_idempotency_outcome_check CHECK (
        outcome IN ('ACCEPTED', 'REPLAYED', 'FAILED', 'UNRESOLVED', 'CANCELLED')
    )
);

CREATE TABLE IF NOT EXISTS business.conversation_read_positions (
    tenant_id UUID NOT NULL,
    relationship_id UUID NOT NULL,
    participant_id UUID NOT NULL,
    last_read_message_id UUID NOT NULL,
    last_read_sequence BIGINT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, relationship_id, participant_id),
    CONSTRAINT conversation_read_positions_relationship_fk FOREIGN KEY (tenant_id, relationship_id)
    REFERENCES business.employment_relationships (tenant_id, relationship_id),
    CONSTRAINT conversation_read_positions_message_fk FOREIGN KEY (last_read_message_id)
    REFERENCES business.conversation_messages (message_id),
    CONSTRAINT conversation_read_positions_sequence_check CHECK (last_read_sequence >= 1)
);

CREATE TABLE IF NOT EXISTS business.conversation_events (
    event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    conversation_id UUID NOT NULL,
    relationship_id UUID NOT NULL,
    sequence BIGINT NOT NULL, -- noqa: RF04
    event_type VARCHAR(32) NOT NULL,
    message_id UUID,
    execution_id UUID,
    data_json JSONB NOT NULL,
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT conversation_events_sequence_unique UNIQUE (tenant_id, relationship_id, sequence),
    CONSTRAINT conversation_events_conversation_fk FOREIGN KEY (conversation_id)
    REFERENCES business.conversations (conversation_id),
    CONSTRAINT conversation_events_sequence_check CHECK (sequence >= 1),
    CONSTRAINT conversation_events_type_check CHECK (event_type IN (
        'message.accepted', 'processing.started', 'response.delta', 'card.upserted',
        'message.completed', 'message.failed', 'stream.cancelled', 'stop.applied',
        'reconciliation.required', 'heartbeat'
    ))
);

CREATE INDEX IF NOT EXISTS idx_conversation_messages_timeline
ON business.conversation_messages (tenant_id, relationship_id, sequence);
CREATE INDEX IF NOT EXISTS idx_conversation_events_replay
ON business.conversation_events (tenant_id, relationship_id, sequence);
CREATE INDEX IF NOT EXISTS idx_conversation_idempotency_lookup
ON business.conversation_idempotency_outcomes
(tenant_id, relationship_id, actor_participant_id, operation_family, idempotency_key);

ALTER TABLE business.conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE business.conversations FORCE ROW LEVEL SECURITY;
ALTER TABLE business.conversation_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE business.conversation_messages FORCE ROW LEVEL SECURITY;
ALTER TABLE business.conversation_executions ENABLE ROW LEVEL SECURITY;
ALTER TABLE business.conversation_executions FORCE ROW LEVEL SECURITY;
ALTER TABLE business.conversation_idempotency_outcomes ENABLE ROW LEVEL SECURITY;
ALTER TABLE business.conversation_idempotency_outcomes FORCE ROW LEVEL SECURITY;
ALTER TABLE business.conversation_read_positions ENABLE ROW LEVEL SECURITY;
ALTER TABLE business.conversation_read_positions FORCE ROW LEVEL SECURITY;
ALTER TABLE business.conversation_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE business.conversation_events FORCE ROW LEVEL SECURITY;

CREATE POLICY conversations_tenant_isolation ON business.conversations
USING (tenant_id = nullif(current_setting('app.current_tenant_id', TRUE), '')::UUID)
WITH CHECK (tenant_id = nullif(current_setting('app.current_tenant_id', TRUE), '')::UUID);
CREATE POLICY conversation_messages_tenant_isolation ON business.conversation_messages
USING (tenant_id = nullif(current_setting('app.current_tenant_id', TRUE), '')::UUID)
WITH CHECK (tenant_id = nullif(current_setting('app.current_tenant_id', TRUE), '')::UUID);
CREATE POLICY conversation_executions_tenant_isolation ON business.conversation_executions
USING (tenant_id = nullif(current_setting('app.current_tenant_id', TRUE), '')::UUID)
WITH CHECK (tenant_id = nullif(current_setting('app.current_tenant_id', TRUE), '')::UUID);
CREATE POLICY conversation_idempotency_tenant_isolation ON business.conversation_idempotency_outcomes
USING (tenant_id = nullif(current_setting('app.current_tenant_id', TRUE), '')::UUID)
WITH CHECK (tenant_id = nullif(current_setting('app.current_tenant_id', TRUE), '')::UUID);
CREATE POLICY conversation_read_positions_tenant_isolation ON business.conversation_read_positions
USING (tenant_id = nullif(current_setting('app.current_tenant_id', TRUE), '')::UUID)
WITH CHECK (tenant_id = nullif(current_setting('app.current_tenant_id', TRUE), '')::UUID);
CREATE POLICY conversation_events_tenant_isolation ON business.conversation_events
USING (tenant_id = nullif(current_setting('app.current_tenant_id', TRUE), '')::UUID)
WITH CHECK (tenant_id = nullif(current_setting('app.current_tenant_id', TRUE), '')::UUID);

GRANT SELECT, INSERT, UPDATE ON business.conversations TO business_app;
GRANT SELECT, INSERT, UPDATE ON business.conversation_messages TO business_app;
GRANT SELECT, INSERT, UPDATE ON business.conversation_executions TO business_app;
GRANT SELECT, INSERT, UPDATE ON business.conversation_idempotency_outcomes TO business_app;
GRANT SELECT, INSERT, UPDATE ON business.conversation_read_positions TO business_app;
GRANT SELECT, INSERT ON business.conversation_events TO business_app;
