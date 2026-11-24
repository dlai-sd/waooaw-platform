-- Implements: work-contracts/WC-169-paid-hire-and-connected-accounts.md WC169-R003
-- Constitutional basis: C-009, C-023, C-063, C-065
-- WC-169: four WC-120 conversation tables gave no privilege to business_app, so any conversation story that reads or writes
-- them would fail with "42501 permission denied" the way provider_configs did (WC-168). Each table already has a forced
-- per-tenant row level security policy (36-wc120-conversation-whatsapp.sql); only the grants are missing.
-- Each grant below follows the code path that uses the table, nothing wider, and nothing is deleted by the application:
--   conversation_context_observations  read, insert, and flip the current flag when a customer corrects a value
--   conversation_context_summaries     read, and invalidate (current, invalidation_reason, invalidated_at); no code inserts
--   conversation_data_right_requests   read and insert (idempotent replay reads first); never updated by the application
--   whatsapp_media                     read, insert, and the quarantine lifecycle columns
-- conversation_migration_watermarks is mapped but no application code path reads or writes it, so it gets no grant.
-- Every statement is idempotent.
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '30s';
SET LOCAL ROLE bp_owner;

DO $guard$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM (VALUES
            ('business.conversation_context_observations'),
            ('business.conversation_context_summaries'),
            ('business.conversation_data_right_requests'),
            ('business.whatsapp_media')
        ) AS required(name)
        LEFT JOIN pg_catalog.pg_class AS relation
            ON relation.oid = pg_catalog.to_regclass(required.name)
        WHERE relation.oid IS NULL
           OR NOT relation.relrowsecurity
           OR NOT relation.relforcerowsecurity
    ) THEN
        RAISE EXCEPTION 'Conversation context and media grants require forced row-level security';
    END IF;
END
$guard$;

GRANT SELECT, INSERT ON business.conversation_context_observations TO business_app;
GRANT UPDATE (current) ON business.conversation_context_observations TO business_app;

GRANT SELECT ON business.conversation_context_summaries TO business_app;
GRANT UPDATE (current, invalidation_reason, invalidated_at)
ON business.conversation_context_summaries TO business_app;

GRANT SELECT, INSERT ON business.conversation_data_right_requests TO business_app;

GRANT SELECT, INSERT ON business.whatsapp_media TO business_app;
GRANT UPDATE (
    state, payload_reference, scanner_engine_version, scanner_policy_version, scanner_signature_version,
    scanner_signature_published_at, verdict_digest, derivative_payload_references_json, legal_hold,
    terminal_at, delete_after
)
ON business.whatsapp_media TO business_app;

COMMIT;
