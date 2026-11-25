# WC-172 - Safe To Charge Real Customers (Roadmap Iteration 5, Milestone M5) - GROOMED

## Record Control

| Field | Value |
|---|---|
| Work Contract | WC-172 |
| Office | Platform IT Expert (INST-010), with single-pass reviews by the Solution Architect (lifecycle and money data contracts) and the Enterprise Architect (environment promotion and workload identity) before build |
| Initiative | IB-172 |
| Roadmap | [ROADMAP.md](../ROADMAP.md), Iteration 5 of 6, milestone M5 |
| Founder assignment | 2026-11-25: groom WC-172 as "safe to charge real customers (M5: Founder approval to take real money)" with PG-26 lifecycle, UAT promotion, real money, and the carry-ins WC-170 B5 and B10, WC-169 R013 price-change policy, Meta App Review, and production secrets with the ADR-046 shared-token rules |
| Status | **GROOMED. Not authorized to build.** The Founder accepts the stories by merging this pull request; the build needs his explicit authorization in the session that starts it (BOOTSTRAP implementation gate). **Taking real money needs a separate written Founder go-live approval (Epic G); no pull request, deployment or ledger row grants it.** Every ledger row is PLANNED |
| Depends on | WC-171 merged and deployed on Demo (alert, oversight and spend read routes are needed to run money safely); WC-170 B1 closed |
| Controlling documents | [agent-employment-experience-contract.md](../architecture/reference/product/agent-employment-experience-contract.md) (AEEC-06 to AEEC-09, OP-LIFECYCLE-COMM-01), [ADR-022](../adr/ADR-022-payment-processing-razorpay-india.md), [ADR-034](../adr/ADR-034-waooaw-billing-engine.md), [ADR-046](../adr/ADR-046-workload-identity-and-service-authentication.md), [ADR-047](../adr/ADR-047-private-ephemeral-deployment-runners.md), [C-088](../knowledge/claims/C-088.md), [C-089](../knowledge/claims/C-089.md), [PG-26](../architecture/reference/product/waooaw-product-gap-register.md), [CB-021](../blockers/CB-021-inst010-wc134-adr046-cloud-workload-credentials-2026-11-16.md), [WC-170](./WC-170-real-agent-work-end-to-end.md) gaps B5 and B10 |
| Agent instructions | [WC-170-agent-execution-instructions.md](./WC-170-agent-execution-instructions.md) apply unchanged, plus the stop conditions below |
| Requirement ledger | [WC-172-requirements.yaml](./WC-172-requirements.yaml) |
| Constitutional basis | C-001, C-002, C-005, C-007, C-009, C-023, C-049, C-059, C-063, C-065, C-088, C-089, C-090 |
| Deployment | Build pull request, then one Environment Deployment of Demo, then the UAT promotion deployments in Epic U, then the Founder's go-live decision |

## Why This Contract Exists

Everything built so far runs in sandbox and test mode on Demo. Four things stand between that and charging a real customer:

1. **The customer cannot yet exercise their rights.** Pause, resume, amend, renew, terminate and export are specified (AEEC) and have pieces of code (pro-rata arithmetic, payment lifecycle, a renewal failure saga, an evidence export), but the commercial edges (OP-LIFECYCLE-COMM-01) are undecided and no complete customer flow with correct billing has been proved.
2. **There is no tax invoice.** ADR-022 specifies GST invoices, numbering and credit notes. No code that issues a tax invoice or credit note was found in the billing engine, and nobody has recorded WAOOAW's GST identity for it.
3. **The money path trusts too much.** The spend chain from WC-170 is sandbox-only; the billing engine takes the caller's evidence ids and "verified" flag on trust (B5); the workload trust bundle is at its size limit and the four spend routes have no grants (B10); the Razorpay client has no guard that stops a live key running outside production; a locked hire quote has no rule for what happens when the package price changes (R013 follow-up).
4. **Nothing beyond Demo is qualified.** UAT and production exist as declared Terraform roots. Cloud workload credentials (ADR-046 amendment, CB-021) are approved for Demo only, with an interim certificate exception that expires on 2026-12-16; the shared tokens are still wired; secrets, vault access, Meta App Review and WhatsApp production are undecided.

The milestone is **M5: lifecycle rights, pro-rata billing, payer and funder, and tax invoices are proved on Demo and UAT; the money path is closed; and the Founder, on the evidence, approves taking real money.** The contract is deliberately a gate: it builds and proves safety, and it ends at the Founder's decision.

