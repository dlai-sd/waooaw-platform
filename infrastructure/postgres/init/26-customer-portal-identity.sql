-- Implements: WC-084 Customer Portal Solution Contract section 4.1
-- constitutional_basis: C-005, C-007, C-023, C-026, C-059, C-063

CREATE TABLE IF NOT EXISTS identity.customer_portal_preferences (
    preference_id                  UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    actor_subject                  VARCHAR(256) NOT NULL,
    tenant_id                      UUID         NOT NULL,
    display_name                   VARCHAR(200),
    organization_display_name      VARCHAR(200),
    locale                         VARCHAR(16)  NOT NULL DEFAULT 'en',
    theme                          VARCHAR(16)  NOT NULL DEFAULT 'SYSTEM' CHECK (theme IN ('SYSTEM', 'LIGHT', 'DARK')),
    timestamp_visibility           VARCHAR(16)  NOT NULL DEFAULT 'RELATIVE' CHECK (timestamp_visibility IN ('RELATIVE', 'ABSOLUTE')),
    approval_request_channels      JSONB        NOT NULL DEFAULT '["IN_APP"]'::jsonb,
    maturity_report_channels       JSONB        NOT NULL DEFAULT '["IN_APP"]'::jsonb,
    monthly_narrative_channels     JSONB        NOT NULL DEFAULT '["IN_APP"]'::jsonb,
    self_governance_alert_channels JSONB        NOT NULL DEFAULT '["IN_APP"]'::jsonb,
    updated_at                     TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT customer_portal_preferences_actor_tenant_unique UNIQUE (actor_subject, tenant_id)
);

ALTER TABLE identity.customer_portal_preferences ENABLE ROW LEVEL SECURITY;
ALTER TABLE identity.customer_portal_preferences FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS customer_portal_preferences_tenant_isolation ON identity.customer_portal_preferences;
CREATE POLICY customer_portal_preferences_tenant_isolation ON identity.customer_portal_preferences
    USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', TRUE), '')::UUID)
    WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', TRUE), '')::UUID);