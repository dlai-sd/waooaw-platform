-- Implements: architecture/reference/product/wc085-identity-provisioning-data-contract.md CURRENT Sections 1-6
-- constitutional_basis: C-005, C-007, C-026, C-059

BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '30s';

ALTER SCHEMA business OWNER TO CURRENT_USER;
ALTER SCHEMA identity OWNER TO CURRENT_USER;
REVOKE CREATE ON SCHEMA business, identity, public
    FROM PUBLIC, business_app, constitutional_app, runtime_app, wbe_app;
GRANT USAGE ON SCHEMA business, identity TO business_app, constitutional_app, runtime_app, wbe_app;
CREATE ROLE identity_resolver_owner NOLOGIN NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE NOREPLICATION;
GRANT USAGE ON SCHEMA identity, business TO identity_resolver_owner;
ALTER DEFAULT PRIVILEGES REVOKE EXECUTE ON FUNCTIONS FROM PUBLIC;

DO $permissions$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_roles AS app JOIN pg_roles AS inherited
          ON pg_has_role(app.oid, inherited.oid, 'MEMBER')
        WHERE app.rolname IN ('business_app', 'constitutional_app', 'runtime_app', 'wbe_app')
          AND (inherited.rolsuper OR inherited.rolbypassrls OR inherited.rolcreaterole
            OR inherited.rolname IN (current_user, 'identity_resolver_owner'))
    ) THEN
        RAISE EXCEPTION 'unsafe application role inheritance';
    END IF;
END;
$permissions$;

ALTER TABLE business.organisations
    ADD COLUMN identity_managed boolean NOT NULL DEFAULT false,
    ADD COLUMN identity_status varchar(24) NOT NULL DEFAULT 'LEGACY_UNVERIFIED'
        CHECK (identity_status IN ('LEGACY_UNVERIFIED', 'ACTIVE', 'INACTIVE')),
    ADD CONSTRAINT organisations_managed_identity_check CHECK (
        NOT identity_managed OR (id = tenant_id AND identity_status IN ('ACTIVE', 'INACTIVE')));

ALTER TABLE identity.registrations
    ADD COLUMN actor_issuer varchar(256) COLLATE "C" CHECK (octet_length(actor_issuer) > 0),
    ALTER COLUMN actor_subject TYPE varchar(256) COLLATE "C",
    ADD COLUMN actor_binding_id uuid,
    ADD COLUMN origin_registration_id uuid REFERENCES identity.registrations(registration_id) ON DELETE RESTRICT,
    ADD COLUMN completed_at timestamptz,
    ADD COLUMN completion_outcome varchar(24) CHECK (completion_outcome IN ('ACCOUNT_CREATED', 'ACCOUNT_REUSED')),
    ADD COLUMN completion_profile_snapshot jsonb CHECK (jsonb_typeof(completion_profile_snapshot) = 'object'),
    ADD COLUMN completion_status_code integer CHECK (completion_status_code = 200),
    ADD COLUMN completion_response_body text,
    ADD CONSTRAINT registrations_actor_unique UNIQUE (registration_id, actor_issuer, actor_subject),
    ADD CONSTRAINT registrations_issuer_required CHECK (actor_issuer IS NOT NULL) NOT VALID,
    ADD CONSTRAINT registrations_subject_nonempty CHECK (octet_length(actor_subject) > 0) NOT VALID,
    ADD CONSTRAINT registrations_completed_identity_check CHECK (state <> 'Completed' OR (
        actor_issuer IS NOT NULL AND actor_binding_id IS NOT NULL AND account_id IS NOT NULL
        AND origin_registration_id IS NOT NULL AND completed_at IS NOT NULL
        AND completion_outcome IS NOT NULL AND completion_profile_snapshot IS NOT NULL
        AND completion_status_code IS NOT NULL AND completion_response_body IS NOT NULL)) NOT VALID;
CREATE INDEX registrations_actor_pair_idx ON identity.registrations(actor_issuer, actor_subject);
CREATE INDEX registrations_origin_idx ON identity.registrations(origin_registration_id);

