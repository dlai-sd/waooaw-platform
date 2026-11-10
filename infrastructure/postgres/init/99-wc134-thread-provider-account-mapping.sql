-- WC-134: owner-controlled catalogue/provider identity; existing threads remain unmapped.
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '30s';
SET LOCAL ROLE bp_owner;

ALTER TABLE institutional.thread_catalog
ADD COLUMN IF NOT EXISTS provider_account_id UUID
REFERENCES institutional.provider_accounts (id);

COMMIT;
