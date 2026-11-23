# WC-154 - Exact-Head Evidence Reuse And Compulsory PR Preparation Path

## Record Control

| Field | Value |
|---|---|
| Work Contract | WC-154 |
| Authoring office | Platform IT Expert (INST-010), under Founder assignment in the current conversation (lightweight record; the Founder may re-assign the number or office) |
| Initiative | IB-154 |
| Founder assignment | Current conversation: "I see value in your proposal. When you implement, do it in such way that future agent session will follow this path / utilities etc as compulsion instead of drifting" |
| Status | IN PROGRESS. Evidence is in the PR body at the exact head |
| Baseline | `main` at `1b43118a` |
| Related contracts | WC-100, WC-109 (pre-check graph and reuse); WC-152 (process control) |
| Requirement ledger | [WC-154-requirements.yaml](./WC-154-requirements.yaml) |
| Constitutional basis | C-059, C-065, C-071 |

## Problem And Evidence

Implementation took about 30% of the elapsed time of recent PRs; the rest went to PR preparation and CI. In the WC-153 session the lifecycle gate ran five times and the prechecks ran on every bind, because `scripts/prepare_pr_body.py` reused earlier evidence only when an agent passed `--precheck-evidence-file` or `--runtime-evidence-file` by hand, and every new head needed two binds (before and after push). Node-level reuse inside the precheck orchestrator already works and is keyed by input digests; gitleaks and the dependency scan are deliberately non-reusable. Agents also pushed heads that the open PR body did not name, which made C-065 fail in CI.

## Authority And Scope

### In scope

1. `prepare_pr_body.py` reuses its own `<body>.precheck-evidence.json` only for the exact base, head, changed files, gate configuration and runner graph, and its own `<body>.runtime-evidence.json` only while it binds the head (same head, or an ancestor with no runtime-affecting change since), and prints when it does. `--no-reuse` forces a fresh run.
2. `.githooks/pre-push` refuses a push to a branch with an open PR whose body `Reviewed Commit` is not the pushed head, and prints the exact binding command.
3. The compulsion: speed policy rule V9, the office card and global instructions, the hook and its test pinned in `validation/process-control.yaml`, and the new test wired into the `quality:scripts` gate and release qualification.

### Out of scope

- Changing gate thresholds, the reusable flag of any gate, or what CI recomputes (Founder authorization and a separate Work Contract are needed to let CI verify evidence instead of recomputing).
- Redeploying anything.

## Canonical Requirement Index

Each row is one normative obligation. The ledger `WC-154-requirements.yaml` binds to this file's complete SHA-256 digest; any edit of this file after the ledger is written requires a new digest.

| ID | Obligation |
|---|---|
| WC154-R001 | Evidence this tool wrote earlier is reused automatically only when it binds the exact base, head, changed files, gate configuration and runner graph (prechecks) or the head (lifecycle gate); anything else is re-executed; `--no-reuse` re-executes everything |
| WC154-R002 | A push to a branch with an open PR is refused when the PR body does not name the pushed head, with the exact binding command; other pushes and gh failures are not blocked |
| WC154-R003 | The path is compulsory: policy V9, the office card, the global instructions, process-control pinning of the hook and its test, and the test in the `quality:scripts` gate and release qualification |

## Implementation Record

Evidence at the exact head (commands and results) is in the PR body.
