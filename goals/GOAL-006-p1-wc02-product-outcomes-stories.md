# GOAL-006 P1-WC02 Product Outcomes, SLO Priorities, And Story Model

## Record Control

| Field | Value |
|---|---|
| `institution_id` | INST-011 |
| `goal_id` | GOAL-006 |
| `record_id` | CR-GOAL-006-INST-011-01 |
| `record_type` | Contribution Record |
| `go_authorization` | GOA-GOAL-006-INST-011-01 |
| `work_component` | P1-WC02 — Operational Outcomes, SLO Priorities, And Story Model |
| `produced_at` | 2026-08-13T09:26:16Z |
| `source_commit` | `65959848797f77986b96b19eeb62e4ea87f5a474` |
| `status` | ACCEPTED — R-108 / CR-GOAL-006-INST-002-03 |

This Product Owner contribution defines value, outcome priority, and the minimum complete story
model. It does not choose architecture, security controls, data design, tools, SKUs, numeric SLOs,
implementation, DNS, cloud resources, or Platform Operations activation. The Founder Session
Directive and FR-001 through FR-056 remain controlling.

## Value And Outcome Order

| Priority | Customer or operator outcome | Observable proof expected from later owners |
|---|---|---|
| 1 | Customers can reach the intended environment and complete critical journeys reliably. | Availability and customer-journey SLIs, external synthetics, qualified environment evidence. |
| 2 | A release is built once, qualified, promoted as the same immutable digest, and safely recovered. | Digest chain, gate evidence, deployment health, rollback and recovery results. |
| 3 | Service, dependency, release, and constitutional health are visible before customer harm grows. | OTel signals, Evidence First and Emergency Stop metrics, alerts, daily health evidence. |
| 4 | Public exposure, identity, secrets, tenant data, and the software supply chain are protected. | Threat-model controls and automated security evidence; internal services remain unreachable publicly. |
| 5 | Durable state can be backed up, restored, migrated, and recovered without unsafe data reuse. | Approved RPO/RTO, restore drills, migration checks, retention and no-production-data evidence. |
| 6 | Approved performance and resilience targets hold under expected and degraded load. | Load, cold-start, saturation, failover, dependency-outage, and recovery evidence. |
| 7 | Cloud cost is attributable, bounded by approved thresholds, and acted on without destroying required state. | Cost model, budgets, anomaly evidence, safe JIT lifecycle, escalation and monthly review. |
| 8 | An accepted and activated operator can run the capability through machine-verifiable procedures. | Runbook simulations, authority checks, incident exercise, handover acceptance, retained action evidence. |

This order applies FR-002. A lower-priority optimization may not weaken a higher-priority customer,
constitutional, security, or recovery outcome.

## SLO Priority Framework

P1-WC02 sets the order and decision rules, not the numeric targets. P1-WC03 through P1-WC09 must
propose measurable values using workload, architecture, risk, and cost evidence. The Founder owns
protected production, cost-above-ceiling, DNS, and activation decisions.

| Priority | SLO/SLI family | Minimum definition required | Decision state and owner |
|---|---|---|---|
| Constitutional floor | Emergency Stop and Evidence First correctness/latency | End-to-end SLI, percentile/window, breach condition, immediate halt/escalation, CCT evidence | Existing constitutional limits control; INST-002 verifies, Founder decides any protected change. |
| Customer access | Web/API critical-journey availability | Journey, environment, measurement window, exclusions, error budget, synthetic signal | Numeric target pending INST-011 proposal informed by INST-009/QA evidence; production commitment is Founder-protected. |
| Deployment safety | Promotion success and rollback/recovery | Digest continuity, gate success, failed-release detection time, rollback success/time | Target pending INST-009 and QA; production gate remains Founder-protected. |
| Service health | Per-service and dependency availability/errors/saturation | Service boundary, RED/saturation signals, dependency treatment, alert and escalation | Target pending INST-009 and INST-005. |
| Data durability | Backup success, restore success, RPO, RTO, migration safety | Data class/environment, retention, restore test, loss/recovery windows | Target pending INST-006; production residual risk requires Founder decision. |
| Security | Unauthorized exposure/access and critical supply-chain findings | Denial/containment signals, vulnerability policy, identity/certificate/secret health | Control thresholds pending INST-007; exceptions require accountable risk acceptance. |
| Performance | API latency/throughput, startup, and scaling | Expected load, percentile/window, cold/warm state, capacity and degradation | Target pending INST-009, INST-005, and QA. |
| Cost | Environment spend, forecast, anomaly, and safe shutdown | Currency, environment, warning/block thresholds, protected-state behavior | Existing constitutional ceilings remain constraints; detailed thresholds pending INST-009 and Founder where protected. |
| Operations | Detection, acknowledgement, response, recovery, and escalation | Incident class, autonomous boundary, human escalation, evidence retention | Target pending Platform Operations candidate and INST-011; activation is Founder-protected. |

