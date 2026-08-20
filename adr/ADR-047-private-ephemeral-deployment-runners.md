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
6. A repository-scoped GitHub App issues short-lived runner registration tokens. Its private key is stored in purge-protected Azure Key Vault, rotated at most every 90 days, and never exposed to the runner, GitHub variables, workflow outputs, logs, or artifacts. App permissions exclude repository contents write, workflow write, environment approval, PR approval, and package mutation.
7. Each ACA execution registers one ephemeral runner, accepts one environment-labelled job, deregisters, and terminates. Cancellation, timeout, and orphan recovery are bounded and evidence-bearing. Idle runner compute is zero.
8. Runner managed identity, bootstrap OIDC identity, and environment deployment OIDC identity are separate authorities. The runner identity cannot deploy resources; the deployment identity cannot read GitHub App material; the bootstrap identity cannot bypass environment authorization.

The normative bootstrap sequence, network/RBAC matrix, DNS ownership, negative tests, cost controls, and activation gate are defined in `architecture/reference/pipeline/azure-deployment-topology.md`.

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

**Cost:** approximately one Private Link endpoint-hour charge per provisioned environment plus low-volume data and one shared private DNS zone. VNet/subnet/private IP allocation adds no direct charge. No load balancer, public IP, or TLS certificate is required. Runner compute is charged only during ACA Job executions.

## Implementation Hold

No Bicep/ARM template, runner image, GitHub App, Key Vault secret, private endpoint, ACA Job, workflow runner-label change, or public-network disablement may be created under this ADR while its status is Proposed. Independent Enterprise Architecture and Security acceptance must change the status to Accepted first.