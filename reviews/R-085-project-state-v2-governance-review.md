# R-085 — PROJECT_STATE Schema V2 Governance Review

**Date:** 2026-08-11
**Scope:** WC-061 and the changes to `constitution/PROJECT_STATE.md`,
`constitution/PROJECT_STATE_ARCHIVE.md`, and `constitution/BOOTSTRAP.md`
**Review mode:** Independent, read-only governance and architecture review

## Decision

**APPROVED**

The compact schema preserves bootstrap recovery, the complete machine-readable sprint control
contract, historical recoverability, explicit versioning, and authorization boundaries. No
constitutional blocker or implementation-gate violation was found.

## Evidence Reviewed

- PROJECT_STATE reduced from 2,613 lines to 94 lines before condition remediation.
- All required `SPRINT_STATE_MACHINE` fields and fenced-block structure remain present.
- 251 focused parser and state-consumer tests pass.
- Structural checks enforce one state-machine block, required fields, history pointers, and the
  200-line budget.
- Git object `b0dbe9c^2:constitution/PROJECT_STATE.md` and all referenced WC-059 evidence resolve.
- Scoped `git diff --check` passes.

## Conditions

| ID | Condition | Resolution |
|---|---|---|
| R085-01 | Remove or close the branch-specific active-maintenance snapshot row before merge so it cannot become stale immediately | RESOLVED — the row was removed; the active checkpoint carries only recovery state |
| R085-02 | Preserve rationale, office, scope, and validation in a durable owning Work Contract or Goal record | RESOLVED — WC-061 is the durable governance record and is linked from PROJECT_STATE history |

## Final Disposition

Independent re-review confirmed both conditions are resolved, all links resolve, the compact
state remains below its line budget with one checkpoint and one sprint control block, and no new
blocker was introduced. Founder review and merge remain required. The implementation, deployment,
provider-activation, WC-060, self-review, and self-merge exclusions remain in force.
