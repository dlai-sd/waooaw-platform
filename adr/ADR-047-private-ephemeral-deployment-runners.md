# ADR-047: Private Ephemeral Deployment Runners

**Status:** Proposed - implementation prohibited until independent EA and Security acceptance
**Date:** 2026-08-20
**Roles Applied:** Enterprise Architect, Security Architect, Platform Architect
**Constitutional Basis:** C-023 Evidence First; C-059 Implementation Traceability; C-065 SDLC Separation; C-066 Authorization Tiers; C-067 Blue-Green and Cost Ceiling; ADR-013; ADR-014; FA-052; WC-076

## Context

GOAL-006 deployment uses GitHub Actions OIDC and an Azure Storage backend with default-deny public networking. A GitHub-hosted runner temporarily allowed the public IP reported by `api.ipify.org`. The exact configuration Blob succeeded after propagation, but Terraform's backend client received `403 AuthorizationFailure` moments later. A discovered public egress address is not a stable trust boundary across tools or requests.

Terraform cannot create the network path required to read its own protected backend. The private runner control plane therefore needs a separate, deterministic bootstrap lifecycle that retains no always-on runner compute and does not introduce GitHub variables, client secrets, public ingress, or a second infrastructure orchestrator state file.

## Decision

WAOOAW will execute environment deployment jobs on ephemeral self-hosted GitHub runners implemented as Azure Container Apps manual Jobs inside environment-isolated runner subnets.

1. A GitHub-hosted management-plane bootstrap job uses the constrained Azure OIDC identity to reconcile a versioned Azure Deployment Stack. The stack owns runner networking, NSG, ACA environment/job, managed identity, bootstrap Key Vault access, Storage private endpoint, private DNS link, diagnostics, and budget controls.
2. Azure Deployment Stacks are the bootstrap ownership and reconciliation record. Bootstrap does not use the protected Terraform backend or retain local Terraform state.
3. Demo, UAT, and Production share one versioned blueprint but have distinct runner groups, labels, subnets, managed identities, private endpoints, state boundaries, and activation evidence. UAT is not provisioned before Founder Demo acceptance. Production remains zero-capacity and plan-only until separately authorized.
4. Storage state and deployment configuration resolve through private endpoints. Public Storage access is disabled only after the Demo private path passes exact backend and rollback qualification. No public-IP allowlist fallback is permitted after activation.
5. One centrally managed `privatelink.blob.core.windows.net` zone may link to isolated runner VNets. DNS does not grant access; NSGs and Azure RBAC enforce environment separation.
6. An organization-installed GitHub App issues short-lived runner registration tokens. Its RSA private key is imported as a non-exportable, purge-protected Azure Key Vault key with a maximum 90-day expiry and 14-day alert. The bootstrap OIDC identity can invoke RS256 signing on that exact key version but cannot export it; private key bytes never enter workflow or runner memory. The live App must exactly match `architecture/reference/pipeline/github-runner-app-manifest.json`. The resulting registration token alone is written to a 15-minute environment-specific Key Vault secret readable only by the runner identity.
7. The workflow separates GitHub-hosted `bootstrap-runner` and `cleanup-runner` jobs from the self-hosted `deploy-private` job. `cleanup-runner` uses `if: always()` for ordinary completion/failure/cancellation. ACA enforces a 60-minute execution limit. A separate two-minute ACA `runner-reconciler` Job runs every five minutes to cover hard workflow termination; its distinct identity can sign a GitHub App JWT, administer runner registrations, delete expired token secrets and stop ACA executions, but cannot read state/configuration or deploy environments. Cleanup verifies deregistration and zero runner execution within five minutes, retries for at most 15 minutes, then keeps the label inactive and alerts INST-009/007. No next deployment runs while an orphan remains. Runner compute is zero between executions; reconciler execution cost is included in the gate forecast.
8. Runner managed identity, bootstrap OIDC identity, and environment deployment OIDC identity are separate authorities. The runner identity cannot deploy resources; the deployment identity cannot read GitHub App material; the bootstrap identity cannot bypass environment authorization.

The normative bootstrap sequence, network/RBAC matrix, DNS ownership, negative tests, cost controls, and activation gate are defined in `architecture/reference/pipeline/azure-deployment-topology.md`.

### Infrastructure Identity Boundary

