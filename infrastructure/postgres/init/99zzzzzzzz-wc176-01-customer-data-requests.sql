-- wc177-apply: update
-- Implements: work-contracts/WC-176-customer-journeys-registration-trial-hire-and-pages.md WC176-R006
-- Constitutional basis: C-023, C-026, C-059, C-063, C-078
-- A customer's request for a copy of their data, or for their account to be erased. The platform records the request and
-- the Founder sees it as an operator task; nothing is erased by this table. Only one request of each kind can be open for
-- a customer at a time, and a repeated submission with the same idempotency key returns the same request. The customer
-- sees only their own requests; the operator reads and resolves requests only when the server sets the operator marker.
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '30s';
SET LOCAL ROLE bp_owner;

CREATE TABLE IF NOT EXISTS business.customer_data_requests (
    request_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    kind VARCHAR(16) NOT NULL CHECK (kind IN ('EXPORT', 'ERASURE')),
    state VARCHAR(16) NOT NULL DEFAULT 'RECEIVED' CHECK (state IN ('RECEIVED', 'COMPLETED', 'DECLINED')),
    idempotency_key UUID NOT NULL,
    requested_by_actor_hash VARCHAR(64) NOT NULL,
    requested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    resolved_by_subject VARCHAR(128),
    resolved_at TIMESTAMPTZ,
    resolution_note VARCHAR(500),
    UNIQUE (tenant_id, idempotency_key),
    CHECK ((state = 'RECEIVED') = (resolved_at IS NULL))
);
ALTER TABLE business.customer_data_requests OWNER TO bp_owner;

CREATE UNIQUE INDEX IF NOT EXISTS customer_data_requests_one_open_per_kind_idx
    ON business.customer_data_requests (tenant_id, kind) WHERE state = 'RECEIVED';
CREATE INDEX IF NOT EXISTS customer_data_requests_open_idx
    ON business.customer_data_requests (requested_at) WHERE state = 'RECEIVED';

ALTER TABLE business.customer_data_requests ENABLE ROW LEVEL SECURITY;
ALTER TABLE business.customer_data_requests FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS customer_data_requests_owner_scope ON business.customer_data_requests;
CREATE POLICY customer_data_requests_owner_scope ON business.customer_data_requests
    TO business_app
    USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
    WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);

DROP POLICY IF EXISTS customer_data_requests_operator_scope ON business.customer_data_requests;
CREATE POLICY customer_data_requests_operator_scope ON business.customer_data_requests
    TO business_app
    USING (current_setting('app.data_requests_operator', true) = 'on')
    WITH CHECK (current_setting('app.data_requests_operator', true) = 'on');

REVOKE ALL ON business.customer_data_requests FROM PUBLIC, business_app;
GRANT SELECT, INSERT, UPDATE ON business.customer_data_requests TO business_app;

COMMIT;