CREATE TABLE identity.accounts (
    account_id uuid PRIMARY KEY,
    initial_tenant_id uuid NOT NULL UNIQUE REFERENCES business.organisations(tenant_id)
        ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED,
    origin_registration_id uuid NOT NULL UNIQUE REFERENCES identity.registrations(registration_id)
        ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED,
    status varchar(16) NOT NULL CHECK (status IN ('ACTIVE', 'INACTIVE')),
    created_at timestamptz NOT NULL DEFAULT now(),
    CHECK (account_id <> initial_tenant_id),
    UNIQUE (account_id, initial_tenant_id)
);
CREATE TABLE identity.login_methods (
    login_method_id uuid PRIMARY KEY,
    provider_issuer varchar(256) COLLATE "C" NOT NULL CHECK (octet_length(provider_issuer) > 0),
    broker_alias varchar(40) COLLATE "C" NOT NULL CHECK (octet_length(broker_alias) > 0),
    provider_subject varchar(256) COLLATE "C" NOT NULL CHECK (octet_length(provider_subject) > 0),
    account_id uuid NOT NULL REFERENCES identity.accounts(account_id)
        ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED,
    status varchar(16) NOT NULL CHECK (status IN ('ACTIVE', 'RETIRED')),
    created_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT login_methods_provider_unique UNIQUE (provider_issuer, broker_alias, provider_subject),
    UNIQUE (login_method_id, account_id)
);
CREATE INDEX login_methods_account_idx ON identity.login_methods(account_id);
CREATE TABLE identity.actor_bindings (
    actor_binding_id uuid PRIMARY KEY,
    actor_issuer varchar(256) COLLATE "C" NOT NULL CHECK (octet_length(actor_issuer) > 0),
    actor_subject varchar(256) COLLATE "C" NOT NULL CHECK (octet_length(actor_subject) > 0),
    login_method_id uuid NOT NULL,
    account_id uuid NOT NULL,
    status varchar(16) NOT NULL CHECK (status IN ('ACTIVE', 'RETIRED')),
    proof_source varchar(32) NOT NULL CHECK (proof_source = 'KEYCLOAK_FEDERATED_IDENTITY'),
    verified_at timestamptz NOT NULL,
    auth_time timestamptz NOT NULL,
    trust_config_digest varchar(64) NOT NULL CHECK (trust_config_digest ~ '^[0-9a-f]{64}$'),
    correlation_id uuid NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    FOREIGN KEY (login_method_id, account_id) REFERENCES identity.login_methods(login_method_id, account_id)
        ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED,
    CONSTRAINT actor_bindings_actor_unique UNIQUE (actor_issuer, actor_subject),
    UNIQUE (actor_binding_id, account_id, actor_issuer, actor_subject),
    CHECK (auth_time <= verified_at + interval '30 seconds')
);
CREATE UNIQUE INDEX actor_bindings_active_login_unique ON identity.actor_bindings(login_method_id) WHERE status = 'ACTIVE';
CREATE INDEX actor_bindings_login_account_idx ON identity.actor_bindings(login_method_id, account_id);
CREATE INDEX actor_bindings_account_idx ON identity.actor_bindings(account_id);
CREATE TABLE identity.memberships (
    membership_id uuid PRIMARY KEY,
    account_id uuid NOT NULL UNIQUE,
    tenant_id uuid NOT NULL,
    roles text[] NOT NULL CHECK (roles = ARRAY['OWNER']::text[]),
    status varchar(16) NOT NULL CHECK (status IN ('ACTIVE', 'INACTIVE')),
    created_at timestamptz NOT NULL DEFAULT now(),
    FOREIGN KEY (account_id, tenant_id) REFERENCES identity.accounts(account_id, initial_tenant_id) ON DELETE RESTRICT,
    UNIQUE (membership_id, account_id, tenant_id)
);
CREATE INDEX memberships_tenant_idx ON identity.memberships(tenant_id);
ALTER TABLE identity.registrations ADD CONSTRAINT registrations_binding_fk
    FOREIGN KEY (actor_binding_id, account_id, actor_issuer, actor_subject)
    REFERENCES identity.actor_bindings(actor_binding_id, account_id, actor_issuer, actor_subject)
    ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
CREATE INDEX registrations_binding_idx ON identity.registrations(actor_binding_id, account_id, actor_issuer, actor_subject);

