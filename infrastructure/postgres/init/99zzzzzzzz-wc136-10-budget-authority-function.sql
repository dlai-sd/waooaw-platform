-- Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C5-04
-- Constitutional basis: C-023, C-059, C-063, C-088
-- WC-136: the environment spend ceiling is changed only through this owner-defined function. It refuses
-- a value above the hard maximum the caller passes in (EnvironmentSpendOptions.HardMaximumInr * 100) and
-- refuses lowering below the exposure already reserved, leased or settled in the window, returning the
-- blocking amount so the operator can see why. A dry run reports the same outcome without writing.
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '30s';
SET LOCAL ROLE bp_owner;

CREATE OR REPLACE FUNCTION business.apply_environment_spend_ceiling(
    p_environment TEXT,
    p_maximum_paise BIGINT,
    p_hard_maximum_paise BIGINT,
    p_authority_evidence_id UUID,
    p_as_of TIMESTAMPTZ,
    p_dry_run BOOLEAN DEFAULT false
) RETURNS TABLE (
    outcome TEXT,
    previous_paise BIGINT,
    applied_paise BIGINT,
    blocking_paise BIGINT
)
LANGUAGE plpgsql SECURITY DEFINER SET search_path = business, pg_temp AS $$
DECLARE
    v_authority business.environment_spend_authorities%ROWTYPE;
    v_exposure BIGINT;
BEGIN
    IF p_environment IS NULL OR length(p_environment) = 0
       OR p_maximum_paise IS NULL OR p_maximum_paise < 0
       OR p_hard_maximum_paise IS NULL OR p_hard_maximum_paise < 0
       OR p_authority_evidence_id IS NULL
       OR p_authority_evidence_id = '00000000-0000-0000-0000-000000000000'::UUID
       OR p_as_of IS NULL THEN
        RAISE EXCEPTION 'SPEND_CEILING_ARGUMENT_INVALID' USING ERRCODE = '22023';
    END IF;

    SELECT * INTO v_authority
    FROM business.environment_spend_authorities
    WHERE environment = p_environment
    FOR UPDATE;
    IF NOT FOUND THEN
        RETURN QUERY SELECT 'AUTHORITY_ABSENT'::TEXT, NULL::BIGINT, NULL::BIGINT, NULL::BIGINT;
        RETURN;
    END IF;

    IF p_maximum_paise > p_hard_maximum_paise THEN
        RETURN QUERY SELECT 'ABOVE_HARD_MAXIMUM'::TEXT, v_authority.maximum_paise, NULL::BIGINT,
            p_hard_maximum_paise;
        RETURN;
    END IF;

    IF p_maximum_paise < v_authority.maximum_paise THEN
        v_exposure := business.environment_spend_exposure(p_environment, p_as_of);
        IF p_maximum_paise < v_exposure THEN
            RETURN QUERY SELECT 'BELOW_EXPOSURE'::TEXT, v_authority.maximum_paise, NULL::BIGINT, v_exposure;
            RETURN;
        END IF;
    END IF;

    IF p_maximum_paise = v_authority.maximum_paise
       AND v_authority.active AND v_authority.migration_complete THEN
        RETURN QUERY SELECT 'UNCHANGED'::TEXT, v_authority.maximum_paise, v_authority.maximum_paise,
            NULL::BIGINT;
        RETURN;
    END IF;

    IF p_dry_run THEN
        RETURN QUERY SELECT 'DRY_RUN_OK'::TEXT, v_authority.maximum_paise, p_maximum_paise, NULL::BIGINT;
        RETURN;
    END IF;

    UPDATE business.environment_spend_authorities
    SET maximum_paise = p_maximum_paise,
        authority_evidence_id = p_authority_evidence_id,
        authority_version = v_authority.authority_version + 1,
        updated_at = clock_timestamp()
    WHERE environment = p_environment;
    RETURN QUERY SELECT 'APPLIED'::TEXT, v_authority.maximum_paise, p_maximum_paise, NULL::BIGINT;
END
$$;
ALTER FUNCTION business.apply_environment_spend_ceiling(TEXT, BIGINT, BIGINT, UUID, TIMESTAMPTZ, BOOLEAN)
    OWNER TO bp_owner;
REVOKE ALL ON FUNCTION
    business.apply_environment_spend_ceiling(TEXT, BIGINT, BIGINT, UUID, TIMESTAMPTZ, BOOLEAN)
    FROM PUBLIC;
GRANT EXECUTE ON FUNCTION
    business.apply_environment_spend_ceiling(TEXT, BIGINT, BIGINT, UUID, TIMESTAMPTZ, BOOLEAN)
    TO business_app;

COMMIT;
