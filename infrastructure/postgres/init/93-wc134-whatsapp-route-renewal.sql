-- WC-134 R002/R007/R009: evidence-bound same-owner renewal with immutable delivery history.
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '30s';
DO $membership$
BEGIN
    IF NOT pg_has_role(session_user, 'bp_owner', 'SET') THEN
        EXECUTE format('GRANT bp_owner TO %I', session_user);
        PERFORM set_config('waooaw.wc134_renewal_granted_bp_owner', 'true', true);
    END IF;
END
$membership$;

CREATE TABLE IF NOT EXISTS business.whatsapp_relationship_route_history (
    service_tenant_id UUID NOT NULL, sender_hash CHAR(64) NOT NULL,
    tenant_id UUID NOT NULL, binding_id UUID NOT NULL, identity_link_id UUID NOT NULL,
    actor_issuer TEXT NOT NULL, actor_id UUID NOT NULL, account_id UUID NOT NULL,
    membership_id UUID NOT NULL, bound_evidence_id UUID NOT NULL, published_at TIMESTAMPTZ NOT NULL,
    retired_at TIMESTAMPTZ NOT NULL, retirement_evidence_id UUID NOT NULL,
    PRIMARY KEY (service_tenant_id, sender_hash, binding_id),
    FOREIGN KEY (tenant_id, binding_id) REFERENCES business.channel_bindings(tenant_id, binding_id),
    CHECK (sender_hash ~ '^[0-9a-f]{64}$'),
    CHECK (retired_at >= published_at)
);
ALTER TABLE business.whatsapp_relationship_route_history OWNER TO bp_owner;
ALTER TABLE business.whatsapp_relationship_route_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE business.whatsapp_relationship_route_history FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS route_history_scope ON business.whatsapp_relationship_route_history;
CREATE POLICY route_history_scope ON business.whatsapp_relationship_route_history
    USING (tenant_id = nullif(current_setting('app.current_tenant_id', true), '')::UUID
        OR service_tenant_id = nullif(current_setting('app.current_tenant_id', true), '')::UUID);
REVOKE ALL ON business.whatsapp_relationship_route_history FROM PUBLIC, business_app;
DROP POLICY IF EXISTS route_owner_service_read ON business.whatsapp_relationship_routes;
CREATE POLICY route_owner_service_read ON business.whatsapp_relationship_routes FOR SELECT TO bp_owner
    USING (service_tenant_id = nullif(current_setting('app.current_tenant_id', true), '')::UUID);

CREATE OR REPLACE FUNCTION business.renew_whatsapp_relationship_route(
    p_service UUID, p_sender TEXT, p_previous UUID, p_binding UUID, p_link UUID,
    p_issuer TEXT, p_actor UUID, p_account UUID, p_membership UUID, p_evidence UUID,
    p_published TIMESTAMPTZ)
