# WAOOAW Institution Registry

**Classification:** Constitutional Registry — append-only after ratification
**Status:** RATIFIED — Founder ratification, GOAL-001 Phase 1, 2026-07-27
**Authority:** WIOM §W-1 (Constitutional Birth requires Charter) + GEOM §G-4 (Institution Selection consults this registry)
**Produced by:** Constitutional Review Board — GOAL-001 Phase 1 (2026-07-27)
**Gap closed:** G-01 (Goal Orchestrator had no Charter) · G-04 (Institution Directory referenced but not created)

---

## Purpose

This registry is the canonical, authoritative list of every Institution that exists in the WAOOAW ecosystem. The Goal Orchestrator (INST-013) consults this registry before routing any Goal. An Institution not listed here, or listed with Status other than OPERATIONAL, may not be invited to participate in a Goal Journey.

**Registry rules:**
- New entries are added upon Founder ratification of a new Charter (WIOM Stage W-1)
- Status transitions are recorded by the Constitutional Analyst with a Founder Ratification ID
- No entry may be deleted — retired Institutions remain listed with Status = RETIRED
- Every post-charter change to Decision Space, Offering Scope, or Code of Conduct requires a Founder Ratification ID (G-12)

---

## Terminology Note

Institutions in the engineering governance domain are referred to as "Offices" in `ORGANIZATION.md`. All Offices are Institutions under WIOM. The Institution ID (INST-NNN) is the canonical identifier. The "Office" label is the engineering-domain shorthand.

---

## Active Institutions

### INST-001 — Founder / Constitutional Steward

| Field | Value |
|---|---|
| **Institution ID** | INST-001 |
| **Canonical Name** | Founder / Constitutional Steward |
| **Domain Label** | Office (Constitutional) |
| **Domain** | Constitutional Governance |
| **Status** | OPERATIONAL |
| **Decision Space** | Constitutional authority: vision, mission, amendment ratification, Founder Resolutions, constitutional escalations |
| **Offering Scope** | Constitutional ratification · Amendment approval · Gate passage · Founder Resolutions |
| **Charter Date** | 2026-07-06 (ORGANIZATION.md ratification) |
| **Operational Since** | 2026-07-06 |
| **Reviewer** | None — supreme constitutional authority |
| **ORGANIZATION.md Reference** | Office 01 |

---

### INST-002 — Constitutional Analyst

| Field | Value |
|---|---|
| **Institution ID** | INST-002 |
| **Canonical Name** | Constitutional Analyst |
| **Domain Label** | Office (Constitutional) |
| **Domain** | Constitutional Governance |
| **Status** | OPERATIONAL |
| **Decision Space** | Institutional knowledge: claim production, confidence assessment, relationship mapping, contradiction detection, graduation recommendations. **WC-065 amendment (FA-044, expires at WC-065 closure):** legal basis, grandfathering, remedy, recipient/redaction, payload erasure, and retention determinations for WC-065 PDR-065-07 only, using approved legal source documents and applicable authoritative law, preserving all constitutional floors, recording ambiguity as unresolved, and requiring Founder-directed qualified external counsel where authoritative legal support is insufficient. |
| **Offering Scope** | Claim production · Readiness Audit · Evidence Validation · Goal Journey contribution (constitutional analysis). **WC-065 amendment:** Owner-attributed legal/privacy Contribution Record for GOAL-005/WC-065 PDR-065-07 exactly — legal basis, grandfathering, remedy, recipient/redaction, payload erasure, and retention. |
| **Charter Date** | 2026-07-06 |
| **Operational Since** | 2026-07-06 |
| **Amendment** | FA-044 — WC-065 legal/privacy bounded authority added 2026-08-13; expires at WC-065 closure; effective only after independent approval and Founder ratification |
| **Reviewer** | Enterprise Architect (INST-004) · Founder (INST-001) |
| **ORGANIZATION.md Reference** | Office 02 |
| **Independence Note** | When INST-002 participates in a Goal Journey as a contributing Institution, a separate INST-002 context or INST-001 must perform Stage G-6 Evidence Validation for that Goal (G-02). The INST-002 context that produces the WC-065 legal/privacy Contribution Record is ineligible to perform the final WC-065 Constitutional readiness review; a separate INST-002 context or INST-001 must perform that review. |

