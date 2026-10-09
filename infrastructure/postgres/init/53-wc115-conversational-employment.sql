-- Implements: architecture/reference/components/conversational-employment-solution-contract.md §10 Data And Retention Contract
-- Constitutional basis: C-005, C-023, C-026, C-059, C-063, C-079, ADR-051
-- IB: N/A - Founder-assigned WC-115

CREATE SCHEMA IF NOT EXISTS ai_runtime;
CREATE SCHEMA IF NOT EXISTS billing;
CREATE SCHEMA IF NOT EXISTS domain_adapter;

CREATE TABLE IF NOT EXISTS business.employment_protocol_gates (
    gate_id TEXT PRIMARY KEY,
    enabled BOOLEAN NOT NULL DEFAULT FALSE,
    rollback_epoch BIGINT NOT NULL DEFAULT 0,
    prior_projection_selector TEXT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT employment_protocol_gate_id_check
        CHECK (gate_id = 'conversational-employment-candidate-v1'),
    CONSTRAINT employment_protocol_gate_epoch_check CHECK (rollback_epoch >= 0),
    CONSTRAINT employment_protocol_gate_disabled_check CHECK (enabled = FALSE)
);

CREATE TABLE IF NOT EXISTS business.employment_workspace_versions (
    tenant_id UUID NOT NULL,
    relationship_id UUID NOT NULL,
    workspace_version TEXT NOT NULL,
    manifest_version TEXT NOT NULL,
    decision_space_version BIGINT NOT NULL,
    wbe_source_version TEXT NOT NULL,
    protocol_version TEXT NOT NULL,
    projection_state TEXT NOT NULL,
    customer_summary JSONB NOT NULL DEFAULT '{}'::JSONB,
    supersedes_workspace_version TEXT,
    rollback_epoch BIGINT NOT NULL DEFAULT 0,
    produced_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at TIMESTAMPTZ,
    PRIMARY KEY (tenant_id, relationship_id, workspace_version),
    CONSTRAINT employment_workspace_relationship_fk
        FOREIGN KEY (tenant_id, relationship_id)
        REFERENCES business.employment_relationships (tenant_id, relationship_id),
    CONSTRAINT employment_workspace_state_check
        CHECK (projection_state IN ('CURRENT', 'STALE', 'PARTIAL', 'UNKNOWN', 'UNAVAILABLE', 'BLOCKED')),
    CONSTRAINT employment_workspace_epoch_check CHECK (rollback_epoch >= 0),
    CONSTRAINT employment_workspace_supersession_check
        CHECK (supersedes_workspace_version IS NULL OR supersedes_workspace_version <> workspace_version)
);

CREATE TABLE IF NOT EXISTS business.employment_plan_versions (
    tenant_id UUID NOT NULL,
    relationship_id UUID NOT NULL,
    plan_version TEXT NOT NULL,
    workspace_version TEXT NOT NULL,
    manifest_version TEXT NOT NULL,
    decision_space_version BIGINT NOT NULL,
    wbe_source_version TEXT NOT NULL,
    state TEXT NOT NULL,
    plan_json JSONB NOT NULL,
    supersedes_plan_version TEXT,
    produced_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, relationship_id, plan_version),
    CONSTRAINT employment_plan_workspace_fk
        FOREIGN KEY (tenant_id, relationship_id, workspace_version)
        REFERENCES business.employment_workspace_versions (tenant_id, relationship_id, workspace_version),
    CONSTRAINT employment_plan_state_check
        CHECK (state IN ('DRAFT', 'PROPOSED', 'ACCEPTED', 'SUPERSEDED', 'REASSESSMENT_REQUIRED', 'BLOCKED')),
    CONSTRAINT employment_plan_supersession_check
        CHECK (supersedes_plan_version IS NULL OR supersedes_plan_version <> plan_version)
);

CREATE TABLE IF NOT EXISTS business.employment_workspace_projection_content (
    tenant_id UUID NOT NULL,
    relationship_id UUID NOT NULL,
    workspace_version TEXT NOT NULL,
    projection_json JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, relationship_id, workspace_version),
    CONSTRAINT employment_workspace_projection_version_fk
        FOREIGN KEY (tenant_id, relationship_id, workspace_version)
        REFERENCES business.employment_workspace_versions (tenant_id, relationship_id, workspace_version)
);

