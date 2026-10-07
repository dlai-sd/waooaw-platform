# Conversational Employment Solution Contract

**Status:** Candidate for Founder acceptance - implementation and activation unauthorized
**Version:** 1.0.0-candidate.1
**Office:** Chief Solution Architect (INST-005)
**Work Contract:** WC-114
**Parent:** WC-113 §11.1; ADR-051; Conversational Employment Workspace 1.0-candidate
**Deployables:** Existing BP, PR, CE, WBE, AIR and web only; no new service

## 1. Decision Summary

The Conversational Employment Workspace is implemented as an additive protocol over the existing
Employment Relationship, Conversation Core and Relationship Workspace. Business Platform remains
the sole ordinary public facade and composition owner. Existing PR, CE and WBE contracts are reused.
Two private candidate contracts are added for AIR proposal generation and profession-neutral domain
semantics. No owner transfers authority and no mandatory protocol version changes through WC-114.

### 1.1 Contract inventory

| Boundary | Version | Disposition | Authority retained |
|---|---:|---|---|
| BP public employment workspace | `1.0.0-candidate.1` | ADD candidate slice | Relationship, phase, plan, readiness, command and public projection truth |
| Conversation Core | BP `1.10.0`; PR `1.3.0` | REUSE | Durable conversation and execution-event projection |
| Relationship Workspace | BP `1.10.0` | REUSE + compose | Public Plan, Work, Results, Usage/Budget, Rights and command truth |
| PR internal | PR `1.3.0` | REUSE | Execution facts, controls and reconciliation |
| CE internal | `constitutional.v1` | REUSE | Constitutional validation and evidence |
| WBE private | `1.1.0` + eligibility `1.0.0-candidate.1` | REUSE + ADD candidate slice | Commercial projection, Skill eligibility and consequence |
| AIR proposal-only | `1.0.0-candidate.1` | ADD candidate slice | Inference output only; no relationship authority |
| Domain adapter private | `1.0.0-candidate.1` | ADD generic candidate slice | Domain meanings, constraints and outcome interpretation |
| Web | generated BP candidate client | REUSE boundary | Presentation and local drafts only |

### 1.2 Build-versus-adopt decisions

| Concern | Decision | Reason |
|---|---|---|
| Relationship identity, conversation and workspace | REUSE | Existing approved components own the required truth |
| Durable orchestration | REUSE Temporal through current owner contracts | No new capability or service is required |
| CE evidence and validation | REUSE `constitutional.v1` | Existing RPCs support typed action context and append-only evidence |
| WBE eligibility and consequence | REUSE `1.1.0` projection/command family + ADD Skill eligibility projection | WBE owns commercial truth, but the existing string consequence is not sufficient for Skill-bounded readiness |
| AIR interpretation | ADD bounded proposal profile | Existing inference ownership is correct; exact typed patch envelope is missing |
| Domain employment semantics | ADD generic adapter profile | Existing DMA outcome adapter is too narrow for induction and planning |
| Public employment protocol | ADD BP subresource | Existing workspace needs exact phase/readiness/plan-version semantics |

## 2. Protected Policy Trace

| WC-113 guardrail | Contract enforcement |
|---|---|
| Partial readiness | BP eligibility is Skill-scoped; adapter isolation proof, WBE consequence and Decision Space must all be current |
| Trial operations | `TRIAL_ADVISORY` permits only simulated, read-only or advisory operation classes |
| Material goal change | Classification `MATERIAL` forces a new plan version and `REASSESSMENT_REQUIRED` |
| Deferred dependencies | Deferral requires blocked Skill references and a non-deferrable-gate check |
| Plan acknowledgement | Acceptance command is required for initial and material versions and irreversible consequences |
| Performance failure | Two missed periods create mandatory diagnosis/corrective-proposal work unless adapter threshold is shorter |
| Billing exhaustion | WBE consequence blocks unfunded consequential work; rights, Stop and read-only review remain |
| Calendar authority | Reschedule command is valid only within the agreed tolerance returned with the active plan |
| Credential loss | Adapter isolation proof scopes the block; unknown isolation blocks dependent work |
| Mandatory readiness override | Contract has no override operation for constitutional, safety, evidence, tenant, authority or financial gates |

## 3. Component Responsibilities

