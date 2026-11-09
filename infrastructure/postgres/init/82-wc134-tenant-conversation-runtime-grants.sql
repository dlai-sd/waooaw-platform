-- Implements: work-contracts/WC-134-requirements.yaml WC134-R002, WC134-R009
-- Constitutional basis: C-023, C-026, C-059, C-063

BEGIN;

DO $guard$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM (VALUES
            ('business.conversation_outbox'),
            ('business.conversation_delivery_observations'),
            ('business.relationship_emergency_stop_latches')
        ) AS required(name)
        LEFT JOIN pg_catalog.pg_class AS relation
            ON relation.oid = pg_catalog.to_regclass(required.name)
        WHERE relation.oid IS NULL
           OR NOT relation.relrowsecurity
           OR NOT relation.relforcerowsecurity
    ) THEN
        RAISE EXCEPTION 'Tenant-scoped conversation runtime grants require forced row-level security';
    END IF;
END
$guard$;

CREATE UNIQUE INDEX IF NOT EXISTS conversation_messages_delivery_scope_unique
ON business.conversation_messages (environment, tenant_id, relationship_id, message_id);
CREATE UNIQUE INDEX IF NOT EXISTS conversations_outbox_scope_unique
ON business.conversations (environment, tenant_id, relationship_id, conversation_id);

DO $constraint$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_catalog.pg_constraint
        WHERE conrelid = 'business.conversation_delivery_observations'::regclass
          AND conname = 'conversation_delivery_message_scope_fk'
    ) THEN
        ALTER TABLE business.conversation_delivery_observations
        ADD CONSTRAINT conversation_delivery_message_scope_fk
        FOREIGN KEY (environment, tenant_id, relationship_id, message_id)
        REFERENCES business.conversation_messages (environment, tenant_id, relationship_id, message_id);
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_catalog.pg_constraint
        WHERE conrelid = 'business.conversation_outbox'::regclass
          AND conname = 'conversation_outbox_conversation_scope_fk'
    ) THEN
        ALTER TABLE business.conversation_outbox
        ADD CONSTRAINT conversation_outbox_conversation_scope_fk
        FOREIGN KEY (environment, tenant_id, relationship_id, conversation_id)
        REFERENCES business.conversations (environment, tenant_id, relationship_id, conversation_id);
    END IF;
END
$constraint$;

GRANT SELECT, INSERT, UPDATE ON business.conversation_outbox TO business_app;
REVOKE DELETE ON business.conversation_outbox FROM business_app;
GRANT SELECT, INSERT ON business.relationship_emergency_stop_latches TO business_app;
REVOKE UPDATE ON business.relationship_emergency_stop_latches FROM business_app;
REVOKE DELETE ON business.relationship_emergency_stop_latches FROM business_app;
REVOKE UPDATE (
    latch_id, environment, tenant_id, relationship_id, stopped_by_participant_id,
    correlation_id, state, evidence_id, latched_at, evidence_confirmed_at
)
ON business.relationship_emergency_stop_latches FROM business_app;
GRANT UPDATE (state, evidence_id, evidence_confirmed_at)
ON business.relationship_emergency_stop_latches TO business_app;
GRANT SELECT, INSERT ON business.conversation_delivery_observations TO business_app;
REVOKE UPDATE, DELETE ON business.conversation_delivery_observations FROM business_app;

COMMIT;
