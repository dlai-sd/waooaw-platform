# WC-105 - Authentication, Guide, Session, And Landing Defect Repair

## Record Control

| Field | Value |
|---|---|
| Office | Platform IT Expert (INST-010), Skills 1-7, 11, 12, 14 and 16 |
| Authorized by | Founder instructions in the 2026-09-21 working session |
| Status | IMPLEMENTATION AUTHORIZED - LOCAL SOURCE, TESTS, PREVIEW, AND UNMERGED PR |
| Baseline | `818ec26441d39b3f13cb75a7650d9389b8cff462` |
| Delivery unit | One bounded defect-repair PR |

## Authority And Scope

The Founder authorized repair and complete testing of the reported authentication, customer portal,
identity-session, Guide, and landing-page defects. The Founder accepted the revised landing preview
on 2026-09-21 and authorized conversion of that preview into durable requirements and executable
evidence.

Authorized changes are limited to the existing Business Platform and Web Application components,
focused tests, this Work Contract and ledger, local Docker validation, the Codespace preview, and one
unmerged PR. Google consent-screen configuration and Google branding are deferred. No cloud mutation,
deployment, provider configuration, customer traffic, Production action, approval, or merge is
authorized.

## Inputs

- Founder defect list and accepted landing-page screenshots from the 2026-09-21 working session.
- WC-093 public/authentication presentation and WC-103 multi-tenant authentication contracts.
- Existing identity security data contract and customer portal membership boundary.
- Exact `origin/main` baseline and repository Docker runners.

## Canonical Requirement Index

| Requirement | Required observable behavior | Executable evidence |
|---|---|---|
| WC105-R001 | Google and other enabled providers launch directly without a WAOOAW intermediate disclosure; Google retains explicit account selection. | Provider command component tests. |
| WC105-R002 | An authenticated customer with an incomplete profile is routed to registration with a sanitized return destination from both login and application-shell entry. | Auth view and application layout tests. |
| WC105-R003 | Concurrent observations of one broker session produce one account-scoped session and one idempotent establishment event without serialization failures or Marketplace `500` responses. | Real PostgreSQL eight-request concurrency test and identity HTTP regression. |
| WC105-R004 | Guide interaction GET and POST resolve customer membership before service execution so a valid customer does not receive a route-owned `401`. | Portal interaction controller tests. |
| WC105-R005 | The Guide composer contains an accessible icon-only up-arrow Send command; a microphone appears only when voice is backend-enabled and browser-supported. | Guide component tests and TypeScript validation. |
| WC105-R006 | Identity security-event persistence remains idempotent for replayed deterministic event keys and does not create duplicate establishment events. | Real PostgreSQL concurrency/event-count assertion and security-event tests. |
| WC105-R007 | Identity-event persistence failure remains bounded and cannot silently be represented as successful durable evidence. | Existing timeout/failure tests or an explicit blocked result when the reported runtime response cannot be reproduced locally. |
| WC105-R008 | Session revocation permits the owning account, remains idempotent, rejects inaccessible sessions, and does not weaken authorization to hide an unexplained `403`. | Session lifecycle and HTTP authorization tests; observed external `403` remains blocked without its response evidence. |
| WC105-R009 | The accepted landing hero uses equal-height cards, card frames 20% wider than the prior `93.6%` width without widening the stage, rear cards dimmed by a further 20%, and the desktop showcase moved down 20%. | Production browser geometry at desktop and mobile. |
| WC105-R010 | DMA copy reads `Watch chaos turn into clarity - You only step in when it matters.` and `Digital Marketing on fire`; problem cards use staggered focus motion while reduced-motion behavior remains respected. | Component copy/timer tests and production browser inspection. |
| WC105-R011 | The revised hero has no horizontal overflow, content clipping, CTA collision, runtime error, or unsupported mobile/desktop layout. | Production Chromium geometry at 1365x720 and 390x844 plus configured browser regression where available. |
| WC105-R012 | The complete changed surface passes focused tests, type checking, production build, diff review, requirement-ledger validation, and exact-head PR prechecks. | Docker test/build output, author review, and prepared PR evidence. |

## Definition Of Done

