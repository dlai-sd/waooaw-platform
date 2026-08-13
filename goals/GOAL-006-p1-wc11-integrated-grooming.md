# GOAL-006 P1-WC11 — Integrated Grooming Package And Phase 2/3 Work Components

## Record Control

| Attestation field | Value |
|---|---|
| `institution_id` | INST-011 — Product Owner |
| `goal_id` | GOAL-006 |
| `record_id` | CR-GOAL-006-INST-011-02 |
| `record_type` | Integrated Grooming Contribution |
| `go_authorization` | GOA-GOAL-006-INST-011-02 |
| `acceptance_record` | ACC-GOAL-006-INST-011-02 |
| `work_component` | P1-WC11 — Integrated Grooming Package And Phase 2/3 Work Components |
| `produced_at` | 2026-08-13 |
| `classification` | Design and grooming only |
| `authority` | Integrated documentation and downstream Work Component specification |
| `status` | PROPOSED — requires specialist owner review and P1-WC12 independent constitutional review |
| `implementation_authority` | NOT GRANTED |
| `cloud_or_live_authority` | NOT GRANTED |
| Governing source | Founder Session Directive and FR-001 through FR-056 |

This contribution integrates independently accepted Phase 1 owner decisions. It does not independently accept those decisions, validate live effectiveness, authorize implementation, query providers, create Azure resources, change DNS, incur expenditure, deploy, accept Production risk, activate Platform Operations, approve a PR, or merge.

## Integration Rule

1. Preserve accepted owner decisions by reference and retain their authority, evidence status, limitations, and protected-decision boundaries.
2. Identify conflicts, unresolved choices, stale evidence, and unknowns explicitly.
3. Never resolve a specialist unknown by Product Owner invention.
4. Repository declarations are not live proof. Recommendations and provisional targets are not accepted commitments.
5. A downstream Work Component may implement only accepted design within its authorized scope. Material design changes require a Dependency Impact Report and accountable-owner review.
6. Founder-protected decisions remain protected even when implementation prerequisites are otherwise complete.

## Accepted Inputs

| Input | Record | Review | Integrated status |
|---|---|---|---|
| Current-state inventory | CR-GOAL-006-INST-009-01 | R-107 | ACCEPTED; P1-R01, P1-R02, P1-R03, P1-R04, P1-R05, P1-R06, P1-R07, P1-R08, P1-R09, and P1-R10 retained |
| Product outcomes and stories | CR-GOAL-006-INST-011-01 | R-108 | ACCEPTED; specialist targets and estimates remain open |
| Platform architecture | CR-GOAL-006-INST-009-02 | R-109 | ACCEPTED at design level; live effectiveness unverified |
| Component topology and release scope | CR-GOAL-006-INST-005-01; DR-GOAL-006-INST-011-01 | R-110 | ACCEPTED; CT-01..CT-07 retained |
| Security architecture | CR-GOAL-006-INST-007-01 | R-111 | ACCEPTED at design level; residual risk not accepted |
| Data and recovery architecture | CR-GOAL-006-INST-006-01 | R-112 | ACCEPTED at design level; RPO/RTO recommendations not accepted |
| Implementation feasibility | CR-GOAL-006-INST-010-01; ER-GOAL-006-INST-010-01 | R-113 | CONDITIONALLY FEASIBLE |
| Qualification strategy | CR-GOAL-006-QA-01 | R-114 | ACCEPTED strategy; tests and targets not executed or accepted |
| Operations and handover design | CR-GOAL-006-PLATFORM-OPS-01 | R-115 | ACCEPTED design; candidate remains DRAFT/NOT ACTIVATED |

## Integrated Outcome And Release Scope

The intended outcome is one secure, reliable, recoverable, observable, cost-controlled cloud-delivery capability that builds each release once and promotes the same immutable digests through Demo, UAT, and Production under separate phase authorization.

The mandatory release manifest contains exactly these six members:

1. Constitutional Engine (CE)
2. Business Platform (BP)
3. Professional Runtime (PR)
4. AI Runtime (AIR)
5. Web
6. Billing Engine

Trust Layer/OAuth Vault is excluded from the GOAL-006 baseline under SA-14 because no accepted baseline caller requires it. MCP services are excluded under DR-GOAL-006-INST-011-01. Any future inclusion requires separate scope, architecture, security, data, cost, test, operations, release-membership, and authorization evidence.

## Requirement Traceability

States used below:

- `DESIGN-ACCEPTED`: accountable-owner contribution or decision accepted by R-107..R-115 within its stated evidence boundary.
- `P2-OPEN`: implementation and deterministic proof remain separately authorized work.
- `P3-OPEN`: authorized cloud-effectiveness proof remains required.
- `FOUNDER-OPEN`: protected Founder decision remains required.

