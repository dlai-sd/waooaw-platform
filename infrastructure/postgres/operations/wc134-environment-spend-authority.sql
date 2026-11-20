\set ON_ERROR_STOP on

-- WC-136 C5-04 (C-059): a Founder-authorized ceiling above INR 500 is allowed only with
-- hard_maximum_paise set explicitly; without it the former 50000 paise limit applies.
\if :{?hard_maximum_paise}
\else
\set hard_maximum_paise 50000
\endif

-- Required psql variables: environment, maximum_paise, authority_evidence_id.
-- Operator-run, never an init file: the init migration deliberately leaves new environments fail-closed
-- (no authority row => every WhatsApp send is refused with ENVIRONMENT_SPEND_AUTHORITY_UNAVAILABLE).
-- Run this only after the Founder has approved an activation whose spend cap equals :maximum_paise.
-- A fresh Demo database has no legacy exposure to map, so migration is complete by construction.
SELECT 1 / CASE
    WHEN :'environment' IN ('demo', 'uat', 'production')
     AND :'maximum_paise' ~ '^[1-9][0-9]{0,8}$'
     AND :'hard_maximum_paise' ~ '^[1-9][0-9]{4,8}$'
     AND :'hard_maximum_paise'::BIGINT >= 50000
     AND (:'maximum_paise'::BIGINT <= 50000
          OR :'maximum_paise'::BIGINT <= :'hard_maximum_paise'::BIGINT)
     AND :'authority_evidence_id' ~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
     AND :'authority_evidence_id' <> '00000000-0000-0000-0000-000000000000'
     AND NOT EXISTS (SELECT 1 FROM business.conversation_model_reservations WHERE environment = :'environment')
    THEN 1
    ELSE 0
END AS valid_wc134_spend_authority_parameters;

BEGIN;
SET LOCAL ROLE bp_owner;
INSERT INTO business.environment_spend_authorities
    (environment, authority_version, maximum_paise, active, migration_complete,
     authority_evidence_id, updated_at)
VALUES (:'environment', 1, :'maximum_paise'::BIGINT, true, true,
        :'authority_evidence_id'::UUID, clock_timestamp())
ON CONFLICT (environment) DO UPDATE
SET maximum_paise = excluded.maximum_paise,
    active = true,
    migration_complete = true,
    authority_evidence_id = excluded.authority_evidence_id,
    authority_version = business.environment_spend_authorities.authority_version + 1,
    updated_at = clock_timestamp();
COMMIT;
