\set ON_ERROR_STOP on

-- Read-only verification for an isolated, non-routable restore.
SELECT 1 / CASE
    WHEN current_setting('transaction_read_only') = 'on' THEN 1
    ELSE 0
END AS read_only_restore;

SELECT migration_id, environment, owner, state, batch_size
FROM business.conversation_migration_watermarks
WHERE state NOT IN ('VERIFIED', 'COMPLETE')
ORDER BY migration_id, environment, owner;

SELECT environment, tenant_id, relationship_id, COUNT(*) AS duplicate_count
FROM business.conversations
GROUP BY environment, tenant_id, relationship_id
HAVING COUNT(*) > 1;

SELECT environment, tenant_id, relationship_id, sequence, COUNT(*) AS duplicate_count
FROM business.conversation_messages
GROUP BY environment, tenant_id, relationship_id, sequence
HAVING COUNT(*) > 1;

SELECT environment, tenant_id, relationship_id, operation_family, idempotency_key, COUNT(*) AS duplicate_count
FROM business.conversation_outbox
GROUP BY environment, tenant_id, relationship_id, operation_family, idempotency_key
HAVING COUNT(*) > 1;

SELECT environment, provider, app_binding_digest, event_identity, COUNT(*) AS duplicate_count
FROM business.provider_event_claims
GROUP BY environment, provider, app_binding_digest, event_identity
HAVING COUNT(*) > 1;

SELECT schemaname, tablename, rowsecurity
FROM pg_catalog.pg_tables
WHERE schemaname = 'business'
  AND tablename IN (
      'conversation_outbox',
      'conversation_context_observations',
      'conversation_context_summaries',
      'conversation_delivery_observations',
      'conversation_data_right_requests',
      'whatsapp_media',
      'relationship_emergency_stop_latches'
  )
  AND rowsecurity IS NOT TRUE;

SELECT 1 / CASE
    WHEN NOT EXISTS (
        SELECT 1
        FROM business.conversation_migration_watermarks
        WHERE state NOT IN ('VERIFIED', 'COMPLETE')
    )
    AND NOT EXISTS (
        SELECT 1
        FROM business.conversations
        GROUP BY environment, tenant_id, relationship_id
        HAVING COUNT(*) > 1
    )
    AND NOT EXISTS (
        SELECT 1
        FROM business.conversation_messages
        GROUP BY environment, tenant_id, relationship_id, sequence
        HAVING COUNT(*) > 1
    )
    AND NOT EXISTS (
        SELECT 1
        FROM business.conversation_outbox
        GROUP BY environment, tenant_id, relationship_id, operation_family, idempotency_key
        HAVING COUNT(*) > 1
    )
    AND NOT EXISTS (
        SELECT 1
        FROM business.provider_event_claims
        GROUP BY environment, provider, app_binding_digest, event_identity
        HAVING COUNT(*) > 1
    )
    AND NOT EXISTS (
        SELECT 1
        FROM pg_catalog.pg_tables
        WHERE schemaname = 'business'
          AND tablename IN (
              'conversation_outbox',
              'conversation_context_observations',
              'conversation_context_summaries',
              'conversation_delivery_observations',
              'conversation_data_right_requests',
              'whatsapp_media',
              'relationship_emergency_stop_latches'
          )
          AND rowsecurity IS NOT TRUE
    )
    THEN 1
    ELSE 0
END AS restore_invariants_valid;
