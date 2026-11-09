-- Implements: WC-134 R005/R008; current tenant contact access for relationship attachment.
-- constitutional_basis: C-023, C-026, C-059

BEGIN;

ALTER TABLE business.whatsapp_journey_contacts ENABLE ROW LEVEL SECURITY;
ALTER TABLE business.whatsapp_journey_contacts FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS whatsapp_contacts_tenant_scope ON business.whatsapp_journey_contacts;
CREATE POLICY whatsapp_contacts_tenant_scope ON business.whatsapp_journey_contacts
TO business_app, bp_owner
USING (
    tenant_id = NULLIF(CURRENT_SETTING('app.current_tenant_id', TRUE), '')::uuid
)
WITH CHECK (
    tenant_id = NULLIF(CURRENT_SETTING('app.current_tenant_id', TRUE), '')::uuid
);

COMMIT;
