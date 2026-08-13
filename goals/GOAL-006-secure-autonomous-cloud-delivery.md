# GOAL-006 — Secure Autonomous Cloud Delivery Capability

**Status:** UNDERSTOOD — CLASSIFICATION AND PLAN PROPOSED; NO GROOMING AUTHORIZATION
**Registrant:** Yogesh Khandge, Founder (INST-001)
**Registered:** 2026-08-13
**Work Contract:** WC-071
**Owning outcome:** WAOOAW can deliver and operate customer-accessible services through secure,
reliable, recoverable, observable, cost-controlled Azure environments with immutable promotion and
bounded autonomous operations.
**Constitutional basis:** C-001, C-007, C-023, C-041, C-059, C-062, C-063, C-065, C-067, C-070,
C-071, C-073, C-076, C-079, C-080; GEOM; accepted cloud and delivery ADRs
**Founder source directive:** `goals/GOAL-006-founder-session-directive.md`

## G-1 — Registration

| Registration field | Value |
|---|---|
| Goal ID | GOAL-006 |
| Registrant | Yogesh Khandge, Founder (INST-001) |
| Registered | 2026-08-13 |
| Initial priority | Elevated; subject to G-3 classification review |

### Original Founder Goal — Preserved

> Establish an industry-grade, secure, cost-controlled, and autonomously operated cloud delivery
> capability for WAOOAW.

Registration acknowledges the obligation. It does not authorize execution, expenditure,
infrastructure changes, DNS changes, deployment, or activation of Platform Operations.

## G-2 — Goal Understanding Record

| Attestation field | Value |
|---|---|
| `institution_id` | INST-013 |
| `goal_id` | GOAL-006 |
| `record_id` | GUR-GOAL-006-INST-013-01 |
| `record_type` | Understanding Record |
| `produced_at` | 2026-08-13T12:01:00+00:00 |
| Registrant | Yogesh Khandge, Founder (INST-001) |
| Reviewer | Fresh Constitutional Analyst (INST-002), not yet routed |

### What The Goal Actually Means

This is an operational capability outcome, not merely an infrastructure build. Completion requires
WAOOAW to prove that one immutable release can be packaged once, promoted safely through demo, UAT,
and production, observed and recovered, operated within explicit cost and authority limits, and
handed to an independently reviewed and Founder-activated Platform Operations agent.

The Goal has three mandatory sequential phases:

1. Discovery, architecture, and grooming establish verified current-state evidence, resolve or
   route owner decisions, quantify cost and reliability, and produce reviewed Work Components.
2. Implementation turns the approved package into tested version-controlled Terraform, workflows,
   policies, automation, observability, and operational controls without creating cloud resources.
3. Azure deployment and handover create and qualify environments only after separate Founder
   authorization for cloud creation, DNS, production activation, and expenditure.

Customer value is the controlling tiebreaker: reliable access, safe deployment, service health,
security, recoverability, performance, and controlled cloud cost. Process artifacts are justified
only when they enable implementation, operation, risk control, or independent verification.

### What This Goal Is Not

- It is not authorization to deploy, spend Azure funds, change DNS, or expose internal services.
- It is not authority for INST-013 to select technical designs or contribute architecture.
- It is not a Kubernetes, Nexus, Grafana, or tooling-modernization initiative.
- It is not permission to rebuild release images per environment or bake secrets into images.
- It does not treat Platform Operations as active before review, correction, acceptance, and
  Founder activation.
- It does not permit Phase 2 or Phase 3 to start early or run in parallel with an incomplete prior
  phase.

### Outcome Success Criteria

