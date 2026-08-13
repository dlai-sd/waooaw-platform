# GOAL-006 P1-WC01 Current-State Inventory And Reuse/Gaps

## Record Control

| Field | Value |
|---|---|
| `institution_id` | INST-009 |
| `goal_id` | GOAL-006 |
| `record_id` | CR-GOAL-006-INST-009-01 |
| `record_type` | Contribution Record |
| `go_authorization` | GOA-GOAL-006-INST-009-01 |
| `work_component` | P1-WC01 — Current-State Inventory And Reuse/Gaps |
| `produced_at` | 2026-08-13T09:10:33Z |
| `source_commit` | `65959848797f77986b96b19eeb62e4ea87f5a474` |
| `status` | ACCEPTED — R-107 / CR-GOAL-006-INST-002-02 |

This contribution inventories committed repository state. It does not verify any running
container, GitHub Actions run, GHCR image, Azure resource, DNS record, credential, customer
endpoint, cost, or deployment. Those remain `LIVE_UNKNOWN` because no live-provider query or
deployment action was authorized or executed for P1-WC01.

## Evidence Rules

| Class | Meaning |
|---|---|
| `REPOSITORY_VERIFIED` | The cited committed artifact exists and directly contains the stated declaration or implementation. |
| `RECORDED_RESULT` | An authoritative project record reports an earlier result; it was not rerun for P1-WC01. |
| `DECLARED_ONLY` | A design or configuration declares intent, but current execution or deployment is unverified. |
| `NOT_FOUND` | Targeted inspection found no artifact implementing the named capability. |
| `LIVE_UNKNOWN` | Current external or runtime state was not queried. |

Repository presence is not proof of production readiness, successful execution, provider state,
or customer availability. Absence findings are limited to the targeted paths and terms described
below.

## Inventory Matrix

