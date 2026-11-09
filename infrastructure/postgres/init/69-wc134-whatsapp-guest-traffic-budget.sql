-- Implements: work-contracts/WC-134-whatsapp-demo-complete-rollout-work-component.md WC134-R008
-- Constitutional basis: C-023, C-026, C-059, C-063

BEGIN;

CREATE TABLE IF NOT EXISTS business.whatsapp_guest_traffic_events (
    tenant_id UUID NOT NULL,
    activation_digest VARCHAR(64) NOT NULL CHECK (activation_digest ~ '^[a-f0-9]{64}$'),
    authority_digest VARCHAR(64) NOT NULL CHECK (authority_digest ~ '^[a-f0-9]{64}$'),
    event_id VARCHAR(64) NOT NULL CHECK (event_id ~ '^[a-f0-9]{64}$'),
    binding_digest CHAR(64) NOT NULL CHECK (binding_digest ~ '^[a-f0-9]{64}$'),
    event_type VARCHAR(16) NOT NULL CHECK (event_type IN ('INBOUND', 'OUTBOUND', 'SESSION')),
    reserved_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (tenant_id, activation_digest, event_id)
);

CREATE INDEX IF NOT EXISTS idx_whatsapp_guest_traffic_binding_window
    ON business.whatsapp_guest_traffic_events
        (tenant_id, activation_digest, binding_digest, reserved_at);
CREATE INDEX IF NOT EXISTS idx_whatsapp_guest_traffic_session_day
    ON business.whatsapp_guest_traffic_events
        (tenant_id, activation_digest, reserved_at)
    WHERE event_type = 'SESSION';

ALTER TABLE business.whatsapp_guest_traffic_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE business.whatsapp_guest_traffic_events FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS whatsapp_guest_traffic_events_tenant_isolation
    ON business.whatsapp_guest_traffic_events;
CREATE POLICY whatsapp_guest_traffic_events_tenant_isolation
    ON business.whatsapp_guest_traffic_events
    USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', TRUE), '')::UUID)
    WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', TRUE), '')::UUID);

REVOKE ALL ON business.whatsapp_guest_traffic_events FROM PUBLIC;
GRANT SELECT, INSERT ON business.whatsapp_guest_traffic_events TO business_app, bp_runtime;
REVOKE UPDATE, DELETE, TRUNCATE
    ON business.whatsapp_guest_traffic_events FROM business_app, bp_runtime;

COMMIT;
