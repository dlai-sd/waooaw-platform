# D-06 — AE-01 Release Grooming and Simulation Package

**Primary Institution:** INST-011 — Product Owner
**Authorization:** GOA-GOAL-005-INST-011-04
**Status:** ACCEPTED — R-041 through R-045 CLEAR; ready for D-07
**Release:** AE-01 — Discover, Interview, Trial, Configure, and Hire a Professional
**First proof:** WhatsApp-first Digital Marketing Agent
**Implementation authority:** NONE

## Institutional Record

| Field | Value |
|---|---|
| `institution_id` | INST-011 |
| `goal_id` | GOAL-005 |
| `record_id` | CR-GOAL-005-INST-011-04 |
| `record_type` | Contribution Record |
| `produced_at` | 2026-08-08T12:40:00+00:00 |
| `authorization_id` | GOA-GOAL-005-INST-011-04 |

Acceptance `ACC-GOAL-005-INST-011-04` was recorded at 2026-08-08T12:39:59+00:00. Learning Record `LR-GOAL-005-INST-011-04` records `constitutional_discovery: no`, `evolution_triggered: no`, and the improvement signal that grooming must inspect implemented foundations before proposing new work.

## Release Outcome

A prospect can enter through WhatsApp or web, discover and evaluate a suitable WAOOAW professional, provide progressive business context, complete a disclosed 14-calendar-day trial, configure goals and authority, accept one Employment Contract, pay once, activate one durable Employment Relationship, continue it through another authenticated channel, inspect evidence, and exercise Emergency Stop.

The product boundary remains generic. DMA supplies vocabulary, examples, and the first simulation only.

## Existing Foundations Reused

| Foundation | Existing evidence | D-06 treatment |
|---|---|---|
| Trial allocation, expiry, quota, and conversion | WC-031 and WC-033 | Integrate and correct policy behavior; do not rebuild |
| Trial LOCAL inference routing | WC-032 | Reuse; prove zero paid API calls |
| Onboarding payment, webhook, and renewal | WC-042 | Reuse for activation choreography |
| WBE reconciliation and billing CCTs | WC-043 | Reuse for exactly-once financial proof |
| Audit Sink and payload erasure | WC-037 | Reuse for evidence integrity and DPDPA separation |
| OAuth vault and Constitutional Tool Gateway | WC-038 and WC-039 | Reuse for later provider access; trial grants none |
| Skill Catalog and Skill Runtime | WC-040 and WC-041 | Reuse for pinned skill disclosure/configuration |
| PAAS workflow and Emergency Stop | WC-014 and WC-012 | Reuse and connect to relationship/channel scope |
| WhatsApp phone identity | ADR-023 | Reuse with risk-tier step-up authentication |

Historical WC-031 through WC-034 text is not controlling where it conflicts with D-02 through D-06. In particular: no three-session expiry, no automatic conversion, no Python Business Platform assumption, no paid trial API, and no claim that a static HTML file completes the AE-01 customer interface.

## Component Decomposition

| Work Contract | Customer slice | Primary components | Depends on |
|---|---|---|---|
| WC-057 | Durable Employment Relationship and customer journey foundation | BP, PostgreSQL, web shell, reference contracts | WC-037, WC-040, D-06/D-07 ratification |
| WC-058 | S01–S06 discover, inspect, interview, context, trial, configure | BP, PR, AIR, WBE, web, WhatsApp identity | WC-057; WC-031–033, WC-040–041 |
| WC-059 | S07–S08 contract, payment, exactly-once activation | BP, WBE, CE, web, PR channel presentation | WC-058; WC-042–043 |
| WC-060 | S09–S10 continuity, Evidence Window, Emergency Stop | BP, PR, CE, web, WhatsApp identity | WC-059; WC-014, WC-037, D-04 |

The four contracts are customer-outcome slices, not horizontal service projects. Each contract may touch multiple components only through their approved ownership boundaries.

## Normative Specialist Contracts

