# Architectural Drivers

**Produced by:** Chief Business Architect (Sprint 002)
**Date:** 2026-07-07
**Work Contract:** WC-002
**Constitutional Basis:** Ratified Claims C-001 through C-035, GENESIS Part 01

---

## Reading this Document

Architectural Drivers are non-negotiable constraints that shape every significant engineering decision. They are not goals or aspirations — they are boundaries. An architecture that violates a driver is constitutionally non-compliant, not merely suboptimal.

Each driver states:
- **What it requires** — the measurable constraint
- **Why it exists** — the constitutional claim or GENESIS source
- **What it constrains** — the capabilities and architectural decisions it shapes
- **Hard or Soft** — Hard = constitutional floor, cannot be traded. Soft = important target, may be balanced against cost.

---

## AD-001 — Emergency Stop Latency

**Requirement:** End-to-end round-trip latency from customer-issued Emergency Stop command to confirmed halt of all active professional operations must not exceed **250ms** in Pre-Authorized Action Space (PAAS) execution contexts.

**Type:** HARD — Constitutional Floor. Cannot be traded for performance, cost, or any other consideration.

**Constitutional Basis:** C-001 (human override is absolute and architecturally guaranteed), C-024 (≤250ms architectural guarantee), C-019 (empirical: deterministic latency is what makes PAAS constitutionally valid), C-020 (absolute time guarantee required)

**Capabilities Constrained:** 2.4 (Exercise Emergency Stop), 3.2 (Execute Pre-Authorized Work)

**Architectural consequence:** Emergency Stop requires a dedicated, pre-warmed persistent connection (WebSocket). Cannot use HTTP request-response. Cannot share a connection with other traffic. The connection must be established at session start and maintained for the session duration.

---

## AD-002 — Evidence First Enforcement

**Requirement:** The Constitutional Engine must write the evidence record to the Constitutional Audit Ledger as an atomic, durable operation **before** returning a success response to any calling service. No action that requires constitutional evidence may succeed if the evidence write fails.

**Type:** HARD — Constitutional Floor derived from the First Law.

**Constitutional Basis:** C-002 (First Law — trust earned through observable evidence), C-023 (Evidence First architectural implication), C-007 (ledger immutability — evidence must persist)

**Capabilities Constrained:** 2.2 (Approve Actions), 2.3 (Confirm Scope Boundary), 3.1 (Execute Approval-Gate), 3.2 (Execute Pre-Authorized), 6.3 (Record Constitutional Evidence)

**Architectural consequence:** The Constitutional Engine must be called synchronously (not asynchronously) before any approval, execution, or authority event returns success. gRPC is the protocol (ADR-001). The calling service must treat a Constitutional Engine timeout as a failure, not a success.

---

## AD-003 — Audit Ledger Immutability

**Requirement:** No record in the Constitutional Audit Ledger may be modified or deleted after it is written. The ledger is append-only. This applies at the database layer — not merely at the application layer.

**Type:** HARD — Constitutional Floor.

**Constitutional Basis:** C-007 (no evidence deleted or modified — Constitutional Floor), C-027 (append-only at database level)

**Capabilities Constrained:** 6.3 (Record Constitutional Evidence), 2.6 (Audit Evidence Ledger)

**Architectural consequence:** The application service account for the Constitutional Engine must have INSERT and SELECT permissions on the constitutional schema — not UPDATE or DELETE. Database-level enforcement (triggers or permission restriction) is required. EF Core migrations must never include UPDATE or DELETE on the constitutional schema.

---

## AD-004 — Multi-Tenant Data Isolation

**Requirement:** No customer's data must be accessible to any other customer under any circumstances, at any layer of the platform, including the database layer.

**Type:** HARD — Constitutional Floor derived from Three-Ledger model.

**Constitutional Basis:** C-005 (Three-Ledger Model — ledgers owned by different stakeholders, never merged), C-026 (isolation enforced at database level), C-006 (Doctrine of Institutional Independence)

**Capabilities Constrained:** All capabilities in all domains. Isolation is a cross-cutting concern.

**Architectural consequence:** Row-Level Security policies on every tenant-scoped table in PostgreSQL, enforced via `SET LOCAL app.tenant_id` on every database session. `tenant_id` from JWT is the isolation anchor propagated through every layer.

