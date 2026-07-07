# ADR-011: Database Schema Migration Strategy

**Status:** Accepted
**Date:** 2026-07-07
**Roles Applied:** Data Architect (schema lifecycle) + Platform Architect (deployment pipeline integration)
**Constitutional Basis:** Constitution Article II (First Law — trust earned through evidence; the Constitutional Audit Ledger is evidence and must never lose records due to schema changes); GENESIS Engineering Quality Mandate (zero manual testing — migrations must be automated and idempotent)

---

## Context

The platform has a single PostgreSQL 16 database shared by all services in each environment. The database has two distinct schema zones with different integrity requirements:

1. **Business schema** — employment contracts, professional profiles, customer organizations, billing. Normal CRUD. Schema evolves as product evolves.
2. **Constitutional Audit Ledger** — append-only immutable evidence records. A migration must never delete or modify a committed audit record. Schema evolution is strictly additive.

The question is: what tool manages migrations, when do migrations run, and who is authoritative for the schema?

## Decision

**EF Core Migrations for all schema changes. Migrations run automatically as an init container before service startup. The Constitutional Audit Ledger schema is governed by an additional migration rule: no destructive operations permitted.**

### Tool Choice: EF Core Migrations

The Business Platform (.NET) and Constitutional Engine (.NET) both use EF Core. EF Core Migrations is the natural choice — migrations are code, version-controlled, and executed via `dotnet ef database update`.

The Professional Runtime and AI Runtime (Python) do **not** own any database schema directly. They call the .NET services via gRPC to read/write data. This keeps schema ownership in one place.

### Migration Execution Pattern

```
Deployment sequence per environment:
  1. Container image promoted to environment (sha tag)
  2. Migration init container runs: dotnet ef database update --project BusinessPlatform
  3. Migration init container runs: dotnet ef database update --project ConstitutionalEngine
  4. Init containers complete successfully → services start
  5. Services start with schema already at target version

If migrations fail → deployment halts → previous version stays running
```

### Constitutional Audit Ledger Migration Rule

The `audit_ledger` table and all tables in the `constitutional` schema are governed by an additional rule enforced in code review:

> **No migration in the `constitutional` schema may contain DROP TABLE, DROP COLUMN, ALTER COLUMN (type change), TRUNCATE, or DELETE.**
> Permitted: CREATE TABLE, ADD COLUMN (nullable or with default), CREATE INDEX, ADD CONSTRAINT.

Violations are caught in Pull Request review by the Constitutional Engine owner. This rule is not currently automated — it is a reviewer obligation.

```sql
-- Example: PERMITTED migration on audit ledger
ALTER TABLE constitutional.evidence_records
  ADD COLUMN IF NOT EXISTS evidence_version integer NOT NULL DEFAULT 1;

-- Example: PROHIBITED migration on audit ledger
ALTER TABLE constitutional.evidence_records
  DROP COLUMN legacy_field;  -- REJECTED: evidence may not be destroyed
```

### pgvector

The `pgvector` extension is installed at database creation time (in Docker Compose and in the PostgreSQL Flexible Server provisioning script). It is not managed through EF Core Migrations.

## Alternatives Considered

| Option | Reason Rejected |
|---|---|
| Flyway | Excellent tool. Rejected because it requires a separate JVM process in the pipeline. EF Core Migrations is already available in the .NET build — no additional tool. |
| Liquibase | Same concern as Flyway. Also, XML/YAML migration files are harder to review than C# migration code. |
| Manual migrations | Violates GENESIS Engineering Quality Mandate (zero manual operations). One forgotten migration = data loss or startup failure in production. |
| Alembic (Python) | Python services do not own schema. No role for Alembic. |
| Schema-per-tenant (separate migrations per tenant) | Correct isolation model but 50-100x migration runtime. Preserved as upgrade path for enterprise tier (Epoch 7+). |

## Consequences

**Benefits:**
- Schema changes are code-reviewed alongside the code that uses them — no schema drift
- Rollback path: EF Core supports down migrations; for the Audit Ledger, down migrations are prohibited (append-only law)
- Zero manual database operations in any environment

**Trade-offs:**
- EF Core Migrations requires the .NET build to run before deployment — this is already the case in the CI pipeline (ADR-013)
- The Audit Ledger migration prohibition is a reviewer obligation, not automated — a future enhancement could add a CI check that scans migration files for prohibited SQL keywords

**Review trigger:**
If the Python services ever need direct database access (currently prohibited by architecture), this ADR must be revisited to add Alembic or extend EF Core access to Python via a migration-only .NET CLI tool.
