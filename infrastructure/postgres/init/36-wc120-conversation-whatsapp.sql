-- Implements: architecture/reference/components/conversation-engine-whatsapp-solution-work-component.md §25.2 WC120-P1
-- constitutional_basis: C-005, C-023, C-026, C-059, C-063

ALTER TABLE business.conversations
    ADD COLUMN IF NOT EXISTS environment VARCHAR(32) NOT NULL DEFAULT 'legacy';

ALTER TABLE business.conversation_messages
    ADD COLUMN IF NOT EXISTS environment VARCHAR(32) NOT NULL DEFAULT 'legacy';

ALTER TABLE business.conversation_messages
    ADD COLUMN IF NOT EXISTS contribution_kind VARCHAR(32) NOT NULL DEFAULT 'TEXT',
    ADD COLUMN IF NOT EXISTS dialogue_act VARCHAR(64),
    ADD COLUMN IF NOT EXISTS interaction_context_json JSONB NOT NULL DEFAULT '{}'::JSONB,
    ADD COLUMN IF NOT EXISTS conversation_policy_json JSONB NOT NULL DEFAULT '{}'::JSONB,
    ADD COLUMN IF NOT EXISTS conclusion_json JSONB;

ALTER TABLE business.whatsapp_journey_contacts
    ADD COLUMN IF NOT EXISTS opted_out_at TIMESTAMPTZ;

ALTER TABLE business.continuity_checkpoints
    ADD COLUMN IF NOT EXISTS candidate_payload_digest CHAR(64),
    ADD COLUMN IF NOT EXISTS candidate_context_version VARCHAR(128),
    ADD COLUMN IF NOT EXISTS candidate_current_sequence BIGINT,
    ADD COLUMN IF NOT EXISTS activation_idempotency_key UUID,
    ADD COLUMN IF NOT EXISTS activation_payload_digest CHAR(64),
    ADD COLUMN IF NOT EXISTS revert_idempotency_key UUID,
    ADD COLUMN IF NOT EXISTS revert_request_digest CHAR(64);

CREATE UNIQUE INDEX IF NOT EXISTS conversations_environment_relationship_unique
ON business.conversations (environment, tenant_id, relationship_id);

CREATE UNIQUE INDEX IF NOT EXISTS conversation_messages_environment_sequence_unique
ON business.conversation_messages (environment, tenant_id, relationship_id, sequence);

CREATE TABLE IF NOT EXISTS business.conversation_outbox (
    outbox_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    environment VARCHAR(32) NOT NULL,
    tenant_id UUID NOT NULL,
    relationship_id UUID NOT NULL,
    conversation_id UUID NOT NULL,
    sequence BIGINT NOT NULL,
    owner VARCHAR(64) NOT NULL,
    aggregate_id VARCHAR(128) NOT NULL,
    operation_family VARCHAR(64) NOT NULL,
    idempotency_key UUID NOT NULL,
    payload_digest CHAR(64) NOT NULL,
    payload_reference VARCHAR(256) NOT NULL,
    purpose VARCHAR(64) NOT NULL,
    recipient_binding_digest CHAR(64) NOT NULL,
    template_name VARCHAR(128),
    template_version VARCHAR(64),
    template_locale VARCHAR(35),
    template_category VARCHAR(64),
    state VARCHAR(32) NOT NULL DEFAULT 'PENDING',
    attempt_number INTEGER NOT NULL DEFAULT 0,
    lease_owner VARCHAR(128),
    lease_expires_at TIMESTAMPTZ,
    heartbeat_at TIMESTAMPTZ,
    next_attempt_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    blocked_reason VARCHAR(64),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT conversation_outbox_order_unique
        UNIQUE (environment, tenant_id, relationship_id, owner, aggregate_id, sequence),
    CONSTRAINT conversation_outbox_identity_unique
        UNIQUE (environment, tenant_id, relationship_id, operation_family, idempotency_key),
    CONSTRAINT conversation_outbox_relationship_fk
        FOREIGN KEY (tenant_id, relationship_id)
        REFERENCES business.employment_relationships (tenant_id, relationship_id),
    CONSTRAINT conversation_outbox_conversation_fk
        FOREIGN KEY (conversation_id) REFERENCES business.conversations (conversation_id),
    CONSTRAINT conversation_outbox_digest_check CHECK (payload_digest ~ '^[0-9a-f]{64}$'),
    CONSTRAINT conversation_outbox_recipient_digest_check
        CHECK (recipient_binding_digest ~ '^[0-9a-f]{64}$'),
    CONSTRAINT conversation_outbox_attempt_check CHECK (attempt_number BETWEEN 0 AND 12),
    CONSTRAINT conversation_outbox_state_check CHECK (
        state IN ('PENDING', 'LEASED', 'DISPATCHING', 'DELIVERED', 'UNRESOLVED', 'BLOCKED')
    )
);

