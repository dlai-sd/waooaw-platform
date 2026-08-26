# GOAL-006 Environment Deployment Local Azure Evidence

| Field | Value |
|---|---|
| `record_id` | `ER-GOAL-006-ENV-DEPLOY-01` |
| `record_type` | Local Azure CLI read-only evidence |
| Observation time | 2026-08-26T12:37:27Z through 2026-08-26T12:42Z |
| Observation point | Implementation commit `0ac5b8ea7ae0d95de526677cc5972d17019b759a`; PR #367 |
| Azure identity | User `yogesh.khandge@dlaisd.com` |
| Azure boundary | Tenant `0471534c-1bbe-40ab-ae65-3f721b62582c`; subscription `2ed11839-6a0f-4eaa-bd94-44ca96ff5d84` (`Enabled`) |
| Mutation and spend | None; read-only CLI and HTTP requests only |
| Overall result | PASS for current Demo topology and controls; post-merge execution still required for the changed workflow |

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