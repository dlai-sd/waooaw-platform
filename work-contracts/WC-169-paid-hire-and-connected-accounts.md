# WC-169 - Paid Hire And Connected Accounts (Roadmap Iteration 2, Milestone M2)

## Record Control

| Field | Value |
|---|---|
| Work Contract | WC-169 |
| Office | Platform IT Expert (INST-010) |
| Initiative | IB-169 |
| Roadmap | [ROADMAP.md](../ROADMAP.md), Iteration 2 of 6, milestone M2 |
| Founder assignment | Current conversation, 2026-11-24: roadmap order accepted ("yes i am good"); commit approved |
| Status | IN PROGRESS (documents and database grants). WC-168 is merged; its deployment read-back is pending. The pull request waits for that read-back. Price rewiring code (R013) waits for the Founder's price-calculator discussion |
| Depends on | WC-168 (Providers works; DMA packages authorized); WC-158 to WC-166 (acceptance harness and vault); WC-149 and WC-162 (connection and publish) |
| Requirement ledger | [WC-169-requirements.yaml](./WC-169-requirements.yaml) |
| Constitutional basis | C-001, C-023, C-049, C-063, C-065, C-080 |
| Deployment | One Environment Deployment of Demo after merge; one repair pull request allowed |

## Why This Contract Exists

The customer journey from discovery to a connected Facebook account is already specified and mostly built: acceptance slice 1 (S1 to S8: discover, sign in, trial, contract, pay, connect, stop, isolate) and slice 2 (publish). It has never run green on Demo. This contract is run-first: run it, repair what fails, and add only what the run proves missing. Its size depends on what the run finds, so repairs are time-boxed and anything larger is recorded and descoped with the Founder.

## Objectives

| Id | Objective |
|---|---|
| O1 | Acceptance slices 1 and 2 run on Demo; every step passes or is honestly BLOCKED-BY-FLAG with a Founder decision |
| O2 | The synthetic customer completes discover to connected accounts and publishes one approved post |
| O3 | Known defects on this path are fixed: WhatsApp STOP can resume; a test coupon gives a partial discount |
| O4 | One valid calibration report exists and every NOT-WITNESSED or FAIL item has an owner |
| O5 | The legacy Key Vault screen is retired once the Providers screen is proven to hold provider keys |
| O6 | External lead-time items start now: Meta App Review and the WhatsApp template needed by Iteration 4 |

## Authority And Scope

In scope: running and repairing slices 1 and 2; the STOP fix; coupon validation; one calibration report; removing the legacy Key Vault screen; starting Meta submissions; polish found by the run.

Out of scope: agent campaign work, alerts, lifecycle, billing model changes, a second agent, real customers, real money, UAT and production.

Authority limits: the harness runs only with the synthetic customer and sandbox or test values; no real payment is made; no secret value is read or printed; the legacy screen is removed only after the Founder confirms a provider key was entered and used through Providers.

## Canonical Requirement Index

