# Work Contract 131 - Install Pinned Azure CLI Extensions On The Deploy Runner

## Record Control

- Office: Platform IT Expert (INST-010).
- Assigned by: Founder, 2026-10-30, current conversation.
- Authority: Environment Deployment run 41042104645 (main cb47539, `image_home=azure`)
  failed at "Run WC-124 database provisioner". The Founder directed "deployment failed.
  let me know rca, evidence and proposed fix. along with this fix add this missing id into
  thes settings file for demo", consistent with the earlier instruction "while creating pr
  disable qualification run componenent".
- Baseline: origin/main at cb47539 (WC-130 merged).
- Status: LOCALLY QUALIFIED - Founder review/merge pending.

## Root Cause

The provisioner execution succeeded (10:47:53-10:49:29). Its result is read from
`az containerapp job logs show`, a command that exists only in the `containerapp`
extension. The deploy runner still uses the August-pinned image `332cbca`, built before
`infrastructure/runner/Dockerfile` added the extension pins, so it carries no extensions
and az installs the newest preview on demand. In this run the on-demand install failed and az
answered "'logs' is misspelled or not recognized"; the result file was empty and the
final `jq -e` exited 4 with no explanation. Run 41028762781 passed only because the
on-demand install worked that time.

The CI ACR upload was skipped because the Demo `publish_client_id` was not recorded, so
each deploy copied images itself (about 2.5 minutes in run 41042104645).

## Authority And Scope

In scope: install the Dockerfile-pinned extensions with retries at the start of the private
runner job; fail with a named error when the provisioner result is missing; record the Demo
image-publish identity `8894d1b4-758c-498c-9d25-8bac3de0dc68` (AcrPush on
`acrwaooawdemo2ed118`, federated subject `repo:dlai-sd/waooaw-platform:ref:refs/heads/main`).
Not in scope: rebuilding or re-pinning the runner image, UAT/Prod identities, deployments,
merges.

## Requirements And Definition Of Done

| ID | Requirement | Executable evidence |
|---|---|---|
| WC131-R001 | The private runner job installs the Dockerfile-pinned `containerapp` and `log-analytics` extensions with retries before any Azure CLI use and fails with a named error if they cannot be installed. | `tests/pipeline/test_goal006_az_extensions.py`; run inside runner image `332cbca`. |
| WC131-R002 | A missing provisioner result fails with a named error and the captured evidence instead of a bare `jq` exit. | `tests/pipeline/test_goal006_az_extensions.py`. |
| WC131-R003 | CI uploads release images to the Demo ACR using the recorded publish identity; UAT and Prod stay unrecorded. | `tests/pipeline/test_goal006_image_home.py`. |
| WC131-R004 | Validate, perform author review, and submit an exact-head PR with Founder-directed Release Qualification OFF. | Commands and results below and in the PR. |

## Stops And Rollback

Rollback: revert this PR. Setting the Demo `publish_client_id` back to null stops CI uploads;
deploys then copy images themselves as before.

## Validation And Delivery Evidence

- Pipeline tests (az extensions, image home, terraform foundations, Keycloak refresh, live
  inventory, runner image source, CI validation efficiency): 166 passed. Ruff, shellcheck and actionlint: PASS.
- Runner image `332cbca` has no extensions (`az version` shows `"extensions": {}`); the new
  script installs both pins on the first attempt, then reports `status=present` on re-run.
- `stream_job_logs` is identical in containerapp 1.2.0b5 and 1.3.0b5, so the pinned
  version keeps the log format the provisioner parser expects.
- Azure: identity client ID, AcrPush on the Demo ACR and the main-branch federated subject
  confirmed; the CI image jobs set no `environment:`.

## Rollout

Merge; the merge's CI run should log "Mirror image to environment ACRs" uploads to the Demo
ACR. Then re-run Environment Deployment for Demo with `apply` and `image_home=both`.