RETURNS BOOLEAN LANGUAGE plpgsql SECURITY DEFINER
SET search_path = pg_catalog SET row_security = on
AS $function$
DECLARE previous RECORD; old_binding RECORD; target RECORD; selected UUID;
BEGIN
    selected := nullif(current_setting('app.current_tenant_id', true), '')::UUID;
    SELECT * INTO previous FROM business.whatsapp_relationship_routes
        WHERE service_tenant_id = p_service AND sender_hash = p_sender FOR UPDATE;
    IF previous IS NULL OR previous.tenant_id IS DISTINCT FROM selected
        OR previous.binding_id IS DISTINCT FROM p_previous OR p_binding = p_previous
        OR previous.actor_id IS DISTINCT FROM p_actor OR previous.actor_issuer IS DISTINCT FROM p_issuer
        OR previous.account_id IS DISTINCT FROM p_account OR previous.membership_id IS DISTINCT FROM p_membership
        OR p_link IS NULL OR p_link = '00000000-0000-0000-0000-000000000000'::UUID
        OR p_evidence IS NULL OR p_evidence = '00000000-0000-0000-0000-000000000000'::UUID
        OR p_published IS NULL OR p_published > clock_timestamp() OR p_published < previous.published_at THEN
        RAISE EXCEPTION 'WhatsApp same-owner renewal denied' USING ERRCODE = '42501';
    END IF;
    SELECT * INTO old_binding FROM business.channel_bindings
        WHERE tenant_id = selected AND binding_id = p_previous FOR SHARE;
    SELECT * INTO target FROM business.channel_bindings
        WHERE tenant_id = selected AND binding_id = p_binding FOR SHARE;
    IF old_binding IS NULL OR target IS NULL
        OR old_binding.status <> 'ENDED' OR old_binding.revoked_at IS NULL
        OR old_binding.revoked_evidence_id IS NULL
        OR old_binding.revoked_evidence_id = '00000000-0000-0000-0000-000000000000'::UUID
        OR old_binding.bound_evidence_id IS DISTINCT FROM previous.bound_evidence_id
        OR old_binding.participant_id IS DISTINCT FROM p_actor
        OR old_binding.external_subject_hash IS DISTINCT FROM p_sender
        OR old_binding.channel <> 'WHATSAPP'
        OR target.status <> 'ACTIVE' OR target.revoked_at IS NOT NULL OR target.channel <> 'WHATSAPP'
        OR target.participant_id IS DISTINCT FROM p_actor OR target.external_subject_hash IS DISTINCT FROM p_sender
        OR target.bound_evidence_id IS DISTINCT FROM p_evidence OR target.bound_at IS NULL
        OR target.bound_at < old_binding.revoked_at OR target.bound_at > p_published
        OR target.relationship_id IS DISTINCT FROM old_binding.relationship_id
        OR target.participant_role IS DISTINCT FROM old_binding.participant_role
        OR target.conversation_id IS DISTINCT FROM old_binding.conversation_id
        OR target.assurance_level <> 'TIER_4_PORTAL_FRESH'
        OR EXISTS (SELECT 1 FROM business.whatsapp_journey_contacts
            WHERE tenant_id = selected AND phone_hmac = p_sender AND opted_out_at IS NOT NULL)
        OR EXISTS (SELECT 1 FROM business.channel_bindings
            WHERE tenant_id = selected AND channel = 'WHATSAPP' AND status = 'ACTIVE'
                AND external_subject_hash = p_sender AND binding_id <> p_binding) THEN
        RAISE EXCEPTION 'WhatsApp same-owner renewal denied' USING ERRCODE = '42501';
    END IF;
    INSERT INTO business.whatsapp_relationship_route_history VALUES (
        previous.service_tenant_id, previous.sender_hash, previous.tenant_id, previous.binding_id,
        previous.identity_link_id, previous.actor_issuer, previous.actor_id, previous.account_id,
        previous.membership_id, previous.bound_evidence_id, previous.published_at,
        p_published, old_binding.revoked_evidence_id);
    UPDATE business.whatsapp_relationship_routes SET binding_id = p_binding,
        identity_link_id = p_link, bound_evidence_id = p_evidence, published_at = p_published
        WHERE service_tenant_id = p_service AND sender_hash = p_sender AND binding_id = p_previous;
    RETURN true;
END
$function$;
ALTER FUNCTION business.renew_whatsapp_relationship_route(UUID, TEXT, UUID, UUID, UUID, TEXT, UUID, UUID, UUID, UUID, TIMESTAMPTZ) OWNER TO bp_owner;
REVOKE ALL ON FUNCTION business.renew_whatsapp_relationship_route(UUID, TEXT, UUID, UUID, UUID, TEXT, UUID, UUID, UUID, UUID, TIMESTAMPTZ) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION business.renew_whatsapp_relationship_route(UUID, TEXT, UUID, UUID, UUID, TEXT, UUID, UUID, UUID, UUID, TIMESTAMPTZ) TO business_app;

CREATE OR REPLACE FUNCTION business.find_whatsapp_delivery_route(
    p_service UUID, p_sender TEXT, p_environment TEXT, p_outbox UUID)
