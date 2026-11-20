-- Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C4-05
-- Constitutional basis: C-059, C-090
-- COMPENSATING SCRIPT - NOT part of the init chain. Run by the Platform IT Expert only on a Founder
-- rollback decision (WC-136 Rollout And Rollback). It restores the original bundle_profiles unique key
-- uq_bundle_profile (agent_type, bundle_tier, bundle_version) that 99zzzzzzzz-wc136-07-pricing-versions.sql
-- replaced. The added columns agent_version and package_version_id and the widened bundle_tier are
-- additive and are left in place so existing contract and allowance rows stay valid.
-- The restore is refused, without changing anything, while two agent versions share a package code
-- and bundle version.
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '30s';
DO $owner$
BEGIN
    IF NOT pg_has_role(session_user, 'bp_owner', 'SET') THEN
        EXECUTE format('GRANT bp_owner TO %I', session_user);
        PERFORM set_config('waooaw.wc136_restore_bp_owner_granted', 'true', true);
    END IF;
END
$owner$;
SET LOCAL ROLE bp_owner;

DO $restore$
BEGIN
    IF EXISTS (
        SELECT 1 FROM institutional.bundle_profiles
        GROUP BY agent_type, bundle_tier, bundle_version
        HAVING COUNT(*) > 1
    ) THEN
        RAISE EXCEPTION 'Cannot restore uq_bundle_profile: several agent versions share a package code'
            USING ERRCODE = '55000';
    END IF;
    ALTER TABLE institutional.bundle_profiles
        DROP CONSTRAINT IF EXISTS uq_bundle_profile_agent_version;
    ALTER TABLE institutional.bundle_profiles
        DROP CONSTRAINT IF EXISTS uq_bundle_profile;
    ALTER TABLE institutional.bundle_profiles
        ADD CONSTRAINT uq_bundle_profile UNIQUE (agent_type, bundle_tier, bundle_version);
END
$restore$;

RESET ROLE;
DO $owner$
BEGIN
    IF current_setting('waooaw.wc136_restore_bp_owner_granted', true) = 'true' THEN
        EXECUTE format('REVOKE bp_owner FROM %I', session_user);
    END IF;
END
$owner$;
COMMIT;
