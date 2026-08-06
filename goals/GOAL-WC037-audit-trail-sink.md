# GOAL-WC037 — Constitutional Audit Trail Sink (Sprint Sub-Goal under IB-024)

**Goal ID:** GOAL-WC037  
**Parent Goal:** IB-024 (Trust Layer & Open Platform Integration)  
**Sprint:** WC-037  
**Status:** G-1 REGISTERED — WC-037 AUTHORIZED by Founder 2026-08-06  
**Registrant:** Goal Orchestrator (INST-013) — 2026-08-06  
**GO Session:** 2026-08-06  
**Constitutional Basis:** C-059 (Traceability), C-078 (Personal data protection — DPDPA), C-031 (ADR-044 required — satisfied)

---

## G-1 — Goal Registration

**Goal Statement:**
> "Implement the Constitutional Audit Trail Sink — a WORM (Write Once Read Many) evidence store in the Constitutional Engine and an erasable Operational Payload Store in Business Platform — so that every agent action has a permanent, tamper-evident constitutional proof record, and WAOOAW can satisfy DPDPA Right-to-Erasure requests without destroying that proof."

**Registered:** 2026-08-06  
**Parent IB:** IB-024 (Trust Layer & Open Platform Integration) — AUTHORIZED 2026-08-06  
**Evidence record location:** `goals/GOAL-WC037-audit-trail-sink.md` (this file)

---

## G-2 — Goal Understanding Record

*Produced by: Goal Orchestrator (INST-013) — 2026-08-06*

### What This Goal Actually Means

The Audit Trail Sink is not a logging feature. It is the **constitutional proof infrastructure** for every claim WAOOAW makes about agent behaviour. Without it, every tool call, every billing decision, every employment event exists only in operational logs that can be sampled, rotated, and deleted. Constitutional claims require permanent, structural evidence.

There are two stores — they must not be confused:

**Store 1 — Immutable Audit Sink (`audit_sink` schema in CE Postgres):**
Proof that an action was authorized and executed. Contains only hashes, IDs, metadata. Zero PII. Zero content. INSERT-only Postgres Row Level Security — the application role cannot UPDATE or DELETE. Retained forever. This is what WAOOAW shows a regulator, an auditor, or a court.

**Store 2 — Erasable Payload Store (`payload_store` schema in BP Postgres):**
What the action touched — content, parameters, customer data. Tagged by `agent_instance_id`. Wiped on DPDPA Right-to-Erasure. This is what the customer owns and can delete.

The Proof/Payload decoupling resolves the DPDPA collision: erasing content does not destroy the proof that the action occurred.

### Why This Sprint Is First

CTG (WC-039) must write an evidence record after every external call. If the Audit Sink does not exist, CTG cannot write those records. WC-037 is the foundation layer — WC-038 and WC-039 cannot be constitutionally complete without it.

---

## G-3 — Goal Classification

| Dimension | Classification |
|---|---|
| Scope | Narrow — two services (CE + BP), migrations only |
| Type | Build — new Postgres schemas, gRPC RPC, one BP endpoint |
| Complexity | Medium — WORM RLS policy is non-standard; gRPC proto extension |
| Cadence | Routine — follows established CE + BP migration patterns |

**Institutions involved:** Platform IT Expert (INST-010) — sole executor  
**Reviewer:** Enterprise Architect (INST-004)

---

## G-4 — Success Criteria

- `audit_sink.evidence_records` table created with INSERT-only RLS (no UPDATE/DELETE for app role)
- `payload_store.operational_payloads` table created with erasure capability
- `RecordErasure` gRPC RPC implemented and proto updated
- CCT-AUDIT-01 passing: every `ValidateAction` (ALLOW + DENY + ESCALATE) writes exactly one evidence record; WORM verified
- CCT-DPDPA-01 passing: Right-to-Erasure wipes payloads, retains proof with erasure timestamp, response contains `proof_retained: true`
- All existing CE + BP tests passing (no regression)

---

## G-5 — Journey Status

**AUTHORIZED** — Implementation Gate cleared by Founder 2026-08-06.  
PIT Expert (INST-010) may begin WC-037 execution.
