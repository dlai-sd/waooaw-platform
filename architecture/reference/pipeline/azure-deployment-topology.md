# GOAL-006 Azure Deployment Topology

## Purpose

This contract turns the accepted GOAL-006 constitutional, security, data, and platform decisions into one deployable Azure topology. Infrastructure and workflows MUST implement this contract before another full Demo apply.

## Skill 17 Cloud Delivery Entry Point

This document is the canonical implementation design for Platform IT Expert Skill 17 cloud-delivery
work. Skill 17 supplies the professional capability; it does not permit a new topology or create
cloud authority. The current authority and stop conditions come from `constitution/PROJECT_STATE.md`
and the assigned Work Contract. ADR-047 controls the private runner decision. If any of those inputs
is missing, inconsistent, or unapproved, execution stops rather than selecting another cloud path.

| Concern | WAOOAW direction |
|---|---|
| Strategy | Azure-first with application-layer portability and a named escape hatch for each Azure-specific dependency. |
| Design | GitHub Actions OIDC, immutable GHCR digests, isolated Azure Container Apps environments, managed identities, Key Vault, private networking, PostgreSQL, and OpenTelemetry/Azure Monitor. |
| Delivery | Build the exact-six tuple once, promote the same digests through Demo, UAT, and Production, and fail closed on authorization, cost, security, recovery, or evidence failure. |
| Runner path | A GitHub-hosted management job reconciles the Azure Deployment Stack; an ephemeral environment runner performs private deployment; independent cleanup removes its registration, token, and execution. |
| Sequence | Qualify Demo first, obtain Founder Demo acceptance before UAT, and keep Production dark and plan-only until separately authorized. |
| Operating posture | Prefer local deterministic validation for fast iteration, but use the protected workflow to prove OIDC identity, private DNS/data paths, environment approval, cleanup, and immutable evidence. |

### Current Delivery State - 2026-08-22

`constitution/PROJECT_STATE.md` remains authoritative for live authorization. This dated snapshot
exists only to prevent implementation sessions from confusing deployed resource scaffolding with an
operational private runner.

| Area | Verified state | Required next result |
|---|---|---|
| Demo runner stack | Azure Deployment Stack succeeded with the VNet, ACA environment/jobs, managed identities, Key Vault, Storage/Key Vault private endpoints, private DNS zones, diagnostics, and deny-delete ownership. | Reconcile all live resources to the reviewed stack and retain a no-destructive-change preview. |
| Runner lifecycle | The manual runner job has never executed. No JIT configuration or short-lived runner-token wiring is present. | Implement GitHub App signing/token exchange, bounded Key Vault handoff, ACA start, registration, and teardown. |
| Cleanup | The reconciler is configured ACTIVE but its placeholder command exits nonzero every five minutes. | Return it to fail-closed inactive operation until correlation-checked cleanup is implemented and tested. |
| Private path | Storage has an approved private endpoint and private A record. Key Vault has an approved endpoint but no private-zone A record. No runner-side DNS or Terraform backend operation has executed. | Prove private DNS plus exact Blob and Terraform list/read/write/lock operations from the ephemeral runner. |
| Deployment workflow | Demo deployment still uses `ubuntu-latest` and temporary Storage public-IP firewall mutation. | Switch the runner label and remove public-IP mutation together only after the complete activation matrix passes. |
| Higher environments | UAT and Production prerequisite resource groups exist, but their runner stacks do not. | Keep UAT blocked until Founder Demo acceptance and Production plan-only until separate authorization. |
| Execution contract | PROJECT_STATE references WC-076, but its Work Contract file is absent from the current repository checkout. | Restore the approved contract before further Skill 17 execution; do not reconstruct its authority from architecture documents. |

The detailed topology, controls, interface gates, and implementation order below are normative. This
section is a routing summary and must not be copied into a separate implementation plan.

## Constitutional Delivery Invariants

