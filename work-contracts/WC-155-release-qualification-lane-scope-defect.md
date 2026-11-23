# WC-155 - Release Qualification Lane Scope Defect

## Record Control

| Field | Value |
|---|---|
| Work Contract | WC-155 |
| Authoring office | Platform IT Expert (INST-010), under Founder assignment in the current conversation (lightweight record; the Founder may re-assign the number or office) |
| Initiative | IB-155 |
| Founder assignment | Current conversation: evaluate the Release qualification job, then "please do this change and give me on new pr", with the instruction that the merge (push to main) run is covered as well |
| Status | IN PROGRESS. Evidence is in the PR body at the exact head |
| Baseline | `main` at `cf739c71` |
| Related contracts | WC-100, WC-102, WC-109 (qualification and change scope); WC-154 (PR process) |
| Requirement ledger | [WC-155-requirements.yaml](./WC-155-requirements.yaml) |
| Constitutional basis | C-059, C-065, C-071 |

## Problem And Evidence

`scripts/validation_control/qualification_change_scope.py` chooses the Release qualification lanes (tests, postgres, demo-data, simulator, azure) from the changed-file list. Any path whose top-level directory or root file it does not know forces every lane on ("missing or ambiguous scope broadens instead of skipping"). `validation/` and `.githooks/` were not known top-level directories, and `README.md`, `SPRINT-REGISTRY.md`, `ARCHITECTURE.md` and `CHANGELOG.md` were not known root files. Since WC-152 every PR regenerates README.md and SPRINT-REGISTRY.md and touches `validation/process-control.yaml`, so almost every PR broadened to all lanes. A sample of 28 executed runs averaged about 457 seconds, and in the runs read in detail the Azure-emulator lane took 310 to 376 seconds, about 75% of the job. Replaying the real file lists of PRs 616 to 623 through the selector gave all five lanes for 6 of 8 PRs. The same selector decides the lanes on a push to `main` (`validation-plan.yaml` diffs `before..sha`), so merges paid the same cost.

## Authority And Scope

### In scope

1. Treat `.githooks`, `validation` (as a top-level directory) and the repository documents `README.md`, `SPRINT-REGISTRY.md`, `ARCHITECTURE.md`, `CHANGELOG.md` as known paths, so they no longer broaden the scope.
2. Keep every deliberate broadening: the gate catalog (`validation/engineering-validation.yaml`), `validation/runner-supply.json`, the shared runner and validation-control files, an empty file list, and any genuinely unknown path still run every lane.
3. Regression tests, and replay of real PR and merge-commit file lists as evidence.

### Out of scope

- Removing the Azure lane from catalog-change broadening, nightly-only scheduling, or any gate threshold.
- The cross-stack handshake test suggested in the evaluation.

## Canonical Requirement Index

Each row is one normative obligation. The ledger `WC-155-requirements.yaml` binds to this file's complete SHA-256 digest; any edit of this file after the ledger is written requires a new digest.

| ID | Obligation |
|---|---|
| WC155-R001 | A change set made only of repository documents, `validation/process-control.yaml`, `.githooks`, standards and Work Contracts selects no release lane and is not broadened |
| WC155-R002 | The gate catalog, `validation/runner-supply.json`, shared validation-control files, an empty list and unknown paths still broaden to every lane |
| WC155-R003 | Pull request and push-to-main runs use the same selector, so the merge run narrows identically |

## Implementation Record

Evidence at the exact head (commands and results) is in the PR body. Unproven until the next CI runs: the hosted job-duration effect.
