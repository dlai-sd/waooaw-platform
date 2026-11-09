-- Implements: work-contracts/WC-134-whatsapp-demo-complete-rollout-work-component.md WC134-R003
-- Constitutional basis: C-023, C-026, C-039, C-059, C-063

BEGIN;

CREATE TABLE IF NOT EXISTS business.whatsapp_guest_consent_history (
    tenant_id UUID NOT NULL,
    binding_digest CHAR(64) NOT NULL,
    evidence_id UUID NOT NULL,
    notice_version VARCHAR(32) NOT NULL,
    notice_message_id UUID NOT NULL,
    notice_queued_at TIMESTAMPTZ NOT NULL,
    consent_message_id VARCHAR(128) NOT NULL,
    consent_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (tenant_id, binding_digest, evidence_id),
    FOREIGN KEY (tenant_id, binding_digest)
        REFERENCES business.whatsapp_guest_sessions (tenant_id, binding_digest)
);

ALTER TABLE business.whatsapp_guest_consent_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE business.whatsapp_guest_consent_history FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS whatsapp_guest_consent_history_tenant_isolation
    ON business.whatsapp_guest_consent_history;
CREATE POLICY whatsapp_guest_consent_history_tenant_isolation
    ON business.whatsapp_guest_consent_history
    USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
    WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);
REVOKE UPDATE, DELETE ON business.whatsapp_guest_consent_history FROM business_app;
GRANT SELECT, INSERT ON business.whatsapp_guest_consent_history TO business_app;

COMMIT;
