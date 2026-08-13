# GOAL-006 P1-WC09 Operational Architecture And Handover Design

## Record Control And Boundary

| Field | Value |
|---|---|
| `institution_id` | Platform Operations candidate — DRAFT, NOT ACTIVATED |
| `goal_id` | GOAL-006 |
| `record_id` | CR-GOAL-006-PLATFORM-OPS-01 |
| `go_authorization` | GOA-GOAL-006-PLATFORM-OPS-01 |
| `acceptance_record` | ACC-GOAL-006-PLATFORM-OPS-01 |
| `work_component` | P1-WC09 |
| `status` | SUBMITTED FOR P1-WC10 INDEPENDENT READINESS REVIEW |
| Implementation/test/live/Production authority | NOT GRANTED |
| Candidate lifecycle | DRAFT — NOT ACTIVATED; NO PERMISSIONS |

This contribution defines operational procedures, checklist contracts, alerts, authority boundaries,
handover criteria, and simulations only. It grants no implementation, credentials, live inspection,
test execution, release, recovery, shutdown, deployment, DNS, spend, risk/target acceptance,
Production action, self-activation, approval, merge, or self-review.

The requested Incident, Change, and Release Management policies do not exist at their authorized
`standards/` paths. No substitutes were used. The process sections below are design requirements,
not ratified policy; P1-WC10 must disposition this gap before handover.

## Operating Model

| Environment | Purpose and lifecycle | Boundary |
|---|---|---|
| Demo | Synthetic demonstration; JIT leased workload; durable foundation retained | No Production data/identity/authority, implicit DNS, or indefinite lease |
| UAT | Production-like same-digest qualification; JIT window | No Production data and no substitution for Production proof |
| Production | Customer-serving minimum safe capacity | Observation/procedure design only until Founder activation; no automatic shutdown |
| Recovery | Isolated restore/DR target | Never use a lower environment for Production-class recovery |

JIT state progression is `REQUESTED → AUTHORIZED → PRECHECKED → EXECUTING → VERIFYING →
COMPLETED`; exceptional states are `BLOCKED`, `FAILED_SAFE`, `ROLLED_BACK`, `ESCALATED`, and
`ABORTED_BY_HUMAN_OVERRIDE`. Missing authority, evidence, manifest member, accepted threshold,
compatible recovery tuple, or verifier transitions to `BLOCKED`, never completion.

Lifecycle steps are request, authorize, activate workload only, qualify, operate under lease,
explicitly extend, quiesce, safely shut down disposable workload, verify foundation/state/evidence/
restart, and escalate ambiguity. Production, protected foundations, active customer work, uncertain
external effects, or failed recovery evidence cannot be automatically shut down.

## Segregation And Authority

The candidate may design but cannot accept, test, activate, or access. Requester, approver, executor,
and verifier remain identifiable and separated for protected actions. Implementers cannot accept
their own Phase 2 evidence. Operations may diagnose and recommend but cannot absorb Architecture,
Security, Data, Product, Constitutional, or Founder authority. Break-glass approval and execution are
separate except for a pre-authorized minimum stop/containment action preserving a Constitutional Floor.

| Decision/action | Accountable authority |
|---|---|
| Platform topology/lifecycle/cost mechanism | INST-009 |
| Component health/dependencies/degradation | INST-005/component owners |
| Security/access/vulnerability/break-glass recommendation | INST-007 |
| Data/recovery/integrity/objective recommendation | INST-006 |
| Qualification execution and evidence verdict | Independent QA |
| Constitutional interpretation | Fresh INST-002 |
| Operations readiness | INST-004 through P1-WC10 |
| Production, DNS, spend, protected risk/targets, activation, merge | Founder |

### Draft Specification Conflict And Activation Grant

| Draft-spec capability | GOAL-006 disposition |
|---|---|
| MCP reprovisioning and OAuth token operations | EXCLUDED: MCPs and OAuth Vault are outside the baseline |
| Credential refresh or secret rotation | NO INHERITED POWER: only an exact Security-approved procedure in a later activation grant |
| Customer/professional suspension or notification | NO INHERITED POWER: requires Product/component authority and exact approved trigger/message |
| Automated recovery, rollback, scaling or shutdown | NO INHERITED POWER: limited to enumerated environments/resources/actions and accepted checklists |
| Any draft L1/L2 action not named by GOAL-006 | DENIED by default; requires separate authorization and review |