RETURNS TABLE (
    service_tenant_id UUID, sender_hash CHAR(64), tenant_id UUID, binding_id UUID,
    identity_link_id UUID, actor_issuer TEXT, actor_id UUID, account_id UUID,
    membership_id UUID, bound_evidence_id UUID, published_at TIMESTAMPTZ
) LANGUAGE plpgsql SECURITY DEFINER
SET search_path = pg_catalog SET row_security = on
AS $function$
DECLARE work RECORD;
BEGIN
    IF p_service IS DISTINCT FROM nullif(current_setting('app.current_tenant_id', true), '')::UUID
        OR p_service IS NULL OR p_sender IS NULL OR p_sender !~ '^[0-9a-f]{64}$'
        OR p_environment IS NULL OR length(p_environment) NOT BETWEEN 1 AND 32 OR p_outbox IS NULL THEN
        RAISE EXCEPTION 'WhatsApp delivery route scope denied' USING ERRCODE = '42501';
    END IF;
    SELECT w.* INTO work FROM business.whatsapp_outbox_work w
        WHERE w.outbox_id = p_outbox AND w.service_tenant_id = p_service
            AND w.environment = p_environment AND w.sender_hash = p_sender;
    IF work IS NULL THEN RETURN; END IF;
    RETURN QUERY SELECT r.service_tenant_id, r.sender_hash, r.tenant_id, r.binding_id, r.identity_link_id,
        r.actor_issuer, r.actor_id, r.account_id, r.membership_id, r.bound_evidence_id, r.published_at
        FROM business.whatsapp_relationship_routes r
        WHERE r.service_tenant_id = p_service AND r.sender_hash = p_sender
            AND r.tenant_id = work.tenant_id AND r.binding_id = work.binding_id
        UNION ALL
        SELECT h.service_tenant_id, h.sender_hash, h.tenant_id, h.binding_id, h.identity_link_id,
            h.actor_issuer, h.actor_id, h.account_id, h.membership_id, h.bound_evidence_id, h.published_at
        FROM business.whatsapp_relationship_route_history h
        WHERE h.service_tenant_id = p_service AND h.sender_hash = p_sender
            AND h.tenant_id = work.tenant_id AND h.binding_id = work.binding_id;
END
$function$;
ALTER FUNCTION business.find_whatsapp_delivery_route(UUID, TEXT, TEXT, UUID) OWNER TO bp_owner;
REVOKE ALL ON FUNCTION business.find_whatsapp_delivery_route(UUID, TEXT, TEXT, UUID) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION business.find_whatsapp_delivery_route(UUID, TEXT, TEXT, UUID) TO business_app;

CREATE OR REPLACE FUNCTION business.matches_whatsapp_outbox_route(
    p_service UUID, p_tenant UUID, p_sender TEXT, p_environment TEXT, p_outbox UUID, p_binding UUID)
RETURNS BOOLEAN LANGUAGE plpgsql SECURITY DEFINER
SET search_path = pg_catalog SET row_security = on
AS $function$
DECLARE matched UUID;
BEGIN
    IF p_tenant IS DISTINCT FROM nullif(current_setting('app.current_tenant_id', true), '')::UUID
        OR p_tenant IS NULL OR p_service IS NULL OR p_sender IS NULL
        OR p_environment IS NULL OR p_outbox IS NULL OR p_binding IS NULL THEN
        RAISE EXCEPTION 'WhatsApp lease route scope denied' USING ERRCODE = '42501';
    END IF;
    SELECT w.outbox_id INTO matched FROM business.whatsapp_outbox_work w
        JOIN business.whatsapp_relationship_routes r ON r.service_tenant_id = w.service_tenant_id
            AND r.sender_hash = w.sender_hash AND r.tenant_id = w.tenant_id AND r.binding_id = w.binding_id
        WHERE w.outbox_id = p_outbox AND w.tenant_id = p_tenant AND w.service_tenant_id = p_service
            AND w.sender_hash = p_sender AND w.environment = p_environment AND w.binding_id = p_binding
        FOR SHARE OF w, r;
    RETURN matched IS NOT NULL;
END
$function$;
ALTER FUNCTION business.matches_whatsapp_outbox_route(UUID, UUID, TEXT, TEXT, UUID, UUID) OWNER TO bp_owner;
REVOKE ALL ON FUNCTION business.matches_whatsapp_outbox_route(UUID, UUID, TEXT, TEXT, UUID, UUID) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION business.matches_whatsapp_outbox_route(UUID, UUID, TEXT, TEXT, UUID, UUID) TO business_app;
DO $membership$
BEGIN
    IF current_setting('waooaw.wc134_renewal_granted_bp_owner', true) = 'true' THEN
        EXECUTE format('REVOKE bp_owner FROM %I', session_user);
    END IF;
END
$membership$;
COMMIT;