ADR-047 governs infrastructure-provisioning identities only; these are not SPIFFE workloads, ADR-046 service identities, or constitutional authorization. GitHub issues the bootstrap OIDC assertion for the exact repository, workflow reference and environment subject. Azure Entra exchanges it only for the bootstrap app registration's audience and environment-scoped management roles. The runner and reconciler use distinct Azure managed identities. The deployment job separately exchanges GitHub OIDC for the environment deployment identity. No identity accepts another identity's audience or assumes another identity's role.

Revocation disables the affected Entra federated credential or managed identity assignment, revokes the GitHub App key version, removes outstanding runner registrations, stops active ACA executions and leaves the environment label inactive. Suspected compromise triggers this sequence before key rotation or recovery. Authentication proves only identity; Deployment Stack reconciliation, policy gates and independent activation evidence remain required proof of readiness.

### Credential Lifecycle

The bootstrap uses the Azure Key Vault Cryptography client or REST `sign` operation with algorithm `RS256`, a 10-second request timeout, at most three bounded transient retries and no plaintext/export fallback. It constructs a GitHub App JWT with an expiry no more than ten minutes, exchanges it at `POST /app/installations/{installation_id}/access_tokens`, then calls `POST /orgs/dlai-sd/actions/runners/registration-token` with the installation token. GitHub, not Azure OIDC, validates the App JWT and issues the runner registration token.

Token issuance occurs only after stack, DNS and permission reconciliation and immediately before ACA execution start. The token secret expires after 15 minutes even though GitHub's upstream token validity may be longer; ACA must consume it and register within ten minutes. Failure or delay at minutes 12, 14 or 16 stops the execution, deletes the secret through the cleanup identity, leaves the label inactive and restarts from a newly issued token only after the pre-start gates pass again. Tokens are never renewed inside a running execution.

### Lifecycle, Drift, And Cost Governance

INST-009 owns Deployment Stack names, template/parameter digests, `what-if` reconciliation and retained run artifacts. Expected absent resources may be reconciled from the approved immutable template. Unexpected ownership, permissions, NSG, endpoint, DNS link/record or destructive drift is alert-only and requires INST-007/009 approval before reconciliation; it never auto-accepts live state. INST-015 independently attests ten consecutive runs whose post-reconciliation `what-if` contains no resource changes.

The reconciler stops only an ACA execution older than 60 minutes or one whose recorded GitHub workflow run is terminal/absent while the runner remains registered. It may delete the corresponding GitHub runner registration and expired token secret. It cannot stop a healthy execution below the limit. Any orphan persisting beyond five minutes resets the complete qualification count, leaves the label inactive and requires cleanup before a new qualification attempt.

ACA concurrency is one per environment, each execution has a 60-minute limit, and the reconciler has a two-minute/five-minute schedule bound. INST-009 owns Azure budget alerts and the per-run/monthly forecast; alerts fire at 50%, 80% and 100% of FA-052's monthly ceiling to INST-009 and the Founder. Azure budgets are detective, not a guaranteed billing cutoff. Preventive controls are the concurrency/runtime bounds and the pre-start forecast gate; crossing the forecast ceiling blocks new executions and requires Founder disposition.

## Activation Gates

Demo workflow activation requires all of the following:

- Deployment Stack reconciliation is healthy and idempotent.
- The runner resolves Storage to the approved private endpoint and cannot reach the public endpoint.
- Exact configuration Blob access and Terraform backend list/read/write/lock operations pass with OIDC/Azure AD authentication.
- Cross-environment Storage and Key Vault access is denied by RBAC.
- Runner registration is ephemeral; completion leaves no online runner and zero ACA job executions.
- Public-IP mutation steps remain present until private qualification, then are removed in the same reviewed activation change that switches the runner label.
- Forecast cost remains inside FA-052.
- INST-007 reviews security evidence and INST-015 independently verifies behavior.

INST-009 owns the interface gate. INST-003 acceptance precedes INST-007 security acceptance; INST-009 then collects immutable stack, permission, NSG/RBAC/DNS and cost manifests; INST-015 independently executes route, denial, cancellation/orphan and zero-idle tests. The environment label remains inactive until all evidence passes. Demo qualification requires ten successful executions and five forced cancellations without an orphan beyond five minutes.

