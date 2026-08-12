# GOAL-005 WC-060 Implementation Evidence

## Contribution Record

| Attestation field | Value |
|---|---|
| `institution_id` | INST-010 |
| `goal_id` | GOAL-005 |
| `record_id` | CR-GOAL-005-INST-010-06 |
| `record_type` | Contribution Record |
| `produced_at` | 2026-08-12T06:30:00Z |
| `authorization_id` | GOA-GOAL-005-INST-010-06 |
| `acceptance_record` | ACC-GOAL-005-INST-010-06 at 2026-08-12T04:00:00Z |
| Work Contract | WC-060, WC060-01 through WC060-09 |
| Learning output | LR-GOAL-005-INST-010-05 below |
| Decision | ACCEPTED - implementation complete; R-087, R-088, and R-089 APPROVED; unmerged PR pending |
| Authority boundary | No provider activation or credentials, deployment, F6-F8 feature implementation, production/customer proof, architecture reinterpretation, self-review, PR approval, merge, or self-merge |

## Scope

This contribution implements the sole WC-034 F5 contract: independently authenticated WhatsApp
identity, signed and evidenced channel handoff, relationship-bound runtime reconnect, tenant-safe
Customer Evidence Window and export, relationship-wide Emergency Stop, proof-bound Tier-4 release,
customer web/WhatsApp surfaces, adversarial CCTs, and proportional F8 acceptance. It does not claim
AE-02 execution, provider connection, deployment, production operation, customer proof, or merge.

## Acceptance Matrix

| Contract | Executable proof | Result |
|---|---|---|
| `UX-CONV-03` | Offline/reconnect fetches authoritative cursor before one submission; request carries the reconciled cursor and duplicate delivery produces one outcome | PASS |
| `UX-RES-02` | Before evidenced activation, target content is absent; timeout preserves source authority; stopped reconnect makes no committed-continuity claim | PASS |
| `UX-CONT-01` | Prepare returns `PREPARED`, leaves source `ACTIVE`, and does not change relationship lifecycle | PASS |
| `UX-CONT-02` | Target content renders only after authenticated activation returns durable resolution evidence | PASS |
| `UX-CONT-03` | Activation timeout reports unresolved and source remains authoritative | PASS |
| `UX-CONT-04` | Identical replay returns prior outcome; divergent idempotency reuse conflicts without mutation | PASS |
| `UX-CONT-05` | Assurance downgrade and cross-tenant attempts receive privacy-safe denial without protected identifiers | PASS |
| `UX-CONT-06` | Relationship Stop preempts activation; confirmed Stop immediately disables same-page commands and SSE remains the cross-session projection | PASS |
| Accessibility/responsive | Axe has zero serious/critical findings; key sections stay within exact 360x800 and 1440x900 viewports; keyboard Stop remains reachable | PASS |
| Privacy/PWA | Browser uses same-origin BFFs, protected payloads remain outside service-worker caches, and denial bodies omit relationship/participant material | PASS |
| Generated contract | OpenAPI Generator 7.17.0 regeneration from BP OpenAPI 1.7.0 produces no diff; Employment handoff, Stop, release, and Evidence Reader surfaces are pinned | PASS |

## Validation Evidence

| Slice | Result |
|---|---|
| Business Platform | PASS - 309/309 in a disposable .NET 9 container with `requirements-test.txt` and Docker/Testcontainers access |
| Constitutional Engine | PASS - 83/83 in .NET 9 Docker |
| Professional Runtime | PASS - 153/153 in the repository Docker runner |
| Web unit and contract | PASS - 89/89 Jest tests |
| Web coverage | PASS - 94.63% lines overall; changed `ConversationExperience` 94.75% and relationship surfaces 98.48% |
| Web lint/build | PASS - zero ESLint findings; strict TypeScript and Next.js production build complete with 23 routes |
| Browser | PASS - 106 tests across Chromium, Firefox, WebKit, exact 360x800, 1440x900, and 768x1024; 19 intentional project-scope skips |
| F5 focused browser | PASS - 8/8 exact compact/expanded scenarios with axe, containment, Stop, replay, denial, and reviewed active/stopped baselines |
| WC060 adversarial matrix | PASS - BP 19/19, PR 71/71, PostgreSQL 22/22, CE 5/5 |
| Generated-client conformance | PASS - deterministic regeneration has zero diff; boundary test requires OpenAPI 1.7.0 and Employment API/models |
| Diff hygiene | PASS - `.coverage` and `logs/blueprint_assurance_report.json` remain protected and unstaged |

