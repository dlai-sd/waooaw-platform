-- Implements: work-contracts/WC-170-real-agent-work-end-to-end.md WC170-R009
-- Constitutional basis: C-059, C-063, C-088, C-089
-- WC-170: the external-spend chain, sandbox and test mode only. A SpendAuthorization is created only for one exact
-- approved and scope-confirmed artifact version; a spend item holds one reservation on the existing wallet ledger (no
-- second ledger) and is charged only on verified provider evidence; the provider's figure is kept as an observation
-- with its reference; a reconciliation result is MATCHED, WITHIN_TOLERANCE or DISCREPANCY and an unresolved
-- DISCREPANCY blocks new spend for that relationship. WBE tables carry no row-level security and are closed to
-- business_app, like the rest of the wallet.
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '30s';
SET LOCAL ROLE bp_owner;

CREATE TABLE IF NOT EXISTS business.spend_authorizations (
    authorization_id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    relationship_id UUID NOT NULL,
    artifact_id UUID NOT NULL,
    artifact_digest CHAR(64) NOT NULL CHECK (artifact_digest ~ '^[0-9a-f]{64}$'),
    approval_evidence_id UUID NOT NULL,
    scope_evidence_id UUID NOT NULL,
    ceiling_paise BIGINT NOT NULL CHECK (ceiling_paise > 0),
    reserved_paise BIGINT NOT NULL DEFAULT 0 CHECK (reserved_paise >= 0),
    currency TEXT NOT NULL CHECK (currency = 'INR'),
    funding_account TEXT NOT NULL CHECK (funding_account IN ('PLATFORM', 'CUSTOMER')),
    window_start TIMESTAMPTZ NOT NULL,
    window_end TIMESTAMPTZ NOT NULL,
    provider_mode TEXT NOT NULL CHECK (provider_mode = 'SANDBOX'),
    status TEXT NOT NULL CHECK (status IN ('ACTIVE', 'CLOSED')),
    idempotency_key UUID NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    CHECK (window_end > window_start),
    CHECK (approval_evidence_id <> scope_evidence_id),
    CHECK (reserved_paise <= ceiling_paise),
    UNIQUE (tenant_id, idempotency_key)
);

CREATE TABLE IF NOT EXISTS business.spend_items (
    authorization_id UUID NOT NULL REFERENCES business.spend_authorizations (authorization_id),
    work_item_id UUID NOT NULL,
    tenant_id UUID NOT NULL,
    relationship_id UUID NOT NULL,
    reservation_id UUID NOT NULL,
    reserved_paise BIGINT NOT NULL CHECK (reserved_paise > 0),
    state TEXT NOT NULL CHECK (state IN ('RESERVED', 'UNCERTAIN', 'CHARGED', 'RELEASED')),
    charged_paise BIGINT CHECK (charged_paise IS NULL OR charged_paise > 0),
    provider_reference TEXT CHECK (provider_reference IS NULL OR length(provider_reference) BETWEEN 1 AND 200),
    created_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (authorization_id, work_item_id),
    CHECK ((state = 'CHARGED') = (charged_paise IS NOT NULL AND provider_reference IS NOT NULL))
);
CREATE INDEX IF NOT EXISTS spend_items_relationship_idx ON business.spend_items (tenant_id, relationship_id);

CREATE TABLE IF NOT EXISTS business.spend_observations (
    observation_id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    authorization_id UUID NOT NULL,
    work_item_id UUID NOT NULL,
    observed_paise BIGINT NOT NULL CHECK (observed_paise >= 0),
    provider_reference TEXT NOT NULL CHECK (length(provider_reference) BETWEEN 1 AND 200),
    observed_at TIMESTAMPTZ NOT NULL,
    UNIQUE (authorization_id, work_item_id, provider_reference)
);

CREATE TABLE IF NOT EXISTS business.spend_reconciliation_results (
    result_id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    relationship_id UUID NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('MATCHED', 'WITHIN_TOLERANCE', 'DISCREPANCY')),
    charged_paise BIGINT NOT NULL CHECK (charged_paise >= 0),
    observed_paise BIGINT NOT NULL CHECK (observed_paise >= 0),
    difference_paise BIGINT NOT NULL,
    unresolved_items INTEGER NOT NULL CHECK (unresolved_items >= 0),
    created_at TIMESTAMPTZ NOT NULL,
    resolved_at TIMESTAMPTZ,
    resolution_evidence_id UUID,
    CHECK ((resolved_at IS NULL) = (resolution_evidence_id IS NULL))
);
CREATE INDEX IF NOT EXISTS spend_reconciliation_relationship_idx
    ON business.spend_reconciliation_results (tenant_id, relationship_id, created_at DESC);

REVOKE ALL ON business.spend_authorizations, business.spend_items, business.spend_observations,
    business.spend_reconciliation_results FROM PUBLIC, business_app;
GRANT SELECT, INSERT ON business.spend_authorizations, business.spend_items, business.spend_observations,
    business.spend_reconciliation_results TO wbe_app;
GRANT UPDATE (reserved_paise, status) ON business.spend_authorizations TO wbe_app;
GRANT UPDATE (state, charged_paise, provider_reference) ON business.spend_items TO wbe_app;
GRANT UPDATE (resolved_at, resolution_evidence_id) ON business.spend_reconciliation_results TO wbe_app;

COMMIT;
