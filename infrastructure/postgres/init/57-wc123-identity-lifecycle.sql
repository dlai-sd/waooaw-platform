-- WC-123 durable provider lifecycle operation and projection authority.

CREATE TABLE IF NOT EXISTS identity.lifecycle_operations (
    operation_id uuid PRIMARY KEY,
    actor_issuer varchar(256) COLLATE "C" NOT NULL,
    actor_subject varchar(256) COLLATE "C" NOT NULL,
    command_type varchar(24) NOT NULL,
    provider_class varchar(16) NOT NULL,
    idempotency_key_version varchar(32) NOT NULL,
    idempotency_digest varchar(128) COLLATE "C" NOT NULL,
    target_link_reference uuid NOT NULL,
    state varchar(32) NOT NULL,
    attempt integer NOT NULL DEFAULT 0,
    version integer NOT NULL DEFAULT 1,
    correlation_id uuid NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    terminal_at timestamptz,
    CONSTRAINT lifecycle_operations_command_check
        CHECK (command_type IN ('LINK', 'UNLINK', 'RECOVERY')),
    CONSTRAINT lifecycle_operations_provider_check
        CHECK (provider_class IN ('GOOGLE', 'FACEBOOK', 'APPLE', 'EMAIL')),
    CONSTRAINT lifecycle_operations_state_check
        CHECK (state IN (
            'PROOF_REQUIRED',
            'IDP_PENDING',
            'IDP_COMMITTED',
            'COMPLETED',
            'FAILED',
            'RECOVERY_REQUIRED'
        )),
    CONSTRAINT lifecycle_operations_terminal_check CHECK (
        (state IN ('COMPLETED', 'FAILED') AND terminal_at IS NOT NULL)
        OR (state NOT IN ('COMPLETED', 'FAILED') AND terminal_at IS NULL)
    ),
    CONSTRAINT lifecycle_operations_idempotency_unique
        UNIQUE (actor_issuer, actor_subject, command_type, idempotency_digest)
);

CREATE TABLE IF NOT EXISTS identity.provider_link_projections (
    link_id uuid PRIMARY KEY,
    global_user_id uuid NOT NULL,
    provider_class varchar(16) NOT NULL,
    binding_reference uuid NOT NULL,
    state varchar(24) NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    retired_at timestamptz,
    CONSTRAINT provider_link_projections_provider_check
        CHECK (provider_class IN ('GOOGLE', 'FACEBOOK', 'APPLE', 'EMAIL')),
    CONSTRAINT provider_link_projections_state_check
        CHECK (state IN ('ACTIVE', 'RETIRED', 'RECOVERY_REQUIRED')),
    CONSTRAINT provider_link_projections_retired_check CHECK (
        (state = 'RETIRED' AND retired_at IS NOT NULL)
        OR (state <> 'RETIRED' AND retired_at IS NULL)
    ),
    CONSTRAINT provider_link_projections_binding_unique UNIQUE (binding_reference)
);

CREATE INDEX IF NOT EXISTS lifecycle_operations_actor_state_idx
    ON identity.lifecycle_operations (actor_issuer, actor_subject, state);
CREATE INDEX IF NOT EXISTS provider_link_projections_user_state_idx
    ON identity.provider_link_projections (global_user_id, state);

ALTER TABLE identity.lifecycle_operations ENABLE ROW LEVEL SECURITY;
ALTER TABLE identity.lifecycle_operations FORCE ROW LEVEL SECURITY;
ALTER TABLE identity.provider_link_projections ENABLE ROW LEVEL SECURITY;
ALTER TABLE identity.provider_link_projections FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS actor_scope ON identity.lifecycle_operations;
CREATE POLICY actor_scope ON identity.lifecycle_operations TO business_app
    USING (
        actor_issuer =
            NULLIF(pg_catalog.current_setting('app.identity_issuer', true), '') COLLATE "C"
        AND actor_subject =
            NULLIF(pg_catalog.current_setting('app.identity_subject', true), '') COLLATE "C"
        AND EXISTS (
            SELECT 1
            FROM identity.actor_bindings AS binding
            JOIN identity.memberships AS membership
              ON membership.account_id = binding.account_id
            WHERE binding.actor_issuer = lifecycle_operations.actor_issuer
              AND binding.actor_subject = lifecycle_operations.actor_subject
              AND binding.status = 'ACTIVE'
              AND membership.status = 'ACTIVE'
        )
    )
    WITH CHECK (
        actor_issuer =
            NULLIF(pg_catalog.current_setting('app.identity_issuer', true), '') COLLATE "C"
        AND actor_subject =
            NULLIF(pg_catalog.current_setting('app.identity_subject', true), '') COLLATE "C"
        AND EXISTS (
            SELECT 1
            FROM identity.actor_bindings AS binding
            JOIN identity.memberships AS membership
              ON membership.account_id = binding.account_id
            WHERE binding.actor_issuer = lifecycle_operations.actor_issuer
              AND binding.actor_subject = lifecycle_operations.actor_subject
              AND binding.status = 'ACTIVE'
              AND membership.status = 'ACTIVE'
        )
    );

