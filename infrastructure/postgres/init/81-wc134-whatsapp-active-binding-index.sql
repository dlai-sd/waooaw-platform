-- Implements: work-contracts/WC-134-requirements.yaml WC134-R002
-- Constitutional basis: C-023, C-026, C-059, C-063

BEGIN;

CREATE INDEX IF NOT EXISTS channel_bindings_active_whatsapp_sender_idx
    ON business.channel_bindings (tenant_id, external_subject_hash)
    WHERE channel = 'WHATSAPP' AND status = 'ACTIVE';

COMMIT;