| Institution | D-06 contribution | Decision surface closed |
|---|---|---|
| INST-003 Business Architect | `architecture/reference/product/ae01-business-boundary-contract.md` | Generic employment vs. DMA adapter, wave and billing-language boundaries |
| INST-005 Solution Architect | `architecture/reference/product/ae01-solution-contract.md` | Component ownership, APIs/compatibility, PAAS workflow, continuity envelope, activation, web |
| INST-006 Data Architect | `architecture/reference/product/ae01-relationship-data-contract.md` | First mint, participant roles, migrations 19–22, RLS, retention, replay, evidence retrieval |
| INST-007 Security Architect | `architecture/reference/product/ae01-security-contract.md` | Assurance tiers, consent, takeover, Stop release, Evidence Reader, injection controls |

R-038 is published at `reviews/R-038-goal-005-D04-gate-review.md`; its out-of-order, takeover, replay, confused-deputy, downgrade, cross-tenant, and trial-policy conditions are carried into these contracts and the adversarial matrix. ADR-044 exists at `adr/ADR-044-constitutional-audit-trail-sink.md` and is a normative evidence/payload dependency.

## AE-01 Checkpoint Matrix

| Story | Deterministic customer proof | Work Contract | Pass condition |
|---|---|---|---|
| S01 | State a business need and receive suitable lawful professionals with reasons | WC-058 | DMA first proof selected without preferred-customer filtering |
| S02 | Inspect skills, limitations, authority, rights, evidence posture, trial mode, and indicative cost | WC-058 | All disclosures precede trial entry |
| S03 | Ask serious-buyer questions and receive sourced, bounded answers | WC-058 | Fact, inference, recommendation, and limitation are distinguishable |
| S04 | Begin with name, location, and business nature and progressively enrich context | WC-058 | One decision-relevant question per cycle; confirmed context persists |
| S05 | Complete 14-day all-skill demonstration | WC-058 | Zero paid API calls and zero consequential external actions |
| S06 | Configure goals, measures, skills, budget, review cadence, Decision Space, and stop conditions | WC-058 | Each item can be accepted, edited, rejected, or deferred independently |
| S07 | Review common AEEC terms plus domain schedule and explicitly accept | WC-059 | Immutable accepted version and authority evidence exist |
| S08 | Pay and activate | WC-059 | One charge and one `ACTIVE` transition for the D-03 tuple under replay |
| S09 | Continue the same relationship through another authenticated channel | WC-060 | Relationship, context, contract, authority, and billing state remain unchanged |
| S10 | Inspect evidence and exercise Emergency Stop | WC-060 | Evidence available from first trial interaction; stop applies across channels |

## WhatsApp-First DMA Simulation

### Scenario

An authorized customer says: “I am Dr. Mehta, a dentist in Viman Nagar, Pune.” The system creates or reuses one tenant-scoped Employment Relationship, discloses rights and limits, demonstrates DMA expertise before asking another question, and runs the 14-day zero-paid-API trial plan from the approved domain synthesis.

### Result

| Check | Result | Evidence method |
|---|---|---|
| AE-01 S01–S10 | PASS 10/10 | Checkpoint matrix and scripted state/evidence assertions |
| Trial entitlement | PASS | Day 1 through Day 14 plan; no session-count truncation |
| Paid provider use | PASS | Trial mode routes only `llm_local`; generated/provider outputs use approved substitutions |
| Consequential trial action | PASS | Publish, spend, third-party message, credential use, and provider mutation denied |
| Context continuity | PASS | Confirmed minimum profile reused after authenticated WhatsApp-to-web handoff |
| Contract ordering | PASS | Configuration → presentation → explicit acceptance → payment → activation |
| Activation replay | PASS | Same four-part tuple returns prior outcome; no duplicate relationship or charge |
| Evidence and stop | PASS | Evidence starts at trial entry; stop is channel-independent and customer-releasable only |

This is specification simulation evidence. It is not executable implementation proof or customer proof.

