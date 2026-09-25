-- Local Codespaces preview fixture only. Never loaded by production workloads.
CREATE OR REPLACE FUNCTION business.seed_auth_preview_agent_admission()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, business, identity
AS $$
BEGIN
    IF NEW.status = 'ACTIVE' THEN
        INSERT INTO business.agent_admissions (
            tenant_id,
            professional_type_id,
            professional_version,
            owner_subject_id,
            state,
            admission_content_digest,
            evidence_set_digest,
            artifact_digest,
            policy_version
        ) VALUES (
            NEW.tenant_id,
            'DIGITAL_MARKETING_LOCAL_SERVICE',
            '1.0.0',
            NEW.account_id,
            'ACTIVE',
            'sha256:' || repeat('a', 64),
            'sha256:' || repeat('b', 64),
            'sha256:' || repeat('c', 64),
            'auth-preview-v1'
        )
        ON CONFLICT (tenant_id, professional_type_id, professional_version) DO NOTHING;
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS seed_auth_preview_agent_admission ON identity.memberships;
CREATE TRIGGER seed_auth_preview_agent_admission
AFTER INSERT OR UPDATE OF status ON identity.memberships
FOR EACH ROW
EXECUTE FUNCTION business.seed_auth_preview_agent_admission();

INSERT INTO business.agent_admissions (
    tenant_id,
    professional_type_id,
    professional_version,
    owner_subject_id,
    state,
    admission_content_digest,
    evidence_set_digest,
    artifact_digest,
    policy_version
)
SELECT
    membership.tenant_id,
    'DIGITAL_MARKETING_LOCAL_SERVICE',
    '1.0.0',
    membership.account_id,
    'ACTIVE',
    'sha256:' || repeat('a', 64),
    'sha256:' || repeat('b', 64),
    'sha256:' || repeat('c', 64),
    'auth-preview-v1'
FROM identity.memberships AS membership
WHERE membership.status = 'ACTIVE'
ON CONFLICT (tenant_id, professional_type_id, professional_version) DO NOTHING;