## What Grooming Found (verified in the repository on 2026-11-25)

| Area | Finding |
|---|---|
| Lifecycle code | `src/billing-engine/payment/lifecycle.py`, `lifecycle_jobs.py`, `router.py` and `tests/billing-engine/test_lifecycle_commands.py` exist (the lifecycle command tests are among the eleven failures that already exist on main and are not caused by this work). `src/billing-engine/payment/prorata.py` computes exact-seconds, paise-exact pause and termination refunds and upgrade differences. `RenewalFailureSaga.cs`, `EmploymentContractService.cs`, `ContractJourney.tsx` (shows the accepted quote and renewal consequence) and an evidence export route and `EvidenceWindow.tsx` exist. No complete customer amend, pause, resume, renew or terminate flow with billing consequences is proved end to end |
| Policy gap | AEEC-16 defers lifecycle commerce; OP-LIFECYCLE-COMM-01 (pause and termination commercial edges, D-05 and D-06) is an open placeholder |
| Tax invoices | ADR-022 specifies invoice numbers (`WAOOAW/2026-27/NNNNNN`), GST fields, per-agent and consolidated invoices, and pro-rata credit notes. No issuing code was found; `invoice` appears only in allowance, reconciliation and pricing modules. To be re-read at build start |
| Razorpay | `razorpay_client.py` creates orders, fetches payments, refunds with adjustment-id idempotency and verifies signatures. Test or live is decided only by the key. Terraform wires test-only keys for Demo and UAT. No guard refuses a live key outside production or a test key in production. ADR-022 says live keys are for production only |
| Spend chain | `src/billing-engine/spend_chain` (service, private routes) and `99zzzzzzzz-wc170-02-spend-chain.sql`, sandbox only. B5: evidence ids and the "verified" flag are trusted from signed callers. B10: the trust bundle is at its 25,600 byte Key Vault limit and the issuer test fails with five more grants; the four spend routes have no grants in `infrastructure/workload-identity/registry.yaml` |
| Price lock | `HireQuoteService` locks package, version, period, price and GST on the acquisition intent (WC-169). ADR-022 Amendment 1.4 (C-090) requires the agreed price to be kept, 30 days' notice and the customer's acknowledgement before a plan change. No code defines a renewal price or applies a catalogue price change to a locked hire. Hire intents created before WC-169 have no quote and fail closed |
| Environments | Terraform roots for demo, uat and prod exist. UAT has external environment and persistent state on, acceptance identity and vault off, workload lease-gated, `web_session_mode = "disabled"`. Prod foundation exists; the deployment workflow limits production applies. `infrastructure/platform-settings/uat.json` and `prod.json` are empty. Open blockers include CB-018 (Demo and UAT capacity inputs), CB-019 (web session database route), CB-020 (persistent-state inputs), CB-021 |
| Promotion | The deployment workflow verifies the signed release manifest and immutable image digests and offers a create-only Demo to UAT configuration promotion. GitHub environment protection is used through `environment: inputs.environment`; reviewer lists are repository settings, not code |
| Workload identity | ADR-046 amendment 1 (cloud issuance) approval is recorded for Demo with an interim certificate exception to 2026-12-16; UAT and production issuance, listener and link are not qualified. Terraform still maps `BP_SERVICE_JWT_SECRET`, `PR_SERVICE_JWT_SECRET` and `OPS_AUTH_TOKEN` to services, which ADR-046 forbids as authority |
| Secrets | Private vault per environment (`kv-waooaw-<env>`); a dedicated acceptance vault (`-acc`) exists for Demo and UAT only, sandbox values only, chosen in WC-164 and seeded by WC-165. Production credentials must never be reachable from a GitHub-hosted runner |
| Meta | The Meta app is in development mode: only people with a role on the app can connect. Advanced Access needs Business Verification and App Review (WC-169 R010 tracker: not yet submitted). The WhatsApp utility template and the production number are not registered |

## Objectives

| Id | Objective |
|---|---|
| O1 | A customer can amend, pause, resume, renew, terminate and export, and each action has the correct billing consequence, evidence and notice |
| O2 | Every charge, refund and credit has a GST tax invoice or credit note with the right identity, numbering and retention |
| O3 | The payer and the funder of every charge are known and recorded (C-088), and a locked hire price changes only by the rule the Founder approves |
| O4 | The spend and payment path is closed: evidence verified at the owner, grants in place, live and test keys cannot cross environments |
| O5 | UAT is provisioned and qualified with the full journey in test mode, with no shared tokens carrying authority |
| O6 | The production secrets, vault, workload identity, Meta and WhatsApp prerequisites are ready and checked, and a go-live checklist exists |
| O7 | The Founder decides, on evidence, whether to take real money, and the first real transaction is rehearsed under a cap |