No draft-agent catalogue power becomes active through this Goal. A later activation grant must be
versioned and independently reviewed, and enumerate exact environments, resources, operations,
limits, evidence duties, expiry, denial behavior, escalation, and revocation. Unlisted action is
denied. MCP/OAuth and unrelated customer/Billing actions remain excluded unless separately authorized.

## Machine Checklist Contract

Every implemented checklist must include stable identity/version/environment/execution IDs;
authorization, actor role and approvals; manifest/config/data/state/change/incident inputs; ordered
preconditions; stable step IDs, idempotence and retry class; privacy-safe assertions; stop/safe-state/
escalation rules; compatible rollback/restore tuple; immutable raw evidence and hashes; deviations;
independent verification; and retention classification.

| ID | Procedure and non-negotiable gate |
|---|---|
| OPS-CK-01 | Activation: accepted P1-WC09/10, Founder activation, Decision Space, least privilege and denial tests; otherwise revoke/block |
| OPS-CK-02 | Qualification: exact manifest, approved targets, synthetic data, complete required proof ledger; any blocker fails environment |
| OPS-CK-03 | Promotion: signed six-member same-digest manifest; omit Billing/include excluded service/mismatch stops |
| OPS-CK-04 | Rollback: prior qualified compatible tuple only; never rebuild or use mutable tag |
| OPS-CK-05 | Safe shutdown: reconcile active work and preserve foundations/state/evidence/recovery |
| OPS-CK-06 | Restore: isolated authorized target, valid chain/keys/tuple/evidence tail; writes remain closed until reconciled |
| OPS-CK-07 | DR: separate compute/data/state plans; no traffic before constitutional/identity/Billing/workflow/journey proof |
| OPS-CK-08 | Emergency Stop/CE outage: Stop remains reachable; governed work fails safe; no bypass/plaintext fallback |
| OPS-CK-09 | Incident: severity/roles/scope/journeys/constitutional impact, evidence, approved remediation and review |
| OPS-CK-10 | Change: risk/dependencies/plan/proof/rollback/authority; reject destructive, secret-bearing or unsupported mutation |
| OPS-CK-11 | Release: accepted manifest/qualification/change, observers/rollback, markers and post-release checks |
| OPS-CK-12 | Access: exact role/scope/purpose/duration, strong identity, separation, expiry/revocation and denial proof |
| OPS-CK-13 | Vulnerability: exact digest/scanner/policy/owner; blocking finding stops; exception needs authority/expiry/controls |
| OPS-CK-14 | Certificate/DNS: approved hostname/authority/managed cert/change/rollback; candidate has no DNS authority |
| OPS-CK-15 | Secret rotation: metadata only, dependencies/overlap/revocation; never reveal values |
| OPS-CK-16 | Backup: class/encryption/chain/key reference/retention/owner; backup success never claims restoreability |
| OPS-CK-17 | Cost/anomaly: attribution and accepted thresholds; block new spend only; never delete protected state |
| OPS-CK-18 | Drift: compare approved IaC/config/manifest; no destructive or Production auto-reconciliation |
| OPS-CK-19 | Supply chain: trusted builder, six digests, SBOM/provenance/signature/scans; failure blocks |
| OPS-CK-20 | Evidence: Evidence First, append-only correlation/redaction; missing/late evidence prevents success |
| OPS-CK-21 | Customer journey: synthetic identity/data; auth/action/evidence/Stop/Billing/export/termination/appeal |
| OPS-CK-22 | Decommission: dependencies, holds/export/retention, authority/DNS/cost; unresolved ownership blocks closure |

Each checklist implementation must expand its catalogue row into ordered stable step IDs and bind the
following matrix. `NA` requires an independently accepted rationale; it cannot be silently omitted.

