-- ============================================================
-- 10-reseller-agency.sql — White-Label + Agency Operations
-- ============================================================
-- Constitutional basis: C-075 (White-Label Reseller Model — RATIFIED),
--                       C-048 (Non-Exploitation), C-049 (Honest Limitation),
--                       C-064 (Three-Human Institution)
--
-- PURPOSE:
--   Enables an agency (like Yashus) to operate WAOOAW under their own brand
--   for their own clients. The agency is the "Reseller". Their clients are
--   "End Customers". Constitutional governance applies at both levels.
--
-- COMMERCIAL MODEL:
--   Reseller pays WAOOAW a wholesale price per active end-customer seat.
--   Reseller bills their end-customers at their own retail price (margin kept by reseller).
--   End-customers never see WAOOAW pricing — they see the reseller's pricing.
-- ============================================================

SET search_path TO business, public;

-- ─── Reseller Account Type ────────────────────────────────────────────────────
-- Extends the existing business.organisations table
-- An organisation can be: DIRECT_CUSTOMER | RESELLER | END_CUSTOMER (of a reseller)

ALTER TABLE business.organisations
    ADD COLUMN IF NOT EXISTS account_type VARCHAR(20)
        NOT NULL DEFAULT 'DIRECT_CUSTOMER'
        CHECK (account_type IN ('DIRECT_CUSTOMER', 'RESELLER', 'END_CUSTOMER')),
    ADD COLUMN IF NOT EXISTS reseller_id UUID REFERENCES business.organisations(id),
    -- NULL for DIRECT_CUSTOMER and RESELLER
    -- Foreign key to reseller organisation for END_CUSTOMER accounts

    -- White-label configuration (C-075)
    ADD COLUMN IF NOT EXISTS whitelabel_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS whitelabel_brand_name VARCHAR(100),
    -- Name shown to end-customers instead of "WAOOAW" (e.g., "Yashus AI")
    ADD COLUMN IF NOT EXISTS whitelabel_agent_prefix VARCHAR(50),
    -- Replaces "WaooaW Expert" in agent names (e.g., "Yashus Expert")
    ADD COLUMN IF NOT EXISTS whitelabel_portal_domain VARCHAR(200),
    -- Custom domain (e.g., clients.yashus.in) — Cloudflare CNAME to waooaw.ai
    ADD COLUMN IF NOT EXISTS whitelabel_logo_url VARCHAR(500),
    ADD COLUMN IF NOT EXISTS whitelabel_primary_color VARCHAR(7),  -- e.g., '#2563EB'
    ADD COLUMN IF NOT EXISTS whitelabel_email_domain VARCHAR(100),
    -- From-address domain for emails sent to end-customers
    ADD COLUMN IF NOT EXISTS whitelabel_report_footer TEXT;
    -- Custom text in report footers (e.g., "Powered by Yashus Digital Marketing")

