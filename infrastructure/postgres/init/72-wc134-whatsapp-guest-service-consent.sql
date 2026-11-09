-- Implements: work-contracts/WC-134-whatsapp-demo-complete-rollout-work-component.md WC134-R003
-- Constitutional basis: C-023, C-026, C-039, C-042, C-059, C-063

BEGIN;

ALTER TABLE business.whatsapp_guest_sessions
    ADD COLUMN IF NOT EXISTS service_consent_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS service_consent_message_id VARCHAR(128),
    ADD COLUMN IF NOT EXISTS service_consent_evidence_id UUID,
    ADD COLUMN IF NOT EXISTS service_consent_notice_queued_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS service_consent_notice_message_id UUID,
    ADD COLUMN IF NOT EXISTS service_consent_notice_version VARCHAR(32);

ALTER TABLE business.whatsapp_guest_sessions
    DROP CONSTRAINT IF EXISTS whatsapp_guest_sessions_service_consent_check,
    ADD CONSTRAINT whatsapp_guest_sessions_service_consent_check CHECK (
        (
            service_consent_notice_queued_at IS NULL
            AND service_consent_notice_message_id IS NULL
            AND service_consent_notice_version IS NULL
            AND service_consent_at IS NULL
            AND service_consent_message_id IS NULL
            AND service_consent_evidence_id IS NULL
        )
        OR (
            service_consent_notice_queued_at IS NOT NULL
            AND service_consent_notice_message_id IS NOT NULL
            AND service_consent_notice_message_id <> '00000000-0000-0000-0000-000000000000'::UUID
            AND service_consent_notice_version IS NOT NULL
            AND service_consent_notice_version <> ''
            AND (
                (
                    service_consent_at IS NULL
                    AND service_consent_message_id IS NULL
                    AND service_consent_evidence_id IS NULL
                )
                OR (
                    service_consent_at IS NOT NULL
                    AND service_consent_message_id IS NOT NULL
                    AND service_consent_message_id <> ''
                    AND service_consent_evidence_id IS NOT NULL
                    AND service_consent_evidence_id <> '00000000-0000-0000-0000-000000000000'::UUID
                )
            )
        )
    );

COMMIT;
