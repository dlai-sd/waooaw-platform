# Evidence State Machine — Data Architecture Specification

**Produced by:** Data Architect (Sprint 005)
**Work Contract:** WC-005
**Date:** 2026-07-07
**Constitutional Basis:** C-028 (PROPOSED as first-class enum), C-007 (ledger immutability), C-027 (append-only), C-023 (Evidence First), AD-002 (Evidence First enforcement), AD-003 (audit ledger immutability), AD-008 (constitutional auditability)

---

## Purpose

This document specifies the complete evidence state machine for the Constitutional Audit Ledger. It extends `ledger-design.md`, which specifies the table structure, schema separation, RLS policies, and permission model.

`ledger-design.md` defines **what** is recorded. This document defines **how it transitions** — the valid states, valid transitions, who triggers each transition, and the constitutional basis for each.

---

## Governing Constraint: Append-Only State Machine

A critical distinction from conventional state machine design:

> **Evidence records are never updated. State transitions create new records.**

C-027 (append-only mandate) means the `state` field of any given evidence record is immutable after INSERT. State transitions are not UPDATEs to existing records — they are new INSERTs with the new state, linked to the originating action instance.

This means the state machine is enforced at the **Constitutional Engine application layer** (not by a DB CHECK constraint that prevents invalid states — all valid enum values can be inserted). The enforcement rule is: before inserting a record with state S₂, the Constitutional Engine must verify the most recent record for that `action_instance_id` has state S₁, where (S₁ → S₂) is a valid transition.

---

## Required Schema Addition: action_instance_id

`ledger-design.md` does not specify a field that groups evidence records belonging to the same action. This is a gap in the data architecture specification.

**Specification:**

```
Column: action_instance_id  UUID NOT NULL
Purpose: Groups all evidence records (PROPOSED → APPROVED → EXECUTED, etc.)
         belonging to one logical action attempt.
         Every INSERT for the same action uses the same action_instance_id.
         The action_instance_id is generated when the PROPOSED record is created
         and is passed in the gRPC RecordEvidence request for all subsequent states.

Index:   CREATE INDEX idx_evidence_action_instance
         ON constitutional.evidence_records(action_instance_id, created_at);
```

The Runtime Professional must add this column to the `constitutional.evidence_records` table and to the `RecordEvidenceRequest` proto message.

---

## Complete Evidence State Enum

The `evidence_state` enum in `ledger-design.md` must be extended:

```
evidence_state:
  PROPOSED             -- action has been proposed; shadow trial begins
  AWAITING_APPROVAL    -- action presented to customer for approval decision
  APPROVED             -- customer has approved; execution may proceed
  REJECTED             -- customer has rejected; execution is prohibited
  EXECUTED             -- action has been executed; constitutional record complete
  ABANDONED            -- action was in progress when an Emergency Stop fired;
                          execution halted before completion
```

`ABANDONED` is constitutionally required because:
- C-007 (ledger immutability): in-flight records cannot be updated or deleted when Emergency Stop fires
- The ledger must explain the full history: an action was proposed, was in flight, and was constitutionally terminated
- A missing record (gap in the ledger) is indistinguishable from a system failure — `ABANDONED` makes the termination explicit and attributable

---

## Execution Model Variants

The evidence state machine has two variants, determined by the `execution_model` field of the Employment Contract's Decision Space.

### Variant A — Approval-Gate Execution Model

Used by: Digital Marketing Professional (Case 001), Creative Professional (Case 002), and any professional type configured with `execution_model = APPROVAL_GATE`.

```
PROPOSED ──────────────────────────────────────────────────► AWAITING_APPROVAL
                                                                      │
                              ┌───────────────────────────────────────┤
                              │                                       │
                              ▼                                       ▼
                          REJECTED                               APPROVED
                                                                      │
                                                                      ▼
                                                                  EXECUTED
```

Any state except EXECUTED and REJECTED can transition to ABANDONED if Emergency Stop fires:

```
PROPOSED ──────────────────────────────────────────────────► ABANDONED
AWAITING_APPROVAL ─────────────────────────────────────────► ABANDONED
APPROVED ──────────────────────────────────────────────────► ABANDONED
```

**Scope-Boundary Path (Approval-Gate only):**

When the Constitutional Engine detects that a proposed action crosses a scope boundary, the standard approval flow is interrupted. A `ScopeBoundaryConfirmation` event record is inserted as a SEPARATE `action_type`. The original action instance remains at `AWAITING_APPROVAL` while boundary confirmation is pending.

```
(original action) action_instance_id=A, action_type=MARKETING_POST, state=PROPOSED
(original action) action_instance_id=A, action_type=MARKETING_POST, state=AWAITING_APPROVAL, is_scope_boundary=TRUE
(boundary event)  action_instance_id=B, action_type=SCOPE_BOUNDARY_CONFIRMATION, state=PROPOSED, scope_boundary_name='LinkedIn direct promotion'
(boundary event)  action_instance_id=B, action_type=SCOPE_BOUNDARY_CONFIRMATION, state=EXECUTED, scope_boundary_acknowledgment='[customer text]'
(original action continues) action_instance_id=A, state=APPROVED
(original action completes) action_instance_id=A, state=EXECUTED
```