CREATE TABLE IF NOT EXISTS business.employment_projection_erasure_tombstones (
    tenant_id UUID NOT NULL,
    relationship_id UUID NOT NULL,
    erasure_id UUID NOT NULL,
    authority_ref TEXT NOT NULL,
    erased_workspace_versions JSONB NOT NULL,
    erased_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, relationship_id, erasure_id),
    CONSTRAINT employment_projection_erasure_relationship_fk
        FOREIGN KEY (tenant_id, relationship_id)
        REFERENCES business.employment_relationships (tenant_id, relationship_id)
);

CREATE TABLE IF NOT EXISTS business.employment_owner_contexts (
    tenant_id UUID NOT NULL,
    relationship_id UUID NOT NULL,
    context_ref TEXT NOT NULL,
    context_kind TEXT NOT NULL,
    context_version TEXT NOT NULL,
    context_digest TEXT NOT NULL,
    context_json JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, relationship_id, context_ref, context_kind, context_version),
    CONSTRAINT employment_owner_context_relationship_fk
        FOREIGN KEY (tenant_id, relationship_id)
        REFERENCES business.employment_relationships (tenant_id, relationship_id)
);

CREATE TABLE IF NOT EXISTS business.employment_commands (
    tenant_id UUID NOT NULL,
    relationship_id UUID NOT NULL,
    command_id UUID NOT NULL,
    actor_id UUID NOT NULL,
    operation_family TEXT NOT NULL,
    idempotency_key UUID NOT NULL,
    canonical_payload_hash CHAR(64) NOT NULL,
    command_kind TEXT NOT NULL,
    expected_workspace_version TEXT NOT NULL,
    expected_manifest_version TEXT NOT NULL,
    rollback_epoch BIGINT NOT NULL,
    accepted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, relationship_id, command_id),
    CONSTRAINT employment_command_identity_unique
        UNIQUE (tenant_id, relationship_id, actor_id, operation_family, idempotency_key),
    CONSTRAINT employment_command_relationship_fk
        FOREIGN KEY (tenant_id, relationship_id)
        REFERENCES business.employment_relationships (tenant_id, relationship_id),
    CONSTRAINT employment_command_hash_check CHECK (canonical_payload_hash ~ '^[0-9a-f]{64}$')
);

CREATE TABLE IF NOT EXISTS business.employment_command_events (
    tenant_id UUID NOT NULL,
    relationship_id UUID NOT NULL,
    command_id UUID NOT NULL,
    event_sequence BIGINT NOT NULL,
    state TEXT NOT NULL,
    owner_steps_json JSONB NOT NULL DEFAULT '[]'::JSONB,
    evidence_refs_json JSONB NOT NULL DEFAULT '[]'::JSONB,
    result_json JSONB,
    reason_code TEXT,
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, relationship_id, command_id, event_sequence),
    CONSTRAINT employment_command_event_command_fk
        FOREIGN KEY (tenant_id, relationship_id, command_id)
        REFERENCES business.employment_commands (tenant_id, relationship_id, command_id),
    CONSTRAINT employment_command_event_sequence_check CHECK (event_sequence >= 1),
    CONSTRAINT employment_command_event_state_check
        CHECK (state IN (
            'ACCEPTED', 'VALIDATING', 'DISPATCHED', 'PARTIAL', 'UNKNOWN',
            'RECONCILING', 'COMPLETED', 'REJECTED', 'CONFLICT', 'BLOCKED'
        ))
);

CREATE TABLE IF NOT EXISTS business.employment_compatibility_scans (
    tenant_id UUID NOT NULL,
    scan_id UUID NOT NULL,
    required_protocol_version TEXT NOT NULL,
    inventory_version TEXT NOT NULL,
    inventory_digest CHAR(64) NOT NULL,
    state TEXT NOT NULL,
    result_json JSONB,
    rollback_epoch BIGINT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    resolved_at TIMESTAMPTZ,
    PRIMARY KEY (tenant_id, scan_id),
    CONSTRAINT employment_scan_identity_unique
        UNIQUE (tenant_id, required_protocol_version, inventory_version, inventory_digest),
    CONSTRAINT employment_scan_digest_check CHECK (inventory_digest ~ '^[0-9a-f]{64}$'),
    CONSTRAINT employment_scan_state_check
        CHECK (state IN ('PENDING', 'RUNNING', 'PARTIAL', 'COMPATIBLE', 'INCOMPATIBLE', 'UNKNOWN', 'BLOCKED'))
);

