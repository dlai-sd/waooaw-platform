# Work Contract 128 - Runner-Stack ACR For Broker And Cleanup Control Images

## Record Control

- Office: Platform IT Expert (INST-010).
- Assigned by: Founder, 2026-10-30, current conversation.
- Authority: Founder declined a pipeline re-run after Environment Deployment run
  41004512229 failed at "Start private signing broker", chose Option 3 (runner-stack
  ACR for the broker and cleanup control image), and authorized the change, a live
  runner-stack redeploy from the Azure CLI, and a new PR.
- Baseline: origin/main at 45484459 (WC-127 merged).
- Status: LOCALLY QUALIFIED, LIVE-DEPLOYED TO DEMO RUNNER STACK - Founder review/merge pending.

## Authority And Scope

The broker and cleanup jobs pulled the 727 MB runner image cross-provider from
GHCR into the Central India runner environment. Pulls took 30-170 seconds and
timed out three times (broker replica deadline 300 s) while GHCR was degraded.
WC-127 deliberately left these dormant broker jobs on GHCR.

Add an ACR to the runner deployment stack and serve the per-execution control
image from it. Job definitions keep the GHCR blueprint digest, so stack
verification, the bootstrap blueprint, execution guards and the runner job image
(enforced by the baked lifecycle code) are unchanged. Any registry problem falls
back to GHCR and never blocks broker or cleanup start.

Not in scope: rebuilding the runner image, moving the runner job execution image,
`private-runner-infrastructure.yaml` and `workload-lease-reconciliation.yaml` broker
paths, UAT runner stack apply, deployments, merges.

## Requirements And Definition Of Done

| ID | Requirement | Executable evidence |
|---|---|---|
| WC128-R001 | The runner stack declares a Basic admin-disabled ACR, an image-pull identity with AcrPull, AcrPull for the cleanup identity, AcrPush for the bootstrap control-plane principal, and `registries` plus the pull identity on the runner, broker and cleanup jobs, keeping the GHCR job image. | Bicep build, live validate/what-if, static tests. |
| WC128-R002 | A resolver selects the runner-ACR control image: `publish` copies the digest when missing, `verify` only checks; any registry, job-configuration or copy problem falls back to the GHCR blueprint with a reason. | `tests/pipeline/test_goal006_runner_image_source.py`. |
| WC128-R003 | Environment Deployment broker and cleanup steps use the resolver with a bounded timeout and GHCR fallback, and accept the runner-ACR form in the control-image guard. | Workflow tests and actionlint. |
| WC128-R004 | Deployment verification and the bootstrap manifest admit the new identity and file digests. | Runner deployment and bootstrap tests. |
| WC128-R005 | The Demo runner stack is redeployed and the runner digest is present in the runner ACR and pullable by the pull identity inside the runner environment. | Live evidence below. |
| WC128-R006 | Validate locally and live, perform author review, and submit an exact-head PR using the repository template and preparation gate. | Commands and results below and in the PR. |

## Stops And Rollback

Stop for missing Founder decisions, unavailable validation, secret requirements or
two reproducible infrastructure failures. Rollback: the workflow falls back to GHCR
automatically; reverting this PR and redeploying the stack detaches the additive ACR
and identity (`actionOnUnmanage detachAll`).

## Validation And Delivery Evidence

- Pipeline tests (`waooaw-platform-test-runner-python:local`, `PYTHONPATH=/workspace`):
  runner image source, image home, demo deployment workflow, runner bootstrap,
  delivery workflow, deployment and prerequisites: PASS.
- Ruff check and format on changed scripts and tests: PASS. actionlint 1.7.7: PASS.
- `az bicep build` of `subscription.bicep`: PASS without warnings.
- `goal006_runner_bootstrap.py --environment demo`: passed, no violations.
- Live `az stack sub validate` and `az deployment sub what-if` for
  `goal006-demo-private-runner`: Create ACR, pull identity and three ACR role
  assignments; registries and pull identity added to runner, broker and cleanup jobs;
  broker `replicaTimeout` 300 to 600 (pending from main). No resource deletions.
- Live `az stack sub create` (same flags as the pipeline): succeeded 05:15-05:20 UTC.
- Runner digest seeded with server-side `az acr import` in 94 s (index digest preserved).
  A client-side copy from the Codespace was capped at 600 s; GitHub-hosted runners
  copied the same image in 90 s under WC-127.
- Resolver against the live broker and cleanup jobs: `publish` and `verify` both
  selected the runner ACR in under 1 s.
- Temporary job in the runner environment using the ACR image and pull identity:
  "Successfully pulled image ... in 13.53s. Image size: 726663168"; execution
  succeeded; the temporary job was deleted.

## Rollout

1. Merge. The Demo runner stack already matches this template.
2. Re-run Environment Deployment for Demo; broker and cleanup pull from the runner ACR.
3. UAT runner stack picks this up on its next reviewed stack apply.
4. A follow-up runner image rebuild can widen the lifecycle image guard so the runner
   job execution image also moves to the runner ACR.

Cost: about USD 5 per month per active runner stack ACR (Basic).
