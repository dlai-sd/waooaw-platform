# GOAL-006 P1-WC03 Platform Architecture

## Record Control

| Field | Value |
|---|---|
| `institution_id` | INST-009 |
| `goal_id` | GOAL-006 |
| `record_id` | CR-GOAL-006-INST-009-02 |
| `record_type` | Contribution Record |
| `go_authorization` | GOA-GOAL-006-INST-009-02 |
| `work_component` | P1-WC03 — Azure Environment, JIT, IaC, CI/CD, Reliability, DR, And Cost Architecture |
| `produced_at` | 2026-08-13T09:48:02Z |
| `source_commit` | `e9b76b61a96313c930394e5406efef067ee17975` |
| `status` | ACCEPTED — R-109 / CR-GOAL-006-INST-002-04 |

This contribution is Phase 1 platform design only. It performs no provider query, pricing query,
implementation, workflow change, credential action, DNS action, spend, deployment, production
decision, or Platform Operations activation. The Founder Session Directive and FR-001 through
FR-056 remain controlling.

## Design Drivers

- Keep Azure-first, Azure Container Apps, PostgreSQL 16, Keycloak, Temporal, OTel, Azure Monitor,
  Key Vault, GitHub Actions, GHCR, Docker, and Terraform unless owner evidence rejects reuse.
- Build once and promote one verified image digest through Demo, UAT, and Production.
- Keep durable data, evidence, Terraform state, Key Vault material, and required recovery artifacts
  outside automatic environment shutdown.
- Remove long-lived Azure deployment credentials and plaintext Terraform secret inputs.
- Make Demo/UAT economical through leased active compute, not unsafe destruction of foundations.
- Treat existing Terraform and workflows as inputs with known defects, not as production proof.
- Do not introduce Kubernetes, Nexus, Grafana, or a replacement registry/CI platform.

## Platform Decisions

| ID | Decision and recommendation | Alternatives evaluated | Owner boundary | Status / protected decision |
|---|---|---|---|---|
| PA-01 | Keep one reusable AzureRM platform module and separate `demo`, `uat`, and `prod` root compositions with separate state and configuration. Retain `dev` for engineering only. | One root with environment switches risks cross-environment state; cloned modules drift. | INST-009 owns layout; INST-005/007/006 supply component, security, and data requirements. | RECOMMENDED. Production subscription/resource-group model remains Founder-protected if cost or authority changes. |
| PA-02 | Split each cloud environment into a durable foundation and leased workload plane. Foundation contains remote state, protected secret store references, required data/recovery resources, evidence, and approved DNS objects. Workload contains Container Apps revisions and other safely reducible compute. | Always-on non-production wastes cost; full `terraform destroy` risks durable state; Kubernetes adds unjustified operations. | INST-009 owns lifecycle architecture; INST-006 defines protected data/recovery; INST-007 defines secret/access safeguards. | RECOMMENDED. Exact retention, RPO/RTO, DNS, and destruction approvals remain open. |
| PA-03 | Use GitHub Actions OIDC federation with a distinct Azure identity and GitHub Environment per environment. Grant only environment-scoped deployment permissions. | `AZURE_CREDENTIALS_*` is long-lived; shared identity increases blast radius; self-hosted runners are not justified. | INST-009 owns workflow integration; INST-007 owns trust conditions, RBAC, break glass, and rotation. | RECOMMENDED. Production identity permissions and approval actors require security review and Founder authorization. |
| PA-04 | Make OCI repository digest the authoritative release identity. Capture digests from the build output into a signed promotion manifest; deploy and roll back by digest. Mutable `demo`, `uat`, and `prod` tags may exist only as non-authoritative pointers. | Commit tags alone do not prove registry content; rebuilding per environment violates FR-031; mutable-tag deployment breaks provenance. | INST-009 owns pipeline; INST-007 owns signing/attestation policy; QA owns gate evidence. | RECOMMENDED. Production promotion remains Founder-protected. |
| PA-05 | Keep GHCR and GitHub Actions. Generate an SBOM, provenance/attestation, signature, vulnerability result, test results, and promotion record for each digest. Security selects the accepted formats/verification policy in P1-WC05. | Nexus/ACR add cost/migration without a proven registry gap; unsigned tags are insufficient. | INST-009 defines artifact flow; INST-007 decides supply-chain controls. | PARTIAL REUSE. Tool detail awaits P1-WC05; no registry replacement ADR needed. |
| PA-06 | Use OTel as the telemetry contract and Azure Monitor/Application Insights as cloud backend. Define dashboards, alerts, synthetics, release markers, cost signals, and daily/monthly summaries as version-controlled IaC. | Grafana duplicates the selected backend; vendor SDK coupling weakens portability. | INST-009 owns platform telemetry; INST-005 defines component health; INST-007 defines redaction; PO/QA accept SLOs. | RECOMMENDED. Numeric production SLOs remain unaccepted proposals. |
| PA-07 | Recreate stateless compute from version-controlled IaC and digest manifests. Data recovery uses interfaces supplied by INST-006; no RPO/RTO or backup schedule is decided here. A secondary Azure region is not provisioned until cost, data, security, and Founder review. | Premature active-active raises cost; backup-only without restore proof is inadequate. | INST-009 owns compute continuity; INST-006 owns data recovery; Founder accepts production residual risk/region. | INTERFACE DEFINED; detailed DR remains open. |
| PA-08 | Enforce cost with environment budgets, forecast/anomaly alerts, mandatory tags, lease expiry, scale-to-zero where safe, and a pre-action cost gate. Budget breach blocks new deployment and escalates; it never deletes protected state automatically. | Shell-only gates are incomplete; automatic full deletion is unsafe; unbounded spend violates control requirements. | INST-009 owns platform controls; Platform Operations later executes; Founder owns ceiling exceptions. | RECOMMENDED. Exact prices and protected thresholds await verified pricing and Founder decisions. |

