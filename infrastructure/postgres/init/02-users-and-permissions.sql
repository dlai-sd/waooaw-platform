-- 02-users-and-permissions.sql
-- Creates application database users and grants precise permissions.
-- Constitutional basis: ledger-design.md "Database User Permissions" section
-- C-027 (append-only enforcement at DB level — no UPDATE/DELETE for constitutional_app)

-- ─── Application users ──────────────────────────────────────────────────────

-- Constitutional Engine: INSERT + SELECT on constitutional only. No UPDATE/DELETE ever.
CREATE USER constitutional_app WITH PASSWORD :'POSTGRES_PASSWORD';

-- Business Platform: full CRUD on business, SELECT on constitutional (reads ledger)
CREATE USER business_app WITH PASSWORD :'POSTGRES_PASSWORD';

-- Professional Runtime + AI Runtime: SELECT on business (reads Decision Space)
CREATE USER runtime_app WITH PASSWORD :'POSTGRES_PASSWORD';

-- Temporal workflow server: own schema management
CREATE USER temporal WITH PASSWORD :'TEMPORAL_DB_PASSWORD';

-- ─── Schema ownership ────────────────────────────────────────────────────────

ALTER SCHEMA constitutional OWNER TO constitutional_app;
ALTER SCHEMA business OWNER TO business_app;
ALTER SCHEMA professional OWNER TO constitutional_app;

-- ─── Constitutional Engine permissions ──────────────────────────────────────
-- SELECT + INSERT on constitutional schema ONLY.
-- NO UPDATE. NO DELETE. This enforces C-027 at the DB permission layer.

GRANT USAGE ON SCHEMA constitutional TO constitutional_app;
GRANT SELECT, INSERT ON ALL TABLES IN SCHEMA constitutional TO constitutional_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA constitutional
  GRANT SELECT, INSERT ON TABLES TO constitutional_app;

-- Constitutional Engine can read business schema (to validate contracts, etc.)
GRANT USAGE ON SCHEMA business TO constitutional_app;
GRANT SELECT ON ALL TABLES IN SCHEMA business TO constitutional_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA business
  GRANT SELECT ON TABLES TO constitutional_app;

-- Constitutional Engine owns the professional schema
GRANT USAGE ON SCHEMA professional TO constitutional_app;
GRANT SELECT, INSERT ON ALL TABLES IN SCHEMA professional TO constitutional_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA professional
  GRANT SELECT, INSERT ON TABLES TO constitutional_app;

-- ─── Business Platform permissions ──────────────────────────────────────────
-- Full CRUD on business schema.
-- SELECT only on constitutional schema (reads evidence via CE gRPC, but can also read directly).
-- NO INSERT/UPDATE/DELETE on constitutional schema — all writes go through CE gRPC.

GRANT USAGE ON SCHEMA business TO business_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA business TO business_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA business
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO business_app;

GRANT USAGE ON SCHEMA constitutional TO business_app;
GRANT SELECT ON ALL TABLES IN SCHEMA constitutional TO business_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA constitutional
  GRANT SELECT ON TABLES TO business_app;

GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA business TO business_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA business
  GRANT USAGE, SELECT ON SEQUENCES TO business_app;

-- ─── Runtime permissions ─────────────────────────────────────────────────────
-- Professional Runtime and AI Runtime: SELECT on business (Decision Space, contracts).
-- No write access — all writes via gRPC to CE or BP.

GRANT USAGE ON SCHEMA business TO runtime_app;
GRANT SELECT ON ALL TABLES IN SCHEMA business TO runtime_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA business
  GRANT SELECT ON TABLES TO runtime_app;

-- AI Runtime reads pgvector embeddings (professional schema — Creative Standard)
GRANT USAGE ON SCHEMA professional TO runtime_app;
GRANT SELECT ON ALL TABLES IN SCHEMA professional TO runtime_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA professional
  GRANT SELECT ON TABLES TO runtime_app;

-- ─── Temporal permissions ────────────────────────────────────────────────────
-- Temporal auto-setup manages its own schema in the 'public' schema by default.
-- Grant necessary permissions for Temporal to operate.

GRANT ALL PRIVILEGES ON DATABASE waooaw TO temporal;
