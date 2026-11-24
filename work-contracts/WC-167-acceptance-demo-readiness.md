# WC-167 - Acceptance Demo Readiness (Founder Admin, Connections, Pricing And Enablement)

## Record Control

| Field | Value |
|---|---|
| Work Contract | WC-167 |
| Office | Platform IT Expert (INST-010) |
| Initiative | IB-167 |
| Founder assignment | Current conversation, 2026-11-24: report that a Founder sign-in on Demo shows no administrative menu and no discount table, and that the Connections page fails for Founder and customers; "let me know rca of these points. Create new work contract with high level objectives as 5 items we need to do and we will use this work contract to iron out defects and to build required stuff for this testing" |
| Status | CONTRACT_AUTHORED. The RCA below is for Founder review. Any `src/`, `web/` or Terraform change starts only when the Founder authorizes that slice in the conversation |
| Baseline | `origin/main` at `dc6bf836` (PR #634 merged) |
| Branch | `ib/167/acceptance-demo-readiness` |
| Decisions | ADR-054 and ADR-055 (accepted); ADR-046 (service identity: no shared token may carry actor or role) |
| Requirement ledger | [WC-167-requirements.yaml](./WC-167-requirements.yaml) |
| Constitutional basis | C-023, C-049, C-063, C-065, C-080 |

**Cross-cutting rule for O1 to O3 and O5:** every screen, component or message touched under this contract is styled to the visual system and tested to the UI acceptance layers named in WC167-R006. The UI is not done when the API answers; it is done when the page is styled, accessible, responsive and covered by tests.

## Why This Contract Exists

The acceptance harness (WC-158 to WC-163) and its vault, secrets seeding and deployment identity (WC-164 to WC-166) are in place. Five Founder tasks still stand between the repository and the first Demo calibration run. Two of them are blocked by product defects found on 2026-11-24, and a third by a known configuration gap. This contract lists the five objectives and the defects to be fixed under them.

## The Five Objectives

| # | Objective | Founder task it unblocks |
|---|---|---|
| O1 | A Founder signed in on Demo sees and can use the administrative screens (Pricing, Providers, Azure Key Vault) | Reach the discount table and the provider screen |
| O2 | The Pricing admin can create the partial-discount test coupon on Demo, and the code reaches the acceptance vault | Coupon for journey S10 (`WC107-R012`) |
| O3 | The Meta acceptance app (`3540811869424622`) is registered in the product and a customer Connections page loads, connects the tester Page and fails honestly | Meta registration and journeys S6 to S9 |
| O4 | Acceptance enablement is applied: `acceptance_client_id` in the profile, Keycloak provisioning client and secret, `acceptance_synthetic_tenants_enabled` true on Demo | Synthetic customers can be created and removed |
| O5 | The sandbox is complete (12 of 12 secrets, saved tester session) and one calibration run has produced a report that is triaged | First evidence for `WC107-R019` |

## Root Cause Analysis (read from Demo on 2026-11-24, read-only)

Method: Log Analytics workspace `law-waooaw-demo-validation`, the Container App `ca-demo-business-platform` environment and the repository at `dc6bf836`. No secret was read and nothing was changed.

### RCA-1: Founder sees no administrative menu

| Item | Finding |
|---|---|
| What the screen does | `web/app/(application)/layout.tsx` shows Pricing when `platformAccess.administrator` is true and Providers when `platformAccess.founder` is true. Both come from `GET /api/v1/platform/me/roles`. |
| What the server does | Roles are never taken from the token. `PlatformRoleClaimsTransformation` adds a role only when `PlatformRoles.TryIdentity` passes (valid subject, `email_verified = true`, valid email) and a stored grant matches the verified email. A bootstrap grant with no subject binds to the first verified sign-in; a later sign-in with the same email but another subject gets no role (`PlatformAccessStore.ResolveRolesAsync`). |
| Evidence | The Business Platform logged "Founder grants reconciled from configuration: count=1" on every start, so one Founder is configured (`PlatformAccess__Founders__0__Email`, a `@dlaisd.com` address, no subject). At 04:51:56 `PlatformAccess.MyRoles` ran for the Founder's page load and the menu showed no admin items, so it returned `founder = false`. |
| Cause (confirmed part) | The signed-in identity did not match the single configured Founder grant. |
| Cause (not yet proven) | One of: (a) the sign-in email is not the configured address (Demo offers only Google and Facebook, and a Facebook account may carry a different email); (b) the Founder first signed in with one provider and now uses the other, so the stored subject differs; (c) the token has no verified email. The realm sets `trustEmail` for both providers in the repository, which makes (c) unlikely. |
| How to settle it | Open `https://cp.demo.waooaw.com/access` while signed in. It prints "Signed in as <email>" or "needs a verified email". That one screen separates (a), (b) and (c). |

### RCA-2: Connections page says "You are not permitted to manage this connection"

| Item | Finding |
|---|---|
| What the screen does | The text is the browser's message for the code `CONNECTION_FORBIDDEN`. The server layer maps every upstream 401 and 403 to that code (`web/lib/provider-connections-server.ts` `fallbackProblems`), so many different causes show one sentence. |
| Where it is refused | `ProviderConnectionsController` is `[CustomerIdentityRoute(requiresMembership: true)]`. `CustomerMembershipMiddleware` resolves the signed-in actor to an active customer membership before the controller runs, and answers `403 IDENTITY_ACTION_DENIED` when there is none (`MembershipRequired` or `MembershipInactive`). |
| Evidence | At 04:52:24 and 04:52:26 (the page load and "Try again") the Business Platform ran the membership lookup (`identity.actor_bindings`, `app.current_membership_id`) and **no `ProviderConnections` controller action followed**; none ran in the previous 3 hours. The same token passed `MyRoles` and `BrowseMarketplace` at 04:51:56, so the token is valid and the marketplace route does not need a membership. |
| Cause (confirmed part) | The request is rejected by the membership check before reaching the controller. |
| Cause (likely, not proven) | The signed-in accounts have no active customer membership, because membership is created by registration and the first hire or trial, and `WC107-R019` already records that synthetic and test sign-ins cannot complete Registration. The Founder is not a customer either. |
| Defect regardless of the cause | A signed-in person without a membership is told they lack permission, instead of being told to complete registration or to hire first. |

### RCA-3: Even with the menu, the discount table would not work on Demo (known, CB-021)

| Item | Finding |
|---|---|
| Evidence | `ca-demo-business-platform` has no `WAOOAW_WORKLOAD_CREDENTIALS` and no `BillingEngine__BaseUrl` or `BillingEngine__OpsAuthToken`; it has `BillingEngine__RelationshipWorkspaceBaseUrl` and `WAOOAW_WID_WORKLOAD`. `Program.cs` registers `UnconfiguredPricingAdminGateway` (lines 528 and 532) in that state. |
| Cause | The Demo workload is not wired to the Billing Engine pricing owner under ADR-046, which is the open blocker CB-021. |
| Effect | `/admin/pricing/coupons` returns 503 even for a Founder, so the coupon cannot be entered until this is configured. |

### Other findings (recorded, not in scope unless the Founder adds them)

- **Old production Meta secret in the acceptance vault.** On 2026-11-24 the vault held the production app id and secret; both were replaced with the acceptance app's and the old versions were disabled. Whether to reset the production app secret is the Founder's decision.
- **Log volume.** The Business Platform logged about 281 thousand lines in 6 hours, almost all Entity Framework command text at Information level.
- **Stale alert.** `WhatsApp operations alert: Code=DEAD_LETTER_AGE_BREACH Severity=PAGE` repeats since 2026-11-22.

## Authority And Scope

### In scope

1. Founder administrative access on Demo (O1): make the grant match the Founder's real sign-in; make the reason visible on `/access`; handle the two sign-in providers so one person is one identity or is told plainly why not.
2. Honest Connections errors and the membership path (O3): separate "sign in again", "complete registration or hire first" and "not permitted" in the browser message; confirm a customer with an active membership loads and connects.
3. Pricing owner wiring for Demo (O2): provide the workload credential and Billing Engine settings through the Terraform workload and the governed ADR-046 path, so the coupon screen works; then enter the partial-discount coupon through the screen.
4. Acceptance enablement (O4): set `acceptance_client_id` in the Demo profile, apply the Keycloak provisioning client, store its secret, and set `acceptance_synthetic_tenants_enabled` for Demo through the deployment.
5. Sandbox completion and first calibration run (O5): register the Meta acceptance app on the provider screen, produce the saved tester session, seed the coupon, confirm 12 of 12 secrets, run the workflow once and triage the report.
6. UI styling and testing for every page or component changed above (the Founder menu and `/access`, the Connections page and its messages, the pricing and coupons screens, the provider screen): apply the visual system and test layers listed in WC167-R006, and fix styling and layout defects found on those pages during Demo checks. A UI defect found on an in-scope page is fixed under this contract, not deferred.

### Out of scope and prohibited

- Any shared token carrying actor, role or step-up; any static certificate (ADR-046).
- Granting a staff role by token claim, by editing the database by hand, or by weakening `TryIdentity` (verified email and subject stay required).
- Production, UAT, the exploratory companion and promotion gating.
- Handling any secret value: the Founder enters values; the author only moves them through stdin.
- Applying Terraform or running the acceptance workflow without the Founder's approval in the conversation.

## Inputs

| Input | Status |
|---|---|
| Acceptance vault `kv-waooaw-demo-acc`, 9 of 12 secrets | Present; missing: coupon, saved session, Keycloak provisioner secret |
| Acceptance identity `id-waooaw-demo-acceptance` client id | `7de8ce13-4b69-40e0-b0fe-8f56a4c5f923` (read 2026-11-24) |
| Meta acceptance app `3540811869424622` and tester Page `1469698226221094` | Present; Page token valid and never expiring |
| The Founder's `/access` screen result | Not yet provided; needed to close RCA-1 |
| Result of a customer completing a trial on Demo | Not yet provided; needed to close RCA-2 |

## Canonical Requirement Index

| ID | Obligation |
|---|---|
| WC167-R001 | A configured Founder who signs in on Demo gets `founder = true` from `/api/v1/platform/me/roles` and sees Pricing, Providers and Azure Key Vault; the cause of RCA-1 is proven and recorded |
| WC167-R002 | A signed-in person without a customer membership, or with an expired session, gets a distinct, honest message on Connections instead of "not permitted to manage this connection"; a customer with an active membership loads the list |
| WC167-R003 | The Demo pricing owner is configured through the governed workload path (no shared token carrying actor or role), and the Founder can create the partial-discount coupon on the coupons screen |
| WC167-R004 | The Demo profile carries `acceptance_client_id`; the Keycloak provisioning client exists with its secret in the vault; `acceptance_synthetic_tenants_enabled` is true on Demo; each is read back from Demo |
| WC167-R005 | The vault holds 12 of 12 secrets, the Meta app is registered in the product, one Demo calibration run produced a valid report, and every NOT-WITNESSED or FAIL item is triaged with an owner |
| WC167-R006 | Every UI page or component changed under R001 to R005 follows `hybrid-visual-system-contract.md` and `constitutional-ux-vocabulary.md` and passes the layers of `hybrid-ui-acceptance-contract.md`: Jest and Testing Library component tests (states, keyboard, accessible names, error recovery); Playwright at 360x800, 768x1024 and 1440x900 with no horizontal overflow (UX-RESP-01); light and dark themes; loading, error, empty and denied states (a non-Founder sees `/403` without Founder navigation, UX-SHELL-03); axe with zero critical violations; Next.js lint, strict TypeScript and production build; at least 90 percent changed interactive line coverage |

## Definition Of Done

1. Every requirement has executable evidence at the exact head (tests in Docker) and, where it concerns Demo, a read-back from Demo. For every changed page, the component tests, the Playwright responsive, theme and accessibility checks, lint and the production build pass in Docker, and the PR body shows screenshots of the changed pages at 360x800 and 1440x900 in light and dark.
2. Each slice is authorized by the Founder before code is written; platform state refreshed; PR body prepared with `scripts/prepare_pr_body.sh`; author review recorded; the Founder merges.
3. No requirement is reported passed on a claim: an unreadable witness is NOT-WITNESSED.

## Stop Conditions

- A fix that would grant a role from a token claim or from manual database edits.
- A need to hold or print a secret value.
- RCA-1 or RCA-2 shows a cause outside the Business Platform or Keycloak configuration that the Founder has not reviewed.

## Implementation Record

Not started. The RCA above is the first deliverable. Slice order proposed: S1 (R001, after the `/access` result), S2 (R002), S3 (R003), S4 (R004), S5 (R005). R006 is not a slice of its own: it is the UI quality bar that S1, S2 and S3 each carry, so no slice that touches a page merges without its styling and tests.
