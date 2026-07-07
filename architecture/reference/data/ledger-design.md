# Data Architecture: Three-Ledger Design

**Produced by:** Data Architect (Sprint 005)
**Date:** 2026-07-07
**Constitutional Basis:** C-005 (Three-Ledger Model), C-007 (immutability), C-026 (DB-level enforcement), C-034 (employment lifecycle), AD-003 (Audit Ledger immutability), AD-004 (multi-tenant isolation)

---

## Three Schema Zones

PostgreSQL 16 hosts three schema zones in a single database. Row-Level Security (RLS) enforces tenant isolation across all zones.

```sql
-- Three schema zones — never joined without explicit constitutional authorization
CREATE SCHEMA constitutional;  -- Constitutional Audit Ledger: APPEND-ONLY
CREATE SCHEMA business;        -- Business schema: standard CRUD
CREATE SCHEMA professional;    -- Professional Experience Ledger: owned by professional identity
```

---

## Constitutional Schema (Append-Only)

The Constitutional Audit Ledger. The application service account has INSERT + SELECT only. No UPDATE. No DELETE.

```sql
-- Constitutional Audit Ledger — immutable record of all constitutional events
CREATE TABLE constitutional.evidence_records (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL,           -- multi-tenant anchor
    contract_id     UUID NOT NULL,
    professional_id UUID NOT NULL,
    action_type     VARCHAR(100) NOT NULL,
    state           evidence_state NOT NULL,  -- see evidence_schema.md
    proposed_content JSONB,
    executed_content JSONB,
    is_scope_boundary BOOLEAN NOT NULL DEFAULT FALSE,
    scope_boundary_name VARCHAR(200),
    scope_boundary_acknowledgment TEXT,
    decision_space_version INT NOT NULL,
    constitutional_basis VARCHAR(500) NOT NULL,  -- which claim/precedent authorized this
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
    -- NO updated_at — append-only. No UPDATE permitted.
);

-- Authority License history — append-only
CREATE TABLE constitutional.authority_licenses (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL,
    contract_id     UUID NOT NULL,
    professional_id UUID NOT NULL,
    authority_level INT NOT NULL,
    granted_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    granted_by      UUID NOT NULL,           -- customer user ID
    constitutional_basis VARCHAR(500) NOT NULL,
    evidence_ids    UUID[] NOT NULL          -- evidence that justified this grant
    -- NO updated_at — append-only
);

-- Enforce append-only at DB level (belt and suspenders with app-layer enforcement)
CREATE RULE no_update_evidence AS ON UPDATE TO constitutional.evidence_records
    DO INSTEAD NOTHING;
CREATE RULE no_delete_evidence AS ON DELETE TO constitutional.evidence_records
    DO INSTEAD NOTHING;
CREATE RULE no_update_authority AS ON UPDATE TO constitutional.authority_licenses
    DO INSTEAD NOTHING;
CREATE RULE no_delete_authority AS ON DELETE TO constitutional.authority_licenses
    DO INSTEAD NOTHING;
```

---

## Business Schema (Standard CRUD)

Owned by Business Platform. Standard CRUD with RLS for tenant isolation.

```sql
-- Organisations / Customers
CREATE TABLE business.organisations (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL UNIQUE,    -- tenant_id IS the org ID in this model
    name            VARCHAR(200) NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Employment Contracts
CREATE TABLE business.employment_contracts (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL,
    professional_id UUID NOT NULL,
    state           employment_state NOT NULL,  -- EVALUATION/ACTIVE/SUSPENDED/TERMINATED
    authority_level INT NOT NULL DEFAULT 1,
    goals           JSONB NOT NULL,
    review_cadence  JSONB NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    activated_at    TIMESTAMPTZ,
    suspended_at    TIMESTAMPTZ,
    terminated_at   TIMESTAMPTZ
);

-- Decision Spaces
CREATE TABLE business.decision_spaces (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL,
    contract_id     UUID NOT NULL REFERENCES business.employment_contracts(id),
    version         INT NOT NULL DEFAULT 1,
    execution_model execution_model_type NOT NULL,  -- APPROVAL_GATE / PRE_AUTHORIZED
    professional_type VARCHAR(50) NOT NULL,
    authorized_actions JSONB NOT NULL,
    prohibited_actions JSONB NOT NULL,
    always_ask_actions JSONB NOT NULL,
    budget_constraints JSONB,
    creative_standard_profile JSONB,          -- Amendment A-005: creative professions
    paas_parameters JSONB,                    -- PAAS execution model parameters
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    is_active       BOOLEAN NOT NULL DEFAULT TRUE
);

-- Approval Requests
CREATE TABLE business.approval_requests (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL,
    contract_id     UUID NOT NULL,
    evidence_record_id UUID,                  -- set when Constitutional Engine records it
    state           approval_state NOT NULL,  -- mirrors evidence_state
    proposed_content JSONB NOT NULL,
    is_scope_boundary BOOLEAN NOT NULL DEFAULT FALSE,
    scope_boundary_name VARCHAR(200),
    customer_response VARCHAR(10),            -- APPROVED / REJECTED
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    responded_at    TIMESTAMPTZ
);
```

