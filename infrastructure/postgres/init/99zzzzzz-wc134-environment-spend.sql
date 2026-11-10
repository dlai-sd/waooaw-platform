-- WC-134: one environment-wide operational monetary authority across service-tenant rotation.
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '30s';
SET LOCAL ROLE bp_owner;

CREATE TABLE IF NOT EXISTS business.environment_spend_authorities (
    environment TEXT PRIMARY KEY,
    authority_version INTEGER NOT NULL CHECK (authority_version > 0),
    maximum_paise BIGINT NOT NULL CHECK (maximum_paise >= 0 AND maximum_paise <= 50000),
    active BOOLEAN NOT NULL DEFAULT false,
    migration_complete BOOLEAN NOT NULL DEFAULT false,
    authority_evidence_id UUID NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS business.environment_spend_attempts (
    environment TEXT NOT NULL REFERENCES business.environment_spend_authorities(environment),
    owner_kind TEXT NOT NULL CHECK (owner_kind IN ('MODEL', 'MESSAGING')),
    attempt_id UUID NOT NULL,
    original_tenant_id UUID NOT NULL,
    activation_digest TEXT NOT NULL,
    request_digest TEXT NOT NULL CHECK (request_digest ~ '^[0-9a-f]{64}$'),
    reservation_reference UUID NOT NULL,
    reserved_paise BIGINT NOT NULL CHECK (reserved_paise >= 0),
    actual_paise BIGINT,
    state TEXT NOT NULL CHECK (state IN ('RESERVED', 'SETTLED', 'RELEASED', 'RECONCILIATION_REQUIRED')),
    overrun BOOLEAN NOT NULL DEFAULT false,
    reserved_at TIMESTAMPTZ NOT NULL,
    usage_at TIMESTAMPTZ,
    settlement_evidence_id UUID,
    PRIMARY KEY (environment, owner_kind, attempt_id),
    UNIQUE (environment, reservation_reference),
    CHECK (
        (state IN ('RESERVED', 'RECONCILIATION_REQUIRED') AND actual_paise IS NULL)
        OR (state = 'SETTLED' AND actual_paise IS NOT NULL AND usage_at IS NOT NULL
            AND settlement_evidence_id IS NOT NULL)
        OR (state = 'RELEASED' AND actual_paise = 0 AND usage_at IS NOT NULL
            AND settlement_evidence_id IS NOT NULL)
    )
);

CREATE TABLE IF NOT EXISTS business.conversation_inference_spend_coordinators (
    tenant_id UUID NOT NULL,
    relationship_id UUID NOT NULL,
    execution_id UUID NOT NULL,
    request_digest TEXT NOT NULL CHECK (request_digest ~ '^[0-9a-f]{64}$'),
    owner_evidence_id UUID NOT NULL,
    component_id TEXT NOT NULL,
    invocation_id UUID NOT NULL,
    wbe_reservation_id UUID,
    operational_reservation_id UUID,
    wbe_state TEXT NOT NULL CHECK (wbe_state IN ('PENDING', 'RESERVED', 'SETTLED', 'RELEASED', 'UNRESOLVED')),
    operational_state TEXT NOT NULL CHECK (operational_state IN ('PENDING', 'RESERVED', 'SETTLED', 'RELEASED', 'UNRESOLVED')),
    provider_dispatch_state TEXT NOT NULL CHECK (provider_dispatch_state IN ('NOT_DISPATCHED', 'POSSIBLE', 'DISPATCHED')),
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (tenant_id, execution_id),
    UNIQUE (tenant_id, relationship_id, invocation_id, component_id)
);

CREATE OR REPLACE FUNCTION business.environment_spend_exposure(
    p_environment TEXT, p_as_of TIMESTAMPTZ
) RETURNS BIGINT
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = business, pg_temp AS $$
    SELECT COALESCE(sum(CASE
        WHEN state IN ('RESERVED', 'RECONCILIATION_REQUIRED') THEN reserved_paise
        WHEN state = 'SETTLED' AND usage_at >= p_as_of - interval '24 hours' THEN actual_paise
        ELSE 0 END), 0)::BIGINT
    FROM business.environment_spend_attempts
    WHERE environment = p_environment
$$;
ALTER FUNCTION business.environment_spend_exposure(TEXT, TIMESTAMPTZ) OWNER TO bp_owner;

CREATE OR REPLACE FUNCTION business.guard_environment_spend_attempt() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'Environment spend history is append-only' USING ERRCODE = '55000';
    END IF;
    IF (NEW.environment, NEW.owner_kind, NEW.attempt_id, NEW.original_tenant_id,
        NEW.activation_digest, NEW.request_digest, NEW.reservation_reference,
        NEW.reserved_paise, NEW.reserved_at)
       IS DISTINCT FROM
       (OLD.environment, OLD.owner_kind, OLD.attempt_id, OLD.original_tenant_id,
        OLD.activation_digest, OLD.request_digest, OLD.reservation_reference,
        OLD.reserved_paise, OLD.reserved_at) THEN
        RAISE EXCEPTION 'Environment spend identity is immutable' USING ERRCODE = '55000';
    END IF;
    IF OLD.state NOT IN ('RESERVED', 'RECONCILIATION_REQUIRED')
        OR NEW.state NOT IN ('SETTLED', 'RELEASED') THEN
        RAISE EXCEPTION 'Environment spend transition is invalid' USING ERRCODE = '55000';
    END IF;
    RETURN NEW;
END $$;
DROP TRIGGER IF EXISTS environment_spend_attempt_guard ON business.environment_spend_attempts;
CREATE TRIGGER environment_spend_attempt_guard
BEFORE UPDATE OR DELETE ON business.environment_spend_attempts
FOR EACH ROW EXECUTE FUNCTION business.guard_environment_spend_attempt();

CREATE OR REPLACE FUNCTION business.require_environment_spend_writer() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path = business, pg_temp AS $$
BEGIN
    IF TG_TABLE_NAME = 'conversation_model_reservations' THEN
        IF NOT EXISTS (
            SELECT 1
            FROM business.environment_spend_authorities authority
            JOIN business.environment_spend_attempts attempt
              ON attempt.environment=authority.environment
             AND attempt.owner_kind='MODEL'
             AND attempt.attempt_id=NEW.execution_id
             AND attempt.reservation_reference=NEW.reservation_id
             AND attempt.original_tenant_id=NEW.customer_tenant_id
            WHERE authority.environment=NEW.environment
              AND authority.active AND authority.migration_complete
        ) THEN
            RAISE EXCEPTION 'Environment spend owner permit is required'
                USING ERRCODE = '42501';
        END IF;
    ELSIF TG_TABLE_NAME = 'whatsapp_traffic_reservations' THEN
        IF NOT EXISTS (
            SELECT 1 FROM business.environment_spend_attempts attempt
            JOIN business.environment_spend_authorities authority
              ON authority.environment=attempt.environment
            WHERE attempt.owner_kind='MESSAGING'
              AND attempt.attempt_id=NEW.outbox_id
              AND attempt.reservation_reference=NEW.outbox_id
              AND attempt.original_tenant_id=NEW.tenant_id
              AND authority.active AND authority.migration_complete
        ) THEN
            RAISE EXCEPTION 'Environment spend owner permit is required'
                USING ERRCODE = '42501';
        END IF;
    END IF;
    RETURN NEW;
END $$;
ALTER FUNCTION business.require_environment_spend_writer() OWNER TO bp_owner;
DROP TRIGGER IF EXISTS conversation_model_environment_writer
    ON business.conversation_model_reservations;
CREATE TRIGGER conversation_model_environment_writer
BEFORE INSERT ON business.conversation_model_reservations
FOR EACH ROW EXECUTE FUNCTION business.require_environment_spend_writer();
DO $messaging_fence$
BEGIN
    IF to_regclass('business.whatsapp_traffic_reservations') IS NOT NULL THEN
        DROP TRIGGER IF EXISTS whatsapp_environment_writer
            ON business.whatsapp_traffic_reservations;
        CREATE TRIGGER whatsapp_environment_writer
        BEFORE INSERT ON business.whatsapp_traffic_reservations
        FOR EACH ROW EXECUTE FUNCTION business.require_environment_spend_writer();
    END IF;
END
$messaging_fence$;

ALTER TABLE business.environment_spend_authorities OWNER TO bp_owner;
ALTER TABLE business.environment_spend_attempts OWNER TO bp_owner;
ALTER TABLE business.conversation_inference_spend_coordinators OWNER TO bp_owner;
ALTER TABLE business.conversation_inference_spend_coordinators ENABLE ROW LEVEL SECURITY;
ALTER TABLE business.conversation_inference_spend_coordinators FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS inference_spend_coordinator_tenant
    ON business.conversation_inference_spend_coordinators;
CREATE POLICY inference_spend_coordinator_tenant
    ON business.conversation_inference_spend_coordinators
    USING (tenant_id = nullif(current_setting('app.current_tenant_id', true), '')::UUID)
    WITH CHECK (tenant_id = nullif(current_setting('app.current_tenant_id', true), '')::UUID);
REVOKE ALL ON business.environment_spend_authorities, business.environment_spend_attempts
    FROM PUBLIC, business_app;
GRANT SELECT ON business.environment_spend_authorities, business.environment_spend_attempts
    TO business_app;
GRANT INSERT ON business.environment_spend_attempts TO business_app;
GRANT UPDATE (actual_paise, state, overrun, usage_at, settlement_evidence_id)
    ON business.environment_spend_attempts TO business_app;
REVOKE ALL ON business.conversation_inference_spend_coordinators FROM PUBLIC, business_app;
GRANT SELECT, INSERT ON business.conversation_inference_spend_coordinators TO business_app;
GRANT UPDATE (wbe_reservation_id, operational_reservation_id, wbe_state,
    operational_state, provider_dispatch_state, updated_at)
    ON business.conversation_inference_spend_coordinators TO business_app;
GRANT EXECUTE ON FUNCTION business.environment_spend_exposure(TEXT, TIMESTAMPTZ) TO business_app;

-- New writers fail closed until an owner explicitly maps legacy exposure and completes cutover.
INSERT INTO business.environment_spend_authorities
    (environment, authority_version, maximum_paise, active, migration_complete,
     authority_evidence_id, updated_at)
SELECT DISTINCT environment, 1, 50000, false, false,
    '00000000-0000-0000-0000-000000000000'::UUID, clock_timestamp()
FROM business.conversation_model_reservations
ON CONFLICT (environment) DO NOTHING;
COMMIT;
