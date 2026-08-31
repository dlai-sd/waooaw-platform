-- Implements: WC-079 AA-03, AA-06, AA-08
-- constitutional_basis: C-003, C-005, C-007, C-023, C-026, C-059, C-063

CREATE TABLE IF NOT EXISTS business.agent_admissions (
    admission_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    professional_type_id VARCHAR(100) NOT NULL,
    professional_version VARCHAR(64) NOT NULL,
    owner_subject_id UUID NOT NULL,
    submitter_subject_id UUID,
    state VARCHAR(32) NOT NULL DEFAULT 'DRAFT',
    state_version INTEGER NOT NULL DEFAULT 0,
    current_revision INTEGER NOT NULL DEFAULT 0,
    admission_content_digest VARCHAR(71),
    evidence_set_digest VARCHAR(71),
    artifact_digest VARCHAR(71),
    policy_version VARCHAR(64),
    successor_version VARCHAR(64),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_agent_admissions_tenant_identity UNIQUE (tenant_id, professional_type_id, professional_version),
    CONSTRAINT uq_agent_admissions_tenant_id UNIQUE (tenant_id, admission_id),
    CONSTRAINT agent_admission_state_check CHECK (state IN ('DRAFT','VALIDATING','REMEDIATION_REQUIRED','VALIDATED','READY_FOR_REVIEW','APPROVED','ACTIVE','SUSPENDED','SUPERSEDED','RETIRED','REJECTED')),
    CONSTRAINT agent_admission_version_check CHECK (state_version >= 0 AND current_revision >= 0),
    CONSTRAINT agent_admission_content_digest_check CHECK (admission_content_digest IS NULL OR admission_content_digest ~ '^sha256:[0-9a-f]{64}$'),
    CONSTRAINT agent_admission_evidence_digest_check CHECK (evidence_set_digest IS NULL OR evidence_set_digest ~ '^sha256:[0-9a-f]{64}$'),
    CONSTRAINT agent_admission_artifact_digest_check CHECK (artifact_digest IS NULL OR artifact_digest ~ '^sha256:[0-9a-f]{64}$')
);

CREATE TABLE IF NOT EXISTS business.agent_admission_revisions (
    revision_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    admission_id UUID NOT NULL,
    revision INTEGER NOT NULL,
    contract_schema_version VARCHAR(32) NOT NULL,
    admission_content_digest VARCHAR(71) NOT NULL,
    admission_content JSONB NOT NULL,
    actor_subject_id UUID NOT NULL,
    predecessor_revision_id UUID,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT agent_admission_revision_parent_fk FOREIGN KEY (tenant_id, admission_id) REFERENCES business.agent_admissions (tenant_id, admission_id),
    CONSTRAINT uq_agent_admission_revision_tenant_id UNIQUE (tenant_id, admission_id, revision_id),
    CONSTRAINT agent_admission_revision_predecessor_fk FOREIGN KEY (tenant_id, admission_id, predecessor_revision_id) REFERENCES business.agent_admission_revisions (tenant_id, admission_id, revision_id),
    CONSTRAINT uq_agent_admission_revision UNIQUE (tenant_id, admission_id, revision),
    CONSTRAINT uq_agent_admission_revision_digest UNIQUE (tenant_id, admission_id, admission_content_digest),
    CONSTRAINT agent_admission_revision_number_check CHECK (revision > 0),
    CONSTRAINT agent_admission_revision_digest_check CHECK (admission_content_digest ~ '^sha256:[0-9a-f]{64}$')
);

CREATE TABLE IF NOT EXISTS business.agent_admission_validations (
    validation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    admission_id UUID NOT NULL,
    revision INTEGER NOT NULL,
    validator_profile VARCHAR(64) NOT NULL,
    idempotency_key UUID NOT NULL,
    request_hash VARCHAR(71) NOT NULL,
    result VARCHAR(8) NOT NULL,
    finding_count INTEGER NOT NULL,
    validated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT agent_admission_validation_parent_fk FOREIGN KEY (tenant_id, admission_id) REFERENCES business.agent_admissions (tenant_id, admission_id),
    CONSTRAINT uq_agent_admission_validation_tenant_id UNIQUE (tenant_id, validation_id),
    CONSTRAINT uq_agent_admission_validation UNIQUE (tenant_id, admission_id, revision, validator_profile, idempotency_key),
    CONSTRAINT uq_agent_admission_validation_tenant_key UNIQUE (tenant_id, idempotency_key),
    CONSTRAINT agent_admission_validation_result_check CHECK (result IN ('PASS','FAIL')),
    CONSTRAINT agent_admission_validation_count_check CHECK (finding_count >= 0),
    CONSTRAINT agent_admission_validation_hash_check CHECK (request_hash ~ '^sha256:[0-9a-f]{64}$')
);

