# Conversational Employment Workspace

**Status:** Proposed Enterprise Architecture - Founder review required  
**Version:** 1.0-candidate  
**Author:** Chief Enterprise Architect (INST-004)  
**Work Contract:** WC-113  
**Decision:** ADR-051  
**Constitutional basis:** C-023, C-034, C-036-C-039, C-041, C-048-C-049, C-059, C-070, C-079, C-088 and C-094

## 1. Purpose And Boundary

The Conversational Employment Workspace is the universal customer relationship model for every
WAOOAW Digital Professional. It combines:

1. one durable professional conversation;
2. one authoritative visual relationship workboard; and
3. one evidence-backed readiness protocol.

It covers three continuous phases:

1. **Onboard, Induct and Groom**;
2. **Goal, Plan, Milestone and Calendar Formation**; and
3. **Operations, Billing and Performance Management**.

The workspace is a composition of existing platform responsibilities. It is not a new deployable
service, project-management product, CRM, accounting system or institutional Goal Orchestrator.

### 1.1 Required customer questions

At every point, the workspace must answer:

1. What are we trying to achieve?
2. What has been completed?
3. What is in progress?
4. What is pending?
5. Why is each pending item required?
6. Who owns the next action?
7. What is blocked or affected?
8. What evidence supports the displayed state?
9. How current is the information?
10. What can I do next?

### 1.2 Explicit exclusions

- no browser-owned relationship, plan, readiness, billing or performance truth;
- no transcript-derived success without deterministic owner confirmation;
- no profession-specific field in the generic workspace;
- no new C-034 lifecycle state;
- no agent self-activation, self-approval or self-expansion of authority;
- no replacement of CE, WBE, PR or domain-owner authority;
- no mandatory protocol activation through this candidate.

## 2. Derivation And Obligation Ledger

| Obligation | Derivation | Existing reusable structure | Architecture gap closed here |
|---|---|---|---|
| Conversation is a complete configuration path | C-039; capability 1.7; AD-013 | Conversation Core; AEEC-05 | Extend the invariant across induction, planning and operations |
| Customer sees business meaning, not platform internals | DP-011; C-037; C-042 where applicable | Relationship Workspace; vocabulary adapters | One common visual phase projection |
| Onboarding learns customer context before work | Capability 1.5; AD-011 | Agent onboarding flows and DMA profiling | Deterministic induction readiness |
| Goals remain customer business outcomes | C-037; capability 4.5; AD-012 | Relationship Goal and Results | Versioned goal/plan readiness and reassessment |
| Skills remain independently governable | C-036; DP-012 | Skill lifecycle and Decision Space subset | Skill-bounded dependencies and operational eligibility |
| Billing follows lifecycle and Skill truth | C-038, C-051, C-088; AD-014 | WBE and billing profiles | WBE truth composed into conversational operations |
| Consequential success requires evidence | C-023; AD-002; DP-001 | CE and Evidence First | Evidence-backed gate decisions |
| Missing capability or dependency is disclosed | C-049, C-079 | blocked/unavailable workspace states | Pending reason, blocked effect and recovery owner |
| Runtime stays profession-neutral | C-035; AD-007; DP-003 | PR and domain adapter pattern | Versioned employment interface manifest |
| Every offered agent tracks mandatory base contract | C-094; ADR-035 | PAC version pinning and gap scan | Atomic all-agent migration gate |
| Customer can stop in every phase | C-001, C-038 | Emergency Stop and lifecycle controls | Stop remains outside readiness and billing gates |
| Performance improves from evidence | C-037; capability 3.4 | domain outcomes and performance assessment | cycle-level learn/change/review projection |

No new business capability is invented. The architecture composes already approved capabilities and
closes their cross-phase interface and readiness gap.

## 3. Structural Model

```text
Customer channels
  Web | WhatsApp | future mobile
                  |
                  v
Business Platform public facade
  Employment Relationship
  Conversation Core
  Relationship Workspace
  Readiness and plan governance
                  |
     +------------+------------+------------------+
     |            |            |                  |
     v            v            v                  v
    CE           WBE           PR         Domain adapter
 authority/   commercial    execution      induction,
 evidence       truth         truth       plan/outcomes
                                  |
                                  v
                                AIR
                         interpretation/proposals
```