---

## AD-005 — PAAS Execution Latency

**Requirement:** Total latency from PAAS execution trigger to evidence-recorded completion must support the 250ms Emergency Stop window. The PAAS execution path — including in-memory Decision Space validation — must complete in under 50ms to leave the remaining budget for network, Emergency Stop detection, and evidence recording.

**Type:** HARD — derives from AD-001.

**Constitutional Basis:** C-025 (PAAS is a first-class execution model requiring zero network calls in hot path), C-024 (≤250ms guarantee), C-018 (PAAS model required for millisecond-scale professions)

**Capabilities Constrained:** 3.2 (Execute Pre-Authorized Work)

**Architectural consequence:** PAAS execution hot path must have zero external network calls. Decision Space parameters are loaded into memory at session start. Validation is in-memory only. This is why session-affinity is required (ADR-005) — the in-memory state cannot be shared across replicas without introducing network calls.

**PAAS latency budget (approximate allocation for 250ms Constitutional Floor):**

| Segment | Budget | Notes |
|---|---|---|
| PAAS execution hot path (in-memory validation + AI inference) | <50ms | Zero network calls |
| Constitutional Engine evidence recording (gRPC + DB write) | <80ms | Synchronous, local network |
| Emergency Stop detection + SignalR routing | <50ms | Pre-warmed connection |
| Halt command processing + confirmation | <50ms | In-memory |
| Safety margin | ~20ms | |
| **Total** | **≤250ms** | **Constitutional Floor** |

Any architectural change that shifts the budget of one segment must be evaluated against this table to confirm the 250ms guarantee is still achievable.

---

## AD-006 — Cost Constraint (Non-Production Environments)

**Requirement:** Each non-production environment (dev, QA, demo, UAT) must not exceed **INR 10,000/month** in total cloud infrastructure cost.

**Type:** SOFT (for production) / HARD (for non-production per GENESIS mandate).

**Constitutional Basis:** GENESIS Part 01 — Cost Constraint ("INR 10,000/month per non-production environment is an Architectural Driver, not a guideline")

**Capabilities Constrained:** 6.1 through 6.5 (all platform operations) — this driver governs the infrastructure design for those capabilities

**Architectural consequence:** Scale-to-zero is required for all non-production services. No always-on QA infrastructure. Container Apps consumption model. Self-hosted Temporal in dev/QA (shared PostgreSQL). No API gateway at MVI. Dev/QA environments sized at minimum viable specifications.

---

## AD-007 — Runtime Universality

**Requirement:** All three Minimum Viable Institution professional scenarios (dental marketing, beauty artist, NIFTY trading) must execute on a single Professional Runtime codebase with zero runtime code changes. Professional differentiation is through Decision Space configuration only.

**Type:** HARD — GENESIS mandate, directly quoted as the Runtime Universality Test.

**Constitutional Basis:** C-035 (Runtime Universality — LAW), C-030 (Decision Space is the architectural primitive)

**Capabilities Constrained:** 1.3 (Define Decision Space), 3.1 (Execute Approval-Gate Work), 3.2 (Execute Pre-Authorized Work), 3.3 (Manage Creative Standard Profile)

**Architectural consequence:** The Professional Runtime must be completely generic. All professional-type-specific behavior — what actions are allowed, what approval flows apply, whether PAAS or approval-gate model is used — is expressed through the Decision Space configuration object, not through code. A `if professionalType == TRADING` conditional in the runtime is a constitutional violation of this driver.

---

## AD-008 — Constitutional Auditability

**Requirement:** Every permission decision, authority grant, authority restriction, scope-boundary crossing, and Emergency Stop event must produce a traceable record in the Constitutional Audit Ledger, naming the specific constitutional claim, precedent, or policy that authorized or denied the decision.

**Type:** HARD — Constitutional Floor.

**Constitutional Basis:** C-028 (Proposed state is a first-class enum), C-029 (scope-boundary confirmation is a distinct record type), Constitution Article XI ("no permission decision may be made without traceable constitutional justification")

**Capabilities Constrained:** 2.1–2.4 (all governance capabilities), 4.2–4.3 (authority expansion and restriction), 6.3 (Record Constitutional Evidence)

