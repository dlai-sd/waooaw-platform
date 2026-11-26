-- Implements: work-contracts/WC-172-safe-to-charge-real-customers.md (Demo defect repairs: trial refused by row security)
-- Constitutional basis: C-023, C-026, C-059, C-063
-- Migration 60 forces row security on every business table that has a tenant_id, and acquisition_intents has one. The
-- table never received a policy, so with row security forced every insert was refused ("new row violates row-level
-- security policy") and a customer who had signed in but not registered could not start a Trial or a Hire.
-- The application sees an intent when it belongs to the customer's tenant, or when it carries the caller's own
-- pseudonymous actor hash (a person who has not registered yet has no tenant). Nothing else is visible or writable.
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '30s';
SET LOCAL ROLE bp_owner;

ALTER TABLE business.acquisition_intents ENABLE ROW LEVEL SECURITY;
ALTER TABLE business.acquisition_intents FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS acquisition_intents_owner_scope ON business.acquisition_intents;
CREATE POLICY acquisition_intents_owner_scope ON business.acquisition_intents
    TO business_app
    USING (
        tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
        OR actor_identity_hash = NULLIF(current_setting('app.acquisition_actor_hash', true), '')
    )
    WITH CHECK (
        tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
        OR actor_identity_hash = NULLIF(current_setting('app.acquisition_actor_hash', true), '')
    );

COMMIT;
