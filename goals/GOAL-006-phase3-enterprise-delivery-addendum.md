# GOAL-006 - Phase 3 Enterprise Delivery Addendum

| Field | Value |
|---|---|
| Record ID | `GEP-GOAL-006-INST-013-03` |
| Record type | Phase 3 enterprise delivery clarification |
| Institution | INST-013 - Goal Orchestrator |
| Work Contract | WC-074 |
| Produced | 2026-08-14 |
| Status | DRAFT FOR INDEPENDENT DELTA REVIEW - NO PHASE 3 AUTHORITY |
| Baseline | PR #286 merge `94701362d957fdc13d88bc7637c8b773a7cfb385` |

## Outcome Clarification

GOAL-006 must produce more than hosted workloads. It must establish a governed delivery capability
that makes software change routine, observable, cost-constrained, independently verifiable and
immediately reversible.

A release succeeds only when the exact approved artifact tuple is:

1. deployed without rebuilding;
2. technically healthy and constitutionally compliant;
3. secure at its intended public/private boundaries;
4. successful on approved customer journeys;
5. operating inside its accepted cost envelope; and
6. recoverable or reversible through a tested path.

Running containers, a successful Terraform apply, or a healthy endpoint alone is not release
success. This addendum makes the enterprise delivery obligations explicit without changing the
accepted P3-WC01 through P3-WC08 sequence or authorizing live action.

## Enterprise Delivery Principles

| ID | Principle | Binding consequence |
|---|---|---|
| ED-01 | Build once, promote by immutable identity | Demo, UAT, Production and rollback consume the same signed exact-six OCI digest manifest; no environment rebuild |
| ED-02 | Intent is simple; control is rigorous | One authorized action starts an orchestration state machine but never bypasses approval, policy, cost or independent verification |
| ED-03 | Blue stays safe until Green is proven | The accepted revision remains available until the candidate passes every applicable gate |
| ED-04 | Failure restores service, not appearances | Failed candidates retain evidence and traffic returns to the last accepted tuple without rebuilding |
| ED-05 | Data change is independently recoverable | Expand/contract compatibility, PITR and forward repair protect durable state; destructive down-migration is prohibited |
| ED-06 | Cost is a deployment property | Estimate, ceiling, lease and actual reconciliation are promotion gates, not after-the-fact reports |
| ED-07 | Customer value is release evidence | Technical health cannot compensate for a failed customer journey or unacceptable unit economics |
| ED-08 | Deployment evidence is independently confirmed | Author, workflow executor and deployment confirmer remain constitutionally distinct under C-065 |
| ED-09 | Every control fails closed | Missing identity, digest, signature, target, cost, backup, telemetry or authority stops progression |
| ED-10 | Portability remains deliberate | Azure services require named escape hatches under ADR-010; delivery contracts remain OCI, OTel and Terraform oriented |

## Target Operator Experience

The authorized operator supplies only intent:

| Input | Values | Constraint |
|---|---|---|
| Action | `DEPLOY`, `PROMOTE`, `ROLLBACK`, `DEACTIVATE`, `STATUS` | Environment-specific authority required |
| Environment | `demo`, `uat`, `prod` | Sequence and separate authorization enforced |
| Release | Signed release-manifest digest | Must resolve to exactly six approved OCI digests |
| Purpose | Approved release, qualification, recovery or retirement reason | Evidence First record required |
| Lease | Required for Demo/UAT | Explicit owner, expiry, cost centre and stop condition |

The workflow derives all other values from reviewed environment configuration. The operator does
not paste credentials, image tags, database passwords, resource names, routing commands or ad hoc
Terraform variables.

`One action` means one governed request, not one unchecked shell command. The request returns one
release-operation ID whose state, evidence, cost, approvals and rollback path are continuously
visible.

## Delivery Control Plane

```text
Authorized intent
  -> authorization and environment gate
  -> release-manifest/signature/provenance verification
  -> state lock, drift, quota, dependency and recovery preflight
  -> reviewed Terraform plan and cost forecast
  -> environment approval
  -> deploy inactive Green revisions
  -> migration compatibility and dependency checks
  -> health + functional + CCT + security + customer-journey checks
  -> approved progressive traffic movement through managed edge
  -> independent post-deployment confirmation
  -> accept Green and retire Blue within C-067 window
  -> reconcile actual cost and publish immutable release evidence
```

The control plane is implemented through GitHub Actions reusable workflows and GitHub Environments,
with Azure OIDC used only by deployment jobs. Runtime identities, Key Vault references, the managed
edge and Container Apps revisions are execution targets, not alternative sources of release
authority.

