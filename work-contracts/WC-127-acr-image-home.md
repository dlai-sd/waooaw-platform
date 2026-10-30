# Work Contract 127 - ACR Image Mirror And Image Home Choice

## Record Control

- Office: Platform IT Expert (INST-010).
- Assigned by: Founder, 2026-10-30, current conversation.
- Authority: Founder accepted the ACR cost (about USD 5 per month per environment
  registry), chose ACR over Nexus, chose CI-time mirroring (Option B), and
  authorized implementation, end-to-end testing and a new PR.
- Baseline: origin/main at dcca59a2.
- Status: LOCALLY QUALIFIED AND LIVE-PROBED - exact-head PR preparation and Founder review/merge pending.

## Authority And Scope

Two Demo deployments failed because Container Apps pulled release images
cross-provider from GHCR into Central India (4-8 minute pulls, revision and
job timeouts). Add an environment-local Azure Container Registry, mirror each
release and runner image into it immediately after CI publishes it, and let
the deployment dispatcher choose where images come from.

No broker or bootstrap-manifest change, no live environment apply, no deployment,
DNS change or merge is authorized by this contract. Scratch Azure resources used
for the end-to-end probe were created and deleted within the session.

## Inputs

- Founder decisions in the current conversation (cost, ACR over Nexus, Option B).
- RCA of Environment Deployment runs 40915810114 and 40986521332.
- CLI feasibility probe: GHCR to ACR copy by digest from a GitHub-hosted runner
  with OIDC took 12-16 seconds per image and preserved the digest; a Container
  Apps job pulled from ACR with a user-assigned pull identity.

## Requirements And Definition Of Done

| ID | Requirement | Executable evidence |
|---|---|---|
| WC127-R001 | `deploy.yaml` exposes `image_home` (`github`, `azure`, `both`; default `github`) beside the existing inputs and passes it to Environment Deployment. | Dispatch-input and workflow wiring tests. |
| WC127-R002 | Each foundation creates a Basic, admin-disabled ACR, an AcrPull identity for workloads, and an AcrPush identity federated to `main` for CI, with outputs. | Terraform validate for all roots and static foundation tests. |
| WC127-R003 | CI copies every published release and runner image to the environment ACRs by digest (index and all child manifests) right after the digest is recorded, in parallel with the remaining jobs, idempotently and without failing publication. | Mirror unit tests and live probe run 41000373132. |
| WC127-R004 | At deploy time, `azure` requires a ready registry and complete mirrors (copying missing ones), `both` falls back to GHCR with a recorded reason, and `github` changes nothing. | Select-mode tests and live probe assertions. |
| WC127-R005 | With an Azure home, every workload app, the billing migration, verification and the database provisioner job pull from ACR through the pull identity; GHCR behaviour is unchanged. | Terraform static tests, provisioner-script execution test and live Container Apps pull probe. |
| WC127-R006 | Validate locally and live, perform author review, and submit an exact-head PR using the repository template and mandatory preparation gate. | Commands and results recorded below and in the PR. |

## Stops And Rollback

Stop for missing Founder decisions, unavailable validation, secret requirements or
two reproducible infrastructure failures. Rollback: dispatch with `image_home=github`
(default); reverting this PR removes the mirror steps. The ACR and identities are
additive foundation resources.

## Validation And Delivery Evidence

- Pipeline tests in `waooaw-platform-test-runner-python:local` with `PYTHONPATH=/workspace`
  (`tests/pipeline/test_goal006_*.py`, `test_wc124_*.py`, WC-085, WC-090): PASS, 1042 tests.
- Ruff check and format on `scripts/` and new tests: PASS.
- actionlint 1.7.7 on `ci.yaml`, `deploy.yaml`, `environment-deployment.yaml`: PASS.
- `terraform fmt` and `terraform validate` (1.9.8, azurerm 4.14.0) for demo, uat and prod
  foundation and workload roots: PASS.
- Live probe (temporary branch and workflow, deleted after use), run 41000373132:
  the exact CI `publish` command copied 8 images in parallel to a scratch ACR in
  18-90 seconds each (runner 89.8 s, web 27.0 s); a second run reported every image
  already present (0.0 s). `select azure` returned 8 ACR references with no copies;
  `select both` with no registry fell back to GitHub with a reason; `select azure`
  with no registry failed.
- Live Container Apps probe: a job using the ACR runner image and pull identity
  succeeded in 47 seconds; a web app revision from ACR became Healthy/Running.

## Rollout

1. Merge; deploy Demo once with `image_home=github` or `both` to create the ACR and identities.
2. Record `image_publish_client_id` in `infrastructure/image-registry/acr-mirrors.json`;
   until then CI skips mirroring with a notice and deploy-time `select` copies missing images.
3. Deploy with `both`, then `azure`.
4. UAT needs control-plane rights on its resource group before `azure` can be used there.

Broker (dormant) changes are deferred to avoid bootstrap-manifest churn.