ALTER TABLE identity.idempotency_ledger
    ADD COLUMN actor_issuer varchar(256) COLLATE "C" CHECK (octet_length(actor_issuer) > 0),
    ALTER COLUMN actor_subject TYPE varchar(256) COLLATE "C",
    ADD COLUMN registration_id uuid,
    DROP CONSTRAINT idempotency_ledger_actor_key_op_unique,
    ADD CONSTRAINT idempotency_ledger_actor_key_op_unique UNIQUE (actor_issuer, actor_subject, idempotency_key, operation_family),
    ADD CONSTRAINT idempotency_registration_fk FOREIGN KEY (registration_id, actor_issuer, actor_subject)
        REFERENCES identity.registrations(registration_id, actor_issuer, actor_subject)
        ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED,
    ADD CONSTRAINT idempotency_issuer_required CHECK (actor_issuer IS NOT NULL) NOT VALID,
    ADD CONSTRAINT idempotency_subject_nonempty CHECK (octet_length(actor_subject) > 0) NOT VALID,
    ADD CONSTRAINT idempotency_completion_check CHECK (operation_family <> 'CompleteRegistration' OR (
        registration_id IS NOT NULL AND status_code = 200 AND response_body IS NOT NULL
        AND idempotency_key ~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
        AND canonical_hash ~ '^[0-9a-f]{64}$')) NOT VALID,
    ADD CONSTRAINT idempotency_completion_retention CHECK (operation_family <> 'CompleteRegistration'
        OR expires_at >= created_at + interval '24 hours') NOT VALID;
CREATE INDEX idempotency_registration_idx ON identity.idempotency_ledger(registration_id, actor_issuer, actor_subject);
ALTER TABLE identity.registration_events
    ADD COLUMN actor_issuer varchar(256) COLLATE "C" CHECK (octet_length(actor_issuer) > 0),
    ALTER COLUMN actor_subject TYPE varchar(256) COLLATE "C",
    ADD CONSTRAINT events_issuer_required CHECK (actor_issuer IS NOT NULL) NOT VALID,
    ADD CONSTRAINT events_subject_nonempty CHECK (octet_length(actor_subject) > 0) NOT VALID,
    ADD CONSTRAINT events_registration_fk FOREIGN KEY (registration_id, actor_issuer, actor_subject)
        REFERENCES identity.registrations(registration_id, actor_issuer, actor_subject)
        ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
CREATE INDEX events_actor_idx ON identity.registration_events(actor_issuer, actor_subject);

DO $tables$
DECLARE
    target regclass;
    column_list text;
BEGIN
    FOREACH target IN ARRAY ARRAY['identity.accounts'::regclass, 'identity.login_methods'::regclass,
        'identity.actor_bindings'::regclass, 'identity.memberships'::regclass, 'identity.registrations'::regclass,
        'identity.registration_events'::regclass, 'identity.idempotency_ledger'::regclass, 'business.organisations'::regclass]
    LOOP
        EXECUTE format('ALTER TABLE %s OWNER TO CURRENT_USER', target);
        EXECUTE format('ALTER TABLE %s ENABLE ROW LEVEL SECURITY', target);
        EXECUTE format('ALTER TABLE %s FORCE ROW LEVEL SECURITY', target);
        EXECUTE format('REVOKE ALL ON %s FROM PUBLIC, business_app, constitutional_app, runtime_app, wbe_app', target);
        SELECT string_agg(quote_ident(attname), ',') INTO column_list
            FROM pg_attribute WHERE attrelid = target AND attnum > 0 AND NOT attisdropped;
        EXECUTE format('REVOKE ALL (%s) ON %s FROM PUBLIC, business_app, constitutional_app, runtime_app, wbe_app',
            column_list, target);
    END LOOP;
END;
$tables$;
GRANT SELECT, INSERT ON identity.accounts, identity.login_methods, identity.actor_bindings,
    identity.memberships, identity.registrations, identity.registration_events, identity.idempotency_ledger TO business_app;
GRANT UPDATE (state, email_verified, display_name, business_name, business_domain, language_preference,
    account_id, actor_binding_id, origin_registration_id, completed_at, completion_outcome,
    completion_profile_snapshot, completion_status_code, completion_response_body, updated_at)
    ON identity.registrations TO business_app;
GRANT SELECT ON business.organisations TO business_app;
GRANT INSERT (id, tenant_id, name, business_domain, identity_managed, identity_status)
    ON business.organisations TO business_app;
GRANT SELECT (actor_issuer, actor_subject, account_id, login_method_id, status)
    ON identity.actor_bindings TO identity_resolver_owner;