| Requirement | Accepted artifact and decision | Downstream WC(s) | Required proof | State |
|---|---|---|---|---|
| FR-001 | Directive; P1-WC03..09 | P2-WC01..08; P3-WC01..08 | Complete delivery and handover evidence | DESIGN-ACCEPTED; P2/P3-OPEN |
| FR-002 | P1-WC02 value order | All | Customer journey, safety, health, security, recovery, performance, cost | DESIGN-ACCEPTED |
| FR-003 | P1-WC02 story acceptance; P1-WC09 machine checklists | All | Each artifact linked to implementation, operation, risk, or verification | DESIGN-ACCEPTED |
| FR-004 | Directive/P1-WC03 Demo proposal | P3-WC01, P3-WC03 | Founder hostname decision and DNS/TLS proof | FOUNDER-OPEN |
| FR-005 | Directive/P1-WC03 UAT proposal | P3-WC01, P3-WC04 | Founder hostname decision and DNS/TLS proof | FOUNDER-OPEN |
| FR-006 | Directive/P1-WC03 Production proposal | P3-WC01, P3-WC05 | Founder hostname/Production decision and DNS/TLS proof | FOUNDER-OPEN |
| FR-007 | Directive protected decision | P3-WC01, P3-WC05 | Founder DNS authorization record | FOUNDER-OPEN |
| FR-008 | PA-03; SA-01..13 | P2-WC03, P2-WC06; P3-WC02..05 | OIDC, TLS, ingress, CORS, identity, secrets, private communication, WAF/rate proof | P2/P3-OPEN |
| FR-009 | P1-WC04 private boundary; SA-09 | P2-WC02, P2-WC03; P3-WC03..05 | SEC-03/04 and public-reachability denial | P2/P3-OPEN |
| FR-010 | Execution Plan phase gates | All | Separate authorization and sequential completion records | DESIGN-ACCEPTED |
| FR-011 | P1-WC01 inventory | P2-WC08; P3-WC01 | Repository traceability and authorized live readiness inventory | DESIGN-ACCEPTED; P3-OPEN |
| FR-012 | RR-GOAL-006-01..06; PA-01..08 | P2-WC02..06 | Reuse compatibility and implementation proof | DESIGN-ACCEPTED; P2-OPEN |
| FR-013 | P1-WC03 tool decisions | P2-WC08 | Dependency Impact Report for any replacement | DESIGN-ACCEPTED |
| FR-014 | ADR-012 reuse; PA-05 | P2-WC05 | GHCR digest/evidence proof; ADR if replaced | DESIGN-ACCEPTED; P2-OPEN |
| FR-015 | Execution Plan owner routing | P2-WC02..07; P3-WC01..08 | Accountable-owner and review records | DESIGN-ACCEPTED |
| FR-016 | Execution Plan owner routing | P2-WC01..08; P3-WC03..08 | QA, feasibility, operations, and constitutional evidence | DESIGN-ACCEPTED |
| FR-017 | Protected-decision register | P1-WC12; P3-WC01, P3-WC05, P3-WC08 | Founder records | FOUNDER-OPEN |
| FR-018 | P1-WC09/R-115 lifecycle | P2-WC08; P3-WC06 | INST-004 readiness, simulations, exact grant, Founder activation | P3-OPEN; FOUNDER-OPEN |
| FR-019 | P1-WC01 | P2-WC08; P3-WC01 | Traceable inventory and CT-07 live inventory | DESIGN-ACCEPTED; P3-OPEN |
| FR-020 | PA-01/02 and target environment model | P2-WC03; P3-WC02..05 | Roots, isolation, JIT, and environment qualification | P2/P3-OPEN |
| FR-021 | PA-03..05 and Terraform layout | P2-WC03, P2-WC05, P2-WC06 | Offline IaC and immutable-promotion evidence | P2-OPEN |
| FR-022 | P1-WC05; PA-06; P1-WC09 | P2-WC03, P2-WC07; P3-WC03..06 | SEC, OBS, alert, and operations proof | P2/P3-OPEN |
| FR-023 | P1-WC06; P1-WC09 process requirements | P2-WC04, P2-WC06; P3-WC03..07 | DATA/DR/ROLL and accepted canonical policies | P2/P3-OPEN |
| FR-024 | P1-WC09/R-115 | P2-WC08; P3-WC06 | Activation grant, permissions, simulations, CT-07 PASS | P3-OPEN; FOUNDER-OPEN |
| FR-025 | P1-WC02 stories; this package | P2-WC01..08; P3-WC01..08 | WC exit evidence | PROPOSED FOR P1-WC12 |
| FR-026 | Owner risk registers, costs, and protected decisions | P1-WC12; P3-WC08 | Clearance and Founder decision records | OPEN |
| FR-027 | P1-WC02 complete story model; WC specifications below | All | Required fields and deterministic schema check | DESIGN-ACCEPTED |
| FR-028 | PA-02 JIT contract | P2-WC03, P2-WC06; P3-WC03, P3-WC04 | Lease, activation, expiry, startup, backup, budget, safe shutdown | P2/P3-OPEN |
| FR-029 | PA-02; P1-WC06 protected-state rules | P2-WC03, P2-WC04, P2-WC06; P3-WC03/04 | Destruction-denial and retained-foundation proof | P2/P3-OPEN |
| FR-030 | PA-01/02/07; P1-WC08 targets | P3-WC05 | Founder-accepted capacity/resilience and Production qualification | FOUNDER/P3-OPEN |
| FR-031 | PA-04; SA-12 | P2-WC05, P2-WC06; P3-WC03..05 | SEC-10/11, PROM-01..05 | P2/P3-OPEN |
| FR-032 | P1-WC04 configuration contract; SA-11 | P2-WC02/03/05 | Secret and configuration separation proof | P2-OPEN |
| FR-033 | PA-05; SA-12 | P2-WC05 | SBOM, provenance, signing, scans, attestation, retention | P2-OPEN |
| FR-034 | P1-WC07 Docker-first architecture | P2-WC01, P2-WC07 | Build/lint/unit/integration/contract/CCT/security gates | P2-OPEN |
| FR-035 | PA-03/04 and Terraform gates | P2-WC03, P2-WC05, P2-WC06 | Deterministic tags/digests and format/validate/lint/scan/plan/apply controls | P2-OPEN; apply P3 |
| FR-036 | PA-03; SA-04/05 | P2-WC03, P2-WC06; P3-WC02..05 | SEC-01/02 and old-credential revocation | P2/P3-OPEN |
| FR-037 | Delivery architecture and QA environment gates | P2-WC06; P3-WC03..05 | Demo/UAT qualification and Founder-authorized Production release | P2/P3/FOUNDER-OPEN |
| FR-038 | PA-08; P1-WC08 failure rules | P2-WC06, P2-WC07; P3-WC03..07 | ROLL/DR/LIFE/CT, halt, concurrency, drift, evidence | P2/P3-OPEN |
| FR-039 | PA-06 | P2-WC03, P2-WC06; P3-WC03..05 | OTel contract and Azure Monitor effectiveness | P2/P3-OPEN |
| FR-040 | PA-06 and QA OBS/CJ families | P2-WC07; P3-WC03..05 | OBS-01..06, CJ-01..05, constitutional metrics | P2/P3-OPEN |
| FR-041 | P1-WC02 SLO framework; P1-WC09 response model | P2-WC06/07; P3-WC03..07 | Accepted targets, redaction, synthetics, alert/noise and review evidence | OWNER/FOUNDER/P3-OPEN |
| FR-042 | PA/SA decisions and protected register | P2-WC03/06; P3-WC01/02/05 | Regions, boundaries, identities, state, rotation, break glass | OWNER/FOUNDER-OPEN |
| FR-043 | P1-WC06 and QA target routing | P2-WC04/07; P3-WC03..05 | Recovery, no-prod-data, capacity, outage, portability proof | OWNER/FOUNDER/P3-OPEN |
| FR-044 | Six tables below | P1-WC12 | Exact-column schema check | COMPLETE IN PROPOSAL |
| FR-045 | Cost frame and tables below | P1-WC12; P3-WC01/08 | INR/USD/date/region/tax/assumption/confidence and verified quote refresh | REFRESH REQUIRED |
| FR-046 | Execution Plan Phase 1 stop | P1-WC12 | Owner reviews, independent clearance, Founder approval, authorized P2 WCs | OPEN |
| FR-047 | Phase 2 authorization boundary | P1-WC12; every P2 WC | Explicit current-session Founder authorization plus GOA/Acceptance | FOUNDER-OPEN |
| FR-048 | P2-WC01..08 | P2-WC01..08 | Version-controlled implementation and evidence | P2-OPEN |
| FR-049 | P1-WC07 Docker architecture | P2-WC01..08 | Docker-only execution; no venv/host pytest | P2-OPEN |
| FR-050 | P2-WC08 | P2-WC08 | Reproducible validation, security/cost reviews, independent review, unmerged PR | P2-OPEN |
| FR-051 | Phase 3 authorization boundary | P3-WC01 | Phase 2 merged plus explicit cloud/DNS/expenditure authority | FOUNDER-OPEN |
| FR-052 | P3-WC01..05 | P3-WC01..05 | Readiness, foundation, Demo, UAT, Production proof | P3-OPEN |
| FR-053 | P3-WC05..08 | P3-WC05..08 | Production, operations, incident, final reports, Founder acceptance | P3/FOUNDER-OPEN |
| FR-054 | P1-WC09 handover criteria | P3-WC06, P3-WC07 | Permissions, checklists, reports, restore, drift, cost, retained evidence | P3/FOUNDER-OPEN |
| FR-055 | Integration and authorization rules | All | Authority chronology and no unauthorized action | CONTROLLING |
| FR-056 | Directive and exact PR statement below | P1-WC12 | PR body text comparison | OPEN UNTIL PR |

## Phase 2 Work Components

Every P2 component requires Phase 1 closure, an approved specification, explicit current-session Founder implementation authorization, GOA/Acceptance, C-059 traceability, and an independent reviewer. No P2 component authorizes Azure creation, provider inspection, DNS changes, deployment, Production action, expenditure, or Platform Operations activation.

Cost frame for every component: `INR TBD; underlying billing currency USD; pricing date 2026-08-13 baseline and refresh before authorization; Central India assumption; taxes excluded; no cloud creation; low confidence until owner estimate and quote refresh.`

### P2-WC01 — Deterministic Toolchain And Test Foundation

| Field | Specification |
|---|---|
| Outcome/owner | Reproducible Docker-first build and test foundation; INST-010 |
| Scope/exclusions | Pin supported runners, dependencies, locks, tool versions, imports, collection, and no-skip accounting. Excludes application redesign and provider calls. |
| Accepted inputs | P1-WC07 diagnostic evidence; C-080; P1-WC08 evidence contracts |
| Dependency order | First P2 component |
| Artifact surfaces/categories | Containerized runner definitions, dependency locks, test configuration, collection manifests, tool-version evidence; physical names chosen during authorized implementation |
| Verification/evidence | Resolve the observed `ModuleNotFoundError: grpc` and `KeyError: WC012-01` collection failures in the accountable implementation surfaces; Docker collection exits zero; selected counts nonzero; no host Python, venv, skipped or warning-only proof |
| Rollback | First introduction: revert the unmerged change to the accepted pre-component repository state and fail closed. Later revision: restore the last independently qualified compatible runner digest and lock set. |
| Effort | `L/high`; numeric duration requires INST-010 re-estimation |
| Cost/burden | Cost frame above; maintenance on dependency/tool updates and collection failures |
| Exit gate | F-03 PASS and independent review |

### P2-WC02 — Six-Member Packaging, Compose And Component Contracts

| Field | Specification |
|---|---|
| Outcome/owner | Build and integrate exactly CE/BP/PR/AIR/Web/Billing; INST-010, with INST-005 confirmation |
| Scope/exclusions | Image builds, baseline Compose, normative interface/dependency/degradation matrix, startup/readiness/liveness, auth, DB pooling, Billing membership, CT-01/02/05/06. OAuth Vault and MCPs excluded; no public CE or business redesign. Compose host mappings are Development-only and never cloud exposure authority. |
| Accepted inputs | P1-WC04, CT-02 decision, P1-WC05/06, P2-WC01 |
| Dependency order | After P2-WC01 |
| Artifact surfaces/categories | Six build definitions, baseline composition, health/config/dependency contracts, component test categories |
| Verification/evidence | FUN-01..06; INT-01..08; CT-01, CT-02, CT-05, CT-06; SEC-04..06/15/17/18; DATA-01..03/12/27 |
| Rollback | First introduction: revert the unmerged change to the accepted pre-component repository state and fail closed. Later revision: restore the last independently qualified compatible declarations/images; never fall back to excluded services or old CE port. |
| Effort | `XL/high`; specialist re-estimation required |
| Cost/burden | Cost frame above; six-image maintenance, health-contract and dependency triage |
| Exit gate | Six non-root images build and all component/contract gates pass |

