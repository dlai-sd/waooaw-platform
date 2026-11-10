-- WC-134: WBE-owned accepted offering/trial component allowance and usage lifecycle.
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '30s';
DO $owner$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'wbe_owner') THEN
        CREATE ROLE wbe_owner NOLOGIN;
    END IF;
    IF NOT pg_has_role(session_user, 'wbe_owner', 'SET') THEN
        EXECUTE format('GRANT wbe_owner TO %I', session_user);
    END IF;
END
$owner$;

ALTER TABLE institutional.platform_cost_ledger
    ADD COLUMN IF NOT EXISTS component_id TEXT,
    ADD COLUMN IF NOT EXISTS offering_reservation_id UUID;
ALTER TABLE institutional.platform_cost_ledger
    ALTER COLUMN raw_cost_inr_paise TYPE BIGINT,
    ALTER COLUMN marked_up_cost_inr_paise TYPE BIGINT;
DROP INDEX IF EXISTS institutional.idx_cost_ledger_dma_invocation;
CREATE UNIQUE INDEX IF NOT EXISTS idx_cost_ledger_component_invocation
    ON institutional.platform_cost_ledger
        (tenant_id, relationship_id, agent_instance_id, invocation_id,
         COALESCE(component_id, ''))
    WHERE invocation_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS business.relationship_commercial_authorities (
    tenant_id UUID NOT NULL,
    relationship_id UUID NOT NULL,
    customer_id UUID NOT NULL REFERENCES business.organisations(id),
    authority_kind TEXT NOT NULL CHECK (authority_kind IN ('ACCEPTED_OFFERING', 'TRIAL')),
    accepted_contract_id UUID,
    contract_version INTEGER,
    bundle_profile_id UUID REFERENCES institutional.bundle_profiles(id),
    trial_id UUID REFERENCES business.trial_allocations(trial_id),
    professional_type TEXT NOT NULL,
    professional_version TEXT NOT NULL,
    active BOOLEAN NOT NULL DEFAULT false,
    valid_from TIMESTAMPTZ NOT NULL,
    valid_until TIMESTAMPTZ,
    evidence_id UUID NOT NULL,
    PRIMARY KEY (tenant_id, relationship_id),
    CHECK (
        (authority_kind = 'ACCEPTED_OFFERING' AND accepted_contract_id IS NOT NULL
            AND contract_version > 0 AND bundle_profile_id IS NOT NULL AND trial_id IS NULL)
        OR
        (authority_kind = 'TRIAL' AND trial_id IS NOT NULL AND accepted_contract_id IS NULL
            AND contract_version IS NULL AND bundle_profile_id IS NULL)
    )
);

CREATE TABLE IF NOT EXISTS business.offering_component_allocations (
    allocation_id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    relationship_id UUID NOT NULL,
    component_id TEXT NOT NULL REFERENCES institutional.thread_catalog(thread_id),
    period_start TIMESTAMPTZ NOT NULL,
    period_end TIMESTAMPTZ NOT NULL,
    granted_units BIGINT NOT NULL CHECK (granted_units >= 0),
    reserved_units BIGINT NOT NULL DEFAULT 0 CHECK (reserved_units >= 0),
    settled_units BIGINT NOT NULL DEFAULT 0 CHECK (settled_units >= 0),
    admission_fenced BOOLEAN NOT NULL DEFAULT false,
    authority_evidence_id UUID NOT NULL,
    UNIQUE (tenant_id, relationship_id, component_id, period_start),
    FOREIGN KEY (tenant_id, relationship_id)
        REFERENCES business.relationship_commercial_authorities(tenant_id, relationship_id),
    CHECK (period_end > period_start)
);

