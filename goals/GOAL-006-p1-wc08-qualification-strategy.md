# GOAL-006 P1-WC08 Qualification, Performance, Resilience, Promotion, And DR Strategy

## Record Control

| Field | Value |
|---|---|
| `institution_id` | Independent QA |
| `goal_id` | GOAL-006 |
| `record_id` | CR-GOAL-006-QA-01 |
| `record_type` | Qualification Strategy Contribution |
| `go_authorization` | GOA-GOAL-006-QA-01 |
| `acceptance_record` | ACC-GOAL-006-QA-01 |
| `work_component` | P1-WC08 |
| `status` | ACCEPTED — R-114 / CR-GOAL-006-INST-002-06 |
| Accepted dependencies | P1-WC02 through P1-WC07; R-108 through R-113 |
| Implementation/test/cloud authority | NOT GRANTED |

## Authority And Evidence Semantics

QA defines tests, provisional targets, evidence contracts, environment gates, failure rules, and
Phase 2/3 allocation. QA cannot implement, execute tests, access credentials/providers, act in cloud
or DNS, use Production, accept targets/risk, deploy, activate, approve, merge, or self-review.

`ACCEPTED_INPUT` is an accepted predecessor requirement. `BINDING_FLOOR` is an existing
constitutional requirement. `RECOMMENDED` and `OWNER-DECISION REQUIRED` are not accepted SLOs.
`PHASE_2_PROOF` is deterministic Docker/CI evidence. `PHASE_3_PROOF` requires authorized cloud
qualification. `NOT_EXECUTED_PHASE_3` is intentional allocation, never a skip or pass.

Every pass binds commit, six-member manifest and OCI digests, configuration digest, data/state
versions where applicable, test and runner IDs, environment, authority, timestamps, raw results,
and independent verifier. A declaration, workflow success, health response, recommendation,
diagnostic, or zero-test run is not qualification evidence.

## Outcome And Target Routing

Priority order is: critical customer journeys; immutable promotion/recovery; constitutional and
service observability; identity/data/supply-chain protection; durable recovery; performance and
resilience; bounded attributable cost; and accepted operational handover. Product owns journeys and
customer SLO proposals; Platform/component owners own mechanisms and capacity; Security/Data own
their controls; QA measures; Founder accepts protected Production commitments.

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
| TGT-11 | DR-0: Demo/UAT RPO ≤15m/RTO ≤4h; Production ≤5m/≤60m | P1-WC06 `RECOMMENDED`, NOT ACCEPTED |
| TGT-12 | DR-1: Demo/UAT ≤60m/≤8h; Production ≤15m/≤2h | P1-WC06 `RECOMMENDED`, NOT ACCEPTED |
| TGT-13 | DR-2: Demo/UAT ≤15m/≤4h; Production ≤15m/≤2h | P1-WC06 `RECOMMENDED`, NOT ACCEPTED |
| TGT-14 | DR-3: Demo/UAT ≤24h/≤8h; Production ≤60m/≤4h | P1-WC06 `RECOMMENDED`, NOT ACCEPTED |
| TGT-15 | DR-4: no backup; reconstruct ≤4h Demo/UAT and ≤2h Production | P1-WC06 `RECOMMENDED`, NOT ACCEPTED |

No availability, request mix, regional failover, cost, growth, or Production capacity value is
accepted here. Any later accepted SLO requires formula, population, percentile, window, exclusions,
error budget, thresholds, owner, response, escalation, retention, redaction, cost, and test.

## Environment Gates

| Environment | Entry | Mandatory qualification | Acceptance |
|---|---|---|---|
| Local | Authorized Phase 2, pinned runners, synthetic fixtures | Docker static/unit/contract/integration; offline Terraform; synthetic recovery | All selected tests execute; zero skip/xfail/provider calls; reproducible evidence |
| CI | Local gate, trusted commit, six build entries | Same Docker commands; images, attestations, all deterministic SEC/DATA/CT proofs, rollback simulation | No conditional omission; all gates pass; independent QA; PR unmerged |
| Demo | Phase 2 merged and explicit Phase 3 cloud/spend/DNS authority | Provision/JIT, boundaries, cold start, smoke, CCT/security, journeys, observability, cost, shutdown/restore | Same digests; complete qualification; foundation survives; no blocker |
| UAT | Accepted Demo, approved lease, same digest | Full functional/security/data/load/chaos/rollback/restore/DR/observability/cost | All mandatory tests pass; recovery proven; independent approval |
| Production | Accepted UAT and Founder Production/DNS/spend/target/risk authority | Same-digest check, non-destructive synthetics, release health, backup/rollback readiness | Protected targets accepted; no blocker; independently confirmed; handover separate |

