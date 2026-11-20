-- Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C4-04
-- Constitutional basis: C-059, C-088, C-089, C-090
-- WC-136 C4-04: PLATFORM FLOOR is never gated, but every use is recorded and counted. This is the
-- append-only record of those uses; it carries no personal data and no pseudonymous lead reference.
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '30s';
DO $owner$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'wbe_owner') THEN
        CREATE ROLE wbe_owner NOLOGIN;
    END IF;
    IF NOT pg_has_role(session_user, 'bp_owner', 'SET') THEN
        EXECUTE format('GRANT bp_owner TO %I', session_user);
        PERFORM set_config('waooaw.wc136_platform_accounts_bp_owner_granted', 'true', true);
    END IF;
    IF NOT pg_has_role(session_user, 'wbe_owner', 'SET') THEN
        EXECUTE format('GRANT wbe_owner TO %I', session_user);
        PERFORM set_config('waooaw.wc136_platform_accounts_wbe_owner_granted', 'true', true);
    END IF;
END
$owner$;
SET LOCAL ROLE bp_owner;
GRANT USAGE ON SCHEMA business TO wbe_owner;
GRANT CREATE ON SCHEMA business TO wbe_owner;
RESET ROLE;

SET LOCAL ROLE wbe_owner;

CREATE TABLE IF NOT EXISTS business.wallet_floor_uses (
    tenant_id UUID NOT NULL,
    environment TEXT NOT NULL CHECK (length(environment) BETWEEN 1 AND 100),
    use_id UUID NOT NULL,
    purpose TEXT NOT NULL CHECK (length(purpose) BETWEEN 1 AND 100),
    component_id TEXT NOT NULL CHECK (length(component_id) BETWEEN 1 AND 200),
    amount_paise BIGINT NOT NULL CHECK (amount_paise >= 0),
    invocation_id UUID,
    evidence_id UUID NOT NULL,
    occurred_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (tenant_id, environment, use_id)
);

CREATE INDEX IF NOT EXISTS wallet_floor_uses_time
    ON business.wallet_floor_uses (tenant_id, environment, occurred_at);

CREATE OR REPLACE TRIGGER wallet_floor_uses_immutable
BEFORE UPDATE OR DELETE ON business.wallet_floor_uses
FOR EACH ROW EXECUTE FUNCTION business.guard_wallet_append_only();
RESET ROLE;

SET LOCAL ROLE bp_owner;
REVOKE CREATE ON SCHEMA business FROM wbe_owner;
RESET ROLE;

REVOKE ALL ON business.wallet_floor_uses FROM PUBLIC, business_app;
GRANT SELECT, INSERT ON business.wallet_floor_uses TO wbe_app;
DO $owner$
BEGIN
    IF current_setting('waooaw.wc136_platform_accounts_wbe_owner_granted', true) = 'true' THEN
        EXECUTE format('REVOKE wbe_owner FROM %I', session_user);
    END IF;
    IF current_setting('waooaw.wc136_platform_accounts_bp_owner_granted', true) = 'true' THEN
        EXECUTE format('REVOKE bp_owner FROM %I', session_user);
    END IF;
END
$owner$;
COMMIT;