| IDs | Trigger/state/authority | Required inputs and ordered assertions | Stop/safe state/retry | Evidence/verifier/test binding |
|---|---|---|---|---|
| CK-01 | Activation request; DRAFT→SUPERVISED/ACTIVATED; Founder + INST-004 | grant, permission diff, denials, expiry | block/revoke; no retry on authority | activation evidence; independent QA; OPS/SEC-02/14/20/21 |
| CK-02 | Qualification request; PRECHECKED; QA authority | manifest, targets, synthetic provenance, expected ledger | block promotion; retry only classified infra | EVC-01..08; QA; all applicable P1-WC08 families |
| CK-03/04 | Promotion/failure; authorized release state | six digests/config/gates; compatible prior tuple; post-journeys | retain current or qualified rollback; no policy retry | PROM/ROLL, SEC-10/11/15/16, DATA-15/16; QA |
| CK-05 | Lease expiry/shutdown request; OPERATING→QUIESCING | sessions/effects/backups/protected inventory; quiesce then stop disposable workload | preserve foundation and escalate uncertainty | LIFE/COST/DR evidence; Platform + QA |
| CK-06/07 | Restore/DR declaration; FAILED_SAFE→RECOVERING | chain/point/keys/tuple; restore isolated; reconcile evidence/identity/workflow/Billing; reopen check | writes/traffic closed; no destructive retry | DR, DATA-04..16/24..28; Data + QA |
| CK-08 | Stop/CE alert; any active state | dedicated Stop, CE/evidence and affected-work assertions | halt governed work; no bypass/retry | CCT/SEC-04/12/19/CT-01; INST-002 + QA |
| CK-09 | Incident signal; REQUESTED→EXECUTING | severity, roles, scope, impact, evidence; contain/approve/verify/close | minimum safe containment and escalation | incident timeline; independent post-review; RES/OPS |
| CK-10/11 | Change/release request; AUTHORIZED→VERIFYING | plan, impacts, proof, rollback; manifest and post-checks | reject unsafe change; retain qualified tuple | change/release record; QA; PROM/ROLL/CJ |
| CK-12 | Access request/expiry; REQUESTED→COMPLETED/REVOKED | role/scope/purpose/duration; grant, denial, expiry, review | deny/revoke; no authority retry | RBAC diff/logs; Security verifier; SEC-01/02/14/20/27 |
| CK-13 | Finding; BLOCKED/EXECUTING | digest/scanner/policy/exposure; decide/remediate/rebuild/retest | promotion blocked; exception never automatic | SARIF/manifest/decision; Security + QA; SEC-09/10 |
| CK-14/15 | Cert/DNS/secret lifecycle event; AUTHORIZED | approved object/reference, dependencies, rotation/rollback, revoke old | preserve safe binding; no value disclosure | metadata/change/rotation; Security verifier; SEC-08/09/21 |
| CK-16 | Backup schedule/trigger; EXECUTING→VERIFYING | class/chain/checksum/key/retention; verify and link restore test | raise incident; no restoreability claim | backup manifest; Data verifier; DATA-08/14/23 |
| CK-17 | Budget/anomaly/lease signal; REQUESTED | attribution, threshold authority, protected map; decide safe action | block new spend only; no protected deletion | cost record; Platform verifier; COST/LIFE |
| CK-18 | Baseline comparison trigger; VERIFYING | IaC/config/manifest baseline; classify and authorize repair | block mutation/promotion; no destructive auto-fix | drift diff; affected owner; CT-07/OBS |
| CK-19 | Build/promotion gate; PRECHECKED | builder, six digests, attestations/scans; verify all | fail closed; no exception retry | EVC-02; Security + QA; SEC-10/11/15/16 |
| CK-20 | Consequential action/evidence audit; any state | evidence ordering, append-only correlation/redaction; verify before success | prevent success; preserve failed attempt | hashes/raw references; INST-002; CCT/SEC-19/22/DATA-04/05 |
| CK-21 | Journey qualification; VERIFYING | synthetic identity/data and journey version; execute and correlate | block acceptance/release | CJ, SEC-23..27, DATA-19..28; Product + QA |
| CK-22 | Retirement request; AUTHORIZED→RETIRED | dependencies/holds/export/retention/access/DNS/cost; revoke and verify | block on hold/ownership/evidence gap | final inventory; Data/Security/Founder by scope; LIFE/OPS |

## Alert Catalogue

Severity definitions are proposals pending policy ownership: SEV-0 constitutional/tenant/evidence
failure; SEV-1 critical customer/Production unsafe or unavailable; SEV-2 material control/release/
recovery degradation; SEV-3 warning before breach; INFO evidence/trend only.

