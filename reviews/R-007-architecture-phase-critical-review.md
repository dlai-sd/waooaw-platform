# R-007 — Critical Review of the Full Architecture Phase

**Review ID:** R-007
**Reviewer Office:** Enterprise Architect + Constitutional Analyst (joint cross-phase review)
**Subject:** Complete Architecture Phase — IB-001 through IB-008 + proto file
**Scope:** All outputs produced from Sprint 001 through Sprint 006
**Date:** 2026-07-07
**Requested by:** Founder

---

## Purpose and Standard

This is not a routine sprint review. This is a critical assessment of the full architecture phase against three standards:

1. **Correctness** — do the outputs accurately derive from the constitutional claims and accepted principles?
2. **Completeness** — are all required outputs present, or are there gaps that will block implementation?
3. **World-class delivery** — do the outputs meet the quality expected of a professionally governed institution?

A passing review confirms Gate G4 is correctly closed. A failing or partial review names what must be produced before implementation can proceed without risk.

---

## Overall Verdict: CONDITIONALLY APPROVED

The architecture phase produced foundational work of genuine quality in the constitutional governance layer, the evidence model, and the core data architecture. Several outputs are world-class by any professional standard. However, **four critical gaps exist** that were either overlooked or deferred — and at least two of them represent risks that could require architectural rework during implementation if not addressed now.

**Gate G4 status:** Closed on reasonable grounds. The gaps are real but they are additive, not structural. The core architectural decisions are sound. The gaps concern completeness of specification, not correctness of direction.

---

## Layer-by-Layer Assessment

---

### Layer 1 — Constitutional Knowledge Corpus (IB-001, 35 claims)

**Verdict: WORLD-CLASS**

35 typed, atomic, traceable claims. Every claim states: type, confidence, source documents, dependencies, contradictions, status, reviewer notes. The typing discipline (EMPIRICAL / HYPOTHESIS / CONFIRMED / LAW / ARCHITECTURAL_IMPLICATION) is rigorous. The Reviewer Notes on each claim provide institutional reasoning that a future agent can rely on without re-reading the source material.

**What is genuinely excellent:**
- C-028 (PROPOSED as first-class enum) with explicit note: "The Data Architect must include this enum in the evidence schema design. The schema must enforce valid state transitions (no jump from Proposed directly to Executed without passing through Approved)." This is architecture-ready claim authoring — not just conceptual.
- C-027 (append-only at DB level, not application level) similarly prescribes the enforcement mechanism, not just the requirement.
- The claim dependency graph (Depends On / Produces) enables downstream tracing without reading everything.
- Confidence Register and Index are present and linked.

**No gaps found at this layer.**

---

### Layer 2 — Business Capabilities, Architectural Drivers, Design Principles (IB-002/003/004)

**Verdict: STRONG — one structural observation**

The 26 capabilities are constitutionally traced, correctly modelled in verb-object format, and sufficiently specific for the Enterprise Architect to derive service boundaries. The 11 Architectural Drivers are measurable and the PAAS latency budget (AD-005) is exceptional — the explicit segment allocation table is a professional-grade deliverable.

**What is genuinely excellent:**
- AD-005 latency budget table (50ms / 80ms / 50ms / 50ms / 20ms = 250ms) gives the implementer a verifiable checklist, not just a number.
- The "HARD" vs "SOFT" classification on drivers correctly distinguishes Constitutional Floors from optimization targets.
- DP-003 (Configuration over Code) with its explicit prohibition of `if professionalType == X` branching is a world-class design principle — precise, enforceable, falsifiable.

**Observation (non-blocking):**

The Design Principles document does not include a principle for **Observability as Constitutional Evidence**. The technical observability principle (ADR-009) and the constitutional observability requirement (OTel spans for constitutional violations) are specified separately. A DP covering "constitutional observability" — that OTel spans must be emitted for every constitutional event (PAAS boundary violation, Evidence First failure, Emergency Stop) — would close the gap between the technical observability infrastructure and its constitutional purpose.

