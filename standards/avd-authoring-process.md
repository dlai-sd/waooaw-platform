# AVD Authoring Process

**Classification:** Standard — Agent Onboarding Governance
**Status:** Proposed — Awaiting Constitutional Analyst review + Founder acknowledgement
**Produced by:** Business Architect (INST-003) — GOAL-001 Phase 4 (2026-07-27)
**Constitutional Basis:** WIOM §W-1 (Constitutional Birth) · GEOM §G-1 (Goal Registration) · ORGANIZATION.md Office 03
**Goal Reference:** GOAL-001 — Semantic Brain Transformation

---

## Purpose

This document defines the constitutional process by which a new agent enters the WAOOAW institution. Every new agent — customer-facing or internal — must traverse this process completely. There are no shortcuts, no informal approvals, and no "we'll spec it properly later."

**The process enforces one truth:** An agent that is not a constitutionally chartered Institution is not a WAOOAW agent. It is an unaccountable AI system. WAOOAW does not deploy unaccountable AI systems.

---

## What the AVD Is

The Agent Vision Document (AVD) is the **business and vision case for a new Institution**. It answers:

- What customer problem does this agent solve?
- Who are the customers?
- What will this agent do — and what will it never do?
- How does it earn trust?
- Why does it belong inside WAOOAW's constitutional model?

The AVD is NOT a technical specification. It does not contain API designs, database schemas, or implementation details. Those are downstream artifacts produced by Enterprise Architect and AI Architect AFTER the AVD is ratified.

**The AVD becomes the Institution's founding document.** Its ratification by the Founder is the act of constitutional birth (WIOM Stage W-1). Everything that follows — the Agent Spec, the Implementation Goal, the Operational Readiness Declaration — derives from it.

---

## The 7-Stage Process

```
Stage 1: Idea → Goal Registration
Stage 2: Business Architect Assignment
Stage 3: AVD Production
Stage 4: Multi-Institution AVD Review
Stage 5: Founder Ratification → Institution Chartered
Stage 6: Agent Specification
Stage 7: Implementation Goal Registration → WIOM Lifecycle begins
```

---

### Stage 1 — Idea to Goal Registration

**Who:** Any Steward (Yogesh / Sujay / Ojal) may propose a new agent. Customers may also request a new agent type through their constitutional employment contract.

**Input mode — raw thoughts are a valid first-class input:**

The Founder or Steward does NOT need to produce a structured Goal statement. The following are all valid Stage 1 inputs:
- A plain English paragraph: *"I want an agent that understands codebases..."*
- A mind map or sketch (photographed, described, or attached)
- A voice note transcript
- A collection of raw thoughts, references, or market observations
- A document like a RepoNav AVD v0.1 (vision-level draft)

**The Goal Orchestrator's Understanding stage (GEOM §G-2) converts any of these into a structured Goal.** The Founder's job in Stage 1 is to share intent — not to produce a constitutionally formatted Goal statement. The Goal Orchestrator produces the understanding; the Founder confirms it.

**Action:** The agent idea is registered as a **Goal in the Goal Register** — not a feature request, not a GitHub Issue, not an informal note.

**Goal format for a new agent:**

```
Goal Statement:    "Create and charter a WAOOAW agent for [domain]"
Registrant:        [Steward name]
Success Criteria:
  SC-01: AVD produced and Founder-ratified
  SC-02: Institution Charter issued and INST-NNN assigned in Institution Registry
  SC-03: Agent Specification complete and EA-approved
  SC-04: Acceptance Scenario defined and Grade A achieved in simulation
  SC-05: Operational Readiness Declaration ratified
Classification:    Narrow · Design · Medium · Routine
```

**Why a Goal, not a ticket?** Because the new agent, once chartered, is an Institution that will participate in customer Goals. It must itself be born through the Goal-governed process. The institution demonstrates the model it will operate under.

**Gate:** Goal registered in Goal Register with all five success criteria stated before Stage 2 begins.

---

### Stage 2 — Business Architect Assignment

**Who:** Goal Orchestrator (INST-013)

**Action:** Goal Orchestrator reviews the Goal, confirms it is within Business Architect's Offering Scope, and issues a GO Authorization to Business Architect (INST-003).

```
GOA-GOAL-NNN-INST-003-01:
  goal_id:            GOAL-NNN
  institution_id:     INST-003
  contribution_scope: AVD production using avd/AVD-TEMPLATE.md
  participation_window: [defined by GO]
  collaboration_type: Primary
  issued_by:          INST-013
```

**Gate:** GO Authorization exists in Goal Register before Business Architect begins.

---

### Stage 3 — AVD Production

**Who:** Business Architect (INST-003)

**Input:** `avd/AVD-TEMPLATE.md` · Market context · Customer evidence (if available)

**Action:** Business Architect produces the AVD using the template. The AVD has 12 sections — all are mandatory. A missing section is a gate failure (this is a gate, not a guide).

