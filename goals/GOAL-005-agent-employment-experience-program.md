# GOAL-005 — Agent Employment Experience Program

**Status:** REGISTERED — GO HANDOFF BLOCKED BY CB-001; NO IMPLEMENTATION AUTHORIZATION
**Registrant:** Yogesh Khandge (Founder)
**Registered:** 2026-08-08
**Work Contract:** WC-052
**Owning outcome:** A customer can discover, hire, work with, govern, and expand a relationship with WAOOAW professionals through one continuous constitutional experience.
**Constitutional basis:** C-001, C-002, C-009, C-030, C-034, C-037, C-039, C-070, C-094

> This document is a planning skeleton. Story order is directional. Story details, acceptance criteria, estimates, component tasks, and sprint assignments require focused grooming and explicit authorization.

## 1. Program Intent

WAOOAW will deliver an Agent Employment SaaS experience rather than a collection of unrelated agent tools. WhatsApp, web, and mobile are channels into one durable customer-agent relationship. Shared employment capabilities are built once and inherited; each professional remains genuinely specialized through its domain specification and domain gap register.

## 2. Program Outcomes

| ID | Outcome | Program proof |
|---|---|---|
| GO5-O1 | A customer can evaluate and hire any supported professional with informed consent | One generic discover-to-hire journey proven first with DMA, with rights and Decision Space visible |
| GO5-O2 | A hired professional performs real domain work under constitutional control | Customer-observable execution, evidence, billing, and Human Override |
| GO5-O3 | The relationship continues across channels and time | One conversation and employment state survive channel and session changes |
| GO5-O4 | A customer can employ multiple professionals without losing boundaries | Per-agent authority, budget, evidence, and lifecycle remain independently governable |
| GO5-O5 | Agents and skills evolve without contract drift | Versioned contracts and compatibility evidence govern every extension |
| GO5-O6 | An organization can delegate outcomes while retaining ultimate control | Cross-agent orchestration remains bounded by customer authority and Emergency Stop |

## 3. Architecture Readiness Gate — Before Wave 1 Implementation

This is a specification gate, not an implementation wave.

| Gate item | Required decision | Closure evidence |
|---|---|---|
| ARG-01 | Agent Employment Experience Contract v1.0 ratified | Approved contract with invariant identifiers, states, rights, and transitions |
| ARG-02 | Shared product gaps classified | Every gap has an owner, blocking class, earliest wave, and closure evidence |
| ARG-03 | Identity and participant semantics locked | Customer, tenant, participant, agent, skill, employment, and channel identities do not conflict |
| ARG-04 | Employment and conversation continuity semantics locked | Lifecycle and cross-channel state ownership are versioned and testable |
| ARG-05 | Existing standards reconciled | Agent Employment Experience Contract, ADR-035 PAC, and Agent Base Spec boundaries remain explicit and non-overlapping |
| ARG-06 | Wave skeleton ratified | Each epic is a customer outcome and each story has a later grooming route |

## 4. Delivery Rules

1. One wave equals one customer-outcome epic.
2. A story is not sprint-ready until its focused grooming iteration supplies acceptance criteria, evidence, risks, and component decomposition.
3. A `FOUNDATION_BLOCKER` closes before Wave 1 implementation begins.
4. A `WAVE_BLOCKER` closes before its assigned epic can be accepted.
5. Shared capabilities are implemented once through the earliest vertical story that needs them.
6. Agent-domain gaps remain in the four domain registers and enter a wave only through grooming.
7. No epic closes on repository evidence alone when its outcome requires customer proof.

## 5. Founder Precedence and Reserved Sprint Reconciliation

The 2026-08-07 Founder decisions remain controlling:

- Customer-journey outcomes take precedence over a horizontal pillar-first implementation program.
- Shared platform behavior and professional-domain behavior remain separate ownership layers.
- DPDPA protection, customer evidence, and constitutional rights are embedded in the first applicable customer journey, not deferred as optional pillars.
- DMA depth requires focused review with Sujay before DMA implementation stories are groomed.

WC-044→048 remain reserved identifiers only. They are not automatically mapped one-to-one onto AE-01→AE-06. Product Owner grooming must determine whether an epic requires one or more Work Contracts, preserve dependencies, and obtain the required authorization. This skeleton therefore refactors customer outcomes without creating, renaming, or authorizing those sprints.

## 6. Epic Register

| Epic | Wave | Customer outcome | Entry dependency | Exit proof |
|---|---|---|---|---|
| AE-01 | 1 | Discover, interview, trial, configure, and hire a professional; first proof is DMA | Architecture Readiness Gate | One customer completes the generic governed journey with DMA through a supported channel |
| AE-02 | 2 | A professional performs real domain work; first instance is DMA marketing | AE-01 + groomed DMA P0 domain gaps | Real DMA campaign work proves the generic execution relationship and produces customer-visible evidence |
| AE-03 | 3 | Continuous agent relationship workplace | AE-02 | Customer continues work across channels, sessions, billing events, and lifecycle changes |
| AE-04 | 4 | Multi-agent employment | AE-03 + second agent release gate | Customer governs at least two professionals with independent boundaries |
| AE-05 | 5 | Governed agent and skill ecosystem | AE-04 | Versioned agent/skill changes occur without employment-contract drift |
| AE-06 | 6 | Autonomous organization | AE-05 | Organization delegates outcomes across agents while retaining constitutional control |

