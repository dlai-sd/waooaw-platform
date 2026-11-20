-- Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C3-01
-- Constitutional basis: C-023, C-059, C-063
-- The environment hard ceiling is configured by EnvironmentSpend__HardMaximumInr; the database keeps
-- only the non-negative invariant so a raised ceiling is not blocked by the former fixed 500 INR cap.
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '30s';
SET LOCAL ROLE bp_owner;

DO $environment_spend_ceiling$
DECLARE
    fixed_cap RECORD;
BEGIN
    FOR fixed_cap IN
        SELECT conname
        FROM pg_constraint
        WHERE conrelid = 'business.environment_spend_authorities'::regclass
          AND contype = 'c'
          AND pg_get_constraintdef(oid) LIKE '%50000%'
    LOOP
        EXECUTE format(
            'ALTER TABLE business.environment_spend_authorities DROP CONSTRAINT IF EXISTS %I',
            fixed_cap.conname
        );
    END LOOP;
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conrelid = 'business.environment_spend_authorities'::regclass
          AND conname = 'environment_spend_authorities_maximum_nonnegative'
    ) THEN
        ALTER TABLE business.environment_spend_authorities
            ADD CONSTRAINT environment_spend_authorities_maximum_nonnegative
            CHECK (maximum_paise >= 0);
    END IF;
END
$environment_spend_ceiling$;

COMMIT;