CREATE TABLE IF NOT EXISTS business.provider_event_claims (
    claim_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    environment VARCHAR(32) NOT NULL,
    provider VARCHAR(32) NOT NULL,
    app_binding_digest CHAR(64) NOT NULL,
    event_identity VARCHAR(256) NOT NULL,
    payload_digest CHAR(64) NOT NULL,
    state VARCHAR(32) NOT NULL DEFAULT 'CLAIMED',
    result_json JSONB NOT NULL DEFAULT '{}'::JSONB,
    lease_owner UUID,
    lease_expires_at TIMESTAMPTZ,
    received_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    terminal_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,
    legal_hold BOOLEAN NOT NULL DEFAULT FALSE,
    CONSTRAINT provider_event_claim_identity_unique
        UNIQUE (environment, provider, app_binding_digest, event_identity),
    CONSTRAINT provider_event_claim_binding_digest_check
        CHECK (app_binding_digest ~ '^[0-9a-f]{64}$'),
    CONSTRAINT provider_event_claim_payload_digest_check
        CHECK (payload_digest ~ '^[0-9a-f]{64}$'),
    CONSTRAINT provider_event_claim_state_check CHECK (
        state IN ('CLAIMED', 'ACCEPTED', 'REJECTED', 'UNRESOLVED', 'BLOCKED')
    )
);

CREATE TABLE IF NOT EXISTS business.relationship_emergency_stop_latches (
    latch_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    environment VARCHAR(32) NOT NULL,
    tenant_id UUID NOT NULL,
    relationship_id UUID NOT NULL,
    stopped_by_participant_id UUID NOT NULL,
    correlation_id UUID NOT NULL,
    state VARCHAR(32) NOT NULL DEFAULT 'LATCHED',
    evidence_id UUID,
    latched_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    evidence_confirmed_at TIMESTAMPTZ,
    CONSTRAINT relationship_emergency_stop_latch_unique
        UNIQUE (environment, tenant_id, relationship_id),
    CONSTRAINT relationship_emergency_stop_latch_relationship_fk
        FOREIGN KEY (tenant_id, relationship_id)
        REFERENCES business.employment_relationships (tenant_id, relationship_id),
    CONSTRAINT relationship_emergency_stop_latch_state_check
        CHECK (state IN ('LATCHED', 'EVIDENCE_CONFIRMED'))
);

CREATE TABLE IF NOT EXISTS business.conversation_context_observations (
    observation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    environment VARCHAR(32) NOT NULL,
    tenant_id UUID NOT NULL,
    relationship_id UUID NOT NULL,
    owner VARCHAR(64) NOT NULL,
    subject_type VARCHAR(64) NOT NULL,
    observation_type VARCHAR(64) NOT NULL,
    status VARCHAR(32) NOT NULL,
    source_type VARCHAR(64) NOT NULL,
    source_version VARCHAR(128) NOT NULL,
    value_json JSONB NOT NULL,
    source_reference VARCHAR(256) NOT NULL,
    source_digest CHAR(64) NOT NULL,
    revision BIGINT NOT NULL,
    supersedes_observation_id UUID,
    current BOOLEAN NOT NULL DEFAULT TRUE,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at TIMESTAMPTZ,
    CONSTRAINT conversation_context_observation_revision_unique
        UNIQUE (environment, tenant_id, relationship_id, owner, observation_type, revision),
    CONSTRAINT conversation_context_observation_relationship_fk
        FOREIGN KEY (tenant_id, relationship_id)
        REFERENCES business.employment_relationships (tenant_id, relationship_id),
    CONSTRAINT conversation_context_observation_supersedes_fk
        FOREIGN KEY (supersedes_observation_id)
        REFERENCES business.conversation_context_observations (observation_id),
    CONSTRAINT conversation_context_observation_digest_check
        CHECK (source_digest ~ '^[0-9a-f]{64}$'),
    CONSTRAINT conversation_context_observation_revision_check CHECK (revision >= 1),
    CONSTRAINT conversation_context_observation_status_check CHECK (
        status IN ('RESEARCHED', 'INFERRED', 'CONFIRMED', 'DISPUTED', 'STALE', 'SUPERSEDED', 'UNAVAILABLE', 'ERASED')
    ),
    CONSTRAINT conversation_context_observation_no_self_cycle
        CHECK (supersedes_observation_id IS NULL OR supersedes_observation_id <> observation_id)
);