1. Build the exact-six application images once. Demo, UAT, Production, and rollback use the same immutable OCI digests.
2. The promoted release tuple is `manifest + six image digests + reviewed configuration digest + data schema compatibility + evidence`.
3. Images contain no environment configuration or secret values. Runtime configuration comes from reviewed environment configuration, managed identity, and Key Vault references.
4. Demo precedes UAT. UAT remains prohibited until explicit Founder Demo acceptance. Production customer traffic remains Founder-reserved.
5. Every environment has separate state, identity, VNet, data, Key Vault, DNS records, and evidence. Production data never moves down. "Dark Production" means the single Production environment before traffic activation, not a second environment.
6. A failed authorization, cost, security, recovery, or evidence gate stops before mutation.
7. First-party release membership remains exactly six. Pinned third-party runtime dependencies are recorded in a separately signed dependency manifest bound to the release tuple; they never become mutable or silently expand exact-six membership.

## Target Topology

```mermaid
flowchart TB
  GH[GitHub Actions OIDC] --> REL[Signed exact-six release tuple in GHCR]
  REL --> D
  REL --> U
  REL --> P

  subgraph D[Demo - leased]
    DDNS[www.demo / api.demo / auth.demo]
    DING[ACA managed ingress and L7 load balancer\nFounder IPv4 allowlist]
    DAPP[ACA revisions\nWeb, BP, PR, CE, AIR, Billing, identity edge, Keycloak, self-hosted Temporal, Redis]
    DDB[PostgreSQL Flexible Server\nprivate DNS, isolated databases]
    DKV[Key Vault private endpoint]
    DMON[Log Analytics]
    DDNS --> DING --> DAPP
    DAPP --> DDB
    DAPP --> DKV
    DAPP --> DMON
  end

  subgraph U[UAT - leased, production-shaped]
    UDNS[www.uat / api.uat / auth.uat]
    UING[ACA managed ingress and L7 load balancer\napproved tester allowlist]
    UAPP[Same digests and revision process\nidentity edge keeps Keycloak private\nTemporal Cloud per ADR-015]
    UDB[PostgreSQL Flexible Server\nPITR and restore qualification]
    UKV[Key Vault private endpoint]
    UMON[Log Analytics]
    UDNS --> UING --> UAPP
    UAPP --> UDB
    UAPP --> UKV
    UAPP --> UMON
  end

  subgraph P[Production - dark until separately activated]
    EDGE[Azure Front Door plus WAF\nintroduced only with approved cost and origin lock]
    PING[Private or origin-locked ACA ingress]
    PAPP[Blue-green ACA revisions]
    PDB[Production PostgreSQL\naccepted HA, PITR, RPO and RTO]
    PKV[Production Key Vault]
    PMON[Production telemetry and alerts]
    EDGE --> PING --> PAPP
    PAPP --> PDB
    PAPP --> PKV
    PAPP --> PMON
  end
```

Azure Container Apps ingress is the environment load balancer. Demo and UAT do not add Application Gateway or Front Door: those always-on products add cost without improving the Founder/tester-only boundary. Production edge is added only before customer traffic, after choosing an origin-lock design and accepting its cost.

## Environment Contract

| Capability | Demo | UAT | Dark Production |
|---|---|---|---|
| Public names | `www.demo.waooaw.com`, `api.demo.waooaw.com`, `auth.demo.waooaw.com` | `www.uat.waooaw.com`, `api.uat.waooaw.com`, `auth.uat.waooaw.com` | `www.waooaw.com`, `api.waooaw.com`, `auth.waooaw.com` reserved |
| Access | Founder `/32` | Approved tester CIDRs | No customer traffic |
| TLS | ACA managed certificates; monitored renewal | ACA managed certificates; monitored renewal | Front Door managed TLS after activation decision |
| Application compute | ACA min replicas `0`, max `1` | ACA min replicas `0`, bounded test max | Accepted production minima; no apply under WC-076 |
| Data | Synthetic; isolated PostgreSQL | Synthetic representative; isolated PostgreSQL and PITR test | Separate production data boundary |
| Redis | Transient ACA dependency; no backup | Transient ACA dependency; no backup | Managed or HA decision before activation |
| Temporal | Self-hosted ACA dependency using environment PostgreSQL | Temporal Cloud namespace and mTLS per ADR-015 | Temporal Cloud namespace; activation remains reserved |
| Expiry | Scale all workloads to zero; stop PostgreSQL; keep state, vault, DNS, backups and evidence | Same | Not leased |
| Cost | Pre-plan forecast gate, tags, alerts, short log retention | Same | Plan-only until separately authorized |

