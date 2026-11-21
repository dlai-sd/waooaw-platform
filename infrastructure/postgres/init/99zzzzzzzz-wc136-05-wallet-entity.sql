-- Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C4-01
-- Constitutional basis: C-059, C-088, C-089, C-090
-- WC-136 C4-01: the single WBE Wallet entity (accounts, lots, entries, reservations).
-- Tenant id is in every key and every query; there are no row-level-security policies on WBE tables.
-- Lots and entries are append-only; a reservation changes only state, actual_paise and resolved_at.
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
        PERFORM set_config('waooaw.wc136_wallet_bp_owner_granted', 'true', true);
    END IF;
    IF NOT pg_has_role(session_user, 'wbe_owner', 'SET') THEN
        EXECUTE format('GRANT wbe_owner TO %I', session_user);
        PERFORM set_config('waooaw.wc136_wallet_wbe_owner_granted', 'true', true);
    END IF;
END
$owner$;
SET LOCAL ROLE bp_owner;
GRANT USAGE ON SCHEMA business TO wbe_owner;
GRANT CREATE ON SCHEMA business TO wbe_owner;
RESET ROLE;

SET LOCAL ROLE wbe_owner;

CREATE TABLE IF NOT EXISTS business.wallet_accounts (
    account_id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    owner_kind TEXT NOT NULL CHECK (owner_kind IN ('CUSTOMER', 'PLATFORM')),
    owner_ref UUID,
    account_class TEXT NOT NULL CHECK (account_class IN (
        'ACQUISITION', 'SETUP_GRANT', 'TRIAL', 'SUBSCRIPTION', 'PLATFORM_FLOOR', 'SIMULATION'
    )),
    scope_kind TEXT NOT NULL CHECK (scope_kind IN ('RELATIONSHIP', 'MARKETPLACE', 'ENVIRONMENT')),
    relationship_id UUID,
    skill_id TEXT,
    campaign_ref TEXT,
    lead_ref TEXT,
    environment TEXT,
    agent_type TEXT,
    agent_version TEXT,
    status TEXT NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE', 'CLOSED')),
    created_at TIMESTAMPTZ NOT NULL,
    UNIQUE (tenant_id, account_id),
    CHECK (
        (account_class = 'SUBSCRIPTION' AND owner_kind = 'CUSTOMER'
            AND scope_kind = 'RELATIONSHIP' AND relationship_id IS NOT NULL)
        OR
        (account_class IN ('TRIAL', 'SETUP_GRANT') AND owner_kind = 'PLATFORM'
            AND scope_kind = 'RELATIONSHIP' AND relationship_id IS NOT NULL
            AND agent_type IS NOT NULL AND agent_version IS NOT NULL)
        OR
        (account_class = 'ACQUISITION' AND owner_kind = 'PLATFORM' AND scope_kind = 'MARKETPLACE')
        OR
        (account_class IN ('PLATFORM_FLOOR', 'SIMULATION') AND owner_kind = 'PLATFORM'
            AND scope_kind = 'ENVIRONMENT' AND environment IS NOT NULL)
    ),
    CHECK ((owner_kind = 'PLATFORM') = (owner_ref IS NULL))
);

CREATE UNIQUE INDEX IF NOT EXISTS wallet_accounts_key
    ON business.wallet_accounts (
        tenant_id, account_class,
        COALESCE(relationship_id, '00000000-0000-0000-0000-000000000000'::uuid),
        COALESCE(skill_id, ''), COALESCE(campaign_ref, ''),
        COALESCE(lead_ref, ''), COALESCE(environment, ''));

CREATE TABLE IF NOT EXISTS business.wallet_lots (
    lot_id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    account_id UUID NOT NULL,
    lot_kind TEXT NOT NULL CHECK (lot_kind IN ('PERIOD_CREDIT', 'TOPUP_CREDIT', 'GRANT')),
    credited_paise BIGINT NOT NULL CHECK (credited_paise > 0),
    valid_from TIMESTAMPTZ NOT NULL,
    valid_until TIMESTAMPTZ NOT NULL,
    source_kind TEXT NOT NULL CHECK (source_kind IN (
        'PACKAGE_PERIOD', 'TOPUP', 'TRIAL_GRANT', 'SETUP_GRANT',
        'ACQUISITION_BUDGET', 'SIMULATION_BUDGET'
    )),
    source_ref TEXT NOT NULL CHECK (length(source_ref) BETWEEN 1 AND 300),
    pinned_versions JSONB NOT NULL,
    evidence_id UUID NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    UNIQUE (tenant_id, lot_id),
    FOREIGN KEY (tenant_id, account_id) REFERENCES business.wallet_accounts (tenant_id, account_id),
    CHECK (valid_until > valid_from),
    CHECK (
        (lot_kind = 'PERIOD_CREDIT' AND source_kind = 'PACKAGE_PERIOD')
        OR (lot_kind = 'TOPUP_CREDIT' AND source_kind = 'TOPUP')
        OR (lot_kind = 'GRANT' AND source_kind IN (
            'TRIAL_GRANT', 'SETUP_GRANT', 'ACQUISITION_BUDGET', 'SIMULATION_BUDGET'))
    )
);