| ID | Evidence-backed success condition |
|---|---|
| SC-01 | A reviewed current-state inventory identifies reusable approved assets, verified gaps, owners, and stale or conflicting evidence. |
| SC-02 | Demo, UAT, and production target architectures define isolation, ingress, internal-only services, identity, data, security, reliability, portability, and cost boundaries. |
| SC-03 | Demo and UAT have tested just-in-time lifecycle controls that preserve durable data, audit evidence, state, secrets, DNS zones, and recovery material. |
| SC-04 | One build produces an immutable signed image digest with provenance, SBOM, scan evidence, retention, promotion, and rollback records through all environments. |
| SC-05 | CI/CD and IaC gates are least-privilege, OIDC-based, concurrency-safe, drift-aware, reproducible, auditable, and halted by constitutional or security failure. |
| SC-06 | OpenTelemetry-based observability proves customer journeys, service/dependency health, constitutional metrics, release health, SLOs, alerts, cost, and redaction. |
| SC-07 | Backup, restore, rollback, disaster recovery, provider-outage, and continuity controls meet approved RPO/RTO and pass repeatable qualification. |
| SC-08 | Security architecture and threat evidence prove environment isolation, restrictive CORS, TLS, secret/certificate rotation, supply-chain controls, RBAC, and protected production access. |
| SC-09 | Cost evidence states INR and Azure billing currency, pricing date, region, assumptions, tax treatment, confidence range, budgets, anomaly thresholds, and shutdown controls. |
| SC-10 | Phase 1 produces reviewed Phase 2 and Phase 3 Work Components with complete story fields, dependencies, tests, evidence, estimates, rollback, cost, burden, and phase. |
| SC-11 | Phase 2 implementation passes Docker-based reproducible validation, independent architecture/security/constitutional review, and cost-plan review in an unmerged PR. |
| SC-12 | Phase 3 qualifies demo, UAT, and production in order using identical approved digests and produces final security, reliability, performance, cost, and evidence reports. |
| SC-13 | Platform Operations is independently reviewed, corrected, accepted, Founder-activated, and proves every handover capability within its approved Decision Space. |
| SC-14 | No Constitutional Engine or internal-only service is directly internet-exposed, and Evidence First plus Emergency Stop are verified after deployment. |
| SC-15 | Founder-reserved decisions, costs, DNS changes, production activation, agent activation, approvals, and merge remain protected throughout the Goal Journey. |

### Clarifications And Protected Decisions

No clarification blocks production of this proposed plan. The following decisions explicitly block
dependent owner contributions or later phases until resolved by the named authority:

| Decision | Current treatment | Protected owner |
|---|---|---|
| Demo/UAT/production URL and API mapping | PROPOSED only; no DNS decision | Founder |
| Primary Azure region and disaster-recovery region | Owner recommendation required | Platform Architect; Founder if cost/production boundary changes |
| Subscription/resource-group and data-service separation | Owner recommendations required | Platform, Security, and Data Architects |
| Production SLO, RPO, RTO, capacity, and cost ceiling | Recommendations required; no implied acceptance | Product Owner and specialist owners; Founder approves protected thresholds |
| Public ingress, Front Door/CDN/WAF/API gateway | Evidence-based owner decision; no tool assumed | Platform and Security Architects |
| Platform Operations activation | DRAFT and inactive | Founder after independent acceptance |
| Azure creation, expenditure, DNS, and production activation | Prohibited in Phases 1 and 2 | Founder |

## G-3 — Provisional Goal Classification

| Attestation field | Value |
|---|---|
| `institution_id` | INST-013 |
| `goal_id` | GOAL-006 |
| `record_id` | GCL-GOAL-006-INST-013-01 |
| `record_type` | Classification Record |
| `produced_at` | 2026-08-13T12:02:00+00:00 |
| `status` | PROVISIONAL — requires fresh INST-002 review and Founder approval before routing |