Production uses synthetic probes. Destructive chaos, restore, failover, rotation, or loss simulation
against customer-serving state needs separate Founder authority and an isolated Production-class
boundary. UAT never substitutes for required Production verification.

## Qualification Families

| IDs | Required proof | Allocation |
|---|---|---|
| FUN-01..06 | Six mandatory services perform approved critical functions; excluded services absent | Phase 2 Docker; Phase 3 journeys |
| INT-01..08 | Service, identity, Temporal, DB/PgBouncer, Billing, telemetry and failure contracts | Phase 2 Compose |
| CCT-01..06 | Evidence First, immutable audit, Stop, CE fail-safe, override, authority/appeal | Phase 2 deterministic plus Phase 3 effectiveness |
| SEC-01..27 | Every P1-WC05 proof below | Phase 2 implementation; Phase 3 cloud effectiveness |
| DATA-01..28 | Every P1-WC06 proof below | Phase 2 implementation; Phase 3 recovery/objectives |
| PERF-01..05 / LOAD-01..04 | Latency, throughput, errors, saturation, recovery, Stop floor | Docker baseline; accepted environment proof later |
| COLD-01..03 | Service readiness, dependency order, critical journey and lease activation | Docker fixtures plus Demo/UAT |
| RES-01..08 / CHAOS-01..06 | Dependency/control loss, kill, delay, denial, saturation, stale config, partial rollout | Docker first; authorized UAT after safety review |
| PROM-01..05 / ROLL-01..05 | Signed six-member same-digest promotion and compatible rollback | Simulation then Demo/UAT/authorized Production |
| DR-01..08 | Separate compute/data/state/evidence/workflow/Billing recovery | Synthetic Phase 2 then cloud measurement |
| OBS-01..06 / COST-01..05 | Correlated redacted signals; attribution, anomaly, gate, lease, protected state | Contract/policy fixtures then cloud effectiveness |
| CJ-01..05 | Auth, professional access, governed action/evidence, Stop, Billing/export/termination/appeal | Synthetic Demo/UAT; non-destructive Production subset |
| LIFE-01..04 / OPS-01..05 | JIT lifecycle and accepted handover procedures | Simulation; P1-WC09/10 ownership |

## CT Proofs

| ID | Test and gate |
|---|---|
| CT-01 | Every caller uses authenticated CE `5002`; any `7000` dependency blocks WC02 |
| CT-02 | Exactly CE/BP/PR/AIR/Web/Billing in build/scan/manifest/promotion; OAuth Vault/MCP absent |
| CT-03 | Policies deny public dependency/MCP/internal endpoints |
| CT-04 | Keycloak customer login public only; admin/management/metrics/health/direct endpoint denied |
| CT-05 | Temporal startup/readiness/dependency-loss behavior prevents unsafe traffic/work |
| CT-06 | No plaintext secrets; accepted DB/PgBouncer context and pool reset pass |
| CT-07 | Authorized Phase 3 inventory matches manifest/topology; `NOT_EXECUTED_PHASE_3` before then |

## Security Proof Ledger

| IDs | Explicit contracts |
|---|---|
| SEC-01..03 | OIDC negative subjects/no long-lived credential; scoped identities; private components unreachable |
| SEC-04..06 | CE peer/delegation; JWT negatives; no tenant/relationship disclosure |
| SEC-07..09 | Keycloak boundary; TLS lifecycle; no secrets in any artifact/surface |
| SEC-10..11 | Manifest integrity and identical digests without rebuild |
| SEC-12..14 | Stop under WAF/load; controlled egress; break-glass denial/scope/expiry/review |
| SEC-15..16 | Billing mandatory/private; OAuth Vault/MCP absent and no token fallback |
| SEC-17..18 | CT-01 CE endpoint and CT-05 Temporal behavior |
| SEC-19..22 | Evidence failure/ledger denial; environment isolation; rotation; redaction |
| SEC-23..27 | Complete export; termination; identity continuity; appeal evidence; authority transparency |