PostgreSQL Flexible Server cannot remain stopped indefinitely: Azure automatically restarts a stopped server after its service limit. A scheduled lease reconciler MUST re-stop expired Demo/UAT servers and verify workloads remain at zero. Reconciliation is idempotent, records evidence, retries only bounded transient failures, and escalates after its final attempt. Storage, backups, state, vault, DNS, and minimal telemetry continue to incur small foundation cost.

## Network And Trust Boundaries

- One VNet per environment with delegated ACA, delegated PostgreSQL, and private-endpoint subnets.
- Deployment jobs run on ephemeral Azure self-hosted runners inside environment-isolated runner subnets. GitHub-hosted runner public-IP discovery and temporary Storage firewall rules are prohibited after the Demo runner activation gate passes.
- Demo, UAT, and Production reuse one versioned runner blueprint, but never one runner instance or one unrestricted subnet. Each environment has a distinct runner label, subnet, managed identity boundary, and Storage private endpoint. Production runners remain at zero capacity unless a separately authorized Production job is active.
- The runner control plane is bootstrapped separately from environment Terraform because a runner must exist before Terraform can read its remote backend. Bootstrap state and credentials must not depend on the protected backend they create. GitHub App runner-registration material is held in Azure Key Vault, retrieved through managed identity, and never stored in GitHub variables or client secrets.
- Private endpoint addresses are environment-local private IPs, not public ingress addresses. One `privatelink.blob.core.windows.net` private DNS zone may be centrally managed and linked to the isolated runner VNets; VNet links do not grant cross-environment data or identity access.
- Terraform state and reviewed deployment configuration use Storage private endpoints. Public network access is disabled after private-path qualification. No load balancer, public IP, application DNS record, or TLS certificate is introduced by the Storage private endpoint path.
- Key Vault and PostgreSQL use private networking and private DNS.
- Only Web, Business Platform API, and a pinned identity-edge proxy receive public hostnames. Keycloak itself remains internal. The identity edge allowlists required OIDC discovery, realm, token, login, callback, and static-resource paths; it denies admin, management, metrics, and arbitrary proxying. CE, AIR, Billing, Redis, Temporal, database, direct Keycloak endpoints, and verification jobs remain private.
- ACA egress is default-deny with explicit HTTPS, Azure DNS, private network, GHCR, Azure control-plane, and approved provider destinations.
- Deployment and independent verification use distinct environment-scoped OIDC identities. Workloads use per-service managed identities and least-privilege Key Vault references.
- Terraform never registers subscription resource providers. Bootstrap owns the explicit provider allowlist.

### Private Runner Isolation Matrix

| Boundary | Demo | UAT | Production | Enforcement |
|---|---|---|---|---|
| Runner execution | ACA manual Job, zero idle executions | Not provisioned before Founder Demo acceptance | Zero capacity; plan-only until separate authorization | Repository-scoped registration with an environment-specific label; one ephemeral registration per execution |
| Runner subnet ingress | Deny all | Deny all | Deny all | No public IP, load balancer, inbound endpoint or reusable runner listener |
| Runner subnet egress | HTTPS to GitHub Actions/GHCR and Azure identity/management; private endpoints for Storage and Key Vault; Azure DNS | Same after activation | Same after activation | NSG denies cross-environment address ranges and permits required HTTPS Internet egress; Storage and Key Vault public access remain disabled, so their data planes are private-only. No unsupported claim of NSG FQDN filtering is permitted. |
| Runner managed identity | Read runner-registration material from bootstrap Key Vault; no secret write; no environment deployment role | Separate identity and vault scope | Separate identity and vault scope | `Key Vault Secrets User` on the one environment runner secret set only |
| Deployment OIDC identity | Environment resource-group deployment roles and environment state container access; no GitHub App secret access | Separate environment scope | Separate environment scope | Azure RBAC and exact GitHub environment subject; runner identity and deployment identity are never interchangeable |
| Storage path | Demo private endpoint and Demo backend/config prefixes | UAT private endpoint and UAT prefixes | Production private endpoint and Production prefixes | Public network disabled after qualification; data-plane RBAC denies every cross-environment identity |
| Negative proof | Demo runner cannot read UAT/Production state or runner secrets | UAT runner cannot read Demo/Production state or runner secrets | Production runner cannot read Demo/UAT state or runner secrets | Activation blocks until independent RBAC and data-plane denial tests pass |