| Component | Must | Must not |
|---|---|---|
| BP Employment Context | Authorize relationship, compose owner truth, version plan/readiness, own public commands | Infer tenant from input, execute work, recalculate WBE or accept AIR output as truth |
| Conversation Core | Persist one timeline and typed candidate-card references | Treat chat completion as readiness or plan agreement |
| Relationship Workspace | Project phases, items, readiness, plans, commands and reconciliation | Create a second relationship or phase-specific source of truth |
| PR | Coordinate professional execution and AIR/adapter calls after BP responsibility is durable | Own plan, readiness, billing, public errors or customer relationship authority |
| CE | Validate consequential action context and append evidence before governed success | Expose REST/public ingress or own business projection |
| WBE | Return allowance, forecast, eligibility and commercial consequence | Permit BP, web or adapter to recompute commercial truth |
| AIR | Return a typed candidate patch with confidence, assumptions and provenance | Mutate authoritative state or claim confirmation, readiness or success |
| Domain adapter | Return domain requirements, constraints, materiality, isolation and outcomes | Own public lifecycle, billing, CE evidence, ordering or relationship truth |
| Web | Use generated BP client, present owner states and hold unconfirmed drafts | Call private owners, authorize from cache or collapse stale/unknown into success |

## 4. Operation Families

### 4.1 BP public candidate operations

Root: `/api/v1/employment/relationships/{relationshipId}/workspace/employment`

| Operation | Method/path | Success |
|---|---|---|
| `getEmploymentWorkspace` | `GET /` | Exact phase/readiness/plan/operations snapshot |
| `getEmploymentPhase` | `GET /phases/{phase}` | One phase projection and requirement-derived progress |
| `getEmploymentReadiness` | `GET /readiness` | Four readiness facets with unmet conditions and sources |
| `getEmploymentPlan` | `GET /plans/current` | Current accepted/draft plan version and materiality rules |
| `getEmploymentPlanVersion` | `GET /plans/{planVersion}` | Immutable historical plan projection |
| `submitEmploymentCommand` | `POST /commands` | Durable command receipt; `202` is responsibility, not success |
| `getEmploymentCommand` | `GET /commands/{commandId}` | Reconciled owner-by-owner outcome |

The exact candidate wire contract is
`architecture/reference/api-specs/conversational-employment-business-platform.openapi.yaml`.

### 4.2 Conversation Core reuse

| Existing operation | Employment use |
|---|---|
| `POST .../conversation/messages` | Customer contribution; may create a candidate-patch card |
| `GET .../conversation/messages` | Durable professional conversation |
| `GET .../conversation/stream` | BP-authoritative candidate/command/projection events |
| `POST .../messages/{messageId}/retry` | Reconcile same contribution; never create a second logical message |
| `DELETE .../executions/{executionId}` | Cancel interpretation/execution; never release Stop |

Candidate patches carry references in cards; the transcript is not the authoritative patch store.

### 4.3 PR reuse

| Existing PR `1.3.0` operation | Employment use |
|---|---|
| `startConversationExecution` | Begin professional interpretation after BP durable acceptance |
| `streamConversationExecution` | Return typed candidate-card events to BP |
| `getRelationshipExecutionProjection` | Supply execution facts for Operations projection |
| `submitRelationshipExecutionControl` | Pause/cancel/reassess affected execution under BP control |
| `getRelationshipExecutionControl` | Reconcile ambiguous internal control outcomes |

PR must bind admitted agent/version, protocol candidate version, manifest version, plan version,
Decision Space version and operation class before AIR or adapter dispatch.

### 4.4 CE reuse

No CE RPC is added. BP and PR use:

- `ValidateAction` for consequential command/action authorization;
- `EvaluatePolicy` for readiness/material-change policy evaluation where the approved evaluator
  catalogue permits it;
- `RecordEvidence` for proposed, accepted/rejected and executed constitutional states;
- `GrantAuthorityLicense` / `RevokeAuthorityLicense` only for actual authority changes; and
- `TriggerEmergencyStop` through the existing independent Stop path.

`action_instance_id` is stable across retries and all evidence transitions for one logical command.
The `action_context`/`action_parameters` canonical payload includes relationship, subject, plan,
manifest, requirement-set, Decision Space and WBE source versions. A CE error cannot be translated
to public success.

