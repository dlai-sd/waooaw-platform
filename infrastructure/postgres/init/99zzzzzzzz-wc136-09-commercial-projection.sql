-- Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C4-09, C4-10
-- Constitutional basis: C-059, C-088, C-089, C-090, C-063
-- WC-136 C4-09/C4-10: durable commercial projection, commercial commands, the subscription period of a
-- relationship and billing adjustments. Wallet credit is never refundable: a fee refund is a billing
-- adjustment recorded here, never a wallet entry.
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
        PERFORM set_config('waooaw.wc136_commercial_bp_owner_granted', 'true', true);
    END IF;
    IF NOT pg_has_role(session_user, 'wbe_owner', 'SET') THEN
        EXECUTE format('GRANT wbe_owner TO %I', session_user);
        PERFORM set_config('waooaw.wc136_commercial_wbe_owner_granted', 'true', true);
    END IF;
END
$owner$;
SET LOCAL ROLE bp_owner;
GRANT USAGE ON SCHEMA business TO wbe_owner;
GRANT CREATE ON SCHEMA business TO wbe_owner;
RESET ROLE;

SET LOCAL ROLE wbe_owner;

CREATE TABLE IF NOT EXISTS business.commercial_projections (
    tenant_id UUID NOT NULL,
    relationship_id UUID NOT NULL,
    projection_version TEXT NOT NULL CHECK (length(projection_version) BETWEEN 1 AND 64),
    body JSONB NOT NULL,
    produced_at TIMESTAMPTZ NOT NULL,
    valid_until TIMESTAMPTZ,
    PRIMARY KEY (tenant_id, relationship_id, projection_version)
);
CREATE INDEX IF NOT EXISTS commercial_projections_latest
    ON business.commercial_projections (tenant_id, relationship_id, produced_at DESC);

CREATE TABLE IF NOT EXISTS business.commercial_commands (
    command_id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    relationship_id UUID NOT NULL,
    idempotency_key TEXT NOT NULL CHECK (length(idempotency_key) BETWEEN 1 AND 128),
    request_digest TEXT NOT NULL CHECK (length(request_digest) = 64),
    command_kind TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN
        ('COMPLETED', 'PENDING', 'REJECTED', 'CONFLICT', 'UNKNOWN', 'UNAVAILABLE', 'BLOCKED')),
    receipt JSONB NOT NULL,
    outcome JSONB NOT NULL,
    accepted_at TIMESTAMPTZ NOT NULL,
    resolved_at TIMESTAMPTZ,
    UNIQUE (tenant_id, relationship_id, idempotency_key)
);

-- One row per billing period of a relationship; the commercial lifecycle (pause, suspend, terminate,
-- a downgrade scheduled for renewal) lives on it so that every command reads one stored truth.
CREATE TABLE IF NOT EXISTS business.relationship_periods (
    tenant_id UUID NOT NULL,
    relationship_id UUID NOT NULL,
    period_start TIMESTAMPTZ NOT NULL,
    period_end TIMESTAMPTZ NOT NULL,
    package_version_id UUID NOT NULL,
    fee_paid_paise BIGINT NOT NULL CHECK (fee_paid_paise >= 0),
    status TEXT NOT NULL CHECK (status IN ('ACTIVE', 'PAUSED', 'SUSPENDED', 'TERMINATED', 'LAPSED')),
    paused_component_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
    refunded_fee_paise BIGINT NOT NULL DEFAULT 0 CHECK (refunded_fee_paise >= 0),
    scheduled_package_version_id UUID,
    grace_until TIMESTAMPTZ,
    updated_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (tenant_id, relationship_id, period_start),
    CHECK (period_end > period_start),
    CHECK (refunded_fee_paise <= fee_paid_paise)
);
CREATE INDEX IF NOT EXISTS relationship_periods_current
    ON business.relationship_periods (tenant_id, relationship_id, period_end DESC);