GRANT SELECT (login_method_id, account_id, status) ON identity.login_methods TO identity_resolver_owner;
GRANT SELECT (account_id, initial_tenant_id, status) ON identity.accounts TO identity_resolver_owner;
GRANT SELECT (membership_id, account_id, tenant_id, roles, status) ON identity.memberships TO identity_resolver_owner;
GRANT SELECT (tenant_id, identity_managed, identity_status) ON business.organisations TO identity_resolver_owner;

CREATE POLICY actor_scope ON identity.actor_bindings TO business_app, identity_resolver_owner
    USING (actor_issuer = NULLIF(current_setting('app.identity_issuer', true), '') COLLATE "C"
       AND actor_subject = NULLIF(current_setting('app.identity_subject', true), '') COLLATE "C")
    WITH CHECK (actor_issuer = NULLIF(current_setting('app.identity_issuer', true), '') COLLATE "C"
       AND actor_subject = NULLIF(current_setting('app.identity_subject', true), '') COLLATE "C");
CREATE POLICY actor_scope ON identity.login_methods TO business_app, identity_resolver_owner
    USING (EXISTS (SELECT 1 FROM identity.actor_bindings AS actor
        WHERE actor.account_id = login_methods.account_id AND actor.login_method_id = login_methods.login_method_id))
    WITH CHECK (EXISTS (SELECT 1 FROM identity.actor_bindings AS actor
        WHERE actor.account_id = login_methods.account_id AND actor.login_method_id = login_methods.login_method_id));
CREATE POLICY actor_scope ON identity.accounts TO business_app, identity_resolver_owner
    USING (EXISTS (SELECT 1 FROM identity.actor_bindings AS actor WHERE actor.account_id = accounts.account_id))
    WITH CHECK (EXISTS (SELECT 1 FROM identity.actor_bindings AS actor WHERE actor.account_id = accounts.account_id));
CREATE POLICY actor_scope ON identity.memberships TO business_app, identity_resolver_owner
    USING (EXISTS (SELECT 1 FROM identity.actor_bindings AS actor WHERE actor.account_id = memberships.account_id))
    WITH CHECK (EXISTS (SELECT 1 FROM identity.actor_bindings AS actor WHERE actor.account_id = memberships.account_id));
CREATE POLICY actor_scope ON identity.registrations TO business_app
    USING (actor_issuer = NULLIF(current_setting('app.identity_issuer', true), '') COLLATE "C"
       AND actor_subject = NULLIF(current_setting('app.identity_subject', true), '') COLLATE "C")
    WITH CHECK (actor_issuer = NULLIF(current_setting('app.identity_issuer', true), '') COLLATE "C"
       AND actor_subject = NULLIF(current_setting('app.identity_subject', true), '') COLLATE "C");
CREATE POLICY actor_scope ON identity.registration_events TO business_app
    USING (actor_issuer = NULLIF(current_setting('app.identity_issuer', true), '') COLLATE "C"
       AND actor_subject = NULLIF(current_setting('app.identity_subject', true), '') COLLATE "C")
    WITH CHECK (actor_issuer = NULLIF(current_setting('app.identity_issuer', true), '') COLLATE "C"
       AND actor_subject = NULLIF(current_setting('app.identity_subject', true), '') COLLATE "C");
CREATE POLICY actor_scope ON identity.idempotency_ledger TO business_app
    USING (actor_issuer = NULLIF(current_setting('app.identity_issuer', true), '') COLLATE "C"
       AND actor_subject = NULLIF(current_setting('app.identity_subject', true), '') COLLATE "C")
    WITH CHECK (actor_issuer = NULLIF(current_setting('app.identity_issuer', true), '') COLLATE "C"
       AND actor_subject = NULLIF(current_setting('app.identity_subject', true), '') COLLATE "C");

DROP POLICY IF EXISTS tenant_isolation ON business.organisations;
CREATE POLICY resolver_actor_scope ON business.organisations FOR SELECT TO identity_resolver_owner
    USING (EXISTS (SELECT 1 FROM identity.accounts AS account WHERE account.initial_tenant_id = organisations.tenant_id));