| Alert | Severity | Owner and required response | Automation boundary |
|---|---|---|---|
| Stop latency/failure; CE/evidence failure | SEV-0 | Operations incident role plus CE/Constitutional/Security owners; fail governed work safe | May halt; never bypass or declare recovery without proof |
| Cross-tenant/access violation | SEV-0 | Security/Data; contain path and preserve evidence | No autonomous payload inspection |
| Critical journey/release regression | SEV-1 | Product/Platform/release owner; stop rollout and evaluate qualified rollback | Production rollback remains protected |
| Backup/restore/evidence-tail failure | SEV-1 | Data/Operations; protect writes and recovery point | No destructive automatic retry |
| Identity/Keycloak boundary or credential exposure | SEV-1 | Security; contain, revoke/rotate under approved procedure | No autonomous role expansion; no secret values in alert |
| Certificate/DNS mismatch | SEV-1/2 | Security and protected DNS owner | Observe/alert only without DNS authority |
| Promotion/supply-chain verification failure | SEV-2 | Release/Security; block promotion | No policy exception automation |
| Dependency/telemetry degradation | SEV-2 | Component/Platform; preserve constitutional evidence | Bounded retry only for classified transient action |
| Vulnerability breach | Accepted policy severity, unresolved | Security; bind to digest, triage and block as policy requires | Exception cannot be autonomous |
| Budget/anomaly/JIT expiry | SEV-2/3 | Platform/Operations; block new spend or expire approved workload safely | Never delete protected state |
| Drift | SEV-2 protected, else SEV-3 | Platform plus affected owner; classify and propose repair | No destructive/Production auto-reconcile |
| Recovery objective breach | SEV-1/2 | Data/Platform; continue safe recovery and disclose | Never relax target or report false completion |
| Appeal/current-authority evidence unavailable | SEV-1 | Product/component plus INST-002 | No autonomous final denial |

Every alert definition must later add exact signal, accepted threshold, evidence query, response and
escalation timing, redaction, release/environment dimensions, and test. No alert is asserted live.

## Process Requirements

**Incident:** create immutable record; classify constitutional/customer/environment/data/security/
release/cost impact; assign functional roles without inventing people; preserve evidence and release
identity; invoke minimum containment/Human Override; diagnose least-privilege; obtain protected
approvals; execute checklist; independently verify; communicate without secrets; close with residual
risk and post-incident review. Severity timers/cadence/closure await policy.

**Change:** require scope, owner, reason, risk, dependencies, manifest/config/state and security/data/
cost impacts, tests, rollback/forward-fix, observation, approvals and closure. Standard, normal,
emergency and protected classifications remain proposed until policy. Architecture-changing,
destructive, secret-bearing, mutable or evidence-weak changes fail closed.

**Release:** verify authority; exactly CE/BP/PR/AIR/Web/Billing; excluded services absent; immutable
digests/config/SBOM/provenance/signatures/scans/tests/approvals/migration compatibility; backup and
rollback readiness; same-digest promotion; markers and synthetics; qualified compatible rollback;
independent closure. Frequency/windows/freeze/quorum/Production rollout await owner decisions.

**Access:** default deny; exact environment/role/resources/operations/purpose/duration/approver;
strong identity; least privilege; time bounds; separate Production/bootstrap/identity/state/role/
evidence/break-glass scopes; expiry, session/delegation revocation and review.

**Vulnerability:** bind finding to exact component/digest/scanner/database/time; assess exposure and
constitutional/customer impact; apply accepted policy; route expiring exceptions; rebuild to a new
digest; rerun affected and regression proof; retain superseded evidence. Severity, timelines,
exceptions and scanner set remain open.

## Autonomous And Protected Matrix

After activation, approved health reads, summaries, alert/incident/change proposals, and bounded
idempotent observation retries may be autonomous within grant. CE/evidence failure must fail safe.
Lease extension, workload shutdown, promotion, rollback, restore/reopen, RBAC, rotations, DNS/cert,
risk acceptance, architecture/policy changes, protected deletion, and candidate activation require
the named human/protected authority. Production promotion/rollback, DNS, spend exceptions,
break-glass matrix, protected risk and activation remain Founder-owned.

