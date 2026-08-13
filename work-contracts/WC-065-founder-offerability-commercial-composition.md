# Work Contract 065 — Founder Offerability And Commercial Composition

**Program:** WC-064 — Founder Commercial Governance Program Design
**Iteration:** 1
**Successor scope:** Carries the offerability portion of WC-063 intent; WC-064 must still retain, relocate, defer, or reject every remaining WC-063 capability
**Status:** IMPLEMENTATION-READY SPECIFICATION — PROTECTED DECISIONS AND IMPLEMENTATION AUTHORIZATION GATED
**Primary outcome owners:** Product Owner (INST-011) + Business Architect (INST-003)
**Required design owners:** INST-004, INST-005, INST-006, INST-007, INST-002
**Implementation office:** INST-010 only after a future complete implementation gate

## Specification Baseline

| Field | Value |
|---|---|
| Program design | `goals/GOAL-005-wc064-program-design.md` / GEP-GOAL-005-INST-013-14 |
| Execution controls | `goals/GOAL-005-wc064-execution-record.md` / ER-GOAL-005-INST-013-WC064-01 |
| Contribution Envelope | CE-GOAL-005-WC064-01 |
| Owner contributions | INST-011 CR-11; INST-003 CR-09; INST-004 CR-14; INST-005 CR-16; INST-006 CR-06; INST-007 CR-09; INST-010 CR-08; INST-002 CR-20 |
| Review state | Pending fresh integrated INST-004 and fresh Constitutional INST-002 verdicts on one hash-pinned package |
| Implementation state | UNAUTHORIZED; no task below is executable |

The baseline fixes behavior, ownership, dependencies, failure outcomes, data and evidence meaning,
security obligations, compatibility consequences, acceptance scenarios, and verification scope.
It intentionally does not choose protected policy values, physical schema names, endpoint names,
class names, or screen components. Those omissions do not grant implementation discretion: policy
values require their protected owner, and physical realization must trace to the approved owner
contracts during a separately authorized implementation plan.

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

## Implementation-Ready Work Packages

These packages are specification-complete but remain non-executable until every Activation Gate
item closes. Each package consumes the exact approved owner records above; an implementation
context may choose physical names only within the named component and behavior boundary and must
record that traceability before writing code.

| Work package | Component responsibility | Required behavior and proof |
|---|---|---|
| WC065-01 | Owner read adapters | Read approved agent/skill/goal/resource/provider and WBE facts with provenance, freshness, confidence, and explicit unavailable states |
| WC065-02 | Approved commercial simulation boundary | Implement or invoke the owner-approved WBE validation/simulation responsibility for price, budget, trial, promotion, cost, tax, and margin scenarios without persisting duplicate financial truth; grooming decides whether this is reuse or a WBE extension |
| WC065-03 | BP offerability orchestration | Assemble version-pinned inputs, request simulations and constitutional authorization, apply approved umbrella policy, and return one evidenced decision |
| WC065-04 | Publication and hiring guard | Require a current eligible decision; deny blocked, expired, stale, superseded, or unresolved decisions |
| WC065-05 | Founder decision experience | Present scenario comparison, assumptions, confidence, customer impact, policy basis, confirmation, conflict, and evidence reference through generated BP contracts |
| WC065-06 | Data and evidence persistence | Apply the approved append-only history and ownership design, or record the approved no-migration result; preserve idempotency and effective dating |
| WC065-07 | Verification and independent review | Run owner-contract, policy, financial, tenant, security, evidence-failure, generated-client, browser/accessibility, coverage, and regression checks; obtain independent review |

### Task-To-Owner-Contract Traceability

| Work package | Controlling decisions | Exact specification references |
|---|---|---|
| WC065-01 | Owner attribution, lifecycle eligibility, PR/AIR side-effect-free feasibility, stale/conflict/unavailable outcomes | Program Design Ownership Map; INST-004 CR-14 ownership/fail-closed model; INST-005 CR-16 authoritative-read and governed-projection contracts; INST-010 CR-08 IR-01, IR-05, IR-07, IR-08 |
| WC065-02 | WBE-only financial truth, canonical financial distinctions, governed category extension, blocked/drifting baseline prohibition | INST-003 CR-09 commercial-policy semantics; INST-005 CR-16 WBE boundary; INST-006 CR-06 financial catalogue; INST-010 CR-08 IR-02 through IR-04 and R-IR-04 through R-IR-06 |
| WC065-03 | One current disposition, proposal/preview/confirmation sequence, policy input, CE authorization and evidence | INST-011 CR-11 acceptance outcomes; INST-003 CR-09 disposition semantics; INST-004 CR-14 decision boundary; INST-005 CR-16 contract sequence; INST-002 CR-20 obligation matrix |
| WC065-04 | Current lifecycle and disposition eligibility across canonical and compatibility paths | INST-011 CR-11 product prohibition; INST-004 CR-14 independent-safety proof; INST-005 CR-16 publication/hiring enforcement; INST-007 CR-09 prohibited-path matrix; INST-010 CR-08 IR-06/R-IR-07 |
| WC065-05 | Founder isolation, version-pinned comparison, honest uncertainty, customer impact, generated BP-only experience | INST-011 CR-11 Founder/customer matrices; INST-005 CR-16 generated-contract categories; INST-007 CR-09 assurance/privacy/customer-rights model; INST-010 CR-08 IR-10 |
| WC065-06 | Additive BP-owned immutable minimum decision history, tenant isolation, effective dating, invalidation and evidence references | INST-006 CR-06 minimum record and additive migration decision; INST-007 CR-09 minimisation/retention/security boundaries; INST-010 CR-08 IR-11 and migration evidence; INST-002 CR-20 Evidence First/history conditions |
| WC065-07 | Complete test matrix, C-076 coverage, C-065 separation and independent implementation review | WC-064 First-Grooming Standard; INST-007 CR-09 threat/failure matrix; INST-010 CR-08 future test obligations; INST-002 CR-20 constitutional conditions |