The central Platform Architect owns the `privatelink.blob.core.windows.net` zone and its audit log. Each VNet link requires the environment owner and Security Architect to approve the expected Storage account resource ID and endpoint IP in a versioned Deployment Stack parameter manifest. Reconciliation rejects a VNet link, endpoint resource ID, or endpoint IP absent from that manifest. A DNS answer is qualification evidence only: successful access still requires matching environment RBAC. Conflicting endpoint records, unexpected VNet links, or resolution to a public Storage address block activation.

Runner VNets are not peered to each other. NSGs explicitly deny the other environment address spaces before their final deny rule. Azure RBAC omits cross-environment grants; no shared runner role is assigned above an environment state account or Key Vault. Azure resource diagnostic logs, Network Watcher connection tests, DNS results, and denied data-plane requests form the negative evidence; DNS alone never proves isolation.

### Runner Bootstrap Playbook

1. A GitHub-hosted bootstrap job authenticates to Azure with the constrained bootstrap OIDC identity. It may call Azure management APIs and GitHub APIs, but it never reads Terraform state or deployment configuration.
2. The job reconciles a versioned Azure Deployment Stack containing the environment runner VNet/subnet, NSG, shared ACA environment, manual runner/start-broker/cleanup-broker Jobs, distinct managed identities, private broker Key Vault access, Storage private endpoint, private DNS link, budgets, and diagnostics. Azure Deployment Stacks are the bootstrap ownership/state record; no local Terraform state or circular dependency on the protected backend is permitted.
3. The stack deployment is idempotent and deny-delete protected for retained networking, identity, vault, DNS, and endpoint resources. An interrupted reconciliation is rerun against the same stack name and template digest. Unexpected ownership, drift, denied deletion, or partial provisioning stops before runner registration.
4. A deterministic pre-token workflow step reads `architecture/reference/pipeline/github-runner-app-manifest.json`, queries the live user-account installation and compares the exact account, selected repository and repository permissions. Any missing or additional live permission or repository blocks token issuance; the step never mutates the App. INST-007 owns manifest changes and permission necessity; INST-009 owns schema validation and live equality. A new permission or replacement App requires an ADR amendment and fresh security acceptance.
5. The dedicated GitHub App is installed only on the Founder-owned `dlai-sd/waooaw-platform` repository with repository Administration write and Metadata read. It has no organization permission or runner-group authority. The Deployment Stack owns a dedicated key-import identity and no-ingress ACA Container App with zero minimum and one maximum replica. `scripts/goal006_import_app_signing_material.sh {environment}` temporarily scales it to one, opens a no-echo interactive import over ACA exec, imports the GitHub-generated PEM directly as a non-exportable Key Vault key limited to `sign` and `verify`, destroys the transient in-container file and always scales back to zero. No GitHub Secret, workflow value, Azure parameter or retained PEM is used. The importer identity has vault-scoped `Key Vault Crypto Officer`, the narrowest verified Azure role that supports import, and no other platform authority. A separate manual private ACA signing broker receives `Key Vault Crypto User` on the exact imported key version and uses the Key Vault Cryptography client/REST `sign` operation with RS256, a 10-second timeout and at most three transient retries; private key bytes never enter workflow or runner memory and no fallback exists. The resulting App JWT (maximum ten-minute expiry) is exchanged at `POST /app/installations/{installation_id}/access_tokens`; that installation token calls `POST /repos/dlai-sd/waooaw-platform/actions/runners/registration-token`. The broker can create/update only the short-lived runner-token secret through a set-only custom role and can read/start only the environment runner Job. The GitHub-hosted bootstrap identity has no Key Vault key-sign or runner-token data-plane authority. The ACA runner identity can `get` only that secret and has no key-sign permission. Token issuance occurs immediately before ACA start; the secret expires after 15 minutes and registration must finish within ten. The cleanup identity alone deletes the secret when registration succeeds, when the attempt fails/expires, and during orphan reconciliation.
6. The workflow has three execution boundaries: GitHub-hosted management jobs validate/reconcile the stack and cost then start a private broker with correlation metadata; `deploy-private` targets the environment runner label; and GitHub-hosted cleanup starts the private cleanup broker under `if: always()`. Hosted compute receives only broker execution status and never an App JWT, installation token or runner registration token. The brokers reuse the runner ACA environment, subnet, Key Vault private endpoint, private DNS, Log Analytics workspace and digest-pinned runner image. Each broker is manual, concurrency one, limited to five minutes and has zero idle replicas; therefore it adds execution-only compute within the existing FA-052 estimate and requires no GitHub account/setup change or new paid network resource. ACA runner concurrency is one and enforces a 60-minute execution timeout; GitHub ephemeral mode accepts one deployment job. Because hard workflow termination cannot guarantee downstream execution, the Deployment Stack also owns a separate ACA scheduled `runner-reconciler` Job every five minutes with a two-minute limit. Its distinct cleanup identity has exact-key signing, GitHub runner administration, token-secret delete and ACA execution read/stop; it has no token read/write, state/config data access or environment deployment role. It stops only executions older than 60 minutes or whose recorded GitHub run is terminal/absent, then removes that runner registration and token secret. Cleanup verifies zero registration/execution within five minutes and retries for at most 15 minutes. Any orphan beyond five minutes resets qualification, keeps the label inactive and notifies INST-009/007; no next deployment starts before cleanup.
7. Activation evidence proves private DNS resolution, exact configuration Blob access, Terraform backend list/read/write/lock behavior, no public Storage route, no cross-environment access, idempotent no-drift stack reconciliation, runner deregistration within the SLA, zero active runner executions, reconciler health/cost, and Deployment Stack health. Under FA-053, Demo qualification accepts successful run `32698031369` with zero forced cancellations; the Founder accepts the Demo-only residual risk that hard-cancellation cleanup remains unproven. Every other proof remains mandatory. Only then may the Demo deployment workflow replace `ubuntu-latest` and remove temporary public-IP firewall mutation.
8. Bootstrap resources survive Demo/UAT lease expiry at zero runner executions. Recovery reconciles the same Deployment Stack. Key deletion, App revocation, unresolved drift, or failed orphan cleanup raises a blocker; it never falls back to a public endpoint or long-lived credential.

