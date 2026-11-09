-- WhatsApp customer-initiated replies incur no provider charge under the approved release policy.
-- Constitutional basis: C-023, C-026, C-059, C-063

BEGIN;

DO $bootstrap_membership$
BEGIN
    IF NOT pg_has_role(session_user, 'bp_owner', 'SET') THEN
        EXECUTE format('GRANT bp_owner TO %I', session_user);
        PERFORM set_config('waooaw.wc134_bp_owner_granted', 'true', true);
    END IF;
END
$bootstrap_membership$;

SET LOCAL ROLE bp_owner;

ALTER TABLE business.whatsapp_traffic_reservations
    DROP CONSTRAINT IF EXISTS whatsapp_traffic_reservations_reserved_cost_inr_check;
ALTER TABLE business.whatsapp_traffic_reservations
    DROP CONSTRAINT IF EXISTS whatsapp_traffic_reservations_nonnegative_reserved_cost_check,
    ADD CONSTRAINT whatsapp_traffic_reservations_nonnegative_reserved_cost_check
        CHECK (reserved_cost_inr >= 0);

RESET ROLE;
DO $bootstrap_membership$
BEGIN
    IF current_setting('waooaw.wc134_bp_owner_granted', true) = 'true' THEN
        EXECUTE format('REVOKE bp_owner FROM %I', session_user);
    END IF;
END
$bootstrap_membership$;

COMMIT;
