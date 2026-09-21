-- Implements: architecture/reference/data/identity-security-data-contract.md §Logical Event Schema, §Database Controls
-- Constitutional basis: C-002, C-005, C-007, C-027, C-059, C-063

CREATE SCHEMA IF NOT EXISTS institutional;

CREATE TABLE IF NOT EXISTS institutional.identity_security_events (
    event_id          UUID         PRIMARY KEY,
    correlation_id    UUID         NOT NULL,
    source_event_id   VARCHAR(128) NOT NULL,
    actor_ref         VARCHAR(64),
    session_ref       VARCHAR(64),
    environment       VARCHAR(16)  NOT NULL,
    event_type        VARCHAR(48)  NOT NULL,
    provider_class    VARCHAR(16)  NOT NULL,
    outcome           VARCHAR(16)  NOT NULL,
    reason_code       VARCHAR(64)  NOT NULL,
    assurance_class   VARCHAR(32)  NOT NULL,
    source_boundary   VARCHAR(32)  NOT NULL,
    reference_key_version VARCHAR(32) NOT NULL,
    retention_class   VARCHAR(32)  NOT NULL DEFAULT 'SECURITY_400D',
    retain_until      TIMESTAMPTZ  NOT NULL,
    schema_version    INTEGER      NOT NULL DEFAULT 1,
    occurred_at       TIMESTAMPTZ  NOT NULL,
    recorded_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    writer_service    VARCHAR(64)  NOT NULL,
    CONSTRAINT identity_security_events_source_unique UNIQUE (source_boundary, source_event_id),
    CONSTRAINT identity_security_events_environment_check CHECK (environment IN ('local', 'demo', 'uat', 'prod')),
    CONSTRAINT identity_security_events_type_check CHECK (event_type IN (
        'AUTHENTICATION_START', 'PROVIDER_HANDOFF', 'CALLBACK_SUCCESS', 'CALLBACK_FAILURE',
        'SESSION_ESTABLISHMENT', 'REGISTRATION_START', 'REGISTRATION_COMPLETION',
        'REGISTRATION_FAILURE', 'REFRESH_SUCCESS', 'REFRESH_FAILURE', 'AUTHORIZATION_DENIAL',
        'LOGOUT_REQUEST', 'LOGOUT_COMPLETION', 'LOGOUT_FAILURE', 'ACCOUNT_SWITCH',
        'SESSION_EXPIRY', 'SESSION_REVOCATION_ONE', 'SESSION_REVOCATION_ALL'
    )),
    CONSTRAINT identity_security_events_provider_check CHECK (provider_class IN (
        'GOOGLE', 'FACEBOOK', 'APPLE', 'EMAIL', 'INTERNAL', 'UNKNOWN'
    )),
    CONSTRAINT identity_security_events_outcome_check CHECK (outcome IN (
        'ATTEMPTED', 'SUCCEEDED', 'DENIED', 'FAILED', 'CANCELLED'
    )),
    CONSTRAINT identity_security_events_assurance_check CHECK (assurance_class IN (
        'ANONYMOUS', 'AAL1', 'AAL2', 'AAL3', 'UNKNOWN'
    )),
    CONSTRAINT identity_security_events_boundary_check CHECK (source_boundary IN (
        'WEB_APPLICATION', 'BUSINESS_PLATFORM', 'KEYCLOAK', 'IDENTITY_EDGE'
    )),
    CONSTRAINT identity_security_events_key_version_check CHECK (reference_key_version ~ '^[A-Za-z0-9_-]{1,32}$'),
    CONSTRAINT identity_security_events_retention_class_check CHECK (retention_class = 'SECURITY_400D'),
    CONSTRAINT identity_security_events_retention_check CHECK (retain_until >= occurred_at + INTERVAL '400 days'),
    CONSTRAINT identity_security_events_reason_check CHECK (reason_code ~ '^[A-Z][A-Z0-9_]{1,63}$'),
    CONSTRAINT identity_security_events_actor_ref_check CHECK (actor_ref IS NULL OR actor_ref ~ '^[0-9a-f]{64}$'),
    CONSTRAINT identity_security_events_session_ref_check CHECK (session_ref IS NULL OR session_ref ~ '^[0-9a-f]{64}$'),
    CONSTRAINT identity_security_events_schema_check CHECK (schema_version = 1)
);