The non-exportable GitHub App key version expires no later than 90 days after import and rotates immediately after suspected disclosure. Azure Monitor alerts INST-007 and the Founder 14 days before expiry. Exactly two Key Vault key versions may overlap during a bounded validation window; the previous App key is revoked in GitHub and disabled in Key Vault after a successful registration test. Recovery requires Founder-controlled GitHub App key issuance/import plus Security Architect validation. Key Vault soft delete and purge protection are mandatory; no plaintext backup is retained. Expiry or rotation failure blocks bootstrap and never activates a fallback credential.

Normal rotation occurs at or before day 60. The 90-day value is an absolute cryptographic expiry, not the operating rotation interval. A missed rotation alert, two missed reconciler schedules, selector ambiguity, permission-manifest mismatch or cleanup authentication failure disables the environment runner label and blocks new token issuance until INST-007 clears the recorded exception.

### Runner Activation Proof Matrix

| Activation stage | Required denial proof | Evidence | Gate consequence |
|---|---|---|---|
| Demo | Demo runner identity is denied access to reserved UAT/Production state scopes and runner-token scopes; no route exists to their address spaces | Azure RBAC assignment export, denied Storage/Key Vault requests where resources exist, no-peering inventory, NSG rules and Network Watcher connection result | Demo label remains inactive on any unexpected grant or route |
| UAT | Demo-to-UAT and UAT-to-Demo Storage/Key Vault requests are denied; neither VNet reaches the other endpoint; UAT is denied reserved Production scopes | Data-plane denial records, diagnostic logs, DNS results, no-peering inventory and Network Watcher connection results | UAT provisioning/label activation remains blocked |
| Production | Production-to-Demo/UAT and reciprocal Storage/Key Vault requests are denied; Production has no public Storage route | Same evidence set, independently run by INST-015 | Production remains plan-only until separate Founder activation |

Each row expands into three mandatory tests for each forbidden source/target pair: target FQDN resolution must not yield a reachable target path; source identity calls to target Storage and Key Vault must return Azure RBAC denial; and direct TCP 443 to the target private endpoint IP must be denied by NSG/Network Watcher or no route. All three results and the corresponding diagnostic/flow records are retained. No single layer may stand in for another.

