-- Implements: architecture/reference/product/ae01-relationship-data-contract.md § Migration 20
-- constitutional_basis: C-005, C-007, C-023, C-026, C-059, C-063, C-078
-- 20b preserves deployment ordering because 20-identity-boundary.sql already exists.

CREATE TABLE IF NOT EXISTS payload_store.relationship_context_payloads (
    payload_reference       UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id               UUID         NOT NULL,
    relationship_id         UUID         NOT NULL,
    field_type              VARCHAR(64)  NOT NULL,
    value_json              JSONB,
    source                  VARCHAR(32)  NOT NULL,
    confidence              NUMERIC(5,4),
    confirmation_status     VARCHAR(24)  NOT NULL DEFAULT 'UNCONFIRMED',
    confirmed_at            TIMESTAMPTZ,
    invalidated_at          TIMESTAMPTZ,
    payload_hash            CHAR(64)     NOT NULL,
    created_at              TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    erased_at               TIMESTAMPTZ,
    CONSTRAINT relationship_context_payloads_relationship_fk
        FOREIGN KEY (tenant_id, relationship_id)
        REFERENCES business.employment_relationships (tenant_id, relationship_id),
    CONSTRAINT relationship_context_payloads_confidence_check
        CHECK (confidence IS NULL OR confidence BETWEEN 0 AND 1),
    CONSTRAINT relationship_context_payloads_status_check
        CHECK (confirmation_status IN ('UNCONFIRMED', 'CONFIRMED', 'CORRECTED')),
    CONSTRAINT relationship_context_payloads_hash_check
        CHECK (payload_hash ~ '^[0-9a-f]{64}$'),
    CONSTRAINT relationship_context_payloads_erasure_check
        CHECK (erased_at IS NULL OR value_json IS NULL)
);

CREATE TABLE IF NOT EXISTS business.context_confirmation_events (
    event_id                UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id               UUID         NOT NULL,
    relationship_id         UUID         NOT NULL,
    payload_reference       UUID         NOT NULL,
    payload_hash            CHAR(64)     NOT NULL,
    field_type              VARCHAR(64)  NOT NULL,
    action                  VARCHAR(16)  NOT NULL,
    actor_participant_id    UUID         NOT NULL,
    correlation_id          UUID         NOT NULL,
    evidence_id             UUID         NOT NULL,
    occurred_at             TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT context_confirmation_events_relationship_fk
        FOREIGN KEY (tenant_id, relationship_id)
        REFERENCES business.employment_relationships (tenant_id, relationship_id),
    CONSTRAINT context_confirmation_events_action_check
        CHECK (action IN ('CONFIRMED', 'CORRECTED')),
    CONSTRAINT context_confirmation_events_hash_check
        CHECK (payload_hash ~ '^[0-9a-f]{64}$')
);

CREATE TABLE IF NOT EXISTS business.relationship_goals (
    goal_id                 UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id               UUID         NOT NULL,
    relationship_id         UUID         NOT NULL,
    goal                    TEXT         NOT NULL,
    baseline                TEXT,
    measure                 TEXT         NOT NULL,
    decision_threshold      TEXT,
    evidence_source         TEXT,
    review_cadence_months   INTEGER      NOT NULL DEFAULT 2,
    status                  VARCHAR(16)  NOT NULL DEFAULT 'PROPOSED',
    created_at              TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT relationship_goals_relationship_fk
        FOREIGN KEY (tenant_id, relationship_id)
        REFERENCES business.employment_relationships (tenant_id, relationship_id),
    CONSTRAINT relationship_goals_tenant_goal_unique UNIQUE (tenant_id, relationship_id, goal_id),
    CONSTRAINT relationship_goals_cadence_check CHECK (review_cadence_months = 2),
    CONSTRAINT relationship_goals_status_check
        CHECK (status IN ('PROPOSED', 'ACCEPTED', 'EDITED', 'REJECTED', 'DEFERRED', 'RETIRED'))
);

CREATE TABLE IF NOT EXISTS business.relationship_skill_configuration (
    configuration_id       UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id               UUID         NOT NULL,
    relationship_id         UUID         NOT NULL,
    skill_id                VARCHAR(128) NOT NULL,
    skill_version           VARCHAR(32)  NOT NULL,
    goal_id                 UUID,
    authority_state         VARCHAR(24)  NOT NULL DEFAULT 'NOT_GRANTED',
    applicability           VARCHAR(24)  NOT NULL DEFAULT 'APPLICABLE',
    applicability_reason    TEXT,
    status                  VARCHAR(16)  NOT NULL DEFAULT 'PROPOSED',
    created_at              TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT relationship_skill_configuration_relationship_fk
        FOREIGN KEY (tenant_id, relationship_id)
        REFERENCES business.employment_relationships (tenant_id, relationship_id),
    CONSTRAINT relationship_skill_configuration_goal_fk
        FOREIGN KEY (tenant_id, relationship_id, goal_id)
        REFERENCES business.relationship_goals (tenant_id, relationship_id, goal_id),
    CONSTRAINT relationship_skill_configuration_unique
        UNIQUE (tenant_id, relationship_id, skill_id, skill_version),
    CONSTRAINT relationship_skill_configuration_authority_check
        CHECK (authority_state IN ('NOT_GRANTED', 'PROPOSED', 'GRANTED', 'CONSTRAINED', 'REVOKED')),
    CONSTRAINT relationship_skill_configuration_applicability_check
        CHECK (applicability IN ('APPLICABLE', 'NOT_APPLICABLE', 'CONDITIONAL')),
    CONSTRAINT relationship_skill_configuration_status_check
        CHECK (status IN ('PROPOSED', 'ACCEPTED', 'EDITED', 'REJECTED', 'DEFERRED', 'RETIRED'))
);