## Authority And Scope

In scope: the lifecycle commands, notices and billing consequences; the policy decisions that settle OP-LIFECYCLE-COMM-01; tax invoices and credit notes; payer and funder; the price-change policy; the closed money path (B5, B10, key guard, reconciliation); UAT provisioning and promotion; the shared-token removal; production readiness (secrets, vault, identity, Meta, WhatsApp, protections); the go-live checklist and gate; UAT acceptance.

Out of scope: production deployment itself and taking real money (a separate Founder act, Epic G); a second agent (WC-173); new pricing models; refunds outside the lifecycle rules; marketplace payouts; multi-currency; international tax; mobile.

Authority limits: no real card, bank or customer is touched before the Founder's written go-live approval; live Razorpay keys exist only in the production vault, are never seeded by a GitHub-hosted runner and are never read by the author; no secret value is read or printed; no row is deleted (a correction is a credit note); the author does not merge or self-approve; any Azure change beyond the reviewed Terraform needs the Founder's explicit approval.

## Decisions For The Founder (proposed answers; the author decides every technical point)

| Id | Decision | Proposed |
|---|---|---|
| D1 | Pause: refund or credit? Can the customer pause for any length? | Unused days credited to the next invoice, not refunded to the card; maximum pause 30 days at a time; Emergency Stop never bills |
| D2 | Terminate: refund of unused days? Notice? | Customer may terminate any day; service ends at the paid period end, no mid-period refund, except a documented service failure; export available for 90 days after |
| D3 | Renewal price: locked price or current catalogue price? | The locked price renews unchanged for the contract term; a changed catalogue price needs 30 days' notice and acknowledgement (ADR-022 Amendment 1.4), otherwise the old price continues |
| D4 | Amend: change package up or down mid-period | Upgrade charged pro-rata at once; downgrade takes effect at the next period; each with a credit note or invoice line |
| D5 | Payer versus funder: who can fund a hire | Payer is the signed-in account holder; a funder (another account) is allowed only with the funder's own acceptance and a billing profile (C-088); the invoice names the payer |
| D6 | GST identity | The Founder supplies WAOOAW's legal name, GSTIN, registered address, state, the SAC code and the invoice series start; the tax professional's confirmation is recorded |
| D7 | Customer launch path while Meta App Review is pending | A: money first with a closed beta of named customers added as app Testers; B: wait for App Review before any real customer |
| D8 | Vault access path for GitHub-hosted acceptance runs | Keep the WC-164 dedicated acceptance vault for sandbox values only on Demo and UAT; production never reachable; the alternative is a private runner only |

## Canonical Requirement Index