## Target Environment Architecture

| Layer | Demo | UAT | Production |
|---|---|---|---|
| Purpose | Short-lived demonstration and acceptance preview | Production-like qualification of the exact approved digest | Customer service at minimum safe capacity |
| Root composition | `environments/demo` | `environments/uat` | Existing `environments/prod`, corrected against accepted designs |
| State | Dedicated remote key and environment identity | Dedicated remote key and environment identity | Dedicated remote key, strongest approved retention/access controls |
| Foundation | Protected state, approved secret/data/recovery references, evidence, approved DNS objects | Same classes, isolated from Demo/Production | Same classes; no automatic shutdown |
| Workload | Leased; activate on approved manual/release trigger; scale safely to zero after expiry | Leased qualification window; activate from approved promotion manifest | Always available at owner-approved minimum safe capacity |
| Data | Synthetic/non-production only; treatment decided by INST-006 | Synthetic/masked non-production only; treatment decided by INST-006 | Production data; recovery and access decided by INST-006/007 |
| Promotion | Deploy digest after CI gates; automated smoke/CCT evidence | Same digest after Demo evidence and UAT approval gate | Same digest after UAT evidence and Founder-reserved production approval |
| Exposure | Proposed URLs only; public/internal map awaits P1-WC04/05 | Proposed URLs only; public/internal map awaits P1-WC04/05 | Proposed URLs only; DNS/production action remains Founder-protected |

No environment is created by copying another environment's state. Shared modules are reused, while
state, identity, configuration, secrets, data, evidence, budgets, and approval gates remain isolated.

## JIT Lifecycle Contract

1. A manual or release trigger requests a lease with environment, purpose, digest, owner, expiry,
   cost centre, and evidence record.
2. The workflow validates authorization, current budget, state lock, approved configuration,
   recovery prerequisites, and digest evidence before changing workload capacity.
3. Activation restores or starts only the workload resources allowed by the approved design, then
   runs health, dependency, synthetic, CCT, security, and cost checks assigned by QA.
4. Lease extension requires recorded authority and a new expiry. No indefinite implicit extension.
5. Expiry stops new use, records evidence, verifies required backup/recovery and active-session
   conditions, then scales or removes only disposable workload resources.
6. Failure leaves protected foundations intact, records the failed step, and escalates. It does not
   loop indefinitely, destroy data, purge secrets, delete state, or alter DNS.

Exact lease durations, startup targets, inactivity thresholds, and backup prerequisites remain
owner proposals for P1-WC06/P1-WC08/P1-WC09 and later Founder acceptance where protected.