### 4.5 WBE reuse

| Existing WBE `1.1.0` operation | Employment use |
|---|---|
| `getRelationshipCommercialProjection` | Current allowance, spend, forecast, eligibility and consequence |
| `submitRelationshipCommercialCommand` | Commercial owner step when a command changes funded work |
| `getRelationshipCommercialCommand` | Reconcile WBE commit status before retry |
| `getEmploymentCommercialEligibility` | Return exact Skill-scoped eligibility and preserved constitutional/read-only paths |

BP relays WBE values and freshness. `STALE`, `UNKNOWN`, `UNAVAILABLE` and `BLOCKED` never become zero,
empty allowance or eligible.

The additive eligibility wire contract is
`architecture/reference/api-specs/conversational-employment-wbe.openapi.yaml`. It does not replace
the `1.1.0` projection or command family.

### 4.6 AIR proposal-only candidate operations

| Operation | Purpose |
|---|---|
| `proposeEmploymentPatch` | Interpret a bounded contribution into one typed, non-authoritative patch |
| `getEmploymentPatchProposal` | Reconcile the immutable proposal result |

The exact contract is
`architecture/reference/api-specs/conversational-employment-ai-runtime.openapi.yaml`.

### 4.7 Domain-adapter candidate operations

| Operation | Purpose |
|---|---|
| `getEmploymentInterfaceManifest` | Return exact immutable protocol/manifest support |
| `getInductionRequirementSet` | Return profession-specific requirements in generic envelopes |
| `validatePlanCandidate` | Validate domain semantics without accepting the plan |
| `classifyMaterialChange` | Return materiality and affected Skill/work references |
| `evaluateDependencyIsolation` | Prove bounded Skill isolation or return unknown |
| `getPerformanceAssessment` | Return business-outcome and agent-performance meanings separately |

The exact generic contract is
`architecture/reference/api-specs/conversational-employment-domain-adapter.openapi.yaml`.

## 5. Canonical Public Schemas

### 5.1 Aggregate

`EmploymentWorkspaceV1` requires:

- `schemaVersion`, `protocolVersion`, `relationshipId`, `workspaceVersion`;
- `agentType`, `agentVersion`, `manifestVersion`;
- four `readiness` facets and three `phases`;
- `currentPlan`, `operations`, `sources`, `limitations`;
- `recommendedNextAction`, `availableCommands`;
- `authoritativeCursor`, `producedAt`.

Every source has `owner`, `contractVersion`, `sourceVersion`, `state`, `observedAt`, optional
`validUntil` and optional customer-safe limitation. Missing owner data is an explicit source entry.

### 5.2 Item and progress

`EmploymentWorkspaceItemV1` requires identity, phase, label, mandatory flag, state, reason,
accountable owner, blocked effects, source state/freshness and available commands. `COMPLETED`
requires an owner-confirmed completion reference; transport acceptance or model output is invalid.

`RequirementProgressV1` contains mandatory/optional totals and completed counts plus blocked and
deferred counts. It never contains a model-generated percentage.

### 5.3 Typed patch

`EmploymentPatchProposalV1` is immutable and requires:

- proposal, relationship, contribution, protocol and manifest identities;
- `patchType`: `INDUCTION_CONTEXT`, `GOAL`, `PLAN`, `CALENDAR`, `DEPENDENCY`,
  `OPERATING_CYCLE` or `CORRECTIVE_PROPOSAL`;
- `operations[]` limited to JSON-Patch-like `ADD`, `REPLACE`, `REMOVE` over an allow-listed semantic
  path catalogue owned by BP;
- confidence, assumptions, unresolved questions, source references and model-policy reference;
- `PROPOSED` state only.

BP rejects unknown paths, owner fields, authority fields, evidence states, billing calculations and
direct readiness mutations.

### 5.4 Command

`EmploymentCommandRequestV1` is a closed discriminator:

- `CONFIRM_INDUCTION_ITEM`
- `DEFER_INDUCTION_ITEM`
- `APPLY_CANDIDATE_PATCH`
- `SUBMIT_PLAN_FOR_REVIEW`
- `ACCEPT_PLAN_VERSION`
- `ACKNOWLEDGE_MATERIAL_CHANGE`
- `RESCHEDULE_WITHIN_TOLERANCE`
- `REQUEST_REASSESSMENT`
- `ACKNOWLEDGE_CORRECTIVE_PROPOSAL`

