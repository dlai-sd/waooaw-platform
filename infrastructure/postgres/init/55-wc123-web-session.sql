-- Implements: CSA-AUTH-001 Sections 12.3-12.6; WC-123 AUTH-WC-02
-- Constitutional basis: C-023, C-026, C-059, C-063, C-080

BEGIN;

CREATE SCHEMA IF NOT EXISTS web_session;
REVOKE ALL ON SCHEMA web_session FROM PUBLIC;

DO $roles$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'web_session_operations') THEN
        CREATE ROLE web_session_operations
            NOLOGIN NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE NOINHERIT;
    END IF;
END
$roles$;

GRANT CREATE ON SCHEMA web_session TO web_session_operations;

CREATE TABLE IF NOT EXISTS web_session.user_generations (
    global_user_id UUID PRIMARY KEY,
    generation BIGINT NOT NULL DEFAULT 1 CHECK (generation > 0),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    last_revocation_reason VARCHAR(64) COLLATE "C",
    last_revocation_correlation UUID,
    CONSTRAINT user_generations_reason_nonempty
        CHECK (last_revocation_reason IS NULL OR length(last_revocation_reason) > 0)
);

CREATE TABLE IF NOT EXISTS web_session.session_families (
    family_id UUID PRIMARY KEY,
    issuer VARCHAR(256) COLLATE "C" NOT NULL CHECK (length(issuer) > 0),
    subject VARCHAR(256) COLLATE "C" NOT NULL CHECK (length(subject) > 0),
    client_id VARCHAR(256) COLLATE "C" NOT NULL CHECK (length(client_id) > 0),
    global_user_id UUID NOT NULL,
    generation BIGINT NOT NULL CHECK (generation > 0),
    assurance_class VARCHAR(32) COLLATE "C" NOT NULL CHECK (length(assurance_class) > 0),
    authenticated_at TIMESTAMPTZ NOT NULL,
    active_membership_id UUID,
    sid_digest_key_version VARCHAR(64) COLLATE "C",
    sid_digest BYTEA,
    token_envelope_key_version VARCHAR(64) COLLATE "C",
    token_envelope BYTEA,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    idle_expires_at TIMESTAMPTZ NOT NULL,
    absolute_expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ,
    erased_at TIMESTAMPTZ,
    refresh_version BIGINT NOT NULL DEFAULT 1 CHECK (refresh_version > 0),
    refresh_lease_owner UUID,
    refresh_lease_expires_at TIMESTAMPTZ,
    state VARCHAR(16) COLLATE "C" NOT NULL DEFAULT 'ACTIVE',
    schema_version INTEGER NOT NULL DEFAULT 1 CHECK (schema_version = 1),
    deploy_version VARCHAR(64) COLLATE "C" NOT NULL CHECK (length(deploy_version) > 0),
    revocation_reason VARCHAR(64) COLLATE "C",
    revocation_correlation UUID,
    CONSTRAINT session_families_user_generation_fk
        FOREIGN KEY (global_user_id) REFERENCES web_session.user_generations(global_user_id)
        ON DELETE RESTRICT,
    CONSTRAINT session_families_state_check
        CHECK (state IN ('ACTIVE', 'REVOKED', 'EXPIRED', 'ERASED')),
    CONSTRAINT session_families_expiry_check
        CHECK (
            absolute_expires_at > created_at
            AND idle_expires_at > created_at
            AND idle_expires_at <= absolute_expires_at
        ),
    CONSTRAINT session_families_sid_check
        CHECK (
            (sid_digest IS NULL AND sid_digest_key_version IS NULL)
            OR (
                sid_digest IS NOT NULL
                AND octet_length(sid_digest) = 32
                AND sid_digest_key_version IS NOT NULL
                AND length(sid_digest_key_version) > 0
            )
        ),
    CONSTRAINT session_families_envelope_state_check
        CHECK (
            (
                state = 'ACTIVE'
                AND token_envelope IS NOT NULL
                AND octet_length(token_envelope) > 0
                AND token_envelope_key_version IS NOT NULL
                AND length(token_envelope_key_version) > 0
                AND revoked_at IS NULL
                AND erased_at IS NULL
            )
            OR (
                state <> 'ACTIVE'
                AND token_envelope IS NULL
                AND token_envelope_key_version IS NULL
                AND refresh_lease_owner IS NULL
                AND refresh_lease_expires_at IS NULL
                AND erased_at IS NOT NULL
            )
        ),
    CONSTRAINT session_families_lease_check
        CHECK (
            (refresh_lease_owner IS NULL) = (refresh_lease_expires_at IS NULL)
        ),
    CONSTRAINT session_families_reason_nonempty
        CHECK (revocation_reason IS NULL OR length(revocation_reason) > 0)
);

CREATE TABLE IF NOT EXISTS web_session.session_handles (
    handle_id UUID PRIMARY KEY,
    family_id UUID NOT NULL,
    digest_key_version VARCHAR(64) COLLATE "C" NOT NULL CHECK (length(digest_key_version) > 0),
    handle_digest BYTEA NOT NULL CHECK (octet_length(handle_digest) = 32),
    state VARCHAR(16) COLLATE "C" NOT NULL DEFAULT 'ACTIVE',
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    expires_at TIMESTAMPTZ NOT NULL,
    superseded_at TIMESTAMPTZ,
    revoked_at TIMESTAMPTZ,
    CONSTRAINT session_handles_family_fk
        FOREIGN KEY (family_id) REFERENCES web_session.session_families(family_id)
        ON DELETE RESTRICT,
    CONSTRAINT session_handles_state_check
        CHECK (state IN ('ACTIVE', 'SUPERSEDED', 'REVOKED', 'EXPIRED')),
    CONSTRAINT session_handles_expiry_check CHECK (expires_at > created_at),
    CONSTRAINT session_handles_transition_check
        CHECK (
            (state = 'ACTIVE' AND superseded_at IS NULL AND revoked_at IS NULL)
            OR (state = 'SUPERSEDED' AND superseded_at IS NOT NULL AND revoked_at IS NULL)
            OR (state = 'REVOKED' AND revoked_at IS NOT NULL)
            OR (state = 'EXPIRED' AND revoked_at IS NOT NULL)
        ),
    CONSTRAINT session_handles_digest_unique UNIQUE (digest_key_version, handle_digest)
);