## Terraform And State Architecture

```text
infrastructure/terraform/
  bootstrap/                 # remote state and federation prerequisites; separately authorized
  modules/
    foundation/              # state-adjacent, identity hooks, monitoring and protected interfaces
    workload/                # Container Apps environment/apps and safely reducible compute
  environments/
    dev/
    demo/
    uat/
    prod/
  policies/                  # static policy inputs selected by security/data owners
```

- Each root has an explicit backend key and environment-scoped identity; no local state is an
  accepted cloud path.
- CI runs format, validate, lint, security/policy checks, and a saved plan. Apply consumes the
  reviewed plan under its GitHub Environment gate.
- Plans and state are treated as sensitive evidence and retained under an owner-approved policy.
- Secret values are never Terraform inputs, resource arguments, outputs, plan artifacts, or plain
  Container App environment variables. Terraform wires managed identity and secret references;
  P1-WC05 defines exact Key Vault/RBAC/bootstrap controls.
- Module outputs expose configuration references and service endpoints, not credentials.
- Destructive plans, protected-resource changes, backend changes, and production changes require
  explicit escalation and cannot be auto-reconciled.

This design replaces the current direct password/PAT variables and executing-principal Key Vault
assignment. It does not claim that merely marking a Terraform value `sensitive` removes it from state.

## Delivery Architecture

```text
PR -> build/test/scan -> image digest + evidence manifest
   -> Demo deploy by digest -> Demo qualification
   -> UAT promote same digest -> UAT qualification/approval
   -> Production promote same digest -> low-risk release -> post-deploy verification
```

The manifest binds source commit, image names/digests, build identity, SBOM, provenance, signature,
scan results, test/CCT results, configuration version, and promotion history. Every gate verifies the
manifest before acting. Environment configuration is separate, reviewed, and contains no secrets.

The current `promote.yaml` design is superseded as follows:

- DAST depends on the actual UAT/QA deployment job, never nonexistent `tag-qa`;
- the workflow passes the manifest/digest between jobs rather than rediscovering mutable tags;
- Demo, UAT, and Production are explicit GitHub Environments with distinct OIDC identities;
- UAT and Production stages exist and enforce their evidence/approval gates;
- rollback selects a previously qualified digest and configuration pair;
- `environment-deployment-verification.yaml` must execute a real rollback path or fail closed, never report a pending
  TODO as completed rollback;
- concurrency prevents overlapping environment mutations; bounded retries apply only to transient,
  idempotent steps; CCT, policy, authorization, security, and destructive-plan failures do not retry.

## Reliability, Observability, And DR Interface

| Concern | Platform recommendation | Required downstream decision/evidence |
|---|---|---|
| Availability | Minimum replicas and scaling are derived per environment from approved customer and constitutional SLOs, expected load, cold-start evidence, and cost. | INST-005 component health/degradation; QA load/cold-start tests; Founder accepts production tradeoff. |
| Telemetry | OTel traces, metrics, logs, and events use release digest, environment, service, correlation, tenant-safe dimensions, and constitutional evidence identifiers. | INST-007 redaction/data rules; INST-005 signal contracts. |
| Alerts | Alert on customer journey, Evidence First/Emergency Stop, service/dependency health, release regression, saturation, certificates, DNS, backup, drift, and cost. | Product Owner/QA set measurable targets; Platform Operations defines response boundaries. |
| Dashboards | Version-controlled Azure workbooks/dashboards show environment, release, journey, service, dependency, data/recovery, security, and cost health. | P1-WC09 daily/monthly operating views and escalation. |
| Compute recovery | Reapply reviewed IaC and deploy the last qualified digest/configuration pair. | QA proves recovery time and failure behavior. |
| Data recovery | Platform exposes backup destination, identity, scheduling, monitoring, and restore execution interfaces. | INST-006 decides frequency, retention, RPO/RTO, encryption, migration, restore and DR region. |
| Regional failure | Keep application/container/database portability and remote evidence sufficient for a second-region plan. | INST-006/007/009 propose region and residual risk; Founder approves cost/production decision. |

P1-WC03 proposes no new numeric availability, latency, cold-start, RPO, or RTO commitment. Existing
constitutional floors remain binding; all other values require owner evidence and acceptance.

