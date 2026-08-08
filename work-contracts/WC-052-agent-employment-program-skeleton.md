# Work Contract 052 — Agent Employment Program Skeleton

**IB:** IB-009
**Office:** Enterprise Architect (INST-004)
**Reviewer:** Business Architect + Constitutional Analyst
**Authorized by:** Founder instruction, 2026-08-08
**Status:** DONE — R-028 APPROVED
**Implementation scope:** Architecture and planning artifacts only; no runtime implementation

## Objective

Create a grooming-ready Goal → Epic/Wave → Story skeleton for the Agent Employment Experience program. Define the thin shared contract and product-gap controls that must guide the customer-outcome waves without prematurely grooming stories into implementation tasks.

## Tasks

| Task | Acceptance criterion | Status |
|---|---|---|
| WC052-01 | Program goal, boundaries, outcomes, and architecture readiness gate are explicit | DONE |
| WC052-02 | Six customer-outcome epics contain thin vertical story skeletons | DONE |
| WC052-03 | Agent Employment Experience Contract skeleton separates customer, agent, and platform obligations | DONE |
| WC052-04 | Shared WAOOAW product gaps have ownership, earliest-wave, blocking class, and closure-evidence placeholders | DONE |
| WC052-05 | Existing Founder precedence and WC-044→048 reservations are reconciled without authorizing implementation | DONE |
| WC052-06 | Independent Business Architecture and Constitutional review is complete | DONE — R-028 APPROVED |

## Boundaries

- This Work Contract does not groom implementation-ready acceptance criteria, estimates, component tasks, or sprint commitments.
- Story entries remain hypotheses for focused grooming iterations.
- Reserved WC-044→048 identifiers remain reservations; this Work Contract does not create or authorize them.
- The four agent-domain gap registers remain separate planning inputs.
- No file under `src/` is created or modified.

## Verification

- Every story traces to one customer-outcome epic and at least one shared capability or agent-domain dependency.
- Every shared product gap has one earliest closure gate; no gap is merely marked "later."
- The contract skeleton references, but does not duplicate, ADR-035 and Agent Base Spec v1.0.
- `git diff --check` passes.
- Independent review records an APPROVED verdict before closure.

## Constitutional Basis

- C-001 — unconditional Human Override
- C-002 — trust through observable evidence
- C-009 — pre-employment rights visibility
- C-030 — Decision Space as the employment primitive
- C-031 — significant architecture decisions require an ADR
- C-034 — governed employment lifecycle
- C-037 — customer business outcomes are primary
- C-039 — conversational configuration
- C-059 — implementation traceability
- C-070 — common Constitutional DNA inheritance
- C-094 — Agent Base Spec compliance