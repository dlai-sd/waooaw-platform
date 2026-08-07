-- WC-040 / ADR-043 §2 — Skill Catalog
-- constitutional_basis: C-036 (skills are constitutional units), C-031 (ADR-043 on file)
-- Owner: business schema (Business Platform)

-- ── Table ─────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS business.skills (
    id            UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    skill_id      VARCHAR(64) NOT NULL,
    version       VARCHAR(32) NOT NULL,    -- semver e.g. "1.0.0"
    display_name  VARCHAR(128) NOT NULL,
    definition    JSONB       NOT NULL,    -- full skill YAML parsed to JSON
    cct_suite     TEXT[]      NOT NULL,    -- CCT IDs that must pass before publication
    status        VARCHAR(32) NOT NULL DEFAULT 'DRAFT', -- DRAFT | PUBLISHED | DEPRECATED
    published_at  TIMESTAMPTZ,
    deprecated_at TIMESTAMPTZ,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT skills_id_version_uq UNIQUE (skill_id, version)
);

-- ── Index: fast lookup by status for catalog list endpoint ───────────────────
CREATE INDEX IF NOT EXISTS idx_skills_status ON business.skills (status);

-- ── Index: fast lookup for pinned-version resolution (hot path at session open) ──
CREATE INDEX IF NOT EXISTS idx_skills_id_version ON business.skills (skill_id, version);

-- ── Row-level security: same tenant isolation scheme as other business tables ─
ALTER TABLE business.skills ENABLE ROW LEVEL SECURITY;

-- Catalog rows are platform-level (no tenant_id column) — all authenticated callers
-- may read PUBLISHED rows; only the platform service account may write.
CREATE POLICY skills_read_published
    ON business.skills
    FOR SELECT
    USING (status = 'PUBLISHED');

-- Service account (business_app) may insert / update — no tenant restriction on catalog
-- runtime_app (Professional Runtime + AI Runtime) may read PUBLISHED rows via RLS policy.
GRANT SELECT ON business.skills TO runtime_app;
GRANT SELECT, INSERT, UPDATE ON business.skills TO business_app;

-- ── Seed: content_publish@1.0.0 ──────────────────────────────────────────────
INSERT INTO business.skills (
    skill_id,
    version,
    display_name,
    definition,
    cct_suite,
    status,
    published_at
) VALUES (
    'content_publish',
    '1.0.0',
    'Content Publishing',
    '{
        "skill_id": "content_publish",
        "version": "1.0.0",
        "display_name": "Content Publishing",
        "description": "Publish approved content to connected social platforms on behalf of the customer.",
        "tools": ["meta.post_content", "meta.post_story", "instagram.post_reel"],
        "required_providers": ["meta"],
        "default_dcm_category": "DETERMINISTIC_REQUIRED",
        "intent_crystallizer": {
            "enabled": true,
            "prompt_template": "skills/content_publish/crystallizer_v1.md",
            "requires_customer_approval": true
        },
        "default_autonomy_level": "APPROVAL_REQUIRED",
        "cct_suite": ["CCT-SKILL-CP-01", "CCT-SKILL-CP-02", "CCT-SKILL-CP-03"],
        "billing_event": "SKILL_TOOL_CALL"
    }',
    ARRAY['CCT-SKILL-CP-01', 'CCT-SKILL-CP-02', 'CCT-SKILL-CP-03'],
    'PUBLISHED',
    now()
) ON CONFLICT (skill_id, version) DO NOTHING;