CREATE TABLE IF NOT EXISTS business.decision_space_snapshots (
    snapshot_id                 UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id                   UUID         NOT NULL,
    relationship_id             UUID         NOT NULL,
    version                     INTEGER      NOT NULL,
    budget_ceiling_inr_paise    BIGINT       NOT NULL,
    authority_boundaries_json   JSONB        NOT NULL,
    stop_conditions_json        JSONB        NOT NULL,
    review_cadence_months       INTEGER      NOT NULL DEFAULT 2,
    accepted_evidence_json      JSONB        NOT NULL,
    created_by_participant_id   UUID         NOT NULL,
    evidence_id                 UUID         NOT NULL,
    created_at                  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT decision_space_snapshots_relationship_fk
        FOREIGN KEY (tenant_id, relationship_id)
        REFERENCES business.employment_relationships (tenant_id, relationship_id),
    CONSTRAINT decision_space_snapshots_version_unique
        UNIQUE (tenant_id, relationship_id, version),
    CONSTRAINT decision_space_snapshots_version_check CHECK (version > 0),
    CONSTRAINT decision_space_snapshots_budget_check CHECK (budget_ceiling_inr_paise >= 0),
    CONSTRAINT decision_space_snapshots_cadence_check CHECK (review_cadence_months = 2),
    CONSTRAINT decision_space_snapshots_authority_check
        CHECK (jsonb_typeof(authority_boundaries_json) = 'array' AND jsonb_array_length(authority_boundaries_json) > 0),
    CONSTRAINT decision_space_snapshots_stop_check
        CHECK (jsonb_typeof(stop_conditions_json) = 'array' AND jsonb_array_length(stop_conditions_json) > 0),
    CONSTRAINT decision_space_snapshots_evidence_check
        CHECK (jsonb_typeof(accepted_evidence_json) = 'array')
);

CREATE TABLE IF NOT EXISTS business.relationship_trial_bindings (
    binding_id          UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           UUID         NOT NULL,
    relationship_id     UUID         NOT NULL,
    customer_id         UUID         NOT NULL,
    correlation_id      UUID         NOT NULL,
    trial_id            UUID,
    starts_at           TIMESTAMPTZ,
    expires_at          TIMESTAMPTZ,
    status              VARCHAR(16)  NOT NULL DEFAULT 'PENDING',
    unresolved_owner    VARCHAR(16),
    created_at          TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT relationship_trial_bindings_relationship_fk
        FOREIGN KEY (tenant_id, relationship_id)
        REFERENCES business.employment_relationships (tenant_id, relationship_id),
    CONSTRAINT relationship_trial_bindings_relationship_unique
        UNIQUE (tenant_id, relationship_id),
    CONSTRAINT relationship_trial_bindings_status_check
        CHECK (status IN ('PENDING', 'UNRESOLVED', 'ACTIVE')),
    CONSTRAINT relationship_trial_bindings_owner_check
        CHECK (unresolved_owner IS NULL OR unresolved_owner IN ('WBE', 'PR')),
    CONSTRAINT relationship_trial_bindings_window_check
        CHECK (expires_at IS NULL OR starts_at IS NOT NULL AND expires_at = starts_at + INTERVAL '14 days'),
    CONSTRAINT relationship_trial_bindings_active_check
        CHECK (status <> 'ACTIVE' OR
            trial_id IS NOT NULL AND starts_at IS NOT NULL AND expires_at IS NOT NULL AND unresolved_owner IS NULL)
);

CREATE INDEX IF NOT EXISTS idx_relationship_context_active
    ON payload_store.relationship_context_payloads (tenant_id, relationship_id, field_type)
    WHERE invalidated_at IS NULL AND erased_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_context_confirmation_timeline
    ON business.context_confirmation_events (tenant_id, relationship_id, occurred_at);
CREATE INDEX IF NOT EXISTS idx_relationship_goals
    ON business.relationship_goals (tenant_id, relationship_id, status);
CREATE INDEX IF NOT EXISTS idx_relationship_skill_configuration
    ON business.relationship_skill_configuration (tenant_id, relationship_id, status);