**Architectural consequence:** Two distinct audit record types must exist: `ActionApproval` (standard approval within scope) and `ScopeBoundaryConfirmation` (approval at or beyond scope limit, with explicit boundary name and customer acknowledgment). A single approval record type with a flag is constitutionally insufficient.

---

## AD-009 — Security by Design

**Requirement:** All Constitutional Floors — human override, evidence immutability, permission traceability, authority licensing — must be enforced architecturally, not by application-layer convention. Security controls must be implemented at the lowest feasible layer.

**Type:** HARD — Constitutional Floor.

**Constitutional Basis:** C-001, C-007, C-008, Constitution Article IX (Constitutional Floors cannot be disabled by configuration or commercial pressure)

**Capabilities Constrained:** 2.4 (Emergency Stop), 6.1 (Authenticate), 6.2 (Isolate Tenant), 6.3 (Record Evidence)

**Architectural consequence:** JWT validation enforced in API middleware — not in individual endpoint handlers. RLS at database layer — not only application layer. Ledger append-only at database permission level — not only convention. Emergency Stop on dedicated WebSocket — not HTTP polling.

---

## AD-010 — Observability by Default

**Requirement:** Every constitutional event must emit structured telemetry automatically — without requiring manual instrumentation per feature. Constitutional compliance must be measurable from observability data alone.

**Type:** SOFT — derives from the First Law (trust through observable evidence applied to the platform itself).

**Constitutional Basis:** C-002 (First Law — the platform must be as observable as the professionals it governs), ADR-009 (OpenTelemetry constitutional spans defined: `constitutional.evidence.recorded`, `constitutional.authority.validated`, `constitutional.emergency_stop`, etc.)

**Capabilities Constrained:** 6.4 (Observe Platform Health and Constitutional Compliance)

**Architectural consequence:** OTel SDK in all four services. Constitutional spans emitted automatically from the Constitutional Engine on every constitutional event. PAAS latency histogram with P99 alert threshold at 200ms (before the 250ms Constitutional Floor is breached).

---

## AD-011 — Creative Standard Integrity

**Requirement:** For creative professional engagements, the Creative Standard Profile must be enforced as a constitutional document — deviations must be flagged, modifications must follow a governed amendment process, and the calibration period must be treated as a provisionally-standard state.

**Type:** HARD — Amendment A-005.

**Constitutional Basis:** C-016 (Amendment A-005 — Creative Standard Profile is a constitutional document), C-011 (scope-boundary confirmation applies to Creative Standard deviations)

**Capabilities Constrained:** 1.5 (Onboard Professional), 3.3 (Manage Creative Standard Profile), 2.3 (Confirm Scope-Boundary Crossings)

**Architectural consequence:** The Decision Space object for creative professions must include a `CreativeStandardProfile` field treated with constitutional authority. Content proposed against a Creative Standard must be validated against it before entering the standard approval flow. Creative Standard amendments must produce `ScopeBoundaryConfirmation` audit records.

---

## Architectural Drivers Summary

| ID | Driver | Type | Primary Constraint |
|---|---|---|---|
| AD-001 | Emergency Stop Latency ≤250ms | HARD | PAAS execution, Emergency Stop capability |
| AD-002 | Evidence First Enforcement | HARD | All execution and governance capabilities |
| AD-003 | Audit Ledger Immutability | HARD | Constitutional evidence recording |
| AD-004 | Multi-Tenant Data Isolation | HARD | All capabilities (cross-cutting) |
| AD-005 | PAAS Execution Latency <50ms hot path | HARD | Pre-Authorized Work execution |
| AD-006 | Cost ≤INR 10k/month per non-prod env | HARD (non-prod) | All platform operations |
| AD-007 | Runtime Universality — one codebase | HARD | Professional execution, Decision Space |
| AD-008 | Constitutional Auditability | HARD | All governance capabilities |
| AD-009 | Security by Design | HARD | Authentication, isolation, evidence |
| AD-010 | Observability by Default | SOFT | Platform health and compliance |
| AD-011 | Creative Standard Integrity | HARD (creative prof.) | Creative professional capabilities |