### Affected Components And Approved Surfaces

| Component | Approved impact | Existing evidence surface |
|---|---|---|
| BP | Public orchestration, owner adapters, scenario/preview/confirmation/disposition, guard, immutable decision history and evidence correlation | `architecture/reference/api-specs/business-platform.openapi.yaml`; existing relationship, catalog, employment and activation orchestration surfaces identified by INST-010 CR-08 |
| WBE | Owner-qualified scenario validation for price, included budget, trial, promotion impact, cost category, tax, margin and reconciliation state | `architecture/reference/api-specs/wbe-relationship-workspace.openapi.yaml`; billing markup/trial/promotion and relationship projection surfaces identified by INST-010 CR-08 |
| PR | Side-effect-free professional resource/feasibility projection with provenance, confidence, validity and unavailable outcomes | `architecture/reference/api-specs/professional-runtime.openapi.yaml`; relationship projection surface identified by INST-010 CR-08 |
| AIR / CTG / provider registry | Side-effect-free provider/resource feasibility and expected-use evidence; no dispatch; CTG remains non-bypassable for later calls | Approved AIR, CTG and provider boundaries cited by INST-005 CR-16 and INST-010 CR-08 |
| Agent lifecycle | Version-pinned professional/skill/Decision Space eligibility and governed proposal outcomes | Catalog, skill, relationship and context-configuration surfaces identified by INST-010 CR-08 |
| CE | Existing constitutional authorization and evidence contracts where semantically sufficient; additive contract only after explicit compatibility decision | `architecture/reference/proto/constitutional_service.proto`; generic boundary evidence in INST-010 CR-08 IR-09 |
| Web generated consumer | Founder/customer experience generated only from BP public contracts; no private owner client | `web/scripts/generate-api.sh` and committed BP generated-client families identified by INST-010 CR-08 IR-10 |
| BP persistence | One additive tenant-isolated decision-history evolution; exact physical names assigned under the approved Data contract during implementation planning | INST-006 CR-06 Migration Decision; existing relationship/contract/activation history surfaces in INST-010 CR-08 IR-11 |

No existing source, migration, generated client, provider or deployment surface is authorized for
modification by this specification. The table defines ownership and future impact only.

### Read And Command Failure Contract

1. Every read returns owner, source/contract version, production or observation time, effective
   meaning, freshness, validity and explicit authoritative/projection/provisional/settled state.
2. Required stale, missing, superseded, contradictory, disputed, ineligible or unavailable inputs
   cannot default, inherit, reuse a cache as truth, or advance publication/hiring.
3. Proposal and preview are non-authorizing. Confirmation binds the exact actor, tenant, purpose,
   consequence, preview, policy and owner versions and expires on any material change.
4. Owner commands validate authority, expected versions and idempotency independently. Dispatch,
   queue acceptance, timeout, partial completion, pending and unknown outcome are not success.
5. CE authorization and durable evidence confirmation precede disposition reuse and every
   publication/hiring success. CE or evidence failure returns no success.
6. Idempotent replay returns the same authoritative terminal or unresolved outcome without
   repeating an owner mutation, provider call, disposition, publication, hiring or evidence event.

### Migration And Contract Decisions

- **Migration:** additive BP-owned persistence is required for the Data-owner minimum retained
  decision record. No WBE, lifecycle, execution, provider or constitutional truth is copied.
  Existing offerings receive no fabricated backfill permission and require fresh assessment.
- **Public contract:** an additive BP-generated contract family must express owner-attributed
  inputs, scenario comparison, assumptions, confidence, customer impact, preview/confirmation,
  disposition, validity, unresolved outcomes and evidence reference.
- **Compatibility:** omission must never mean allowed, current or evidenced. Existing publication
  and legacy hire paths must consume the same current guard, be narrowed to non-consequential
  evaluation, or be retired by an explicit Product/Solution compatibility decision.
- **Private contracts:** WBE, lifecycle, PR and AIR contracts require additive, owner-approved
  semantics where current relationship projections are partial. AIR feasibility is side-effect-
  free; provider execution is not simulation.
- **Generated consumers:** every approved public BP change regenerates committed consumers and
  proves compatibility. Browsers never import private WBE/PR/AIR/CTG/CE/provider contracts.
