# WC-160 - Customer Journey Acceptance Slice 1 Content

## Record Control

| Field | Value |
|---|---|
| Work Contract | WC-160 |
| Office | Platform IT Expert (INST-010) |
| Initiative | IB-158 |
| Founder assignment | Current conversation, 2026-11-23: "Synthetic customer for testing"; scope through slice 1 (discover to connect Facebook); implementation code authorized for this session |
| Status | IMPLEMENTATION_AUTHORIZED. Evidence is in the PR body at the exact head |
| Baseline | `origin/main` at `018d196e184e6a29f5ec4264bfe80d9134ea0cd4` |
| Branch | `ib/158/synthetic-acceptance-customers` |
| Decisions | ADR-054, ADR-055 (accepted) |
| Controlling specification | `architecture/reference/acceptance/customer-journey-acceptance-architecture.md` sections 6, 7, 8; `validation/acceptance/plans/slice-1-discover-to-connect.v1.yaml` |
| Requirement ledger | [WC-160-requirements.yaml](./WC-160-requirements.yaml) |
| Depends on | WC-158 (harness core), WC-159 (synthetic tenant support) |
| Constitutional basis | C-023, C-027, C-049, C-059, C-063, C-065, C-071, C-080 |

## Authority And Scope

### In scope

1. Agent-written Playwright specs implementing every step of the slice 1 plan (S1, S2, S3, S3b, S4, S5, S5b, S6, S6b,
   S7, S8), each citing its plan step and existing requirement, story and gap identifiers.
2. The `live-scope.yaml` seed and the ratchet floor of 100% of slice-1 plan steps having specs.
3. Witness readers: W2 platform reads through the web application's same-origin server routes under the customer's own
   browser session; W3 Razorpay test API reader with the `rzp_test_` mode check; W3 Meta Graph reader with the
   development-mode check; signed Razorpay webhook replay.
4. Honest precondition handling: `BLOCKED-BY-FLAG` with its reason for no offerable price, Meta provider not
   registered, and conversation flags off; `NOT-COVERED` for Google or Facebook first-login linking and for the trial
   identity-hash binding.
5. Local proof that the specs and report plumbing run to completion in the Docker runner against an unreachable environment and a non-product stand-in. A full product stack was not started. No live provider traffic.

### Out of scope and prohibited

- Running against Demo or any live provider; entering or reading any secret.
- Reading the Business Platform bearer token, a service token or the database; reading `customer-connection-` secrets.
- Slice 2 and later journeys (WC-162), the sandbox readiness check (WC-161), conversation stories.

## Inputs

| Input | Status |
|---|---|
| WC-158 and WC-159 outputs in this branch | Present once implemented in this branch |
| Slice 1 plan and architecture package | Present on `main` (plan moved to `validation/acceptance/plans/`) |
| WC-107 and WC-149 requirement IDs, GOAL-005 story IDs, product gap register | Present on `main` |
| Founder authorization of implementation code in this session | Present (current conversation) |

## Canonical Requirement Index

| ID | Obligation |
|---|---|
| WC160-R001 | Every slice-1 plan step has at least one spec, and every spec cites its step and existing identifiers (floor of 100% recorded in the ratchet) |
| WC160-R002 | `live-scope.yaml` lists the WC-107 R009 to R016 and R019 and WC-149 R007 to R010 identifiers that exist in their ledgers and each has a covering spec or a recorded `NOT-COVERED` reason |
| WC160-R003 | Platform reads use only the web application's same-origin server routes under the synthetic customer's session; a claim whose state has no customer-reachable route is `NOT-WITNESSED` |
| WC160-R004 | The Razorpay reader refuses to proceed unless the key id begins `rzp_test_`, and a payment claim requires screen, platform and sandbox payment agreement for the shown GST-inclusive amount |
| WC160-R005 | The webhook replay signs with the webhook secret and delivers to the environment's callback address; a replay never causes a second activation or charge |
| WC160-R006 | The Meta reader refuses to proceed unless the app is in development mode, and a connection claim requires screen, platform list and Graph grant agreement with no token in any response |
| WC160-R007 | A missing price, unregistered Meta provider or disabled conversation setting yields `BLOCKED-BY-FLAG` with its reason, never a pass or a failure |
| WC160-R008 | The isolation step learns customer B's identifiers only from B's own session and fails if any appears in an A response |
| WC160-R009 | The specs run to completion against an unreachable environment and against a reachable stand-in that is not the product, producing a schema-valid report with honest verdicts, and no live provider is contacted |
| WC160-R010 | The first-login linking and trial identity-hash binding limits are reported `NOT-COVERED` in every report |

## Definition Of Done

1. Every requirement above has direct executable evidence run in Docker at the exact head.
2. `playwright test --list` enumerates one or more specs for every plan step; `tsc` passes on the harness.
3. Platform state refreshed in Docker; PR body prepared with `scripts/prepare_pr_body.sh`; author review recorded for
   the exact head; Founder reviews and merges.
4. No Demo, live-provider or real-phone result is claimed; hosted evidence is reported as not run.

## Stop Conditions

- Any need for credentials the Founder has not entered, or for a non-sandbox provider.
- Any spec that mocks a route or provider when claiming a witness the run did not read.
- A cited identifier that does not exist.

## Implementation Record

Evidence at the exact head is in the PR body. Honest limits recorded in the specs and reports:

- **S1** is `NOT-WITNESSED` by design today: the disclosure price, rights and limits are served only with a bearer token the harness must not hold, and no customer-reachable route exposes them. Exposing a read route is a separate decision.
- **W2 reads** use `/api/relationships/{id}/workbench/`, `.../workbench/evidence`, `/api/provider-connections` and `/api/identity/account`; a field those routes do not expose makes the witness unreadable, never a pass.
- **S6b** W3 is unreadable: revoke deletes the stored secret version inside Business Platform custody, which the harness must not read, and Graph cannot show it.
- **S7** reversibility is unreadable when no customer release control exists (none was found in the web components).
- **Locators are unproven on Demo.** They were written from the web source (labels, roles) and the Razorpay checkout and Facebook consent pages follow documented sandbox flows; the first run is the calibration run and any selector mismatch is reported as a step failure with its reason.
- **Registration.** If a first-time synthetic customer is routed to registration that needs more input than the harness supplies, the sign-in step fails with that reason.
- **Not run:** any Demo, live-provider or real-phone run; a full product stack.
