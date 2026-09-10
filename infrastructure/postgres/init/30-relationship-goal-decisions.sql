-- Implements: WC-085 D-GOAL append-only verification lineage
-- constitutional_basis: C-005, C-007, C-023, C-026, C-059, C-063

CREATE TABLE IF NOT EXISTS business.relationship_goal_decisions (
    decision_id                UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id                  UUID         NOT NULL,
    relationship_id            UUID         NOT NULL,
    goal_id                    UUID         NOT NULL,
    goal_version               VARCHAR(64)  NOT NULL,
    skill_id                   VARCHAR(128) NOT NULL,
    skill_version              VARCHAR(32)  NOT NULL,
    measure                    TEXT         NOT NULL,
    review_cadence_months      INTEGER      NOT NULL,
    decision                   VARCHAR(24)  NOT NULL,
    correction_reason          VARCHAR(500),
    prior_decision_id          UUID,
    actor_participant_id       UUID         NOT NULL,
    expected_workspace_version VARCHAR(64)  NOT NULL,
    expected_subject_version   VARCHAR(64)  NOT NULL,
    idempotency_key            UUID         NOT NULL,
    material_request_hash      CHAR(64)     NOT NULL,
    evidence_id                UUID         NOT NULL,
    occurred_at                TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT relationship_goal_decisions_relationship_fk
        FOREIGN KEY (tenant_id, relationship_id)
        REFERENCES business.employment_relationships (tenant_id, relationship_id),
    CONSTRAINT relationship_goal_decisions_goal_fk
        FOREIGN KEY (tenant_id, relationship_id, goal_id)
        REFERENCES business.relationship_goals (tenant_id, relationship_id, goal_id),
    CONSTRAINT relationship_goal_decisions_lineage_unique
        UNIQUE (tenant_id, relationship_id, goal_id, decision_id),
    CONSTRAINT relationship_goal_decisions_prior_fk
        FOREIGN KEY (tenant_id, relationship_id, goal_id, prior_decision_id)
        REFERENCES business.relationship_goal_decisions
            (tenant_id, relationship_id, goal_id, decision_id),
    CONSTRAINT relationship_goal_decisions_outcome_check
        CHECK (decision IN ('VERIFIED', 'CHANGES_REQUESTED')),
    CONSTRAINT relationship_goal_decisions_reason_check CHECK (
        (decision = 'VERIFIED' AND correction_reason IS NULL)
        OR (decision = 'CHANGES_REQUESTED'
            AND correction_reason IS NOT NULL
            AND length(trim(correction_reason)) BETWEEN 1 AND 500)
    ),
    CONSTRAINT relationship_goal_decisions_cadence_check CHECK (review_cadence_months > 0),
    CONSTRAINT relationship_goal_decisions_hash_check CHECK (material_request_hash ~ '^[0-9a-f]{64}$'),
    CONSTRAINT relationship_goal_decisions_idempotency_unique
        UNIQUE (tenant_id, relationship_id, idempotency_key)
);

CREATE INDEX IF NOT EXISTS idx_relationship_goal_decisions_timeline
    ON business.relationship_goal_decisions
    (tenant_id, relationship_id, goal_id, occurred_at DESC, decision_id DESC);

CREATE OR REPLACE FUNCTION business.reject_relationship_goal_decision_mutation()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION 'relationship goal decisions are append-only';
END;
$$;

DROP TRIGGER IF EXISTS relationship_goal_decisions_no_update
    ON business.relationship_goal_decisions;
CREATE TRIGGER relationship_goal_decisions_no_update
    BEFORE UPDATE ON business.relationship_goal_decisions
    FOR EACH ROW EXECUTE FUNCTION business.reject_relationship_goal_decision_mutation();

DROP TRIGGER IF EXISTS relationship_goal_decisions_no_delete
    ON business.relationship_goal_decisions;
CREATE TRIGGER relationship_goal_decisions_no_delete
    BEFORE DELETE ON business.relationship_goal_decisions
    FOR EACH ROW EXECUTE FUNCTION business.reject_relationship_goal_decision_mutation();

ALTER TABLE business.relationship_goal_decisions ENABLE ROW LEVEL SECURITY;
ALTER TABLE business.relationship_goal_decisions FORCE ROW LEVEL SECURITY;
CREATE POLICY relationship_goal_decisions_tenant_isolation
    ON business.relationship_goal_decisions
    USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', TRUE), '')::UUID)
    WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', TRUE), '')::UUID);

GRANT SELECT, INSERT ON business.relationship_goal_decisions TO business_app;