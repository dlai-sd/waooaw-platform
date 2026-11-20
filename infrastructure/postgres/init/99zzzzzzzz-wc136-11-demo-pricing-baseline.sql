-- Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C5-06
-- Constitutional basis: C-059, C-088, C-089, C-090, C-091
-- WC-136: Demo pricing baseline. Every row is flagged seed = true and every statement is idempotent.
-- This file belongs to the lower-environment init chain only (the Demo provisioner applies it);
-- Production values are never seeded and are entered through the Pricing Console.
-- The illustrative STARTER package stays a DRAFT on purpose: its proactive-message recipe references a
-- thread pending Founder authorization and its publication components are default-off, so it cannot be
-- authorized and no price becomes effective. Bodies are in the canonical stored form of the validators,
-- and each body_digest is computed in SQL with the same canonical JSON the pricing service uses.
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '30s';
DO $owner$
BEGIN
    IF NOT pg_has_role(session_user, 'bp_owner', 'SET') THEN
        EXECUTE format('GRANT bp_owner TO %I', session_user);
        PERFORM set_config('waooaw.wc136_baseline_bp_owner_granted', 'true', true);
    END IF;
    IF NOT pg_has_role(session_user, 'wbe_owner', 'SET') THEN
        EXECUTE format('GRANT wbe_owner TO %I', session_user);
        PERFORM set_config('waooaw.wc136_baseline_wbe_owner_granted', 'true', true);
    END IF;
END
$owner$;
SET LOCAL ROLE bp_owner;
GRANT USAGE, CREATE ON SCHEMA institutional TO wbe_owner;
RESET ROLE;
SET LOCAL ROLE wbe_owner;

-- Canonical JSON: keys sorted by code point, compact separators, strings as the pricing service writes them.
CREATE OR REPLACE FUNCTION institutional.pricing_canonical_json(p_value JSONB) RETURNS TEXT
LANGUAGE plpgsql IMMUTABLE SET search_path = pg_catalog, institutional AS $$
DECLARE
    v_type TEXT := jsonb_typeof(p_value);
BEGIN
    IF v_type = 'object' THEN
        RETURN '{' || COALESCE((
            SELECT string_agg(
                to_jsonb(item.key)::TEXT || ':' || institutional.pricing_canonical_json(item.value),
                ',' ORDER BY item.key COLLATE "C")
            FROM jsonb_each(p_value) AS item
        ), '') || '}';
    ELSIF v_type = 'array' THEN
        RETURN '[' || COALESCE((
            SELECT string_agg(institutional.pricing_canonical_json(item.value), ',' ORDER BY item.position)
            FROM jsonb_array_elements(p_value) WITH ORDINALITY AS item(value, position)
        ), '') || ']';
    END IF;
    RETURN p_value::TEXT;
END
$$;

CREATE OR REPLACE FUNCTION institutional.pricing_body_digest(p_body JSONB) RETURNS TEXT
LANGUAGE sql IMMUTABLE SET search_path = pg_catalog, institutional AS $$
    SELECT encode(sha256(convert_to(institutional.pricing_canonical_json(p_body), 'UTF8')), 'hex')
$$;

GRANT EXECUTE ON FUNCTION
    institutional.pricing_canonical_json(JSONB),
    institutional.pricing_body_digest(JSONB)
    TO wbe_app;

CREATE TEMPORARY TABLE pricing_baseline_seed (
    version_id UUID NOT NULL,
    event_id UUID NOT NULL,
    evidence_id UUID NOT NULL,
    kind TEXT NOT NULL,
    subject_key TEXT NOT NULL,
    state TEXT NOT NULL,
    body JSONB NOT NULL,
    reason TEXT NOT NULL
) ON COMMIT DROP;

