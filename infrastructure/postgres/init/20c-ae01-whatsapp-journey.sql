-- Implements: ADR-023 and WC058-06 WhatsApp S01-S06 presentation boundary
-- constitutional_basis: C-023, C-026, C-042, C-059, C-063
-- Phone lookup establishes tenant context, so these minimised bootstrap tables are
-- service-private rather than tenant-RLS queried. No raw phone or message text is stored.

CREATE TABLE IF NOT EXISTS business.whatsapp_journey_contacts (
    contact_id                          UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id                           UUID         NOT NULL UNIQUE,
    phone_hmac                          CHAR(64)     NOT NULL UNIQUE,
    opted_in_at                         TIMESTAMPTZ  NOT NULL,
    last_inbound_at                     TIMESTAMPTZ  NOT NULL,
    journey_stage                       VARCHAR(24)  NOT NULL DEFAULT 'DISCOVER',
    pending_medium_risk_confirmation    BOOLEAN      NOT NULL DEFAULT FALSE,
    CONSTRAINT whatsapp_contacts_phone_hmac_check
        CHECK (phone_hmac ~ '^[0-9a-f]{64}$'),
    CONSTRAINT whatsapp_contacts_stage_check
        CHECK (journey_stage IN ('DISCOVER', 'DISCLOSURE', 'INTERVIEW', 'CONTEXT', 'TRIAL', 'CONFIGURE'))
);

CREATE TABLE IF NOT EXISTS business.whatsapp_message_receipts (
    message_id              VARCHAR(128) PRIMARY KEY,
    tenant_id               UUID         NOT NULL,
    session_token_hash      CHAR(64)     NOT NULL,
    session_expires_at      TIMESTAMPTZ  NOT NULL,
    received_at             TIMESTAMPTZ  NOT NULL,
    expires_at              TIMESTAMPTZ  NOT NULL,
    CONSTRAINT whatsapp_message_receipts_tenant_fk
        FOREIGN KEY (tenant_id) REFERENCES business.whatsapp_journey_contacts (tenant_id),
    CONSTRAINT whatsapp_message_receipts_token_hash_check
        CHECK (session_token_hash ~ '^[0-9a-f]{64}$'),
    CONSTRAINT whatsapp_message_receipts_window_check
        CHECK (session_expires_at = received_at + INTERVAL '30 minutes'
            AND expires_at = received_at + INTERVAL '24 hours')
);

CREATE INDEX IF NOT EXISTS idx_whatsapp_contacts_phone_hmac
    ON business.whatsapp_journey_contacts (phone_hmac);
CREATE INDEX IF NOT EXISTS idx_whatsapp_receipts_tenant_time
    ON business.whatsapp_message_receipts (tenant_id, received_at);
CREATE INDEX IF NOT EXISTS idx_whatsapp_receipts_expiry
    ON business.whatsapp_message_receipts (expires_at);

CREATE OR REPLACE FUNCTION business.reject_unexpired_whatsapp_receipt_delete()
RETURNS TRIGGER AS $$
BEGIN
    IF OLD.expires_at > NOW() THEN
        RAISE EXCEPTION 'whatsapp_message_receipts is immutable during its 24-hour deduplication window';
    END IF;
    RETURN OLD;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS whatsapp_message_receipts_no_update ON business.whatsapp_message_receipts;
CREATE TRIGGER whatsapp_message_receipts_no_update
    BEFORE UPDATE ON business.whatsapp_message_receipts
    FOR EACH ROW EXECUTE FUNCTION business.reject_ae01_append_only_mutation();
DROP TRIGGER IF EXISTS whatsapp_message_receipts_no_delete ON business.whatsapp_message_receipts;
CREATE TRIGGER whatsapp_message_receipts_no_delete
    BEFORE DELETE ON business.whatsapp_message_receipts
    FOR EACH ROW EXECUTE FUNCTION business.reject_unexpired_whatsapp_receipt_delete();

GRANT SELECT, INSERT, UPDATE ON business.whatsapp_journey_contacts TO business_app;
GRANT SELECT, INSERT ON business.whatsapp_message_receipts TO business_app;