Every accepted SLO must include its SLI formula, measurement source, window, error budget, warning and
breach thresholds, owner, automated response boundary, escalation, retention, redaction, cost, and
qualification test. Unknown values are package gaps, not zero or implied acceptance.

## Epic Model

| Epic | Outcome | Primary owner | Phase 1 dependency | Risks covered |
|---|---|---|---|---|
| E-01 Environment And Delivery Architecture | Reproducible Demo/UAT/Production lifecycle and immutable delivery | INST-009 | P1-WC03 | P1-R01, R02, R04, R05, R08, R10 |
| E-02 Deployable Component Topology | Explicit placement, boundaries, dependencies, health, and degradation | INST-005 | P1-WC04 | P1-R06, R10 |
| E-03 Security And Supply Chain | Least-privilege identity, protected ingress/secrets, verified artifacts | INST-007 | P1-WC05 | P1-R02, R03, R04, R06 |
| E-04 Data Durability And Recovery | Isolated non-production data and qualified backup/restore/migration | INST-006 | P1-WC06 | P1-R03, R07, R10 |
| E-05 Feasibility And Qualification | Implementable package with deterministic functional and resilience proof | INST-010 plus independent QA capability | P1-WC07/P1-WC08 | P1-R01 through R10 |
| E-06 Operations And Handover | Safe, bounded, evidenced autonomous operation | Platform Operations candidate, reviewed by INST-004 | P1-WC09/P1-WC10 | P1-R08, R09, R10 |
| E-07 Integrated Phase 2/3 Delivery | Traceable implementation and deployment contracts with protected stops | INST-011 | P1-WC11/P1-WC12 | P1-R01 through R10 |

The repository has no registered QA or Platform Operations Institution ID. INST-013 must resolve the
accountable QA institution before issuing P1-WC08. Platform Operations remains a draft candidate and
may contribute requirements but cannot accept live responsibility before review and Founder activation.

## Story Cost Convention

Each story below includes a Product Owner effort range, not a cloud or procurement promise. Until
the specialist owner supplies a priced design, monetary fields use this complete FR-045 frame:

`INR: pending specialist design; underlying Azure billing currency: USD pending current rate;
pricing date: 2026-08-13 baseline, refresh at owner review; region: Central India unless an approved
design changes it; assumptions: no cloud creation in Phase 1 and existing repository/tooling reused
where valid; taxes: excluded; confidence range: low / not yet priceable.`

### E01-S01 — Environment, JIT, IaC, Delivery, Reliability, And Cost Design

| FR-027 field | Value |
|---|---|
| ID/value | `E01-S01`. Enable repeatable Demo/UAT qualification and minimum safe Production delivery without idle waste or per-environment rebuilds. |
| Owning Institution | INST-009 Platform Architect |
| Scope/exclusions | Produce P1-WC03: environment topology, lifecycle/JIT, Terraform/state layout, immutable promotion, observability, scaling, continuity, DR and cost design, including six required conclusion tables. Excludes implementation, provider action, DNS, spend, and production approval. |
| Dependencies | Accepted P1-WC01 and P1-WC02; Founder directive; FR-020, FR-021, FR-028 through FR-045; P1-R01, R02, R04, R05, R08, R10. |
| Basis | Accepted ADR reuse records RR-GOAL-006-01 through RR-GOAL-006-06 are partial constraints, not proof of completeness. |
| Security/constitutional obligations | Preserve internal-only services, immutable digest promotion, OIDC/no long-lived Azure credentials, durable state during shutdown, cost floors, Evidence First, Human Override, and phase stops. Route security/data decisions. |
| Acceptance | Owner-reviewed design answers every assigned Founder question, includes alternatives/evidence, measurable proposed SLOs, complete cost assumptions, risk/decision mapping, and no unresolved contradiction with P1-WC01. |
| Automated tests | Specify Terraform/workflow static tests, policy/security scans, digest-chain checks, lifecycle/recovery tests, cost-control tests, and observability contract tests for Phase 2/3. No tests run under this story. |
| Evidence | P1-WC03 contribution, diagrams, decision/reuse records, cost model, six conclusion tables, assumptions, rejected alternatives, and owner review. |
| Rollback/recovery | Design must define configuration rollback, failed-promotion recovery, state protection, safe lifecycle recovery, and exit paths for provider-specific choices. |
| Size | Product Owner range: `XL`, 10-15 specialist working days; INST-009 must re-estimate after design decomposition. |
| One-time cost | FR-045 convention above; pending INST-009 design and implementation estimate. |
| Monthly cost | FR-045 convention above; pending environment/SKU/lifecycle design. |
| Operational burden | Pending INST-009 and Platform Operations analysis; must quantify routine time, alerts, exceptions, and specialist dependency. |
| Phase | Phase 1 design. Result feeds separately authorized Phase 2 implementation and Phase 3 deployment WCs. |