| Id | Requirement |
|---|---|
| WC169-R001 | The acceptance vault holds 12 of 12 secrets, with the coupon code and the saved Meta test-user session added by the Founder |
| WC169-R002 | Slice 1 runs on Demo and the report lists S1 to S8 with witnesses W1, W2 and W3; every failure is triaged to an owner |
| WC169-R003 | The application role can use the four WC-120 conversation tables its code touches (`conversation_context_observations`, `conversation_context_summaries`, `conversation_data_right_requests`, `whatsapp_media`) with row level security kept: init file `99zzzzzzzz-wc169-01-conversation-context-media-runtime-access.sql` grants exactly what each code path does and never DELETE, a real-database test proves it, and a read-only catalog read of Demo after deployment confirms it; `conversation_migration_watermarks` has no code path and stays closed; the conversation stories stay BLOCKED-BY-FLAG with recorded reasons until the Founder enables `WC120_CONVERSATION_ENABLED` |
| WC169-R004 | The Meta app is registered on the Meta provider row, and the Facebook connection uses the dialog the app supports; the scopes requested equal the scopes granted, read from the provider side; the open question of classic login versus Facebook Login for Business (WC-167 RV-2) is answered by a real run of S6 and S6b |
| WC169-R005 | Slice 2 publishes an approved post to the acceptance Page, reads it back from Meta and deletes it |
| WC169-R006 | A guest who sent STOP can resume on Demo. Read-back of 2026-11-24: Demo already runs `VisitorConversation__Mode = V2`, where START asks for consent again and YES resumes, and tests already prove it (`VisitorStateMachineTests`, `VisitorConversationServiceTests`, `WhatsAppGuestStopAcknowledgementPostgresTests`); my earlier assumption that Demo ran LEGACY was wrong. What remains is the live proof: one real STOP, START and YES run in the acceptance run, with evidence and no duplicate message |
| WC169-R007 | A test coupon gives a partial discount on the Digital Marketing hire and the payable amount is validated without paying; the coupon is created by the Founder on the coupons screen, which depends on the pricing owner path being usable for writes (read-back at the start of this iteration) |
| WC169-R008 | One calibration report is produced and recorded here; every NOT-WITNESSED and FAIL item is listed with an owner |
| WC169-R009 | The legacy `/admin/azure-key-vault` screen is removed after the Founder confirms a provider key was entered and used through Providers |
| WC169-R010 | Meta App Review and WhatsApp template submissions are made and tracked with dates |
| WC169-R011 | Customer-visible polish found by the run (styling, wording, dark mode) is fixed to the WC-167 R006 bar |
| WC169-R012 | The Keycloak provisioning client deployed in WC-167 is read back by its first real use: the harness obtains a token with it, registers a synthetic subject, and the registration is visible to the platform; the token carries only the intended roles and expires in 60 seconds |
| WC169-R013 | One customer price source for a signed-in customer's hire. The amount, GST and billing period come from the monthly package the Founder authorized and put on sale on the Pricing screen, resolved by the Business Platform from the billing owner and never from the client or the static `indicativePrice` in the agent descriptor. Design reviewed by the Solution Architect office on 2026-11-24 (see Implementation Record): the selected package code flows through preview, acceptance and checkout; the server resolves one immutable quote bound to the customer and contract hash; the contract terms, the hire preview and the payment use that same quote; a coupon payable is the authorized gross less the validated discount; with no package for sale, or the owner unavailable, there is no amount and no hire, with no descriptor fallback; changed terms before charging need renewed acceptance. Only the amount is in scope, with no component wiring. Until the customer chooses among packages in the interface, the lowest-priced package for sale is the default, and the choice screen is the next story. The acceptance pay step (S5) proves the amount paid equals the authorized price including GST |
| WC169-R021 | The public Marketplace card and the anonymous disclosure no longer show the descriptor price: an anonymous visitor has no tenant or actor, and no anonymous principal is invented (ADR-046, identity boundary). The amount is shown after sign-in and membership, from the for-sale packages. A public price projection needs its own approved workload policy and is deferred |
| WC169-R014 | The Founder's decision on which `DEFAULT_OFF` DMA components are sold (for example `SOCIAL_PUBLICATION` and `SOCIAL_OBSERVATION`) is applied to the DMA experience declaration and its admission as a new agent version, so a package that contains them can be authorized and the publish slice can run; nothing is switched on that the Founder did not name |
| WC169-R015 | The cause of the one blocked outbound WhatsApp message on Demo is recorded and handed over: Meta error 131026 ("undeliverable") on 2026-11-20 and 2026-11-22 for the same real, active number, with the row left as `PROVIDER_REJECTED`. The governed route to read and resolve blocked messages and the alert behaviour belong to WC-171 (roadmap Iteration 4) and are not built here; WC-169 only re-sends one test message to that number during the acceptance run if the Founder confirms the number is a test user, and records the result |
| WC169-R016 | A Founder step-up works from every Founder console page. Found in the WC-168 read-back on 2026-11-24: the sign-in start refused the return to `/admin/providers` with HTTP 400 `IDENTITY_ACTION_DENIED`, so the multi-factor sign-in never reached Keycloak and every Founder write (provider key, pricing authorization, access approval) was refused with `PROVIDER_STEP_UP_REQUIRED`. The return list in `normalizeOidcCallback` now has a closed Founder console list with no query string; a unit test proves it; the Demo read-back is a saved provider value after a multi-factor sign-in |
| WC169-R017 | A package carries a description of the customer maturity it suits (up to 500 characters, optional so existing packages stay valid). The Billing Engine package body (`extra=forbid`) gains the field, the Pricing package editor edits it, and the package list shows it; a test proves a package with and without a description round-trips and that an over-long description is refused |
| WC169-R018 | The package editor shows one build-up table: each component's cost lines (quantity, thread, marked-up unit cost from the authorized rate), the infrastructure share, the total cost floor, the package's target margin, and the suggested GST-inclusive price (cost floor divided by one minus the target margin, plus GST, rounded up to the next whole rupee). The Founder types and saves the final price; the suggestion never saves itself. A thread without an authorized rate is listed and its cost is shown as unknown, so a suggestion is never presented as complete (existing `unauthorizedThreadIds` rule). The engine's refusal of a price below the cost floor and the policy page's minimum margin stay unchanged |
| WC169-R019 | The target margin is set per package on the package body (0 up to but not including 100 percent) with no platform restriction beyond R018's unchanged refusals; an existing package without one falls back to the policy page's minimum margin; a test proves the suggested price for a worked example (for instance a cost floor of ₹825 and a 40 percent target margin gives a base price of ₹1,375 and a suggested price including 18 percent GST of ₹1,623) |
| WC169-R020 | The Founder creates three monthly packages on Demo through the screen with names and descriptions of his choice (Starter, Runner and Winner are the example), authorizes them with step-up, and the hire amount shown and charged in S5 equals the authorized price including GST (R013); no component activation wiring is built; the package values are entered by the Founder at run time and are never seeded or hard-coded |

