-- Implements: architecture/reference/product/ae01-relationship-data-contract.md § Migration 22
-- constitutional_basis: C-005, C-007, C-023, C-026, C-059, C-063
-- WC-060 Task WC060-01: channel bindings, continuity checkpoints, delivery acknowledgements, deduplication

DO $$ BEGIN
    IF to_regclass('business.whatsapp_journey_contacts') IS NOT NULL THEN
        ALTER TABLE business.whatsapp_journey_contacts
            ADD COLUMN IF NOT EXISTS mpin_hash CHAR(64),
            ADD COLUMN IF NOT EXISTS mpin_failed_attempts INTEGER NOT NULL DEFAULT 0,
            ADD COLUMN IF NOT EXISTS mpin_locked_until TIMESTAMPTZ;
        IF NOT EXISTS (
            SELECT 1 FROM pg_constraint WHERE conname = 'whatsapp_journey_contacts_mpin_hash_check'
        ) THEN
            ALTER TABLE business.whatsapp_journey_contacts
                ADD CONSTRAINT whatsapp_journey_contacts_mpin_hash_check
                CHECK (mpin_hash IS NULL OR mpin_hash ~ '^[0-9a-f]{64}$');
        END IF;
        IF NOT EXISTS (
            SELECT 1 FROM pg_constraint WHERE conname = 'whatsapp_journey_contacts_mpin_attempts_check'
        ) THEN
            ALTER TABLE business.whatsapp_journey_contacts
                ADD CONSTRAINT whatsapp_journey_contacts_mpin_attempts_check
                CHECK (mpin_failed_attempts BETWEEN 0 AND 3);
        END IF;
    END IF;
END $$;

-- ── channel_bindings ────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS business.relationship_evidence_exports (
    export_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    relationship_id UUID NOT NULL,
    participant_id UUID NOT NULL,
    participant_role VARCHAR(32) NOT NULL,
    idempotency_key UUID NOT NULL,
    material_request_hash CHAR(64) NOT NULL,
    document_json JSONB NOT NULL,
    document_sha256 CHAR(64) NOT NULL,
    evidence_id UUID NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    UNIQUE (tenant_id, relationship_id, idempotency_key),
    FOREIGN KEY (tenant_id, relationship_id)
        REFERENCES business.employment_relationships (tenant_id, relationship_id),
    CHECK (expires_at = created_at + INTERVAL '15 minutes')
);

ALTER TABLE business.relationship_evidence_exports ENABLE ROW LEVEL SECURITY;
ALTER TABLE business.relationship_evidence_exports FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS relationship_evidence_exports_tenant_isolation ON business.relationship_evidence_exports;
CREATE POLICY relationship_evidence_exports_tenant_isolation ON business.relationship_evidence_exports
    USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', TRUE), '')::UUID)
    WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', TRUE), '')::UUID);
GRANT SELECT, INSERT ON business.relationship_evidence_exports TO business_app;

