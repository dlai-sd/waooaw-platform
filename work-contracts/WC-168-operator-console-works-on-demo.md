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
| RC-1 Providers outage: the Business Platform database role is denied on `business.provider_configs` | Web log `web.admin.providers.list_failed` status 500 at 09:23 UTC; Business Platform log `Npgsql.PostgresException 42501: permission denied for table provider_configs` on `SELECT ... FROM business.provider_configs` | Error confirmed. Cause not yet proven. Candidate: `16-provider-registry.sql` creates the table without `SET LOCAL ROLE bp_owner`, so the table may not inherit the default grants set in `02-users-and-permissions.sh`. Owner and privileges have not been read |
| RC-2 Other tables may share the defect | Same init pattern across older init files | Unproven. A sweep is part of this contract |
| RC-3 Pricing lists zero packages while the Marketplace shows "From Rs 2,499" | Pricing dashboards answer HTTP 200 with an empty package list | Unproven. Two price sources are possible |
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
| WC168-R003 | The cause of RC-1 is proven by a bounded, read-only, Founder-approved read of the table owner and privileges on Demo; the fix creates or grants so that `business_app` can read every table it uses; a test applies the whole init chain in a real database and asserts that `business_app` can select from every business table the application queries |
| WC168-R004 | The RC-2 sweep lists every init-chain table whose owner is not `bp_owner` or whose privileges for `business_app` are missing, fixes them at their source, and records the list in the contract |
| WC168-R005 | After deployment `/admin/providers` on Demo lists providers, the Founder can open the Meta provider row, and web logs show no `list_failed`; no credential value is displayed or logged |
| WC168-R006 | DMA Starter, Runner and Winner exist as authorized packages with components and cost recipes from `dma-bundle-definitions.md`; the Marketplace price equals the authorized price; the contract names the single price source; a test proves the Marketplace and Pricing agree |
| WC168-R007 | The Pricing Overview does not say "Healthy" when zero packages were checked |
| WC168-R008 | The Azure Key Vault page and menu appear for a signed-in Founder through the platform Founder grant, still refuse everyone else, and no longer depend on a hard-coded email in the visibility rule |
| WC168-R009 | The Access screen has no layout gap; a person who already holds a staff role sees no request form; the stale sign-in ID hint is removed; the screen passes the WC-167 R006 layers in light and dark at 360, 768 and 1440 |
| WC168-R010 | Connections and Settings tell staff without a customer account what to do in staff terms; the "Try again" and "Browse Marketplace" buttons carry no back arrow; the floating stop box never overlaps page content; each passes the WC-167 R006 layers |
| WC168-R011 | The Temporal startup qualification waits up to six minutes for the previous copy to drain and still refuses a pool that is genuinely busy; a fault-injection test covers both |
| WC168-R012 | The blocked WhatsApp message behind DEAD_LETTER_AGE_BREACH has a recorded cause and is resolved through a governed operations route; nothing is deleted and no alert is muted; the Founder approves the read first |
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

## Stop Conditions

- The table owner and privileges cannot be read through a governed route: stop and ask the Founder.
- A fix would widen the privileges of `business_app` beyond what it already holds on its own tables: stop.
- The Marketplace and Pricing disagree on price and the authorized source is unclear: stop and ask the Founder.
- The Founder does not approve the blocked-message read: R012 stays open and the rest proceeds.
- A test or gate fails for a reason outside this contract: record it and do not widen scope.

## Implementation Record

Contract written 2026-11-24 with `ROADMAP.md`, WC-169 and WC-170. Implementation not yet authorized.
