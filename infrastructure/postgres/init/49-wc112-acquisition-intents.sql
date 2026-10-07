-- Implements: WC-112 R020-R031
-- Constitutional basis: C-023, C-049, C-059, C-063

CREATE TABLE IF NOT EXISTS business.acquisition_intents (
    acquisition_intent_id UUID PRIMARY KEY,
    actor_identity_hash CHAR(64) NOT NULL,
    idempotency_key UUID NOT NULL,
    tenant_id UUID,
    participant_id UUID,
    professional_type VARCHAR(64) NOT NULL,
    professional_version VARCHAR(32) NOT NULL,
    mode VARCHAR(8) NOT NULL CHECK (mode IN ('TRIAL', 'HIRE')),
    disclosure_revision VARCHAR(32) NOT NULL,
    contract_version VARCHAR(32) NOT NULL,
    contract_document_uri VARCHAR(500) NOT NULL,
    contract_hash CHAR(64) NOT NULL,
    material_request_hash CHAR(64) NOT NULL,
    coupon_code VARCHAR(64),
    planned_relationship_id UUID,
    planned_agent_instance_id UUID,
    status VARCHAR(32) NOT NULL CHECK (
        status IN ('PENDING_REGISTRATION', 'READY_TO_COMPLETE', 'COMPLETING', 'COMPLETED', 'EXPIRED', 'UNRESOLVED')
    ),
    contract_accepted_at TIMESTAMPTZ NOT NULL,
    relationship_id UUID,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    CONSTRAINT acquisition_intents_actor_idempotency_unique
        UNIQUE (actor_identity_hash, idempotency_key),
    CONSTRAINT acquisition_intents_actor_hash_check
        CHECK (actor_identity_hash ~ '^[0-9a-f]{64}$'),
    CONSTRAINT acquisition_intents_contract_hash_check
        CHECK (contract_hash ~ '^[0-9a-f]{64}$'),
    CONSTRAINT acquisition_intents_material_hash_check
        CHECK (material_request_hash ~ '^[0-9a-f]{64}$'),
    CONSTRAINT acquisition_intents_professional_version_check
        CHECK (professional_version ~ '^[0-9]+\.[0-9]+\.[0-9]+$'),
    CONSTRAINT acquisition_intents_planned_identity_complete CHECK (
        (planned_relationship_id IS NULL AND planned_agent_instance_id IS NULL)
        OR (planned_relationship_id IS NOT NULL AND planned_agent_instance_id IS NOT NULL)
    ),
    CONSTRAINT acquisition_intents_completion_check CHECK (
        (status = 'COMPLETED' AND relationship_id IS NOT NULL AND completed_at IS NOT NULL)
        OR (status <> 'COMPLETED' AND completed_at IS NULL)
    )
);

CREATE INDEX IF NOT EXISTS idx_acquisition_intents_tenant_participant
    ON business.acquisition_intents (tenant_id, participant_id, updated_at DESC)
    WHERE tenant_id IS NOT NULL AND participant_id IS NOT NULL;

GRANT SELECT, INSERT, UPDATE ON business.acquisition_intents TO business_app;
