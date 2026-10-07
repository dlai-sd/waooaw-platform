-- Implements: WC-112 R056
-- Constitutional basis: C-023, C-059, C-088

CREATE TABLE IF NOT EXISTS business.coupon_reservations (
    reservation_id UUID PRIMARY KEY,
    checkout_intent_id UUID NOT NULL UNIQUE,
    coupon_id UUID NOT NULL REFERENCES business.coupon_codes(coupon_id),
    customer_id UUID NOT NULL,
    professional_type VARCHAR(64) NOT NULL,
    professional_version VARCHAR(32) NOT NULL,
    status VARCHAR(16) NOT NULL CHECK (status IN ('RESERVED', 'CONSUMED', 'RELEASED', 'EXPIRED')),
    reserved_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    consumed_at TIMESTAMPTZ,
    released_at TIMESTAMPTZ,
    CONSTRAINT coupon_reservation_version_check
        CHECK (professional_version ~ '^[0-9]+\.[0-9]+\.[0-9]+$')
);

CREATE INDEX IF NOT EXISTS idx_coupon_reservations_capacity
    ON business.coupon_reservations (coupon_id, status, expires_at);

GRANT SELECT, INSERT, UPDATE ON business.coupon_reservations TO wbe_app;

ALTER TABLE business.pre_hire_checkout_orders
    DROP CONSTRAINT IF EXISTS pre_hire_checkout_status_check;

ALTER TABLE business.pre_hire_checkout_orders
    ADD CONSTRAINT pre_hire_checkout_status_check CHECK (
        status IN (
            'CREATING', 'AWAITING_PROVIDER', 'CAPTURED', 'FULLY_DISCOUNTED',
            'UNRESOLVED', 'CANCELLED'
        )
    );
