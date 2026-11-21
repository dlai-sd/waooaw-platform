-- Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C4-10
-- Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C5-03
-- Constitutional basis: C-059, C-038, C-088, C-089, C-090, C-063
-- WC-136 C4-10: a renewal period remembers the payment that bought it (one payment starts one period) and an
-- upgrade fee difference is a billing adjustment that is collected, not only reported.
-- WC-136 C5-03: the pricing-admin idempotency record is durable and shared by every billing-engine replica.
-- Also grants the read the pricing dashboard needs on the provider circuit-breaker state.
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
        PERFORM set_config('waooaw.wc136_renewal_bp_owner_granted', 'true', true);
    END IF;
    IF NOT pg_has_role(session_user, 'wbe_owner', 'SET') THEN
        EXECUTE format('GRANT wbe_owner TO %I', session_user);
        PERFORM set_config('waooaw.wc136_renewal_wbe_owner_granted', 'true', true);
    END IF;
END
$owner$;
SET LOCAL ROLE bp_owner;
GRANT USAGE ON SCHEMA business TO wbe_owner;
GRANT CREATE ON SCHEMA business TO wbe_owner;
RESET ROLE;

SET LOCAL ROLE wbe_owner;

ALTER TABLE business.relationship_periods ADD COLUMN IF NOT EXISTS payment_reference TEXT;
CREATE UNIQUE INDEX IF NOT EXISTS relationship_periods_payment
    ON business.relationship_periods (tenant_id, relationship_id, payment_reference)
    WHERE payment_reference IS NOT NULL;

DO $kinds$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'business.billing_adjustments'::regclass
          AND conname = 'billing_adjustments_adjustment_kind_check'
          AND pg_get_constraintdef(oid) LIKE '%UPGRADE_FEE%'
    ) THEN
        ALTER TABLE business.billing_adjustments DROP CONSTRAINT IF EXISTS billing_adjustments_adjustment_kind_check;
        ALTER TABLE business.billing_adjustments ADD CONSTRAINT billing_adjustments_adjustment_kind_check
            CHECK (adjustment_kind IN ('FEE_REFUND', 'UPGRADE_FEE'));
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'business.billing_adjustments'::regclass
          AND conname = 'billing_adjustments_status_check'
          AND pg_get_constraintdef(oid) LIKE '%COLLECTED%'
    ) THEN
        ALTER TABLE business.billing_adjustments DROP CONSTRAINT IF EXISTS billing_adjustments_status_check;
        ALTER TABLE business.billing_adjustments ADD CONSTRAINT billing_adjustments_status_check
            CHECK (status IN ('PENDING_PROVIDER', 'DISPATCHED', 'FAILED_RETRYABLE', 'NOT_PAYABLE',
                              'ORDER_CREATED', 'COLLECTED'));
    END IF;
END
$kinds$;

DROP INDEX IF EXISTS business.billing_adjustments_open;
CREATE INDEX IF NOT EXISTS billing_adjustments_open_by_kind
    ON business.billing_adjustments (adjustment_kind, status, created_at)
    WHERE status IN ('PENDING_PROVIDER', 'FAILED_RETRYABLE');

-- One stored response per (actor, operation, key); a replay with another body digest is a conflict.
CREATE TABLE IF NOT EXISTS business.pricing_admin_idempotency (
    actor_id TEXT NOT NULL CHECK (length(actor_id) > 0),
    operation TEXT NOT NULL CHECK (length(operation) BETWEEN 1 AND 80),
    idempotency_key TEXT NOT NULL CHECK (length(idempotency_key) BETWEEN 1 AND 128),
    request_digest TEXT NOT NULL CHECK (length(request_digest) = 64),
    status_code INTEGER NOT NULL CHECK (status_code BETWEEN 200 AND 299),
    payload JSONB NOT NULL,
    stored_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (actor_id, operation, idempotency_key)
);
CREATE INDEX IF NOT EXISTS pricing_admin_idempotency_stored
    ON business.pricing_admin_idempotency (stored_at);
RESET ROLE;

SET LOCAL ROLE bp_owner;
REVOKE CREATE ON SCHEMA business FROM wbe_owner;
RESET ROLE;

REVOKE ALL ON business.pricing_admin_idempotency FROM PUBLIC, business_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON business.pricing_admin_idempotency TO wbe_app;
GRANT SELECT ON institutional.provider_circuit_breaker TO wbe_app;
DO $owner$
BEGIN
    IF current_setting('waooaw.wc136_renewal_wbe_owner_granted', true) = 'true' THEN
        EXECUTE format('REVOKE wbe_owner FROM %I', session_user);
    END IF;
    IF current_setting('waooaw.wc136_renewal_bp_owner_granted', true) = 'true' THEN
        EXECUTE format('REVOKE bp_owner FROM %I', session_user);
    END IF;
END
$owner$;
COMMIT;
