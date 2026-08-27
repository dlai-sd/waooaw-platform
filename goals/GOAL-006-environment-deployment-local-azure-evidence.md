# GOAL-006 Environment Deployment Local Azure Evidence

| Field | Value |
|---|---|
| `record_id` | `ER-GOAL-006-ENV-DEPLOY-01` |
| `record_type` | Local Azure CLI and pre-PR deployment qualification evidence |
| Observation time | 2026-08-26T12:37:27Z through 2026-08-27T15:25:32Z |
| Observation point | Qualification run `33085991935`; source `218792566470292c56300bf953822405c0a731db` |
| Azure identity | User `yogesh.khandge@dlaisd.com` |
| Azure boundary | Tenant `0471534c-1bbe-40ab-ae65-3f721b62582c`; subscription `2ed11839-6a0f-4eaa-bd94-44ca96ff5d84` (`Enabled`) |
| Mutation and spend | Bounded Demo deployment mutation under FA-052; private runner cleanup passed |
| Overall result | PASS - verified Demo deployment URL, exact-six inventory, functional probes and `49.36.49.189/32` ingress |

## Commands Executed

The local proof used only read operations:

```bash
python scripts/goal006_environment_config.py --environment demo
python scripts/goal006_environment_config.py --environment uat --allow-inactive
python scripts/goal006_environment_config.py --environment prod --allow-inactive
az account show
az group show --name waooaw-demo-rg
az containerapp env show --name cae-waooaw-demo --resource-group waooaw-demo-rg
az containerapp list --resource-group waooaw-demo-rg
az containerapp show --name ca-demo-web --resource-group waooaw-demo-rg
az containerapp job show --name job-demo-deployment-verification --resource-group waooaw-demo-rg
az containerapp job execution list --name job-demo-deployment-verification --resource-group waooaw-demo-rg
az identity show --name <deployment-or-verification-identity> --resource-group waooaw-demo-rg
az role assignment list --assignee-object-id <principal-id> --all --include-inherited
az storage account show --name waooawp3tfstate2ed118 --resource-group waooaw-platform-rg
az storage blob exists --account-name waooawp3tfstate2ed118 --container-name deployment-config \
  --name demo/foundation-cache.json --auth-mode login
az containerapp job show --name <runner-job> --resource-group waooaw-demo-runner-rg
az containerapp job execution list --name <runner-job> --resource-group waooaw-demo-runner-rg
curl https://api.ipify.org
curl https://ca-demo-web.wonderfulmoss-740b2b2d.centralindia.azurecontainerapps.io/
gh api repos/dlai-sd/waooaw-platform/environments/<environment>
```

Dynamic IDs were resolved with Azure CLI before role queries. No credential values, access tokens,
Key Vault secret values, state content, or deployment configuration content were read or recorded.

## Environment Resolution

| Environment | Repository activation | Identity state | Result |
|---|---|---|---|
| Demo | `ACTIVE` | Control-plane and cleanup client IDs configured | Eligible |
| UAT | `INACTIVE` | Client IDs empty | Fails closed before deployment |
| Prod | `INACTIVE` | Client IDs empty | Fails closed before deployment |

All three resolve to the protected state account `waooawp3tfstate2ed118`. The inactive UAT and Prod
records prove parameter readiness without activating either environment.

## Demo Foundation

| Resource | Observation | Result |
|---|---|---|
| Resource group `waooaw-demo-rg` | Central India; `Succeeded`; tags identify `demo`, Terraform and GOAL-006 | PASS |
| Container Apps environment `cae-waooaw-demo` | Central India; `Succeeded`; default domain present | PASS |
| Deployment identity | `id-waooaw-demo-deployment` exists in the authorized tenant | PASS |
| Verification identity | `id-waooaw-demo-verification` exists in the authorized tenant and is distinct | PASS |
| Verification job | Manual trigger; `Succeeded`; timeout 300 seconds; retry limit 1 | PASS |

