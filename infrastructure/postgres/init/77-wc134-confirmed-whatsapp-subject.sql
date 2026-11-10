-- Implements: WC-134 R005; identity-boundary.md Section 6.3.
-- constitutional_basis: C-023, C-026, C-059, C-063

BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '30s';

ALTER TABLE identity.account_links
    ADD COLUMN IF NOT EXISTS confirmed_phone_subject_hash varchar(64);

UPDATE identity.account_links
SET state = 'Expired', updated_at = clock_timestamp()
WHERE state = 'Linked'
  AND (
      confirmed_phone_subject_hash IS NULL
      OR confirmed_phone_subject_hash !~ '^[0-9a-f]{64}$'
  );

DO $constraints$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'identity.account_links'::regclass
          AND conname = 'account_links_confirmed_phone_subject_check'
    ) THEN
        ALTER TABLE identity.account_links
            ADD CONSTRAINT account_links_confirmed_phone_subject_check CHECK (
                state <> 'Linked' OR (
                    confirmed_phone_subject_hash IS NOT NULL
                    AND confirmed_phone_subject_hash ~ '^[0-9a-f]{64}$'
                )
            ) NOT VALID;
    END IF;
END
$constraints$;

ALTER TABLE identity.account_links
    VALIDATE CONSTRAINT account_links_confirmed_phone_subject_check;

COMMIT;
