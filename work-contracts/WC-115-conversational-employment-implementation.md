# WC-115 - Conversational Employment Protocol Implementation

## Record Control

| Field | Value |
|---|---|
| Authoring office | Chief Solution Architect (INST-005) |
| Implementing office | WAOOAW AI Agent - Platform IT Expert (INST-010) |
| Status | FOUNDER-AUTHORIZED FOR IMPLEMENTATION - PROTOCOL ACTIVATION AND DEPLOYMENT UNAUTHORIZED |
| Parent authority | Founder instruction dated 2026-10-08; merged WC-114; ADR-051; WC-113 |
| Controlling solution package | `architecture/reference/components/conversational-employment-solution-contract.md` `1.0.0-candidate.3`, its unchanged five `1.0.0-candidate.2` OpenAPI contracts and specialist profile |
| Delivery unit | One bounded implementation PR after separate current-session Founder implementation authorization |
| Constitutional basis | C-001, C-003, C-005, C-007, C-023, C-026, C-030, C-034-C-039, C-041-C-044, C-048-C-049, C-051, C-059, C-063, C-065, C-066, C-070, C-079, C-080, C-088 and C-094 |
| Activation authority | None |
| Deployment authority | None |

## 1. Objective

Implement WC-114 as an additive, disabled-by-default candidate protocol across the existing Business
Platform (BP), Conversation Core, Relationship Workspace, Professional Runtime (PR), Constitutional
Engine (CE), Work and Billing Engine (WBE), AI Runtime (AIR), domain adapters and web application.
The implementation must be independently executable from this contract and the controlling solution
package without inventing an owner, interface, state, policy, security boundary, persistence semantic,
failure behavior, test oracle, rollout rule or activation decision.

This contract authorizes no implementation by itself. Before the Platform IT Expert writes or changes
any runnable code or generated artifact, the Founder must explicitly answer the current-session
implementation gate:

> This would begin writing implementation code. Do you authorize WC-115 implementation for the current session?

Absent that explicit answer, only review, planning, Docker validation of this contract and PR handoff
are permitted.

## 2. Authority, Invariants And Exclusions

### 2.1 Authorized outcome after separate implementation authorization

- implement the five WC-114 candidate OpenAPI interfaces on existing deployables;
- reuse, rather than redefine, the approved Conversation Core, Relationship Workspace, PR, CE and
  WBE contracts;
- add owner-controlled persistence, generated clients, projections, reconciliation and tests needed
  by the candidate protocol;
- expose candidate behavior only behind a default-off capability gate that cannot be enabled by
  configuration committed in this Work Contract; and
- produce Docker-only executable evidence and an exact-head Founder-ready PR.

### 2.2 Non-negotiable invariants

1. BP is the sole ordinary public facade, relationship authority, composition owner and public error
   mapper.
2. AIR is proposal-only. AIR output cannot mutate relationship, readiness, plan, billing, authority
   or evidence state.
3. WBE remains the sole commercial and Skill-eligibility authority.
4. CE validation and append-only evidence precede governed success. CE failure never becomes success.
5. PR persists external intent before dispatch and reconciles ambiguous outcomes before retry.
6. Tenant and relationship authority are server-derived; inaccessible, absent and cross-tenant
   resources remain indistinguishable.
7. Unknown, stale, partial, disputed, unavailable and blocked states remain distinct and never
   collapse into ready, active, complete or eligible.
8. `202 Accepted` means durable responsibility only, never business completion.
9. Operations never serializes as `COMPLETE`.
10. Constitutional, safety, evidence, tenant, authority and financial gates have no override.
11. Emergency Stop remains independent and reachable through every relevant degraded state.
12. Append-only plans, commands and constitutional evidence are never deleted or rewritten by
    rollback.
13. Compatibility `PASS` and `activationEligible=true` are evidence only and never activation
    authority.
14. No offered agent is grandfathered, and mixed mandatory major versions fail closed.
15. The prior mandatory employment protocol remains available throughout implementation and rollback.

### 2.3 Explicit exclusions

This Work Contract excludes:

- protocol activation, default-on feature flags, publication as mandatory, customer traffic or
  conformance claims;
- Demo, UAT or Production deployment; cloud/provider mutation; DNS, secrets, protected environments,
  runners, workflow authority, spend or live data;
- a new deployable, database, shared authority service, business capability, lifecycle or ADR;
- changes to the ten WC-113 Founder guardrails, C-034 lifecycle, ADR-051 or the candidate wire
  semantics;
- agent-specification, prompt-policy, model-policy, Decision Consequence Map or product-copy changes;
- implementation of a missing specialist decision by the Platform IT Expert;
- unrelated refactors, dependency upgrades, formatting sweeps, test-threshold reductions or existing
  defect repair outside the dependency closure of this contract; and
- PR approval, merge, protocol activation, deployment or final acceptance by the author.

## 3. Controlling Inputs And Preconditions

| Order | Input | Required state before implementation |
|---:|---|---|
| 0 | Current `origin/main`, `validation/process-control.yaml`, Platform IT Expert office card | Freshness and declared digests PASS |
| 1 | WC-113, ADR-051 and Conversational Employment Workspace 1.0-candidate | Merged and unchanged |
| 2 | WC-114 Work Contract and requirement ledger | Merged; architecture-only ledger remains `NOT_APPLICABLE` |
| 3 | WC-114 solution contract, five candidate OpenAPI documents and specialist profile | Solution exact `1.0.0-candidate.3`; unchanged interfaces/profile exact `1.0.0-candidate.2`; profile digest `41e2147f5d4c6e95b3f3bb714ea43ecedbfb4deb2cebd535d236b90e8a87455f`; schema and reference checks PASS |
| 4 | Conversation Core BP `1.10.0`, PR `1.3.0`, CE `constitutional.v1`, WBE `1.1.0` | Current canonical contracts present |
| 5 | Specialist controls in Sections 7.1-7.5 | Accepted in this contract by Founder review or supplied by separately approved owner contract |
| 6 | `work-contracts/WC-115-requirements.yaml` | Digest matches this complete contract; Docker ledger validation PASS |
| 7 | Current-session Founder implementation authorization | Explicit and recorded after this contract is accepted |

Implementation order is strict: baseline and ledger; persistence/security foundations; owner-local
domain logic; private generated clients and owner contract tests; public BP composition; generated
web client and UI; cross-owner reconciliation; fitness/negative/acceptance tests; exact-candidate
qualification; Founder handoff. A later stage may not compensate for a failed earlier stage.