CREATE TABLE IF NOT EXISTS business.channel_bindings (
    binding_id              UUID         NOT NULL DEFAULT gen_random_uuid(),
    tenant_id               UUID         NOT NULL,
    relationship_id         UUID         NOT NULL,
    participant_id          UUID         NOT NULL,
    participant_role        VARCHAR(32)  NOT NULL,
    channel                 VARCHAR(16)  NOT NULL,
    external_subject_hash   CHAR(64)     NOT NULL,
    conversation_id         VARCHAR(256) NOT NULL,
    assurance_level         VARCHAR(40)  NOT NULL,
    status                  VARCHAR(16)  NOT NULL DEFAULT 'PREPARED',
    prepared_evidence_id    UUID         NOT NULL,
    bound_evidence_id       UUID,
    revoked_evidence_id     UUID,
    created_at              TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    bound_at                TIMESTAMPTZ,
    revoked_at              TIMESTAMPTZ,
    CONSTRAINT channel_bindings_pk PRIMARY KEY (binding_id),
    CONSTRAINT channel_bindings_tenant_unique UNIQUE (tenant_id, binding_id),
    CONSTRAINT channel_bindings_relationship_fk
        FOREIGN KEY (tenant_id, relationship_id)
        REFERENCES business.employment_relationships (tenant_id, relationship_id),
    CONSTRAINT channel_bindings_status_check
        CHECK (status IN ('PREPARED', 'ACTIVE', 'REVOKED', 'EXPIRED')),
    CONSTRAINT channel_bindings_role_check
        CHECK (participant_role IN ('EVALUATOR', 'EMPLOYER', 'OUTCOME_OWNER', 'RELATIONSHIP_MANAGER')),
    CONSTRAINT channel_bindings_channel_check
        CHECK (channel IN ('WHATSAPP', 'WEB')),
    CONSTRAINT channel_bindings_assurance_check
        CHECK (assurance_level IN (
            'TIER_1_PHONE_IDENTITY',
            'TIER_2_EXPLICIT_CONFIRMATION',
            'TIER_3_MPIN',
            'TIER_4_PORTAL_FRESH'
        )),
    CONSTRAINT channel_bindings_hash_check
        CHECK (external_subject_hash ~ '^[0-9a-f]{64}$'),
    -- ACTIVE requires bound_evidence_id and bound_at
    CONSTRAINT channel_bindings_active_fields CHECK (
        status != 'ACTIVE'
        OR (bound_evidence_id IS NOT NULL AND bound_at IS NOT NULL)
    ),
    -- REVOKED requires revoked_evidence_id and revoked_at
    CONSTRAINT channel_bindings_revoked_fields CHECK (
        status != 'REVOKED'
        OR (revoked_evidence_id IS NOT NULL AND revoked_at IS NOT NULL)
    ),
    -- EXPIRED requires revoked_at
    CONSTRAINT channel_bindings_expired_fields CHECK (
        status != 'EXPIRED'
        OR revoked_at IS NOT NULL
    ),
    -- PREPARED has no resolution fields
    CONSTRAINT channel_bindings_prepared_fields CHECK (
        status != 'PREPARED'
        OR (bound_evidence_id IS NULL AND bound_at IS NULL
            AND revoked_evidence_id IS NULL AND revoked_at IS NULL)
    )
);

-- Prevent competing live bindings for same participant + channel
CREATE UNIQUE INDEX IF NOT EXISTS channel_bindings_live_unique
    ON business.channel_bindings (tenant_id, relationship_id, participant_id, channel)
    WHERE status IN ('PREPARED', 'ACTIVE');

CREATE INDEX IF NOT EXISTS channel_bindings_relationship_status_idx
    ON business.channel_bindings (tenant_id, relationship_id, status);
CREATE INDEX IF NOT EXISTS channel_bindings_conversation_idx
    ON business.channel_bindings (tenant_id, conversation_id);

ALTER TABLE business.channel_bindings ENABLE ROW LEVEL SECURITY;
ALTER TABLE business.channel_bindings FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS channel_bindings_tenant_isolation ON business.channel_bindings;
CREATE POLICY channel_bindings_tenant_isolation ON business.channel_bindings
    USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', TRUE), '')::UUID)
    WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', TRUE), '')::UUID);

GRANT SELECT, INSERT ON business.channel_bindings TO business_app;
GRANT UPDATE (status, bound_evidence_id, bound_at, revoked_evidence_id, revoked_at)
    ON business.channel_bindings TO business_app;

-- Transition trigger: only PREPARED → ACTIVE|REVOKED|EXPIRED and ACTIVE → REVOKED|EXPIRED
CREATE OR REPLACE FUNCTION business.channel_binding_transition_guard()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP = 'UPDATE' THEN
        -- Block changes to immutable identity fields
        IF OLD.tenant_id        != NEW.tenant_id
        OR OLD.relationship_id  != NEW.relationship_id
        OR OLD.participant_id   != NEW.participant_id
        OR OLD.participant_role != NEW.participant_role
        OR OLD.channel          != NEW.channel
        OR OLD.assurance_level  != NEW.assurance_level
        OR OLD.prepared_evidence_id != NEW.prepared_evidence_id
        THEN
            RAISE EXCEPTION 'channel_binding identity fields are immutable';
        END IF;
        -- Block reopening terminal state
        IF OLD.status IN ('REVOKED', 'EXPIRED') THEN
            RAISE EXCEPTION 'channel_binding % is terminal and cannot be updated', OLD.binding_id;
        END IF;
        -- Only legal transitions
        IF NOT (
            (OLD.status = 'PREPARED' AND NEW.status IN ('ACTIVE', 'REVOKED', 'EXPIRED'))
            OR (OLD.status = 'ACTIVE'   AND NEW.status IN ('REVOKED', 'EXPIRED'))
            OR OLD.status = NEW.status
        ) THEN
            RAISE EXCEPTION 'illegal channel_binding transition % → %', OLD.status, NEW.status;
        END IF;
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS channel_binding_transition ON business.channel_bindings;
CREATE TRIGGER channel_binding_transition
    BEFORE UPDATE ON business.channel_bindings
    FOR EACH ROW EXECUTE FUNCTION business.channel_binding_transition_guard();