- **CE/CTG:** reuse existing generic boundaries when the approved action/evidence meaning fits.
  Any extension requires explicit owner compatibility approval; this specification assumes no
  new RPC or provider activation.

### Acceptance IDs And Verification Obligations

| ID | Acceptance obligation | Future verification evidence |
|---|---|---|
| AS-065-01 | Defensible baseline produces one reconstructable current disposition | Unit/property checks; owner-contract and integration evidence; immutable-history reconstruction |
| AS-065-02 | Policy-bounded calculated risk preserves assumptions, exposure, customer impact, expiry and review above every floor | Policy-boundary, floor, expiry, concentration and customer-disclosure checks |
| AS-065-03 | Constitutional or commercial-floor breach is `BLOCK` with no override | CE/CCT, WBE floor, Founder-role, compatibility-path and prohibited-fallback checks |
| AS-065-04 | Stale, missing, contradictory, ineligible or unavailable owner state fails closed | Contract variants, cache invalidation, owner outage and explicit-unresolved integration checks |
| AS-065-05 | Concurrent policy/offering/owner change invalidates preview and confirmation | Version-conflict, refreshed impact, renewed assurance and idempotency checks |
| AS-065-06 | Prospective customer-impacting change preserves notice, effective date, review, choice, continuity and remedy | Data effective-dating, Product language, Security privacy and customer-rights checks |
| AS-065-07 | Evidence failure returns no success or reusable permission | CE unavailable/deny, evidence-write/correlation failure and recovery checks |
| AS-065-08 | Cross-tenant or insufficient assurance denies without disclosure | RLS/FORCE RLS, authorization-before-disclosure, non-enumeration and privacy-safe error checks |
| AS-065-09 | Canonical and compatibility publication/hiring paths cannot bypass the guard | Public contract, legacy adapter, activation and generated-client regression checks |
| AS-065-10 | Category extension preserves owner, unit, attribution, reconciliation and Evidence First | Provider/resource/cost/charging-unit contract and property checks |

Future implementation validation must use the repository's constitutionally required execution
environment. Python checks run through `docker compose run --rm test-runner`; .NET checks use the
approved devcontainer SDK. The activated implementation plan must name exact scoped commands and
must include unit, property, owner-contract, integration, migration, constitutional, security,
data, generated-client, browser/accessibility and regression evidence with at least 90 percent
affected-surface line coverage. No test is executed by this specification sprint.

## Protected Decision Register

| Decision | Owner | Current state | Activation effect |
|---|---|---|---|
| Margin and planning position | Founder policy authority with WBE/Business inputs | SATISFIED by FA-047 | Publish only with non-negative direct contribution; track fully loaded margin without a launch floor until review evidence exists |
| Calculated-risk exposure and concentration | Founder policy authority | SATISFIED by FA-047 | Disabled for lean launch; no `ALLOW_CALCULATED_RISK` disposition |
| Minimum evidence/confidence | Founder policy authority with Product/Data/Security/Constitutional inputs | SATISFIED by FA-047 | Current authoritative owner evidence required; missing or conflicting facts block |
| Delegated adjustments and Founder-reserved exceptions | Founder policy authority | SATISFIED by FA-047 | Routine adjustments inside approved price and policy are delegated; price, floors, exceptions, and customer harm remain Founder-reserved |
| Validity, expiry, review cadence and escalation | Founder policy authority | SATISFIED by FA-047 | Input or policy change invalidates; review after first 10 paid hires or 30 days, whichever occurs first |
| Consequence and assurance class | Founder policy authority with Security/Constitutional inputs | SATISFIED by FA-047 | Normal assurance for drafts; fresh explicit confirmation for publish, hire, policy change, or customer impact |
| Grandfathering, remedy, legal, disclosure, erasure, and retention treatment | Founder direction with existing approved Privacy, Refund, and Grievance Policies | SATISFIED by FA-046 reuse baseline | Existing industry-standard policy applies; only a concrete material exception requires scoped review before activation |

These decisions are preserved, not delegated to INST-013 or implementation. They do not justify
detailed grooming of WC-066 through WC-069.

## Activation Gate

No implementation task is executable until:

1. The exact WC-064/WC-065 package is hash-pinned and receives fresh integrated INST-004 approval
  plus fresh INST-002 Constitutional readiness approval.
2. Every protected decision required for the activated policy and implementation package is
  recorded by its owner. Existing approved policy may be reused when no material change is
  introduced; silence may not create a new exception or weaken an existing customer protection.
3. The Registrant acknowledges the reviewed implementation specification.
4. The Founder explicitly confirms WC-065 implementation for that later session.
5. INST-013 issues an implementation GOA and INST-010 records a temporally later Acceptance.
6. The implementation Work Contract binds exact physical artifacts and scoped validation commands
  to the approved behavior, owner-contract, Data and Security specifications above.
7. Independent implementation review remains separate from execution under C-065.

Until all seven items close, this is an implementation-ready specification and nothing more.
WC-066 through WC-069 remain outcome-and-boundary records gated by real earlier-iteration evidence.