CREATE POLICY bp_select ON business.organisations FOR SELECT TO business_app USING (true);
CREATE POLICY bp_insert ON business.organisations FOR INSERT TO business_app WITH CHECK (identity_status = 'ACTIVE');
CREATE POLICY bp_identity_boundary ON business.organisations AS RESTRICTIVE TO business_app
    USING (identity_managed AND id = tenant_id AND (
        (NULLIF(current_setting('app.tenant_id', true), '') IS NULL
         AND NULLIF(current_setting('app.current_tenant_id', true), '') IS NULL
         AND EXISTS (SELECT 1 FROM identity.accounts AS account WHERE account.initial_tenant_id = organisations.tenant_id))
        OR (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid
        AND tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
        AND identity_status = 'ACTIVE' AND EXISTS (
            SELECT 1 FROM identity.accounts AS account
            JOIN identity.actor_bindings AS actor ON actor.account_id = account.account_id
            JOIN identity.login_methods AS login ON login.login_method_id = actor.login_method_id AND login.account_id = account.account_id
            JOIN identity.memberships AS membership ON membership.account_id = account.account_id AND membership.tenant_id = account.initial_tenant_id
            WHERE account.initial_tenant_id = organisations.tenant_id AND account.status = 'ACTIVE'
              AND actor.status = 'ACTIVE' AND login.status = 'ACTIVE' AND membership.status = 'ACTIVE'
              AND membership.roles = ARRAY['OWNER']::text[]))))
    WITH CHECK (identity_managed AND id = tenant_id AND identity_status = 'ACTIVE'
        AND NULLIF(current_setting('app.tenant_id', true), '') IS NULL
        AND NULLIF(current_setting('app.current_tenant_id', true), '') IS NULL
        AND EXISTS (SELECT 1 FROM identity.accounts AS account WHERE account.initial_tenant_id = organisations.tenant_id));
CREATE POLICY service_tenant_boundary ON business.organisations AS RESTRICTIVE TO constitutional_app, runtime_app, wbe_app
    USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid
       AND tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
    WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid
       AND tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);

CREATE FUNCTION identity.resolve_customer_membership()
RETURNS TABLE (account_id uuid, tenant_id uuid, membership_id uuid, roles text[])
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = pg_catalog SET row_security = on
AS $function$
DECLARE
    resolved record;
BEGIN
    IF NULLIF(pg_catalog.current_setting('app.identity_issuer', true), '') IS NULL
       OR NULLIF(pg_catalog.current_setting('app.identity_subject', true), '') IS NULL THEN RETURN; END IF;
    BEGIN
        SELECT account.account_id, account.initial_tenant_id AS tenant_id, membership.membership_id, membership.roles
        INTO STRICT resolved
        FROM identity.actor_bindings AS actor
        JOIN identity.login_methods AS login ON login.login_method_id = actor.login_method_id AND login.account_id = actor.account_id
        JOIN identity.accounts AS account ON account.account_id = actor.account_id
        JOIN business.organisations AS organisation ON organisation.tenant_id = account.initial_tenant_id
        JOIN identity.memberships AS membership ON membership.account_id = account.account_id AND membership.tenant_id = account.initial_tenant_id
        WHERE actor.actor_issuer = NULLIF(pg_catalog.current_setting('app.identity_issuer', true), '') COLLATE "C"
          AND actor.actor_subject = NULLIF(pg_catalog.current_setting('app.identity_subject', true), '') COLLATE "C"
          AND actor.status = 'ACTIVE' AND login.status = 'ACTIVE' AND account.status = 'ACTIVE'
          AND organisation.identity_managed AND organisation.identity_status = 'ACTIVE'
          AND membership.status = 'ACTIVE' AND membership.roles = ARRAY['OWNER']::text[];
    EXCEPTION
        WHEN no_data_found THEN RETURN;
        WHEN too_many_rows THEN RAISE EXCEPTION 'customer membership invariant failed' USING ERRCODE = '23514';
    END;
    RETURN QUERY SELECT resolved.account_id, resolved.tenant_id, resolved.membership_id, resolved.roles;
END;
$function$;
GRANT CREATE ON SCHEMA identity TO identity_resolver_owner;
ALTER FUNCTION identity.resolve_customer_membership() OWNER TO identity_resolver_owner;
REVOKE CREATE ON SCHEMA identity FROM identity_resolver_owner;
REVOKE ALL ON FUNCTION identity.resolve_customer_membership() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION identity.resolve_customer_membership() TO business_app, constitutional_app, runtime_app, wbe_app;

