-- Implements: work-contracts/WC-175-demo-registration-trial-hire-and-founder-defects.md WC175-R023, R025
-- Constitutional basis: C-005, C-023, C-026, C-059, C-063
-- The Founder's decision on which professional versions customers may take on Trial or Hire. One row per version, shared
-- by every customer, so it carries no tenant data. Each decision is also written to an append-only history, bound to the
-- digest of the definition that was approved, so the record shows who approved exactly what and when.
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '30s';
SET LOCAL ROLE bp_owner;

CREATE TABLE IF NOT EXISTS business.platform_professional_approvals (
    professional_type_id VARCHAR(100) NOT NULL,
    professional_version VARCHAR(64) NOT NULL,
    state VARCHAR(16) NOT NULL CHECK (state IN ('APPROVED', 'SUSPENDED', 'RETIRED')),
    content_digest VARCHAR(71) NOT NULL CHECK (content_digest ~ '^sha256:[0-9a-f]{64}$'),
    release_revision VARCHAR(128) NOT NULL,
    decided_by_subject VARCHAR(128) NOT NULL,
    decided_at TIMESTAMPTZ NOT NULL,
    reason VARCHAR(500),
    state_version INTEGER NOT NULL CHECK (state_version >= 1),
    PRIMARY KEY (professional_type_id, professional_version)
);
ALTER TABLE business.platform_professional_approvals OWNER TO bp_owner;

CREATE TABLE IF NOT EXISTS business.platform_professional_approval_events (
    event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    professional_type_id VARCHAR(100) NOT NULL,
    professional_version VARCHAR(64) NOT NULL,
    state VARCHAR(16) NOT NULL CHECK (state IN ('APPROVED', 'SUSPENDED', 'RETIRED')),
    content_digest VARCHAR(71) NOT NULL CHECK (content_digest ~ '^sha256:[0-9a-f]{64}$'),
    release_revision VARCHAR(128) NOT NULL,
    decided_by_subject VARCHAR(128) NOT NULL,
    decided_at TIMESTAMPTZ NOT NULL,
    reason VARCHAR(500),
    state_version INTEGER NOT NULL CHECK (state_version >= 1),
    UNIQUE (professional_type_id, professional_version, state_version)
);
ALTER TABLE business.platform_professional_approval_events OWNER TO bp_owner;

CREATE OR REPLACE FUNCTION business.guard_platform_professional_approval_events()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $guard$
BEGIN
    RAISE EXCEPTION 'platform professional approval history is append-only';
END
$guard$;
ALTER FUNCTION business.guard_platform_professional_approval_events() OWNER TO bp_owner;

CREATE OR REPLACE TRIGGER platform_professional_approval_events_append_only
BEFORE UPDATE OR DELETE ON business.platform_professional_approval_events
FOR EACH ROW EXECUTE FUNCTION business.guard_platform_professional_approval_events();

REVOKE ALL ON business.platform_professional_approvals FROM PUBLIC, business_app;
GRANT SELECT, INSERT, UPDATE ON business.platform_professional_approvals TO business_app;
REVOKE ALL ON business.platform_professional_approval_events FROM PUBLIC, business_app;
GRANT SELECT, INSERT ON business.platform_professional_approval_events TO business_app;

COMMIT;
