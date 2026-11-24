# WC-168 - Operator Console Works On Demo (Roadmap Iteration 1, Milestone M1)

## Record Control

| Field | Value |
|---|---|
| Work Contract | WC-168 |
| Office | Platform IT Expert (INST-010) |
| Initiative | IB-168 |
| Roadmap | [ROADMAP.md](../ROADMAP.md), Iteration 1 of 6, milestone M1 (platform-led, DMA-proved) |
| Founder assignment | Current conversation, 2026-11-24: "Approve committing WC-168 and WC-169 in full and WC-170 as the gated skeleton ... Yes." |
| Status | IMPLEMENTATION_AUTHORIZED. Founder, 2026-11-24: "Authorize implementation code for WC-168, including the temporary read-only job that reads the Demo database's table owner and privileges. include this in PR documentation and i approve PR". The read-only job and the roadmap changelog entry are documented in the pull request body |
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

Authority limits: no secret value is read or printed; no database row is deleted; no alert is muted; no privilege is widened beyond what an application role is already meant to hold on its own tables; every Demo read is read-only until the Founder authorizes a change; the author does not merge or self-approve. The Founder-authorized temporary read-only job (R003) runs one catalog query (table owners, access lists and role memberships, no business rows) with the Business Platform's own database credential by reference, inside a read-only transaction, then is deleted. The blocked-message read (R012) is a separate read that needs its own Founder approval.

## Canonical Requirement Index