## Cost Model

No Azure pricing API, calculator export, invoice, or live resource query was authorized or examined.
Therefore this contribution does not invent SKU prices or claim ceiling compliance. Every later priced
row must use: INR; Azure billing currency USD; pricing date; Central India unless approved otherwise;
exchange rate/source; usage/lease/retention/support assumptions; taxes included/excluded; and confidence
range. P1-WC03 uses `TBD — verified pricing required` where those inputs are unavailable.

Cost controls are mandatory tags, per-environment budgets, warning/block thresholds, forecast and
anomaly alerts, JIT workload leases, safe scale-to-zero, log sampling/retention, cost attribution by
service/environment, pre-deployment cost checks, and monthly reliability/cost review. A ceiling breach
blocks new spend and escalates; it does not weaken a constitutional floor or delete protected state.

## P1 Risk Treatment

| Risk | P1-WC03 treatment | Remaining owner/gate | Status |
|---|---|---|---|
| P1-R01 | Demo/UAT roots and durable-foundation/JIT-workload pattern defined. | Phase 2 implementation and Phase 3 qualification | DESIGN ADDRESSED; OPEN |
| P1-R02 | OIDC-only, environment-scoped deployment identity defined. | P1-WC05 trust/RBAC; Founder production authority | DESIGN ADDRESSED; OPEN |
| P1-R03 | No secret values through Terraform; managed reference interface defined. | P1-WC05 secret/state/bootstrap controls | ROUTED; OPEN |
| P1-R04 | Digest-authoritative manifest, SBOM/provenance/signature/scan evidence defined. | P1-WC05 verification policy; QA gates | DESIGN ADDRESSED; OPEN |
| P1-R05 | Correct stage dependency and real rollback requirements defined. | Phase 2 workflow implementation/testing | DESIGN ADDRESSED; OPEN |
| P1-R06 | Platform exposes public/internal and network interfaces only. | P1-WC04 component placement; P1-WC05 security design | ROUTED; OPEN |
| P1-R07 | Compute recovery and data-recovery interface defined without RPO/RTO invention. | P1-WC06 data/recovery design | ROUTED; OPEN |
| P1-R08 | IaC-managed telemetry/alerts/dashboards and operating interfaces defined. | P1-WC05/P1-WC09 policies and response | PARTIAL; OPEN |
| P1-R09 | No activation assumed. | P1-WC09/P1-WC10 and Founder activation | OPEN |
| P1-R10 | Live state remains unknown. | Phase 3 authorized provider verification and qualification | OPEN |

## Mandatory Conclusion Tables

All monetary cells below use this frame: `INR TBD; Azure billing currency USD; pricing date
2026-08-13; region Central India unless approved otherwise; no live pricing or deployment usage;
taxes excluded; low confidence pending verified price/usage evidence.`

### A. Component And Cost Summary

| Component | Purpose | Azure/tool option | Environment | Always on or JIT | Size/SKU | One-time cost | Monthly baseline | Monthly active-use cost | Cost control | Owner |
|---|---|---|---|---|---|---|---|---|---|---|
| Remote state foundation | Isolated locked Terraform state | Azure Storage backend | Demo/UAT/Production | Always on | TBD after security design | INR TBD under frame above | INR TBD under frame above | INR TBD under frame above | RBAC, retention, lock, budget, no secrets | INST-009 + INST-007 |
| Secret/identity foundation | Workload references and federation | Key Vault + managed identity + GitHub OIDC | Each environment | Always on | TBD by P1-WC05 | INR TBD under frame above | INR TBD under frame above | INR TBD under frame above | Least privilege, audit, rotation, no plaintext state | INST-007 + INST-009 |
| Application workload | Run deployable services | Azure Container Apps | Demo/UAT/Production | Demo/UAT JIT; Production always available | Pending P1-WC04/SLO tests | INR TBD under frame above | INR TBD under frame above | INR TBD under frame above | Lease, safe scale-to-zero, replica caps, budget | INST-009 |
| Data platform | Durable application/evidence data | PostgreSQL 16/pgvector candidate reuse | Each environment isolated | Always on unless Data design proves safe alternative | Pending P1-WC06 | INR TBD under frame above | INR TBD under frame above | INR TBD under frame above | Retention, backup, capacity, cost alerts | INST-006 + INST-009 |
| Identity broker/workflow dependencies | Authentication and durable orchestration | Keycloak 25.0.6; Temporal candidate reuse | Per approved topology | Pending component/reliability design | Pending P1-WC04 | INR TBD under frame above | INR TBD under frame above | INR TBD under frame above | Capacity, retention, dependency health | INST-005 + INST-009 |
| Observability | Logs, metrics, traces, dashboards, alerts | OTel + Azure Monitor/Application Insights | Each environment | Always on with controlled ingestion | Pending signal/retention design | INR TBD under frame above | INR TBD under frame above | INR TBD under frame above | Sampling, retention, budgets, noise control | INST-009 |
| Delivery and registry | Build, evidence, immutable promotion | GitHub Actions + GHCR | Cross-environment | On demand | Existing plan/limits; verify | INR TBD under frame above | INR TBD under frame above | INR TBD under frame above | Concurrency, retention, digest evidence | INST-009 |