The deployment identity has Contributor and Role Based Access Control Administrator only at the
Demo resource-group scope, Key Vault Secrets Officer at `kv-waooaw-demo`, and Storage Blob Data
Contributor at the exact state account. The independent verification identity has Reader at the
Demo resource group and Container Apps Jobs Operator only at the verification job.

## Live Workload Inventory

Every observed app reported `provisioningState=Succeeded` and
`latestRevision == latestReadyRevision`.

| App | Ingress | Ready revision | Image |
|---|---|---|---|
| `ca-demo-ai-runtime` | Internal | `0000005` | `ghcr.io/dlai-sd/ai-runtime@sha256:9f8fb2c095df298926a809eca830a3efb23f17e46d1d8bda112be4c08520ce43` |
| `ca-demo-billing-engine` | Internal | `0000005` | `ghcr.io/dlai-sd/billing-engine@sha256:b8c25fcfd7aa11ec10d019eefe4d31eceb71d7b89da01ef04cb3793c07943c70` |
| `ca-demo-business-platform` | External | `0000005` | `ghcr.io/dlai-sd/business-platform@sha256:dfc929155ae006ee72e655bf1ebbe7c170bca40254b9e5afbb3828b9151b92f2` |
| `ca-demo-constitutional-engine` | Internal | `0000005` | `ghcr.io/dlai-sd/constitutional-engine@sha256:5b4b385f4021345066955a99d29e802e7f0818fe8b0cd3f9a3d1802cddbc635c` |
| `ca-demo-professional-runtime` | External | `0000005` | `ghcr.io/dlai-sd/professional-runtime@sha256:816ffedfb39c9651479c06c8b05a2b1c178f8541fe85aabab8e79b3ab9c5ae56` |
| `ca-demo-web` | External | `0000005` | `ghcr.io/dlai-sd/web@sha256:7a399233f5508533d4d9599ae104ea60df0825adccb455edfd1a0dfa62a8ff94` |
| `ca-demo-identity-edge` | External | `0000001` | Immutable nginx digest |
| `ca-demo-keycloak` | Internal | `0000003` | Immutable Keycloak digest |

## Browser CIDR Evidence

The live web ingress has one allow rule:

```text
name=founder-review action=Allow ipAddressRange=49.36.51.221/32
```

The local workspace public IPv4 was `4.240.18.226`. An HTTPS request from this workspace to the live
web FQDN returned HTTP `403`. This is the expected negative control because the caller is outside
the configured Founder `/32`; it proves the live ingress restriction is enforced. It does not prove
that `49.36.51.221` is the Founder's current browser IPv4.

## Private Runner And Verification History

The runner resource group and all three manually triggered jobs exist and report `Succeeded`:

- `goal006-demo-runner-broker`
- `goal006-demo-runner-job`
- `goal006-demo-runner-cleanup`

The latest three observed executions of each job succeeded. The latest five independent deployment
verification executions also succeeded, including the most recent execution ending at
`2026-08-26T09:49:20Z`.

The Azure runner resource-group tag still says `runner-activation=INACTIVE`, while the authoritative
repository parameter resolves Demo as `ACTIVE`. Runtime eligibility is controlled by the repository
parameter and the runner jobs are demonstrably operational, but the stale Azure tag is retained here
as a configuration-drift observation. This PR does not mutate that tag.

## Protected State Evidence

The state account reports:

| Control | Observed value | Result |
|---|---|---|
| Provisioning | `Succeeded`, Central India | PASS |
| HTTPS only | `true` | PASS |
| Minimum TLS | `TLS1_2` | PASS |
| Shared key access | `false` | PASS |
| Blob public access | `false` | PASS |
| Firewall | `defaultAction=Deny`; Azure-services bypass | PASS |

The hosted workspace cannot perform a data-plane `blob exists` operation against
`deployment-config/demo/foundation-cache.json`; Azure returned the expected network-rule denial and
the command exited 1. Therefore this local session cannot claim whether the cache blob exists. The
changed workflow performs that check on the private runner inside the allowed network boundary.

## GitHub Environment Administration

