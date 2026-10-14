-- WC-123 AUTH-WC-02 executable PostgreSQL contract.
\set ON_ERROR_STOP on

DO $assertions$
DECLARE
    v_boolean BOOLEAN;
    v_count INTEGER;
BEGIN
    SELECT count(*) = 5
      INTO v_boolean
      FROM pg_class c
      JOIN pg_namespace n ON n.oid = c.relnamespace
     WHERE n.nspname = 'web_session' AND c.relkind = 'r';
    IF NOT v_boolean THEN
        RAISE EXCEPTION 'web_session must contain exactly five relations';
    END IF;

    SELECT bool_and(p.proowner = r.oid)
      INTO v_boolean
      FROM pg_proc p
      JOIN pg_namespace n ON n.oid = p.pronamespace
      JOIN pg_roles r ON r.rolname = 'web_session_operations'
     WHERE n.nspname = 'web_session';
    IF NOT COALESCE(v_boolean, FALSE) THEN
        RAISE EXCEPTION 'every web_session function must be operation-owner owned';
    END IF;

    IF has_table_privilege('web_session_app', 'web_session.session_families', 'SELECT')
       OR has_table_privilege('business_app', 'web_session.session_families', 'SELECT') THEN
        RAISE EXCEPTION 'runtime or Business Platform received forbidden session-table access';
    END IF;

    SELECT count(*)
      INTO v_count
      FROM information_schema.role_routine_grants
     WHERE grantee = 'web_session_app'
       AND routine_schema = 'web_session';
    IF v_count < 7 THEN
        RAISE EXCEPTION 'Web runtime is missing required function execution grants';
    END IF;
END
$assertions$;

SET ROLE web_session_app;

DO $lifecycle$
DECLARE
    v_created RECORD;
    v_protocol RECORD;
    v_result BOOLEAN;
    v_count INTEGER;
    v_logout INTEGER;
    v_revoke INTEGER;
