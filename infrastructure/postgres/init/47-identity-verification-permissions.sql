-- Implements: architecture/reference/components/identity-boundary.md section 8
-- Constitutional basis: C-005, C-007, C-026, C-059

GRANT SELECT, INSERT, UPDATE ON identity.verification_challenges TO business_app;

GRANT UPDATE (
    state,
    email_verified,
    mobile_verified,
    email_hmac_key,
    email_hmac_version,
    email_hmac_domain,
    mobile_hmac_key,
    mobile_hmac_version,
    mobile_hmac_domain,
    masked_email,
    masked_mobile,
    updated_at
) ON identity.registrations TO business_app;