CREATE TABLE IF NOT EXISTS business.employment_outbox (
    tenant_id UUID NOT NULL,
    event_id UUID NOT NULL,
    relationship_id UUID NOT NULL,
    owner TEXT NOT NULL,
    aggregate_id TEXT NOT NULL,
    aggregate_version TEXT NOT NULL,
    event_type TEXT NOT NULL,
    payload_json JSONB NOT NULL,
    rollback_epoch BIGINT NOT NULL,
    disposition TEXT NOT NULL DEFAULT 'PENDING',
    attempts INTEGER NOT NULL DEFAULT 0,
    available_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, event_id),
    CONSTRAINT employment_outbox_relationship_fk
        FOREIGN KEY (tenant_id, relationship_id)
        REFERENCES business.employment_relationships (tenant_id, relationship_id),
    CONSTRAINT employment_outbox_disposition_check
        CHECK (disposition IN ('PENDING', 'LEASED', 'DELIVERED', 'BLOCKED', 'QUARANTINED')),
    CONSTRAINT employment_outbox_attempts_check CHECK (attempts >= 0)
);

CREATE TABLE IF NOT EXISTS business.employment_inbox (
    tenant_id UUID NOT NULL,
    consumer TEXT NOT NULL,
    event_id UUID NOT NULL,
    effect_digest CHAR(64) NOT NULL,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, consumer, event_id),
    CONSTRAINT employment_inbox_digest_check CHECK (effect_digest ~ '^[0-9a-f]{64}$')
);

CREATE TABLE IF NOT EXISTS professional.employment_execution_records (
    tenant_id UUID NOT NULL,
    relationship_id UUID NOT NULL,
    command_id UUID NOT NULL,
    record_sequence BIGINT NOT NULL,
    record_kind TEXT NOT NULL,
    state TEXT NOT NULL,
    owner_key TEXT NOT NULL,
    provider_correlation_ref TEXT,
    reason_code TEXT,
    payload_ref TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, relationship_id, command_id, record_sequence),
    CONSTRAINT professional_employment_record_sequence_check CHECK (record_sequence >= 1),
    CONSTRAINT professional_employment_record_kind_check
        CHECK (record_kind IN ('INTENT', 'OUTCOME', 'RECONCILIATION')),
    CONSTRAINT professional_employment_record_state_check
        CHECK (state IN ('PENDING', 'DISPATCHED', 'PARTIAL', 'UNKNOWN', 'RECONCILING', 'COMPLETED', 'FAILED', 'BLOCKED'))
);

CREATE TABLE IF NOT EXISTS ai_runtime.employment_patch_proposals (
    tenant_id UUID NOT NULL,
    relationship_ref TEXT NOT NULL,
    proposal_id UUID NOT NULL,
    idempotency_key UUID NOT NULL,
    request_digest CHAR(64) NOT NULL,
    protocol_version TEXT NOT NULL,
    semantic_catalogue_version TEXT NOT NULL,
    semantic_catalogue_digest CHAR(64) NOT NULL,
    prompt_policy_version TEXT NOT NULL,
    prompt_policy_digest CHAR(64) NOT NULL,
    model_policy_version TEXT NOT NULL,
    model_policy_digest CHAR(64) NOT NULL,
    receipt_json JSONB NOT NULL,
    proposal_json JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, relationship_ref, proposal_id),
    CONSTRAINT air_employment_proposal_identity_unique
        UNIQUE (tenant_id, relationship_ref, idempotency_key),
    CONSTRAINT air_employment_request_digest_check CHECK (request_digest ~ '^[0-9a-f]{64}$'),
    CONSTRAINT air_employment_catalogue_digest_check CHECK (semantic_catalogue_digest ~ '^[0-9a-f]{64}$'),
    CONSTRAINT air_employment_prompt_digest_check CHECK (prompt_policy_digest ~ '^[0-9a-f]{64}$'),
    CONSTRAINT air_employment_model_digest_check CHECK (model_policy_digest ~ '^[0-9a-f]{64}$')
);

