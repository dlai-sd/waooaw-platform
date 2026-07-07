#!/bin/bash
# 02-users-and-permissions.sh
# Creates application database users and grants precise permissions.
# Constitutional basis: ledger-design.md "Database User Permissions" section
# C-027 (append-only enforcement — constitutional_app has NO UPDATE/DELETE ever)
#
# Run by the PostgreSQL docker-entrypoint as a bash script.
# Environment variables POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB are
# automatically available from docker-compose environment section.
# TEMPORAL_DB_PASSWORD defaults to POSTGRES_PASSWORD in dev if not set.

set -e

TEMPORAL_PASS="${TEMPORAL_DB_PASSWORD:-${POSTGRES_PASSWORD}}"

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL

-- ─── Application users ──────────────────────────────────────────────────────

-- Constitutional Engine: INSERT + SELECT on constitutional only. No UPDATE/DELETE.
CREATE USER constitutional_app WITH PASSWORD '${POSTGRES_PASSWORD}';

-- Business Platform: full CRUD on business, SELECT on constitutional
CREATE USER business_app WITH PASSWORD '${POSTGRES_PASSWORD}';

-- Professional Runtime + AI Runtime: SELECT on business
CREATE USER runtime_app WITH PASSWORD '${POSTGRES_PASSWORD}';

-- Temporal workflow server
CREATE USER temporal WITH PASSWORD '${TEMPORAL_PASS}';

-- ─── Schema ownership ────────────────────────────────────────────────────────

ALTER SCHEMA constitutional OWNER TO constitutional_app;
ALTER SCHEMA business OWNER TO business_app;
ALTER SCHEMA professional OWNER TO constitutional_app;

-- ─── Constitutional Engine permissions ──────────────────────────────────────
-- SELECT + INSERT on constitutional ONLY. No UPDATE. No DELETE. C-027.

GRANT USAGE ON SCHEMA constitutional TO constitutional_app;
GRANT SELECT, INSERT ON ALL TABLES IN SCHEMA constitutional TO constitutional_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA constitutional
  GRANT SELECT, INSERT ON TABLES TO constitutional_app;

GRANT USAGE ON SCHEMA business TO constitutional_app;
GRANT SELECT ON ALL TABLES IN SCHEMA business TO constitutional_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA business
  GRANT SELECT ON TABLES TO constitutional_app;

GRANT USAGE ON SCHEMA professional TO constitutional_app;
GRANT SELECT, INSERT ON ALL TABLES IN SCHEMA professional TO constitutional_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA professional
  GRANT SELECT, INSERT ON TABLES TO constitutional_app;

-- ─── Business Platform permissions ──────────────────────────────────────────

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

GRANT USAGE ON SCHEMA business TO runtime_app;
GRANT SELECT ON ALL TABLES IN SCHEMA business TO runtime_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA business
  GRANT SELECT ON TABLES TO runtime_app;

GRANT USAGE ON SCHEMA professional TO runtime_app;
GRANT SELECT ON ALL TABLES IN SCHEMA professional TO runtime_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA professional
  GRANT SELECT ON TABLES TO runtime_app;

-- ─── Temporal permissions ────────────────────────────────────────────────────

GRANT ALL PRIVILEGES ON DATABASE $POSTGRES_DB TO temporal;

EOSQL
