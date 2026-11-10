-- Implements: WC-134 R002, R006; verified sender-scoped relationship reply routing.
-- constitutional_basis: C-023, C-026, C-059, C-063

BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '30s';

ALTER TABLE business.whatsapp_journey_contacts
ADD COLUMN IF NOT EXISTS protected_destination varchar(256),
ADD COLUMN IF NOT EXISTS destination_verified_at timestamptz;

DO $constraints$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'business.whatsapp_journey_contacts'::regclass
          AND conname = 'whatsapp_journey_contacts_destination_check'
    ) THEN
        ALTER TABLE business.whatsapp_journey_contacts
            ADD CONSTRAINT whatsapp_journey_contacts_destination_check CHECK (
                (protected_destination IS NULL AND destination_verified_at IS NULL)
                OR (protected_destination LIKE 'v1.%' AND destination_verified_at IS NOT NULL)
            );
    END IF;
END
$constraints$;

COMMIT;
