-- Implements: work-contracts/WC-176-customer-journeys-registration-trial-hire-and-pages.md WC176-R015, WC176-R016, WC176-R017
-- Constitutional basis: C-023, C-059, C-063
-- WC-176: a payment captured at Razorpay is never lost, and recurring billing is collected.
--   * razorpay_webhook_events records each verified provider event once, so a replay is acknowledged and never repeated.
--   * razorpay_captures records each captured payment before anything is done with it; the reconciliation completes
--     it, or marks it REFUND_DUE when no Hire was completed in time. Rows are never deleted.
--   * renewal_collections remembers the provider order opened for a period's renewal and whether its grace has started.
-- WBE tables carry no row-level security and are closed to business_app, like the rest of the wallet.
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
        PERFORM set_config('waooaw.wc176_bp_owner_granted', 'true', true);
    END IF;
    IF NOT pg_has_role(session_user, 'wbe_owner', 'SET') THEN
        EXECUTE format('GRANT wbe_owner TO %I', session_user);
        PERFORM set_config('waooaw.wc176_wbe_owner_granted', 'true', true);
    END IF;
END
$owner$;
SET LOCAL ROLE bp_owner;
GRANT USAGE ON SCHEMA business TO wbe_owner;
GRANT CREATE ON SCHEMA business TO wbe_owner;
RESET ROLE;

SET LOCAL ROLE wbe_owner;

CREATE TABLE IF NOT EXISTS business.razorpay_webhook_events (
    event_id TEXT PRIMARY KEY CHECK (length(event_id) BETWEEN 1 AND 200),
    event_type TEXT NOT NULL CHECK (length(event_type) BETWEEN 1 AND 100),
    payment_id TEXT CHECK (payment_id IS NULL OR length(payment_id) BETWEEN 1 AND 200),
    payload_digest CHAR(64) NOT NULL CHECK (payload_digest ~ '^[0-9a-f]{64}$'),
    received_at TIMESTAMPTZ NOT NULL,
    processed_at TIMESTAMPTZ,
    outcome TEXT CHECK (outcome IS NULL OR length(outcome) <= 100),
    CHECK ((processed_at IS NULL) = (outcome IS NULL))
);

CREATE TABLE IF NOT EXISTS business.razorpay_captures (
    payment_id TEXT PRIMARY KEY CHECK (length(payment_id) BETWEEN 1 AND 200),
    order_id TEXT NOT NULL DEFAULT '',
    amount_paise BIGINT NOT NULL CHECK (amount_paise > 0),
    currency TEXT NOT NULL DEFAULT 'INR' CHECK (currency = 'INR'),
    notes JSONB NOT NULL DEFAULT '{}'::jsonb,
    source TEXT NOT NULL CHECK (source IN ('WEBHOOK', 'RECONCILIATION')),
    status TEXT NOT NULL CHECK (status IN ('RECEIVED', 'COMPLETED', 'REFUND_DUE', 'REFUNDED')),
    attempts INTEGER NOT NULL DEFAULT 0 CHECK (attempts >= 0),
    last_error TEXT CHECK (last_error IS NULL OR length(last_error) <= 200),
    first_seen_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ,
    refund_due_at TIMESTAMPTZ,
    refund_reference TEXT CHECK (refund_reference IS NULL OR length(refund_reference) <= 200)
);
CREATE INDEX IF NOT EXISTS razorpay_captures_open
    ON business.razorpay_captures (status, first_seen_at) WHERE status IN ('RECEIVED', 'COMPLETED');

CREATE TABLE IF NOT EXISTS business.renewal_collections (
    tenant_id UUID NOT NULL,
    relationship_id UUID NOT NULL,
    period_start TIMESTAMPTZ NOT NULL,
    order_id TEXT CHECK (order_id IS NULL OR length(order_id) <= 200),
    amount_paise BIGINT NOT NULL CHECK (amount_paise >= 0),
    status TEXT NOT NULL CHECK (status IN ('ORDER_CREATED', 'PAID_FROM_CREDIT', 'GRACE_STARTED')),
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (tenant_id, relationship_id, period_start)
);

REVOKE ALL ON business.razorpay_webhook_events, business.razorpay_captures, business.renewal_collections
    FROM PUBLIC, business_app;
GRANT SELECT, INSERT ON business.razorpay_webhook_events, business.razorpay_captures TO wbe_app;
GRANT UPDATE (processed_at, outcome) ON business.razorpay_webhook_events TO wbe_app;
GRANT UPDATE (status, attempts, last_error, completed_at, refund_due_at, refund_reference)
    ON business.razorpay_captures TO wbe_app;
GRANT SELECT, INSERT, UPDATE ON business.renewal_collections TO wbe_app;

RESET ROLE;
DO $owner$
BEGIN
    IF current_setting('waooaw.wc176_wbe_owner_granted', true) = 'true' THEN
        EXECUTE format('REVOKE wbe_owner FROM %I', session_user);
    END IF;
    IF current_setting('waooaw.wc176_bp_owner_granted', true) = 'true' THEN
        EXECUTE format('REVOKE bp_owner FROM %I', session_user);
    END IF;
END
$owner$;
COMMIT;
