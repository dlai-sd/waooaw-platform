# WC-148 - Founder Provider And Credential Registry Screen

## Record Control

| Field | Value |
|---|---|
| Work Contract | WC-148 |
| Authoring office | Platform IT Expert (INST-010), under Founder assignment in the current conversation (lightweight record; the Founder may re-assign the number or office) |
| Initiative | IB-147 (delivered in the same PR as WC-147) |
| Founder assignment | Current conversation: "Founder screen for platform used APIs (LLM etc.) and agent specific paid APIs; founder enters values, tests, and WAOOAW uses them on the fly once confirmed and saved; security like other Founder screens"; "of course yes include and test and confirm item 5 works"; "scope not stop with creating screen but adding menu for it, styling etc. ie waooaw standards" |
| Status | IN PROGRESS. Evidence is in the PR body at the exact head |
| Baseline | `ib/147/cloud-workload-credentials` |
| Related contracts | WC-147 (cloud workload credentials, same PR); WC-144 (deferred this scope); ADR-042 Section 1 (provider registry) and Section 2 (tool gateway); ADR-014 (Key Vault); ADR-046 Section 12 |
| Requirement ledger | [WC-148-requirements.yaml](./WC-148-requirements.yaml) |
| Constitutional basis | C-023, C-059, C-063, C-083, C-084 |

## Problem And Evidence

The Founder has no way to enter a platform LLM key or an agent-specific paid API key, check that it works, and make WAOOAW use it without a deployment. Evidence in the repository at the baseline:

- `business.provider_configs` (ADR-042) holds provider routing rows with a `vault_path_key`, but no credential version, no test state and no write API. `ProvidersController` is read-only service-to-service.
- `/admin/azure-key-vault` writes a raw secret with the browser's Azure token for one hard-coded administrator email. It cannot test, version, roll back or tell which provider a secret belongs to, and it has no production target.
- The AI runtime dispatches only to local Ollama. `_dispatch_mid` and `_dispatch_frontier` raise `NotImplementedError`, so no saved key is consumed by any running code path.

## Authority And Scope

### In scope

1. Registry schema: provider category (platform LLM or agent API), optional agent type, optional test endpoint and header scheme, and a credential version history with exactly one active version per provider. Seed platform-level rows for OpenAI, Anthropic, Google and Sarvam with no credential.
2. Business Platform Founder-only admin API: list, create provider, list versions, Test, Confirm and save, and roll back. Every write and Test needs the same fresh step-up that pricing admin requires. No response, log or error ever contains a secret value.
3. Test performs one read-only HTTPS call to the provider's test endpoint with the entered value, with SSRF limits (HTTPS only, no private, loopback or link-local addresses, no redirects, short timeout), and returns only a sanitized outcome. Confirm re-runs the same test on the submitted value in the same request and writes only if it passes; a provider with no test endpoint needs an explicit acknowledgement.
4. Confirm writes a new Key Vault secret version through the Business Platform managed identity, records it as the single active version, and supersedes the previous one. Rollback re-activates an earlier recorded version without reading or re-sending the value.
5. A consumer library: the AI runtime resolver reads the active secret version through the registry (short TTL) and then that pinned version from Key Vault, so a new or rolled-back version is used without a restart. `_dispatch_mid` uses it for Sarvam, the one provider that already has an adapter. The running AI runtime service does not mount that dispatch path and has no authenticated link to the registry, so this item is proven by tests with a stand-in registry and vault, not by a running service (see Out of scope).
6. Founder web screen at `/admin/providers` with a menu entry, a same-origin proxy with a write limit, and WAOOAW portal styling, accessibility and responsive behaviour like the pricing screens. The existing Azure Key Vault screen is unchanged.
7. Terraform for every environment: Business Platform may write and the AI runtime may read only secrets whose names begin `provider-`, enforced by a role-assignment condition, plus the settings that carry the vault address.

### Out of scope

- Gemini and Anthropic dispatch adapters (`_dispatch_frontier`); keys for them can be stored and tested, but nothing consumes them until those adapters exist.
- Mounting the paid-model dispatch in the running AI runtime, and the workload credential for the AI runtime to registry call under ADR-046. The resolver sends no usable service token today, so until a follow-up contract delivers both, no running service consumes a saved key.
- Customer-owned credentials, OAuth providers, payer model, agency channel billing and tax invoices.
- Changing or removing `/admin/azure-key-vault`.
- New ADRs or claims.

## Canonical Requirement Index

Each row is one normative obligation. The ledger `WC-148-requirements.yaml` binds to this file's complete SHA-256 digest; any edit of this file after the ledger is written requires a new digest.

| ID | Obligation |
|---|---|
| WC148-R001 | The registry schema holds category, optional agent type, test endpoint settings and a credential version history with at most one active version per provider; seeded platform rows start with no credential |
| WC148-R002 | The admin API is Founder-only, every write and Test needs fresh step-up, and no response, log or error contains a secret value |
| WC148-R003 | Test returns a sanitized outcome after one SSRF-limited read-only call; Confirm re-tests the submitted value and writes only on a pass, or on explicit acknowledgement when no test exists |
| WC148-R004 | Confirm writes a Key Vault secret version, records it as the single active version and supersedes the prior one; rollback re-activates a recorded version without handling the value |
| WC148-R005 | The AI runtime resolver reads the active secret version through the registry and Key Vault, uses a new or rolled-back version without a restart, and the Sarvam dispatch function uses it; proven with a stand-in registry and vault |
| WC148-R006 | The Founder screen at `/admin/providers` offers create, Test, Confirm and save, history and rollback, appears in the menu only for the Founder, and follows WAOOAW portal styling and accessibility |
| WC148-R007 | Terraform for demo, uat and prod limits Business Platform writes and AI runtime reads to `provider-` secrets and validates |
| WC148-R008 | New tests run in the release-qualification gate; the contract records what is implemented and what is unproven until Demo |

## Implementation Record

Evidence at the exact head (commands and results) is in the PR body. Not provable before a Demo deployment: the role-assignment condition on Key Vault secret names, Business Platform writing a secret version with its managed identity, the AI runtime reading a pinned version with its identity, and a real provider accepting a Founder-entered key. Also unproven: that the Azure role-assignment condition on secret names is accepted without a perpetual plan difference, and that the deployer may write conditional role assignments. No running service consumes a saved key until the follow-up contract named in Out of scope.
