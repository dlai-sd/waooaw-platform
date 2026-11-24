# WC-167 - Acceptance Demo Readiness (Founder Admin, Connections, Pricing And Enablement)

## Record Control

| Field | Value |
|---|---|
| Work Contract | WC-167 |
| Office | Platform IT Expert (INST-010) |
| Initiative | IB-167 |
| Founder assignment | Current conversation, 2026-11-24: report that a Founder sign-in on Demo shows no administrative menu and no discount table, and that the Connections page fails for Founder and customers; "let me know rca of these points. Create new work contract with high level objectives as 5 items we need to do and we will use this work contract to iron out defects and to build required stuff for this testing"; then, on the same day, "add them" for the three additional findings AF-1 to AF-3 |
| Status | IMPLEMENTATION_AUTHORIZED. Founder, 2026-11-24: "you are authorized to implement and update required constitutional artifacts as appropriate with light weight documentation approach". Work proceeds in slices; evidence is in each PR body; this record carries only status |
| Baseline | `origin/main` at `2d5daca6` (PR #636 merged; slices B and C build on PR #637; the contract itself was first merged at `dc6bf836`) |
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
| Cause (narrowed 2026-11-24) | The Founder's `/access` result read "Signed in as **yogesh.khandge@dlaisd.com**" with the request form shown, which means the email **is** the configured Founder address and **is** verified. That removes (a) and (c). What remains is (b): the stored Founder grant is tied to a different sign-in identity (subject) than the one in use, for example because the first verified sign-in after a Demo reset came through the other provider, or the identity provider's user was re-created. `PlatformAccessStore.ResolveRolesAsync` returns a role only when the grant has no subject yet or the subject equals the signed-in one, and `ReconcileFoundersAsync` re-binds a subject only when the configuration names one, which Demo's settings do not. (b) is the most likely cause and is not read from the database. |
| How to settle it | Free check: sign in with the other provider (Google or Facebook) and see whether Pricing and Providers appear. Lasting fix (R001, R010): `/access` now shows the person's own sign-in ID; the Founder gives it, and it is pinned as `subject` in `infrastructure/platform-settings/demo.json`, so the role re-attaches on every deployment and survives a reset. The exact-match rule is not loosened. |

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

### Additional findings (added to scope by the Founder on 2026-11-24: "add them")

- **AF-1 Old production Meta secret in the acceptance vault.** On 2026-11-24 the vault held the production Meta app id and secret (`2590813568086235`, "WAOOAW Customer Login", used by the Keycloak Facebook broker through `meta-login-client-secret` in the private vault). Both were replaced with the acceptance app's and the old versions were disabled (not purgeable: purge protection is on). The old values were readable by vault readers for about 80 minutes. Open decision: reset the production app secret or accept the residual risk. A reset also changes the live Facebook login, so it needs the new value in `meta-login-client-secret` and a Keycloak restart, through the governed path.
- **AF-2 Log volume.** The Business Platform logged about 281 thousand lines in 6 hours, almost all `Microsoft.EntityFrameworkCore.Database.Command` text at Information level. The Demo workload already lowers two other categories for the same reason (`modules/workload/main.tf`, the Demo-only `Logging__LogLevel__...` block); the database command category was left at the default.
- **AF-3 Standing PAGE alert.** `WhatsApp operations alert: Code=DEAD_LETTER_AGE_BREACH Severity=PAGE` repeats every 30 seconds with `TriggeredAt=2026-11-22 08:56:11`. By `ConversationOperationsService` it fires when the oldest blocked outbound message is older than 30 minutes; the heartbeat shows `BlockedOutboxCount=1`. It is a real unresolved blocked message, not noise, and it pollutes the evidence of any acceptance run while it stands.

## Review Of PR #618 (WC-149, merged) Against This Contract

Method: read the merged code and tests at `dc6bf836`; nothing was run and no page was viewed rendered. "Gap" means a difference from WC-167, not a claim that WC-149 failed its own contract.

| # | Finding | Evidence | Requirement |
|---|---|---|---|
| RV-1 | **Connections is offered to everyone but works only for a customer with an active membership.** The menu shows Connections to every signed-in customer, yet `ProviderConnectionsController` is `[CustomerIdentityRoute(requiresMembership: true)]`. A person without a membership is refused and the page says "not permitted to manage this connection". The Connect button is drawn only when the list loads (`ConnectionsWorkspace.tsx`), so one refusal also removes the way forward. WC149-R008 says "a customer can connect" without stating the membership precondition, and no test separates "sign in again", "no membership" and "not permitted". | `web/components/connections/ConnectionsWorkspace.tsx`, `web/lib/provider-connections-server.ts` (`fallbackProblems`), `ProviderConnectionsController.cs` | R002 |
| RV-2 | **The Meta flow is untested against the acceptance app type.** It builds the classic login dialog (`dialog/oauth?...&scope=pages_show_list,pages_manage_posts,pages_read_engagement`) on Graph `v21.0`, set in `modules/workload/provider-credentials.tf` (`ProviderConnections__Meta__GraphVersion`). The acceptance app uses the Pages use case (Facebook Login for Business), which may expect a `config_id`, and `v21.0` is old next to the `v27.0` the app defaults to. Whether Meta accepts the classic dialog for this app is unproven. | `MetaGraphClient.cs` (`AuthorizationUrl`, `DefaultGraphVersion`) | R005 |
| RV-3 | **A Founder-only screen redirects instead of showing a denied page.** `/admin/providers` sends a non-Founder to `/home`. This is deliberate: WC-148 designed and tested it so the screen's existence is not disclosed, and the `(founder)` route group uses `/403` as UX-SHELL-03 expects. **No change made (reviewed 2026-11-24).** The real point stands: the `meta` row, which holds the app id and secret as JSON `{"appId","appSecret"}`, is reachable only through that screen, so RCA-1 blocks Meta registration. | `web/app/(application)/admin/providers/page.tsx`, `web/__tests__/app/application/providers-page.test.tsx` | R001, R005 |
| RV-4 | **UI quality is partial.** Good: 10 component tests (loading, empty, error with retry, https-only navigation, revoke dialog with focus return, return codes). Gaps: the customer page borrows admin styling and components (`providers-admin` class, `PricingMessage` from admin pricing); I found no responsive, light and dark, or axe specs for `/connections`. | `ConnectionsWorkspace.test.tsx`, `connections/page.tsx`, `web/tests/e2e` | R006 |
| RV-5 | **An assumption no longer holds.** WC-149 says test users and app roles work in development mode. Meta now refuses to create test users, so the tester is a dedicated real account with the Tester role, and the runbook and ADR-055 wording must change. | `WC-149-...md` line 49; session of 2026-11-24 | R005 |

What conforms and should stay: tokens exist only in Key Vault, OAuth state is single-use, the redirect address must be https, revoke deletes the secret version, and the browser receives only fixed problem codes.

## Authority And Scope

### In scope

1. Founder administrative access on Demo (O1): make the grant match the Founder's real sign-in; make the reason visible on `/access`; handle the two sign-in providers so one person is one identity or is told plainly why not.
2. Honest Connections errors and the membership path (O3): separate "sign in again", "complete registration or hire first" and "not permitted" in the browser message; confirm a customer with an active membership loads and connects.
3. Pricing owner wiring for Demo (O2): provide the workload credential and Billing Engine settings through the Terraform workload and the governed ADR-046 path, so the coupon screen works; then enter the partial-discount coupon through the screen.
4. Acceptance enablement (O4): set `acceptance_client_id` in the Demo profile, apply the Keycloak provisioning client, store its secret, and set `acceptance_synthetic_tenants_enabled` for Demo through the deployment.
5. Sandbox completion and first calibration run (O5): register the Meta acceptance app on the provider screen, produce the saved tester session, seed the coupon, confirm 12 of 12 secrets, run the workflow once and triage the report.
6. UI styling and testing for every page or component changed above (the Founder menu and `/access`, the Connections page and its messages, the pricing and coupons screens, the provider screen): apply the visual system and test layers listed in WC167-R006, and fix styling and layout defects found on those pages during Demo checks. A UI defect found on an in-scope page is fixed under this contract, not deferred.
7. AF-1: record the Founder's decision on the production Meta app secret; if a reset is chosen, do it through the governed path and read the Facebook login back.
8. AF-2: lower the database command log category for the Demo Business Platform through the Terraform workload, keeping the audit and security categories unchanged.
9. AF-3: find why the blocked outbound message is blocked, resolve it through the governed WhatsApp operations path (not by deleting the row or muting the alert), and show the alert clearing.

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
| WC167-R007 | The Founder's decision on the production Meta app secret (AF-1) is recorded; if a reset is chosen, `meta-login-client-secret` and the Keycloak Facebook broker carry the new value and a Facebook sign-in on Demo is read back; the old acceptance-vault versions stay disabled |
| WC167-R008 | On the Demo Business Platform the database command log category is at Warning or above while audit, security and application categories are unchanged; Demo ingestion for the app falls measurably (lines per hour before and after) |
| WC167-R009 | The blocked outbound WhatsApp message behind `DEAD_LETTER_AGE_BREACH` has a recorded cause and is resolved through the governed operations path; the PAGE alert stops repeating and no row was deleted and no alert muted to achieve it |
| WC167-R010 | The staff access screens (`/access` for requesting and, for the Founder, deciding; `/founder/access`) use the portal page layout and control styling, are reachable from the menus (an "Access" item for staff, "Staff access" in every signed-in person's account menu, an "Access" item in the Founder navigation), show a signed-in person their own sign-in ID, and pass the R006 test layers in light and dark at 360, 768 and 1440 |
| WC167-R011 | A Founder whose environment opts in (`rebind_on_start`, Demo only, never with a configured `subject`) keeps the Founder role across deployments without any step on `/access`: each start releases the stored sign-in tie and records `FOUNDER_SUBJECT_RELEASED`, and the next verified sign-in with the configured email ties it again; another identity gets nothing in that window; UAT and production keep the strict tie; the rule is written into policy A2 |

## Definition Of Done

1. Every requirement has executable evidence at the exact head (tests in Docker) and, where it concerns Demo, a read-back from Demo. For every changed page, the component tests, the Playwright responsive, theme and accessibility checks, lint and the production build pass in Docker, and the PR body shows screenshots of the changed pages at 360x800 and 1440x900 in light and dark.
2. Each slice is authorized by the Founder before code is written; platform state refreshed; PR body prepared with `scripts/prepare_pr_body.sh`; author review recorded; the Founder merges.
3. No requirement is reported passed on a claim: an unreadable witness is NOT-WITNESSED.

## Stop Conditions

- A fix that would grant a role from a token claim or from manual database edits.
- Any step that deletes the blocked outbound row, mutes the PAGE alert, or hides the symptom instead of resolving the cause (AF-3).
- A reset of the production Meta app secret that is not paired with the new value in `meta-login-client-secret` and a Facebook sign-in read-back (AF-1).
- A need to hold or print a secret value.
- RCA-1 or RCA-2 shows a cause outside the Business Platform or Keycloak configuration that the Founder has not reviewed.

## Implementation Record

**Slice order (proposed):** S1 (R001, after the `/access` result), S2 (R002), S3 (R003), S4 (R004), S5 (R005), then S6 (R007 and R008, one small Terraform change), S7 (R009, after the cause is read from the WhatsApp operations path) and the AF-1 decision (R007) whenever the Founder decides. R006 is not a slice of its own: it is the UI quality bar that S1, S2 and S3 each carry, so no slice that touches a page merges without its styling and tests.

**Progress (updated per slice, evidence in the PR body):**

| Slice | State |
|---|---|
| Slice A (PR #636, merged) | R002 done: Connections separates "sign in again" and "no customer account yet", each with one next step, and keeps "not permitted" for a real permission refusal (component and route tests, tsc and lint pass). R008 done in code (Demo-only Warning for the database command category; Demo read-back after the next deployment). R004 partly done: `acceptance_client_id` and `telemetry_workspace_id` set in the Demo profile. The vision note joins the repo as `strategy/customer-digital-presence-vision-note-2026-11-24.md` (working note, not a decision). |
| Slice B (this PR) | **R006 done for `/connections`:** a Playwright spec (`web/tests/e2e/wc167-connections.spec.ts`) runs 11 checks at 360x800, 768x1024 and 1440x900 (33 runs, all passing): each error state, the empty state and the no-admin-navigation check, in light and dark, with no sideways scroll and zero serious or critical axe findings. **It found and fixed a real defect:** in dark mode the error text (`#b42318` on `#0b1117`) had contrast 2.88 against the required 4.5; the style now uses the theme's `--color-error`, and the dark success colour uses `--green`. **R004 (flag):** `acceptance_synthetic_tenants_enabled` is set for Demo in `infrastructure/platform-settings/demo.json` (the repository-owned base layer; a test pins it on for Demo only); it takes effect on the next Demo deployment. The earlier WC-159 guard (`SyntheticEffectsTests.WC159_R001_TheShippedSettingsAreOffAndTheWorkloadModuleRefusesProduction`) required the setting to be absent from `demo.json`; it now requires it on for Demo and still forbids it for UAT and production, and WC159-R001 itself (refused for production in three places) is unchanged. |
| Findings of Slice B | **R009:** the stuck message cannot be read from outside the database. The logs show only `BlockedOutboxCount=1` and `OpenSignalCount=26`; the reason is in `business.conversation_outbox.blocked_reason`. The code has no route to read or resolve a blocked outbox row, and the repository has no runbook for it, so no governed resolution exists yet. Needed: a read-only probe through the private runner, then the owner's decision. **R003:** blocked by design (CB-021): the Business Platform has no ADR-046 workload credential and no Billing Engine address on Demo, and cloud credential issuance is still undesigned, so the pricing owner cannot be wired without breaking ADR-046. **R004 (Keycloak):** the Demo realm is built by a migration job and no code creates and stores the `waooaw-acceptance-provisioner` client secret, so applying it means changing a live identity provider's realm; it needs the Founder's explicit approval. **R001:** the configured Founder in `infrastructure/platform-settings/demo.json` is `yogesh.khandge@dlaisd.com`; the role is only granted when the signed-in account has that exact verified email, so a Google or Facebook sign-in with another email gets no Founder menu. |
| Slice C (this PR) | **R010 done in code and tests:** `/access` and `/founder/access` now use the portal page layout and control styling (they were bare, unstyled components); `/access` shows the person's own sign-in ID; menus: "Access" for staff in the side menu, "Staff access" in every signed-in person's account menu, "Access" in the Founder navigation. Tests: 109 Jest tests (new: token-subject helper, sign-in ID display, account menu link) and `web/tests/e2e/wc167-access.spec.ts` (5 checks, all passing at 360, 768 and 1440 in light and dark with zero serious axe findings), using new fixture endpoints for the staff-access routes. **R001 lasting fix is ready:** once deployed the Founder reads their sign-in ID on `/access` and gives it for pinning in `infrastructure/platform-settings/demo.json`. **R001 cause narrowed:** the email matches (see RCA-1). |
| Slice D (this PR) | **R011 done in code and tests:** `rebind_on_start` option (default off) for a configured Founder; the store releases a BOOTSTRAP grant's stored sign-in tie at start and records `FOUNDER_SUBJECT_RELEASED` (new init file `99zzzzzzzz-wc167-01-founder-subject-release-event.sql`); Terraform, deployment-input validation and Demo settings carry the flag; policy A2 updated. Real-Postgres tests (release, no release when off or when a subject is configured, intruder gets nothing in the window) and Python input tests pass. The Demo read-back (Founder menu after the next deployment, with a first sign-in as the Founder) is still to do |
| Not started | R001 pin (no longer needed once R011 deploys; the Founder role follows the configured email, and the first Founder sign-in after a deployment re-ties it), R005 (follows R001), R007 (needs the Founder's decision), R009 (needs the read-only probe), R003 and R004 Keycloak (need the Founder's decision as above) |
| R006 so far | Done for `/connections`, `/access` and `/founder/access`. The pricing and coupons screens and the provider screen carry the same bar when they change |
