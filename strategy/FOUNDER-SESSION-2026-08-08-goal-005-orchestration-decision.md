# Founder Strategy Session — GOAL-005 Orchestration and Grooming Decision

**Date:** 2026-08-08
**Participants:** Yogesh Khandge (Founder, INST-001) + Enterprise Architect (INST-004)
**Session type:** Program operating-model decision
**Goal:** GOAL-005 — Agent Employment Experience Program
**Work Contract:** WC-053
**Status:** FOUNDER DECISION RECORDED — HANDOFF BLOCKED BY CB-001
**Continues from:** `strategy/FOUNDER-SESSION-2026-08-07-customer-first-decision.md`

## 1. Context

WC-051 separated professional-domain release gaps for Digital Marketing, Agricultural Advisor, Trading, and Private Tutor from capabilities that WAOOAW should build once and inherit across all professionals.

WC-052 then produced the GOAL-005 planning skeleton:

- an Architecture Readiness Gate;
- six customer-outcome epics, AE-01 through AE-06;
- 43 intentionally ungroomed story skeletons;
- a 16-clause Agent Employment Experience Contract skeleton; and
- a register of 37 shared WAOOAW product gaps with explicit closure gates.

The remaining decision was not what the program contains. It was how the institution should take that skeleton to implementation-grade detail without either designing all six waves speculatively or allowing individual sprints to invent shared architecture.

## 2. The Debate

### Option A — Groom the Entire Program to Work-Contract Detail Now

Bring all 43 stories to the level used for WC-038, WC-039, and WC-040 before any new implementation begins. EA, PO, and other offices would complete component ownership, acceptance criteria, CCTs, dependencies, and sprint decomposition across all six waves.

**Advantages**

- Maximum apparent predictability before implementation.
- Cross-wave dependencies can be considered together.
- Future sprint creation becomes largely mechanical.

**Risks**

- Later-wave detail would be based on assumptions rather than customer evidence.
- Multi-agent, ecosystem, and autonomous-organization designs could become stale before use.
- Large upfront grooming would delay the first customer outcome.
- The institution could mistake detailed documentation for validated product knowledge.

### Option B — Continue Wave Delivery and Track Gaps for Later Closure

Begin Wave 1 delivery from the skeleton and leave shared gaps in the register until a story needs them.

**Advantages**

- Fastest apparent movement toward implementation.
- Customer-facing work starts immediately.
- Detail is produced closer to use.

**Risks**

- Identity, lifecycle, contract, consent, and omnichannel decisions could be invented inside implementation.
- Shared behavior could become DMA-specific and require later migration.
- Gaps marked for later could remain open without an accountable closure route.
- This would violate the Architecture Readiness Gate and invert the constitutional chain.

### Option C — Goal-Orchestrated, Just-in-Time Institutional Grooming

Activate GOAL-005 through the Goal Orchestrator. INST-013 produces the Goal Understanding Record, Classification, participating-Institution routing, Evidence Specifications, Participation Windows, and Goal Execution Plan. Specialist offices contribute within their own Decision Spaces.

Shared foundations and the next customer outcome are groomed deeply. Later epics remain skeletons until evidence and entry gates justify focused grooming.

**Advantages**

- Preserves one program-level outcome and evidence chain.
- Keeps institutional responsibilities constitutionally separated.
- Produces detailed work only when it is decision-relevant.
- Prevents implementation from creating architecture.
- Allows customer evidence from each wave to refine later-wave understanding.

**Risks**

- Requires disciplined Goal Journey monitoring and explicit contribution records.
- The Goal Orchestrator must not become a substitute architect, Product Owner, or implementer.
- A weak Execution Plan could create handoff delays between offices.

## 3. Founder Decision

The Founder selected **Option C — Goal-Orchestrated, Just-in-Time Institutional Grooming**.

> GOAL-005 will be activated through the Goal Orchestrator for specification and grooming. The Goal Orchestrator coordinates the journey; PO, BA, EA, CA, Data, Security, Solution Architecture, and domain authorities contribute within their own Decision Spaces. This decision does not authorize implementation.