Read-only API evidence confirms required-reviewer and custom branch-policy rules remain on `demo`,
`demo-verification`, `uat`, and `uat-verification`. `prod` and `prod-verification` return HTTP 404 and
were not created. The attempted reviewer removal returned HTTP 403
`Resource not accessible by integration` for all four existing environments; a subsequent read
proved there was no partial mutation.

## Evidence Boundary

This record proves the current live Demo baseline and the local negative controls available before
merge. It does not claim that PR #367's changed workflow has executed in Azure: the workflow rejects
a release SHA that is not current `main`. After Founder review and merge, one trusted Demo apply is
still required to prove the submitted browser IPv4 persistence, automatic lease, foundation-cache
miss/hit behavior, conditional seeding, parallel probes, and reused release evidence end to end.

## Post-Merge Attempt 1 - Preflight Failure

| Field | Value |
|---|---|
| Workflow run | `32971678939` |
| Trusted release | CI run `32970620994`; source `a0fd4e9e3f068ac9f6f0c7efd3304b921db2abe3` |
| Requested access | `4.240.18.226/32` |
| Result | FAIL before configuration, Terraform or workload mutation |
| Cleanup | PASS; cleanup execution `goal006-demo-runner-cleanup-8naos0r` succeeded |

The exact-six release artifact was downloaded locally and
`goal006_registry_manifest.py` returned `{"passed": true, "violations": []}`. Authorization,
environment resolution, broker execution and ephemeral runner registration passed. The correlated
runner `goal006-demo-32971678939-1` came online with the exact run labels and accepted the private
job.

The private job failed in the RBAC/provider preflight. No configuration, lease, foundation,
credential or workload step ran. Live web ingress remained `49.36.51.221/32`, and independent
verification was correctly skipped.

A human control-plane query proved client `60c07330-4cc1-4e12-95a2-adc0966f1941` already has all
five required assignments at the exact state-account and Demo resource-group scopes. No RBAC grant
was missing and no permission was added.

### Forensic Correction - 2026-08-27

The original diagnosis attributed the failure to
`az role assignment list --all --include-inherited`, but the run log did not prove that command
executed. GitHub printed the complete shell block before execution, the step then exited without an
Azure CLI error, and no role-assignment artifact was created. A later audit reproduced the earlier
failure at `test -n "$TFSTATE_STORAGE_ACCOUNT"`: PR #367 had removed that job-level variable while
retaining its uses throughout the deployment job. The private runner definition does not inject the
variable.

PR #368's exact-scope RBAC queries reduced enumeration scope, but its regression test checked YAML
text rather than executing the preflight environment contract. It therefore did not repair or detect
the missing variable. Claims that the first run was proven to fail at the broad RBAC query, or that
the scoped-query change was runtime-qualified, are withdrawn by this correction.

## Pre-PR Qualification - Key Vault DNS Failure

| Field | Value |
|---|---|
| Workflow run | `33072729696` |
| Qualification source | `d3f07e6958154877d19eb95ea0a845955e004b42` |
| Trusted release | CI run `33068493419`; source `4ae12b0fbde1507eb4dc52fa62d6bb43e06f98e5` |
| Requested access | `49.36.49.189/32` |
| Result | FAIL at credential inventory after foundation plan/apply |
| Cleanup | PASS; temporary branch policies and cleanup OIDC credential removed |

The repaired storage-account contract, exact-scope RBAC preflight, configuration download,
foundation plan, foundation policy, foundation apply and deployment-identity OIDC login all passed.
The foundation plan reported no drift. Credential inventory then failed because the private runner
could not resolve `kv-waooaw-demo.vault.azure.net`.

Azure CLI showed that `privatelink.vaultcore.azure.net` was linked only to `vnet-waooaw-demo`; the
private runner executes in `goal006-demo-runner-vnet`.

## Pre-PR Qualification - Overlapping Private DNS Zone Rejected

