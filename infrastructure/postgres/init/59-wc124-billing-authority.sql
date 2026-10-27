-- Implements: architecture/reference/components/demo-uat-persistent-state-lifecycle-work-component.md §8
-- Constitutional basis: C-005, C-023, C-026, C-059, C-080, C-091

BEGIN;

-- The provisioner (PostgreSQL 16 CREATEROLE admin, implicit ADMIN without SET) needs temporary
-- settable membership. The restricted billing_migrator already holds it without ADMIN OPTION, so
-- it must neither grant nor revoke it (Demo run 40530276041).
DO $bootstrap_membership$
BEGIN
    IF NOT pg_has_role(session_user, 'billing_owner', 'SET') THEN
        EXECUTE format('GRANT billing_owner TO %I', session_user);
        PERFORM set_config('waooaw.wc124_billing_owner_granted', 'true', true);
    END IF;
END
$bootstrap_membership$;

DO $preflight$
DECLARE
    schema_owner text;
BEGIN
    SELECT pg_get_userbyid(nspowner)
    INTO schema_owner
    FROM pg_namespace
    WHERE nspname = 'billing';

    IF schema_owner IS NULL THEN
        RAISE EXCEPTION 'billing schema must be provisioned before migration';
    END IF;
    IF schema_owner <> 'billing_owner' THEN
        RAISE EXCEPTION 'billing schema owner must be billing_owner, found %', schema_owner;
    END IF;
    IF NOT pg_has_role(session_user, 'billing_owner', 'SET') THEN
        RAISE EXCEPTION '% cannot assume billing_owner', session_user;
    END IF;
END
$preflight$;

SET LOCAL ROLE billing_owner;

CREATE OR REPLACE FUNCTION billing.reject_authority_history_mutation()
RETURNS trigger
LANGUAGE plpgsql
AS $function$
BEGIN
    RAISE EXCEPTION 'billing authority history is append-only';
END
$function$;
ALTER FUNCTION billing.reject_authority_history_mutation() OWNER TO billing_owner;

CREATE TABLE IF NOT EXISTS billing.integrity_states (
    environment varchar(16) COLLATE "C" NOT NULL,
    tenant_id uuid NOT NULL,
    accounting_scope_id uuid NOT NULL,
    state varchar(32) COLLATE "C" NOT NULL,
    active_halt_event_id uuid,
    state_version bigint NOT NULL DEFAULT 1 CHECK (state_version > 0),
    updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    CONSTRAINT integrity_states_pk
        PRIMARY KEY (environment, tenant_id, accounting_scope_id),
    CONSTRAINT integrity_states_environment_check
        CHECK (environment IN ('demo', 'uat')),
    CONSTRAINT integrity_states_state_check
        CHECK (state IN ('CLEAR', 'HALTED', 'RECONCILIATION_REQUIRED')),
    CONSTRAINT integrity_states_halt_check
        CHECK (
            (state = 'CLEAR' AND active_halt_event_id IS NULL)
            OR (state <> 'CLEAR' AND active_halt_event_id IS NOT NULL)
        )
);