INSERT INTO pricing_baseline_seed (version_id, event_id, evidence_id, kind, subject_key, state, body, reason)
VALUES
('136a0000-0000-4000-8000-000000000001', '136e0000-0000-4000-8000-000000000001',
 '136c0000-0000-4000-8000-000000000001', 'POLICY', 'policy:platform', 'EFFECTIVE',
 '{"minimumMarginPct":55.0,"minimumMarginNote":"SEED_UNCONFIRMED","paymentGraceDays":7,"sunsetNoticeDays":30,"costToleranceFraction":0.2,"costAlertFraction":0.1,"upgradeTiming":"IMMEDIATE","downgradeTiming":"AT_RENEWAL","changeSizeGuardPercent":30.0,"priceMultipleGuard":20.0}'::JSONB,
 'SEED_DEMO_BASELINE'),
('136a0000-0000-4000-8000-000000000002', '136e0000-0000-4000-8000-000000000002',
 '136c0000-0000-4000-8000-000000000002', 'BUDGET', 'budget:ENVIRONMENT_CEILING|demo', 'EFFECTIVE',
 '{"scope":"ENVIRONMENT_CEILING","reference":"demo","maximumPaise":50000}'::JSONB,
 'SEED_DEMO_BASELINE'),
('136a0000-0000-4000-8000-000000000003', '136e0000-0000-4000-8000-000000000003',
 '136c0000-0000-4000-8000-000000000003', 'BUDGET', 'budget:ACQUISITION_CAMPAIGN|DEFAULT', 'EFFECTIVE',
 '{"scope":"ACQUISITION_CAMPAIGN","reference":"DEFAULT","maximumPaise":10000}'::JSONB,
 'SEED_DEMO_BASELINE'),
('136a0000-0000-4000-8000-000000000004', '136e0000-0000-4000-8000-000000000004',
 '136c0000-0000-4000-8000-000000000004', 'BUDGET', 'budget:SIMULATION|demo', 'EFFECTIVE',
 '{"scope":"SIMULATION","reference":"demo","maximumPaise":5000}'::JSONB,
 'SEED_DEMO_BASELINE'),
('136a0000-0000-4000-8000-000000000005', '136e0000-0000-4000-8000-000000000005',
 '136c0000-0000-4000-8000-000000000005', 'GRANT', 'grant:TRIAL|DIGITAL_MARKETING_LOCAL_SERVICE|1.0.0',
 'EFFECTIVE',
 '{"grantKind":"TRIAL","agentType":"DIGITAL_MARKETING_LOCAL_SERVICE","agentVersion":"1.0.0","amountPaise":5000,"durationDays":7,"disabled":false}'::JSONB,
 'SEED_DEMO_BASELINE'),
('136a0000-0000-4000-8000-000000000006', '136e0000-0000-4000-8000-000000000006',
 '136c0000-0000-4000-8000-000000000006', 'GRANT', 'grant:SETUP|DIGITAL_MARKETING_LOCAL_SERVICE|1.0.0',
 'EFFECTIVE',
 '{"grantKind":"SETUP","agentType":"DIGITAL_MARKETING_LOCAL_SERVICE","agentVersion":"1.0.0","amountPaise":2000,"durationDays":30,"disabled":false}'::JSONB,
 'SEED_DEMO_BASELINE'),
