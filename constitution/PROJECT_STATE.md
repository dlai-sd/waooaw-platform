# PROJECT_STATE.md

**State Schema:** 2.0.0
**State Revision:** 5
**Last Updated:** 2026-08-11
**Purpose:** Current operational state for bootstrap, recovery, and automated sprint controls.

This file is a snapshot, not a session ledger. Keep it below 200 lines. Update the active
checkpoint in place; record durable detail in the owning Work Contract, Goal record, review,
or evidence artifact. Completed history remains in git and the archive index below.

---

## Institutional Snapshot

| Field | Current Value |
|---|---|
| Epoch | Epoch 1 — Foundation |
| Gate | G5 CLEAR — prerequisites met; not session implementation authority |
| Engineering status | IMPLEMENTATION |
| Platform version | 1.45.0 |
| Latest completed Work Contract | WC-059 — AE-01 contract, payment, and exactly-once activation |
| Latest merge | PR #265 merged to `main` as `b0dbe9c` |
| Active implementation Work Contract | None |

## Active Checkpoint — PROJECT_STATE Schema V2

| Milestone | Status |
|---|---|
| Consumer and parser inventory | DONE — machine consumers require the unique `SPRINT_STATE_MACHINE` YAML block and scalar fields |
| Compact state schema | DONE — 94-line current snapshot with versioned metadata, recovery data, boundaries, and history pointers |
| BOOTSTRAP retention rule | DONE — update one checkpoint in place; archive durable detail outside the hot path; 200-line ceiling |
| Focused compatibility validation | DONE — 251 relevant tests pass; uniqueness, required-field, history, and line-budget checks pass |
| Independent review | DONE — R-085 APPROVED after R085-01 and R085-02 resolution |
| Founder PR | DONE — PR #266 is open against `main`; review and merge remain Founder-controlled |

### Recovery Context

- **Branch:** `chore/project-state-v2`
- **Objective:** Keep mandatory startup state concise, versioned, current, and machine compatible.
- **Hypothesis:** Historical session records are not parser inputs; removing them will not alter sprint tooling.
- **Validation:** Focused sprint-state parser tests plus structural checks for uniqueness, required fields, archive pointer, and line budget.
- **Protected local artifacts:** `.coverage` and `logs/blueprint_assurance_report.json` are unrelated and must remain unstaged.

## Authorization Boundary

This activity may compact and version governance state records and clarify BOOTSTRAP retention.
It does not authorize implementation code, live Razorpay or provider activation, WC-060,
deployment, self-review, self-approval, self-merge, or production/customer-proof claims.

## Current Blockers

None for the schema-v2 governance change. Independent review remains required before merge.

## Next Authorized Action

Founder reviews PR #266. No merge or further work follows automatically.

## History And Evidence

- History through 2026-07-22: `constitution/PROJECT_STATE_ARCHIVE.md`.
- History from 2026-07-23 through WC-059 closure: git object
  `b0dbe9c^2:constitution/PROJECT_STATE.md` (the merged PR #265 head snapshot).
- WC-059 durable evidence: `work-contracts/WC-059-ae01-contract-payment-activation.md`,
  `goals/GOAL-005-wc059-implementation-evidence.md`, and reviews R-083/R-084.
- Schema-v2 governance record and independent review:
  `work-contracts/WC-061-project-state-v2-governance.md` and R-085.
- Earlier completed work remains authoritative in its owning Work Contract, Goal, review,
  constitutional record, and repository history; it must not be copied back into this file.

---

## SPRINT_STATE_MACHINE
<!-- Machine-readable by autonomous-sprint.yaml. YAML-parseable block. -->
<!-- Edit ONLY the fields below. Do not alter the heading or fenced-block structure. -->
<!-- Task progress lives in work-contracts/WC-NNN-*.md, not here. -->

```yaml
autonomous_halt: false
platform_phase: IMPLEMENTATION
current_sprint: WC-034
sprint_status: DONE
branch: ib/014/wc034-f3-implementation
consecutive_failures: 0
tasks_done:
  - WC034-08
  - WC034-09
  - WC034-10
  - WC034-11
  - WC034-12
tasks_remaining: []
notes: |
  WC-034 F3 is complete and PR #254 merged as 8a1fcfa.
  This control block is retained for pipeline compatibility; it grants no new authority.
```

## Platform Delivery Summary

Last PM report: 2026-08-11
Platform Status issue: see GitHub Issues with label `platform-status`
