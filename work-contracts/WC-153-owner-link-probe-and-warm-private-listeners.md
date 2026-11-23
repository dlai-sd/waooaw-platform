# WC-153 - Owner-Link Probe Identity And Warm Private Listeners

## Record Control

| Field | Value |
|---|---|
| Work Contract | WC-153 |
| Authoring office | Platform IT Expert (INST-010), under Founder assignment in the current conversation (lightweight record; the Founder may re-assign the number or office) |
| Initiative | IB-153 |
| Founder assignment | Current conversation: RCA and fix for Environment Deployment run 45106599832, with every later deployment step tested locally against live Demo before the PR |
| Status | IN PROGRESS. Evidence is in the PR body at the exact head |
| Baseline | `main` at `edd9f9e4` |
| Related contracts | WC-147 (Key Vault workload credentials); WC-149 (AI runtime warm replica); WC-150; WC-151; ADR-046 |
| Requirement ledger | [WC-153-requirements.yaml](./WC-153-requirements.yaml) |
| Constitutional basis | ADR-046, C-059, C-063, C-084 |

## Problem And Evidence

Demo run 45106599832 failed in step "Issue workload credentials and prove Business Platform uses them" (`scripts/goal006_wid_gate.py`) with `owner_link[billing]=UNAVAILABLE; owner_link[professional-runtime]=UNAVAILABLE`, although both issuer jobs succeeded and Business Platform held a READY credential.

Two independent defects were found with Azure logs and the live Demo:

1. **Probe compared the wrong identity.** The WBE and PR `/internal/v1/service-link` handlers answer `peer_identity_uri` with the identity of the caller (their tests assert the Business Platform URI). `OwnerLinkProber` compared it with the target owner's URI, so the link could never become READY. Live evidence: billing and PR logged `GET /internal/v1/service-link 200 OK` every five minutes from 04:17 UTC while `/health/detail` kept reporting `UNAVAILABLE`. The unit test stub echoed the owner's URI, so it encoded the same mistake.
2. **Private listeners scaled to zero.** Billing and PR had no minimum replica. KEDA scaled them to zero at 04:07 UTC; the Business Platform probe woke PR at 04:12 (`0 to 1`, `s0-upstream_rq_total`) and the cold start outlasted the 10-second probe timeout. Business Platform then waited a full 300 seconds for the next probe. The AI runtime already carries one warm replica for the same reason (`air_min_replicas`).

## Authority And Scope

### In scope

1. The probe treats a link as READY only when the owner answers `status:"ok"` and echoes Business Platform's own identity URI.
2. Business Platform re-probes at the 30-second minimum interval while any owner link is UNAVAILABLE.
3. Billing and Professional Runtime keep one warm replica in Demo and UAT (`billing_min_replicas` defaults to 1; `pr_min_replicas` set to 1 in the Demo and UAT roots; Production already requires a positive value).
4. Local execution against live Demo of every deployment step after the failed gate.

### Out of scope

- Changing the owner handlers, the registry or the issuer.
- Redeploying Demo, which needs Founder approval.

## Canonical Requirement Index

Each row is one normative obligation. The ledger `WC-153-requirements.yaml` binds to this file's complete SHA-256 digest; any edit of this file after the ledger is written requires a new digest.

| ID | Obligation |
|---|---|
| WC153-R001 | An owner link is READY only when the owner echoes Business Platform's own identity URI; echoing the owner's URI is UNAVAILABLE |
| WC153-R002 | While any owner link is UNAVAILABLE, Business Platform re-probes at the 30-second minimum interval; otherwise it uses the credential refresh interval |
| WC153-R003 | Terraform keeps one warm replica for billing-engine and professional-runtime in Demo and UAT |

## Implementation Record

Evidence at the exact head (commands and results) is in the PR body. Unproven until Demo is redeployed: that both links report READY after the new revisions start, and that the steps after the gate pass in the workflow itself (each was exercised locally against live Demo).
