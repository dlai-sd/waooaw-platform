-- Implements: WC-084 Customer Portal Solution Contract section 4.3
-- constitutional_basis: C-005, C-007, C-023, C-026, C-059, C-063

CREATE TABLE IF NOT EXISTS business.relationship_onboard_preferences (
    preference_id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id                   UUID        NOT NULL,
    relationship_id             UUID        NOT NULL,
    preferred_agent_display_name VARCHAR(80),
    chat_appearance             VARCHAR(24) CHECK (chat_appearance IN ('CONSTITUTIONAL', 'COMPACT')),
    timestamp_visibility        VARCHAR(16) CHECK (timestamp_visibility IN ('RELATIVE', 'ABSOLUTE')),
    theme_preference            VARCHAR(16) CHECK (theme_preference IN ('SYSTEM', 'LIGHT', 'DARK')),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT relationship_onboard_preferences_relationship_fk
        FOREIGN KEY (tenant_id, relationship_id)
        REFERENCES business.employment_relationships (tenant_id, relationship_id),
    CONSTRAINT relationship_onboard_preferences_tenant_relationship_unique
        UNIQUE (tenant_id, relationship_id)
);

ALTER TABLE business.relationship_onboard_preferences ENABLE ROW LEVEL SECURITY;
ALTER TABLE business.relationship_onboard_preferences FORCE ROW LEVEL SECURITY;
CREATE POLICY relationship_onboard_preferences_tenant_isolation
    ON business.relationship_onboard_preferences
    USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', TRUE), '')::UUID)
    WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', TRUE), '')::UUID);

GRANT SELECT, INSERT, UPDATE ON business.relationship_onboard_preferences TO business_app;