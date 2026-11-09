-- WC-134 R008: preserve the activation-limit decision for idempotent inbound replay.

BEGIN;

ALTER TABLE business.whatsapp_guest_traffic_events
    DROP CONSTRAINT IF EXISTS whatsapp_guest_traffic_events_inbound_notice_check,
    ADD CONSTRAINT whatsapp_guest_traffic_events_inbound_notice_check CHECK (
        inbound_notice IS NULL
        OR (event_type = 'INBOUND' AND inbound_notice IN
            ('NONE', 'GUEST_MESSAGE_LIMIT', 'GLOBAL_RATE_LIMIT', 'ACTIVATION_LIMIT'))
        OR (event_type = 'SESSION_LIMIT' AND inbound_notice = 'GUEST_SESSION_LIMIT')
    );

COMMIT;
