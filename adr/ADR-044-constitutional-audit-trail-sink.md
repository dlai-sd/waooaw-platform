# ADR-044 — Constitutional Audit Trail Sink

**Status:** Accepted  
**Date:** 2026-08-06  
**Authority:** C-031 (No significant architectural decision without an ADR — LAW); C-059 (Traceability Requirements)  
**Deciders:** Yogesh Khandge (Founder), Enterprise Architect (INST-004)  
**Extends:** ADR-009 (OpenTelemetry Observability — covers metrics/traces/logs, NOT constitutional evidence)  
**Required by:** ADR-042 (CTG writes evidence records to Audit Sink after every external call)

---

## Context

WAOOAW's constitutional claims require that every agent action has an immutable evidence record — who authorized it, under what authority, at what time, with what outcome. C-059 (Traceability Requirements) states this explicitly.

The Constitutional Engine already records `EvidenceRecord` rows in its Postgres instance (one record per `ValidateAction` call). Two unresolved problems make this insufficient for production:

**Problem 1 — Evidence records contain operational payload.** The current `EvidenceRecord` schema in CE stores `action_type`, `tool_name`, and `context_json` which may contain customer data, content previews, or campaign parameters. Under India's DPDPA (Digital Personal Data Protection Act 2023) and GDPR, a customer's Right to Erasure requires deletion of personal data. If the evidence record contains personal data, erasing it destroys the proof that the action occurred — a constitutional audit violation.

**Problem 2 — No WORM (Write Once Read Many) guarantee.** The current CE Postgres table has standard insert/update/delete permissions. There is no structural guarantee that a database migration or admin action could not alter or delete historical evidence records. An immutable audit trail must be structurally non-deletable, not just operationally non-deleted.

**Problem 3 — ADR-009 (OTel) is not a substitute.** OpenTelemetry spans and logs are observability infrastructure — they are not constitutional evidence. OTel data may be sampled, rotated, compressed, or dropped under load. Constitutional evidence must be every action, durably, always. These are different concerns.

The Founder strategy session on 2026-08-06 identified the Proof/Payload decoupling pattern as the constitutional resolution: **the audit record is proof that an action occurred; the operational data is the payload of that action.** These must live in separate stores with different retention policies.

---

## Constitutional Basis

| Claim | Application |
|---|---|
| **C-031** | This ADR records the Audit Sink architecture decision |
| **C-059** | Traceability — every consequential action must have a traceable, verifiable, immutable evidence record |
| **C-041** | Tool authorization — every CTG call that results in an external API call must leave an audit record |
| **C-078** | Personal data protection — customer PII must be erasable; evidence of actions must be preserved |
| **ADR-009** | OTel is observability, not evidence — this ADR is explicitly distinct and non-overlapping |
| **ADR-042** | CTG writes evidence records to the Audit Sink after every external call |

---

## Decision

### 1. Proof / Payload Decoupling

Constitutional evidence is split into two stores with different retention semantics:

```
IMMUTABLE AUDIT SINK (Proof)                OPERATIONAL PAYLOAD STORE (Data)
─────────────────────────────────────────   ──────────────────────────────────────
Zero PII. Zero raw content.                 Raw content, customer PII, campaign text,
Cryptographic hash of payload only.         images, structured parameters.
WORM — rows may never be updated/deleted.   Tagged by tenant_id + agent_instance_id.
Proves: who authorized, what action, when.  Erasable on Right-to-Erasure request.
Retained: forever (constitutional record).  Retained: until erasure or 7-year default.
```

This separation means:
- A Right-to-Erasure request wipes the Operational Payload Store for the specified agent instance
- The Audit Sink retains the proof record with the hash and an erasure timestamp
- Platform legal statement: *"Agent X executed action Y under authority DEC-9912 at T. Content payload purged per DPDPA Order #E-102 on T+N. Hash: 0x8f3c..."*
- Constitutional audit is satisfied. DPDPA is satisfied. Neither is compromised.

### 2. Immutable Audit Sink Schema

The Audit Sink lives in the **Constitutional Engine's Postgres instance**, in a separate schema `audit_sink`. The CE already owns the authoritative evidence — placing the sink here keeps it in the same constitutional boundary.

```sql
-- Create audit_sink schema (separate from public schema)
CREATE SCHEMA audit_sink;

CREATE TABLE audit_sink.evidence_records (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  decision_id         VARCHAR(64) NOT NULL UNIQUE,   -- DEC-NNNN from CE.ValidateAction
  tenant_id           UUID NOT NULL,
  agent_id            VARCHAR(64) NOT NULL,
  agent_instance_id   VARCHAR(64) NOT NULL,          -- specific Employment Contract instance
  action_type         VARCHAR(64) NOT NULL,           -- TOOL_CALL | APPROVAL | EMERGENCY_STOP | LIFECYCLE
  tool_name           VARCHAR(128),                   -- null for non-tool actions
  args_hash           VARCHAR(128),                   -- sha256(canonical_json(args))
  payload_ref_id      UUID,                           -- FK into operational_payloads (null if no payload)
  credential_provider VARCHAR(64),                    -- "meta" | "google" | "openai" | null
  vault_alias         VARCHAR(128),                   -- "waooaw-dev-kv" | null (never full URL)
  execution_status    VARCHAR(32) NOT NULL,           -- AUTHORIZED | DENIED | SUCCESS | FAILED | ESCALATED
  constitutional_basis TEXT[],                        -- e.g. ["C-041", "C-043"]
  evidence_hash       VARCHAR(128) NOT NULL,          -- sha256 of the full record at write time
  recorded_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
  erasure_status      VARCHAR(32) DEFAULT 'NONE',     -- NONE | PAYLOAD_PURGED
  erasure_timestamp   TIMESTAMPTZ
);

-- WORM: no UPDATE or DELETE on evidence_records — enforced via Postgres row security
ALTER TABLE audit_sink.evidence_records ENABLE ROW LEVEL SECURITY;
CREATE POLICY evidence_insert_only ON audit_sink.evidence_records
  FOR INSERT TO ce_service_role
  WITH CHECK (true);
-- No UPDATE or DELETE policy = structural prohibition
```

