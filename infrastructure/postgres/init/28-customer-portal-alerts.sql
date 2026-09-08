-- Implements: WC-084 Customer Portal Solution Contract section 4.5
-- constitutional_basis: C-005, C-007, C-023, C-026, C-059, C-063

CREATE TABLE IF NOT EXISTS business.customer_alerts (
    alert_id UUID PRIMARY KEY DEFAULT gen_random_uuid(), tenant_id UUID NOT NULL,
    version INTEGER NOT NULL DEFAULT 1, alert_type VARCHAR(24) NOT NULL,
    severity VARCHAR(16) NOT NULL, source VARCHAR(32) NOT NULL,
    relationship_id UUID, occurred_at TIMESTAMPTZ NOT NULL,
    due_meaning VARCHAR(240), read_state VARCHAR(16) NOT NULL DEFAULT 'UNREAD',
    destination_surface VARCHAR(32) NOT NULL, destination_subject_id VARCHAR(120),
    available_action VARCHAR(16) NOT NULL DEFAULT 'NONE',
    CHECK (alert_type IN ('ACTIONABLE', 'INFORMATIONAL')),
    CHECK (severity IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
    CHECK (source IN ('RELATIONSHIP_ATTENTION', 'BILLING', 'RESULT', 'PROFILE', 'MARKETPLACE', 'SYSTEM')),
    CHECK (read_state IN ('UNREAD', 'READ', 'ACKNOWLEDGED')),
    CHECK (available_action IN ('OPEN', 'ACKNOWLEDGE', 'NONE'))
);
CREATE INDEX IF NOT EXISTS customer_alerts_tenant_order_idx
    ON business.customer_alerts (tenant_id, occurred_at DESC, alert_id);

CREATE TABLE IF NOT EXISTS business.customer_alert_idempotency (
    entry_id UUID PRIMARY KEY DEFAULT gen_random_uuid(), tenant_id UUID NOT NULL,
    alert_id UUID NOT NULL REFERENCES business.customer_alerts (alert_id),
    actor_subject VARCHAR(256) NOT NULL, idempotency_key UUID NOT NULL,
    operation VARCHAR(32) NOT NULL, request_hash VARCHAR(64) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (tenant_id, actor_subject, idempotency_key, operation)
);

ALTER TABLE business.customer_alerts ENABLE ROW LEVEL SECURITY;
ALTER TABLE business.customer_alerts FORCE ROW LEVEL SECURITY;
CREATE POLICY customer_alerts_tenant_isolation ON business.customer_alerts
    USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', TRUE), '')::UUID)
    WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', TRUE), '')::UUID);
ALTER TABLE business.customer_alert_idempotency ENABLE ROW LEVEL SECURITY;
ALTER TABLE business.customer_alert_idempotency FORCE ROW LEVEL SECURITY;
CREATE POLICY customer_alert_idempotency_tenant_isolation ON business.customer_alert_idempotency
    USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', TRUE), '')::UUID)
    WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', TRUE), '')::UUID);

GRANT SELECT, INSERT, UPDATE ON business.customer_alerts TO business_app;
GRANT SELECT, INSERT ON business.customer_alert_idempotency TO business_app;