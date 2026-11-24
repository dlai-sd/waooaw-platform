-- Implements: work-contracts/WC-167-acceptance-demo-readiness.md WC167-R011; standards/PLATFORM-SETTINGS-AND-ACCESS-POLICY.md rule A2
-- Constitutional basis: C-009, C-023, C-059, C-063
-- WC-167 R011: a configured Founder may opt in (rebind_on_start) to releasing the stored sign-in identity at every start,
-- so the first verified sign-in after a deployment ties it again. The release is recorded as its own event; the event
-- table still only ever receives inserts from the application.
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '30s';
SET LOCAL ROLE bp_owner;

ALTER TABLE business.platform_access_events
    DROP CONSTRAINT IF EXISTS platform_access_events_event_type_check,
    ADD CONSTRAINT platform_access_events_event_type_check CHECK (event_type IN (
        'FOUNDER_BOOTSTRAPPED', 'FOUNDER_SUBJECT_BOUND', 'FOUNDER_SUBJECT_RELEASED', 'FOUNDER_REMOVED_BY_CONFIGURATION',
        'REQUESTED', 'APPROVED', 'REJECTED', 'REVOKED'
    ));

COMMIT;
