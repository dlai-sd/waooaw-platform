-- 05-append-only-rules.sql
-- Enforces Constitutional Audit Ledger immutability at the DB layer.
-- Constitutional basis: C-007 (LAW — no evidence deleted or modified),
--                       C-027 (append-only at database level),
--                       ADR-011 (no destructive migrations on constitutional schema)
--
-- Belt-and-suspenders approach:
--   Layer 1: Application layer (Constitutional Engine never issues UPDATE/DELETE)
--   Layer 2: DB permissions (constitutional_app has INSERT+SELECT only — no UPDATE/DELETE)
--   Layer 3: PostgreSQL RULE (this file) — even if a privilege is misconfigured,
--             these rules prevent data modification
--
-- Note: PostgreSQL RULE is used rather than triggers for simplicity.
-- The RULE redirects UPDATE/DELETE to DO INSTEAD NOTHING — the operation is silently ignored.
-- The application layer (CE) is responsible for detecting the 0-rows-affected response.

-- ─── evidence_records: append-only ───────────────────────────────────────────

CREATE RULE no_update_evidence_records AS
    ON UPDATE TO constitutional.evidence_records
    DO INSTEAD NOTHING;

CREATE RULE no_delete_evidence_records AS
    ON DELETE TO constitutional.evidence_records
    DO INSTEAD NOTHING;

-- ─── authority_licenses: append-only ─────────────────────────────────────────

CREATE RULE no_update_authority_licenses AS
    ON UPDATE TO constitutional.authority_licenses
    DO INSTEAD NOTHING;

CREATE RULE no_delete_authority_licenses AS
    ON DELETE TO constitutional.authority_licenses
    DO INSTEAD NOTHING;

-- ─── experience_records: append-only (Professional Experience Ledger) ─────────

CREATE RULE no_update_experience_records AS
    ON UPDATE TO professional.experience_records
    DO INSTEAD NOTHING;

CREATE RULE no_delete_experience_records AS
    ON DELETE TO professional.experience_records
    DO INSTEAD NOTHING;

-- ─── Verification query (run after apply to confirm rules exist) ──────────────
-- SELECT rulename, tablename FROM pg_rules
-- WHERE tablename IN ('evidence_records', 'authority_licenses', 'experience_records')
-- ORDER BY tablename, rulename;