-- ── continuity_checkpoints ───────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS business.continuity_checkpoints (
    checkpoint_id               UUID         NOT NULL DEFAULT gen_random_uuid(),
    tenant_id                   UUID         NOT NULL,
    relationship_id             UUID         NOT NULL,
    source_binding_id           UUID         NOT NULL,
    target_binding_id           UUID         NOT NULL,
    continuity_envelope_hash    CHAR(64)     NOT NULL,
    continuity_envelope         JSONB,
    material_request_hash       CHAR(64)     NOT NULL,
    causal_marker               UUID         NOT NULL,
    sequence_number             BIGINT       NOT NULL,
    idempotency_key             UUID         NOT NULL,
    status                      VARCHAR(16)  NOT NULL DEFAULT 'PREPARED',
    prepared_evidence_id        UUID         NOT NULL,
    resolution_evidence_id      UUID,
    prepared_at                 TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    expires_at                  TIMESTAMPTZ  NOT NULL DEFAULT (NOW() + INTERVAL '15 minutes'),
    resolved_at                 TIMESTAMPTZ,
    CONSTRAINT continuity_checkpoints_pk PRIMARY KEY (checkpoint_id),
    CONSTRAINT continuity_checkpoints_tenant_unique UNIQUE (tenant_id, checkpoint_id),
    CONSTRAINT continuity_checkpoints_relationship_fk
        FOREIGN KEY (tenant_id, relationship_id)
        REFERENCES business.employment_relationships (tenant_id, relationship_id),
    CONSTRAINT continuity_checkpoints_source_binding_fk
        FOREIGN KEY (tenant_id, source_binding_id)
        REFERENCES business.channel_bindings (tenant_id, binding_id),
    CONSTRAINT continuity_checkpoints_target_binding_fk
        FOREIGN KEY (tenant_id, target_binding_id)
        REFERENCES business.channel_bindings (tenant_id, binding_id),
    CONSTRAINT continuity_checkpoints_status_check
        CHECK (status IN ('PREPARED', 'COMMITTED', 'REVERTED', 'CONFLICT', 'EXPIRED')),
    CONSTRAINT continuity_checkpoints_envelope_hash_check
        CHECK (continuity_envelope_hash ~ '^[0-9a-f]{64}$'),
    CONSTRAINT continuity_checkpoints_material_hash_check
        CHECK (material_request_hash ~ '^[0-9a-f]{64}$'),
    CONSTRAINT continuity_checkpoints_sequence_check
        CHECK (sequence_number > 0),
    CONSTRAINT continuity_checkpoints_distinct_bindings_check
        CHECK (source_binding_id != target_binding_id),
    CONSTRAINT continuity_checkpoints_expiry_check
        CHECK (expires_at = prepared_at + INTERVAL '15 minutes'),
    -- PREPARED: no resolution fields
    CONSTRAINT continuity_checkpoints_prepared_fields CHECK (
        status != 'PREPARED'
        OR (resolution_evidence_id IS NULL AND resolved_at IS NULL)
    ),
    -- Terminal states require resolution fields
    CONSTRAINT continuity_checkpoints_terminal_fields CHECK (
        status IN ('PREPARED')
        OR (resolution_evidence_id IS NOT NULL AND resolved_at IS NOT NULL)
    ),
    -- Idempotency: unique within tenant + relationship
    CONSTRAINT continuity_checkpoints_idempotency_unique
        UNIQUE (tenant_id, relationship_id, idempotency_key),
    CONSTRAINT continuity_checkpoints_causal_unique
        UNIQUE (tenant_id, relationship_id, causal_marker),
    CONSTRAINT continuity_checkpoints_sequence_unique
        UNIQUE (tenant_id, relationship_id, sequence_number)
);