CREATE TABLE IF NOT EXISTS business.billing_adjustments (
    adjustment_id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    relationship_id UUID NOT NULL,
    command_id UUID NOT NULL UNIQUE,
    adjustment_kind TEXT NOT NULL CHECK (adjustment_kind IN ('FEE_REFUND')),
    amount_paise BIGINT NOT NULL CHECK (amount_paise > 0),
    payment_reference TEXT,
    status TEXT NOT NULL CHECK (status IN ('PENDING_PROVIDER', 'DISPATCHED', 'FAILED_RETRYABLE', 'NOT_PAYABLE')),
    provider_reference TEXT,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);
CREATE INDEX IF NOT EXISTS billing_adjustments_open
    ON business.billing_adjustments (status, created_at)
    WHERE status IN ('PENDING_PROVIDER', 'FAILED_RETRYABLE');

CREATE OR REPLACE FUNCTION business.guard_commercial_command_change() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP = 'DELETE'
       OR NEW.command_id IS DISTINCT FROM OLD.command_id
       OR NEW.tenant_id IS DISTINCT FROM OLD.tenant_id
       OR NEW.relationship_id IS DISTINCT FROM OLD.relationship_id
       OR NEW.idempotency_key IS DISTINCT FROM OLD.idempotency_key
       OR NEW.request_digest IS DISTINCT FROM OLD.request_digest
       OR NEW.command_kind IS DISTINCT FROM OLD.command_kind
       OR NEW.accepted_at IS DISTINCT FROM OLD.accepted_at THEN
        RAISE EXCEPTION 'Commercial commands keep their request; only the outcome is resolved'
            USING ERRCODE = '55000';
    END IF;
    RETURN NEW;
END;
$$;

CREATE OR REPLACE FUNCTION business.guard_billing_adjustment_change() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP = 'DELETE'
       OR NEW.adjustment_id IS DISTINCT FROM OLD.adjustment_id
       OR NEW.tenant_id IS DISTINCT FROM OLD.tenant_id
       OR NEW.relationship_id IS DISTINCT FROM OLD.relationship_id
       OR NEW.command_id IS DISTINCT FROM OLD.command_id
       OR NEW.adjustment_kind IS DISTINCT FROM OLD.adjustment_kind
       OR NEW.amount_paise IS DISTINCT FROM OLD.amount_paise
       OR NEW.created_at IS DISTINCT FROM OLD.created_at THEN
        RAISE EXCEPTION 'Billing adjustments keep their amount; only the provider status changes'
            USING ERRCODE = '55000';
    END IF;
    RETURN NEW;
END;
$$;

CREATE OR REPLACE TRIGGER commercial_projections_immutable
BEFORE UPDATE OR DELETE ON business.commercial_projections
FOR EACH ROW EXECUTE FUNCTION business.guard_wallet_append_only();

CREATE OR REPLACE TRIGGER commercial_commands_guard
BEFORE UPDATE OR DELETE ON business.commercial_commands
FOR EACH ROW EXECUTE FUNCTION business.guard_commercial_command_change();

CREATE OR REPLACE TRIGGER billing_adjustments_guard
BEFORE UPDATE OR DELETE ON business.billing_adjustments
FOR EACH ROW EXECUTE FUNCTION business.guard_billing_adjustment_change();
RESET ROLE;

SET LOCAL ROLE bp_owner;
REVOKE CREATE ON SCHEMA business FROM wbe_owner;
RESET ROLE;

REVOKE ALL ON business.commercial_projections, business.commercial_commands,
    business.relationship_periods, business.billing_adjustments FROM PUBLIC, business_app;
GRANT SELECT, INSERT ON business.commercial_projections TO wbe_app;
GRANT SELECT, INSERT, UPDATE ON business.commercial_commands, business.relationship_periods,
    business.billing_adjustments TO wbe_app;
REVOKE ALL ON FUNCTION business.guard_commercial_command_change(),
    business.guard_billing_adjustment_change() FROM PUBLIC, business_app;
DO $owner$
BEGIN
    IF current_setting('waooaw.wc136_commercial_wbe_owner_granted', true) = 'true' THEN
        EXECUTE format('REVOKE wbe_owner FROM %I', session_user);
    END IF;
    IF current_setting('waooaw.wc136_commercial_bp_owner_granted', true) = 'true' THEN
        EXECUTE format('REVOKE bp_owner FROM %I', session_user);
    END IF;
END
$owner$;
COMMIT;