| Surface | Verified current state | Evidence | Class | Gap or unknown |
|---|---|---|---|---|
| Service source | `src/` contains Constitutional Engine, Business Platform, Professional Runtime, AI Runtime, Billing Engine, and Trust Layer. The web application is under `web/`. | `src/`; `web/` | `REPOSITORY_VERIFIED` | CI and Terraform package only CE, BP, PR, AIR, and web. Billing Engine and Trust Layer are outside that five-image deployment set. Runtime state is `LIVE_UNKNOWN`. |
| Local topology | `docker-compose.yml` declares test/sprint runners, platform dependencies, five core application services, Billing Engine, many MCP services, and web. | `docker-compose.yml` | `REPOSITORY_VERIFIED` | Compose declarations were not started in P1-WC01. Health and compatibility are `LIVE_UNKNOWN`. |
| API contracts | OpenAPI contracts exist for Business Platform, Professional Runtime, AI transcription, DMA relationship outcomes, WBE relationship workspace, and Relationship Workspace; Emergency Stop WebSocket is documented separately. | `architecture/reference/api-specs/` | `REPOSITORY_VERIFIED` | CI lints only the Business Platform and Professional Runtime OpenAPI contracts. |
| Keycloak | A committed WAOOAW realm export exists. Docker Compose and Terraform declare Keycloak 25.0.6. | `infrastructure/keycloak/waooaw-realm.json`; `docker-compose.yml`; `infrastructure/terraform/modules/core/main.tf` | `REPOSITORY_VERIFIED` | Import/provisioning success and live realm state are `LIVE_UNKNOWN`. |
| Terraform environments | Environment compositions exist for `dev` and `prod`; both call the shared AzureRM core module. No `demo` or `uat` composition exists. | `infrastructure/terraform/environments/dev/main.tf`; `infrastructure/terraform/environments/prod/main.tf` | `REPOSITORY_VERIFIED` | Founder-required Demo and UAT topology is not represented. Backend storage configuration is not committed beyond the state key. No plan/apply was run. |
| Azure core module | The module declares resource group, Log Analytics, Application Insights, Key Vault, PostgreSQL 16 with extensions, Container Apps environment, five platform apps, Keycloak, Temporal, Ollama, and PgBouncer. | `infrastructure/terraform/modules/core/main.tf` | `REPOSITORY_VERIFIED` | No VNet/subnet/private endpoint, DNS zone, custom domain, WAF, managed certificate, or alert resource was found in the Terraform tree. Live resources are `LIVE_UNKNOWN`. |
| Exposure | Terraform declares CE, AIR, Temporal, Ollama, and PgBouncer with internal ingress; BP, PR, web, and Keycloak with external ingress. | `infrastructure/terraform/modules/core/main.tf` | `DECLARED_ONLY` | Internal-only intent is not backed by private networking or a live exposure test. CORS enforcement was not found in Terraform. |
| Secret handling | The accepted secret-management ADR requires Key Vault and managed identity for cloud workloads. Current Terraform passes database passwords and GHCR PAT values directly into Container App environment/secret blocks and assigns Key Vault access to the executing principal. | `adr/ADR-014-secret-management.md`; `infrastructure/terraform/modules/core/main.tf` | `REPOSITORY_VERIFIED` | Workload managed identities and Key Vault secret references are not implemented in the core module. Terraform state exposure risk requires Security Architect review before implementation. |
| CI build and quality | CI builds and pushes five SHA-tagged images, runs gitleaks, unit/coverage checks, OpenAPI/proto lint, CodeQL, Trivy, dependency scanning, and license checks. | `.github/workflows/ci.yaml` | `REPOSITORY_VERIFIED` | The workflow pushes images on pull requests. No SBOM generation, image signature, or provenance attestation was found. Current workflow execution is `LIVE_UNKNOWN`. |
| Deployment and promotion | On pushes to `main`, `promote.yaml` retags the same SHA images to mutable `dev` and `qa` tags, deploys the SHA images to dev, then declares integration and CCT gates. | `.github/workflows/promote.yaml` | `REPOSITORY_VERIFIED` | The workflow uses `AZURE_CREDENTIALS_DEV` rather than OIDC, has no UAT/production promotion, and its DAST job depends on nonexistent job `tag-qa`. Immutable digest capture and digest-based promotion are not implemented. |
| Rollback and verification | Blue-green deployment script contains traffic rollback on failed green health checks. Post-deploy workflow declares a rollback job. | `scripts/blue-green-deploy.sh`; `.github/workflows/post-deploy-verify.yaml` | `REPOSITORY_VERIFIED` | Post-deploy rollback execution is a TODO and only records `PENDING`; no general release rollback workflow is implemented. |
| Drift and lifecycle | No Terraform drift workflow or safe environment create/destroy/lease workflow was found in `.github/workflows/`. Dev uses zero minimum replicas; prod declares CE minimum one and references a separately applied scaling rule. | `.github/workflows/`; `infrastructure/terraform/environments/dev/main.tf`; `infrastructure/terraform/environments/prod/main.tf`; `infrastructure/container-apps/scaling-rules.yaml` | `NOT_FOUND` / `DECLARED_ONLY` | JIT leases, TTL cleanup, lifecycle evidence, drift control, and reproducible Demo/UAT creation remain gaps. |
| Data durability | PostgreSQL 16 and prod high availability are declared. No platform backup script, restore drill, RPO/RTO qualification, or disaster-recovery runbook was found in targeted `scripts/`, `infrastructure/`, and `standards/` inspection. | `infrastructure/terraform/modules/core/main.tf`; `scripts/`; `standards/` | `DECLARED_ONLY` / `NOT_FOUND` | Backup retention, restore acceptance, migration safety, and DR evidence require Data Architect ownership. |
| Observability | OTel/Jaeger/Azure Monitor is the accepted posture. Terraform declares Log Analytics and Application Insights. Performance and post-deploy workflows exist. | `adr/ADR-009-opentelemetry-observability.md`; `infrastructure/terraform/modules/core/main.tf`; `.github/workflows/performance-baseline.yaml`; `.github/workflows/post-deploy-verify.yaml` | `REPOSITORY_VERIFIED` | No Azure Monitor alert rule or committed dashboard resource was found. The CE OTLP value is constructed as a URL from an Application Insights connection string and requires implementation validation. |
| Cost control | Dev and prod Terraform tags declare INR 10,000 and INR 15,000 monthly ceilings. Promotion contains an Azure consumption query and 80% warning/95% block logic. | environment `main.tf` files; `.github/workflows/promote.yaml`; `adr/ADR-027-cloud-architecture-optimization.md` | `REPOSITORY_VERIFIED` | No budget resource, anomaly alert, forecast, or emergency cost shutdown automation was found. The shell cost gate has not been execution-verified here. |
| Operations policy | No dedicated incident, change, release, vulnerability-management, access-control, backup, or DR standard exists in `standards/`. Platform Operations agent specification is explicitly `DRAFT`, pending EA review and Founder approval, and `NOT ACTIVATED`. | `standards/`; `architecture/reference/agents/platform-operations-agent.md` | `NOT_FOUND` / `REPOSITORY_VERIFIED` | Operational handover cannot claim readiness or activation. Policy owners must supply the missing controls in later Phase 1 components. |
| Qualification evidence | PROJECT_STATE records WC-065 as the latest completed Work Contract and PR #278 as the latest merge. Existing tests and coverage artifacts are repository evidence only. | `constitution/PROJECT_STATE.md`; `tests/`; coverage artifacts | `RECORDED_RESULT` | No tests, Terraform validation, workflow run, image inspection, or live probe was executed for P1-WC01. |

