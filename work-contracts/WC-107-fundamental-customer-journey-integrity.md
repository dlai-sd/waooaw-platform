# WC-107 - Fundamental Customer Journey Integrity

## Record Control

| Field | Value |
|---|---|
| Office | Chief Solution Architect (INST-005) |
| Implementation office | Platform IT Expert (INST-010) |
| Authorized by | Founder instruction in the 2026-09-28 continuous working session |
| Implementation authorization | Founder confirmed WC-107 implementation in the 2026-09-28 continuous working session |
| Status | IMPLEMENTATION AUTHORIZED - NOT YET QUALIFIED |
| Baseline | `origin/main` at `27ffe882eecd972d75c47282c434601c2bad98ea` |
| Delivery unit | One bounded cross-component customer-journey repair |

## Authority And Scope

Define the complete Login, Registration, Logout, Trial, Hire, payment-confirmation, and My Agents
continuation behavior needed to prevent iterative drift in WAOOAW's fundamental customer journeys.

The design baseline consists of:

- `architecture/reference/components/fundamental-customer-journeys.md`;
- this Work Contract;
- `work-contracts/WC-107-requirements.yaml`; and
- the compact component-reference index entry.

Current-session authorization permits the existing Web Application, Business Platform, Billing Engine,
and their tests to implement the atomized WC107 requirements. It does not authorize new dependencies,
schema or provider-contract changes, cloud mutation, deployment, customer traffic, acceptance,
approval, or merge.

## Inputs

- Founder defect reports and screenshots supplied on 2026-09-28.
- Read-only Demo evidence from Web revision `ca-demo-web--0000057` and Business Platform revision
  `ca-demo-business-platform--0000052`, both built from baseline `27ffe882`.
- `architecture/reference/components/identity-boundary.md`.
- `architecture/reference/product/ae01-security-contract.md`.
- `architecture/reference/billing/customer-acquisition-spec.md`.
- `work-contracts/WC-097-marketplace-acquisition-experience.md`.
- ADR-003, ADR-008, and ADR-022.

## Outputs

1. One normative component contract composing identity and acquisition without changing owner
   authority.
2. One atomized, machine-readable requirement-to-evidence ledger.
3. One compact index route for later agents.

## Requirement Index

| Requirement | Normative outcome |
|---|---|
| WC107-R001 | Login authenticates without creating or forcing Registration. |
| WC107-R002 | Registration begins only from an explicit Register, Trial, or Hire intent and preserves a safe target. |
| WC107-R003 | Registration creates or reuses exactly one durable account, membership, and binding. |
| WC107-R004 | Logout and account switch clear protected state and prevent silent restoration. |
| WC107-R005 | Returning Login restores the same authorized account without Registration or a generic denial. |
| WC107-R006 | Register selected by an existing account continues without duplicate registration. |
| WC107-R007 | Authentication presentation remains accessible and usable at every required viewport. |
| WC107-R008 | Typed identity failures preserve bounded recovery semantics. |
| WC107-R009 | The Marketplace card is the complete concise decision surface. |
| WC107-R010 | One explicit Terms and Privacy consent gates Trial and Hire. |
| WC107-R011 | Trial is durable and never enters Hire or payment code. |
| WC107-R012 | Optional coupon validation precedes order creation without entering URLs. |
| WC107-R013 | Hire requires signed payment or approved zero-payable evidence before relationship creation. |
| WC107-R014 | Payment uncertainty reconciles the same payment without a second charge. |
| WC107-R015 | Confirmation derives only from authoritative durable state. |
| WC107-R016 | My Agents selects the authorized resulting relationship with one-use server-held state. |
| WC107-R017 | Customer and command state remains absent from URLs, history, unsafe logs, and traces. |
| WC107-R018 | Each complete fundamental journey retains one privacy-safe cross-service trace. |
| WC107-R019 | Exact Demo candidate images pass all five desktop and mobile journeys. |
| WC107-R020 | Exact-head quality gates and mandatory author review have no unresolved finding. |

## Strategic Implementation And Validation Plan

Work proceeds in the following dependency order. A group remains `IN PROGRESS` until every listed
requirement has direct evidence meeting its completion clause. The next group does not begin while a
current-group requirement is failed, deferred, substituted, or untested.

