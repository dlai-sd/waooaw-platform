-- Demo checkout coupon and zero-price evidence upgrade for fresh and reused databases.

INSERT INTO business.coupon_codes
    (coupon_id, code, discount_pct, bonus_credits_paise, agent_type, min_bundle_tier,
     max_uses, uses_count, valid_from, valid_until, active, is_active)
VALUES
    (gen_random_uuid(), 'DEMO100', 100, 0, NULL, NULL,
     NULL, 0, NOW(), NULL, TRUE, TRUE)
ON CONFLICT (code) DO UPDATE SET
    discount_pct = EXCLUDED.discount_pct,
    max_uses = NULL,
    valid_until = NULL,
    active = TRUE,
    is_active = TRUE;

ALTER TABLE business.zero_price_commercial_outcomes
ADD COLUMN IF NOT EXISTS coupon_code VARCHAR(20);

CREATE OR REPLACE FUNCTION business.protect_zero_price_commercial_outcome()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'zero-price commercial outcomes cannot be deleted';
    END IF;
    IF ROW(
        OLD.checkout_intent_id, OLD.tenant_id, OLD.customer_id, OLD.relationship_id,
        OLD.accepted_contract_id, OLD.contract_version, OLD.contract_hash,
        OLD.contract_acceptance_id, OLD.payment_consent_evidence_id,
        OLD.commercial_evidence_id, OLD.agent_type, OLD.bundle_tier,
        OLD.quote_version, OLD.promotion_version, OLD.coupon_code, OLD.outcome_reference, OLD.created_at
    ) IS DISTINCT FROM ROW(
        NEW.checkout_intent_id, NEW.tenant_id, NEW.customer_id, NEW.relationship_id,
        NEW.accepted_contract_id, NEW.contract_version, NEW.contract_hash,
        NEW.contract_acceptance_id, NEW.payment_consent_evidence_id,
        NEW.commercial_evidence_id, NEW.agent_type, NEW.bundle_tier,
        NEW.quote_version, NEW.promotion_version, NEW.coupon_code, NEW.outcome_reference, NEW.created_at
    ) THEN
        RAISE EXCEPTION 'zero-price commercial outcome identity is immutable';
    END IF;
    IF OLD.status = 'ACTIVATED' AND NEW IS DISTINCT FROM OLD THEN
        RAISE EXCEPTION 'activated zero-price commercial outcomes are immutable';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;