### E02-S01 — Deployable Component And Integration Topology

| FR-027 field | Value |
|---|---|
| ID/value | `E02-S01`. Ensure every deployable component has an explicit, testable placement and dependency contract. |
| Owning Institution | INST-005 Solution Architect |
| Scope/exclusions | Produce P1-WC04 component placement, public/internal boundaries, ports/protocols, configuration, health, dependencies, failure/degradation, and promotion contracts. Excludes cloud resource selection changes, security approval, code, and deployment. |
| Dependencies | Accepted E01-S01/P1-WC03; P1-WC01 source/API/Compose/Terraform findings; FR-008, FR-009, FR-020 through FR-023; P1-R06, R10. |
| Basis | Existing API contracts and accepted service/protocol ADRs, subject to explicit compatibility review. |
| Security/constitutional obligations | CE and internal-only services remain non-public; tenant and evidence boundaries remain explicit; unsafe dependency loss must fail safely. |
| Acceptance | Every deployed component has owner, image/config source, ingress, protocol, health contract, dependencies, data access, failure behavior, observability, promotion/config boundary, and unresolved decision list. |
| Automated tests | Specify contract, health, configuration, network reachability, dependency failure, and degradation tests for QA. |
| Evidence | P1-WC04 contribution, topology views, interface matrix, configuration/dependency contracts, and INST-005 review. |
| Rollback/recovery | Define compatible configuration rollback and dependency degradation/recovery expectations without overwriting platform or data recovery design. |
| Size | Product Owner range: `L`, 5-8 specialist working days; INST-005 must re-estimate. |
| One-time cost | FR-045 convention above; pending INST-005 topology and INST-010 feasibility. |
| Monthly cost | FR-045 convention above; component cost allocated by INST-009 after placement. |
| Operational burden | Pending component/dependency count and health model; quantify manual interventions and provider dependencies. |
| Phase | Phase 1 design; downstream implementation/deployment remain separately authorized. |

### E03-S01 — Security Architecture, Identity, Exposure, And Supply Chain

| FR-027 field | Value |
|---|---|
| ID/value | `E03-S01`. Prevent unauthorized access, secret leakage, public bypass of constitutional controls, and untrusted artifact promotion. |
| Owning Institution | INST-007 Security Architect |
| Scope/exclusions | Produce P1-WC05 identity/OIDC/RBAC, ingress/egress/private communication, TLS/DNS/certificates, secrets, supply chain, WAF/rate-limit evidence, break-glass, threat model, and tests. Excludes implementation, DNS action, credential creation, and risk acceptance outside Decision Space. |
| Dependencies | Accepted P1-WC01 through P1-WC04; FR-008, FR-009, FR-031 through FR-038, FR-042; P1-R02, R03, R04, R06. |
| Basis | ADR-014 partial reuse plus controlling Founder security requirements; current repository divergence is evidence, not an accepted pattern. |
| Security/constitutional obligations | Least privilege, workload federation, managed secret references, no secrets in images/state/logs, protected internal services, tenant isolation, Human Override, and auditable break glass. |
| Acceptance | Threat model covers assets/actors/trust boundaries/abuse cases/controls/residual risks; each control has owner, enforcement point, automated test, evidence, rotation/recovery, and exception authority. |
| Automated tests | Specify IaC/security policy, OIDC/RBAC denial, secret leakage, ingress/CORS/TLS, certificate expiry, rate/WAF where justified, SBOM/signature/attestation, vulnerability and DAST tests. |
| Evidence | P1-WC05 contribution, threat model, control matrix, identity/RBAC matrix, supply-chain policy, residual-risk register, and independent security review plan. |
| Rollback/recovery | Define identity/secret/certificate rotation, revoked-access recovery, failed-security-change rollback, break-glass expiry, and compromised-artifact response. |
| Size | Product Owner range: `XL`, 8-12 specialist working days; INST-007 must re-estimate. |
| One-time cost | FR-045 convention above; pending selected controls and implementation estimate. |
| Monthly cost | FR-045 convention above; pending managed security/service choices. |
| Operational burden | Pending INST-007; quantify rotations, access reviews, vulnerability triage, certificate response, and exception handling. |
| Phase | Phase 1 design; Phase 2 implementation and Phase 3 activation remain unauthorized. |