## 7. AE-01 — Discover, Interview, Trial, Configure, and Hire a Professional

**Epic status:** SKELETON — NOT GROOMED
**First proof:** Digital Marketing Agent. The journey semantics remain valid for Agricultural Advisor, Trading, Private Tutor, and future professionals.

| Story | Thin customer story | Shared gap dependencies | Domain dependency |
|---|---|---|---|
| AE-01-S01 | As a prospect, I can discover a suitable professional in conversation and understand whom it serves | PG-01, PG-03 | DMA positioning and eligibility for first proof |
| AE-01-S02 | As a prospect, I can inspect the professional's skills, limitations, authority, rights, and indicative cost before commitment | PG-02, PG-04, PG-09 | DMA capability and limitation disclosures for first proof |
| AE-01-S03 | As a prospect, I can interview the professional using my situation and receive evidence-backed answers | PG-05, PG-06 | DMA interview scenarios and domain vocabulary for first proof |
| AE-01-S04 | As a prospect, I can provide essential business context conversationally without technical configuration | PG-06, PG-07 | DMA customer profile minimum |
| AE-01-S05 | As a prospect, I can enter a clearly disclosed demonstration or trial relationship | PG-08, PG-09, PG-13 | DMA trial-safe capability set |
| AE-01-S06 | As a customer, I can define goals, budget, skills, review cadence, and Decision Space in business language | PG-07, PG-10 | DMA goal and authority vocabulary |
| AE-01-S07 | As a customer, I can review and accept an Employment Contract containing my rights and agreed boundaries | PG-02, PG-10, PG-11 | DMA contract schedule |
| AE-01-S08 | As a customer, I can make the onboarding payment and see the relationship become Active exactly once | PG-09, PG-11, PG-12 | DMA billing profile |
| AE-01-S09 | As a customer, I can continue the same relationship on another supported channel | PG-03, PG-14 | None |
| AE-01-S10 | As a customer, I can see evidence and reach Emergency Stop from the first trial interaction | PG-04, PG-15 | DMA evidence vocabulary |

## 8. AE-02 — A Professional Performs Real Domain Work

**Epic status:** SKELETON — NOT GROOMED
**First instance:** DMA marketing execution. These stories are the first domain vertical and do not relocate DMA-specific behavior into the shared platform layer.

| Story | Thin customer story | Shared gap dependencies | Domain dependency |
|---|---|---|---|
| AE-02-S01 | As a customer, I can connect required marketing providers without exposing credentials to the agent | PG-16 | DMA provider verification and scopes |
| AE-02-S02 | As a customer, I receive a domain-aware profile, market assessment, and maturity baseline | PG-17, PG-18 | DMA DVE and profiling proof |
| AE-02-S03 | As a customer, I can agree a campaign brief that governs downstream work | PG-18, PG-19 | DMA campaign coherence rules |
| AE-02-S04 | As a customer, I can review and decide proposed creative actions at the appropriate authority boundary | PG-19, PG-20 | DMA content and channel rules |
| AE-02-S05 | As a customer, I can observe approved work being published through connected providers | PG-16, PG-20, PG-21 | DMA end-to-end execution proof |
| AE-02-S06 | As a customer, I can authorize paid promotion within an explicit spend ceiling | PG-12, PG-20, PG-22 | DMA ad-wallet and reconciliation gaps |
| AE-02-S07 | As a customer, I can see enquiries, bookings, and campaign outcomes traced to work and spend | PG-21, PG-23 | DMA attribution and analytics gaps |
| AE-02-S08 | As a customer, I am told clearly when provider, budget, or capability limits change what DMA can do | PG-13, PG-16, PG-24 | DMA domain degradation rules |

## 9. AE-03 — Continuous Agent Relationship Workplace

**Epic status:** SKELETON — NOT GROOMED

| Story | Thin customer story | Shared gap dependencies | Domain dependency |
|---|---|---|---|
| AE-03-S01 | As a customer, I can resume the same conversation with context intact across channels and sessions | PG-03, PG-14 | None |
| AE-03-S02 | As a customer, I can see current work, proposals, approvals, alerts, and outcomes in one relationship view | PG-15, PG-20, PG-21 | Agent-specific presentation extensions |
| AE-03-S03 | As a customer, I receive material alerts in the right channel without duplicate or conflicting messages | PG-14, PG-24 | Agent-specific urgency vocabulary |
| AE-03-S04 | As a customer, I can understand usage, invoices, wallet state, and renewal consequences in business terms | PG-12, PG-13 | Agent billing profile vocabulary |
| AE-03-S05 | As a customer, I can review performance against the business outcomes I hired the agent to achieve | PG-23, PG-25 | Agent outcome model |
| AE-03-S06 | As a customer, I can amend, pause, resume, renew, or terminate employment without losing evidence | PG-11, PG-26 | Agent-specific amendment impacts |
| AE-03-S07 | As a customer, I receive a periodic evidence-backed business review and agreed next actions | PG-23, PG-25 | Agent MBR content |

