-- Implements: architecture/reference/data/identity-security-data-contract.md §Session Projection
-- Constitutional basis: C-001, C-007, C-026, C-059, C-063

CREATE TABLE IF NOT EXISTS business.identity_session_generations (
    account_ref      VARCHAR(64) PRIMARY KEY,
    revoked_before   TIMESTAMPTZ,
    generation       BIGINT      NOT NULL DEFAULT 0,
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT identity_session_generations_account_ref_check CHECK (account_ref ~ '^[0-9a-f]{64}$')
);

CREATE TABLE IF NOT EXISTS business.identity_sessions (
    session_id          UUID         PRIMARY KEY,
    account_ref         VARCHAR(64)  NOT NULL,
    actor_ref           VARCHAR(64)  NOT NULL,
    issued_at           TIMESTAMPTZ  NOT NULL,
    last_seen_at        TIMESTAMPTZ  NOT NULL,
    absolute_expires_at TIMESTAMPTZ  NOT NULL,
    revoked_at          TIMESTAMPTZ,
    assurance_class     VARCHAR(32)  NOT NULL,
    provider_class      VARCHAR(16)  NOT NULL,
    device_label        VARCHAR(40)  NOT NULL,
    revocation_reason   VARCHAR(32),
    CONSTRAINT identity_sessions_account_ref_check CHECK (account_ref ~ '^[0-9a-f]{64}$'),
    CONSTRAINT identity_sessions_actor_ref_check CHECK (actor_ref ~ '^[0-9a-f]{64}$'),
    CONSTRAINT identity_sessions_expiry_check CHECK (absolute_expires_at > issued_at),
    CONSTRAINT identity_sessions_assurance_check CHECK (assurance_class IN ('AAL1', 'AAL2', 'AAL3')),
    CONSTRAINT identity_sessions_provider_check CHECK (provider_class IN ('GOOGLE', 'FACEBOOK', 'APPLE', 'EMAIL', 'UNKNOWN')),
    CONSTRAINT identity_sessions_revocation_check CHECK ((revoked_at IS NULL) = (revocation_reason IS NULL))
);

CREATE INDEX IF NOT EXISTS identity_sessions_account_active_idx
    ON business.identity_sessions (account_ref, last_seen_at DESC)
    WHERE revoked_at IS NULL;

ALTER TABLE business.identity_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE business.identity_sessions FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS identity_sessions_account_isolation ON business.identity_sessions;
CREATE POLICY identity_sessions_account_isolation ON business.identity_sessions
    USING (account_ref = NULLIF(current_setting('app.identity_account_ref', TRUE), ''))
    WITH CHECK (account_ref = NULLIF(current_setting('app.identity_account_ref', TRUE), ''));

ALTER TABLE business.identity_session_generations ENABLE ROW LEVEL SECURITY;
ALTER TABLE business.identity_session_generations FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS identity_session_generations_account_isolation ON business.identity_session_generations;
CREATE POLICY identity_session_generations_account_isolation ON business.identity_session_generations
    USING (account_ref = NULLIF(current_setting('app.identity_account_ref', TRUE), ''))
    WITH CHECK (account_ref = NULLIF(current_setting('app.identity_account_ref', TRUE), ''));

REVOKE ALL ON business.identity_sessions, business.identity_session_generations FROM PUBLIC;
GRANT USAGE ON SCHEMA business TO business_app;
GRANT SELECT, INSERT, UPDATE ON business.identity_sessions, business.identity_session_generations TO business_app;
