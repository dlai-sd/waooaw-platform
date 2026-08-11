# WC-061 — PROJECT_STATE Schema V2 Governance

**Status:** DONE — pending Founder review and merge
**Office:** INST-010 — Platform IT Expert
**Reviewer:** Independent governance/architecture reviewer
**Authority:** Founder directive to keep `constitution/PROJECT_STATE.md` slim, relevant,
versioned, and useful during repeated Work Contract execution.

## Objective

Replace the mandatory bootstrap file's accumulated session ledger with a compact, versioned
current-state interface without weakening crash recovery, sprint parser compatibility, historical
recoverability, authorization boundaries, or independent review.

## Scope

| Task | Result |
|---|---|
| Inventory human and machine consumers | DONE — machine consumers depend on the unique `SPRINT_STATE_MACHINE` fenced YAML block and scalar fields |
| Define state schema v2 | DONE — current institutional snapshot, one active checkpoint, boundaries, blockers, next action, history pointers, and sprint controls |
| Preserve historical records | DONE — pre-2026-07-23 archive retained; 2026-07-23 through WC-059 retained at git object `b0dbe9c^2:constitution/PROJECT_STATE.md` |
| Prevent renewed growth | DONE — BOOTSTRAP requires in-place checkpoint updates, purpose-built durable evidence, semantic schema versioning, revision increments, and a 200-line ceiling |
| Validate compatibility | DONE — 251 focused consumer tests pass; structural, archive-resolution, evidence-link, whitespace, and protected-artifact checks pass |
| Independent review | DONE — R-085 approved with two conditions; both resolved in this Work Contract and the current-state snapshot |

## Acceptance Criteria

- `constitution/PROJECT_STATE.md` remains below 200 lines.
- Exactly one `## Active Checkpoint` and one `## SPRINT_STATE_MACHINE` block exist.
- Existing sprint-state consumers parse the unchanged control fields.
- Completed detail is retained in owning artifacts or immutable git history, not copied into the hot path.
- `.coverage` and `logs/blueprint_assurance_report.json` remain unstaged and outside this Work Contract.

## Exclusions

No implementation code, WC-060 execution, live Razorpay or provider activation, deployment,
self-review, self-approval, self-merge, or production/customer-proof claim is authorized.