**AVD File naming:** `avd/AVD-NNN-[agent-slug]-v0.1.md`

**The 12 mandatory AVD sections:**

| # | Section | Purpose |
|---|---|---|
| 1 | Agent Identity | Name, domain, vision, mission, customer promise |
| 2 | Why This Agent Exists | Customer problem, why now, why existing solutions fail |
| 3 | Customer Universe | Customer ecosystems (not individual personas) |
| 4 | Agent Purpose | One sentence — the institutional purpose |
| 5 | Core Principles | Constitutional principles this agent inherits + any domain-specific additions |
| 6 | Skills (MVP1) | What the agent can do on day one — purpose, inputs, outputs, success measures |
| 7 | Knowledge Universe | What the agent knows and learns from (internal + operational + external) |
| 8 | Semantic Twin | What institutional knowledge the agent maintains and how it evolves |
| 9 | Goal Journey | How the agent processes a customer Goal (GEOM-aligned: Understand → Reason → Evidence → Recommend → Execute → Learn) |
| 10 | AI Execution | How MagicLLM serves this agent's task categories |
| 11 | **Institution Charter Parameters** *(new — WIOM alignment)* | Proposed Decision Space · Offering Scope · Code of Conduct · Constitutional Authority references |
| 12 | **Why WAOOAW** *(constitutional employment fit)* | Why this agent requires constitutional governance; what constitutional obligations it carries |

**Business Architect Evidence produced:**

```
institution_id:  INST-003
goal_id:         GOAL-NNN
record_id:       AVD-NNN-v0.1
record_type:     Agent Vision Document
sections_complete: all 12
produced_at:     [timestamp]
```

**Gate:** All 12 sections present and non-empty. `avd/AVD-NNN-[slug]-v0.1.md` committed to repository.

---

### Stage 4 — Multi-Institution AVD Review

**Who:** Goal Orchestrator routes simultaneously to reviewing Institutions.

**Parallel review streams:**

| Institution | Review focus | Output |
|---|---|---|
| Constitutional Analyst (INST-002) | Constitutional alignment: does Section 12 cite the correct claims and articles? Does Section 11 propose a valid Decision Space? Is the Code of Conduct complete? | Constitutional Alignment Record |
| Enterprise Architect (INST-004) | Architectural feasibility: can the skills in Section 6 be implemented within the existing reference architecture? What new components would be required? | Architectural Feasibility Record |
| AI Architect (INST-008) | AI execution validity: does Section 10 describe a coherent MagicLLM integration? What task categories does this agent require? | AI Execution Validity Record |

**Each review Institution must answer three questions:**
1. Is this AVD constitutionally sound for ratification?
2. What must change before ratification?
3. What is deferred to Agent Specification (Stage 6)?

**Gate:** All three Contribution Records published. All blocking objections resolved. Business Architect updates AVD to `v0.2` incorporating review feedback.

---

### Stage 5 — Founder Ratification → Institution Chartered

**Who:** Founder (INST-001)

**Action:** Founder reviews the AVD (`v0.2+`) with the three Institution review records and ratifies.

**Ratification produces three constitutional artifacts simultaneously:**

**Artifact 1 — Ratified AVD** (`avd/AVD-NNN-[slug]-v1.0.md`)
The AVD version number advances to `v1.0` upon ratification. The v1.0 AVD is the agent's founding document.

**Artifact 2 — Institution Charter entry in INSTITUTION-REGISTRY.md**
A new `INST-NNN` entry is created using the Charter Parameters from AVD Section 11:

```
INST-NNN | [Agent Canonical Name] | [Domain] | CHARTERED
Decision Space: [from AVD §11]
Offering Scope: [from AVD §6 skills]
Charter Date: [ratification date]
Status: CAPABILITY DEVELOPMENT (WIOM Stage W-2)
```

**Artifact 3 — Goal Register Contribution Record**
The Founder's ratification is recorded as a Contribution Record against the Goal:

```
SC-01: SATISFIED — AVD-NNN-v1.0 ratified
SC-02: SATISFIED — INST-NNN issued and registered
```

**Gate:** Institution Registry entry exists with Status = CAPABILITY DEVELOPMENT. Both SC-01 and SC-02 marked SATISFIED in Goal Register.

---

### Stage 6 — Agent Specification

**Who:** Enterprise Architect (INST-004) + AI Architect (INST-008)

**Prerequisite:** Ratified AVD v1.0. No Agent Specification may begin without this.

**Input:** Ratified AVD · INSTITUTION-REGISTRY.md entry · AGENT-AUTHORING-GUIDE.md

**Action:** Enterprise Architect and AI Architect produce the full agent specification following AGENT-AUTHORING-GUIDE.md. The specification is explicitly derived from the AVD:

- AVD §6 (Skills) → Section 3 (Skill Catalogue) of the Agent Spec
- AVD §11 (Charter Parameters) → Section 0 (Constitutional DNA) of the Agent Spec
- AVD §9 (Goal Journey) → Skill Execution Models in Agent Spec
- AVD §10 (AI Execution) → MagicLLM task category configuration

**Gate:** EA review + Founder approval per AGENT-AUTHORING-GUIDE.md §gate requirements. SC-03 marked SATISFIED in Goal Register.

---

### Stage 7 — Implementation Goal Registration → WIOM Lifecycle

**Who:** Founder (registers Implementation Goal) → Goal Orchestrator (routes it)

**Action:** The Founder registers a separate Goal for implementation:

```
Goal Statement:   "Implement [Agent Name] per AVD-NNN-v1.0"
Registrant:       Founder
Parent AVD:       AVD-NNN-v1.0
Parent Goal:      GOAL-NNN (the new-agent Goal)
Success Criteria:
  - All skills in Agent Spec implemented and Grade A in simulation
  - Operational Readiness Declaration ratified (WIOM Stage W-3)
  - First live customer session completed and constitutional compliance verified
```

This implementation Goal follows the **Engineering Execution Model (EEM)** exactly like any other engineering Goal. The Implementation Goal is the bridge between the AVD process and the EEM.

**WIOM lifecycle parallel track:**

While the implementation Goal is in progress, the new Institution simultaneously progresses through WIOM:
- **Stage W-2 (Capability Development):** Agent is built; simulations run; decision spaces are validated
- **Stage W-3 (Operational Readiness Declaration):** Agent passes C-086 Simulation Gate (Grade A); CA produces Readiness Audit; Founder ratifies → Institution is OPERATIONAL
- **Stage W-4 (Active Service):** Agent accepts customer Goals

**SC-04** (Acceptance Scenario Grade A) and **SC-05** (Operational Readiness Declaration) are satisfied during Stage W-3.

**Goal Closure:** The original new-agent Goal (from Stage 1) is closed by the Goal Orchestrator after all five SC-NNN are SATISFIED and the Operational Readiness Declaration is ratified.

---

## Governance Constraints

| Constraint | Source | Effect on AVD Process |
|---|---|---|
| No implementation without ratified AVD | BOOTSTRAP Step 10b (Spec-First) | Stage 6 cannot begin without Stage 5 complete |
| All Goals must trace to Goal Register | GEOM Principle G-1 | Agent idea must be a registered Goal (Stage 1) |
| Institution Charter requires Founder ratification | WIOM §W-1 | Stage 5 is the constitutional birth act — no shortcuts |
| One process for all agents | WIOM Principle W-1 (Uniform Operating Behaviour) | Internal agents (Platform IT Expert, Steward Assistant) follow this same process |
| AVD v1.0 is the founding document | This standard | AVD changes after v1.0 require a constitutional amendment to the agent's Charter |

---

## AVD Versioning

| Version | Meaning | Trigger |
|---|---|---|
| `v0.1` | Initial draft by Business Architect | Stage 3 completion |
| `v0.x` | Review revisions | Stage 4 feedback incorporated |
| `v1.0` | Founder-ratified | Stage 5 ratification |
| `v1.x` | Minor skill additions or clarifications | Subsequent Goal-Driven Evolution (WIOM Stage W-5) |
| `v2.0` | Major mission or customer universe change | New AVD process from Stage 3 |

**A v1.0 AVD cannot be retroactively modified.** It is a constitutional founding document. Changes to a live agent's scope require Stage W-5 (Goal-Driven Evolution) and produce a new AVD version, not an edit to v1.0.

---

## Process Summary Table

| Stage | Institution | Input | Output | Gate |
|---|---|---|---|---|
| 1. Idea → Goal | Founder/Steward | Agent idea | Registered Goal with 5 SC-NNN | Goal in Goal Register |
| 2. Assignment | Goal Orchestrator | Goal + Institution Registry | GO Authorization to INST-003 | GOA in Goal Register |
| 3. AVD Production | Business Architect (INST-003) | AVD Template + context | AVD v0.1 (12 sections) | All sections complete |
| 4. Multi-Review | CA + EA + AI Architect | AVD v0.1 | 3 Review Records + AVD v0.2 | All 3 records published, objections resolved |
| 5. Ratification | Founder (INST-001) | AVD v0.2 + reviews | AVD v1.0 + INST-NNN + SC-01/02 satisfied | Institution Registry entry = CHARTERED |
| 6. Agent Spec | Enterprise Architect + AI Architect | AVD v1.0 | Agent Spec (AGENT-AUTHORING-GUIDE) | EA review + Founder approval |
| 7. Implementation | All Engineering Institutions | Agent Spec + EEM | Live agent (Grade A) | Operational Readiness Declaration ratified |

---

*Produced by Business Architect (INST-003) — GOAL-001 Phase 4*
*For Constitutional Analyst review (INST-002) and Founder acknowledgement.*
*Pending review, this is a proposed standard — not yet governing.*