ALTER TABLE ai_runtime.employment_patch_proposals
ADD COLUMN IF NOT EXISTS proposal_json JSONB;
DROP TRIGGER IF EXISTS ai_runtime_employment_patch_proposals_append_only
ON ai_runtime.employment_patch_proposals;
UPDATE ai_runtime.employment_patch_proposals
SET proposal_json = receipt_json
WHERE proposal_json IS NULL;
ALTER TABLE ai_runtime.employment_patch_proposals
ALTER COLUMN proposal_json SET NOT NULL;

CREATE TABLE IF NOT EXISTS ai_runtime.employment_patch_proposal_events (
    tenant_id UUID NOT NULL,
    relationship_ref TEXT NOT NULL,
    proposal_id UUID NOT NULL,
    event_sequence BIGINT NOT NULL,
    state TEXT NOT NULL,
    result_json JSONB,
    reason_code TEXT,
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, relationship_ref, proposal_id, event_sequence),
    CONSTRAINT air_employment_proposal_event_fk
        FOREIGN KEY (tenant_id, relationship_ref, proposal_id)
        REFERENCES ai_runtime.employment_patch_proposals (tenant_id, relationship_ref, proposal_id),
    CONSTRAINT air_employment_event_sequence_check CHECK (event_sequence >= 1),
    CONSTRAINT air_employment_event_state_check
        CHECK (state IN ('PENDING', 'PROPOSED', 'UNREPRESENTABLE', 'FAILED')),
    CONSTRAINT air_employment_event_result_check CHECK (
        (state = 'PROPOSED' AND result_json IS NOT NULL AND reason_code IS NULL)
        OR (state IN ('UNREPRESENTABLE', 'FAILED') AND result_json IS NULL AND reason_code IS NOT NULL)
        OR (state = 'PENDING' AND result_json IS NULL AND reason_code IS NULL)
    )
);

CREATE TABLE IF NOT EXISTS ai_runtime.employment_patch_transient_content (
    tenant_id UUID NOT NULL,
    relationship_ref TEXT NOT NULL,
    proposal_id UUID NOT NULL,
    encrypted_content_ref TEXT NOT NULL,
    delete_after TIMESTAMPTZ NOT NULL,
    absolute_expiry TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, relationship_ref, proposal_id),
    CONSTRAINT air_employment_transient_proposal_fk
        FOREIGN KEY (tenant_id, relationship_ref, proposal_id)
        REFERENCES ai_runtime.employment_patch_proposals (tenant_id, relationship_ref, proposal_id),
    CONSTRAINT air_employment_transient_expiry_check
        CHECK (delete_after <= absolute_expiry AND absolute_expiry <= created_at + INTERVAL '24 hours')
);

CREATE TABLE IF NOT EXISTS billing.employment_eligibility_versions (
    tenant_id UUID NOT NULL,
    relationship_id UUID NOT NULL,
    skill_id TEXT NOT NULL,
    source_version TEXT NOT NULL,
    state TEXT NOT NULL,
    reason_codes JSONB NOT NULL DEFAULT '[]'::JSONB,
    consequence_json JSONB NOT NULL DEFAULT '{}'::JSONB,
    produced_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    supersedes_source_version TEXT,
    PRIMARY KEY (tenant_id, relationship_id, skill_id, source_version),
    CONSTRAINT billing_employment_state_check
        CHECK (state IN ('ELIGIBLE', 'INELIGIBLE', 'STALE', 'UNKNOWN', 'UNAVAILABLE', 'BLOCKED')),
    CONSTRAINT billing_employment_supersession_check
        CHECK (supersedes_source_version IS NULL OR supersedes_source_version <> source_version)
);

CREATE TABLE IF NOT EXISTS domain_adapter.employment_interface_manifests (
    tenant_id UUID NOT NULL,
    agent_type TEXT NOT NULL,
    agent_version TEXT NOT NULL,
    manifest_version TEXT NOT NULL,
    manifest_digest CHAR(64) NOT NULL,
    protocol_major INTEGER NOT NULL,
    manifest_json JSONB NOT NULL,
    supersedes_manifest_version TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, agent_type, agent_version, manifest_version),
    CONSTRAINT domain_adapter_manifest_digest_check CHECK (manifest_digest ~ '^[0-9a-f]{64}$'),
    CONSTRAINT domain_adapter_protocol_major_check CHECK (protocol_major >= 1),
    CONSTRAINT domain_adapter_manifest_supersession_check
        CHECK (supersedes_manifest_version IS NULL OR supersedes_manifest_version <> manifest_version)
);