## Adversarial and Ordering Simulation

| Scenario | Expected result | Result |
|---|---|---|
| Duplicate first-contact admission | Reuse relationship; no duplicate mint | PASS |
| Out-of-order payment before acceptance | Reject; remain pre-active; evidence reason | PASS |
| Direct `TRIAL_ACTIVE` to `ACTIVE` | Reject illegal transition | PASS |
| Identical activation replay | Return prior activation and charge outcome | PASS |
| Divergent activation under same intent | Explicit conflict; zero mutation | PASS |
| WhatsApp account takeover attempt | Tier-4 portal for contract/payment/Stop release; deny on failure | PASS |
| Confused deputy | Participant role and relationship authority mismatch denied | PASS |
| Assurance downgrade | Reduce capability; never weaken protection | PASS |
| Cross-tenant relationship/evidence request | Deny with zero data disclosure | PASS |
| Stop-release by reconnect, timeout, or operator | Deny; only freshly authenticated same-tenant `EMPLOYER` portal release may resume | PASS |
| Trial inactivity and expiry | No conversion; expire entitlement; preserve evidence/artifacts/rights | PASS |
| Reminder replay or repeated solicitation | Deduplicate; one bounded informational reminder | PASS |

## Gap Closure Evidence

PG-01 through PG-15 have a customer scenario, deterministic acceptance condition, Work Contract owner, and proof route in the checkpoint matrix and WC-057 through WC-060. Foundation gaps remain specification-closed; they become implementation-closed only after the relevant CCTs and end-to-end acceptance pass. No gap is closed by repository prose alone.

## Release Risks and Controls

| Risk | Control |
|---|---|
| Existing BP endpoints return placeholders rather than durable records | WC-057 replaces placeholders behind versioned contracts and RLS-backed persistence |
| Existing trial expiry activity treats unknown status as lapse | WC-058 requires unresolved state on uncertainty and no fail-open conversion/lapse mutation |
| Existing trial conversion updates state before guaranteed paid activation | WC-059 requires one atomic/idempotent choreography with compensating unresolved state |
| Web scaffold evidence does not match current static artifact | WC-057 establishes the actual Next.js customer journey shell before dependent UI |
| Phone identity is insufficient for high-risk actions | WC-059/WC-060 require ADR-023 risk-tier step-up authentication |
| Evidence query may expose another tenant or raw sensitive payload | WC-060 uses BP tenant-scoped Evidence Reader and payload references, not direct ledger access |
| Generic journey becomes coupled to DMA | Shared code consumes Professional Evaluation Adapter; DMA owns its 19-skill adapter; non-DMA fixture proves conformance |
| Billing `CONVERTED` is mistaken for relationship lifecycle | It remains a WBE billing projection emitted only from successful paid activation; D-03 states are unchanged |

## D-06 Exit Criteria

1. Product, Business, Enterprise, Solution, Data, and Security reviews are CLEAR.
2. WC-057 through WC-060 meet the WC-038 through WC-040 quality benchmark.
3. All fifteen Wave 1 gaps map to deterministic implementation and acceptance evidence.
4. Simulation passes S01 through S10, ordering, replay, takeover, confused-deputy, downgrade, and cross-tenant cases.
5. No unresolved architecture decision is delegated to implementation.
6. D-07 independently validates the package before any implementation decision.

## Learning Record

`improvement_signal`: Canonical sprint status and implemented source must be checked before grooming; historical pending Work Contracts may already be complete and must not be duplicated.

`constitutional_discovery`: no

`evolution_triggered`: no

## Acceptance

R-041 (Business), R-042 (Enterprise Architecture), R-043 (Solution), R-044 (Data), and R-045 (Security) independently returned **CLEAR** with zero conditions after remediation. D-06 is accepted as specification-complete. WC-057 through WC-060 are implementation-ready candidates and remain explicitly unauthorized pending D-07 ratification and a separate Founder implementation directive.