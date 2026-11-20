-- Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C3-04
-- Constitutional basis: C-023, C-059, C-063
-- The spend account decision is stored once at reserve; settle, release and reconcile read it back.
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '30s';
SET LOCAL ROLE bp_owner;

ALTER TABLE business.conversation_inference_spend_coordinators
    ADD COLUMN IF NOT EXISTS account_class TEXT
        CHECK (account_class IS NULL OR account_class IN (
            'ACQUISITION', 'SETUP_GRANT', 'TRIAL', 'SUBSCRIPTION', 'PLATFORM_FLOOR', 'SIMULATION')),
    ADD COLUMN IF NOT EXISTS pinned_wallet_account_id UUID;

ALTER TABLE business.environment_spend_attempts
    ADD COLUMN IF NOT EXISTS account_class TEXT
        CHECK (account_class IS NULL OR account_class IN (
            'ACQUISITION', 'SETUP_GRANT', 'TRIAL', 'SUBSCRIPTION', 'PLATFORM_FLOOR', 'SIMULATION')),
    ADD COLUMN IF NOT EXISTS pinned_wallet_account_id UUID;

CREATE OR REPLACE FUNCTION business.guard_spend_account_pin() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF (OLD.account_class IS NOT NULL AND NEW.account_class IS DISTINCT FROM OLD.account_class)
       OR (OLD.pinned_wallet_account_id IS NOT NULL
           AND NEW.pinned_wallet_account_id IS DISTINCT FROM OLD.pinned_wallet_account_id) THEN
        RAISE EXCEPTION 'Spend account pin is immutable once set' USING ERRCODE = '55000';
    END IF;
    RETURN NEW;
END $$;
ALTER FUNCTION business.guard_spend_account_pin() OWNER TO bp_owner;

CREATE OR REPLACE TRIGGER conversation_inference_spend_coordinator_pin_guard
BEFORE UPDATE ON business.conversation_inference_spend_coordinators
FOR EACH ROW EXECUTE FUNCTION business.guard_spend_account_pin();

CREATE OR REPLACE TRIGGER environment_spend_attempt_pin_guard
BEFORE UPDATE ON business.environment_spend_attempts
FOR EACH ROW EXECUTE FUNCTION business.guard_spend_account_pin();

COMMIT;
