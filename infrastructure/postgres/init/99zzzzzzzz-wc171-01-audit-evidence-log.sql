-- Implements: work-contracts/WC-171-agent-navigation-alerts-and-oversight.md WC171-R012
-- Constitutional basis: C-007 (append-only audit), C-023 (evidence before action), C-059
-- WC-171 C4: the nightly reconciliation writes one evidence row per audit run into audit_evidence_log, and no init file
-- created the table, so every run failed at that insert on Demo (WC-169 G14). Columns match what the service binds:
-- ISO-8601 text for the date and timestamp, a text id. Append-only: the runtime roles may insert and read, never
-- update or delete.
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '30s';

CREATE TABLE IF NOT EXISTS institutional.audit_evidence_log (
    id TEXT NOT NULL PRIMARY KEY,
    audit_type TEXT NOT NULL,
    audit_date TEXT NOT NULL,
    total_checked INTEGER NOT NULL CHECK (total_checked >= 0),
    unlinked_count INTEGER NOT NULL CHECK (unlinked_count >= 0),
    outcome TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS audit_evidence_log_type_date_idx
    ON institutional.audit_evidence_log (audit_type, audit_date DESC);

DO $$
DECLARE
    runtime_role TEXT;
BEGIN
    FOREACH runtime_role IN ARRAY ARRAY['wbe_app', 'billing_runtime'] LOOP
        IF EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = runtime_role) THEN
            EXECUTE format('GRANT SELECT, INSERT ON institutional.audit_evidence_log TO %I', runtime_role);
        END IF;
    END LOOP;
END
$$;

COMMIT;
