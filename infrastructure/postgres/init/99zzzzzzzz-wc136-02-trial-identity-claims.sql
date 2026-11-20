-- Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C3-03
-- Constitutional basis: C-019, C-059, C-088, C-090
-- WC-136 C3-03: one trial per verified identity per exact agent version.
-- The claim key is the server-verified pseudonymous subject hash; no phone, name or email is stored.
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
        PERFORM set_config('waooaw.wc136_trial_claims_bp_owner_granted', 'true', true);
    END IF;
    IF NOT pg_has_role(session_user, 'wbe_owner', 'SET') THEN
        EXECUTE format('GRANT wbe_owner TO %I', session_user);
        PERFORM set_config('waooaw.wc136_trial_claims_wbe_owner_granted', 'true', true);
    END IF;
END
$owner$;
SET LOCAL ROLE bp_owner;

CREATE TABLE IF NOT EXISTS business.trial_identity_claims (
    identity_subject_hash TEXT NOT NULL CHECK (identity_subject_hash ~ '^[0-9a-f]{64}$'),
    agent_type TEXT NOT NULL,
    agent_version TEXT NOT NULL,
    trial_id UUID NOT NULL REFERENCES business.trial_allocations(trial_id),
    claimed_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (identity_subject_hash, agent_type, agent_version)
);

GRANT USAGE ON SCHEMA business TO wbe_owner;
GRANT CREATE ON SCHEMA business TO wbe_owner;
RESET ROLE;
ALTER TABLE business.trial_identity_claims OWNER TO wbe_owner;
SET LOCAL ROLE wbe_owner;
CREATE INDEX IF NOT EXISTS trial_identity_claims_trial
    ON business.trial_identity_claims (trial_id);
RESET ROLE;
SET LOCAL ROLE bp_owner;
REVOKE CREATE ON SCHEMA business FROM wbe_owner;
RESET ROLE;
REVOKE ALL ON business.trial_identity_claims FROM PUBLIC, business_app;
GRANT SELECT, INSERT ON business.trial_identity_claims TO wbe_app;
DO $owner$
BEGIN
    IF current_setting('waooaw.wc136_trial_claims_wbe_owner_granted', true) = 'true' THEN
        EXECUTE format('REVOKE wbe_owner FROM %I', session_user);
    END IF;
    IF current_setting('waooaw.wc136_trial_claims_bp_owner_granted', true) = 'true' THEN
        EXECUTE format('REVOKE bp_owner FROM %I', session_user);
    END IF;
END
$owner$;
COMMIT;
