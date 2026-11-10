-- WC-134: immutable agent-skill inference binding, AIR results, shared BP cost ledger.
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '30s';
DO $membership$
BEGIN
    IF NOT pg_has_role(session_user, 'air_owner', 'SET') THEN
        EXECUTE format('GRANT air_owner TO %I', session_user);
        PERFORM set_config('waooaw.generation_air_owner_granted', 'true', true);
    END IF;
    IF NOT pg_has_role(session_user, 'bp_owner', 'SET') THEN
        EXECUTE format('GRANT bp_owner TO %I', session_user);
        PERFORM set_config('waooaw.generation_bp_owner_granted', 'true', true);
    END IF;
END
$membership$;
CREATE TABLE IF NOT EXISTS ai_runtime.conversation_generations (
    tenant_id UUID NOT NULL, relationship_id UUID NOT NULL, idempotency_key UUID NOT NULL,
    execution_id UUID NOT NULL, request_digest TEXT NOT NULL CHECK (request_digest ~ '^[0-9a-f]{64}$'),
    admission_claimed BOOLEAN NOT NULL DEFAULT false, dispatch_claimed BOOLEAN NOT NULL DEFAULT false,
    result_json JSONB, created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(), completed_at TIMESTAMPTZ,
    PRIMARY KEY (tenant_id, relationship_id, idempotency_key),
    UNIQUE (tenant_id, execution_id),
    CHECK ((result_json IS NULL) = (completed_at IS NULL))
);
ALTER TABLE ai_runtime.conversation_generations ADD COLUMN IF NOT EXISTS admission_claimed BOOLEAN NOT NULL DEFAULT false;
ALTER TABLE ai_runtime.conversation_generations OWNER TO air_owner;
ALTER TABLE ai_runtime.conversation_generations ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_runtime.conversation_generations FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS generation_tenant_scope ON ai_runtime.conversation_generations;
CREATE POLICY generation_tenant_scope ON ai_runtime.conversation_generations
    USING (tenant_id = nullif(current_setting('app.current_tenant_id', true), '')::UUID)
    WITH CHECK (tenant_id = nullif(current_setting('app.current_tenant_id', true), '')::UUID);
REVOKE ALL ON ai_runtime.conversation_generations FROM PUBLIC, ai_runtime_app;
GRANT SELECT, INSERT ON ai_runtime.conversation_generations TO ai_runtime_app;
GRANT UPDATE (admission_claimed, dispatch_claimed, result_json, completed_at) ON ai_runtime.conversation_generations TO ai_runtime_app;

CREATE TABLE IF NOT EXISTS business.conversation_inference_bindings (
    binding_id UUID PRIMARY KEY, tenant_id UUID NOT NULL, admission_id UUID NOT NULL,
    relationship_id UUID NOT NULL, accepted_contract_id UUID NOT NULL, configuration_revision INTEGER NOT NULL,
    admission_revision INTEGER NOT NULL CHECK (admission_revision > 0),
    professional_type TEXT NOT NULL, professional_version TEXT NOT NULL,
    skill_id TEXT NOT NULL, skill_version TEXT NOT NULL,
    prompt_ref TEXT NOT NULL, prompt_version TEXT NOT NULL, prompt_digest TEXT NOT NULL,
    model_policy_ref TEXT NOT NULL, model_policy_version TEXT NOT NULL, model_policy_digest TEXT NOT NULL,
    binding_json JSONB NOT NULL CHECK (jsonb_typeof(binding_json) = 'object'),
    binding_digest TEXT NOT NULL CHECK (binding_digest ~ '^sha256:[0-9a-f]{64}$'),
    approved_evidence_id UUID NOT NULL CHECK (approved_evidence_id <> '00000000-0000-0000-0000-000000000000'::UUID),
    active BOOLEAN NOT NULL DEFAULT false,
    UNIQUE (tenant_id, relationship_id, admission_id, admission_revision, skill_id, skill_version, prompt_digest, model_policy_digest)
);
ALTER TABLE business.conversation_inference_bindings OWNER TO bp_owner;
ALTER TABLE business.conversation_inference_bindings ENABLE ROW LEVEL SECURITY;
ALTER TABLE business.conversation_inference_bindings FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS inference_binding_tenant ON business.conversation_inference_bindings;
CREATE POLICY inference_binding_tenant ON business.conversation_inference_bindings
    USING (tenant_id = nullif(current_setting('app.current_tenant_id', true), '')::UUID);
REVOKE ALL ON business.conversation_inference_bindings FROM PUBLIC, business_app;
GRANT SELECT ON business.conversation_inference_bindings TO business_app;

