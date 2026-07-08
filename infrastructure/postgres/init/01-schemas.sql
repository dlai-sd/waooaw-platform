-- 01-schemas.sql
-- Creates the three constitutional schema zones.
-- Constitutional basis: C-005 (Three-Ledger separation), ADR-011 (migration strategy)
-- These schemas correspond exactly to ledger-design.md specification.
-- Executed by docker-compose postgres init BEFORE any service starts.

-- Constitutional Audit Ledger — APPEND-ONLY
CREATE SCHEMA IF NOT EXISTS constitutional;

-- Business schema — standard CRUD with RLS
CREATE SCHEMA IF NOT EXISTS business;

-- Professional Experience Ledger — professional-owned, portable
CREATE SCHEMA IF NOT EXISTS professional;

-- Institutional Learning — WAOOAW IP (FR-003, ADR-019)
-- Domain knowledge + platform intelligence derived from aggregate signals
-- NOT customer data. NOT subject to RLS. WAOOAW internal use only.
CREATE SCHEMA IF NOT EXISTS institutional;

-- Keycloak uses its own schema (configured in docker-compose KC_DB_SCHEMA)
CREATE SCHEMA IF NOT EXISTS keycloak;

-- Temporal uses default public schema (auto-setup image manages this)

COMMENT ON SCHEMA constitutional IS 'Constitutional Audit Ledger. Append-only. No UPDATE or DELETE by any user. C-005, C-007, C-027.';
COMMENT ON SCHEMA business IS 'Business data. Standard CRUD with Row-Level Security. C-005, AD-004.';
COMMENT ON SCHEMA professional IS 'Professional Experience Ledger. Professional-owned. No tenant_id. C-005.';