| Id | Requirement |
|---|---|
| WC172-R001 | The Founder's decisions D1 to D5 are recorded as a lifecycle commercial policy (settling OP-LIFECYCLE-COMM-01) and each rule is a tested configuration or code path, not prose |
| WC172-R002 | A customer can pause and resume a hire; the commercial consequence follows the policy, is shown before confirmation, is billed or credited correctly to the paise, produces evidence, and Emergency Stop remains separate from pause |
| WC172-R003 | A customer can terminate; the consequence, the end date, the notice and the export window follow the policy; nothing is deleted; the evidence export is produced and downloadable and its content and retention follow the data-rights rules |
| WC172-R004 | A customer can amend (upgrade or downgrade); the pro-rata difference, effective date and invoice or credit note follow the policy; the accepted contract and quote are superseded by evidence, never edited |
| WC172-R005 | Renewal and price change: a hire renews at its locked price; a catalogue price change reaches an existing hire only after 30 days' notice and the customer's acknowledgement (C-090); a failed renewal follows the existing saga with a defined grace and notice; a hire created before the quote lock is migrated or refused by a stated rule |
| WC172-R006 | A GST tax invoice is issued for every captured payment and a credit note for every refund or credit: sequential numbering per series and financial year without gaps, the identity from D6, customer details, place of supply, tax split, SAC code, amounts in paise that sum exactly, stored immutably, retrievable by the customer and the Founder, with a test of reproducibility; a correction is a new document |
| WC172-R007 | Payer and funder are recorded on every charge and invoice (C-088): a funder needs a billing profile and their own acceptance; a charge with no known payer or funder is refused |
| WC172-R008 | The billing engine verifies the evidence ids and the "verified" provider proof of a spend or charge with the evidence owner instead of trusting the caller (WC-170 B5); a forged or missing evidence id is refused; the signed caller is still required |
| WC172-R009 | The workload trust bundle fits with headroom (split or slimmed, with the issuer test passing at the new grant count) and the four spend routes have route grants (WC-170 B10); a call from an unlisted service is refused |
| WC172-R010 | Money mode is guarded: each environment has an explicit payment mode; a live Razorpay key is refused outside production and a test key is refused in production at startup; the mode is visible to the Founder; a real-money gate (`real_money_enabled`) is off everywhere, can be turned on only by the Founder's step-up action in production, records who and when, and can be turned off at once |
| WC172-R011 | Reconciliation of money is complete and independent: provider settlement against invoices, refunds and credit notes, daily, with a discrepancy blocking new charges until resolved with evidence (extends the WC-170 chain); an unreconciled item is visible on the operations console from WC-171 |
| WC172-R012 | UAT is provisioned from reviewed Terraform with the Founder's approval, the Demo to UAT configuration promotion is exercised, the capacity and persistent-state blockers (CB-018, CB-019, CB-020) are closed or have a recorded owner, the UAT settings are explicit and tested, and a UAT deployment passes the release qualification lane |
| WC172-R013 | ADR-046 on UAT: cloud workload credentials, listener and link are qualified for UAT (CB-021 closure evidence for UAT), the Demo interim certificate exception is retired before 2026-12-16 or formally extended by the Founder, and `BP_SERVICE_JWT_SECRET`, `PR_SERVICE_JWT_SECRET` and `OPS_AUTH_TOKEN` carry no actor, role, step-up or authority anywhere and are removed from governed routes; a test enumerates the remaining uses |
| WC172-R014 | UAT acceptance: the full journey (discover, hire, pay in test mode, connect, work, alert, pause, resume, amend, renew, terminate, export, invoice, credit note, reconcile) runs for a synthetic customer on UAT with one calibration report whose every NOT-WITNESSED or FAIL item has an owner; the acceptance vault path follows D8 and holds only sandbox values |
| WC172-R015 | Production readiness is checked without production being changed beyond reviewed Terraform: the production vault, identities, Razorpay live account and webhook, Meta production app and permissions, WhatsApp number and approved templates, GitHub environment protections and reviewers, rollback and freeze plan, and monitoring and paging are each listed with an owner, status and evidence in a go-live checklist; the live Razorpay keys are entered only by the Founder into the production vault and are never visible to the author or a GitHub-hosted runner |
| WC172-R016 | Meta App Review is tracked to a decision: Business Verification, screencast and reviewer instructions are prepared from the UAT run, the submission date and result are recorded by the Founder, and decision D7 governs who may be a customer until it passes |
| WC172-R017 | The go-live gate: M5 is reached only when R001 to R016 are PASS or Founder-reserved with evidence, the checklist is complete, and the Founder records his written approval to take real money, then runs one rehearsal transaction (his own card, a small amount, then a full refund and credit note) under a cap with the author reading back every record; any failure stops the gate |

## Epics And Groomed Stories

### Epic L. Lifecycle (PG-26; R001 to R005)

| Story | As a ... I can ... | Acceptance | Owner | Size | Req |
|---|---|---|---|---|---|
| L1 | As the Founder I settle the commercial rules | D1 to D5 recorded; each is a configuration or tested code path | Founder, BP, billing engine | M | R001 |
| L2 | As a customer I pause and resume | Consequence shown before confirmation; correct to the paise; evidence; Emergency Stop distinct | BP, billing engine, Web | L | R002 |
| L3 | As a customer I terminate and export | End date, notice and export window per policy; nothing deleted; export downloadable | BP, Web | L | R003 |
| L4 | As a customer I amend | Upgrade pro-rata now, downgrade next period; contract and quote superseded by evidence | BP, billing engine, Web | L | R004 |
| L5 | As a customer my price is protected | Renews at the locked price; a catalogue change needs 30 days' notice and acknowledgement; pre-quote hires follow a stated rule; failed renewal saga with grace | BP, billing engine | L | R005 |

### Epic T. Tax invoices (R006, R007)

