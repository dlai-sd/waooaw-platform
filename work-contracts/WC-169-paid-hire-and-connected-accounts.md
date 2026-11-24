# WC-169 - Paid Hire And Connected Accounts (Roadmap Iteration 2, Milestone M2)

## Record Control

| Field | Value |
|---|---|
| Work Contract | WC-169 |
| Office | Platform IT Expert (INST-010) |
| Initiative | IB-169 |
| Roadmap | [ROADMAP.md](../ROADMAP.md), Iteration 2 of 6, milestone M2 |
| Founder assignment | Current conversation, 2026-11-24: roadmap order accepted ("yes i am good"); commit approved |
| Status | CONTRACT WRITTEN. Starts only after WC-168 is merged, deployed and read back. Implementation code is not yet authorized |
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
| WC169-R003 | The conversation stories stay BLOCKED-BY-FLAG with recorded reasons until the Founder enables `WC120_CONVERSATION_ENABLED` |
| WC169-R004 | The Meta app is registered on the Meta provider row, and the Facebook connection uses the dialog the app supports; the scopes requested equal the scopes granted, read from the provider side; the open question of classic login versus Facebook Login for Business (WC-167 RV-2) is answered by a real run of S6 and S6b |
| WC169-R005 | Slice 2 publishes an approved post to the acceptance Page, reads it back from Meta and deletes it |
| WC169-R006 | A guest who sent STOP can resume on Demo: the code already resumes on START in the V2 visitor flow (the person must say YES again), but the default mode is LEGACY and neither Terraform nor `demo.json` sets it, so Demo is expected to run LEGACY where a stopped guest cannot resume. The Demo value is read first; if it is LEGACY the Founder decides to set `VisitorConversation:Mode` to V2 for Demo through the settings path; a test and a Demo read-back prove STOP then START then YES resumes with evidence and no duplicate message |
| WC169-R007 | A test coupon gives a partial discount on the Digital Marketing hire and the payable amount is validated without paying; the coupon is created by the Founder on the coupons screen, which depends on the pricing owner path being usable for writes (read-back at the start of this iteration) |
| WC169-R008 | One calibration report is produced and recorded here; every NOT-WITNESSED and FAIL item is listed with an owner |
| WC169-R009 | The legacy `/admin/azure-key-vault` screen is removed after the Founder confirms a provider key was entered and used through Providers |
| WC169-R010 | Meta App Review and WhatsApp template submissions are made and tracked with dates |
| WC169-R011 | Customer-visible polish found by the run (styling, wording, dark mode) is fixed to the WC-167 R006 bar |
| WC169-R012 | The Keycloak provisioning client deployed in WC-167 is read back by its first real use: the harness obtains a token with it, registers a synthetic subject, and the registration is visible to the platform; the token carries only the intended roles and expires in 60 seconds |
| WC169-R013 | One customer price source. The Marketplace card, the employment contract terms and the hire amount come from the authorized package the Founder set on the Pricing screen, never from the static `indicativePrice` in the agent descriptor; until a package is authorized no amount is shown and the hire is not offerable; the acceptance pay step (S5) proves the amount paid equals the authorized price including GST; an edited package name, features and price reach the Marketplace after authorization |
| WC169-R014 | The Founder's decision on which `DEFAULT_OFF` DMA components are sold (for example `SOCIAL_PUBLICATION` and `SOCIAL_OBSERVATION`) is applied to the DMA experience declaration and its admission as a new agent version, so a package that contains them can be authorized and the publish slice can run; nothing is switched on that the Founder did not name |

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
| G1 | The STOP "defect" was asserted, not verified | `WhatsAppGuestSessionService` resumes on START when `IsVisitorV2`; `VisitorOptions.Mode` defaults to LEGACY; Terraform and `demo.json` do not set it | FIXED: R006 is now a setting decision plus proof, not new code |
| G2 | The synthetic customer's sign-in path was untested | The provisioning client was deployed in WC-167 and only its import was read back | FIXED: R012 added |
| G3 | The coupon needs a working pricing write path | The coupons screen returned 503 before (CB-021); only dashboard reads were seen to work on 2026-11-24 | FIXED: R007 states the dependency and a start-of-iteration read-back; stop condition added |
| G4 | The Razorpay reachability question was open | Terraform wires the test secrets into the Demo runtime | Closed |
| G5 | Meta scope mismatch is possible | The seeded Meta row lists `pages_manage_posts` and `instagram_content_publish`; the acceptance app holds `pages_manage_posts` and `pages_read_engagement` | FIXED: R004 requires the scopes requested to equal the scopes granted, read from the provider side |
| G6 | Facebook connection works only for app Testers in development mode | Meta app mode is development | Recorded as a known limit; R010 starts App Review |
| G7 | Repairs may exceed one pull request | Run-first scope | FIXED: time-box and one repair pull request already allowed; stop condition below |

## Stop Conditions

- The coupons screen cannot write because of the pricing owner path (CB-021): R007 becomes BLOCKED and moves to the Founder; the rest proceeds.
- WC-168 is not read back green: do not start.
- A failed step needs a repair larger than one requirement: record it, descope with the Founder, and do not stretch the pull request.
- Anything involving real money or a real customer: stop.

## Implementation Record

Contract written 2026-11-24. Not started.
