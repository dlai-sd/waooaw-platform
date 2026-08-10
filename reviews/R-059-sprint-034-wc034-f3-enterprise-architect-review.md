# R-059 — WC-034 F3 Conversation Core Enterprise Architect Review

| Field | Value |
|---|---|
| `institution_id` | INST-004 |
| `work_contract` | WC-034 / IB-014 / F3 Conversation Core |
| `commit_reviewed` | `f06cbaf` |
| `record_id` | R-059 |
| `review_type` | Independent architecture and contract review under C-065 |
| `produced_at` | 2026-08-10 |
| **Decision** | **APPROVED** |

## Independence Declaration

This review was performed by a fresh, read-only INST-004 instance that did not author the
reviewed F3 package. The reviewer loaded the Enterprise Architect charter and professional
standard, inspected only architecture and governance inputs, and did not inspect application
source, edit files, commit, push, or participate in F3 authoring.

## Scope

Reviewed:

- `architecture/reference/components/conversation-core.md`;
- Business Platform OpenAPI 1.2.0 F3 operations and schemas;
- Professional Runtime OpenAPI 1.1.0 F3 internal operations and schemas;
- BP/PR component ownership updates;
- WC-034 shell, decomposition, acceptance, dependency, and authorization boundaries;
- OpenAPI Generator 7.17.0 validation/generation and strict TypeScript evidence.

Excluded and not authorized: application code, `@ai-sdk/react`, direct browser-to-PR or
provider connections, attachments, voice, F4-F8, provider activation, deployment, merge,
version closure, and implementation CCT execution.

## Conformance Result

| Area | Result | Evidence |
|---|---|---|
| Public/internal ownership | **PASS** | BP is the sole ordinary public ingress; all PR F3 operations are `x-internal` and require BP service authentication; existing Stop transport is unchanged |
| Public conversation contract | **PASS** | Timeline, send, retry, read-position, cancellation, and BP SSE are complete and versioned |
| Internal execution contract | **PASS** | PR start/replay, cancellation, and typed resumable SSE are explicit and BP-only |
| Versioned data shapes | **PASS** | Message V1, Action/Plan/Deliverable/Decision card V1, BP event V1, and PR event V1 have compatibility rules |
| Idempotency and reconciliation | **PASS** | Original key/hash replay, divergent conflict, authoritative cursor fetch, client-message matching, and no timeout success are deterministic |
| Privacy and tenant isolation | **PASS** | JWT/service-assertion tenant derivation, normalized inaccessible response, no protected URL/cache/telemetry surface |
| Stop and Evidence First | **PASS** | Stop preempts execution; reconnect cannot release it; delivery, processing, and CE-confirmed evidence remain independent |
| Error contract | **PASS** | RFC 9457 public/internal codes are stable, privacy-safe, and actionable without leaking dependency detail |
| F3 acceptance mapping | **PASS** | UX-CONV-01–07, CCT-UX-HO-01–03, CCT-UX-EF-01–02, UX-PWA-03, UX-RES-01, and supporting contract/privacy/accessibility IDs map to concrete surfaces |
| Generator compatibility | **PASS** | F3-filtered BP spec validates and generates; generated `ConversationApi.ts` and models compile under strict TypeScript; no tenant/private runtime/provider surface |
| Scope and authority | **PASS** | No application code, dependency, provider connection, F4-F8 work, or deployment authority is introduced |

## Findings

| ID | Priority | Finding | Disposition |
|---|---|---|---|
| CR-F3-01 | P0 | BP sole-ingress and PR internal-only boundary is complete | APPROVED |
| CR-F3-02 | P0 | Versioned message/card/event contracts and compatibility rules are complete | APPROVED |
| CR-F3-03 | P0 | Canonical timeline/send/retry/read-position/cancel/stream behavior is complete | APPROVED |
| CR-F3-04 | P1 | Idempotency and unknown-outcome semantics do not permit duplicate or fabricated success | APPROVED |
| CR-F3-05 | P1 | Offline reconciliation is deterministic and relationship-local | APPROVED |
| CR-F3-06 | P1 | Privacy and tenant isolation are structurally enforced by the contracts | APPROVED |
| CR-F3-07 | P1 | Stop and Evidence First semantics remain independent and authoritative | APPROVED |
| CR-F3-08 | P1 | Public and internal error contracts are normalized and complete | APPROVED |
| CR-F3-09 | P1 | All F3 acceptance IDs have concrete contract evidence | APPROVED |
| CR-F3-10 | P1 | Generated-client evidence closes the F3 contract compatibility requirement | APPROVED |
| CR-F3-11 | P2 | Dependency gates are complete and correctly preserve implementation/deployment blockers | APPROVED |
| CR-F3-12 | P2 | Explicit exclusions prevent authority leakage into F4-F8 or dependencies | APPROVED |
| CR-F3-13 | P2 | Existing reference architecture is decomposed without a new deployable component | APPROVED |

## Dependency Gate Decision

| Gate | Review decision |
|---|---|
| G-F3-01 BP public OpenAPI | **CLEARED** |
| G-F3-02 PR internal OpenAPI | **CLEARED** |
| G-F3-03 data, idempotency, privacy, tenant, error, reconciliation semantics | **CLEARED** |
| G-F3-04 acceptance mapping | **CLEARED** |
| G-F3-05 independent INST-004 review | **CLEARED by R-059** |
| G-F3-06 generated-client compatibility | **CLEARED** |
| G-F3-07 no new deployable component | **CLEARED** |
| G-F3-08 implementation authorization | **BLOCKED — separate Founder/GO authorization required** |
| G-F3-09 deployment authorization | **BLOCKED — separate Founder action required** |

## Validation Note

Full Business Platform validation continues to report pre-existing dangling schemas outside
the F3 surface. The dependency-closed F3 specification has zero validation issues and the
generated Conversation client compiles without manual patches. The pre-existing full-spec
debt does not originate in or block this architecture package.

## Decision

**APPROVED.** WC-034 F3 architecture and dependency closure is complete. The package is ready
for a separately authorized implementation selection. This review does not authorize
implementation, dependency installation, F4-F8, provider connection, deployment, or merge.