## 4. Component Ownership And Permitted File Surfaces

Only the following surfaces may change after separate implementation authorization. Existing files
within a permitted surface may be changed only when directly required by a WC115 requirement.

| Owner | Permitted implementation surfaces | Owned result | Prohibited |
|---|---|---|---|
| BP | `src/business-platform/**`, `tests/business-platform.Tests/**`, `infrastructure/postgres/init/**` for BP-owned schema/RLS/outbox only | Public workspace, phase, readiness, plan and command APIs; private compatibility scan; composition; public errors | AIR calls, WBE recomputation, client-derived tenant, protocol activation |
| PR | `src/professional-runtime/**`, `tests/professional-runtime/**` | Execution coordination, AIR/adapter dispatch, durable external intent and reconciliation | Public lifecycle, billing or plan authority |
| AIR | `src/ai-runtime/**`, `tests/ai-runtime/**` | Proposal-only request, receipt and immutable result | Owner-state mutation or customer identity |
| WBE | `src/billing-engine/**`, `tests/billing-engine/**` | Skill-scoped eligibility and commercial consequence | Customer-facing messages, CE calls or PII |
| Domain adapters | `src/agent-adapters/**`, `tests/agent-adapters/**` | Generic manifest, requirements, plan validation, materiality, isolation and performance semantics | Public lifecycle, billing, evidence or cross-relationship access |
| Web | `web/app/**`, `web/components/**`, `web/lib/**`, `web/types/**`, `web/__tests__/**`, `web/tests/**` | Generated-BP-client-backed presentation and local drafts | Private owner calls, handwritten wire DTOs, cached authorization |
| Cross-service tests | `tests/contract/**`, `tests/integration/**`, `tests/constitutional/**`, `tests/acceptance/**`, `tests/fixtures/**`, `tests/performance/**` | Contract, negative, journey, constitutional and bounded performance evidence | Implementation logic |
| Validation evidence | `validation/evidence/wc115/**`, `work-contracts/WC-115-requirements.yaml` | Bounded machine-readable evidence and requirement disposition | Secrets, PII, conversation, prompt, plan or evidence payloads |

The five WC-114 OpenAPI documents and solution component are controlling inputs, not implementation
surfaces. If implementation proves one ambiguous, contradictory or unimplementable, stop; do not
silently repair architecture inside the implementation PR. No `.github/workflows/**`,
`infrastructure/terraform/**`, deployment manifest, provider configuration, agent specification,
constitutional file or unrelated service is permitted.

Every changed `src/` file must carry the repository-standard C-059 header pointing to the exact
controlling solution-contract section. Generated files must carry generator provenance where the
generator supports it and must be traceable through the generation manifest when it does not.

## 5. Candidate Interfaces And Generated-Client Ownership

### 5.1 BP public candidate

Contract:
`architecture/reference/api-specs/conversational-employment-business-platform.openapi.yaml`.

| Operation ID | Method and path | Implementing owner | Required consumer |
|---|---|---|---|
| `getEmploymentWorkspace` | `GET /api/v1/employment/relationships/{relationshipId}/workspace/employment` | BP | Generated BP web client |
| `getEmploymentPhase` | `GET .../phases/{phase}` | BP | Generated BP web client |
| `getEmploymentReadiness` | `GET .../readiness` | BP | Generated BP web client |
| `getEmploymentPlan` | `GET .../plans/current` | BP | Generated BP web client |
| `getEmploymentPlanVersion` | `GET .../plans/{planVersion}` | BP | Generated BP web client |
| `submitEmploymentCommand` | `POST .../commands` | BP | Generated BP web client; idempotency required |
| `getEmploymentCommand` | `GET .../commands/{commandId}` | BP | Generated BP web client; reconciliation |

The generated TypeScript client is owned under `web/lib/api/generated/**` and is the only ordinary web
wire integration. Web adapters may wrap it but may not duplicate schemas or call private owners.

### 5.2 BP private compatibility candidate

Contract:
`architecture/reference/api-specs/conversational-employment-compatibility-scan.openapi.yaml`.

- `startEmploymentCompatibilityScan`:
  `POST /internal/v1/employment-interface/compatibility-scans`.
- `getEmploymentCompatibilityScan`:
  `GET /internal/v1/employment-interface/compatibility-scans/{scanId}`.

The generated client is owned at
`src/business-platform/Clients/Generated/EmploymentCompatibility/**`. It must never be bundled into
web/mobile or called by an agent, adapter or customer channel.

### 5.3 AIR proposal-only candidate

Contract:
`architecture/reference/api-specs/conversational-employment-ai-runtime.openapi.yaml`.

- `proposeEmploymentPatch`: `POST /internal/v1/employment-patch-proposals`.
- `getEmploymentPatchProposal`: `GET /internal/v1/employment-patch-proposals/{proposalId}`.

The generated AIR client is owned at
`src/professional-runtime/clients/generated/employment_ai_runtime/**`. BP, web and domain adapters
must not consume it.

### 5.4 WBE eligibility candidate

Contract:
`architecture/reference/api-specs/conversational-employment-wbe.openapi.yaml`.

- `getEmploymentCommercialEligibility`:
  `GET /internal/v1/relationships/{relationshipId}/employment-eligibility`.

The generated WBE client is owned at
`src/business-platform/Clients/Generated/EmploymentWbe/**`. Browser, PR, AIR and adapters must not
consume it.

### 5.5 Domain-adapter candidate

Contract:
`architecture/reference/api-specs/conversational-employment-domain-adapter.openapi.yaml`.

- `getEmploymentInterfaceManifest`;
- `getInductionRequirementSet`;
- `validatePlanCandidate`;
- `classifyMaterialChange`;
- `evaluateDependencyIsolation`; and
- `getPerformanceAssessment`.

BP owns the generated validation/projection client at
`src/business-platform/Clients/Generated/EmploymentDomainAdapter/**`. PR may own a separately
generated adapter client at
`src/professional-runtime/clients/generated/employment_domain_adapter/**` only for admitted execution
semantics explicitly named by BP. Neither client may expose cross-relationship lookup or customer-
facing authority.

### 5.6 Generation controls

All generated clients must pin generator name/version, exact input path and SHA-256 digest, output
surface and reproducible command in a checked-in generation manifest or existing repository-standard
equivalent. Regeneration must be deterministic. Handwritten duplicate wire DTOs, browser-private
clients and generator output outside the owning component are prohibited.

