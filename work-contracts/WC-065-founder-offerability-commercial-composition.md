# Work Contract 065 — Founder Offerability And Commercial Composition

**Program:** WC-064 — Founder Commercial Governance Program Design
**Iteration:** 1
**Successor scope:** Carries the offerability portion of WC-063 intent; WC-064 must still retain, relocate, defer, or reject every remaining WC-063 capability
**Status:** PLANNED IMPLEMENTATION CANDIDATE — DETAILED GROOMING GATED; IMPLEMENTATION UNAUTHORIZED
**Primary outcome owners:** Product Owner (INST-011) + Business Architect (INST-003)
**Required design owners:** INST-004, INST-005, INST-006, INST-007, INST-002
**Implementation office:** INST-010 only after a future complete implementation gate

## Outcome

Before an offering is published or hired, WAOOAW can determine whether an approved agent version,
skill and customer-goal envelope, providers and resources, advertising envelope, expected costs,
customer price, and included budgets form a commercially and constitutionally defensible offer.

Within approved policy, WAOOAW may adjust granular goals or resources and take a calculated,
documented risk while preserving the approved margin band and constitutional floors. The Founder
reviews policy performance and consequential exceptions rather than every granular decision.

## Objective And Success Measures

Deliver one governed offerability decision before publication or hiring. A successful Iteration 1
must prove that the Founder can:

- identify the approved professional, version, skills, customer-goal envelope, resources,
  providers, advertising envelope, price, included budgets, and policy version being assessed;
- distinguish authoritative WBE values from projections, assumptions, confidence, and unknowns;
- compare at least the baseline, minimum viable, and policy-bounded alternative scenarios;
- receive exactly one evidenced decision: `ALLOW`, `ALLOW_CALCULATED_RISK`, `REVISE`, `ESCALATE`,
  or `BLOCK`, with expiry and review conditions where applicable; and
- prevent publication or hiring when owner evidence is stale, unavailable, contradictory, below
  an approved constitutional or margin floor, or cannot be recorded before success.

## Candidate Capability Boundary

### Included

- compose an offering from approved agent, skill, goal, provider, resource, and WBE facts;
- model expected cost scenarios, customer price, included budgets, and planning margins without
  creating financial truth outside WBE;
- test minimum viable resource and Meta/Google advertising envelopes for the promised goal;
- simulate goal, resource, markup, trial-budget, and limited promotional adjustments;
- produce allow, calculated-risk allow, revise, escalate, or block-publication/hiring decisions;
- preserve evidence, policy version, confidence, assumptions, customer impact, and unresolved
  state for every decision; and
- retain Markup Designer and Trial Budget Configuration only as governed composition controls;
  retain the minimum coupon-impact behavior needed to test offerability.

### Excluded

- active-employment performance oversight, settled reconciliation operations, portfolio learning,
  helpdesk, customer-owned advertising accounts, new financial truth, direct WBE browser access,
  and autonomous changes outside approved policy.

## Design Questions Reserved For WC-064

- approved contribution-margin and fully loaded planning-margin bands;
- calculated-risk exposure limits by offering, cohort, customer, and period;
- minimum evidence and confidence required for a defensible envelope;
- which adjustments execute autonomously and which require Founder review;
- publication/hiring blocks and customer-facing disclosure language; and
- exact treatment of coupons that reduce price without weakening margin floors.

## First Grooming Package

### Required Inputs

| Input | Owner | Grooming proof |
|---|---|---|
| Hireable offering, customer outcome, and disclosure requirements | Product Owner + Business Architect | Approved offering and customer-value contribution |
| Approved agent versions, skills, Decision Space, and lifecycle status | Agent lifecycle owner | Read contract and stale/unavailable behavior |
| Price, trial, promotion, wallet, usage, tax, cost, and reconciliation facts | WBE | Authoritative read/simulation contract; no BP recomputation |
| Provider/resource feasibility and expected usage ingredients | AIR, CTG, provider owners, and PR | Bounded projections with source, freshness, and confidence |
| Umbrella policy and calculated-risk boundaries | Founder policy routed through Product, Business, Security, and Constitutional owners | Version, effective date, expiry, thresholds, and escalation rules |
| Founder authority and customer-impact controls | Security, Product, Data, Constitutional owners | Assurance, notice, choice, grandfathering, minimisation, and evidence rules |