INST-009 owns and executes the Runner Bootstrap interface gate after INST-003 accepts ADR-047 and INST-007 accepts the security design. INST-009 collects the immutable stack/template digest, exact GitHub App permission manifest, NSG/RBAC/DNS manifests and cost estimate. INST-015 independently executes the proof matrix, private-route tests, cancellation/orphan tests and zero-idle check. Results are recorded in the WC-076 checkpoint and PR evidence. Missing evidence keeps the environment runner label inactive with no public fallback.

The approved DNS parameter manifest is a preventive pre-start gate. The bootstrap job runs Deployment Stack `what-if` and compares live links/endpoints/records with the manifest. Wrong IDs/IPs, unexpected records/links or a public answer stop before token creation/ACA execution, retain live inventory and alert INST-007/009 for approved repair. Transient API timeout or expected-propagation NXDOMAIN retries at most three times with bounded backoff, then fails and alerts INST-009. Neither path creates a runner or silently changes DNS.

Before `what-if`, bootstrap verifies that the checked-in Deployment Stack template and environment parameter files come from the selected trusted-main commit and match the approved SHA-256 manifest. Runtime-generated templates, mutable template URIs and unrecorded overrides are prohibited. After convergence, the same commit/template/parameter tuple must produce a no-change `what-if`; otherwise runner registration remains blocked.

Bootstrap covers only the Deployment Stack resource graph and is state-idempotent/convergent within three attempts. Partial resources stay under the same stack ownership record and are repaired from the same immutable tuple; retained networking, identity, vault, endpoint and DNS resources are never rollback-deleted. Failure to converge enters `BOOTSTRAP_DRIFT_HOLD`. GitHub token issuance and runner/environment execution occur only after convergence and are outside bootstrap idempotency.

GitHub runner cleanup uses only the selected repository's runner inventory to evaluate candidates. Deletion requires one and only one registration to match the exact repository, environment label, `goal006-{environment}-` prefix, recorded workflow run ID, ACA correlation ID and lifecycle predicate. Selector ambiguity fails closed. If normal cleanup fails, the scheduled reconciler is the independent path; if two schedules are missed or authentication is unavailable for ten minutes, the environment enters cleanup-degraded hold and an INST-007-authorized GitHub-hosted recovery workflow performs the same correlation-checked cleanup. No deployment label is active during either hold.

Bootstrap generates `goal006:{environment}:{github_run_id}:{github_run_attempt}` before ACA start and binds it into the immutable manifest, ACA execution metadata and unique runner name. Cleanup eligibility is limited to a terminal/absent recorded GitHub run or an ACA execution at least 60 minutes old, with proof that no non-terminal job is assigned. The stateless scheduled ACA Job derives decisions from GitHub/Azure control-plane state and writes correlation-keyed Log Analytics events plus a 90-day token-free JSON artifact.

Suspected compromise places the environment in security hold and requires credential/key disablement, run cancellation, correlated execution/registration cleanup and token-secret deletion within five minutes. Recovery requires fresh non-exportable key material, clean inventory, manifest equality, private-route and cross-environment denial proof, a forced-cancellation cleanup test and INST-007 release. Full procedure and measurable SLAs are normative in ADR-047.

The Founder-authorized FA-052 limits are cumulative across all tagged GOAL-006 Azure resources. The pre-start gate is hard/fail-closed, CE-independent, and combines Azure Cost Management month-to-date actuals/forecast no older than 24 hours with the reviewed incremental estimate. Unavailable/stale cost data, missing tags, or projected breach blocks before mutation. The decision artifact and digest become GOAL-006 evidence.

ADR-046 governs workload-to-service authentication and does not create a new runner certificate authority here. ADR-047 runner trust uses GitHub's ephemeral runner registration, Azure managed identity and environment-scoped OIDC. If a runner later calls a governed private WAOOAW service, that call must separately satisfy ADR-046; runner registration never substitutes for workload mTLS.

## Data And Migration Contract