## 6. State, Idempotency, Reconciliation And Errors

### 6.1 State obligations

The implementation must encode and test the exact WC-114 state machines for phase item, induction
readiness, plan, operations eligibility, candidate patch, command/reconciliation, phase projection
and compatibility scan. Illegal transitions fail closed without owner calls. Terminal item versions
remain immutable. Material change creates a new plan version and relocks only the affected bounded
work. `OUTCOME_UNKNOWN` always enters reconciliation.

### 6.2 Idempotency and concurrency

Every mutation binds authenticated actor, server-derived tenant, relationship, operation family,
idempotency key, canonical payload hash and expected workspace/plan/manifest/Decision Space/WBE
versions. Same identity and hash replay the original receipt/outcome. Same identity with a different
hash returns conflict with no owner call. Expected-version conflict returns only customer-safe current
versions and requires a fresh read. BP derives stable owner-scoped keys and one stable CE
`action_instance_id`.

Compatibility-scan identity additionally binds required protocol version plus exact offered-agent
inventory version and digest. A changed inventory is a new scan. Partial owner commit freezes
incompatible commands until reconciliation. Blind retry after timeout or disconnect is prohibited.

### 6.3 Public and private errors

BP must emit RFC 9457 `EmploymentProblemDetailV1` using only the following stable public mappings:

| Code | HTTP | Required path |
|---|---:|---|
| `EMPLOYMENT_NOT_ACCESSIBLE` | 404 | Missing, inaccessible and cross-tenant remain indistinguishable |
| `EMPLOYMENT_INVALID_REQUEST` | 400 | Shape or semantic invalidity; no owner mutation |
| `EMPLOYMENT_ASSURANCE_REQUIRED` | 403 | Consequence requires stronger accepted assurance |
| `EMPLOYMENT_VERSION_CONFLICT` | 409 | Expected authoritative version changed |
| `EMPLOYMENT_IDEMPOTENCY_CONFLICT` | 409 | Same key, different canonical hash |
| `EMPLOYMENT_REASSESSMENT_REQUIRED` | 409 | Material or stale source relocked affected work |
| `EMPLOYMENT_BLOCKED` | 423 | Known policy, dependency or commercial block |
| `EMPLOYMENT_OUTCOME_UNKNOWN` | 503 | Commit may have occurred; reconcile existing command |
| `EMPLOYMENT_SOURCE_UNAVAILABLE` | 503 | Required owner unavailable |
| `EMPLOYMENT_PROTOCOL_UNSUPPORTED` | 503 | Exact protocol/manifest major unsupported |

Private diagnostics use closed reason codes and may include owner-safe correlation only. Public and
private responses, logs, traces and metrics must not expose PII, credentials, tenant existence,
provider payloads, policy text, prompts, plans or constitutional evidence payloads.

## 7. Specialist Control Package

These controls are implementation obligations fixed by
`architecture/reference/api-specs/conversational-employment-specialist-profiles.yaml`
`1.0.0-candidate.2`, not permission for the Platform IT Expert to select alternatives. A
contradiction with an approved owner contract stops implementation and returns to the owning office.

### 7.1 Data controls

- BP owns public workspace, phase, readiness, plan, command, compatibility-scan and projection
  persistence; PR owns execution intent/outcome and provider correlation; AIR owns immutable proposal
  request/receipt/result; WBE owns commercial eligibility; adapters own immutable manifests and
  domain assessments; CE owns constitutional evidence.
- Every tenant-bearing row is RLS-protected and keyed by server-derived tenant plus owning identity.
- Plans, command transitions, proposal results, scan findings and evidence references are append-only
  or corrected by explicit supersession; owner ledgers are not merged.
- Transactional outbox records bind owner commit, event identity, source version and reconciliation
  state. Recovery replays idempotently and never manufactures success.
- Workspace records store references, closed reason codes and customer-safe summaries only; no
  credentials, prompt bodies, model payloads or constitutional evidence payloads.
- Retention/erasure removes customer-removable projection content while preserving legally required
  audit/evidence references and tombstones. Erasure cannot rewrite CE evidence.
- Calendar values preserve UTC instant, IANA zone, local representation and the agreed tolerance
  version; daylight-saving ambiguity must be explicit and fail closed.

### 7.2 Security controls

- Public calls require the repository-standard authenticated actor assertion; private calls require
  workload identity with exact audience, caller and operation purpose.
- BP derives tenant and relationship authorization and performs it before data access or owner calls.
- Consequential commands bind accepted assurance to operation class; stale or missing assurance fails
  closed.
- Delegated calls carry the minimum immutable identities and never reusable customer credentials.
- Compatibility scan and private clients are unreachable from browser/mobile and excluded from public
  OpenAPI generation.
- Cached, offline, stale or partially available state cannot authorize readiness, execution or
  compatibility.
- Emergency Stop remains available when CE or an owner is unavailable and preserves its existing
  latency and independent-path guarantees.
- Logs, traces, metrics, errors and evidence enforce redaction at source; tests include hostile
  cross-tenant identifiers, forged versions, purpose/audience mismatch and enumeration attempts.

### 7.3 AI controls

- AIR independently canonicalizes and verifies the request digest before accepting responsibility.
- The semantic path catalogue is allow-listed and versioned by BP; AIR cannot emit owner, authority,
  readiness, billing or evidence paths.
- Proposal output includes confidence, assumptions, unresolved questions, source references and
  exact prompt/model policy provenance. Confidence never becomes authority.
- Prompt injection, tool-output injection and hostile transcript content remain untrusted data and
  cannot alter system policy, path allow-list, tenant, relationship or operation class.
- Inputs are minimized to the bounded contribution and required references; AIR must not know raw
  customer identity or retain unrelated transcript content.
- Reconciliation rejects any receipt/result whose relationship, contribution, agent, manifest,
  semantic-catalogue or canonical request-digest identity differs from the accepted request.

### 7.4 Product and accessibility controls

- The first release preserves conversation as the primary interaction while presenting owner-backed
  candidate cards, confirmations, pending reasons, blocked effects, limitations and next action.
- Web exposes the same relationship, plan, rights and evidence identities across supported channels.
- Stale, partial, unknown, blocked and unavailable states have distinct accessible labels and do not
  use color alone.
- Stop remains visible and keyboard/screen-reader reachable in every operations, billing and degraded
  projection.
- No copy, visual hierarchy or local draft may imply readiness, agreement, execution or success before
  owner confirmation.

