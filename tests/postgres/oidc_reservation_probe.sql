-- Post-handoff OIDC provider-start probe: proves the runtime role can reserve and consume an OIDC
-- transaction through the SECURITY DEFINER boundary after 60-wc124-principal-handoff.sql.
-- Regression for Demo Google sign-in 503 (SQLSTATE 42501, 2026-10-29). Leaves no rows behind.
\set ON_ERROR_STOP on

DO $definers$
DECLARE
    v_misowned TEXT;
BEGIN
    SELECT string_agg(p.oid::regprocedure::TEXT || ' owned by ' || pg_get_userbyid(p.proowner), ', ')
      INTO v_misowned
      FROM pg_proc p
      JOIN pg_namespace n ON n.oid = p.pronamespace
     WHERE p.prosecdef
       AND (
           (n.nspname = 'web_session' AND pg_get_userbyid(p.proowner) <> 'web_session_operations')
           OR (n.nspname = 'identity' AND pg_get_userbyid(p.proowner) <> 'identity_resolver_owner')
       );
    IF v_misowned IS NOT NULL THEN
        RAISE EXCEPTION 'SECURITY DEFINER routines lost their RLS-admitted principal: %', v_misowned;
    END IF;
END
$definers$;

BEGIN;
SET LOCAL ROLE web_session_app;
DO $reservation$
DECLARE
    v_consumed INTEGER;
BEGIN
    PERFORM web_session.create_oidc_transaction(
        gen_random_uuid(),
        'probe-v1',
        decode(repeat('a1', 32), 'hex'),
        'probe-v1',
        decode('0102', 'hex'),
        decode(repeat('b2', 32), 'hex'),
        'GOOGLE',
        clock_timestamp() + INTERVAL '10 minutes'
    );
    SELECT count(*)
      INTO v_consumed
      FROM web_session.consume_oidc_transaction(
          'probe-v1',
          decode(repeat('a1', 32), 'hex'),
          decode(repeat('b2', 32), 'hex'),
          clock_timestamp()
      );
    IF v_consumed <> 1 THEN
        RAISE EXCEPTION 'OIDC transaction reservation was not consumable by web_session_app';
    END IF;
END
$reservation$;
ROLLBACK;

SELECT 'oidc-reservation-probe: passed' AS result;