### Release Operation State Machine

```text
REQUESTED
  -> AUTHORIZED
  -> PREFLIGHT_PASSED
  -> PLAN_APPROVED
  -> GREEN_DEPLOYED
  -> GREEN_VERIFIED
  -> TRAFFIC_SHIFTING
  -> INDEPENDENTLY_CONFIRMED
  -> ACCEPTED
  -> BLUE_RETIRED
  -> CLOSED
```

Terminal or recovery states are `DENIED`, `BLOCKED`, `FAILED_GREEN`, `ROLLING_BACK`,
`ROLLED_BACK`, `FAILED_ROLLBACK`, `DEACTIVATED` and `REVOKED`. Every transition records actor,
authority, prior state, release tuple, environment, timestamp, evidence references, cost snapshot
and reason. Retrying creates a new attempt under the same operation; it never erases the failed
attempt.

### Workflow Surface

| Workflow | Responsibility | Must not do |
|---|---|---|
| Build and attest | Build six images, test, scan, generate SBOM/provenance/OpenVEX, sign manifest | Access Azure or promote mutable tags as authority |
| Readiness and plan | Verify live prerequisites when authorized, acquire lock, detect drift, produce plan and cost delta | Apply resources or read secret values |
| Deploy Green | Apply reviewed workload change and create inactive candidate revisions | Move accepted traffic or rebuild images |
| Verify Green | Run health, integration, CCT, security, data and customer-journey checks | Self-accept the deployment |
| Shift traffic | Apply owner-approved stages and observation windows through the selected edge | Expose private services or exceed accepted risk |
| Confirm release | Independently compare telemetry, journeys, constitutional checks and cost with accepted targets | Author deployment changes |
| Roll back | Restore traffic to the last accepted tuple and preserve failure evidence | Rebuild, mutate evidence or down-migrate constitutional data |
| Retire/deactivate | Retire Blue within C-067 window or stop leased lower workload safely | Destroy protected state, recovery material, vaults or evidence |

## Immutable Promotion Contract

The release manifest is the sole promotion authority and binds:

- exactly six OCI repository digests;
- source commit and reviewed configuration identity;
- manifest signature and signer policy;
- SBOM, SLSA provenance, OpenVEX and scan evidence per member;
- migration/data compatibility declaration;
- minimum platform contract and dependency versions;
- qualification evidence inherited from each preceding environment; and
- the last compatible rollback tuple.

Promotion performs registry retrieval and verification before environment action. Convenience tags
may point to an accepted digest but never authorize deployment. UAT and Production reject a tuple
that differs from the predecessor environment. Lost registry content is not replaced by rebuilding
the same source; it is a material release failure requiring requalification.

## Progressive Blue-Green Contract

1. Resolve Blue as the environment's last independently accepted tuple.
2. Deploy Green as inactive revisions with zero accepted public traffic.
3. Validate Green through private or tightly controlled qualification paths.
4. Prove schema, identity, dependency, telemetry and rollback compatibility.
5. Move traffic through owner-approved stages and observation windows.
6. At every stage evaluate technical, constitutional, security, journey and cost signals.
7. Automatically stop progression and restore Blue when a blocking signal breaches its accepted
   target or required evidence becomes unavailable.
8. Obtain independent deployment confirmation before declaring Green accepted.
9. Retire or scale Blue to zero within the C-067 30-minute post-confirmation limit.
10. Reconcile cost and close the operation only after traffic, revision and evidence state agree.

Exact percentages, observation durations, minimum sample sizes and automatic-rollback thresholds are
QA/Product/Platform/Security owner decisions informed by authorized live evidence. Until accepted,
traffic progression remains blocked rather than defaulting to industry-generic values.

Emergency Stop remains pre-warmed and outside ordinary rate limits throughout traffic movement. CE,
AIR, Billing, data, management, metrics and administrative surfaces remain private. The selected
managed edge/WAF must control public routing without making direct Container Apps endpoints an
alternate public path.

## Rollback And Recovery Contract

| Failure class | Automatic response | Required evidence |
|---|---|---|
| Green provisioning or startup | Keep Blue at accepted traffic; mark Green failed | Plan/apply logs, revision state, health and cost |
| Green qualification | Do not progress traffic; isolate Green | Failed test, CCT, security, journey or dependency evidence |
| Progressive traffic regression | Stop progression and restore Blue | Trigger signal, target, traffic history and restoration proof |
| Independent confirmation failure | Restore Blue unless an accepted safe hold state exists | Confirmer verdict and resulting traffic state |
| Blue restoration failure | Raise high-severity incident and execute accepted recovery path | Failed rollback and incident evidence; no false success |
| Data incompatibility | Stop before traffic; restore data only through accepted PITR/recovery authority | Migration tuple, recovery point and integrity checks |