CREATE TABLE IF NOT EXISTS billing.integrity_events (
    event_id uuid PRIMARY KEY,
    environment varchar(16) COLLATE "C" NOT NULL,
    tenant_id uuid NOT NULL,
    accounting_scope_id uuid NOT NULL,
    event_type varchar(32) COLLATE "C" NOT NULL,
    prior_state varchar(32) COLLATE "C" NOT NULL,
    resulting_state varchar(32) COLLATE "C" NOT NULL,
    discrepancy_paise bigint,
    actor_id varchar(256) COLLATE "C" NOT NULL,
    authority_reference varchar(256) COLLATE "C" NOT NULL,
    reason varchar(1024) COLLATE "C" NOT NULL,
    evidence_reference varchar(256) COLLATE "C" NOT NULL,
    occurred_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    CONSTRAINT integrity_events_environment_check
        CHECK (environment IN ('demo', 'uat')),
    CONSTRAINT integrity_events_type_check
        CHECK (event_type IN ('HALT', 'RELEASE', 'RECONCILIATION_REQUIRED')),
    CONSTRAINT integrity_events_prior_state_check
        CHECK (prior_state IN ('CLEAR', 'HALTED', 'RECONCILIATION_REQUIRED')),
    CONSTRAINT integrity_events_resulting_state_check
        CHECK (resulting_state IN ('CLEAR', 'HALTED', 'RECONCILIATION_REQUIRED')),
    CONSTRAINT integrity_events_transition_check
        CHECK (
            (event_type = 'HALT' AND resulting_state = 'HALTED' AND discrepancy_paise > 1)
            OR (
                event_type = 'RELEASE'
                AND prior_state IN ('HALTED', 'RECONCILIATION_REQUIRED')
                AND resulting_state = 'CLEAR'
                AND discrepancy_paise IS NULL
            )
            OR (
                event_type = 'RECONCILIATION_REQUIRED'
                AND resulting_state = 'RECONCILIATION_REQUIRED'
            )
        )
);

ALTER TABLE billing.integrity_states
    DROP CONSTRAINT IF EXISTS integrity_states_active_halt_fk;
DO $idempotent$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'integrity_states_active_halt_fk' AND conrelid = 'billing.integrity_states'::regclass) THEN
        ALTER TABLE billing.integrity_states
            ADD CONSTRAINT integrity_states_active_halt_fk
            FOREIGN KEY (active_halt_event_id)
            REFERENCES billing.integrity_events(event_id)
            ON DELETE RESTRICT
            DEFERRABLE INITIALLY DEFERRED;
    END IF;
END
$idempotent$;

CREATE TABLE IF NOT EXISTS billing.reconciliation_executions (
    execution_id uuid PRIMARY KEY,
    environment varchar(16) COLLATE "C" NOT NULL,
    tenant_id uuid NOT NULL,
    accounting_scope_id uuid NOT NULL,
    reconciliation_type varchar(64) COLLATE "C" NOT NULL,
    covered_period_start timestamptz NOT NULL,
    covered_period_end timestamptz NOT NULL,
    source_watermark varchar(256) COLLATE "C" NOT NULL,
    execution_key char(64) COLLATE "C" NOT NULL,
    payload_digest char(64) COLLATE "C" NOT NULL,
    status varchar(32) COLLATE "C" NOT NULL,
    claim_owner uuid,
    claim_expires_at timestamptz,
    attempt_count integer NOT NULL DEFAULT 1 CHECK (attempt_count > 0),
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    CONSTRAINT reconciliation_executions_key_unique UNIQUE (execution_key),
    CONSTRAINT reconciliation_executions_identity_unique UNIQUE (
        environment,
        tenant_id,
        accounting_scope_id,
        reconciliation_type,
        covered_period_start,
        covered_period_end,
        source_watermark
    ),
    CONSTRAINT reconciliation_executions_environment_check
        CHECK (environment IN ('demo', 'uat')),
    CONSTRAINT reconciliation_executions_period_check
        CHECK (covered_period_end > covered_period_start),
    CONSTRAINT reconciliation_executions_key_check
        CHECK (execution_key ~ '^[0-9a-f]{64}$'),
    CONSTRAINT reconciliation_executions_digest_check
        CHECK (payload_digest ~ '^[0-9a-f]{64}$'),
    CONSTRAINT reconciliation_executions_status_check
        CHECK (
            status IN (
                'CLAIMED',
                'RUNNING',
                'COMMITTED',
                'FAILED_RETRYABLE',
                'FAILED_FINAL',
                'RECONCILIATION_REQUIRED'
            )
        ),
    CONSTRAINT reconciliation_executions_claim_check
        CHECK ((claim_owner IS NULL) = (claim_expires_at IS NULL))
);