---

## Professional Schema (Professional Experience Ledger)

Owned by Constitutional Engine. Separate from customer data per Article VI. **Never joined with business schema without explicit constitutional authorization.**

```sql
-- Professional Identities
CREATE TABLE professional.identities (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    professional_type VARCHAR(50) NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Experience Ledger — portable, privacy-preserving, not tenant-scoped
CREATE TABLE professional.experience_records (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    professional_id UUID NOT NULL REFERENCES professional.identities(id),
    engagement_type VARCHAR(50) NOT NULL,
    industry        VARCHAR(50) NOT NULL,
    capability_demonstrated VARCHAR(200) NOT NULL,
    evidence_hash   VARCHAR(64) NOT NULL,     -- hash of evidence, not the evidence itself
    recorded_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
    -- No tenant_id — experience records are professional-owned, not tenant-owned
);
```

---

## Row-Level Security Policies

```sql
-- Enable RLS on all tenant-scoped tables
ALTER TABLE business.employment_contracts ENABLE ROW LEVEL SECURITY;
ALTER TABLE business.decision_spaces ENABLE ROW LEVEL SECURITY;
ALTER TABLE business.approval_requests ENABLE ROW LEVEL SECURITY;
ALTER TABLE constitutional.evidence_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE constitutional.authority_licenses ENABLE ROW LEVEL SECURITY;

-- Policy: tenant_id must match the session variable set from JWT
CREATE POLICY tenant_isolation ON business.employment_contracts
    USING (tenant_id = current_setting('app.tenant_id')::UUID);

CREATE POLICY tenant_isolation ON constitutional.evidence_records
    USING (tenant_id = current_setting('app.tenant_id')::UUID);

-- (Same policy applied to all other tenant-scoped tables)
```

**How the session variable is set (in every DB connection):**
```sql
-- Set at the start of every database session, sourced from JWT claim
SET LOCAL app.tenant_id = '{tenant_id_from_jwt}';
```

---

## Enums

```sql
CREATE TYPE evidence_state AS ENUM (
    'PROPOSED', 'AWAITING_APPROVAL', 'APPROVED', 'REJECTED', 'EXECUTED'
);

CREATE TYPE employment_state AS ENUM (
    'EVALUATION', 'ACTIVE', 'SUSPENDED', 'TERMINATED'
);

CREATE TYPE execution_model_type AS ENUM (
    'APPROVAL_GATE', 'PRE_AUTHORIZED'
);

CREATE TYPE approval_state AS ENUM (
    'PENDING', 'SCOPE_BOUNDARY_PENDING', 'APPROVED', 'REJECTED'
);
```

---

## Database User Permissions

```sql
-- Business Platform application user
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA business TO business_app;
GRANT SELECT ON ALL TABLES IN SCHEMA constitutional TO business_app;
-- business_app may NOT write to constitutional schema (reads only, via Constitutional Engine gRPC)

-- Constitutional Engine application user
GRANT SELECT, INSERT ON ALL TABLES IN SCHEMA constitutional TO constitutional_app;
GRANT SELECT ON ALL TABLES IN SCHEMA business TO constitutional_app;
GRANT SELECT, INSERT ON ALL TABLES IN SCHEMA professional TO constitutional_app;
-- NO UPDATE, NO DELETE on constitutional schema for ANY user

-- Professional Runtime application user
GRANT SELECT ON ALL TABLES IN SCHEMA business TO runtime_app;
-- Professional Runtime reads Decision Space; writes are via Constitutional Engine gRPC
```