| Id | Requirement |
|---|---|
| WC168-R001 | `ROADMAP.md` holds iterations 1 to 6, milestones, Work Contract numbers, status and the deviation rule; README, PROJECT_STATE, AGENT-ENTRY and BOOTSTRAP carry a pointer, and README and PROJECT_STATE a current iteration line, outside the generated blocks; a test fails if a pointer or a Work Contract file is missing or the current iteration lines disagree; the test is in the quality-scripts gate |
| WC168-R002 | The document map in `ROADMAP.md` names the governing document for each concern, and every path it lists exists |
| WC168-R003 | The cause of RC-1 is proven by a bounded, read-only, Founder-approved read of the table owner, privileges and row-level-security policies on Demo; the fix gives the application role exactly what the Founder provider screen does (read platform rows and its own tenant's rows, insert platform rows, update only the active credential version, never delete) through narrow grants and matching policies; a real-database test reproduces the Demo state and proves the allowed and the refused operations, and that the fix is idempotent; the fix reaches Demo through the existing database chain reconciliation (the chain fingerprint changes when init files change) and the read-back confirms it did |
| WC168-R004 | The sweep is measured, not guessed: the same read-only job lists every business table the application role cannot select (63 on 2026-11-24, most of them billing or legacy tables the Business Platform does not use) and the contract records the ones the Business Platform code does use (six: `provider_configs`, fixed here, and five WC-120 conversation tables). The five conversation tables stay ungranted while the conversation feature is off, and granting them (with a per-table privilege analysis) is a precondition of WC170-R008, where conversation is first enabled. The job is committed so the sweep can be re-run at any time |
| WC168-R005 | After deployment `/admin/providers` on Demo lists providers, the Founder can open the Meta provider row, and web logs show no `list_failed`; no credential value is displayed or logged |
| WC168-R006 | The Founder sets package names, features and prices at run time on the Pricing screen and nothing is seeded or hard-coded: an administrator or the Founder can create a package, rename it, edit its features (components and cost recipes) and its price, and the Founder authorizes it there; tests prove the draft, edit and authorize path end to end through the existing screen and gateway, and a Demo read-back proves it once R015's preconditions are cleared. **Finding recorded here, fixed in WC-169 R013:** the Marketplace card, the employment contract terms and the hire amount are built from the static `indicativePrice` in the agent descriptor (`ProfessionalCatalog` manifest through `EmploymentRelationshipsController` and `AcquisitionController`), not from the authorized package; the customer package catalogue (`PackagesController`) and `hire-preview` already exist. Rewiring the customer price to the authorized package is a payment-path change, so it is proved by the acceptance pay step in Iteration 2 |
| WC168-R015 | The Founder's run-time pricing decisions are made on the Pricing screen and are not recorded as constants in the repository: the contract records only that they were made and when. The seeded draft can be authorized only after the pending proactive-message thread (`whatsapp_template_utility`) has its rate authorized on the Pricing screen (Rates), and the Founder records his separate decision on which `DEFAULT_OFF` DMA components he wants to sell (for example `SOCIAL_PUBLICATION` and `SOCIAL_OBSERVATION`, whose activation authority in the DMA declaration is "FOUNDER_SEPARATE_DECISION"). Applying that decision to the DMA declaration and its admission is a change to the agent, not a Demo setting, and is WC169-R014 |
| WC168-R007 | The Pricing Overview does not say "Healthy" when zero packages were checked |
| WC168-R008 | The Azure Key Vault page and menu appear for a signed-in Founder through the platform Founder grant, still refuse everyone else, and no longer depend on a hard-coded email in the visibility rule |
| WC168-R009 | The Access screen has no layout gap (its page class no longer collides with the public landing layout), a Founder sees no request form and no sign-in ID hint, other staff keep the form but lose the hint once they hold a role, and the screen passes the WC-167 R006 layers in light and dark at 360, 768 and 1440 |
| WC168-R010 | Connections and Settings tell staff without a customer account what to do in staff terms; the "Try again" and "Browse Marketplace" buttons carry no back arrow; the floating stop box never overlaps page content; each passes the WC-167 R006 layers |
| WC168-R011 | Before the Temporal startup job runs, the deployment waits until the previous Temporal app has no replica (polled, with a refusal after eight minutes), and the startup job's own pool check still refuses a pool that is genuinely busy; a fault-injection test covers the drained path, the busy path and the timeout |
| WC168-R012 | The blocked WhatsApp message behind DEAD_LETTER_AGE_BREACH has a recorded cause, read through the same bounded read-only Founder-approved job as R003 (the product has no route that reads a blocked row); the Founder decides the resolution from the recorded cause and it is applied through a Founder-approved bounded action with evidence; nothing is deleted and no alert is muted. A permanent governed route for blocked messages is Iteration 4 (WC-171), not this contract |
| WC168-R013 | The Founder's decision on the production Meta secret found in the acceptance vault (reset or keep) is recorded; if reset, `meta-login-client-secret` is updated and a Facebook sign-in on Demo is read back |
| WC168-R014 | WC-167 is closed by identifier: R001 and R008 are recorded done with their Demo read-back evidence; R004's Keycloak client read-back moves to WC169-R012; R011's deployed proof is the first Founder sign-in after the WC-168 deployment; R003, R005, R007 and R009 are moved by identifier to WC168-R012 and R013 and to WC-169 (R001, R002, R007, R008) |

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
| G1 | RC-3 was only "possible"; it is real and there are four conflicting prices for the same agent | Descriptor Rs 2,499 (the old "Growth Engine" incl. GST tier); ADR-022 note Rs 1,499 for the entry tier; billing floor analysis Rs 825; Founder statement of 2026-11-20 Rs 2,000 for Starter | FIXED: R006 rewritten to one source. The Founder then decided (2026-11-24) that prices, package names and features are run-time choices made on the Pricing screen, which already offers package code, name, components and authorization (`PackageEditor`); nothing is seeded or hard-coded |
| G2 | The only seeded package cannot be authorized | Baseline SQL says it stays DRAFT because its thread awaits Founder authorization and its publication components are default-off. The components are `DEFAULT_OFF` with activation authority "FOUNDER_SEPARATE_DECISION" in the DMA declaration (`experience-components.v1.json`), so they are an agent decision, not a Demo setting | FIXED: R015 lists the thread rate authorization and the Founder's component decision; applying it to the DMA declaration is WC169-R014 |
| G3 | The RC-1 cause in the first draft was wrong or at least unproven | Rows with no `business_app` grant exist in 11 files, but other tables from those files work | FIXED: cause marked a candidate; R003 requires a governed read first |
| G4 | A new real-database test would be a large item | `scripts/wc124_init_chain_local.sh` and `wc124_db_provisioner.py` already apply the chain locally | FIXED: R003 reuses the existing harness |
| G5 | A fix in init files may not reach Demo | Environment Deployment has a chain-reuse decision keyed on a fingerprint of the chain | FIXED: R003 requires read-back; a changed init file changes the fingerprint, so reconciliation runs. Risk: a longer deployment |
| G6 | Temporal fix as "wait six minutes" is a guess | The scale-down cooldown is 300 seconds; the pool check allows 24 seconds (12 tries of 2 seconds) | FIXED: R011 now waits for zero replicas, not a timer |
| G7 | R012 hid a new feature | No route reads or resolves a blocked outbox row; the service only counts them | FIXED: R012 reads the cause through the bounded job; the permanent route moves to WC-171 |
| G8 | Razorpay reachability was open in WC-169 | Terraform wires the Razorpay test secrets into the Demo runtime (`READY_TEST`) | Closed here; recorded in WC-169 |
| G9 | The iteration is large | 15 requirements across data, web, workflow, pricing and governed reads | FIXED: cut line below |

Init files that create business tables with no `business_app` mention in the same file (static sweep, input to R004, not a verdict): `10-reseller-agency`, `13-customer-acquisition`, `16-provider-registry`, `18-wbe-s7-payment`, `21c-ae01-paid-activation-ordering`, `34-wc095-zero-price-outcomes`, `36-wc120-conversation-whatsapp`, `44-razorpay-checkout-orders`, `45-pre-hire-checkout-orders`, `48-wc112-trial-agent-version`, `50-wc112-coupon-reservations`.

### Counter views and cut line

- The Founder-reserved items (R012 resolution, R013 decision, R015 thread authorization and setting) can stall on a person. If any is still open when the other requirements are read back green, the pull request ships without it and the item moves to WC-169 by identifier. It is not allowed to hold the iteration.
- R003 may show the cause is deeper than a missing grant (for example ownership or an out-of-band revoke). If the fix is larger than one requirement, record it and stop (Stop Conditions).

## Stop Conditions

- The table owner and privileges cannot be read through a governed route: stop and ask the Founder.
- A fix would widen the privileges of `business_app` beyond what it already holds on its own tables: stop.
- The Marketplace and Pricing disagree on price and the authorized source is unclear: stop and ask the Founder.
- The Founder does not approve the blocked-message read: R012 stays open and the rest proceeds.
- A test or gate fails for a reason outside this contract: record it and do not widen scope.

## Implementation Record

Contract written 2026-11-24 with `ROADMAP.md`, WC-169 and WC-170. Implementation authorized by the Founder the same day.

### What was built

| Requirement | Delivered |
|---|---|
| R001, R002 | `ROADMAP.md`, pointers in README, PROJECT_STATE, AGENT-ENTRY (FR-006), BOOTSTRAP and the Copilot instructions, `tests/pipeline/test_roadmap_single_source.py` in the quality-scripts gate |
| R003, R005 | `infrastructure/postgres/init/99zzzzzzzz-wc168-01-provider-registry-runtime-access.sql`; `tests/business-platform.Tests/ProviderRegistry/ProviderRegistryRuntimeAccessPostgresTests.cs` (4 tests, real Postgres, reproduces the Demo state); the Demo read-back follows the deployment |
| R003, R004 (the read) | `scripts/wc168_demo_db_catalog_read.sh` and `infrastructure/postgres/operations/wc168-catalog-read.sql`; `tests/pipeline/test_wc168_catalog_read.py` (5 tests) |
| R006 | Recorded as a finding and split: the Pricing screen already supports run-time package names, features, prices and authorization; the customer price rewiring is WC169-R013 |
| R007 | `LiveMarginBanner` says "Nothing to check yet" for zero checked packages; unit test |
| R008 | The Key Vault menu, page and write route follow the platform Founder grant (`resolvePlatformAccess`); `isKeyVaultPortalAdministrator` removed; tests updated |
| R009 | Page class renamed to `staff-access-page` (it collided with the public landing layout); a Founder sees no request form; the sign-in ID hint shows only to people with no staff role; unit and Playwright tests |
| R010 | `StateView` shows the back arrow only with `back`; staff-aware Connections and Settings wording; clearance below page content for the fixed Emergency Stop button; unit tests |
| R011 | `scripts/wait_for_replicas_drained.sh` polls the old Temporal app's replica count every 5 seconds and continues as soon as it is zero, with an 8-minute safety limit; called before the startup job in `environment-deployment.yaml`; `tests/pipeline/test_wc168_temporal_drain_wait.py` (4 tests including fault injection) |
| R014 | WC-167 closed by identifier (progress table and ledger rows R001 and R008 marked PASS with evidence) |

### The Demo catalog read (Founder-authorized, read-only, 2026-11-24)

Run three times as a temporary Container Apps job with the Business Platform's own database credential by reference, inside a read-only transaction. It read catalog metadata only (no business rows, no secrets) and was deleted each time. Results:

- Connecting role `bp_runtime`, a member of `business_app`. 207 business tables: 191 owned by `bp_owner`, 16 by `wbe_owner`.
- `business.provider_configs` is owned by `bp_owner` with the access list `{bp_owner, bp_verifier=r}`: no privilege for `business_app`. Row-level security is enabled and forced and no policy exists on it. Its siblings `provider_credential_versions` and `customer_provider_connections` were granted explicitly (`business_app=ar`).
- 63 business tables cannot be selected by the application role. Six of them are used by the Business Platform code: `provider_configs` (fixed here) and five WC-120 conversation tables (`conversation_context_observations`, `conversation_context_summaries`, `conversation_data_right_requests`, `conversation_migration_watermarks`, `whatsapp_media`), carried to WC170-R008. The other 57 belong to billing or legacy features the Business Platform does not use.
- Why a grant alone is not enough: the principal handoff (`60-wc124-principal-handoff.sql`) enables and forces row-level security on every table with a tenant column, and `provider_configs` has no policy. The new init file adds both the grants and the policies.

### Test evidence (all in Docker)

| Check | Result |
|---|---|
| .NET real-database tests, Provider registry runtime access | 4 passed |
| .NET Platform access tests (earlier slice, unchanged) | 49 passed |
| Web jest, whole suite | 161 suites passed, 1174 tests passed |
| Web `tsc --noEmit` and Biome format | clean |
| Playwright wc167-access and wc167-connections on chromium at 360, 768 and 1440, light and dark | 48 passed |
| Pipeline tests added for WC-168 (roadmap guard, catalog read, Temporal drain) | passed |
| Init-chain lint | the new init file has no findings; the 15 findings in older files predate this contract and are untouched |
| Requirement ledgers WC-167 to WC-170 | validated |

### Open items that need the Founder

| Item | What is needed |
|---|---|
| R012 | Approval to read the blocked WhatsApp message through the same bounded read-only job, then a decision on the resolution |
| R013 | Decision on the production Meta app secret found in the acceptance vault (reset or keep) |
| R015 | Authorize the thread rate `whatsapp_template_utility` on Pricing, then Rates; say which `DEFAULT_OFF` DMA components you want to sell (the activation itself is WC169-R014); make the package pricing decisions on the Pricing screen |
| R005, R006 read-back | After the deployment: Providers lists providers, and the draft, edit and authorize path is exercised on the Pricing screen |
| R011 proof | First Founder sign-in after the deployment shows the menus with no step on `/access` |

### Deviations from the contract as first written

R004 was redefined from a CI test of the whole init chain to a measured, re-runnable catalog read, because the existing local harness fails the init-chain lint on `main` for older files. R006 was split because the hire price comes from the agent descriptor and changing a payment path belongs with the acceptance pay step.