## Material Delivery Risks

| ID | Verified risk | Required owner contribution | Effect |
|---|---|---|---|
| P1-R01 | Demo and UAT Terraform compositions are absent. | INST-009 Platform Architect | Blocks a complete environment model. |
| P1-R02 | Deployment authentication uses a credential secret; workload identity is not implemented in the deployment path. | INST-007 Security Architect with INST-009 | Blocks security acceptance of cloud delivery. |
| P1-R03 | Runtime secrets are passed through Terraform values and Container App configuration rather than managed identity plus Key Vault references. | INST-007 Security Architect with INST-009 | Blocks security acceptance; may place sensitive values in Terraform state. |
| P1-R04 | The pipeline does not capture/promote immutable image digests and lacks SBOM, signing, and attestation. | INST-009 Platform Architect with INST-007 | Blocks supply-chain acceptance and Founder-required immutable promotion. |
| P1-R05 | `promote.yaml` references nonexistent job `tag-qa`; UAT and production stages are absent. | INST-009 Platform Architect | Blocks a credible end-to-end promotion design. |
| P1-R06 | Private networking, DNS/custom domains, managed TLS, WAF, and explicit cloud CORS controls are absent from Terraform. | INST-007 Security Architect, INST-009, INST-005 Solution Architect | Blocks exposure-boundary acceptance. |
| P1-R07 | Backup/restore, RPO/RTO, and DR qualification artifacts are absent. | INST-006 Data Architect | Blocks data durability and recovery acceptance. |
| P1-R08 | Alert/dashboard resources and formal incident/change/release/access/vulnerability policies are absent. | INST-009, INST-007, INST-011 Product Owner | Blocks operational handover acceptance. |
| P1-R09 | Platform Operations is draft and not activated. | INST-004 Enterprise Architect; Founder activation remains protected | Blocks assignment of autonomous operating responsibility. |
| P1-R10 | Live Azure, GHCR, DNS, workflow, and endpoint state is unknown. | Phase 3 authorized owners | Cannot be used as evidence in Phase 1 or Phase 2 readiness claims. |

## Contribution Reuse Tests

All reuse decisions below are limited to Phase 1 grooming for GOAL-006. Each source is `Accepted`,
exists at the pinned source commit, and has an immutable file hash. Reuse does not prove its
implementation complete or its declarations current in Azure.

