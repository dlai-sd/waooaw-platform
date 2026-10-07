# ADR-051 - Conversational Employment Workspace And Readiness Protocol

**Status:** Proposed - Founder review required  
**Date:** 2026-10-07  
**Author:** Chief Enterprise Architect (INST-004)  
**Work Contract:** WC-113  
**Constitutional Basis:** C-023, C-034, C-036-C-039, C-041, C-048-C-049, C-059, C-070, C-079, C-088 and C-094  
**Related Decisions:** ADR-002, ADR-003, ADR-015, ADR-018, ADR-031, ADR-034, ADR-035, ADR-040, ADR-043, ADR-044 and ADR-049

## Context

WAOOAW already defines:

- one constitutionally governed Employment Relationship;
- conversational agent configuration;
- one durable relationship conversation;
- a Relationship Workspace containing Plan, Goals, Work, Results, Usage/Budget and Rights;
- agent-type activation gates;
- versioned platform-agent signals; and
- skill-level billing and business-outcome performance.

These structures do not yet compose into one mandatory, machine-verifiable employment protocol that
every agent must follow before and during customer operations. Agent-type approval answers whether a
professional type is specified and offerable. It does not prove that a particular customer
relationship is understood, planned, supplied, authorized and measurable enough to operate.

The Founder requires three universal conversational phases:

1. Onboard, Induct and Groom;
2. Goal, Plan, Milestone and Calendar Formation; and
3. Operations, Billing and Performance Management.

Each phase must have a visual reflection of progress, completed work, in-progress work and pending
work, including why a pending item is required and what it blocks.

## Decision

WAOOAW adopts a **Conversational Employment Workspace** and an **Employment Readiness Protocol**.

### 1. One relationship, conversation and workspace

Each Employment Relationship has:

- one durable relationship identity;
- one durable professional conversation; and
- one authoritative Business Platform relationship workspace.

The three phases are views and readiness facets of the same relationship. They are not separate
employment relationships, conversations, services or C-034 lifecycle states.

### 2. Conversation proposes; authoritative owners commit

Conversation is the primary customer authoring path in every phase. A professional may interpret a
message and propose a typed context, plan, calendar, dependency or operating-cycle patch. The
proposal becomes authoritative only after deterministic validation and any required customer,
constitutional, commercial or owner decision.

The browser, transcript and model output never independently determine completion, readiness,
authority, billing or performance.

### 3. One common visual phase projection

Every phase projection exposes:

- phase and phase status;
- progress basis;
- completed, in-progress and pending items;
- pending reason, accountable owner, due meaning and blocked effect;
- blockers, assumptions and dependencies;
- current goal and plan version where applicable;
- milestones and calendar commitments where applicable;
- evidence state, source freshness and limitations;
- available authoritative commands; and
- recommended next action.

Progress is derived from declared requirements and item states. An unexplained model-generated
percentage is prohibited.

### 4. Readiness is orthogonal to employment lifecycle

C-034 lifecycle remains `EVALUATION`, `ACTIVE`, `SUSPENDED` and `TERMINATED`.

The relationship adds independent readiness facets:

- `induction_readiness`;
- `plan_readiness`;
- `operations_eligibility`; and
- `performance_assurance`.

An employment relationship may be contractually active while consequential operations remain locked.

### 5. Gates are distinct

The architecture distinguishes:

1. Agent Type Publication Gate;
2. Relationship Admission Gate;
3. Induction Readiness Gate;
4. Plan Acceptance Gate;
5. Operational Admission Gate;
6. Continuous Action Gate; and
7. Material-Change Reassessment Gate.

Passing an earlier gate never substitutes for a later gate. All consequential gate success is
evidence-first and attributable.

### 6. Existing bounded contexts retain authority

- Business Platform owns public relationship, readiness, plan, goal, workboard and command truth.
- Conversation Core owns durable conversation projection under Business Platform.
- Professional Runtime owns execution truth.
- AI Runtime interprets and proposes but owns no customer relationship authority.
- Constitutional Engine owns constitutional validation and constitutional evidence.
- WBE owns billing, allowance, forecast and commercial consequences.
- Domain adapters contribute professional meanings and outcomes without becoming public facades.
- Web presents generated Business Platform contracts and owns no durable relationship truth.

No new deployable service is authorized by this decision.

### 7. Every agent must declare conformance

A future Agent Base Specification and Platform-Agent Contract version will require a machine-readable
Employment Interface Conformance Manifest covering induction, planning and operations.

The new mandatory version activates only after:

