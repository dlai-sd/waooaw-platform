# WC-145 - CI Image Layer Cache Reuse

## Record Control

| Field | Value |
|---|---|
| Work Contract | WC-145 |
| Authoring office | Platform IT Expert (INST-010), under Founder assignment in the current conversation (lightweight record; the Founder may re-assign the number or office) |
| Initiative | IB-145 |
| Founder assignment | Current conversation: "proceed as per your plan of 3 prs"; implementation authorized for WC-145 first, then WC-143, then WC-144 |
| Status | IMPLEMENTED - FOUNDER REVIEW PENDING. Evidence is in the PR body at the exact head |
| Baseline | `origin/main` `cf7c1f72` (WC-142 merged; merge run 44928125993, ai-runtime publish job 328 s against about 100 s for the other six services) |
| Related contracts | WC-109 security refresh layers (design preserved, cadence changed); WC-141 digest-gated reuse on merge (test reuse stays there) |
| Requirement ledger | [WC-145-requirements.yaml](./WC-145-requirements.yaml) |
| Constitutional basis | C-059, C-063 |

## Problem And Evidence

Every service Dockerfile declares `ARG SECURITY_REFRESH` before the pip install (Python services) and before `apt-get upgrade`. `ci.yaml` passed `SECURITY_REFRESH=${{ github.run_id }}`, so these layers were invalid on every run. In run 44928125993 the ai-runtime pip layer rebuilt (68 s), exported a new multi-hundred-MB blob (38 s), pushed it (56 s) and wrote it to the GitHub Actions cache (108 s). The same cause makes the six other services slower than necessary.

## Authority And Scope

### In scope

1. The refresh argument is a stable key that changes at most once per UTC day, in both the pull-request `build` job and the merge `publish` job.
2. The repository variable `WAOOAW_IMAGE_REFRESH_EPOCH` is a kill switch: changing its value forces an immediate refresh of the OS and pip layers on the next build.

### Out of scope

- Re-tagging the pull-request image on merge, and reusing test results on merge (WC-141, each needs its own authorization because of attestation, signing and the release manifest contract).
- Any change to Dockerfiles, Trivy, `dep-scan`, license check or SAST.
- A scheduled warm-up build on main.

## Security Posture Decision

Before this contract the OS and pip layers were refreshed on every run. Now they refresh at most every UTC day, or immediately when the variable is changed. Direct dependencies are pinned, but transitive ones are not, so the daily refresh is what picks up transitive fixes. Trivy and `dep-scan` still gate every pull request and every merge. Failure mode: a newly fixed HIGH or CRITICAL finding can block a release until the next UTC day. Runbook: set `WAOOAW_IMAGE_REFRESH_EPOCH` to any new value and rebuild. The first merge of each UTC day is a cold build, as it is today.

## Canonical Requirement Index

Each row is one normative obligation. The ledger `WC-145-requirements.yaml` binds to this file's complete SHA-256 digest; any edit of this file after the ledger is written requires a new digest.

| ID | Obligation |
|---|---|
| WC145-R001 | The `build` and `publish` jobs each resolve the refresh key in a step that runs before the image build step, as `<epoch or daily>-<UTC yyyymmdd>`, and pass it as `SECURITY_REFRESH`; `github.run_id` is no longer a build argument |
| WC145-R002 | The epoch comes from the repository variable `WAOOAW_IMAGE_REFRESH_EPOCH` and defaults to `daily` when it is unset |
| WC145-R003 | The Dockerfile refresh layers, Trivy, `dep-scan`, license check and SAST are unchanged |

## Implementation Record

Evidence at the exact head (commands and results) is in the PR body. The expected saving is about 2 minutes on merge CI, mostly on ai-runtime, and is measured by the first merge after the first cold build of a UTC day; it is not claimed here.