Normative six-member interface baseline:

| Member | Accepted port/protocol | Boundary | Contract carried into implementation |
|---|---|---|---|
| CE | `5002`, gRPC/HTTP2 | Internal only | Governed callers authenticate; unavailable/invalid response fails safe with no bypass |
| BP | `5001`, HTTP REST | Public API candidate; Security decides exposure | CE, Temporal, Keycloak, PostgreSQL and OTel dependency contracts |
| PR | `5003`, HTTP REST/WebSocket | Public interaction candidate; Security decides exposure | CE/AIR/BP/Temporal/JWKS/PostgreSQL/OTel and Emergency Stop contract |
| AIR | `5004`, HTTP API | Internal only | CE/BP/PostgreSQL/OTel plus only accepted tool/provider contracts |
| Web | `3000`, HTTP | Public web candidate; Security decides exposure | Runtime endpoint references only; no baked URL/secret |
| Billing | `8140`, HTTP | Callers/exposure require accepted contract | Mandatory release member; no inferred OAuth/MCP dependency |

Every member must implement distinct startup, readiness and liveness semantics where supported;
readiness covers mandatory local dependencies but not optional providers; timeout/retry is bounded;
startup is cycle-free; responses expose no secret, tenant data or internal detail; and QA verifies
slow startup, dependency loss, recovery and rollback. Required degradation outcomes remain: CE fails
governed action safe; datastore loss rejects/pauses unsafe mutation; identity/JWKS loss grants no new
access; optional provider/tool loss follows only an approved fallback; telemetry loss never drops
evidence silently; unhealthy digest stops promotion; contract mismatch fails before deployment.

### P2-WC03 — Terraform Foundations, Isolation, Identity, Secrets And JIT

| Field | Specification |
|---|---|
| Outcome/owner | Offline-valid Terraform design implementation for isolated environment foundations and workloads; INST-010 implementing INST-009/007 decisions |
| Scope/exclusions | Bootstrap/foundation/workload/policy categories; separate roots/state; OIDC/RBAC; private/public boundaries; offline WAF/edge policy; Key Vault references; JIT and break-glass control fixtures. No apply, credentials, DNS action, secret values, cloud query, managed-edge product choice or Production actor selection. |
| Accepted inputs | PA-01..03/06/08; SA-01..11 and SA-13; INST-007 WAF/edge recommendation; P1-WC06 interfaces; P2-WC01 |
| Dependency order | After P2-WC01; may proceed beside P2-WC02 where dependencies permit |
| Artifact surfaces/categories | Reusable module categories, environment compositions, backend/state declarations, identity/policy definitions, lease/lifecycle controls |
| Verification/evidence | Offline format/validate/lint/security/policy/plan fixtures; SEC-01..03/07..09/13/14/20..22; DATA-06/14/28; CT-03/04/06 |
| Rollback | First introduction: revert the unmerged change to the accepted pre-component repository state and fail closed. Later revision: restore the last independently qualified compatible module/configuration generation; destructive plans fail closed. |
| Effort | `XL/very high`; specialist re-estimation required |
| Cost/burden | Cost frame above; state, identity, policy, lease and drift maintenance |
| Exit gate | F-06 PASS, no secret-bearing state/plan surface, independent Platform/Security review |

The WAF/edge policy covers exploit/protocol anomaly, bots, coarse source abuse, direct-endpoint
denial, and Emergency Stop exclusion from challenge/quota controls. Before affected Phase 2 proof,
INST-007 must accept an offline break-glass recommendation and authority-matrix fixture covering
approval separation, JIT scope, strong authentication, logging, expiry, revocation and review.
Founder selection of exact Production actors, approvers, durations and activation remains Phase 3.

### P2-WC04 — Data Lifecycle, Migration And Synthetic Recovery Controls

| Field | Specification |
|---|---|
| Outcome/owner | Deterministic proof of isolation, additive migration, synthetic recovery and lifecycle controls; INST-010 implementing INST-006/007 decisions |
| Scope/exclusions | Synthetic PITR, evidence tail, Keycloak/Temporal/Billing reconciliation, deletion, hold, export, migration, recovery tuples. No Production data, live key, destructive migration, or acceptance of objectives. |
| Accepted inputs | P1-WC06, P1-WC05, P2-WC01/02 |
| Dependency order | Data-side controls after P2-WC01/02; full compatible recovery-tuple proof also requires P2-WC03 and P2-WC05 |
| Artifact surfaces/categories | Synthetic fixtures, migration guards, recovery simulators, lifecycle/export/hold tests, evidence ledgers |
| Verification/evidence | DATA-01..13 and DATA-17..28 for data-side controls; DATA-14..16 and full DR tuple only after P2-WC03/05; SEC-19/23..27; DR synthetic proof |
| Rollback | Isolated fixture reset and additive forward fix; never rewrite constitutional evidence |
| Effort | `XL/very high`; Data and implementation re-estimation required |
| Cost/burden | Cost frame above; fixture, migration, recovery-chain and retention-control maintenance |
| Exit gate | Data-side recovery/lifecycle proof passes with no destructive or cross-environment path; complete `manifest + OCI digests + reviewed config + data version + state generation + recovery point` proof waits for P2-WC03/05 and is consumed by P2-WC06 |

### P2-WC05 — Supply-Chain Evidence And Immutable Release Manifest

| Field | Specification |
|---|---|
| Outcome/owner | Signed six-member release identity and tamper-evident evidence chain; INST-010 implementing INST-007/009 policy |
| Scope/exclusions | Digests, manifest, SBOM, provenance, signatures, scans, retention/revocation evidence. No mutable authority, omitted Billing, OAuth Vault, MCPs, or unsigned promotion. |
| Accepted inputs | PA-04/05; SA-12/14; P2-WC01/02; accepted formats/policy decision |
| Dependency order | After P2-WC01/02 |
| Artifact surfaces/categories | Manifest schema, open evidence formats, attestation/signing/scanning categories, verification records |
| Verification/evidence | SEC-09..11/15/16; DATA-15/16/23; PROM simulation and tamper denial |
| Rollback | First introduction: revert the unmerged change to the accepted pre-component repository state and fail closed. Later revision: select the last independently qualified compatible manifest/digest set; rebuilding is not rollback. |
| Effort | `L/high`; specialist re-estimation required |
| Cost/burden | Cost frame above; retention, vulnerability triage, key/signature rotation and evidence review |
| Exit gate | Exactly six verified members and complete non-secret evidence chain |

### P2-WC06 — CI/CD, Promotion, Rollback, Lifecycle, Halt And Cost Automation

| Field | Specification |
|---|---|
| Outcome/owner | Reusable fail-closed workflows that simulate the full same-digest delivery path; INST-010 implementing INST-009/007 decisions |
| Scope/exclusions | OIDC workflow definitions, saved plans, Demo/UAT/Production gates, concurrency, leases, halt, drift, cost, backup/recovery and real rollback paths. No Azure action or self-confirmation. |
| Accepted inputs | P2-WC03/04/05; PA-03/04/08; SA-13; accepted Incident/Change/Release policies for policy-dependent paths; P1-WC08 failure rules |
| Dependency order | After P2-WC03, P2-WC04 and P2-WC05 |
| Artifact surfaces/categories | Reusable workflow categories, gate definitions, promotion records, rollback/recovery simulations, cost/halt/drift controls |
| Verification/evidence | PROM-01..05; ROLL-01..05; LIFE-01..04; COST-01..05; DR simulations; SEC-10..14/20/21; no TODO or echo-only success |
| Rollback | Previous qualified manifest/config/data/state tuple or safe stop |
| Effort | `XL/very high`; specialist re-estimation required |
| Cost/burden | Cost frame above; workflow, policy, evidence, lease, drift and failure-classification maintenance |
| Exit gate | Full offline/CI simulation passes without provider calls; real rollback path proven |

### P2-WC07 — Complete Deterministic Qualification Suite