1. every offered agent has an exact-version manifest;
2. compatibility scanning passes;
3. agent-specific conformance scenarios pass;
4. billing and constitutional gates remain current; and
5. the Founder explicitly activates the version.

Until then, the protocol is proposed architecture and does not make current agents non-compliant by
prematurely changing the current mandatory version.

The detailed contract is
`architecture/reference/conversational-employment-workspace.md`.

## Alternatives Considered

| Alternative | Decision |
|---|---|
| Build separate onboarding, planning and operations services | Rejected: duplicates relationship identity and authoritative state, increases reconciliation failure and lacks a capability requiring new deployables |
| Create three separate conversations | Rejected: fragments professional continuity and permits contradictory context or plans |
| Make phase progress a browser-managed checklist | Rejected: browser state is not authority, is not channel invariant and can silently drift |
| Infer readiness from transcript completion | Rejected: non-deterministic, unauditable and vulnerable to missing or hallucinated facts |
| Add onboarding/planning as C-034 employment states | Rejected: changes ratified lifecycle semantics and conflates employment with operational readiness |
| Let each agent invent its own lifecycle interface | Rejected: violates Runtime Universality and prevents platform-wide gate enforcement |
| Put profession-specific fields in the generic workspace | Rejected: couples WAOOAW to DMA and makes future professions require platform schema redesign |
| Immediately bump Agent Base Spec and migrate later | Rejected: C-094 would instantly make currently offered agents non-compliant |
| Use the institutional Goal Orchestrator as customer goal authority | Rejected: institutional delivery governance and customer employment planning are different bounded contexts |
| Reuse Conversation Core and Relationship Workspace with an explicit readiness protocol | Accepted: minimum structure that preserves existing authority and continuity |

## Consequences

### Positive

- Customers experience one coherent professional relationship across all phases and channels.
- Every pending item explains why it matters, who owns it and what it blocks.
- Operations cannot begin from an approved agent type alone.
- Domain expertise remains agent-specific while platform governance stays uniform.
- Billing and performance appear together without merging their authority.
- Material goal, dependency or credential changes trigger bounded reassessment.
- Compatibility scanning can prevent non-conforming agents from being offered.

### Negative

- Existing agents require conformance manifests and scenario evidence before protocol activation.
- Business Platform relationship governance becomes the composition point for more owner projections.
- Plan and readiness versioning introduce additional conflict and reconciliation states.
- Customer-visible partial, stale and blocked states increase interface complexity.
- Cross-channel projections require strict semantic consistency.

### Risks And Controls

| Risk | Control |
|---|---|
| Readiness becomes an opaque score | Requirement-derived status with explainable item counts and mandatory-item evidence |
| Agent marks its own onboarding complete | BP-owned gate evaluation; agent supplies proposals and domain evidence only |
| Chat silently changes agreed plan | Typed patch, impact summary, version check and required acceptance |
| Billing or performance is recomputed by UI/agent | WBE/domain-owner projections relayed through BP without recomputation |
| DMA assumptions leak into platform contract | Generic adapter contract and Trading/Private Tutor universality tests |
| Mixed agent conformance after version bump | Atomic compatibility gate and Founder-controlled activation |
| External action outcome is ambiguous | Idempotency, intent/outcome separation and owner reconciliation |
| Goal change leaves unsafe work running | Material-change classification and affected-work relock |
| Credential loss exposes unrelated Skills | Dependency graph and bounded Skill isolation; fail closed when isolation is unproven |
| Missing evidence appears as completion | Explicit pending/unknown/unavailable states and Evidence First |

## Reversibility

Before activation, ADR-051 may be rejected or amended without runtime migration. After acceptance,
the protocol remains non-operational until downstream contracts and all-agent conformance pass.

Protocol activation must retain the prior supported version for a bounded rollback window. Rollback
restores the prior protocol projection and blocks commands introduced only by the new version; it
does not delete plans, evidence or customer work. A later ADR must supersede this decision and name
relationship, agent and evidence migration consequences.

## Founder Decisions Required

The Founder must accept or change the WC-113 defaults for partial Skill readiness, trial operations,
material goal change, deferred dependencies, plan acknowledgement, performance-failure escalation,
billing exhaustion, calendar tolerance, credential loss and readiness override.

## Implementation Boundary

This ADR authorizes no endpoint, schema, prompt, code, deployment or agent-protocol activation.
Solution, Data, Security, AI, Product, Platform, Test and Runtime work require the ordered handoff and
separate authority in WC-113.

