-- Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C4-05
-- Constitutional basis: C-059, C-088, C-089, C-090, C-091
-- WC-136: versioned pricing configuration, package projection key, component units.
-- Every pricing version is an append-only row; only the permitted state and authorization columns
-- change, and only through the wbe_owner SECURITY DEFINER functions defined here.
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '30s';
DO $owner$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'wbe_owner') THEN
        CREATE ROLE wbe_owner NOLOGIN;
    END IF;
    IF NOT pg_has_role(session_user, 'bp_owner', 'SET') THEN
        EXECUTE format('GRANT bp_owner TO %I', session_user);
        PERFORM set_config('waooaw.wc136_pricing_bp_owner_granted', 'true', true);
    END IF;
    IF NOT pg_has_role(session_user, 'wbe_owner', 'SET') THEN
        EXECUTE format('GRANT wbe_owner TO %I', session_user);
        PERFORM set_config('waooaw.wc136_pricing_wbe_owner_granted', 'true', true);
    END IF;
END
$owner$;
SET LOCAL ROLE bp_owner;

-- Package projection key: the same package code may exist for several agent versions.
ALTER TABLE institutional.bundle_profiles
    ADD COLUMN IF NOT EXISTS agent_version TEXT,
    ADD COLUMN IF NOT EXISTS package_version_id UUID;
ALTER TABLE institutional.bundle_profiles
    ALTER COLUMN bundle_tier TYPE VARCHAR(64);
UPDATE institutional.bundle_profiles SET agent_version = '1.0.0' WHERE agent_version IS NULL;
ALTER TABLE institutional.bundle_profiles
    ALTER COLUMN agent_version SET NOT NULL;
ALTER TABLE institutional.bundle_profiles
    DROP CONSTRAINT IF EXISTS uq_bundle_profile;
DO $key$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'uq_bundle_profile_agent_version'
          AND conrelid = 'institutional.bundle_profiles'::regclass
    ) THEN
        ALTER TABLE institutional.bundle_profiles
            ADD CONSTRAINT uq_bundle_profile_agent_version
            UNIQUE (agent_type, agent_version, bundle_tier, bundle_version);
    END IF;
END
$key$;
CREATE INDEX IF NOT EXISTS idx_bundle_profiles_package_version
    ON institutional.bundle_profiles (package_version_id)
    WHERE package_version_id IS NOT NULL;

GRANT USAGE ON SCHEMA institutional, business TO wbe_owner;
GRANT SELECT, INSERT, UPDATE ON institutional.bundle_profiles TO wbe_owner;
GRANT SELECT, UPDATE ON institutional.thread_catalog TO wbe_owner;
GRANT CREATE ON SCHEMA institutional, business TO wbe_owner;
RESET ROLE;

SET LOCAL ROLE wbe_owner;

CREATE TABLE IF NOT EXISTS institutional.pricing_versions (
    version_id UUID PRIMARY KEY,
    kind TEXT NOT NULL CHECK (kind IN ('RATE', 'PACKAGE', 'POLICY', 'GRANT', 'BUDGET', 'COUPON')),
    subject_key TEXT NOT NULL CHECK (length(subject_key) BETWEEN 1 AND 300),
    version_no INTEGER NOT NULL CHECK (version_no > 0),
    state TEXT NOT NULL CHECK (state IN (
        'DRAFT', 'SIMULATED', 'SUBMITTED', 'AUTHORIZED', 'EFFECTIVE', 'SUPERSEDED', 'DISCARDED'
    )),
    body JSONB NOT NULL,
    body_digest TEXT NOT NULL CHECK (body_digest ~ '^[0-9a-f]{64}$'),
    seed BOOLEAN NOT NULL DEFAULT false,
    effective_from TIMESTAMPTZ,
    supersedes UUID REFERENCES institutional.pricing_versions (version_id),
    created_by TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    authorized_by TEXT,
    authorized_at TIMESTAMPTZ,
    evidence_id UUID,
    needs_second_confirmation BOOLEAN NOT NULL DEFAULT false,
    second_confirmed_by TEXT,
    UNIQUE (kind, subject_key, version_no),
    CHECK (
        (authorized_by IS NULL AND authorized_at IS NULL AND evidence_id IS NULL)
        OR (authorized_by IS NOT NULL AND authorized_at IS NOT NULL AND evidence_id IS NOT NULL)
    ),
    CHECK (
        state NOT IN ('AUTHORIZED', 'EFFECTIVE', 'SUPERSEDED')
        OR (authorized_by IS NOT NULL AND effective_from IS NOT NULL)
    )
);
CREATE INDEX IF NOT EXISTS idx_pricing_versions_subject
    ON institutional.pricing_versions (kind, subject_key, state, effective_from DESC);