CREATE TABLE IF NOT EXISTS domain_adapter.employment_assessments (
    tenant_id UUID NOT NULL,
    assessment_id UUID NOT NULL,
    agent_type TEXT NOT NULL,
    agent_version TEXT NOT NULL,
    manifest_version TEXT NOT NULL,
    assessment_kind TEXT NOT NULL,
    request_digest CHAR(64) NOT NULL,
    result_json JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, assessment_id),
    CONSTRAINT domain_adapter_assessment_identity_unique
        UNIQUE (tenant_id, agent_type, agent_version, manifest_version, assessment_kind, request_digest),
    CONSTRAINT domain_adapter_assessment_digest_check CHECK (request_digest ~ '^[0-9a-f]{64}$'),
    CONSTRAINT domain_adapter_assessment_kind_check
        CHECK (assessment_kind IN (
            'INDUCTION_REQUIREMENTS', 'PLAN_VALIDATION', 'MATERIAL_CHANGE',
            'DEPENDENCY_ISOLATION', 'PERFORMANCE'
        ))
);

CREATE INDEX IF NOT EXISTS idx_employment_outbox_delivery
ON business.employment_outbox (tenant_id, disposition, available_at, created_at);
CREATE INDEX IF NOT EXISTS idx_professional_employment_reconciliation
ON professional.employment_execution_records (tenant_id, relationship_id, state, created_at);
CREATE INDEX IF NOT EXISTS idx_air_employment_transient_expiry
ON ai_runtime.employment_patch_transient_content (delete_after, absolute_expiry);

CREATE OR REPLACE FUNCTION prevent_wc115_append_only_mutation()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION '% is append-only', TG_TABLE_NAME;
END;
$$ LANGUAGE plpgsql;

DO $$
DECLARE
    qualified_table TEXT;
    trigger_name TEXT;
BEGIN
    FOREACH qualified_table IN ARRAY ARRAY[
        'business.employment_workspace_versions',
        'business.employment_plan_versions',
        'business.employment_owner_contexts',
        'business.employment_projection_erasure_tombstones',
        'business.employment_commands',
        'business.employment_command_events',
        'business.employment_inbox',
        'professional.employment_execution_records',
        'ai_runtime.employment_patch_proposals',
        'ai_runtime.employment_patch_proposal_events',
        'billing.employment_eligibility_versions',
        'domain_adapter.employment_interface_manifests',
        'domain_adapter.employment_assessments'
    ]
    LOOP
        trigger_name := replace(qualified_table, '.', '_') || '_append_only';
        EXECUTE format('DROP TRIGGER IF EXISTS %I ON %s', trigger_name, qualified_table);
        EXECUTE format(
            'CREATE TRIGGER %I BEFORE UPDATE OR DELETE ON %s '
            'FOR EACH ROW EXECUTE FUNCTION prevent_wc115_append_only_mutation()',
            trigger_name,
            qualified_table
        );
    END LOOP;
END;
$$;