CREATE INDEX IF NOT EXISTS continuity_checkpoints_sequence_idx
    ON business.continuity_checkpoints (tenant_id, relationship_id, sequence_number);
CREATE INDEX IF NOT EXISTS continuity_checkpoints_status_idx
    ON business.continuity_checkpoints (tenant_id, relationship_id, status);
CREATE INDEX IF NOT EXISTS continuity_checkpoints_target_binding_idx
    ON business.continuity_checkpoints (tenant_id, target_binding_id, status);

ALTER TABLE business.continuity_checkpoints ENABLE ROW LEVEL SECURITY;
ALTER TABLE business.continuity_checkpoints FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS continuity_checkpoints_tenant_isolation ON business.continuity_checkpoints;
CREATE POLICY continuity_checkpoints_tenant_isolation ON business.continuity_checkpoints
    USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', TRUE), '')::UUID)
    WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', TRUE), '')::UUID);

GRANT SELECT, INSERT ON business.continuity_checkpoints TO business_app;
GRANT UPDATE (status, resolution_evidence_id, resolved_at)
    ON business.continuity_checkpoints TO business_app;

-- Transition trigger: PREPARED → COMMITTED|REVERTED|CONFLICT|EXPIRED only
CREATE OR REPLACE FUNCTION business.continuity_checkpoint_transition_guard()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP = 'UPDATE' THEN
        -- Block changes to immutable fields
        IF OLD.tenant_id             != NEW.tenant_id
        OR OLD.relationship_id       != NEW.relationship_id
        OR OLD.source_binding_id     != NEW.source_binding_id
        OR OLD.target_binding_id     != NEW.target_binding_id
        OR OLD.continuity_envelope_hash != NEW.continuity_envelope_hash
        OR OLD.continuity_envelope IS DISTINCT FROM NEW.continuity_envelope
        OR OLD.material_request_hash != NEW.material_request_hash
        OR OLD.causal_marker         != NEW.causal_marker
        OR OLD.sequence_number       != NEW.sequence_number
        OR OLD.idempotency_key       != NEW.idempotency_key
        OR OLD.prepared_evidence_id  != NEW.prepared_evidence_id
        THEN
            RAISE EXCEPTION 'continuity_checkpoint immutable fields cannot be changed';
        END IF;
        -- Block terminal updates
        IF OLD.status != 'PREPARED' THEN
            RAISE EXCEPTION 'continuity_checkpoint % is already resolved', OLD.checkpoint_id;
        END IF;
        -- Only legal transitions
        IF NEW.status NOT IN ('COMMITTED', 'REVERTED', 'CONFLICT', 'EXPIRED') THEN
            RAISE EXCEPTION 'illegal continuity_checkpoint transition % → %', OLD.status, NEW.status;
        END IF;
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS continuity_checkpoint_transition ON business.continuity_checkpoints;
CREATE TRIGGER continuity_checkpoint_transition
    BEFORE UPDATE ON business.continuity_checkpoints
    FOR EACH ROW EXECUTE FUNCTION business.continuity_checkpoint_transition_guard();