## User Stories By Area

Each story names who wants it, what they do, and the requirement that proves it. Founder stories are marked F, customer stories C, platform stories P.

| Area | Story | Proved by |
|---|---|---|
| Journey run | F1: As the Founder I read one calibration report that lists every step as pass, fail or blocked, each failure with an owner | R002, R008 |
| Journey run | C1: As a business owner I find the Digital Marketing professional, sign in, start a trial or hire, and nothing starts until I confirm | R002 (S1 to S4) |
| Journey run | C2: As a business owner my data is never visible to another customer | R002 (S8) |
| Paid hire | F2: As the Founder I define a monthly package (for example Starter, Runner or Winner) with a name and a description of the customer maturity it suits | R017 |
| Paid hire | F2b: As the Founder I see one build-up table for a package: each cost line with its markup, the infrastructure share, the total cost, my target margin for this package, and the suggested price including GST, then I set the final price myself | R018, R019 |
| Paid hire | F3: As the Founder I choose which switched-off components to sell, and only those are switched on (on hold) | R014 |
| Paid hire | C3: As a business owner I pay the authorized monthly price including GST, with a test coupon giving a partial discount, and no more; only the amount is taken from the Pricing screen for now, with no component wiring | R013, R007 |
| Connected accounts | F4: As the Founder I save the Meta app in Providers after a multi-factor sign-in that actually asks for my second factor | R016, R004, R009 |
| Connected accounts | C4: As a business owner I connect my Facebook Page through a dialog without technical steps, and see only the permissions I granted | R004, R012 |
| Connected accounts | C5: As a business owner I see the agent publish one approved post to my Page and I can stop work at any time | R005 |
| Connected accounts | F5: As the Founder I know the dates of Meta App Review and the WhatsApp template, started now | R010 |
| WhatsApp and conversation | C6: As a business owner who sent STOP I can resume by saying START and then YES, with evidence and no duplicate message | R006 |
| WhatsApp and conversation | P1: As the platform I can store and read conversation context and media for each customer without exposing another customer's rows | R003 |
| WhatsApp and conversation | F6: As the Founder I am told the cause of the blocked message and where its resolution belongs (WC-171) | R015 |
| Cleanup | F7: As the Founder I see one Key Vault screen path, after I confirm a provider key was entered and used through Providers | R009 |
| Cleanup | C7: As a business owner I meet no wrong wording, broken styling or dark-mode defects on the pages the run touches | R011 |

## Founder And Customer Journey Simulation

Customer: discover, sign in, trial, contract, pay, connect, publish, stop, isolate.
- Pay needs an authorized price: WC-168 R006 supplies it. If it is missing, S5 is BLOCKED and WC-169 does not start.
- The Meta app is in development mode, so only app Testers can connect. Real customers cannot connect until App Review. This is recorded as a known limit and R010 starts the review.
- The Founder login cannot also be the customer. The run uses the synthetic customer.
- Razorpay test credentials are wired into the Demo runtime (`READY_TEST`); R002 reads back that the checkout works.

