-- Implements: architecture/reference/components/identity-boundary.md §8 Canonical Data Contracts
-- constitutional_basis: C-005, C-007, C-026, C-059
-- Mutable identity workflow snapshots with append-only event/idempotency evidence — Migration 20

CREATE SCHEMA IF NOT EXISTS identity;

-- ── Registration workflow ─────────────────────────────────────────────────

-- Registrations intentionally have no tenant RLS: a pre-account actor has no tenant_id.
-- The service binds every read/write to the validated issuer + subject pair; tenant RLS
-- begins on post-account resources such as account_links after completion mints a tenant.

CREATE TABLE IF NOT EXISTS identity.registrations (
    registration_id         UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    actor_subject           VARCHAR(256) NOT NULL,
    state                   VARCHAR(64)  NOT NULL DEFAULT 'Started',
    authentication_path     VARCHAR(32)  NOT NULL,
    provider_label          VARCHAR(40),
    provider_issuer         VARCHAR(256),
    email_verified          BOOLEAN      NOT NULL DEFAULT FALSE,
    mobile_verified         BOOLEAN      NOT NULL DEFAULT FALSE,
    -- match keys are keyed HMAC values; raw PII is never stored here
    email_hmac_key          VARCHAR(128),
    mobile_hmac_key         VARCHAR(128),
    masked_email            VARCHAR(254),
    masked_mobile           VARCHAR(32),
    display_name            VARCHAR(120),
    business_name           VARCHAR(160),
    business_domain         VARCHAR(100),
    language_preference     VARCHAR(5)   NOT NULL DEFAULT 'en',
    account_id              UUID,
    expires_at              TIMESTAMPTZ  NOT NULL DEFAULT NOW() + INTERVAL '2 hours',
    created_at              TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT registrations_state_check CHECK (state IN (
        'Started', 'FederatedIdentityAccepted', 'CredentialIdentityAccepted',
        'WhatsAppIdentityAccepted', 'EmailVerificationRequired',
        'DuplicateResolutionRequired', 'ProfileCompletionRequired',
        'ReadyToComplete', 'Completed', 'Expired', 'Cancelled'
    ))
);

CREATE INDEX IF NOT EXISTS registrations_actor_subject_idx ON identity.registrations (actor_subject);
CREATE INDEX IF NOT EXISTS registrations_state_idx ON identity.registrations (state);

-- State transitions are recorded here as append-only evidence; registrations remain mutable snapshots.
CREATE TABLE IF NOT EXISTS identity.registration_events (
    event_id            UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    registration_id     UUID         NOT NULL REFERENCES identity.registrations (registration_id),
    event_type          VARCHAR(64)  NOT NULL,
    actor_subject       VARCHAR(256) NOT NULL,
    from_state          VARCHAR(64),
    to_state            VARCHAR(64)  NOT NULL,
    correlation_id      UUID         NOT NULL DEFAULT gen_random_uuid(),
    occurred_at         TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS registration_events_reg_idx ON identity.registration_events (registration_id, occurred_at);

-- ── Verification challenges ───────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS identity.verification_challenges (
    challenge_id         UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    registration_id      UUID        REFERENCES identity.registrations (registration_id),  -- NULL for progressive
    actor_subject        VARCHAR(256) NOT NULL,
    purpose              VARCHAR(16)  NOT NULL CHECK (purpose IN ('Email', 'Mobile')),
    state                VARCHAR(16)  NOT NULL DEFAULT 'Pending' CHECK (state IN ('Pending', 'Verified', 'Expired', 'Consumed')),
    code_hmac            VARCHAR(128) NOT NULL,
    masked_destination   VARCHAR(254) NOT NULL,
    expires_at           TIMESTAMPTZ  NOT NULL DEFAULT NOW() + INTERVAL '15 minutes',
    resend_after         TIMESTAMPTZ  NOT NULL DEFAULT NOW() + INTERVAL '1 minute',
    verified_at          TIMESTAMPTZ,
    created_at           TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS verification_challenges_reg_idx ON identity.verification_challenges (registration_id);
CREATE INDEX IF NOT EXISTS verification_challenges_actor_idx ON identity.verification_challenges (actor_subject, state);

-- ── Account links (WhatsApp-to-web) ──────────────────────────────────────

CREATE TABLE IF NOT EXISTS identity.account_links (
    link_id                  UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    actor_subject            VARCHAR(256) NOT NULL,
    tenant_id                UUID         NOT NULL,
    state                    VARCHAR(64)  NOT NULL DEFAULT 'PendingPortalApproval' CHECK (state IN (
        'PendingPortalApproval', 'PendingWhatsAppConfirmation',
        'Linked', 'DuplicateResolutionRequired', 'Expired', 'Cancelled'
    )),
    masked_mobile            VARCHAR(32)  NOT NULL,
    verified_mobile_proof_id UUID         NOT NULL,
    expires_at               TIMESTAMPTZ  NOT NULL DEFAULT NOW() + INTERVAL '15 minutes',
    created_at               TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at               TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS account_links_actor_tenant_idx ON identity.account_links (actor_subject, tenant_id);

ALTER TABLE identity.account_links ENABLE ROW LEVEL SECURITY;
ALTER TABLE identity.account_links FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS account_links_tenant_isolation ON identity.account_links;
CREATE POLICY account_links_tenant_isolation ON identity.account_links
    USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', TRUE), '')::UUID)
    WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', TRUE), '')::UUID);

-- ── Idempotency ledger ────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS identity.idempotency_ledger (
    entry_id          UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    actor_subject     VARCHAR(256) NOT NULL,
    idempotency_key   VARCHAR(36)  NOT NULL,
    operation_family  VARCHAR(64)  NOT NULL,
    canonical_hash    VARCHAR(64)  NOT NULL,
    status_code       INTEGER      NOT NULL,
    response_body     TEXT,
    expires_at        TIMESTAMPTZ  NOT NULL DEFAULT NOW() + INTERVAL '25 hours',
    created_at        TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT idempotency_ledger_actor_key_op_unique UNIQUE (actor_subject, idempotency_key, operation_family)
);