The full BP run initially failed in incomplete SDK-only and socket-restricted containers. Those
runs are not cited as product failures: the authoritative rerun used the repository-declared Python
test dependencies plus Docker access and passed 309/309.

## Implementation Findings Closed

- Committed handoff replay now verifies the envelope and target context before returning prior success.
- Handoff activation rebinds tenant, relationship, participant, conversation, checkpoint,
  idempotency, freshness, role, authority, and assurance; downgrade and confused-deputy attempts fail closed.
- Relationship Stop state now reaches conversation controls directly after authoritative same-page
  confirmation instead of depending on stream delivery; SSE continues to project Stop across sessions.
- Compact visual review found and repaired clipped navigation, colliding acknowledgement text, and
  unreadably narrow workspace sections that a document-level overflow check did not detect.
- WebKit reconciles durable evidence and cancellation through the authoritative BFF/timeline when
  its browser-test fetch stream buffers an open response; Chromium and Firefox retain live stream proof.

## Residual Limits And Review Handoff

Browser scenarios use deterministic contract fixtures and are not deployment or customer proof.
No live Meta, Keycloak, Razorpay, provider, or production credential was configured. Independent
INST-007 approved identity, HMAC, replay, release, and privacy boundaries in R-087; INST-006 approved
Migration 22 ownership, RLS, retention, and reconstruction in R-088; fresh INST-004 approved
integrated ownership, generated-contract compatibility, F5/F8 evidence, and visual acceptance in
R-089. INST-010 does not self-review, approve, merge, deploy, or declare Goal completion.

## Learning Record

| Attestation field | Value |
|---|---|
| `institution_id` | INST-010 |
| `goal_id` | GOAL-005 |
| `record_id` | LR-GOAL-005-INST-010-05 |
| `record_type` | Learning Record |
| `produced_at` | 2026-08-12T06:30:01Z |
| `authorization_id` | GOA-GOAL-005-INST-010-06 |
| Contribution | CR-GOAL-005-INST-010-06 |
| `improvement_signal` | Cross-channel acceptance must rebind signed replay inputs before returning stored success, and responsive review must inspect element containment and rendered baselines rather than relying only on document scroll width. |
| `constitutional_discovery` | no |
| `evolution_triggered` | no |

### Reusable Learning

1. Stored success is not authorization for the current request. Verify the current signed artifact,
   authenticated target, assurance, authority, freshness, and idempotency identity before replay.
2. Browser-supplied session lists cannot define relationship Stop scope. The server must discover
   the relationship's current executions, while the UI projects confirmed Stop immediately and
   remains independent of a particular stream implementation.
3. A green `scrollWidth <= clientWidth` check can coexist with clipped controls and unreadable grid
   tracks. Required-width acceptance needs element containment plus reviewer-visible screenshots.
4. Open-ended SSE behavior differs across browser harnesses. Durable terminal state must always be
   recoverable from the authoritative timeline; live stream evidence is additive, not the sole truth.
5. Cross-stack .NET tests that invoke Python and Testcontainers require the complete declared test
   environment. Partial SDK images can create misleading infrastructure failures.

No new constitutional principle or institutional capability gap was discovered. These findings fit
the existing C-001, C-023, C-026, C-032, C-063, C-071, C-076, and WC-060 obligations, so no
constitutional evolution is triggered.