-- Implements: WC-134 R005; identity-boundary.md Section 6.3.
-- constitutional_basis: C-023, C-026, C-059, C-063

BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '30s';

ALTER TABLE identity.account_links
    ADD COLUMN IF NOT EXISTS confirmation_evidence_id uuid,
    ADD COLUMN IF NOT EXISTS cancellation_evidence_id uuid,
    ADD COLUMN IF NOT EXISTS confirmation_message_digest varchar(64),
    ADD COLUMN IF NOT EXISTS confirmed_at timestamptz;

-- A legacy label without fresh-channel evidence is not a verified binding.
UPDATE identity.account_links
SET state = 'Expired', updated_at = clock_timestamp()
WHERE state = 'Linked'
  AND (confirmation_evidence_id IS NULL
       OR confirmation_evidence_id = '00000000-0000-0000-0000-000000000000'::uuid
       OR confirmation_message_digest IS NULL
       OR confirmation_message_digest !~ '^[0-9a-f]{64}$'
       OR confirmed_at IS NULL
       OR confirmed_at < created_at
       OR confirmed_at > expires_at
       OR approval_evidence_id IS NULL
       OR approval_evidence_id = '00000000-0000-0000-0000-000000000000'::uuid
       OR start_evidence_id IS NULL
       OR start_evidence_id = '00000000-0000-0000-0000-000000000000'::uuid);

DO $constraints$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'identity.account_links'::regclass
          AND conname = 'account_links_confirmed_evidence_check'
    ) THEN
        ALTER TABLE identity.account_links
            ADD CONSTRAINT account_links_confirmed_evidence_check CHECK (
                state <> 'Linked' OR (
                    confirmation_evidence_id IS NOT NULL
                    AND confirmation_evidence_id <> '00000000-0000-0000-0000-000000000000'::uuid
                    AND confirmation_message_digest IS NOT NULL
                    AND confirmation_message_digest ~ '^[0-9a-f]{64}$'
                    AND confirmed_at IS NOT NULL
                    AND confirmed_at >= created_at
                    AND confirmed_at <= expires_at
                    AND approval_evidence_id IS NOT NULL
                    AND approval_evidence_id <> '00000000-0000-0000-0000-000000000000'::uuid
                    AND start_evidence_id IS NOT NULL
                    AND start_evidence_id <> '00000000-0000-0000-0000-000000000000'::uuid
                )
            ) NOT VALID;
    END IF;
END
$constraints$;

ALTER TABLE identity.account_links
    VALIDATE CONSTRAINT account_links_confirmed_evidence_check;

COMMIT;
