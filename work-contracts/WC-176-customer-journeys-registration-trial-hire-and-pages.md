# WC-176 - Registration, Trial, Hire And Customer Pages To Full Extent

## Record Control

| Field | Value |
|---|---|
| Work Contract | WC-176 |
| Office | Platform IT Expert (INST-010) |
| Initiative | IB-134 (Demo rollout recovery), continuing WC-175 |
| Founder assignment | Current conversation, 2026-11-27: "create new work contract and include remaining defects, required items for trial and hire completion after grooming it by doing end to end journeys using current code so be it defect or be it enhancement, we shall now deliver registration, trial, hire to full extent along with customer login pages like alerts, billing, profile, settings." |
| Status | GROOMED, AWAITING FOUNDER REVIEW OF SCOPE AND THE SIX FOUNDER DECISIONS. Implementation proceeds chunk by chunk on the Founder's current-session direction; a requirement that names a Founder decision stops at that decision. |
| Baseline | `origin/main` at `521b156e` (PR #657 merged: WC-175 R023 to R025, the Founder's approval of professionals; R026 is its live check) |
| Requirement ledger | [WC-176-requirements.yaml](./WC-176-requirements.yaml) |
| Constitutional basis | C-023, C-059, C-063, C-065 |
| Relationship to WC-175 | WC-175 keeps its open items (R016 Billing scan, R017 alert noise, R018 keys and Keycloak mode, R019 live re-test); WC-176 takes everything else needed to deliver the customer journeys |
| Deployment | One Demo deployment per completed chunk, then the live run of Skill 24 |

## Why This Contract Exists

WC-175 repaired what blocked a customer on Demo. Walking the journeys again on the current code (three live probes as a
registered throwaway customer and four read-only traces of the code) shows that a customer can now register, but the
journeys do not yet end in a working, billed agent, and several customer pages are unfinished. This contract lists what
stands between today's code and "registration, Trial and Hire work to their full extent, with Alerts, Billing, Profile and
Settings complete", each item marked as a defect (should already work) or an enhancement (not built yet).

## How It Was Groomed

| Method | What it showed |
|---|---|
| Live: registered throwaway customer, walk and Trial journey (2026-11-27) | Registration with the synthetic code works end to end; Trial is refused 409 (fixed by WC-175 R023 once the Founder approves); pages load |
| Live: API probe `JOURNEY=probe` | `/api/alert-controls/*` answers 403 `IDENTITY_ACTION_DENIED` every time, in about 20 ms; the pages themselves render in about 20 ms |
| Code: the membership middleware (`CustomerMembershipMiddleware`) | A customer token calling an endpoint without the customer identity marker is refused with that code; `AlertControlsController` has no marker. Customer-facing controllers also without it: Notifications, Customers, CustomerData, Subscriptions, Offerability, Skills (to be checked one by one in R001) |
| Code: `agent_skill_runtime_bindings` | Read by the mandate resolver; no code anywhere creates a row, so no relationship can reach "ready" |
| Code: hire checkout route | Capture then continue then bind then redirect to My Agents; nothing starts activation, a subscription or an invoice |
| Code: Settings, header, My Agents | Notification choices are shown but not editable; language is free text; header Billing opens `/profile#billing`; the page says "My Experts" |
| Four parallel read-only traces (Trial, Hire, customer pages, registration) | Step lists with file references; items they could not resolve are marked below as UNVERIFIED and are covered by a requirement that proves them |

Evidence class: LIVE = seen on Demo; CODE = read in source; UNVERIFIED = a trace could not resolve it and the requirement proves it first.

## Journey Status Today

| Journey step | Status | Evidence |
|---|---|---|
| Login, register, profile, email, WhatsApp code (synthetic code), workspace creation | WORKS | LIVE |
| Real Google or Facebook registration | UNVERIFIED on Demo (code and tests cover it) | CODE |
| Tenant claim after registration | NOT NEEDED for routes with the marker: the membership middleware sets the tenant from the membership | CODE |
| Trial: approval gate and workspace admission | WORKS once the Founder approves (WC-175 R023) | CODE, tests |
| Trial: relationship created, trial started at the billing owner | WORKS in tests; UNVERIFIED live | CODE |
| Trial: runtime bindings, readiness, first agent reply | BROKEN (R007 to R009) | CODE |
| Trial: days left, expiry, conversion | MISSING (R010, R011) | CODE |
| Hire: price and quote | WORKS once a package is for sale (R013) | CODE |
| Hire: Razorpay order, signature check, bind | WORKS in tests; needs Razorpay test keys (R018) | CODE |
| Hire: activation, recurring billing, invoice | BROKEN or MISSING (R014 to R017) | CODE |
| Alerts | BROKEN, 403 (R001); producers not wired (R020) | LIVE, CODE |
| Billing | MISSING, honest placeholder (R019) | LIVE |
| Profile, Settings, Connections, My Agents | WORKS but incomplete (R003 to R006, R021, R022) | LIVE, CODE |

## Objectives

| Id | Objective |
|---|---|
| O1 | A visitor registers, starts a Trial and receives the agent's first reply, with every missing step explained |
| O2 | A customer Hires, pays, and ends with an activated, billed and invoiced agent; no captured payment is lost |
| O3 | Alerts, Billing, Profile, Settings, Connections and My Agents are complete and use one plain vocabulary |
| O4 | The same journeys run automatically and live, so the next regression is found by a test, not by a customer |

## Authority And Scope

In scope: Business Platform customer routes, workspace and activation, runtime bindings, trial and hire workflows; the
billing owner's subscription, reconciliation and invoice code; the customer web pages named above; tests; the runbooks and
Skill 24; one Demo deployment per chunk and a live run of Skill 24.

Out of scope: UAT and Production; Razorpay live payments and KYC (Founder); changing the Founder's WhatsApp spend policy;
Email and Apple login; the WC-175 open items listed in Record Control.

Authority limits: no secret value is read or printed; real money is never charged (Razorpay test mode only until the
Founder decides otherwise); no WhatsApp message goes to a real person without the Founder's current-session approval;
throwaway customers are Demo only and are deleted afterwards (Skill 24); an API contract change is written in OpenAPI
before the code that serves it.

## Canonical Requirement Index

| Id | Requirement |
|---|---|
| WC176-R001 | [DEFECT, S] Every customer-facing Business Platform route carries the customer identity marker, so a registered customer's Alerts inbox and categories load instead of answering 403 IDENTITY_ACTION_DENIED. A test enumerates every authorized controller action and fails unless it is marked customer, staff, internal-service or anonymous, with a short written allow-list for documented exceptions. |
| WC176-R002 | [DEFECT, S] The Alerts page shows a loading state, says plainly what to do when the inbox cannot load, and does not keep retrying in the background. |
| WC176-R003 | [DEFECT, S] The header Billing entry opens /billing, and "My Experts" becomes "My Agents" everywhere, so one label means one place. |
| WC176-R004 | [DEFECT, M] Settings saves notification choices the customer changes, offers language as a choice of supported languages (not free text), and explains each security action in plain words. |
| WC176-R005 | [ENHANCEMENT, M] A customer can change the WhatsApp number from the Profile page: a code proves control of the new number (the synthetic code for throwaway customers), and the old number stops working only after the new one is verified. |
| WC176-R006 | [ENHANCEMENT, M] A customer can ask for a copy of their data and for their account to be erased from Settings, with plain words about what happens and when; the platform records the request and the Founder sees it as an operator task. |
| WC176-R007 | [DEFECT, L] The exact skill runtime bindings a relationship needs are created: when a workspace receives its admission from the Founder's approval, one binding per skill is written from the agent package (specification, prompt and schema digests, release sequence), idempotently, append-only and tied to the approved version, so the operational mandate resolver reports ready for a configured relationship. |
| WC176-R008 | [DEFECT, M] The relationship workspace says in plain words what is still missing before the agent can work (admission, contract, skill setup, goal, connection) with one next action, and never leaves the customer at a dead end. |
| WC176-R009 | [DEFECT, L] After a Trial starts, the customer reaches the induction conversation, sends a first message and receives the agent's bounded reply (no paid API calls and no external actions during Trial), through the real Business Platform, Professional Runtime and agent adapter. |
| WC176-R010 | [ENHANCEMENT, M] The Trial shows the real days left and the end date from the billing owner's trial status, and the allowance used, replacing the fixed "Day of 14" display. |
| WC176-R011 | [ENHANCEMENT, M] When a Trial ends the agent stops taking new work, the customer is told in an alert and shown a one-step way to Hire, and their data is kept for the period the policy states. |
| WC176-R012 | [ENHANCEMENT, M] When a skill needs a connected account, the workspace says so before the work needs it and links to Connections; the Trial runs in sandbox mode where the connection is not yet made. |
| WC176-R013 | [DEFECT, S] At least one sellable monthly package for Digital Marketing exists on the Founder Pricing page with GST terms, so Hire shows its price and opens for a registered customer. |
| WC176-R014 | [DEFECT, L] After a payment is captured the platform carries the Hire on by itself: contract acceptance, activation and induction run in order, replay-safe, and the customer sees progress and lands on the working agent instead of the agent list. |
| WC176-R015 | [DEFECT, M] A payment captured at Razorpay is never lost: the webhook and a reconciliation job complete the Hire or refund it, and a browser failure after capture shows "we are completing your Hire" and recovers. |
| WC176-R016 | [DEFECT, L] Recurring billing starts at activation: the billing owner creates the subscription, collects renewals, handles failure and grace, and supports cancel, stop and refund as its lifecycle code and the policy define, and the customer sees each state. |
| WC176-R017 | [DEFECT, M] A tax invoice with GST is issued for each captured payment and the customer can open it from Billing. |
| WC176-R018 | [ENHANCEMENT, S] The Razorpay settings for each environment (keys, webhook address, test mode for Demo) are written in a runbook and verified read-only before each live run; live KYC remains the Founder's. |
| WC176-R019 | [ENHANCEMENT, L] The Billing page shows the customer's plan, status, next renewal, invoices, payment method and allowance, with a way to manage or cancel, and an honest empty state before a Hire; it reads a customer billing projection served through Business Platform, specified in OpenAPI before it is built. |
| WC176-R020 | [ENHANCEMENT, M] Alerts are raised for the events a customer must see: Trial ending, payment failed or renewal due, connection needs repair, agent needs attention; each appears in the inbox with a plain next step. |
| WC176-R021 | [DEFECT, S] My Agents lists every agent (paged), with the Trial or Hire state in plain words. |
| WC176-R022 | [ENHANCEMENT, M] Connections lists the providers the Founder has admitted, not only Facebook, each with connect, reconnect and revoke. |
| WC176-R023 | [ENHANCEMENT, M] Automated end-to-end acceptance covers registration (synthetic code), Trial to first reply, Hire in Razorpay test mode and every customer page, runs in Docker with one documented command, and is the same journeys Skill 24 runs live. |
| WC176-R024 | [ENHANCEMENT, S] After deployment, Skill 24 runs registration, Trial with a first reply, Hire in test mode with an invoice, and the Billing, Alerts, Profile and Settings pages with throwaway customers; every result is recorded and the customers are deleted. |
| WC176-R025 | [ENHANCEMENT, S] A prerequisite runbook lists, in order, the Founder steps a live run needs (approve the professional, publish the package, Razorpay test keys, GST identity) and a read-only check reports which are done. |

## Founder Decisions Needed

| Id | Decision | Blocks |
|---|---|---|
| D1 | GST legal identity, registered address, SAC code and invoice series for tax invoices | R017 |
| D2 | Razorpay account: test keys and webhook for Demo; live KYC and keys later | R014, R015, R016, R018 |
| D3 | Data export and erasure scope, and what is kept after erasure | R006 |
| D4 | Which providers besides Facebook customers may connect | R022 |
| D5 | The monthly price and package for Digital Marketing | R013 |
| D6 | How long a customer's data is kept after a Trial ends without a Hire | R011 |

## Execution Chunks (dependency order)

| Chunk | Requirements | Outcome | Depends on |
|---|---|---|---|
| A. Quick wins (no new design) | R001 to R006 | Alerts load; header, settings, profile and wording are right; customer rights are reachable | none (R006 erasure needs D3) |
| B. Trial to a working agent | R007 to R012 | A registered customer starts a Trial, sees what is missing, and gets the agent's first reply | A for R001; R007 first |
| C. Hire to a working, billed agent | R013 to R018 | A paid Hire activates the agent, bills it, invoices it and never loses a payment | B; Founder actions D1, D2, D5 |
| D. Customer pages | R019 to R022 | Billing, Alerts, My Agents and Connections are complete | C for R019 and R020 |
| E. Proof | R023 to R025 | The same journeys run automatically and live, and the defect register closes | A to D deployed |

Chunk A can start at once. Docker validation runs once per completed chunk, never per defect.

## Definition Of Done

1. Every requirement has direct executable evidence in `WC-176-requirements.yaml`: a failing test first where code changes, then passing in the Docker runners (Python with `PYTHONPATH=/workspace:/workspace/scripts`, .NET with `GITHUB_WORKSPACE=/workspace` and the Docker socket, web gate), and the commands and results are in each PR body.
2. After each chunk is merged and deployed, the matching part of Skill 24 runs live with the Founder-approved throwaway customers, all deleted afterwards.
3. R024 closes the contract: registration, Trial with a first reply, Hire in test mode with an invoice, and the four customer pages, all recorded.
4. Every Founder decision D1 to D6 is either answered or its requirement is recorded as waiting.
5. Author review is bound to the exact head commit; every PR goes to the Founder for review and merge. No self-approval.

## Stop Conditions

- A requirement reaches a Founder decision (D1 to D6) or a Razorpay, Meta or Google account action.
- A change needs a new architecture decision, a trust-rule change in identity, or real money to move.
- A WhatsApp message would reach a real person without current-session approval.
- A live run cannot be repeated, or a throwaway customer cannot be deleted.

## Implementation Record

Not started. Grooming notes are appended below as they are proven.

### Grooming Log

| Date | Item | Result |
|---|---|---|
| 2026-11-27 | Contract created | Groomed from live probes and four code traces; 25 requirements, six Founder decisions |
| 2026-11-27 | Alerts root cause | Proven: 403 `IDENTITY_ACTION_DENIED` from the membership middleware because `AlertControlsController` lacks the customer identity marker; reproduced three times with `JOURNEY=probe`. The earlier "12 seconds" was the walk waiting for network idle; the pages answer in about 20 ms |
| 2026-11-27 | Tenant claim after registration | Not a defect for marked routes: tenant comes from the membership. One trace suspected a missing Keycloak attribute; the live Trial call reached the controller with the tenant, which disproves it for customer routes |
| 2026-11-27 | Runtime bindings | No code creates `agent_skill_runtime_bindings`; the agent package carries skill ids and versions but no prompt or schema digests, so R007 derives them from the package files |
| 2026-11-27 | Hire hand-off | `web/app/api/acquisition/hire-checkout/route.ts` ends at bind and a redirect; no activation, subscription or invoice call (trace to be proved by the R014 failing test first) |
