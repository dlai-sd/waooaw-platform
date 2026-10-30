# Work Contract 130 - Verify Release Images From The Environment ACR

## Record Control

- Office: Platform IT Expert (INST-010).
- Assigned by: Founder, 2026-10-30, current conversation.
- Authority: Environment Deployment run 41028762781 (main ed77ff4a, `image_home=both`)
  failed independent verification. The Founder directed "fix this, resolve and test and
  give new pr" and "while creating pr disable qualification run componenent".
- Baseline: origin/main at ed77ff4a (WC-129 merged).
- Status: LOCALLY QUALIFIED AND LIVE DRY-RUN PASSED - Founder review/merge pending.

## Root Cause

WC-127 lets workloads pull release images from the environment ACR. In run 41028762781
`both` resolved to `azure`, so all seven release apps ran the identical digests from
`acrwaooawdemo2ed118.azurecr.io/dlai-sd/...`. `scripts/goal006_live_inventory.py`
compared the live image string with the exact `ghcr.io/dlai-sd/...@sha256:...` manifest
reference and reported seven `DIGEST_MISMATCH` violations, stopping verification before
the sign-in checks.

## Authority And Scope

In scope: accept a release member when it is the same repository path and digest in
the environment's own ACR (`acrwaooaw<env><first six subscription hex>.azurecr.io`,
subscription from the logged-in Azure account). Pinned third-party dependencies stay
exact. Not in scope: image-home selection, mirroring, deployments, merges.

## Requirements And Definition Of Done

| ID | Requirement | Executable evidence |
|---|---|---|
| WC130-R001 | Live inventory accepts release members at the manifest digest from the environment ACR and rejects other digests, repositories, environments, subscriptions, tags and ACR-hosted pinned dependencies. | `tests/pipeline/test_goal006_live_inventory.py`. |
| WC130-R002 | Deployment verification passes the logged-in subscription to the inventory check. | `tests/pipeline/test_goal006_live_inventory.py`. |
| WC130-R003 | The new check passes against live Demo and the exact ed77ff4a release manifest where the previous check fails. | Live evidence below. |
| WC130-R004 | Validate, perform author review, and submit an exact-head PR with Founder-directed Release Qualification OFF. | Commands and results below and in the PR. |

## Stops And Rollback

Rollback: revert this PR; Demo can deploy with `image_home=github` meanwhile.

## Validation And Delivery Evidence

- Pipeline tests (live inventory, terraform foundations, CI validation efficiency, image
  home, Keycloak refresh): 142 passed. Ruff check and format: PASS.
- Live dry-run with the ed77ff4a `registry-release-manifest.json` and live Demo
  inventory: previous check reports seven `DIGEST_MISMATCH`; new check
  `{"passed": true, "violations": []}`.
- Live provider-start, Google and Facebook verifiers against Demo: all PASS.

## Rollout

Merge, then re-run Environment Deployment for Demo with `apply` and `image_home=both`.
