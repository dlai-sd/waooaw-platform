\set ON_ERROR_STOP on

-- Required psql variables: environment, batch_size.
SELECT 1 / CASE
    WHEN :'environment' IN ('demo', 'uat', 'production', 'local')
     AND :'batch_size'::INTEGER BETWEEN 1 AND 1000
    THEN 1
    ELSE 0
END AS valid_wc120_parameters;

INSERT INTO business.conversation_migration_watermarks (
    migration_id,
    environment,
    owner,
    last_primary_key,
    batch_size,
    state
)
VALUES ('WC120-CONVERSATIONS', :'environment', 'BUSINESS_PLATFORM', '', :'batch_size', 'RUNNING')
ON CONFLICT (migration_id, environment, owner) DO NOTHING;

WITH batch AS (
    SELECT conversation_id
    FROM business.conversations
    WHERE environment = 'legacy'
      AND conversation_id::TEXT > (
          SELECT last_primary_key
          FROM business.conversation_migration_watermarks
          WHERE migration_id = 'WC120-CONVERSATIONS'
            AND environment = :'environment'
            AND owner = 'BUSINESS_PLATFORM'
      )
    ORDER BY conversation_id
    LIMIT :'batch_size'
),
updated AS (
    UPDATE business.conversations AS target
    SET environment = :'environment'
    FROM batch
    WHERE target.conversation_id = batch.conversation_id
    RETURNING target.conversation_id
)
UPDATE business.conversation_migration_watermarks
SET last_primary_key = COALESCE((SELECT MAX(conversation_id)::TEXT FROM updated), last_primary_key),
    state = CASE WHEN (SELECT COUNT(*) FROM updated) = 0 THEN 'COMPLETE' ELSE 'RUNNING' END,
    updated_at = now()
WHERE migration_id = 'WC120-CONVERSATIONS'
  AND environment = :'environment'
  AND owner = 'BUSINESS_PLATFORM';

INSERT INTO business.conversation_migration_watermarks (
    migration_id,
    environment,
    owner,
    last_primary_key,
    batch_size,
    state
)
VALUES ('WC120-MESSAGES', :'environment', 'BUSINESS_PLATFORM', '', :'batch_size', 'RUNNING')
ON CONFLICT (migration_id, environment, owner) DO NOTHING;

WITH batch AS (
    SELECT message_id
    FROM business.conversation_messages
    WHERE environment = 'legacy'
      AND message_id::TEXT > (
          SELECT last_primary_key
          FROM business.conversation_migration_watermarks
          WHERE migration_id = 'WC120-MESSAGES'
            AND environment = :'environment'
            AND owner = 'BUSINESS_PLATFORM'
      )
    ORDER BY message_id
    LIMIT :'batch_size'
),
updated AS (
    UPDATE business.conversation_messages AS target
    SET environment = :'environment',
        interaction_context_json = CASE
            WHEN target.interaction_context_json = '{}'::JSONB THEN jsonb_build_object(
                'contextId', target.message_id,
                'schemaVersion', '1.0',
                'relationshipId', target.relationship_id,
                'professionalInstanceId', relationship.agent_instance_id,
                'conversationId', target.conversation_id,
                'phase', 'LEGACY',
                'purpose', 'LEGACY',
                'subjectType', 'EMPLOYMENT_RELATIONSHIP',
                'subjectReference', target.relationship_id::TEXT,
                'pendingIntentReference', NULL,
                'decisionSpaceVersion', GREATEST(1, relationship.state_version),
                'planVersion', NULL,
                'profileVersion', NULL,
                'policyVersion', 'legacy-unversioned',
                'locale', 'und',
                'channel', target.channel,
                'assuranceLevel', 'TIER_1',
                'sourceVersions', jsonb_build_array(jsonb_build_object(
                    'sourceType', 'LEGACY_CONVERSATION_CORE',
                    'sourceReference', target.message_id::TEXT,
                    'version', target.schema_version
                )),
                'freshness', 'STALE',
                'resolvedAt', target.accepted_at
            )
            ELSE target.interaction_context_json
        END,
        conversation_policy_json = CASE
            WHEN target.conversation_policy_json = '{}'::JSONB THEN jsonb_build_object(
                'version', 'legacy-unversioned',
                'institutionalPolicyVersion', 'legacy-unversioned',
                'professionalPolicyVersion', COALESCE(
                    relationship.professional_version,
                    'legacy-unversioned'
                ),
                'interactionPolicyVersion', 'legacy-unversioned',
                'customerCommunicationProfileVersion', NULL,
                'vocabularyPolicyVersion', NULL,
                'localeAccessibilityPolicyVersion', NULL,
                'channelRenderingPolicyVersion', 'legacy-unversioned'
            )
            ELSE target.conversation_policy_json
        END
    FROM batch,
         business.employment_relationships AS relationship
    WHERE target.message_id = batch.message_id
      AND relationship.tenant_id = target.tenant_id
      AND relationship.relationship_id = target.relationship_id
    RETURNING target.message_id
)
UPDATE business.conversation_migration_watermarks
SET last_primary_key = COALESCE((SELECT MAX(message_id)::TEXT FROM updated), last_primary_key),
    state = CASE WHEN (SELECT COUNT(*) FROM updated) = 0 THEN 'COMPLETE' ELSE 'RUNNING' END,
    updated_at = now()
WHERE migration_id = 'WC120-MESSAGES'
  AND environment = :'environment'
  AND owner = 'BUSINESS_PLATFORM';