### 3.1 Minimum structure principle

No new deployable is required:

- Conversation Core already supplies durable conversation.
- Relationship Workspace already supplies Plan, Goals, Work, Results, Usage/Budget and Rights.
- Business Platform already owns the public relationship projection and commands.
- PR, CE, WBE and AIR already have distinct execution, evidence, commercial and inference roles.

The missing structure is an explicit common protocol, readiness evaluation and agent-conformance
contract.

## 4. Common Visual Phase Projection

The following is a conceptual semantic contract, not a wire schema:

```text
ConversationalPhaseWorkspace
  relationshipRef
  phase
  phaseStatus
  progressBasis
    mandatoryTotal
    mandatoryCompleted
    optionalTotal
    optionalCompleted
    blockedCount
    deferredCount
  currentGoalRef?
  currentPlanVersion?
  completedItems[]
  inProgressItems[]
  pendingItems[]
    itemRef
    customerLabel
    reasonRequired
    accountableOwner
    dueMeaning?
    blockedEffects[]
    dependencyState
    evidenceState
    sourceFreshness
    availableActions[]
  blockers[]
  assumptions[]
  dependencies[]
  milestones[]
  calendarCommitments[]
  billingSummary?
  performanceSummary?
  evidenceState
  sourceFreshness
  limitations[]
  recommendedNextAction?
  availableCommands[]
```

### 4.1 Progress rules

Progress must be:

- derived from declared requirement and item state;
- explainable as counts and named conditions;
- scoped to one phase, plan version or operating cycle;
- separated into mandatory and optional work; and
- invalidated when a material source becomes stale or superseded.

An LLM-generated percentage, elapsed-time estimate or message count cannot authorize progress or gate
success.

### 4.2 Item states

```text
PROPOSED
READY
IN_PROGRESS
WAITING_ON_CUSTOMER
WAITING_ON_AGENT
WAITING_ON_PLATFORM
BLOCKED
COMPLETED
DEFERRED
CANCELLED
SUPERSEDED
OUTCOME_UNKNOWN
```

`COMPLETED` means the owning domain confirmed the required outcome. Transport acceptance, model
response, optimistic UI state or pending evidence is not completion.

### 4.3 Pending-item minimum

Every mandatory pending item names:

- what is needed in customer vocabulary;
- why it is needed;
- the accountable owner;
- what goal, milestone, Skill or action it blocks;
- whether work can proceed partially;
- due meaning, if any;
- authoritative state and freshness;
- available action or recovery owner.

## 5. Phase 1 - Onboard, Induct And Groom

### 5.1 Purpose

Build enough confirmed understanding for the professional to propose responsible goals and plans.
Induction is consultative professional discovery, not a disguised technical form.

### 5.2 Common induction subjects

- customer and organization identity;
- business model, products/services and customer vocabulary;
- target customers and desired business outcomes;
- existing processes, channels, prior work and standards;
- baseline outcome evidence and measurement limitations;
- Decision Space, budget, approval and review preferences;
- credentials, integrations, assets and external dependencies;
- constraints, legal/domain rules and prohibited actions;
- confirmed facts, inferences, assumptions and open questions;
- agent limitations and deferred capabilities.

### 5.3 Induction item provenance

Each item is classified:

```text
CONFIRMED_BY_CUSTOMER
CONFIRMED_BY_AUTHORITY_SOURCE
INFERRED_PENDING_CONFIRMATION
ASSUMPTION_OWNER_BOUND
UNKNOWN
NOT_APPLICABLE
DEFERRED_WITH_EFFECT
```

Inference is useful for reducing customer burden but never silently becomes fact.

### 5.4 Induction readiness

```text
NOT_STARTED
IN_PROGRESS
READY_WITH_DEFERRED_ITEMS
READY
BLOCKED
STALE_REASSESSMENT_REQUIRED
```

`READY_WITH_DEFERRED_ITEMS` is valid only when:

- every deferred item names affected Skills and blocked effects;
- no constitutional, tenant, evidence, safety, authority or financial gate is deferred;
- unaffected work is independently bounded; and
- the customer sees the limitation.