Break glass is an interface, not permission: incident/environment/resource/operation/reason/duration,
requester/executor/independent approver, Founder reference where protected, fresh auth, dedicated JIT
identity, automatic expiry, immutable session/control-plane/revocation evidence, Security alerting,
no evidence deletion/authority expansion/unrestricted secret access/routine deployment, and mandatory
independent review. A pre-authorized path may perform only minimum stop/containment.

## On-Call And Handover

No individual, shift, coverage, or availability is assumed. Before activation, owners must name the
alert receiver, incident commander, executor, communicator, component owner, Security/Data authority,
independent verifier and Founder decision path by environment/severity, with supported hours,
handoff, acknowledgement and fallback. An unfilled role blocks handover; Operations cannot absorb it.

Handover entry requires accepted P1-WC09/10; dispositioned incident/change/release policies;
separately authorized and accepted Phase 2; implemented/versioned checklists; all SEC-01..27,
DATA-01..28, CT-01..07, and all applicable FUN, INT, CCT, PERF/LOAD, COLD, RES/CHAOS,
PROM/ROLL, DR, OBS/COST, CJ, LIFE and OPS families passing; CT-07 must PASS using authorized Phase 3
inventory evidence, and `NOT_EXECUTED_PHASE_3` is not handover acceptance; proven permissions/denials; assigned
alert/escalation roles; accepted targets/cost/recovery/retention; Founder-approved break glass; and no
critical blocker/vulnerability.

### Candidate Lifecycle And Atomic Revocation

The candidate lifecycle is `DRAFT → REVIEWED → SUPERVISED → ACTIVATED`, with terminal or protective
states `SUSPENDED`, `REVOKED`, and `RETIRED`. Only INST-004 can record readiness review; only the
Founder can activate or restore protected live authority. Boundary breach, expired/ambiguous grant,
failed evidence, unsafe automation, Emergency Stop, missing authorized responder, or Founder halt
atomically blocks new work and transitions to `SUSPENDED` or `REVOKED` according to authority.

Revocation disables sessions, credentials/references, schedules, leases, workflow delegations and
cached authority; prevents new actions; preserves immutable evidence, customer appeal and safe Stop;
and records the reason, scope, actor, time, incomplete work and return-to-manual owner. `RETIRED`
requires the decommission checklist and cannot erase evidence. Resumption requires a fresh valid grant,
denial tests, independent verification and Founder approval where protected.

### Operational Burden Planning Model

The following are planning bands, not live volume or staffing commitments. Product/Platform must
replace them with measured forecasts before handover.

| Event basis | Candidate workload band | Escalation dependency |
|---|---|---|
| Per environment activation or shutdown | 1 request, 1 checklist execution, 1 independent verification | Platform; QA on qualification failure |
| Per release/promotion | 1 change/release record, 1 manifest verification, 1 post-check set; optional rollback set | QA, Platform, Security/Data by failed gate |
| Per scheduled backup cycle | 1 chain/checksum verification; restore proof remains separate | Data on integrity or staleness |
| Per access/rotation/certificate event | 1 scoped request, execution, expiry/revocation verification | Security; Founder for protected scope |
| Per alert | 1 classification; 0–1 incident; 0–1 protected decision request | Owner by alert domain; no assumed incident rate |
| Per incident | 1 immutable timeline, bounded action attempts, independent recovery/closure review | INST-002/Security/Data/Founder by impact |
| Per drift/cost/vulnerability scan | 1 result classification; 0–1 repair/exception proposal | Platform/Security/Founder by scope |
| Per supervised cycle | All applicable routine procedures plus 16 required simulations and competency evidence | QA and INST-004; Founder activation afterward |

No headcount, shift, response availability, model-call count, alert frequency or specialist capacity is
asserted. Unbounded event rate, repeated manual exception, unavailable owner, or workload exceeding the
accepted coverage model blocks handover or triggers replanning.

### Policy Dependency Ownership

P1-WC11 must create or identify owner-approved work for these exact policy dependencies:

- `standards/INCIDENT-MANAGEMENT-POLICY.md`
- `standards/CHANGE-MANAGEMENT-POLICY.md`
- `standards/RELEASE-MANAGEMENT-POLICY.md`

