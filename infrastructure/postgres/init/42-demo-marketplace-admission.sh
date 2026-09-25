#!/usr/bin/env bash
# Implements: work-contracts/WC-103-multitenant-authentication-assessment.md Target Authentication Journeys
# Constitutional basis: C-023 (Evidence First), C-059 (Implementation Traceability)

set -euo pipefail

admission_content_digest="${DMA_ADMISSION_CONTENT_DIGEST:-sha256:$(printf 'codespaces-preview-admission' | sha256sum | cut -d ' ' -f 1)}"
artifact_digest="${DMA_ARTIFACT_DIGEST:-sha256:$(printf 'codespaces-preview-artifact' | sha256sum | cut -d ' ' -f 1)}"
evidence_set_digest="sha256:$(printf '%s\n%s\n%s' "$admission_content_digest" "$artifact_digest" 'demo-marketplace-admission-v1' | sha256sum | cut -d ' ' -f 1)"
: "${POSTGRES_USER:?POSTGRES_USER is required}"
: "${POSTGRES_DB:?POSTGRES_DB is required}"

for digest in "$admission_content_digest" "$artifact_digest" "$evidence_set_digest"; do
  if [[ ! "$digest" =~ ^sha256:[0-9a-f]{64}$ ]]; then
    echo "DMA admission digest is invalid" >&2
    exit 1
  fi
done

psql --host "${PGHOST:-/var/run/postgresql}" --port "${PGPORT:-5432}" \
  --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" --set ON_ERROR_STOP=1 <<SQL
CREATE OR REPLACE FUNCTION business.seed_demo_dma_admission()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, business, identity
AS \$function\$
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
            '$admission_content_digest',
            '$evidence_set_digest',
            '$artifact_digest',
            'demo-marketplace-admission-v1'
        )
        ON CONFLICT (tenant_id, professional_type_id, professional_version) DO NOTHING;
    END IF;
    RETURN NEW;
END;
\$function\$;

DROP TRIGGER IF EXISTS seed_demo_dma_admission ON identity.memberships;
CREATE TRIGGER seed_demo_dma_admission
AFTER INSERT OR UPDATE OF status ON identity.memberships
FOR EACH ROW
EXECUTE FUNCTION business.seed_demo_dma_admission();

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
    '$admission_content_digest',
    '$evidence_set_digest',
    '$artifact_digest',
    'demo-marketplace-admission-v1'
FROM identity.memberships AS membership
WHERE membership.status = 'ACTIVE'
ON CONFLICT (tenant_id, professional_type_id, professional_version) DO NOTHING;
SQL