CREATE UNIQUE INDEX IF NOT EXISTS session_handles_one_active_per_family_idx
    ON web_session.session_handles (family_id)
    WHERE state = 'ACTIVE';
CREATE INDEX IF NOT EXISTS session_handles_family_idx
    ON web_session.session_handles (family_id);

CREATE TABLE IF NOT EXISTS web_session.oidc_transactions (
    transaction_id UUID PRIMARY KEY,
    state_digest_key_version VARCHAR(64) COLLATE "C" NOT NULL
        CHECK (length(state_digest_key_version) > 0),
    state_digest BYTEA NOT NULL CHECK (octet_length(state_digest) = 32),
    transaction_envelope_key_version VARCHAR(64) COLLATE "C",
    transaction_envelope BYTEA,
    initiating_browser_digest BYTEA NOT NULL CHECK (octet_length(initiating_browser_digest) = 32),
    provider_class VARCHAR(16) COLLATE "C" NOT NULL
        CHECK (provider_class IN ('GOOGLE', 'FACEBOOK', 'APPLE', 'EMAIL')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    expires_at TIMESTAMPTZ NOT NULL,
    consumed_at TIMESTAMPTZ,
    schema_version INTEGER NOT NULL DEFAULT 1 CHECK (schema_version = 1),
    CONSTRAINT oidc_transactions_expiry_check CHECK (expires_at > created_at),
    CONSTRAINT oidc_transactions_consumption_check
        CHECK (
            (
                consumed_at IS NULL
                AND transaction_envelope_key_version IS NOT NULL
                AND length(transaction_envelope_key_version) > 0
                AND transaction_envelope IS NOT NULL
                AND octet_length(transaction_envelope) > 0
            )
            OR (
                consumed_at IS NOT NULL
                AND transaction_envelope_key_version IS NULL
                AND transaction_envelope IS NULL
            )
        ),
    CONSTRAINT oidc_transactions_state_unique
        UNIQUE (state_digest_key_version, state_digest)
);

CREATE TABLE IF NOT EXISTS web_session.logout_replays (
    issuer VARCHAR(256) COLLATE "C" NOT NULL CHECK (length(issuer) > 0),
    client_id VARCHAR(256) COLLATE "C" NOT NULL CHECK (length(client_id) > 0),
    digest_key_version VARCHAR(64) COLLATE "C" NOT NULL CHECK (length(digest_key_version) > 0),
    jti_digest BYTEA NOT NULL CHECK (octet_length(jti_digest) = 32),
    received_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    expires_at TIMESTAMPTZ NOT NULL,
    CONSTRAINT logout_replays_pk
        PRIMARY KEY (issuer, client_id, digest_key_version, jti_digest),
    CONSTRAINT logout_replays_expiry_check CHECK (expires_at > received_at)
);

ALTER TABLE web_session.user_generations ENABLE ROW LEVEL SECURITY;
ALTER TABLE web_session.user_generations FORCE ROW LEVEL SECURITY;
ALTER TABLE web_session.session_families ENABLE ROW LEVEL SECURITY;
ALTER TABLE web_session.session_families FORCE ROW LEVEL SECURITY;
ALTER TABLE web_session.session_handles ENABLE ROW LEVEL SECURITY;
ALTER TABLE web_session.session_handles FORCE ROW LEVEL SECURITY;
ALTER TABLE web_session.oidc_transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE web_session.oidc_transactions FORCE ROW LEVEL SECURITY;
ALTER TABLE web_session.logout_replays ENABLE ROW LEVEL SECURITY;
ALTER TABLE web_session.logout_replays FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS user_generations_operations_only ON web_session.user_generations;
CREATE POLICY user_generations_operations_only ON web_session.user_generations
    FOR ALL TO web_session_operations USING (TRUE) WITH CHECK (TRUE);
DROP POLICY IF EXISTS session_families_operations_only ON web_session.session_families;
CREATE POLICY session_families_operations_only ON web_session.session_families
    FOR ALL TO web_session_operations USING (TRUE) WITH CHECK (TRUE);
DROP POLICY IF EXISTS session_handles_operations_only ON web_session.session_handles;
CREATE POLICY session_handles_operations_only ON web_session.session_handles
    FOR ALL TO web_session_operations USING (TRUE) WITH CHECK (TRUE);
DROP POLICY IF EXISTS oidc_transactions_operations_only ON web_session.oidc_transactions;
CREATE POLICY oidc_transactions_operations_only ON web_session.oidc_transactions
    FOR ALL TO web_session_operations USING (TRUE) WITH CHECK (TRUE);
DROP POLICY IF EXISTS logout_replays_operations_only ON web_session.logout_replays;
CREATE POLICY logout_replays_operations_only ON web_session.logout_replays
    FOR ALL TO web_session_operations USING (TRUE) WITH CHECK (TRUE);

CREATE OR REPLACE FUNCTION web_session.lookup_session(
    p_digest_key_version VARCHAR(64),
    p_handle_digest BYTEA,
    p_now TIMESTAMPTZ
) RETURNS TABLE (
    family_id UUID,
    handle_id UUID,
    global_user_id UUID,
    assurance_class VARCHAR(32),
    authenticated_at TIMESTAMPTZ,
    active_membership_id UUID,
    token_envelope_key_version VARCHAR(64),
    token_envelope BYTEA,
    refresh_version BIGINT,
    idle_expires_at TIMESTAMPTZ,
    absolute_expires_at TIMESTAMPTZ
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, web_session
AS $function$
BEGIN
    RETURN QUERY
    SELECT sf.family_id,
           sh.handle_id,
           sf.global_user_id,
           sf.assurance_class,
           sf.authenticated_at,
           sf.active_membership_id,
           sf.token_envelope_key_version,
           sf.token_envelope,
           sf.refresh_version,
           sf.idle_expires_at,
           sf.absolute_expires_at
      FROM web_session.session_handles sh
      JOIN web_session.session_families sf ON sf.family_id = sh.family_id
      JOIN web_session.user_generations ug ON ug.global_user_id = sf.global_user_id
     WHERE sh.digest_key_version = p_digest_key_version
       AND sh.handle_digest = p_handle_digest
       AND sh.state = 'ACTIVE'
       AND sh.expires_at > p_now
       AND sf.state = 'ACTIVE'
       AND sf.idle_expires_at > p_now
       AND sf.absolute_expires_at > p_now
       AND sf.generation = ug.generation
     FOR UPDATE OF ug, sf, sh;
END
$function$;

CREATE OR REPLACE FUNCTION web_session.create_session(
    p_family_id UUID,
    p_handle_id UUID,
    p_global_user_id UUID,
    p_issuer VARCHAR(256),
    p_subject VARCHAR(256),
    p_client_id VARCHAR(256),
    p_assurance_class VARCHAR(32),
    p_authenticated_at TIMESTAMPTZ,
    p_sid_digest_key_version VARCHAR(64),
    p_sid_digest BYTEA,
    p_token_envelope_key_version VARCHAR(64),
    p_token_envelope BYTEA,
    p_handle_digest_key_version VARCHAR(64),
    p_handle_digest BYTEA,
    p_idle_expires_at TIMESTAMPTZ,
    p_absolute_expires_at TIMESTAMPTZ,
    p_deploy_version VARCHAR(64)
) RETURNS TABLE (family_id UUID, handle_id UUID, generation BIGINT)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, web_session
AS $function$
DECLARE
    v_generation BIGINT;
BEGIN
    INSERT INTO web_session.user_generations (global_user_id)
    VALUES (p_global_user_id)
    ON CONFLICT (global_user_id) DO NOTHING;

    SELECT ug.generation
      INTO v_generation
      FROM web_session.user_generations ug
     WHERE ug.global_user_id = p_global_user_id
     FOR UPDATE;

    INSERT INTO web_session.session_families (
        family_id, issuer, subject, client_id, global_user_id, generation,
        assurance_class, authenticated_at, sid_digest_key_version, sid_digest,
        token_envelope_key_version, token_envelope, idle_expires_at,
        absolute_expires_at, deploy_version
    ) VALUES (
        p_family_id, p_issuer, p_subject, p_client_id, p_global_user_id, v_generation,
        p_assurance_class, p_authenticated_at, p_sid_digest_key_version, p_sid_digest,
        p_token_envelope_key_version, p_token_envelope, p_idle_expires_at,
        p_absolute_expires_at, p_deploy_version
    );

    INSERT INTO web_session.session_handles (
        handle_id, family_id, digest_key_version, handle_digest, expires_at
    ) VALUES (
        p_handle_id, p_family_id, p_handle_digest_key_version, p_handle_digest,
        LEAST(p_idle_expires_at, p_absolute_expires_at)
    );

    RETURN QUERY SELECT p_family_id, p_handle_id, v_generation;
END
$function$;

CREATE OR REPLACE FUNCTION web_session.create_oidc_transaction(
    p_transaction_id UUID,
    p_state_digest_key_version VARCHAR(64),
    p_state_digest BYTEA,
    p_transaction_envelope_key_version VARCHAR(64),
    p_transaction_envelope BYTEA,
    p_initiating_browser_digest BYTEA,
    p_provider_class VARCHAR(16),
    p_expires_at TIMESTAMPTZ
) RETURNS UUID
LANGUAGE sql
SECURITY DEFINER
SET search_path = pg_catalog, web_session
AS $function$
    INSERT INTO web_session.oidc_transactions (
        transaction_id,
        state_digest_key_version,
        state_digest,
        transaction_envelope_key_version,
        transaction_envelope,
        initiating_browser_digest,
        provider_class,
        expires_at
    ) VALUES (
        p_transaction_id,
        p_state_digest_key_version,
        p_state_digest,
        p_transaction_envelope_key_version,
        p_transaction_envelope,
        p_initiating_browser_digest,
        p_provider_class,
        p_expires_at
    )
    RETURNING oidc_transactions.transaction_id
$function$;

CREATE OR REPLACE FUNCTION web_session.consume_oidc_transaction(
    p_state_digest_key_version VARCHAR(64),
    p_state_digest BYTEA,
    p_initiating_browser_digest BYTEA,
    p_now TIMESTAMPTZ
) RETURNS TABLE (
    transaction_id UUID,
    transaction_envelope_key_version VARCHAR(64),
    transaction_envelope BYTEA,
    provider_class VARCHAR(16)
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, web_session
AS $function$
DECLARE
    v_transaction web_session.oidc_transactions%ROWTYPE;
BEGIN
    SELECT *
      INTO v_transaction
      FROM web_session.oidc_transactions ot
     WHERE ot.state_digest_key_version = p_state_digest_key_version
       AND ot.state_digest = p_state_digest
       AND ot.initiating_browser_digest = p_initiating_browser_digest
       AND ot.consumed_at IS NULL
       AND ot.expires_at > p_now
     FOR UPDATE;
    IF NOT FOUND THEN
        RETURN;
    END IF;

    UPDATE web_session.oidc_transactions
       SET consumed_at = p_now,
           transaction_envelope_key_version = NULL,
           transaction_envelope = NULL
     WHERE oidc_transactions.transaction_id = v_transaction.transaction_id;

    RETURN QUERY
    SELECT v_transaction.transaction_id,
           v_transaction.transaction_envelope_key_version,
           v_transaction.transaction_envelope,
           v_transaction.provider_class;
END
$function$;

CREATE OR REPLACE FUNCTION web_session.record_logout_replay(
    p_issuer VARCHAR(256),
    p_client_id VARCHAR(256),
    p_digest_key_version VARCHAR(64),
    p_jti_digest BYTEA,
    p_received_at TIMESTAMPTZ,
    p_expires_at TIMESTAMPTZ
) RETURNS BOOLEAN
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, web_session
AS $function$
BEGIN
    INSERT INTO web_session.logout_replays (
        issuer, client_id, digest_key_version, jti_digest, received_at, expires_at
    ) VALUES (
        p_issuer, p_client_id, p_digest_key_version, p_jti_digest,
        p_received_at, p_expires_at
    )
    ON CONFLICT DO NOTHING;
    RETURN FOUND;
END
$function$;

CREATE OR REPLACE FUNCTION web_session.rotate_handle(
    p_family_id UUID,
    p_expected_refresh_version BIGINT,
    p_old_handle_id UUID,
    p_new_handle_id UUID,
    p_new_digest_key_version VARCHAR(64),
    p_new_handle_digest BYTEA,
    p_new_expires_at TIMESTAMPTZ,
    p_active_membership_id UUID DEFAULT NULL
) RETURNS BOOLEAN
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, web_session
AS $function$
BEGIN
    PERFORM 1
      FROM web_session.session_families sf
     WHERE sf.family_id = p_family_id
       AND sf.state = 'ACTIVE'
       AND sf.refresh_version = p_expected_refresh_version
     FOR UPDATE;
    IF NOT FOUND THEN
        RETURN FALSE;
    END IF;

    UPDATE web_session.session_handles
       SET state = 'SUPERSEDED', superseded_at = clock_timestamp()
     WHERE handle_id = p_old_handle_id
       AND family_id = p_family_id
       AND state = 'ACTIVE';
    IF NOT FOUND THEN
        RETURN FALSE;
    END IF;

    INSERT INTO web_session.session_handles (
        handle_id, family_id, digest_key_version, handle_digest, expires_at
    ) VALUES (
        p_new_handle_id, p_family_id, p_new_digest_key_version,
        p_new_handle_digest, p_new_expires_at
    );

    UPDATE web_session.session_families
       SET active_membership_id = p_active_membership_id,
           refresh_version = refresh_version + 1,
           last_seen_at = clock_timestamp()
     WHERE family_id = p_family_id;
    RETURN TRUE;
END
$function$;

CREATE OR REPLACE FUNCTION web_session.acquire_refresh_lease(
    p_family_id UUID,
    p_expected_refresh_version BIGINT,
    p_lease_owner UUID,
    p_lease_seconds INTEGER
) RETURNS BOOLEAN
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, web_session
AS $function$
BEGIN
    IF p_lease_seconds < 1 OR p_lease_seconds > 15 THEN
        RAISE EXCEPTION 'refresh lease must be between 1 and 15 seconds'
            USING ERRCODE = '22023';
    END IF;

    UPDATE web_session.session_families sf
       SET refresh_lease_owner = p_lease_owner,
           refresh_lease_expires_at = clock_timestamp() + make_interval(secs => p_lease_seconds)
     WHERE sf.family_id = p_family_id
       AND sf.state = 'ACTIVE'
       AND sf.refresh_version = p_expected_refresh_version
       AND sf.absolute_expires_at > clock_timestamp()
       AND sf.idle_expires_at > clock_timestamp()
       AND (
           sf.refresh_lease_expires_at IS NULL
           OR sf.refresh_lease_expires_at <= clock_timestamp()
       );
    RETURN FOUND;
END
$function$;

CREATE OR REPLACE FUNCTION web_session.complete_refresh(
    p_family_id UUID,
    p_expected_refresh_version BIGINT,
    p_lease_owner UUID,
    p_token_envelope_key_version VARCHAR(64),
    p_token_envelope BYTEA,
    p_idle_expires_at TIMESTAMPTZ
) RETURNS BOOLEAN
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, web_session
AS $function$
BEGIN
    UPDATE web_session.session_families sf
       SET token_envelope_key_version = p_token_envelope_key_version,
           token_envelope = p_token_envelope,
           idle_expires_at = LEAST(p_idle_expires_at, sf.absolute_expires_at),
           refresh_version = refresh_version + 1,
           refresh_lease_owner = NULL,
           refresh_lease_expires_at = NULL,
           last_seen_at = clock_timestamp()
     WHERE sf.family_id = p_family_id
       AND sf.state = 'ACTIVE'
       AND sf.refresh_version = p_expected_refresh_version
       AND sf.refresh_lease_owner = p_lease_owner
       AND sf.refresh_lease_expires_at > clock_timestamp();
    RETURN FOUND;
END
$function$;

CREATE OR REPLACE FUNCTION web_session.revoke_family(
    p_family_id UUID,
    p_reason VARCHAR(64),
    p_correlation UUID
) RETURNS BOOLEAN
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, web_session
AS $function$
DECLARE
    v_now TIMESTAMPTZ := clock_timestamp();
BEGIN
    PERFORM 1
      FROM web_session.session_families sf
     WHERE sf.family_id = p_family_id
     FOR UPDATE;
    IF NOT FOUND THEN
        RETURN FALSE;
    END IF;

    UPDATE web_session.session_handles
       SET state = 'REVOKED', revoked_at = COALESCE(revoked_at, v_now)
     WHERE family_id = p_family_id AND state = 'ACTIVE';

    UPDATE web_session.session_families
       SET state = 'REVOKED',
           token_envelope = NULL,
           token_envelope_key_version = NULL,
           active_membership_id = NULL,
           refresh_lease_owner = NULL,
           refresh_lease_expires_at = NULL,
           revoked_at = COALESCE(revoked_at, v_now),
           erased_at = COALESCE(erased_at, v_now),
           revocation_reason = p_reason,
           revocation_correlation = p_correlation
     WHERE family_id = p_family_id;
    RETURN TRUE;
END
$function$;

CREATE OR REPLACE FUNCTION web_session.revoke_all(
    p_global_user_id UUID,
    p_reason VARCHAR(64),
    p_correlation UUID
) RETURNS INTEGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, web_session
AS $function$
DECLARE
    v_now TIMESTAMPTZ := clock_timestamp();
    v_count INTEGER;
BEGIN
    INSERT INTO web_session.user_generations (global_user_id)
    VALUES (p_global_user_id)
    ON CONFLICT (global_user_id) DO NOTHING;

    UPDATE web_session.user_generations
       SET generation = generation + 1,
           updated_at = v_now,
           last_revocation_reason = p_reason,
           last_revocation_correlation = p_correlation
     WHERE global_user_id = p_global_user_id;

    PERFORM 1
      FROM web_session.session_families sf
     WHERE sf.global_user_id = p_global_user_id
     ORDER BY sf.family_id
     FOR UPDATE;

    UPDATE web_session.session_handles sh
       SET state = 'REVOKED', revoked_at = COALESCE(sh.revoked_at, v_now)
      FROM web_session.session_families sf
     WHERE sf.global_user_id = p_global_user_id
       AND sh.family_id = sf.family_id
       AND sh.state = 'ACTIVE';

    UPDATE web_session.session_families
       SET state = 'REVOKED',
           token_envelope = NULL,
           token_envelope_key_version = NULL,
           active_membership_id = NULL,
           refresh_lease_owner = NULL,
           refresh_lease_expires_at = NULL,
           revoked_at = COALESCE(revoked_at, v_now),
           erased_at = COALESCE(erased_at, v_now),
           revocation_reason = p_reason,
           revocation_correlation = p_correlation
     WHERE global_user_id = p_global_user_id
       AND state = 'ACTIVE';
    GET DIAGNOSTICS v_count = ROW_COUNT;
    RETURN v_count;
END
$function$;

CREATE OR REPLACE FUNCTION web_session.expire_sessions(p_now TIMESTAMPTZ)
RETURNS INTEGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, web_session
AS $function$
DECLARE
    v_count INTEGER;
BEGIN
    PERFORM 1
      FROM web_session.session_families sf
     WHERE sf.state = 'ACTIVE'
       AND (sf.idle_expires_at <= p_now OR sf.absolute_expires_at <= p_now)
     ORDER BY sf.family_id
     FOR UPDATE;

    UPDATE web_session.session_handles sh
       SET state = 'EXPIRED', revoked_at = COALESCE(sh.revoked_at, p_now)
      FROM web_session.session_families sf
     WHERE sh.family_id = sf.family_id
       AND sf.state = 'ACTIVE'
       AND (sf.idle_expires_at <= p_now OR sf.absolute_expires_at <= p_now)
       AND sh.state = 'ACTIVE';

    UPDATE web_session.session_families
       SET state = 'EXPIRED',
           token_envelope = NULL,
           token_envelope_key_version = NULL,
           active_membership_id = NULL,
           refresh_lease_owner = NULL,
           refresh_lease_expires_at = NULL,
           erased_at = p_now
     WHERE state = 'ACTIVE'
       AND (idle_expires_at <= p_now OR absolute_expires_at <= p_now);
    GET DIAGNOSTICS v_count = ROW_COUNT;
    RETURN v_count;
END
$function$;

CREATE OR REPLACE FUNCTION web_session.list_sessions(
    p_global_user_id UUID,
    p_current_family_id UUID,
    p_now TIMESTAMPTZ
) RETURNS TABLE (
    session_id UUID,
    issued_at TIMESTAMPTZ,
    last_seen_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,
    assurance_level VARCHAR,
    provider VARCHAR,
    device_label VARCHAR,
    current_session BOOLEAN
)
LANGUAGE sql
SECURITY DEFINER
STABLE
SET search_path = pg_catalog, web_session
AS $function$
    SELECT sh.handle_id,
           sf.created_at,
           sf.last_seen_at,
           sf.absolute_expires_at,
           sf.assurance_class,
           'UNKNOWN'::VARCHAR,
           CASE WHEN sf.family_id = p_current_family_id
                THEN 'Current browser'::VARCHAR
                ELSE 'Browser session'::VARCHAR
           END,
           sf.family_id = p_current_family_id
      FROM web_session.session_families sf
      JOIN web_session.session_handles sh
        ON sh.family_id = sf.family_id
       AND sh.state = 'ACTIVE'
     WHERE sf.global_user_id = p_global_user_id
       AND sf.state = 'ACTIVE'
       AND sf.idle_expires_at > p_now
       AND sf.absolute_expires_at > p_now
     ORDER BY sf.last_seen_at DESC, sf.family_id
$function$;

CREATE OR REPLACE FUNCTION web_session.revoke_one(
    p_global_user_id UUID,
    p_handle_id UUID,
    p_reason VARCHAR(64),
    p_correlation UUID
) RETURNS INTEGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, web_session
AS $function$
DECLARE
    v_now TIMESTAMPTZ := clock_timestamp();
    v_family_id UUID;
BEGIN
    SELECT sf.family_id
      INTO v_family_id
      FROM web_session.session_families sf
      JOIN web_session.session_handles selected
        ON selected.family_id = sf.family_id
     WHERE sf.global_user_id = p_global_user_id
       AND selected.handle_id = p_handle_id
     FOR UPDATE OF sf;
    IF NOT FOUND THEN
        RETURN -1;
    END IF;

    UPDATE web_session.session_handles
       SET state = 'REVOKED',
           revoked_at = COALESCE(revoked_at, v_now)
     WHERE family_id = v_family_id
       AND state = 'ACTIVE';

    UPDATE web_session.session_families
       SET state = 'REVOKED',
           token_envelope = NULL,
           token_envelope_key_version = NULL,
           active_membership_id = NULL,
           refresh_lease_owner = NULL,
           refresh_lease_expires_at = NULL,
           revoked_at = COALESCE(revoked_at, v_now),
           erased_at = COALESCE(erased_at, v_now),
           revocation_reason = p_reason,
           revocation_correlation = p_correlation
     WHERE family_id = v_family_id
       AND state = 'ACTIVE';
    RETURN CASE WHEN FOUND THEN 1 ELSE 0 END;
END
$function$;

CREATE OR REPLACE FUNCTION web_session.schema_ready(
    p_schema_version INTEGER,
    p_deploy_version VARCHAR(64)
) RETURNS BOOLEAN
LANGUAGE sql
SECURITY DEFINER
STABLE
SET search_path = pg_catalog, web_session
AS $function$
    SELECT p_schema_version = 1
       AND p_deploy_version = 'wc123-auth-session-v1'
       AND to_regclass('web_session.user_generations') IS NOT NULL
       AND to_regclass('web_session.session_families') IS NOT NULL
       AND to_regclass('web_session.session_handles') IS NOT NULL
       AND to_regclass('web_session.oidc_transactions') IS NOT NULL
       AND to_regclass('web_session.logout_replays') IS NOT NULL
$function$;

CREATE OR REPLACE FUNCTION web_session.key_version_usage(
    p_key_class VARCHAR(32),
    p_key_version VARCHAR(64)
) RETURNS BIGINT
LANGUAGE sql
SECURITY DEFINER
STABLE
SET search_path = pg_catalog, web_session
AS $function$
    SELECT CASE p_key_class
        WHEN 'HANDLE_DIGEST' THEN (
            SELECT count(*) FROM web_session.session_handles
             WHERE digest_key_version = p_key_version
        )
        WHEN 'PROTOCOL_DIGEST' THEN (
            SELECT
                (SELECT count(*) FROM web_session.session_families
                  WHERE sid_digest_key_version = p_key_version)
              + (SELECT count(*) FROM web_session.oidc_transactions
                  WHERE state_digest_key_version = p_key_version)
              + (SELECT count(*) FROM web_session.logout_replays
                  WHERE digest_key_version = p_key_version)
        )
        WHEN 'TOKEN_ENVELOPE' THEN (
            SELECT
                (SELECT count(*) FROM web_session.session_families
                  WHERE token_envelope_key_version = p_key_version)
              + (SELECT count(*) FROM web_session.oidc_transactions
                  WHERE transaction_envelope_key_version = p_key_version)
        )
        ELSE -1
    END
$function$;

CREATE OR REPLACE FUNCTION web_session.cleanup_retained(p_now TIMESTAMPTZ)
RETURNS TABLE (
    oidc_transactions_deleted INTEGER,
    logout_replays_deleted INTEGER,
    handles_deleted INTEGER,
    families_deleted INTEGER,
    user_generations_deleted INTEGER
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, web_session
AS $function$
DECLARE
    v_oidc INTEGER;
    v_logout INTEGER;
    v_handles INTEGER;
    v_families INTEGER;
    v_users INTEGER;
BEGIN
    DELETE FROM web_session.oidc_transactions
     WHERE expires_at <= p_now - INTERVAL '24 hours';
    GET DIAGNOSTICS v_oidc = ROW_COUNT;

    DELETE FROM web_session.logout_replays WHERE expires_at <= p_now;
    GET DIAGNOSTICS v_logout = ROW_COUNT;

    DELETE FROM web_session.session_handles
     WHERE state <> 'ACTIVE'
       AND COALESCE(revoked_at, superseded_at, expires_at) <= p_now - INTERVAL '30 days';
    GET DIAGNOSTICS v_handles = ROW_COUNT;

    DELETE FROM web_session.session_families sf
     WHERE sf.state <> 'ACTIVE'
       AND sf.erased_at <= p_now - INTERVAL '30 days'
       AND NOT EXISTS (
           SELECT 1 FROM web_session.session_handles sh WHERE sh.family_id = sf.family_id
       );
    GET DIAGNOSTICS v_families = ROW_COUNT;

    DELETE FROM web_session.user_generations ug
     WHERE NOT EXISTS (
         SELECT 1 FROM web_session.session_families sf
          WHERE sf.global_user_id = ug.global_user_id
     )
       AND ug.updated_at <= p_now - INTERVAL '30 days';
    GET DIAGNOSTICS v_users = ROW_COUNT;

    RETURN QUERY SELECT v_oidc, v_logout, v_handles, v_families, v_users;
END
$function$;

CREATE OR REPLACE FUNCTION web_session.sanitize_restored_sessions(
    p_reason VARCHAR(64),
    p_correlation UUID,
    p_restore_epoch TIMESTAMPTZ
) RETURNS TABLE (users_advanced INTEGER, families_erased INTEGER, handles_revoked INTEGER)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, web_session
AS $function$
DECLARE
    v_users INTEGER;
    v_families INTEGER;
    v_handles INTEGER;
BEGIN
    UPDATE web_session.user_generations
       SET generation = generation + 1,
           updated_at = p_restore_epoch,
           last_revocation_reason = p_reason,
           last_revocation_correlation = p_correlation;
    GET DIAGNOSTICS v_users = ROW_COUNT;

    UPDATE web_session.session_handles
       SET state = 'REVOKED', revoked_at = COALESCE(revoked_at, p_restore_epoch)
     WHERE state = 'ACTIVE';
    GET DIAGNOSTICS v_handles = ROW_COUNT;

    UPDATE web_session.session_families
       SET state = 'REVOKED',
           token_envelope = NULL,
           token_envelope_key_version = NULL,
           active_membership_id = NULL,
           refresh_lease_owner = NULL,
           refresh_lease_expires_at = NULL,
           revoked_at = COALESCE(revoked_at, p_restore_epoch),
           erased_at = COALESCE(erased_at, p_restore_epoch),
           revocation_reason = p_reason,
           revocation_correlation = p_correlation
     WHERE state = 'ACTIVE';
    GET DIAGNOSTICS v_families = ROW_COUNT;

    DELETE FROM web_session.oidc_transactions WHERE expires_at <= p_restore_epoch;
    RETURN QUERY SELECT v_users, v_families, v_handles;
END
$function$;

CREATE OR REPLACE FUNCTION web_session.apply_backchannel_logout(
    p_issuer VARCHAR(256),
    p_client_id VARCHAR(256),
    p_digest_key_version VARCHAR(64),
    p_jti_digest BYTEA,
    p_sid_digest BYTEA,
    p_subject VARCHAR(256),
    p_received_at TIMESTAMPTZ,
    p_expires_at TIMESTAMPTZ,
    p_correlation UUID
) RETURNS INTEGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, web_session
AS $function$
DECLARE
    v_family_ids UUID[];
    v_count INTEGER;
BEGIN
    IF (p_sid_digest IS NULL) = (p_subject IS NULL) THEN
        RAISE EXCEPTION 'exactly one logout subject is required' USING ERRCODE = '22023';
    END IF;
    IF NOT web_session.record_logout_replay(
        p_issuer,
        p_client_id,
        p_digest_key_version,
        p_jti_digest,
        p_received_at,
        p_expires_at
    ) THEN
        RETURN -1;
    END IF;

    SELECT array_agg(sf.family_id ORDER BY sf.family_id)
      INTO v_family_ids
      FROM web_session.session_families sf
     WHERE sf.issuer = p_issuer
       AND sf.client_id = p_client_id
       AND sf.state = 'ACTIVE'
       AND (
           (p_sid_digest IS NOT NULL
            AND sf.sid_digest_key_version = p_digest_key_version
            AND sf.sid_digest = p_sid_digest)
           OR (p_subject IS NOT NULL AND sf.subject = p_subject)
       );
    IF v_family_ids IS NULL THEN
        RETURN 0;
    END IF;

    PERFORM 1
      FROM web_session.session_families sf
     WHERE sf.family_id = ANY(v_family_ids)
     ORDER BY sf.family_id
     FOR UPDATE;

    UPDATE web_session.user_generations ug
       SET generation = generation + 1,
           updated_at = p_received_at,
           last_revocation_reason = 'BACKCHANNEL_LOGOUT',
           last_revocation_correlation = p_correlation
     WHERE p_subject IS NOT NULL
       AND ug.global_user_id IN (
           SELECT sf.global_user_id
             FROM web_session.session_families sf
            WHERE sf.family_id = ANY(v_family_ids)
       );

    UPDATE web_session.session_handles
       SET state = 'REVOKED',
           revoked_at = COALESCE(revoked_at, p_received_at)
     WHERE family_id = ANY(v_family_ids) AND state = 'ACTIVE';

    UPDATE web_session.session_families
       SET state = 'REVOKED',
           token_envelope = NULL,
           token_envelope_key_version = NULL,
           active_membership_id = NULL,
           refresh_lease_owner = NULL,
           refresh_lease_expires_at = NULL,
           revoked_at = COALESCE(revoked_at, p_received_at),
           erased_at = COALESCE(erased_at, p_received_at),
           revocation_reason = 'BACKCHANNEL_LOGOUT',
           revocation_correlation = p_correlation
     WHERE family_id = ANY(v_family_ids);
    GET DIAGNOSTICS v_count = ROW_COUNT;
    RETURN v_count;
END
$function$;

REVOKE ALL ON ALL TABLES IN SCHEMA web_session FROM PUBLIC;
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA web_session FROM PUBLIC;
REVOKE ALL ON ALL TABLES IN SCHEMA web_session
    FROM business_app, constitutional_app, runtime_app, ai_runtime_app, wbe_app,
         domain_adapter_app, web_session_app;

GRANT USAGE ON SCHEMA web_session TO web_session_operations;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA web_session
    TO web_session_operations;

ALTER FUNCTION web_session.create_session(
    UUID, UUID, UUID, VARCHAR, VARCHAR, VARCHAR, VARCHAR, TIMESTAMPTZ,
    VARCHAR, BYTEA, VARCHAR, BYTEA, VARCHAR, BYTEA, TIMESTAMPTZ, TIMESTAMPTZ, VARCHAR
) OWNER TO web_session_operations;
ALTER FUNCTION web_session.create_oidc_transaction(
    UUID, VARCHAR, BYTEA, VARCHAR, BYTEA, BYTEA, VARCHAR, TIMESTAMPTZ
) OWNER TO web_session_operations;
ALTER FUNCTION web_session.lookup_session(VARCHAR, BYTEA, TIMESTAMPTZ)
    OWNER TO web_session_operations;
ALTER FUNCTION web_session.consume_oidc_transaction(VARCHAR, BYTEA, BYTEA, TIMESTAMPTZ)
    OWNER TO web_session_operations;
ALTER FUNCTION web_session.record_logout_replay(
    VARCHAR, VARCHAR, VARCHAR, BYTEA, TIMESTAMPTZ, TIMESTAMPTZ
) OWNER TO web_session_operations;
ALTER FUNCTION web_session.apply_backchannel_logout(
    VARCHAR, VARCHAR, VARCHAR, BYTEA, BYTEA, VARCHAR, TIMESTAMPTZ, TIMESTAMPTZ, UUID
) OWNER TO web_session_operations;
ALTER FUNCTION web_session.rotate_handle(
    UUID, BIGINT, UUID, UUID, VARCHAR, BYTEA, TIMESTAMPTZ, UUID
) OWNER TO web_session_operations;
ALTER FUNCTION web_session.acquire_refresh_lease(UUID, BIGINT, UUID, INTEGER)
    OWNER TO web_session_operations;
ALTER FUNCTION web_session.complete_refresh(UUID, BIGINT, UUID, VARCHAR, BYTEA, TIMESTAMPTZ)
    OWNER TO web_session_operations;
ALTER FUNCTION web_session.revoke_family(UUID, VARCHAR, UUID)
    OWNER TO web_session_operations;
ALTER FUNCTION web_session.revoke_all(UUID, VARCHAR, UUID)
    OWNER TO web_session_operations;
ALTER FUNCTION web_session.list_sessions(UUID, UUID, TIMESTAMPTZ)
    OWNER TO web_session_operations;
ALTER FUNCTION web_session.revoke_one(UUID, UUID, VARCHAR, UUID)
    OWNER TO web_session_operations;
ALTER FUNCTION web_session.expire_sessions(TIMESTAMPTZ)
    OWNER TO web_session_operations;
ALTER FUNCTION web_session.schema_ready(INTEGER, VARCHAR)
    OWNER TO web_session_operations;
ALTER FUNCTION web_session.key_version_usage(VARCHAR, VARCHAR)
    OWNER TO web_session_operations;
ALTER FUNCTION web_session.sanitize_restored_sessions(VARCHAR, UUID, TIMESTAMPTZ)
    OWNER TO web_session_operations;
ALTER FUNCTION web_session.cleanup_retained(TIMESTAMPTZ)
    OWNER TO web_session_operations;

GRANT USAGE ON SCHEMA web_session TO web_session_app;
GRANT EXECUTE ON FUNCTION web_session.lookup_session(VARCHAR, BYTEA, TIMESTAMPTZ)
    TO web_session_app;
GRANT EXECUTE ON FUNCTION web_session.create_session(
    UUID, UUID, UUID, VARCHAR, VARCHAR, VARCHAR, VARCHAR, TIMESTAMPTZ,
    VARCHAR, BYTEA, VARCHAR, BYTEA, VARCHAR, BYTEA, TIMESTAMPTZ, TIMESTAMPTZ, VARCHAR
) TO web_session_app;
GRANT EXECUTE ON FUNCTION web_session.create_oidc_transaction(
    UUID, VARCHAR, BYTEA, VARCHAR, BYTEA, BYTEA, VARCHAR, TIMESTAMPTZ
) TO web_session_app;
GRANT EXECUTE ON FUNCTION web_session.consume_oidc_transaction(
    VARCHAR, BYTEA, BYTEA, TIMESTAMPTZ
) TO web_session_app;
GRANT EXECUTE ON FUNCTION web_session.record_logout_replay(
    VARCHAR, VARCHAR, VARCHAR, BYTEA, TIMESTAMPTZ, TIMESTAMPTZ
) TO web_session_app;
GRANT EXECUTE ON FUNCTION web_session.apply_backchannel_logout(
    VARCHAR, VARCHAR, VARCHAR, BYTEA, BYTEA, VARCHAR, TIMESTAMPTZ, TIMESTAMPTZ, UUID
) TO web_session_app;
GRANT EXECUTE ON FUNCTION web_session.rotate_handle(
    UUID, BIGINT, UUID, UUID, VARCHAR, BYTEA, TIMESTAMPTZ, UUID
) TO web_session_app;
GRANT EXECUTE ON FUNCTION web_session.acquire_refresh_lease(UUID, BIGINT, UUID, INTEGER)
    TO web_session_app;
GRANT EXECUTE ON FUNCTION web_session.complete_refresh(
    UUID, BIGINT, UUID, VARCHAR, BYTEA, TIMESTAMPTZ
) TO web_session_app;
GRANT EXECUTE ON FUNCTION web_session.revoke_family(UUID, VARCHAR, UUID)
    TO web_session_app;
GRANT EXECUTE ON FUNCTION web_session.revoke_all(UUID, VARCHAR, UUID)
    TO web_session_app;
GRANT EXECUTE ON FUNCTION web_session.list_sessions(UUID, UUID, TIMESTAMPTZ)
    TO web_session_app;
GRANT EXECUTE ON FUNCTION web_session.revoke_one(UUID, UUID, VARCHAR, UUID)
    TO web_session_app;
GRANT EXECUTE ON FUNCTION web_session.schema_ready(INTEGER, VARCHAR)
    TO web_session_app;
GRANT EXECUTE ON FUNCTION web_session.key_version_usage(VARCHAR, VARCHAR)
    TO web_session_app;

REVOKE ALL ON FUNCTION web_session.expire_sessions(TIMESTAMPTZ) FROM web_session_app;
REVOKE ALL ON FUNCTION web_session.sanitize_restored_sessions(VARCHAR, UUID, TIMESTAMPTZ)
    FROM web_session_app;
REVOKE ALL ON FUNCTION web_session.cleanup_retained(TIMESTAMPTZ) FROM web_session_app;

REVOKE CREATE ON SCHEMA web_session FROM web_session_operations;

COMMIT;