CREATE TABLE IF NOT EXISTS business.conversation_context_summaries (
    summary_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    environment VARCHAR(32) NOT NULL,
    tenant_id UUID NOT NULL,
    relationship_id UUID NOT NULL,
    source_sequence_start BIGINT NOT NULL,
    source_sequence_end BIGINT NOT NULL,
    source_digests_json JSONB NOT NULL,
    derivation_contract_version VARCHAR(64) NOT NULL,
    model_policy_version VARCHAR(64) NOT NULL,
    conversation_policy_version VARCHAR(64) NOT NULL,
    payload_reference VARCHAR(256) NOT NULL,
    current BOOLEAN NOT NULL DEFAULT TRUE,
    invalidation_reason VARCHAR(64),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    invalidated_at TIMESTAMPTZ,
    CONSTRAINT conversation_context_summary_relationship_fk
        FOREIGN KEY (tenant_id, relationship_id)
        REFERENCES business.employment_relationships (tenant_id, relationship_id),
    CONSTRAINT conversation_context_summary_sequence_check
        CHECK (source_sequence_start >= 1 AND source_sequence_end >= source_sequence_start)
);

CREATE TABLE IF NOT EXISTS business.conversation_delivery_observations (
    observation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    environment VARCHAR(32) NOT NULL,
    tenant_id UUID NOT NULL,
    relationship_id UUID NOT NULL,
    message_id UUID NOT NULL,
    provider VARCHAR(32) NOT NULL,
    provider_event_identity VARCHAR(256) NOT NULL,
    provider_reference_digest CHAR(64) NOT NULL,
    delivery_state VARCHAR(32) NOT NULL,
    observation_digest CHAR(64) NOT NULL,
    observed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    retain_until TIMESTAMPTZ NOT NULL,
    legal_hold BOOLEAN NOT NULL DEFAULT FALSE,
    CONSTRAINT conversation_delivery_observation_unique
        UNIQUE (
            environment,
            tenant_id,
            relationship_id,
            message_id,
            provider,
            provider_event_identity
        ),
    CONSTRAINT conversation_delivery_observation_message_fk
        FOREIGN KEY (message_id) REFERENCES business.conversation_messages (message_id),
    CONSTRAINT conversation_delivery_observation_digest_check
        CHECK (provider_reference_digest ~ '^[0-9a-f]{64}$' AND observation_digest ~ '^[0-9a-f]{64}$')
);

CREATE TABLE IF NOT EXISTS business.conversation_data_right_requests (
    request_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    environment VARCHAR(32) NOT NULL,
    tenant_id UUID NOT NULL,
    relationship_id UUID NOT NULL,
    participant_id UUID NOT NULL,
    request_type VARCHAR(32) NOT NULL,
    scope_digest CHAR(64) NOT NULL,
    state VARCHAR(64) NOT NULL DEFAULT 'PENDING_OWNER_DECISION',
    idempotency_key UUID NOT NULL,
    request_digest CHAR(64) NOT NULL,
    owner_decision_reference VARCHAR(256),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT conversation_data_right_identity_unique
        UNIQUE (environment, tenant_id, relationship_id, participant_id, request_type, idempotency_key),
    CONSTRAINT conversation_data_right_relationship_fk
        FOREIGN KEY (tenant_id, relationship_id)
        REFERENCES business.employment_relationships (tenant_id, relationship_id),
    CONSTRAINT conversation_data_right_digest_check
        CHECK (scope_digest ~ '^[0-9a-f]{64}$' AND request_digest ~ '^[0-9a-f]{64}$')
);