The `ScopeBoundaryConfirmation` record is complete when state = EXECUTED. The original action can only advance to APPROVED after the boundary confirmation is complete.

### Variant B — PAAS (Pre-Authorized Action Space) Execution Model

Used by: Algorithmic Trading Professional (Case 003) and any professional type configured with `execution_model = PRE_AUTHORIZED`.

```
PROPOSED ──────────────────────────────────────────────────► EXECUTED
     │
     └─────────────────────────────────────────────────────► REJECTED
         (Decision Space validation fails at Constitutional Engine)
```

There is no `AWAITING_APPROVAL` or `APPROVED` state in PAAS — the Decision Space pre-authorizes execution. The `PROPOSED` → `EXECUTED` transition is atomic from the customer's perspective: the PAAS engine validates against the in-memory Decision Space, calls Constitutional Engine, and receives the EXECUTED confirmation in a single hot-path operation.

`PROPOSED` must still be a distinct INSERT before `EXECUTED` — they are never merged into a single record. C-028 mandates `PROPOSED` as a first-class state that produces its own ledger record. The two records are linked by `action_instance_id`.

PAAS Emergency Stop path:

```
PROPOSED ──────────────────────────────────────────────────► ABANDONED
```

When Emergency Stop fires during PAAS execution, the in-flight `PROPOSED` record cannot be updated. A new `ABANDONED` record is inserted with the same `action_instance_id`.

---

## State Transition Table

| From State | To State | Execution Model | Trigger | Service | Constitutional Basis |
|---|---|---|---|---|---|
| — | PROPOSED | Both | Professional proposes action | Constitutional Engine (via Professional Runtime gRPC call) | C-028 (PROPOSED as first-class), AD-002 (Evidence First) |
| PROPOSED | AWAITING_APPROVAL | Approval-Gate | Action routed to customer for approval | Constitutional Engine (Evidence First Enforcer) | C-023, AD-002 |
| AWAITING_APPROVAL | APPROVED | Approval-Gate | Customer approves action | Constitutional Engine (via Business Platform gRPC) | C-003 (authority licensed), C-023 |
| AWAITING_APPROVAL | REJECTED | Approval-Gate | Customer rejects action | Constitutional Engine (via Business Platform gRPC) | C-003, C-023 |
| PROPOSED | EXECUTED | PAAS | Decision Space validated; action executed | Constitutional Engine (via Professional Runtime gRPC) | C-018 (PAAS pre-authorization), C-023, AD-005 |
| PROPOSED | REJECTED | PAAS | Decision Space validation fails | Constitutional Engine (via Professional Runtime gRPC) | C-003 (Decision Space is the authority boundary), C-023 |
| APPROVED | EXECUTED | Approval-Gate | Action executed after approval | Constitutional Engine (via Professional Runtime gRPC) | C-023, AD-002 |
| PROPOSED | ABANDONED | Both | Emergency Stop fired | Constitutional Engine (TriggerEmergencyStop gRPC) | C-013 (Emergency Override), AD-001 |
| AWAITING_APPROVAL | ABANDONED | Approval-Gate | Emergency Stop fired | Constitutional Engine (TriggerEmergencyStop gRPC) | C-013, AD-001 |
| APPROVED | ABANDONED | Approval-Gate | Emergency Stop fired before execution | Constitutional Engine (TriggerEmergencyStop gRPC) | C-013, AD-001 |
| — | EXECUTED | Both (Emergency Stop event itself) | Emergency Stop command received and recorded | Constitutional Engine (TriggerEmergencyStop gRPC — separate action_instance_id) | C-013, AD-001 |

**Prohibited transitions (enforced by Constitutional Engine before INSERT):**

| Prohibited | Reason |
|---|---|
| PROPOSED → EXECUTED (Approval-Gate) | Bypasses customer approval. Violates C-003 (authority requires customer authorization). |
| REJECTED → EXECUTED | Executing a rejected action is a constitutional violation. No exception. |
| REJECTED → APPROVED | Approval cannot be granted retroactively. |
| AWAITING_APPROVAL → EXECUTED | Execution before approval decision violates Evidence First (AD-002). |
| EXECUTED → any | EXECUTED is a terminal state. No further transitions. C-027 (append-only): the record is complete. |
| ABANDONED → any | ABANDONED is a terminal state. The action was constitutionally terminated. |
| Any → PROPOSED | PROPOSED is the initial state only. An action cannot be re-proposed under the same `action_instance_id`. A new action is a new `action_instance_id`. |

---

## Constitutional Basis Field Specification

Every evidence record carries `constitutional_basis VARCHAR(500) NOT NULL`.

**Purpose:** Implements AD-008. Every permission decision and every state transition must name the specific constitutional authority that authorized it.

**Format:** A semicolon-separated list of one or more of the following reference types:

| Reference Type | Format | Example |
|---|---|---|
| Ratified Claim | `C-NNN` | `C-023` |
| Constitutional Precedent | `CP-NNN` | `CP-001` |
| Architectural Driver | `AD-NNN` | `AD-002` |
| Constitutional Article | `ART-[roman]` | `ART-XI` |
| Emergency Stop reference | `EMERGENCY_STOP:[uuid]` | `EMERGENCY_STOP:d3f1a...` |

