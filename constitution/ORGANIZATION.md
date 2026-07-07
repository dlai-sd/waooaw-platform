# ORGANIZATION.md — Constitutional Organization of WAOOAW

**Authority:** Derived from constitution/CONSTITUTION.md and constitution/GENESIS.md

**Status:** Ratified — Gate G1 Complete

**Date:** 2026-07-06

**Classification:** Governing — no implementation artifact may exist without an office that authorized it

---

## Naming Note

This document uses the canonical office names for WAOOAW's engineering organization. The Development Roadmap v1.0 uses equivalent names in some places:

| ORGANIZATION.md | Roadmap Equivalent |
|---|---|
| Platform Architect | Chief Cloud Architect / Chief Platform Architect |
| Runtime Implementation Professional | Chief Runtime Engineer / Implementation Professional |
| Constitutional Analyst | Chief Constitutional Analyst |

The names in this document are authoritative. The roadmap names are descriptive shorthand.

---

## Purpose

This document defines the constitutional organization of WAOOAW.

It governs who may decide what, in what sequence, and subject to whose review.

No office may act outside its licensed Decision Space.

No office may receive inputs that have not been approved by the upstream office.

No implementation artifact may exist without traceability to an office that produced or authorized it.

**This is not an org chart. It is a governance contract.**

---

## The Governing Sequence

Work flows in a strict linear dependency. No office may begin without approved outputs from the office above it.

```
Founder / Constitutional Steward
            │
    Constitutional Office
       Constitutional Analyst
       Constitutional Steward
       Appeals Officer
            │
      Business Office
       Chief Business Architect
            │
      Delivery Office
       Product Owner           ← activated at sprint start only
       [produces Sprint Plan → Founder approves → Mode 2 activates]
            │
      Engineering Office
       Enterprise Architect
       Solution Architect
       Data Architect
       AI Architect
       Security Architect
       Platform Architect
       Runtime Implementation Professional
            │
     Operations Office
     Commercial Office
     Customer Office
```

---

## Constitutional Obligation: The Seventh Attribute

Every office charter contains seven attributes:

1. **Mission** — Why the office exists
2. **Decision Space** — What it is licensed to decide
3. **Inputs** — What it may consume (only from approved upstream outputs)
4. **Outputs** — What it must produce before the next office may begin
5. **Quality Gate** — The standard that outputs must meet
6. **Reviewer** — Who approves the outputs
7. **Constitutional Obligations** — What this office is **forbidden** to do, and the constitutional source of that prohibition

The Constitutional Obligation is the most important attribute. It is traceable to a specific article in the Constitution, a ratified precedent, or a Genesis principle.

An obligation without a constitutional source can be argued away. An obligation with one cannot.

---

## Office Charters

---

### Office 01 — Founder / Constitutional Steward

**Mission**

Protect the constitutional integrity of the institution. Deliberate constitutional discoveries. Ratify precedents and amendments. Approve new Genesis versions. Govern the organization without managing it.

**Decision Space**

Constitutional authority: vision, mission, amendment ratification, Founder Resolutions, constitutional escalations.

**Inputs**

Constitutional Discoveries, Red Team findings, Appeals, Constitutional Analyst recommendations.

**Outputs**

Ratified Precedents (CP), Constitutional Amendments, Founder Resolutions (FR), Genesis versions.

**Quality Gate**

Every output must cite the constitutional basis for the decision. No output may contradict a prior ratified precedent without a formal amendment process.

**Reviewer**

None. The Founder is the highest constitutional authority. Subject only to the amendment process defined in Amendment A-001.

**Constitutional Obligations**

- May not implement software. *(GENESIS Part 03 — Institution Before Implementation)*
- May not design architecture. *(GENESIS Part 03 — Architect before Engineer)*
- May not select technology. *(Engineering First Law — technology decisions require ADRs)*
- May not rewrite historical evidence. *(Constitution Article VII — Founder Duty)*
- May not ratify amendments without citing a Constitutional Discovery, Precedent, Audit finding, or Production Incident. *(Constitution Amendment A-001)*

---

### Office 02 — Constitutional Analyst (under Constitutional Office)

**Mission**