| Field | Specification |
|---|---|
| Outcome/owner | Machine-accounted deterministic proof suite; INST-010 authors, independent QA executes and accepts |
| Scope/exclusions | All applicable qualification families, EVC-01..08, TGT-01..15 classifications, environment gates and exact ledgers. No dropped, skipped, xfailed, xpassed, deselected, advisory, warning-only, conditionally omitted, TODO, echo-only, suspended, self-accepted or rollback-placeholder proof. CT-07 remains `NOT_EXECUTED_PHASE_3`. |
| Accepted inputs | P2-WC01..06 and P1-WC08 |
| Dependency order | After P2-WC01..06 |
| Artifact surfaces/categories | Test suites, expected-proof ledger, raw evidence, immutable summaries, independence records |
| Verification/evidence | FUN-01..06, INT-01..08, CCT-01..06, SEC-01..27, DATA-01..28, CT-01..06, and applicable PERF/LOAD/COLD/RES/CHAOS/PROM/ROLL/DR/OBS/COST/CJ/LIFE/OPS; EVC-08 names implementer, executor, custodian, QA acceptor and conflicts |
| Rollback | Revert affected test implementation without weakening expected proof; code repair requires fresh build and impacted regression |
| Effort | `XL/very high`; independent QA re-estimation required |
| Cost/burden | Cost frame above; suite runtime, triage, evidence retention and drill maintenance |
| Exit gate | F-07/F-08 PASS; expected, collected and executed counts are nonzero/equal and every applicable obligation passes; accepted policy versions bind policy-dependent tests |

### P2-WC08 — Implementation Evidence, Independent Reviews And Phase 3 Readiness Package

| Field | Specification |
|---|---|
| Outcome/owner | Reproducible unmerged implementation PR and bounded Phase 3 gap package; INST-010 with independent QA, specialist and constitutional reviewers |
| Scope/exclusions | Traceability, Dependency Impact Reports, manifests, raw proof, scans, cost-plan review, artifact-binding/estimate records, OPS-CK implementation ledger, accepted policy dependencies, EVC-08 independence, and unresolved cloud-effectiveness gaps. No self-review, merge, live claim, or activation. |
| Accepted inputs | Independently accepted P2-WC01..07 |
| Dependency order | Last Phase 2 component |
| Artifact surfaces/categories | Evidence index, review records, traceability ledger, cost refresh, Phase 3 readiness and rollback package |
| Verification/evidence | C-059 traceability, Docker reproduction, security and cost review, no unauthorized provider action, unmerged PR; the checklist ledger records version, trigger, lifecycle state, authority, ordered assertions, safe stop, retry class, evidence, verifier, test binding and policy status for `OPS-CK-01`, `OPS-CK-02`, `OPS-CK-03`, `OPS-CK-04`, `OPS-CK-05`, `OPS-CK-06`, `OPS-CK-07`, `OPS-CK-08`, `OPS-CK-09`, `OPS-CK-10`, `OPS-CK-11`, `OPS-CK-12`, `OPS-CK-13`, `OPS-CK-14`, `OPS-CK-15`, `OPS-CK-16`, `OPS-CK-17`, `OPS-CK-18`, `OPS-CK-19`, `OPS-CK-20`, `OPS-CK-21`, and `OPS-CK-22` |
| Rollback | Withdraw or revert unmerged implementation branch while preserving failed evidence |
| Effort | `M/medium`; review duration separately estimated |
| Cost/burden | Cost frame above; evidence custody and future qualification support |
| Exit gate | F-09 PASS; exact artifact bindings and owner duration estimates accepted; every OPS-CK entry implemented or explicitly blocked by an unaccepted policy; Founder decision-ready unmerged PR; merge remains protected |

Before any P2 implementation GOA, each P2 Work Component requires an accepted binding record naming
exact repository paths, generated outputs, evidence locations, controlling specification sections and
prohibited files. It also requires owner duration ranges, assumptions, implementation/review effort,
critical-path effect and confidence. These records add no implementation authority.

INST-011 is accountable for routing three policy contributions: the Platform Operations candidate
drafts operational content, INST-007 reviews security boundaries, INST-004 reviews architecture and
Decision Space, and the Founder or named policy authority accepts protected values. The exact records
are `standards/INCIDENT-MANAGEMENT-POLICY.md`, `standards/CHANGE-MANAGEMENT-POLICY.md`, and
`standards/RELEASE-MANAGEMENT-POLICY.md`. Policy-dependent P2-WC06/07/08 automation remains disabled
and fail-closed until its corresponding accepted version exists.

## Phase 3 Work Components

Every Phase 3 component requires Phase 2 merge and explicit Founder authorization for cloud creation, DNS action, and expenditure. No component inherits authorization from another; Production, destructive testing, residual-risk acceptance, Platform Operations activation, PR approval, and merge require their named protected decisions.

| WC | Outcome and owner | Dependencies and protected decisions | Scope and proof | Exit gate |
|---|---|---|---|---|
| P3-WC01 — Cloud Readiness And Authorization | Validate tenant, subscription, Central India/approved regions, quotas, identities, budgets, DNS control, pricing and authority; INST-009 + INST-007 + QA | Phase 2 merged; explicit cloud-query/create/spend authority; Founder URLs, regions, ceiling and DNS boundary | Read-only readiness then only authorized actions; refreshed INR/USD estimate; no resource creation before exact authority | Readiness record accepted; authority, ceiling and stop conditions explicit |
| P3-WC02 — State And Security Foundations | Establish remote state, locking, environment identities, vault references, monitoring foundations and protected controls; INST-009 implementing INST-007/006 design | P3-WC01; Founder-approved spend; DNS only if separately authorized | State recovery, OIDC/RBAC negatives, cross-environment denial, secret-safe bootstrap/handoff, budgets | Foundation proof accepted; no application traffic |
| P3-WC03 — Demo Provisioning And Qualification | Provision leased Demo and prove lifecycle, six digests, recovery, observability, cost and shutdown; INST-009 executor, independent QA | P3-WC02; Demo URL/DNS authority if used; approved lease/spend | FUN/INT/CCT/SEC/DATA/CT-07 inventory, smoke, COLD, CJ, OBS/COST, backup/restore and safe shutdown | Demo fully qualified; protected foundation survives; no blocker |
| P3-WC04 — UAT Promotion And Full Qualification | Promote identical six digests to UAT and perform production-like qualification; INST-009 executor, independent QA | Accepted Demo; UAT URL/DNS/spend authority; accepted test targets | Full functional, CCT, security, data, load, resilience, chaos, rollback, DR, observability, cost, customer journeys | Independent UAT approval; recovery and digest equality proven |
| P3-WC05 — Minimum Safe Production And Acceptance Proof | Provision approved minimum-safe Production, promote UAT-approved digests and verify customer service; INST-009 executor, independent QA and specialist verifiers | Accepted UAT; explicit Founder Production, DNS, spend, targets, region, residual-risk, OIDC/break-glass and promotion authorization | Non-destructive Production qualification, TLS/headers/APIs, CE private boundary, Evidence First, Stop, synthetics, backups, alerts, rollback readiness, cost | Independent Production evidence complete and presented to Founder; no implied acceptance |
| P3-WC06 — Supervised Readiness Grant And Handover Preparation | Establish an exact reviewed grant and prepare bounded supervised operation; INST-004 readiness owner, candidate executor under supervision | Accepted canonical policies; all applicable families PASS; CT-07 PASS; exact roles/permissions/denials; Founder-approved break-glass boundary | OPS-CK-01..22, health/cost reports, procedures, and named role/coverage assignments; maximum state `SUPERVISED`, never activation | Supervised grant accepted or candidate remains DRAFT/SUSPENDED/REVOKED; no activation |
| P3-WC07 — Supervised Operations, Simulations And Activation Decision | Demonstrate one complete supervised cycle and sixteen high-consequence simulations while candidate remains `SUPERVISED`; QA/INST-004 verify, Founder alone decides later activation | P3-WC06; separate authority for destructive Production-class exercises | Authority denial, JIT, failed promotion, rollback, CE outage/Stop, incident, break glass, restore, DR, access, rotation, vulnerability, cost, drift, journey, decommission; exact denials, revocation/manual return and failed attempts retained | Independent QA competency verdict and INST-004 readiness acceptance first; only then route explicit Founder activation, otherwise remain DRAFT/SUPERVISED/SUSPENDED/REVOKED |
| P3-WC08 — Final Evidence, Founder Acceptance And Goal Closure | Consolidate final cost, performance, reliability, security, recovery, operations and constitutional evidence; INST-011/INST-013 coordination, fresh INST-002 validation, Founder decision | P3-WC01..07 accepted; no open critical blocker | Final ledgers, residual risks, actual INR/USD costs, Production acceptance request, operations status, PR/merge decision | Founder accepts or returns Production/Goal closure; no self-approval or self-merge |