**Recommendation:** Add DP-011 — Constitutional Observability, before IB-009 begins.

---

### Layer 3 — Reference Architecture (IB-005: C4 context, containers, domain model, capability map)

**Verdict: STRONG — one architectural risk identified**

The C4 model is complete. The capability-to-container mapping is complete (all 26 capabilities, correct ownership separation). The domain model accurately derives from C-030 (Decision Space as primitive) and C-034 (employment lifecycle).

**What is genuinely excellent:**
- The explicit statement in the capability map: "Constitutional Engine is invoked by nearly every governance capability — it is the most coupled service in the platform, by constitutional design." This is intellectually honest — most architectures hide coupling; this one names it as a constitutional requirement.
- The three-schema zone design (constitutional / business / professional) maps precisely to the Three-Ledger principle (C-005). The cross-schema join prohibition is a direct architectural consequence of a LAW-type claim.

**Critical Risk — GAP-003: Emergency Stop fan-out at scale (HIGH SEVERITY)**

The Reference Architecture correctly routes the Emergency Stop WebSocket through Professional Runtime. ADR-005 correctly requires session affinity for PAAS sessions. However, `TriggerEmergencyStop` arrives at the Constitutional Engine from Business Platform, not at the Professional Runtime replica.

At scale with multiple Professional Runtime replicas:

```
Customer issues Emergency Stop
  → WebSocket → Professional Runtime Replica-7 (this replica owns the session)
  → Professional Runtime Replica-7 → Constitutional Engine: TriggerEmergencyStop

BUT ALSO:
  → Business Platform → Constitutional Engine: TriggerEmergencyStop
     (the customer may trigger via the web app, not just the WebSocket)
```

If the Emergency Stop arrives at Constitutional Engine, how does CE signal Replica-7 specifically? The `EmergencyStopResponse` returns `affected_sessions`, but how does CE know which replica owns session S?

**This is not specified anywhere in the architecture.** Options:
- Temporal signal: CE sends a signal to the PAAS Temporal workflow (preferred — Temporal workflow is replica-independent)
- Redis pub/sub: CE publishes stop event; all replicas subscribe (adds infrastructure)
- Direct HTTP: CE maintains a registry of which replica owns which session (tight coupling, fragile)

The Temporal signal is architecturally cleanest and is consistent with the Temporal adoption (ADR-015). But this option requires the PAAS session to be modelled as a Temporal workflow — which is not currently stated in the component specifications.

**Required action before Gate G5:** The Enterprise Architect or Solution Architect must specify how TriggerEmergencyStop reaches the specific Professional Runtime replica handling the session. This is a safety-critical architectural gap.

---

### Layer 4 — Component Specifications (IB-006: 4 service specs)

**Verdict: SOLID — two gaps require resolution before Gate G5**

The component specifications are detailed enough for the Runtime Professional to implement without inventing business logic. The separation of responsibilities is clean: Business Platform governs (manages state machines), Constitutional Engine records (append-only), Professional Runtime executes (the only code that calls AI), AI Runtime generates (no authority).

**What is genuinely excellent:**
- The explicit "What X does NOT do" sections in every component spec. This is the most valuable part of each spec — it prevents the Runtime Professional from incorrectly expanding a service's responsibility.
- The PAAS Engine specification correctly describes both the happy path and the Decision Space version change detection (halt and restart when version mismatch detected).

**Critical Gap — GAP-001: Missing technology stack ADRs (HIGH SEVERITY)**

The component specs reference: .NET 9, ASP.NET Core, Entity Framework Core 9, Temporal .NET SDK, Python 3.12, FastAPI, Temporal Python SDK. None of these have ADRs. The Enterprise Architect Quality Gate requires: "Every technology selection must have an ADR." The ORGANIZATION.md Office 04 Constitutional Obligations state: "May not select implementation details or implementation frameworks without ADRs."

This is a constitutional violation in the architecture deliverables. The implementation was authorized at Gate G5, but the Runtime Professional has no ADR to cite when choosing which Python web framework version to pin, or why .NET 9 over Java for the Constitutional Engine.