| Story | As a ... I can ... | Acceptance | Owner | Size | Req |
|---|---|---|---|---|---|
| T1 | As the Founder I give the GST identity | D6 supplied and the tax professional's confirmation recorded | Founder | S | R006 |
| T2 | As a customer I receive a tax invoice for every payment and a credit note for every refund | Sequential, gap-free numbering per series and year; exact paise; immutable; retrievable by customer and Founder; correction is a new document | Billing engine, Web | L | R006 |
| T3 | As the platform I know payer and funder | Recorded on every charge and invoice; funder acceptance and billing profile; unknown payer refused | BP, billing engine | M | R007 |

### Epic M. Closed money path (R008 to R011)

| Story | As a ... I can ... | Acceptance | Owner | Size | Req |
|---|---|---|---|---|---|
| M1 | As the billing engine I verify evidence at its owner | Spend and charge ask the evidence owner; forged or missing ids refused | Billing engine, CE | M | R008 |
| M2 | As the platform I fit the trust bundle and grant the spend routes | Bundle split or slimmed with headroom; issuer test passes; four route grants; unlisted caller refused | Workload identity | M | R009 |
| M3 | As the Founder I know which money mode each environment is in | Mode per environment; key guard at startup; `real_money_enabled` off everywhere, Founder-only step-up in production, audited, instantly reversible | Billing engine, BP, Web | M | R010 |
| M4 | As the Founder I trust the books | Daily provider-to-invoice reconciliation; a discrepancy blocks new charges until resolved; visible on the operations console | Billing engine | L | R011 |

### Epic U. UAT promotion (R012 to R014)

| Story | As a ... I can ... | Acceptance | Owner | Size | Req |
|---|---|---|---|---|---|
| U1 | As the Founder I get a UAT environment | Reviewed Terraform applied with his approval; blockers CB-018, CB-019, CB-020 closed or owned; explicit UAT settings tested | Platform IT | L | R012 |
| U2 | As the platform I promote Demo configuration to UAT | The create-only promotion exercised; release qualification passes on UAT | Platform IT | M | R012 |
| U3 | As the platform UAT services authenticate with workload identity only | CB-021 closure evidence for UAT; Demo interim certificate retired by 2026-12-16 or extended in writing; shared tokens carry no authority, test enumerates remaining uses | Platform IT, security | L | R013 |
| U4 | As the harness I run the full journey on UAT | Acceptance vault per D8; one calibration report with an owner for every gap | Harness | L | R014 |

### Epic G. Go-live readiness and gate (R015 to R017)

| Story | As a ... I can ... | Acceptance | Owner | Size | Req |
|---|---|---|---|---|---|
| G1 | As the Founder I see every production prerequisite in one list | Checklist rows: vault, identities, Razorpay live account and webhook, Meta production app, WhatsApp number and templates, protections and reviewers, rollback and freeze, paging; owner, status, evidence | Platform IT | M | R015 |
| G2 | As the Founder I submit Meta App Review | Materials prepared from the UAT run; he submits and records dates; D7 recorded | Founder, author | M | R016 |
| G3 | As the Founder I approve real money | Written approval, one capped rehearsal with refund and credit note, every record read back; the gate can be switched off at once | Founder | S | R017 |

## Founder-Reserved Items

| Item | When | What |
|---|---|---|
| Authorize the build | Before any code | Explicit words in the session that starts the build |
| D1 to D8 | At grooming acceptance, or before the story that needs each | The decisions above; proposed answers are the author's recommendation, not decisions |
| GST identity and tax confirmation | Before T2 is proved | Legal name, GSTIN, address, SAC, invoice series; the tax professional's confirmation |
| Approve Azure applies | Before U1 and any production Terraform | Explicit approval of each reviewed apply |
| Razorpay live keys and production secrets | Go-live | Entered by the Founder into the production vault; never by the author or a hosted runner |
| Meta Business Verification and App Review | During the iteration | His Meta login; dates recorded by him |
| WhatsApp number and template | During the iteration | Registration and approval in WhatsApp Manager |
| Go-live approval | End | Written approval, then the capped rehearsal |

## PR And Deployment Plan

| Step | What | Who |
|---|---|---|
| 1 | This grooming pull request (docs only) merges | Founder |
| 2 | WC-171 build, Demo deployment and read-back | Per WC-171 |
| 3 | WC-172 build pull request, all application stories (Epics L, T, M and the code parts of U and G), one Docker pass, bound PR body | Author builds, Founder authorizes and merges |
| 4 | One Environment Deployment of Demo; read back; Demo lifecycle and invoice run in test mode | Founder deploys, author reads back |
| 5 | UAT promotion in order: foundation apply (approval), workload apply, configuration promotion, workload identity qualification, release qualification, each an Environment Deployment | Founder runs, author reads back; a repair pull request only if a read-back fails |
| 6 | UAT acceptance run and calibration report; production readiness checklist completed; Meta App Review submitted | Author and Founder |
| 7 | Go-live decision and the capped rehearsal | Founder |

