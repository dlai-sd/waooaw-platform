-- Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C3-06
-- Constitutional basis: C-023, C-059, C-063
-- Budget leases: an instance draws per-call reservations from a leased slice of the environment
-- ceiling without taking the environment-wide lock. The exposure function counts an ACTIVE lease
-- at its full grant and counts attempts directly once the lease is returned or expired, so total
-- exposure never exceeds the ceiling and unused lease value returns on close or expiry.
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '30s';
SET LOCAL ROLE bp_owner;

CREATE TABLE IF NOT EXISTS business.environment_spend_leases (
    lease_id UUID PRIMARY KEY,
    environment TEXT NOT NULL REFERENCES business.environment_spend_authorities(environment),
    holder TEXT NOT NULL CHECK (length(holder) BETWEEN 1 AND 128),
    granted_paise BIGINT NOT NULL CHECK (granted_paise > 0),
    consumed_paise BIGINT NOT NULL DEFAULT 0 CHECK (consumed_paise >= 0),
    state TEXT NOT NULL CHECK (state IN ('ACTIVE', 'RETURNED', 'EXPIRED')),
    granted_at TIMESTAMPTZ NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    CHECK (expires_at > granted_at)
);
ALTER TABLE business.environment_spend_leases OWNER TO bp_owner;

CREATE INDEX IF NOT EXISTS environment_spend_leases_active_idx
    ON business.environment_spend_leases (environment) WHERE state = 'ACTIVE';

ALTER TABLE business.environment_spend_attempts
    ADD COLUMN IF NOT EXISTS lease_id UUID REFERENCES business.environment_spend_leases(lease_id);

CREATE INDEX IF NOT EXISTS environment_spend_attempts_lease_idx
    ON business.environment_spend_attempts (lease_id) WHERE lease_id IS NOT NULL;

CREATE OR REPLACE FUNCTION business.guard_environment_spend_lease() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'Environment spend lease history is append-only' USING ERRCODE = '55000';
    END IF;
    IF (NEW.lease_id, NEW.environment, NEW.holder, NEW.granted_paise, NEW.granted_at, NEW.expires_at)
       IS DISTINCT FROM
       (OLD.lease_id, OLD.environment, OLD.holder, OLD.granted_paise, OLD.granted_at, OLD.expires_at) THEN
        RAISE EXCEPTION 'Environment spend lease identity is immutable' USING ERRCODE = '55000';
    END IF;
    IF NEW.state IS DISTINCT FROM OLD.state
       AND (OLD.state <> 'ACTIVE' OR NEW.state NOT IN ('RETURNED', 'EXPIRED')) THEN
        RAISE EXCEPTION 'Environment spend lease transition is invalid' USING ERRCODE = '55000';
    END IF;
    RETURN NEW;
END $$;
ALTER FUNCTION business.guard_environment_spend_lease() OWNER TO bp_owner;

CREATE OR REPLACE TRIGGER environment_spend_lease_guard
BEFORE UPDATE OR DELETE ON business.environment_spend_leases
FOR EACH ROW EXECUTE FUNCTION business.guard_environment_spend_lease();

CREATE OR REPLACE FUNCTION business.guard_environment_spend_attempt_lease() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF OLD.lease_id IS NOT NULL AND NEW.lease_id IS DISTINCT FROM OLD.lease_id THEN
        RAISE EXCEPTION 'Environment spend attempt lease is immutable' USING ERRCODE = '55000';
    END IF;
    RETURN NEW;
END $$;
ALTER FUNCTION business.guard_environment_spend_attempt_lease() OWNER TO bp_owner;

CREATE OR REPLACE TRIGGER environment_spend_attempt_lease_guard
BEFORE UPDATE ON business.environment_spend_attempts
FOR EACH ROW EXECUTE FUNCTION business.guard_environment_spend_attempt_lease();

CREATE OR REPLACE FUNCTION business.environment_spend_exposure(
    p_environment TEXT, p_as_of TIMESTAMPTZ
) RETURNS BIGINT
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = business, pg_temp AS $$
    SELECT (
        COALESCE((
            SELECT sum(CASE
                WHEN attempt.state IN ('RESERVED', 'RECONCILIATION_REQUIRED')
                    THEN attempt.reserved_paise
                WHEN attempt.state = 'SETTLED' AND attempt.usage_at >= p_as_of - interval '24 hours'
                    THEN attempt.actual_paise
                ELSE 0 END)
            FROM business.environment_spend_attempts attempt
            LEFT JOIN business.environment_spend_leases lease ON lease.lease_id = attempt.lease_id
            WHERE attempt.environment = p_environment
              AND COALESCE(lease.state, '') <> 'ACTIVE'
        ), 0)
        + COALESCE((
            SELECT sum(active_lease.granted_paise)
            FROM business.environment_spend_leases active_lease
            WHERE active_lease.environment = p_environment AND active_lease.state = 'ACTIVE'
        ), 0)
    )::BIGINT
$$;
ALTER FUNCTION business.environment_spend_exposure(TEXT, TIMESTAMPTZ) OWNER TO bp_owner;

REVOKE ALL ON business.environment_spend_leases FROM PUBLIC, business_app;
GRANT SELECT, INSERT ON business.environment_spend_leases TO business_app;
GRANT UPDATE (consumed_paise, state) ON business.environment_spend_leases TO business_app;
GRANT EXECUTE ON FUNCTION business.environment_spend_exposure(TEXT, TIMESTAMPTZ) TO business_app;

COMMIT;
