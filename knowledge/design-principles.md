# Design Principles

**Produced by:** Chief Business Architect (Sprint 002 + v0.8.0 update)
**Date:** 2026-07-07 (updated 2026-07-08)
**Constitutional Basis:** Ratified Claims C-001 through C-039

---

## Reading this Document

Design Principles are engineering directives derived from constitutional claims. Every significant implementation decision must be evaluable against these principles.

A principle has three parts:
- **Directive** — what the engineering organization must do (or must not do)
- **Constitutional Basis** — the claim(s) from which it derives
- **Enforcement** — how compliance is verified

Principles are listed in order of constitutional priority — Constitutional Floor principles first.

---

## DP-001 — Evidence First

**Directive:** Record constitutional evidence before returning success. Never return a success response for an action that requires constitutional evidence if the evidence write has not been confirmed durable.

**Why:** Trust is earned through observable evidence (C-002, First Law). Evidence that is not recorded before the action succeeds can be lost if the system fails between action completion and evidence write. Lost evidence is a trust void — it cannot be recovered.

**Constitutional Basis:** C-002 (First Law), C-023 (Evidence First architectural implication), C-007 (ledger immutability)

**Enforcement:**
- The Constitutional Engine is called synchronously via gRPC before any approval, execution, or authority event returns success
- The calling service treats a Constitutional Engine timeout as a failure — the action did not succeed
- Constitutional Compliance Tests (CCTs) verify this in every environment before promotion
- Operational Discovery: any code path that returns success before Constitutional Engine confirmation is a constitutional violation, not a bug

---

## DP-002 — Human Override is Unconditional

**Directive:** The Emergency Stop path must never be degraded, rate-limited, queued, or made asynchronous. It is the last architectural guarantee of constitutional governance.

**Why:** Human override of any digital professional is absolute and architecturally guaranteed (C-001, Constitutional Floor). "Architecturally guaranteed" means the guarantee exists at the infrastructure layer, not the application layer.

**Constitutional Basis:** C-001 (human override absolute), C-024 (≤250ms architectural guarantee), C-019 (deterministic latency makes PAAS constitutional)

**Enforcement:**
- Emergency Stop uses a dedicated pre-warmed WebSocket connection (ADR-004, Azure SignalR)
- Emergency Stop path has no shared queue with regular API traffic
- Constitutional Compliance Tests measure Emergency Stop round-trip latency in every environment — P99 > 200ms triggers an alert before the 250ms Constitutional Floor is breached
- Any infrastructure change that would share the Emergency Stop connection with other traffic requires Founder approval

---

## DP-003 — Configuration over Code

**Directive:** Professional-type differences must be expressed through configuration and Decision Space parameters. No conditional logic of the form `if professionalType == X` may exist in the Professional Runtime.

**Why:** All three MVI professional scenarios must run on one runtime codebase with zero code changes (C-035, Runtime Universality Test). The Decision Space object is the mechanism through which all professional-type behavior is expressed (C-030).

**Constitutional Basis:** C-035 (Runtime Universality — LAW), C-030 (Decision Space as architectural primitive)

**Enforcement:**
- Runtime Universality Test is a gate: "A dental marketing professional, a beauty artist professional, and a trading professional must all execute on the same codebase with only their Decision Space configuration differing"
- Code review rejects any `professionalType` conditional in Professional Runtime or AI Runtime
- This principle does NOT prevent professional-type-specific configuration files — it prevents runtime branching

---

## DP-004 — Decision Space is the Primitive

**Directive:** Design all employment, authority, approval, and execution models around the Decision Space object as the central first-class concept. Employment is the delegation of a Decision Space. Authority is the license to occupy it. Capability is the ability to exercise judgment within it.

**Why:** ECI-001 (ratified as working assumption C-030) is the constitutional primitive from which all other models derive. Designing around a different primitive (e.g., role-based permissions, feature flags) would produce a system that cannot faithfully embody the constitutional model.

**Constitutional Basis:** C-030 (Decision Space as architectural primitive — ratified working assumption), C-014 (shadow authority is a natural behavior — implies Decision Space has observable boundaries), C-018 (PAAS is a geometric property of Decision Space)

**Enforcement:**
- The Decision Space object must be independently inspectable, versionable, and auditable in the domain model
- The Decision Space must be the configuration object customers interact with at hiring — not a derived consequence of role assignment
- Any change to a customer's Decision Space must produce a Constitutional Audit Ledger record

---

## DP-005 — Append-Only for Truth