- Every requirement is recorded in `work-contracts/WC-105-requirements.yaml` with source, owner,
  evidence class, direct test path, completion rule, result, and residual risk.
- Every in-scope behavior has executable evidence; blocked external observations remain explicitly
  blocked and are not represented as fixed.
- Relevant Business Platform and Web tests, TypeScript, production build, browser geometry, and
  repository PR prechecks pass against the final committed head.
- Author review covers correctness, concurrency, authorization, privacy, accessibility, responsive
  layout, rollback, and scope.
- The branch is pushed and one unmerged PR is submitted for Founder review.

## Stop Conditions

Stop on any requirement to weaken membership or revocation authorization, suppress persistence
failure, change provider/cloud configuration, add a dependency, deploy, access customer data, mutate
Demo/UAT/Production, bypass a quality gate, self-approve, or self-merge. An unreproduced event timeout
or revocation `403` must remain blocked rather than receive a speculative repair.

## Rollback

Revert the bounded commits. No schema, migration, provider, secret, cloud, or customer-data rollback
is required.

## Post-Deployment RCA And Follow-Up Requirements

PR #470 was deployed from merge commit `e9c8726f41ba594ee7897ea76b8aab19cdbe2da1` to the intended
Demo revisions and image digests. The deployment was correct, but retained Azure telemetry from
2026-09-22 disproved customer-journey completion and established the following bounded follow-up.

| Requirement | Unresolved point | RCA | Azure evidence | Authorized fix | Closure evidence |
|---|---|---|---|---|---|
| WC105-R013 | Marketplace / My Agents unavailable | One protected render fans out through layout and page identity-session calls. Session locking ends before establishment-event persistence, so a shared identity dependency can fail while the marketplace and relationship APIs succeed. | Marketplace and relationships returned `200`; concurrent identity-session requests returned `200`, `403`, and `409`, with PostgreSQL `40001` and `23505`. | Deduplicate identity resolution within one server render and keep session observation plus establishment-event outcome inside one serialized, idempotent boundary. | Protected-render component tests and a concurrent real-PostgreSQL service test complete without duplicate session observations, database command failures, or incorrect protected content. |
| WC105-R014 | Duplicate identity events | Concurrent callers insert the same deterministic source event. Exception recovery depends on one direct wrapper shape and allows a wrapped unique violation to escape. | Repeated `23505` for `identity_security_events_source_unique` wrapped in `DbUpdateException`. | Persist with atomic PostgreSQL conflict handling and return the existing outcome without exception-driven duplicate control flow. | Parallel same-source writes all complete, exactly one event is stored, and no database error is emitted. |
| WC105-R015 | WAOOAW Guide initial `503` | Guide membership/session middleware can fail before controller execution; first-use context creation also uses a check-then-insert sequence. | Guide GET returned `503` beside the identity-event `23505`; a later request returned `200`. | Remove the identity-event failure path, make Guide context creation atomic under concurrent first use, and preserve downstream problem code and correlation ID. | Simultaneous first Guide loads return `200`, share one context, and expose typed diagnostics for an injected downstream failure. |
| WC105-R016 | Security-event timeout | The Web waits five seconds for event persistence while duplicate writes and database contention prevent a durable response. | Repeated Web `TimeoutError`; backend event requests included `499` and duplicate-key failures. | Use bounded atomic persistence and distinguish accepted duplicate, dependency failure, timeout, and caller cancellation without reporting false durable success. | Concurrent persistence completes within the bounded test deadline with one event; timeout and failure tests preserve truthful typed outcomes. |
| WC105-R017 | Identity / alerts `403` | The Web maps every identity `403` to step-up although the backend distinguishes step-up from action denial and other typed identity outcomes. | Demo identity and alerts requests returned `403`; the client projected a generic or misleading state. | Classify identity responses by the backend problem `code`, reserve step-up for `IDENTITY_STEP_UP_REQUIRED`, and preserve the correlation ID for diagnostics. | Contract tests cover each supported `403` code and the alerts/protected-route presentation receives the correct typed state. |

The follow-up remains limited to Business Platform and Web source, focused tests, this Work Contract
and its requirement ledger, Docker validation, and one unmerged PR. It does not authorize deployment,
provider mutation, customer traffic, approval, or merge.