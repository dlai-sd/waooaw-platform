-- Implements: WC-065 WC065-06
-- constitutional_basis: C-005, C-007, C-023, C-026, C-059

CREATE TABLE IF NOT EXISTS business.offerability_decisions (
    decision_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    relationship_id UUID NOT NULL,
    relationship_state_version INTEGER NOT NULL,
    policy_version VARCHAR(64) NOT NULL,
    disposition VARCHAR(16) NOT NULL,
    direct_contribution_amount NUMERIC(18,4) NOT NULL,
    owner_versions_json JSONB NOT NULL,
    reasons_json JSONB NOT NULL,
    evidence_id UUID NOT NULL,
    produced_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at TIMESTAMPTZ NOT NULL,
    CONSTRAINT offerability_relationship_fk FOREIGN KEY (tenant_id, relationship_id)
        REFERENCES business.employment_relationships (tenant_id, relationship_id),
    CONSTRAINT offerability_disposition_check CHECK (disposition IN ('ALLOW', 'REVISE', 'ESCALATE', 'BLOCK')),
    CONSTRAINT offerability_expiry_check CHECK (expires_at > produced_at)
);

CREATE INDEX IF NOT EXISTS ix_offerability_current
ON business.offerability_decisions (tenant_id, relationship_id, produced_at DESC);

ALTER TABLE business.offerability_decisions ENABLE ROW LEVEL SECURITY;
ALTER TABLE business.offerability_decisions FORCE ROW LEVEL SECURITY;

CREATE POLICY offerability_tenant_isolation ON business.offerability_decisions
USING (tenant_id = nullif(current_setting('app.current_tenant_id', TRUE), '')::UUID)
WITH CHECK (tenant_id = nullif(current_setting('app.current_tenant_id', TRUE), '')::UUID);

CREATE OR REPLACE FUNCTION business.reject_offerability_mutation()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'offerability decisions are append-only';
END;
$$;

CREATE TRIGGER offerability_append_only
BEFORE UPDATE OR DELETE ON business.offerability_decisions
FOR EACH ROW EXECUTE FUNCTION business.reject_offerability_mutation();

GRANT SELECT, INSERT ON business.offerability_decisions TO business_app;