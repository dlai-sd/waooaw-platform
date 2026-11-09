-- Implements: WC-134 web registration requires verified WhatsApp contact
-- constitutional_basis: C-005, C-026, C-059, C-063

ALTER TABLE identity.verification_challenges
ADD COLUMN IF NOT EXISTS destination_hmac_key VARCHAR(128),
ADD COLUMN IF NOT EXISTS destination_hmac_version VARCHAR(32),
ADD COLUMN IF NOT EXISTS destination_hmac_domain VARCHAR(16),
ADD COLUMN IF NOT EXISTS failed_attempts INTEGER NOT NULL DEFAULT 0
CHECK (failed_attempts BETWEEN 0 AND 5),
ADD COLUMN IF NOT EXISTS delivery_state VARCHAR(16)
CHECK (delivery_state IN ('DISPATCHING', 'SUBMITTED', 'UNAVAILABLE'));

UPDATE identity.verification_challenges
SET state = 'Expired'
WHERE
    registration_id IS NOT NULL
    AND purpose = 'Mobile'
    AND state = 'Pending'
    AND (
        destination_hmac_key IS NULL
        OR destination_hmac_version IS NULL
        OR destination_hmac_domain IS DISTINCT FROM 'mobile'
        OR delivery_state IS DISTINCT FROM 'SUBMITTED'
    );

ALTER TABLE identity.registrations
DROP CONSTRAINT IF EXISTS registrations_state_check,
ADD CONSTRAINT registrations_state_check CHECK (state IN (
    'Started', 'FederatedIdentityAccepted', 'CredentialIdentityAccepted',
    'WhatsAppIdentityAccepted', 'EmailVerificationRequired',
    'DuplicateResolutionRequired', 'ProfileCompletionRequired',
    'MobileVerificationRequired', 'ReadyToComplete', 'Completed',
    'Expired', 'Cancelled'
));

DROP INDEX IF EXISTS identity.registrations_mobile_match_key_idx;

CREATE UNIQUE INDEX IF NOT EXISTS registrations_mobile_match_key_idx
ON identity.registrations (mobile_hmac_domain, mobile_hmac_version, mobile_hmac_key)
WHERE mobile_hmac_key IS NOT NULL
AND mobile_verified = TRUE
AND state = 'Completed';

UPDATE identity.registrations AS r
SET
    mobile_verified = FALSE,
    mobile_hmac_key = NULL,
    mobile_hmac_version = NULL,
    mobile_hmac_domain = NULL,
    masked_mobile = NULL,
    updated_at = NOW()
WHERE
    r.state <> 'Completed'
    AND r.mobile_verified = TRUE
    AND NOT EXISTS (
        SELECT 1
        FROM identity.verification_challenges AS c
        WHERE
            c.registration_id = r.registration_id
            AND c.purpose = 'Mobile'
            AND c.state = 'Consumed'
            AND c.delivery_state = 'SUBMITTED'
            AND c.verified_at IS NOT NULL
            AND c.destination_hmac_key = r.mobile_hmac_key
            AND c.destination_hmac_version = r.mobile_hmac_version
            AND c.destination_hmac_domain = r.mobile_hmac_domain
    );

UPDATE identity.registrations
SET
    state = 'MobileVerificationRequired',
    updated_at = NOW()
WHERE
    state = 'ReadyToComplete'
    AND mobile_verified = FALSE;