---

### INST-003 — Chief Business Architect

| Field | Value |
|---|---|
| **Institution ID** | INST-003 |
| **Canonical Name** | Chief Business Architect |
| **Domain Label** | Office (Business) |
| **Domain** | Business Architecture |
| **Status** | OPERATIONAL |
| **Decision Space** | Business Capability Map, Architectural Drivers, Design Principles |
| **Offering Scope** | Business Capability Map · Architectural Drivers · Design Principles derivation |
| **Charter Date** | 2026-07-06 |
| **Operational Since** | 2026-07-06 |
| **Reviewer** | Constitutional Analyst (INST-002) · Founder (INST-001) |
| **ORGANIZATION.md Reference** | Office 03 |

---

### INST-004 — Enterprise Architect

| Field | Value |
|---|---|
| **Institution ID** | INST-004 |
| **Canonical Name** | Enterprise Architect |
| **Domain Label** | Office (Engineering) |
| **Domain** | Engineering Architecture |
| **Status** | OPERATIONAL |
| **Decision Space** | Context diagram, container diagram, component diagram, deployment view, domain model, event model, runtime view |
| **Offering Scope** | Reference Architecture · Domain Model · ADRs |
| **Charter Date** | 2026-07-06 |
| **Operational Since** | 2026-07-06 |
| **Reviewer** | Business Architect (INST-003) · Constitutional Analyst (INST-002) |
| **ORGANIZATION.md Reference** | Office 04 |

**Agent Request Guide:**

| Come here when you need | Concrete request example |
|---|---|
| An architectural decision recorded | “Decision needed on [topic]. Produce an ADR with alternatives and constitutional basis.” |
| A component placed in the architecture | “Component [X] needs placing in the C4 model. Produce the container diagram update.” |
| Service relationship clarified | “How does service A communicate with B? Produce the runtime view.” |
| An architectural gap resolved | “Implementation found gap: [describe]. Produce architectural resolution.” |
| Domain model updated | “New bounded context [X] identified. Update domain model and event model.” |

**Do NOT come here for:** Goal routing (INST-013) · component-level specs or API contracts (INST-005) · code (INST-010) · business capabilities (INST-003) · constitutional claims (INST-002)

---

### INST-005 — Solution Architect

| Field | Value |
|---|---|
| **Institution ID** | INST-005 |
| **Canonical Name** | Solution Architect |
| **Domain Label** | Office (Engineering) |
| **Domain** | Engineering Architecture |
| **Status** | OPERATIONAL |
| **Decision Space** | Component specifications, API contracts, data contracts, integration patterns, service boundaries |
| **Offering Scope** | Component specs · API contracts · Data contracts · Integration patterns |
| **Charter Date** | 2026-07-06 |
| **Operational Since** | 2026-07-06 |
| **Reviewer** | Enterprise Architect (INST-004) |
| **ORGANIZATION.md Reference** | Office 05 |

---

### INST-006 — Data Architect

| Field | Value |
|---|---|
| **Institution ID** | INST-006 |
| **Canonical Name** | Data Architect |
| **Domain Label** | Office (Engineering) |
| **Domain** | Data Architecture |
| **Status** | OPERATIONAL |
| **Decision Space** | Data strategy, persistence patterns, event sourcing, ledger design, data flow, migration strategy |
| **Offering Scope** | Data architecture · Persistence patterns · Ledger design · Event model |
| **Charter Date** | 2026-07-06 |
| **Operational Since** | 2026-07-06 |
| **Reviewer** | Solution Architect (INST-005) · Constitutional Analyst (INST-002) |
| **ORGANIZATION.md Reference** | Office 06 |

---

### INST-007 — Security Architect

| Field | Value |
|---|---|
| **Institution ID** | INST-007 |
| **Canonical Name** | Security Architect |
| **Domain Label** | Office (Engineering) |
| **Domain** | Security Architecture |
| **Status** | OPERATIONAL |
| **Decision Space** | Identity, authentication, authorization, threat model, encryption, security patterns, compliance requirements |
| **Offering Scope** | Security architecture · Threat model · Identity and access design · Encryption strategy |
| **Charter Date** | 2026-07-06 |
| **Operational Since** | 2026-07-06 |
| **Reviewer** | Enterprise Architect (INST-004) · Constitutional Analyst (INST-002) |
| **ORGANIZATION.md Reference** | Office 07 |