CREATE TABLE IF NOT EXISTS business.agent_admission_findings (
    finding_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    validation_id UUID NOT NULL,
    rule_id VARCHAR(16) NOT NULL,
    severity VARCHAR(8) NOT NULL,
    contract_path VARCHAR(512) NOT NULL,
    constitutional_basis VARCHAR(128) NOT NULL,
    expected VARCHAR(512) NOT NULL,
    observed_category VARCHAR(128) NOT NULL,
    remediation VARCHAR(512) NOT NULL,
    blocking BOOLEAN NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT agent_admission_finding_validation_fk FOREIGN KEY (tenant_id, validation_id) REFERENCES business.agent_admission_validations (tenant_id, validation_id),
    CONSTRAINT uq_agent_admission_finding UNIQUE (tenant_id, validation_id, rule_id, contract_path),
    CONSTRAINT agent_admission_finding_rule_check CHECK (rule_id ~ '^AAV-0(0[1-9]|1[0-4])$'),
    CONSTRAINT agent_admission_finding_severity_check CHECK (severity IN ('ERROR','WARNING'))
);

CREATE TABLE IF NOT EXISTS business.agent_admission_assertions (
    assertion_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    admission_id UUID NOT NULL,
    assertion_type VARCHAR(64) NOT NULL,
    subject_digest VARCHAR(71) NOT NULL,
    environment VARCHAR(16) NOT NULL,
    status VARCHAR(16) NOT NULL,
    source_authority VARCHAR(128) NOT NULL,
    observed_at TIMESTAMPTZ NOT NULL,
    valid_until TIMESTAMPTZ NOT NULL,
    policy_version VARCHAR(64) NOT NULL,
    evidence_ref VARCHAR(256) NOT NULL,
    CONSTRAINT agent_admission_assertion_parent_fk FOREIGN KEY (tenant_id, admission_id) REFERENCES business.agent_admissions (tenant_id, admission_id),
    CONSTRAINT uq_agent_admission_assertion UNIQUE (tenant_id, admission_id, assertion_type, environment, subject_digest, policy_version, observed_at),
    CONSTRAINT agent_admission_assertion_status_check CHECK (status IN ('PASS','FAIL','UNKNOWN','UNAVAILABLE','REVOKED')),
    CONSTRAINT agent_admission_assertion_environment_check CHECK (environment IN ('demo','uat','prod')),
    CONSTRAINT agent_admission_assertion_expiry_check CHECK (valid_until > observed_at),
    CONSTRAINT agent_admission_assertion_digest_check CHECK (subject_digest ~ '^sha256:[0-9a-f]{64}$')
);

CREATE TABLE IF NOT EXISTS business.agent_admission_transitions (
    transition_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    admission_id UUID NOT NULL,
    from_state VARCHAR(32) NOT NULL,
    to_state VARCHAR(32) NOT NULL,
    actor_subject_id UUID NOT NULL,
    actor_authority VARCHAR(64) NOT NULL,
    correlation_id UUID NOT NULL,
    admission_content_digest VARCHAR(71) NOT NULL,
    evidence_set_digest VARCHAR(71) NOT NULL,
    artifact_digest VARCHAR(71),
    policy_version VARCHAR(64) NOT NULL,
    ce_evidence_ref UUID NOT NULL,
    reason_category VARCHAR(64),
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT agent_admission_transition_parent_fk FOREIGN KEY (tenant_id, admission_id) REFERENCES business.agent_admissions (tenant_id, admission_id),
    CONSTRAINT uq_agent_admission_transition_tenant_id UNIQUE (tenant_id, transition_id),
    CONSTRAINT uq_agent_admission_transition UNIQUE (tenant_id, admission_id, from_state, to_state, correlation_id),
    CONSTRAINT agent_admission_transition_content_check CHECK (admission_content_digest ~ '^sha256:[0-9a-f]{64}$'),
    CONSTRAINT agent_admission_transition_evidence_check CHECK (evidence_set_digest ~ '^sha256:[0-9a-f]{64}$'),
    CONSTRAINT agent_admission_transition_artifact_check CHECK (artifact_digest IS NULL OR artifact_digest ~ '^sha256:[0-9a-f]{64}$')
);