Rollback uses the retained accepted OCI digest/configuration tuple. Database change uses additive
expand/contract sequencing so Blue and Green remain compatible during the release window.
Constitutional schema down-migration, evidence rewriting and Production-to-lower data movement remain
prohibited. Where data cannot safely roll back, application traffic restores to the compatible Blue
revision and the database follows an accepted forward-repair plan.

## Environment And Cost Operating Model

| Environment | Runtime posture | Promotion role | Cost posture |
|---|---|---|---|
| Demo | Sole active lower workload first; synthetic data; explicit lease | Prove deploy, blue-green, rollback, recovery, journeys and shutdown | Scale-to-zero/removal after evidence and backup gates; retain only approved foundation |
| UAT | Activated only after Demo acceptance and Demo workload shutdown | Promote identical tuple; production-like load, resilience, DR and rollback | Explicit lease and expiry; no indefinite idle capacity |
| Production | Separate identity, state, data, edge and risk decision | Promote identical UAT-accepted tuple after Founder approval | Owner-approved minimum safe capacity; no automatic full shutdown |

One lower-environment public edge/IP may serve Demo and later UAT when only one is active, with
separate hostname, certificate, routing and evidence identities. Production requires a separate
edge/IP and policy boundary. This is a recommended cost/blast-radius balance, not a product or DNS
decision.

Production PostgreSQL and its backup chain remain separate. A lower-environment PostgreSQL service
may be shared sequentially only if Data and Security accept separate databases, roles, credentials,
network boundaries, backups and environment-addressable restore evidence, and prove that no Demo/UAT
overlap or Production-derived data exists.

### FinOps Gates

| Gate | Required behaviour |
|---|---|
| Before request acceptance | Confirm environment authority, lease, cost centre and remaining ceiling |
| Before plan approval | Show dated estimate, current spend, forecast, resource delta, uncertainty and ceiling impact |
| Before Green deployment | Revalidate budget and detect price/configuration drift |
| During dual revisions | Track incremental release-window cost and enforce C-067 retirement timer |
| During environment life | Enforce lease expiry, scale-to-zero eligibility, anomaly alerts and protected-resource exclusions |
| After release or rollback | Reconcile estimate with actual cost and attribute variance to release/resources |
| At environment acceptance | Report total environment cost and cost per successful approved customer journey |

C-067 ceilings remain binding maxima, not spending targets. The plan should recommend lower operating
limits from dated evidence. Breach blocks new deployment; it never automatically deletes protected
state. Cost optimization cannot weaken availability, Evidence First, Emergency Stop, isolation,
security, recovery or independent verification.

## Release Intelligence Contract

Every release operation has one correlated view containing:

- operation, manifest, commit, six digests, environment and active revisions;
- current state, approvals, lease, traffic distribution and rollback tuple;
- deployment events and release markers across traces, metrics and logs;
- API RED, saturation, dependency and data health;
- Evidence First and Emergency Stop availability/latency;
- security, WAF, identity, secret-reference and boundary signals;
- approved customer-journey outcomes;
- current, forecast and incremental cost plus unit economics;
- failed attempts, rollback/recovery events and independent verdict; and
- DORA deployment frequency, lead time, change failure rate and restoration time.

Telemetry absence is not health. Public health endpoints expose no secrets, topology or sensitive
detail. Release confirmation consumes independently collected telemetry and tests rather than the
deployer's assertion.

## Phase 3 Capability Binding