**Missing ADRs required before IB-009:**
- ADR-016: Service language selection — .NET 9 (CE + BP) vs Python 3.12 (PR + AI Runtime): alternatives considered, WAOOAW-specific reasons
- ADR-017: Web application framework — Next.js / TypeScript PWA for Phase 1: alternatives (React SPA, SvelteKit, etc.), mobile strategy reasoning

**Critical Gap — GAP-002: OpenAPI specifications not produced (HIGH SEVERITY)**

ADR-002 is titled "OpenAPI Specification Strategy — Spec-First" and is ACCEPTED. It states: "OpenAPI specs live in `architecture/reference/api-specs/`." That directory does NOT exist. The Solution Architect's outputs include "API contracts (OpenAPI or equivalent)."

The Runtime Professional cannot implement Business Platform's REST API without an approved OpenAPI spec. Without it, the spec-first principle (ADR-002) is violated from the first line of implementation code.

**Required before Gate G5:**
- `architecture/reference/api-specs/business-platform.openapi.yaml`
- `architecture/reference/api-specs/professional-runtime.openapi.yaml` (at minimum the Emergency Stop WebSocket spec)

---

### Layer 5 — Data Architecture (IB-007: ledger-design.md + evidence-schema.md)

**Verdict: WORLD-CLASS for what was specified — one data architecture gap remains**

The three-schema zone design, append-only enforcement at DB level (PostgreSQL RULE + permission restriction), Row-Level Security implementation pattern, and the evidence state machine (including the ABANDONED state and action_instance_id) are all genuinely excellent. The decision to enforce append-only at BOTH the application layer (no UPDATE call) AND the DB layer (PostgreSQL RULE) is belt-and-suspenders engineering applied to a constitutional floor — exactly right.

The `action_instance_id` identification (it was missing from ledger-design.md and specified in evidence-schema.md) demonstrates exactly the kind of gap-finding that a critical architecture review should produce.

**Gap — GAP-004: PAAS session state persistence not designed (MEDIUM SEVERITY)**

The data architecture does not define a PAAS session tracking table. Professional Runtime tracks active PAAS sessions in memory. If the replica crashes:
- The customer's active trading session is lost
- ADR-005 says "the new replica reloads Decision Space on the first post-failure request" — but when does this happen? What signals the reload?
- Is there a constitutional evidence record for "PAAS session interrupted by replica failure"? There should be.

A `business.paas_sessions` table (or equivalent) is needed with at minimum: session_id, contract_id, replica_id, started_at, ended_at, termination_reason (NORMAL / EMERGENCY_STOP / REPLICA_FAILURE). This enables:
1. The new replica to find interrupted sessions on startup
2. The Constitutional Audit Ledger to have a matching session record for every execution record
3. The customer's evidence dashboard to show "trading session interrupted" events

**Gap — GAP-005: Creative Standard Profile embeddings table not designed (MEDIUM SEVERITY)**