| Field | Value |
|---|---|
| Workflow run | `33075103178` |
| Qualification source | `e59175fe2271d041e74724407f8631349ac2420b` |
| Trusted release | CI run `33068493419`; source `4ae12b0fbde1507eb4dc52fa62d6bb43e06f98e5` |
| Requested access | `49.36.49.189/32` |
| Result | FAIL during foundation apply before credential inventory |
| Cleanup | PASS; temporary branch policies and cleanup OIDC credential removed |

The qualification executed the repair branch's Terraform and scripts while retaining the trusted
current-main exact-six release. Foundation planning correctly proposed a runner VNet link, but Azure
rejected its creation because `goal006-demo-runner-vnet` was already linked to another private DNS
zone named `privatelink.vaultcore.azure.net` in `waooaw-demo-runner-rg`.

Azure CLI then proved that the runner-owned zone and VNet link were healthy, but the zone contained
only the runner vault record. The Demo workload Key Vault private endpoint was healthy at
`10.60.2.4`; its record existed only in the workload-owned zone, which the isolated runner VNet
cannot use.

The corrected design manages an environment-scoped A record for the workload vault in the existing
runner-owned zone instead of attempting a second overlapping zone link. The record ID is part of
guarded foundation-cache evidence, so a missing record forces foundation reconciliation for Demo,
UAT and Prod.

## Pre-PR Qualification - Cross-VNet Address Unroutable

| Field | Value |
|---|---|
| Workflow run | `33083587636` |
| Qualification source | `4484f673973a377be266050879a9b0b626727fec` |
| Trusted release | CI run `33068493419`; source `4ae12b0fbde1507eb4dc52fa62d6bb43e06f98e5` |
| Requested access | `49.36.49.189/32` |
| Result | FAIL during credential inventory before workload plan/apply |
| Cleanup | PASS; temporary branch policies and cleanup OIDC credential removed |

Foundation plan and apply succeeded and created `kv-waooaw-demo -> 10.60.2.4` in the runner-owned
private DNS zone. The first Key Vault inventory call then timed out after 300 seconds. Azure CLI
proved that neither `goal006-demo-runner-vnet` nor `vnet-waooaw-demo` had any VNet peering, and the
runner resource group had no private endpoint targeting `kv-waooaw-demo`. The A record therefore
resolved correctly but directed the runner to an unroutable private endpoint in the workload VNet.

The corrected topology creates an environment-scoped private endpoint for the workload vault in the
runner VNet's existing `private-endpoints` subnet and points the runner-zone A record to that local
endpoint. Both endpoint and record IDs participate in guarded foundation-cache evidence for Demo,
UAT and Prod.

## Pre-PR Qualification - Verified Demo Deployment

| Field | Value |
|---|---|
| Workflow run | `33085991935` - PASS |
| Qualification source | `218792566470292c56300bf953822405c0a731db` |
| Trusted release | CI run `33068493419`; source `4ae12b0fbde1507eb4dc52fa62d6bb43e06f98e5` |
| Verified Demo URL | `https://ca-demo-web.wonderfulmoss-740b2b2d.centralindia.azurecontainerapps.io` |
| Access boundary | `49.36.49.189/32` |
| Web revision | `ca-demo-web--0000006`; latest and latest-ready; provisioning `Succeeded` |
| Runner vault route | Private endpoint `pe-waooaw-demo-vault-runner` approved at `10.70.0.39`; runner-zone record `kv-waooaw-demo -> 10.70.0.39` |
| Functional verification | `job-demo-deployment-verification-nh5hps6` - `Succeeded` |
| Cleanup | PASS; temporary branch policies and cleanup OIDC credential removed; only `main` remains trusted |

The private apply passed foundation reconciliation, credential inventory, digest-pinned credential
seeding, workload plan and workload apply. Independent verification passed trusted release checks,
live exact-six image inventory, active healthy revision checks, internal functional probes and the
returned URL/ingress binding. URL publication then completed successfully.

Retained run artifacts are `goal006-private-runner-prestart-33085991935-1`,
`goal006-demo-apply-33068493419`, `goal006-private-runner-cleanup-33085991935-1` and
`goal006-demo-independent-verification-33068493419`.