-- Implements: work-contracts/WC-176-customer-journeys-registration-trial-hire-and-pages.md WC176-R009, WC176-R011
-- Constitutional basis: C-019, C-059, C-088
-- A Trial for any agent type can be recorded. business.trial_allocations was created for the four short legacy codes
-- (DMA, DPA, DCA, DSA) as VARCHAR(20) with a CHECK on exactly those codes, so starting the first Trial of
-- DIGITAL_MARKETING_LOCAL_SERVICE (31 characters) failed in the billing engine with "value too long for type
-- character varying(20)" and the customer saw "Acquisition continuation unavailable". The column now matches the
-- other agent_type columns (VARCHAR(64), see 48-wc112) and the CHECK accepts a well-formed agent type code.
-- The file widens a column, so it is full-class on purpose: the update path refuses column type changes.
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '30s';
DO $owner$
BEGIN
    IF NOT pg_has_role(session_user, 'bp_owner', 'SET') THEN
        EXECUTE format('GRANT bp_owner TO %I', session_user);
        PERFORM set_config('waooaw.wc176_trial_agent_type_bp_owner_granted', 'true', true);
    END IF;
END
$owner$;
SET LOCAL ROLE bp_owner;

ALTER TABLE business.trial_allocations
    ALTER COLUMN agent_type TYPE VARCHAR(64);

ALTER TABLE business.trial_allocations
    DROP CONSTRAINT IF EXISTS trial_allocations_agent_type_check;

ALTER TABLE business.trial_allocations
    DROP CONSTRAINT IF EXISTS trial_allocations_agent_type_shape,
    ADD CONSTRAINT trial_allocations_agent_type_shape CHECK (agent_type ~ '^[A-Z][A-Z0-9_]{1,63}$');

RESET ROLE;
DO $owner$
BEGIN
    IF current_setting('waooaw.wc176_trial_agent_type_bp_owner_granted', true) = 'true' THEN
        EXECUTE format('REVOKE bp_owner FROM %I', session_user);
    END IF;
END
$owner$;
COMMIT;