There is intentionally no readiness override, force-success, arbitrary action or destination field.

## 6. State Machines

### 6.1 Phase item

```text
PROPOSED -> READY -> IN_PROGRESS -> COMPLETED
             |          |  |  |
             |          |  |  +-> OUTCOME_UNKNOWN -> IN_PROGRESS | COMPLETED | BLOCKED
             |          |  +----> WAITING_ON_CUSTOMER | WAITING_ON_AGENT | WAITING_ON_PLATFORM
             |          +-------> BLOCKED
             +------------------> DEFERRED
ANY NONTERMINAL -> CANCELLED | SUPERSEDED
```

`COMPLETED`, `CANCELLED` and `SUPERSEDED` are terminal for that item version.

### 6.2 Induction readiness

```text
NOT_STARTED -> IN_PROGRESS -> READY_WITH_DEFERRED_ITEMS -> READY
                   |                    |                   |
                   +--------------------+------------------> BLOCKED
READY | READY_WITH_DEFERRED_ITEMS -> STALE_REASSESSMENT_REQUIRED -> IN_PROGRESS
```

`READY_WITH_DEFERRED_ITEMS` is rejected when any deferred item weakens a mandatory constitutional,
safety, evidence, tenant, authority or financial gate.

### 6.3 Plan

```text
DRAFT -> GROOMING -> READY_FOR_REVIEW -> AGREED -> ACTIVE -> COMPLETED
  |         |              |              |         |
  +---------+--------------+--------------+--------> BLOCKED
AGREED | ACTIVE -> SUPERSEDED
ANY NONTERMINAL -> CANCELLED
```

Material change creates a new `DRAFT` version; the prior active version remains immutable and
affected work becomes `REASSESSMENT_REQUIRED`.

### 6.4 Operations eligibility

```text
LOCKED -> ELIGIBLE -> ACTIVE -> PAUSED -> ACTIVE
   |         |          |         |
   +---------+----------+--------> BLOCKED
ELIGIBLE | ACTIVE | PAUSED -> REASSESSMENT_REQUIRED -> LOCKED | ELIGIBLE
ANY -> TERMINATED
```

The C-034 relationship lifecycle is independent and unchanged.

### 6.5 Candidate patch

```text
PROPOSED -> VALIDATED -> AWAITING_CONFIRMATION -> APPLIED
    |           |                |
    +-----------+----------------+-> REJECTED
    +------------------------------> SUPERSEDED
```

AIR can produce only `PROPOSED`. BP owns every later state.

### 6.6 Command and reconciliation

```text
ACCEPTED -> VALIDATING -> DISPATCHED -> COMPLETED
    |            |           |
    |            |           +-> PARTIAL -> RECONCILING -> COMPLETED | BLOCKED | REJECTED
    |            +-------------> REJECTED | CONFLICT | BLOCKED
    +---------------------------> UNKNOWN -> RECONCILING
```

`202` maps only to `ACCEPTED`. `COMPLETED` requires all required owner commits and CE evidence.

## 7. Interaction Sequences

### 7.1 Conversation to authoritative induction item

1. Web sends a contribution through generated BP Conversation client with one idempotency key.
2. BP durably accepts the message, then asks PR to interpret it.
3. PR binds admitted versions and calls AIR `proposeEmploymentPatch`.
4. AIR returns `PROPOSED`; PR emits the typed proposal reference to BP.
5. BP validates schema/path ownership and asks the domain adapter for requirement semantics.
6. BP projects a candidate card; no authoritative state changes.
7. Customer confirms where required.
8. BP validates expected versions and mandatory gates, records CE evidence when consequential, then
   commits the new BP item/workspace version.

### 7.2 Plan acceptance

1. BP obtains current induction, adapter, WBE, Decision Space and evidence source versions.
2. Adapter validates domain semantics; WBE remains owner of commercial assumptions.
3. BP produces impact summary and exact immutable plan version.
4. Customer submits `ACCEPT_PLAN_VERSION` with explicit acknowledgement and expected versions.
5. BP validates actor/assurance, calls CE, commits evidence, then marks the exact plan `AGREED`.
6. Operational admission runs separately; plan agreement does not authorize execution.