## 10. AE-04 — Multi-Agent Employment

**Epic status:** SKELETON — NOT GROOMED

| Story | Thin customer story | Shared gap dependencies | Domain dependency |
|---|---|---|---|
| AE-04-S01 | As a customer, I can discover and hire a second professional through the same employment experience | PG-01, PG-02, PG-05 | Selected agent P0 release gaps |
| AE-04-S02 | As a customer, I can see all employed professionals without merging their authority, budget, or evidence | PG-27, PG-28 | Per-agent domain boundaries |
| AE-04-S03 | As a customer, I can govern each professional and skill independently | PG-26, PG-27 | Agent-specific skill lifecycle |
| AE-04-S04 | As a customer, I can authorize bounded information handoffs between professionals | PG-28, PG-29 | Domain confidentiality constraints |
| AE-04-S05 | As a customer, I can review combined business outcomes without obscuring individual accountability | PG-23, PG-27, PG-30 | Cross-domain outcome definitions |
| AE-04-S06 | As a customer, I can stop one professional or all professionals with unambiguous scope | PG-04, PG-27 | Agent-specific halt consequences |

## 11. AE-05 — Governed Agent and Skill Ecosystem

**Epic status:** SKELETON — NOT GROOMED

| Story | Thin customer story | Shared gap dependencies | Domain dependency |
|---|---|---|---|
| AE-05-S01 | As a customer, I can compare compatible agents and skills using consistent rights and outcome information | PG-01, PG-02, PG-31 | Domain catalogue content |
| AE-05-S02 | As a customer, I can add or remove a skill through a governed Employment Contract amendment | PG-26, PG-31, PG-32 | Skill-specific contract effects |
| AE-05-S03 | As a customer, I am protected when an agent or skill version changes during employment | PG-32, PG-33 | Domain compatibility declaration |
| AE-05-S04 | As WAOOAW, I can detect agent contracts that lag required platform signals or base behavior | PG-33, PG-34 | Agent PAC compliance |
| AE-05-S05 | As a steward, I can govern publication, suspension, and retirement of agents and skills | PG-31, PG-32, PG-34 | Domain review evidence |
| AE-05-S06 | As a customer, I can connect ecosystem providers under the same credential and constitutional controls | PG-16, PG-35 | Provider-specific domain scopes |

## 12. AE-06 — Autonomous Organization

**Epic status:** SKELETON — NOT GROOMED

| Story | Thin customer story | Shared gap dependencies | Domain dependency |
|---|---|---|---|
| AE-06-S01 | As an organization, I can express a business outcome and receive a proposed multi-agent plan | PG-29, PG-30, PG-36 | Participating domain capabilities |
| AE-06-S02 | As an organization, I can approve authority, budget, dependencies, and stop conditions before execution | PG-27, PG-28, PG-36 | Domain Decision Consequence Maps |
| AE-06-S03 | As an organization, I can let agents coordinate only through authorized, evidenced handoffs | PG-28, PG-29, PG-37 | Domain handoff constraints |
| AE-06-S04 | As an organization, I can monitor progress, conflicts, spend, and business outcomes across the plan | PG-23, PG-30, PG-37 | Cross-domain outcome attribution |
| AE-06-S05 | As an organization, I can intervene, amend, or stop the plan at any level | PG-04, PG-26, PG-36 | Domain halt and amendment effects |
| AE-06-S06 | As WAOOAW, I can improve orchestration from evidence without silently expanding authority | PG-25, PG-32, PG-37 | Domain learning boundaries |

## 13. Focused Grooming Sequence

Each iteration selects one story or tightly coupled story group and produces:

1. Customer scenario and measurable outcome.
2. Constitutional and legal obligations.
3. Happy path, alternate paths, and failure/degradation behavior.
4. Acceptance criteria and customer-proof method.
5. Shared product gaps and agent-domain gaps consumed or discovered.
6. Owning components, contracts, data, security, and operational dependencies.
7. CCT and non-constitutional test obligations.
8. Estimate, sprint placement, and explicit Founder authorization where required.

## 14. Related Planning Inputs

- `architecture/reference/product/agent-employment-experience-contract.md`
- `architecture/reference/product/waooaw-product-gap-register.md`
- `architecture/reference/agents/gaps/README.md`
- `strategy/FOUNDER-SESSION-2026-08-07-customer-first-decision.md`
- `adr/ADR-035-platform-agent-contract-standard.md`
- `architecture/reference/agents/AGENT-BASE-SPEC.md`