ALTER TABLE business.employment_workspace_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE business.employment_workspace_versions FORCE ROW LEVEL SECURITY;
ALTER TABLE business.employment_plan_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE business.employment_plan_versions FORCE ROW LEVEL SECURITY;
ALTER TABLE business.employment_workspace_projection_content ENABLE ROW LEVEL SECURITY;
ALTER TABLE business.employment_workspace_projection_content FORCE ROW LEVEL SECURITY;
ALTER TABLE business.employment_projection_erasure_tombstones ENABLE ROW LEVEL SECURITY;
ALTER TABLE business.employment_projection_erasure_tombstones FORCE ROW LEVEL SECURITY;
ALTER TABLE business.employment_owner_contexts ENABLE ROW LEVEL SECURITY;
ALTER TABLE business.employment_owner_contexts FORCE ROW LEVEL SECURITY;
ALTER TABLE business.employment_commands ENABLE ROW LEVEL SECURITY;
ALTER TABLE business.employment_commands FORCE ROW LEVEL SECURITY;
ALTER TABLE business.employment_command_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE business.employment_command_events FORCE ROW LEVEL SECURITY;
ALTER TABLE business.employment_compatibility_scans ENABLE ROW LEVEL SECURITY;
ALTER TABLE business.employment_compatibility_scans FORCE ROW LEVEL SECURITY;
ALTER TABLE business.employment_outbox ENABLE ROW LEVEL SECURITY;
ALTER TABLE business.employment_outbox FORCE ROW LEVEL SECURITY;
ALTER TABLE business.employment_inbox ENABLE ROW LEVEL SECURITY;
ALTER TABLE business.employment_inbox FORCE ROW LEVEL SECURITY;
ALTER TABLE professional.employment_execution_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE professional.employment_execution_records FORCE ROW LEVEL SECURITY;
ALTER TABLE ai_runtime.employment_patch_proposals ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_runtime.employment_patch_proposals FORCE ROW LEVEL SECURITY;
ALTER TABLE ai_runtime.employment_patch_proposal_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_runtime.employment_patch_proposal_events FORCE ROW LEVEL SECURITY;
ALTER TABLE ai_runtime.employment_patch_transient_content ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_runtime.employment_patch_transient_content FORCE ROW LEVEL SECURITY;
ALTER TABLE billing.employment_eligibility_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE billing.employment_eligibility_versions FORCE ROW LEVEL SECURITY;
ALTER TABLE domain_adapter.employment_interface_manifests ENABLE ROW LEVEL SECURITY;
ALTER TABLE domain_adapter.employment_interface_manifests FORCE ROW LEVEL SECURITY;
ALTER TABLE domain_adapter.employment_assessments ENABLE ROW LEVEL SECURITY;
ALTER TABLE domain_adapter.employment_assessments FORCE ROW LEVEL SECURITY;

CREATE POLICY employment_workspace_tenant_isolation ON business.employment_workspace_versions
USING (tenant_id = nullif(current_setting('app.current_tenant_id', TRUE), '')::UUID)
WITH CHECK (tenant_id = nullif(current_setting('app.current_tenant_id', TRUE), '')::UUID);
CREATE POLICY employment_plan_tenant_isolation ON business.employment_plan_versions
USING (tenant_id = nullif(current_setting('app.current_tenant_id', TRUE), '')::UUID)
WITH CHECK (tenant_id = nullif(current_setting('app.current_tenant_id', TRUE), '')::UUID);
CREATE POLICY employment_workspace_projection_content_tenant_isolation
ON business.employment_workspace_projection_content
USING (tenant_id = nullif(current_setting('app.current_tenant_id', TRUE), '')::UUID)
WITH CHECK (tenant_id = nullif(current_setting('app.current_tenant_id', TRUE), '')::UUID);
CREATE POLICY employment_projection_erasure_tombstone_tenant_isolation
ON business.employment_projection_erasure_tombstones
USING (tenant_id = nullif(current_setting('app.current_tenant_id', TRUE), '')::UUID)
WITH CHECK (tenant_id = nullif(current_setting('app.current_tenant_id', TRUE), '')::UUID);
CREATE POLICY employment_owner_context_tenant_isolation
ON business.employment_owner_contexts
USING (tenant_id = nullif(current_setting('app.current_tenant_id', TRUE), '')::UUID)
WITH CHECK (tenant_id = nullif(current_setting('app.current_tenant_id', TRUE), '')::UUID);
CREATE POLICY employment_command_tenant_isolation ON business.employment_commands
USING (tenant_id = nullif(current_setting('app.current_tenant_id', TRUE), '')::UUID)
WITH CHECK (tenant_id = nullif(current_setting('app.current_tenant_id', TRUE), '')::UUID);
CREATE POLICY employment_command_event_tenant_isolation ON business.employment_command_events
USING (tenant_id = nullif(current_setting('app.current_tenant_id', TRUE), '')::UUID)
WITH CHECK (tenant_id = nullif(current_setting('app.current_tenant_id', TRUE), '')::UUID);
CREATE POLICY employment_scan_tenant_isolation ON business.employment_compatibility_scans
USING (tenant_id = nullif(current_setting('app.current_tenant_id', TRUE), '')::UUID)
WITH CHECK (tenant_id = nullif(current_setting('app.current_tenant_id', TRUE), '')::UUID);
CREATE POLICY employment_outbox_tenant_isolation ON business.employment_outbox
USING (tenant_id = nullif(current_setting('app.current_tenant_id', TRUE), '')::UUID)
WITH CHECK (tenant_id = nullif(current_setting('app.current_tenant_id', TRUE), '')::UUID);
CREATE POLICY employment_inbox_tenant_isolation ON business.employment_inbox
USING (tenant_id = nullif(current_setting('app.current_tenant_id', TRUE), '')::UUID)
WITH CHECK (tenant_id = nullif(current_setting('app.current_tenant_id', TRUE), '')::UUID);
CREATE POLICY professional_employment_tenant_isolation ON professional.employment_execution_records
USING (tenant_id = nullif(current_setting('app.current_tenant_id', TRUE), '')::UUID)
WITH CHECK (tenant_id = nullif(current_setting('app.current_tenant_id', TRUE), '')::UUID);
CREATE POLICY air_employment_tenant_isolation ON ai_runtime.employment_patch_proposals
USING (tenant_id = nullif(current_setting('app.current_tenant_id', TRUE), '')::UUID)
WITH CHECK (tenant_id = nullif(current_setting('app.current_tenant_id', TRUE), '')::UUID);
CREATE POLICY air_employment_event_tenant_isolation ON ai_runtime.employment_patch_proposal_events
USING (tenant_id = nullif(current_setting('app.current_tenant_id', TRUE), '')::UUID)
WITH CHECK (tenant_id = nullif(current_setting('app.current_tenant_id', TRUE), '')::UUID);
CREATE POLICY air_employment_transient_tenant_isolation ON ai_runtime.employment_patch_transient_content
USING (tenant_id = nullif(current_setting('app.current_tenant_id', TRUE), '')::UUID)
WITH CHECK (tenant_id = nullif(current_setting('app.current_tenant_id', TRUE), '')::UUID);
CREATE POLICY billing_employment_tenant_isolation ON billing.employment_eligibility_versions
USING (tenant_id = nullif(current_setting('app.current_tenant_id', TRUE), '')::UUID)
WITH CHECK (tenant_id = nullif(current_setting('app.current_tenant_id', TRUE), '')::UUID);
CREATE POLICY domain_adapter_manifest_tenant_isolation ON domain_adapter.employment_interface_manifests
USING (tenant_id = nullif(current_setting('app.current_tenant_id', TRUE), '')::UUID)
WITH CHECK (tenant_id = nullif(current_setting('app.current_tenant_id', TRUE), '')::UUID);
CREATE POLICY domain_adapter_assessment_tenant_isolation ON domain_adapter.employment_assessments
USING (tenant_id = nullif(current_setting('app.current_tenant_id', TRUE), '')::UUID)
WITH CHECK (tenant_id = nullif(current_setting('app.current_tenant_id', TRUE), '')::UUID);