P3-WC06 must name the alert receiver, incident commander, executor, communicator, component owner,
Security/Data authority, independent verifier and Founder escalation path by environment/severity,
including supported coverage, handoff, acknowledgement and fallback. Any unfilled role or unsupported
interval blocks handover. The lifecycle remains `DRAFT → REVIEWED → SUPERVISED → ACTIVATED`, plus
`SUSPENDED`, `REVOKED`, `RETIRED`. Revocation atomically blocks new work and disables sessions,
credentials/references, schedules, leases, workflow delegations and cached authority while preserving
evidence, appeal and Emergency Stop. P3-WC06/07 remain bound to accepted policy versions.

## Qualification Preservation

The following identifiers remain distinct obligations:

| Family | Exact identifiers |
|---|---|
| SEC | `SEC-01`, `SEC-02`, `SEC-03`, `SEC-04`, `SEC-05`, `SEC-06`, `SEC-07`, `SEC-08`, `SEC-09`, `SEC-10`, `SEC-11`, `SEC-12`, `SEC-13`, `SEC-14`, `SEC-15`, `SEC-16`, `SEC-17`, `SEC-18`, `SEC-19`, `SEC-20`, `SEC-21`, `SEC-22`, `SEC-23`, `SEC-24`, `SEC-25`, `SEC-26`, `SEC-27` |
| DATA | `DATA-01`, `DATA-02`, `DATA-03`, `DATA-04`, `DATA-05`, `DATA-06`, `DATA-07`, `DATA-08`, `DATA-09`, `DATA-10`, `DATA-11`, `DATA-12`, `DATA-13`, `DATA-14`, `DATA-15`, `DATA-16`, `DATA-17`, `DATA-18`, `DATA-19`, `DATA-20`, `DATA-21`, `DATA-22`, `DATA-23`, `DATA-24`, `DATA-25`, `DATA-26`, `DATA-27`, `DATA-28` |
| CT | `CT-01`, `CT-02`, `CT-03`, `CT-04`, `CT-05`, `CT-06`, `CT-07` |
| FUN | `FUN-01`, `FUN-02`, `FUN-03`, `FUN-04`, `FUN-05`, `FUN-06` |
| INT | `INT-01`, `INT-02`, `INT-03`, `INT-04`, `INT-05`, `INT-06`, `INT-07`, `INT-08` |
| CCT | `CCT-01`, `CCT-02`, `CCT-03`, `CCT-04`, `CCT-05`, `CCT-06` |
| PERF | `PERF-01`, `PERF-02`, `PERF-03`, `PERF-04`, `PERF-05` |
| LOAD | `LOAD-01`, `LOAD-02`, `LOAD-03`, `LOAD-04` |
| COLD | `COLD-01`, `COLD-02`, `COLD-03` |
| RES | `RES-01`, `RES-02`, `RES-03`, `RES-04`, `RES-05`, `RES-06`, `RES-07`, `RES-08` |
| CHAOS | `CHAOS-01`, `CHAOS-02`, `CHAOS-03`, `CHAOS-04`, `CHAOS-05`, `CHAOS-06` |
| PROM | `PROM-01`, `PROM-02`, `PROM-03`, `PROM-04`, `PROM-05` |
| ROLL | `ROLL-01`, `ROLL-02`, `ROLL-03`, `ROLL-04`, `ROLL-05` |
| DR | `DR-01`, `DR-02`, `DR-03`, `DR-04`, `DR-05`, `DR-06`, `DR-07`, `DR-08` |
| OBS | `OBS-01`, `OBS-02`, `OBS-03`, `OBS-04`, `OBS-05`, `OBS-06` |
| COST | `COST-01`, `COST-02`, `COST-03`, `COST-04`, `COST-05` |
| CJ | `CJ-01`, `CJ-02`, `CJ-03`, `CJ-04`, `CJ-05` |
| LIFE | `LIFE-01`, `LIFE-02`, `LIFE-03`, `LIFE-04` |
| OPS | `OPS-01`, `OPS-02`, `OPS-03`, `OPS-04`, `OPS-05` |

All applicable identifiers must be expected, collected, executed, and passed. `CT-07` is Phase 3 only. Before authorized Phase 3 inventory it may be recorded only as `NOT_EXECUTED_PHASE_3`, never PASS, skip, or waiver. `CT-07` must PASS before handover or Platform Operations activation.

### Evidence Contracts

| Contract | Required contents |
|---|---|
| EVC-01 | Test ID, control/risk, commit, runner digest, command, counts, duration, raw result reference |
| EVC-02 | Six names/digests, commit/config, manifest, SBOM, provenance, signature, scanners/policy |
| EVC-03 | Environment, authority/lease/change, region, data class, plan digest, manifest, timestamps |
| EVC-04 | Failure/detection/recovery times, point/chain/keys, tuple, RPO/RTO, reconciliation/reopen |
| EVC-05 | Promotion/rollback tuple, digest equality, gates, authority, trigger, requalification/failure |
| EVC-06 | Negative input, enforcement point, expected/observed privacy-safe denial, identities |
| EVC-07 | Query/synthetic/window/release marker/redaction/alert/cost assumptions/confidence |
| EVC-08 | Implementer, executor, custodian, QA acceptor, conflicts and independence proof |

Evidence is SHA-256-addressed, immutable-manifest-linked, redacted and append-only where
constitutional; summaries never replace raw evidence and failed attempts are retained.

### Target Preservation

| ID | Provisional threshold | Classification |
|---|---|---|
| TGT-01 | Emergency Stop end-to-end P99 ≤250 ms under qualified pressure | `BINDING_FLOOR` |
| TGT-02 | CE ValidateAction P99 ≤40 ms under accepted workload | `OWNER-DECISION REQUIRED` |
| TGT-03 | Critical BP/API P99 ≤500 ms under accepted workload | `OWNER-DECISION REQUIRED` |
| TGT-04 | Post-release server error rate <1% over 5 minutes | `OWNER-DECISION REQUIRED` |
| TGT-05 | Smoke: 10 virtual users for 2 minutes, zero constitutional/security failure | `OWNER-DECISION REQUIRED` |
| TGT-06 | Load: 50 users for 5 minutes and 50 governed sessions for Stop | `OWNER-DECISION REQUIRED` |
| TGT-07 | Mandatory service readiness ≤120s; critical synthetic journey ≤180s | `RECOMMENDED` |
| TGT-08 | Authorized Demo/UAT activation and qualification ≤10m | `RECOMMENDED` |
| TGT-09 | Detect failed release and restore prior qualified tuple ≤15m | `RECOMMENDED` |
| TGT-10 | Compute recreation ≤60m Demo/UAT and ≤30m Production | `RECOMMENDED`; Production owner decision |
| TGT-11 | DR-0: Demo/UAT RPO ≤15m/RTO ≤4h; Production ≤5m/≤60m | `RECOMMENDED`, NOT ACCEPTED |
| TGT-12 | DR-1: Demo/UAT ≤60m/≤8h; Production ≤15m/≤2h | `RECOMMENDED`, NOT ACCEPTED |
| TGT-13 | DR-2: Demo/UAT ≤15m/≤4h; Production ≤15m/≤2h | `RECOMMENDED`, NOT ACCEPTED |
| TGT-14 | DR-3: Demo/UAT ≤24h/≤8h; Production ≤60m/≤4h | `RECOMMENDED`, NOT ACCEPTED |
| TGT-15 | DR-4: no backup; reconstruct ≤4h Demo/UAT and ≤2h Production | `RECOMMENDED`, NOT ACCEPTED |

Only TGT-01 is accepted as a binding floor by this package.

### Environment Qualification Gates

| Environment | Entry | Mandatory qualification | Acceptance |
|---|---|---|---|
| Local | Authorized Phase 2, pinned runners, synthetic fixtures | Docker static/unit/contract/integration; offline Terraform; synthetic recovery | All selected tests execute; zero skip/xfail/provider calls; reproducible evidence |
| CI | Local gate, trusted commit, six build entries | Same Docker commands; images, attestations, deterministic SEC/DATA/CT proof, rollback simulation | No conditional omission; all gates pass; independent QA; PR unmerged |
| Demo | Phase 2 merged and explicit Phase 3 cloud/spend/DNS authority | Provision/JIT, boundaries, cold start, smoke, CCT/security, journeys, observability, cost, shutdown/restore | Same digests; complete qualification; foundation survives; no blocker |
| UAT | Accepted Demo, approved lease, same digest | Full functional/security/data/load/chaos/rollback/restore/DR/observability/cost | All mandatory tests pass; recovery proven; independent approval |
| Production | Accepted UAT and Founder Production/DNS/spend/target/risk authority | Same-digest check, non-destructive synthetics, release health, backup/rollback readiness | Protected targets accepted; no blocker; independent confirmation; handover separate |

