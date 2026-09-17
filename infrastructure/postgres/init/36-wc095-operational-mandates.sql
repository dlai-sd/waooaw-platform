-- Implements: WC-095 Section 6.3 operational mandate snapshots
-- constitutional_basis: C-005, C-007, C-023, C-026, C-059, C-063, C-079

ALTER TABLE business.conversation_messages
ADD COLUMN IF NOT EXISTS skill_id VARCHAR(128) NOT NULL DEFAULT '';

CREATE TABLE IF NOT EXISTS business.agent_skill_runtime_bindings (
    binding_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    admission_id UUID NOT NULL,
    skill_id VARCHAR(128) NOT NULL,
    skill_version VARCHAR(32) NOT NULL,
    release_sequence INTEGER NOT NULL,
    specification_revision VARCHAR(64) NOT NULL,
    specification_digest VARCHAR(71) NOT NULL,
    prompt_version VARCHAR(64) NOT NULL,
    prompt_digest VARCHAR(71) NOT NULL,
    input_schema_digest VARCHAR(71) NOT NULL,
    output_schema_digest VARCHAR(71) NOT NULL,
    activated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    superseded_at TIMESTAMPTZ,
    CONSTRAINT agent_skill_runtime_binding_admission_fk
    FOREIGN KEY (tenant_id, admission_id)
    REFERENCES business.agent_admissions (tenant_id, admission_id),
    CONSTRAINT agent_skill_runtime_binding_release_check CHECK (release_sequence > 0),
    CONSTRAINT agent_skill_runtime_binding_spec_digest_check CHECK (specification_digest ~ '^sha256:[0-9a-f]{64}$'),
    CONSTRAINT agent_skill_runtime_binding_prompt_digest_check CHECK (prompt_digest ~ '^sha256:[0-9a-f]{64}$'),
    CONSTRAINT agent_skill_runtime_binding_input_digest_check CHECK (input_schema_digest ~ '^sha256:[0-9a-f]{64}$'),
    CONSTRAINT agent_skill_runtime_binding_output_digest_check CHECK (output_schema_digest ~ '^sha256:[0-9a-f]{64}$')
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_agent_skill_runtime_binding_active
ON business.agent_skill_runtime_bindings (tenant_id, admission_id, skill_id, skill_version)
WHERE superseded_at IS NULL;

CREATE TABLE IF NOT EXISTS business.operational_mandate_snapshots (
    mandate_id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    relationship_id UUID NOT NULL,
    agent_instance_id UUID NOT NULL,
    actor_participant_id UUID NOT NULL,
    admission_id UUID NOT NULL,
    runtime_binding_id UUID NOT NULL REFERENCES business.agent_skill_runtime_bindings (binding_id),
    contract_id UUID NOT NULL,
    decision_space_snapshot_id UUID NOT NULL,
    constitutional_evidence_id UUID NOT NULL,
    idempotency_identity UUID NOT NULL,
    skill_id VARCHAR(128) NOT NULL,
    mandate_digest VARCHAR(71) NOT NULL,
    mandate_json JSONB NOT NULL,
    deadline TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT operational_mandate_relationship_fk
    FOREIGN KEY (tenant_id, relationship_id)
    REFERENCES business.employment_relationships (tenant_id, relationship_id),
    CONSTRAINT operational_mandate_admission_fk
    FOREIGN KEY (tenant_id, admission_id)
    REFERENCES business.agent_admissions (tenant_id, admission_id),
    CONSTRAINT operational_mandate_digest_check CHECK (mandate_digest ~ '^sha256:[0-9a-f]{64}$'),
    CONSTRAINT operational_mandate_idempotency_unique
    UNIQUE (tenant_id, relationship_id, idempotency_identity)
);

CREATE OR REPLACE FUNCTION business.reject_wc095_immutable_mutation()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'WC-095 runtime bindings and mandates are append-only';
END;
$$;

CREATE TRIGGER agent_skill_runtime_bindings_no_update
BEFORE UPDATE ON business.agent_skill_runtime_bindings
FOR EACH ROW EXECUTE FUNCTION business.reject_wc095_immutable_mutation();
CREATE TRIGGER agent_skill_runtime_bindings_no_delete
BEFORE DELETE ON business.agent_skill_runtime_bindings
FOR EACH ROW EXECUTE FUNCTION business.reject_wc095_immutable_mutation();
CREATE TRIGGER operational_mandate_snapshots_no_update
BEFORE UPDATE ON business.operational_mandate_snapshots
FOR EACH ROW EXECUTE FUNCTION business.reject_wc095_immutable_mutation();
CREATE TRIGGER operational_mandate_snapshots_no_delete
BEFORE DELETE ON business.operational_mandate_snapshots
FOR EACH ROW EXECUTE FUNCTION business.reject_wc095_immutable_mutation();

ALTER TABLE business.agent_skill_runtime_bindings ENABLE ROW LEVEL SECURITY;
ALTER TABLE business.agent_skill_runtime_bindings FORCE ROW LEVEL SECURITY;
ALTER TABLE business.operational_mandate_snapshots ENABLE ROW LEVEL SECURITY;
ALTER TABLE business.operational_mandate_snapshots FORCE ROW LEVEL SECURITY;

CREATE POLICY agent_skill_runtime_bindings_tenant_isolation ON business.agent_skill_runtime_bindings
USING (tenant_id = nullif(current_setting('app.current_tenant_id', TRUE), '')::UUID)
WITH CHECK (tenant_id = nullif(current_setting('app.current_tenant_id', TRUE), '')::UUID);
CREATE POLICY operational_mandate_snapshots_tenant_isolation ON business.operational_mandate_snapshots
USING (tenant_id = nullif(current_setting('app.current_tenant_id', TRUE), '')::UUID)
WITH CHECK (tenant_id = nullif(current_setting('app.current_tenant_id', TRUE), '')::UUID);

GRANT SELECT, INSERT ON business.agent_skill_runtime_bindings TO business_app;
GRANT SELECT, INSERT ON business.operational_mandate_snapshots TO business_app;