CREATE TABLE IF NOT EXISTS business.offering_component_reservations (
    reservation_id UUID PRIMARY KEY,
    allocation_id UUID NOT NULL REFERENCES business.offering_component_allocations(allocation_id),
    tenant_id UUID NOT NULL,
    customer_id UUID NOT NULL,
    relationship_id UUID NOT NULL,
    accepted_contract_id UUID,
    contract_version INTEGER,
    bundle_profile_id UUID,
    trial_id UUID,
    agent_instance_id UUID NOT NULL,
    professional_type TEXT NOT NULL,
    professional_version TEXT NOT NULL,
    skill_id TEXT NOT NULL,
    skill_version TEXT NOT NULL,
    work_item_id UUID NOT NULL,
    invocation_id UUID NOT NULL,
    component_id TEXT NOT NULL,
    idempotency_key UUID NOT NULL,
    request_digest TEXT NOT NULL CHECK (request_digest ~ '^[0-9a-f]{64}$'),
    owner_evidence_id UUID NOT NULL,
    catalogue_thread_id TEXT NOT NULL,
    provider_account_id UUID NOT NULL,
    rate_version TEXT NOT NULL,
    raw_unit_cost_paise BIGINT NOT NULL CHECK (raw_unit_cost_paise >= 0),
    marked_up_unit_cost_paise BIGINT NOT NULL CHECK (marked_up_unit_cost_paise >= 0),
    maximum_units BIGINT NOT NULL CHECK (maximum_units > 0),
    reserved_raw_paise BIGINT NOT NULL CHECK (reserved_raw_paise >= 0),
    reserved_marked_up_paise BIGINT NOT NULL CHECK (reserved_marked_up_paise >= 0),
    actual_units BIGINT,
    actual_raw_paise BIGINT,
    actual_marked_up_paise BIGINT,
    state TEXT NOT NULL CHECK (state IN ('RESERVED', 'SETTLED', 'RELEASED')),
    reserved_at TIMESTAMPTZ NOT NULL,
    settled_at TIMESTAMPTZ,
    settlement_evidence_id UUID,
    non_dispatch_evidence_id UUID,
    UNIQUE (tenant_id, relationship_id, invocation_id, component_id),
    UNIQUE (tenant_id, relationship_id, idempotency_key),
    CHECK (
        (state = 'RESERVED' AND actual_units IS NULL AND settled_at IS NULL)
        OR (state = 'SETTLED' AND actual_units IS NOT NULL AND actual_raw_paise IS NOT NULL
            AND actual_marked_up_paise IS NOT NULL AND settled_at IS NOT NULL
            AND settlement_evidence_id IS NOT NULL)
        OR (state = 'RELEASED' AND actual_units = 0 AND actual_raw_paise = 0
            AND actual_marked_up_paise = 0 AND settled_at IS NOT NULL
            AND non_dispatch_evidence_id IS NOT NULL)
    )
);

CREATE INDEX IF NOT EXISTS offering_component_reservation_allocation
    ON business.offering_component_reservations(allocation_id, state);

CREATE OR REPLACE FUNCTION business.guard_offering_usage_immutable() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'Offering usage is append-only' USING ERRCODE = '55000';
    END IF;
    IF (NEW.reservation_id, NEW.allocation_id, NEW.tenant_id, NEW.customer_id,
        NEW.relationship_id, NEW.accepted_contract_id, NEW.contract_version,
        NEW.bundle_profile_id, NEW.trial_id, NEW.agent_instance_id,
        NEW.professional_type, NEW.professional_version, NEW.skill_id,
        NEW.skill_version, NEW.work_item_id, NEW.invocation_id, NEW.component_id,
        NEW.idempotency_key, NEW.request_digest, NEW.owner_evidence_id,
        NEW.catalogue_thread_id, NEW.provider_account_id, NEW.rate_version,
        NEW.raw_unit_cost_paise, NEW.marked_up_unit_cost_paise, NEW.maximum_units,
        NEW.reserved_raw_paise, NEW.reserved_marked_up_paise, NEW.reserved_at)
       IS DISTINCT FROM
       (OLD.reservation_id, OLD.allocation_id, OLD.tenant_id, OLD.customer_id,
        OLD.relationship_id, OLD.accepted_contract_id, OLD.contract_version,
        OLD.bundle_profile_id, OLD.trial_id, OLD.agent_instance_id,
        OLD.professional_type, OLD.professional_version, OLD.skill_id,
        OLD.skill_version, OLD.work_item_id, OLD.invocation_id, OLD.component_id,
        OLD.idempotency_key, OLD.request_digest, OLD.owner_evidence_id,
        OLD.catalogue_thread_id, OLD.provider_account_id, OLD.rate_version,
        OLD.raw_unit_cost_paise, OLD.marked_up_unit_cost_paise, OLD.maximum_units,
        OLD.reserved_raw_paise, OLD.reserved_marked_up_paise, OLD.reserved_at) THEN
        RAISE EXCEPTION 'Offering reservation identity is immutable' USING ERRCODE = '55000';
    END IF;
    IF OLD.state <> 'RESERVED' OR NEW.state NOT IN ('SETTLED', 'RELEASED') THEN
        RAISE EXCEPTION 'Offering reservation transition is invalid' USING ERRCODE = '55000';
    END IF;
    RETURN NEW;
END $$;
DROP TRIGGER IF EXISTS offering_usage_immutable ON business.offering_component_reservations;
CREATE TRIGGER offering_usage_immutable
BEFORE UPDATE OR DELETE ON business.offering_component_reservations
FOR EACH ROW EXECUTE FUNCTION business.guard_offering_usage_immutable();

ALTER TABLE business.relationship_commercial_authorities OWNER TO wbe_owner;
ALTER TABLE business.offering_component_allocations OWNER TO wbe_owner;
ALTER TABLE business.offering_component_reservations OWNER TO wbe_owner;
REVOKE ALL ON business.relationship_commercial_authorities,
    business.offering_component_allocations, business.offering_component_reservations
    FROM PUBLIC, business_app;
GRANT SELECT, INSERT, UPDATE ON business.relationship_commercial_authorities,
    business.offering_component_allocations, business.offering_component_reservations TO wbe_app;
GRANT SELECT, INSERT ON institutional.platform_cost_ledger TO wbe_app;
COMMIT;