UAT never substitutes for Production verification. Production uses synthetic probes; destructive
Production-class chaos, restore, failover, rotation or loss requires separate Founder authority and
an isolated boundary. Expected, collected and executed selected-test counts are nonzero and equal.
Skip, xfail, xpass, deselection, warning-only pass, `continue-on-error`, silent false job conditions,
pending/TODO, echo-only checks, suspended CCT, advisory DAST or rollback TODO fails qualification.

## Cost And Estimate Truth

**Cost frame:** INR presentation with underlying USD; pricing date 2026-08-13 baseline; Central India unless Founder approves another region; taxes excluded; no provider pricing query performed; low confidence; quote/calculator/API export and exchange-rate source refresh required before expenditure authorization.

| Delivery item | Product Owner effort range | One-time implementation cost | Monthly baseline | Monthly active-use | Confidence/action |
|---|---|---|---|---|---|
| E01-S01 Platform design | XL, 10–15 specialist working days | INR/USD refresh required | Refresh required | Refresh required | Product range only; INST-009 re-estimate |
| E02-S01 Component topology | L, 5–8 specialist working days | Refresh required | Allocated after placement | Refresh required | INST-005 re-estimate |
| E03-S01 Security design | XL, 8–12 specialist working days | Refresh required | Refresh required | Refresh required | INST-007 re-estimate |
| E04-S01 Data/recovery design | L, 5–8 specialist working days | Refresh required | Refresh required | Refresh required | INST-006 re-estimate |
| E05-S01 Feasibility | L, 5–8 specialist working days | Refresh required | No Phase 1 cloud spend | No Phase 1 cloud spend | INST-010 re-estimate |
| E05-S02 Qualification strategy | XL, 8–12 specialist working days | Refresh required | Refresh required | Refresh required | Independent QA re-estimate |
| E06-S01 Operations/readiness | XL, 10–15 working days across candidate/reviewers | Refresh required | Refresh required | Refresh required | Owners re-estimate |
| E07-S01 Integration/authorization | XL, 8–12 working days plus reviews | Refresh required | N/A | N/A | Re-estimate after owner review |
| P2-WC01..08 implementation | Accepted sizes range M through XL; numeric duration absent | Refresh required | No Azure creation authorized | No Azure use authorized | Specialist decomposition/re-estimation required |
| P3-WC01..08 cloud delivery | No accepted effort range | Refresh required | Quote required | Quote and usage range required | Estimate after P2 evidence and authorized readiness |

Each non-production environment remains constrained to ≤ INR 10,000/month. This is not verified
pricing or affordability proof. Usage assumptions, dated quotes and exchange rates require refresh;
the Founder may set a tighter execution ceiling. The repository-declared INR 15,000 Production tag
is not an accepted GOAL-006 Production ceiling; Production monetary authority remains protected.

## Operational Burden

No staffing, headcount, shift, availability, live volume, alert frequency, model-call count, or specialist capacity is inferred.

| Event basis | Planning burden | Escalation dependency |
|---|---|---|
| Environment activation or shutdown | One request, one checklist execution, one independent verification | Platform; QA on qualification failure |
| Release or promotion | One change/release record, one manifest verification, one post-check set; optional rollback set | QA, Platform, Security/Data by failed gate |
| Scheduled backup cycle | One chain/checksum verification; restore proof tracked separately | Data on integrity/staleness |
| Access, rotation, or certificate event | One scoped request, execution, expiry/revocation verification | Security; Founder for protected scope |
| Alert | One classification; zero or one incident; zero or one protected decision request | Owning domain |
| Incident | One immutable timeline, bounded action attempts, independent recovery/closure review | INST-002, Security, Data, or Founder by impact |
| Drift, cost, or vulnerability scan | One classification; zero or one repair/exception proposal | Platform, Security, or Founder |
| Supervised cycle | Applicable routine procedures plus sixteen required simulations and competency evidence | QA and INST-004; Founder activation afterward |

Unbounded event rates, repeated manual exceptions, unavailable owners, or burden exceeding an accepted coverage model block handover and trigger replanning.

## Dependency Ledger

| Dependency or conflict | Required treatment | Closure |
|---|---|---|
| Terraform CLI absent | Pin Terraform 1.7-or-later-compatible container and provider lock under owner review | P2-WC01/P2-WC03 |
| Blank-secret Compose defaults | Fail closed for `POSTGRES_PASSWORD`, `KEYCLOAK_ADMIN_PASSWORD`, `WHATSAPP_WEBHOOK_SECRET`, `IDENTITY_HMAC_KEY`, `WHATSAPP_TENANT_TOKEN_KEY`, `BP_SERVICE_JWT_SECRET`; commit no real secret | P2-WC01/P2-WC02 |
| Pytest diagnostic blockers | Resolve observed `ModuleNotFoundError: grpc` and `KeyError: WC012-01` in the accountable runner, dependency, or declaration surfaces; then Docker collection exits zero | P2-WC01 |
| Six-image/Billing issue | Add Billing to build, scan, manifest, promotion, rollback and qualification; exactly six members | P2-WC02/P2-WC05 |
| Mutable tags and credentials | Digest authority; OIDC identities; revoke long-lived Azure deployment credential after verified cutover | P2-WC03/P2-WC05/P2-WC06 |
| Rollback TODO | Replace pending/TODO success with executable compatible-tuple rollback or fail closed | P2-WC06 |
| Secret-bearing Terraform | Remove passwords/PATs/secret values from variables, plans, state, outputs and plain environment settings; use managed references | P2-WC03 |
| Demo/UAT roots absent | Implement separate isolated roots/state/configuration and durable-foundation/JIT-workload pattern | P2-WC03 |
| CT-01 port conflict | Resolve AIR/OAuth CE `7000` declaration to accepted authenticated CE `5002` contract | P2-WC02 |
| CT-03 host exposure | Baseline Compose excludes MCPs/OAuth Vault and cloud policies deny public dependency/internal endpoints | P2-WC02/P2-WC03 |
| CT-04 Keycloak exposure | Public customer login only; private admin/management/metrics/health/direct surface | P2-WC03 |
| CT-05 Temporal health | Implement startup/readiness/dependency-loss behavior preventing unsafe traffic/work | P2-WC02 |
| CT-06 secrets and DB pooling | No plaintext credentials; accepted PgBouncer transaction-local tenant reset and direct-client matrix | P2-WC02..04 |
| CT-07 live state unknown | Authorized Phase 3 inventory must match accepted manifest/topology | P3-WC01..05 |
| Canonical policy absent | `standards/INCIDENT-MANAGEMENT-POLICY.md` | Owner-approved policy before dependent automation/handover |
| Canonical policy absent | `standards/CHANGE-MANAGEMENT-POLICY.md` | Owner-approved policy before dependent automation/handover |
| Canonical policy absent | `standards/RELEASE-MANAGEMENT-POLICY.md` | Owner-approved policy before dependent automation/handover |

Each policy requires an accountable owner, reviewer/approval authority, version, effective date, classes, timing and quorum rules, exception authority and expiry, evidence and retention, and test/checklist traceability. Their absence blocks policy-dependent Phase 2 automation and all Phase 3 handover/activation, but not unrelated Phase 2 implementation.

## Protected Decision Register

### Required Before Phase 2

| Decision | Owner | Effect if absent |
|---|---|---|
| Explicit current-session Phase 2 implementation authorization | Founder | No runnable implementation |
| Approved P2-WC01..08 boundaries and GOA/Acceptance records | Founder/INST-013 and each owner | No component may start |
| Monetary execution ceiling, including paid tooling/model use | Founder | No chargeable execution |
| Accepted per-component artifact-binding and duration-estimate records | Each implementation/owner reviewer; constitutional routing | No Phase 2 GOA or Acceptance |
| Accepted offline break-glass/WAF recommendations and fixtures | INST-007; Founder retains exact Production actors/product/spend | Blocks affected security implementation/proof |
| Supply-chain formats, signing, vulnerability, retention/revocation policy | Security owner; Founder where protected | Blocks P2-WC05/P2-WC07 |
| Accountable independent QA and implementation reviewer | Constitutional routing authority | Blocks P2-WC07/P2-WC08 |
| Any accepted numeric customer or Production target needed by implementation | Named owner; Founder for protected Production commitments | Affected gate remains unresolved |