-- ─── Reseller Profile ─────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS business.reseller_profiles (
    reseller_id         UUID PRIMARY KEY REFERENCES business.organisations(id),

    -- Commercial model
    plan_type           VARCHAR(20) NOT NULL DEFAULT 'AGENCY_STARTER'
        CHECK (plan_type IN ('AGENCY_STARTER', 'AGENCY_GROWTH', 'AGENCY_SCALE', 'ENTERPRISE')),

    -- Wholesale pricing (what reseller pays WAOOAW per end-customer seat per month)
    wholesale_price_inr DECIMAL(8,2) NOT NULL,
    -- Includes all AI inference, platform ops, storage for that end-customer
    -- Reseller charges their client whatever retail price they choose (margin is theirs)

    -- Capacity limits per plan
    max_end_customers   INTEGER NOT NULL DEFAULT 10,  -- Starter: 10, Growth: 50, Scale: 200, Enterprise: unlimited
    max_skills_per_customer INTEGER NOT NULL DEFAULT 13,  -- All skills in DMA v3.0

    -- Account Manager allocation
    max_account_managers INTEGER NOT NULL DEFAULT 2,  -- See business.agency_staff

    -- White-label enablement
    whitelabel_enabled  BOOLEAN NOT NULL DEFAULT FALSE,  -- Enabled from Growth plan upward

    -- Billing
    billing_cycle       VARCHAR(10) NOT NULL DEFAULT 'MONTHLY',
    next_billing_date   DATE,
    active_seat_count   INTEGER NOT NULL DEFAULT 0,
    -- Incremented when a new end-customer is activated; decremented when terminated

    -- Status
    status              VARCHAR(20) NOT NULL DEFAULT 'ACTIVE'
        CHECK (status IN ('ACTIVE', 'SUSPENDED', 'CHURNED')),
    onboarded_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE business.reseller_profiles IS
    'C-075: Agency reseller commercial configuration. Reseller pays wholesale price
     per end-customer seat. They bill their own clients at retail price (margin theirs).
     End-customers are isolated per reseller — they cannot see each other.';

-- ─── Plan definitions (reference table) ───────────────────────────────────────
CREATE TABLE IF NOT EXISTS business.reseller_plans (
    plan_type           VARCHAR(20) PRIMARY KEY,
    display_name        VARCHAR(100) NOT NULL,
    monthly_wholesale_inr_per_seat DECIMAL(8,2) NOT NULL,
    max_end_customers   INTEGER NOT NULL,
    whitelabel_enabled  BOOLEAN NOT NULL,
    agency_dashboard_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    multi_location_enabled BOOLEAN NOT NULL DEFAULT FALSE
);

INSERT INTO business.reseller_plans VALUES
('AGENCY_STARTER', 'Agency Starter',   1499, 10,         FALSE, TRUE, FALSE),
('AGENCY_GROWTH',  'Agency Growth',    1299, 50,         TRUE,  TRUE, TRUE),
('AGENCY_SCALE',   'Agency Scale',     1099, 200,        TRUE,  TRUE, TRUE),
('ENTERPRISE',     'Enterprise',        899, 9999,       TRUE,  TRUE, TRUE);

COMMENT ON TABLE business.reseller_plans IS
    'C-075 commercial model. Wholesale price per seat decreases at scale.
     Reseller bills their clients at retail price of their choice.
     A 25-client Growth agency paying Rs 1,299/seat × 25 = Rs 32,475/month
     billing clients at Rs 15,000/month × 25 = Rs 3,75,000/month earns
     Rs 3,42,525/month gross margin before their own overheads.';

-- ─── Agency Staff (Account Managers, not WAOOAW stewards) ────────────────────
-- Agency employees who manage end-customer relationships on behalf of the reseller.
-- They are NOT the three WAOOAW stewards (C-064). They are the reseller's operational team.
-- They operate within a constrained Decision Space: review content, approve campaigns,
-- handle escalations — but they cannot modify constitutional configuration.

CREATE TABLE IF NOT EXISTS business.agency_staff (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    reseller_id         UUID NOT NULL REFERENCES business.organisations(id),
    name                VARCHAR(100) NOT NULL,
    email               VARCHAR(200) NOT NULL,
    role                VARCHAR(30) NOT NULL
        CHECK (role IN ('ACCOUNT_MANAGER', 'SENIOR_AM', 'AGENCY_ADMIN')),

    -- Client portfolio (which end-customers this AM manages)
    assigned_customer_ids UUID[] NOT NULL DEFAULT '{}',

    -- Keycloak configuration (they get a sub-account in the reseller's Keycloak realm)
    keycloak_user_id    VARCHAR(100),

    -- Decision Space limits for this AM (within reseller's approved permissions)
    can_approve_content     BOOLEAN NOT NULL DEFAULT TRUE,
    can_approve_campaigns   BOOLEAN NOT NULL DEFAULT FALSE,  -- Senior AM and above
    can_approve_ad_spend    BOOLEAN NOT NULL DEFAULT FALSE,  -- Agency Admin only
    can_view_all_clients    BOOLEAN NOT NULL DEFAULT FALSE,  -- Agency Admin only

    status              VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_agency_staff_reseller
    ON business.agency_staff (reseller_id, status);

COMMENT ON TABLE business.agency_staff IS
    'Agency Account Managers — the reseller''s operational team.
     NOT WAOOAW stewards (C-064). They operate within the reseller''s
     approved Decision Space. They can review content and approve campaigns
     but cannot modify constitutional configuration or agent specifications.
     C-075: the reseller takes responsibility for their staff''s actions.';

-- ─── Agency-Level Reporting ────────────────────────────────────────────────────
-- Pre-computed agency dashboard aggregates — updated nightly by Platform Operations.
-- Enables the agency to see all clients in one view without N+1 queries.

CREATE TABLE IF NOT EXISTS business.agency_dashboard_snapshot (
    reseller_id         UUID NOT NULL REFERENCES business.organisations(id),
    snapshot_date       DATE NOT NULL,

    -- Portfolio-level KPIs
    total_active_clients        INTEGER NOT NULL DEFAULT 0,
    clients_at_risk             INTEGER NOT NULL DEFAULT 0,
    -- Clients with no post in 5+ days OR pending content approval > 48h

    campaigns_running           INTEGER NOT NULL DEFAULT 0,
    campaigns_pending_approval  INTEGER NOT NULL DEFAULT 0,
    content_items_due_today     INTEGER NOT NULL DEFAULT 0,
    ad_budgets_near_ceiling     INTEGER NOT NULL DEFAULT 0,
    -- Clients at > 80% of their monthly ad budget ceiling

    -- Quality signals
    clients_with_grade_a_simulation INTEGER NOT NULL DEFAULT 0,
    clients_with_grade_b_or_lower   INTEGER NOT NULL DEFAULT 0,
    -- Grade B or lower = AM should proactively review this client

    -- Revenue signals (for Yashus's own P&L tracking)
    total_active_seats          INTEGER NOT NULL DEFAULT 0,
    total_wholesale_cost_inr    DECIMAL(10,2) NOT NULL DEFAULT 0,
    -- Yashus's cost to WAOOAW this month

    computed_at                 TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    PRIMARY KEY (reseller_id, snapshot_date)
);

-- ─── Client Delivery Score (per end-customer, for AM morning review) ──────────
-- Computed nightly. Drives AM attention prioritization in agency dashboard.

CREATE TABLE IF NOT EXISTS business.client_delivery_score (
    customer_id         UUID PRIMARY KEY,
    reseller_id         UUID NOT NULL REFERENCES business.organisations(id),
    score_date          DATE NOT NULL,

    -- Component scores (0-100 each)
    content_consistency_score   DECIMAL(5,2),  -- Are posts going out on schedule?
    engagement_trend_score      DECIMAL(5,2),  -- Is engagement improving?
    campaign_performance_score  DECIMAL(5,2),  -- Are campaigns achieving target KPIs?
    response_time_score         DECIMAL(5,2),  -- Is content approved promptly? (client cooperation)
    reputation_score            DECIMAL(5,2),  -- Are reviews being managed?

    -- Composite
    overall_delivery_score      DECIMAL(5,2),
    -- < 60: RED (needs immediate AM attention)
    -- 60-79: AMBER (monitor)
    -- 80-100: GREEN (on track)

    attention_flags             VARCHAR[] NOT NULL DEFAULT '{}',
    -- e.g., ['NO_POST_5_DAYS', 'AD_BUDGET_90_PCT', 'PENDING_APPROVAL_48H', 'GRADE_B_SIMULATION']
    -- AM sees these flags as reasons to reach out to the client today

    computed_at                 TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_client_delivery_score_reseller
    ON business.client_delivery_score (reseller_id, overall_delivery_score ASC);
-- AM sorts ascending to see worst-performing clients first

COMMENT ON TABLE business.client_delivery_score IS
    'Nightly computed delivery health per end-customer. The agency dashboard
     shows this to AMs so they know which clients need attention today.
     Replaces the manual "check each client''s analytics" routine.';

-- ─── Multi-Location Support ────────────────────────────────────────────────────
-- A single end-customer organisation can have multiple physical locations
-- (e.g., Smile Dental Group with 4 clinics). Each location has its own
-- GBP, Instagram, and local content — but shares a brand identity and ad account.

CREATE TABLE IF NOT EXISTS business.customer_locations (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id         UUID NOT NULL,  -- Parent organisation
    location_name       VARCHAR(100) NOT NULL,  -- e.g., "Smile Dental — Viman Nagar"
    location_code       VARCHAR(20) NOT NULL,   -- e.g., "SDL-VN" for short references
    address             TEXT NOT NULL,
    city                VARCHAR(50) NOT NULL,
    pin_code            VARCHAR(10),

    -- Platform accounts for this specific location
    gbp_place_id        VARCHAR(200),   -- Google Business Profile Place ID
    instagram_account_id VARCHAR(100),  -- This location's Instagram Business account
    facebook_page_id    VARCHAR(100),

    -- Content strategy
    is_primary_location BOOLEAN NOT NULL DEFAULT FALSE,
    -- Primary location: brand-level content (announcements, campaigns)
    -- Non-primary: location-specific content (staff, local offers, local reviews)

    target_area_radius_km INTEGER DEFAULT 5,
    -- Hyperlocal targeting radius for paid ads (each location targets its own area)

    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_customer_locations_customer
    ON business.customer_locations (customer_id, is_active);

COMMENT ON TABLE business.customer_locations IS
    'Multi-location support for agency clients with multiple branches.
     Each location gets its own GBP, Instagram, and local content.
     All locations share the parent organisation''s brand identity and ad account.
     Agency clients with chains (dental groups, restaurant franchises) need this.';
-- Validated: WC-011 Sprint 011 (infrastructure check only)