- Remove PostgreSQL sidecars from CE, BP, and Billing. One PostgreSQL Flexible Server per environment hosts separate databases/roles for application state, Keycloak, and Temporal.
- Terraform first creates PostgreSQL with Entra authentication enabled, password authentication disabled, and no administrator password. The environment deployment identity is the bounded Entra database administrator.
- A private, digest-pinned bootstrap job connects with an Entra token, creates separate databases and least-privilege roles, and writes generated dependency credentials directly to Key Vault. Values never pass through Terraform inputs, state, plans, outputs, workflow logs, or artifacts.
- Application services MUST use managed-identity token refresh where their runtime supports it. Password authentication is enabled only in a second reviewed foundation plan when a pinned dependency such as Keycloak or self-hosted Demo Temporal cannot use Entra tokens; only its generated non-admin role may use that path.
- UAT and Production use Temporal Cloud under ADR-015, with environment-specific mTLS material held in Key Vault. They do not deploy a self-hosted Temporal server.
- Redis remains reconstructible and transient in Demo/UAT.
- Migration is a digest-pinned, one-shot pre-traffic job. Migrations are expand-only and bind release/config/schema compatibility.
- A successful compute health check does not prove data recovery. UAT MUST prove isolated restore/PITR before Production readiness.
- Rollback never runs destructive down-migrations. The previous qualified digest must read the current additive schema.

## Implementation Interface Gates

| Gate | Required input | Output | Fail-closed behavior | Evidence owner |
|---|---|---|---|---|
| Runner bootstrap | Accepted ADR-047, versioned Deployment Stack template, GitHub App permission manifest, environment label/group, subnet/NSG/RBAC/DNS matrix and cost estimate | One healthy ephemeral runner execution with private state/config access, negative isolation proof, deregistration and zero-idle evidence | Missing ADR acceptance, secret material, private resolution, exact backend operation, isolation denial, cleanup, stack health or cost proof blocks runner-label activation; no public fallback | INST-009 with INST-007; INST-015 independently verifies |
| State isolation | Environment backend key, resource scope, OIDC subject, naming and tags | Separate environment plan/state with no cross-environment reference | Wrong subscription, scope, backend or existing-resource ownership stops plan | INST-009 with INST-007 |
| Release and dependencies | Signed exact-six manifest, signed pinned-dependency manifest, reviewed config digest, schema compatibility | One immutable deployment tuple | Missing member, digest/signature mismatch, mutable dependency or incompatible schema stops before cloud mutation | INST-009 with INST-006/007 |
| Runtime configuration | Versioned non-secret schema, Key Vault references, per-service identity matrix | Validated startup configuration with no image-baked environment values | Missing/unknown config, secret fallback or identity failure keeps revision unready | INST-005/007 with INST-009 |
| Database bootstrap | Entra-only server, database/role/RLS contract, bounded bootstrap identity | Separate databases/roles and Key Vault references; no value in Terraform or workflow evidence | Partial bootstrap, Key Vault write failure or unexpected password authority blocks application plan | INST-006/007 with INST-009 |
| Dependency handoff | Pinned identity-edge, Keycloak, Demo Temporal and Redis digests; Temporal Cloud endpoint/mTLS for UAT | Healthy private dependencies and approved public identity paths | Version, TLS, health or path-policy failure keeps application traffic at zero | INST-005/007 with INST-009 |
| Pre-traffic qualification | Migration result, readiness/dependency probes, required CCT set, public journey probes | Signed traffic-switch decision | Any required internal or public probe, CCT, migration or evidence failure leaves old revision active | INST-015 with INST-005/009 |
| Rollback | Previous qualified tuple, current schema compatibility, approval and hold state | Audited ACA traffic switch with no rebuild or migration | Missing tuple, expired hold, incompatible schema or approval failure blocks rollback | INST-009 with INST-006 |
| Lease expiry | Lease record, drain deadline, evidence watermark, protected-foundation inventory | Apps at zero, PostgreSQL stopped, evidence complete, foundation retained | Incomplete evidence, active work or protected-resource delta raises blocker; bounded retries never delete protected state | INST-009 with INST-006/015 |

The exact CCT subset, probe semantics, timeout bounds, configuration schema, role/RLS matrix, and dependency versions are executable inputs owned by the offices above. They must be versioned before the corresponding Terraform slice can apply.

## Promotion, Blue-Green, And Rollback

