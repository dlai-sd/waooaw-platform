-- wc177-apply: update
-- Implements: work-contracts/WC-178-demo-live-journey-defects.md WC178-R005
-- Constitutional basis: C-023, C-026, C-059, C-088
-- Migration 60 forces row security on every business table that carries customer_id, tenant_id or organisation_id.
-- business.trial_allocations has customer_id, and no policy was ever written for the billing engine's application role
-- (wbe_app), so with row security forced every Trial insert was refused ("new row violates row-level security policy")
-- and no customer could start a Trial. The billing engine owns Trial records, so its application role may read and write
-- them; every other role still has no policy and sees nothing. The table has no tenant column to scope by, and the
-- billing engine does not set one for Trial calls.
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '30s';
SET LOCAL ROLE bp_owner;

DROP POLICY IF EXISTS trial_allocations_billing_owner ON business.trial_allocations;
CREATE POLICY trial_allocations_billing_owner ON business.trial_allocations
    FOR ALL
    TO wbe_app
    USING (true)
    WITH CHECK (true);

COMMIT;