### 7.3 Material goal change

1. Contribution produces a candidate patch.
2. Adapter classifies materiality and affected Skills/work; BP independently enforces protected
   materiality categories.
3. If material, BP creates a new draft plan, relocks affected work and projects impact.
4. Existing plan remains immutable; unaffected work proceeds only when independently bounded.
5. Renewed explicit agreement and operational admission are required.

### 7.4 Operational admission and action

1. BP composes exact relationship, induction, plan, dependency, WBE, Decision Space, Stop and
   measurement source versions.
2. BP calculates eligibility only from owner results; unknown/stale mandatory sources fail closed.
3. BP records the gate decision through CE where consequential.
4. PR receives admitted immutable versions and performs continuous action checks.
5. Trial mode rejects consequential operation classes unless a separate trial-policy reference is
   present and current.
6. PR executes, reconciles provider intent/outcome and emits facts; BP alone updates public state.

### 7.5 Billing exhaustion

1. WBE returns the current consequence and source version.
2. BP blocks the affected unfunded consequential work and projects the WBE-owned reason.
3. Constitutional rights, Emergency Stop, evidence access and read-only review remain available.
4. Resumption requires a fresh WBE projection and a new operational admission decision.

### 7.6 Ambiguous external outcome

1. PR persists intent and immutable provider correlation before dispatch.
2. Timeout or disconnect yields `OUTCOME_UNKNOWN`, never success or automatic retry.
3. PR reconciles by the same provider correlation and invocation identity.
4. BP shows accountable owner and limitation.
5. Retry is legal only after authoritative no-commit or idempotent replay is proven.

## 8. Idempotency, Concurrency And Reconciliation

Every mutation binds:

```text
authenticated actor
+ server-derived tenant
+ relationship
+ operation family
+ idempotency key
+ canonical payload hash
+ expected workspace/plan/manifest/Decision Space/WBE source versions
```

- Same identity and hash replays the prior receipt/outcome.
- Same identity with a different hash returns conflict and performs no owner call.
- BP derives stable owner-scoped keys and one CE `action_instance_id`.
- Expected-version conflict returns current safe versions and requires a fresh read.
- A timeout after possible commit enters `UNKNOWN`; callers reconcile the existing command.
- Partial owner commit freezes incompatible commands until reconciliation.
- Reconciliation can report authoritative success, rejection or block; it cannot manufacture
  success or delete prior records.

## 9. Error Contract

Public errors use RFC 9457 and the candidate `EmploymentProblemDetailV1`.

| Code | HTTP | Meaning |
|---|---:|---|
| `EMPLOYMENT_NOT_ACCESSIBLE` | 404 | Absent, inaccessible and cross-tenant are indistinguishable |
| `EMPLOYMENT_INVALID_REQUEST` | 400 | Shape or semantic validation failed |
| `EMPLOYMENT_ASSURANCE_REQUIRED` | 403 | Accepted assurance is insufficient |
| `EMPLOYMENT_VERSION_CONFLICT` | 409 | Expected authoritative version changed |
| `EMPLOYMENT_IDEMPOTENCY_CONFLICT` | 409 | Key was reused with a different canonical hash |
| `EMPLOYMENT_REASSESSMENT_REQUIRED` | 409 | Material/stale source relocked affected work |
| `EMPLOYMENT_BLOCKED` | 423 | Known policy/dependency/commercial condition blocks action |
| `EMPLOYMENT_OUTCOME_UNKNOWN` | 503 | Commit may have occurred; reconcile existing command |
| `EMPLOYMENT_SOURCE_UNAVAILABLE` | 503 | Required owner is unavailable |
| `EMPLOYMENT_PROTOCOL_UNSUPPORTED` | 503 | Exact protocol/manifest major is unsupported |

Private errors add owner-safe diagnostics but never expose customer PII, provider secrets, tenant
existence or internal policy text. BP maps private errors to the stable public vocabulary.

## 10. Generated-Client Boundaries