AI Runtime component spec states: "PostgreSQL (pgvector — Creative Standard Profile embeddings, read only)." The data architecture does not specify this table. Which schema does it live in? (Not constitutional — it's not a governance event. Business? Professional? New `ai` schema?) What is the table structure? Who writes to it? (Professional Runtime, when the customer updates their Creative Standard Profile.)

This gap means the AI Architect sprint has not been executed — no AI architecture document was produced. The AI Runtime component spec covers the surface but not the depth of the AI layer design.

---

### Layer 6 — Infrastructure (IB-008: docker-compose.yml + .env.example)

**Verdict: CORRECT — operational gap noted**

The docker-compose.yml correctly models all 10 containers, uses ADR-ratified versions, implements correct startup ordering with healthchecks. The observability configuration (Jaeger OTel) is consistent with ADR-009.

The three IB-009 notes from R-006 (Temporal DB user, web healthcheck, AI pgvector access) are correctly scoped to implementation.

---

### Layer 7 — Proto Contract (CA-R004-01: constitutional_service.proto)

**Verdict: WORLD-CLASS**

The proto contract is complete, precise, and well-documented. The field-level comments explain the constitutional basis for each field. The tenant-ID-via-metadata pattern (not in the request body) is architecturally correct and prevents tenant ID spoofing at the application layer. The latency budget targets in the file header are directly linked to AD-001 and AD-005.

Particularly excellent: the EvidenceState enum comment — "each state is a new INSERT; transitions do not UPDATE existing records (C-027)" — makes the append-only constraint explicit at the API contract level, preventing a Runtime Professional from implementing a state UPDATE pattern even if they overlooked the data architecture doc.

---

### Layer 8 — Missing Architecture Sprints

**Verdict: TWO SIGNIFICANT GAPS**

**GAP-006a: Security Architecture sprint not executed (HIGH SEVERITY)**

No security architecture document exists. The Security Architect office (Office 07) has a full charter and the backlog includes no IB item for it. Yet:
- There is no threat model
- The network topology is unspecified (which components are in which subnet, which NSGs apply)
- The Constitutional Engine is "INTERNAL ONLY" — but how is this enforced at the network layer, not just the application layer? (ADR-007 covers mTLS; but mTLS is not a substitute for network segmentation)
- There is no specification for how Azure Key Vault references are injected into Container Apps at runtime
- JWT signature verification is mentioned but not specified (which algorithm, key rotation policy)
- The PAAS execution path has a latency constraint (AD-005); a security control that adds latency to this path is a constitutional concern — no security architect has evaluated this

The Security Architect office should execute a sprint (IB-010 or as a sub-task of IB-009) covering: threat model, network segmentation, Key Vault injection pattern, JWT validation specification, TLS configuration, and constitutional-security interaction (security controls must not degrade Emergency Stop latency).

**GAP-006b: AI Architecture sprint not executed (MEDIUM SEVERITY)**

No AI architecture document exists. The AI Architect office (Office 08) has a charter. The AI Runtime component spec covers the surface: LLM gateway, tool registry, creative standard enforcer, decision space reasoner. But the AI architecture document should specify:
- LLM provider failover strategy (what happens if Azure OpenAI is unavailable?)
- Decision Space reasoner for the UNCERTAIN case — when ValidateAction returns ESCALATE on a PAAS action, what happens in the sub-50ms budget?
- Prompt architecture specification (the constitutional prompt injection is described but not formally specified)
- Token budget management (LLM calls have context length limits; long Decision Spaces may exceed them)
- Rate limiting at the LLM gateway layer

---

## Summary of Gaps

| ID | Severity | Gap | Required before |
|---|---|---|---|
| GAP-001 | HIGH | Missing technology stack ADRs (language + framework selection) | Gate G5 |
| GAP-002 | HIGH | OpenAPI specifications not produced (`architecture/reference/api-specs/`) | Gate G5 |
| GAP-003 | HIGH | Emergency Stop fan-out at scale not specified (how does CE signal correct PR replica?) | Gate G5 |
| GAP-004 | MEDIUM | PAAS session state persistence not designed (no `paas_sessions` table) | Gate G5 |
| GAP-005 | MEDIUM | Creative Standard Profile embeddings table not specified | Gate G5 |
| GAP-006a | HIGH | Security Architecture sprint not executed (no threat model, no network topology) | Gate G5 |
| GAP-006b | MEDIUM | AI Architecture sprint not executed (no LLM failover, no UNCERTAIN path, no token budget) | Before Production |
| GAP-007 | MEDIUM | Billing (capability 6.5) not designed at component or data level | Before Production |
| GAP-008 | LOW | Temporal dynamic config not specified | IB-009 |
| DP-011 | LOW | No "Constitutional Observability" design principle | Before IB-009 |

---

## What Is World-Class — What Is Not

### Genuinely World-Class (keep exactly as-is)

- **Evidence state machine** — PROPOSED through ABANDONED, append-only transitions, action_instance_id, PAAS vs Approval-Gate variants, Emergency Stop two-record pattern. This is precise, falsifiable, and directly constitutionally traceable.
- **PAAS latency budget** — the explicit segment allocation table (AD-005) is professional-grade systems architecture.
- **Constitutional traceability on every decision** — every capability, driver, ADR, and component spec cites the specific claim or article that demands it. This is the institution's deepest differentiator.
- **Three-ledger separation at DB level** — append-only enforcement via PostgreSQL RULE + permission restriction is belt-and-suspenders on a Constitutional Floor. Correct.
- **Decision Space as primitive** — the architectural consistency of this concept across the domain model, the proto contract, the component specs, and the design principles is intellectually rigorous.
- **BOOTSTRAP protocol** — deterministic, reproducible agent onboarding with mandatory checkpoints is a genuine institutional innovation.
- **Two-agent review policy** — the pattern of having AI agents review each other's work (rather than self-approving) is the right governance model.
- **Proto contract quality** — field-level constitutional comments, latency targets in the header, tenant ID via metadata. This is not a typical proto file.

### Not Yet World-Class (gaps to close)

- **Technology selection without ADRs** — any architect who cannot answer "why .NET for Constitutional Engine and not Java?" with a reference document is producing incomplete work.
- **Spec-first without specs** — ADR-002 ratified the principle but the specs don't exist. Principle without artifact is aspirational, not architectural.
- **Emergency Stop fan-out** — the most safety-critical path in the system is partially unspecified. This is the highest-risk gap.
- **No Security Architecture** — an institution that governs autonomous digital professionals with access to trading accounts and social media has serious attack surface. No threat model is not world-class.

---

## Verdict

| Dimension | Score | Notes |
|---|---|---|
| Constitutional Correctness | 9/10 | Near-perfect traceability. One OD-003 scope question open. |
| Constitutional Completeness | 7/10 | Security + AI architecture sprints missing. |
| Structural Architecture | 8/10 | Solid foundations. Emergency Stop fan-out gap is the weakest point. |
| Data Architecture | 9/10 | World-class evidence model. PAAS session table + pgvector gap. |
| API Contract | 8/10 | Proto is excellent. OpenAPI specs missing entirely. |
| Infrastructure | 8/10 | Correct and reviewable. Minor IB-009 notes. |
| ADR Coverage | 6/10 | Protocol/pattern ADRs excellent. No technology stack ADRs. |
| Overall | **7.9/10** | Strong foundation. Critical gaps must close before implementation. |

**Gate G4 was correctly closed** for the work that exists. The architecture is sound where it has been done. The four HIGH-severity gaps are additive — they do not invalidate what has been produced, but they represent work that must be completed to reach genuine world-class delivery at Gate G5.

---

## Required Actions Before IB-009 Begins

These are not suggestions. They are constitutional requirements.

| # | Action | Office | Priority |
|---|---|---|---|
| 1 | Produce ADR-016 (language selection: .NET 9 / Python 3.12) | Enterprise Architect | P0 |
| 2 | Produce ADR-017 (web framework: Next.js / TypeScript) | Enterprise Architect | P0 |
| 3 | Produce `architecture/reference/api-specs/business-platform.openapi.yaml` | Solution Architect | P0 |
| 4 | Produce `architecture/reference/api-specs/professional-runtime.openapi.yaml` | Solution Architect | P0 |
| 5 | Specify Emergency Stop fan-out mechanism (Temporal signal recommendation) | Enterprise Architect | P0 |
| 6 | Execute Security Architecture sprint — threat model, network topology, JWT spec | Security Architect | P0 |
| 7 | Add `paas_sessions` table specification to data architecture | Data Architect | P1 |
| 8 | Specify pgvector embeddings table for Creative Standard Profiles | AI Architect or Data Architect | P1 |
| 9 | Add DP-011 (Constitutional Observability) to Design Principles | Business Architect | P1 |

**Reviewer:** Enterprise Architect + Constitutional Analyst (AI agent, joint review)
**Date:** 2026-07-07
**Review closed.**