BEGIN
    IF NOT web_session.schema_ready(1, 'wc123-auth-session-v1') THEN
        RAISE EXCEPTION 'known schema and deploy version must be ready';
    END IF;
    IF web_session.schema_ready(2, 'wc123-auth-session-v1')
       OR web_session.schema_ready(1, 'wc123-unknown-v2') THEN
        RAISE EXCEPTION 'unknown schema or deploy version must fail closed';
    END IF;

    PERFORM web_session.create_oidc_transaction(
        '10000000-0000-0000-0000-000000000010',
        'protocol-v1',
        decode(repeat('44', 32), 'hex'),
        'envelope-v1',
        decode('0506', 'hex'),
        decode(repeat('55', 32), 'hex'),
        'GOOGLE',
        clock_timestamp() + INTERVAL '10 minutes'
    );
    SELECT *
      INTO v_protocol
      FROM web_session.consume_oidc_transaction(
        'protocol-v1',
        decode(repeat('44', 32), 'hex'),
        decode(repeat('55', 32), 'hex'),
        clock_timestamp()
      );
    IF v_protocol.transaction_id <> '10000000-0000-0000-0000-000000000010' THEN
        RAISE EXCEPTION 'OIDC transaction was not consumed exactly once';
    END IF;
    SELECT count(*)
      INTO v_count
      FROM web_session.consume_oidc_transaction(
        'protocol-v1',
        decode(repeat('44', 32), 'hex'),
        decode(repeat('55', 32), 'hex'),
        clock_timestamp()
      );
    IF v_count <> 0 THEN
        RAISE EXCEPTION 'consumed OIDC transaction replay was accepted';
    END IF;

    v_result := web_session.record_logout_replay(
        'https://identity.test/realms/waooaw',
        'waooaw-web',
        'protocol-v1',
        decode(repeat('66', 32), 'hex'),
        clock_timestamp(),
        clock_timestamp() + INTERVAL '24 hours'
    );
    IF NOT v_result THEN
        RAISE EXCEPTION 'first logout replay identifier was not recorded';
    END IF;
    v_result := web_session.record_logout_replay(
        'https://identity.test/realms/waooaw',
        'waooaw-web',
        'protocol-v1',
        decode(repeat('66', 32), 'hex'),
        clock_timestamp(),
        clock_timestamp() + INTERVAL '24 hours'
    );
    IF v_result THEN
        RAISE EXCEPTION 'duplicate logout replay identifier was accepted';
    END IF;

    SELECT *
      INTO v_created
      FROM web_session.create_session(
        '10000000-0000-0000-0000-000000000001',
        '10000000-0000-0000-0000-000000000002',
        '10000000-0000-0000-0000-000000000003',
        'https://identity.test/realms/waooaw',
        'subject-1',
        'waooaw-web',
        'AAL2',
        clock_timestamp(),
        'sid-v1',
        decode(repeat('11', 32), 'hex'),
        'envelope-v1',
        decode('0102', 'hex'),
        'handle-v1',
        decode(repeat('22', 32), 'hex'),
        clock_timestamp() + INTERVAL '30 minutes',
        clock_timestamp() + INTERVAL '8 hours',
        'wc123-auth-session-v1'
      );
    IF v_created.generation <> 1 THEN
        RAISE EXCEPTION 'session create did not capture generation one';
    END IF;
    IF web_session.key_version_usage('HANDLE_DIGEST', 'handle-v1') <> 1
       OR web_session.key_version_usage('PROTOCOL_DIGEST', 'protocol-v1') <> 2
       OR web_session.key_version_usage('TOKEN_ENVELOPE', 'envelope-v1') <> 1
       OR web_session.key_version_usage('UNKNOWN', 'v1') <> -1 THEN
        RAISE EXCEPTION 'key-version usage did not block unsafe retirement';
    END IF;
    SELECT count(*)
      INTO v_count
      FROM web_session.lookup_session(
        'handle-v1', decode(repeat('22', 32), 'hex'), clock_timestamp()
      );
    IF v_count <> 1 THEN
        RAISE EXCEPTION 'active handle did not resolve exactly one current session';
    END IF;

    PERFORM web_session.create_session(
        '10000000-0000-0000-0000-000000000021',
        '10000000-0000-0000-0000-000000000022',
        '10000000-0000-0000-0000-000000000023',
        'https://identity.test/realms/waooaw',
        'subject-backchannel',
        'waooaw-web',
        'AAL2',
        clock_timestamp(),
        'sid-v1',
        decode(repeat('71', 32), 'hex'),
        'envelope-backchannel',
        decode('0708', 'hex'),
        'handle-backchannel',
        decode(repeat('72', 32), 'hex'),
        clock_timestamp() + INTERVAL '30 minutes',
        clock_timestamp() + INTERVAL '8 hours',
        'wc123-auth-session-v1'
    );
    v_logout := web_session.apply_backchannel_logout(
        'https://identity.test/realms/waooaw',
        'waooaw-web',
        'sid-v1',
        decode(repeat('73', 32), 'hex'),
        decode(repeat('71', 32), 'hex'),
        NULL,
        clock_timestamp(),
        clock_timestamp() + INTERVAL '10 minutes',
        '10000000-0000-0000-0000-000000000024'
    );
    IF v_logout <> 1 THEN
        RAISE EXCEPTION 'back-channel logout did not revoke the exact sid family';
    END IF;
    v_logout := web_session.apply_backchannel_logout(
        'https://identity.test/realms/waooaw',
        'waooaw-web',
        'sid-v1',
        decode(repeat('73', 32), 'hex'),
        decode(repeat('71', 32), 'hex'),
        NULL,
        clock_timestamp(),
        clock_timestamp() + INTERVAL '10 minutes',
        '10000000-0000-0000-0000-000000000025'
    );
    IF v_logout <> -1 THEN
        RAISE EXCEPTION 'back-channel logout replay was not denied';
    END IF;

    v_result := web_session.acquire_refresh_lease(
        v_created.family_id, 1, '10000000-0000-0000-0000-000000000004', 15
    );
    IF NOT v_result THEN
        RAISE EXCEPTION 'first refresh lease was not acquired';
    END IF;
    v_result := web_session.acquire_refresh_lease(
        v_created.family_id, 1, '10000000-0000-0000-0000-000000000005', 15
    );
    IF v_result THEN
        RAISE EXCEPTION 'second refresh lease contender must lose';
    END IF;

    v_result := web_session.complete_refresh(
        v_created.family_id,
        1,
        '10000000-0000-0000-0000-000000000004',
        'envelope-v1',
        decode('0304', 'hex'),
        clock_timestamp() + INTERVAL '30 minutes'
    );
    IF NOT v_result THEN
        RAISE EXCEPTION 'lease owner could not complete refresh';
    END IF;

    v_result := web_session.rotate_handle(
        v_created.family_id,
        1,
        v_created.handle_id,
        '10000000-0000-0000-0000-000000000006',
        'handle-v1',
        decode(repeat('33', 32), 'hex'),
        clock_timestamp() + INTERVAL '30 minutes',
        NULL
    );
    IF v_result THEN
        RAISE EXCEPTION 'stale refresh version must not rotate a handle';
    END IF;

    v_result := web_session.rotate_handle(
        v_created.family_id,
        2,
        v_created.handle_id,
        '10000000-0000-0000-0000-000000000006',
        'handle-v1',
        decode(repeat('33', 32), 'hex'),
        clock_timestamp() + INTERVAL '30 minutes',
        NULL
    );
    IF NOT v_result THEN
        RAISE EXCEPTION 'current refresh version did not rotate the handle';
    END IF;

    v_result := web_session.revoke_family(
        v_created.family_id,
        'LOGOUT',
        '10000000-0000-0000-0000-000000000007'
    );
    IF NOT v_result THEN
        RAISE EXCEPTION 'session family was not revoked';
    END IF;

    SELECT *
      INTO v_created
      FROM web_session.create_session(
        '10000000-0000-0000-0000-000000000020',
        '10000000-0000-0000-0000-000000000021',
        '10000000-0000-0000-0000-000000000003',
        'https://identity.test/realms/waooaw',
        'subject-1',
        'waooaw-web',
        'AAL2',
        clock_timestamp(),
        NULL,
        NULL,
        'envelope-v1',
        decode('0708', 'hex'),
        'handle-v1',
        decode(repeat('77', 32), 'hex'),
        clock_timestamp() + INTERVAL '30 minutes',
        clock_timestamp() + INTERVAL '8 hours',
        'wc123-auth-session-v1'
      );
    v_count := web_session.revoke_all(
        '10000000-0000-0000-0000-000000000003',
        'LOGOUT_ALL',
        '10000000-0000-0000-0000-000000000022'
    );
    IF v_count <> 1 THEN
        RAISE EXCEPTION 'revoke-all did not revoke exactly the active family';
    END IF;
    SELECT count(*)
      INTO v_count
      FROM web_session.lookup_session(
        'handle-v1', decode(repeat('77', 32), 'hex'), clock_timestamp()
      );
    IF v_count <> 0 THEN
        RAISE EXCEPTION 'generation-advanced session remained resolvable';
    END IF;

    SELECT *
      INTO v_created
      FROM web_session.create_session(
        '10000000-0000-0000-0000-000000000030',
        '10000000-0000-0000-0000-000000000031',
        '10000000-0000-0000-0000-000000000003',
        'https://identity.test/realms/waooaw',
        'subject-1',
        'waooaw-web',
        'AAL2',
        clock_timestamp(),
        NULL,
        NULL,
        'envelope-v1',
        decode('090a', 'hex'),
        'handle-v1',
        decode(repeat('88', 32), 'hex'),
        clock_timestamp() + INTERVAL '30 minutes',
        clock_timestamp() + INTERVAL '8 hours',
        'wc123-auth-session-v1'
      );
    IF v_created.generation <> 2 THEN
        RAISE EXCEPTION 'post-revoke-all create did not capture advanced generation';
    END IF;

    SELECT *
      INTO v_created
      FROM web_session.create_session(
        '10000000-0000-0000-0000-000000000050',
        '10000000-0000-0000-0000-000000000051',
        '10000000-0000-0000-0000-000000000053',
        'https://identity.test/realms/waooaw',
        'subject-management',
        'waooaw-web',
        'AAL2',
        clock_timestamp(),
        NULL,
        NULL,
        'envelope-v1',
        decode('0b0c', 'hex'),
        'handle-v1',
        decode(repeat('99', 32), 'hex'),
        clock_timestamp() + INTERVAL '30 minutes',
        clock_timestamp() + INTERVAL '8 hours',
        'wc123-auth-session-v1'
      );
    SELECT count(*)
      INTO v_count
      FROM web_session.list_sessions(
        '10000000-0000-0000-0000-000000000053',
        v_created.family_id,
        clock_timestamp()
      );
    IF v_count <> 1 THEN
        RAISE EXCEPTION 'session list did not return the exact global user family';
    END IF;
    SELECT count(*)
      INTO v_count
      FROM web_session.list_sessions(
        '10000000-0000-0000-0000-000000000054',
        v_created.family_id,
        clock_timestamp()
      );
    IF v_count <> 0 THEN
        RAISE EXCEPTION 'session list crossed the global user boundary';
    END IF;
    v_revoke := web_session.revoke_one(
        '10000000-0000-0000-0000-000000000054',
        v_created.handle_id,
        'CUSTOMER_REVOKED',
        '10000000-0000-0000-0000-000000000055'
    );
    IF v_revoke <> -1 THEN
        RAISE EXCEPTION 'foreign global user revoked an inaccessible handle';
    END IF;
    v_revoke := web_session.revoke_one(
        '10000000-0000-0000-0000-000000000053',
        v_created.handle_id,
        'CUSTOMER_REVOKED',
        '10000000-0000-0000-0000-000000000056'
    );
    IF v_revoke <> 1 THEN
        RAISE EXCEPTION 'session owner could not revoke the selected handle';
    END IF;
    SELECT count(*)
      INTO v_count
      FROM web_session.lookup_session(
        'handle-v1', decode(repeat('99', 32), 'hex'), clock_timestamp()
      );
    IF v_count <> 0 THEN
        RAISE EXCEPTION 'revoked selected handle remained resolvable';
    END IF;
