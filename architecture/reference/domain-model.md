# Domain Model

**Produced by:** Enterprise Architect (Sprint 003)
**Date:** 2026-07-07
**Constitutional Basis:** C-030 (Decision Space as primitive), C-034 (employment lifecycle), C-005 (Three-Ledger), C-028 (evidence state machine), C-036 (Skills as constitutional units), C-037 (business KPIs), C-038 (pro-rata billing), C-039 (conversational configuration)

---

## Core Domain Concepts

### Decision Space
The constitutional primitive. All other domain objects derive from it.

```
DecisionSpace {
  id: UUID
  version: int
  employmentContractId: UUID
  professionalType: enum(MARKETING, CREATIVE, TRADING, ...)
  executionModel: enum(APPROVAL_GATE, PRE_AUTHORIZED)
  authorizedActions: [ActionDefinition]
  prohibitedActions: [ActionDefinition]
  alwaysAskActions: [ActionDefinition]
  budgetConstraints: BudgetConstraints
  creativeStandardProfile: CreativeStandardProfile?   // creative professions only
  paasParameters: PAASParameters?                     // PAAS execution model only
}
```

### Employment Contract
The constitutional relationship between a Customer and a Digital Professional.

```
EmploymentContract {
  id: UUID
  tenantId: UUID                    // multi-tenancy anchor (ADR-003)
  customerId: UUID
  professionalIdentityId: UUID
  decisionSpaceId: UUID
  state: enum(EVALUATION, ACTIVE, SUSPENDED, TERMINATED)  // C-034
  authorityLevel: int               // starts at minimum, expands by evidence
  lifecycleType: enum(PERMANENT, SESSION_BOUND, TRIAL)
  // FR-002: Trial = full constitutional employment. All rights apply from day one.
  isTrial: boolean                  // true = 7-day trial period, no billing commitment
  trialEndsAt: datetime?            // auto-terminates if not converted
  trialConvertedAt: datetime?       // set when customer converts to paid subscription
  goals: [BusinessGoal]
  reviewCadence: ReviewCadence
  startDate: datetime
  endDate: datetime?
  createdAt: datetime
}
```

### Evidence Record
The atomic unit of constitutional trust-building.

```
EvidenceRecord {
  id: UUID
  tenantId: UUID
  contractId: UUID
  professionalIdentityId: UUID
  actionType: string
  state: enum(PROPOSED, AWAITING_APPROVAL, APPROVED, REJECTED, EXECUTED)  // C-028
  proposedContent: JSONB
  executedContent: JSONB?
  customerJustification: string?
  isScopeBoundary: boolean          // C-029: scope-boundary crossings are flagged
  scopeBoundaryName: string?
  scopeBoundaryAcknowledgment: string?
  decisionSpaceVersion: int
  createdAt: datetime               // append-only — no updatedAt
}
```

### Authority License
The constitutional record of a professional's current authority level.

```
AuthorityLicense {
  id: UUID
  contractId: UUID
  level: int
  grantedAt: datetime
  grantedBy: UUID                   // customerId
  constitutionalBasis: string       // which claim/precedent authorized this grant
  evidenceIds: [UUID]               // the evidence that justified the grant
}
// Append-only — new record per authority change. No UPDATE.
```

### Skill (v0.8.0 — C-036)
The independently governable unit of professional capability. A Digital Professional has one or more Skills. Each Skill has its own lifecycle, configuration, and performance evidence.

```
Skill {
  id: UUID
  contractId: UUID
  tenantId: UUID
  skillType: string                   // INSTAGRAM_MARKETING, FACEBOOK_MARKETING, TRADE_EXECUTION, etc.
  name: string                        // human-readable: "Instagram Content & Posting"
  state: enum(ACTIVE, PAUSED, TERMINATED)  // C-036 independent lifecycle
  decisionSpaceSubset: DecisionSpaceSubset  // the portion of the agent's Decision Space governing this skill
  goals: [SkillGoal]                  // business KPI targets for this skill (C-037)
  configuration: JSONB                // credentials, schedule, frequency (per C-039 — set via conversation)
  activatedAt: datetime?
  pausedAt: datetime?
  terminatedAt: datetime?
  createdAt: datetime
}

SkillGoal {
  kpiName: string                     // "appointments_per_week", "enquiries_per_month", "daily_return_pct"
  targetValue: decimal
  currentValue: decimal               // updated by performance monitoring
  measurementPeriod: string           // "week", "month", "day"
}
```

### SubscriptionBillingEvent (v0.8.0 — C-038)
An immutable billing event produced at every lifecycle change. Pro-rata billing is calculated from the event ledger at billing period end.

```
SubscriptionBillingEvent {
  id: UUID
  tenantId: UUID
  contractId: UUID
  skillId: UUID?                      // null = contract-level event
  eventType: enum(ACTIVATED, PAUSED, RESUMED, TERMINATED, TRIAL_STARTED, TRIAL_CONVERTED)
  occurredAt: datetime                // exact minute-level timestamp (AD-014)
  pricePerMonth: decimal              // the rate at the time of this event
  // Billing calculation: sum(pricePerMonth * duration_between_ACTIVATED_and_PAUSED_events)
}
// Append-only — billing events cannot be modified. C-038: pro-rata is constitutional.
```

