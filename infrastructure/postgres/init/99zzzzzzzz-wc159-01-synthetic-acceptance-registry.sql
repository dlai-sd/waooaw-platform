-- Implements: architecture/reference/acceptance/customer-journey-acceptance-architecture.md §5 and adr/ADR-055-synthetic-acceptance-tenants-and-evidence.md decision 4
-- Constitutional basis: C-059 (Implementation Traceability)
-- WC-159: server-side registry of synthetic acceptance subjects. A subject is registered only through the internal
-- acceptance-provisioner route (default off, Demo and UAT only). A tenant created at first login by a registered
-- Keycloak (iss, sub) is labelled synthetic in synthetic_tenants. The label reduces side effects only (business
-- metrics, outbound delivery); it never grants authority. Nothing here is ever deleted by the application: the
-- application role has no DELETE grant, and the only UPDATE is deactivated_at on a registration.
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '30s';
SET LOCAL ROLE bp_owner;

CREATE TABLE IF NOT EXISTS business.synthetic_subjects (
    registration_id UUID PRIMARY KEY,
    issuer TEXT NOT NULL CHECK (length(issuer) BETWEEN 1 AND 256),
    subject TEXT NOT NULL CHECK (length(subject) BETWEEN 8 AND 128),
    run_id TEXT NOT NULL CHECK (run_id ~ '^[A-Za-z0-9._-]{8,64}$'),
    registered_by TEXT NOT NULL CHECK (length(registered_by) BETWEEN 1 AND 128),
    registered_at TIMESTAMPTZ NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    deactivated_at TIMESTAMPTZ,
    CONSTRAINT synthetic_subjects_window CHECK (expires_at > registered_at)
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_synthetic_subjects_actor
    ON business.synthetic_subjects (issuer, subject);
CREATE INDEX IF NOT EXISTS idx_synthetic_subjects_run
    ON business.synthetic_subjects (run_id);

CREATE TABLE IF NOT EXISTS business.synthetic_sandbox_recipients (
    recipient_id UUID PRIMARY KEY,
    run_id TEXT NOT NULL CHECK (run_id ~ '^[A-Za-z0-9._-]{8,64}$'),
    recipient_digest TEXT NOT NULL CHECK (recipient_digest ~ '^[0-9a-f]{64}$'),
    registered_by TEXT NOT NULL CHECK (length(registered_by) BETWEEN 1 AND 128),
    registered_at TIMESTAMPTZ NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    deactivated_at TIMESTAMPTZ,
    CONSTRAINT synthetic_sandbox_recipients_window CHECK (expires_at > registered_at)
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_synthetic_sandbox_recipients_run_digest
    ON business.synthetic_sandbox_recipients (run_id, recipient_digest);

CREATE TABLE IF NOT EXISTS business.synthetic_tenants (
    tenant_id UUID PRIMARY KEY,
    run_id TEXT NOT NULL CHECK (run_id ~ '^[A-Za-z0-9._-]{8,64}$'),
    registration_id UUID NOT NULL,
    labelled_at TIMESTAMPTZ NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_synthetic_tenants_run
    ON business.synthetic_tenants (run_id);

CREATE TABLE IF NOT EXISTS business.synthetic_delivery_suppressions (
    suppression_id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    run_id TEXT NOT NULL CHECK (run_id ~ '^[A-Za-z0-9._-]{8,64}$'),
    outbox_id UUID NOT NULL,
    attempt_number INTEGER NOT NULL CHECK (attempt_number >= 0),
    recipient_digest TEXT NOT NULL CHECK (recipient_digest ~ '^[0-9a-f]{64}$'),
    reason TEXT NOT NULL CHECK (reason IN ('RECIPIENT_NOT_SANDBOX')),
    suppressed_at TIMESTAMPTZ NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_synthetic_delivery_suppressions_attempt
    ON business.synthetic_delivery_suppressions (outbox_id, attempt_number);
CREATE INDEX IF NOT EXISTS idx_synthetic_delivery_suppressions_tenant
    ON business.synthetic_delivery_suppressions (tenant_id, suppressed_at);

REVOKE ALL ON business.synthetic_subjects, business.synthetic_sandbox_recipients,
    business.synthetic_tenants, business.synthetic_delivery_suppressions FROM PUBLIC;
GRANT SELECT, INSERT ON business.synthetic_subjects, business.synthetic_sandbox_recipients,
    business.synthetic_tenants, business.synthetic_delivery_suppressions TO business_app;
GRANT UPDATE (deactivated_at) ON business.synthetic_subjects, business.synthetic_sandbox_recipients
    TO business_app;

COMMIT;