### B. Performance And Reliability Summary

| Component | Expected load | Latency target | Availability target | Scaling rule | Cold-start target | RPO | RTO | Monitoring signal | Failure response |
|---|---|---|---|---|---|---|---|---|---|
| Constitutional Engine | Pending workload evidence | Existing constitutional floor; no new value accepted | Pending constitutional/customer/cost review | Warm/scale policy from QA evidence; no public ingress | Pending QA evidence | N/A for stateless compute; data values by INST-006 | Compute recreation target pending QA | Evidence First, Emergency Stop, gRPC RED/saturation | Fail safe, halt affected action, escalate |
| Business Platform/Web journey | Pending Product/QA model | Proposed target pending QA baseline | Proposed target pending Product/Founder acceptance | Request/saturation rule after load test | Pending QA evidence | Data values by INST-006 | Compute recovery pending QA; data by INST-006 | External synthetic, RED, release marker | Roll back digest/config; diagnose dependency |
| Professional/AI Runtime | Pending workload/provider model | Proposed target pending QA baseline | Proposed target pending Product acceptance | Queue/request/provider signals after test | Pending QA evidence | Data values by INST-006 | Pending compute/provider recovery design | Session, provider, dependency, constitutional signals | Degrade or halt within approved boundary |
| PostgreSQL/data state | Pending capacity/data model | Query target pending Data/QA | Target pending Data/Platform/Founder | Capacity plan; no unsafe automatic downsize | N/A | Pending INST-006 proposal | Pending INST-006 proposal | Capacity, connection, backup, restore, replication | Contain writes if unsafe; execute tested restore/escalation |
| Delivery pipeline | Expected release frequency pending PO | Gate/rollback time pending QA | Gate integrity required; no bypass | Concurrency by environment; bounded idempotent retries | N/A | Promotion evidence retained per policy | Previous qualified digest/config recovery target pending QA | Gate, digest, deployment, cost, rollback evidence | Fail closed; automatic rollback only when proven safe |

### C. Delivery Tool Decision Summary

| Capability | Existing tool | Alternatives evaluated | Selected tool | Why selected | Cost | Lock-in/exit path | Decision/ADR needed |
|---|---|---|---|---|---|---|---|
| Cloud runtime | Azure Container Apps | AKS/Kubernetes; other managed container runtimes | Azure Container Apps | Existing Azure-first decision, scale-to-zero, lower operations; no proven gap | INR TBD under frame above | OCI images; rewrite provider IaC | No new ADR unless owner evidence rejects ADR-010 |
| Registry | GHCR | Nexus; ACR; Docker Hub | GHCR | Accepted ADR-012; current CI integration; no material gap | INR TBD under frame above | OCI registry migration and manifest copy | No replacement ADR |
| CI/CD | GitHub Actions | Azure Pipelines; Jenkins; GitLab CI | GitHub Actions | Accepted ADR-013; repository-native environments/OIDC | INR TBD under frame above | Workflow rewrite; evidence format retained | No new ADR; workflow design review required |
| IaC | Terraform AzureRM | Pulumi; Bicep; manual CLI | Terraform AzureRM | Existing modules/skills and declarative plan/state controls | INR TBD under frame above | Azure provider rewrite; preserve module contracts | No new ADR |
| Observability | OTel + Azure Monitor/Application Insights | Grafana stack; vendor APM | Existing OTel/Azure stack | Accepted ADR-009; portable telemetry without another operator surface | INR TBD under frame above | Retarget OTLP; recreate dashboards/alerts | No new ADR |
| Secrets/identity | Key Vault + Azure/GitHub identities | Vault; long-lived service principal secrets | Existing Key Vault plus OIDC/managed identity | Accepted posture and removes stored deployment credentials | INR TBD under frame above | Secret-provider migration behind approved references | P1-WC05 security decision; ADR only if posture changes |
| Supply-chain evidence | GHCR/GitHub evidence capabilities plus open formats | Tag-only; separate artifact repository | Digest manifest with SBOM/provenance/signature | Meets FR-031/033 without new registry; exact controls owned by Security | INR TBD under frame above | OCI/open evidence formats | P1-WC05 decision; ADR if new strategic service introduced |