CREATE INDEX IF NOT EXISTS identity_security_events_correlation_idx
    ON institutional.identity_security_events (correlation_id, occurred_at);
CREATE INDEX IF NOT EXISTS identity_security_events_actor_idx
    ON institutional.identity_security_events (actor_ref, occurred_at)
    WHERE actor_ref IS NOT NULL;

CREATE TABLE IF NOT EXISTS institutional.identity_security_event_legal_holds (
    hold_event_id         UUID         PRIMARY KEY,
    reference_key_version VARCHAR(32) NOT NULL,
    action                VARCHAR(8)   NOT NULL CHECK (action IN ('APPLY', 'RELEASE')),
    authority_ref         VARCHAR(64)  NOT NULL CHECK (authority_ref ~ '^[0-9a-f]{64}$'),
    reason_code           VARCHAR(64)  NOT NULL CHECK (reason_code ~ '^[A-Z][A-Z0-9_]{1,63}$'),
    occurred_at           TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE OR REPLACE VIEW institutional.identity_security_event_key_retirement AS
WITH latest_hold AS (
    SELECT DISTINCT ON (reference_key_version)
        reference_key_version, action
    FROM institutional.identity_security_event_legal_holds
    ORDER BY reference_key_version, occurred_at DESC, hold_event_id DESC
), retention AS (
    SELECT reference_key_version, MAX(retain_until) AS retain_until
    FROM institutional.identity_security_events
    GROUP BY reference_key_version
)
SELECT retention.reference_key_version,
       retention.retain_until,
       COALESCE(latest_hold.action = 'APPLY', FALSE) AS legal_hold_active,
       retention.retain_until <= NOW()
           AND NOT COALESCE(latest_hold.action = 'APPLY', FALSE) AS eligible_for_key_destruction
FROM retention
LEFT JOIN latest_hold USING (reference_key_version);

CREATE OR REPLACE FUNCTION institutional.reject_identity_security_event_mutation()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION 'identity security events are append-only';
END;
$$;

DROP TRIGGER IF EXISTS identity_security_events_no_update_delete
    ON institutional.identity_security_events;
CREATE TRIGGER identity_security_events_no_update_delete
    BEFORE UPDATE OR DELETE ON institutional.identity_security_events
    FOR EACH ROW EXECUTE FUNCTION institutional.reject_identity_security_event_mutation();

DROP TRIGGER IF EXISTS identity_security_events_no_truncate
    ON institutional.identity_security_events;
CREATE TRIGGER identity_security_events_no_truncate
    BEFORE TRUNCATE ON institutional.identity_security_events
    FOR EACH STATEMENT EXECUTE FUNCTION institutional.reject_identity_security_event_mutation();

DROP TRIGGER IF EXISTS identity_security_event_holds_no_update_delete
    ON institutional.identity_security_event_legal_holds;
CREATE TRIGGER identity_security_event_holds_no_update_delete
    BEFORE UPDATE OR DELETE ON institutional.identity_security_event_legal_holds
    FOR EACH ROW EXECUTE FUNCTION institutional.reject_identity_security_event_mutation();

DROP TRIGGER IF EXISTS identity_security_event_holds_no_truncate
    ON institutional.identity_security_event_legal_holds;
CREATE TRIGGER identity_security_event_holds_no_truncate
    BEFORE TRUNCATE ON institutional.identity_security_event_legal_holds
    FOR EACH STATEMENT EXECUTE FUNCTION institutional.reject_identity_security_event_mutation();

REVOKE ALL ON institutional.identity_security_events FROM PUBLIC;
REVOKE ALL ON institutional.identity_security_event_legal_holds,
    institutional.identity_security_event_key_retirement FROM PUBLIC;
GRANT USAGE ON SCHEMA institutional TO business_app;
GRANT INSERT ON institutional.identity_security_events TO business_app;