| Dimension | Classification | Basis |
|---|---|---|
| Scope | Cross-domain | Product, platform, solution, security, data, runtime feasibility, QA, operations, constitutional review, and Founder decisions are inseparable. |
| Nature | Design | The currently requested and authorized stage is discovery, architecture, and implementation grooming; Build and Operate are later separately authorized phases. |
| Risk | Constitutional | Customer access, Evidence First, Emergency Stop, production authority, security, data, immutable evidence, agent activation, and expenditure create constitutional consequences. |
| Urgency | Elevated | Cloud delivery is required for customer value and safe production, but no live incident justifies Emergency preemption. |

**Proposed priority:** P2 — Constitutional Risk. No GO Authorization may be issued until a fresh
Constitutional Analyst completes the R2-10 challenge window/readiness review and the Founder
explicitly approves this classification and `GEP-GOAL-006-INST-013-01`.

## Founder Requirement Baseline — Controlling For Grooming

This section retains the Founder's instructions as stable requirements. Phase 1 grooming must
trace every deliverable, story, Work Component, review, and acceptance record to these IDs. Any
omission is a package defect; any semantic change requires Founder acknowledgement.

The complete human-readable source is `goals/GOAL-006-founder-session-directive.md`. This
normalized baseline supports deterministic traceability and may not narrow that source directive.

### Capability And Value

| ID | Requirement |
|---|---|
| FR-001 | Cover Azure architecture/infrastructure, Docker packaging, IaC, GitHub Actions CI/CD, immutable demo→UAT→production promotion, automated lifecycle, observability/incident/recovery, security/secrets/certificates/DNS/isolation, cost/capacity/reliability/performance, and Platform Operations handover. |
| FR-002 | Prioritize reliable customer access, deployment safety, service health, security, recoverability, performance, and controlled cloud cost. |
| FR-003 | Create no artifact solely for process compliance; every artifact must enable implementation, operation, risk control, or independent verification. |

### Proposed Addresses And Exposure Boundaries

| ID | Requirement |
|---|---|
| FR-004 | Treat `https://www.demo.waooaw.com` and `https://api.demo.waooaw.com` as proposed Demo addresses requiring Founder confirmation. |
| FR-005 | Treat `https://www.uat.waooaw.com` and `https://api.uat.waooaw.com` as proposed UAT addresses requiring Founder confirmation. |
| FR-006 | Treat `https://www.waooaw.com` and `https://api.waooaw.com` as proposed Production addresses requiring Founder confirmation. |
| FR-007 | The Founder owns `waooaw.com`; no DNS or production decision is implied by this record. |
| FR-008 | Use environment-specific subdomains, TLS, secure API ingress, restrictive CORS, workload identity, managed secrets, private internal communication, rate limiting, and justified WAF controls. |
| FR-009 | Never expose the Constitutional Engine or other internal-only services directly to the internet. |

### Phase And Ownership Controls

| ID | Requirement |
|---|---|
| FR-010 | Execute three sequential phases without combining or skipping: Phase 1 discovery/architecture/grooming; Phase 2 implementation; Phase 3 Azure deployment/handover. |
| FR-011 | Phase 1 studies actual business, constitutional controls, services, source layout, Docker topology, stores, dependencies, Terraform/Azure/workflows/security/ADRs/scripts/observability/cost/operations-agent evidence. |
| FR-012 | Reuse approved decisions where suitable; specifically evaluate Azure-first, Container Apps, PostgreSQL, Keycloak, Temporal, Azure Monitor/Application Insights, OpenTelemetry, Key Vault, GitHub Actions, GHCR, Docker, and Terraform. |
| FR-013 | Do not introduce Kubernetes, Nexus, Grafana, or another platform without evidence of a material gap and net operational value. |
| FR-014 | GHCR remains default under ADR-012 unless a material requirement proves it insufficient; replacement needs an architecture decision and migration analysis. |
| FR-015 | Route outcomes/stories to Product Owner; cloud/IaC/CI-CD/observability/reliability/DR/cost to Platform Architect; deployable topology to Solution Architect; security/threats to Security Architect; data isolation/backup/restore/retention/migration to Data Architect. |
| FR-016 | Route feasibility/pipeline needs to Runtime Implementation Professional or Platform IT Expert; qualification/performance/resilience/promotion tests to QA; runbooks/alerts/autonomous actions/handover to Platform Operations; independent compliance to Constitutional Analyst. |
| FR-017 | Founder retains protected decisions, costs above ceiling, production activation, DNS changes, and agent activation. |
| FR-018 | Platform Operations is draft and inactive; include minimum review, correction, acceptance, and Founder activation before live ownership. |