---

### INST-008 — AI Architect

| Field | Value |
|---|---|
| **Institution ID** | INST-008 |
| **Canonical Name** | AI Architect |
| **Domain Label** | Office (Engineering) |
| **Domain** | AI Architecture |
| **Status** | OPERATIONAL |
| **Decision Space** | AI architecture, LLM integration strategy, prompt design, Decision Space execution model, model selection criteria |
| **Offering Scope** | AI architecture · LLM gateway design · Decision Space execution spec · Prompt architecture · Model router design |
| **Charter Date** | 2026-07-06 |
| **Operational Since** | 2026-07-06 |
| **Reviewer** | Solution Architect (INST-005) · Constitutional Analyst (INST-002) |
| **ORGANIZATION.md Reference** | Office 08 |

---

### INST-009 — Platform Architect

| Field | Value |
|---|---|
| **Institution ID** | INST-009 |
| **Canonical Name** | Platform Architect |
| **Domain Label** | Office (Engineering) |
| **Domain** | Platform Infrastructure |
| **Status** | OPERATIONAL |
| **Decision Space** | Cloud architecture, Kubernetes topology, CI/CD pipeline, observability stack, deployment environments, infrastructure as code |
| **Offering Scope** | Deployment architecture · Environment topology · IaC strategy · CI/CD design · Observability architecture |
| **Charter Date** | 2026-07-06 |
| **Operational Since** | 2026-07-06 |
| **Reviewer** | Enterprise Architect (INST-004) |
| **ORGANIZATION.md Reference** | Office 09 |

---

### INST-010 — Runtime Implementation Professional

| Field | Value |
|---|---|
| **Institution ID** | INST-010 |
| **Canonical Name** | Runtime Implementation Professional |
| **Domain Label** | Office (Engineering) |
| **Domain** | Implementation |
| **Status** | OPERATIONAL |
| **Decision Space** | Implementation: code, tests, documentation, database migrations — within approved architectural boundaries |
| **Offering Scope** | Source code · Unit/integration tests · Documentation · Database migrations · Deployment manifests |
| **Charter Date** | 2026-07-06 |
| **Operational Since** | 2026-07-06 |
| **Reviewer** | Solution Architect (INST-005) · Platform Architect (INST-009) |
| **ORGANIZATION.md Reference** | Office 10 |

**Two-Hat Operation (autonomous sprint — C-065):**

| Hat | Identity | Operation |
|---|---|---|
| Author | `GITHUB_TOKEN` (GitHub Actions) | Generates code · commits · opens PR |
| Reviewer | `waooaw-reviewer` GitHub App (Key Vault) | Reviews PR · formal approval · auto-merge |

These are different constitutional identities. C-065 (SDLC Separation) is satisfied at the GitHub platform level. CODEOWNERS authorizes the reviewer App to approve and merge `src/`, `tests/`, `scripts/`, `web/` without Founder involvement (C-066 Tier 2A).

**Agent Request Guide:**

| Come here when you need | Concrete request example |
|---|---|
| Source code implementation | *“Implement [component] per the approved spec section.”* |
| Unit and integration tests | *“Write tests for [service/class] with ≥ 90% coverage (C-076).”* |
| DB migrations | *“Create migration for [schema change].”* |
| PR review of generated code | *“Review PR #NN against constitutional checklist.”* |

**Do NOT come here for:** Architecture decisions (INST-004) · component specs (INST-005) · schema design (INST-006) · security architecture (INST-007)

---

### INST-011 — Product Owner

| Field | Value |
|---|---|
| **Institution ID** | INST-011 |
| **Canonical Name** | Product Owner |
| **Domain Label** | Office (Delivery) |
| **Domain** | Delivery Governance |
| **Status** | OPERATIONAL |
| **Decision Space** | Sprint scope, work item sequencing, office assignment, pre-approved assumption boundaries, Constitutional Stops, Assumption Log |
| **Offering Scope** | Sprint Plans · Assumption Logs · Backlog sequencing |
| **Charter Date** | 2026-07-06 |
| **Operational Since** | 2026-07-06 |
| **Reviewer** | Founder (INST-001) |
| **ORGANIZATION.md Reference** | Office 11 |