### D. Story And Delivery Summary

| Epic/story | Objective | Owner | Dependencies | Size | Implementation estimate | Cloud cost impact | Phase | Acceptance evidence |
|---|---|---|---|---|---|---|---|---|
| E01-S01 | Environment/JIT/IaC/delivery/reliability/cost design | INST-009 | P1-WC01/P1-WC02 | XL; specialist re-estimate required | Pending P1-WC07 decomposition | INR TBD under frame above | Phase 1 design; later Phase 2/3 | Accepted P1-WC03, decisions, tables, reviews |
| E02-S01 | Deployable component/integration topology | INST-005 | Accepted P1-WC03 | L; owner re-estimate required | Pending P1-WC07 | INR allocated after topology | Phase 1 design | P1-WC04 component/config/health/failure contracts |
| E03-S01 | Security architecture and threat model | INST-007 | P1-WC01 through P1-WC04 | XL; owner re-estimate required | Pending P1-WC07 | INR TBD under frame above | Phase 1 design | P1-WC05 control/test/risk evidence |
| E04-S01 | Data isolation and recovery design | INST-006 | P1-WC01/P1-WC03/P1-WC04 | L; owner re-estimate required | Pending P1-WC07 | INR TBD under frame above | Phase 1 design | P1-WC06 recovery/migration/test evidence |
| E05-S01/E05-S02 | Feasibility and qualification architecture | INST-010 / accountable QA TBD | Accepted specialist designs | XL combined; owners re-estimate | P1-WC07 supplies | Qualification active-use INR TBD | Phase 1, then authorized Phase 2/3 | Feasibility record and complete automated qualification matrix |
| E06-S01 | Operations policies and handover readiness | Platform Operations candidate + INST-004 review | P1-WC02 through P1-WC08 | XL; owners re-estimate | Pending accepted operations design | INR TBD under frame above | Phase 1 readiness; Phase 3 activation protected | Runbooks, simulations, review, Founder activation record |
| E07-S01 | Integrated Phase 2/3 authorization package | INST-011 + reviewers | P1-WC01 through P1-WC10 | XL; re-estimate at integration | Consolidated from owner estimates | Consolidated verified cost model | Phase 1 closure | Six tables, traceability, clearance, Founder decisions |

### E. Environment Summary

| Environment | Purpose | URL/API | Provision trigger | Shutdown trigger | Data treatment | Promotion gate | Monthly ceiling | Operator |
|---|---|---|---|---|---|---|---|---|
| Demo | Demonstration and early environment acceptance | Proposed `www.demo.waooaw.com` / `api.demo.waooaw.com`; Founder confirmation required | Authorized manual/release request with lease and digest | Lease expiry/inactivity after protected-state checks | Synthetic/non-production; INST-006 design pending | CI evidence plus Demo smoke/CCT/security checks | Current ceiling constraint applies; exact acceptance/price evidence pending | Platform Operations candidate after activation; supervised before then |
| UAT | Production-like qualification of same digest | Proposed `www.uat.waooaw.com` / `api.uat.waooaw.com`; Founder confirmation required | Approved digest after Demo evidence and UAT lease | Qualification end/lease expiry after protected-state checks | Synthetic/masked non-production; no production data | UAT functional/CCT/security/performance/recovery evidence and approval | Current ceiling constraint applies; exact acceptance/price evidence pending | Platform Operations candidate after activation; supervised before then |
| Production | Customer service at minimum safe capacity | Proposed `www.waooaw.com` / `api.waooaw.com`; Founder confirmation required | Founder-reserved promotion of UAT-qualified digest | No automatic environment shutdown | Production data under INST-006/007 controls | Founder authorization, low-risk release, post-deploy verification | Founder-protected; verified model required before authorization | Activated Platform Operations after acceptance; otherwise no handover |

