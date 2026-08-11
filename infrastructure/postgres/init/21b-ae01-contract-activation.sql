-- Implements: architecture/reference/product/ae01-relationship-data-contract.md § Migration 21
-- constitutional_basis: C-005, C-007, C-023, C-026, C-038, C-059, C-063
-- 21b preserves deployment ordering because 21-conversation-core.sql already exists.

CREATE TABLE IF NOT EXISTS business.employment_contract_versions (
    contract_id                         UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id                           UUID         NOT NULL,
    relationship_id                     UUID         NOT NULL,
    version                             INTEGER      NOT NULL,
    contract_hash                       CHAR(64)     NOT NULL,
    aeec_version                        VARCHAR(32)  NOT NULL,
    domain_schedule_payload_reference   UUID,
    domain_schedule_hash                CHAR(64)     NOT NULL,
    configuration_snapshot_json         JSONB        NOT NULL,
    price_tax_summary_json               JSONB        NOT NULL,
    state                               VARCHAR(16)  NOT NULL DEFAULT 'PRESENTED',
    created_by_participant_id            UUID         NOT NULL,
    created_at                          TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT employment_contract_versions_relationship_fk
        FOREIGN KEY (tenant_id, relationship_id)
        REFERENCES business.employment_relationships (tenant_id, relationship_id),
    CONSTRAINT employment_contract_versions_tenant_contract_unique
        UNIQUE (tenant_id, relationship_id, contract_id),
    CONSTRAINT employment_contract_versions_exact_identity_unique
        UNIQUE (tenant_id, relationship_id, contract_id, version, contract_hash),
    CONSTRAINT employment_contract_versions_version_unique
        UNIQUE (tenant_id, relationship_id, version),
    CONSTRAINT employment_contract_versions_hash_unique
        UNIQUE (tenant_id, relationship_id, contract_hash),
    CONSTRAINT employment_contract_versions_version_check CHECK (version > 0),
    CONSTRAINT employment_contract_versions_contract_hash_check
        CHECK (contract_hash ~ '^[0-9a-f]{64}$'),
    CONSTRAINT employment_contract_versions_schedule_hash_check
        CHECK (domain_schedule_hash ~ '^[0-9a-f]{64}$'),
    CONSTRAINT employment_contract_versions_configuration_check
        CHECK (jsonb_typeof(configuration_snapshot_json) = 'object'),
    CONSTRAINT employment_contract_versions_price_check
        CHECK (jsonb_typeof(price_tax_summary_json) = 'object'),
    CONSTRAINT employment_contract_versions_state_check
        CHECK (state IN ('PROPOSED', 'PRESENTED', 'SUPERSEDED'))
);

CREATE TABLE IF NOT EXISTS business.contract_acceptances (
    acceptance_id               UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id                   UUID         NOT NULL,
    relationship_id             UUID         NOT NULL,
    contract_id                 UUID         NOT NULL,
    contract_version            INTEGER      NOT NULL,
    contract_hash               CHAR(64)     NOT NULL,
    participant_id              UUID         NOT NULL,
    participant_role            VARCHAR(32)  NOT NULL,
    authentication_assurance    VARCHAR(32)  NOT NULL,
    authority_snapshot_id       UUID         NOT NULL,
    scope_confirmation_hash     CHAR(64)     NOT NULL,
    acceptance_evidence_id      UUID         NOT NULL,
    accepted_at                 TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT contract_acceptances_exact_contract_fk
        FOREIGN KEY (tenant_id, relationship_id, contract_id, contract_version, contract_hash)
        REFERENCES business.employment_contract_versions
            (tenant_id, relationship_id, contract_id, version, contract_hash),
    CONSTRAINT contract_acceptances_tenant_acceptance_unique
        UNIQUE (tenant_id, relationship_id, acceptance_id),
    CONSTRAINT contract_acceptances_contract_identity_unique
        UNIQUE (tenant_id, relationship_id, contract_id, acceptance_id),
    CONSTRAINT contract_acceptances_effective_version_unique
        UNIQUE (tenant_id, relationship_id, contract_id),
    CONSTRAINT contract_acceptances_hash_check
        CHECK (contract_hash ~ '^[0-9a-f]{64}$'),
    CONSTRAINT contract_acceptances_scope_hash_check
        CHECK (scope_confirmation_hash ~ '^[0-9a-f]{64}$'),
    CONSTRAINT contract_acceptances_role_check
        CHECK (participant_role = 'EMPLOYER'),
    CONSTRAINT contract_acceptances_assurance_check
        CHECK (authentication_assurance = 'AAL3_FRESH')
);

