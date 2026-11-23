# WC-151 - WID Leaf Issuer Root-Key Read Defect

## Record Control

| Field | Value |
|---|---|
| Work Contract | WC-151 |
| Authoring office | Platform IT Expert (INST-010), under Founder assignment in the current conversation (lightweight record; the Founder may re-assign the number or office) |
| Initiative | IB-151 |
| Founder assignment | Current conversation: RCA and fix for Environment Deployment run 45049023141, with every later deployment step tested locally before the PR |
| Status | IN PROGRESS. Evidence is in the PR body at the exact head |
| Baseline | `main` at `6c98fcd4` |
| Related contracts | WC-147 (Key Vault workload credentials); WC-150 (private listener start-up); ADR-046 |
| Requirement ledger | [WC-151-requirements.yaml](./WC-151-requirements.yaml) |
| Constitutional basis | ADR-046, C-059, C-063, C-084 |

## Problem And Evidence

Demo deployment run 45049023141 failed in step "Issue workload credentials and prove Business Platform uses them" (`scripts/goal006_wid_gate.py`). The leaf-issuer job `job-demo-wid-leaf-issuer` received `HTTP 403` on `GET /keys/wid-root/...` from Key Vault `kv-waooaw-demo`.

Terraform (`workload-identity.tf`, `wid_job_grants`) gives `id-demo-wid-leaf-issuer` Crypto User on `wid-intermediate` only; only `id-demo-wid-ca-rotator` holds grants on `wid-root`, by design, because the root key is the trust anchor. Leaf mode, however, called `_check_state_keys`, which reads both keys. The unit tests used a fake vault with no RBAC, so they could not see the 403.

## Authority And Scope

### In scope

1. Leaf mode checks only the `wid-intermediate` key against its certificate; CA mode still checks both keys; the root certificate in `wid-ca-state` still anchors chain verification.
2. A regression test that derives the leaf-issuer key grants from Terraform and runs leaf mode against a vault that refuses every other key.
3. Local read-only exercise against live Demo of the deployment steps after the failing step.
4. The Founder communication preference and the test-locally-before-PR rule in the Platform IT Expert office card, with the process-control digest refreshed.

### Out of scope

- Granting the leaf issuer any right on the root key, and any change to Terraform, Key Vault or the registry.
- Redeploying Demo, or starting any Azure job; both need Founder approval.

## Canonical Requirement Index

Each row is one normative obligation. The ledger `WC-151-requirements.yaml` binds to this file's complete SHA-256 digest; any edit of this file after the ledger is written requires a new digest.

| ID | Obligation |
|---|---|
| WC151-R001 | Leaf mode reads and signs with only the `wid-intermediate` key and never reads `wid-root`; CA mode still checks both keys |
| WC151-R002 | A test fails on the old behaviour by running leaf mode against a vault that grants exactly the keys Terraform gives the leaf issuer |
| WC151-R003 | The office card records the Founder communication preference and the local pre-test rule, and `validation/process-control.yaml` carries its current digest |

## Implementation Record

Evidence at the exact head (commands and results) is in the PR body. Unproven until Demo is redeployed: that the leaf job completes (secret writes and trust-bundle publication were not exercised, because Key Vault is reachable only from inside the VNet), and that Business Platform, Billing and Professional Runtime reach READY after issuance.