## Definition Of Done

Every requirement has a ledger row with a report or test as evidence; the Founder has deployed and the read-back is recorded; the calibration report is attached; `ROADMAP.md`, README and PROJECT_STATE are updated at close; the Founder merges.

## Critical Review And Simulation Record (2026-11-24)

Method: each requirement was checked against the repository, Demo state and the acceptance architecture; the customer journey was walked step by step against what exists today. Findings that changed this contract are marked FIXED.

### Customer journey run against today's Demo (what slice 1 will meet)

| Step | Expected today | Evidence | Contract response |
|---|---|---|---|
| S1 Discover | Loads, but the price is a static descriptor value | WC-168 RC-3 | Depends on WC-168 R006 |
| S2 Sign in as customer A | Needs a Keycloak customer for the synthetic subject; the provisioning client exists but has never been used | WC-167 read-back was partial | R012 added |
| S3, S3b Trial | Expected to run; not exercised on Demo yet | none | R002 |
| S4 Contract | Expected to run | none | R002 |
| S5 Pay | BLOCKED until a package is authorized; Razorpay test secrets are wired into the Demo runtime (`READY_TEST`) | WC-168 R006, R015; Terraform `razorpay_secret_uris` | Dependency stated; reachability gap closed |
| S6 Connect | BLOCKED until Providers works and the Meta app is on its provider row | WC-168 RC-1 | R004 |
| S7 Stop, S8 Isolate | Expected to run | none | R002 |

### Gaps found and how they were fixed

| Id | Gap | Evidence | Status |
|---|---|---|---|
| G1 | The STOP "defect" was asserted, not verified | `WhatsAppGuestSessionService` resumes on START when `IsVisitorV2`; Demo read-back 2026-11-24 shows `VisitorConversation__Mode = V2`; existing tests prove STOP, START, YES | FIXED: R006 is now live proof only; no setting decision and no code is needed |
| G2 | The synthetic customer's sign-in path was untested | The provisioning client was deployed in WC-167 and only its import was read back | FIXED: R012 added |
| G3 | The coupon needs a working pricing write path | The coupons screen returned 503 before (CB-021); only dashboard reads were seen to work on 2026-11-24 | FIXED: R007 states the dependency and a start-of-iteration read-back; stop condition added |
| G4 | The Razorpay reachability question was open | Terraform wires the test secrets into the Demo runtime | Closed |
| G5 | Meta scope mismatch is possible | The seeded Meta row lists `pages_manage_posts` and `instagram_content_publish`; the acceptance app holds `pages_manage_posts` and `pages_read_engagement` | FIXED: R004 requires the scopes requested to equal the scopes granted, read from the provider side |
| G6 | Facebook connection works only for app Testers in development mode | Meta app mode is development | Recorded as a known limit; R010 starts App Review |
| G7 | Repairs may exceed one pull request | Run-first scope | FIXED: time-box and one repair pull request already allowed; stop condition below |
| G8 | Five conversation tables were unreadable by the application role | Catalog read of 2026-11-24 (WC-168): no privilege for `business_app`, forced row level security | FIXED: R003 grants four with a real-database test; the fifth has no code path |
| G9 | One WhatsApp message is blocked and pages every 30 seconds | Demo logs: `metaCode=131026` on 2026-11-20 and 2026-11-22, same real number the Founder knows | RECORDED and handed to WC-171 (governed route and alert behaviour); the cause is on Meta's side (recipient cannot receive), not a secret or a WAOOAW limit. My first draft built it into WC-169, which the roadmap does not allow; corrected |
| G10 | The customer price must come from ingredient costs, not a static value | Founder: price comes from API call cost, infrastructure cost and similar; a calculator is needed | R013 holds `src/` work until the design is agreed |
| G11 | The Founder cannot save a provider key: the step-up sign-in is refused before it reaches Keycloak | Browser network log of 2026-11-24: `POST /api/auth/signin/keycloak?...acr_values=2` returned 400; `normalizeOidcCallback` accepts only `/home`, `/verify`, `/account-link`, `/login`, `/register` | FIXED locally: R016 |