### F. Risk And Decision Summary

| Risk/decision | Impact | Recommendation | Owner | Founder decision required | Deadline | Blocking work |
|---|---|---|---|---|---|---|
| Demo/UAT roots absent | Cannot reproduce required environments | Implement accepted PA-01/PA-02 after Phase 2 authorization | INST-009 | No unless cost/authority boundary changes | Before Phase 2 completion | Phase 3 Demo/UAT |
| Long-lived Azure credential | Credential exposure and rotation risk | OIDC-only per PA-03; revoke old credential after verified cutover | INST-007 + INST-009 | Production permissions/authority only | Before any cloud deployment | Security and Phase 3 |
| Plaintext Terraform secret flow | State/plan/revision exposure | P1-WC05 defines reference/bootstrap model; Phase 2 removes values | INST-007 + INST-009 | Only if residual risk requires acceptance | Before implementation acceptance | Security and deployment |
| Mutable-tag promotion/no attestations | Build-once chain cannot be proven | Digest manifest and evidence per PA-04/PA-05 | INST-009 + INST-007 + QA | Production promotion remains protected | Before Phase 2 implementation acceptance | UAT/Production promotion |
| Broken/incomplete promote workflow | Current pipeline cannot qualify end to end | Implement explicit Demo/UAT/Production graph and real rollback | INST-009 | Production gate choice only | Before Phase 2 completion | Phase 3 |
| Numeric SLOs/RPO/RTO unknown | Capacity, reliability, recovery and cost cannot be accepted | Owners propose from evidence; QA validates; Founder accepts protected production values | INST-011/005/006/009/QA | Yes for protected production commitments/residual risk | Before Phase 1 closure | Final cost/capacity and Phase 2 WCs |
| Verified Azure pricing absent | Ceiling compliance cannot be claimed | Obtain owner-reviewed calculator/API export and usage assumptions without creating resources | INST-009 + INST-011 | Yes for ceiling exception | Before Phase 1 closure | Founder authorization package |
| DNS/region/production topology open | Deployment endpoint and DR scope unresolved | Present owner recommendations after security/data design | INST-009/007/006 | Yes | Before Phase 3 authorization; package may retain explicit decision | DNS/Production/DR |
| Platform Operations inactive | No autonomous live owner | Complete P1-WC09/10, simulations, then Founder activation | Candidate + INST-004 | Yes | Before handover | Phase 3 closure |
| Live state unknown | Repository design may differ from provider state | Verify only under Phase 3 authorization; fail on unmanaged drift | INST-009 + QA | Cloud-query/deployment authority required | Phase 3 entry | Provisioning/qualification |

## Completeness And Routing

| Obligation | Status |
|---|---|
| Demo/UAT/Production topology and JIT contract | COMPLETE FOR P1-WC03 |
| Terraform/state/repository layout | COMPLETE FOR P1-WC03; security/data details routed |
| OIDC and immutable delivery architecture | COMPLETE FOR P1-WC03; security/QA controls routed |
| Observability/scaling/continuity/DR/cost architecture | COMPLETE AT PLATFORM INTERFACE; numeric and specialist decisions open |
| P1-R01/R02/R04/R05/R08/R10 treatment | COMPLETE; risks remain open until implementation/live proof |
| Six exact Founder conclusion tables | COMPLETE |
| FR-045 pricing truth | COMPLETE AT UNKNOWN-STAGE; verified price evidence still required |
| Phase 2/3 authority | NOT GRANTED |

Recommended next gate: independent review of CR-GOAL-006-INST-009-02. If accepted, route P1-WC04
to INST-005 for deployable component and integration topology only. P1-WC05/P1-WC06 decisions,
implementation, cloud action, DNS, production, and activation remain blocked.
