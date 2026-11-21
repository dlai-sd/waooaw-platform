-- Implements: work-contracts/WC-137-platform-access-and-environment-feature-settings.md WC137-R003, WC137-R004, WC137-R005
-- Constitutional basis: C-009, C-023, C-059, C-063
-- WC-137: staff roles are durable grants, never self-assigned. A signed-in person files an access request,
-- the Founder approves it with a fresh strong sign-in, and the approval becomes a grant. Founder grants
-- (source BOOTSTRAP) come only from the environment's configuration and are re-asserted at every start, so
-- they survive a redeploy, a schema upgrade, a Demo database reset and a fresh database. Every change is
-- appended to an event table that is never updated or deleted by the application.
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '30s';
SET LOCAL ROLE bp_owner;

CREATE TABLE IF NOT EXISTS business.platform_role_grants (
    grant_id UUID PRIMARY KEY,
    email_normalized TEXT NOT NULL
        CHECK (length(email_normalized) BETWEEN 3 AND 254 AND email_normalized = lower(email_normalized)),
    subject TEXT CHECK (subject IS NULL OR length(subject) BETWEEN 8 AND 128),
    role TEXT NOT NULL CHECK (role IN (
        'founder', 'pricing_admin', 'admission_operator', 'validator_operator', 'admission_reviewer',
        'admission_approver', 'platform_activation_authority', 'constitutional_authority',
        'operations_authority', 'lifecycle_authority'
    )),
    source TEXT NOT NULL CHECK (source IN ('BOOTSTRAP', 'APPROVAL')),
    granted_by TEXT NOT NULL CHECK (length(granted_by) BETWEEN 1 AND 254),
    request_id UUID,
    granted_at TIMESTAMPTZ NOT NULL,
    expires_at TIMESTAMPTZ,
    revoked_at TIMESTAMPTZ,
    revoked_by TEXT CHECK (revoked_by IS NULL OR length(revoked_by) BETWEEN 1 AND 254),
    revoke_reason TEXT CHECK (revoke_reason IS NULL OR length(revoke_reason) BETWEEN 1 AND 500),
    -- A Founder is never granted by approval: only the configured root of trust can create that role.
    CONSTRAINT platform_role_grants_founder_is_bootstrap CHECK (role <> 'founder' OR source = 'BOOTSTRAP'),
    CONSTRAINT platform_role_grants_revocation_complete CHECK (
        (revoked_at IS NULL AND revoked_by IS NULL) OR (revoked_at IS NOT NULL AND revoked_by IS NOT NULL)
    )
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_platform_role_grants_active
    ON business.platform_role_grants (email_normalized, role)
    WHERE revoked_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_platform_role_grants_email
    ON business.platform_role_grants (email_normalized);

CREATE TABLE IF NOT EXISTS business.platform_access_requests (
    request_id UUID PRIMARY KEY,
    subject TEXT NOT NULL CHECK (length(subject) BETWEEN 8 AND 128),
    email_normalized TEXT NOT NULL
        CHECK (length(email_normalized) BETWEEN 3 AND 254 AND email_normalized = lower(email_normalized)),
    role TEXT NOT NULL CHECK (role IN (
        'pricing_admin', 'admission_operator', 'validator_operator', 'admission_reviewer',
        'admission_approver', 'platform_activation_authority', 'constitutional_authority',
        'operations_authority', 'lifecycle_authority'
    )),
    justification TEXT NOT NULL CHECK (length(justification) BETWEEN 10 AND 500),
    status TEXT NOT NULL CHECK (status IN ('PENDING', 'APPROVED', 'REJECTED')),
    requested_at TIMESTAMPTZ NOT NULL,
    decided_at TIMESTAMPTZ,
    decided_by TEXT CHECK (decided_by IS NULL OR length(decided_by) BETWEEN 1 AND 254),
    decision_reason TEXT CHECK (decision_reason IS NULL OR length(decision_reason) BETWEEN 1 AND 500),
    CONSTRAINT platform_access_requests_decision_complete CHECK (
        (status = 'PENDING' AND decided_at IS NULL AND decided_by IS NULL)
        OR (status <> 'PENDING' AND decided_at IS NOT NULL AND decided_by IS NOT NULL)
    )
);
-- One open request per person; the abuse limit counts earlier requests by requested_at.
CREATE UNIQUE INDEX IF NOT EXISTS idx_platform_access_requests_one_pending
    ON business.platform_access_requests (subject)
    WHERE status = 'PENDING';
CREATE INDEX IF NOT EXISTS idx_platform_access_requests_status
    ON business.platform_access_requests (status, requested_at);
CREATE INDEX IF NOT EXISTS idx_platform_access_requests_subject
    ON business.platform_access_requests (subject, requested_at);

CREATE TABLE IF NOT EXISTS business.platform_access_events (
    event_id UUID PRIMARY KEY,
    event_type TEXT NOT NULL CHECK (event_type IN (
        'FOUNDER_BOOTSTRAPPED', 'FOUNDER_SUBJECT_BOUND', 'FOUNDER_REMOVED_BY_CONFIGURATION',
        'REQUESTED', 'APPROVED', 'REJECTED', 'REVOKED'
    )),
    actor TEXT NOT NULL CHECK (length(actor) BETWEEN 1 AND 254),
    target_email TEXT CHECK (target_email IS NULL OR length(target_email) BETWEEN 3 AND 254),
    role TEXT CHECK (role IS NULL OR length(role) BETWEEN 1 AND 64),
    reference_id UUID,
    occurred_at TIMESTAMPTZ NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_platform_access_events_time
    ON business.platform_access_events (occurred_at);

REVOKE ALL ON business.platform_role_grants, business.platform_access_requests, business.platform_access_events
    FROM PUBLIC;
GRANT SELECT, INSERT ON business.platform_role_grants TO business_app;
GRANT UPDATE (subject, revoked_at, revoked_by, revoke_reason) ON business.platform_role_grants TO business_app;
GRANT SELECT, INSERT ON business.platform_access_requests TO business_app;
GRANT UPDATE (status, decided_at, decided_by, decision_reason) ON business.platform_access_requests TO business_app;
GRANT SELECT, INSERT ON business.platform_access_events TO business_app;

COMMIT;
