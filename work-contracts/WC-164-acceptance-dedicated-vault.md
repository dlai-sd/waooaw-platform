# WC-164 - Dedicated Acceptance Key Vault

## Record Control

| Field | Value |
|---|---|
| Work Contract | WC-164 |
| Office | Platform IT Expert (INST-010) |
| Initiative | IB-164 |
| Founder assignment | Current conversation, 2026-11-23: help with the blocked items one at a time, starting with the Key Vault access path; the Founder was unavailable to choose, so the pragmatic option A (dedicated acceptance vault, Demo) was selected as recommended |
| Status | IMPLEMENTATION_AUTHORIZED. Evidence is in the PR body at the exact head |
| Baseline | `origin/main` at `aded15d3ffff138954c507ac433b19b27beb1a42` |
| Branch | `ib/164/acceptance-dedicated-vault` |
| Decisions | ADR-054 item 9 and ADR-055 (accepted) |
| Requirement ledger | [WC-164-requirements.yaml](./WC-164-requirements.yaml) |
| Constitutional basis | C-063, C-065, C-080 |

## Authority And Scope

### In scope

1. A dedicated acceptance Key Vault in the foundation Terraform module: off by default, Demo and UAT only, requires the acceptance identity, rights-based authorization, purge protection, reachable from GitHub-hosted runners.
2. A Secrets Officer role on that vault for named Founder principals, and the acceptance identity's secret reader roles scoped to it.
3. Demo and UAT roots pass the new variables (both off) and expose the vault name; the demo profile reads `kv-waooaw-demo-acc`.
4. The runbook records the access path decision and that the three Razorpay test values are copied into the new vault.

### Out of scope and prohibited

- Applying Terraform, entering any secret, or changing the private environment vault or its network rules.
- Any change to the harness, the workflow logic or the product.

## Inputs

| Input | Status |
|---|---|
| PR #629 merged | Present on `main` |
| Finding that the environment vault is private (`public_network_access_enabled = false`) | Recorded in PR #627 and the WC-158 Implementation Record |
| Founder choice of access path | Not given; option A chosen as the recommended, smallest-blast-radius option and presented to the Founder with reasons |

## Canonical Requirement Index

| ID | Obligation |
|---|---|
| WC164-R001 | The acceptance vault is created only when `acceptance_vault_enabled` is true, which needs the acceptance identity and Demo or UAT, and defaults to false in the module and both roots |
| WC164-R002 | The vault uses rights-based authorization and purge protection, is named `kv-<env>-acc`, and is separate from the private environment vault |
| WC164-R003 | The acceptance identity's secret reader roles are scoped to the acceptance vault when it is enabled, and the Secrets Officer role goes only to the listed principals |
| WC164-R004 | The demo profile reads the dedicated vault and the runbook records the decision, the copy of the three Razorpay test values and the apply steps |

## Definition Of Done

1. Every requirement has direct executable evidence run in Docker at the exact head; `terraform fmt` and `validate` pass for the demo foundation root.
2. Platform state refreshed in Docker; PR body prepared with `scripts/prepare_pr_body.sh`; author review recorded for the exact head; Founder reviews and merges.
3. No Terraform apply or secret entry is claimed.

## Stop Conditions

- Any need to open the private environment vault or to hold a credential in GitHub.
- A request to enable the vault in an environment root before the Founder has reviewed a plan.

## Implementation Record

Evidence at the exact head is in the PR body.

- **Trade-off.** The vault is reachable from the internet and protected only by access rights. It holds sandbox and test values plus the Keycloak provisioner client secret (which can manage users in the Demo realm only). The private vault keeps everything else. Options B (harness job in the private network) and C (self-hosted runner with Docker) remain available and need their own contracts.
- **Razorpay copies.** The three Razorpay test values must be copied into the new vault because the acceptance identity reads only that vault.
- **Not run:** any Terraform plan or apply against Azure.