### 5.5 Induction gate

Required evidence includes:

- minimum agent-declared context confirmed;
- material assumptions resolved or owner-bound;
- baseline recorded or explicitly unavailable with impact;
- required dependencies identified and classified;
- Decision Space proposal available;
- limitations disclosed;
- customer-facing induction summary reviewed; and
- CE evidence committed where the decision is consequential.

## 6. Phase 2 - Goal, Plan, Milestone And Calendar Formation

### 6.1 Conversation-to-plan flow

```text
Customer contribution
  -> professional interpretation
  -> typed candidate patch
  -> deterministic shape and owner validation
  -> policy/authority/commercial validation where applicable
  -> customer-visible impact summary
  -> explicit acceptance where required
  -> authoritative new plan version
  -> visual projection refresh
```

The AI Runtime may prepare candidate meaning. Business Platform owns plan and goal truth.

### 6.2 Plan minimum

A plan version contains:

- business outcome and accountable owner;
- baseline, target, measure, attribution boundary and review period;
- professional recommendation and rationale;
- milestones and completion criteria;
- intended work and Skill mapping;
- calendar commitments, cadence and review points;
- dependencies, credentials, assets and customer decisions;
- Decision Space and approval mode references;
- budget/allowance assumptions and WBE references;
- risks, assumptions, limitations and failure conditions;
- performance measurement path; and
- change and cancellation consequences.

### 6.3 Plan states

```text
DRAFT
GROOMING
READY_FOR_REVIEW
AGREED
ACTIVE
BLOCKED
SUPERSEDED
CANCELLED
COMPLETED
```

`AGREED` is not authority to execute. Operational admission and continuous action gates remain
separate.

### 6.4 Calendar semantics

The generic calendar role must support:

- customer and operating timezone;
- local date/time plus authoritative instant;
- recurrence and review cadence;
- business/market/platform availability windows;
- dependency-relative timing;
- customer-agreed rescheduling tolerance;
- missed-window policy;
- cancellation versus rescheduling;
- immutable change history; and
- domain adapter constraints.

Trading market calendars, tutoring lesson recurrence and DMA publishing calendars are adapter-owned
specializations.

### 6.5 Material change

A change is material when it affects:

- business outcome, baseline or target;
- budget ceiling or commercial consequence;
- Decision Space or approval mode;
- milestone order or irreversible deadline;
- active Skill set;
- credential/dependency availability;
- regulated or safety boundary;
- measurement or attribution basis; or
- more than the agreed calendar tolerance.

Material change creates a new plan version, explicit impact summary and affected-work reassessment.

### 6.6 Plan readiness

```text
NO_PLAN
DRAFT
GROOMING
READY_FOR_REVIEW
AGREED
BLOCKED
STALE_REASSESSMENT_REQUIRED
```

Plan acceptance requires current induction evidence, complete minimum plan fields, dependency
classification, customer agreement and constitutional/commercial evidence where applicable.

## 7. Phase 3 - Operations, Billing And Performance

### 7.1 Purpose

Operate the agreed plan while continuously showing what was planned, completed, in progress,
pending, blocked, spent, learned and proposed next.

Operations is continuous. Completion applies to a work item, milestone, campaign, billing period,
review period or goal, not to the entire phase.

### 7.2 Operating-cycle projection

Each cycle exposes:

- agreed plan version;
- planned work;
- scheduled and active work;
- completed work and deliverables;
- pending customer, agent, platform or provider actions;
- exceptions and reconciliations;
- WBE-owned allowance, spend, forecast and consequence;
- domain-owned outcome measures and attribution limits;
- agent performance separate from external business outcome;
- learning and proposed correction;
- next review and customer decision.

### 7.3 Operations eligibility

```text
LOCKED
ELIGIBLE
ACTIVE
PAUSED
BLOCKED
REASSESSMENT_REQUIRED
TERMINATED
```

Operational admission requires:

1. agent type publication gate;
2. current exact agent/version admission;
3. current billing profile and commercial eligibility;
4. valid relationship admission;
5. induction readiness;
6. agreed current plan;
7. ready required dependencies;
8. current Decision Space and authority;
9. reachable Emergency Stop;
10. performance baseline/measurement path or explicit bounded limitation; and
11. committed gate evidence.