1. CI builds and attests the exact-six tuple once.
2. Plan verifies current-main release, configuration digest, cost, identity, state, provider allowlist, DNS prerequisites, and migration compatibility.
3. Apply creates a new ACA revision with a release-derived suffix while the previous revision remains available.
4. Run migration, private health probes, the environment-required CCT set, and public journey probes against the new revision without shifting production traffic. Failure of any required probe is blocking.
5. Shift traffic to the new revision only after all gates pass. Keep the immediately previous qualified revision at zero traffic for at least 24 hours and through the active Demo/UAT lease, whichever is later. Retain at most two inactive qualified revisions unless an incident or evidence hold requires more.
6. Rollback is a traffic switch to the immediately previous qualified revision plus its compatible configuration tuple. The previous digest MUST read the current additive schema; a release with a breaking schema cannot shift traffic until compatibility is restored and qualified. Rollback does not rebuild, retag, or run a destructive down-migration.
7. Failed new revisions receive zero traffic and are retained with evidence until the incident/release retention rule permits removal.

Demo may shift directly from zero to 100% after verification. UAT proves the same blue-green and rollback mechanics required for Production. Production rollout percentages and observation windows require accepted SLO evidence.

## Cost Controls

- Reuse the existing state account and GHCR release evidence.
- Private runner networking is budgeted independently from application infrastructure: approximately one Private Link endpoint-hour charge per active environment plus low-volume data processing and one shared private DNS zone. VNet/subnet creation, private IP allocation, load balancers, and certificates add no runner-path charge because the design does not provision public ingress. The combined plan remains fail-closed above FA-052's INR 15,000 one-time or INR 10,000 monthly ceiling.
- Runner compute is ephemeral and starts at zero capacity. Demo is activated and cost-qualified first; UAT remains unprovisioned until Founder Demo acceptance; Production runner capacity remains zero and its private path is plan-only until separately authorized.
- The target state boundary is one Storage account per environment. During incremental migration, multiple environment-specific private endpoints may reach the existing account, but backend keys, identities, subnets, and evidence remain isolated; account separation must complete before UAT qualification.
- Use one small PostgreSQL Flexible Server per non-Production environment; stop it on lease expiry and reconcile the stopped state.
- Keep ACA workloads at min replicas zero outside active leases.
- Use short non-Production log retention and bounded ingestion.
- Do not provision Front Door Premium, Application Gateway, managed Redis, production HA, or a second region under the Demo recovery sprint.
- Every plan records current cost, forecast, incremental monthly estimate, lease expiry, and tagged resource delta. Forecast above the FA-052 INR 15,000 one-time or INR 10,000 monthly envelope blocks apply.

## Implementation Order

1. **Runner control plane:** bootstrap the Demo ephemeral self-hosted runner subnet, managed identity, Storage private endpoint and shared private DNS without depending on the protected remote backend; prove exact-blob and Terraform backend access, teardown, and cost evidence before changing workflow runner labels.
2. **Control plane:** after the complete qualification matrix passes, INST-009 records the result and the Founder authorizes Demo activation. One reviewed commit/PR must switch Demo plan jobs to the environment-scoped runner label and remove temporary public-IP firewall mutation, with an automated assertion that both deltas are present. Disable Storage public network access only after the private job proves exact backend operations. Repeat for UAT only after Founder Demo acceptance; keep Production plan-only and zero-capacity. Reintroducing public mutation or a GitHub-hosted deploy label requires a new reviewed architecture decision.
3. **Foundation:** VNet/subnets, Log Analytics, Key Vault, PostgreSQL Flexible Server, private DNS, environment identities, DNS prerequisites.
4. **Runtime dependencies:** database roles/config references, Keycloak, Temporal, transient Redis; remove sidecar databases.
5. **Application plane:** exact-six ACA revisions, private/public boundaries, custom domains, managed TLS, managed identities.
6. **Release mechanics:** migration job, pre-traffic verification, blue-green traffic switch, rollback, lease expiry and scale-to-zero reconciliation.
7. **Promotion:** Founder Demo acceptance gate, same-tuple UAT deployment/qualification, dark-Production plan only.

A full Demo apply is prohibited until slices 1 through 5 pass a real OIDC plan and independent review. Documentation updates are limited to this contract, WC-076 execution references, and PROJECT_STATE checkpoints; executable code and cloud evidence remain primary.
