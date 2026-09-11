-- Implements: architecture/reference/components/environment-readiness-and-data-continuity.md §6
-- Constitutional basis: C-023, C-026, C-059, C-063

ALTER TABLE identity.registrations
    ADD COLUMN IF NOT EXISTS email_hmac_version VARCHAR(32),
    ADD COLUMN IF NOT EXISTS email_hmac_domain VARCHAR(16),
    ADD COLUMN IF NOT EXISTS mobile_hmac_version VARCHAR(32),
    ADD COLUMN IF NOT EXISTS mobile_hmac_domain VARCHAR(16);

ALTER TABLE identity.verification_challenges
    ADD COLUMN IF NOT EXISTS code_hmac_version VARCHAR(32) NOT NULL DEFAULT 'v1';

UPDATE identity.registrations
SET email_hmac_version = COALESCE(email_hmac_version, 'legacy-v1'),
    email_hmac_domain = COALESCE(email_hmac_domain, 'legacy-email')
WHERE email_hmac_key IS NOT NULL;

UPDATE identity.registrations
SET mobile_hmac_version = COALESCE(mobile_hmac_version, 'legacy-v1'),
    mobile_hmac_domain = COALESCE(mobile_hmac_domain, 'legacy-mobile')
WHERE mobile_hmac_key IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS registrations_email_match_key_idx
    ON identity.registrations (email_hmac_domain, email_hmac_version, email_hmac_key)
    WHERE email_hmac_key IS NOT NULL AND state = 'Completed';

CREATE UNIQUE INDEX IF NOT EXISTS registrations_mobile_match_key_idx
    ON identity.registrations (mobile_hmac_domain, mobile_hmac_version, mobile_hmac_key)
    WHERE mobile_hmac_key IS NOT NULL AND state = 'Completed';