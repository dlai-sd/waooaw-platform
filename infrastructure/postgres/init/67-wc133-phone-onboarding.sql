-- Implements: work-contracts/WC-133-whatsapp-first-registration-and-web-registration-repair.md R001-R004
-- constitutional_basis: C-023, C-026, C-039, C-059, C-063

BEGIN;

CREATE TABLE IF NOT EXISTS identity.phone_onboarding (
    tenant_id UUID NOT NULL,
    binding_digest CHAR(64) NOT NULL CHECK (binding_digest ~ '^[0-9a-f]{64}$'),
    participant_id UUID NOT NULL UNIQUE,
    evidence_id UUID CHECK (evidence_id <> '00000000-0000-0000-0000-000000000000'::UUID),
    first_observed_at TIMESTAMPTZ NOT NULL,
    admitted_at TIMESTAMPTZ,
    last_inbound_at TIMESTAMPTZ NOT NULL,
    stopped_at TIMESTAMPTZ,
    PRIMARY KEY (tenant_id, binding_digest),
    CHECK ((evidence_id IS NULL) = (admitted_at IS NULL))
);
ALTER TABLE identity.phone_onboarding ENABLE ROW LEVEL SECURITY;
ALTER TABLE identity.phone_onboarding FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS phone_onboarding_tenant_isolation ON identity.phone_onboarding;
CREATE POLICY phone_onboarding_tenant_isolation ON identity.phone_onboarding
USING (tenant_id = nullif(current_setting('app.current_tenant_id', TRUE), '')::UUID)
WITH CHECK (tenant_id = nullif(current_setting('app.current_tenant_id', TRUE), '')::UUID);
GRANT SELECT, INSERT, UPDATE ON identity.phone_onboarding TO business_app;

CREATE UNIQUE INDEX IF NOT EXISTS portal_context_tenant_key
ON business.portal_interaction_contexts (tenant_id, context_id);
CREATE UNIQUE INDEX IF NOT EXISTS portal_message_context_key
ON business.portal_interaction_messages (tenant_id, context_id, message_id);

ALTER TABLE business.conversation_outbox
ADD COLUMN IF NOT EXISTS portal_context_id UUID,
ALTER COLUMN relationship_id DROP NOT NULL,
ALTER COLUMN conversation_id DROP NOT NULL;
ALTER TABLE business.conversation_outbox
DROP CONSTRAINT IF EXISTS conversation_outbox_scope_check,
ADD CONSTRAINT conversation_outbox_scope_check CHECK (
    (portal_context_id IS NULL AND relationship_id IS NOT NULL AND conversation_id IS NOT NULL)
    OR (
        portal_context_id IS NOT NULL AND relationship_id IS NULL AND conversation_id IS NULL
        AND purpose = 'PHONE_ONBOARDING' AND template_name IS NULL
        AND template_version IS NULL AND template_locale IS NULL AND template_category IS NULL
    )
);
ALTER TABLE business.conversation_outbox
DROP CONSTRAINT IF EXISTS conversation_outbox_portal_fk,
ADD CONSTRAINT conversation_outbox_portal_fk FOREIGN KEY (tenant_id, portal_context_id)
REFERENCES business.portal_interaction_contexts (tenant_id, context_id);
CREATE UNIQUE INDEX IF NOT EXISTS conversation_outbox_portal_identity
ON business.conversation_outbox (environment, tenant_id, portal_context_id, operation_family, idempotency_key)
WHERE portal_context_id IS NOT NULL;

ALTER TABLE business.conversation_delivery_observations
ADD COLUMN IF NOT EXISTS portal_context_id UUID,
ADD COLUMN IF NOT EXISTS portal_message_id UUID,
ALTER COLUMN relationship_id DROP NOT NULL,
ALTER COLUMN message_id DROP NOT NULL;
ALTER TABLE business.conversation_delivery_observations
DROP CONSTRAINT IF EXISTS conversation_delivery_scope_check,
ADD CONSTRAINT conversation_delivery_scope_check CHECK (
    (portal_context_id IS NULL AND portal_message_id IS NULL AND relationship_id IS NOT NULL AND message_id IS NOT NULL)
    OR (
        portal_context_id IS NOT NULL
        AND portal_message_id IS NOT NULL
        AND relationship_id IS NULL
        AND message_id IS NULL
    )
);
ALTER TABLE business.conversation_delivery_observations
DROP CONSTRAINT IF EXISTS conversation_delivery_portal_fk,
ADD CONSTRAINT conversation_delivery_portal_fk FOREIGN KEY (tenant_id, portal_context_id, portal_message_id)
REFERENCES business.portal_interaction_messages (tenant_id, context_id, message_id);
CREATE UNIQUE INDEX IF NOT EXISTS conversation_delivery_portal_identity
ON business.conversation_delivery_observations
(environment, tenant_id, portal_context_id, portal_message_id, provider, provider_event_identity)
WHERE portal_context_id IS NOT NULL;

COMMIT;
