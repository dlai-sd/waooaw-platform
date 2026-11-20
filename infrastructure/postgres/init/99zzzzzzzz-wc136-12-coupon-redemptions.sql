-- Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C5-07
-- Constitutional basis: C-059, C-088, C-089
-- WC-136: every goodwill coupon redemption is recorded with its reason. A coupon applies at hire or
-- renewal only; it is the single goodwill path and never creates wallet credit. A redemption names its
-- period so a renewal redeems once per period, and a retry with the same idempotency key replays.
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '30s';
SET LOCAL ROLE bp_owner;

CREATE TABLE IF NOT EXISTS business.coupon_version_redemptions (
    redemption_id UUID PRIMARY KEY,
    version_id UUID NOT NULL,
    coupon_code TEXT NOT NULL CHECK (length(coupon_code) BETWEEN 1 AND 64),
    tenant_id UUID NOT NULL,
    relationship_id UUID NOT NULL,
    event TEXT NOT NULL CHECK (event IN ('HIRE', 'RENEWAL')),
    period_start TIMESTAMPTZ NOT NULL,
    price_incl_gst_paise BIGINT NOT NULL CHECK (price_incl_gst_paise > 0),
    discount_paise BIGINT NOT NULL CHECK (discount_paise >= 0),
    reason TEXT NOT NULL CHECK (length(reason) BETWEEN 1 AND 500),
    idempotency_key UUID NOT NULL UNIQUE,
    redeemed_at TIMESTAMPTZ NOT NULL,
    UNIQUE (version_id, relationship_id, event, period_start)
);
CREATE INDEX IF NOT EXISTS idx_coupon_version_redemptions_version
    ON business.coupon_version_redemptions (version_id);

REVOKE ALL ON business.coupon_version_redemptions FROM PUBLIC, business_app;
GRANT SELECT, INSERT ON business.coupon_version_redemptions TO wbe_app;

COMMIT;
