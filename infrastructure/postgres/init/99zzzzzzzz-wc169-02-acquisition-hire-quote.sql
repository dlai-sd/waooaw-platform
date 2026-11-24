-- Implements: work-contracts/WC-169-paid-hire-and-connected-accounts.md WC169-R013
-- Constitutional basis: C-023, C-059, C-063
-- WC-169 R013: a Hire is priced from the monthly package the Founder put on sale, locked when the customer accepts it.
-- The quote lives on the acquisition intent, so it is bound to the customer, the accepted contract hash and the payment
-- by the same row. The columns are written once at insert and are immutable afterwards; the grants already given to the
-- application on this table (select, insert, update) are unchanged and nothing is deleted.
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '30s';
SET LOCAL ROLE bp_owner;

ALTER TABLE business.acquisition_intents
    ADD COLUMN IF NOT EXISTS quote_package_id UUID,
    ADD COLUMN IF NOT EXISTS quote_package_code VARCHAR(64),
    ADD COLUMN IF NOT EXISTS quote_period_days INTEGER,
    ADD COLUMN IF NOT EXISTS quote_gross_inr_paise BIGINT,
    ADD COLUMN IF NOT EXISTS quote_gst_inr_paise BIGINT,
    ADD COLUMN IF NOT EXISTS quote_base_inr_paise BIGINT,
    ADD COLUMN IF NOT EXISTS quote_version CHAR(64);

ALTER TABLE business.acquisition_intents
    DROP CONSTRAINT IF EXISTS acquisition_intents_quote_complete_check,
    ADD CONSTRAINT acquisition_intents_quote_complete_check CHECK (
        (
            quote_package_id IS NULL AND quote_package_code IS NULL AND quote_period_days IS NULL
            AND quote_gross_inr_paise IS NULL AND quote_gst_inr_paise IS NULL AND quote_base_inr_paise IS NULL
            AND quote_version IS NULL
        )
        OR (
            mode = 'HIRE'
            AND quote_package_id IS NOT NULL AND quote_package_code IS NOT NULL AND quote_period_days > 0
            AND quote_gross_inr_paise > 0 AND quote_gst_inr_paise >= 0 AND quote_gst_inr_paise <= quote_gross_inr_paise
            AND quote_base_inr_paise >= 0 AND quote_version ~ '^[0-9a-f]{64}$'
        )
    );

CREATE OR REPLACE FUNCTION business.acquisition_intents_quote_immutable()
RETURNS trigger
LANGUAGE plpgsql
AS $function$
BEGIN
    IF ROW(NEW.quote_package_id, NEW.quote_package_code, NEW.quote_period_days, NEW.quote_gross_inr_paise,
           NEW.quote_gst_inr_paise, NEW.quote_base_inr_paise, NEW.quote_version)
       IS DISTINCT FROM
       ROW(OLD.quote_package_id, OLD.quote_package_code, OLD.quote_period_days, OLD.quote_gross_inr_paise,
           OLD.quote_gst_inr_paise, OLD.quote_base_inr_paise, OLD.quote_version) THEN
        RAISE EXCEPTION 'The accepted Hire quote cannot change' USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END
$function$;

CREATE OR REPLACE TRIGGER acquisition_intents_quote_immutable
    BEFORE UPDATE ON business.acquisition_intents
    FOR EACH ROW EXECUTE FUNCTION business.acquisition_intents_quote_immutable();

COMMIT;