This is a sequencing decision, not a reduction in rigor. Work approaching implementation must reach the same specification quality demonstrated by WC-038, WC-039, and WC-040. The difference is that detail is produced in focused iterations, not speculatively across the full program.

## 4. Selected Operating Model

### 4.1 Goal Orchestrator Responsibility

INST-013 owns orchestration only:

- produce the Goal Understanding Record;
- classify scope, nature, risk, and urgency;
- select OPERATIONAL participating Institutions;
- define contribution sequence and dependencies;
- issue GO Authorizations after required reviews;
- define per-Institution Evidence Specifications and Participation Windows;
- monitor alignment with GOAL-005 success criteria;
- route capability gaps without silently resolving them; and
- assemble Goal evidence for validation and closure.

INST-013 may not contribute architecture, business capabilities, constitutional analysis, product priorities, implementation specifications, code, or tests to GOAL-005. If it contributed, it could no longer independently orchestrate the same Goal under GEOM G-13.

### 4.2 Specialist Institution Responsibility

| Institution | GOAL-005 contribution boundary |
|---|---|
| Business Architect | Confirm employment capabilities, customer outcomes, actors, and business vocabulary |
| Enterprise Architect | Derive AEEC structure, shared boundaries, cross-wave invariants, and required ADRs |
| Constitutional Analyst | Validate rights, consent, Human Override, evidence, constitutional traceability, and Goal records |
| Product Owner | Prioritize stories, define release candidates, and convert approved contributions into proposed Work Contracts |
| Data Architect | Define participant identity, relationship aggregate, lifecycle state, evidence correlation, and continuity data |
| Security Architect | Define participant verification, channel handoff, consent protection, tenant isolation, and threat controls |
| Solution Architect | Convert approved architecture into component, API, event, and failure contracts |
| Domain authority | Validate the professional instance; Sujay is required before DMA implementation grooming closes |
| Runtime Implementation Professional | Implement only from approved specifications, Work Contracts, and explicit implementation authorization |

No participating Institution owns GOAL-005. Each owns only its attested contribution. Evidence belongs to the Goal.

## 5. Grooming Depth Decision

| Scope | Required detail now | Reason |
|---|---|---|
| Architecture Readiness Gate | Full normative and conformance detail | Shared foundations are expensive to migrate after customer data exists |
| AE-01 — generic discover-to-hire journey, first proof DMA | Implementation-ready after foundation approval | It is the next customer outcome |
| AE-02 — real professional work, first instance DMA | Remain skeleton while Sujay workshop and AE-01 foundation work proceed; then groom | Domain depth must be expert-validated and consume the approved platform contract |
| AE-03→AE-06 | Remain outcome/story skeletons | Later-wave detail must incorporate evidence from preceding waves |
| Agent-domain registers | Groom only the gaps consumed by the selected wave | Prevents domain backlog expansion without release relevance |

An implementation-bound story must eventually reach WC-038→040 quality: customer outcome, constitutional basis, approved source specification, component ownership, interfaces, data and security impacts, failure behavior, CCT obligations, dependencies, and measurable completion evidence.

## 6. Initial GOAL-005 Specification Journey

The Goal Orchestrator must validate and may refine this draft sequence during G-2 through G-4. It is decision context, not a pre-issued Execution Plan.

| Draft deliverable | Expected contributing Institutions | Intended evidence |
|---|---|---|
| D-01 Employment Capability Confirmation | Business Architect + Product Owner | Confirmed generic capability and actor coverage for AE-01 |
| D-02 AEEC Foundation v1.0 | Enterprise Architect + Constitutional Analyst | Normative clauses for identity, rights, lifecycle, consent, trial, hire, evidence, and Human Override |
| D-03 Identity and Employment State Model | Enterprise Architect + Data Architect | Participant model, relationship aggregate, state transitions, idempotency, and evidence correlation |
| D-04 Omnichannel Continuity Contract | Enterprise Architect + Security Architect + Solution Architect | Authenticated channel handoff, channel-neutral state ownership, degradation, and conformance scenarios |
| D-05 Shared Gap Closure Plan | Product Owner + Enterprise Architect | Foundation gap sequence, ownership, acceptance evidence, and epic gates |
| D-06 AE-01 Release Grooming | Product Owner + required architecture offices | Proposed implementation-grade Work Contract set for AE-01 |
| D-07 Independent Validation and Ratification | Constitutional Analyst + Founder where required | Constitutional Clearance Record and explicit implementation decision boundary |

