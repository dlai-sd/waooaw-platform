-- Implements: work-contracts/WC-172-safe-to-charge-real-customers.md WC172-R002, WC172-R003, WC172-R004, WC172-R005
-- Implements: work-contracts/WC-172-safe-to-charge-real-customers.md WC172-R006, WC172-R007, WC172-R010, WC172-R011
-- Constitutional basis: C-007, C-038, C-059, C-063, C-088, C-089, C-090
-- WC-172: lifecycle rights, GST tax documents, payer and funder, the money gate and money discrepancies.
--   * relationship_period_marks remembers a pause end and a termination date beside the period (D1, D2).
--   * a pause is a FEE_CREDIT billing adjustment applied to the next renewal, never a card refund (D1).
--   * relationship_price_notices holds the 30-day notice and acknowledgement of a catalogue price change (D3, C-090).
--   * tax_documents are immutable, gap-free numbered per series and financial year; a correction is a new
--     document (ADR-022); funder_acceptances and billing_profiles back payer and funder (D5, C-088).
--   * money_gate is the real-money switch (off by default); money_gate_audit records every change; an unresolved
--     money_discrepancies row blocks new charges until the Founder resolves it with evidence.
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
        PERFORM set_config('waooaw.wc172_bp_owner_granted', 'true', true);
    END IF;
    IF NOT pg_has_role(session_user, 'wbe_owner', 'SET') THEN
        EXECUTE format('GRANT wbe_owner TO %I', session_user);
        PERFORM set_config('waooaw.wc172_wbe_owner_granted', 'true', true);
    END IF;
END
$owner$;
SET LOCAL ROLE bp_owner;
GRANT USAGE ON SCHEMA business TO wbe_owner;
GRANT CREATE ON SCHEMA business TO wbe_owner;
RESET ROLE;

SET LOCAL ROLE wbe_owner;

-- Billing adjustments: a pause credit is available until a renewal applies it, in whole or in part.
ALTER TABLE business.billing_adjustments ADD COLUMN IF NOT EXISTS remaining_paise BIGINT;
DO $kinds$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'business.billing_adjustments'::regclass
          AND conname = 'billing_adjustments_adjustment_kind_check'
          AND pg_get_constraintdef(oid) LIKE '%FEE_CREDIT%'
    ) THEN
        ALTER TABLE business.billing_adjustments DROP CONSTRAINT IF EXISTS billing_adjustments_adjustment_kind_check;
        ALTER TABLE business.billing_adjustments ADD CONSTRAINT billing_adjustments_adjustment_kind_check
            CHECK (adjustment_kind IN ('FEE_REFUND', 'UPGRADE_FEE', 'FEE_CREDIT'));
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'business.billing_adjustments'::regclass
          AND conname = 'billing_adjustments_status_check'
          AND pg_get_constraintdef(oid) LIKE '%AVAILABLE%'
    ) THEN
        ALTER TABLE business.billing_adjustments DROP CONSTRAINT IF EXISTS billing_adjustments_status_check;
        ALTER TABLE business.billing_adjustments ADD CONSTRAINT billing_adjustments_status_check
            CHECK (status IN ('PENDING_PROVIDER', 'DISPATCHED', 'FAILED_RETRYABLE', 'NOT_PAYABLE',
                              'ORDER_CREATED', 'COLLECTED', 'AVAILABLE', 'APPLIED'));
    END IF;
END
$kinds$;
CREATE INDEX IF NOT EXISTS billing_adjustments_credit_available
    ON business.billing_adjustments (tenant_id, relationship_id, created_at)
    WHERE adjustment_kind = 'FEE_CREDIT' AND status = 'AVAILABLE';

CREATE TABLE IF NOT EXISTS business.relationship_period_marks (
    tenant_id UUID NOT NULL,
    relationship_id UUID NOT NULL,
    period_start TIMESTAMPTZ NOT NULL,
    pause_ends_at TIMESTAMPTZ,
    terminates_at TIMESTAMPTZ,
    service_failure_evidence_id UUID,
    updated_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (tenant_id, relationship_id, period_start)
);

CREATE TABLE IF NOT EXISTS business.relationship_price_notices (
    notice_id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    relationship_id UUID NOT NULL,
    from_package_version_id UUID NOT NULL,
    to_package_version_id UUID NOT NULL,
    current_price_paise BIGINT NOT NULL CHECK (current_price_paise >= 0),
    new_price_paise BIGINT NOT NULL CHECK (new_price_paise >= 0),
    notified_at TIMESTAMPTZ NOT NULL,
    effective_from TIMESTAMPTZ NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('NOTIFIED', 'ACKNOWLEDGED', 'WITHDRAWN')),
    acknowledged_at TIMESTAMPTZ,
    acknowledged_by TEXT,
    notice_evidence_id UUID NOT NULL,
    CHECK (effective_from >= notified_at),
    CHECK ((status = 'ACKNOWLEDGED') = (acknowledged_at IS NOT NULL)),
    UNIQUE (tenant_id, relationship_id, to_package_version_id)
);

