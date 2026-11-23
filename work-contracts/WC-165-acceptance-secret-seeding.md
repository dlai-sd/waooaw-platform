# WC-165 - Acceptance Secret Seeding And Demo Enablement

## Record Control

| Field | Value |
|---|---|
| Work Contract | WC-165 |
| Office | Platform IT Expert (INST-010) |
| Initiative | IB-165 |
| Founder assignment | Current conversation, 2026-11-23: "yes, i want full automation where i will copy secret from host system and copy at place which you tell me, once for all"; and "I open a small PR turning on acceptance_enabled and acceptance_vault_enabled for Demo ... Say if you want that PR now" answered with the same instruction |
| Status | IMPLEMENTATION_AUTHORIZED. Evidence is in the PR body at the exact head |
| Baseline | `origin/main` at `36175a89` (PR #630 merged) |
| Branch | `ib/165/acceptance-secret-seeding` |
| Decisions | ADR-054 item 9 and ADR-055 (accepted); WC-164 |
| Requirement ledger | [WC-165-requirements.yaml](./WC-165-requirements.yaml) |
| Constitutional basis | C-063, C-065, C-080 |

## Authority And Scope

### In scope

1. The Demo foundation root enables the acceptance identity and the dedicated vault and lists the Founder's object id as the only secret officer. UAT stays off.
2. `scripts/acceptance_seed_secrets.sh`: a Docker-only script that creates a private template outside every repository, signs in by device code, stores each filled value into the acceptance vault through stdin, shreds the file and lists names only.
3. Runbook step 4 replaced by this flow; the wrong secret name example removed.

### Out of scope and prohibited

- Applying Terraform (the Founder runs the Environment deployment), reading, holding or entering any secret value, changing the private vault, any harness or product change.
- Entering the Keycloak provisioner client secret (it is produced by the Keycloak step).

## Inputs

| Input | Status |
|---|---|
| PR #630 merged | Present on `main` |
| Founder object id | Read from the Founder's own signed-in Azure session; a principal id, not a credential |
| Secret values | Held by the Founder only; never seen by the author |

## Canonical Requirement Index

| ID | Obligation |
|---|---|
| WC165-R001 | Demo enables the identity and the dedicated vault with exactly one officer principal; UAT keeps both off |
| WC165-R002 | The seed script covers exactly the profile secrets except the Keycloak one, and passes values only through stdin (never arguments, output or git) |
| WC165-R003 | The seed script keeps existing secrets unless told, refuses a non-test Razorpay key id, unknown keys and a file readable by others, keeps the file on any failure and deletes it on success |
| WC165-R004 | The runbook describes the one-time flow and carries no wrong secret name |

## Definition Of Done

1. Every requirement has executable evidence run in Docker at the exact head; shellcheck, `terraform fmt` and `validate` pass.
2. Platform state refreshed; PR body prepared; author review recorded; Founder reviews and merges.
3. No Terraform apply or secret entry is claimed.

## Stop Conditions

- Any need to print, log or hold a secret value, or to open the private environment vault.

## Implementation Record

Evidence at the exact head is in the PR body.

- **Founder sequence after merge:** run the Environment deployment for Demo (creates the vault), then `login`, `init`, fill the file, `seed`.
- **Razorpay:** the private environment vault cannot be read from a Codespace (`ForbiddenByConnection`), so the Founder copies the three test values into the template.
- **Not run:** any Terraform plan or apply, and any real seeding.