### 7.5 Specialist closure profiles and upstream repairs

The focused Data, Security, AI and Product/Quality review found controls that cannot be safely
invented by the Platform IT Expert. WC-114 `1.0.0-candidate.2` now supplies the following
digest-bound profiles and candidate-interface repairs. WC-115 must not advance to
`IMPLEMENTATION_AUTHORIZED` until the Founder accepts that exact candidate and profile digest. This
Work Contract does not authorize the implementer to replace their values.

| Closure input | Exact mandatory content | Blocking stage |
|---|---|---|
| Data persistence profile | Specialist profile `data_profile` | WC115-01 |
| Security assertion profile | Specialist profile `security_profile.workload_identity` | WC115-01 |
| Assurance matrix | Specialist profile `security_profile.assurance` | WC115-01 |
| Source freshness profile | Specialist profile `freshness_profile` | WC115-01 |
| Stop binding | Specialist profile `emergency_stop_profile` | WC115-01 |
| AI control profile | Specialist profile `ai_profile` | WC115-02 |
| Product truth profile | Specialist profile `product_truth_profile` | WC115-04 |
| Rollback control profile | Specialist profile `rollback_profile` | WC115-01 |

WC-114 `1.0.0-candidate.2` repairs the prior candidate where it could not express these controlling
requirements:

1. `CalendarCommitmentV1` must require IANA zone, validated local datetime, UTC instant, UTC
   offset/fold discriminator, tzdb version, tolerance-policy reference/version and consistency
   validation.
2. BP `401` must use the existing canonical BP authentication problem contract rather than forcing an
   undefined `EmploymentProblemCode`.
3. `EmploymentCommandRequestV1` must be a discriminator-based closed `oneOf` with exact applicable
   expected versions per command; terminal `200` replay must return an outcome shape preserving owner
   steps, evidence and resulting version.
4. AIR request, receipt and result must carry protocol, patch type, prompt-policy and model-policy
   references/digests plus required model-decision provenance. Its semantic catalogue must be a
   trusted immutable reference, not caller-selected path prefixes. Result variants must distinguish
   `PENDING`, successful `PROPOSED`, `UNREPRESENTABLE` and `FAILED` with state-dependent constraints.
5. CEW-FIT-12 must read the aggregate workspace and assert `operations.stopReachable=true` for every
   phase/readiness/billing/degraded setup; it must not require that field on schemas that do not own it.
6. CEW-NEG-010 must contain at least two offered agents with different mandatory major versions and
   assert aggregate `FAIL`, `activationEligible=false`, a closed mixed-major reason and no activation
   mutation.

Absence of any applicable profile or interface repair is an upstream specification blocker, not an
implementation story. Founder approval of this Work Contract does not by itself approve unknown
profile values or amend the WC-114 candidate contracts.

## 8. Delivery Stages And Milestone Commits

| Stage | Dependency | Required output | Exit oracle | Milestone commit |
|---|---|---|---|---|
| WC115-00 Baseline | None | Fresh process controls, digest-valid ledger, selected Skill 2/3/4/5/6/7/12/15/16 sections | Docker ledger and preflight PASS | `chore(platform): bind WC-115 implementation baseline` |
| WC115-01 Foundations | 00 | Owner persistence, RLS, append-only/supersession, outbox, security assertions, default-off gate | Data/security negative tests PASS | `constitutional(bp): add employment protocol foundations` |
| WC115-02 Private owners | 01 | AIR, WBE and adapter candidate interfaces plus PR coordination/reconciliation | Owner unit and generated-client contract tests PASS | `feat(runtime): implement private employment protocol owners` |
| WC115-03 BP composition | 02 | Seven public BP operations and two private compatibility operations | BP unit/contract tests and error matrix PASS | `feat(bp): implement conversational employment composition` |
| WC115-04 Web experience | 03 | Generated BP client and accessible conversation/workspace presentation | Typecheck, unit, browser and accessibility tests PASS | `feat(web): add governed employment workspace experience` |
| WC115-05 Cross-owner proof | 04 | Success, partial, stale, blocked, unknown, outage and reconciliation journeys | Integration, CCT, CEW-FIT and CEW-NEG suites PASS | `cct(platform): prove conversational employment invariants` |
| WC115-06 Qualification | 05 | Frozen candidate, complete Docker qualification, scans, evidence ledger | Exact-candidate aggregate PASS | `chore(platform): qualify WC-115 candidate` |
| WC115-07 Handoff | 06 | Exact-head author review and prepared PR | Remote-head precheck PASS; PR open | No post-review commit |

Each milestone must leave the branch executable. A repair after candidate freeze creates a new
candidate and reruns the affected dependency closure. Commit messages must include repository-required
`IB:` and `Constitutional:` fields and the Copilot co-author trailer. `PROJECT_STATE.md` is updated
only for a real externally meaningful state transition, never for routine milestone progress.
Because this contract was assigned directly by the Founder and has no Institutional Backlog item,
the exact milestone body value is `IB: N/A - Founder-assigned WC-115`. The constitutional body value
must list the requirement-specific claims and at minimum `Constitutional: C-059, C-065, C-080,
ADR-051`.

## 9. Canonical Requirement Index

Each row is normative and maps one stable implementation requirement to direct evidence in
`WC-115-requirements.yaml`.

