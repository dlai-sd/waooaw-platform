-- WC-120 Demo outbound effect reservations. No token, phone, message or provider body is stored here.
-- Constitutional basis: C-005, C-023, C-026, C-059, C-063

BEGIN;

DO $bootstrap_membership$
BEGIN
    IF NOT pg_has_role(session_user, 'bp_owner', 'SET') THEN
        EXECUTE format('GRANT bp_owner TO %I', session_user);
        PERFORM set_config('waooaw.wc120_bp_owner_granted', 'true', true);
    END IF;
END
$bootstrap_membership$;

SET LOCAL ROLE bp_owner;

CREATE TABLE IF NOT EXISTS business.whatsapp_traffic_reservations (
    tenant_id UUID NOT NULL,
    activation_digest VARCHAR(64) NOT NULL,
    authority_digest VARCHAR(64) NOT NULL,
    outbox_id UUID NOT NULL,
    attempt_number INTEGER NOT NULL CHECK (attempt_number > 0),
    reserved_cost_inr NUMERIC(18, 6) NOT NULL CHECK (reserved_cost_inr > 0),
    reserved_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (tenant_id, activation_digest, outbox_id),
    CONSTRAINT whatsapp_traffic_activation_digest_check
        CHECK (activation_digest ~ '^[a-f0-9]{64}$'),
    CONSTRAINT whatsapp_traffic_authority_digest_check
        CHECK (authority_digest ~ '^[a-f0-9]{64}$')
);

CREATE INDEX IF NOT EXISTS idx_whatsapp_traffic_reservations_window
    ON business.whatsapp_traffic_reservations (tenant_id, activation_digest, reserved_at);

ALTER TABLE business.whatsapp_traffic_reservations OWNER TO bp_owner;
ALTER TABLE business.whatsapp_traffic_reservations ENABLE ROW LEVEL SECURITY;
ALTER TABLE business.whatsapp_traffic_reservations FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS whatsapp_traffic_reservations_tenant_isolation
    ON business.whatsapp_traffic_reservations;
CREATE POLICY whatsapp_traffic_reservations_tenant_isolation
    ON business.whatsapp_traffic_reservations
    USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', TRUE), '')::UUID)
    WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', TRUE), '')::UUID);

REVOKE ALL ON business.whatsapp_traffic_reservations FROM PUBLIC;
GRANT SELECT, INSERT ON business.whatsapp_traffic_reservations TO business_app, bp_runtime;
REVOKE UPDATE, DELETE, TRUNCATE
    ON business.whatsapp_traffic_reservations FROM business_app, bp_runtime;

RESET ROLE;
DO $bootstrap_membership$
BEGIN
    IF current_setting('waooaw.wc120_bp_owner_granted', true) = 'true' THEN
        EXECUTE format('REVOKE bp_owner FROM %I', session_user);
    END IF;
END
$bootstrap_membership$;

COMMIT;