CREATE TABLE IF NOT EXISTS business.activation_intents (
    activation_intent_id       UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id                  UUID         NOT NULL,
    relationship_id            UUID         NOT NULL,
    accepted_contract_id       UUID         NOT NULL,
    contract_acceptance_id     UUID         NOT NULL,
    payment_reference          VARCHAR(128) NOT NULL,
    correlation_id             UUID         NOT NULL,
    material_request_hash      CHAR(64)     NOT NULL,
    conflicting_request_hash   CHAR(64),
    status                     VARCHAR(24)  NOT NULL DEFAULT 'PENDING',
    outcome_subscription_id    UUID,
    outcome_evidence_id        UUID,
    outcome_json               JSONB,
    created_at                 TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at                 TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    completed_at               TIMESTAMPTZ,
    CONSTRAINT activation_intents_relationship_fk
        FOREIGN KEY (tenant_id, relationship_id)
        REFERENCES business.employment_relationships (tenant_id, relationship_id),
    CONSTRAINT activation_intents_contract_fk
        FOREIGN KEY (tenant_id, relationship_id, accepted_contract_id)
        REFERENCES business.employment_contract_versions (tenant_id, relationship_id, contract_id),
    CONSTRAINT activation_intents_accepted_contract_fk
        FOREIGN KEY (tenant_id, relationship_id, accepted_contract_id, contract_acceptance_id)
        REFERENCES business.contract_acceptances
            (tenant_id, relationship_id, contract_id, acceptance_id),
    CONSTRAINT activation_intents_tuple_unique
        UNIQUE (tenant_id, relationship_id, accepted_contract_id, payment_reference),
    CONSTRAINT activation_intents_correlation_unique
        UNIQUE (tenant_id, relationship_id, correlation_id),
    CONSTRAINT activation_intents_request_hash_check
        CHECK (material_request_hash ~ '^[0-9a-f]{64}$'),
    CONSTRAINT activation_intents_conflict_hash_check
        CHECK (conflicting_request_hash IS NULL OR conflicting_request_hash ~ '^[0-9a-f]{64}$'),
    CONSTRAINT activation_intents_status_check
        CHECK (status IN ('PENDING', 'SUCCEEDED', 'FAILED_RETRYABLE', 'CONFLICT')),
    CONSTRAINT activation_intents_outcome_check CHECK (
        (status = 'SUCCEEDED'
            AND outcome_subscription_id IS NOT NULL
            AND outcome_evidence_id IS NOT NULL
            AND outcome_json IS NOT NULL
            AND completed_at IS NOT NULL
            AND conflicting_request_hash IS NULL)
        OR (status = 'CONFLICT'
            AND conflicting_request_hash IS NOT NULL
            AND outcome_subscription_id IS NULL
            AND outcome_evidence_id IS NULL
            AND outcome_json IS NULL
            AND completed_at IS NOT NULL)
        OR (status IN ('PENDING', 'FAILED_RETRYABLE')
            AND outcome_subscription_id IS NULL
            AND outcome_evidence_id IS NULL
            AND outcome_json IS NULL
            AND completed_at IS NULL
            AND conflicting_request_hash IS NULL)
    )
);

CREATE INDEX IF NOT EXISTS idx_employment_contract_versions_relationship
    ON business.employment_contract_versions (tenant_id, relationship_id, version DESC);
CREATE INDEX IF NOT EXISTS idx_contract_acceptances_relationship
    ON business.contract_acceptances (tenant_id, relationship_id, accepted_at DESC);
CREATE INDEX IF NOT EXISTS idx_activation_intents_status
    ON business.activation_intents (tenant_id, relationship_id, status);
CREATE INDEX IF NOT EXISTS idx_activation_intents_request_hash
    ON business.activation_intents (tenant_id, relationship_id, material_request_hash);

CREATE OR REPLACE FUNCTION business.reject_contract_record_mutation()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION '% is immutable', TG_TABLE_NAME;
END;
$$;

DROP TRIGGER IF EXISTS employment_contract_versions_no_update ON business.employment_contract_versions;
CREATE TRIGGER employment_contract_versions_no_update
    BEFORE UPDATE ON business.employment_contract_versions
    FOR EACH ROW EXECUTE FUNCTION business.reject_contract_record_mutation();
