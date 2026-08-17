# WC-076 - PR #292 Constitutional Repair

**Goal:** GOAL-007
**PR:** #292
**Blocker:** CB-007 / Issue #293
**Office:** INST-010 - Platform IT Expert
**Tier:** Tier 1 bug fix
**Status:** AUTHORIZED AND ACCEPTED
**Constitutional basis:** C-023, C-059, C-062, C-065, C-066, C-076, C-080; ADR-013; ADR-045

## Authority

The Founder explicitly approved this complete repair scope for the current human session on
2026-08-17 and directed one lightweight execution record with priority on code and evidence.
This record is the approved bug-fix specification and Work Contract.

| Record | Time | Authority |
|---|---|---|
| `FA-051` | `2026-08-17T10:53:16Z` | Founder current-session implementation approval for WC-076 recorded |
| `GOA-GOAL-007-INST-010-01` | `2026-08-17T10:53:17Z` | INST-013 routing token issued ministerially under FA-051 |
| `ACC-GOAL-007-INST-010-01` | `2026-08-17T10:53:18Z` | INST-010 accepts the complete repair envelope |

The contribution envelope is indivisible: repair fail-closed C-059/C-066 gates; complete ADR-045
Docker runners for .NET and Web tests; repair the AIR transcription response contract and its
integration coverage; remove or govern dependency-scan exceptions; correct PR disclosure; validate,
push, and request fresh independent review.

## Acceptance

- Missing or incomplete authorization evidence fails CI.
- .NET, Python, and Web automated tests execute in Docker and retain coverage evidence.
- Voice orchestration persists the validated AIR `transcriptionId` and proves the real HTTP-client path.
- Dependency audits pass without unexplained suppressions; any unavoidable exception has owner,
  rationale, expiry, and remediation trigger.
- PR #292 truthfully describes its complete scope and all required CI checks pass.
- A fresh independent reviewer closes or retains CB-007 against the repaired SHA.

## Boundary

This authorizes repository-only implementation and validation on `fix/qa-ci-job-conditions`.
It grants no cloud, deployment, Production, expenditure, self-review, PR approval, or merge authority.
The Founder remains the merge authority after independent approval.
