# Work Contract 063 — WC-034 F7 Founder Administration

**Goal:** GOAL-005 — Agent Employment Experience Program
**Parent:** WC-034 F7 — Founder Administration
**Track:** Governed platform administration
**Grooming Office:** Goal Orchestrator (INST-013)
**Implementation Office:** Platform IT Expert (INST-010)
**Required specification owners:** Product Owner (INST-011), Solution Architect (INST-005), Data Architect (INST-006), Security Architect (INST-007)
**Integrated architecture reviewer:** Enterprise Architect (INST-004)
**Readiness reviewer:** Constitutional Analyst (INST-002)
**Status:** SUPERSEDED — replaced prospectively by WC-064 through WC-069; never implementation-authorized
**Constitutional basis:** C-007, C-023, C-043, C-048, C-051, C-056, C-059, C-064, C-065, C-076, C-080, C-088, C-089, C-090, C-091; ADR-002, ADR-003, ADR-008, ADR-022, ADR-034

## Supersession Notice

Founder-sponsored discovery on 2026-08-12 determined that this contract organized delivery
around three administration surfaces rather than the institutional decision outcome the Founder
needs. WC-064 now owns the cross-iteration Founder Commercial Governance program design.
WC-065 through WC-069 are its gated implementation-iteration candidates.

Markup Designer, Trial Budget Configuration, and Coupon Manager are not discarded as business
capabilities. Their valid behavior is reconsidered inside the program design and may be retained,
relocated, deferred, or rejected based on the coherent outcome of each iteration. The historical
scope, tasks, and gates below remain as evidence of the superseded proposal only. They authorize
no specification contribution, implementation, migration, test, deployment, or live change.

## Historical Outcome

Provide an isolated Founder administration surface for three governed capabilities: Markup Designer, Trial Budget Configuration, and Coupon Manager. Every read and command uses a canonical generated Business Platform contract, preserves WBE ownership of billing truth, requires explicit Founder authority, records durable evidence before reporting success, and presents conflicts or unresolved outcomes honestly.

F7 is platform administration, not customer navigation and not a new source of billing truth. It exposes approved management capabilities through BP; it never lets a browser call WBE or a ledger directly.

## Existing Capability And Gap Boundary

| Capability | Existing reusable foundation | Missing before implementation |
|---|---|---|
| Markup Designer | WC-027 Markup Engine; WBE thread catalog read and deterministic margin-floor validation | Versioned WBE management command, canonical BP Founder facade, editable-field policy, conflict/idempotency semantics, evidence contract |
| Trial Budget Configuration | WC-031 trial lifecycle and allocation behavior; WC-032/033 trial routing and lifecycle integration | Authoritative configuration model and versioning, WBE read/write management contract, BP Founder facade, effective-date and in-flight-trial policy |
| Coupon Manager | WC-031 promotions validation/application and referral behavior; WC-042/043 payment/reconciliation controls | Coupon list/create/deactivate management contract, immutable history/versioning, BP Founder facade, authority and evidence rules |

`architecture/reference/billing/customer-acquisition-spec.md` currently describes direct browser calls to WBE. That direction is superseded for F7 by WC-034, R-047, and `UX-CONTRACT-01`: ordinary Founder traffic must use generated BP contracts, and WBE remains private. The owning specifications must be reconciled before implementation.

## Scope Boundary

### Included

- server-authorized Founder routes for markup, trial budgets, and coupons;
- canonical BP Founder-management OpenAPI operations and generated TypeScript client;
- private service-authenticated BP-to-WBE management contracts;
- explicit review/confirmation before each mutation, version/conflict handling, idempotency, and honest pending/unresolved states;
- WBE-owned financial validation, margin-floor enforcement, trial allocation rules, coupon lifecycle, and reconciliation;
- append-only evidence references for every proposal, authorization, mutation outcome, rejection, conflict, and reconciliation;
- keyboard, RTL, exact-360px, expanded, axe, privacy, and no-customer-navigation-leakage acceptance; and
- proportional F8 contract, security, financial, browser, coverage, lint, build, and regression evidence.

### Excluded

- direct browser access to WBE, PostgreSQL, Redis, Key Vault, a private ledger, or an undocumented route;
- changing C-089 margin floors, C-090 grandfather obligations, constitutional claims, pricing policy, refund policy, or Founder authority through UI code;
- deleting or overwriting financial, coupon, trial, configuration, or constitutional history;
- customer-facing coupon entry, payment, trial, or relationship behavior already owned by WC-031/WC-042/WC-043/WC-058/WC-059;
- provider credentials, Razorpay activation, deployment, production operation, or customer-proof claims;
- CSS-only authorization, trust in request-body tenant/Founder fields, or success inferred from transport acceptance; and
- any source, test, migration, generated client, build artifact, or live configuration before every entry gate below closes.

## Required Specification Contributions