END
$lifecycle$;

RESET ROLE;

DO $erasure$
DECLARE
    v_restore RECORD;
    v_cleanup RECORD;
BEGIN
    IF NOT EXISTS (
        SELECT 1
          FROM web_session.session_families
         WHERE family_id = '10000000-0000-0000-0000-000000000001'
           AND state = 'REVOKED'
           AND token_envelope IS NULL
           AND token_envelope_key_version IS NULL
           AND refresh_lease_owner IS NULL
           AND refresh_lease_expires_at IS NULL
           AND active_membership_id IS NULL
    ) THEN
        RAISE EXCEPTION 'revocation did not erase session authority';
    END IF;
    IF NOT EXISTS (
        SELECT 1
          FROM web_session.session_families
         WHERE family_id = '10000000-0000-0000-0000-000000000050'
           AND state = 'REVOKED'
           AND token_envelope IS NULL
    ) THEN
        RAISE EXCEPTION 'selected-session revocation did not erase token authority';
    END IF;
    IF EXISTS (
        SELECT 1
          FROM web_session.session_handles
         WHERE family_id = '10000000-0000-0000-0000-000000000001'
           AND state = 'ACTIVE'
    ) THEN
        RAISE EXCEPTION 'revocation left an active handle';
    END IF;

    SELECT *
      INTO v_restore
      FROM web_session.sanitize_restored_sessions(
        'RESTORE_EPOCH',
        '10000000-0000-0000-0000-000000000040',
        clock_timestamp()
      );
    IF v_restore.families_erased <> 1 OR v_restore.handles_revoked <> 1 THEN
        RAISE EXCEPTION 'restore sanitization did not erase the active restored authority';
    END IF;
    IF EXISTS (
        SELECT 1
          FROM web_session.session_families
         WHERE family_id = '10000000-0000-0000-0000-000000000030'
           AND (
               state = 'ACTIVE'
               OR token_envelope IS NOT NULL
               OR refresh_lease_owner IS NOT NULL
           )
    ) THEN
        RAISE EXCEPTION 'restore sanitization resurrected session authority';
    END IF;

    UPDATE web_session.session_handles
       SET revoked_at = clock_timestamp() - INTERVAL '31 days'
     WHERE state IN ('REVOKED', 'EXPIRED');
    UPDATE web_session.session_handles
       SET superseded_at = clock_timestamp() - INTERVAL '31 days'
     WHERE state = 'SUPERSEDED';
    UPDATE web_session.session_families
       SET erased_at = clock_timestamp() - INTERVAL '31 days'
     WHERE state <> 'ACTIVE';
    UPDATE web_session.user_generations
       SET updated_at = clock_timestamp() - INTERVAL '31 days';
    UPDATE web_session.logout_replays
       SET received_at = clock_timestamp() - INTERVAL '25 hours',
           expires_at = clock_timestamp() - INTERVAL '1 second';
    UPDATE web_session.oidc_transactions
       SET created_at = clock_timestamp() - INTERVAL '50 hours',
           expires_at = clock_timestamp() - INTERVAL '25 hours';

    SELECT *
      INTO v_cleanup
      FROM web_session.cleanup_retained(clock_timestamp());
    IF v_cleanup.handles_deleted < 3
       OR v_cleanup.families_deleted < 3
       OR v_cleanup.user_generations_deleted < 2
       OR v_cleanup.logout_replays_deleted < 2
       OR v_cleanup.oidc_transactions_deleted <> 1 THEN
        RAISE EXCEPTION 'retention cleanup did not remove every eligible record class';
    END IF;
    IF web_session.key_version_usage('HANDLE_DIGEST', 'handle-v1') <> 0
       OR web_session.key_version_usage('PROTOCOL_DIGEST', 'protocol-v1') <> 0
       OR web_session.key_version_usage('TOKEN_ENVELOPE', 'envelope-v1') <> 0 THEN
        RAISE EXCEPTION 'retired key versions remained referenced after eligible cleanup';
    END IF;
END
$erasure$;