CREATE TABLE IF NOT EXISTS business.conversation_model_reservations (
    reservation_id UUID PRIMARY KEY, tenant_id UUID NOT NULL, environment TEXT NOT NULL,
    activation_digest TEXT NOT NULL, authority_digest TEXT NOT NULL, cost_day DATE NOT NULL,
    customer_tenant_id UUID NOT NULL, relationship_id UUID NOT NULL, execution_id UUID NOT NULL,
    actor_id UUID NOT NULL, idempotency_key UUID NOT NULL, mandate_digest TEXT NOT NULL,
    request_digest TEXT NOT NULL CHECK (request_digest ~ '^[0-9a-f]{64}$'),
    binding_id UUID NOT NULL, binding_digest TEXT NOT NULL, rate_digest TEXT NOT NULL,
    evidence_id UUID NOT NULL, reserved_paise BIGINT NOT NULL CHECK (reserved_paise >= 0),
    input_rate_paise BIGINT NOT NULL CHECK (input_rate_paise >= 0),
    output_rate_paise BIGINT NOT NULL CHECK (output_rate_paise >= 0),
    actual_paise NUMERIC(28,0) CHECK (actual_paise >= 0), input_tokens BIGINT, output_tokens BIGINT,
    state TEXT NOT NULL CHECK (state IN ('RESERVED', 'SETTLED', 'RELEASED')),
    overrun BOOLEAN NOT NULL DEFAULT false, settlement_evidence_id UUID,
    reserved_at TIMESTAMPTZ NOT NULL, expires_at TIMESTAMPTZ NOT NULL, settled_at TIMESTAMPTZ,
    UNIQUE (tenant_id, customer_tenant_id, execution_id),
    CHECK ((state = 'RESERVED' AND actual_paise IS NULL AND settled_at IS NULL)
        OR (state = 'SETTLED' AND actual_paise IS NOT NULL AND settled_at IS NOT NULL AND settlement_evidence_id IS NOT NULL)
        OR (state = 'RELEASED' AND actual_paise = 0 AND settled_at IS NOT NULL AND settlement_evidence_id IS NOT NULL))
);
ALTER TABLE business.conversation_model_reservations OWNER TO bp_owner;
CREATE INDEX IF NOT EXISTS conversation_model_daily_budget
    ON business.conversation_model_reservations(tenant_id, reserved_at);
ALTER TABLE business.conversation_model_reservations ENABLE ROW LEVEL SECURITY;
ALTER TABLE business.conversation_model_reservations FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS model_budget_tenant ON business.conversation_model_reservations;
CREATE POLICY model_budget_tenant ON business.conversation_model_reservations
    USING (tenant_id = nullif(current_setting('app.current_tenant_id', true), '')::UUID)
    WITH CHECK (tenant_id = nullif(current_setting('app.current_tenant_id', true), '')::UUID);
REVOKE ALL ON business.conversation_model_reservations FROM PUBLIC, business_app;
GRANT SELECT, INSERT ON business.conversation_model_reservations TO business_app;
GRANT UPDATE (actual_paise, input_tokens, output_tokens, state, overrun, settlement_evidence_id, settled_at)
    ON business.conversation_model_reservations TO business_app;
DO $receipt_constraint$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint
        WHERE conrelid = 'business.conversation_model_reservations'::regclass
            AND conname = 'conversation_model_receipt_identity') THEN
        ALTER TABLE business.conversation_model_reservations
            ADD CONSTRAINT conversation_model_receipt_identity
            UNIQUE (tenant_id, customer_tenant_id, execution_id, reservation_id);
    END IF;
END
$receipt_constraint$;
CREATE TABLE IF NOT EXISTS business.conversation_model_budget_receipts (
    tenant_id UUID NOT NULL, execution_id UUID NOT NULL, reservation_id UUID NOT NULL,
    budget_tenant_id UUID NOT NULL,
    PRIMARY KEY (tenant_id, execution_id),
    FOREIGN KEY (budget_tenant_id, tenant_id, execution_id, reservation_id)
        REFERENCES business.conversation_model_reservations
            (tenant_id, customer_tenant_id, execution_id, reservation_id)
);
ALTER TABLE business.conversation_model_budget_receipts OWNER TO bp_owner;
ALTER TABLE business.conversation_model_budget_receipts ENABLE ROW LEVEL SECURITY;
ALTER TABLE business.conversation_model_budget_receipts FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS model_receipt_customer_tenant ON business.conversation_model_budget_receipts;
CREATE POLICY model_receipt_customer_tenant ON business.conversation_model_budget_receipts
    USING (tenant_id = nullif(current_setting('app.current_tenant_id', true), '')::UUID)
    WITH CHECK (tenant_id = nullif(current_setting('app.current_tenant_id', true), '')::UUID);
REVOKE ALL ON business.conversation_model_budget_receipts FROM PUBLIC, business_app;
GRANT SELECT, INSERT ON business.conversation_model_budget_receipts TO business_app;
ALTER TABLE business.provider_configs ADD COLUMN IF NOT EXISTS provider_identity_uri TEXT;
ALTER TABLE business.provider_configs DROP CONSTRAINT IF EXISTS provider_configs_auth_method_check;
DO $constraint$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid = 'business.provider_configs'::regclass
        AND conname = 'provider_configs_auth_method_check') THEN
        ALTER TABLE business.provider_configs ADD CONSTRAINT provider_configs_auth_method_check
            CHECK (auth_method IN ('OAUTH2', 'API_KEY', 'INTERNAL_JWT', 'INSTITUTIONAL_MTLS'));
    END IF;