CREATE TABLE IF NOT EXISTS billing.reconciliation_outcomes (
    outcome_id uuid PRIMARY KEY,
    execution_id uuid NOT NULL UNIQUE
        REFERENCES billing.reconciliation_executions(execution_id) ON DELETE RESTRICT,
    environment varchar(16) COLLATE "C" NOT NULL,
    tenant_id uuid NOT NULL,
    accounting_scope_id uuid NOT NULL,
    outcome varchar(32) COLLATE "C" NOT NULL,
    discrepancy_paise bigint NOT NULL,
    result_digest char(64) COLLATE "C" NOT NULL,
    evidence_reference varchar(256) COLLATE "C" NOT NULL,
    committed_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    CONSTRAINT reconciliation_outcomes_environment_check
        CHECK (environment IN ('demo', 'uat')),
    CONSTRAINT reconciliation_outcomes_outcome_check
        CHECK (outcome IN ('PASS', 'HALTED', 'RECONCILIATION_REQUIRED', 'FAILED_FINAL')),
    CONSTRAINT reconciliation_outcomes_digest_check
        CHECK (result_digest ~ '^[0-9a-f]{64}$')
);

CREATE TABLE IF NOT EXISTS billing.discrepancy_evidence (
    evidence_id uuid PRIMARY KEY,
    execution_id uuid NOT NULL
        REFERENCES billing.reconciliation_executions(execution_id) ON DELETE RESTRICT,
    outcome_id uuid
        REFERENCES billing.reconciliation_outcomes(outcome_id) ON DELETE RESTRICT,
    environment varchar(16) COLLATE "C" NOT NULL,
    tenant_id uuid NOT NULL,
    accounting_scope_id uuid NOT NULL,
    subject_type varchar(64) COLLATE "C" NOT NULL,
    subject_reference varchar(256) COLLATE "C" NOT NULL,
    expected_paise bigint NOT NULL,
    actual_paise bigint NOT NULL,
    discrepancy_paise bigint GENERATED ALWAYS AS (actual_paise - expected_paise) STORED,
    evidence_reference varchar(256) COLLATE "C" NOT NULL,
    recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    CONSTRAINT discrepancy_evidence_environment_check
        CHECK (environment IN ('demo', 'uat'))
);

CREATE TABLE IF NOT EXISTS billing.audit_results (
    audit_result_id uuid PRIMARY KEY,
    execution_id uuid NOT NULL
        REFERENCES billing.reconciliation_executions(execution_id) ON DELETE RESTRICT,
    environment varchar(16) COLLATE "C" NOT NULL,
    tenant_id uuid NOT NULL,
    accounting_scope_id uuid NOT NULL,
    audit_type varchar(64) COLLATE "C" NOT NULL,
    outcome varchar(32) COLLATE "C" NOT NULL,
    result_digest char(64) COLLATE "C" NOT NULL,
    evidence_reference varchar(256) COLLATE "C" NOT NULL,
    completed_at timestamptz NOT NULL,
    CONSTRAINT audit_results_environment_check
        CHECK (environment IN ('demo', 'uat')),
    CONSTRAINT audit_results_digest_check
        CHECK (result_digest ~ '^[0-9a-f]{64}$')
);

CREATE TABLE IF NOT EXISTS billing.audit_projections (
    environment varchar(16) COLLATE "C" NOT NULL,
    tenant_id uuid NOT NULL,
    accounting_scope_id uuid NOT NULL,
    audit_type varchar(64) COLLATE "C" NOT NULL,
    last_audit_result_id uuid NOT NULL
        REFERENCES billing.audit_results(audit_result_id) ON DELETE RESTRICT,
    last_completed_at timestamptz NOT NULL,
    projection_version bigint NOT NULL DEFAULT 1 CHECK (projection_version > 0),
    CONSTRAINT audit_projections_pk
        PRIMARY KEY (environment, tenant_id, accounting_scope_id, audit_type),
    CONSTRAINT audit_projections_environment_check
        CHECK (environment IN ('demo', 'uat'))
);