CREATE INDEX IF NOT EXISTS wallet_lots_account
    ON business.wallet_lots (tenant_id, account_id, valid_until);

CREATE TABLE IF NOT EXISTS business.wallet_reservations (
    reservation_id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    account_id UUID NOT NULL,
    lot_id UUID NOT NULL,
    component_id TEXT NOT NULL CHECK (length(component_id) BETWEEN 1 AND 200),
    reserved_paise BIGINT NOT NULL CHECK (reserved_paise > 0),
    actual_paise BIGINT,
    state TEXT NOT NULL CHECK (state IN ('RESERVED', 'SETTLED', 'RELEASED', 'UNKNOWN')),
    pinned_account_class TEXT NOT NULL CHECK (pinned_account_class IN (
        'ACQUISITION', 'SETUP_GRANT', 'TRIAL', 'SUBSCRIPTION', 'PLATFORM_FLOOR', 'SIMULATION'
    )),
    pinned_versions JSONB NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    resolved_at TIMESTAMPTZ,
    UNIQUE (tenant_id, reservation_id),
    FOREIGN KEY (tenant_id, account_id) REFERENCES business.wallet_accounts (tenant_id, account_id),
    FOREIGN KEY (tenant_id, lot_id) REFERENCES business.wallet_lots (tenant_id, lot_id),
    CHECK (
        (state = 'SETTLED' AND actual_paise IS NOT NULL AND actual_paise > 0 AND resolved_at IS NOT NULL)
        OR (state = 'RELEASED' AND actual_paise = 0 AND resolved_at IS NOT NULL)
        OR (state IN ('RESERVED', 'UNKNOWN') AND actual_paise IS NULL AND resolved_at IS NULL)
    )
);

CREATE INDEX IF NOT EXISTS wallet_reservations_lot
    ON business.wallet_reservations (tenant_id, lot_id, state);
CREATE INDEX IF NOT EXISTS wallet_reservations_account
    ON business.wallet_reservations (tenant_id, account_id, state);

CREATE TABLE IF NOT EXISTS business.wallet_entries (
    entry_id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    account_id UUID NOT NULL,
    lot_id UUID,
    entry_kind TEXT NOT NULL CHECK (entry_kind IN (
        'CREDIT', 'RESERVE', 'SETTLE', 'RELEASE', 'EXPIRE', 'ADJUST'
    )),
    amount_paise BIGINT NOT NULL CHECK (amount_paise > 0),
    reservation_id UUID,
    idempotency_key UUID NOT NULL,
    request_digest TEXT NOT NULL CHECK (request_digest ~ '^[0-9a-f]{64}$'),
    component_id TEXT,
    invocation_id UUID,
    evidence_id UUID,
    occurred_at TIMESTAMPTZ NOT NULL,
    UNIQUE (tenant_id, idempotency_key, entry_kind),
    FOREIGN KEY (tenant_id, account_id) REFERENCES business.wallet_accounts (tenant_id, account_id),
    FOREIGN KEY (tenant_id, lot_id) REFERENCES business.wallet_lots (tenant_id, lot_id),
    FOREIGN KEY (tenant_id, reservation_id)
        REFERENCES business.wallet_reservations (tenant_id, reservation_id)
);

CREATE INDEX IF NOT EXISTS wallet_entries_account
    ON business.wallet_entries (tenant_id, account_id, occurred_at);
CREATE INDEX IF NOT EXISTS wallet_entries_lot
    ON business.wallet_entries (tenant_id, lot_id, entry_kind);

CREATE OR REPLACE FUNCTION business.guard_wallet_append_only() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'Wallet % rows are append-only', TG_TABLE_NAME USING ERRCODE = '55000';
END;
$$;

