-- Implements: work-contracts/WC-103-multitenant-authentication-journeys.md §AUTH-S10
-- Constitutional basis: C-005, C-023, C-026, C-059

ALTER TABLE identity.account_links
    ADD COLUMN IF NOT EXISTS start_evidence_id UUID,
    ADD COLUMN IF NOT EXISTS approval_evidence_id UUID;

ALTER TABLE identity.account_links
    DROP CONSTRAINT IF EXISTS account_links_start_evidence_required,
    ADD CONSTRAINT account_links_start_evidence_required CHECK (start_evidence_id IS NOT NULL) NOT VALID;

COMMENT ON COLUMN identity.account_links.start_evidence_id IS
    'Constitutional Audit Ledger evidence confirmed before link creation.';
COMMENT ON COLUMN identity.account_links.approval_evidence_id IS
    'Constitutional Audit Ledger evidence confirmed before portal approval.';