## Meta Lead-Time Tracker (R010)

These submissions have outside waiting time, so they start in this iteration. Only the Founder can submit them because they need the account owner's Meta login. Dates are filled in by the Founder when each step happens; the agent never enters a date it did not see. Meta's documents change, so each line must be checked against the cited page at submission time.

| Item | What is requested | Evidence the repository already holds | Still needed from the Founder | Submitted | Decided |
|---|---|---|---|---|---|
| Meta App Review, Advanced Access | `pages_show_list`, `pages_manage_posts`, `pages_read_engagement` (the exact scopes in `MetaConnectionOptions.Scopes`). Needed before any customer who is not an app Tester can connect a Page. [Permissions reference](https://developers.facebook.com/documentation/development/permissions.md/) | Public privacy page `/privacy`, terms `/terms` and data deletion page `/data-deletion` exist in the web app | Business Verification of the Meta business account; the review screencast of the real connect and publish flow (use the acceptance run); step-by-step reviewer login instructions; app icon and category; confirm the data-deletion URL | | |
| WhatsApp message template (utility) | One utility template for proactive messages (the Founder's rule: up to 30 proactive alerts or messages a month in every subscription) | The thread rate `whatsapp_template_utility` exists and is awaiting authorization on the Pricing screen | Template name, text and variables chosen by the Founder; the payment method on the WhatsApp Business account (the Meta page lists "Add payment to send business-initiated messages" as not done); submit in WhatsApp Manager and record approval | | |
| WhatsApp phone number | Register the number `+91 88889 12344` shown on the Meta production setup page | None | Finish the "Register your WhatsApp phone number" step | | |

Recorded risk: until App Review passes, only app Testers can connect, so the acceptance run uses the synthetic customer as a Tester (known limit G6).

## Stop Conditions

- The coupons screen cannot write because of the pricing owner path (CB-021): R007 becomes BLOCKED and moves to the Founder; the rest proceeds.
- WC-168 is not read back green: do not start.
- A failed step needs a repair larger than one requirement: record it, descope with the Founder, and do not stretch the pull request.
- Anything involving real money or a real customer: stop.

## Implementation Record

Contract written 2026-11-24. Work started on branch `ib/169/paid-hire-and-connected-accounts` while the Founder deploys WC-168; no pull request is opened until the Founder has seen that deployment.

Founder decisions recorded 2026-11-24:
- The five conversation tables are handled in this contract (R003).
- Reading the blocked WhatsApp message was approved. The application login saw no rows until the configured default tenant was named; the row is one `PROVIDER_REJECTED` message from 2026-11-22. The Founder approved a stronger read on a temporary basis, which was not needed and not used. Meta error 131026 appeared on 2026-11-20 and 2026-11-22 for the same real, active number. It is parked as low priority (log noise only) and handed to WC-171 by R015.
- The production Meta secret reset was chosen by "ok" to the recommendation. It does not fix error 131026.
- Package names, features and prices stay Founder run-time choices; the price calculator from ingredient costs is discussed before R013 code (G10).
- The Starter definition (4 posts a week, 1 ad boost, monitoring on 4 platforms) needs `SOCIAL_PUBLICATION` and `SOCIAL_OBSERVATION` switched on (R014); `AD_BOOST` is UNAVAILABLE and would have to be built, which is a decision for the Founder.
- No pull request until the Founder has seen the WC-168 deployment.
- The WC-169 work is bundled into one pull request and one Demo deployment because every deployment is costly (Founder, 2026-11-24). The step-up fix (R016) ships in that deployment, so saving the Meta app secret and the Meta part of the run wait for it.
- `AD_BOOST` and the choice of components to sell are on hold. The Founder's concept: the agent has skills, each skill produces countable outcomes (components), and the thing sold is a skill pack of a chosen size, for example Content Creation (theme creation, content creation, content publication) as a pack of 3 components. The comparison given is a telecom data top-up or an insurance rider.
- PIVOT (Founder, 2026-11-24, replaces the pack, rider and top-up thinking above): WAOOAW does not sell individual outcomes for now. It offers digital employees hired monthly, each with skills and capabilities, paid a monthly fee for achieving goals. Every agent is available for monthly hiring with a set of skills. The customer gets a set of deliverables for the month under a package chosen for their maturity: Starter (new to digital marketing, may have no Facebook or Google account), Runner (basic setup, but post frequency, quality, tagging and ads are weak) and Winner (professional maturity). Package names will vary. The Founder defines each package with a name and description, then cost lines and a margin on each, and the final figure carries one more margin on the total. Agent wiring is out of scope for now: the hire amount is simply picked from the Pricing screen. The earlier decisions on top-ups, riders and expiry are parked. The target margin is still set per package with no platform restriction, and the engine's cost-floor refusal and the policy page's minimum margin stay as they are.
- Gaps the design must close: the engine checks a typed price and does not suggest one; a package has no maturity description; the build-up of cost lines, per-line margin and total margin is not shown as one table to the Founder.

Work done so far (committed locally on the branch, not pushed): the conversation-table grants and their real-database test; the read-only blocked-message read script and guard test; the Founder step-up return fix (R016); the package description, build-up table and per-package margin (R017 to R019). R013, R014, R020 and R021 are still to build.

Implementation authorization (Founder, 2026-11-24): "please dont ask me technical points, you are expert and empowered to take these decisions. At anypoint if you feel its need expertise other than you, use offices in waooaw like enterprise architect, solution architect etc with single pass read write access and focused clear request from these offices for review repair as required." This is read as authority to decide the technical points of R016 to R020 and to call a review office once for a focused pass. The price-calculator scope is the Founder's pivot above.

Solution Architect review (one focused pass, 2026-11-24) and how each finding was resolved:

| Finding | Resolution |
|---|---|
| The simulation response did not expose cost lines or unknown costs | `buildUp` added to the simulation response (cost lines per ingredient, infrastructure share, floor, target margin, suggestion, status), in both API specs and the regenerated web client |
| A preview could be stale after an edit | Saving a draft clears the older simulation; the build-up says it describes the saved draft and tells the Founder to save then simulate |
| A missing rate or empty recipe counted as zero | Cost lines carry an unknown rate as unknown (no cost shown); a component with no recipe is listed; either makes the suggestion INCOMPLETE and the web offers no one-click price |
| Rounding could disagree with the stated formula | The suggestion is computed exactly (floor divided by one minus margin, then GST) and only then rounded up to the next whole rupee; tests cover 82,500 paise at 40 percent (162,300) and 85 paise at 0 percent (200) |
| A margin of zero could fall back to the policy margin | An explicit not-None check: zero set on the package is a real target; no cost, or no margin anywhere, gives UNUSABLE |
| Contract changes must ship together | Both specs changed identically (additive optional fields); the generator script reran; the manifest digest and contract tests pass (184); mixed-version rollout is avoided because everything deploys together in the one WC-169 deployment |
| The package list did not show the description | A Description column was added |
| Stored versions must not change | The stored-body digest hashes the submitted mapping, not a model dump, and the body adapter passes unknown keys through; a test proves a legacy package gains no new fields |

Evidence for R016 to R019 (Docker runners): billing engine package, router and simulator tests 72 passed plus the 11 new tests; contract tests 184 passed; web tests 461 passed with type check and Biome clean on the changed files; the full billing engine and contract run shows the same 11 failures on unmodified main and on this branch (components units, lifecycle commands, baseline seed, export and import, WC-124 billing authority), so they predate this work and were not touched.

Demo read-back, 2026-11-24 (Azure Container Apps settings, values only for non-secret settings): the Business Platform runs `VisitorConversation__Mode = V2`, `VisitorConversation__PublicEntryEnabled = false`, `VisitorConversation__SimulatorEnabled = false` and `Wc120Conversation__Enabled = true`. `WC120_CONVERSATION_ENABLED`, named in the acceptance plans, is the web setting for the portal conversation, which is a different switch from the backend one; my earlier statement that the conversation feature is off on Demo was only true for the web switch. R003 stays as written because its grants are needed by the backend paths in either case.

Solution Architect decision memo on the price source (one pass, 2026-11-24), the specification for R013 and R021:
- Hide the anonymous Marketplace price, including the descriptor price in public responses; do not invent an anonymous actor or tenant. After sign-in and membership, show the Founder-authorized for-sale monthly packages.
- One pull request slice: pass the selected package code through preview, acceptance and checkout; the Business Platform resolves the effective package version, GST-inclusive price, GST and period from the billing owner and stores an immutable quote bound to the customer and the contract hash; the same quote feeds pre-hire payment and the relationship contract composition; client-supplied commercial-terms paths are closed or guarded; a coupon payable is the authorized gross less the validated discount, not the gross.
- Fail closed: no effective for-sale package means no amount and no hire; an owner failure means unavailable, never a descriptor fallback; before charging, validate or reserve the quoted version atomically, and changed terms need renewed acceptance; captured-payment reconciliation is preserved.
- Tests: selection, absence, outage, price change, tampering, partial coupon and payment-to-contract binding; S5 needs a real Founder-authorized package.
- Deferred: anonymous "from" pricing, caching, and all agent-component activation wiring.
- Top risks found in the repository: pre-hire checkout (`web/app/api/acquisition/hire-checkout/route.ts`, lines 140 to 142) charges the descriptor price before the relationship contract is composed, so both paths must bind to the quote; the billing owner lists only packages that are effective and activated for sale, so the Founder screen must be shown to complete both steps without component wiring (`src/billing-engine/package_catalog.py`); and the hire preview falls back to the descriptor and omits the professional version the billing owner needs (`web/app/api/acquisition/hire-preview/route.ts`).
- Facts behind the memo: the web hire interface never sends a package code today (the preview picks the first package, checkout uses the descriptor); the Business Platform composes contract terms from `disclosure.IndicativePrice` (`EmploymentRelationshipsController`, about line 1130) and hashes it into the contract hash (`AcquisitionController`, about line 457); the public disclosure and Marketplace endpoints are anonymous.

Implementation of R013 and R021 (2026-11-24, one consolidated validation pass at the end of the bundle, by Founder instruction):
- Design: the locked quote is stored on `business.acquisition_intents`, the row that already binds the customer, the accepted contract hash and the later relationship, through seven nullable columns, an all-or-nothing and Hire-only check, and a trigger that refuses any later change (`99zzzzzzzz-wc169-02-acquisition-hire-quote.sql`; no new grants, no delete). `HireQuoteService` lists the for-sale packages from the billing owner, keeps those of the exact professional version with a 28 to 31 day period, picks the named package or the lowest-priced one, and hashes package, version, period and amounts into the quote version.
- New `POST /api/v1/acquisition/hire-quote` previews a quote and stores nothing. Hire intents lock the quote when created; the acquisition contract hash now includes the quote instead of the descriptor price. Hire setup builds contract terms only from the locked quote and returns 409 `HIRE_QUOTE_UNAVAILABLE` when there is none; the client-supplied contract path refuses any mismatched amount, GST, period, package or quote version. The web checkout takes amounts only from the quote the server returns, ignores client amounts, and the preview now sends the professional version the billing owner requires.
- The billing engine is unchanged: it already computes the payable as the gross less the validated discount and refuses a payment whose amount differs from the contract (`PRE_HIRE_CONTRACT_PRICE_MISMATCH`).
- R021: `IndicativePrice` is removed from the Business Platform disclosure model, the anonymous disclosure and the Marketplace listing. Public pages say "Price shown after you sign in"; signed-in pages show the amount from the quote and disable Hire (Trial stays) when there is none. The agent descriptor file still holds the old price and is now ignored.
- Decisions: monthly means a 28 to 31 day package; a changed price on replay returns 409 and needs renewed acceptance; confirming a payment already taken never re-prices; a Hire intent is no longer saved before registration because there is no workspace to price against.
- Review finding fixed by the lead: the first draft accepted package codes only in upper case with underscores, but the Pricing screen and billing engine accept mixed case, dashes and dots and the Founder chooses codes at run time. The three code checks (Business Platform controller, hire-preview and hire-checkout routes) now match the billing engine rule `^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$`, with a test for `Starter-Monthly.1`.
- Known limits: hire intents created before this change have no quote and fail closed with 409; the old end-to-end spec `wc097-marketplace-experience.spec.ts` still expects the descriptor price and was already out of date; the generated web models for the new quote were copied by hand because a full regeneration would also change an unrelated stale file; the S5 acceptance step compares the amount the app shows with the amount Razorpay captured, and a reading that the shown amount equals the Founder-authorized package price is a calibration item for the first run.