GRANT SELECT, INSERT ON business.employment_workspace_versions TO business_app;
GRANT SELECT, INSERT ON business.employment_plan_versions TO business_app;
GRANT SELECT, INSERT, DELETE ON business.employment_workspace_projection_content TO business_app;
GRANT SELECT, INSERT ON business.employment_projection_erasure_tombstones TO business_app;
GRANT SELECT, INSERT ON business.employment_owner_contexts TO business_app;
GRANT SELECT, INSERT ON business.employment_commands TO business_app;
GRANT SELECT, INSERT ON business.employment_command_events TO business_app;
GRANT SELECT, INSERT ON business.employment_compatibility_scans TO business_app;
GRANT SELECT, INSERT, UPDATE ON business.employment_outbox TO business_app;
GRANT SELECT, INSERT ON business.employment_inbox TO business_app;
GRANT USAGE ON SCHEMA professional TO runtime_app;
GRANT SELECT, INSERT ON professional.employment_execution_records TO runtime_app;
GRANT USAGE ON SCHEMA ai_runtime TO ai_runtime_app;
GRANT SELECT, INSERT ON ai_runtime.employment_patch_proposals TO ai_runtime_app;
GRANT SELECT, INSERT ON ai_runtime.employment_patch_proposal_events TO ai_runtime_app;
GRANT SELECT, INSERT, DELETE ON ai_runtime.employment_patch_transient_content TO ai_runtime_app;
GRANT USAGE ON SCHEMA billing TO wbe_app;
GRANT SELECT, INSERT ON billing.employment_eligibility_versions TO wbe_app;
GRANT USAGE ON SCHEMA domain_adapter TO domain_adapter_app;
GRANT SELECT, INSERT ON domain_adapter.employment_interface_manifests TO domain_adapter_app;
GRANT SELECT, INSERT ON domain_adapter.employment_assessments TO domain_adapter_app;
