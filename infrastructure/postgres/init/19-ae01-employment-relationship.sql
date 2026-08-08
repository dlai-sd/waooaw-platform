-- Implements: architecture/reference/product/ae01-relationship-data-contract.md § Migration 19
-- constitutional_basis: C-005, C-007, C-023, C-026, C-059

CREATE TABLE IF NOT EXISTS business.employment_relationships (
    relationship_id             UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id                   UUID         NOT NULL,
    professional_type           VARCHAR(64)  NOT NULL,
    evaluation_intent_id        UUID         NOT NULL,
    initiating_participant_id   UUID         NOT NULL,
    source_relationship_id      UUID,
    fork_evidence_id            UUID,
    state                       VARCHAR(48)  NOT NULL DEFAULT 'DISCOVERED',
    state_version               INTEGER      NOT NULL DEFAULT 0,
    authority_snapshot_id       UUID,
    accepted_contract_id        UUID,
    activation_id               UUID,
    stopped_at                  TIMESTAMPTZ,
    created_at                  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT employment_relationships_tenant_relationship_unique
        UNIQUE (tenant_id, relationship_id),
    CONSTRAINT employment_relationships_first_mint_unique
        UNIQUE (tenant_id, initiating_participant_id, professional_type, evaluation_intent_id),
    CONSTRAINT employment_relationships_source_fk
        FOREIGN KEY (tenant_id, source_relationship_id)
        REFERENCES business.employment_relationships (tenant_id, relationship_id),
    CONSTRAINT employment_relationships_state_version_check CHECK (state_version >= 0),
    CONSTRAINT employment_relationships_fork_evidence_check CHECK (
        (source_relationship_id IS NULL AND fork_evidence_id IS NULL)
        OR (source_relationship_id IS NOT NULL AND fork_evidence_id IS NOT NULL)
    ),
    CONSTRAINT employment_relationships_state_check CHECK (state IN (
        'DISCOVERED',
        'INTERVIEWING',
        'TRIAL_ACTIVE',
        'CONFIGURING',
        'CONTRACT_PENDING_ACCEPTANCE',
        'CONTRACT_ACCEPTED_PENDING_PAYMENT',
        'ACTIVATION_PENDING',
        'ACTIVE',
        'PAUSED',
        'STOPPED_EMERGENCY',
        'TERMINATED'
    ))
);