-- ── delivery_acknowledgements ────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS business.delivery_acknowledgements (
    acknowledgement_id      UUID         NOT NULL DEFAULT gen_random_uuid(),
    tenant_id               UUID         NOT NULL,
    relationship_id         UUID         NOT NULL,
    checkpoint_id           UUID,
    binding_id              UUID         NOT NULL,
    message_id_hash         CHAR(64)     NOT NULL,
    acknowledgement_type    VARCHAR(32)  NOT NULL,
    acknowledged_at         TIMESTAMPTZ  NOT NULL,
    evidence_id             UUID         NOT NULL,
    created_at              TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT delivery_acknowledgements_pk PRIMARY KEY (acknowledgement_id),
    CONSTRAINT delivery_acknowledgements_relationship_fk
        FOREIGN KEY (tenant_id, relationship_id)
        REFERENCES business.employment_relationships (tenant_id, relationship_id),
    CONSTRAINT delivery_acknowledgements_checkpoint_fk
        FOREIGN KEY (tenant_id, checkpoint_id)
        REFERENCES business.continuity_checkpoints (tenant_id, checkpoint_id),
    CONSTRAINT delivery_acknowledgements_binding_fk
        FOREIGN KEY (tenant_id, binding_id)
        REFERENCES business.channel_bindings (tenant_id, binding_id),
    CONSTRAINT delivery_acknowledgements_type_check
        CHECK (acknowledgement_type IN ('TRANSPORT_ACCEPTED', 'PARTICIPANT_OBSERVED')),
    CONSTRAINT delivery_acknowledgements_hash_check
        CHECK (message_id_hash ~ '^[0-9a-f]{64}$'),
    -- Each acknowledgement event is independently replay-safe
    CONSTRAINT delivery_acknowledgements_replay_safe_unique
        UNIQUE (tenant_id, binding_id, message_id_hash, acknowledgement_type)
);

CREATE INDEX IF NOT EXISTS delivery_acknowledgements_timeline_idx
    ON business.delivery_acknowledgements (tenant_id, relationship_id, acknowledged_at);
CREATE INDEX IF NOT EXISTS delivery_acknowledgements_checkpoint_idx
    ON business.delivery_acknowledgements (tenant_id, checkpoint_id);
CREATE INDEX IF NOT EXISTS delivery_acknowledgements_message_idx
    ON business.delivery_acknowledgements (tenant_id, binding_id, message_id_hash);

ALTER TABLE business.delivery_acknowledgements ENABLE ROW LEVEL SECURITY;
ALTER TABLE business.delivery_acknowledgements FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS delivery_acknowledgements_tenant_isolation ON business.delivery_acknowledgements;
CREATE POLICY delivery_acknowledgements_tenant_isolation ON business.delivery_acknowledgements
    USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', TRUE), '')::UUID)
    WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', TRUE), '')::UUID);

-- Append-only: no UPDATE or DELETE for business_app
GRANT SELECT, INSERT ON business.delivery_acknowledgements TO business_app;

CREATE OR REPLACE FUNCTION business.delivery_acknowledgements_append_only()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'delivery_acknowledgements rows are append-only';
END;
$$;

DROP TRIGGER IF EXISTS delivery_acknowledgements_no_update ON business.delivery_acknowledgements;
CREATE TRIGGER delivery_acknowledgements_no_update
    BEFORE UPDATE OR DELETE ON business.delivery_acknowledgements
    FOR EACH ROW EXECUTE FUNCTION business.delivery_acknowledgements_append_only();

-- ── channel_message_deduplication ───────────────────────────────────────────

CREATE TABLE IF NOT EXISTS business.channel_message_deduplication (
    deduplication_id            UUID         NOT NULL DEFAULT gen_random_uuid(),
    tenant_id                   UUID         NOT NULL,
    relationship_id             UUID         NOT NULL,
    binding_id                  UUID         NOT NULL,
    provider_message_id_hash    CHAR(64)     NOT NULL,
    material_message_hash       CHAR(64)     NOT NULL,
    received_at                 TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    outcome_reference           UUID,
    status                      VARCHAR(16)  NOT NULL DEFAULT 'RECEIVED',
    expires_at                  TIMESTAMPTZ  NOT NULL DEFAULT (NOW() + INTERVAL '48 hours'),
    CONSTRAINT channel_message_deduplication_pk PRIMARY KEY (deduplication_id),
    CONSTRAINT channel_message_deduplication_relationship_fk
        FOREIGN KEY (tenant_id, relationship_id)
        REFERENCES business.employment_relationships (tenant_id, relationship_id),
    CONSTRAINT channel_message_deduplication_binding_fk
        FOREIGN KEY (tenant_id, binding_id)
        REFERENCES business.channel_bindings (tenant_id, binding_id),
    CONSTRAINT channel_message_deduplication_status_check
        CHECK (status IN ('RECEIVED', 'SUCCEEDED', 'FAILED', 'CONFLICT')),
    CONSTRAINT channel_message_deduplication_provider_hash_check
        CHECK (provider_message_id_hash ~ '^[0-9a-f]{64}$'),
    CONSTRAINT channel_message_deduplication_material_hash_check
        CHECK (material_message_hash ~ '^[0-9a-f]{64}$'),
    CONSTRAINT channel_message_deduplication_expiry_check
        CHECK (expires_at = received_at + INTERVAL '48 hours'),
    -- First receiver owns processing
    CONSTRAINT channel_message_deduplication_provider_unique
        UNIQUE (tenant_id, binding_id, provider_message_id_hash),
    -- RECEIVED has no outcome_reference
    CONSTRAINT channel_message_deduplication_received_fields CHECK (
        status != 'RECEIVED'
        OR outcome_reference IS NULL
    ),
    -- Terminal states require outcome_reference
    CONSTRAINT channel_message_deduplication_terminal_fields CHECK (
        status = 'RECEIVED'
        OR outcome_reference IS NOT NULL
    )
);