('136a0000-0000-4000-8000-000000000007', '136e0000-0000-4000-8000-000000000007',
 '136c0000-0000-4000-8000-000000000007', 'PACKAGE', 'package:DIGITAL_MARKETING_LOCAL_SERVICE|1.0.0|STARTER',
 'DRAFT',
 '{"agentType":"DIGITAL_MARKETING_LOCAL_SERVICE","agentVersion":"1.0.0","packageCode":"STARTER","displayName":"Digital Marketing Agent Starter ILLUSTRATIVE_NOT_FOR_SALE","billingPeriodDays":30,"priceInclGstPaise":200000,"gstRatePercent":18,"infrastructureSharePaise":15000,"components":[{"componentId":"CONTENT_PLAN","kind":"COUNTED","quantity":1,"cadence":"SPREAD","priceAllocationPaise":10000,"recipe":[{"threadId":"llm_mid_gemini","unitsPerUnit":1}],"topupAllowed":false},{"componentId":"CONTENT_DRAFT","kind":"COUNTED","quantity":4,"cadence":"SPREAD","priceAllocationPaise":40000,"recipe":[{"threadId":"llm_mid_gemini","unitsPerUnit":1}],"topupAllowed":false},{"componentId":"CONTENT_ASSET","kind":"COUNTED","quantity":4,"cadence":"SPREAD","priceAllocationPaise":30000,"recipe":[{"threadId":"image_gen_per_image","unitsPerUnit":1}],"topupAllowed":false},{"componentId":"SOCIAL_PUBLICATION","kind":"COUNTED","quantity":4,"cadence":"SPREAD","priceAllocationPaise":20000,"recipe":[{"threadId":"llm_mid_gemini","unitsPerUnit":1}],"topupAllowed":false},{"componentId":"SOCIAL_OBSERVATION","kind":"SELECTED","quantity":4,"cadence":"SPREAD","selectableMaximum":4,"priceAllocationPaise":60000,"recipe":[{"threadId":"llm_mid_gemini","unitsPerUnit":1}],"topupAllowed":false},{"componentId":"AD_BOOST","kind":"COUNTED","quantity":1,"cadence":"SPREAD","priceAllocationPaise":20000,"recipe":[{"threadId":"ad_spend_meta","unitsPerUnit":1}],"topupAllowed":false},{"componentId":"PROACTIVE_MESSAGE","kind":"COUNTED","quantity":30,"cadence":"SPREAD","priceAllocationPaise":20000,"recipe":[{"threadId":"whatsapp_template_utility","unitsPerUnit":1}],"topupAllowed":false}]}'::JSONB,
 'ILLUSTRATIVE_NOT_FOR_SALE');

INSERT INTO institutional.pricing_versions
    (version_id, kind, subject_key, version_no, state, body, body_digest, seed, effective_from,
     created_by, created_at, authorized_by, authorized_at, evidence_id)
SELECT
    seed.version_id, seed.kind, seed.subject_key, 1, seed.state, seed.body,
    institutional.pricing_body_digest(seed.body), true,
    CASE WHEN seed.state = 'EFFECTIVE' THEN clock_timestamp() END,
    'wc136-demo-baseline-seed', clock_timestamp(),
    CASE WHEN seed.state = 'EFFECTIVE' THEN 'wc136-demo-baseline-seed' END,
    CASE WHEN seed.state = 'EFFECTIVE' THEN clock_timestamp() END,
    CASE WHEN seed.state = 'EFFECTIVE' THEN seed.evidence_id END
FROM pricing_baseline_seed seed
ON CONFLICT (kind, subject_key, version_no) DO NOTHING;

INSERT INTO institutional.pricing_version_events
    (event_id, version_id, from_state, to_state, direction, actor, occurred_at, reason)
SELECT seed.event_id, seed.version_id, NULL, seed.state, 'NORMAL', 'wc136-demo-baseline-seed',
    clock_timestamp(), seed.reason
FROM pricing_baseline_seed seed
JOIN institutional.pricing_versions version ON version.version_id = seed.version_id
ON CONFLICT (event_id) DO NOTHING;

DROP TABLE pricing_baseline_seed;
RESET ROLE;
SET LOCAL ROLE bp_owner;
REVOKE CREATE ON SCHEMA institutional FROM wbe_owner;
RESET ROLE;
DO $owner$
BEGIN
    IF current_setting('waooaw.wc136_baseline_wbe_owner_granted', true) = 'true' THEN
        EXECUTE format('REVOKE wbe_owner FROM %I', session_user);
    END IF;
    IF current_setting('waooaw.wc136_baseline_bp_owner_granted', true) = 'true' THEN
        EXECUTE format('REVOKE bp_owner FROM %I', session_user);
    END IF;
END
$owner$;
COMMIT;