### Phase 1 Package

| ID | Requirement |
|---|---|
| FR-019 | Produce current-state inventory and verified gaps. |
| FR-020 | Produce target demo/UAT/production architecture and environment lifecycle/JIT policy. |
| FR-021 | Produce CI/CD immutable promotion and IaC architecture/repository layout. |
| FR-022 | Produce cloud security architecture/threat model and observability/operational architecture. |
| FR-023 | Produce backup, restoration, rollback, DR, continuity, incident, change, release, access, and vulnerability-management designs/policies. |
| FR-024 | Produce Platform Operations activation/handover plan. |
| FR-025 | Produce epics, stories, tasks, dependencies, estimates, acceptance criteria, Phase 2 Work Components, and Phase 3 deployment/qualification Work Components. |
| FR-026 | Produce risks, protected decisions, assumptions, Founder actions, cost model/thresholds, and independent review/authorization package. |
| FR-027 | Every story includes ID/value, owning Institution, scope/exclusions, dependencies, basis, security/constitutional obligations, acceptance, automated tests, evidence, rollback/recovery, size, one-time cost, monthly cost, operational burden, and phase. |

### Just-In-Time Environments

| ID | Requirement |
|---|---|
| FR-028 | Demo/UAT exist or consume material resources only when needed; evaluate scale-to-zero, schedules, workflow dispatch, PR/release triggers, TTL leases, Terraform lifecycle, retained foundations/data, database pause/serverless, backup/start health, unavailable-DNS behavior, startup target, inactivity shutdown, budgets/anomaly/emergency shutdown. |
| FR-029 | Automated shutdown never destroys durable data, audit records, Terraform state, Key Vault material, DNS zones, or required recovery evidence. |
| FR-030 | Production remains available at the smallest configuration satisfying customer safety, constitutional enforcement, backup, recovery, security, and approved service objectives; no unjustified single point of failure. |

### Immutable Promotion And CI/CD

| ID | Requirement |
|---|---|
| FR-031 | Build each release image once and promote the exact digest from source/CI/registry through demo qualification, UAT qualification/approval, production, and post-production verification; never rebuild for UAT/production. |
| FR-032 | Environment behavior comes only from reviewed configuration, managed identity, Key Vault references, feature controls, and environment settings; never bake environment secrets into images. |
| FR-033 | Define provenance, SBOM, signing, vulnerability scan, attestation, retention, rollback, and promotion evidence. |
| FR-034 | PR gates cover build, lint, unit, integration, contract, CCT, dependency/secret/SAST/container/IaC security checks. |
| FR-035 | Docker build uses deterministic tags and immutable digest recording; Terraform gates cover format, validate, lint, security scan, plan, approval, and apply. |
| FR-036 | Use GitHub deployment environments, least privilege, OIDC workload federation, and no long-lived Azure credentials. |
| FR-037 | Demo deploy runs smoke/CCT; UAT promotion requires qualification evidence; production promotion requires Founder-reserved authorization and low-risk blue-green or equivalent release. |
| FR-038 | Define explicit health rollback, audit retention, emergency halt, failure classes/retries/escalation, concurrency protection, drift detection/reconciliation, and tested DR workflows. |

### Observability And Operations

