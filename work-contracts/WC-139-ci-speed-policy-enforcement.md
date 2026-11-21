# WC-139 - CI Speed Policy Enforcement And Routing

## Record Control

| Field | Value |
|---|---|
| Work Contract | WC-139 |
| Authoring office | Platform IT Expert (INST-010), under Founder assignment in the current conversation (lightweight record; the Founder may re-assign the number or office) |
| Initiative | IB-139 (continuation) |
| Founder assignment | Current conversation: "do proposed changes and any more if you feel necessary to ensure pr preparation and pre checks optimization" |
| Status | IMPLEMENTED - FOUNDER REVIEW PENDING. Evidence is in the PR body at the exact head |
| Baseline | `origin/main` `3c54b115` (WC-138 merged) |
| Related contracts | WC-138 CI validation speed-up |
| Requirement ledger | [WC-139-requirements.yaml](./WC-139-requirements.yaml) |
| Standing policy | [CI-VALIDATION-SPEED-POLICY](../standards/CI-VALIDATION-SPEED-POLICY.md) |
| Constitutional basis | C-059, C-063 |

## Authority And Scope

### In scope

1. A test that fails when a non-static pre-check node has no cheap-check dependency (rule V1).
2. A Business Platform test that fails when a test outside the named list starts a real Postgres container (rules V2, V3).
3. Routing: a pointer in `.github/copilot-instructions.md`, the Platform IT Expert office card and its CI repair path, and an enforcement table in the policy.

### Out of scope

- Any change to gate behaviour, thresholds or pre-check ordering.
- Release Qualification `az` parallelisation, hosted-CI carry-forward and the deploy workflow (on hold or separate Work Contracts).
- Deployment, approval and merge.

## Canonical Requirement Index

Each row is one normative obligation. The ledger `WC-139-requirements.yaml` binds to this file's complete SHA-256 digest; any edit of this file after the ledger is written requires a new digest.

| ID | Obligation |
|---|---|
| WC139-R001 | Every non-static pre-check node must have a dependency on a static pre-check, and the test fails otherwise |
| WC139-R002 | A Business Platform test file outside the named real-container list that names a real Postgres container fails the Business Platform gate |
| WC139-R003 | A new session reaches the speed policy from the always-loaded instructions, the Platform IT Expert office card and its CI repair path, and the policy states which rules a test enforces |

## Implementation Record

Evidence at the exact head (commands and results) is in the PR body.
