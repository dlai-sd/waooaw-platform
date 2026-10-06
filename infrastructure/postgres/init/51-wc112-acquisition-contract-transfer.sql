-- Implements: WC-112 R025, R031
-- Constitutional basis: C-023, C-049, C-059

ALTER TABLE business.employment_relationships
    ADD COLUMN IF NOT EXISTS acquisition_intent_id UUID,
    ADD COLUMN IF NOT EXISTS acquisition_contract_version VARCHAR(32),
    ADD COLUMN IF NOT EXISTS acquisition_contract_hash CHAR(64),
    ADD COLUMN IF NOT EXISTS acquisition_contract_accepted_at TIMESTAMPTZ;

CREATE UNIQUE INDEX IF NOT EXISTS uq_employment_relationship_acquisition_intent
    ON business.employment_relationships (tenant_id, acquisition_intent_id)
    WHERE acquisition_intent_id IS NOT NULL;

ALTER TABLE business.employment_relationships
    DROP CONSTRAINT IF EXISTS employment_relationship_acquisition_contract_complete;

ALTER TABLE business.employment_relationships
    ADD CONSTRAINT employment_relationship_acquisition_contract_complete CHECK (
        (acquisition_intent_id IS NULL
            AND acquisition_contract_version IS NULL
            AND acquisition_contract_hash IS NULL
            AND acquisition_contract_accepted_at IS NULL)
        OR
        (acquisition_intent_id IS NOT NULL
            AND acquisition_contract_version IS NOT NULL
            AND acquisition_contract_hash ~ '^[0-9a-f]{64}$'
            AND acquisition_contract_accepted_at IS NOT NULL)
    );