CREATE TABLE IF NOT EXISTS institutional.pricing_version_events (
    event_id UUID PRIMARY KEY,
    version_id UUID NOT NULL REFERENCES institutional.pricing_versions (version_id),
    from_state TEXT,
    to_state TEXT NOT NULL,
    direction TEXT NOT NULL CHECK (direction IN ('NORMAL', 'SAFETY')),
    actor TEXT NOT NULL,
    occurred_at TIMESTAMPTZ NOT NULL,
    reason TEXT
);
CREATE INDEX IF NOT EXISTS idx_pricing_version_events_version
    ON institutional.pricing_version_events (version_id, occurred_at);

CREATE TABLE IF NOT EXISTS business.component_units (
    tenant_id UUID NOT NULL,
    relationship_id UUID NOT NULL,
    agent_instance_id UUID NOT NULL,
    package_version_id UUID NOT NULL REFERENCES institutional.pricing_versions (version_id),
    component_id TEXT NOT NULL,
    kind TEXT NOT NULL CHECK (kind IN ('COUNTED', 'SELECTED', 'TIME_ACCESS', 'CAPACITY')),
    period_start TIMESTAMPTZ NOT NULL,
    period_end TIMESTAMPTZ NOT NULL,
    quantity INTEGER NOT NULL CHECK (quantity >= 0),
    released_cadence TEXT,
    PRIMARY KEY (tenant_id, relationship_id, component_id, period_start),
    CHECK (period_end > period_start)
);