### Professional Identity
The persistent constitutional entity of a digital professional.

```
ProfessionalIdentity {
  id: UUID
  professionalType: enum
  createdAt: datetime
  // Experience Ledger is a separate schema — not joined with Customer data (C-005)
}
```

---

## Bounded Contexts

### Employment Context (Business Platform owns)
**Responsibility:** Everything about the employment relationship.
**Aggregates:** EmploymentContract (root), DecisionSpace, BusinessGoal, ReviewRecord
**Domain Events emitted:**
- `EmploymentContractFormed` — customer signed contract
- `DecisionSpaceConfigured` — Decision Space set/updated
- `ProfessionalActivated` — moved to ACTIVE state
- `EmploymentSuspended` — moved to SUSPENDED state
- `EmploymentTerminated` — moved to TERMINATED state
- `ContractRenewed` — governed re-consent event

### Governance Context (Business Platform + Constitutional Engine)
**Responsibility:** All customer oversight actions and constitutional boundary enforcement.
**Aggregates:** ApprovalRequest (Business Platform), EvidenceRecord (Constitutional Engine)
**Domain Events emitted:**
- `ActionProposed` — professional proposed an action
- `ActionApproved` — customer approved
- `ActionRejected` — customer rejected
- `ScopeBoundaryConfirmed` — explicit scope-boundary acknowledgment
- `EmergencyStopTriggered` — customer issued halt command
- `EmergencyStopConfirmed` — all operations halted (with latency timestamp)

### Evidence Context (Constitutional Engine owns — append-only)
**Responsibility:** Immutable recording of all constitutional events.
**Aggregates:** EvidenceRecord (root), AuthorityLicense, ConstitutionalAuditEntry
**Domain Events emitted:**
- `EvidenceRecorded` — evidence written to ledger
- `AuthorityExpanded` — authority license level increased
- `AuthorityRestricted` — authority license level decreased
- `ConstitutionalViolationDetected` — PAAS boundary breach or other constitutional event

### Execution Context (Professional Runtime owns)
**Responsibility:** The two execution engines.
**Aggregates:** PAASSession (PAAS execution), ApprovalGateSession (approval-gate execution)
**Domain Events emitted:**
- `PAASSessionStarted` — Decision Space loaded into memory
- `PAASActionExecuted` — action completed within Decision Space
- `PAASBoundaryViolationAttempted` — action tried to exceed Decision Space
- `ApprovalGateActionProposed` — professional proposed (Proposed state)
- `ApprovalGateActionExecuted` — approved action executed

### AI Context (AI Runtime owns)
**Responsibility:** All LLM inference, tool execution, and Decision Space reasoning.
**No direct domain events** — the AI Runtime is an execution tool, not a domain event producer. Governance events are produced by the Execution Context that calls it.

---

## Aggregate Boundaries and Ownership

| Aggregate | Owns | Does NOT own |
|---|---|---|
| EmploymentContract | DecisionSpace, Goals, ReviewSchedule | EvidenceRecords (those are Constitutional Engine's) |
| EvidenceRecord | ConstitutionalAuditEntry, AuthorityLicense | Business schema data |
| PAASSession | In-memory Decision Space snapshot | The canonical Decision Space (owned by EmploymentContract) |
| ApprovalGateSession | Approval workflow state | The evidence record (written by Constitutional Engine) |

---

## State Machines

### Employment Lifecycle (C-034)
```
[EVALUATION] ──(contract signed)──► [ACTIVE]
[ACTIVE]     ──(suspend command)──► [SUSPENDED]
[SUSPENDED]  ──(resume command)───► [ACTIVE]
[ACTIVE]     ──(terminate)────────► [TERMINATED]
[SUSPENDED]  ──(terminate)────────► [TERMINATED]
```

### Evidence State Machine (C-028)
```
[PROPOSED] ──(submitted for review)──► [AWAITING_APPROVAL]
[AWAITING_APPROVAL] ──(customer approves)──► [APPROVED]
[AWAITING_APPROVAL] ──(customer rejects)───► [REJECTED]
[APPROVED] ──(executed)──► [EXECUTED]
```
Note: PAAS execution skips PROPOSED/AWAITING_APPROVAL — it goes directly to EXECUTED with the PAAS session ID as constitutional authority. The Decision Space IS the pre-approval.

---

## Key Invariants

1. **EvidenceRecord is written before the action succeeds** (AD-002, Evidence First)
2. **EvidenceRecord.tenantId must match the session's JWT tenant_id** (AD-004, multi-tenant isolation)
3. **AuthorityLicense records are append-only** — authority history must never be rewritten
4. **PAASSession Decision Space snapshot must match EmploymentContract.DecisionSpace at session start** — any mid-session Decision Space change terminates the PAAS session
5. **EmergencyStop must produce an EvidenceRecord before confirmation is sent to customer** (AD-002)