### Decisions To Close During First Grooming

1. Define the canonical offerability input and result concepts without creating a second WBE or
  agent-lifecycle truth.
2. Assign each scenario ingredient to an authoritative read, governed projection, or explicit
  Founder assumption, including freshness and unavailable behavior.
3. Define how baseline, minimum viable, and alternative scenarios are compared and when a missing
  value blocks rather than defaults.
4. Specify policy-owned margin bands, calculated-risk exposure, confidence, expiry, review, and
  escalation semantics without hard-coding the numeric values in this routing contract.
5. Decide how trial budget, markup, and coupon impact are previewed, effective-dated, and disclosed
  while WBE retains validation and financial truth.
6. Define publication and hiring enforcement so a stale, blocked, expired, or unresolved decision
  cannot be presented or reused as permission.

### Grooming Deliverables

- Product acceptance matrix and Founder/customer language catalogue.
- Business offering-composition and policy semantics.
- Enterprise ownership, resilience, and iteration-boundary decision.
- Solution contracts for authoritative reads, scenario evaluation, policy decision, publication
  enforcement, evidence, conflict, and unavailable outcomes.
- Data contract for identities, lineage, versioning, effective dates, assumptions, projections,
  decision history, expiry, and evidence references, plus a migration or no-migration decision.
- Security and privacy contract covering Founder assurance, tenant isolation, CSRF/replay,
  idempotency, abuse, disclosure, and prohibited override paths.
- Constitutional readiness record and one integrated implementation traceability matrix.

## Acceptance Scenarios Required Before Implementation Authorization

| Scenario | Required result |
|---|---|
| Defensible baseline | Complete fresh inputs produce an evidenced decision and reconstructable scenario |
| Calculated-risk alternative | Approved policy permits the bounded risk, records assumptions/exposure/expiry, and schedules review |
| Constitutional or margin-floor breach | Decision is `BLOCK`; no Founder UI or downstream caller can override it |
| Stale, missing, or unavailable owner | State remains explicit and fails closed for publication/hiring |
| Concurrent policy or offering change | Stale preview cannot commit; conflict requires refresh and renewed confirmation |
| Customer-impacting prospective change | Notice, effective date, grandfathering, choice, and renewal treatment are visible |
| Evidence failure | No success or reusable authorization is returned |
| Cross-tenant or insufficient assurance | Request is denied without revealing the existence or economics of another tenant |

## Gated Implementation Work Packages

These packages become executable tasks only after the first grooming package names their approved
contracts and the complete implementation authorization chain closes.

| Candidate task | Component responsibility | Required behavior and proof |
|---|---|---|
| WC065-01 | Owner read adapters | Read approved agent/skill/goal/resource/provider and WBE facts with provenance, freshness, confidence, and explicit unavailable states |
| WC065-02 | Approved commercial simulation boundary | Implement or invoke the owner-approved WBE validation/simulation responsibility for price, budget, trial, promotion, cost, tax, and margin scenarios without persisting duplicate financial truth; grooming decides whether this is reuse or a WBE extension |
| WC065-03 | BP offerability orchestration | Assemble version-pinned inputs, request simulations and constitutional authorization, apply approved umbrella policy, and return one evidenced decision |
| WC065-04 | Publication and hiring guard | Require a current eligible decision; deny blocked, expired, stale, superseded, or unresolved decisions |
| WC065-05 | Founder decision experience | Present scenario comparison, assumptions, confidence, customer impact, policy basis, confirmation, conflict, and evidence reference through generated BP contracts |
| WC065-06 | Data and evidence persistence | Apply the approved append-only history and ownership design, or record the approved no-migration result; preserve idempotency and effective dating |
| WC065-07 | Verification and independent review | Run owner-contract, policy, financial, tenant, security, evidence-failure, generated-client, browser/accessibility, coverage, and regression checks; obtain independent review |

## Activation Gate

No detailed implementation tasks exist until WC-064 closes and WC064-07 produces an approved,
version-pinned WC-065 package with acceptance scenarios, owner contracts, Data and Security
decisions, integrated review, and Constitutional readiness. Implementation then still requires
fresh Founder confirmation, GO Authorization, later Acceptance, and independent review.

The activated contract must replace each candidate task above with exact approved specification
references, affected files/components, validation commands, acceptance IDs, and evidence outputs.