### 7.4 Billing composition

WBE owns:

- allowance and actual use;
- customer spend;
- ceilings and thresholds;
- forecast and assumptions;
- price, invoice and payment state;
- commercial consequences.

BP relays WBE truth in the operating workspace. Agent, BP and web do not recalculate it. Billing
failure never blocks Emergency Stop, evidence access or other constitutional rights.

### 7.5 Performance composition

The domain adapter supplies:

- business outcome identity and label;
- baseline, target, period and observed value;
- attribution basis and confidence;
- evidence references;
- external factors and limitations;
- agent-performance evidence;
- recommended correction.

BP owns the public Results meaning after validation. Technical execution metrics cannot substitute
for business outcomes.

## 8. Gate Taxonomy

| Gate | Subject | Owner | Required result | Prohibited substitution |
|---|---|---|---|---|
| Agent Type Publication | Professional type/version | Agent lifecycle governance plus Founder-required approvals | Offerable exact version | Relationship success or simulation alone |
| Relationship Admission | Tenant/customer/relationship | BP, CE and WBE where applicable | Valid trial/hire relationship | Login, conversation or payment transport alone |
| Induction Readiness | Relationship and affected Skills | BP using agent manifest/domain evidence | READY or bounded READY_WITH_DEFERRED_ITEMS | Transcript length or model confidence |
| Plan Acceptance | Exact plan version | BP with customer/CE/WBE decisions | AGREED exact version | Draft card or ordinary chat acknowledgement |
| Operational Admission | Relationship/Skill set | BP composed from owners | ELIGIBLE with evidence | Agent type pass or plan agreement alone |
| Continuous Action | Exact action/work item | PR caller plus CE/WBE/owner checks | Authorized current execution | Prior action, stale plan or capability |
| Material-Change Reassessment | Affected plan/work | BP and authoritative owners | Continued, relocked or revised | Silent continuation |

## 9. Ownership Matrix

| Concern | Authoritative owner | Permitted contribution | Prohibited ownership |
|---|---|---|---|
| Relationship identity/lifecycle | BP Employment Context | CE/WBE outcomes | Transcript, web or adapter inference |
| Conversation timeline | BP Conversation Core | PR typed execution events | Browser or model provider |
| Induction requirement set | Agent conformance manifest interpreted by BP | Domain adapter specialization | Browser checklist |
| Confirmed induction truth | BP relationship governance with named authority source | Agent proposals | AIR direct mutation |
| Goal and plan | BP relationship governance | Professional/domain candidate semantics | PR, AIR or web public mutation |
| Calendar commitment | BP plan governance | Domain constraints and provider availability | Provider calendar as relationship authority |
| Readiness/eligibility | BP composed from current owners | Agent manifest and domain evidence | Agent self-declaration |
| Constitutional validity/evidence | CE | BP/PR validation requests | WBE, AIR, web or adapter |
| Execution | PR | AIR/tool results | BP, web or WBE |
| Billing/commercial truth | WBE | BP public relay | Agent/domain adapter/web calculation |
| Domain outcome semantics | Domain adapter | PR facts and approved evidence references | Public ordering, lifecycle or authority |
| Public Results/attention | BP | Validated domain/WBE/PR candidates | Adapter or browser |
| Inference and candidate patches | AIR | Prompt/knowledge/tool execution | Authoritative relationship commit |
| Presentation | Web/channels | Generated BP projections/commands | Durable truth or eligibility |

## 10. Failure, Degradation And Reconciliation

