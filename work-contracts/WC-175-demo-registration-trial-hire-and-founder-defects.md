# WC-175 - Demo Registration, Trial, Hire And Founder Screen Defects

## Record Control

| Field | Value |
|---|---|
| Work Contract | WC-175 |
| Office | Platform IT Expert (INST-010) |
| Initiative | IB-134 (Demo rollout recovery); defects found after Demo deploy run 45870001597 |
| Founder assignment | Current conversation, 2026-11-27: "first create a work contracts with defects. Next start grooming, analysing and finding a fix for these, starting with whatsapp verification code." |
| Status | DRAFT FOR FOUNDER REVIEW - IMPLEMENTATION NOT AUTHORIZED. Grooming and read-only analysis are authorized; no `src/` or `web/` code is written until the Founder authorizes implementation in the current session. |
| Baseline | `origin/main` at `60e944ea` (PR #654 merged; Demo deployed by run 45870001597) |
| Requirement ledger | [WC-175-requirements.yaml](./WC-175-requirements.yaml) |
| Constitutional basis | C-023, C-059, C-063, C-065 |
| Numbering | WC-168 to WC-173 are reserved by `ROADMAP.md`; WC-174 exists; this contract takes WC-175 |
| Deployment | One Environment Deployment of Demo after merge, then one live re-test with Skill 24 |

## Why This Contract Exists

On 2026-11-27 a throwaway customer was created with `scripts/demo_synthetic_customer.py`, signed in, and walked through
registration, Trial and Hire; the platform logs were read with `az` and the Founder screens were audited in code. The full
evidence is in the session register `defect-register-2026-11-27.md`. The customer can sign in but cannot register, so Trial
and Hire cannot be completed, and several customer and Founder screens mislead or are missing.

## Findings Carried Into This Contract

Evidence class: LIVE = seen on Demo; LOG = platform log; CODE = read in source, not yet seen live; INFERRED = consistent with code and a live symptom.

| Id | Finding | Evidence |
|---|---|---|
| C1 | Registration stops at the WhatsApp code step: `POST /api/v1/identity/registrations/{id}/mobile-verifications` returns 503 `IDENTITY_DEPENDENCY_UNAVAILABLE` and the page says "Delivery could not be confirmed" | LIVE, LOG, CONFIG. Cause proven 2026-11-27: Demo has `IdentityVerification__WhatsApp__Enabled=false`, `WhatsAppCapability__Authority__AllowRegistrationVerification=false`, no authentication template (only the MARKETING invitation template `waooaw_demo_invitation_v1` is approved), and the Founder's standing policy forbids the autopilot to enable it (`scripts/wc134_demo_whatsapp_autopilot.py:333`). Code refuses with `REGISTRATION_VERIFICATION_DENIED`. Not a code defect: the feature built under WC134-R005/R012 was never activated on Demo, yet the page invites the customer to request a code |
| C2 | Hire is disabled and says "Price cannot be shown right now" for every unregistered customer | INFERRED: hire-quote needs a membership; `web/lib/api/hire-quote.ts` maps any non-409 refusal to "unavailable" |
| C3 | Trial checkout lets the customer accept the contract and confirm, then answers 409 `REGISTRATION_REQUIRED` | LIVE |
| C4 | `/billing` is "Page not found"; no customer billing screen or API | LIVE |
| C5 | Profile says organization and billing details are created only when the customer chooses Trial or Hire, but registration (name, business) comes first | LIVE |
| C6 | Connections shows a red "could not be loaded" error for an unregistered customer (403 `CONNECTION_ACCOUNT_REQUIRED`) | LIVE |
| C7 | Profile, Settings and Alerts are placeholders; the registered-customer view is untested | LIVE |
| C8 | The Register page shows a Log in block above the Create account block | LIVE |
| C9 | Registration says "Verified by Google" for any non-Facebook user | CODE |
| C10 | Free Trial checkout lists disabled Razorpay methods; customers opening `/admin/*` are redirected silently while `/founder` shows a 403 page | LIVE |
| C11 | Styling: narrow left-aligned cards on wide screens, a grey "No active work to stop" button on every page that looks disabled, icon-only menu by default | LIVE (screenshots) |
| F1 | Two-factor returns 400 `IDENTITY_ACTION_DENIED` on `/admin/azure-key-vault` and `/founder`; the allow-list in `web/lib/oidc-transaction.ts` omits both | LIVE, CODE |
| F2 | Providers and Agent operation share one menu icon | CODE |
| F3 | On `/founder` pages the menu shows only Founder home and Access; Operations, Pricing, Providers and Key Vault are missing | CODE |
| F4 | Two menu entries named Access (`/access` titled "Staff access", `/founder/access`) | CODE |
| F5 | Operations tab "Pages" means paging alerts and shows humanized machine codes | CODE |
| F6 | Agent operation uses the placeholder `AGENT_TYPE=500` and unexplained columns Asked, Accepted, Tool, Assistant share | CODE |
| F7 | Founder home "Offerability" and Pricing use terms such as "direct contribution", "Day-one exposure" and "Implied margin" without plain explanation | CODE |
| F8 | Founder menu labels are English only; duplicate element id `ops-overview` | CODE |
| D1 | Billing daily scan returns 500 on every run since 2026-11-25: `unrecognized configuration parameter "app.tenant_id"` | LOG |
| D2 | WhatsApp PAGE alert `DEAD_LETTER_AGE_BREACH` open since 2026-11-22 (56 open signals, 3 blocked messages); Business Platform writes about 2,000 warn lines per 9 hours | LOG |
| D3 | Inbound WhatsApp messages are rejected with 403 `PHONE_IDENTITY_PROOF_INVALID`: 319 events since 2026-11-19 (about 40 a day). The check in `WhatsAppJourneyService.cs:571-577` has five triggers (missing message id, phone hash or text, expired proof, more than 5 minutes between sent and verified) and the log names none. The 401 `TOKEN_MISMATCH` events cluster on deploy days and are probably the deploy's own negative checks (to be confirmed) | LOG, CODE |
| D4 | Business Platform uses in-memory, unencrypted data-protection keys | LOG |
| D5 | Keycloak runs in development mode on Demo | LOG |
| D6 | Registration delivery failures log no reason code | CODE, LOG |

## Objectives

| Id | Objective |
|---|---|
| O1 | A customer can register on Demo, then start a Trial and a Hire, end to end |
| O2 | Every customer message says what is true and what to do next |
| O3 | Founder screens are reachable, distinguishable and meaningful to the Founder |
| O4 | Platform failures are visible, not silent, and background jobs do not fail unnoticed |

## Authority And Scope

In scope: the Business Platform identity delivery path and its logging; the web customer and Founder screens named above;
the Billing Engine daily scan; WhatsApp alert and log behaviour; tests; one Demo deployment and one live re-test.

Out of scope: UAT and Production; changing the Founder's WhatsApp spend policy; creating or verifying the Meta business
number (a Founder or Meta action); a Billing page that needs a new billing API (R011 asks only for an honest page);
Email and Apple login (Founder decision); AI replies and model hosting; Razorpay live payments.

Authority limits: no secret value is read or printed; no WhatsApp message is sent to a real person without the Founder's
approval in the current session; synthetic customers are Demo only, run-scoped and deleted afterwards (Skill 24); no
Production or UAT change; every Demo read is read-only unless the Founder approves a named change.

## Canonical Requirement Index

| Id | Requirement |
|---|---|
| WC175-R001 | The cause of C1 is proven from Demo evidence and recorded in the Implementation Record before any fix is written. Satisfied by the 2026-11-27 grooming: live configuration flags, the Founder policy and the dispatcher code (Grooming Log) |
| WC175-R002 | Registration delivery and WhatsApp inbound failures (C1, D3, D6) log a bounded reason code naming which check failed, never a phone number, code or token, so the next failure names its cause |
| WC175-R003 | While registration verification is not active on an environment, the registration page says so plainly ("WhatsApp verification is not available on this Demo yet") and offers no send button that cannot succeed; when active, a delivery failure distinguishes "try again" from "contact support" (C1) |
| WC175-R004 | The inbound 403 events of D3 are classified by trigger using the R002 logging, each is fixed or recorded with the Founder or Meta action it needs, and the 401 events are shown to be the deploy's own checks or fixed |
| WC175-R005 | Hire shows "Complete registration to see the price" and offers registration when the customer has no account, and shows the price once registered (C2) |
| WC175-R006 | Trial and Hire ask for registration before the contract and payment steps, not after confirmation (C3) |
| WC175-R007 | Profile text, Connections and Register match the real flow: no contradiction about when profile details are created, an unregistered customer sees an empty state with guidance rather than a red error, and the Register page shows only the sign-up block (C5, C6, C8) |
| WC175-R008 | Registration names the real identity provider, or none, instead of hard-coding Google (C9) |
| WC175-R009 | A free Trial hides payment-method choices; a customer opening an admin route gets the same plain not-permitted page as `/founder` (C10) |
| WC175-R010 | Customer layout and the stop control are fixed: content uses the screen width sensibly, the stop button looks available when work can be stopped, and the menu shows labels when space allows (C11) |
| WC175-R011 | `/billing` shows an honest page that says what billing is available now and where invoices will appear, until a billing API exists (C4) |
| WC175-R012 | Profile, Settings and Alerts show useful content for a registered customer (name, business, language, notification choices, recent alerts) (C7) |
| WC175-R013 | Two-factor starts from every Founder page, including `/admin/azure-key-vault` and `/founder`; a test enumerates every Founder route against the allow-list (F1) |
| WC175-R014 | Every Founder menu entry has its own icon and one name; the Founder menu on `/founder` reaches Operations, Pricing, Providers, Agent operation, Key Vault and Access (F2, F3, F4) |
| WC175-R015 | Founder wording is plain: the Operations tab is renamed, Agent operation explains Asked, Accepted, Tool and Assistant share and drops the `AGENT_TYPE=500` placeholder, Offerability and Pricing terms have one-line explanations, labels are translated, and `ops-overview` is unique (F5, F6, F7, F8) |
| WC175-R016 | The Billing daily scan succeeds on Demo and its failure is caught by an alert, not found by a log search (D1) |
| WC175-R017 | The open WhatsApp page alert is resolved or acknowledged with a recorded reason, and the standing-alert and heartbeat logging is rate-limited so a standing condition does not write a line every 30 seconds (D2) |
| WC175-R018 | Business Platform data-protection keys persist across restarts and are protected; Keycloak runs in production mode on every environment that is not a local preview, or each is recorded as a Founder-accepted Demo exception (D4, D5) |
| WC175-R019 | After deployment, Skill 24 re-tests registration, Trial, Hire, Billing, Profile, Settings, Alerts and Connections with a throwaway customer, and the Founder screens are reviewed live with a Founder session; every outcome is recorded and the customers are deleted |
| WC175-R020 | PARKED, FOUNDER-RESERVED. Registration verification is configuration, not an environment-specific fix: the same image is promoted to Demo and UAT, and each environment turns it on through its own settings (`IdentityVerification__WhatsApp__*`, `AllowRegistrationVerification`) once the Founder has a Meta-approved AUTHENTICATION template and an approved policy version with its own message and spend ceiling for that environment. The Business Platform verifies the template through the Meta API at runtime. Then a customer receives a code and completes registration |
| WC175-R021 | FOUNDER-RESERVED architecture decision. A throwaway customer can complete registration on a non-Production environment without sending a WhatsApp message, by a default-off path, enabled only by configuration on Demo and UAT and keyed to the existing server-side synthetic marker (ADR-055), so Skill 24 can test Trial and Hire before R020 is live. Not built unless the Founder approves this option |

## Execution Chunks (grooming proposal, dependency order)

| Chunk | Requirements | Outcome | Depends on |
|---|---|---|---|
| A. Registration delivery | R001 (done), R002, R003, R004; Founder-reserved R020, R021 | Failures name their cause; the page tells the truth; customers can register once R020 or R021 is decided | R020 needs a Meta template and a Founder policy; R021 needs a Founder decision |
| B. Customer journey honesty | R005 to R010 | Trial and Hire read truthfully, registration first | A for live proof |
| C. Customer pages | R011, R012 | Billing, Profile, Settings, Alerts are useful | B |
| D. Founder screens | R013, R014, R015 | Founder can reach and understand every screen | none |
| E. Platform hygiene | R016, R017, R018 | Scan works, alert noise gone, keys persist | none |
| F. Live re-test | R019 | Defect register closed with evidence | A to E deployed |

Chunks D and E are independent of A and can proceed in parallel; Docker validation runs once per completed chunk.

## Definition Of Done

1. Every requirement has direct executable evidence in `WC-175-requirements.yaml`: a failing test first where code changes, then passing in the Docker runners (Python with `PYTHONPATH=/workspace:/workspace/scripts`, .NET with `GITHUB_WORKSPACE=/workspace`, web TypeScript).
2. One Demo deployment after merge succeeds, followed by the live re-test of R019 with the Founder-approved throwaway customers, all deleted afterwards.
3. The defect register shows each finding closed with live or log evidence, or recorded with the Founder action it needs.
4. Author review is bound to the exact head commit; the PR is submitted for Founder review and merge. No self-approval.

## Stop Conditions

- The Founder has not authorized implementation for the current session.
- A fix needs a Meta, Google or Razorpay account action, a secret, spend or a Production or UAT change: stop and name the Founder action.
- A WhatsApp message would reach a real person without current-session approval.
- A change needs a new architecture decision, a new billing API or a trust-rule change in Business Platform identity.
- Two reproducible infrastructure failures, or Demo evidence that cannot be reproduced.

## Implementation Record

Not started. Grooming notes are appended below as they are proven.

### Grooming Log

| Date | Item | Result |
|---|---|---|
| 2026-11-27 | Contract created | Draft; findings and requirements recorded; nothing implemented |
| 2026-11-27 | C1 root cause (R001) | Proven. Read-only Demo evidence: Business Platform settings `IdentityVerification__WhatsApp__Enabled=false`, `AllowRegistrationVerification=false`, authority window 2026-11-26T18:10Z to 2026-12-03T18:10Z active, public admission allowed, only the MARKETING invitation template approved. Code: `WhatsAppIdentityVerificationDispatcher.cs:51` throws `REGISTRATION_VERIFICATION_DENIED` when the flag is false, mapped to 503 by `IdentityController.cs`. Founder policy `release/wc134/demo-whatsapp-activation-policy.json` approves invitation messages only, and the autopilot raises "candidate enables registration verification, which the policy does not approve". No WhatsApp message was sent to any real number during the test (the fictitious 555 number was refused before any send) |
| 2026-11-27 | Fix options for C1 | (1) R003 and R002, code only: honest page and reason logs; (2) R020, Founder: authentication template plus policy v2, then autopilot and config change, which sends real code messages and spends within its own ceiling; (3) R021, Founder architecture decision: synthetic-only path for tests. Options 1 can ship alone; 2 is the only fix for real customers |
| 2026-11-27 | D3 | 319 inbound 403s since 2026-11-19 need R002 logging to name the trigger; 401s cluster on deploy days |
| 2026-11-27 | Parked | Founder, 2026-11-27: park the registration fix; it must stay configurable by environment because one image is promoted to UAT and Demo. Blocked on a Meta authentication template: the Founder's Meta login is under a new-device security hold. R003 and R002 stay in scope as environment-neutral code |
| 2026-11-27 | D1 root cause (R016) | Proven from the traceback and code. `meter/service.py:760` `run_daily_scan` reads `wallet_buckets` joined to `customer_wallets` on a session with no tenant set. `infrastructure/postgres/init/12-billing-engine.sql:139` defines the row-security policy with `current_setting('app.tenant_id')` (no missing-ok), so a session without it fails. The scan is cross-tenant by design, so setting one tenant is wrong. Other billing code sets a different name, `app.current_tenant_id` (`reconciliation/authority.py:92`), a second inconsistency. Effect: threshold alerts to customers have not run since the first logged failure (2026-11-25 00:30Z, nightly). Proposed fix: a security-definer function owned by the table owner that returns the active customer ids, executable by `wbe_app`, called by the scan; a real-PostgreSQL test; a nightly failure alert. Needs a data-owner decision on the function, so it is a design step, not a one-line patch |
| 2026-11-27 | D2 root cause (R017) | `ConversationOperationsService.cs` raises `DEAD_LETTER_AGE_BREACH` (PAGE) when the oldest blocked outbound message is older than 30 minutes. One blocked message from 2026-11-22 08:26Z is still in the outbox, so the alert stays open and the hosted service logs the heartbeat and the alert every 30 seconds (about 2,000 lines per 9 hours). Fix: the Founder resolves or retries that message on the Operations page, and standing-alert logging is limited to once per change or per hour |
| 2026-11-27 | Not yet checked | Meta number verification expiry cannot be read without the provider token; it is a Founder action either way |
