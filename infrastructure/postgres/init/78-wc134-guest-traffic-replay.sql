-- Implements: work-contracts/WC-134-whatsapp-demo-complete-rollout-work-component.md WC134-R008
-- Constitutional basis: C-023, C-026, C-059, C-063

BEGIN;

ALTER TABLE business.whatsapp_guest_traffic_events
    ADD COLUMN IF NOT EXISTS inbound_notice VARCHAR(32);
ALTER TABLE business.whatsapp_guest_traffic_events
    DROP CONSTRAINT IF EXISTS whatsapp_guest_traffic_events_inbound_notice_check,
    ADD CONSTRAINT whatsapp_guest_traffic_events_inbound_notice_check CHECK (
        inbound_notice IS NULL
        OR (event_type = 'INBOUND' AND inbound_notice IN
            ('NONE', 'GUEST_MESSAGE_LIMIT', 'GLOBAL_RATE_LIMIT', 'ACTIVATION_LIMIT'))
        OR (event_type = 'SESSION_LIMIT' AND inbound_notice = 'GUEST_SESSION_LIMIT')
    );

COMMIT;