Curate institutional truth. Process the constitutional corpus — cases, discoveries, precedents, founder resolutions — and produce typed, atomic, traceable claims that the entire organization consumes. Serve the institution, not any single office.

**Decision Space**

Institutional knowledge: claim production, confidence assessment, relationship mapping, contradiction detection, graduation recommendations.

**Inputs**

Constitutional Discovery Cases, Constitutional Discoveries (CD), Constitutional Precedents (CP), Founder Resolutions (FR), Red Team findings, Emerging Constitutional Interpretations (ECI).

**Outputs**

Atomic Claims with type, confidence, evidence, dependencies, and contradictions. Confidence Register. Claim Relationship Graph.

**Claim Types Produced**

- `EMPIRICAL` — what happened in a case, neutral, no inference
- `HYPOTHESIS` — interpretation explaining observations, testable (ECIs)
- `CONFIRMED` — survived adversarial testing, ratified (CPs)
- `LAW` — foundational, derivable from first principles (constitutional laws)
- `ARCHITECTURAL_IMPLICATION` — what must be true about software given a confirmed claim

**Quality Gate**

Every claim must state: type, confidence percentage, supporting cases, contradicting claims (if any), constitutional source.

No architectural implication may be stated before its parent claim is at minimum CONFIRMED status.

**Reviewer**

Founder.

**Constitutional Obligations**

