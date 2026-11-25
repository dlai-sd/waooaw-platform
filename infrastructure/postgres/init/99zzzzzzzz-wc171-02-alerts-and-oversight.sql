-- Implements: work-contracts/WC-171-agent-navigation-alerts-and-oversight.md WC171-R005, WC171-R007, WC171-R008, WC171-R009
-- Constitutional basis: C-001, C-005, C-007, C-023, C-059, C-063
-- WC-171: one alert policy (class, category, dedup key, WhatsApp decision), per-category mutes, snooze, alert delivery
-- outcomes, and an append-only record of an operator's decision about a blocked outbound message. Nothing is deleted:
-- a closed blocked message keeps its outbox row and leaves the page because a resolution exists for it.
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '30s';
SET LOCAL ROLE bp_owner;

ALTER TABLE business.customer_alerts
    ADD COLUMN IF NOT EXISTS category VARCHAR(40) NOT NULL DEFAULT 'GENERAL',
    ADD COLUMN IF NOT EXISTS alert_class VARCHAR(24) NOT NULL DEFAULT 'INFORMATION',
    ADD COLUMN IF NOT EXISTS snoozed_until TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS dedup_key VARCHAR(200),
    ADD COLUMN IF NOT EXISTS whatsapp_decision VARCHAR(48);
ALTER TABLE business.customer_alerts DROP CONSTRAINT IF EXISTS customer_alerts_alert_class_check;
ALTER TABLE business.customer_alerts ADD CONSTRAINT customer_alerts_alert_class_check
    CHECK (alert_class IN ('FLOOR', 'ACTION_REQUIRED', 'AT_RISK', 'INFORMATION', 'OPERATIONS'));
ALTER TABLE business.customer_alerts DROP CONSTRAINT IF EXISTS customer_alerts_source_check;
ALTER TABLE business.customer_alerts ADD CONSTRAINT customer_alerts_source_check
    CHECK (source IN (
        'RELATIONSHIP_ATTENTION', 'BILLING', 'RESULT', 'PROFILE', 'MARKETPLACE', 'SYSTEM',
        'AGENT_DECLARED', 'BILLING_THRESHOLD', 'SPEND_DISCREPANCY', 'EMERGENCY_STOP', 'OPERATIONS'
    ));
CREATE UNIQUE INDEX IF NOT EXISTS customer_alerts_dedup_idx
    ON business.customer_alerts (tenant_id, dedup_key) WHERE dedup_key IS NOT NULL;
CREATE INDEX IF NOT EXISTS customer_alerts_relationship_idx
    ON business.customer_alerts (tenant_id, relationship_id, occurred_at DESC);

CREATE TABLE IF NOT EXISTS business.alert_category_mutes (
    tenant_id UUID NOT NULL,
    category VARCHAR(40) NOT NULL,
    muted BOOLEAN NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    updated_by VARCHAR(256) NOT NULL,
    PRIMARY KEY (tenant_id, category),
    CHECK (category ~ '^[A-Z][A-Z0-9_]{2,39}$'),
    CHECK (category NOT IN ('EMERGENCY_STOP', 'AUTHORITY', 'SAFETY') OR muted = FALSE)
);
ALTER TABLE business.alert_category_mutes ENABLE ROW LEVEL SECURITY;
ALTER TABLE business.alert_category_mutes FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS alert_category_mutes_tenant_isolation ON business.alert_category_mutes;
CREATE POLICY alert_category_mutes_tenant_isolation ON business.alert_category_mutes
    USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', TRUE), '')::UUID)
    WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', TRUE), '')::UUID);
GRANT SELECT, INSERT, UPDATE ON business.alert_category_mutes TO business_app;

CREATE TABLE IF NOT EXISTS business.alert_deliveries (
    delivery_id UUID PRIMARY KEY,
    tenant_id UUID,
    alert_id UUID,
    signal VARCHAR(160) NOT NULL,
    alert_class VARCHAR(24) NOT NULL,
    channel VARCHAR(24) NOT NULL,
    outcome VARCHAR(24) NOT NULL,
    reason VARCHAR(120),
    recorded_at TIMESTAMPTZ NOT NULL,
    CHECK (channel IN ('portal', 'whatsapp_text', 'operator_page')),
    CHECK (outcome IN ('EMITTED', 'DELIVERED', 'FAILED', 'ACKNOWLEDGED', 'SUPPRESSED'))
);
CREATE INDEX IF NOT EXISTS alert_deliveries_recorded_idx ON business.alert_deliveries (recorded_at DESC);
GRANT SELECT, INSERT, UPDATE ON business.alert_deliveries TO business_app;

CREATE TABLE IF NOT EXISTS business.conversation_outbox_resolutions (
    resolution_id UUID PRIMARY KEY,
    outbox_id UUID NOT NULL REFERENCES business.conversation_outbox (outbox_id),
    tenant_id UUID NOT NULL,
    environment VARCHAR(32) NOT NULL,
    action VARCHAR(24) NOT NULL,
    reason VARCHAR(240) NOT NULL,
    resolved_by VARCHAR(128) NOT NULL,
    idempotency_key UUID NOT NULL,
    resolved_at TIMESTAMPTZ NOT NULL,
    CONSTRAINT conversation_outbox_resolutions_action_check
        CHECK (action IN ('RETRY', 'CLOSE_WITH_REASON', 'MARK_UNDELIVERABLE')),
    CONSTRAINT conversation_outbox_resolutions_idempotency_unique UNIQUE (idempotency_key)
);
CREATE INDEX IF NOT EXISTS conversation_outbox_resolutions_outbox_idx
    ON business.conversation_outbox_resolutions (outbox_id, resolved_at DESC);
ALTER TABLE business.conversation_outbox_resolutions ENABLE ROW LEVEL SECURITY;
ALTER TABLE business.conversation_outbox_resolutions FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS conversation_outbox_resolutions_tenant_isolation ON business.conversation_outbox_resolutions;
CREATE POLICY conversation_outbox_resolutions_tenant_isolation ON business.conversation_outbox_resolutions
    USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', TRUE), '')::UUID)
    WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', TRUE), '')::UUID);
GRANT SELECT, INSERT ON business.conversation_outbox_resolutions TO business_app;
REVOKE UPDATE, DELETE ON business.conversation_outbox_resolutions FROM business_app;

COMMIT;