CREATE TABLE IF NOT EXISTS business.agent_admission_idempotency (
    idempotency_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    admission_id UUID NOT NULL,
    operation VARCHAR(64) NOT NULL,
    idempotency_key UUID NOT NULL,
    actor_subject_id UUID NOT NULL,
    subject_digest VARCHAR(71),
    material_request_hash VARCHAR(71) NOT NULL,
    outcome_reference UUID,
    response_json JSONB,
    status VARCHAR(16) NOT NULL DEFAULT 'RECEIVED',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ,
    CONSTRAINT agent_admission_idempotency_parent_fk FOREIGN KEY (tenant_id, admission_id) REFERENCES business.agent_admissions (tenant_id, admission_id),
    CONSTRAINT uq_agent_admission_idempotency UNIQUE (tenant_id, admission_id, operation, idempotency_key),
    CONSTRAINT uq_agent_admission_idempotency_tenant_key UNIQUE (tenant_id, operation, idempotency_key),
    CONSTRAINT agent_admission_idempotency_status_check CHECK (status IN ('RECEIVED','COMPLETED','FAILED')),
    CONSTRAINT agent_admission_idempotency_request_hash_check CHECK (material_request_hash ~ '^sha256:[0-9a-f]{64}$'),
    CONSTRAINT agent_admission_idempotency_subject_check CHECK (subject_digest IS NULL OR subject_digest ~ '^sha256:[0-9a-f]{64}$')
);

CREATE TABLE IF NOT EXISTS business.agent_admission_outbox (
    outbox_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    admission_id UUID NOT NULL,
    transition_id UUID NOT NULL,
    event_type VARCHAR(128) NOT NULL,
    scope_hash VARCHAR(71) NOT NULL,
    payload JSONB NOT NULL,
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    published_at TIMESTAMPTZ,
    publish_attempts INTEGER NOT NULL DEFAULT 0,
    CONSTRAINT agent_admission_outbox_parent_fk FOREIGN KEY (tenant_id, admission_id) REFERENCES business.agent_admissions (tenant_id, admission_id),
    CONSTRAINT agent_admission_outbox_transition_fk FOREIGN KEY (tenant_id, transition_id) REFERENCES business.agent_admission_transitions (tenant_id, transition_id),
    CONSTRAINT uq_agent_admission_outbox UNIQUE (tenant_id, transition_id, scope_hash),
    CONSTRAINT agent_admission_outbox_scope_check CHECK (scope_hash ~ '^sha256:[0-9a-f]{64}$'),
    CONSTRAINT agent_admission_outbox_attempts_check CHECK (publish_attempts >= 0)
);

CREATE INDEX IF NOT EXISTS ix_agent_admissions_offerable ON business.agent_admissions (tenant_id, state, professional_type_id, professional_version);
CREATE INDEX IF NOT EXISTS ix_agent_admission_assertions_current ON business.agent_admission_assertions (tenant_id, admission_id, environment, assertion_type, observed_at DESC);
CREATE INDEX IF NOT EXISTS ix_agent_admission_outbox_pending ON business.agent_admission_outbox (tenant_id, occurred_at) WHERE published_at IS NULL;

