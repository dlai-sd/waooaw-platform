-- Implements: work-contracts/WC-134-whatsapp-demo-complete-rollout-work-component.md WC134-R001, WC134-R002, WC134-R005
-- Constitutional basis: C-023, C-026, C-039, C-059, C-063
-- Give voluntary WhatsApp visitors BP-owned guest sessions, separate from customer Identity.

BEGIN;

ALTER TABLE business.whatsapp_message_receipts
    ADD COLUMN IF NOT EXISTS contact_id UUID;

DROP TRIGGER IF EXISTS whatsapp_message_receipts_no_update
    ON business.whatsapp_message_receipts;

UPDATE business.whatsapp_message_receipts AS receipt
SET contact_id = contact.contact_id
FROM business.whatsapp_journey_contacts AS contact
WHERE receipt.contact_id IS NULL
  AND receipt.tenant_id = contact.tenant_id;

CREATE OR REPLACE TRIGGER whatsapp_message_receipts_no_update
    BEFORE UPDATE ON business.whatsapp_message_receipts
    FOR EACH ROW EXECUTE FUNCTION business.reject_ae01_append_only_mutation();

ALTER TABLE business.whatsapp_message_receipts
    ALTER COLUMN contact_id SET NOT NULL;

ALTER TABLE business.whatsapp_message_receipts
    DROP CONSTRAINT IF EXISTS whatsapp_message_receipts_tenant_fk;

ALTER TABLE business.whatsapp_journey_contacts
    DROP CONSTRAINT IF EXISTS whatsapp_journey_contacts_tenant_id_key;

ALTER TABLE identity.phone_onboarding
    ADD COLUMN IF NOT EXISTS protected_destination VARCHAR(512);

CREATE TABLE IF NOT EXISTS business.whatsapp_guest_sessions (
    tenant_id UUID NOT NULL,
    binding_digest CHAR(64) NOT NULL CHECK (binding_digest ~ '^[0-9a-f]{64}$'),
    participant_id UUID NOT NULL UNIQUE,
    evidence_id UUID CHECK (evidence_id <> '00000000-0000-0000-0000-000000000000'::UUID),
    protected_destination VARCHAR(512),
    first_observed_at TIMESTAMPTZ NOT NULL,
    admitted_at TIMESTAMPTZ,
    last_inbound_at TIMESTAMPTZ NOT NULL,
    stopped_at TIMESTAMPTZ,
    PRIMARY KEY (tenant_id, binding_digest),
    CHECK ((evidence_id IS NULL) = (admitted_at IS NULL))
);
ALTER TABLE business.whatsapp_guest_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE business.whatsapp_guest_sessions FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS whatsapp_guest_sessions_tenant_isolation
    ON business.whatsapp_guest_sessions;
CREATE POLICY whatsapp_guest_sessions_tenant_isolation
    ON business.whatsapp_guest_sessions
    USING (tenant_id = nullif(current_setting('app.current_tenant_id', TRUE), '')::UUID)
    WITH CHECK (tenant_id = nullif(current_setting('app.current_tenant_id', TRUE), '')::UUID);
GRANT SELECT, INSERT, UPDATE ON business.whatsapp_guest_sessions TO business_app;

INSERT INTO business.whatsapp_guest_sessions
    (tenant_id, binding_digest, participant_id, evidence_id, protected_destination,
     first_observed_at, admitted_at, last_inbound_at, stopped_at)
SELECT tenant_id, binding_digest, participant_id, evidence_id, protected_destination,
       first_observed_at, admitted_at, last_inbound_at, stopped_at
FROM identity.phone_onboarding
ON CONFLICT (tenant_id, binding_digest) DO NOTHING;

UPDATE business.conversation_outbox
SET purpose = 'WHATSAPP_GUEST_DISCOVERY'
WHERE purpose = 'PHONE_ONBOARDING'
  AND portal_context_id IS NOT NULL;
ALTER TABLE business.conversation_outbox
    DROP CONSTRAINT IF EXISTS conversation_outbox_scope_check,
    ADD CONSTRAINT conversation_outbox_scope_check CHECK (
        (portal_context_id IS NULL AND relationship_id IS NOT NULL AND conversation_id IS NOT NULL)
        OR (
            portal_context_id IS NOT NULL AND relationship_id IS NULL AND conversation_id IS NULL
            AND purpose = 'WHATSAPP_GUEST_DISCOVERY' AND template_name IS NULL
            AND template_version IS NULL AND template_locale IS NULL AND template_category IS NULL
        )
    );

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'whatsapp_journey_contacts_tenant_contact_key'
          AND conrelid = 'business.whatsapp_journey_contacts'::regclass
    ) THEN
        ALTER TABLE business.whatsapp_journey_contacts
            ADD CONSTRAINT whatsapp_journey_contacts_tenant_contact_key
            UNIQUE (tenant_id, contact_id);
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'whatsapp_message_receipts_tenant_contact_fk'
          AND conrelid = 'business.whatsapp_message_receipts'::regclass
    ) THEN
        ALTER TABLE business.whatsapp_message_receipts
            ADD CONSTRAINT whatsapp_message_receipts_tenant_contact_fk
            FOREIGN KEY (tenant_id, contact_id)
            REFERENCES business.whatsapp_journey_contacts (tenant_id, contact_id);
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_whatsapp_journey_contacts_tenant_id
    ON business.whatsapp_journey_contacts (tenant_id);

COMMIT;
