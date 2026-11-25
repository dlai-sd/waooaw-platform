-- Implements: work-contracts/WC-172-safe-to-charge-real-customers.md WC172-R008
-- Implements: work-contracts/WC-170-real-agent-work-end-to-end.md gap B5
-- Constitutional basis: C-005, C-023, C-059, C-063
-- WC-172 B5: the billing engine verifies spend evidence at its owner instead of trusting the caller. The Business
-- Platform owns business.real_work_records (forced row-level security). Two functions it owns answer, for one tenant
-- and relationship, whether (1) an artifact is locked at an exact digest, is not superseded, and has both customer
-- decision records, and (2) a work item's timeline event carries the provider's own reference. The billing engine's
-- runtime role may call them and may read nothing in the table itself. Payload keys are matched without regard to
-- case because the lock record and the decision and timeline records are written with different naming options.
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '30s';
SET LOCAL ROLE bp_owner;

CREATE OR REPLACE FUNCTION business.real_work_field(p_payload jsonb, p_name text) RETURNS text
LANGUAGE sql IMMUTABLE PARALLEL SAFE
AS $$
    SELECT value #>> '{}' FROM jsonb_each(p_payload) WHERE lower(key) = lower(p_name) LIMIT 1
$$;

CREATE OR REPLACE FUNCTION business.real_work_authorization_evidence_ok(
    p_tenant uuid, p_relationship uuid, p_artifact uuid, p_digest text, p_approval uuid, p_scope uuid
) RETURNS boolean
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, business
AS $$
DECLARE
    previous text := current_setting('app.current_tenant_id', true);
    verified boolean;
BEGIN
    PERFORM set_config('app.current_tenant_id', p_tenant::text, true);
    SELECT
        EXISTS (
            SELECT 1 FROM business.real_work_records r
            WHERE r.tenant_id = p_tenant AND r.relationship_id = p_relationship AND r.kind = 'ARTIFACT_LOCKED'
              AND lower(business.real_work_field(r.payload, 'ArtifactId')) = lower(p_artifact::text)
              AND business.real_work_field(r.payload, 'Digest') = p_digest
              AND lower(business.real_work_field(r.payload, 'ApprovalEvidenceId')) = lower(p_approval::text)
        )
        AND NOT EXISTS (
            SELECT 1 FROM business.real_work_records r
            WHERE r.tenant_id = p_tenant AND r.relationship_id = p_relationship AND r.kind = 'ARTIFACT_SUPERSEDED'
              AND lower(business.real_work_field(r.payload, 'ArtifactId')) = lower(p_artifact::text)
        )
        AND EXISTS (
            SELECT 1 FROM business.real_work_records r
            WHERE r.tenant_id = p_tenant AND r.relationship_id = p_relationship AND r.kind = 'DECISION'
              AND business.real_work_field(r.payload, 'Kind') = 'APPROVAL'
              AND lower(business.real_work_field(r.payload, 'ArtifactId')) = lower(p_artifact::text)
              AND business.real_work_field(r.payload, 'ArtifactDigest') = p_digest
              AND lower(business.real_work_field(r.payload, 'EvidenceId')) = lower(p_approval::text)
        )
        AND EXISTS (
            SELECT 1 FROM business.real_work_records r
            WHERE r.tenant_id = p_tenant AND r.relationship_id = p_relationship AND r.kind = 'DECISION'
              AND business.real_work_field(r.payload, 'Kind') = 'SCOPE_CONFIRMATION'
              AND lower(business.real_work_field(r.payload, 'ArtifactId')) = lower(p_artifact::text)
              AND business.real_work_field(r.payload, 'ArtifactDigest') = p_digest
              AND lower(business.real_work_field(r.payload, 'EvidenceId')) = lower(p_scope::text)
        )
    INTO verified;
    PERFORM set_config('app.current_tenant_id', COALESCE(previous, ''), true);
    RETURN COALESCE(verified, false);
END
$$;

CREATE OR REPLACE FUNCTION business.real_work_provider_proof_ok(
    p_tenant uuid, p_relationship uuid, p_event uuid, p_work_item uuid, p_provider_reference text
) RETURNS boolean
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, business
AS $$
DECLARE
    previous text := current_setting('app.current_tenant_id', true);
    verified boolean;
BEGIN
    PERFORM set_config('app.current_tenant_id', p_tenant::text, true);
    SELECT EXISTS (
        SELECT 1 FROM business.real_work_records r
        WHERE r.tenant_id = p_tenant AND r.relationship_id = p_relationship AND r.kind = 'TIMELINE'
          AND lower(business.real_work_field(r.payload, 'EventId')) = lower(p_event::text)
          AND lower(business.real_work_field(r.payload, 'WorkItemId')) = lower(p_work_item::text)
          AND business.real_work_field(r.payload, 'ProviderReference') = p_provider_reference
    ) INTO verified;
    PERFORM set_config('app.current_tenant_id', COALESCE(previous, ''), true);
    RETURN COALESCE(verified, false);
END
$$;

REVOKE ALL ON FUNCTION business.real_work_field(jsonb, text),
    business.real_work_authorization_evidence_ok(uuid, uuid, uuid, text, uuid, uuid),
    business.real_work_provider_proof_ok(uuid, uuid, uuid, uuid, text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION business.real_work_field(jsonb, text),
    business.real_work_authorization_evidence_ok(uuid, uuid, uuid, text, uuid, uuid),
    business.real_work_provider_proof_ok(uuid, uuid, uuid, uuid, text) TO wbe_app;

COMMIT;