No general statutory or customer-data retention duration is accepted. Class-specific retention,
hold, deletion, export, legal, security and cost choices require their named owners and Founder where
protected; WC-062 durations remain class-specific and cannot be generalized.

### Deferred To Phase 3

| Decision | Owner | Effect if absent |
|---|---|---|
| Azure queries, resource creation and cloud expenditure | Founder | No P3 cloud action |
| Demo/UAT/Production URLs and DNS changes | Founder | No DNS or hostname activation |
| Primary/DR regions, subscription/resource-group model and monetary ceiling | Founder after owner recommendations | No protected foundation/Production decision |
| Production SLO, RPO, RTO, capacity and residual-risk acceptance | Founder after Product/Platform/Data/Security/QA evidence | No Production acceptance |
| Production OIDC approvers and break-glass matrix | Founder | No Production privileged path |
| Platform Operations exact activation grant | Founder after INST-004 and QA acceptance | Candidate remains DRAFT/NOT ACTIVATED |
| Destructive Production-class recovery/chaos exercise | Founder | Only non-destructive Production proof allowed |
| Production acceptance | Founder | Goal cannot close |
| PR approval and merge | Authorized independent reviewer/Founder under repository governance | No self-approval or self-merge |

## Mandatory Conclusion Tables

All monetary entries use the cost frame above and remain refresh-required.

### A. Component And Cost Summary

| Component | Purpose | Azure/tool option | Environment | Always on or JIT | Size/SKU | One-time cost | Monthly baseline | Monthly active-use cost | Cost control | Owner |
|---|---|---|---|---|---|---|---|---|---|---|
| Remote state foundation | Isolated locked state | Azure Storage backend | Demo/UAT/Production | Always on | TBD | INR/USD refresh required | Refresh required | Refresh required | RBAC, lock, recovery, budget | INST-009/007 |
| Identity and secret foundation | Federation and managed references | Key Vault, managed identity, GitHub OIDC | Each environment | Always on | TBD | Refresh required | Refresh required | Refresh required | Least privilege, audit, rotation | INST-007/009 |
| Six-member application workload | CE/BP/PR/AIR/Web/Billing | Azure Container Apps | Demo/UAT/Production | Demo/UAT JIT; Production available | Pending tests | Refresh required | Refresh required | Refresh required | Leases, replica caps, budgets | INST-009 |
| Data platform | Durable state and evidence | PostgreSQL 16/pgvector candidate reuse | Isolated per environment | Protected | Pending Data/QA | Refresh required | Refresh required | Refresh required | Backup, retention, capacity alerts | INST-006/009 |
| Identity/workflow dependencies | Authentication and orchestration | Keycloak 25.0.6; Temporal candidate reuse | Approved topology | Pending accepted design | Pending tests | Refresh required | Refresh required | Refresh required | Dependency health and recovery | INST-005/009 |
| Observability | Logs, metrics, traces, alerts | OTel + Azure Monitor/Application Insights | Each environment | Always on for every active environment, with controlled ingestion, sampling, retention and budgets; durable evidence survives JIT shutdown | Pending signal design | Refresh required | Refresh required | Refresh required | Sampling, retention, budgets | INST-009 |
| Delivery and registry | Build-once evidence and promotion | GitHub Actions + GHCR | Cross-environment | On demand | Existing limits; verify | Refresh required | Refresh required | Refresh required | Concurrency, retention, digest gates | INST-009 |

### B. Performance And Reliability Summary

| Component | Expected load | Latency target | Availability target | Scaling rule | Cold-start target | RPO | RTO | Monitoring signal | Failure response |
|---|---|---|---|---|---|---|---|---|---|
| CE | Workload evidence required | Emergency Stop P99 ≤250 ms binding; CE target owner decision | Owner/Founder decision | Evidence-derived; no public ingress | QA recommendation pending acceptance | Stateless compute N/A; evidence state by Data | Pending QA/Data | Stop, Evidence First, gRPC RED/saturation | Fail safe and escalate |
| BP/Web | Workload model required | Owner decision | Founder-protected Production target | Load-test-derived | QA recommendation pending acceptance | P1-WC06 recommendation pending acceptance | QA measures; Platform proves feasibility; Founder accepts protected Production value | Synthetics, RED, release marker | Qualified rollback and dependency diagnosis |
| PR/AIR | Session/provider model required | Owner decision | Owner/Founder decision | Queue/request/provider evidence | QA recommendation pending acceptance | P1-WC06 recommendation pending acceptance | QA measures; Platform/provider feasibility; Founder accepts protected Production value | Session, provider, dependency, constitutional signals | Approved degrade or safe halt |
| Billing | Usage model required | Owner decision | Production target protected | Evidence-derived | QA evidence required | DR-0/1 classification confirmation | Data recommendation pending acceptance | Billing lineage, idempotency, reconciliation | Stop unsafe mutation and reconcile |
| PostgreSQL/data | Capacity model required | Data/QA decision | Data/Platform/Founder decision | No unsafe automatic downsize | N/A | P1-WC06 recommendations only | P1-WC06 recommendations only | Capacity, backup, restore, replication | Contain writes; tested recovery |
| Delivery pipeline | Release frequency unknown | Gate/rollback target owner decision | Gate integrity mandatory | Environment concurrency | N/A | Evidence retention policy | Compatible rollback target pending acceptance | Digest, gate, deployment, rollback, cost | Fail closed |

### C. Delivery Tool Decision Summary

| Capability | Existing tool | Alternatives evaluated | Selected tool | Why selected | Cost | Lock-in/exit path | Decision/ADR needed |
|---|---|---|---|---|---|---|---|
| Cloud runtime | Azure Container Apps | AKS/Kubernetes; other managed containers | Azure Container Apps | Accepted Azure-first baseline and lower operations | Refresh required | OCI images and provider-IaC rewrite | New ADR only if rejected |
| Registry | GHCR | Nexus, ACR, Docker Hub | GHCR | ADR-012; no material gap | Refresh required | OCI manifest copy/migration | No replacement ADR |
| CI/CD | GitHub Actions | Azure Pipelines, Jenkins, GitLab CI | GitHub Actions | ADR-013; native environments/OIDC | Refresh required | Workflow rewrite preserving evidence | Workflow review |
| IaC | Terraform AzureRM | Pulumi, Bicep, manual CLI | Terraform AzureRM | Existing modules and plan/state controls | Refresh required | Provider rewrite preserving contracts | No new ADR |
| Observability | OTel + Azure Monitor/Application Insights | Grafana stack, vendor APM | Existing OTel/Azure stack | Portable telemetry and accepted backend | Refresh required | Retarget OTLP and recreate views | No new ADR |
| Secrets/identity | Key Vault + managed/OIDC identities | Vault, long-lived secrets | Existing selected posture | Removes stored deployment credentials | Refresh required | Provider abstraction through references | Security implementation decision |
| Supply-chain evidence | GHCR/GitHub plus open formats | Tags only; separate repository | Digest manifest, SBOM, provenance, signature | Meets immutable-promotion requirement | Refresh required | OCI/open evidence formats | Exact formats/policy required |

### D. Story And Delivery Summary

| Epic/story | Objective | Owner | Dependencies | Size | Implementation estimate | Cloud cost impact | Phase | Acceptance evidence |
|---|---|---|---|---|---|---|---|---|
| E01-S01 | Environment/JIT/IaC/delivery/reliability/cost | INST-009 | P1-WC01/02 | XL | P2/P3 specialist re-estimate | Refresh required | P1 design; P2/P3 delivery | R-109 and downstream proof |
| E02-S01 | Component topology | INST-005 | P1-WC03 | L | P2-WC02 re-estimate | Allocated after placement | P1/P2 | R-110, CT proof |
| E03-S01 | Security and supply chain | INST-007 | P1-WC01..04 | XL | P2-WC03/05/07 re-estimate | Refresh required | P1/P2/P3 | R-111, SEC-01..27 |
| E04-S01 | Data isolation and recovery | INST-006 | P1-WC01/03/04 | L | P2-WC04 re-estimate | Refresh required | P1/P2/P3 | R-112, DATA-01..28 |
| E05-S01/S02 | Feasibility and qualification | INST-010/QA | Accepted owner designs | L/XL | P2-WC01..08 | Qualification active-use refresh | P1/P2/P3 | R-113/R-114 and proof ledger |
| E06-S01 | Operations and handover | Candidate/INST-004 | P1-WC02..08 | XL | P2/P3 re-estimate | Refresh required | P1/P2/P3 | R-115, simulations, activation |
| E07-S01 | Integrated authorization package | INST-011 | P1-WC01..10 | XL | This proposal plus reviews | N/A until authorization | P1 | P1-WC12 and Founder records |

