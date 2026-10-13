\set ON_ERROR_STOP on

-- Required psql variables: environment, rollback_evidence_id.
SELECT 1 / CASE
    WHEN :'environment' IN ('demo', 'uat', 'production', 'local')
     AND :'rollback_evidence_id' ~ '^[0-9a-f-]{36}$'
    THEN 1
    ELSE 0
END AS valid_wc120_rollback_parameters;

-- Application configuration must disable callback acceptance and dispatch before this fence.
-- Refuse rollback while in-flight or unknown provider outcomes still require reconciliation.
SELECT 1 / CASE
    WHEN NOT EXISTS (
        SELECT 1
        FROM business.conversation_outbox
        WHERE environment = :'environment'
          AND state IN ('DISPATCHING', 'UNRESOLVED')
    )
    THEN 1
    ELSE 0
END AS provider_outcomes_reconciled;

UPDATE business.conversation_outbox
SET state = 'BLOCKED',
    blocked_reason = 'ROLLBACK_FENCED',
    lease_owner = NULL,
    lease_expires_at = NULL,
    heartbeat_at = NULL,
    updated_at = now()
WHERE environment = :'environment'
  AND state = 'PENDING';

UPDATE business.conversation_migration_watermarks
SET state = CASE WHEN state = 'COMPLETE' THEN state ELSE 'BLOCKED' END,
    updated_at = now()
WHERE environment = :'environment';

INSERT INTO business.conversation_operational_signals (
    environment,
    category,
    code,
    state,
    occurred_at
)
VALUES (
    :'environment',
    'ROLLBACK',
    'APPLICATION_ROLLBACK_FENCE_APPLIED',
    'OPEN',
    now()
);