| Requirement | Normative outcome |
|---|---|
| WC115-R001 | Implementation starts only from fresh process controls, accepted inputs, a digest-valid ledger and explicit current-session Founder authorization. |
| WC115-R002 | The implementation is additive on existing deployables and remains disabled by default without any activation or deployment path. |
| WC115-R003 | Changes remain inside the exact permitted surfaces in Section 4 and contain no unrelated repair or refactor. |
| WC115-R004 | Every changed source file and generated artifact has C-059 traceability to the approved controlling specification. |
| WC115-R005 | BP remains the sole public facade, relationship authority, composition owner and public error mapper. |
| WC115-R006 | Conversation Core and Relationship Workspace are reused without a duplicate transcript, relationship or phase truth. |
| WC115-R007 | PR owns execution coordination, durable external intent and ambiguous-outcome reconciliation without public lifecycle authority. |
| WC115-R008 | CE validation and append-only evidence precede governed success while Emergency Stop remains independent. |
| WC115-R009 | WBE remains the sole commercial and Skill-eligibility authority and its stale/unknown states never become eligible. |
| WC115-R010 | AIR remains proposal-only and cannot mutate authoritative owner state. |
| WC115-R011 | Domain adapters remain generic and own only domain meanings, constraints, isolation and outcome interpretation. |
| WC115-R012 | Web uses generated BP clients only and never calls a private owner or authorizes from cache. |
| WC115-R013 | `getEmploymentWorkspace` implements the exact BP candidate operation and complete closed aggregate. |
| WC115-R014 | `getEmploymentPhase` implements the complete common phase projection and phase-specific state constraints. |
| WC115-R015 | `getEmploymentReadiness` implements four owner-backed readiness facets with unmet conditions and sources. |
| WC115-R016 | `getEmploymentPlan` and `getEmploymentPlanVersion` expose current and immutable historical plan versions without rewriting history. |
| WC115-R017 | `submitEmploymentCommand` durably accepts a closed command discriminator and returns responsibility rather than success. |
| WC115-R018 | `getEmploymentCommand` reconciles every required owner step to a stable terminal or blocked outcome. |
| WC115-R019 | The private BP compatibility start operation binds one exact offered-agent inventory and required protocol version. |
| WC115-R020 | The private BP compatibility read operation fails closed on partial, stale, unknown, mixed-major, unresolved or missing evidence. |
| WC115-R021 | AIR implements proposal submission with independent canonical-digest verification and immutable identities. |
| WC115-R022 | AIR implements proposal reconciliation without accepting identity or digest drift. |
| WC115-R023 | WBE implements exact Skill-scoped commercial eligibility while preserving constitutional and read-only paths. |
| WC115-R024 | Domain adapters implement the exact manifest and induction-requirement operations. |
| WC115-R025 | Domain adapters implement exact plan-validation and material-change-classification operations. |
| WC115-R026 | Domain adapters implement exact dependency-isolation and performance-assessment operations. |
| WC115-R027 | Generated clients pin generator version, input digest and owning output surface and regenerate deterministically. |
| WC115-R028 | Handwritten duplicate wire DTOs, browser-private clients and cross-owner generated artifacts are absent. |
| WC115-R029 | Phase-item, induction-readiness, plan and operations-eligibility transitions exactly match WC-114 and reject illegal transitions before owner calls. |
| WC115-R030 | Candidate-patch, command/reconciliation, phase-projection and compatibility-scan transitions exactly match WC-114. |
| WC115-R031 | Unknown, stale, partial, disputed, unavailable and blocked source states remain explicit and cannot serialize authoritative success. |
| WC115-R032 | Operations can never serialize `COMPLETE`; bounded work retains separate completion. |
| WC115-R033 | Every mutation binds actor, server-derived tenant, relationship, operation family, idempotency key, canonical hash and expected owner versions. |
| WC115-R034 | Same idempotency identity/hash replays the original result; a different hash conflicts with zero owner calls. |
| WC115-R035 | Expected-version conflict requires a fresh read and reveals only customer-safe current versions. |
| WC115-R036 | BP derives stable owner keys and one CE `action_instance_id` across retries and evidence transitions. |
| WC115-R037 | Timeout, disconnect or possible partial commit enters `OUTCOME_UNKNOWN`; blind retry is prohibited until reconciliation proves safety. |
| WC115-R038 | Compatibility scan identity binds protocol and exact inventory version/digest; changed inventory creates a new scan. |
| WC115-R039 | BP emits only the exact RFC 9457 public error vocabulary and status mappings in Section 6.3. |
| WC115-R040 | Missing, inaccessible and cross-tenant resources are indistinguishable `404` responses without existence signals. |
| WC115-R041 | Private diagnostics use closed owner-safe reason codes and all errors/logs/traces/metrics are privacy-safe. |
| WC115-R042 | BP, PR, AIR, WBE, adapter and CE data ownership remains separate and tenant-bearing persistence enforces server-derived RLS. |
| WC115-R043 | Plans, commands, proposals, scan findings and evidence references are append-only or explicitly superseded. |
| WC115-R044 | Transactional outbox and reconciliation records recover idempotently without manufacturing success. |
| WC115-R045 | Retention/erasure removes removable projection content while preserving mandatory audit/evidence references and tombstones. |
| WC115-R046 | Calendar persistence preserves instant, IANA zone, local representation, tolerance version and ambiguous-time handling. |
| WC115-R047 | Public and private authentication use exact actor/workload assertions, audience, purpose and minimum delegated identities. |
| WC115-R048 | Assurance is bound to consequence and stale, missing, cached, offline or partial state cannot authorize. |
| WC115-R049 | Emergency Stop remains reachable and preserves existing independence and latency during owner or CE failure. |
| WC115-R050 | AIR enforces the versioned semantic path allow-list, proposal provenance, injection resistance and input minimisation. |
| WC115-R051 | Observability binds privacy-safe correlation, exact versions, owner freshness, decisions, reconciliation identities and retry disposition. |
| WC115-R052 | Metrics exclude raw tenant/customer/domain payloads and dashboards separate availability, gates, blocks, staleness, reconciliation, providers, performance and outcomes. |
| WC115-R053 | Rollout follows specialist acceptance, frozen schemas, owner implementation/tests, complete manifests/scenarios, exact-inventory scan, shadow projection and separate Founder activation. |
| WC115-R054 | Rollback blocks candidate-only commands, restores prior projection and preserves plans, commands, owner facts and CE evidence. |
| WC115-R055 | BP, PR, AIR, WBE, adapter and web focused unit suites cover owned success, validation, illegal transition and owner-failure paths. |
| WC115-R056 | Generated-client and provider/consumer contract tests prove all five OpenAPI contracts with no unresolved reference or DTO drift. |
| WC115-R057 | Integration tests prove conversation-to-induction, plan acceptance, material change, operational admission, billing exhaustion and ambiguous-outcome reconciliation. |
| WC115-R058 | Security tests prove RLS, anti-enumeration, cross-tenant denial, audience/purpose binding, assurance, redaction and cached-state anti-bypass. |
| WC115-R059 | AI tests prove proposal-only behavior, immutable identity/digest, path rejection, hostile injection handling, minimisation and reconciliation mismatch denial. |
| WC115-R060 | Data tests prove append-only/supersession, outbox replay, duplicate delivery, recovery, erasure split and calendar ambiguity. |
| WC115-R061 | Web tests prove generated-client-only integration, truthful state distinctions, no premature success and accessible persistent Stop. |
| WC115-R062 | CE outage tests prove writes fail closed, reads remain safe, PR pauses/reconciles and Stop remains independent. |
| WC115-R063 | Exact-inventory compatibility tests prove every offered agent requires exact manifest, adapter and conformance evidence and cannot activate the protocol. |
| WC115-R064 | DMA, Trading and Tutor fixtures pass the same generic BP/adapter schemas without platform domain fields. |
| WC115-R065 | CEW-FIT-01 through CEW-FIT-18 each have an executable owner contract or journey test with the exact WC-114 oracle. |
| WC115-R066 | CEW-NEG-001 through CEW-NEG-011 and CEW-POLICY-001 execute as runtime/contract negative tests, not schema-only substitutes. |
| WC115-R067 | Acceptance proves the three-phase conversational journey, partial readiness, deferred dependencies, material relock, billing preservation, credential isolation and corrective proposal. |
| WC115-R068 | Accessibility, bounded performance, CCT, SAST, dependency, secret, license and observability gates pass without threshold reduction. |
| WC115-R069 | All implementation and test tooling runs through catalog-owned Docker runners; host language tools and ad hoc Docker authority produce no PASS evidence. |
| WC115-R070 | Focused story evidence uses catalog selection and the final immutable candidate completes one dependency-complete WC-104 qualification. |
| WC115-R071 | Every requirement has direct machine-readable evidence bound to exact candidate, command, environment and result identity. |
| WC115-R072 | Author review re-reads the complete output, repairs every finding and binds PASS to the exact remote 40-character head. |
| WC115-R073 | Milestone commits preserve executable state, use required traceability fields and do not update PROJECT_STATE for routine progress. |
| WC115-R074 | Founder handoff uses the exact prepared PR body; the author neither approves, merges, activates nor deploys. |
| WC115-R075 | Any stop condition in Section 14 halts the affected stage without compensation or scope expansion. |
| WC115-R076 | A rollback trigger restores the last qualified stage or prior mandatory protocol while preserving immutable history and evidence. |
| WC115-R077 | A Founder-accepted owner-by-record persistence matrix fixes canonical stores, keys, versions, transactions and prohibited writers before implementation. |
| WC115-R078 | Every tenant table enforces forced RLS, transaction-local server-derived context, tenant-complete references and non-bypass application/worker roles. |
| WC115-R079 | Corrections create immutable, same-owner acyclic supersession records with compare-and-swap concurrency rather than update/delete. |
| WC115-R080 | Owner mutation/outbox and consumer effect/inbox commit atomically with exact identity, ordering, lease, retry, poison and crash semantics. |
| WC115-R081 | A Founder-accepted retention/erasure matrix fixes legal basis, periods, authority, removable/preserved fields, order, backup expiry and verification. |
| WC115-R082 | Calendar implementation waits for and conforms to the repaired instant/zone/fold/tzdb/tolerance wire contract. |
| WC115-R083 | Every mutation has accepted canonicalization vectors and an atomic idempotency reservation whose lifetime covers possible owner effects. |
| WC115-R084 | Database evolution uses forward-only expand/backfill/verify/cutover with resumable checkpoints, deterministic order and duplicate-safe restart. |
| WC115-R085 | Customer-visible implementation uses an approved product lexicon/state mapping; raw owner codes or generated copy are prohibited. |
| WC115-R086 | BP authentication failures use the canonical authentication problem contract and never invent an employment error code. |
| WC115-R087 | Employment commands use closed per-kind schemas with exact applicable versions and reject extra/missing fields before owner calls. |
| WC115-R088 | Terminal command replay returns the complete immutable outcome and proves equality with the original owner/evidence/result state. |
| WC115-R089 | Every runtime negative fixture names operation, setup, input/owner response, expected safe result, prohibited observations and exact side-effect count. |
| WC115-R090 | Stop fitness reads the aggregate owner field and proves reachable control for every degraded setup. |
| WC115-R091 | Mixed-major compatibility evidence uses at least two offered agents and proves aggregate fail with no activation mutation. |
| WC115-R092 | Docker PASS envelopes bind gate, pinned image digest, in-container command, candidate, environment, exit code and artifact digest. |
| WC115-R093 | Every PASS ledger reference is immutable and binds candidate, gate, command, image, environment, result, time, artifact URI and digest. |
| WC115-R094 | Rollback implementation waits for an accepted existing capability-gate owner, identifier, route, selector and reconciliation contract. |
| WC115-R095 | AIR hashes RFC 8785/JCS request bytes excluding the digest field and uses the accepted PR-workload/relationship/operation/key identity tuple. |
| WC115-R096 | AIR resolves a trusted versioned/digested semantic catalogue whose entries fix patch type, operation, pointer template, value schema and cardinality. |
| WC115-R097 | AIR request, receipt and result preserve exact protocol, patch, prompt/model policy and model-decision provenance through reconciliation. |
| WC115-R098 | AIR result variants are closed and state-dependent; non-success results carry no operations and require closed reason codes. |
| WC115-R099 | Confidence is diagnostic only; material uncertainty produces an unresolved question and no authoritative or applicable patch. |
| WC115-R100 | AIR persists only identities, digest, receipt/result and references; transient raw content is encrypted, bounded by an accepted expiry and never logged. |
| WC115-R101 | One immutable AI evaluation corpus proves digest, path, provenance, injection, minimisation, confidence and unresolved-question safety at 100%. |
| WC115-R102 | A Founder-accepted security assertion profile fixes every allowed and denied caller/issuer/subject/audience/purpose/delegation/age/replay tuple. |
| WC115-R103 | A Founder-accepted assurance matrix fixes assurance, authentication age, reauthentication and revocation for every command and operation class. |
| WC115-R104 | A Founder-accepted source-freshness profile fixes age, clock skew, invalidation and unavailable behavior for every authoritative source. |
| WC115-R105 | Emergency Stop tests bind the exact existing endpoint, actors, independent dependencies, degraded behavior and numeric SLO. |
| WC115-R106 | Closed public/private error templates and reason allow-lists prohibit free-form protected text and prove body/timing anti-enumeration equivalence. |
| WC115-R107 | Rollback atomically fences new candidate work by epoch and drains/quarantines in-flight/outbox work while preserving reconciliation. |
| WC115-R108 | Private APIs require private ingress plus operation-level workload allow-lists and are absent from CORS, public gateways and browser bundles. |