| Reuse record | Source | SHA-256 | Producer / decision owner | Approved target scope | Compatibility and assumptions | Changed facts / applicability | Validation |
|---|---|---|---|---|---|---|---|
| RR-GOAL-006-01 | ADR-009 | `566b064373277f469181264c3aa5d3dc926e21a6617fdb720c65817e32c03799` | INST-009 + INST-004 / accepted ADR authority | Phase 1 observability baseline | OTel remains the vendor-neutral telemetry contract. | Current Terraform has no alert/dashboard resources; `PARTIAL`. | INST-009 at 2026-08-13T09:10:33Z |
| RR-GOAL-006-02 | ADR-010 | `90364de2316183a8977ce758c7cbed58e9957876bdb460c9d8c28a5effb45821` | INST-004 + INST-009 / accepted ADR authority | Azure-first architecture and portability assessment | Application services remain OCI-packaged and use open protocols. | Azure core module exists; portability escape hatches remain design claims; `PARTIAL`. | INST-009 at 2026-08-13T09:10:33Z |
| RR-GOAL-006-03 | ADR-012 | `0c058af06d2bf8cc72ce845a2078d2b2fdf8bb3166ed53184cc0fd4e166bb62f` | INST-009 + INST-004 / accepted ADR authority | Registry and build-once baseline | GHCR remains the selected registry. | SHA tags exist, but digest capture/promotion does not; `PARTIAL`. | INST-009 at 2026-08-13T09:10:33Z |
| RR-GOAL-006-04 | ADR-013 | `c34b5c3e560776e4a4fd15b786998f6773ff2c4f657f599dd9368dd105e72c61` | INST-009 + INST-004 / accepted ADR authority | CI/CD stage and gate baseline | GitHub Actions remains the selected pipeline. | Current workflow stops before UAT/prod and contains a broken dependency; `PARTIAL`. | INST-009 at 2026-08-13T09:10:33Z |
| RR-GOAL-006-05 | ADR-014 | `2014c377ad32c156c2c7cce9aecc5a46b0146e974dd5b8a656577f9bbeccb60f` | INST-007 + INST-009 / accepted ADR authority | Secret and identity control baseline | Key Vault and managed identity remain required for cloud workloads. | Current Terraform and workflow diverge from the ADR; `PARTIAL`. | INST-009 at 2026-08-13T09:10:33Z |
| RR-GOAL-006-06 | ADR-027 | `eec39130fed79cdca3cbcf18e9c591409ef4c38c1a5c32c93cddd0039bdb5744` | INST-004 / accepted ADR authority | Cost and scaling constraints | Constitutional cost ceilings remain controlling. | IaC tags and a shell check exist; provider budgets/anomaly controls do not; `PARTIAL`. | INST-009 at 2026-08-13T09:10:33Z |

All records use source commit `65959848797f77986b96b19eeb62e4ea87f5a474`. No broader ADR
family reuse is claimed. Reuse outside the stated target scope requires a new applicability test.

## Completeness And Routing Verdict

| Question | Verdict |
|---|---|
| Is the P1-WC01 repository inventory sufficient to begin Product Owner outcome, SLO-priority, and story-model work in P1-WC02? | `YES — SUBJECT TO INDEPENDENT EVIDENCE REVIEW` |
| Does P1-WC01 establish that the cloud delivery capability is secure, complete, deployable, or production-ready? | `NO` |
| Does P1-WC01 authorize implementation, workflow changes, cloud queries, spend, DNS, deployment, or Platform Operations activation? | `NO` |
| Are the material risks accepted or remediated? | `NO — P1-R01 through P1-R10 remain open inputs to later Phase 1 owner contributions.` |
| Is Phase 2 implementation unblocked? | `NO — separate Phase 1 closure, Founder authorization, GOA, and Acceptance remain mandatory.` |

Recommended routing after independent acceptance: issue P1-WC02 only to INST-011 Product Owner for
operational outcomes, SLO priorities, and the required story model. Architecture, security, data,
implementation, deployment, and activation decisions remain outside P1-WC02.

## Learning Record

| Field | Value |
|---|---|
| `institution_id` | INST-009 |
| `goal_id` | GOAL-006 |
| `record_id` | LR-GOAL-006-INST-009-M1-01 |
| `record_type` | Learning Record |
| `produced_at` | 2026-08-13T09:10:33Z |
| `improvement_signal` | Earlier draft inventory treated repository declarations as live proof, asserted absent artifacts that exist, used incorrect Institution mappings, and expanded inventory into target design. |
| `learning` | Inventory evidence must cite exact artifacts, distinguish declaration from execution, limit absence claims to searched surfaces, and route remediation to the owning office without inventing the solution. |
| `practice_change` | Future platform inventories will use the five evidence classes in this record and hash-pin only individually validated reuse candidates. |
