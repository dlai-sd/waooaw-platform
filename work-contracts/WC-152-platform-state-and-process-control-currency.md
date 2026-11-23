# WC-152 - Platform State And Process-Control Currency

## Record Control

| Field | Value |
|---|---|
| Work Contract | WC-152 |
| Authoring office | Platform IT Expert (INST-010), under Founder assignment in the current conversation (lightweight record; the Founder may re-assign the number or office) |
| Initiative | IB-152 |
| Founder assignment | Current conversation, 2026-11-23: "bring these components to present state as these are stale and correct gaps which make them stale or dont keep upto date with every PR preparation" (the README Platform Status and `constitution/PROJECT_STATE.md`, and `validation/process-control.yaml`). Founder decisions: derive facts from the repository, enforce at PR preparation and in CI, extend the process-control scope, backfill SPRINT-REGISTRY in full |
| Status | IMPLEMENTED - FOUNDER REVIEW PENDING. Evidence is in the PR body at the exact head |
| Baseline | `main` at `edd9f9e4` (PR #620) |
| Related contracts | WC-061 (PROJECT_STATE schema v2); WC-100 (process-control manifest); WC-139 (CI speed policy) |
| Requirement ledger | [WC-152-requirements.yaml](./WC-152-requirements.yaml) |
| Constitutional basis | C-008, C-032, C-059, C-065, C-071, C-080 |

## Problem And Evidence

- The README Platform Status, `ARCHITECTURE.md`, `constitution/AGENT-ENTRY.md` and `SPRINT-REGISTRY.md` were rendered by
  `scripts/sync_platform_state.py` from hand-typed registry counts last edited on 2026-09-11 (WC-080, 83 Work Contracts,
  44 ADRs). The repository held WC-151, 144 Work Contract ids and 53 ADR files. The sync test only compared the summaries
  with that stale registry and was wired into no validation gate; no PR step refreshed anything.
- `constitution/PROJECT_STATE.md` was 309 lines against its own 200-line rule, described WC-136 to WC-147 as awaiting review
  after they merged, and its bootstrap-read sections were stale.
- `validation/process-control.yaml` pinned three files, never changed its version (`wc100-r033-v1`), relied on a hand-bumped
  pytest pin, covered neither PR preparation nor the governance standards, and was verified by no PR step.
- BOOTSTRAP Step 2 asked for fields (Authorized Office, Engineering Status, Epoch) that the README did not carry.
- `adr/ADR-INDEX.md` omitted ADR-042, 043, 044, 045 and 048 and counted 51 ADRs.

## Authority And Scope

### In scope

1. `scripts/derive_platform_state.py` derives Work Contract, ADR, claim and CCT counts and the latest delivered Work Contract
   from the tree and a Git-built, committed delivery ledger; the registry keeps judgement fields only.
2. `scripts/sync_platform_state.py` renders every summary from derived facts plus a generated Work Contract index (WC-081
   onward) in `SPRINT-REGISTRY.md`; `--check` fails on drift.
3. `validation/process-control.yaml` v2: sources are the union of every control's sources (extended with PR preparation,
   resource governance, CI speed policy and state currency), a monotonic revision and a content-hash version, verified or
   refreshed by `scripts/verify_process_control.py`.
4. `scripts/run_platform_state_refresh.sh` refreshes ledger, summaries and manifest in Docker; `scripts/prepare_pr_body.py`
   fails a PR whose summaries, manifest, revision or delivery ledger are stale; the same checks and their tests run in
   `quality:scripts`.
5. Reconcile `PROJECT_STATE.md` (below 200 lines, revision 383 retained at a git object), the README Epoch line, BOOTSTRAP
   Step 2, the office card and the ADR index.

### Out of scope

- Editing the status text of historical Work Contract files, the long-form README body, `VERSION` or `CHANGELOG.md`.
- Any `src/` change, deployment, provider or cloud action.

## Canonical Requirement Index

Each row is one normative obligation. The ledger `WC-152-requirements.yaml` binds to this file's complete SHA-256 digest; any edit of this file after the ledger is written requires a new digest.

| ID | Obligation |
|---|---|
| WC152-R001 | Counts, version, as-of date and the latest delivered Work Contract are derived from the repository and the delivery ledger, not typed into the registry |
| WC152-R002 | The delivery ledger is rebuilt from Git first-parent history and a missing merged pull request is detected |
| WC152-R003 | README, ARCHITECTURE, AGENT-ENTRY, SPRINT-REGISTRY (with the generated WC-081 onward index), knowledge index, ADR index and the PROJECT_STATE date line are rendered from derived facts and `--check` fails when stale |
| WC152-R004 | `PROJECT_STATE.md` is reconciled to present state below 200 lines, revision 383 is retained at a git object and indexed, and the ADR index lists every ADR file |
| WC152-R005 | The process-control manifest pins exactly the sources named by its controls, carries a revision and content-hash version, and refresh is idempotent and bumps the revision only when a digest changed |
| WC152-R006 | `prepare_pr_body.py` fails a PR with a stale summary, stale manifest, non-increased revision or a ledger missing merged pull requests, and the checks with their tests run in `quality:scripts` |
| WC152-R007 | BOOTSTRAP Step 2, the office card and the Docker-only refresh script describe and perform the refresh before the final commit |

## Implementation Record

Evidence at the exact head (commands and results) is in the PR body. Known limits: the Work Contract index status column repeats
each file's own authoring-time text and can lag a merge; Work Contract to PR mapping uses `WC-NNN` references found in merged
commits and branch names, so a pull request without such a reference is recorded with no Work Contract. The delivery ledger is
checked against Git only at PR preparation; hosted CI checks the tree for consistency because a merge commit cannot be in the ledger
of the pull request that created it.