DROP TRIGGER IF EXISTS employment_contract_versions_no_delete ON business.employment_contract_versions;
CREATE TRIGGER employment_contract_versions_no_delete
    BEFORE DELETE ON business.employment_contract_versions
    FOR EACH ROW EXECUTE FUNCTION business.reject_contract_record_mutation();
DROP TRIGGER IF EXISTS contract_acceptances_no_update ON business.contract_acceptances;
CREATE TRIGGER contract_acceptances_no_update
    BEFORE UPDATE ON business.contract_acceptances
    FOR EACH ROW EXECUTE FUNCTION business.reject_contract_record_mutation();
DROP TRIGGER IF EXISTS contract_acceptances_no_delete ON business.contract_acceptances;
CREATE TRIGGER contract_acceptances_no_delete
    BEFORE DELETE ON business.contract_acceptances
    FOR EACH ROW EXECUTE FUNCTION business.reject_contract_record_mutation();

CREATE OR REPLACE FUNCTION business.guard_activation_intent_update()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF NEW.tenant_id <> OLD.tenant_id
        OR NEW.relationship_id <> OLD.relationship_id
        OR NEW.accepted_contract_id <> OLD.accepted_contract_id
        OR NEW.contract_acceptance_id <> OLD.contract_acceptance_id
        OR NEW.payment_reference <> OLD.payment_reference
        OR NEW.correlation_id <> OLD.correlation_id
        OR NEW.material_request_hash <> OLD.material_request_hash
        OR NEW.created_at <> OLD.created_at THEN
        RAISE EXCEPTION 'activation intent identity and request are immutable';
    END IF;

    IF OLD.status IN ('SUCCEEDED', 'CONFLICT') THEN
        RAISE EXCEPTION 'terminal activation intent is immutable';
    END IF;

    IF OLD.status = 'PENDING' AND NEW.status NOT IN ('PENDING', 'SUCCEEDED', 'FAILED_RETRYABLE', 'CONFLICT') THEN
        RAISE EXCEPTION 'invalid activation intent transition';
    END IF;

    IF OLD.status = 'FAILED_RETRYABLE' AND NEW.status NOT IN ('PENDING', 'SUCCEEDED', 'FAILED_RETRYABLE', 'CONFLICT') THEN
        RAISE EXCEPTION 'invalid activation intent retry transition';
    END IF;

    NEW.updated_at := NOW();
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS activation_intents_guard_update ON business.activation_intents;
CREATE TRIGGER activation_intents_guard_update
    BEFORE UPDATE ON business.activation_intents
    FOR EACH ROW EXECUTE FUNCTION business.guard_activation_intent_update();
DROP TRIGGER IF EXISTS activation_intents_no_delete ON business.activation_intents;
CREATE TRIGGER activation_intents_no_delete
    BEFORE DELETE ON business.activation_intents
    FOR EACH ROW EXECUTE FUNCTION business.reject_contract_record_mutation();

ALTER TABLE business.employment_contract_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE business.employment_contract_versions FORCE ROW LEVEL SECURITY;
ALTER TABLE business.contract_acceptances ENABLE ROW LEVEL SECURITY;
ALTER TABLE business.contract_acceptances FORCE ROW LEVEL SECURITY;
ALTER TABLE business.activation_intents ENABLE ROW LEVEL SECURITY;
ALTER TABLE business.activation_intents FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS employment_contract_versions_tenant_isolation ON business.employment_contract_versions;
CREATE POLICY employment_contract_versions_tenant_isolation ON business.employment_contract_versions
    USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', TRUE), '')::UUID)
    WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', TRUE), '')::UUID);
DROP POLICY IF EXISTS contract_acceptances_tenant_isolation ON business.contract_acceptances;
CREATE POLICY contract_acceptances_tenant_isolation ON business.contract_acceptances
    USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', TRUE), '')::UUID)
    WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', TRUE), '')::UUID);
DROP POLICY IF EXISTS activation_intents_tenant_isolation ON business.activation_intents;
CREATE POLICY activation_intents_tenant_isolation ON business.activation_intents
    USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', TRUE), '')::UUID)
    WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', TRUE), '')::UUID);

GRANT SELECT, INSERT ON business.employment_contract_versions TO business_app;
GRANT SELECT, INSERT ON business.contract_acceptances TO business_app;
GRANT SELECT, INSERT, UPDATE ON business.activation_intents TO business_app;