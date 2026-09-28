-- Implements: WC-107 R015-R016 authoritative My Agents confirmation handoff
-- constitutional_basis: C-002, C-023, C-059, C-063

CREATE TABLE IF NOT EXISTS business.my_agents_selection_flash (
    selection_id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    handle_hash            VARCHAR(64) NOT NULL UNIQUE,
    tenant_id              UUID        NOT NULL,
    actor_participant_id   UUID        NOT NULL,
    relationship_id        UUID        NOT NULL,
    outcome_kind           VARCHAR(20) NOT NULL
        CHECK (outcome_kind IN ('TRIAL_STARTED', 'HIRE_PAID', 'HIRE_ZERO_PRICE')),
    created_at             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at             TIMESTAMPTZ NOT NULL,
    consumed_at            TIMESTAMPTZ,
    CONSTRAINT my_agents_selection_flash_expiry
        CHECK (expires_at = created_at + INTERVAL '5 minutes'),
    CONSTRAINT my_agents_selection_flash_relationship_fk
        FOREIGN KEY (tenant_id, relationship_id)
        REFERENCES business.employment_relationships(tenant_id, relationship_id)
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_my_agents_selection_flash_active
    ON business.my_agents_selection_flash (tenant_id, actor_participant_id, expires_at)
    WHERE consumed_at IS NULL;

GRANT SELECT, INSERT, UPDATE ON business.my_agents_selection_flash TO business_app;