CREATE TABLE IF NOT EXISTS business.component_unit_entries (
    entry_id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    relationship_id UUID NOT NULL,
    component_id TEXT NOT NULL,
    period_start TIMESTAMPTZ NOT NULL,
    entry_kind TEXT NOT NULL CHECK (entry_kind IN ('CONSUME', 'SELECT', 'SWAP', 'DESELECT', 'CLOSE')),
    units INTEGER,
    item_ref TEXT,
    completion_evidence_id UUID,
    idempotency_key UUID NOT NULL,
    occurred_at TIMESTAMPTZ NOT NULL,
    UNIQUE (tenant_id, relationship_id, idempotency_key),
    FOREIGN KEY (tenant_id, relationship_id, component_id, period_start)
        REFERENCES business.component_units (tenant_id, relationship_id, component_id, period_start)
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_component_unit_entries_evidence
    ON business.component_unit_entries (tenant_id, relationship_id, component_id, completion_evidence_id)
    WHERE completion_evidence_id IS NOT NULL;

CREATE OR REPLACE FUNCTION institutional.guard_pricing_version_change() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    v_open_states CONSTANT TEXT[] := ARRAY['DRAFT', 'SIMULATED', 'SUBMITTED'];
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'Pricing versions are append-only' USING ERRCODE = '55000';
    END IF;
    IF (NEW.version_id, NEW.kind, NEW.subject_key, NEW.version_no, NEW.seed, NEW.created_by, NEW.created_at)
       IS DISTINCT FROM
       (OLD.version_id, OLD.kind, OLD.subject_key, OLD.version_no, OLD.seed, OLD.created_by, OLD.created_at) THEN
        RAISE EXCEPTION 'Pricing version identity is immutable' USING ERRCODE = '55000';
    END IF;
    IF (NEW.body, NEW.body_digest) IS DISTINCT FROM (OLD.body, OLD.body_digest) THEN
        IF OLD.state NOT IN ('DRAFT', 'SIMULATED') OR NEW.state <> 'DRAFT' THEN
            RAISE EXCEPTION 'Pricing version body is immutable after submission' USING ERRCODE = '55000';
        END IF;
    END IF;
    IF NEW.state <> OLD.state AND NOT (
        (OLD.state = 'DRAFT' AND NEW.state IN ('SIMULATED', 'DISCARDED'))
        OR (OLD.state = 'SIMULATED' AND NEW.state IN ('SUBMITTED', 'DRAFT', 'DISCARDED'))
        OR (OLD.state = 'SUBMITTED' AND NEW.state IN ('AUTHORIZED', 'DRAFT', 'DISCARDED'))
        OR (OLD.state = 'AUTHORIZED' AND NEW.state = 'EFFECTIVE')
        OR (OLD.state = 'EFFECTIVE' AND NEW.state = 'SUPERSEDED')
    ) THEN
        RAISE EXCEPTION 'PRICING_ILLEGAL_TRANSITION: % to % is not allowed', OLD.state, NEW.state
            USING ERRCODE = '55000';
    END IF;
    IF (NEW.authorized_by, NEW.authorized_at, NEW.evidence_id, NEW.effective_from)
       IS DISTINCT FROM
       (OLD.authorized_by, OLD.authorized_at, OLD.evidence_id, OLD.effective_from)
       AND NOT (OLD.state = 'SUBMITTED' AND NEW.state = 'AUTHORIZED') THEN
        RAISE EXCEPTION 'Pricing authorization is immutable' USING ERRCODE = '55000';
    END IF;
    IF NEW.supersedes IS DISTINCT FROM OLD.supersedes
       AND NOT (OLD.state = 'AUTHORIZED' AND NEW.state = 'EFFECTIVE') THEN
        RAISE EXCEPTION 'Pricing supersession link is immutable' USING ERRCODE = '55000';
    END IF;
    IF (NEW.needs_second_confirmation, NEW.second_confirmed_by)
       IS DISTINCT FROM
       (OLD.needs_second_confirmation, OLD.second_confirmed_by)
       AND NOT (OLD.state = ANY (v_open_states) AND NEW.state = ANY (v_open_states)) THEN
        RAISE EXCEPTION 'Pricing confirmation is immutable after submission' USING ERRCODE = '55000';
    END IF;
    RETURN NEW;
END $$;
CREATE OR REPLACE TRIGGER pricing_versions_guard
BEFORE UPDATE OR DELETE ON institutional.pricing_versions
FOR EACH ROW EXECUTE FUNCTION institutional.guard_pricing_version_change();

CREATE OR REPLACE FUNCTION institutional.guard_pricing_event_append_only() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'Pricing version events are append-only' USING ERRCODE = '55000';
END $$;
CREATE OR REPLACE TRIGGER pricing_version_events_append_only
BEFORE UPDATE OR DELETE ON institutional.pricing_version_events
FOR EACH ROW EXECUTE FUNCTION institutional.guard_pricing_event_append_only();

CREATE OR REPLACE FUNCTION institutional.record_pricing_event(
    p_event_id UUID, p_version_id UUID, p_from_state TEXT, p_to_state TEXT, p_direction TEXT,
    p_actor TEXT, p_at TIMESTAMPTZ, p_reason TEXT
) RETURNS VOID
LANGUAGE plpgsql SECURITY DEFINER SET search_path = institutional, business, pg_temp AS $$
BEGIN
    INSERT INTO institutional.pricing_version_events
        (event_id, version_id, from_state, to_state, direction, actor, occurred_at, reason)
    VALUES (p_event_id, p_version_id, p_from_state, p_to_state, p_direction, p_actor, p_at, p_reason);
END $$;

CREATE OR REPLACE FUNCTION institutional.create_pricing_draft(
    p_version_id UUID, p_kind TEXT, p_subject_key TEXT, p_body JSONB, p_body_digest TEXT,
    p_actor TEXT, p_needs_second BOOLEAN, p_at TIMESTAMPTZ
) RETURNS institutional.pricing_versions
LANGUAGE plpgsql SECURITY DEFINER SET search_path = institutional, business, pg_temp AS $$
DECLARE
    v_next INTEGER;
    v_row institutional.pricing_versions;
BEGIN
    PERFORM pg_advisory_xact_lock(hashtextextended(p_kind || ':' || p_subject_key, 0));
    SELECT COALESCE(MAX(version_no), 0) + 1 INTO v_next
    FROM institutional.pricing_versions WHERE kind = p_kind AND subject_key = p_subject_key;
    INSERT INTO institutional.pricing_versions
        (version_id, kind, subject_key, version_no, state, body, body_digest, created_by,
         created_at, needs_second_confirmation)
    VALUES (p_version_id, p_kind, p_subject_key, v_next, 'DRAFT', p_body, p_body_digest, p_actor,
            p_at, COALESCE(p_needs_second, false))
    RETURNING * INTO v_row;
    PERFORM institutional.record_pricing_event(
        gen_random_uuid(), p_version_id, NULL, 'DRAFT', 'NORMAL', p_actor, p_at, 'CREATE');
    RETURN v_row;
END $$;

CREATE OR REPLACE FUNCTION institutional.edit_pricing_draft(
    p_version_id UUID, p_body JSONB, p_body_digest TEXT, p_actor TEXT, p_needs_second BOOLEAN,
    p_at TIMESTAMPTZ
) RETURNS institutional.pricing_versions
LANGUAGE plpgsql SECURITY DEFINER SET search_path = institutional, business, pg_temp AS $$
DECLARE
    v_row institutional.pricing_versions;
    v_prior TEXT;
BEGIN
    SELECT * INTO v_row FROM institutional.pricing_versions WHERE version_id = p_version_id FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'PRICING_VERSION_NOT_FOUND' USING ERRCODE = 'P0002';
    END IF;
    IF v_row.state NOT IN ('DRAFT', 'SIMULATED') THEN
        RAISE EXCEPTION 'PRICING_ILLEGAL_TRANSITION: % cannot be edited', v_row.state
            USING ERRCODE = '55000';
    END IF;
    v_prior := v_row.state;
    UPDATE institutional.pricing_versions
    SET body = p_body, body_digest = p_body_digest, state = 'DRAFT',
        needs_second_confirmation = COALESCE(p_needs_second, false), second_confirmed_by = NULL
    WHERE version_id = p_version_id
    RETURNING * INTO v_row;
    PERFORM institutional.record_pricing_event(
        gen_random_uuid(), p_version_id, v_prior, 'DRAFT', 'NORMAL', p_actor, p_at, 'EDIT');
    RETURN v_row;
END $$;

CREATE OR REPLACE FUNCTION institutional.transition_pricing_version(
    p_version_id UUID, p_to_state TEXT, p_actor TEXT, p_reason TEXT, p_at TIMESTAMPTZ,
    p_authorized_by TEXT, p_evidence_id UUID, p_effective_from TIMESTAMPTZ,
    p_needs_second BOOLEAN, p_second_confirmed_by TEXT
) RETURNS institutional.pricing_versions
LANGUAGE plpgsql SECURITY DEFINER SET search_path = institutional, business, pg_temp AS $$
DECLARE
    v_row institutional.pricing_versions;
    v_previous institutional.pricing_versions;
    v_has_previous BOOLEAN;
BEGIN
    SELECT * INTO v_row FROM institutional.pricing_versions WHERE version_id = p_version_id FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'PRICING_VERSION_NOT_FOUND' USING ERRCODE = 'P0002';
    END IF;
    PERFORM pg_advisory_xact_lock(hashtextextended(v_row.kind || ':' || v_row.subject_key, 0));
    IF NOT (
        (v_row.state = 'DRAFT' AND p_to_state IN ('SIMULATED', 'DISCARDED'))
        OR (v_row.state = 'SIMULATED' AND p_to_state IN ('SUBMITTED', 'DISCARDED'))
        OR (v_row.state = 'SUBMITTED' AND p_to_state IN ('AUTHORIZED', 'DRAFT', 'DISCARDED'))
        OR (v_row.state = 'AUTHORIZED' AND p_to_state = 'EFFECTIVE')
        OR (v_row.state = 'EFFECTIVE' AND p_to_state = 'SUPERSEDED')
    ) THEN
        RAISE EXCEPTION 'PRICING_ILLEGAL_TRANSITION: % to % is not allowed', v_row.state, p_to_state
            USING ERRCODE = '55000';
    END IF;

    IF p_to_state = 'SIMULATED' THEN
        UPDATE institutional.pricing_versions
        SET state = 'SIMULATED',
            needs_second_confirmation = COALESCE(p_needs_second, v_row.needs_second_confirmation)
        WHERE version_id = p_version_id;
    ELSIF p_to_state = 'SUBMITTED' THEN
        IF v_row.needs_second_confirmation AND p_second_confirmed_by IS NULL THEN
            RAISE EXCEPTION 'PRICING_NEEDS_SECOND_CONFIRMATION' USING ERRCODE = '55000';
        END IF;
        UPDATE institutional.pricing_versions
        SET state = 'SUBMITTED', second_confirmed_by = p_second_confirmed_by
        WHERE version_id = p_version_id;
    ELSIF p_to_state = 'DRAFT' THEN
        UPDATE institutional.pricing_versions
        SET state = 'DRAFT', second_confirmed_by = NULL
        WHERE version_id = p_version_id;
    ELSIF p_to_state = 'AUTHORIZED' THEN
        IF p_authorized_by IS NULL OR p_evidence_id IS NULL THEN
            RAISE EXCEPTION 'PRICING_ILLEGAL_TRANSITION: authorization needs an actor and evidence'
                USING ERRCODE = '55000';
        END IF;
        UPDATE institutional.pricing_versions
        SET state = 'AUTHORIZED', authorized_by = p_authorized_by, authorized_at = p_at,
            evidence_id = p_evidence_id, effective_from = COALESCE(p_effective_from, p_at)
        WHERE version_id = p_version_id;
    ELSIF p_to_state = 'EFFECTIVE' THEN
        IF v_row.effective_from > p_at THEN
            RAISE EXCEPTION 'PRICING_ILLEGAL_TRANSITION: effective_from is in the future'
                USING ERRCODE = '55000';
        END IF;
        SELECT * INTO v_previous FROM institutional.pricing_versions
        WHERE kind = v_row.kind AND subject_key = v_row.subject_key AND state = 'EFFECTIVE'
          AND version_id <> p_version_id
        FOR UPDATE;
        v_has_previous := FOUND;
        IF v_has_previous THEN
            UPDATE institutional.pricing_versions SET state = 'SUPERSEDED'
            WHERE version_id = v_previous.version_id;
            PERFORM institutional.record_pricing_event(
                gen_random_uuid(), v_previous.version_id, 'EFFECTIVE', 'SUPERSEDED', 'NORMAL',
                p_actor, p_at, 'SUPERSEDED_BY ' || p_version_id::TEXT);
        END IF;
        UPDATE institutional.pricing_versions
        SET state = 'EFFECTIVE',
            supersedes = CASE WHEN v_has_previous THEN v_previous.version_id ELSE NULL END
        WHERE version_id = p_version_id;
        IF v_row.kind = 'RATE' THEN
            -- An effective RATE version is the Founder authorization of the catalogue entry (C-091).
            UPDATE institutional.thread_catalog
            SET raw_cost_inr_paise = (v_row.body ->> 'rawCostPaise')::INTEGER,
                fx_buffer_pct = (v_row.body ->> 'fxBufferPct')::NUMERIC,
                operational_overhead_pct = (v_row.body ->> 'opsOverheadPct')::NUMERIC,
                risk_premium_pct = (v_row.body ->> 'riskPremiumPct')::NUMERIC,
                provider = COALESCE(left(v_row.body ->> 'provider', 100), provider),
                unit_description = COALESCE(left(v_row.body ->> 'unit', 100), unit_description),
                status = 'ACTIVE', founder_authorized_at = v_row.authorized_at,
                founder_authorized_by = left(v_row.authorized_by, 100), updated_at = p_at
            WHERE thread_id = v_row.body ->> 'threadId';
            IF NOT FOUND THEN
                RAISE EXCEPTION 'PRICING_DRAFT_INVALID: the catalogue entry does not exist'
                    USING ERRCODE = '55000';
            END IF;
        END IF;
    ELSE
        UPDATE institutional.pricing_versions SET state = p_to_state WHERE version_id = p_version_id;
    END IF;

    PERFORM institutional.record_pricing_event(
        gen_random_uuid(), p_version_id, v_row.state, p_to_state, 'NORMAL', p_actor, p_at, p_reason);
    SELECT * INTO v_row FROM institutional.pricing_versions WHERE version_id = p_version_id;
    RETURN v_row;
END $$;

CREATE OR REPLACE FUNCTION institutional.apply_pricing_safety_successor(
    p_event_id UUID, p_kind TEXT, p_subject_key TEXT, p_body JSONB, p_body_digest TEXT,
    p_actor TEXT, p_reason TEXT, p_at TIMESTAMPTZ
) RETURNS institutional.pricing_versions
LANGUAGE plpgsql SECURITY DEFINER SET search_path = institutional, business, pg_temp AS $$
DECLARE
    v_previous institutional.pricing_versions;
    v_next INTEGER;
    v_row institutional.pricing_versions;
BEGIN
    IF p_kind NOT IN ('BUDGET', 'GRANT') THEN
        RAISE EXCEPTION 'PRICING_ILLEGAL_TRANSITION: safety successor applies to BUDGET and GRANT only'
            USING ERRCODE = '55000';
    END IF;
    PERFORM pg_advisory_xact_lock(hashtextextended(p_kind || ':' || p_subject_key, 0));
    SELECT * INTO v_previous FROM institutional.pricing_versions
    WHERE kind = p_kind AND subject_key = p_subject_key AND state = 'EFFECTIVE'
    FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'PRICING_VERSION_NOT_FOUND' USING ERRCODE = 'P0002';
    END IF;
    SELECT COALESCE(MAX(version_no), 0) + 1 INTO v_next
    FROM institutional.pricing_versions WHERE kind = p_kind AND subject_key = p_subject_key;
    UPDATE institutional.pricing_versions SET state = 'SUPERSEDED' WHERE version_id = v_previous.version_id;
    INSERT INTO institutional.pricing_versions
        (version_id, kind, subject_key, version_no, state, body, body_digest, effective_from,
         supersedes, created_by, created_at, authorized_by, authorized_at, evidence_id)
    VALUES (gen_random_uuid(), p_kind, p_subject_key, v_next, 'EFFECTIVE', p_body, p_body_digest, p_at,
            v_previous.version_id, p_actor, p_at, p_actor, p_at, p_event_id)
    RETURNING * INTO v_row;
    PERFORM institutional.record_pricing_event(
        gen_random_uuid(), v_previous.version_id, 'EFFECTIVE', 'SUPERSEDED', 'SAFETY', p_actor, p_at,
        p_reason);
    PERFORM institutional.record_pricing_event(
        p_event_id, v_row.version_id, NULL, 'EFFECTIVE', 'SAFETY', p_actor, p_at, p_reason);
    RETURN v_row;
END $$;

CREATE OR REPLACE FUNCTION institutional.project_package_profile(
    p_version_id UUID, p_thread_rations JSONB, p_cost_floor_paise INTEGER,
    p_infrastructure_share_paise INTEGER, p_minimum_margin_pct NUMERIC, p_display_name TEXT
) RETURNS UUID
LANGUAGE plpgsql SECURITY DEFINER SET search_path = institutional, business, pg_temp AS $$
DECLARE
    v_row institutional.pricing_versions;
    v_profile_id UUID;
BEGIN
    SELECT * INTO v_row FROM institutional.pricing_versions WHERE version_id = p_version_id;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'PRICING_VERSION_NOT_FOUND' USING ERRCODE = 'P0002';
    END IF;
    IF v_row.kind <> 'PACKAGE' OR v_row.state NOT IN ('AUTHORIZED', 'EFFECTIVE') THEN
        RAISE EXCEPTION 'PRICING_ILLEGAL_TRANSITION: only authorized packages are projected'
            USING ERRCODE = '55000';
    END IF;
    INSERT INTO institutional.bundle_profiles
        (agent_type, agent_version, bundle_tier, bundle_version, display_name, thread_rations,
         infrastructure_share_paise, cost_floor_paise, minimum_margin_pct, status,
         founder_authorized_at, is_active, package_version_id)
    VALUES (v_row.body ->> 'agentType', v_row.body ->> 'agentVersion', v_row.body ->> 'packageCode',
            v_row.version_no, left(p_display_name, 100), p_thread_rations,
            p_infrastructure_share_paise, p_cost_floor_paise, p_minimum_margin_pct,
            'FOUNDER_AUTHORIZED', v_row.authorized_at, false, v_row.version_id)
    ON CONFLICT (agent_type, agent_version, bundle_tier, bundle_version) DO UPDATE
    SET display_name = EXCLUDED.display_name, thread_rations = EXCLUDED.thread_rations,
        infrastructure_share_paise = EXCLUDED.infrastructure_share_paise,
        cost_floor_paise = EXCLUDED.cost_floor_paise,
        minimum_margin_pct = EXCLUDED.minimum_margin_pct, status = EXCLUDED.status,
        founder_authorized_at = EXCLUDED.founder_authorized_at,
        package_version_id = EXCLUDED.package_version_id
    RETURNING id INTO v_profile_id;
    RETURN v_profile_id;
END $$;

CREATE OR REPLACE FUNCTION institutional.set_package_sale_state(
    p_version_id UUID, p_for_sale BOOLEAN, p_direction TEXT, p_actor TEXT, p_reason TEXT,
    p_at TIMESTAMPTZ
) RETURNS BOOLEAN
LANGUAGE plpgsql SECURITY DEFINER SET search_path = institutional, business, pg_temp AS $$
DECLARE
    v_row institutional.pricing_versions;
    v_count INTEGER;
BEGIN
    SELECT * INTO v_row FROM institutional.pricing_versions WHERE version_id = p_version_id FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'PRICING_VERSION_NOT_FOUND' USING ERRCODE = 'P0002';
    END IF;
    IF v_row.kind <> 'PACKAGE' OR v_row.state <> 'EFFECTIVE' THEN
        RAISE EXCEPTION 'PRICING_ILLEGAL_TRANSITION: sale state applies to an effective package'
            USING ERRCODE = '55000';
    END IF;
    IF p_for_sale THEN
        UPDATE institutional.bundle_profiles SET is_active = false
        WHERE agent_type = v_row.body ->> 'agentType'
          AND agent_version = v_row.body ->> 'agentVersion'
          AND bundle_tier = v_row.body ->> 'packageCode'
          AND package_version_id IS DISTINCT FROM p_version_id
          AND is_active;
    END IF;
    UPDATE institutional.bundle_profiles SET is_active = p_for_sale
    WHERE package_version_id = p_version_id;
    GET DIAGNOSTICS v_count = ROW_COUNT;
    IF v_count = 0 THEN
        RAISE EXCEPTION 'PRICING_VERSION_NOT_FOUND: package profile is not projected'
            USING ERRCODE = 'P0002';
    END IF;
    PERFORM institutional.record_pricing_event(
        gen_random_uuid(), p_version_id, 'EFFECTIVE', 'EFFECTIVE', p_direction, p_actor, p_at, p_reason);
    RETURN p_for_sale;
END $$;

REVOKE ALL ON institutional.pricing_versions, institutional.pricing_version_events,
    business.component_units, business.component_unit_entries FROM PUBLIC, business_app;
GRANT SELECT ON institutional.pricing_versions, institutional.pricing_version_events TO wbe_app;
GRANT SELECT, INSERT ON business.component_units, business.component_unit_entries TO wbe_app;

REVOKE ALL ON FUNCTION
    institutional.record_pricing_event(UUID, UUID, TEXT, TEXT, TEXT, TEXT, TIMESTAMPTZ, TEXT),
    institutional.create_pricing_draft(UUID, TEXT, TEXT, JSONB, TEXT, TEXT, BOOLEAN, TIMESTAMPTZ),
    institutional.edit_pricing_draft(UUID, JSONB, TEXT, TEXT, BOOLEAN, TIMESTAMPTZ),
    institutional.transition_pricing_version(
        UUID, TEXT, TEXT, TEXT, TIMESTAMPTZ, TEXT, UUID, TIMESTAMPTZ, BOOLEAN, TEXT),
    institutional.apply_pricing_safety_successor(
        UUID, TEXT, TEXT, JSONB, TEXT, TEXT, TEXT, TIMESTAMPTZ),
    institutional.project_package_profile(UUID, JSONB, INTEGER, INTEGER, NUMERIC, TEXT),
    institutional.set_package_sale_state(UUID, BOOLEAN, TEXT, TEXT, TEXT, TIMESTAMPTZ)
    FROM PUBLIC, business_app;
GRANT EXECUTE ON FUNCTION
    institutional.create_pricing_draft(UUID, TEXT, TEXT, JSONB, TEXT, TEXT, BOOLEAN, TIMESTAMPTZ),
    institutional.edit_pricing_draft(UUID, JSONB, TEXT, TEXT, BOOLEAN, TIMESTAMPTZ),
    institutional.transition_pricing_version(
        UUID, TEXT, TEXT, TEXT, TIMESTAMPTZ, TEXT, UUID, TIMESTAMPTZ, BOOLEAN, TEXT),
    institutional.apply_pricing_safety_successor(
        UUID, TEXT, TEXT, JSONB, TEXT, TEXT, TEXT, TIMESTAMPTZ),
    institutional.project_package_profile(UUID, JSONB, INTEGER, INTEGER, NUMERIC, TEXT),
    institutional.set_package_sale_state(UUID, BOOLEAN, TEXT, TEXT, TEXT, TIMESTAMPTZ)
    TO wbe_app;
RESET ROLE;

SET LOCAL ROLE bp_owner;
REVOKE CREATE ON SCHEMA institutional, business FROM wbe_owner;
RESET ROLE;
DO $owner$
BEGIN
    IF current_setting('waooaw.wc136_pricing_wbe_owner_granted', true) = 'true' THEN
        EXECUTE format('REVOKE wbe_owner FROM %I', session_user);
    END IF;
    IF current_setting('waooaw.wc136_pricing_bp_owner_granted', true) = 'true' THEN
        EXECUTE format('REVOKE bp_owner FROM %I', session_user);
    END IF;
END
$owner$;
COMMIT;