CREATE FUNCTION identity.guard_registration_identity() RETURNS trigger
LANGUAGE plpgsql SECURITY INVOKER SET search_path = pg_catalog AS $guard$
BEGIN
    IF TG_OP = 'UPDATE' THEN
        IF OLD.state = 'Completed' OR ROW(NEW.registration_id, NEW.actor_issuer, NEW.actor_subject, NEW.created_at)
           IS DISTINCT FROM ROW(OLD.registration_id, OLD.actor_issuer, OLD.actor_subject, OLD.created_at) THEN
            RAISE EXCEPTION 'immutable registration identity' USING ERRCODE = '23514';
        END IF;
    END IF;
    IF NEW.state <> 'Completed' AND (NEW.account_id IS NOT NULL OR NEW.actor_binding_id IS NOT NULL
       OR NEW.origin_registration_id IS NOT NULL OR NEW.completed_at IS NOT NULL OR NEW.completion_outcome IS NOT NULL
       OR NEW.completion_profile_snapshot IS NOT NULL OR NEW.completion_status_code IS NOT NULL OR NEW.completion_response_body IS NOT NULL) THEN
        RAISE EXCEPTION 'incomplete association' USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END;
$guard$;
CREATE TRIGGER guard_registration_identity BEFORE INSERT OR UPDATE ON identity.registrations
    FOR EACH ROW EXECUTE FUNCTION identity.guard_registration_identity();

CREATE FUNCTION identity.assert_completed_cohort() RETURNS trigger
LANGUAGE plpgsql SECURITY INVOKER SET search_path = pg_catalog AS $cohort$
DECLARE
    target_registration uuid;
    registration_row identity.registrations%ROWTYPE;
    root_row identity.registrations%ROWTYPE;
    cohort record;
