-- Implements: WC-088 Customer Multi-Agent And Skill Journey
-- constitutional_basis: C-005, C-007, C-023, C-026, C-059

ALTER TABLE business.relationship_skill_configuration
    DROP CONSTRAINT relationship_skill_configuration_status_check;
ALTER TABLE business.relationship_skill_configuration
    ADD CONSTRAINT relationship_skill_configuration_status_check
    CHECK (status IN ('PROPOSED', 'SELECTED', 'ACCEPTED', 'EDITED', 'REJECTED', 'DEFERRED', 'RETIRED'));

DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'relationship_skill_configuration_tenant_relationship_configuration_unique'
    ) THEN
        ALTER TABLE business.relationship_skill_configuration
            ADD CONSTRAINT relationship_skill_configuration_tenant_relationship_configuration_unique
            UNIQUE (tenant_id, relationship_id, configuration_id);
    END IF;
END $$;

CREATE TABLE IF NOT EXISTS business.relationship_skill_decisions (
    decision_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    relationship_id UUID NOT NULL,
    configuration_id UUID NOT NULL,
    skill_id VARCHAR(128) NOT NULL,
    skill_version VARCHAR(32) NOT NULL,
    decision VARCHAR(24) NOT NULL,
    actor_participant_id UUID NOT NULL,
    expected_workspace_version VARCHAR(64) NOT NULL,
    expected_subject_version VARCHAR(64) NOT NULL,
    idempotency_key UUID NOT NULL,
    material_request_hash CHAR(64) NOT NULL,
    evidence_id UUID NOT NULL,
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT relationship_skill_decisions_relationship_fk
        FOREIGN KEY (tenant_id, relationship_id)
        REFERENCES business.employment_relationships (tenant_id, relationship_id),
    CONSTRAINT relationship_skill_decisions_configuration_fk
        FOREIGN KEY (tenant_id, relationship_id, configuration_id)
        REFERENCES business.relationship_skill_configuration
            (tenant_id, relationship_id, configuration_id),
    CONSTRAINT relationship_skill_decisions_outcome_check
        CHECK (decision IN ('SELECT_SKILL', 'UPDATE_SKILL', 'ACCEPT_SKILL', 'DEFER_SKILL')),
    CONSTRAINT relationship_skill_decisions_hash_check
        CHECK (material_request_hash ~ '^[0-9a-f]{64}$'),
    CONSTRAINT relationship_skill_decisions_idempotency_unique
        UNIQUE (tenant_id, relationship_id, idempotency_key)
);

CREATE INDEX IF NOT EXISTS idx_relationship_skill_decisions_timeline
    ON business.relationship_skill_decisions
    (tenant_id, relationship_id, configuration_id, occurred_at DESC, decision_id DESC);

CREATE OR REPLACE FUNCTION business.reject_relationship_skill_decision_mutation()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'relationship skill decisions are append-only';
END;
$$;

DROP TRIGGER IF EXISTS relationship_skill_decisions_no_update ON business.relationship_skill_decisions;
CREATE TRIGGER relationship_skill_decisions_no_update
    BEFORE UPDATE ON business.relationship_skill_decisions
    FOR EACH ROW EXECUTE FUNCTION business.reject_relationship_skill_decision_mutation();
DROP TRIGGER IF EXISTS relationship_skill_decisions_no_delete ON business.relationship_skill_decisions;
CREATE TRIGGER relationship_skill_decisions_no_delete
    BEFORE DELETE ON business.relationship_skill_decisions
    FOR EACH ROW EXECUTE FUNCTION business.reject_relationship_skill_decision_mutation();

ALTER TABLE business.relationship_skill_decisions ENABLE ROW LEVEL SECURITY;
ALTER TABLE business.relationship_skill_decisions FORCE ROW LEVEL SECURITY;
CREATE POLICY relationship_skill_decisions_tenant_isolation
    ON business.relationship_skill_decisions
    USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', TRUE), '')::UUID)
    WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', TRUE), '')::UUID);

GRANT SELECT, INSERT ON business.relationship_skill_decisions TO business_app;