## Journey Simulation (grooming review)

| Step | Expectation after the build | Risk found in grooming | Response |
|---|---|---|---|
| Customer pays the hire price | Invoice with GST and number arrives | No issuing code | T2 |
| Customer pauses for two weeks | Consequence shown first, credit on the next invoice | Edges undecided | L1, L2 |
| Customer terminates mid-month | Service to period end, export available, no deletion | Edges undecided | L1, L3 |
| Customer upgrades | Pro-rata invoice line now | Credit notes missing | L4, T2 |
| Package price rises | Existing hire keeps its price for 30 days' notice and acknowledgement | No rule applies a catalogue change to a locked hire | L5 |
| A friend funds a hire | Invoice names payer, funder accepted and profiled | Payer versus funder not modelled in the invoice | T3 |
| An agent spends | Evidence verified at its owner | Billing engine trusts the caller | M1 |
| Live key set on UAT by mistake | Service refuses to start | No guard | M3 |
| UAT service calls another | Workload identity only | Shared tokens still mapped | U3 |
| A real customer connects before App Review | Refused unless a listed Tester | App in development mode | G2, D7 |

## Gaps Found In Grooming And How They Were Fixed

| Id | Gap | Evidence | Status |
|---|---|---|---|
| G1 | The lifecycle is partly coded and wholly unproved | Pro-rata, payment lifecycle, saga and export exist; no end-to-end flow | FIXED: Epic L, with decisions D1 to D5 first |
| G2 | No tax invoice or credit note issuer | Search of `src` | FIXED: T2 (re-read at build start) |
| G3 | The WAOOAW GST identity is nowhere in the repository | No GSTIN or SAC in `src` | FIXED: Founder item D6 |
| G4 | Live and test keys can cross environments | Mode is decided only by the key | FIXED: M3 |
| G5 | The lifecycle command tests already fail on main | Eleven known billing engine failures | RECORDED: the build must either fix them (they are in the module being changed) or record each with an owner; they are not hidden |
| G6 | Locked price has no renewal rule | `HireQuoteService`, ADR-022 Amendment 1.4 | FIXED: L5, D3 |
| G7 | Trust bundle at its size limit blocks every new route | WC-170 B10, issuer test | FIXED: M2, before any new grant |
| G8 | Demo's interim certificate exception expires 2026-12-16 | CB-021 | FIXED: U3 has the date; the Founder extends in writing or it is retired |
| G9 | UAT settings are empty and the blockers are open | `uat.json`, CB-018 to CB-020 | FIXED: U1 |
| G10 | App Review has a lead time outside our control | WC-169 tracker | RECORDED: G2 and D7 decouple money from App Review; submission starts at the beginning of the iteration |
| G11 | The size is large and includes infrastructure | Five epics | RECORDED: the application build is one pull request; UAT and go-live are deployments and a checklist, not code; if the build proves larger the author asks for a split at that point, lifecycle and invoices first, closed money path second |

## Stop Conditions

- The Founder has not authorized the build: no code.
- Any step that would touch a real card, bank or customer, or enter a live key, before the Founder's written go-live approval: stop.
- A live key or a production secret would be read, printed, or seeded by a GitHub-hosted runner: stop.
- A UAT or production Azure apply that the Founder has not approved: stop.
- An invoice, credit note or refund that cannot be tied to evidence, payer and funder: refuse it.
- A fix that grants authority from a shared token or a manual database edit: stop.
- Any rule in D1 to D8 that is not yet decided when its story starts: that story waits for the Founder; the others proceed.

## Definition Of Done

Build pull request: every application requirement has a ledger row with executable evidence; the single Docker validation pass is green on the commit gate commands; the pull request body is bound to the final commit. Post-merge qualification: the Demo read-back, the UAT promotion read-backs and the UAT calibration report are recorded in the ledger; the go-live checklist is complete; `ROADMAP.md`, README and PROJECT_STATE are updated at close. **M5 itself is reached only by the Founder's written go-live approval and the capped rehearsal (R017).**

## Implementation Record

Groomed 2026-11-25 on branch `ib/171/groomed-alerts-menus-and-real-money` from `origin/main` at `1519cc8a` (PR #644 merged). Facts above were read from the repository by a read-only pass; no Demo or Azure read and no code was done. Not yet built.
