-- WC-134 R002/R005: explicit attachment-owned routing coordinates, not account authentication.
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '30s';
DO $membership$
BEGIN
    IF NOT pg_has_role(session_user, 'bp_owner', 'SET') THEN
        EXECUTE format('GRANT bp_owner TO %I', session_user);
        PERFORM set_config('waooaw.wc134_route_granted_bp_owner', 'true', true);
    END IF;
END
$membership$;

CREATE TABLE IF NOT EXISTS business.whatsapp_relationship_routes (
    service_tenant_id UUID NOT NULL,
    sender_hash CHAR(64) NOT NULL CHECK (sender_hash ~ '^[0-9a-f]{64}$'),
    tenant_id UUID NOT NULL,
    binding_id UUID NOT NULL,
    identity_link_id UUID NOT NULL,
    actor_issuer TEXT NOT NULL CHECK (length(actor_issuer) BETWEEN 1 AND 2048),
    actor_id UUID NOT NULL,
    account_id UUID NOT NULL,
    membership_id UUID NOT NULL,
    bound_evidence_id UUID NOT NULL,
    published_at TIMESTAMPTZ NOT NULL,
    CONSTRAINT whatsapp_relationship_routes_pk PRIMARY KEY (service_tenant_id, sender_hash),
    CONSTRAINT whatsapp_relationship_routes_binding_unique UNIQUE (tenant_id, binding_id),
    CONSTRAINT whatsapp_relationship_routes_binding_fk FOREIGN KEY (tenant_id, binding_id)
        REFERENCES business.channel_bindings (tenant_id, binding_id)
);

ALTER TABLE business.whatsapp_relationship_routes OWNER TO bp_owner;
ALTER TABLE business.whatsapp_relationship_routes ENABLE ROW LEVEL SECURITY;
ALTER TABLE business.whatsapp_relationship_routes FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS whatsapp_relationship_routes_customer ON business.whatsapp_relationship_routes;
CREATE POLICY whatsapp_relationship_routes_customer ON business.whatsapp_relationship_routes
    USING (tenant_id = nullif(current_setting('app.current_tenant_id', true), '')::UUID)
    WITH CHECK (tenant_id = nullif(current_setting('app.current_tenant_id', true), '')::UUID);

DROP POLICY IF EXISTS whatsapp_relationship_routes_service_lookup ON business.whatsapp_relationship_routes;
CREATE POLICY whatsapp_relationship_routes_service_lookup ON business.whatsapp_relationship_routes
    FOR SELECT TO business_app
    USING (service_tenant_id = nullif(current_setting('app.current_tenant_id', true), '')::UUID);

GRANT SELECT, INSERT ON business.whatsapp_relationship_routes TO business_app;
REVOKE UPDATE, DELETE ON business.whatsapp_relationship_routes FROM business_app;

COMMENT ON TABLE business.whatsapp_relationship_routes IS
    'Private attachment-owned directory. Lookup grants no customer authority: current Identity, channel binding, participant, consent and Stop must be revalidated before tenant-scoped work. No legacy or recognition backfill.';
DO $membership$
BEGIN
    IF current_setting('waooaw.wc134_route_granted_bp_owner', true) = 'true' THEN
        EXECUTE format('REVOKE bp_owner FROM %I', session_user);
    END IF;
END
$membership$;
COMMIT;
