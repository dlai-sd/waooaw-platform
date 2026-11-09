-- Implements: work-contracts/WC-134-whatsapp-demo-complete-rollout-work-component.md WC134-R008
-- Constitutional basis: C-023, C-026, C-059, C-063

BEGIN;

ALTER TABLE business.whatsapp_guest_traffic_events
    DROP CONSTRAINT IF EXISTS whatsapp_guest_traffic_events_event_type_check,
    ADD CONSTRAINT whatsapp_guest_traffic_events_event_type_check
        CHECK (event_type IN ('INBOUND', 'OUTBOUND', 'SESSION', 'SESSION_LIMIT'));

ALTER TABLE business.conversation_outbox
    ADD COLUMN IF NOT EXISTS protected_recipient_destination VARCHAR(512);
ALTER TABLE business.conversation_outbox
    DROP CONSTRAINT IF EXISTS conversation_outbox_scope_check,
    ADD CONSTRAINT conversation_outbox_scope_check CHECK (
        (portal_context_id IS NULL AND relationship_id IS NOT NULL AND conversation_id IS NOT NULL)
        OR (
            portal_context_id IS NOT NULL AND relationship_id IS NULL AND conversation_id IS NULL
            AND purpose IN ('WHATSAPP_GUEST_DISCOVERY', 'WHATSAPP_GUEST_SESSION_LIMIT_NOTICE')
            AND template_name IS NULL
            AND template_version IS NULL
            AND template_locale IS NULL
            AND template_category IS NULL
        )
    );
ALTER TABLE business.conversation_outbox
    DROP CONSTRAINT IF EXISTS conversation_outbox_session_limit_destination_check,
    ADD CONSTRAINT conversation_outbox_session_limit_destination_check CHECK (
        (
            purpose = 'WHATSAPP_GUEST_SESSION_LIMIT_NOTICE'
            AND protected_recipient_destination IS NOT NULL
            AND portal_context_id IS NOT NULL
            AND relationship_id IS NULL
            AND conversation_id IS NULL
        )
        OR (
            purpose <> 'WHATSAPP_GUEST_SESSION_LIMIT_NOTICE'
            AND protected_recipient_destination IS NULL
        )
    );

COMMIT;