### E. Environment Summary

| Environment | Purpose | URL/API | Provision trigger | Shutdown trigger | Data treatment | Promotion gate | Monthly ceiling | Operator |
|---|---|---|---|---|---|---|---|---|
| Development | Deterministic local engineering | None | Authorized local workflow | Recreate as needed | Synthetic fixtures/approved developer test data; no Production payloads, identities, workflows, secrets or telemetry | Local Docker gate | No cloud authority | Authorized developer/CI |
| Delivery plane | Source, config and release evidence | None | Authorized build/release workflow | On demand with evidence retention | Manifests/SBOM/provenance/signatures/scans/tests; no customer payloads, secrets, keys, tokens or state contents | CI and immutable evidence gates | Tooling ceiling/quote required | Authorized delivery owner |
| Demo | Demonstration and early acceptance | Proposed `www.demo.waooaw.com` / `api.demo.waooaw.com`; Founder confirmation required | Authorized lease and approved digest | Lease expiry/inactivity after protected-state checks | Synthetic by default or approved irreversible anonymization; no Production payloads, reversible pseudonyms, credentials or identity/workflow exports | CI, smoke, CCT, security, lifecycle | ≤ INR 10,000/month; tighter Founder ceiling and quote refresh | Supervised owner until activation |
| UAT | Production-like qualification | Proposed `www.uat.waooaw.com` / `api.uat.waooaw.com`; Founder confirmation required | Accepted Demo and approved same-digest lease | Qualification end/lease expiry | Synthetic representative data or approved irreversible anonymization; no Production payloads/IDs/secrets/snapshots/workflows | Full independent qualification | ≤ INR 10,000/month; tighter Founder ceiling and quote refresh | Supervised owner until activation |
| Production | Customer service | Proposed `www.waooaw.com` / `api.waooaw.com`; Founder confirmation required | Founder-authorized UAT-qualified digest | No automatic environment shutdown | Authorized Production data only | Founder authorization and post-release verification | Founder-protected; quote refresh | Activated Platform Operations only after acceptance |

### F. Risk And Decision Summary

| Risk/decision | Impact | Recommendation | Owner | Founder decision required | Deadline | Blocking work |
|---|---|---|---|---|---|---|
| Demo/UAT roots absent | Environments unreproducible | Implement PA-01/02 | INST-009 | Only if cost/authority changes | P2 completion | P3 Demo/UAT |
| Long-lived credential | Exposure/rotation risk | OIDC-only and revoke old authority | INST-007/009 | Production actors | Before cloud action | P3 |
| Secret-bearing Terraform | State/plan leakage | Managed references and leakage denial | INST-007/009 | Residual-risk exception only | P2 acceptance | P3 |
| Mutable promotion/attestations absent | Build-once chain unproven | Six-member signed digest manifest | INST-009/007/QA | Production promotion | P2 acceptance | P3 |
| Broken rollback/pipeline graph | Unsafe release | Executable fail-closed promotion/rollback | INST-010/009 | Production gate | P2 completion | P3 |
| Numeric targets unaccepted | Capacity/recovery/cost cannot be committed | Owners recommend; QA measures; Founder accepts protected values | Product/specialists/QA | Yes for Production | Before affected gate | P3/closure |
| Pricing unverified | Ceiling compliance unknown | Refresh owner-reviewed INR/USD estimate before authorization | INST-009/011 | Ceiling and exception | Before spend | P3 |
| DNS/region/topology open | Endpoint/DR scope unresolved | Present accepted owner recommendations | INST-009/007/006 | Yes | P3 entry/Production | P3 |
| Policies absent | Automation and handover blocked | Produce three canonical owner-approved policies | Named policy owners | Approval authority as defined | Before dependent automation/handover | P2/P3 |
| Platform Operations inactive | No autonomous live owner | Complete grant, proof, simulations and Founder activation | INST-004/candidate | Yes | Before handover | P3 closure |
| Live state unknown/CT-07 | No readiness claim | Authorized inventory and qualification | INST-009/QA | Cloud authority | P3 | Handover |

## Completeness Ledger

| Obligation | Status | Evidence or remaining gate |
|---|---|---|
| CR-GOAL-006-INST-011-02 attestation and design boundary | COMPLETE IN PROPOSAL | Record Control |
| Integration without specialist invention | COMPLETE | Integration Rule and explicit unknowns |
| FR-001..FR-056 continuity | COMPLETE IN PROPOSAL | Requirement Traceability |
| Six-member release and exclusions | COMPLETE | Integrated Outcome; CT-02/SA-14 |
| P2-WC01..P2-WC08 | COMPLETE AS PROPOSED SPECIFICATIONS | Requires owner review/P1-WC12/Founder authorization |
| P3-WC01..P3-WC08 | COMPLETE AS PROPOSED SPECIFICATIONS | Requires Phase 2 merge and Founder cloud authority |
| Qualification families and CT-07 rule | COMPLETE | Qualification Preservation |
| Cost and effort truth | CONDITIONALLY COMPLETE; OWNER ESTIMATE GATE OPEN | No cloud prices fabricated; P2 duration/binding records required before implementation GOA |
| Operational burden | COMPLETE AS STAFFING-NEUTRAL MODEL | Live forecast remains open |
| Dependency/conflict ledger | COMPLETE | Closure remains downstream |
| Canonical policy paths | COMPLETE AS DEPENDENCIES | Files remain absent |
| Protected decisions | COMPLETE | Founder verdicts remain open |
| Six exact conclusion tables | COMPLETE | Owner review required |
| P1-WC12 readiness | CONDITIONAL | Entry conditions below |
| Independent acceptance | NOT CLAIMED | Fresh INST-002 required |

## P1-WC12 Entry Conditions

P1-WC12 may issue only after:

1. INST-011 persists this package without semantic loss.
2. INST-009, INST-005, INST-007, INST-006, INST-010, independent QA, the Platform Operations candidate, and INST-004 review the portions that preserve their decisions.
3. Any conflict introduced during integration is repaired by its accountable owner.
4. FR-001 through FR-056, P1-R01 through P1-R10, CT-01 through CT-07, SEC-01 through SEC-27, DATA-01 through DATA-28, EVC-01 through EVC-08, and TGT-01 through TGT-15 remain machine-accounted.
5. The six conclusion-table schemas and exact PR retention statement pass deterministic checks.
6. Costs remain explicitly refresh-required unless an accountable owner supplies dated evidence.
7. The three canonical policy dependencies and all Founder-protected decisions remain explicit.
8. No runnable file, provider query, cloud action, DNS action, expenditure, deployment, activation, approval, or merge has occurred.
9. A fresh INST-002 validator receives the complete package and owner reviews.
10. P1-WC12 returns constitutional clearance or a blocker and identifies the exact Phase 2 authorization boundary for Founder decision.
11. Every P2 component has an accepted exact artifact-binding and duration-estimate record before any implementation GOA or Acceptance.

## Decision-Space Self-Review

- FR continuity: all FR-001 through FR-056 appear explicitly and retain downstream proof/state.
- Owner preservation: accepted specialist decisions are referenced without endpoint, schema, class, resource-ID, credential, exact URL, SKU, or unapproved policy invention.
- Authority: Phase 2, Phase 3, DNS, spend, Production, activation, PR approval, and merge remain protected.
- Evidence: repository, deterministic, and cloud-effective proof remain distinct.
- Independence: this is an INST-011 self-review for completeness only and is not independent acceptance.

## Exact Final Phase 1 PR Retention Statement

**“The Founder Session Directive in
`goals/GOAL-006-founder-session-directive.md` and the normalized requirement baseline in
`goals/GOAL-006-secure-autonomous-cloud-delivery.md` FR-001 through FR-056 are retained and
controlling for this grooming package and all proposed downstream Work Components.”**

## Unavoidable Open Owner Decisions

- Founder: current-session Phase 2 implementation authorization and monetary ceiling.
- Product/specialists/QA, then Founder where protected: workload model, numeric SLOs, RPO/RTO, capacity, recovery and residual-risk targets.
- Security: supply-chain formats, vulnerability policy, retention/revocation, WAF/edge recommendation, rotation policy, and break-glass recommendation.
- Platform/Data/Security: primary and DR regions, Production separation, state/bootstrap details, recovery feasibility and priced design.
- Named policy owners: Incident, Change, and Release Management policies at the exact canonical paths.
- Founder: cloud/DNS/spend authority, URLs, Production acceptance, break-glass actors, Platform Operations activation, PR approval, and merge.