CREATE INDEX IF NOT EXISTS idx_relationship_trial_bindings_status
    ON business.relationship_trial_bindings (tenant_id, status);

CREATE OR REPLACE FUNCTION business.reject_ae01_append_only_mutation()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION '% is append-only', TG_TABLE_NAME;
END;
$$;

DROP TRIGGER IF EXISTS context_confirmation_events_no_update ON business.context_confirmation_events;
CREATE TRIGGER context_confirmation_events_no_update
    BEFORE UPDATE ON business.context_confirmation_events
    FOR EACH ROW EXECUTE FUNCTION business.reject_ae01_append_only_mutation();
DROP TRIGGER IF EXISTS context_confirmation_events_no_delete ON business.context_confirmation_events;
CREATE TRIGGER context_confirmation_events_no_delete
    BEFORE DELETE ON business.context_confirmation_events
    FOR EACH ROW EXECUTE FUNCTION business.reject_ae01_append_only_mutation();
DROP TRIGGER IF EXISTS decision_space_snapshots_no_update ON business.decision_space_snapshots;
CREATE TRIGGER decision_space_snapshots_no_update
    BEFORE UPDATE ON business.decision_space_snapshots
    FOR EACH ROW EXECUTE FUNCTION business.reject_ae01_append_only_mutation();
DROP TRIGGER IF EXISTS decision_space_snapshots_no_delete ON business.decision_space_snapshots;
CREATE TRIGGER decision_space_snapshots_no_delete
    BEFORE DELETE ON business.decision_space_snapshots
    FOR EACH ROW EXECUTE FUNCTION business.reject_ae01_append_only_mutation();

ALTER TABLE payload_store.relationship_context_payloads ENABLE ROW LEVEL SECURITY;
ALTER TABLE payload_store.relationship_context_payloads FORCE ROW LEVEL SECURITY;
ALTER TABLE business.context_confirmation_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE business.context_confirmation_events FORCE ROW LEVEL SECURITY;
ALTER TABLE business.relationship_goals ENABLE ROW LEVEL SECURITY;
ALTER TABLE business.relationship_goals FORCE ROW LEVEL SECURITY;
ALTER TABLE business.relationship_skill_configuration ENABLE ROW LEVEL SECURITY;
ALTER TABLE business.relationship_skill_configuration FORCE ROW LEVEL SECURITY;
ALTER TABLE business.decision_space_snapshots ENABLE ROW LEVEL SECURITY;
ALTER TABLE business.decision_space_snapshots FORCE ROW LEVEL SECURITY;
ALTER TABLE business.relationship_trial_bindings ENABLE ROW LEVEL SECURITY;
ALTER TABLE business.relationship_trial_bindings FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS relationship_context_payloads_tenant_isolation ON payload_store.relationship_context_payloads;
CREATE POLICY relationship_context_payloads_tenant_isolation ON payload_store.relationship_context_payloads
    USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', TRUE), '')::UUID)
    WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', TRUE), '')::UUID);
DROP POLICY IF EXISTS context_confirmation_events_tenant_isolation ON business.context_confirmation_events;
CREATE POLICY context_confirmation_events_tenant_isolation ON business.context_confirmation_events
    USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', TRUE), '')::UUID)
    WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', TRUE), '')::UUID);
DROP POLICY IF EXISTS relationship_goals_tenant_isolation ON business.relationship_goals;
CREATE POLICY relationship_goals_tenant_isolation ON business.relationship_goals
    USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', TRUE), '')::UUID)
    WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', TRUE), '')::UUID);
DROP POLICY IF EXISTS relationship_skill_configuration_tenant_isolation ON business.relationship_skill_configuration;
CREATE POLICY relationship_skill_configuration_tenant_isolation ON business.relationship_skill_configuration
    USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', TRUE), '')::UUID)
    WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', TRUE), '')::UUID);
DROP POLICY IF EXISTS decision_space_snapshots_tenant_isolation ON business.decision_space_snapshots;
CREATE POLICY decision_space_snapshots_tenant_isolation ON business.decision_space_snapshots
    USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', TRUE), '')::UUID)
    WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', TRUE), '')::UUID);
DROP POLICY IF EXISTS relationship_trial_bindings_tenant_isolation ON business.relationship_trial_bindings;
CREATE POLICY relationship_trial_bindings_tenant_isolation ON business.relationship_trial_bindings
    USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', TRUE), '')::UUID)
    WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', TRUE), '')::UUID);

GRANT SELECT, INSERT, UPDATE ON payload_store.relationship_context_payloads TO business_app;
GRANT SELECT, INSERT ON business.context_confirmation_events TO business_app;
GRANT SELECT, INSERT, UPDATE ON business.relationship_goals TO business_app;
GRANT SELECT, INSERT, UPDATE ON business.relationship_skill_configuration TO business_app;
GRANT SELECT, INSERT ON business.decision_space_snapshots TO business_app;
GRANT SELECT, INSERT, UPDATE ON business.relationship_trial_bindings TO business_app;