| Gate | Combined stories and requirements | Why combined | Group Definition of Done |
|---|---|---|---|
| G1 - Identity continuity and authentication presentation | Login, Registration, Logout/returning Login, typed recovery, safe targets, modal layout; WC107-R001 through R008 | These stories share the broker session, identity-session result, route-backed modal, protected cache cleanup, and registration handoff | Focused Web and Business Platform identity tests pass; real-PostgreSQL identity tests pass where required; 320/360/390/tablet/desktop geometry, keyboard, focus, axe, RTL, zoom, logout, account-switch, and relogin stories pass; no forced Registration or generic `/403` remains |
| G2 - Marketplace decision, consent, and coupon preparation | Concise card, canonical charge, progressive disclosure, consent, optional coupon, clean continuation state; WC107-R009, R010, R012, and applicable R017 | These stories share one authoritative offer projection and one customer decision surface before any consequential action | Component/API tests prove canonical offer ownership, no mandatory detail detour, consent withdrawal/no mutation, coupon policy and amount refresh before order creation, and zero command/coupon/idempotency values in URLs or browser history; responsive/axe/browser stories pass |
| G3 - Trial, Hire, reconciliation, confirmation, and My Agents | Trial-only execution, direct paid/zero-payable Hire, commercial binding, pending reconciliation, truthful confirmation, selected authorized relationship; WC107-R011 and R013 through R016 plus applicable R017 | These stories form one consequential transaction boundary and must be tested together to prevent cross-intent retries, duplicate charges, or fabricated success | Trial never enters Hire/payment; provider cancel has zero consequence; paid and zero-payable Hire bind exactly once; unknown outcomes reconcile without another order/charge; My Agents authoritatively projects, selects, focuses, then consumes actor/account-bound flash state on a clean URL; focused Web, Billing Engine, Business Platform, PostgreSQL, and browser tests pass |
| G4 - Cross-service observability and exact-image qualification | Privacy-safe traces, full regression, production images, integrated local journeys, author review; WC107-R017, R018, and R020 | Observability and qualification must cover the final combined state, not intermediate implementations | Secret/privacy scans, lint, strict typecheck, changed-line coverage, production builds, affected full suites, exact local images, integrated Docker journeys, diff review, and mandatory author review pass on one exact commit |

WC107-R019 is a separate deployed-acceptance gate. It remains `NOT_STARTED` until the Founder grants
Demo deployment and customer-traffic authority. Local Docker evidence, image builds, or emulation do
not qualify it and do not block completion of the authorized local implementation groups.

### Efficient Docker Execution Policy

1. Build the stack-specific `test-runner-ts`, `test-runner-dotnet`, and, only if Billing Engine Python
  changes, `test-runner-python` images once. Reuse them with `--no-deps`; never use the deprecated
  full multi-stack runner for a single-stack check.
2. During implementation, run only the test file/class that can falsify the current story. Batch
  adjacent tests once the story is internally complete.
3. The TypeScript runner stages Web source in container tmpfs and reuses its cached dependency tree;
  it does not start Keycloak, PostgreSQL, Temporal, CE, or Business Platform for Jest/lint/typecheck.
4. At each group gate, run the applicable focused coverage, static, security, contract, PostgreSQL,
  accessibility, and browser checks once. Record direct evidence before advancing the group.
5. After G1 through G3 pass their focused gates, build each affected production image once and run
  the integrated local Docker journeys against those exact image IDs. Rebuild only if a subsequent
  repair changes that image's source or build input.
6. Do not poll CI or batch jobs. Submit exact-head evidence and perform one required result lookup.

## Defect-To-Requirement Trace

| Confirmed basis | Covered by |
|---|---|
| Login forced Registration or generic `/403`; repeat Register failed | WC107-R001, R005, R006, R008 |
| Logout/relogin did not reliably restore the same identity session | WC107-R004, R005 |
| Registration dialog overflowed and used incorrect copy/typography | WC107-R007 |
| Deployed path added a mandatory second decision page; the observed session ended before consent | WC107-R009, R010 |
| Coupon and continuation state entered URLs | WC107-R012, R017 |
| Trial retry invoked Hire/Razorpay code | WC107-R011 |
| Source lacked authoritative completion confirmation and selected My Agents continuation | WC107-R013 through R016 |
| Demo had no completed Trial/Hire POST in the observed window | WC107-R018, R019 require future deployed proof; no deployed-success claim is made |

## Required Flow Outcomes

### Login, Registration, And Logout

Login is non-mutating. A visitor without an account reaches Marketplace. Registration begins only
from Register, Trial, or Hire. Completion creates/reuses one account and returns through a renewed
authorized session. Logout clears all protected state and Keycloak session. Returning Login restores
the same account/membership without forced Registration or generic `/403`.