The Goal Orchestrator must not treat this table as authorization. It must first produce and review the Goal Understanding Record and Classification, then issue its own constitutional Execution Plan.

## 7. First Focused Iteration Recommendation

The first contribution package should resolve relationship identity and lifecycle before channel or feature grooming:

- AEEC-01 — Identity and participants
- AEEC-03 — Relationship states
- AEEC-07 — Contract formation
- PG-03 — Durable relationship and conversation identity
- PG-10 — Generic Employment Contract composition
- PG-11 — Employment lifecycle state and transition contract

Expected outputs are a participant model, employment relationship aggregate, valid transition table, consent and contract evidence rules, idempotency rules, and a WhatsApp-first trial-to-hire conformance scenario.

This recommendation is an input to Goal Understanding. INST-013 may reorder it only through an evidence-backed Goal Execution Plan.

## 8. Relationship to Existing Roadmaps

- The 2026-08-07 customer-first decision remains valid.
- Shared platform behavior and professional-domain behavior remain separate layers.
- DMA remains the first proof, not the boundary of the generic employment platform.
- AE-01→AE-06 remain customer-outcome epics, not Work Contracts.
- WC-044→048 remain reserved identifiers and are not automatically mapped to the six epics.
- One epic may require multiple specification, skeleton, implementation, and CCT Work Contracts.
- The four agent-domain gap registers remain separate grooming inputs.

## 9. Authorization Record

| Decision | Made by | Date | Effect |
|---|---|---|---|
| Use Goal Orchestrator for GOAL-005 | Yogesh Khandge, Founder (INST-001) | 2026-08-08 | INST-013 is selected to understand, classify, plan, route, and monitor the Goal |
| Use specialist Institutions for contributions | Yogesh Khandge, Founder (INST-001) | 2026-08-08 | GO coordinates; PO/BA/EA/CA and downstream offices contribute within Decision Space |
| Groom foundations and AE-01 deeply; retain later-wave skeletons | Yogesh Khandge, Founder (INST-001) | 2026-08-08 | Just-in-time detail with WC-038→040 quality at implementation entry |
| Specification and grooming only | Yogesh Khandge, Founder (INST-001) | 2026-08-08 | No `src/` work, implementation WC, sprint execution, or deployment is authorized |

## 10. Handoff

After this decision record is independently reviewed, the active office changes from Enterprise Architect (INST-004) to Goal Orchestrator (INST-013).

The Goal Orchestrator's first authorized action is to load its constitutional operating context and assess GOAL-005 readiness for G-2 Understanding. It must report `READY` or `BLOCKED` before producing the Goal Understanding Record.

**Handoff inputs:**

- `goals/GOAL-005-agent-employment-experience-program.md`
- `architecture/reference/product/agent-employment-experience-contract.md`
- `architecture/reference/product/waooaw-product-gap-register.md`
- `architecture/reference/agents/gaps/README.md`
- `strategy/FOUNDER-SESSION-2026-08-07-customer-first-decision.md`
- this decision record

---

*Decision recorded by Enterprise Architect (INST-004). The intended handoff to Goal Orchestrator (INST-013) is blocked by CB-001; the recorder does not participate as orchestrator.*

## 11. Post-Review Handoff Blocker

The INST-013 readiness check found a contradiction in `constitution/INSTITUTION-REGISTRY.md`: the Institution entry says `PROPOSED`, while the append-only change log says INST-013 was chartered and activated `OPERATIONAL` by Founder ratification on 2026-07-27.

CB-001 records the contradiction. The Founder decision in this document remains valid, but the office handoff cannot complete until the Constitutional Analyst reconciles the canonical registry. No GOAL-005 G-2 record may be produced before CB-001 closes.