## 10. Required Test And Acceptance Scope

### 10.1 Test families

| Test family | Required scope | Stable oracles |
|---|---|---|
| Unit | Every owner-local validator, canonicalizer, transition, mapper, generated-client adapter, replay and redaction branch | WC115-R055 |
| Contract | Provider and consumer tests for every operation in Sections 5.1-5.5, generated DTO equality and local-reference closure | WC115-R013-R028, WC115-R056 |
| Integration | Owner-realistic database/outbox/CE/WBE/AIR/adapter composition for all seven WC-114 sequences | WC115-R029-R038, WC115-R057 |
| Negative | Every public error, illegal transition, stale/partial/unknown state, tenant attack, digest drift, duplicate delivery and all WC-114 negative fixtures | WC115-R039-R050, WC115-R058-R060, CEW-NEG-001-011, CEW-POLICY-001 |
| Constitutional | Evidence First, Human Override/Stop, multi-tenancy, security and observability remain passing | Existing applicable CCT inventory plus WC115-R049/R062/R068 |
| Fitness | One executable test for every enterprise fitness rule | CEW-FIT-01-18 |
| Web | Typecheck, generated-client integration, component, browser journey and accessibility | WC115-R061 |
| Acceptance | Induction, Planning and continuous Operations across ready, partial, blocked, stale, unknown and recovery paths | WC115-R067 |
| Quality/security | Lint, format, type, SAST, dependency, secret, license, mutation where catalogued, and privacy-safe telemetry | WC115-R068 |
| Qualification | Complete applicable catalog inventory for one immutable candidate with exact evidence identity | WC115-R069-R071 |
| Specialist closure | Machine-readable owner profiles and repaired candidate schemas are contract-tested before their dependent stage | WC115-R077-R108 |