| ID | Requirement |
|---|---|
| FR-039 | OpenTelemetry is the instrumentation standard; evaluate Azure Monitor/Application Insights for logs, metrics, traces, events, dashboards, workbooks, and alerts. |
| FR-040 | Observe service/dependency/release health; Evidence First and Emergency Stop latency; customer journeys/outcomes; API RED/saturation/availability; databases, Temporal, Keycloak, Container Apps, certificates, DNS, queues, external providers, and cost. |
| FR-041 | Define SLOs, SLIs, error budgets, thresholds, escalation, tenant-safe correlation, PII/secret redaction, retention/cost controls, external synthetics, alert dedup/noise control, autonomous-response boundaries, daily health, and monthly reliability/cost review. |

### Architecture, Security, Data, Reliability, And Portability Decisions

| ID | Requirement |
|---|---|
| FR-042 | Resolve or route Azure primary/DR regions; subscription/resource-group separation; data-service sharing; network/private endpoints; public ingress; gateway/Front Door/CDN/WAF/DNS; managed certificates; GitHub/operations identity; Terraform state/locking/backup/access; secret rotation; production/break-glass access. |
| FR-043 | Resolve or route backup frequency/retention/RPO/RTO; masking and no production customer data in demo/UAT; capacity/scaling; sandbox/production external credentials; dependency/provider outage behavior; Azure portability and escape hatches. |

### Mandatory Conclusion Tables And Cost Truth

| ID | Requirement |
|---|---|
| FR-044 | End Phase 1 grooming with Component and Cost, Performance and Reliability, Delivery Tool Decision, Story and Delivery, Environment, and Risk and Decision summary tables using the exact Founder-specified columns. |
| FR-045 | Every monetary estimate states INR, underlying Azure billing currency, pricing date, region, assumptions, taxes included/excluded, and confidence range. |

### Phase Stops, Implementation, Deployment, And Handover

| ID | Requirement |
|---|---|
| FR-046 | Stop Phase 1 only after owner reviews, independent constitutional review, Founder-reserved decisions identified, Founder approval, and authorized Phase 2 Work Components; do not modify runnable infrastructure in Phase 1. |
| FR-047 | Start Phase 2 only with explicit current-session Founder implementation authorization and approved Phase 2 Work Components. |
| FR-048 | Phase 2 implements reusable Terraform/compositions/state/workflows/promotion/security/lifecycle/monitoring/budgets/DNS/certs/backup/DR/policy/runbooks/operations integration/tests as version-controlled artifacts. |
| FR-049 | All Phase 2 repository execution/testing follows C-080 Docker requirements; do not create or use a Python virtual environment. |
| FR-050 | Phase 2 ends with independent review, reproducible validation, security verification, cost-plan review, and an unmerged PR for Founder approval. |
| FR-051 | Start Phase 3 only after Phase 2 merge and explicit Founder authorization for cloud creation, DNS, and expenditure. |
| FR-052 | Phase 3 validates tenant/subscription/region/quotas/identities/budgets/DNS; establishes state/security; provisions and proves demo lifecycle/recovery/monitoring/cost; promotes identical digests to UAT; qualifies UAT; obtains approval; provisions minimum production; promotes and verifies production. |
| FR-053 | Phase 3 verifies DNS, TLS, headers, APIs, observability, backups, alerts, rollback, Emergency Stop, Evidence First, customer journeys, supervised operations, incident simulation, final cost/performance/reliability/security/evidence, and Founder production acceptance; never self-approve or self-merge. |
| FR-054 | Handover completes only when activated Platform Operations can safely activate/shut demo/UAT, observe releases, diagnose failures, respond/retry/rollback/escalate, enforce cost, verify/restore backups, detect drift, monitor cert/rotation, report health/cost, execute machine-verifiable runbooks, and retain action evidence. |
| FR-055 | Reuse approved architecture/evidence where valid; never invent authority, activate Platform Operations, spend, change DNS, deploy, or write implementation artifacts without owner and Founder decisions. |
| FR-056 | Retain this requirement baseline in Phase 1 grooming documentation and state that retention explicitly in the final Phase 1 PR. |