| Order | Institution | Required contribution | Closure evidence |
|---|---|---|---|
| 1 | INST-011 Product Owner | Exact editable/read-only fields, confirmation language, effective-date behavior, in-flight trial impact, coupon lifecycle, customer-impact disclosure, and dedicated F7 acceptance matrix | Attested Product Contribution and Learning Records |
| 2 | INST-005 Solution Architect | Canonical BP Founder facade, private BP-to-WBE management operations, generated-client schemas, idempotency/conflict/reconciliation semantics, error model, and correction of direct browser-to-WBE wording | Approved component contracts and BP OpenAPI update |
| 3 | INST-006 Data Architect | Versioned configuration and coupon history, effective dating, immutability, RLS/service ownership, evidence references, migration blueprint, and rollback-by-new-version semantics | Approved data contract and migration blueprint or explicit no-migration decision |
| 4 | INST-007 Security Architect | Founder claim and fresh-assurance requirements, server route isolation, CSRF/replay protection, service authentication, tenant boundaries, abuse/rate controls, privacy-safe audit, and financial adversarial CCTs | Approved security contract and adversarial CCT matrix |
| 5 | INST-004 Enterprise Architect | Integrated review of Orders 1–4 against WC-027/WC-031/WC-042/WC-043, ADR-022/034, C-089/C-090/C-091, and BP-only public ingress | APPROVED integrated readiness review |
| 6 | INST-002 Constitutional Analyst | Independent readiness review of the execution-plan amendment and this Work Contract | APPROVED Constitutional Clearance/Readiness Record |

Orders 1–4 may proceed in parallel but must reconcile into one version-pinned package before Order 5. INST-013 coordinates and verifies records; it does not decide pricing, financial policy, security assurance, data ownership, or API architecture.

## Implementation Tasks

Implementation tasks remain dormant until the Entry Gate is fully satisfied.

| Task | Scope | Model hint | Status |
|---|---|---|---|
| WC063-01 | Implement approved WBE management reads/commands for markup configuration, trial budget configuration, and coupon lifecycle while preserving margin floors, immutable history, effective dating, idempotency, and reconciliation. | reasoning | gated |
| WC063-02 | Implement the canonical BP Founder facade with validated server-session authority, tenant and scope enforcement, private service authentication, CE authorization where required, Evidence First, privacy-safe RFC 9457 failures, conflict, and unresolved outcome handling. | reasoning | gated |
| WC063-03 | Apply the approved append-only migration blueprint and ownership/RLS model, or record the approved no-migration result; no destructive migration or direct browser-owned persistence. | reasoning | gated |
| WC063-04 | Generate the TypeScript client without manual patches and implement isolated Founder routes for Markup Designer, Trial Budget Configuration, and Coupon Manager. | reasoning | gated |
| WC063-05 | Add explicit confirmation, before/after projection, effective-date disclosure, immutable evidence reference, conflict recovery, pending reconciliation, and no-fabricated-success presentation. | reasoning | gated |
| WC063-06 | Add unit, contract, integration, migration where applicable, tenant/role isolation, CSRF/replay, stale-version, margin-floor, trial-impact, coupon-abuse, duplicate-command, WBE/CE-unavailable, evidence-failure, and reconciliation tests. | auto | gated |
| WC063-07 | Execute proportional F8 acceptance across Chromium, Firefox, WebKit, exact 360×800 and expanded viewports, keyboard, RTL, axe, privacy/network inspection, generated-contract conformance, Docker-only regression, at least 90% affected-surface coverage, lint, build, and independent implementation review. | auto | gated |

## Entry Gate — All Required

1. Orders 1–6 above are complete, attested, and mutually consistent.
2. The dedicated F7 acceptance IDs and financial/authorization CCTs exist in approved contracts.
3. Canonical BP Founder-management OpenAPI operations and private WBE management contracts are approved and generated-client compatible.
4. Direct browser-to-WBE wording is removed or explicitly superseded in every controlling F7 specification.
5. Data and Security contracts close versioning, effective-date, immutability, Founder assurance, CSRF/replay, service authentication, tenant isolation, and evidence decisions.
6. A GOAL-005 Execution Plan amendment defines the contribution scope, evidence specification, Participation Window, review sequence, and exclusions.
7. The Registrant acknowledges that exact amendment after CA readiness approval.
8. The Founder explicitly authorizes WC-063 implementation for the current session.
9. INST-013 issues a WC-063-specific GO Authorization only after items 1–8.
10. INST-010 records Acceptance after the GO Authorization issuance timestamp.

`G5 CLEAR`, existing WBE code, this Work Contract, a future backlog priority, or completion of specification grooming does not satisfy items 7–10.

## Implementation Definition Of Done

- All three Founder surfaces use generated BP contracts; browser bundles and network traces contain no private WBE or database route.
- Only a validated Founder server session with the approved fresh assurance can read or mutate the authorized management scope.
- WBE remains authoritative for pricing, trial, coupon, and reconciliation truth; BP and web do not recompute financial outcomes.
- Every mutation has explicit confirmation, idempotency, version/conflict behavior, evidence-before-success, and honest unresolved reconciliation.
- Margin-floor, immutable-history, effective-date, in-flight-trial, coupon-abuse, tenant, role, CSRF/replay, CE/WBE failure, and duplicate-command tests pass.
- Generated-client conformance, all assigned acceptance IDs, Docker suites, at least 90% affected-surface coverage, lint, build, accessibility, privacy, and security gates pass.
- Fresh independent implementation review approves one complete unmerged PR.

## Current Readiness Decision

**NOT IMPLEMENTATION-READY.** WC-027/WC-031/WC-042/WC-043 provide reusable billing foundations, but canonical management commands, the BP Founder facade, versioned data rules, Founder assurance, dedicated acceptance/CCTs, and integrated readiness approval do not yet exist. The direct browser-to-WBE direction in the older acquisition specification must be corrected before implementation.

No implementation, financial-policy decision, provider activation, deployment, PR approval, merge, self-review, or self-merge is authorized by this grooming record.