REVOKE ALL ON business.relationship_period_marks, business.relationship_price_notices FROM PUBLIC, business_app;
GRANT SELECT, INSERT, UPDATE ON business.relationship_period_marks, business.relationship_price_notices TO wbe_app;

-- GST identity of the customer a tax document is issued to; the funder of a hire needs one too (C-088).
CREATE TABLE IF NOT EXISTS business.billing_profiles (
    customer_id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    legal_name TEXT NOT NULL CHECK (length(legal_name) BETWEEN 1 AND 200),
    gstin TEXT CHECK (gstin IS NULL OR gstin ~ '^[0-9]{2}[A-Z0-9]{10}[0-9]Z[A-Z0-9]$'),
    state_code CHAR(2) NOT NULL CHECK (state_code ~ '^[0-9]{2}$'),
    address TEXT NOT NULL CHECK (length(address) BETWEEN 1 AND 500),
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS business.funder_acceptances (
    acceptance_id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    relationship_id UUID NOT NULL,
    funder_customer_id UUID NOT NULL REFERENCES business.billing_profiles (customer_id),
    acceptance_evidence_id UUID NOT NULL,
    accepted_at TIMESTAMPTZ NOT NULL,
    UNIQUE (tenant_id, relationship_id, funder_customer_id)
);

CREATE TABLE IF NOT EXISTS business.tax_document_counters (
    series TEXT NOT NULL CHECK (series IN ('INV', 'CN')),
    fiscal_year TEXT NOT NULL CHECK (fiscal_year ~ '^[0-9]{4}-[0-9]{2}$'),
    last_number BIGINT NOT NULL CHECK (last_number >= 0),
    PRIMARY KEY (series, fiscal_year)
);

CREATE TABLE IF NOT EXISTS business.tax_documents (
    document_id UUID PRIMARY KEY,
    document_kind TEXT NOT NULL CHECK (document_kind IN ('TAX_INVOICE', 'CREDIT_NOTE')),
    series TEXT NOT NULL CHECK (series IN ('INV', 'CN')),
    fiscal_year TEXT NOT NULL CHECK (fiscal_year ~ '^[0-9]{4}-[0-9]{2}$'),
    sequence_no BIGINT NOT NULL CHECK (sequence_no >= 1),
    document_number TEXT NOT NULL UNIQUE,
    tenant_id UUID,
    relationship_id UUID,
    payer_customer_id UUID NOT NULL,
    funder_customer_id UUID,
    source_kind TEXT NOT NULL CHECK (source_kind IN ('PAYMENT', 'ADJUSTMENT')),
    source_reference TEXT NOT NULL CHECK (length(source_reference) BETWEEN 1 AND 200),
    original_document_id UUID REFERENCES business.tax_documents (document_id),
    issued_at TIMESTAMPTZ NOT NULL,
    supplier JSONB NOT NULL,
    bill_to JSONB NOT NULL,
    place_of_supply TEXT NOT NULL CHECK (place_of_supply ~ '^[0-9]{2}$'),
    supply_type TEXT NOT NULL CHECK (supply_type IN ('INTRA_STATE', 'INTER_STATE')),
    lines JSONB NOT NULL,
    taxable_paise BIGINT NOT NULL CHECK (taxable_paise >= 0),
    cgst_paise BIGINT NOT NULL CHECK (cgst_paise >= 0),
    sgst_paise BIGINT NOT NULL CHECK (sgst_paise >= 0),
    igst_paise BIGINT NOT NULL CHECK (igst_paise >= 0),
    total_paise BIGINT NOT NULL CHECK (total_paise > 0),
    currency TEXT NOT NULL CHECK (currency = 'INR'),
    body_digest CHAR(64) NOT NULL CHECK (body_digest ~ '^[0-9a-f]{64}$'),
    CHECK (total_paise = taxable_paise + cgst_paise + sgst_paise + igst_paise),
    CHECK ((supply_type = 'INTRA_STATE') = (igst_paise = 0)),
    CHECK ((document_kind = 'CREDIT_NOTE') = (series = 'CN')),
    CHECK ((document_kind = 'CREDIT_NOTE') = (original_document_id IS NOT NULL)),
    CHECK (funder_customer_id IS NULL OR funder_customer_id <> payer_customer_id),
    UNIQUE (series, fiscal_year, sequence_no),
    UNIQUE (document_kind, source_kind, source_reference)
);
CREATE INDEX IF NOT EXISTS tax_documents_by_payer ON business.tax_documents (payer_customer_id, issued_at DESC);
CREATE INDEX IF NOT EXISTS tax_documents_by_tenant ON business.tax_documents (tenant_id, issued_at DESC);
CREATE INDEX IF NOT EXISTS tax_documents_by_relationship
    ON business.tax_documents (tenant_id, relationship_id, issued_at DESC);

CREATE OR REPLACE FUNCTION business.guard_tax_document_change() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'Tax documents are immutable; a correction is a new document'
        USING ERRCODE = '55000';
END;
$$;
CREATE OR REPLACE TRIGGER tax_documents_immutable
BEFORE UPDATE OR DELETE ON business.tax_documents
FOR EACH ROW EXECUTE FUNCTION business.guard_tax_document_change();

CREATE TABLE IF NOT EXISTS business.money_gate (
    gate_key TEXT PRIMARY KEY CHECK (gate_key = 'REAL_MONEY'),
    enabled BOOLEAN NOT NULL DEFAULT FALSE,
    changed_by TEXT NOT NULL,
    changed_at TIMESTAMPTZ NOT NULL,
    reason TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS business.money_gate_audit (
    audit_id UUID PRIMARY KEY,
    enabled BOOLEAN NOT NULL,
    environment TEXT NOT NULL CHECK (environment IN ('demo', 'uat', 'production')),
    changed_by TEXT NOT NULL,
    step_up BOOLEAN NOT NULL,
    reason TEXT NOT NULL,
    changed_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS business.money_discrepancies (
    discrepancy_id UUID PRIMARY KEY,
    kind TEXT NOT NULL CHECK (kind IN (
        'PAYMENT_WITHOUT_INVOICE', 'INVOICE_WITHOUT_PAYMENT', 'AMOUNT_MISMATCH',
        'REFUND_WITHOUT_CREDIT_NOTE', 'CREDIT_NOTE_WITHOUT_REFUND')),
    reference TEXT NOT NULL CHECK (length(reference) BETWEEN 1 AND 200),
    expected_paise BIGINT NOT NULL CHECK (expected_paise >= 0),
    observed_paise BIGINT NOT NULL CHECK (observed_paise >= 0),
    detected_at TIMESTAMPTZ NOT NULL,
    resolved_at TIMESTAMPTZ,
    resolved_by TEXT,
    resolution_evidence_id UUID,
    CHECK ((resolved_at IS NULL) = (resolution_evidence_id IS NULL))
);
CREATE UNIQUE INDEX IF NOT EXISTS money_discrepancies_open
    ON business.money_discrepancies (kind, reference) WHERE resolved_at IS NULL;

CREATE OR REPLACE FUNCTION business.guard_money_audit_change() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'The money gate audit is append-only' USING ERRCODE = '55000';
END;
$$;
CREATE OR REPLACE TRIGGER money_gate_audit_append_only
BEFORE UPDATE OR DELETE ON business.money_gate_audit
FOR EACH ROW EXECUTE FUNCTION business.guard_money_audit_change();

REVOKE ALL ON business.billing_profiles, business.funder_acceptances, business.tax_document_counters,
    business.tax_documents, business.money_gate, business.money_gate_audit, business.money_discrepancies
    FROM PUBLIC, business_app;
GRANT SELECT, INSERT, UPDATE ON business.billing_profiles, business.tax_document_counters, business.money_gate
    TO wbe_app;
GRANT SELECT, INSERT ON business.funder_acceptances, business.tax_documents, business.money_gate_audit,
    business.money_discrepancies TO wbe_app;
GRANT UPDATE (resolved_at, resolved_by, resolution_evidence_id) ON business.money_discrepancies TO wbe_app;
REVOKE ALL ON FUNCTION business.guard_tax_document_change(), business.guard_money_audit_change()
    FROM PUBLIC, business_app;

RESET ROLE;
DO $owner$
BEGIN
    IF current_setting('waooaw.wc172_wbe_owner_granted', true) = 'true' THEN
        EXECUTE format('REVOKE wbe_owner FROM %I', session_user);
    END IF;
    IF current_setting('waooaw.wc172_bp_owner_granted', true) = 'true' THEN
        EXECUTE format('REVOKE bp_owner FROM %I', session_user);
    END IF;
END
$owner$;
COMMIT;