CREATE TABLE IF NOT EXISTS business.whatsapp_media (
    media_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    environment VARCHAR(32) NOT NULL,
    tenant_id UUID NOT NULL,
    relationship_id UUID NOT NULL,
    provider_reference_digest CHAR(64) NOT NULL,
    declared_media_type VARCHAR(64) NOT NULL,
    detected_media_type VARCHAR(64) NOT NULL,
    wire_bytes BIGINT NOT NULL,
    expanded_bytes BIGINT NOT NULL,
    duration_seconds INTEGER NOT NULL,
    cpu_milliseconds INTEGER NOT NULL,
    wall_time_milliseconds INTEGER NOT NULL,
    peak_memory_bytes BIGINT NOT NULL,
    recursion_depth INTEGER NOT NULL,
    archive_entries INTEGER NOT NULL,
    page_count INTEGER NOT NULL,
    video_frames INTEGER NOT NULL,
    animation_frames INTEGER NOT NULL,
    image_megapixels INTEGER NOT NULL,
    isolation_confirmed BOOLEAN NOT NULL,
    locale VARCHAR(35) NOT NULL,
    state VARCHAR(32) NOT NULL DEFAULT 'QUARANTINED',
    payload_reference VARCHAR(256),
    scanner_engine_version VARCHAR(64),
    scanner_policy_version VARCHAR(64),
    scanner_signature_version VARCHAR(64),
    scanner_signature_published_at TIMESTAMPTZ,
    verdict_digest CHAR(64),
    derivative_payload_references_json JSONB NOT NULL DEFAULT '[]'::JSONB,
    legal_hold BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    terminal_at TIMESTAMPTZ,
    delete_after TIMESTAMPTZ NOT NULL,
    CONSTRAINT whatsapp_media_identity_unique
        UNIQUE (environment, tenant_id, relationship_id, provider_reference_digest),
    CONSTRAINT whatsapp_media_relationship_fk
        FOREIGN KEY (tenant_id, relationship_id)
        REFERENCES business.employment_relationships (tenant_id, relationship_id),
    CONSTRAINT whatsapp_media_digest_check CHECK (provider_reference_digest ~ '^[0-9a-f]{64}$'),
    CONSTRAINT whatsapp_media_size_check CHECK (
        wire_bytes BETWEEN 1 AND 5242880
        AND expanded_bytes BETWEEN wire_bytes AND 104857600
        AND expanded_bytes <= wire_bytes * 10
    ),
    CONSTRAINT whatsapp_media_duration_check CHECK (duration_seconds BETWEEN 1 AND 120),
    CONSTRAINT whatsapp_media_resource_check CHECK (
        cpu_milliseconds BETWEEN 0 AND 5000
        AND wall_time_milliseconds BETWEEN 0 AND 10000
        AND peak_memory_bytes BETWEEN 0 AND 268435456
        AND recursion_depth BETWEEN 0 AND 16
        AND archive_entries = 0
        AND page_count = 0
        AND video_frames = 0
        AND animation_frames = 0
        AND image_megapixels BETWEEN 0 AND 40
        AND isolation_confirmed
    ),
    CONSTRAINT whatsapp_media_locale_check CHECK (locale = 'en-IN'),
    CONSTRAINT whatsapp_media_verdict_digest_check
        CHECK (verdict_digest IS NULL OR verdict_digest ~ '^[0-9a-f]{64}$'),
    CONSTRAINT whatsapp_media_state_check CHECK (
        state IN ('QUARANTINED', 'SCANNING', 'CLEAN', 'REJECTED', 'EXPIRED', 'ERASED')
    )
);

CREATE TABLE IF NOT EXISTS business.conversation_migration_watermarks (
    migration_id VARCHAR(128) NOT NULL,
    environment VARCHAR(32) NOT NULL,
    owner VARCHAR(64) NOT NULL,
    last_primary_key VARCHAR(128) NOT NULL,
    batch_size INTEGER NOT NULL,
    state VARCHAR(32) NOT NULL DEFAULT 'PENDING',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (migration_id, environment, owner),
    CONSTRAINT conversation_migration_batch_check CHECK (batch_size BETWEEN 1 AND 1000),
    CONSTRAINT conversation_migration_state_check CHECK (
        state IN ('PENDING', 'RUNNING', 'VERIFIED', 'BLOCKED', 'COMPLETE')
    )
);

CREATE TABLE IF NOT EXISTS business.conversation_operational_signals (
    signal_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    environment VARCHAR(32) NOT NULL,
    category VARCHAR(64) NOT NULL,
    code VARCHAR(64) NOT NULL,
    state VARCHAR(16) NOT NULL DEFAULT 'OPEN',
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    resolved_at TIMESTAMPTZ,
    CONSTRAINT conversation_operational_signal_state_check
        CHECK (state IN ('OPEN', 'ACKNOWLEDGED', 'RESOLVED'))
);

