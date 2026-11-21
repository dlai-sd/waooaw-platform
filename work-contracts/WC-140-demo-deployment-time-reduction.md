# WC-140 - Demo Deployment Time Reduction

## Record Control

| Field | Value |
|---|---|
| Work Contract | WC-140 |
| Authoring office | Platform IT Expert (INST-010), under Founder assignment in the current conversation (lightweight record; the Founder may re-assign the number or office) |
| Initiative | IB-140 |
| Founder assignment | Current conversation: "review deploy.yaml workflow run to understand timings"; "ok, please proceed and i suggest make one pr combining both. Test locally az cli end to end and prepare pr as restrospective pr so we dont waste time and money in rework" |
| Status | IMPLEMENTED - FOUNDER REVIEW PENDING. Evidence is in the PR body at the exact head |
| Baseline | `origin/main` `3c54b115` (WC-138 merged) |
| Related contracts | WC-124 database authority chain; WC-134 Demo WhatsApp activation |
| Requirement ledger | [WC-140-requirements.yaml](./WC-140-requirements.yaml) |
| Constitutional basis | C-059, C-063 |

## Authority And Scope

### In scope (every change keeps the failure and recovery paths unchanged)

1. The terminal WC-124 authority step proves zero database authority from Azure itself, read-only, when the deployment succeeded, instead of repeating a foundation plan and apply.
2. The three normal-path foundation authority flips plan against the state the initial foundation plan of the same run just refreshed.
3. The activation-readiness gate and the Demo revision cleanup inspect Container Apps concurrently.
4. The two GitHub-hosted jobs restore the pinned Azure CLI extensions from a cache.

### Out of scope (separate Work Contracts, each needs Founder authorization)

- Skipping migrations, Temporal qualification or the database authority chain by digest comparison.
- Running verification concurrently with runner clean-up, and the vendor migrations concurrently.
- Shorter job polling intervals and a shorter WhatsApp activation proof wait.
- Any change to the Terraform workload module (it needs the Pre-PR Runtime Evidence gate).
- Dispatching a deployment, approval and merge.

## Canonical Requirement Index

Each row is one normative obligation. The ledger `WC-140-requirements.yaml` binds to this file's complete SHA-256 digest; any edit of this file after the ledger is written requires a new digest.

| ID | Obligation |
|---|---|
| WC140-R001 | After a successful deployment the terminal step writes `zero-authority-verified` evidence only when Azure reports zero Entra bootstrap administrators and zero provisioner Key Vault Secrets Officer assignments, and runs no Terraform in that case |
| WC140-R002 | If Azure reports any leftover authority after a successful deployment, or the deployment did not succeed, the terminal step still runs the full forced removal and fails closed unless both counts reach zero |
| WC140-R003 | The schema-reconciliation, plan-B and bootstrap-removal foundation plans use `-refresh=false`; the initial foundation plan and the terminal fallback plan still refresh state |
| WC140-R004 | Readiness and revision-cleanup inspections run concurrently, return the same observations and plans in the same order as the serial version, raise the first failure in app order, and perform every mutating call serially |
| WC140-R005 | Only the hosted `start-broker` and `cleanup-private` jobs restore the Azure CLI extension cache, keyed on the Dockerfile pins, using a commit-pinned action; the private runner still installs the pinned versions |

## Implementation Record

Evidence at the exact head (commands and results) is in the PR body. Local Azure evidence against Demo: the readiness pass over 12 apps took 44 s serially and 8 s concurrently with identical results; the revision-cleanup plan took 32 s and 8 s. The end-to-end saving of the deployment is measured by the first Demo deployment after merge, not claimed here.
