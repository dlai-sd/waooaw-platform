-- Implements: work-contracts/WC-096-conversational-customer-portal.md §5
-- constitutional_basis: C-005, C-026, C-049, C-059, C-063

CREATE TABLE IF NOT EXISTS business.portal_interaction_contexts (
    context_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    participant_id UUID NOT NULL,
    next_message_sequence BIGINT NOT NULL DEFAULT 1,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT portal_interaction_context_unique UNIQUE (tenant_id, participant_id),
    CONSTRAINT portal_interaction_sequence_check CHECK (next_message_sequence >= 1)
);

CREATE TABLE IF NOT EXISTS business.portal_interaction_messages (
    message_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    context_id UUID NOT NULL,
    participant_id UUID NOT NULL,
    sequence BIGINT NOT NULL, -- noqa: RF04
    actor VARCHAR(16) NOT NULL,
    content_json JSONB NOT NULL,
    capabilities_json JSONB NOT NULL DEFAULT '[]'::JSONB,
    current_surface VARCHAR(32) NOT NULL,
    client_message_id UUID,
    accepted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT portal_interaction_message_sequence_unique UNIQUE (tenant_id, participant_id, sequence),
    CONSTRAINT portal_interaction_message_client_unique UNIQUE (tenant_id, participant_id, client_message_id),
    CONSTRAINT portal_interaction_message_context_fk FOREIGN KEY (context_id)
    REFERENCES business.portal_interaction_contexts (context_id),
    CONSTRAINT portal_interaction_message_actor_check CHECK (actor IN ('CUSTOMER', 'GUIDE')),
    CONSTRAINT portal_interaction_message_surface_check CHECK (
        current_surface IN (
            'MARKETPLACE', 'MY_AGENTS', 'ALERTS', 'RELATIONSHIP',
            'PERFORMANCE', 'BILLING', 'SETTINGS', 'PROFILE'
        )
    ),
    CONSTRAINT portal_interaction_message_sequence_check CHECK (sequence >= 1)
);

CREATE TABLE IF NOT EXISTS business.portal_interaction_idempotency_outcomes (
    idempotency_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    participant_id UUID NOT NULL,
    idempotency_key UUID NOT NULL,
    request_hash CHAR(64) NOT NULL,
    response_json JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT portal_interaction_idempotency_unique UNIQUE (tenant_id, participant_id, idempotency_key),
    CONSTRAINT portal_interaction_idempotency_hash_check CHECK (request_hash ~ '^[0-9a-f]{64}$')
);

CREATE INDEX IF NOT EXISTS idx_portal_interaction_timeline
ON business.portal_interaction_messages (tenant_id, participant_id, sequence);

ALTER TABLE business.portal_interaction_contexts ENABLE ROW LEVEL SECURITY;
ALTER TABLE business.portal_interaction_contexts FORCE ROW LEVEL SECURITY;
ALTER TABLE business.portal_interaction_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE business.portal_interaction_messages FORCE ROW LEVEL SECURITY;
ALTER TABLE business.portal_interaction_idempotency_outcomes ENABLE ROW LEVEL SECURITY;
ALTER TABLE business.portal_interaction_idempotency_outcomes FORCE ROW LEVEL SECURITY;

CREATE POLICY portal_interaction_contexts_tenant_isolation ON business.portal_interaction_contexts
USING (tenant_id = nullif(current_setting('app.current_tenant_id', TRUE), '')::UUID)
WITH CHECK (tenant_id = nullif(current_setting('app.current_tenant_id', TRUE), '')::UUID);
CREATE POLICY portal_interaction_messages_tenant_isolation ON business.portal_interaction_messages
USING (tenant_id = nullif(current_setting('app.current_tenant_id', TRUE), '')::UUID)
WITH CHECK (tenant_id = nullif(current_setting('app.current_tenant_id', TRUE), '')::UUID);
CREATE POLICY portal_interaction_idempotency_tenant_isolation ON business.portal_interaction_idempotency_outcomes
USING (tenant_id = nullif(current_setting('app.current_tenant_id', TRUE), '')::UUID)
WITH CHECK (tenant_id = nullif(current_setting('app.current_tenant_id', TRUE), '')::UUID);

GRANT SELECT, INSERT, UPDATE ON business.portal_interaction_contexts TO business_app;
GRANT SELECT, INSERT ON business.portal_interaction_messages TO business_app;
GRANT SELECT, INSERT ON business.portal_interaction_idempotency_outcomes TO business_app;