CREATE OR REPLACE FUNCTION business.get_offerable_professional_versions(p_environment TEXT)
RETURNS TABLE (projection JSONB)
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = pg_catalog, business
AS $$
    SELECT jsonb_build_object(
        'professionalTypeId', admission.professional_type_id,
        'professionalVersion', admission.professional_version,
        'admissionContentDigest', admission.admission_content_digest,
        'displayName', replace(admission.professional_type_id, '_', ' '),
        'supportedChannels', revision.admission_content #> '{professionalIdentity,supportedChannels}',
        'skills', (
            SELECT jsonb_agg(jsonb_build_object(
                'skillId', skill ->> 'skillId',
                'skillVersion', skill ->> 'skillVersion',
                'capability', skill ->> 'capability',
                'businessKpi', skill ->> 'businessKpi'))
            FROM jsonb_array_elements(revision.admission_content -> 'skillManifest') AS skill
        ))
    FROM business.agent_admissions AS admission
    JOIN business.agent_admission_revisions AS revision
      ON revision.tenant_id = admission.tenant_id
     AND revision.admission_id = admission.admission_id
     AND revision.revision = admission.current_revision
    WHERE admission.state = 'ACTIVE'
      AND p_environment IN ('demo', 'uat', 'prod')
      AND 6 = (
          SELECT count(*)
          FROM unnest(ARRAY['RUNTIME','ENVIRONMENT','PROVIDER','BILLING','ARTIFACT','CONSTITUTIONAL']) AS required(assertion_type)
          WHERE (
              SELECT assertion.status = 'PASS'
                 AND assertion.valid_until > now()
                 AND assertion.policy_version = admission.policy_version
                 AND assertion.subject_digest = CASE
                     WHEN required.assertion_type = 'ARTIFACT' THEN admission.artifact_digest
                     ELSE admission.admission_content_digest
                 END
              FROM business.agent_admission_assertions AS assertion
              WHERE assertion.tenant_id = admission.tenant_id
                AND assertion.admission_id = admission.admission_id
                AND assertion.environment = p_environment
                AND assertion.assertion_type = required.assertion_type
              ORDER BY assertion.observed_at DESC
              LIMIT 1
          ) IS TRUE
      );
$$;

REVOKE ALL ON FUNCTION business.get_offerable_professional_versions(TEXT) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION business.get_offerable_professional_versions(TEXT) TO business_app;

DO $$
DECLARE table_name TEXT;
BEGIN
    FOREACH table_name IN ARRAY ARRAY[
        'agent_admissions', 'agent_admission_revisions', 'agent_admission_validations',
        'agent_admission_findings', 'agent_admission_assertions', 'agent_admission_transitions',
        'agent_admission_idempotency', 'agent_admission_outbox'
    ] LOOP
        EXECUTE format('ALTER TABLE business.%I ENABLE ROW LEVEL SECURITY', table_name);
        EXECUTE format('ALTER TABLE business.%I FORCE ROW LEVEL SECURITY', table_name);
        EXECUTE format(
            'CREATE POLICY %I ON business.%I USING (tenant_id = nullif(current_setting(''app.current_tenant_id'', TRUE), '''')::UUID) WITH CHECK (tenant_id = nullif(current_setting(''app.current_tenant_id'', TRUE), '''')::UUID)',
            table_name || '_tenant_isolation', table_name);
    END LOOP;
END;
$$;

CREATE OR REPLACE FUNCTION business.reject_agent_admission_lineage_mutation()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'agent admission lineage is append-only';
END;
$$;

DO $$
DECLARE table_name TEXT;
BEGIN
    FOREACH table_name IN ARRAY ARRAY[
        'agent_admission_revisions', 'agent_admission_validations', 'agent_admission_findings',
        'agent_admission_assertions', 'agent_admission_transitions'
    ] LOOP
        EXECUTE format('CREATE TRIGGER %I BEFORE UPDATE OR DELETE ON business.%I FOR EACH ROW EXECUTE FUNCTION business.reject_agent_admission_lineage_mutation()', table_name || '_append_only', table_name);
    END LOOP;
END;
$$;

GRANT SELECT, INSERT, UPDATE ON business.agent_admissions TO business_app;
GRANT SELECT, INSERT ON business.agent_admission_revisions, business.agent_admission_validations,
    business.agent_admission_findings, business.agent_admission_assertions, business.agent_admission_transitions TO business_app;
GRANT SELECT, INSERT, UPDATE ON business.agent_admission_idempotency, business.agent_admission_outbox TO business_app;