| Contract | Generated consumer | Prohibited consumer |
|---|---|---|
| BP public candidate | Web server/client boundary and approved customer channels | PR, AIR, WBE or adapters as authority shortcuts |
| PR existing private | BP service client | Browser/mobile |
| WBE existing private | BP service client | Browser, PR, AIR, domain adapter |
| WBE eligibility candidate | BP service client | Browser, PR, AIR, domain adapter |
| AIR candidate private | PR service client | BP, web, domain adapter |
| Domain adapter candidate private | BP for validation/projection; PR only for admitted execution semantics explicitly named by BP | Browser, AIR, cross-relationship adapter |
| CE proto | BP and PR generated gRPC clients | Browser, WBE, AIR, domain adapter |

Generated artifacts are implementation outputs and are not created by WC-114. Later implementation
must pin generator version and spec digest, place generated code behind an owner adapter and prohibit
hand-written duplicate DTOs.

## 11. Observability

Every gate, command and reconciliation span/event includes:

- privacy-safe tenant/relationship correlation;
- protocol, agent, manifest, requirement-set and plan versions;
- gate/operation/subject and operation class;
- owner source versions, states and freshness;
- decision, unmet condition codes and accountable recovery owner;
- command, action-instance and reconciliation identities;
- evidence reference/state, never evidence payload;
- latency/timeout class and retry disposition.

Dashboards and alerts must keep separate:

1. platform availability;
2. gate-evaluation health;
3. blocked relationships by reason;
4. stale owner projections;
5. reconciliation backlog/age;
6. provider failure;
7. agent performance; and
8. customer business outcomes.

No metric label contains raw tenant, customer, prompt, credential or plan content.

## 12. Compatibility, Rollout And Rollback

- Candidate contracts use semantic versions; additive optional fields may change a minor version,
  incompatible schema/semantic changes require a major version.
- Unknown major versions fail closed. Unknown additive fields are ignored only where the schema
  explicitly permits forward compatibility; these candidate schemas default to closed objects.
- The BP public candidate is not advertised as mandatory until downstream contracts and all-agent
  conformance pass.
- Rollout order: accepted specialist contracts, frozen schema, implementation WC, generated clients,
  owner contract tests, agent manifests/scenarios, compatibility scan, shadow projection, Founder
  activation.
- Prior mandatory version remains supported through a bounded rollback window.
- Rollback blocks new candidate-only commands and restores the prior projection; it does not delete
  plans, commands, owner facts or CE evidence.
- Mixed conformance cannot be activated and no offered agent is grandfathered after activation.

## 13. Downstream Handoff Constraints

### 13.1 Data Architect

Must define canonical persistence/projection ownership, provenance, version columns, tenant/RLS
policy, correction/supersession, retention/erasure split, calendar instant/local-time semantics,
outbox/reconciliation records, recovery and migration. Must not merge owner ledgers, store secrets in
workspace records or turn transcript/model output into authority.

### 13.2 Security Architect

Must define accepted actor/service assertions, assurance by consequence, anti-enumeration,
anti-bypass, delegated audience/purpose binding, credential-reference minimisation, stale-state and
cross-tenant abuse tests, Stop independence, and private error/log redaction. Must not add a readiness
override or let cached/offline state authorize.

### 13.3 AI Architect

Must define prompt/model policy, semantic path catalogue, confidence interpretation, provenance,
assumption and unresolved-question rules, injection resistance, minimisation and evaluation. AIR
must remain proposal-only and cannot directly mutate relationship, readiness, plan, billing,
authority or evidence state.

### 13.4 Product Office

Must define first-release journey, customer vocabulary, visual hierarchy, accessibility and
acceptance scenarios while preserving every owner/state distinction. Product may not replace
conversation with forms, hide pending reasons/owners/blocked effects, collapse stale/partial/unknown
into success, or alter protected guardrails.

## 14. Implementation-Readiness Test

| Question | Result |
|---|---|
| Must an implementer invent a deployable or owner? | NO |
| Must an implementer invent a public/private path or operation family? | NO |
| Must an implementer invent a state or transition? | NO |
| Must an implementer invent idempotency or reconciliation? | NO |
| Must an implementer invent failure, telemetry, rollout or rollback behavior? | NO |
| Are Data/Security/AI/Product-owned decisions explicitly deferred to their offices? | YES |
| Does this package authorize implementation or activation? | NO |

Implementation remains blocked until the downstream contracts are accepted and a later bounded Work
Contract receives explicit current-session Founder authorization.