**Fields that must never appear in `evidence_records`:**
- Token value (any fragment)
- OAuth client_secret
- Full Azure Key Vault URL
- Raw content (text, image, video)
- Customer name, phone number, email
- Campaign content or creative

### 3. Operational Payload Store Schema

The Operational Payload Store lives in the **Business Platform's Postgres instance**, in a separate schema `payload_store`. BP owns the Employment Contract and is the correct service to handle DPDPA erasure requests.

```sql
CREATE SCHEMA payload_store;

CREATE TABLE payload_store.operational_payloads (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  payload_ref_id      UUID NOT NULL UNIQUE,        -- referenced by audit_sink.evidence_records.payload_ref_id
  tenant_id           UUID NOT NULL,
  agent_instance_id   VARCHAR(64) NOT NULL,
  action_type         VARCHAR(64) NOT NULL,
  payload_json        JSONB,                       -- structured payload (content, args, results)
  payload_blob_ref    VARCHAR(512),                -- S3/Azure Blob reference for binary payloads
  pii_present         BOOLEAN NOT NULL DEFAULT false,
  created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
  erased_at           TIMESTAMPTZ                  -- set on Right-to-Erasure; payload_json → null; blob deleted
);

CREATE INDEX idx_payloads_agent_instance ON payload_store.operational_payloads (agent_instance_id);
CREATE INDEX idx_payloads_tenant ON payload_store.operational_payloads (tenant_id);
```

### 4. Right-to-Erasure Flow

```
Customer submits DPDPA erasure request (via Support or Portal)
        │
        ▼
Business Platform receives: DELETE /api/v1/customers/{tenant_id}/data
        │
        ▼
BP queries payload_store.operational_payloads
  WHERE agent_instance_id IN (select contracts for tenant)
  AND erased_at IS NULL
        │
        ▼
For each payload row:
  1. Set payload_json = NULL
  2. Delete payload_blob_ref from Azure Blob (if present)
  3. Set erased_at = now()
        │
        ▼
BP calls CE via gRPC: RecordErasure(tenant_id, erasure_order_id)
        │
        ▼
CE updates audit_sink.evidence_records
  SET erasure_status = 'PAYLOAD_PURGED', erasure_timestamp = now()
  WHERE tenant_id = $1
        │
        ▼
BP generates DPDPA compliance certificate:
  "Evidence records retained. Payloads purged per erasure order {erasure_order_id} on {timestamp}."
```

### 5. Where Evidence Records Are Written

Every following code path must write an evidence record to the Audit Sink:

| Event | Writer | Record type |
|---|---|---|
| CE.ValidateAction (any outcome) | Constitutional Engine | AUTHORIZED / DENIED / ESCALATED |
| CTG.call() success | Constitutional Tool Gateway (via CE gRPC call) | SUCCESS |
| CTG.call() failure | Constitutional Tool Gateway (via CE gRPC call) | FAILED |
| Emergency Stop signal received | Professional Runtime → CE | EMERGENCY_STOP |
| Agent lifecycle state transition | Business Platform → CE | LIFECYCLE |
| Skill added/removed (contract amendment) | Business Platform → CE | SKILL_AMENDMENT |
| Customer consent given (approval gate) | Business Platform → CE | APPROVAL |

### 6. Performance and Availability

Evidence record writes are **synchronous and blocking** on the critical path. C-059 (Traceability) takes precedence over latency optimization. If CE is unavailable:

- ADR-031 (CE Fail-Safe Unavailability) governs behaviour: agent halts, does not proceed
- An evidence record cannot be written post-hoc — if CE is unreachable, the action does not execute

Evidence record reads (for audit reports, performance reports, DPDPA queries) use **read replicas** and never block the write path.

---

## Rejected Alternatives

**A — Store evidence records in OTel / OpenTelemetry:** OTel data is sampled, rotated, and subject to infrastructure cost controls. Constitutional evidence must be every action, always, with WORM semantics. OTel is not a substitute. Rejected — ADR-009 and ADR-044 are explicitly separate concerns.

**B — Keep payload in the evidence record (current CE state):** Violates DPDPA Right-to-Erasure. Rejected — Proof/Payload decoupling is the constitutional resolution.

**C — Separate Audit Sink service with dedicated database:** The CE already owns constitutional evidence. Introducing a fifth database adds operational complexity. The `audit_sink` Postgres schema within CE's instance provides schema-level isolation with the same constitutional boundary ownership. Rejected.

**D — Async evidence writes (fire-and-forget for performance):** Creates a window where an action executes before its evidence record is written. If the system crashes in that window, the action is unaudited. C-059 compliance requires synchronous writes. Rejected.

---

## Implementation Prerequisites

Before any WC opens for Audit Sink implementation:
1. ✅ ADR-044 merged (this document)
2. ✅ ADR-042 merged (CTG needs Audit Sink to write evidence records)
3. ⏳ CE Postgres migration adds `audit_sink` schema and WORM policy
4. ⏳ BP Postgres migration adds `payload_store` schema
5. ⏳ CE gRPC proto extended with `RecordErasure` RPC
6. ⏳ CCT-DPDPA-01: Right-to-Erasure wipes payloads; evidence records retained with erasure timestamp
7. ⏳ CCT-AUDIT-01: Every CTG call leaves an evidence record (verified in integration test)
