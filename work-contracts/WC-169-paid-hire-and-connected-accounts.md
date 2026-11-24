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
| WC169-R004 | The Meta app is registered on the Meta provider row, and the Facebook connection uses the dialog the app supports; the open question of classic login versus Facebook Login for Business (WC-167 RV-2) is answered by a real run of S6 and S6b |
| WC169-R005 | Slice 2 publishes an approved post to the acceptance Page, reads it back from Meta and deletes it |
| WC169-R006 | A guest who sent STOP can resume, with evidence and no duplicate message |
| WC169-R007 | A test coupon gives a partial discount on the Digital Marketing hire and the payable amount is validated without paying |
| WC169-R008 | One calibration report is produced and recorded here; every NOT-WITNESSED and FAIL item is listed with an owner |
| WC169-R009 | The legacy `/admin/azure-key-vault` screen is removed after the Founder confirms a provider key was entered and used through Providers |
| WC169-R010 | Meta App Review and WhatsApp template submissions are made and tracked with dates |
| WC169-R011 | Customer-visible polish found by the run (styling, wording, dark mode) is fixed to the WC-167 R006 bar |

## Founder And Customer Journey Simulation

Customer: discover, sign in, trial, contract, pay, connect, publish, stop, isolate.
- Pay needs an authorized price: WC-168 R006 supplies it. If it is missing, S5 is BLOCKED and WC-169 does not start.
- The Meta app is in development mode, so only app Testers can connect. Real customers cannot connect until App Review. This is recorded as a known limit and R010 starts the review.
- The Founder login cannot also be the customer. The run uses the synthetic customer.
- Razorpay test credentials must be reachable by the platform at run time, not only held in the acceptance vault. R002 confirms this.

## Definition Of Done

Every requirement has a ledger row with a report or test as evidence; the Founder has deployed and the read-back is recorded; the calibration report is attached; `ROADMAP.md`, README and PROJECT_STATE are updated at close; the Founder merges.

## Stop Conditions

- WC-168 is not read back green: do not start.
- A failed step needs a repair larger than one requirement: record it, descope with the Founder, and do not stretch the pull request.
- Anything involving real money or a real customer: stop.

## Implementation Record

Contract written 2026-11-24. Not started.