| Component | Enterprise delivery obligations added or made explicit | Exit effect |
|---|---|---|
| P3-WC01 Readiness | Verify registry retrieval, workflow/environment configuration, OIDC subjects, edge options, revision capability, cost/pricing inputs, monitoring prerequisites and rollback dependencies | No resource creation until the complete control-plane prerequisites and owner decisions are visible |
| P3-WC02 Foundations | Establish remote state/locking, isolated identities/vault references, monitoring, budgets, managed edge foundations and deployment evidence custody | Foundations support governed plans and zero application traffic |
| P3-WC03 Demo | Execute one-action deployment, Green isolation, progressive shift, automatic/manual rollback drill, release dashboard, cost reconciliation and safe deactivation | Demo proves the delivery system, not only application functionality |
| P3-WC04 UAT | Promote the identical tuple; execute production-like load, resilience, rollback, recovery, migration compatibility and release-intelligence gates | Independent proof that promotion and recovery hold under accepted UAT targets |
| P3-WC05 Production | Require explicit Founder promotion; deploy minimum-safe Green, perform non-destructive progression, preserve Blue, confirm independently and reconcile actual cost | Production evidence is presented without implied acceptance |
| P3-WC06 Handover | Bind deployment, rollback, cost, evidence and access runbooks to accepted Incident/Change/Release policies | Supervised operators can act without receiving architecture or self-approval authority |
| P3-WC07 Supervision | Exercise failed deploy, stalled Green, automatic rollback, failed rollback, budget breach, drift, recovery and decommission scenarios | Measured competence and DORA baseline support activation decision |
| P3-WC08 Closure | Consolidate release operations, environment evidence, actual cost, unit economics, DORA, residual risks and activation status | Founder receives a complete delivery-capability acceptance package |

## Current Repository Gaps Routed To Phase 3

The following are gaps to verify and route, not authorization to repair:

1. The legacy promotion workflow uses long-lived `AZURE_CREDENTIALS_DEV`, mutable retagging and a
   five-service list; it is not the accepted exact-six OIDC promotion control plane.
2. The signed six-member manifest and offline promotion simulator are not yet connected to live
   GitHub Environment deployment workflows.
3. Blue-green revision creation, staged traffic movement, independent confirmation and automated
   rollback are not implemented as one stateful operation.
4. Current Phase 2 Terraform does not yet provide the complete data, identity, workflow, cache,
   managed edge/WAF, public-IP, DNS/certificate and private-registry execution topology.
5. Cost checks do not yet combine plan delta, dated forecast, actual spend, lease state,
   double-capacity timer and post-release reconciliation.
6. Release intelligence does not yet correlate manifest, revisions, traffic, CCT/security/journey
   evidence, rollback and cost in one operation record.
7. Canonical Incident, Change and Release policies remain required before P3-WC06/07.

Each material repair requires an accepted owner contract, exact artifact binding, fresh estimate,
GO Authorization, later Acceptance and independent review. Platform IT Expert Skill 17 remains
inactive until its separate lifecycle gate completes.

## Protected Decisions

This addendum does not decide:

- Azure edge/WAF, database, cache, identity, workflow, monitoring or SKU selection;
- region, subscription/resource-group model, IP, hostname, DNS or certificate action;
- traffic percentages, observation windows, automatic-rollback thresholds or test targets;
- RPO/RTO, retention, backup cadence, Production capacity or residual risk;
- monetary ceilings below the binding constitutional maxima or approval actors;
- credentials, secret values, provider access, cloud creation, expenditure or activation.

These remain with the named Platform, Solution, Security, Data, Product, QA, Operations or Founder
authority. Missing decisions stop the affected component.

## Dependency Impact Report

| Field | Finding |
|---|---|
| Changed fact | Founder clarified that visible enterprise CI/CD, DevOps, cloud, monitoring and cost excellence are required Goal outcomes |
| Baseline | WC-073/R-127 and PR #286 remain the approved Phase 3 readiness baseline |
| Direct impact | P3-WC01..08 acceptance evidence must explicitly prove the bound delivery capabilities |
| Indirect impact | Owner contracts for workflow, edge, data, observability, cost and operations must align before implementation/live execution |
| Unaffected evidence | Phase 1 architecture, Phase 2 implementation, 147/147 tests, 150/150 proofs and R-120..R-127 remain accepted within their stated boundaries |
| Rework decision | No Phase 2 file is reopened by this planning record; gaps are routed as Phase 3 owner contributions |
| New protected actions | None; all cloud, DNS, spend, Production, activation, approval and merge controls remain unchanged |
| Review requirement | Fresh independent Platform, Solution, Security, Data, QA and constitutional delta review |

## Acceptance Standard

This addendum is complete only when independent review confirms that it:

- makes every enterprise capability mandatory and measurable without inventing specialist decisions;
- preserves exact-six immutable promotion and the accepted Demo-to-UAT-to-Production sequence;
- defines fail-closed one-action orchestration, blue-green progression and compatible rollback;
- treats customer journey, constitutional compliance, security and cost as co-equal release gates;
- preserves C-065 independence and C-067 cost/double-capacity controls; and
- grants no Phase 3 execution or Platform IT Expert Skill 17 activation authority.