BEGIN
    IF TG_TABLE_NAME = 'accounts' THEN target_registration := NEW.origin_registration_id;
    ELSIF TG_TABLE_NAME = 'idempotency_ledger' THEN
        IF NEW.operation_family <> 'CompleteRegistration' THEN RETURN NULL; END IF;
        target_registration := NEW.registration_id;
    ELSE target_registration := NEW.registration_id;
    END IF;
    SELECT registration.* INTO STRICT registration_row FROM identity.registrations AS registration
        WHERE registration.registration_id = target_registration;
    IF TG_TABLE_NAME = 'registrations' AND registration_row.state <> 'Completed' THEN RETURN NULL; END IF;
    IF registration_row.state <> 'Completed' THEN
        RAISE EXCEPTION 'completion invariant failed' USING ERRCODE = '23514';
    END IF;
    SELECT account.origin_registration_id, actor.verified_at, actor.auth_time INTO STRICT cohort
        FROM identity.accounts AS account
        JOIN identity.actor_bindings AS actor ON actor.account_id = account.account_id
        JOIN identity.login_methods AS login ON login.login_method_id = actor.login_method_id AND login.account_id = account.account_id
        JOIN identity.memberships AS membership ON membership.account_id = account.account_id AND membership.tenant_id = account.initial_tenant_id
        JOIN business.organisations AS organisation ON organisation.tenant_id = account.initial_tenant_id
        WHERE account.account_id = registration_row.account_id AND actor.actor_binding_id = registration_row.actor_binding_id
          AND actor.actor_issuer = registration_row.actor_issuer COLLATE "C" AND actor.actor_subject = registration_row.actor_subject COLLATE "C"
          AND actor.status = 'ACTIVE' AND login.status = 'ACTIVE' AND account.status = 'ACTIVE'
          AND organisation.identity_managed AND organisation.id = organisation.tenant_id AND organisation.identity_status = 'ACTIVE'
          AND membership.status = 'ACTIVE' AND membership.roles = ARRAY['OWNER']::text[];
    SELECT registration.* INTO STRICT root_row FROM identity.registrations AS registration
        WHERE registration.registration_id = cohort.origin_registration_id;
    IF root_row.state <> 'Completed' OR root_row.origin_registration_id IS DISTINCT FROM root_row.registration_id
       OR registration_row.origin_registration_id IS DISTINCT FROM root_row.registration_id
       OR ROW(registration_row.actor_issuer, registration_row.actor_subject, registration_row.actor_binding_id,
            registration_row.account_id, registration_row.completion_outcome, registration_row.completion_status_code,
            registration_row.completion_response_body, registration_row.completion_profile_snapshot)
          IS DISTINCT FROM ROW(root_row.actor_issuer, root_row.actor_subject, root_row.actor_binding_id,
            root_row.account_id, root_row.completion_outcome, root_row.completion_status_code,
            root_row.completion_response_body, root_row.completion_profile_snapshot)
       OR root_row.email_verified IS DISTINCT FROM true OR root_row.authentication_path <> 'Google'
       OR NULLIF(btrim(root_row.display_name), '') IS NULL OR NULLIF(btrim(root_row.business_name), '') IS NULL
       OR NULLIF(btrim(root_row.business_domain), '') IS NULL OR NULLIF(btrim(root_row.language_preference), '') IS NULL
       OR root_row.completion_profile_snapshot IS DISTINCT FROM jsonb_build_object(
            'displayName', root_row.display_name, 'businessName', root_row.business_name,
            'businessDomain', root_row.business_domain, 'languagePreference', root_row.language_preference,
            'emailVerified', true, 'mobileVerified', root_row.mobile_verified) THEN
        RAISE EXCEPTION 'completion invariant failed' USING ERRCODE = '23514';
    END IF;
    IF TG_TABLE_NAME = 'accounts' THEN
        IF NEW.account_id IS DISTINCT FROM registration_row.account_id
           OR cohort.verified_at < clock_timestamp() - interval '5 minutes'
           OR cohort.auth_time < clock_timestamp() - interval '5 minutes'
           OR cohort.verified_at > clock_timestamp() + interval '30 seconds'
           OR cohort.auth_time > clock_timestamp() + interval '30 seconds' THEN
            RAISE EXCEPTION 'completion proof invalid' USING ERRCODE = '23514';
        END IF;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM identity.registration_events AS event
        WHERE event.registration_id = target_registration AND event.actor_issuer = registration_row.actor_issuer COLLATE "C"
          AND event.actor_subject = registration_row.actor_subject COLLATE "C"
          AND event.event_type = 'RegistrationCompleted' AND event.to_state = 'Completed')
       OR NOT EXISTS (SELECT 1 FROM identity.idempotency_ledger AS entry
        WHERE entry.registration_id = target_registration AND entry.actor_issuer = registration_row.actor_issuer COLLATE "C"
          AND entry.actor_subject = registration_row.actor_subject COLLATE "C" AND entry.operation_family = 'CompleteRegistration'
          AND entry.status_code = root_row.completion_status_code AND entry.response_body = root_row.completion_response_body) THEN
        RAISE EXCEPTION 'completion evidence missing' USING ERRCODE = '23514';
    END IF;
    IF TG_TABLE_NAME = 'idempotency_ledger' THEN
        IF NEW.status_code IS DISTINCT FROM root_row.completion_status_code OR NEW.response_body IS DISTINCT FROM root_row.completion_response_body
           OR NEW.actor_issuer IS DISTINCT FROM registration_row.actor_issuer OR NEW.actor_subject IS DISTINCT FROM registration_row.actor_subject
           OR NEW.idempotency_key !~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
           OR NEW.canonical_hash !~ '^[0-9a-f]{64}$' THEN
            RAISE EXCEPTION 'completion replay invariant failed' USING ERRCODE = '23514';
        END IF;
    END IF;
    RETURN NULL;
EXCEPTION
    WHEN no_data_found OR too_many_rows THEN RAISE EXCEPTION 'completion invariant failed' USING ERRCODE = '23514';
END;
$cohort$;
CREATE CONSTRAINT TRIGGER account_completed_cohort AFTER INSERT ON identity.accounts DEFERRABLE INITIALLY DEFERRED
    FOR EACH ROW EXECUTE FUNCTION identity.assert_completed_cohort();
CREATE CONSTRAINT TRIGGER registration_completed_cohort AFTER INSERT OR UPDATE ON identity.registrations DEFERRABLE INITIALLY DEFERRED
    FOR EACH ROW EXECUTE FUNCTION identity.assert_completed_cohort();
CREATE CONSTRAINT TRIGGER replay_completed_cohort AFTER INSERT ON identity.idempotency_ledger DEFERRABLE INITIALLY DEFERRED
    FOR EACH ROW EXECUTE FUNCTION identity.assert_completed_cohort();
REVOKE ALL ON FUNCTION identity.guard_registration_identity(), identity.assert_completed_cohort() FROM PUBLIC;
COMMIT;