### Trial

The primary card shows the offer, monthly charge, trial terms, capabilities, consent, and action.
After consent, one Trial command starts only a durable Trial relationship. Success is confirmed from
authoritative state and continues to My Agents with the new Trial card selected.

### Hire

The primary card shows the offer, monthly charge, capabilities, consent, and action. An optional
coupon is validated in a compact pre-checkout step. The customer accepts the exact amount and enters
Razorpay. Only signed payment evidence, durable Hire relationship, commercial binding, and My Agents
projection permit confirmation and selection of the new card. The later operational contract and
activation remain separate authorities.

## Definition Of Done

- Every entry in `work-contracts/WC-107-requirements.yaml` is `PASS` with the named direct evidence.
- Login, Register, Logout/returning Login, Trial, and Hire state-machine tests pass in Docker.
- Logout and account-switch tests prove RP-initiated logout, explicit account selection, no silent
  restoration, and zero prior-account presentation or cache leakage.
- Desktop and mobile browser tests prove the default and transition states have no clipping,
  overlap, root overflow, dialog overflow, progress overflow, or hidden primary action.
- Trial retry cannot call Hire or payment code; Hire reconciliation cannot create a second charge.
- No customer command state appears in a URL, browser history, customer-visible log, or trace.
- A separately authorized exact-image Demo run proves all five journeys and retains cross-service
  traces, exact revisions, status outcomes, and authoritative My Agents confirmation.
- Full applicable Web, Business Platform, Billing Engine, contract, security, accessibility, and
  constitutional tests pass.
- Mandatory author review covers requirements, authority, identity continuity, tenant isolation,
  payment idempotency, truthful success, accessibility, privacy, observability, rollback, and scope.
- The exact final commit is submitted for Founder review. The author does not approve or merge it.

## Design Author Review

| Finding | Repair | Result |
|---|---|---|
| AR-01 WC-097 required a detail route while WC-107 removed the mandatory detour without declaring precedence | Limited WC-107 precedence to presentation; retained WC-097 ownership/safety and the slug route as the same direct-entry/expanded surface | RESOLVED |
| AR-02 Encrypted browser flash state contradicted the server-state and privacy rules | Required server-held state keyed by a random one-use scoped cookie with no relationship or outcome value | RESOLVED |
| AR-03 Logout omitted silent-restoration, account-selection, and account-switch isolation controls | Added RP logout, `prompt=select_account`, no history/background restoration, and prior-account sentinel evidence | RESOLVED |
| AR-04 Ledger evidence under-specified safe targets, typed errors, accessibility, and coupon policy | Expanded the applicable requirements and evidence | RESOLVED |
| AR-05 Pre-checkout wording incorrectly moved the later operational contract before Razorpay and added a mandatory review step | Restored AE-01 sequencing: versioned offer and payment terms before direct checkout; operational contract after funded Hire | RESOLVED |
| AR-06 Trial omitted metering and no-paid-fallback invariants | Added durable trial billing, quota/provider failure, and no-charge requirements | RESOLVED |
| AR-07 The state diagram forced a fully discounted Hire through Razorpay and used paid confirmation text for it | Added an approved zero-payable path and outcome-specific truthful confirmation | RESOLVED |
| AR-08 Close, withdrawn consent, and provider cancellation were under-specified | Added no-mutation cancellation behavior and direct evidence requirements | RESOLVED |
| AR-09 Flash state was not explicitly actor/account-bound and one defect row overstated causality | Added strict binding/expiry and limited the defect statement to observed facts | RESOLVED |

This review is author self-verification of the design artifacts, not approval, implementation
qualification, or independent assurance. Implementation author review remains WC107-R020.

## Stop Conditions

Stop on any proposal to:

- make Login create or force Registration;
- infer account, tenant, price, discount, payment, or relationship state in the browser;
- weaken actor/membership, tenant, consent, fresh-authentication, payment-signature, or Evidence First
  checks;
- show success before the authoritative durable outcome;
- retry Trial through Hire, create a second charge during reconciliation, or bypass Razorpay evidence;
- put command identifiers, coupon, payment, identity, or relationship data in URLs or unsafe logs;
- replace a required deployed journey with local or mocked evidence;
- add a dependency or change a provider contract without separate authority; or
- implement, deploy, accept, self-approve, or self-merge without the required authority.

## Rollback

This design-only Work Component adds no runtime or provider state. Before implementation, rollback is
reversion of these documents. A future implementation must define code, data, provider, and deployment
rollback evidence in its separately authorized delivery.