ALTER TABLE business.conversation_outbox ENABLE ROW LEVEL SECURITY;
ALTER TABLE business.conversation_outbox FORCE ROW LEVEL SECURITY;
ALTER TABLE business.conversation_context_observations ENABLE ROW LEVEL SECURITY;
ALTER TABLE business.conversation_context_observations FORCE ROW LEVEL SECURITY;
ALTER TABLE business.conversation_context_summaries ENABLE ROW LEVEL SECURITY;
ALTER TABLE business.conversation_context_summaries FORCE ROW LEVEL SECURITY;
ALTER TABLE business.conversation_delivery_observations ENABLE ROW LEVEL SECURITY;
ALTER TABLE business.conversation_delivery_observations FORCE ROW LEVEL SECURITY;
ALTER TABLE business.conversation_data_right_requests ENABLE ROW LEVEL SECURITY;
ALTER TABLE business.conversation_data_right_requests FORCE ROW LEVEL SECURITY;
ALTER TABLE business.whatsapp_media ENABLE ROW LEVEL SECURITY;
ALTER TABLE business.whatsapp_media FORCE ROW LEVEL SECURITY;
ALTER TABLE business.relationship_emergency_stop_latches ENABLE ROW LEVEL SECURITY;
ALTER TABLE business.relationship_emergency_stop_latches FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS conversation_outbox_tenant_isolation ON business.conversation_outbox;
DROP POLICY IF EXISTS conversation_outbox_tenant_isolation ON business.conversation_outbox;
CREATE POLICY conversation_outbox_tenant_isolation ON business.conversation_outbox
USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', TRUE), '')::UUID)
WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', TRUE), '')::UUID);

DROP POLICY IF EXISTS conversation_context_observations_tenant_isolation
ON business.conversation_context_observations;
DROP POLICY IF EXISTS conversation_context_observations_tenant_isolation ON business.conversation_context_observations;
CREATE POLICY conversation_context_observations_tenant_isolation
ON business.conversation_context_observations
USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', TRUE), '')::UUID)
WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', TRUE), '')::UUID);

DROP POLICY IF EXISTS conversation_context_summaries_tenant_isolation
ON business.conversation_context_summaries;
DROP POLICY IF EXISTS conversation_context_summaries_tenant_isolation ON business.conversation_context_summaries;
CREATE POLICY conversation_context_summaries_tenant_isolation
ON business.conversation_context_summaries
USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', TRUE), '')::UUID)
WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', TRUE), '')::UUID);

DROP POLICY IF EXISTS conversation_delivery_observations_tenant_isolation
ON business.conversation_delivery_observations;
DROP POLICY IF EXISTS conversation_delivery_observations_tenant_isolation ON business.conversation_delivery_observations;
CREATE POLICY conversation_delivery_observations_tenant_isolation
ON business.conversation_delivery_observations
USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', TRUE), '')::UUID)
WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', TRUE), '')::UUID);

DROP POLICY IF EXISTS conversation_data_right_requests_tenant_isolation
ON business.conversation_data_right_requests;
DROP POLICY IF EXISTS conversation_data_right_requests_tenant_isolation ON business.conversation_data_right_requests;
CREATE POLICY conversation_data_right_requests_tenant_isolation
ON business.conversation_data_right_requests
USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', TRUE), '')::UUID)
WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', TRUE), '')::UUID);

DROP POLICY IF EXISTS whatsapp_media_tenant_isolation ON business.whatsapp_media;
DROP POLICY IF EXISTS whatsapp_media_tenant_isolation ON business.whatsapp_media;
CREATE POLICY whatsapp_media_tenant_isolation ON business.whatsapp_media
USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', TRUE), '')::UUID)
WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', TRUE), '')::UUID);

DROP POLICY IF EXISTS relationship_emergency_stop_latches_tenant_isolation
ON business.relationship_emergency_stop_latches;
DROP POLICY IF EXISTS relationship_emergency_stop_latches_tenant_isolation ON business.relationship_emergency_stop_latches;
CREATE POLICY relationship_emergency_stop_latches_tenant_isolation
ON business.relationship_emergency_stop_latches
USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', TRUE), '')::UUID)
WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', TRUE), '')::UUID);
