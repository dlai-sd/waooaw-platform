-- Implements: work-contracts/WC-137-platform-access-and-environment-feature-settings.md WC137-R006
-- Constitutional basis: C-009, C-048, C-059, C-063
-- The WhatsApp journey now asks which professional a visitor wants before anything else, so a visitor session
-- can be in two more states. Idempotent: the constraint is replaced only while it lacks the new states, because
-- Demo re-applies every init file at BP startup.
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '30s';

DO $$
BEGIN
    IF to_regclass('business.visitor_sessions') IS NOT NULL
       AND NOT EXISTS (
           SELECT 1
           FROM pg_constraint
           WHERE conrelid = 'business.visitor_sessions'::regclass
             AND conname = 'visitor_sessions_state_check'
             AND pg_get_constraintdef(oid) LIKE '%CHOOSE_PROFESSIONAL%'
       )
    THEN
        ALTER TABLE business.visitor_sessions DROP CONSTRAINT IF EXISTS visitor_sessions_state_check;
        ALTER TABLE business.visitor_sessions ADD CONSTRAINT visitor_sessions_state_check CHECK (
            state IN ('NEW', 'CONSENT_PENDING', 'DISCOVER', 'QUALIFY', 'CHOOSE_PROFESSIONAL',
                      'PROFESSIONAL_CARD', 'SHOW_VALUE', 'OTHER_PROFESSIONALS', 'HANDOFF', 'STOPPED')
        );
    END IF;
END
$$;

COMMIT;