**Enforcement:** `NOT NULL` at the database level. Empty string is prohibited by application-layer validation in Constitutional Engine before INSERT. The Policy Evaluator (constitutional-engine.md) constructs this string before calling RecordEvidence.

**Minimum valid value for each state:**

| State | Minimum constitutional_basis |
|---|---|
| PROPOSED | `C-028; AD-002` |
| AWAITING_APPROVAL | `C-023; AD-002` |
| APPROVED | `C-003; C-023` |
| REJECTED | `C-003; C-023` |
| EXECUTED | `C-023; AD-002` |
| ABANDONED | `C-013; AD-001` |

---

## Emergency Stop Evidence Record Specification

When an Emergency Stop fires, the Constitutional Engine produces **two** categories of records:

**1. The Emergency Stop Event Record** (new action instance):

```
action_instance_id: [new UUID — the stop event itself]
action_type:        EMERGENCY_STOP
state:              EXECUTED
constitutional_basis: C-013; AD-001
proposed_content:   null
executed_content:   { "stopped_at": "<timestamp>", "affected_sessions": ["<session_id>", ...] }
is_scope_boundary:  false
```

**2. ABANDONED record(s) for each in-flight action** (one per in-flight action_instance_id):

```
action_instance_id: [same as the in-flight action]
action_type:        [same as the in-flight action]
state:              ABANDONED
constitutional_basis: C-013; AD-001; EMERGENCY_STOP:[emergency_stop_action_instance_id]
proposed_content:   null
executed_content:   null
```

**Ordering guarantee:** The Emergency Stop Event Record must be INSERTed **before** the ABANDONED records. The `EMERGENCY_STOP:[uuid]` reference in the ABANDONED records' `constitutional_basis` is only valid after the Event Record exists. This ordering is enforced by the Constitutional Engine's `TriggerEmergencyStop` handler, which uses a single database transaction for all inserts in the Emergency Stop sequence.

---

## State Machine Enforcement in Constitutional Engine

The Constitutional Engine's `Evidence First Enforcer` component (constitutional-engine.md) must enforce the state machine as follows before every INSERT:

```
FUNCTION validateTransition(action_instance_id, proposed_state):
  1. Query: SELECT state FROM constitutional.evidence_records
            WHERE action_instance_id = $1
            ORDER BY created_at DESC
            LIMIT 1
  2. current_state = result (NULL if no prior records — PROPOSED is always valid as initial state)
  3. IF (current_state, proposed_state) NOT IN allowed_transitions:
       RETURN gRPC error FAILED_PRECONDITION
       "Invalid state transition: {current_state} → {proposed_state} for action {action_instance_id}"
  4. IF (current_state IN [EXECUTED, REJECTED, ABANDONED]) AND proposed_state != ABANDONED:
       RETURN gRPC error FAILED_PRECONDITION
       "Terminal state {current_state} — no further transitions permitted"
  5. PROCEED to INSERT
```

This validation runs **within the same database transaction** as the INSERT, preventing race conditions on the same `action_instance_id`.

---

## Relationship to ledger-design.md

| Design concern | Where specified |
|---|---|
| Schema zones (constitutional / business / professional) | `ledger-design.md` |
| RLS policies and tenant isolation | `ledger-design.md` |
| DB-level append-only enforcement (PostgreSQL RULE) | `ledger-design.md` |
| Database user permissions | `ledger-design.md` |
| Evidence state enum | `ledger-design.md` (base) + this document (extended with ABANDONED) |
| action_instance_id column | **This document** |
| State machine transitions and valid paths | **This document** |
| Constitutional basis field format | **This document** |
| PAAS vs Approval-Gate variant | **This document** |
| Emergency Stop evidence records | **This document** |
| Scope-boundary confirmation event | **This document** |

---

## Implementation Notes for Runtime Professional

1. **Add `action_instance_id UUID NOT NULL` to `constitutional.evidence_records`** — see index specification above. This column was specified here, not in `ledger-design.md`. Add it in the same initial migration (EF Core — AddColumn on evidence_records).

2. **Extend the `evidence_state` enum** to include `ABANDONED`. In PostgreSQL, `ALTER TYPE evidence_state ADD VALUE 'ABANDONED'` is non-destructive and does not require a table rebuild. Per ADR-011, this is a safe migration.

3. **Add `action_instance_id` to the `RecordEvidenceRequest` proto message** (constitutional_service.proto) — required for state machine enforcement at the Constitutional Engine layer.

4. **The `approval_state` enum** in `business.approval_requests` is a separate, business-schema concern. It mirrors (but does not replace) the evidence state. When `evidence_records.state = AWAITING_APPROVAL`, the corresponding `approval_requests.state = PENDING`. Synchronization is the responsibility of Business Platform calling Constitutional Engine gRPC.

5. **No EF Core migration may include UPDATE or DELETE on the constitutional schema** (ADR-011 hard rule). The ABANDONED state is always a new INSERT, never an update to an existing record.