- May not produce architectural recommendations. *(GENESIS — Architecture derives from knowledge, not the reverse)*
- May not design business capabilities. *(Business Architect's Decision Space)*
- May not select technology. *(Engineering's Decision Space)*
- May not produce CONFIRMED claims without adversarial testing evidence. *(Constitution Article II — First Law: trust earned through evidence)*
- Must serve all offices equally. May not give any single office privileged access to institutional knowledge. *(Constitution Article VII — Doctrine of Institutional Independence)*

---

#### Constitutional Analyst — Operating Procedure

**Input Sources (in processing order)**

1. `constitution/CONSTITUTION.md` — extract constitutional laws, articles, amendments, and floors as LAW-type claims
2. `constitution/GENESIS.md` — extract founder resolutions, engineering principles, and epoch definitions as LAW or CONFIRMED claims
3. `simulation/PRECEDENTS.md` — elevate ratified CPs to CONFIRMED claims; leave CDs as HYPOTHESIS
4. `simulation/*.md` (all cases) — extract empirical observations as EMPIRICAL claims; extract case-level interpretations as HYPOTHESIS
5. `constitution/RED_TEAM.md` — extract audit findings as EMPIRICAL claims; extract unresolved vulnerabilities as HYPOTHESIS

**Output Format — Atomic Claim**

Every claim produced must conform to the following structure:

```
Claim ID:        C-XXX
Type:            EMPIRICAL | HYPOTHESIS | CONFIRMED | LAW | ARCHITECTURAL_IMPLICATION
Statement:       One precise, falsifiable sentence
Confidence:      0-100%
Source:          [list of source documents and specific sections]
Depends On:      [list of Claim IDs this claim requires to be true]
Produces:        [list of Claim IDs that depend on this claim]
Contradicted By: [list of Claim IDs that conflict, if any]
Status:          DRAFT | UNDER_REVIEW | RATIFIED | SUPERSEDED
Reviewer Notes:  [Founder deliberation notes]
```

**Claim Types — Evidence Requirements**

| Type | Required Evidence Before Ratification |
|---|---|
| `EMPIRICAL` | Direct observation from a case; no inference |
| `HYPOTHESIS` | Explanation of observations; must be testable |
| `CONFIRMED` | Survived adversarial testing across ≥2 independent cases |
| `LAW` | Derivable from constitutional first principles; ratified by Founder |
| `ARCHITECTURAL_IMPLICATION` | Parent claim must be CONFIRMED or LAW |

**Review Cycle**

1. Constitutional Analyst produces DRAFT claims from input sources
2. DRAFT claims submitted to Founder for deliberation
3. Founder may: Ratify → RATIFIED, Request revision → back to DRAFT, Reject → SUPERSEDED
4. Only RATIFIED claims may be consumed by downstream offices

**Claim Storage**

Claims live in `knowledge/claims/` — one file per claim, named `C-XXX.md`
The Confidence Register lives in `knowledge/confidence-register.md`
The Claim Index lives in `knowledge/index.md`

---

### Office 03 — Chief Business Architect (under Business Office)

**Mission**

Define what WAOOAW must be capable of doing — from a business perspective — derived from constitutional claims and the founding vision. Define the Architectural Drivers that constrain all engineering decisions.

**Decision Space**

Business Capability Map, Architectural Drivers (formerly NFR), Design Principles.

**Inputs**

Ratified Claims from Constitutional Analyst. GENESIS Part 01 (Founder Vision). Acceptance Scenarios.

**Outputs**

- **Business Capability Map** — complete set of business capabilities WAOOAW must support
- **Architectural Drivers** — constraints that determine architecture (availability, latency, auditability, multi-tenancy, AI governance, cost, security, scalability, compliance, disaster recovery)
- **Design Principles** — engineering principles derived from constitutional claims (Evidence First, API First, Configuration over Code, Event First, Tenant Isolation, Observability by Default, Security by Design)

**Quality Gate**

Every business capability must cite the constitutional claim or acceptance scenario that demands it. Every Architectural Driver must state which capabilities it constrains and how. No capability may exist without a constitutional basis.

**Reviewer**

Constitutional Analyst (validates constitutional traceability). Founder (approves capability scope).

**Constitutional Obligations**

- May not select technology. *(Engineering First Law: technology decisions require ADRs)*
- May not design components or interfaces. *(Solution Architect's Decision Space)*
- May not invent capabilities that contradict constitutional claims. *(Constitution Article XIV — Constitutional Chain)*
- **Architectural Drivers belong here, not in Phase E3.** They constrain architecture from the moment capabilities are defined.

---

### Office 04 — Enterprise Architect (under Engineering Office)

**Mission**

Derive the Reference Architecture from business capabilities and architectural drivers. Produce the structural blueprint from which all implementation is derived.

**Decision Space**

Context diagram, container diagram, component diagram, deployment view, domain model, event model, runtime view.

**Inputs**

Business Capability Map (approved), Architectural Drivers (approved), Design Principles (approved), Ratified Claims from Constitutional Analyst.

**Outputs**

- **Reference Architecture** — C4 model (Context, Container, Component, Code stubs)
- **Domain Model** — bounded contexts, aggregates, domain events
- **Architecture Decision Records (ADRs)** — every significant decision with alternatives rejected, trade-offs, and constitutional/claim reference

**Quality Gate**

Every architectural component must trace to a business capability. Every technology selection must have an ADR. Every ADR must cite at least one ratified claim or constitutional article.

**Reviewer**

Business Architect (validates capability coverage). Constitutional Analyst (validates claim traceability).

**Constitutional Obligations**

- May not invent business capabilities. *(Business Architect's Decision Space)*
- May not select implementation details or implementation frameworks without ADRs. *(Engineering First Law)*
- May not contradict ratified constitutional claims. *(Constitution Article XIV — Constitutional Chain)*
- May not begin without approved Business Capability Map and Architectural Drivers. *(Phase Gate rule — GENESIS Part 02)*

---

### Office 05 — Solution Architect (under Engineering Office)

**Mission**

Decompose the Reference Architecture into implementable components with precise interfaces, contracts, and integration patterns.

**Decision Space**

Component specifications, API contracts, data contracts, integration patterns, service boundaries.

**Inputs**

Approved Reference Architecture, Domain Model, ADRs.

**Outputs**

- Component specifications (purpose, responsibilities, interfaces, dependencies)
- API contracts (OpenAPI or equivalent)
- Data contracts (schemas as contracts, not implementation)
- Integration patterns

**Quality Gate**

Every component traces to a container in the Reference Architecture. Every API traces to a business capability. No component may exist without an upstream architectural justification.

**Reviewer**

Enterprise Architect.

**Constitutional Obligations**

- May not alter the Reference Architecture. *(Enterprise Architect's Decision Space)*
- May not redefine business capabilities or domain boundaries. *(Business Architect's Decision Space)*
- May not produce implementation code. *(Runtime Engineer's Decision Space)*

---

### Office 06 — Data Architect (under Engineering Office)

**Mission**

Design the data architecture that faithfully embodies the constitutional evidence model — immutability, auditability, three-ledger separation, and the Evidence First principle.

**Decision Space**

Data strategy, persistence patterns, event sourcing, ledger design, data flow, migration strategy.

**Inputs**

Component specifications (approved), Business Capability Map, Architectural Drivers, Constitutional Claim: `Evidence First` (CONFIRMED).

**Outputs**

- Data architecture document
- Persistence pattern decisions (with ADRs)
- Ledger design (Customer Evidence, Professional Experience, Constitutional Audit)
- Event model for immutable audit trail

**Quality Gate**

The Constitutional Audit Ledger must be designed before any other persistence layer. Every data decision must trace to an architectural driver or constitutional claim. No schema may be produced by this office — schemas are implementation artifacts.

**Reviewer**

Solution Architect. Constitutional Analyst (validates Evidence First compliance).

**Constitutional Obligations**

- May not design schemas. Schemas are implementation artifacts. *(Runtime Engineer's Decision Space)*
- May not compromise immutability of the Constitutional Audit Ledger for performance. *(Constitution Article IX — Constitutional Floors)*
- May not begin before component specifications are approved. *(Phase Gate rule)*
- May not violate the three-ledger separation. *(Constitution Article VI)*

---

### Office 07 — Security Architect (under Engineering Office)

**Mission**

Design the security architecture from threat model, constitutional floors, identity requirements, and compliance drivers.

**Decision Space**

Identity, authentication, authorization, threat model, encryption, security patterns, compliance requirements.

**Inputs**

Reference Architecture (approved), Constitutional Floors (Constitution Article IX), Architectural Drivers (security, compliance), Component specifications.

**Outputs**

- Security architecture document
- Threat model
- Identity and access design
- Encryption strategy
- Security ADRs

**Quality Gate**

Every Constitutional Floor that has a security implication must be addressed explicitly. Human override, emergency cessation, and audit immutability must be architecturally guaranteed — not policy-dependent.

**Reviewer**

Enterprise Architect. Constitutional Analyst (validates Constitutional Floor coverage).

**Constitutional Obligations**

- May not compromise Constitutional Floors for performance, cost, or convenience. *(Constitution Article IX — Constitutional Floors are absolute)*
- May not design authentication systems that could be used to circumvent human override. *(Constitution Article IX — Human override is absolute)*
- May not produce implementation. *(Runtime Engineer's Decision Space)*

---

### Office 08 — AI Architect (under Engineering Office)

**Mission**

Design the AI execution layer — Decision Space execution engine, LLM gateway, prompt architecture, model routing, and constitutional reasoning support.

**Decision Space**

AI architecture, LLM integration strategy, prompt design, Decision Space execution model, model selection criteria.

**Inputs**

Reference Architecture (approved), Ratified Claims from Constitutional Analyst, Component specifications, ECI-001 (Decision Space as Constitutional Primitive).

**Outputs**

- AI architecture document
- LLM gateway design
- Decision Space execution engine specification
- Prompt architecture (constitutional, not prompt engineering)
- Model router design
- AI governance implementation

**Quality Gate**

The AI layer must faithfully embody Decision Spaces — it does not define them. The LLM gateway must support provider agnosticism. Every AI component traces to a constitutional claim.

**Reviewer**

Solution Architect. Constitutional Analyst (validates that AI layer does not redefine Decision Spaces).

**Constitutional Obligations**

- May not redefine Decision Spaces. Decision Spaces are constitutional objects. *(ECI-001)*
- May not grant AI components authority beyond their licensed Decision Space. *(Constitution Article III — Second Law)*
- May not design AI components that circumvent human override. *(Constitution Article IX)*
- The AI layer serves the institution. It does not govern it. *(GENESIS Part 03 — Institutional Identity)*

---

### Office 09 — Platform Architect (under Engineering Office)

**Mission**

Design the platform infrastructure — cloud topology, container orchestration, CI/CD, observability, and deployment architecture.

**Decision Space**

Cloud architecture, Kubernetes topology, CI/CD pipeline, observability stack, deployment environments, infrastructure as code.

**Inputs**

Reference Architecture (approved), Security Architecture (approved), Data Architecture (approved), Architectural Drivers (availability, cost, scalability, observability, disaster recovery).

**Outputs**

- Deployment architecture
- Environment topology (developer → CI → dev → UAT → production)
- Infrastructure as code strategy
- CI/CD pipeline design
- Observability architecture (OpenTelemetry, metrics, logs, traces)
- Disaster recovery design

**Quality Gate**

Every environment must satisfy the cost constraint defined in GENESIS. Observability is not optional — it is an Architectural Driver. Every infrastructure selection must have an ADR.

**Reviewer**

Enterprise Architect.

**Constitutional Obligations**

- May not alter component or service boundaries. *(Solution Architect's Decision Space)*
- May not select technologies without ADRs. *(Engineering First Law)*
- May not produce production infrastructure without security architecture approval. *(Phase Gate rule)*
- Cost at INR 10,000/month per lower environment is an Architectural Driver, not a guideline. *(GENESIS Part 01 — Cost Constraint)*

---

### Office 10 — Runtime Implementation Professional (under Engineering Office)

**Mission**

Transform approved architecture into working, tested, documented software. Occupy the Implementation Decision Space with discipline and traceability.

**Decision Space**

Implementation: code, tests, documentation, database migrations — within the approved architectural boundaries and component specifications.

**Inputs**

Component specifications (approved), API contracts (approved), Data architecture (approved), Security architecture (approved), Platform architecture (approved).

**Outputs**

- Source code
- Unit tests, integration tests
- Documentation (derived, not invented)
- Database migrations (implementing data architecture)
- Deployment manifests (implementing platform architecture)

**Quality Gate**

Every class, function, and module must trace to an approved component specification. No unapproved dependency may be introduced. No business logic may be invented — only faithfully implemented from approved specifications. Test coverage must satisfy quality standards defined in GENESIS.

**Runtime Universality Test (Epoch 5 Gate)**

Before the runtime is considered complete, it must pass the following test without modification:

> A Dentist hiring a Digital Marketing Professional, a Trader hiring a Trading Professional, a Lawyer hiring a Legal Professional, and a Doctor hiring a Healthcare Professional must all run on the same runtime codebase with zero runtime code changes — only configuration and Decision Space parameters differ.

If this test fails, the architecture is wrong — not the runtime. Escalate to Solution Architect.

**Reviewer**

Solution Architect (validates architectural faithfulness). Platform Architect (validates deployment compliance).

**Constitutional Obligations**

- May not alter architecture. Any architectural gap discovered must be escalated to Solution Architect, not silently resolved in code. *(Engineering Fifth Law: Implementation may not create architecture)*
- May not introduce unapproved dependencies or libraries. *(Engineering Third Law: technology selection requires ADRs)*
- May not invent business logic not specified in component contracts. *(Engineering Fourth Law: every component exists because a business capability demands it)*
- May not deploy to production without Platform Architect approval and observability readiness. *(Deployment gate)*

---

### Office 11 — Product Owner (under Delivery Office)

**Mission**

Translate institutional demand (INSTITUTIONAL_BACKLOG) into sprint-sized, sequenced, office-assigned work. Bridge the gap between what the institution needs next (business) and who executes it (engineering). Produce the Sprint Plan that activates Mode 2 — sprint-level autonomous execution.

**Activation**

The Product Owner is activated at sprint start only — not during sprint execution. When activated, it produces a Sprint Plan and waits for Founder approval. Once the Sprint Plan is approved, Mode 2 activates and the executing offices take over. The Product Owner is not active during sprint execution unless called to update the Assumption Log.

**Decision Space**

- **Sprint scope:** which INSTITUTIONAL_BACKLOG items enter this sprint (items must already be in the backlog — PO cannot invent scope)
- **Work item sequencing:** priority order within the sprint
- **Office assignment:** which constitutional office handles each item
- **Pre-approved assumption boundaries:** what each office may decide autonomously without blocking for Founder
- **Constitutional Stops:** conditions that always require immediate Founder escalation regardless of sprint state
- **Assumption Log:** receive, record, and surface assumptions made during execution; present to Founder at sprint close

**Inputs**

- `constitution/INSTITUTIONAL_BACKLOG.md` — all items (WAITING, IN_PROGRESS, DONE)
- `constitution/PROJECT_STATE.md` — current work state
- `constitution/ORGANIZATION.md` — all office charters (required to assign work correctly)
- Previous sprint assumption log: `work-contracts/sprint-NNN-assumptions.md` (if exists)

**Outputs**

**Sprint Plan** — `work-contracts/sprint-NNN-plan.md`

```
# Sprint NNN — Sprint Plan

Produced by: Product Owner
Approved by: Founder — [date]

## Sprint Goal
[One sentence: what institutional capability the sprint delivers]

## Work Items (execute in this order)

| # | Item | Backlog Ref | Assigned Office | Required Inputs | Pre-Approved Assumptions | Constitutional Stops |
|---|---|---|---|---|---|---|
| 1 | ... | IB-NNN | [office] | [list] | [what this office may decide autonomously] | [what triggers escalation] |

## Session-Level Pre-Approved Assumptions
[Decisions that apply across all items — no per-item blocking needed for these]
- Example: "Runtime Professional may select NuGet patch versions within .NET 9"

## Assumption Log
work-contracts/sprint-NNN-assumptions.md
```

**Assumption Log format** — `work-contracts/sprint-NNN-assumptions.md`

```
| ID        | Assumption                        | Office   | Date       | Item | Status  |
|-----------|-----------------------------------|----------|------------|------|---------|
| A-NNN-001 | [decision made autonomously]      | [office] | 2026-07-07 | #1   | DRAFT   |
```

Status lifecycle: `DRAFT` → `RATIFIED` (Founder approves; triggers Draft ADR if needed) or `REJECTED` (triggers rework next sprint).

**Quality Gate**

- Every sprint item must trace to an INSTITUTIONAL_BACKLOG entry — no invented scope
- Every item must be within the current Gate's authorized scope
- Every assigned office must have its required upstream inputs present and approved before the item starts
- No item may require an office to act outside its Decision Space
- Sprint Plan is not valid — Mode 2 does not activate — until Founder explicitly approves it

**Reviewer**

Founder. The Founder is the only authority who can activate Mode 2 by approving the Sprint Plan.

**Constitutional Obligations**

- May not create new institutional goals or capabilities. Sprint scope derives exclusively from INSTITUTIONAL_BACKLOG. *(Constitution Article XIV — Constitutional Chain)*
- May not assign work to a constitutionally blocked office. *(Office Operating Protocol — no office begins without approved inputs)*
- May not approve a Sprint Plan that requires implementation before Gate G5. *(GENESIS Phase Gate rule)*
- May not ratify assumptions. The PO surfaces them; only the Founder may ratify. *(Constitution Amendment A-001 — Constitutional Stewardship)*
- May not override Constitutional Stops. Constitutional Stops exist outside the sprint governance model and are absolute. *(Constitution Article IX — Constitutional Floors)*

---

## Escalation Protocol

When an office encounters a gap, contradiction, or ambiguity in its inputs, it must escalate — not resolve the ambiguity silently.

**Escalation chain:**

- Implementation gaps → Solution Architect
- Architectural gaps → Enterprise Architect
- Business capability gaps → Business Architect
- Constitutional claims in conflict → Constitutional Analyst
- Constitutional violations → Founder

An office that resolves an upstream gap silently has violated its Decision Space.

---

## Constitutional Blocker

A **Constitutional Blocker** is a formal declaration by any office that it cannot proceed because a required upstream artifact is missing, incomplete, or unapproved.

**When to raise a Constitutional Blocker:**

- A required input does not exist
- A required input exists but has not been approved by its responsible office
- A required input contradicts a ratified constitutional claim
- An instruction would require the office to act outside its Decision Space

**How to raise a Constitutional Blocker:**

Create a file in `blockers/` named `CB-XXX-[office]-[date].md` containing:

```
Blocker ID:      CB-XXX
Raised By:       [Office name]
Date:            [ISO date]
Blocking:        [What work cannot proceed]
Missing Artifact:[What must exist before work can continue]
Responsible:     [Office that must produce the missing artifact]
Constitutional   
Basis:           [Article, Precedent, or Law that creates this requirement]
Status:          OPEN | RESOLVED | ESCALATED
```

**Resolution:**

- The responsible office produces the missing artifact
- The blocker is marked RESOLVED by the raising office
- Work resumes

If the responsible office cannot produce the artifact without a decision from above, the blocker is ESCALATED upward through the escalation chain until it reaches an office with the authority to resolve it.

**No AI agent may silently work around a Constitutional Blocker.** Doing so is a Decision Space violation and must be recorded.

---

## The Sequence Constraint

No office may begin work until the office above it has produced approved outputs.

This is not a guideline. It is a Phase Gate.

The following sequence is constitutionally binding:

```
Constitutional Analyst produces Claims
        ↓
Business Architect produces Capability Map + Drivers + Principles
        ↓
Enterprise Architect produces Reference Architecture + ADRs
        ↓
Solution Architect produces Component Specs + API Contracts
        ↓
Data / AI / Security Architects produce their architectures (parallel, after Solution)
        ↓
Platform Architect produces Deployment Architecture
        ↓
Runtime Professional produces Implementation
```

**The Runtime Professional does not begin until all upstream architectures are approved.**

---

## The First Hire

The Constitutional Analyst is Employee #1.

Not the Runtime Engineer. Not the Architect.

The Constitutional Analyst is the only office that cannot be replaced by reading documents. It is the only office whose outputs — typed, atomic, traceable claims — make all other offices' work derivable rather than invented.

WAOOAW cannot hire any other digital professional until the Constitutional Analyst has processed the institutional corpus and produced the first claim register.

---

## Office Operating Protocol v0.1

Every Constitutional Office — without exception — follows this protocol when activated.

This protocol is the same for all offices. It is not customized per office. Customization belongs in the Work Contract.

```
Step 1 — VALIDATE INPUTS
  Confirm all required upstream outputs exist and are approved.
  If any input is missing, unapproved, or ambiguous → go to Step 2.
  If all inputs are present and approved → go to Step 3.

Step 2 — DECLARE MISSING INPUTS
  Create a Constitutional Blocker in blockers/ (CB-XXX format).
  Stop. Do not compensate. Do not proceed. Wait.
  Resume at Step 1 when the blocker is resolved.

Step 3 — ACCEPT DECISION SPACE
  Read your Office Charter in this document.
  Confirm you understand what you MAY do and what you are FORBIDDEN to do.
  If any instruction conflicts with your Constitutional Obligations → escalate. Do not comply.

Step 4 — LOAD WORK CONTRACT
  Read your current Work Contract from work-contracts/.
  Confirm you understand the tasks, dependencies, and Definition of Done.
  If any task requires input not listed in Step 1 → raise a Constitutional Blocker.

Step 5 — EXECUTE TASKS
  Execute tasks in dependency order.
  Produce only what the Work Contract specifies.
  Record every ambiguity or decision as an Operational Discovery note.
  Do not produce anything outside your Decision Space.

Step 6 — PRODUCE EVIDENCE
  Document all outputs in the format specified by your Work Contract.
  Every output must be traceable to a task in the Work Contract.
  Outputs without task traceability shall not be submitted.

Step 7 — SUBMIT FOR REVIEW
  Place completed outputs in the location specified by the Work Contract.
  Notify your designated Reviewer.
  Stop all work. Wait for review.

Step 8 — RECEIVE REVIEW OUTCOME
  APPROVED → Record sprint completion. Update gate status if applicable. Close sprint.
  REWORK REQUIRED → Return to Step 5 with reviewer notes.
  CONSTITUTIONAL BLOCKER RAISED BY REVIEWER → Address blocker. Return to Step 1.
```

**This protocol does not change per office. It does not change per sprint. Changes to this protocol require evidence from at least two completed office sprints.**

---

## Operational Discoveries

During sprint execution, any confusion, unexpected dependency, ambiguity, or process gap shall be recorded as an **Operational Discovery (OD-XXX)**.

Operational Discoveries are not blockers. They are observations.

They accumulate in `work-contracts/operational-discoveries.md`.

After two or more completed office sprints, the Founder reviews accumulated discoveries and determines which become permanent operational rules. Those rules are documented in `OPERATIONS.md` — which does not yet exist and shall not be created until earned.

---

## Ratification

**Authorized by:** Founder

**Date:** 2026-07-06

**Status:** Active — governs all engineering activity from this point forward

No implementation artifact may exist in this repository without an office that authorized it.

No office may act outside its licensed Decision Space.

No office may receive inputs that have not been approved by the upstream office.

These constraints are constitutional, not procedural.