CREATE TABLE IF NOT EXISTS business.relationship_participants (
    binding_id             UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id              UUID         NOT NULL,
    relationship_id        UUID         NOT NULL,
    participant_id         UUID         NOT NULL,
    role                   VARCHAR(32)  NOT NULL,
    status                 VARCHAR(16)  NOT NULL DEFAULT 'ACTIVE',
    bound_evidence_id      UUID         NOT NULL,
    bound_at               TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    revoked_evidence_id    UUID,
    revoked_at             TIMESTAMPTZ,
    CONSTRAINT relationship_participants_relationship_fk
        FOREIGN KEY (tenant_id, relationship_id)
        REFERENCES business.employment_relationships (tenant_id, relationship_id),
    CONSTRAINT relationship_participants_role_check CHECK (
        role IN ('EVALUATOR', 'EMPLOYER', 'OUTCOME_OWNER', 'RELATIONSHIP_MANAGER')
    ),
    CONSTRAINT relationship_participants_status_check CHECK (status IN ('ACTIVE', 'REVOKED')),
    CONSTRAINT relationship_participants_revocation_check CHECK (
        (status = 'ACTIVE' AND revoked_evidence_id IS NULL AND revoked_at IS NULL)
        OR (status = 'REVOKED' AND revoked_evidence_id IS NOT NULL AND revoked_at IS NOT NULL)
    )
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_relationship_participants_active_role
    ON business.relationship_participants (tenant_id, relationship_id, participant_id, role)
    WHERE status = 'ACTIVE';

CREATE TABLE IF NOT EXISTS business.relationship_state_history (
    history_id               UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id                UUID         NOT NULL,
    relationship_id          UUID         NOT NULL,
    state_version            INTEGER      NOT NULL,
    from_state               VARCHAR(48),
    to_state                 VARCHAR(48)  NOT NULL,
    actor_participant_id     UUID         NOT NULL,
    actor_role               VARCHAR(32)  NOT NULL,
    authority_snapshot_id    UUID,
    correlation_id           UUID         NOT NULL,
    evidence_id              UUID         NOT NULL,
    occurred_at              TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT relationship_state_history_relationship_fk
        FOREIGN KEY (tenant_id, relationship_id)
        REFERENCES business.employment_relationships (tenant_id, relationship_id),
    CONSTRAINT relationship_state_history_version_unique
        UNIQUE (tenant_id, relationship_id, state_version),
    CONSTRAINT relationship_state_history_version_check CHECK (state_version >= 0),
    CONSTRAINT relationship_state_history_actor_role_check CHECK (
        actor_role IN ('EVALUATOR', 'EMPLOYER', 'OUTCOME_OWNER', 'RELATIONSHIP_MANAGER', 'CONSTITUTIONAL_AUTHORITY')
    ),
    CONSTRAINT relationship_state_history_from_state_check CHECK (
        from_state IS NULL OR from_state IN (
            'DISCOVERED', 'INTERVIEWING', 'TRIAL_ACTIVE', 'CONFIGURING',
            'CONTRACT_PENDING_ACCEPTANCE', 'CONTRACT_ACCEPTED_PENDING_PAYMENT',
            'ACTIVATION_PENDING', 'ACTIVE', 'PAUSED', 'STOPPED_EMERGENCY', 'TERMINATED'
        )
    ),
    CONSTRAINT relationship_state_history_to_state_check CHECK (to_state IN (
        'DISCOVERED', 'INTERVIEWING', 'TRIAL_ACTIVE', 'CONFIGURING',
        'CONTRACT_PENDING_ACCEPTANCE', 'CONTRACT_ACCEPTED_PENDING_PAYMENT',
        'ACTIVATION_PENDING', 'ACTIVE', 'PAUSED', 'STOPPED_EMERGENCY', 'TERMINATED'
    ))
);

CREATE TABLE IF NOT EXISTS business.relationship_idempotency (
    idempotency_id          UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id               UUID         NOT NULL,
    relationship_id         UUID         NOT NULL,
    purpose                 VARCHAR(64)  NOT NULL,
    idempotency_key         VARCHAR(128) NOT NULL,
    material_request_hash   CHAR(64)     NOT NULL,
    outcome_reference       UUID,
    status                  VARCHAR(24)  NOT NULL DEFAULT 'RECEIVED',
    created_at              TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    completed_at            TIMESTAMPTZ,
    CONSTRAINT relationship_idempotency_relationship_fk
        FOREIGN KEY (tenant_id, relationship_id)
        REFERENCES business.employment_relationships (tenant_id, relationship_id),
    CONSTRAINT relationship_idempotency_key_unique
        UNIQUE (tenant_id, purpose, idempotency_key),
    CONSTRAINT relationship_idempotency_hash_check CHECK (
        material_request_hash ~ '^[0-9a-f]{64}$'
    ),
    CONSTRAINT relationship_idempotency_status_check CHECK (
        status IN ('RECEIVED', 'SUCCEEDED', 'FAILED', 'CONFLICT')
    )
);

CREATE INDEX IF NOT EXISTS idx_employment_relationships_tenant_relationship
    ON business.employment_relationships (tenant_id, relationship_id);
CREATE INDEX IF NOT EXISTS idx_employment_relationships_participant_professional
    ON business.employment_relationships (tenant_id, initiating_participant_id, professional_type);
CREATE INDEX IF NOT EXISTS idx_relationship_state_history_timeline
    ON business.relationship_state_history (tenant_id, relationship_id, state_version);
CREATE INDEX IF NOT EXISTS idx_relationship_state_history_correlation
    ON business.relationship_state_history (tenant_id, relationship_id, correlation_id);

CREATE OR REPLACE FUNCTION business.reject_relationship_history_mutation()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION 'relationship_state_history is append-only';
END;
$$;

DROP TRIGGER IF EXISTS relationship_state_history_no_update ON business.relationship_state_history;
CREATE TRIGGER relationship_state_history_no_update
    BEFORE UPDATE ON business.relationship_state_history
    FOR EACH ROW EXECUTE FUNCTION business.reject_relationship_history_mutation();

DROP TRIGGER IF EXISTS relationship_state_history_no_delete ON business.relationship_state_history;
CREATE TRIGGER relationship_state_history_no_delete
    BEFORE DELETE ON business.relationship_state_history
    FOR EACH ROW EXECUTE FUNCTION business.reject_relationship_history_mutation();

ALTER TABLE business.employment_relationships ENABLE ROW LEVEL SECURITY;
ALTER TABLE business.employment_relationships FORCE ROW LEVEL SECURITY;
ALTER TABLE business.relationship_participants ENABLE ROW LEVEL SECURITY;
ALTER TABLE business.relationship_participants FORCE ROW LEVEL SECURITY;
ALTER TABLE business.relationship_state_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE business.relationship_state_history FORCE ROW LEVEL SECURITY;
ALTER TABLE business.relationship_idempotency ENABLE ROW LEVEL SECURITY;
ALTER TABLE business.relationship_idempotency FORCE ROW LEVEL SECURITY;

CREATE POLICY employment_relationships_tenant_isolation
    ON business.employment_relationships
    USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', TRUE), '')::UUID)
    WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', TRUE), '')::UUID);
CREATE POLICY relationship_participants_tenant_isolation
    ON business.relationship_participants
    USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', TRUE), '')::UUID)
    WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', TRUE), '')::UUID);
CREATE POLICY relationship_state_history_tenant_isolation
    ON business.relationship_state_history
    USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', TRUE), '')::UUID)
    WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', TRUE), '')::UUID);
CREATE POLICY relationship_idempotency_tenant_isolation
    ON business.relationship_idempotency
    USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', TRUE), '')::UUID)
    WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', TRUE), '')::UUID);

GRANT SELECT, INSERT, UPDATE ON business.employment_relationships TO business_app;
GRANT SELECT, INSERT, UPDATE ON business.relationship_participants TO business_app;
GRANT SELECT, INSERT ON business.relationship_state_history TO business_app;
GRANT SELECT, INSERT, UPDATE ON business.relationship_idempotency TO business_app;