DO $ownership$
DECLARE
    table_name text;
BEGIN
    FOREACH table_name IN ARRAY ARRAY[
        'integrity_states',
        'integrity_events',
        'reconciliation_executions',
        'reconciliation_outcomes',
        'discrepancy_evidence',
        'audit_results',
        'audit_projections'
    ]
    LOOP
        EXECUTE format('ALTER TABLE billing.%I OWNER TO billing_owner', table_name);
        EXECUTE format('ALTER TABLE billing.%I ENABLE ROW LEVEL SECURITY', table_name);
        EXECUTE format('ALTER TABLE billing.%I FORCE ROW LEVEL SECURITY', table_name);
    END LOOP;
END
$ownership$;

DO $policies$
DECLARE
    table_name text;
BEGIN
    FOREACH table_name IN ARRAY ARRAY[
        'integrity_states',
        'integrity_events',
        'reconciliation_executions',
        'reconciliation_outcomes',
        'discrepancy_evidence',
        'audit_results',
        'audit_projections'
    ]
    LOOP
        EXECUTE format('DROP POLICY IF EXISTS billing_scope_isolation ON billing.%I', table_name);
        EXECUTE format(
            'CREATE POLICY billing_scope_isolation ON billing.%I '
            'USING (environment = NULLIF(current_setting(''app.current_environment'', true), '''') '
            'AND tenant_id = NULLIF(current_setting(''app.current_tenant_id'', true), '''')::uuid) '
            'WITH CHECK (environment = NULLIF(current_setting(''app.current_environment'', true), '''') '
            'AND tenant_id = NULLIF(current_setting(''app.current_tenant_id'', true), '''')::uuid)',
            table_name
        );
    END LOOP;
END
$policies$;

DO $append_only$
DECLARE
    table_name text;
BEGIN
    FOREACH table_name IN ARRAY ARRAY[
        'integrity_events',
        'reconciliation_outcomes',
        'discrepancy_evidence',
        'audit_results'
    ]
    LOOP
        IF NOT EXISTS (
            SELECT 1
            FROM pg_trigger
            WHERE tgname = table_name || '_append_only'
              AND tgrelid = format('billing.%I', table_name)::regclass
              AND NOT tgisinternal
        ) THEN
            EXECUTE format(
                'CREATE TRIGGER %I BEFORE UPDATE OR DELETE ON billing.%I '
                'FOR EACH ROW EXECUTE FUNCTION billing.reject_authority_history_mutation()',
                table_name || '_append_only',
                table_name
            );
        END IF;
    END LOOP;
END
$append_only$;

REVOKE ALL ON ALL TABLES IN SCHEMA billing FROM PUBLIC;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA billing FROM PUBLIC;
REVOKE ALL ON FUNCTION billing.reject_authority_history_mutation() FROM PUBLIC;

GRANT USAGE ON SCHEMA billing TO billing_migrator, billing_runtime, billing_verifier;
GRANT SELECT, INSERT, UPDATE ON billing.integrity_states TO billing_runtime;
GRANT SELECT, INSERT ON billing.integrity_events TO billing_runtime;
GRANT SELECT, INSERT, UPDATE ON billing.reconciliation_executions TO billing_runtime;
GRANT SELECT, INSERT ON billing.reconciliation_outcomes TO billing_runtime;
GRANT SELECT, INSERT ON billing.discrepancy_evidence TO billing_runtime;
GRANT SELECT, INSERT ON billing.audit_results TO billing_runtime;
GRANT SELECT, INSERT, UPDATE ON billing.audit_projections TO billing_runtime;
GRANT SELECT ON ALL TABLES IN SCHEMA billing TO billing_verifier;

RESET ROLE;
DO $bootstrap_membership$
BEGIN
    IF current_setting('waooaw.wc124_billing_owner_granted', true) = 'true' THEN
        EXECUTE format('REVOKE billing_owner FROM %I', session_user);
    END IF;
END
$bootstrap_membership$;

COMMIT;
