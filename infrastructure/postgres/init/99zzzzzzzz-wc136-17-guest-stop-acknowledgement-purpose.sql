-- Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C1-02, C1-03
-- Constitutional basis: C-023, C-026, C-059, C-063
-- WC-136 C1-02/C1-03: the guest and relationship STOP acknowledgements are portal-scoped outbox purposes. Like the
-- session limit notice they carry the protected destination on the row, because the recipient is already stopped.
BEGIN;
DO $membership$
BEGIN
    IF NOT pg_has_role(session_user, 'bp_owner', 'SET') THEN
        EXECUTE format('GRANT bp_owner TO %I', session_user);
        PERFORM set_config('waooaw.wc136_stop_ack_granted', 'true', true);
    END IF;
END
$membership$;

ALTER TABLE business.conversation_outbox
    DROP CONSTRAINT IF EXISTS conversation_outbox_scope_check,
    ADD CONSTRAINT conversation_outbox_scope_check CHECK (
        (portal_context_id IS NULL AND relationship_id IS NOT NULL AND conversation_id IS NOT NULL)
        OR (
            portal_context_id IS NOT NULL AND relationship_id IS NULL AND conversation_id IS NULL
            AND purpose IN (
                'WHATSAPP_GUEST_DISCOVERY',
                'WHATSAPP_GUEST_SESSION_LIMIT_NOTICE',
                'WHATSAPP_GUEST_STOP_ACK',
                'WHATSAPP_RELATIONSHIP_STOP_ACK'
            )
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
            purpose IN (
                'WHATSAPP_GUEST_SESSION_LIMIT_NOTICE',
                'WHATSAPP_GUEST_STOP_ACK',
                'WHATSAPP_RELATIONSHIP_STOP_ACK'
            )
            AND protected_recipient_destination IS NOT NULL
            AND portal_context_id IS NOT NULL
            AND relationship_id IS NULL
            AND conversation_id IS NULL
        )
        OR (
            purpose NOT IN (
                'WHATSAPP_GUEST_SESSION_LIMIT_NOTICE',
                'WHATSAPP_GUEST_STOP_ACK',
                'WHATSAPP_RELATIONSHIP_STOP_ACK'
            )
            AND protected_recipient_destination IS NULL
        )
    );

DO $membership$
BEGIN
    IF current_setting('waooaw.wc136_stop_ack_granted', true) = 'true' THEN
        EXECUTE format('REVOKE bp_owner FROM %I', session_user);
    END IF;
END
$membership$;
COMMIT;