CREATE OR REPLACE FUNCTION business.guard_wallet_reservation() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'Wallet reservations are never deleted' USING ERRCODE = '55000';
    END IF;
    IF (NEW.reservation_id, NEW.tenant_id, NEW.account_id, NEW.lot_id, NEW.component_id,
        NEW.reserved_paise, NEW.pinned_account_class, NEW.pinned_versions,
        NEW.expires_at, NEW.created_at)
       IS DISTINCT FROM
       (OLD.reservation_id, OLD.tenant_id, OLD.account_id, OLD.lot_id, OLD.component_id,
        OLD.reserved_paise, OLD.pinned_account_class, OLD.pinned_versions,
        OLD.expires_at, OLD.created_at) THEN
        RAISE EXCEPTION 'Wallet reservation identity is immutable' USING ERRCODE = '55000';
    END IF;
    IF OLD.state IN ('SETTLED', 'RELEASED')
       AND (NEW.state, NEW.actual_paise, NEW.resolved_at)
           IS DISTINCT FROM (OLD.state, OLD.actual_paise, OLD.resolved_at) THEN
        RAISE EXCEPTION 'A resolved wallet reservation cannot change' USING ERRCODE = '55000';
    END IF;
    RETURN NEW;
END;
$$;

CREATE OR REPLACE TRIGGER wallet_lots_immutable
BEFORE UPDATE OR DELETE ON business.wallet_lots
FOR EACH ROW EXECUTE FUNCTION business.guard_wallet_append_only();

CREATE OR REPLACE TRIGGER wallet_entries_immutable
BEFORE UPDATE OR DELETE ON business.wallet_entries
FOR EACH ROW EXECUTE FUNCTION business.guard_wallet_append_only();

CREATE OR REPLACE TRIGGER wallet_reservations_guard
BEFORE UPDATE OR DELETE ON business.wallet_reservations
FOR EACH ROW EXECUTE FUNCTION business.guard_wallet_reservation();

-- Per lot: credited minus open reservations minus settled actuals minus expired value, summed over
-- the lots valid at p_at. WalletLedger computes the same quantity; keep the two in step.
CREATE OR REPLACE FUNCTION business.wallet_available(p_tenant UUID, p_account UUID, p_at TIMESTAMPTZ)
RETURNS BIGINT
LANGUAGE sql STABLE SECURITY INVOKER AS $$
    SELECT COALESCE(SUM(
        l.credited_paise
        - COALESCE((SELECT SUM(r.reserved_paise) FROM business.wallet_reservations r
                    WHERE r.tenant_id = l.tenant_id AND r.lot_id = l.lot_id
                      AND r.state IN ('RESERVED', 'UNKNOWN')), 0)
        - COALESCE((SELECT SUM(r.actual_paise) FROM business.wallet_reservations r
                    WHERE r.tenant_id = l.tenant_id AND r.lot_id = l.lot_id
                      AND r.state = 'SETTLED'), 0)
        - COALESCE((SELECT SUM(e.amount_paise) FROM business.wallet_entries e
                    WHERE e.tenant_id = l.tenant_id AND e.lot_id = l.lot_id
                      AND e.entry_kind = 'EXPIRE'), 0)
    ), 0)::BIGINT
    FROM business.wallet_lots l
    WHERE l.tenant_id = p_tenant AND l.account_id = p_account
      AND l.valid_from <= p_at AND l.valid_until > p_at;
$$;
RESET ROLE;

SET LOCAL ROLE bp_owner;
REVOKE CREATE ON SCHEMA business FROM wbe_owner;
RESET ROLE;

REVOKE ALL ON business.wallet_accounts, business.wallet_lots, business.wallet_entries,
    business.wallet_reservations FROM PUBLIC, business_app;
GRANT SELECT, INSERT ON business.wallet_accounts, business.wallet_lots,
    business.wallet_entries TO wbe_app;
GRANT SELECT, INSERT ON business.wallet_reservations TO wbe_app;
GRANT UPDATE (state, actual_paise, resolved_at) ON business.wallet_reservations TO wbe_app;
REVOKE ALL ON FUNCTION business.wallet_available(UUID, UUID, TIMESTAMPTZ) FROM PUBLIC, business_app;
GRANT EXECUTE ON FUNCTION business.wallet_available(UUID, UUID, TIMESTAMPTZ) TO wbe_app;
REVOKE ALL ON FUNCTION business.guard_wallet_append_only(), business.guard_wallet_reservation()
    FROM PUBLIC, business_app;
DO $owner$
BEGIN
    IF current_setting('waooaw.wc136_wallet_wbe_owner_granted', true) = 'true' THEN
        EXECUTE format('REVOKE wbe_owner FROM %I', session_user);
    END IF;
    IF current_setting('waooaw.wc136_wallet_bp_owner_granted', true) = 'true' THEN
        EXECUTE format('REVOKE bp_owner FROM %I', session_user);
    END IF;
END
$owner$;
COMMIT;
