-- Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C4-08
-- Constitutional basis: C-005, C-023, C-026, C-059, C-063, ADR-051
-- WC-136: an owner-confirmed deliverable that consumes a package component unit is recorded here in the same
-- tenant-scoped write path that confirms it, so a restart of the Business Platform never loses a unit. A worker
-- drains the table through the claim/mark functions below; the Billing Engine counts idempotently on the
-- evidence id, so a re-delivery after an unresolved outcome is always safe.
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '30s';
SET LOCAL ROLE bp_owner;

CREATE TABLE IF NOT EXISTS business.component_unit_outbox (
    outbox_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    relationship_id UUID NOT NULL,
    component_id TEXT NOT NULL CHECK (component_id ~ '^[A-Za-z0-9_.-]{1,100}$'),
    completion_evidence_id UUID NOT NULL,
    actor_subject TEXT NOT NULL CHECK (length(actor_subject) BETWEEN 1 AND 128),
    state TEXT NOT NULL DEFAULT 'PENDING'
        CHECK (state IN ('PENDING', 'LEASED', 'DELIVERED', 'REFUSED', 'UNRESOLVED')),
    attempt_number INTEGER NOT NULL DEFAULT 0 CHECK (attempt_number >= 0),
    next_attempt_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    lease_expires_at TIMESTAMPTZ,
    last_code TEXT CHECK (last_code IS NULL OR length(last_code) BETWEEN 1 AND 100),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    resolved_at TIMESTAMPTZ,
    UNIQUE (tenant_id, relationship_id, component_id, completion_evidence_id)
);
ALTER TABLE business.component_unit_outbox OWNER TO bp_owner;
CREATE INDEX IF NOT EXISTS component_unit_outbox_due
    ON business.component_unit_outbox (next_attempt_at, outbox_id)
    WHERE state = 'PENDING';
CREATE INDEX IF NOT EXISTS component_unit_outbox_leased
    ON business.component_unit_outbox (lease_expires_at, outbox_id)
    WHERE state = 'LEASED';

ALTER TABLE business.component_unit_outbox ENABLE ROW LEVEL SECURITY;
ALTER TABLE business.component_unit_outbox FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS component_unit_outbox_tenant_isolation ON business.component_unit_outbox;
CREATE POLICY component_unit_outbox_tenant_isolation ON business.component_unit_outbox TO business_app
    USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', TRUE), '')::UUID)
    WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', TRUE), '')::UUID);
DROP POLICY IF EXISTS component_unit_outbox_owner ON business.component_unit_outbox;
CREATE POLICY component_unit_outbox_owner ON business.component_unit_outbox TO bp_owner
    USING (true) WITH CHECK (true);

REVOKE ALL ON business.component_unit_outbox FROM PUBLIC, business_app;
GRANT SELECT, INSERT ON business.component_unit_outbox TO business_app;

CREATE OR REPLACE FUNCTION business.claim_component_unit_work(p_limit INTEGER, p_lease_seconds INTEGER)
RETURNS TABLE (
    work_id UUID,
    work_tenant_id UUID,
    work_relationship_id UUID,
    work_component_id TEXT,
    work_evidence_id UUID,
    work_actor_subject TEXT,
    work_attempt INTEGER
)
LANGUAGE plpgsql SECURITY DEFINER
SET search_path = pg_catalog SET row_security = on
AS $function$
BEGIN
    IF p_limit IS NULL OR p_limit NOT BETWEEN 1 AND 100
        OR p_lease_seconds IS NULL OR p_lease_seconds NOT BETWEEN 5 AND 900 THEN
        RAISE EXCEPTION 'Component unit claim scope is invalid' USING ERRCODE = '42501';
    END IF;
    RETURN QUERY
    WITH due AS (
        SELECT candidate.outbox_id
        FROM business.component_unit_outbox AS candidate
        WHERE (candidate.state = 'PENDING' AND candidate.next_attempt_at <= now())
            OR (candidate.state = 'LEASED' AND candidate.lease_expires_at <= now())
        ORDER BY candidate.next_attempt_at, candidate.outbox_id
        LIMIT p_limit
        FOR UPDATE SKIP LOCKED
    )
    UPDATE business.component_unit_outbox AS work
    SET state = 'LEASED', lease_expires_at = now() + make_interval(secs => p_lease_seconds)
    FROM due
    WHERE work.outbox_id = due.outbox_id
    RETURNING work.outbox_id, work.tenant_id, work.relationship_id, work.component_id,
        work.completion_evidence_id, work.actor_subject, work.attempt_number;
END
$function$;
ALTER FUNCTION business.claim_component_unit_work(INTEGER, INTEGER) OWNER TO bp_owner;
REVOKE ALL ON FUNCTION business.claim_component_unit_work(INTEGER, INTEGER) FROM PUBLIC, business_app;
GRANT EXECUTE ON FUNCTION business.claim_component_unit_work(INTEGER, INTEGER) TO business_app;

CREATE OR REPLACE FUNCTION business.mark_component_unit_work(
    p_outbox_id UUID, p_outcome TEXT, p_delay_seconds INTEGER, p_code TEXT
)
RETURNS BOOLEAN
LANGUAGE plpgsql SECURITY DEFINER
SET search_path = pg_catalog SET row_security = on
AS $function$
DECLARE changed INTEGER;
BEGIN
    IF p_outbox_id IS NULL OR p_outcome NOT IN ('DELIVERED', 'REFUSED', 'RETRY', 'UNRESOLVED')
        OR (p_outcome = 'RETRY' AND (p_delay_seconds IS NULL OR p_delay_seconds NOT BETWEEN 0 AND 86400))
        OR (p_code IS NOT NULL AND length(p_code) NOT BETWEEN 1 AND 100) THEN
        RAISE EXCEPTION 'Component unit outcome is invalid' USING ERRCODE = '42501';
    END IF;
    UPDATE business.component_unit_outbox AS work
    SET state = CASE p_outcome WHEN 'RETRY' THEN 'PENDING' ELSE p_outcome END,
        attempt_number = work.attempt_number + CASE WHEN p_outcome = 'RETRY' THEN 1 ELSE 0 END,
        next_attempt_at = CASE WHEN p_outcome = 'RETRY'
            THEN now() + make_interval(secs => p_delay_seconds) ELSE work.next_attempt_at END,
        lease_expires_at = NULL,
        last_code = p_code,
        resolved_at = CASE WHEN p_outcome = 'RETRY' THEN NULL ELSE now() END
    WHERE work.outbox_id = p_outbox_id AND work.state = 'LEASED';
    GET DIAGNOSTICS changed = ROW_COUNT;
    RETURN changed = 1;
END
$function$;
ALTER FUNCTION business.mark_component_unit_work(UUID, TEXT, INTEGER, TEXT) OWNER TO bp_owner;
REVOKE ALL ON FUNCTION business.mark_component_unit_work(UUID, TEXT, INTEGER, TEXT) FROM PUBLIC, business_app;
GRANT EXECUTE ON FUNCTION business.mark_component_unit_work(UUID, TEXT, INTEGER, TEXT) TO business_app;

COMMIT;