### 10.2 Acceptance scenarios

At minimum, executable acceptance must prove:

1. conversation contribution produces a proposal card, requires confirmation where applicable and
   commits an authoritative induction item only after BP validation and CE evidence;
2. initial plan and every material change require exact-version acknowledgement and separate
   operational admission;
3. ready Skills can proceed only when dependency, WBE and Decision Space isolation is proven;
4. deferred items name blocked Skills and cannot weaken a mandatory gate;
5. trial mode rejects consequential classes without a separately current trial-policy reference;
6. billing exhaustion blocks unfunded consequential work while Stop, rights, evidence access and
   read-only review remain;
7. credential loss scopes only proven-isolated Skills and otherwise fails closed;
8. two consecutive missed review periods create diagnosis/corrective proposal unless the adapter's
   accepted threshold is shorter;
9. rescheduling succeeds only inside the exact active-plan tolerance;
10. ambiguous provider outcome reconciles the original intent without duplicate dispatch;
11. every offered agent passes exact-version compatibility with complete evidence while activation
    remains false/default-off; and
12. rollback restores the prior projection without deleting any plan, command, owner fact or evidence.

## 11. Docker-Only Validation Commands

These are the only authoritative execution routes. The implementing office must replace
`<base-sha>` and `<head-sha>` with exact commits and supply changed paths as repeated
`--changed-file` arguments. Direct `pytest`, `dotnet test`, `npm`, `npx`, host Python/Node/.NET,
virtual environments and ad hoc `docker run`/`docker compose run` are diagnostic only and cannot
complete a requirement.

```bash
# Contract/ledger gate before implementation planning or first story START
python scripts/validation_control/local_catalog_gate.py \
  --gate requirement-ledger \
  --base <base-sha> --head <head-sha> \
  --git-common-dir "$(git rev-parse --git-common-dir)" \
  --changed-file work-contracts/WC-115-conversational-employment-implementation.md \
  --changed-file work-contracts/WC-115-requirements.yaml \
  --mode focused

# Repeat for each impact-selected focused gate during stories, for example:
python scripts/validation_control/local_catalog_gate.py \
  --gate test-business-platform \
  --base <base-sha> --head <head-sha> \
  --git-common-dir "$(git rev-parse --git-common-dir)" \
  --changed-file <changed-path> --mode focused

# Dependency-complete final immutable-candidate qualification
scripts/validation_control/run_wc104_qualification.sh

# Exact-head PR preparation after final push
scripts/prepare_pr_body.sh \
  --body-file /tmp/pr-body.md \
  --base origin/main \
  --expected-worktree "$PWD" \
  --expected-head "$(git rev-parse HEAD)"
```

The changed-path selection must include all touched BP, PR, AIR, WBE, adapter, web, database,
generated-client and test surfaces. The applicable final inventory must include their build, unit,
integration, REST contract, multi-tenant, PostgreSQL migration, CCT, web/type/accessibility, spec
lint, SAST, dependency, secret, license, observability, traceability, commit, authorization,
requirement-ledger and author-review gates. No applicable failure may be represented as PASS,
carried forward across an identity-changing input or omitted for elapsed time.

## 12. Requirement-To-Evidence Ledger

`work-contracts/WC-115-requirements.yaml` is the canonical requirement-to-evidence ledger. It must:

- bind the SHA-256 digest of this complete file;
- contain exactly WC115-R001 through WC115-R108 in this order;
- start each implementation row as `expected-fail` / `PLANNED`;
- name owner, direct test plan, dependencies, completion rule and bounded evidence class;
- replace plans with exact file, test result, catalog envelope, image/candidate digest, hosted run or
  immutable evidence references as work completes;
- distinguish local focused evidence, exact-candidate qualification and hosted-only evidence;
- never mark documentation, mocks, schema parsing or generated code alone as implementation PASS;
- declare `DONE` only when every row is `PASS` or explicitly `FOUNDER_RESERVED`; and
- remain privacy-safe and contain no secret, customer, conversation, prompt, plan or evidence payload.

## 13. Definition Of Done

WC-115 implementation is complete only when:

- every WC115 requirement is directly evidenced and the digest-bound ledger validates in Docker;
- all five candidate interfaces and every operation are implemented by the exact existing owner;
- all specialist closure profiles and the six WC-114 interface/fixture repairs in Section 7.5 are
  Founder-accepted, digest-bound and executable before their dependent stage;
- generated-client ownership, deterministic regeneration and no-duplicate-DTO checks pass;
- state, idempotency, reconciliation, privacy-safe errors, RLS, append-only history, outbox recovery,
  retention split, AI proposal-only constraints and Stop independence pass executable tests;
- CEW-FIT-01-18, CEW-NEG-001-011 and CEW-POLICY-001 pass as runtime/contract/journey oracles;
- all acceptance scenarios in Section 10.2 pass;
- one immutable candidate passes the complete applicable Docker qualification without reduced
  thresholds or invalid evidence carry-forward;