### E04-S01 — Data Isolation, Backup, Restore, Retention, And Migration

| FR-027 field | Value |
|---|---|
| ID/value | `E04-S01`. Protect customer, constitutional, and operational data across lifecycle, failure, migration, and recovery. |
| Owning Institution | INST-006 Data Architect |
| Scope/exclusions | Produce P1-WC06 environment data model, masking/no-production-data rules, Terraform/database state protection, backup/restore/retention/migration, RPO/RTO recommendations and tests. Excludes provisioning, copying production data, and Founder acceptance of production residual risk. |
| Dependencies | Accepted P1-WC01, P1-WC03, P1-WC04; FR-023, FR-028 through FR-030, FR-038, FR-043; P1-R03, R07, R10. |
| Basis | ADR-003 and ADR-011 where applicability is validated; current absence of recovery evidence controls scope. |
| Security/constitutional obligations | No production customer data in Demo/UAT; tenant isolation; encryption and least privilege; durable audit/evidence/state survives shutdown; destructive migration controls. |
| Acceptance | Every data/state class has environment boundary, authority, retention, backup, restore, RPO/RTO proposal, migration/rollback, masking, deletion, test, evidence, and unresolved risk. |
| Automated tests | Specify cross-environment/tenant denial, backup integrity, point-in-time restore, recovery timing, migration forward/rollback, retained-state lifecycle, and no-production-data tests. |
| Evidence | P1-WC06 contribution, data/state inventory, flow/isolation model, backup/restore design, RPO/RTO rationale, migration policy, and drill plan. |
| Rollback/recovery | Define tested restore, migration reversal/forward-fix, corruption containment, state recovery, and evidence preservation. |
| Size | Product Owner range: `L`, 5-8 specialist working days; INST-006 must re-estimate. |
| One-time cost | FR-045 convention above; pending data architecture and drill implementation. |
| Monthly cost | FR-045 convention above; pending storage, backup, retention, and recovery design. |
| Operational burden | Pending INST-006; quantify backup verification, restore drills, migrations, retention review, and data-access review. |
| Phase | Phase 1 design; no data movement or provider action authorized. |

### E05-S01 — Implementation And Pipeline Feasibility

| FR-027 field | Value |
|---|---|
| ID/value | `E05-S01`. Convert approved specialist designs into a deterministic, testable implementation decomposition without coding early. |
| Owning Institution | INST-010 Runtime Implementation Professional |
| Scope/exclusions | Produce P1-WC07 toolchain prerequisites, feasibility findings, implementation dependencies, Docker/C-080 test strategy, and Phase 2 decomposition. Excludes code, runnable infrastructure, specialist decision replacement, self-review, and deployment. |
| Dependencies | Accepted P1-WC03 through P1-WC06; FR-025, FR-034 through FR-038, FR-048 through FR-050; all P1 risks. |
| Basis | Approved owner designs and repository toolchain; unsupported assumptions are returned to the owning architect. |
| Security/constitutional obligations | Preserve approved boundaries, C-080 Docker execution, Evidence First, separation of author/reviewer, no secret material, no unauthorized cloud action. |
| Acceptance | Every implementation unit has inputs/outputs/dependencies/owner/files/tests/evidence/rollback/estimate; toolchain checks are reproducible; infeasible or ambiguous designs are explicitly blocked. |
| Automated tests | Specify Docker-based static, unit, integration, contract, CCT, IaC/workflow, security, migration, promotion, recovery, and evidence checks. |
| Evidence | P1-WC07 contribution, prerequisite results, implementation dependency graph, Phase 2 task decomposition, test command map, and feasibility blockers. |
| Rollback/recovery | Each planned implementation unit includes reversible change or explicit forward-recovery strategy and evidence checkpoint. |
| Size | Product Owner range: `L`, 5-8 specialist working days; INST-010 must re-estimate. |
| One-time cost | FR-045 convention above; labor/procurement estimate pending decomposition. |
| Monthly cost | FR-045 convention above; implementation itself creates no authorized cloud spend. |
| Operational burden | Pending decomposition; identify new maintenance, credentials, schedules, reviews, and failure-response duties. |
| Phase | Phase 1 feasibility only; Phase 2 requires explicit current-session Founder authorization. |