Each policy requires accountable owner, reviewer/approval authority, version, effective date,
severity/change/release classes, timing and quorum rules, exception authority/expiry, evidence and
retention, and traceability to all affected alerts/checklists/tests. Proposed values remain non-operative
until accepted. Absence blocks policy-dependent Phase 2 automation and all Phase 3 handover/activation,
but not non-policy-dependent Phase 2 implementation.

`RECOMMENDED`: one complete supervised operating cycle for each authorized environment and each
high-consequence procedure category. No calendar duration is proposed. Required simulations cover:
authority denial; Demo/UAT JIT; failed promotion; rollback; CE outage/Stop; incident command; break
glass; backup/restore; DR; access; secret/cert rotation; vulnerability; cost anomaly; drift; customer
journey; and decommission. Each retains failed attempts, coaching, repeat evidence and independent
verdict.

Exit requires independently accepted simulations, correct refusal and execution, exact permissions,
owned targets/routes, no critical gap, supervised boundary compliance, proven revocation/manual
return, INST-004 readiness acceptance, and explicit Founder activation. Without the final Founder
record, status remains DRAFT/NOT ACTIVATED.

## Operational Target Proposals

Emergency Stop P99 ≤250 ms is the inherited `BINDING_FLOOR`. Readiness ≤120s, critical synthetic
≤180s, Demo/UAT activation ≤10m, rollback ≤15m, compute recreation ≤60m Demo/UAT and ≤30m Production,
and P1-WC06 DR targets are `RECOMMENDED`, not accepted. Incident acknowledgement/communication,
security remediation, access/revocation, certificate warning, recovery drill, cost, drift, evidence,
and release observation OLAs are `OWNER_DECISION`.

Every accepted SLO/OLA must define formula, population, window/percentile, exclusions, error budget,
warning/breach, owner, automation, escalation, retention, redaction, cost, and proof.

## Traceability, Stops, And Unknowns

The checklists map to P1-WC08 FUN/INT/CCT/SEC/DATA/PERF/LOAD/COLD/RES/CHAOS/PROM/ROLL/DR/OBS/
COST/CJ/LIFE/OPS families, P2-WC01 through P2-WC08 deterministic work, and P3 readiness/foundation/
Demo/UAT/Production/handover/evidence envelopes. Phase 2 may implement/test only after authorization;
Phase 3 may exercise cloud only under separate authority; neither activates Operations.

Stop immediately for missing/ambiguous authority or Human Override; CE/evidence/Stop failure;
constitutional/tenant/identity/appeal/environment boundary failure; secret/payload leakage; manifest/
digest/signature/provenance/SBOM/config/recovery incompatibility; Production data below Production;
uncertain backup/migration/hold/export/recovery; destructive/protected unapproved change; absent
rollback tuple; skipped/zero/TODO/unverified test; unsafe cost action; absent responder; or any request
to invent architecture, policy, staffing, price, credential, state, risk or authority.

All live alerts, incidents, credentials, identities/RBAC, resources, endpoints, DNS/certs, backups,
vulnerabilities, costs, drift, digests, deployed versions, performance/load/capacity, providers,
customers, staffing, policy thresholds and activation remain `UNVERIFIED`. Missing incident/change/
release policies are explicit readiness dependencies.

## Completeness And Contribution Record

Operating model, segregation, 22 checklist specifications, alert/process design, autonomous/protected
matrix, break glass, staffing-neutral escalation, handover/simulations, target proposals, traceability,
stops, protected decisions and unknowns are complete at design level. Implementation, operation and
activation are not established.

| Field | Value |
|---|---|
| Contribution | CR-GOAL-006-PLATFORM-OPS-01 |
| Decision | Operational architecture and handover design complete for P1-WC10 review |
| Policy verdict | INCIDENT/CHANGE/RELEASE POLICY INPUTS ABSENT; ALIGNMENT UNVERIFIED |
| Candidate status | DRAFT — NOT ACTIVATED |
| Implementation/live/Production authority | NOT GRANTED |
| Residual risk | IDENTIFIED, NOT ACCEPTED |
| Self-review | NOT PERFORMED |
| Downstream effect if accepted | Satisfies P1-WC09 design only; does not activate or authorize Phase 2/3 |