**Directive:** Constitutional and evidence records grow forward in time, never backward. No UPDATE or DELETE operation may be applied to the Constitutional Audit Ledger or the Customer Evidence Ledger by any actor, including database administrators, under normal operations.

**Why:** No evidence in any ledger may be retroactively modified or deleted (C-007, Constitutional Floor). This protection must be enforced at the database layer, not the application layer (C-027).

**Constitutional Basis:** C-007 (ledger immutability), C-027 (append-only at database level)

**Enforcement:**
- The application service account for the Constitutional Engine has INSERT + SELECT permissions — no UPDATE or DELETE on the constitutional schema
- EF Core migrations on the constitutional schema must be reviewed against the prohibited SQL operations list (ADR-011)
- When business logic requires "correcting" a previous evidence record, the correct pattern is to append a correction record, not modify the original

---

## DP-006 — Security by Design

**Directive:** Implement Constitutional Floors at the lowest feasible architectural layer. Application-layer enforcement is always secondary to infrastructure-layer enforcement for constitutional requirements.

**Why:** Constitutional Floors cannot be disabled by configuration, commercial pressure, or application bugs (Constitution Article XI). An application-layer-only enforcement can be bypassed by a sufficiently sophisticated bug or misconfiguration. Infrastructure-layer enforcement cannot.

**Constitutional Basis:** C-001 (human override absolute), C-007 (immutability), C-004 (three systems independent — cannot be conflated at application layer), C-006 (Institutional Independence), C-009 (AD-009)

**Enforcement:**
- JWT validation in API middleware — not in individual handlers
- Row-Level Security in PostgreSQL — not only in repository queries
- Ledger immutability at database permission level — not only in EF Core model
- mTLS between services — not only application-layer authentication
- Emergency Stop on dedicated WebSocket — not HTTP polling

---

## DP-007 — Tenant Isolation by Default

**Directive:** Multi-tenant isolation must be enforced at the database layer as the primary mechanism. Application-layer isolation is a secondary defense, not the primary one. Every database query must operate within the tenant boundary established by the authenticated JWT.

**Why:** The Three-Ledger Model requires that no stakeholder may access another's ledger without explicit constitutional authorization (C-005). Application-layer-only isolation can be bypassed (C-026). The tenant_id from the JWT is the isolation anchor.

**Constitutional Basis:** C-005 (Three-Ledger Model), C-026 (database-level enforcement), C-006 (Institutional Independence)

**Enforcement:**
- PostgreSQL RLS policies on every tenant-scoped table using `SET LOCAL app.tenant_id`
- Every API request extracts tenant_id from JWT and propagates it through gRPC metadata into DB session
- Constitutional Compliance Tests include a cross-tenant isolation test: a request authenticated as Tenant A must receive a 403 or empty response for any Tenant B resource
- No shared database credentials between tenants at any layer

---

## DP-008 — Authority is Earned, Not Assumed

**Directive:** Digital professionals begin at the minimum authority level configured in the Employment Contract. Authority expands only through evidence-demonstrated competence in governed assessments. No professional begins with authority granted by capability alone.

**Why:** Authority is never granted by confidence — it is continuously licensed through constitutional evidence (C-003, Second Law). Maximum capability does not confer authority (C-004, Three Systems independent).

**Constitutional Basis:** C-003 (Second Law), C-004 (Capability ≠ Authority), C-009 (CP-001 — authority level must be visible at evaluation)

**Enforcement:**
- The Employment Contract stores the initial authority level — not derived from the professional profile
- Authority expansion requires an explicit governance event recorded in the Constitutional Audit Ledger
- The UI must display the current authority level at all times during active employment
- Authority cannot be expanded silently by the platform — it requires a customer governance action

---

## DP-009 — API First

**Directive:** Interfaces are defined and reviewed before implementations begin. The OpenAPI specification is the source of truth for external APIs. The gRPC `.proto` file is the source of truth for internal APIs. Implementations must conform to the specification — specifications are never generated from code.

**Why:** The Constitutional Chain requires that architecture precedes implementation (C-008, C-032). An API specification is architecture — defining it after implementation inverts the chain.

**Constitutional Basis:** C-008 (Constitutional Chain), C-031 (significant decisions require ADRs — API design is a significant decision), C-032 (implementation may not create architecture), ADR-002 (spec-first OpenAPI strategy)

**Enforcement:**
- Pull requests adding new endpoints must include the OpenAPI spec update first
- CI pipeline validates implementation responses against the spec (schemathesis, ADR-002)
- `.proto` files are version-controlled in `architecture/reference/proto/` (ADR-001)
- Code review rejects implementations where the spec was not written first