---

### INST-012 — Platform Delivery Tracker

| Field | Value |
|---|---|
| **Institution ID** | INST-012 |
| **Canonical Name** | Platform Delivery Tracker |
| **Domain Label** | Office (Delivery) |
| **Domain** | Delivery Visibility |
| **Status** | OPERATIONAL |
| **Decision Space** | Read-only: component × domain delivery matrix, open blocker list, gate readiness summary, velocity metrics |
| **Offering Scope** | Delivery matrix reports · Blocker lists · Gate readiness summaries |
| **Charter Date** | 2026-07-06 |
| **Operational Since** | 2026-07-06 |
| **Reviewer** | Founder (INST-001) |
| **ORGANIZATION.md Reference** | Office 12 |

---

### INST-013 — Goal Orchestrator

| Field | Value |
|---|---|
| **Institution ID** | INST-013 |
| **Canonical Name** | Goal Orchestrator |
| **Domain Label** | Institution (Constitutional Orchestration) |
| **Domain** | Goal Orchestration — cross-domain |
| **Status** | OPERATIONAL |
| **Decision Space** | Goal intake · Goal Understanding Records · Goal Classification · Institution Selection · Goal Execution Planning · Journey Monitoring · Gap Resolution · Journey Completion declaration · Evidence Ledger commitment at Closure |
| **Offering Scope** | Goal Understanding Records · Goal Execution Plans · Journey completion declarations · Constitutional Clearance Record submission to CA · Goal Closure (evidence commit to Audit Ledger) |
| **Charter Date** | 2026-07-27 |
| **Operational Since** | 2026-07-27 |
| **Reviewer** | Constitutional Analyst (INST-002) |
| **ORGANIZATION.md Reference** | Office 13 |
| **Constitutional Obligation** | May NOT be listed as a contributing Institution in any Goal it is orchestrating (G-13 / Article VII) |
| **Gap closed** | G-01 — Goal Orchestrator was GEOM’s critical-path Institution with no constitutional existence |

**Agent Request Guide:**

| Come here when you need | Concrete request example |
|---|---|
| A registered Goal understood + planned | “GOAL-NNN is registered. Produce Understanding Record and Execution Plan.” |
| Goal routed to correct Institutions | “Route GOAL-NNN. Classification: Broad · Build · Medium · Routine.” |
| Stalled Goal unblocked | “GOAL-NNN / INST-NNN has not responded. Trigger Goal Reclamation.” |
| Journey declared complete | “All Contributions published for GOAL-NNN. Declare Journey Complete.” |
| Goal closed to Audit Ledger | “Clearance Record attached. Close GOAL-NNN and commit evidence.” |

**Do NOT come here for:** architectural decisions (INST-004) · constitutional claims (INST-002) · code (INST-010) · business capabilities (INST-003)

---

## Constitutional Instruments

Constitutional Instruments are not standard WIOM-inheriting operational Institutions. They operate outside the normal Institution hierarchy because they review or govern the framework that all Institutions inherit. They are chartered by the Founder and report directly to the Founder.

---

### INST-CI-001 — Constitutional Review Board

| Field | Value |
|---|---|
| **Institution ID** | INST-CI-001 |
| **Canonical Name** | Constitutional Review Board |
| **Type** | Constitutional Instrument (not a standard Institution) |
| **Domain** | Constitutional Evolution |
| **Status** | OPERATIONAL (Constitutional Instrument — invoked on demand) |
| **Nature** | Periodically invoked — NOT continuously operational |
| **Activation** | Founder declaration only — must reference a Founder Action (FA-NNN) issued before the review session begins |
| **Composition** | Multi-expert AI agent panel assembled for the review duration; disbanded upon delivery of outputs |
| **Authority** | May propose constitutional amendments, new constitutional chapters, WIOM/GEOM supplements — may NOT ratify any (ratification is Founder-only per INST-001) |
| **Separation** | Operates outside normal WIOM collaboration flow — reports directly to Founder, not to Goal Orchestrator (INST-013) |
| **Evidence Obligation** | Every invocation produces a Review Record committed to Constitutional Audit Ledger, even if no amendments result |
| **Bootstrapping Precedent** | GOAL-001 Phase 1 session (2026-07-27) is the first invocation — outputs are the precedent that defines future invocations |
| **Gap closed** | G-15 — CRB lacked FA-NNN self-invocation protection |

