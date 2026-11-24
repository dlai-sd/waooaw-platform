-- Implements: work-contracts/WC-168-operator-console-works-on-demo.md WC168-R012
-- Constitutional basis: C-023, C-049, C-063, C-065
-- Founder-approved (2026-11-24: "approved") read of the blocked outbound WhatsApp message behind DEAD_LETTER_AGE_BREACH.
-- It reads only the message id, its state, the blocked reason and its age. It never reads the payload reference, the
-- recipient, the template, the tenant or any message text. It changes nothing: it runs inside a read-only transaction
-- that is rolled back. Run through scripts/wc168_demo_db_catalog_read.sh with WC168_SQL_FILE pointing at this file.
BEGIN READ ONLY;
\pset tuples_only on
\pset format unaligned
\pset fieldsep '|'

SELECT 'ROLE|' || current_user;

SELECT 'OUTBOXSTATE|' || state || '|' || COALESCE(blocked_reason, '<none>') || '|' || count(*)
FROM business.conversation_outbox
WHERE state IN ('BLOCKED', 'UNRESOLVED')
GROUP BY state, blocked_reason;

SELECT 'BLOCKED|' || outbox_id || '|' || state || '|' || COALESCE(blocked_reason, '<none>') || '|created=' || created_at || '|updated=' || updated_at ||
       '|age_minutes=' || floor(extract(epoch FROM (now() - updated_at)) / 60)
FROM business.conversation_outbox
WHERE state = 'BLOCKED'
ORDER BY updated_at
LIMIT 20;

ROLLBACK;
