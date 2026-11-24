# WC-168 - Operator Console Works On Demo (Roadmap Iteration 1, Milestone M1)

## Record Control

| Field | Value |
|---|---|
| Work Contract | WC-168 |
| Office | Platform IT Expert (INST-010) |
| Initiative | IB-168 |
| Roadmap | [ROADMAP.md](../ROADMAP.md), Iteration 1 of 6, milestone M1 (platform-led, DMA-proved) |
| Founder assignment | Current conversation, 2026-11-24: "Approve committing WC-168 and WC-169 in full and WC-170 as the gated skeleton ... Yes." |
| Status | CONTRACT WRITTEN. Writing contracts and documents is authorized. **Implementation code is not yet authorized** (BOOTSTRAP implementation gate); the Founder authorizes it explicitly before any code is written |
| Baseline | `origin/main` at `c96e2ca6` (PR #639 merged) |
| Branch | `ib/168/iteration-1-operator-console` |
| Requirement ledger | [WC-168-requirements.yaml](./WC-168-requirements.yaml) |
| Constitutional basis | C-009, C-023, C-049, C-059, C-063, C-065, C-080 |
| Deployment | One Environment Deployment of Demo after merge; a second pull request only if the read-back fails |

## Why This Contract Exists

The Founder can now sign in on Demo and see the operator menus, but the operator screens do not work. Screenshots and Demo logs of 2026-11-24 show Providers failing, Pricing empty, the Key Vault page hidden, and layout and wording defects on several screens. Nothing after this iteration (hire, pay, connect, agent work) can be proven until the Founder can run the platform from these screens.

## Root Cause Read From Demo (read-only, 2026-11-24)

| Finding | Evidence | Confidence |
|---|---|---|
| RC-1 Providers outage: the Business Platform database role is denied on `business.provider_configs` | Web log `web.admin.providers.list_failed` status 500 at 09:23 UTC; Business Platform log `Npgsql.PostgresException 42501: permission denied for table provider_configs` on `SELECT ... FROM business.provider_configs`. The Providers screen reads through the `ProviderRegistry` connection, which Terraform does not set, so it falls back to `DefaultConnection` (role `bp_runtime`, member of `business_app`) | Error confirmed. Cause not proven. Candidates: `16-provider-registry.sql` contains no grant to `business_app`, and neither `99zzzzzzzz-wc148` nor `-wc149` grants on `provider_configs`; 11 init files create business tables with no `business_app` mention in the same file (a static proxy, not proof, because other such tables evidently work). Owner and privileges have not been read |
| RC-2 Other tables may share the defect | Same init pattern across 11 files (list in the review record below) | Unproven. The sweep and test are part of this contract |
| RC-3 Pricing lists zero packages while the Marketplace shows "From Rs 2,499" | The Marketplace price is a static `indicativePrice` (249900 paise) in the DMA integration descriptor `digital-marketing-local-service.v1.json`, not from the pricing engine; the only engine package is a DRAFT `STARTER ... ILLUSTRATIVE_NOT_FOR_SALE` that "cannot be authorized" because its proactive-message thread awaits Founder authorization and its publication components are default-off | **Confirmed: two price sources**, and the figures disagree (see the review record) |
| RC-4 Key Vault menu hidden | `web/lib/key-vault-admin.ts` requires a Keycloak `founder` realm role in the token and does not consult the platform Founder grant | Confirmed by code |
| RC-5 Temporal startup qualification fails when migrations finish early | Run 45347039018: connection pools still occupied 3m45s after scale-down; passes at 4m10s and 4m21s | Confirmed |

## Objectives

| Id | Objective |
|---|---|
| O1 | One roadmap: `ROADMAP.md` is the only roadmap and progress record; README, PROJECT_STATE, AGENT-ENTRY and BOOTSTRAP point to it; deviations need Founder approval |
| O2 | Providers works for the Founder on Demo |
| O3 | Pricing holds DMA Starter, Runner and Winner as authorized packages from one named price source |
| O4 | Founder access is coherent: the Key Vault page follows the platform Founder grant; Access, Settings and Connections behave correctly for staff |
| O5 | Deployment and platform hygiene: Temporal wait, blocked WhatsApp message, production Meta secret decision |
| O6 | WC-167 is closed, with its remaining items recorded or moved by identifier |

## Authority And Scope

In scope: `ROADMAP.md` and its pointers with a guard test; the init-chain grant defect and sweep with a real-database test; the Providers read-back; DMA package seeding through the existing pricing path; the Key Vault visibility rule; the Access, Connections, Settings and shell fixes; the Temporal wait; the blocked WhatsApp message through a governed route; the WC-167 closure.

Out of scope: hire and pay, customer provider connection, agent work, alerts, lifecycle, billing model changes, a second agent, historic WC-064 to WC-069, UAT and production.

Authority limits: no secret value is read or printed; no database row is deleted; no alert is muted; no privilege is widened beyond the SELECT, INSERT, UPDATE and DELETE that `business_app` already holds on its own tables; every Demo read is read-only until the Founder authorizes a change; the author does not merge or self-approve.

## Canonical Requirement Index

| Id | Requirement |
|---|---|
| WC168-R001 | `ROADMAP.md` holds iterations 1 to 6, milestones, Work Contract numbers, status and the deviation rule; README, PROJECT_STATE, AGENT-ENTRY and BOOTSTRAP carry a pointer, and README and PROJECT_STATE a current iteration line, outside the generated blocks; a test fails if a pointer or a Work Contract file is missing or the current iteration lines disagree; the test is in the quality-scripts gate |
| WC168-R002 | The document map in `ROADMAP.md` names the governing document for each concern, and every path it lists exists |
| WC168-R003 | The cause of RC-1 is proven by a bounded, read-only, Founder-approved read of the table owner and privileges on Demo; the fix gives `bp_runtime` (through `business_app`) the privileges it needs on every table the application queries; a test applies the whole init chain in a real database by reusing `scripts/wc124_init_chain_local.sh` and asserts `has_table_privilege` for `bp_runtime` on each such table. The fix reaches Demo through the existing database chain reconciliation (the chain fingerprint changes when init files change); the read-back confirms it did |
| WC168-R004 | The RC-2 sweep lists every init-chain table whose owner is not `bp_owner` or whose privileges for `business_app` are missing, fixes them at their source, and records the list in the contract |
| WC168-R005 | After deployment `/admin/providers` on Demo lists providers, the Founder can open the Meta provider row, and web logs show no `list_failed`; no credential value is displayed or logged |
| WC168-R006 | One price source. The customer-facing DMA price comes from the pricing engine's authorized package and never from the static `indicativePrice` in the agent descriptor; until a package is authorized the Marketplace shows no amount and says the price is shown before hire; DMA Starter, Runner and Winner exist as packages in the engine with the components and cost recipes the Founder decided on 2026-11-20 (not the older text in `dma-bundle-definitions.md` where they differ); a test proves the Marketplace amount equals the authorized package price |
| WC168-R015 | Founder-reserved inputs for R006 are supplied and recorded: the prices of Starter, Runner and Winner including GST (Starter: Rs 2,000 a month with 4 posts, 1 ad boost and monitoring across 4 selected platforms per the Founder's 2026-11-20 statement; Runner and Winner not yet given), authorization of the pending proactive-message thread in the Thread Catalog, and the Demo setting that turns the publication components on |
| WC168-R007 | The Pricing Overview does not say "Healthy" when zero packages were checked |
| WC168-R008 | The Azure Key Vault page and menu appear for a signed-in Founder through the platform Founder grant, still refuse everyone else, and no longer depend on a hard-coded email in the visibility rule |
| WC168-R009 | The Access screen has no layout gap; a person who already holds a staff role sees no request form; the stale sign-in ID hint is removed; the screen passes the WC-167 R006 layers in light and dark at 360, 768 and 1440 |
| WC168-R010 | Connections and Settings tell staff without a customer account what to do in staff terms; the "Try again" and "Browse Marketplace" buttons carry no back arrow; the floating stop box never overlaps page content; each passes the WC-167 R006 layers |
| WC168-R011 | Before the Temporal startup job runs, the deployment waits until the previous Temporal app has no replica (polled, with a refusal after eight minutes), and the startup job's own pool check still refuses a pool that is genuinely busy; a fault-injection test covers the drained path, the busy path and the timeout |
| WC168-R012 | The blocked WhatsApp message behind DEAD_LETTER_AGE_BREACH has a recorded cause, read through the same bounded read-only Founder-approved job as R003 (the product has no route that reads a blocked row); the Founder decides the resolution from the recorded cause and it is applied through a Founder-approved bounded action with evidence; nothing is deleted and no alert is muted. A permanent governed route for blocked messages is Iteration 4 (WC-171), not this contract |
| WC168-R013 | The Founder's decision on the production Meta secret found in the acceptance vault (reset or keep) is recorded; if reset, `meta-login-client-secret` is updated and a Facebook sign-in on Demo is read back |
| WC168-R014 | WC-167 R001, R004, R008 and R011 are recorded as done with read-back evidence; WC-167 R003, R005, R007 and R009 are moved to the named requirement here or in WC-169 |

## Founder And Customer Journey Simulation

Founder: sign in, open the menus, open Providers, enter the Meta app, open Pricing, authorize the DMA packages, open Access.
- Providers returns 500: fixed by R003 to R005.
- Pricing is empty and the Key Vault is hidden: fixed by R006 to R008.
- The Founder login cannot also act as a customer: customer journeys use the synthetic customer, and no "view as customer" feature is added.

Customer: not exercised in this iteration beyond reading the Marketplace price (R006). The customer journey starts in WC-169.

## Definition Of Done

- Every requirement has a ledger row with evidence: a test in the Docker runner and, for each Demo outcome, a read-back from Demo.
- The Founder has run the Environment Deployment and signed in; the read-back is recorded.
- `ROADMAP.md` progress record and the README and PROJECT_STATE lines are updated at close.
- WC-169 and WC-170 are committed in the same pull request.
- The Founder merges; the author does not.

## Critical Review And Simulation Record (2026-11-24)

Method: every requirement was checked against the repository, Demo logs and Azure state; the Founder and customer journeys were then walked step by step and each result recorded. Findings that changed this contract are marked FIXED.

### Founder journey run (Demo evidence of 2026-11-24)

| Step | Result | Evidence | Contract response |
|---|---|---|---|
| Sign in as the configured Founder | PASS | Founder grants reconciled at every start; menu shows Pricing, Providers, Access | none |
| Open Access | PASS with defects | Page loads; layout gap, request form shown to a Founder, stale hint | R009 |
| Open Pricing | PASS with defect | Dashboards answer in about 150 ms; zero packages; "Healthy" shown | R006, R007 |
| Open Providers | FAIL | 500, `42501 permission denied for table provider_configs` | R003 to R005 |
| Open Azure Key Vault | FAIL | Menu hidden: needs a Keycloak role, not the platform grant | R008 |
| Open Connections and Settings as staff | PASS with defects | Customer wording shown to staff; placeholder Settings | R010 |
| Authorize DMA packages | BLOCKED | No authorizable package exists (RC-3) | R006, R015 |

### Customer journey run (what slice 1 needs from this iteration)

| Step | Result | Evidence | Contract response |
|---|---|---|---|
| S1 Discover | PASS with defect | Marketplace card loads; price is a static descriptor value | R006 |
| S5 Pay | BLOCKED | The acceptance architecture blocks S5 with "no offerable price" until a package is authorized | R006, R015 |
| S6 Connect | BLOCKED | Needs the Meta provider row, which lives on the failing Providers screen | R003 to R005 |

### Gaps found and how they were fixed

| Id | Gap | Evidence | Status |
|---|---|---|---|
| G1 | RC-3 was only "possible"; it is real and there are four conflicting prices for the same agent | Descriptor Rs 2,499 (the old "Growth Engine" incl. GST tier); ADR-022 note Rs 1,499 for the entry tier; billing floor analysis Rs 825; Founder statement of 2026-11-20 Rs 2,000 for Starter | FIXED: R006 rewritten to one source, R015 added for the Founder's prices |
| G2 | The only seeded package cannot be authorized | Baseline SQL says it stays DRAFT because its thread awaits Founder authorization and its publication components are default-off | FIXED: R015 lists the thread authorization and the setting |
| G3 | The RC-1 cause in the first draft was wrong or at least unproven | Rows with no `business_app` grant exist in 11 files, but other tables from those files work | FIXED: cause marked a candidate; R003 requires a governed read first |
| G4 | A new real-database test would be a large item | `scripts/wc124_init_chain_local.sh` and `wc124_db_provisioner.py` already apply the chain locally | FIXED: R003 reuses the existing harness |
| G5 | A fix in init files may not reach Demo | Environment Deployment has a chain-reuse decision keyed on a fingerprint of the chain | FIXED: R003 requires read-back; a changed init file changes the fingerprint, so reconciliation runs. Risk: a longer deployment |
| G6 | Temporal fix as "wait six minutes" is a guess | The scale-down cooldown is 300 seconds; the pool check allows 24 seconds (12 tries of 2 seconds) | FIXED: R011 now waits for zero replicas, not a timer |
| G7 | R012 hid a new feature | No route reads or resolves a blocked outbox row; the service only counts them | FIXED: R012 reads the cause through the bounded job; the permanent route moves to WC-171 |
| G8 | Razorpay reachability was open in WC-169 | Terraform wires the Razorpay test secrets into the Demo runtime (`READY_TEST`) | Closed here; recorded in WC-169 |
| G9 | The iteration is large | 15 requirements across data, web, workflow, pricing and governed reads | FIXED: cut line below |

Init files that create business tables with no `business_app` mention in the same file (static sweep, input to R004, not a verdict): `10-reseller-agency`, `13-customer-acquisition`, `16-provider-registry`, `18-wbe-s7-payment`, `21c-ae01-paid-activation-ordering`, `34-wc095-zero-price-outcomes`, `36-wc120-conversation-whatsapp`, `44-razorpay-checkout-orders`, `45-pre-hire-checkout-orders`, `48-wc112-trial-agent-version`, `50-wc112-coupon-reservations`.

### Counter views and cut line

- The Founder-reserved items (R012 resolution, R013 decision, R015 prices and thread authorization) can stall on a person. If any is still open when the other requirements are read back green, the pull request ships without it and the item moves to WC-169 by identifier. It is not allowed to hold the iteration.
- R003 may show the cause is deeper than a missing grant (for example ownership or an out-of-band revoke). If the fix is larger than one requirement, record it and stop (Stop Conditions).

## Stop Conditions

- The table owner and privileges cannot be read through a governed route: stop and ask the Founder.
- A fix would widen the privileges of `business_app` beyond what it already holds on its own tables: stop.
- The Marketplace and Pricing disagree on price and the authorized source is unclear: stop and ask the Founder.
- The Founder does not approve the blocked-message read: R012 stays open and the rest proceeds.
- A test or gate fails for a reason outside this contract: record it and do not widen scope.

## Implementation Record

Contract written 2026-11-24 with `ROADMAP.md`, WC-169 and WC-170. Implementation not yet authorized.