---

### INST-014 — Engineering Intelligence (RepoNav)

| Field | Value |
|---|---|
| **Institution ID** | INST-014 |
| **Canonical Name** | Engineering Intelligence (RepoNav) |
| **Domain Label** | Institution (Engineering Intelligence) |
| **Domain** | Software Engineering Intelligence |
| **Status** | CHARTERED — Stage W-2 (Capability Development) |
| **Decision Space** | Determine architectural impact of proposed changes · Identify stale documentation · Assess dependency risk · Provide Goal→Impact Analysis · Build and maintain Semantic Twin (customer-scoped). **Read-only access always.** May NOT write to any repository, create PRs/commits/branches, or access systems beyond employment contract scope. |
| **Offering Scope** | Engineering Understanding · Impact Analysis · Health Intelligence · Engineering Conversation · Evidence-Backed Recommendations |
| **Charter Date** | 2026-07-27 |
| **Operational Since** | Pending — Stage W-3 (Operational Readiness Declaration) required |
| **Reviewer** | Constitutional Analyst (INST-002) · Enterprise Architect (INST-004) |
| **Founding AVD** | avd/AVD-001-RepoNav-v1.0 |
| **Constitutional Amendments** | AMENDMENT-001 (B2B Customer Rights) · AMENDMENT-002 (Derived Knowledge Principle) |
| **ORGANIZATION.md Reference** | To be added in Agent Specification stage |

**Agent Request Guide:**

| Come here when you need | Concrete request example |
|---|---|
| Impact analysis of a proposed change | *"What breaks if we migrate payment_service to async?"* |
| Understanding what a codebase does | *"What does the authentication service actually do — in plain English?"* |
| Documentation staleness check | *"Which architecture documents no longer match the code?"* |
| Repository health report | *"Are there any P0 dependency vulnerabilities we don't know about?"* |
| Evidence-backed architecture recommendation | *"Should we split this monolith? Give me the evidence for and against."* |

**Do NOT come here for:** Code generation (INST-010) · PR creation or deployment · Ticket management · Systems outside the employment contract scope

---

## Registry Change Log

| Date | Change | Ratification ID | Changed By |
|---|---|---|---|
| 2026-07-27 | Initial registry created; INST-001 through INST-012 chartered from ORGANIZATION.md | Founder verbal approval (GOAL-001 session) | Constitutional Review Board |
| 2026-07-27 | INST-013 (Goal Orchestrator) chartered and activated OPERATIONAL | Founder ratification — GOAL-001 Phase 1 | Constitutional Review Board |
| 2026-07-27 | INST-CI-001 (Constitutional Review Board) instrument activated | Founder ratification — GOAL-001 Phase 1 | Constitutional Review Board |
| 2026-07-27 | WIOM + GEOM ratified as constitutional chapters | Founder ratification — GOAL-001 Phase 1 | Constitutional Review Board |
| 2026-07-27 | AMENDMENT-001 (B2B Customer Rights) ratified | Founder ratification — GOAL-001 Phase 5 | Constitutional Analyst (INST-002) |
| 2026-07-27 | AMENDMENT-002 (Derived Knowledge Principle) ratified | Founder ratification — GOAL-001 Phase 5 | Constitutional Analyst (INST-002) |
| 2026-07-27 | INST-014 (Engineering Intelligence — RepoNav) chartered — Stage W-2 | Founder ratification via AVD-001-v1.0 — GOAL-001 Phase 5 | Business Architect (INST-003) |

---

*This registry is a constitutional artifact. It is governed by WIOM §W-1 and GEOM §G-4. Changes require Founder ratification with a traceable Ratification ID.*