Explicit machine ledger: `SEC-01`, `SEC-02`, `SEC-03`, `SEC-04`, `SEC-05`, `SEC-06`,
`SEC-07`, `SEC-08`, `SEC-09`, `SEC-10`, `SEC-11`, `SEC-12`, `SEC-13`, `SEC-14`,
`SEC-15`, `SEC-16`, `SEC-17`, `SEC-18`, `SEC-19`, `SEC-20`, `SEC-21`, `SEC-22`,
`SEC-23`, `SEC-24`, `SEC-25`, `SEC-26`, `SEC-27`.

## Data Proof Ledger

| IDs | Explicit contracts |
|---|---|
| DATA-01..03 | Transaction-local RLS, pool reset and current relationship binding across all stores |
| DATA-04..05 | Destructive constitutional operations denied; evidence lineage survives PITR |
| DATA-06..07 | No Production class below Production; re-identifiable anonymization denied |
| DATA-08..11 | Backup chain/evidence tail, Keycloak identity and Temporal duplicate prevention |
| DATA-12..13 | Redis non-authoritative; exact vector reconstruction provenance |
| DATA-14..16 | Secret-safe state, exact GHCR evidence and compatible recovery tuple |
| DATA-17..18 | Additive migration compatibility and destructive/down/Python-ownership denial |
| DATA-19..23 | Deletion, hold, lifecycle replay, isolated export and no secrets/keys/tokens |
| DATA-24..28 | Authoritative RPO/RTO measurement, termination/identity/Billing continuity, redacted telemetry |

Explicit machine ledger: `DATA-01`, `DATA-02`, `DATA-03`, `DATA-04`, `DATA-05`, `DATA-06`,
`DATA-07`, `DATA-08`, `DATA-09`, `DATA-10`, `DATA-11`, `DATA-12`, `DATA-13`,
`DATA-14`, `DATA-15`, `DATA-16`, `DATA-17`, `DATA-18`, `DATA-19`, `DATA-20`,
`DATA-21`, `DATA-22`, `DATA-23`, `DATA-24`, `DATA-25`, `DATA-26`, `DATA-27`,
`DATA-28`.

## Evidence Contracts And Proof Accounting

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

Evidence is SHA-256-addressed, immutable-manifest-linked, controlled and redacted. Constitutional
evidence is append-only; correction and rerun add attempts without deleting failures. Raw evidence
cannot be replaced by summaries. Retention duration remains an owner decision.

Every run compares expected manifest to collection/results. Exactly SEC-01..27, DATA-01..28 and
CT-01..07 must appear. CT-07 may be `NOT_EXECUTED_PHASE_3`, never passed/skipped early. Expected,
collected and executed counts must be nonzero and equal for selected tests. Skip, xfail, xpass,
deselection, warning-only pass, `continue-on-error`, silent false job conditions, pending/TODO,
echo-only checks, suspended CCT, advisory DAST, or rollback TODO fail qualification.

## Failure, Retest, Data And Execution Boundaries

Constitutional, Evidence First, immutability, tenant, exposure, secret, digest, destructive-data, or
authority failure stops promotion. Missing authority/member/evidence/test/dependency/provenance/
verifier/accepted threshold fails closed. Security/data/policy/auth/digest/signature/rollback failures
do not auto-retry. Transient retry requires idempotence, independent classification, retained attempt,
and no assertion execution. Flaky means failed; no quarantine/skip/threshold relaxation/rerun-to-pass.

Repair requires impact analysis, owner review for changed design, fresh build for code changes,
affected tests plus all constitutional/security/data regression gates, and downstream reruns. Cloud
failure admits no traffic and restores a qualified tuple or safe stop. Production rollback never
rebuilds; unavailable/incompatible/unsigned prior tuples stop and escalate.

All Local/CI/Demo/UAT data is deterministic synthetic data with versioned schemas/seeds and no
Production-derived identifiers, payloads, distributions, text, media, embeddings, telemetry,
backups, or metadata. Irreversible anonymization is not synthetic and needs separate approval/proof.
Production qualification uses synthetic probes except separately authorized Production-class recovery.

