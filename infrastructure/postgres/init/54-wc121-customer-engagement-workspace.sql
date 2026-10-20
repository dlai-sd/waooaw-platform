-- Implements: architecture/reference/components/customer-engagement-workspace-solution-contract.md §§10.5-10.12
-- Constitutional basis: C-005, C-023, C-026, C-059, C-063

BEGIN;

ALTER TABLE identity.customer_portal_preferences
    ADD COLUMN IF NOT EXISTS workspace_layout_version integer NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS navigation_visibility varchar(16) NOT NULL DEFAULT 'VISIBLE',
    ADD COLUMN IF NOT EXISTS progress_visibility varchar(16) NOT NULL DEFAULT 'VISIBLE',
    ADD COLUMN IF NOT EXISTS conversation_width_percent integer NOT NULL DEFAULT 50,
    ADD COLUMN IF NOT EXISTS reduce_motion boolean NOT NULL DEFAULT false;

ALTER TABLE identity.customer_portal_preferences
    DROP CONSTRAINT IF EXISTS ck_customer_portal_workspace_layout;
DO $idempotent$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_customer_portal_workspace_layout' AND conrelid = 'identity.customer_portal_preferences'::regclass) THEN
        ALTER TABLE identity.customer_portal_preferences
            ADD CONSTRAINT ck_customer_portal_workspace_layout CHECK (
                workspace_layout_version >= 0
                AND navigation_visibility IN ('VISIBLE', 'COLLAPSED', 'HIDDEN')
                AND progress_visibility IN ('VISIBLE', 'COLLAPSED', 'HIDDEN')
                AND conversation_width_percent BETWEEN 35 AND 75
            );
    END IF;
END
$idempotent$;

ALTER TABLE business.relationship_onboard_preferences
    ADD COLUMN IF NOT EXISTS workspace_preference_version integer NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS default_focus varchar(32) NOT NULL DEFAULT 'LIFECYCLE',
    ADD COLUMN IF NOT EXISTS open_progress_on_conversation_focus boolean NOT NULL DEFAULT true;

ALTER TABLE business.relationship_onboard_preferences
    DROP CONSTRAINT IF EXISTS ck_relationship_workspace_preferences;
DO $idempotent$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_relationship_workspace_preferences' AND conrelid = 'business.relationship_onboard_preferences'::regclass) THEN
        ALTER TABLE business.relationship_onboard_preferences
            ADD CONSTRAINT ck_relationship_workspace_preferences CHECK (
                workspace_preference_version >= 0
                AND default_focus IN (
                    'LIFECYCLE',
                    'INDUCTION',
                    'SKILLS_GOALS',
                    'OPERATIONS',
                    'PERFORMANCE',
                    'BUDGET',
                    'RIGHTS'
                )
            );
    END IF;
END
$idempotent$;

CREATE TABLE IF NOT EXISTS business.customer_engagement_admission_operations (
    operation_id uuid PRIMARY KEY,
    tenant_id uuid NOT NULL,
    participant_id uuid NOT NULL,
    idempotency_key varchar(128) NOT NULL,
    client_intent_id uuid NOT NULL,
    material_request_hash char(64) NOT NULL,
    state varchar(32) NOT NULL,
    relationship_id uuid NOT NULL,
    agent_instance_id uuid NOT NULL,
    conversation_id uuid NOT NULL,
    engagement_intent varchar(8) NOT NULL,
    evidence_id uuid,
    outcome_json jsonb,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    completed_at timestamptz,
    CONSTRAINT uq_cew_admission_key UNIQUE (tenant_id, participant_id, idempotency_key),
    CONSTRAINT uq_cew_client_intent UNIQUE (tenant_id, participant_id, client_intent_id),
    CONSTRAINT ck_cew_admission_hash CHECK (material_request_hash ~ '^[0-9a-f]{64}$'),
    CONSTRAINT ck_cew_admission_state CHECK (
        state IN ('RESERVED', 'IN_PROGRESS', 'SUCCEEDED', 'RECONCILE_REQUIRED', 'CONFLICT')
    ),
    CONSTRAINT ck_cew_engagement_intent CHECK (engagement_intent IN ('TRIAL', 'HIRE'))
);

ALTER TABLE business.customer_engagement_admission_operations ENABLE ROW LEVEL SECURITY;
ALTER TABLE business.customer_engagement_admission_operations FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation_customer_engagement_admission_operations
    ON business.customer_engagement_admission_operations;
DROP POLICY IF EXISTS tenant_isolation_customer_engagement_admission_operations ON business.customer_engagement_admission_operations;
CREATE POLICY tenant_isolation_customer_engagement_admission_operations
    ON business.customer_engagement_admission_operations
    USING (
        tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
    )
    WITH CHECK (
        tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
    );

GRANT SELECT, INSERT, UPDATE
    ON business.customer_engagement_admission_operations
    TO business_app;

COMMIT;