---

## DP-010 — Observability by Default

**Directive:** Every constitutional event must emit structured telemetry automatically as part of the event processing — not as an optional logging step added after the fact. Constitutional compliance must be measurable from observability data without additional instrumentation.

**Why:** Trust is earned through observable evidence (C-002). The platform that governs digital professionals must itself be observable. The institution cannot claim its professionals are trustworthy if the platform governing them cannot be observed.

**Constitutional Basis:** C-002 (First Law — observable evidence), ADR-009 (constitutional spans: `constitutional.evidence.recorded`, `constitutional.authority.validated`, `constitutional.emergency_stop`, `constitutional.ai.inference`)

**Enforcement:**
- Constitutional Engine emits a constitutional span for every evidence record, authority validation, authority violation, and Emergency Stop event
- PAAS latency histogram `paas.execution.latency_ms` P99 alert at 200ms (50ms before Constitutional Floor)
- OTel SDK integrated in all four services from day one — not added when needed
- Constitutional Compliance Tests validate that constitutional spans appear in traces for every governed event

---

## DP-011 — Business Outcome First in Every Interface (v0.8.0)

**Directive:** Every customer-facing interface — configuration, monitoring, reporting, billing — must present business outcomes as the primary language. Technical metrics, system identifiers, and operational state are secondary context. If a customer must think in technical terms to use WAOOAW, the interface has failed.

**Why:** GENESIS establishes that the customer hires business capability, not technology. An interface that presents `authorized_actions[0].actionType = INSTAGRAM_POST` requires the customer to think technically. An interface that says "the agent is allowed to post on Instagram" delivers the same information in business language. C-039 mandates conversational configuration precisely because form-based technical interfaces violate this principle.

**Constitutional Basis:** C-039 (conversational configuration — CONFIRMED); C-037 (business KPIs as primary performance measure — LAW); GENESIS "Business Outcome First"

**Enforcement:**
- All customer-facing API fields use business vocabulary (not enum codes) in human-readable form
- UI/UX review must validate that no customer-facing screen requires technical literacy
- Performance dashboards must lead with business KPIs; technical metrics are accessible but not primary
- Agent onboarding conversational flow is tested with actual business owners (dentist, beauty artist, trader), not engineers

---

## DP-012 — Skill Granularity in Governance (v0.8.0)

**Directive:** Every governance mechanism — Evidence First, Emergency Stop, authority licensing, billing — must operate at the Skill level, not only at the agent level. A customer who pauses a single Skill must not cause the entire agent to halt.

**Why:** C-036 establishes that Skills are independently governable constitutional units. If the governance infrastructure only operates at the agent level, C-036 is architecturally unenforceable. A dental marketing agent with four skills (Instagram, Facebook, Google Business, WhatsApp) must allow the customer to pause only Instagram without affecting the others.

**Constitutional Basis:** C-036 (Skills as independently governable units — LAW); C-038 (pro-rata billing at Skill level — LAW)

**Enforcement:**
- The `professional_skills` table has its own lifecycle state (ACTIVE, PAUSED, TERMINATED)
- Billing events are generated per-Skill, not per-agent
- Emergency Stop at agent level halts all Skills; but Skill-level pause only halts that Skill
- The capability-to-container map must show Skill-level capabilities mapped to their owning containers

---

## Design Principles Summary (v0.8.0)

| ID | Principle | Type | Constitutional Floor? |
|---|---|---|---|
| DP-001 | Evidence First | Engineering mandate | Yes — First Law |
| DP-002 | Human Override is Unconditional | Engineering mandate | Yes — Article XI |
| DP-003 | Configuration over Code | Engineering mandate | Yes — Runtime Universality |
| DP-004 | Decision Space is the Primitive | Design directive | No — working assumption |
| DP-005 | Append-Only for Truth | Engineering mandate | Yes — Article XI |
| DP-006 | Security by Design | Engineering mandate | Yes — Article XI |
| DP-007 | Tenant Isolation by Default | Engineering mandate | Yes — Article VI |
| DP-008 | Authority is Earned, Not Assumed | Design directive | No — Second Law consequence |
| DP-009 | API First | Engineering process | No — Constitutional Chain consequence |
| DP-010 | Observability by Default | Engineering mandate | No — First Law consequence |
| **DP-011** | **Business Outcome First in Every Interface** | Engineering mandate | No — GENESIS mandate |
| **DP-012** | **Skill Granularity in Governance** | Engineering mandate | Yes — C-036 LAW |