### E05-S02 — Qualification, Performance, Resilience, Promotion, And DR Evidence

| FR-027 field | Value |
|---|---|
| ID/value | `E05-S02`. Prove the capability meets customer, constitutional, security, recovery, performance, and promotion outcomes before production. |
| Owning Institution | QA capability; accountable Institution ID must be resolved before GOA |
| Scope/exclusions | Produce P1-WC08 automated qualification matrix, environments, entry/exit gates, test data, load/cold-start/recovery targets, promotion/rollback/chaos/security/CCT/DR evidence. Excludes implementation, self-validation by implementers, cloud execution, and production approval. |
| Dependencies | Accepted P1-WC02 through P1-WC07; FR-025, FR-034 through FR-041, FR-050, FR-052, FR-053; all P1 risks. |
| Basis | Approved owner designs and Product Owner SLO framework; no invented target is accepted. |
| Security/constitutional obligations | Independent evidence, tenant-safe test data, Evidence First, Emergency Stop, no-production-data controls, immutable digest chain, Human Override, and non-bypassable failures. |
| Acceptance | Matrix covers every requirement/risk/control/SLO with environment, setup, automation, threshold, expected result, evidence, owner, failure class, retry/escalation, and promotion effect. |
| Automated tests | The deliverable is the complete automated test plan: functional, integration, contract, CCT, security, performance, resilience, rollback, restore, DR, lifecycle, cost, drift, and operations acceptance. |
| Evidence | P1-WC08 contribution, traceability matrix, fixtures/data policy, environment prerequisites, expected artifacts, independence plan, and gate decision rules. |
| Rollback/recovery | Failed qualification blocks promotion; preserve evidence and environment for diagnosis; define safe retry/reset and previous-digest recovery. |
| Size | Product Owner range: `XL`, 8-12 specialist working days; accountable QA owner must re-estimate. |
| One-time cost | FR-045 convention above; pending test tooling and environment-runtime estimate. |
| Monthly cost | FR-045 convention above; pending qualification frequency and active environment time. |
| Operational burden | Pending QA/INST-009; quantify suite duration, triage, flaky-test policy, evidence retention, and scheduled drills. |
| Phase | Phase 1 test architecture; Phase 2 automation; Phase 3 authorized qualification. |

### E06-S01 — Operational Architecture, Policies, And Handover Readiness

| FR-027 field | Value |
|---|---|
| ID/value | `E06-S01`. Enable a bounded operator to run releases, environments, incidents, cost, recovery, and reporting safely and repeatably. |
| Owning Institution | Platform Operations candidate; INST-004 owns readiness review; Founder owns activation |
| Scope/exclusions | Produce P1-WC09 runbooks/checklists, alerts, incident/change/release/access/vulnerability operations, autonomous boundaries and handover tests; P1-WC10 reviews spec/permissions/readiness. Excludes activation, live permissions, cloud action, and substitution for specialist decisions. |
| Dependencies | Accepted P1-WC02 through P1-WC08; FR-018, FR-023, FR-024, FR-041, FR-054; P1-R08, R09, R10. |
| Basis | Draft Platform Operations specification and accepted specialist designs, subject to INST-004 review and Founder decision. |
| Security/constitutional obligations | Least privilege, bounded autonomy, Human Override, evidence before action, emergency halt, escalation, retained audit, no self-activation or self-approval. |
| Acceptance | Machine-verifiable procedures cover activation/shutdown, release observation, diagnosis/retry/rollback/escalation, cost, backup/restore, drift, certificates/rotation, health/cost reports, incidents and access; simulations prove boundaries. |
| Automated tests | Specify runbook schema/lint, permission denial, lifecycle, release/rollback, incident, cost, backup/restore, drift, certificate, escalation, audit, and supervised handover simulations. |
| Evidence | P1-WC09 contribution, policy/runbook set, authority matrix, alert/action map, simulations, P1-WC10 independent readiness review, unresolved activation blockers. |
| Rollback/recovery | Revoke permissions and return to supervised/manual operation on boundary breach, failed evidence, unsafe automation, or Founder halt. |
| Size | Product Owner range: `XL`, 10-15 working days across candidate and reviewers; owners must re-estimate. |
| One-time cost | FR-045 convention above; pending policy automation and integration design. |
| Monthly cost | FR-045 convention above; pending operational telemetry/tooling and model-runtime design. |
| Operational burden | Core acceptance dimension; candidate must quantify routine daily/monthly work, incident load, human escalations, model calls, and specialist support. |
| Phase | Phase 1 contribution/readiness only; activation is a separate Founder-protected Phase 3 act. |

