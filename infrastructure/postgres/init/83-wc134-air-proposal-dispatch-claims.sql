-- WC-134: reserve an interpretation identity before invoking an interpreter.
CREATE TABLE IF NOT EXISTS ai_runtime.employment_patch_dispatch_claims (
    tenant_id UUID NOT NULL,
    relationship_ref TEXT NOT NULL,
    idempotency_key UUID NOT NULL,
    request_digest CHAR(64) NOT NULL CHECK (request_digest ~ '^[0-9a-f]{64}$'),
    claimed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, relationship_ref, idempotency_key)
);

ALTER TABLE ai_runtime.employment_patch_dispatch_claims ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_runtime.employment_patch_dispatch_claims FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS air_employment_dispatch_tenant_isolation
    ON ai_runtime.employment_patch_dispatch_claims;
CREATE POLICY air_employment_dispatch_tenant_isolation
    ON ai_runtime.employment_patch_dispatch_claims
    USING (tenant_id = nullif(current_setting('app.current_tenant_id', true), '')::uuid)
    WITH CHECK (tenant_id = nullif(current_setting('app.current_tenant_id', true), '')::uuid);
GRANT SELECT, INSERT ON ai_runtime.employment_patch_dispatch_claims TO ai_runtime_app;
