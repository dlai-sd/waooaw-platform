# CB-008 - WC-080 Implementation Issue Binding Missing

| Field | Value |
|---|---|
| `institution_id` | `INST-010` |
| `record_id` | `CB-008` |
| `record_type` | Constitutional Blocker |
| `produced_at` | `2026-08-31` |
| Status | **RESOLVED** |
| Raised by | INST-010 - Platform IT Expert |
| Affected work | WC-080 Agent Runtime Adapter Contract v1 implementation |
| Accepted specification package | PR #384, merged as `bc836a6ecead6fd4f10e1e4feb12207a50d63ecc` |
| Resolution | GitHub issue #385 |

## Blocker

WC-080 required a Founder-assigned implementation issue binding the accepted commit, authorization
tier, branch, implementation paths, versions, CCTs, fixtures, environment boundary, qualification
command, tests, and stops before runnable implementation could begin.

## Resolution

Issue #385 now binds all required controls. It carries `tier:3-constitutional`, `approved:yogesh`,
`status:in-progress`, the accepted PR #384 merge commit, branch
`ib/080/agent-runtime-adapter-v1`, exact authorized paths, Adapter Protocol and Schema v1.0.0,
Digital Marketing v3.1.0 and Trading v1.8.0 fixtures, CCT and acceptance IDs, Docker-only validation,
the no-provider-mutation environment boundary, and the final qualification command.

## Gate Effect

- The missing implementation-issue gate is cleared.
- Platform IT Expert may execute WC-080 within issue #385 and all controlling-plan stops.
- This resolution grants no provider mutation, deployment, customer traffic, UAT, Production,
  self-approval, or merge authority.