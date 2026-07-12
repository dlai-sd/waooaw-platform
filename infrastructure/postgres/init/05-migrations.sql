-- ============================================================
-- 05-migrations.sql — Order-safe ALTER TABLE migrations
-- ============================================================
-- This file runs AFTER all CREATE TABLE statements in 03-enums-and-tables.sql.
-- Use this file for column additions to existing tables (ALTER TABLE ... ADD COLUMN IF NOT EXISTS).
-- Adding columns here (rather than in 03-) ensures the base table always exists first.
-- ADR-011: append-only rule — no DROP, no ALTER TYPE DROP VALUE on constitutional schema.
-- ============================================================

-- ─── v0.40.0 Simulation Gap Bridges ─────────────────────────────────────────

-- GAP-A013: Farmer price target — farmer_profiles table (created in 03-enums-and-tables.sql)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'business' AND table_name = 'farmer_profiles') THEN
        ALTER TABLE business.farmer_profiles
            ADD COLUMN IF NOT EXISTS stated_price_target_inr_per_quintal NUMERIC(8,2),
            ADD COLUMN IF NOT EXISTS price_target_updated_at TIMESTAMPTZ;
    END IF;
END $$;

-- GAP-A011: IMD warning reference — weather_alert_log (created in agricultural advisor schema)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'business' AND table_name = 'weather_alert_log') THEN
        ALTER TABLE business.weather_alert_log
            ADD COLUMN IF NOT EXISTS imd_warning_id VARCHAR(100),
            ADD COLUMN IF NOT EXISTS imd_warning_fetched_at TIMESTAMPTZ,
            ADD COLUMN IF NOT EXISTS imd_warning_confirmed BOOLEAN NOT NULL DEFAULT FALSE;
        CREATE INDEX IF NOT EXISTS idx_weather_alert_imd ON business.weather_alert_log(imd_warning_id) WHERE imd_warning_id IS NOT NULL;
    END IF;
END $$;

-- GAP-D006: SIR multi-skill evidence attribution — agent_evidence_records (institutional schema)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'institutional' AND table_name = 'agent_evidence_records') THEN
        ALTER TABLE institutional.agent_evidence_records
            ADD COLUMN IF NOT EXISTS parent_request_id UUID,
            ADD COLUMN IF NOT EXISTS sir_skill_position SMALLINT;
        CREATE INDEX IF NOT EXISTS idx_evidence_parent_request ON institutional.agent_evidence_records(parent_request_id) WHERE parent_request_id IS NOT NULL;
    END IF;
END $$;

-- Remove duplicate ALTER TABLE statements from 03-enums-and-tables.sql if they were appended
-- (those statements are now managed here; the IF NOT EXISTS guards prevent duplicate column errors)

-- ─── Future migrations go here ──────────────────────────────────────────────
-- Follow the pattern: DO $$ BEGIN IF EXISTS (...) THEN ALTER TABLE ... END IF; END $$;
-- Never DROP columns; never ALTER existing column types on constitutional schema tables.