- the default-off candidate has not been activated, advertised as mandatory, deployed or exposed to
  customer traffic;
- author review repairs every finding and is bound to the exact remote head;
- the repository PR preparation control passes and the exact generated body is submitted; and
- the PR is open for Founder review without self-approval or merge.

## 14. Stop Conditions

Stop the affected stage immediately and report a blocker if:

1. explicit current-session Founder implementation authorization is absent;
2. a process-control digest, Work Contract digest, requirement ID or baseline ancestry check fails;
3. a required controlling or specialist input is missing, unaccepted, contradictory or changed;
4. implementation requires a new deployable, owner transfer, new capability, new protocol version or
   architecture/specification repair;
5. a candidate interface cannot preserve an existing canonical contract semantic;
6. tenant, relationship, assurance, purpose, audience, Stop, evidence or commercial authority cannot
   fail closed;
7. a generic contract requires DMA-, Trading-, Tutor- or other profession-specific platform fields;
8. generated ownership would expose a private client to web/mobile or duplicate wire DTOs;
9. persistence cannot preserve RLS, append-only history, owner separation, recovery or erasure split;
10. AIR can mutate authoritative state or a model output is required to decide readiness/success;
11. timeout, partial commit or provider ambiguity cannot reconcile without blind retry;
12. any error, log, trace, metric or evidence would expose protected content or resource existence;
13. any CEW fitness, negative, CCT, security, acceptance or applicable catalog gate fails;
14. validation requires host language tooling, unclassified Docker authority or a threshold reduction;
15. a repair after freeze is proposed without a new candidate and affected dependency rerun;
16. deployment, provider/cloud mutation, protocol activation, customer traffic or a default-on flag
    becomes necessary;
17. an unrelated defect or requested enhancement falls outside the exact dependency closure; or
18. exact-head author review and PR preparation cannot bind the remote 40-character head.
19. any Section 7.5 specialist profile or candidate-interface repair is absent, ambiguous or
    unaccepted when its dependent stage would start;
20. an implementation would need to select an issuer, assurance level, freshness age, retention
    period, transient-content expiry, customer copy, capability gate or rollback actor not fixed by
    an accepted input.

No stop may be bypassed by documenting a limitation, narrowing a test, broad catching, silent
default, success-shaped fallback, compensating in another component or expanding scope.

## 15. Rollback And Reversibility

### 15.1 Implementation-stage rollback

- Before candidate freeze, revert only the failed stage to the last executable milestone while
  retaining failure evidence.
- After candidate freeze, any code, dependency, generated client, schema, configuration or effective
  build-input repair creates a new candidate. Reuse only identity-compatible unaffected PASS evidence.
- Migration rollback must be tested from populated fixtures and must preserve append-only history,
  evidence references and owner facts. Destructive down migrations are prohibited.

### 15.2 Runtime rollback preparation

The implementation must provide, but this contract does not authorize executing, a rollback control
that disables candidate-only commands and restores the prior projection/version. It must leave
candidate records readable for reconciliation and preserve plans, commands, owner facts, outbox
records and CE evidence. Prior mandatory protocol support remains until separately authorized
activation, bounded observation and rollback acceptance complete.

### 15.3 Authorization consequence

Failure of rollback proof blocks implementation completion. Successful rollback proof does not
authorize activation, deployment or rollback execution in any environment.

## 16. Author Review

The Chief Solution Architect must re-read this complete contract against WC-114, all five candidate
interfaces, WC-114 state/failure/fitness rules, the Platform IT Expert process controls and the
Founder request. Review findings and repairs belong here before the final commit. The final review
must explicitly confirm requirements coverage, interface completeness, ownership, dependency order,
security, data, AI, product/accessibility, operability, tests, Docker execution, reversibility,
exclusions, stops and lack of activation/deployment authority.

### 16.1 Findings And Repairs

| Lens | Finding | Repair | Result |
|---|---|---|---|
| Internal consistency | The specialist precondition referenced nonexistent Sections 7.4-7.7 | Corrected it to the complete specialist package, now Sections 7.1-7.5 | RESOLVED |
| Client ownership | Private clients were assigned to an unspecified "existing" namespace that does not exist | Defined exact owner-local generated-client directories for BP and PR | RESOLVED |
| Docker execution | The first draft invoked a non-executable Python file directly | Corrected both catalog examples to use the repository's Python controller, which supplies the Docker runner | RESOLVED |
| Milestone traceability | Required `IB:` and `Constitutional:` fields lacked exact values for a Founder-direct assignment | Defined exact no-IB and minimum constitutional body values | RESOLVED |
| Scope and authority | Implementation, activation and deployment could be conflated | Reconfirmed separate current-session implementation authorization and retained absolute activation/deployment prohibition | PASS |
| Requirements coverage | Interfaces, owners, states, idempotency, reconciliation, errors, specialist controls, tests, evidence, rollback and stops were compared with WC-114 | All controlling obligations map to WC115-R001-R108 or the named CEW-FIT/CEW-NEG policy oracles | PASS |
| Independent executability | An implementer might otherwise need to invent order, surfaces, commands or acceptance | Exact dependencies, surfaces, client locations, stages, Docker entrypoints and completion rules are present | PASS |
| Data specialist review | Canonical stores, RLS roles, correction lineage, outbox/inbox, retention, calendar and migration semantics were underspecified | Added exact closure profiles, R077-R084, direct data oracles and blocking upstream calendar repair | RESOLVED |
| Security specialist review | Assertions, assurance, freshness, Stop binding, error templates, rollback fencing and private ingress lacked closed profiles | Added R102-R108 and made each accepted profile a stage prerequisite and hard stop | RESOLVED |
| AI specialist review | Canonical digest, trusted semantic catalogue, provenance, state union, uncertainty, minimisation and evaluation needed exact controls | Added R095-R101 and blocked WC115-02 until the accepted AI profile and AIR wire repair exist | RESOLVED |
| Product/Quality review | Copy authority, command/replay schemas, runtime negative oracles, Stop fitness, mixed-major fixture and evidence identity could permit invention or false PASS | Added R085-R094, six upstream repair requirements and exact evidence-envelope rules | RESOLVED |

### 16.2 Result

Post-specialist repair author review: **PASS**. The repair cycle intentionally converts unresolved
owner-policy values and WC-114 wire defects into explicit upstream prerequisites and hard stops; it
does not authorize the Platform IT Expert to invent or approve them.