INST-007 acceptance covers OIDC subjects/audiences, App key lifecycle and permissions, reconciler/runner/bootstrap RBAC, NSGs and cross-environment denial. INST-009 validates implementability, manifest equality, Deployment Stack lifecycle, sequencing and cost. INST-015 executes rather than merely audits the qualification matrix; any failed assertion blocks activation. Every new App permission requires an ADR amendment and fresh INST-007 acceptance.

Negative proofs are stage-specific: Demo must have no grants or routes to reserved UAT/Production scopes; UAT activation must prove reciprocal Demo/UAT Storage and Key Vault denial plus Production denial; Production must prove reciprocal denial against both lower environments. Evidence consists of RBAC exports, denied data-plane requests, diagnostic logs, no-peering inventory, NSG rules, private DNS results and Network Watcher connection tests. DNS resolution alone is insufficient.

The centrally managed private DNS Deployment Stack uses a reviewed parameter manifest of exact Storage resource IDs, endpoint private IPs and VNet links. A wrong resource ID/IP, unexpected link/record or public answer is security drift: bootstrap stops before token creation or ACA start, records the live inventory, alerts INST-007/009 and requires approved repair. A transient Azure API timeout or NXDOMAIN during expected propagation retries at most three times with bounded backoff, then fails the deployment and alerts INST-009; it does not create an orphan because execution has not started. Runner VNets are never peered. NSGs deny other environment address ranges; Storage and Key Vault public access are disabled after qualification. Required GitHub/GHCR Internet HTTPS egress is acknowledged explicitly rather than represented as unsupported NSG FQDN filtering.

ADR-046 continues to govern workload-to-service authentication. Runner trust uses GitHub ephemeral registration, Azure managed identity and environment-scoped OIDC; it creates no runner CA or substitute for ADR-046 mTLS on governed service calls.

Qualification is per Demo runner blueprint version and must complete within seven consecutive days: ten consecutive successful no-drift executions and five forced-cancellation executions, including cancellation before assignment, during Terraform init, during plan, and one hard workflow termination. Any orphan beyond five minutes resets qualification. Evidence is retained in the named GOAL-006 run artifact and checked on every bootstrap; live permission, RBAC, DNS and stack manifests are preventive gates, while diagnostic/denial/cancellation records are detective evidence.

UAT repeats the gates only after Founder Demo acceptance. Production may be planned but not activated under WC-076.

## Alternatives Considered

| Option | Disposition |
|---|---|
| GitHub-hosted runner with discovered temporary public IP | Rejected: observed client/request egress is not a reliable Storage trust boundary. |
| Permanent VM self-hosted runner with static public IP | Rejected: public Storage path, persistent attack surface, patching burden, and non-zero idle compute. |
| NAT Gateway with reserved public IP | Rejected for state access: stable but still public and adds always-on cost; retain only if a future approved external dependency requires fixed egress. |
| Azure VM Scale Set runner | Deferred: valid private option but heavier image, scaling, patching, and lifecycle operations than one-shot ACA jobs. |
| Shared runner/subnet across environments | Rejected: cross-environment blast radius and Production boundary violation. |
| Separate private DNS zone per environment | Rejected as unnecessary duplication; shared zone plus isolated endpoint/RBAC controls is sufficient and cheaper. |

## Consequences

**Benefits:** private state path, stable Azure networking, zero idle runner compute, no temporary Storage firewall mutation, environment isolation, deterministic bootstrap ownership, OIDC deployment authority, and evidence-bearing teardown.

**Trade-offs:** a new GitHub App lifecycle, bootstrap Deployment Stack, runner image maintenance, private endpoint/DNS charges, and orphan-recovery monitoring.

**Cost:** approximately one Private Link endpoint-hour charge per provisioned environment plus low-volume data and one shared private DNS zone. VNet/subnet/private IP allocation adds no direct charge. No load balancer, public IP, or TLS certificate is required. Runner compute is charged only during ACA Job executions. The combined plan blocks above FA-052's INR 15,000 one-time or INR 10,000 monthly ceiling.

## Implementation Hold

No Bicep/ARM template, runner image, GitHub App, Key Vault secret, private endpoint, ACA Job, workflow runner-label change, or public-network disablement may be created under this ADR while its status is Proposed. Independent Enterprise Architecture and Security acceptance must change the status to Accepted first.