| Failure | Required behavior | Consequential work | Customer projection |
|---|---|---|---|
| CE unavailable | Preserve Emergency Stop; advisory/read-only planning may continue | Halt CE-governed actions | `BLOCKED`, reason and recovery owner |
| WBE unavailable/stale | Preserve last-known labelled history; no new commercial assertion | Block work requiring fresh commercial truth | `STALE` or `UNAVAILABLE`, never zero/default |
| AIR unavailable | Preserve authoritative workspace; allow deterministic commands | No new AI-derived proposal; existing authorized deterministic work follows owner policy | Disclose reduced advisory capability |
| PR unavailable | Preserve plan, rights and history | Work remains pending/blocked; no completed claim | Execution unavailable with reconciliation owner |
| Domain adapter unavailable | Preserve prior labelled results | No fresh domain outcome or readiness assertion dependent on it | Partial Results with missing owner named |
| Provider timeout after action intent | Reconcile by idempotency/correlation before retry | No blind duplicate | `OUTCOME_UNKNOWN` until owner resolution |
| Credential expired/revoked | Reassess dependency graph | Block affected Skills; block wider work if isolation unproven | Pending credential, reason and blocked effect |
| Goal/plan source stale | Require reassessment | Relock affected work | `STALE_REASSESSMENT_REQUIRED` |
| Channel loss | Resume through another authenticated channel | No authority change | Same relationship/workspace version |
| Evidence commit failure | Return no governed success | Halt/retain unresolved | Evidence pending/failed, not completed |

### 10.1 Recovery rules

- Commands are idempotent and bound to actor, tenant, relationship, subject, expected version and
  canonical payload hash.
- Same key/hash replays the prior outcome; divergent reuse conflicts.
- External intent and observed outcome are separate.
- Reconciliation names an accountable owner and cannot manufacture success.
- Recovery preserves append-only plan/evidence history.

## 11. Security And Privacy

1. Tenant and relationship authority derive from authenticated server context, never customer input.
2. Credential values never appear in conversation or workspace projections; only minimised readiness
   references and customer-safe recovery actions appear.
3. Induction collects the minimum data required by declared professional capability.
4. Domain adapters cannot read or contribute across relationships.
5. Plan acceptance, material acknowledgements and authority changes require the accepted assurance
   level for their consequence class.
6. Anti-enumeration behavior applies to relationship, dependency, plan and evidence resources.
7. Cached and offline browser state cannot authorize commands.
8. Emergency Stop remains transport-independent from ordinary readiness and billing paths.
9. Erasable personal payloads remain separate from append-only proof integrity.
10. Agent-conformance manifests contain no customer secrets.

## 12. Observability And Operability

Every gate decision emits structured, privacy-minimised telemetry naming:

- tenant-safe relationship correlation;
- agent type/version and protocol version;
- gate and subject;
- plan and requirement-set versions;
- authoritative sources and freshness;
- decision and unmet conditions;
- evidence reference/state;
- latency and timeout class;
- accountable recovery owner; and
- prior decision when reassessment occurs.

Operational dashboards must distinguish:

- platform availability;
- gate evaluation health;
- blocked relationships by reason;
- stale owner projections;
- reconciliation backlog;
- provider failure;
- agent performance; and
- customer business outcomes.

These categories may be correlated but not collapsed.

## 13. Employment Interface Conformance Manifest

The future machine-readable agent declaration has this conceptual shape:

```yaml
employment_interface:
  protocol_version: "1.0"
  induction:
    requirement_set_version: "..."
    mandatory_context: [...]
    optional_context: [...]
    dependency_types: [...]
    readiness_rules: [...]
    domain_summary_adapter: "..."
  planning:
    supported_goal_types: [...]
    milestone_types: [...]
    calendar_constraints: [...]
    material_change_rules: [...]
    performance_measures: [...]
    plan_adapter: "..."
  operations:
    operating_cycle_types: [...]
    work_item_types: [...]
    reassessment_triggers: [...]
    outcome_adapter: "..."
    billing_profile_ref: "..."
    degradation_profile: "..."
  conformance_scenarios:
    - scenario_id: "..."
      evidence_ref: "..."
```

### 13.1 Manifest rules

- Every mandatory field is versioned and machine-readable.
- Domain terms are allowed only inside the agent declaration and adapter payload.
- Manifest references must resolve to current approved agent, billing, prompt, tool and Decision
  Consequence Map artifacts.
- A missing or outdated manifest blocks publication under the future activated protocol.
- Runtime input uses an admitted immutable manifest version; mutable repository text is not queried
  during an action.

### 13.2 Compatibility scan

The compatibility scanner reports:

- exact protocol and manifest version per agent;
- missing mandatory phase declarations;
- unsupported major versions;
- unresolved billing/profile references;
- missing conformance scenarios;
- stale domain adapters;
- offered agents that would become non-compliant; and
- safe activation or rollback status.

Unknown parsing, missing references or mixed mandatory versions fail closed.

### 13.3 Atomic migration

1. Founder accepts ADR-051 and protected defaults.
2. Solution/Data/Security/AI/Product contracts are accepted.
3. Candidate manifest schema and compatibility rules are frozen.
4. Every offered agent receives a candidate manifest and conformance evidence.
5. DMA, Trading and Private Tutor pass cross-domain scenarios; every other offered agent passes its
   declared scenarios.
6. Gap scan reports zero offered-agent gaps.
7. Agent Base Specification and PAC versions are bumped in one controlled change.
8. Founder explicitly activates the mandatory protocol version.
9. Prior version remains available for bounded rollback without allowing new non-conforming offers.

No grandfathering is permitted after activation.

## 14. DMA Conformance Proof

| Phase | DMA specialization | Generic platform mapping | Gate evidence |
|---|---|---|---|
| Induction | Account mode, business profile, aspiration, audience, prior agency experience | Confirmed/inferred context items | Customer-confirmed profile summary |
| Induction | Public market research and maturity assessment | Domain evidence and baseline contribution | Source provenance, limitations and maturity record |
| Induction | Creative Fingerprint, brand vocabulary and standards | Professional standard context | Customer confirmation and amendment history |
| Induction | Instagram, Facebook, GBP, WhatsApp, analytics, booking, website and asset dependencies | Typed dependencies with affected Skills | Credential/asset readiness without secret exposure |
| Planning | Campaign target outcome and audience | Relationship Goal | Baseline, target, attribution boundary and review period |
| Planning | Platform mix and campaign brief | Domain plan contribution | Evidence-backed recommendation and customer acceptance |
| Planning | Weekly themes, content cadence and publication calendar | Milestones and calendar commitments | Exact plan version and schedule |
| Planning | Approval mode and Decision Space | Authority/approval references | Current license and material-change rules |
| Planning | Ad budget and wallet | WBE references | Fresh ceiling and commercial consequence |
| Operations | Content creation, SCR, customer/synthetic approval | Work/deliverable lifecycle | Approval and quality evidence |
| Operations | Publication and provider response | External side-effect reconciliation | Intent, provider correlation and outcome |
| Operations | Paid advertising | Financial continuous-action gate | CE and WBE fresh authorization |
| Operations | Analytics and attribution | Domain Results adapter | Outcome, confidence, evidence and limitations |
| Operations | Performance review and next campaign correction | Operating-cycle learning | Miss/escalation and proposed plan revision |

### 14.1 DMA failure scenarios

| Scenario | Required result |
|---|---|
| Facebook credential never supplied | Facebook-dependent Skills remain pending/blocked; unaffected Skills may proceed only when independently bounded |
| Customer changes target after calendar agreement | New plan version, impact summary and affected-work reassessment |
| Customer revokes approval | No later publication relies on revoked approval; active work reconciles |
| Ad wallet is empty | WBE consequence blocks spend; organic/read-only constitutional paths remain according to policy |
| Publish request times out | `OUTCOME_UNKNOWN`; reconcile provider correlation before retry |
| Analytics unavailable | Partial report names missing source; no invented outcome |
| Booking attribution incomplete | Performance shows bounded attribution confidence, not proven bookings |
| Goal missed twice | Customer-visible diagnosis and corrective proposal; no silent continuation |
| One Skill paused | Its work and pro-rata billing stop without halting independently bounded Skills |
| Emergency Stop | All affected operations halt independently of readiness, budget or channel |

No DMA field is added to the generic workspace.

## 15. Universality Challenge

### 15.1 Trading

| Challenge | Generic fit | Domain-owned extension |
|---|---|---|
| High-frequency operation | Continuous Action Gate | Trading session and risk checks |
| Market calendar | Calendar contract | Exchange sessions, holidays and halts |
| Financial caps | Decision Space/WBE/CE references | Capital, loss and order limits |
| Immediate stale-data risk | Freshness and reassessment | Market-data validity threshold |
| External broker ambiguity | Intent/outcome reconciliation | Broker order correlation |