END
$constraint$;
CREATE OR REPLACE FUNCTION ai_runtime.protect_conversation_generation() RETURNS TRIGGER
LANGUAGE plpgsql SET search_path = pg_catalog AS $body$
BEGIN
    IF OLD.result_json IS NOT NULL
        OR (OLD.dispatch_claimed AND (NOT NEW.dispatch_claimed OR (OLD.admission_claimed AND NOT NEW.admission_claimed)))
        OR ROW(OLD.tenant_id, OLD.relationship_id, OLD.idempotency_key, OLD.execution_id, OLD.request_digest, OLD.created_at)
            IS DISTINCT FROM ROW(NEW.tenant_id, NEW.relationship_id, NEW.idempotency_key, NEW.execution_id, NEW.request_digest, NEW.created_at) THEN
        RAISE EXCEPTION 'Original generation identity and result are immutable' USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END
$body$;
ALTER FUNCTION ai_runtime.protect_conversation_generation() OWNER TO air_owner;
REVOKE ALL ON FUNCTION ai_runtime.protect_conversation_generation() FROM PUBLIC;
CREATE OR REPLACE TRIGGER protect_conversation_generation BEFORE UPDATE ON ai_runtime.conversation_generations
    FOR EACH ROW EXECUTE FUNCTION ai_runtime.protect_conversation_generation();
CREATE OR REPLACE FUNCTION business.protect_conversation_model_settlement() RETURNS TRIGGER
LANGUAGE plpgsql SET search_path = pg_catalog AS $body$
BEGIN
    IF OLD.state <> 'RESERVED' OR NEW.state NOT IN ('SETTLED', 'RELEASED')
        OR ROW(OLD.reservation_id, OLD.tenant_id, OLD.environment, OLD.activation_digest, OLD.authority_digest,
            OLD.cost_day, OLD.customer_tenant_id, OLD.relationship_id, OLD.execution_id, OLD.actor_id,
            OLD.idempotency_key, OLD.mandate_digest, OLD.request_digest, OLD.binding_id, OLD.binding_digest,
            OLD.rate_digest, OLD.evidence_id, OLD.reserved_paise, OLD.input_rate_paise, OLD.output_rate_paise,
            OLD.reserved_at, OLD.expires_at)
        IS DISTINCT FROM ROW(NEW.reservation_id, NEW.tenant_id, NEW.environment, NEW.activation_digest, NEW.authority_digest,
            NEW.cost_day, NEW.customer_tenant_id, NEW.relationship_id, NEW.execution_id, NEW.actor_id,
            NEW.idempotency_key, NEW.mandate_digest, NEW.request_digest, NEW.binding_id, NEW.binding_digest,
            NEW.rate_digest, NEW.evidence_id, NEW.reserved_paise, NEW.input_rate_paise, NEW.output_rate_paise,
            NEW.reserved_at, NEW.expires_at) THEN
        RAISE EXCEPTION 'Original model reservation and terminal settlement are immutable' USING ERRCODE = '23514';
    END IF;
    IF NEW.state = 'SETTLED' THEN
        IF NEW.input_tokens IS NULL OR NEW.output_tokens IS NULL OR NEW.input_tokens < 0 OR NEW.output_tokens < 0
            OR NEW.actual_paise IS DISTINCT FROM
                (ceil(OLD.input_rate_paise::NUMERIC * NEW.input_tokens / 1000000)
                    + ceil(OLD.output_rate_paise::NUMERIC * NEW.output_tokens / 1000000))
            OR NEW.overrun IS DISTINCT FROM
                (NEW.actual_paise > OLD.reserved_paise OR NEW.input_tokens > 8192 OR NEW.output_tokens > 2048) THEN
            RAISE EXCEPTION 'Model settlement must record full immutable usage' USING ERRCODE = '23514';
        END IF;
    ELSIF NEW.actual_paise IS DISTINCT FROM 0::NUMERIC OR NEW.input_tokens IS NOT NULL
        OR NEW.output_tokens IS NOT NULL OR NEW.overrun THEN
        RAISE EXCEPTION 'Released model reservation cannot contain usage' USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END
$body$;
ALTER FUNCTION business.protect_conversation_model_settlement() OWNER TO bp_owner;
REVOKE ALL ON FUNCTION business.protect_conversation_model_settlement() FROM PUBLIC;
CREATE OR REPLACE TRIGGER protect_conversation_model_settlement BEFORE UPDATE ON business.conversation_model_reservations
    FOR EACH ROW EXECUTE FUNCTION business.protect_conversation_model_settlement();
DO $membership$
BEGIN
    IF current_setting('waooaw.generation_air_owner_granted', true) = 'true' THEN
        EXECUTE format('REVOKE air_owner FROM %I', session_user);
    END IF;
    IF current_setting('waooaw.generation_bp_owner_granted', true) = 'true' THEN
        EXECUTE format('REVOKE bp_owner FROM %I', session_user);
    END IF;
END
$membership$;
COMMIT;