| Layer | Boundary |
|---|---|
| L0 static/schema | Pinned formatting, typing, contracts, workflow, Terraform/policy, manifests |
| L1 unit | Pinned service runners and synthetic fixtures |
| L2 component | Built images and API/auth/health/config/failure contracts |
| L3 integration | Isolated baseline Compose with six members and required dependencies |
| L4 constitutional/security/data | Complete CCT/SEC/DATA/CT and migration/recovery/promotion simulations |
| L5 performance/resilience | Recorded Docker resource/load/fault profiles; not cloud effectiveness |
| L6 environment | Authorized OIDC/RBAC/TLS/WAF/backup/cost/cold-start/load/DR/drift proof |

No host Python, venv, host pip, unpinned downloads, credentials, or provider calls. Docker proof cannot
claim cloud effectiveness; cloud evidence cannot excuse missing deterministic proof.

## P1-WC07 And Phase Allocation

Entry prerequisites remain: diagnose missing `grpc` and `WC012-01`, then pass full Docker collection;
pin Terraform/AzureRM; approve six build entries; accept supply-chain/vulnerability/retention policy;
close Phase 1 and explicitly authorize Phase 2; assign independent QA/reviewer; close CT-01..06;
accept Product workload, component health, Security controls, Data recovery method, and protected
Founder decisions before affected gates.

| P2 WC | Qualification allocation |
|---|---|
| WC01 | Pinned runners, locks, import/collection/version parity and no-skips ledger |
| WC02 | Six builds/Compose; CT-01/02/05/06; function/contract/health/auth/pool/Billing tests |
| WC03 | Offline Terraform/OIDC/RBAC/boundary/state/secret/JIT/cost policy proofs |
| WC04 | Additive migration and synthetic PITR/evidence/lifecycle/export/hold/recovery proofs |
| WC05 | Six-member manifest, SBOM/provenance/signature/scans/tamper/retention evidence |
| WC06 | Saved-plan, same-digest promotion/rollback/lifecycle/halt/cost/recovery simulation |
| WC07 | Execute complete SEC-01..27, DATA-01..28, CCT and CT deterministic suite |
| WC08 | Package traceability, impacts, manifests, raw proof/scan results and Phase 3 gaps |

Phase 3 allocates readiness, foundations, Demo, UAT, minimum safe Production provisioning,
non-destructive Production proof, supervised handover simulations, and final immutable evidence/
Founder acceptance. Every envelope requires its separate authorization.

## Ownership, Protected Decisions, And Unknowns

Product owns journeys/workload/customer SLO proposals; Platform topology/lifecycle/capacity/compute/
cost; Solution/component owners health/dependencies; Security controls/policy/risk recommendation;
Data classes/recovery/objectives; INST-010 implementation/test code; independent QA execution and
acceptance; fresh INST-002 constitutional clearance; accepted P1-WC09/10 operational procedures;
Founder Production objectives/DNS/spend/risk/approvers/activation/promotion/approval/merge.

Founder decisions remain required for Phase 2/3 authority, regions, hostnames/DNS, expenditure,
Production SLO/RPO/RTO/risk, OIDC/break-glass actors, destructive Production drills, promotion and
Operations activation. Specialist decisions remain open for workload, tooling, sizing, health,
WAF/signing/vulnerability/retention/rotation/redaction, synthetic provenance and recovery lifecycle.

All live cloud, GitHub, GHCR, DNS/TLS, identity, mTLS, backup/WAL, cost, drift, digest, endpoint,
capacity, performance, cold-start, resilience and Production facts are `UNVERIFIED`. No pass,
accepted provisional target, readiness, or residual-risk acceptance is claimed.

## Completeness And Contribution Record

Environment gates, qualification families, CT/SEC/DATA proofs, targets, evidence contracts,
no-skips, failure/retest, synthetic data, Docker/cloud separation, Phase 2/3 allocation, ownership,
protected decisions, and unknowns are complete at strategy level. Implementation and execution are
not established.

| Field | Value |
|---|---|
| Contribution | CR-GOAL-006-QA-01 |
| Decision | Qualification strategy complete and submitted for independent review |
| Verdict | STRATEGY DEFINED; IMPLEMENTATION/EXECUTION/LIVE EFFECTIVENESS UNVERIFIED |
| Provisional targets | RECOMMENDED OR OWNER-DECISION REQUIRED; NOT ACCEPTED |
| Residual risk | IDENTIFIED, NOT ACCEPTED |
| Test/cloud/Production authority | NOT GRANTED |
| Self-review | NOT PERFORMED |
| Downstream effect if accepted | Satisfies P1-WC08 for P1-WC09 planning only |
