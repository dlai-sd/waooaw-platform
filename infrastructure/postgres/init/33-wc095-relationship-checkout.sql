-- Implements: architecture/reference/api-specs/business-platform.openapi.yaml §RelationshipCheckoutOutcome
-- Constitutional basis: C-005, C-007, C-023, C-059, C-063, C-088

CREATE TABLE IF NOT EXISTS business.relationship_checkout_intents (
    checkout_intent_id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    relationship_id UUID NOT NULL,
    contract_id UUID NOT NULL,
    contract_version INTEGER NOT NULL,
    contract_hash CHAR(64) NOT NULL,
    contract_acceptance_id UUID NOT NULL,
    payment_consent_evidence_id UUID,
    idempotency_key UUID NOT NULL,
    material_request_hash CHAR(64) NOT NULL,
    status VARCHAR(24) NOT NULL DEFAULT 'PENDING',
    outcome_kind VARCHAR(48),
    outcome_json JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    CONSTRAINT relationship_checkout_intents_relationship_fk
    FOREIGN KEY (tenant_id, relationship_id)
    REFERENCES business.employment_relationships (tenant_id, relationship_id),
    CONSTRAINT relationship_checkout_intents_contract_fk
    FOREIGN KEY (tenant_id, relationship_id, contract_id, contract_version, contract_hash)
    REFERENCES business.employment_contract_versions
    (tenant_id, relationship_id, contract_id, version, contract_hash),
    CONSTRAINT relationship_checkout_intents_idempotency_unique
    UNIQUE (tenant_id, idempotency_key),
    CONSTRAINT relationship_checkout_intents_hash_check CHECK (
        material_request_hash ~ '^[0-9a-f]{64}$'
    ),
    CONSTRAINT relationship_checkout_intents_status_check CHECK (
        status IN ('PENDING', 'AWAITING_PROVIDER', 'COMPLETED', 'UNRESOLVED')
    ),
    CONSTRAINT relationship_checkout_intents_outcome_check CHECK (
        (status = 'PENDING' AND outcome_kind IS NULL AND outcome_json IS NULL AND completed_at IS NULL)
        OR (
            status = 'AWAITING_PROVIDER' AND outcome_kind = 'RAZORPAY_CHECKOUT_REQUIRED'
            AND outcome_json IS NOT NULL AND completed_at IS NULL AND payment_consent_evidence_id IS NOT NULL
        )
        OR (
            status IN ('COMPLETED', 'UNRESOLVED') AND outcome_kind IS NOT NULL
            AND outcome_json IS NOT NULL AND completed_at IS NOT NULL
        )
    )
);

CREATE INDEX IF NOT EXISTS idx_relationship_checkout_intents_relationship
ON business.relationship_checkout_intents (tenant_id, relationship_id, created_at DESC);

CREATE OR REPLACE FUNCTION business.guard_relationship_checkout_intent_update()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF NEW.checkout_intent_id IS DISTINCT FROM OLD.checkout_intent_id
       OR NEW.tenant_id IS DISTINCT FROM OLD.tenant_id
       OR NEW.relationship_id IS DISTINCT FROM OLD.relationship_id
       OR NEW.contract_id IS DISTINCT FROM OLD.contract_id
       OR NEW.contract_version IS DISTINCT FROM OLD.contract_version
       OR NEW.contract_hash IS DISTINCT FROM OLD.contract_hash
       OR NEW.contract_acceptance_id IS DISTINCT FROM OLD.contract_acceptance_id
       OR (OLD.payment_consent_evidence_id IS NOT NULL
           AND NEW.payment_consent_evidence_id IS DISTINCT FROM OLD.payment_consent_evidence_id)
       OR NEW.idempotency_key IS DISTINCT FROM OLD.idempotency_key
       OR NEW.material_request_hash IS DISTINCT FROM OLD.material_request_hash
       OR NEW.created_at IS DISTINCT FROM OLD.created_at THEN
        RAISE EXCEPTION 'relationship checkout intent identity is immutable';
    END IF;
    IF OLD.status NOT IN ('PENDING', 'AWAITING_PROVIDER') THEN
        RAISE EXCEPTION 'terminal relationship checkout intent is immutable';
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS relationship_checkout_intents_guard_update
ON business.relationship_checkout_intents;
CREATE TRIGGER relationship_checkout_intents_guard_update
BEFORE UPDATE ON business.relationship_checkout_intents
FOR EACH ROW EXECUTE FUNCTION business.guard_relationship_checkout_intent_update();

DROP TRIGGER IF EXISTS relationship_checkout_intents_no_delete
ON business.relationship_checkout_intents;
CREATE TRIGGER relationship_checkout_intents_no_delete
BEFORE DELETE ON business.relationship_checkout_intents
FOR EACH ROW EXECUTE FUNCTION business.reject_relationship_history_mutation();

ALTER TABLE business.relationship_checkout_intents ENABLE ROW LEVEL SECURITY;
ALTER TABLE business.relationship_checkout_intents FORCE ROW LEVEL SECURITY;

CREATE POLICY relationship_checkout_intents_tenant_isolation
ON business.relationship_checkout_intents
USING (tenant_id = NULLIF(CURRENT_SETTING('app.current_tenant_id', TRUE), '')::UUID)
WITH CHECK (tenant_id = NULLIF(CURRENT_SETTING('app.current_tenant_id', TRUE), '')::UUID);

GRANT SELECT, INSERT, UPDATE ON business.relationship_checkout_intents TO business_app;