CREATE INDEX IF NOT EXISTS channel_message_dedup_timeline_idx
    ON business.channel_message_deduplication (tenant_id, relationship_id, received_at);
CREATE INDEX IF NOT EXISTS channel_message_dedup_provider_idx
    ON business.channel_message_deduplication (tenant_id, binding_id, provider_message_id_hash);
CREATE INDEX IF NOT EXISTS channel_message_dedup_expiry_idx
    ON business.channel_message_deduplication (expires_at);

ALTER TABLE business.channel_message_deduplication ENABLE ROW LEVEL SECURITY;
ALTER TABLE business.channel_message_deduplication FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS channel_message_deduplication_tenant_isolation
    ON business.channel_message_deduplication;
CREATE POLICY channel_message_deduplication_tenant_isolation
    ON business.channel_message_deduplication
    USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', TRUE), '')::UUID)
    WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', TRUE), '')::UUID);

GRANT SELECT, INSERT ON business.channel_message_deduplication TO business_app;
GRANT UPDATE (status, outcome_reference) ON business.channel_message_deduplication TO business_app;

-- Maintenance role: delete only expired rows
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_roles WHERE rolname = 'business_continuity_maintenance'
    ) THEN
        CREATE ROLE business_continuity_maintenance NOLOGIN;
    END IF;
END $$;

-- Schema access required for the role to reach its single-table grant
GRANT USAGE ON SCHEMA business TO business_continuity_maintenance;
GRANT SELECT, DELETE ON business.channel_message_deduplication
    TO business_continuity_maintenance;

-- Transition trigger: RECEIVED → SUCCEEDED|FAILED|CONFLICT only
CREATE OR REPLACE FUNCTION business.channel_message_dedup_transition_guard()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP = 'UPDATE' THEN
        IF OLD.tenant_id                 != NEW.tenant_id
        OR OLD.relationship_id           != NEW.relationship_id
        OR OLD.binding_id                != NEW.binding_id
        OR OLD.provider_message_id_hash  != NEW.provider_message_id_hash
        OR OLD.material_message_hash     != NEW.material_message_hash
        OR OLD.received_at               != NEW.received_at
        THEN
            RAISE EXCEPTION 'channel_message_deduplication identity fields are immutable';
        END IF;
        IF OLD.status != 'RECEIVED' THEN
            RAISE EXCEPTION 'channel_message_deduplication % is already resolved', OLD.deduplication_id;
        END IF;
        IF NEW.status NOT IN ('SUCCEEDED', 'FAILED', 'CONFLICT') THEN
            RAISE EXCEPTION 'illegal deduplication transition % → %', OLD.status, NEW.status;
        END IF;
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS channel_message_dedup_transition
    ON business.channel_message_deduplication;
CREATE TRIGGER channel_message_dedup_transition
    BEFORE UPDATE ON business.channel_message_deduplication
    FOR EACH ROW EXECUTE FUNCTION business.channel_message_dedup_transition_guard();