Result: no new generic component, field or lifecycle state.

### 15.2 Private Tutor

| Challenge | Generic fit | Domain-owned extension |
|---|---|---|
| Guardian and learner roles | Accountable owners and assurance | Guardian authority and student presentation |
| Recurring learning plan | Goal, milestone and calendar | Lesson sequence and curriculum |
| Progress evaluation | Business/domain outcome adapter | Mastery and learning evidence |
| Safeguarding | Continuous Action and security gates | Child-specific prohibitions |
| Billing-invisible student | Channel projection policy | Guardian-only WBE communication |

Result: no new generic component, field or lifecycle state.

### 15.3 Universality conclusion

DMA, Trading and Private Tutor share the same relationship, phase projection, readiness, plan,
calendar, operations, billing composition, performance composition and failure semantics. Their
differences remain manifest/adapter-owned. Runtime Universality is preserved.

## 16. Architecture Fitness Contract

| ID | Measurable condition |
|---|---|
| CEW-FIT-01 | Every offered agent resolves to exactly one active supported employment-interface manifest version |
| CEW-FIT-02 | Every relationship exposes exactly one authoritative workspace and durable conversation identity |
| CEW-FIT-03 | Every mandatory pending item has reason, owner, blocked effect, freshness and action/recovery |
| CEW-FIT-04 | No consequential operation is available before all required admission gates pass |
| CEW-FIT-05 | Chat/model output cannot commit authoritative induction, plan, readiness, billing or performance state directly |
| CEW-FIT-06 | Every plan change creates or replays an immutable versioned outcome with impact summary |
| CEW-FIT-07 | Billing values displayed by BP equal the exact WBE projection version and are never locally recalculated |
| CEW-FIT-08 | Performance leads with business outcomes and names attribution limits |
| CEW-FIT-09 | Unknown, stale, partial, disputed, unavailable and blocked never serialize as completed/current success |
| CEW-FIT-10 | Channel change preserves relationship, conversation, plan, readiness, rights and evidence identity |
| CEW-FIT-11 | Skill pause stops only independently bounded affected work and WBE-owned pro-rata billing |
| CEW-FIT-12 | Emergency Stop is reachable and effective in every phase regardless of billing/readiness state |
| CEW-FIT-13 | Material goal, budget, authority, dependency or calendar change triggers affected-work reassessment |
| CEW-FIT-14 | External ambiguous outcomes reconcile before retry and cannot duplicate consequential action |
| CEW-FIT-15 | Compatibility scan fails on missing, outdated, unparsable or unresolved offered-agent manifests |
| CEW-FIT-16 | Mandatory protocol activation is impossible while any offered agent lacks exact-version PASS evidence |
| CEW-FIT-17 | DMA, Trading and Private Tutor conformance fixtures use the same generic workspace contract |
| CEW-FIT-18 | Tenant/relationship authority is derived server-side and cross-tenant existence is not disclosed |

## 17. Reversibility And Evolution

- Minor backward-compatible additions do not change existing required meanings.
- Removing, renaming or changing required meaning is a major version.
- Major versions require dual-read/controlled-write migration, compatibility scan and rollback proof.
- Accepted plans and evidence remain readable after protocol upgrade.
- Unsupported commands remain blocked rather than guessed.
- A superseding architecture decision must name agent, relationship, data, evidence and customer
  migration consequences.

## 18. Downstream Decomposition Boundary

The Solution Architect may define:

- endpoint paths and operation families;
- wire schemas and generated-client boundary;
- internal event and adapter contracts;
- exact state-machine transitions and error codes;
- orchestration, retry and reconciliation sequences.

The Solution Architect may not change:

- the three phases or common visual obligations;
- bounded-context authority;
- C-034 lifecycle preservation;
- gate separation;
- WBE/CE/PR/AIR ownership;
- atomic all-agent protocol activation;
- Founder policy defaults without a Founder decision.

Data, Security, AI, Product, Platform, Test and Runtime offices follow the ordered WC-113 handoff.