### E07-S01 — Integrated Phase 2/3 Work Contracts And Authorization Package

| FR-027 field | Value |
|---|---|
| ID/value | `E07-S01`. Give the Founder one traceable, costed, reviewable package for deciding implementation and later deployment. |
| Owning Institution | INST-011 Product Owner, with specialist owner reviews and fresh INST-002 clearance |
| Scope/exclusions | Produce P1-WC11 integrated package and proposed Phase 2/3 Work Components; P1-WC12 supplies independent review, protected decisions, Founder actions, and exact authorization boundary. Excludes implementation, cloud/DNS action, activation, approval substitution, and merge. |
| Dependencies | Accepted P1-WC01 through P1-WC10; FR-019 through FR-056; all P1 risks and owner decisions. |
| Basis | Founder Session Directive, normalized FR baseline, GEOM, vNext standard, accepted owner contributions and reviews. |
| Security/constitutional obligations | Full traceability, evidence provenance, independence, protected decisions, cost truth, phase stops, no self-review/merge, and explicit original-directive retention in the Phase 1 PR. |
| Acceptance | Every FR and risk maps to accepted design/story/test/evidence/owner/phase; six exact conclusion tables complete; estimates reviewed; blockers and Founder decisions explicit; Phase 2/3 WCs are dependency-safe and independently cleared. |
| Automated tests | Deterministic checks for all FR-001..056, every FR-027 field, reuse records, record chronology, owner/review independence, six table schemas, phase exclusions, links/hashes, and PR retention statement. |
| Evidence | P1-WC11 integrated contribution, owner reviews, completeness/dependency ledgers, proposed WCs, P1-WC12 clearance or blocker, Founder decision records, Phase 1 draft PR. |
| Rollback/recovery | Reject or amend only affected contribution/WC; preserve prior accepted evidence; no implementation begins until a complete authorized boundary exists. |
| Size | Product Owner range: `XL`, 8-12 working days plus review windows; re-estimate after P1-WC10. |
| One-time cost | FR-045 convention above; consolidated estimate pending all specialist priced designs. |
| Monthly cost | FR-045 convention above; consolidated baseline/active-use ranges pending all specialist models. |
| Operational burden | Consolidate all routine, exception, review, incident, model, and specialist burdens; unresolved burden blocks Phase 1 closure. |
| Phase | Phase 1 closure and authorization package only. Phase 2/3 remain separately authorized. |

## Completeness Ledger

| Requirement | Status | Evidence or required follow-up |
|---|---|---|
| FR-002 ordered customer value | COMPLETE | Value And Outcome Order |
| SLO priorities and decision ownership | COMPLETE FOR PRODUCT SCOPE | SLO Priority Framework; numeric proposals remain owner work |
| FR-025 coherent epics/stories/dependencies/estimates/acceptance | COMPLETE FOR P1-WC02 | Seven epics and eight stories; specialist re-estimation required |
| FR-027 all fields on every story | COMPLETE | Each story has all 15 required fields |
| FR-045 cost truth | COMPLETE AT UNKNOWN-STAGE | Full currency/date/region/assumption/tax/confidence frame; no fabricated prices |
| P1-R01 through P1-R10 | COVERED | Epic table and story dependencies; risks remain open |
| Architecture/security/data/implementation decisions | NOT MADE | Routed to INST-009/005/007/006/010 and QA capability |
| QA accountable Institution | OPEN ROUTING GAP | INST-013 must resolve before P1-WC08 GOA |
| Platform Operations activation | PROTECTED AND OPEN | Draft candidate only; INST-004 review and Founder activation required |
| Phase 2/3 authority | NOT GRANTED | Explicit exclusions in every story and controlling plan |

## Product Owner Acceptance Recommendation

Accept P1-WC02 when independent review confirms that the value order, SLO framework, stories, cost
truth, owner routing, and phase boundaries are complete and do not invent specialist decisions.
Acceptance permits routing P1-WC03 to INST-009 only. It does not accept any numeric SLO, cost,
architecture, implementation, cloud action, DNS decision, production decision, or activation.
