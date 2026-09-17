-- Implements: WC-095 Sections 10 and 13 performance review windows
-- constitutional_basis: C-005, C-007, C-023, C-026, C-059, C-063, C-079

CREATE TABLE IF NOT EXISTS business.performance_review_windows (
    review_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    relationship_id UUID NOT NULL,
    agent_instance_id UUID NOT NULL,
    skill_id VARCHAR(128) NOT NULL,
    skill_version VARCHAR(32) NOT NULL,
    revision INTEGER NOT NULL,
    policy_version VARCHAR(64) NOT NULL,
    period_start TIMESTAMPTZ NOT NULL,
    period_end TIMESTAMPTZ NOT NULL,
    source_versions_json JSONB NOT NULL,
    work_delivery_json JSONB NOT NULL,
    agent_quality_json JSONB NOT NULL,
    constitutional_performance_json JSONB NOT NULL,
    commercial_usage_json JSONB NOT NULL,
    customer_business_outcome_json JSONB NOT NULL,
    customer_assessment_json JSONB NOT NULL,
    trust_autonomy_json JSONB NOT NULL,
    recommendation VARCHAR(64) NOT NULL,
    evidence_id UUID NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT performance_review_relationship_fk
    FOREIGN KEY (tenant_id, relationship_id)
    REFERENCES business.employment_relationships (tenant_id, relationship_id),
    CONSTRAINT performance_review_period_check CHECK (period_start < period_end),
    CONSTRAINT performance_review_revision_check CHECK (revision > 0),
    CONSTRAINT performance_review_source_versions_check CHECK (
        jsonb_typeof(source_versions_json) = 'object' AND source_versions_json <> '{}'::JSONB
    ),
    CONSTRAINT performance_review_dimensions_check CHECK (
        jsonb_typeof(work_delivery_json) = 'object'
        AND jsonb_typeof(agent_quality_json) = 'object'
        AND jsonb_typeof(constitutional_performance_json) = 'object'
        AND jsonb_typeof(commercial_usage_json) = 'object'
        AND jsonb_typeof(customer_business_outcome_json) = 'object'
        AND jsonb_typeof(customer_assessment_json) = 'object'
        AND jsonb_typeof(trust_autonomy_json) = 'object'
    ),
    CONSTRAINT performance_review_recommendation_check CHECK (recommendation IN (
        'CONTINUE_CURRENT_MANDATE',
        'TUNE_NON_MATERIAL_PRESENTATION',
        'PROPOSE_GOAL_OR_CONFIGURATION_CHANGE',
        'REASSESSMENT_REQUIRED',
        'PAUSE_AFFECTED_WORK',
        'ESCALATE_LIMITATION_OR_BLOCKER',
        'OFFER_TERMINATION_OR_APPROVED_MIGRATION'
    )),
    CONSTRAINT performance_review_revision_unique
    UNIQUE (tenant_id, relationship_id, skill_id, revision)
);

CREATE INDEX IF NOT EXISTS ix_performance_review_period
ON business.performance_review_windows (tenant_id, relationship_id, period_end DESC);

CREATE OR REPLACE FUNCTION business.reject_wc095_immutable_mutation()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'WC-095 runtime bindings, mandates and reviews are append-only';
END;
$$;

DROP TRIGGER IF EXISTS performance_review_windows_no_update ON business.performance_review_windows;
CREATE TRIGGER performance_review_windows_no_update
BEFORE UPDATE ON business.performance_review_windows
FOR EACH ROW EXECUTE FUNCTION business.reject_wc095_immutable_mutation();
DROP TRIGGER IF EXISTS performance_review_windows_no_delete ON business.performance_review_windows;
CREATE TRIGGER performance_review_windows_no_delete
BEFORE DELETE ON business.performance_review_windows
FOR EACH ROW EXECUTE FUNCTION business.reject_wc095_immutable_mutation();

ALTER TABLE business.performance_review_windows ENABLE ROW LEVEL SECURITY;
ALTER TABLE business.performance_review_windows FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS performance_review_windows_tenant_isolation ON business.performance_review_windows;
CREATE POLICY performance_review_windows_tenant_isolation ON business.performance_review_windows
USING (tenant_id = nullif(current_setting('app.current_tenant_id', TRUE), '')::UUID)
WITH CHECK (tenant_id = nullif(current_setting('app.current_tenant_id', TRUE), '')::UUID);

GRANT SELECT, INSERT ON business.performance_review_windows TO business_app;