DROP POLICY IF EXISTS actor_scope ON identity.provider_link_projections;
CREATE POLICY actor_scope ON identity.provider_link_projections TO business_app
    USING (
        EXISTS (
            SELECT 1
            FROM identity.lifecycle_operations AS operation
            WHERE operation.target_link_reference = provider_link_projections.link_id
              AND operation.actor_issuer =
                  NULLIF(pg_catalog.current_setting('app.identity_issuer', true), '') COLLATE "C"
              AND operation.actor_subject =
                  NULLIF(pg_catalog.current_setting('app.identity_subject', true), '') COLLATE "C"
        )
    )
    WITH CHECK (
        EXISTS (
            SELECT 1
            FROM identity.lifecycle_operations AS operation
            WHERE operation.target_link_reference = provider_link_projections.link_id
              AND operation.actor_issuer =
                  NULLIF(pg_catalog.current_setting('app.identity_issuer', true), '') COLLATE "C"
              AND operation.actor_subject =
                  NULLIF(pg_catalog.current_setting('app.identity_subject', true), '') COLLATE "C"
        )
    );

REVOKE ALL ON identity.lifecycle_operations FROM PUBLIC;
REVOKE ALL ON identity.provider_link_projections FROM PUBLIC;
GRANT SELECT, INSERT, UPDATE ON identity.lifecycle_operations TO business_app;
GRANT SELECT, INSERT, UPDATE ON identity.provider_link_projections TO business_app;

CREATE OR REPLACE FUNCTION identity.lifecycle_history_is_immutable()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog
AS $function$
BEGIN
    IF OLD.operation_id <> NEW.operation_id
       OR OLD.actor_issuer <> NEW.actor_issuer
       OR OLD.actor_subject <> NEW.actor_subject
       OR OLD.command_type <> NEW.command_type
       OR OLD.provider_class <> NEW.provider_class
       OR OLD.idempotency_key_version <> NEW.idempotency_key_version
       OR OLD.idempotency_digest <> NEW.idempotency_digest
       OR OLD.target_link_reference <> NEW.target_link_reference
       OR OLD.correlation_id <> NEW.correlation_id
       OR OLD.created_at <> NEW.created_at
       OR NEW.version <> OLD.version + 1
       OR NEW.attempt < OLD.attempt
       OR OLD.state IN ('COMPLETED', 'FAILED')
    THEN
        RAISE EXCEPTION 'lifecycle operation immutable history violation'
            USING ERRCODE = '42501';
    END IF;
    NEW.updated_at := now();
    RETURN NEW;
END
$function$;

CREATE OR REPLACE TRIGGER lifecycle_operations_immutable
BEFORE UPDATE ON identity.lifecycle_operations
FOR EACH ROW EXECUTE FUNCTION identity.lifecycle_history_is_immutable();

CREATE OR REPLACE FUNCTION identity.provider_link_key_is_immutable()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog
AS $function$
BEGIN
    IF OLD.link_id <> NEW.link_id
       OR OLD.global_user_id <> NEW.global_user_id
       OR OLD.provider_class <> NEW.provider_class
       OR OLD.binding_reference <> NEW.binding_reference
       OR OLD.created_at <> NEW.created_at
       OR OLD.state = 'RETIRED'
       OR (OLD.state = 'RECOVERY_REQUIRED' AND NEW.state <> 'RETIRED')
       OR (OLD.state = 'ACTIVE' AND NEW.state = 'ACTIVE')
    THEN
        RAISE EXCEPTION 'provider link immutable key violation'
            USING ERRCODE = '42501';
    END IF;
    RETURN NEW;
END
$function$;

CREATE OR REPLACE TRIGGER provider_link_projections_immutable
BEFORE UPDATE ON identity.provider_link_projections
FOR EACH ROW EXECUTE FUNCTION identity.provider_link_key_is_immutable();

CREATE OR REPLACE FUNCTION identity.lifecycle_history_delete_denied()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog
AS $function$
BEGIN
    RAISE EXCEPTION 'identity lifecycle history cannot be deleted'
        USING ERRCODE = '42501';
END
$function$;

CREATE OR REPLACE TRIGGER lifecycle_operations_delete_denied
BEFORE DELETE ON identity.lifecycle_operations
FOR EACH ROW EXECUTE FUNCTION identity.lifecycle_history_delete_denied();
CREATE OR REPLACE TRIGGER provider_link_projections_delete_denied
BEFORE DELETE ON identity.provider_link_projections
FOR EACH ROW EXECUTE FUNCTION identity.lifecycle_history_delete_denied();

REVOKE ALL ON FUNCTION identity.lifecycle_history_is_immutable() FROM PUBLIC;
REVOKE ALL ON FUNCTION identity.provider_link_key_is_immutable() FROM PUBLIC;
REVOKE ALL ON FUNCTION identity.lifecycle_history_delete_denied() FROM PUBLIC;
