# WC-150 - Private Listener Start-Up Defect And Start-Up Guard

## Record Control

| Field | Value |
|---|---|
| Work Contract | WC-150 |
| Authoring office | Platform IT Expert (INST-010), under Founder assignment in the current conversation (lightweight record; the Founder may re-assign the number or office) |
| Initiative | IB-150 |
| Founder assignment | Current conversation: Environment Deployment run 45034410008 failed; "of course, and ensure we catch such static failures in testing" |
| Status | IN PROGRESS. Evidence is in the PR body at the exact head |
| Baseline | `main` at `4e2532ad` |
| Related contracts | WC-147 (Key Vault workload credentials); WC-149 (AI runtime private listener); ADR-046 |
| Requirement ledger | [WC-150-requirements.yaml](./WC-150-requirements.yaml) |
| Constitutional basis | C-026, C-059, C-063, C-083, C-084 |

## Problem And Evidence

Demo deployment run 45034410008 applied Terraform, then failed the gate that requires every activated Container Apps revision to become ready. `ca-demo-ai-runtime` (revisions 108 and 109) and `ca-demo-professional-runtime` (revisions 111 and 112) are `ActivationFailed`; the AI runtime reports "Deployment Progress Deadline Exceeded. 0/1 replicas ready."

Console logs of both services in `law-waooaw-demo-validation` show the same traceback from `private_server.py`, line 113 (AI runtime) and its professional-runtime twin: `AttributeError: 'Config' object has no attribute 'ssl'`, then `entrypoint child_exited status=1`. Pinned uvicorn 0.30.6 assigns `Config.ssl` only inside `Config.load()`, so `main()` reads an attribute that does not exist yet. `billing-engine/private_server.py` calls `config.load()` first and is healthy.

The unit tests missed it because they replace the uvicorn config with a mock that has an `ssl` attribute, so `main()` never ran against a real `uvicorn.Config`. No gate started a private listener the way the cloud does.

## Authority And Scope

### In scope

1. Fix `main()` in the AI runtime and professional runtime private listeners: load the config first, then read `config.ssl`; Key Vault mode then installs the hot-reload TLS context and directory mode keeps its file-based context.
2. Real start-up tests for billing, AI runtime and professional runtime: `main()` runs against a real `uvicorn.Config` with only the server loop replaced, in directory mode with generated certificate files and, for the AI runtime and professional runtime, in Key Vault mode with a stand-in credential holder.
3. A repository guard in the quality gate that fails when any `src/*/private_server.py` `main()` reads `config.ssl` before calling `config.load()`.
4. Wire the guard into the quality-scripts gate; the service tests already run in each service's test gate.

### Out of scope

- Changing what the listeners do after start-up, the credential bundle, Terraform or the registry.
- Proving Key Vault access, mTLS between services, provider egress or Meta behaviour; those stay unproven until the Demo redeploy.

## Canonical Requirement Index

Each row is one normative obligation. The ledger `WC-150-requirements.yaml` binds to this file's complete SHA-256 digest; any edit of this file after the ledger is written requires a new digest.

| ID | Obligation |
|---|---|
| WC150-R001 | AI runtime and professional runtime `main()` call `config.load()` before reading `config.ssl`, and then serve with the Key Vault TLS context in Key Vault mode or the file-based context in directory mode |
| WC150-R002 | Billing, AI runtime and professional runtime start-up is tested against a real `uvicorn.Config`, not a mock, in each credential mode the service supports |
| WC150-R003 | A repository guard fails when any `src/*/private_server.py` reads `config.ssl` in `main()` before calling `config.load()` |
| WC150-R004 | The guard runs in the quality-scripts gate, and the contract records what stays unproven until Demo is redeployed |

## Implementation Record

Evidence at the exact head (commands and results) is in the PR body. Unproven until Demo is redeployed: that both revisions become Healthy, that Key Vault credentials resolve and that the services accept mTLS peers. Both services log `workload_credential ... reason=UNISSUED` just before exiting, which is the expected first state; a second fault behind this one cannot be excluded.
