# WC-121 - Customer Engagement Workspace Implementation

## 0. Record Control

| Field | Value |
|---|---|
| Work Contract | WC-121 |
| Version | 1.0.0-candidate.6 |
| Status | AUTHOR REVIEW PASS - SPECIALIST-INTEGRATED CANDIDATE FOR FOUNDER REVIEW - IMPLEMENTATION BLOCKED |
| Authorizing Office | Founder approval required |
| Specification Office | Chief Solution Architect, Office 05 |
| Implementation Office | Platform IT Expert |
| Enterprise input | `architecture/reference/components/customer-engagement-workspace-enterprise-requirements.md` |
| Solution input | `architecture/reference/components/customer-engagement-workspace-solution-contract.md` |
| Additive API input | `architecture/reference/api-specs/customer-engagement-workspace-business-platform.openapi.yaml` |
| Channel API input | `architecture/reference/api-specs/channel-neutral-conversation-business-platform.openapi.yaml` |
| Result | PLANNED |

This candidate Work Contract does not authorize implementation. G5 CLEAR, a backlog entry, a GitHub
issue, or Founder acceptance of this document does not by itself authorize a current-session source
change. Before runnable code, generated implementation artifacts, or build artifacts are created,
the Platform IT Expert must receive explicit current-session implementation authorization.

Provider mutation, cloud mutation, deployment, external traffic, activation, PR approval, and merge
are independent protected actions. None is implied by implementation authorization.

## 1. Objective and Customer Outcome

Deliver one conversation-first Customer Engagement Workspace through:

1. a responsive Customer Portal with configurable context, conversation, and adaptive progress
   regions;
2. a WhatsApp presentation with the same lifecycle, terminology, professional identity, owner
   state, evidence meaning, and safe next actions;
3. complete conversational registration/login continuation, Trial, Hire, induction, skills/goals,
   operations, performance, logout, and WhatsApp end-session journeys; and
4. same-image functional parity across Demo-, UAT-, and Production-shaped configuration.

Customers may use Portal, WhatsApp, or both without creating duplicate accounts, relationships,
conversations, commands, professional work, or evidence.

## 2. Authority and Entry Gates

### 2.1 Mandatory gates before Component 01

All must be true:

1. Founder accepts the exact versions of the Enterprise requirements, CSA-CEW-001, candidate API,
   and WC-121.
2. Candidate package passes the repository's Docker-only architecture validation.
3. Required accepted ADR and owner contracts remain compatible.
4. The current session receives explicit implementation authorization.
5. Platform IT Expert completes an impact analysis and records every changed file, owner, migration,
   generated artifact, test, deployment surface, and rollback dependency.
6. The exact source digests accepted by the Founder are recorded in the implementation issue or
   branch evidence.
7. Existing WC-113 through WC-120 capabilities that are reused are either accepted/available or
   replaced by an explicitly authorized dependency plan; no silent substitute is allowed.
8. The Data Architect disposition is accepted for the exact candidate and every affected data
   class has an accepted owner lifecycle policy, tenant boundary, migration path, and evidence plan.
9. Platform Architecture and the Founder have accepted numeric RPO, RTO, backup retention, and
   recovery-environment authority for the affected persistence owners.
10. The Security Architect disposition and CSA-CEW-001 Section 11 security envelope are accepted for
   the exact candidate, and the impact analysis maps every public/internal edge to its accepted
   identity, assurance, authorization, Stop, webhook, abuse, workload, key, encryption, redaction,
   revocation, and rollback contract.
11. The Platform Architect disposition and CSA-CEW-001 Sections 13.5-13.12 are accepted for the
    exact candidate, and impact analysis freezes existing-workload placement, configuration and
    secret-catalog bindings, health/readiness semantics, capacity envelope, backpressure, SLO/alert
    ownership, immutable release tuple, migration/deployment/rollback sequence, and DR dependencies.

Failure of any gate makes Component 01 and all dependents `BLOCKED`.

### 2.2 Additional gates before Component 07

1. The accepted channel-neutral conversation and WhatsApp foundation is implementation-ready.
2. Identity assurance, webhook verification, replay, handoff, message-state, and data-rights
   contracts are accepted for the exact candidate.
3. Approved emulators contain no provider secrets or protected full telephone identity.

### 2.3 Additional gates before Component 09

All must be separately recorded:

1. CEW-WC-08 passes on the exact deployable image.
2. Same sender/recipient feasibility closes under CSA-CEW-001 Section 13.4, or a distinct authorized
   recipient is provided.
3. Provider account and credential-use authority.
4. Azure/cloud mutation authority.
5. Deployment authority for the target environment.
6. External traffic authority for the bounded recipient set.
7. Activation authority.
8. Approved observability, rollback, incident owner, test window, and spend boundary.
9. Accepted numeric SLO/error-budget and queue-age targets, qualification load, alert routing,
   capacity envelope, and bounded recovery objective.
10. Accepted RPO, RTO, backup retention, regional-copy policy, recovery environment, and
    recovery-execution authority for every affected durable owner.

Component 09 is `BLOCKED` until every item is true.

## 3. Constitutional and Architectural Basis

WC-121 implements:

1. `CEW-ER-001` through `CEW-ER-046`;
2. `CEW-FIT-01` through `CEW-FIT-26`;
3. CSA-CEW-001 decisions `CEW-SD-001` through `CEW-SD-015`;
4. the existing Customer Portal, Identity Boundary, Conversation Core, Agent Employment Experience,
   Omnichannel Continuity, Hybrid Application Shell, Hybrid Visual System, and Hybrid UI Acceptance
   contracts; and
5. canonical BP and channel-neutral API ownership.

If an implementation detail conflicts with these sources, the higher source wins and work stops for
clarification. The implementer does not reinterpret enterprise requirements.

## 4. Permitted and Prohibited Repository Surfaces

### 4.1 Permitted roots

After implementation authorization, only impact-analysis-listed files under these roots may change:

| Surface | Permitted purpose |
|---|---|
| `architecture/reference/api-specs/business-platform.openapi.yaml` | Merge the accepted additive API contract |
| `architecture/reference/api-specs/customer-engagement-workspace-business-platform.openapi.yaml` | Maintain exact candidate/evidence until canonical merge |
| `architecture/reference/api-specs/channel-neutral-conversation-business-platform.openapi.yaml` | Compatible accepted amendments only; no fork |
| `src/business-platform/**` | BP admission tightening, projection, focus, preference, channel-session facade, adapter boundary |
| `web/**` | Portal shell, generated BP client consumption, presentation, accessibility, browser tests |
| `tests/**` | Unit, contract, integration, security, privacy, journey, migration, and evidence tests |
| `docs/runbooks/**` | Customer-engagement operations and rollback runbooks |
| `infra/**` | Component 09 only, after separate cloud/deployment authority |
| `.github/workflows/**` | Component 09 only, after separate CI/deployment-workflow authority |

Existing canonical migration directories inside `src/business-platform/**` are permitted only for an
additive, rollback-specified migration approved by impact analysis.

### 4.2 Prohibited without a new Work Contract or explicit amendment

1. Constitution, Genesis, or immutable governance changes.
2. New deployables, public facades, lifecycle owners, identity stores, relationship stores,
   conversation stores, progress truth stores, or evidence stores.
3. Direct client integration to PR, AIR, WBE, CE, adapters, or provider business APIs.
4. Changes under PR, AIR, WBE, CE, or identity-provider implementation roots.
5. Provider credentials, full protected phone identities, live payload captures, or secrets in any
   repository artifact.
6. DMA-specific shared-platform state, route, schema, or branch.
7. Environment-specific product forks or reduced Demo builds.
8. Deployment, traffic, activation, PR approval, or merge.

If impact analysis shows a required change outside permitted roots, stop and request an amended Work
Contract. Do not expand scope by convenience.

## 5. No-Drift Implementation Rules

1. Reuse and tighten existing `admitEmploymentRelationship`; do not add a competing admission.
2. Reuse canonical relationship workspace and owner projections; do not store duplicate lifecycle
   or readiness truth.
3. Merge the accepted additive API into canonical BP before Portal/adapter code consumes it.
4. Generate clients from the accepted canonical contract; do not hand-maintain competing request or
   response types.
5. All owner writes are typed commands with idempotency, correlation, versioning, evidence, and
   explicit error semantics.
6. Portal and WhatsApp render the same server-projected next action and status meaning.
7. Layout and focus preferences never grant authority or change business state.
8. Focus tokens are body-only opaque references, never URL values or authority grants, and are
   reauthorized on every resolution under CSA-CEW-001 Sections 10.8 and 11.4.
9. Login, registration, logout, end-session, unlink, switch, termination, deletion, and Stop remain
   separate operations.
10. Unknown, unavailable, disputed, partial, stale, failed, and blocked never render as empty or
    successful.
11. The exact image carries every route, component, schema, and lifecycle behavior in each
    environment-shaped configuration.
12. Default-off controls evaluate authority/configuration, never an environment-name branch.
13. Emulator evidence is labeled emulator evidence and cannot satisfy live-provider acceptance.
14. Use `DEMO_WHATSAPP_SENDER_REF` and `DEMO_WHATSAPP_TEST_RECIPIENT_REF`; never persist the resolved
    values in repository, URL, log, telemetry, transcript, screenshot, or evidence.

## 6. Work Component Plan

### 6.1 CEW-WC-01 - Contract Baseline and Generated Clients

**Outcome:** canonical BP exposes the accepted customer-engagement delta and generated clients build.

**Tasks**

1. Pin accepted source digests and complete changed-path/owner impact analysis.
2. Merge candidate paths and schemas into canonical BP without deleting supported fields.
3. Tighten admission with idempotency key, exact disclosure/version/intent, atomic result, stable
   replay, and explicit errors.
4. Add layout preferences, relationship preferences, engagement progress, focus resolution, and
   channel-session end contracts.
5. Resolve external references in the channel-neutral contract without copying or forking schemas.
6. Regenerate clients through repository tooling.
7. Add producer/consumer compatibility fixtures and negative security fixtures.

**Completion**

- OpenAPI lint, slice, reference, compatibility, and generated-client checks pass.
- Existing supported consumers pass.
- Same idempotency key and digest replay; key reuse with changed input conflicts.
- No second public facade or schema fork exists.

### 6.2 CEW-WC-02 - Portal Workspace Shell

**Depends on:** 01.

**Outcome:** expanded and compact Portal compositions are conversation-first and accessible.

**Tasks**

1. Implement context, conversation, and adaptive progress regions using the accepted shell and
   visual-system tokens.
2. Implement eligible hide/show/collapse/resize behavior and accessible restoration.
3. Persist account layout through identity settings, relationship defaults through Onboard
   preferences, and transient focus only in session presentation state.
4. Keep Stop, current lifecycle, identity state, required action, and recovery reachable.
5. Bind compact context/progress sheets to the same semantics and commands.
6. Eliminate raw platform/provider/workflow vocabulary from customer presentation.

**Completion**

- Expanded and 360px compact tests pass.
- Keyboard, screen-reader, 200% zoom, RTL, reduced-motion, and focus-restore tests pass.
- Preference mutation changes no relationship or owner truth.
- The client network allowlist contains only generated BP, identity handoff, and Stop traffic.

### 6.3 CEW-WC-03 - Acquisition and Identity Continuity

**Depends on:** 01-02.

**Outcome:** discovery, registration/login continuation, and exact relationship admission work
without identity/employment conflation.

**Tasks**

1. Implement anonymous need-led marketplace discovery from published facts only.
2. Preserve only allowlisted non-secret Trial/Hire context through identity-owned pages/redirects.
3. Return to exact safe context after registration, login, step-up, or stale-session recovery.
4. Invoke the one admission operation only after explicit Trial/Hire intent and exact disclosure.
5. Render the admitted `DISCOVERED` relationship, conversation, and resume focus.
6. Keep credentials, provider tokens, and institutional registration outside professional history.

**Completion**

- Anonymous discovery produces zero prohibited writes.
- Identity success alone produces no relationship.
- Duplicate/timeout/cross-channel admission produces one relationship, agent instance,
  conversation, workspace, and evidence outcome.
- Open-redirect, cross-tenant, disclosure-version, and inactive-admission negatives pass.

### 6.4 CEW-WC-04 - Trial, Hire, and Lifecycle Workspace

**Depends on:** 01-03.

**Outcome:** Trial and Hire are conversational, evidenced, idempotent, commercially distinct, and
visible through adaptive progress.

**Tasks**

1. Bind Trial and Hire turns to existing trial, contract, billing, payment, and lifecycle owners.
2. Show effect, authority, cost, limitation, confirmation, cancellation, and recovery.
3. Render lifecycle stage, required action, evidence freshness, and commercial state from BP.
4. Reconcile timeout and unknown outcome before retry.
5. Preserve one transcript while visual focus changes.

**Completion**

- Discovery-to-Trial and discovery-to-Hire journeys pass without a primary long form.
- Trial and Hire owner calls/evidence/commercial results are distinct.
- Progress never infers eligibility or completion.
- Consequential-action disclosure snapshots pass.

### 6.5 CEW-WC-05 - Induction, Skills, Goals, and Planning

**Depends on:** 01-04.

**Outcome:** customers configure the professional conversationally and verify versioned detail
visually.

**Tasks**

1. Render known, missing, owner, reason, blocked effect, freshness, and next question.
2. Compose and confirm skills, goals, plan, milestones, schedule, budget, and Decision Space through
   existing typed commands.
3. Show version conflicts and material changes before reconfirmation.
4. Keep visual forms secondary and prevent silent authoritative commit.
5. Support DMA and one non-DMA fixture without shared-platform specialization.

**Completion**

- First-use timing, required-field, conflict, correction, and evidence tests pass.
- Visual navigation performs no owner write.
- DMA Packages A-E and non-DMA fixture pass the same shell/lifecycle/progress/channel contract.

### 6.6 CEW-WC-06 - Operations and Performance

**Depends on:** 01-05.

**Outcome:** operations and performance show customer outcomes and independent truth dimensions.

**Tasks**

1. Render operation scheduling, working state, alerts, budget, evidence, and recovery.
2. Keep delivery, processing, evidence, commercial, and outcome dimensions independent.
3. Lead performance with business outcomes and show technical metrics only as supporting evidence.
4. Provide typed correction, reconciliation, next-goal, and Stop routes.
5. Implement telemetry and runbooks without protected payloads.

**Completion**

- All five truth dimensions vary independently in fixtures.
- Unknown/stale/partial/blocked/unavailable/disputed states never render as success.
- Outcome-first snapshots, operation replay, evidence outage, and Stop tests pass.
- Performance and telemetry budgets in CSA-CEW-001 pass.

### 6.7 CEW-WC-07 - WhatsApp Parity and End-Session

**Depends on:** 01, 03-06 and Section 2.2 gates.

**Outcome:** WhatsApp provides the same customer lifecycle and distinct session semantics through
the approved adapter and BP contracts.

**Tasks**

1. Render shared professional identity, terminology, status, evidence, and next action.
2. Bind inbound choices/contributions to the same typed commands and canonical conversation.
3. Keep institutional registration exchange out of professional context.
4. Implement secure Portal continuation and exact focus return.
5. Implement WhatsApp end-session as the bounded channel-session command.
6. Preserve provider delivery truth separately from owner processing/evidence/outcome.

**Completion**

- Portal/WhatsApp parity, webhook verification/replay, identity-assurance, content-limit, and
  transcript-isolation tests pass.
- End-session affects only the named session.
- Provider failure cannot duplicate a business command.
- Stop is directly invocable in every supported WhatsApp state.

### 6.8 CEW-WC-08 - Cross-Channel and Same-Image Qualification

**Depends on:** 02-07.

**Outcome:** the exact deployable image satisfies all enterprise fitness obligations in emulated,
environment-shaped qualification.

**Tasks**

1. Run Portal-to-WhatsApp-to-Portal handoff at every lifecycle stage.
2. Race retry, timeout, replay, concurrent focus, session end, logout, switch, unlink, Stop,
   termination, and deletion.
3. Execute security, privacy, accessibility, performance, operability, migration, and rollback
   suites.
4. Record one image digest and compare route/component/command/schema/lifecycle manifests across
   Demo-, UAT-, and Production-shaped configuration.
5. Run default-off and enabled qualification on the same image.
6. Produce a `CEW-FIT-01` through `CEW-FIT-26` evidence index.
7. Prove CEW adds no deployable, public ingress, store, queue, or release-tuple member and record the
   existing Web/BP/Conversation-adapter/evidence workload mapping.
8. Validate the closed-world environment manifest, secret catalog, capability-state records,
   release/configuration/catalog digest binding, and protected-value exclusion.
9. Qualify liveness/startup/traffic/feature readiness separately; freeze and load-test the capacity
   envelope; prove bounded queues, typed overload, durable retry, quarantine, and recovery.
10. Exercise required SLI telemetry, alert routes/runbooks, migration at zero traffic, previous-tuple
    rollback, UAT isolated restore/non-resurrection, and default-off activation expiry.

**Completion**

- All 26 fitness oracles pass.
- One logical command and conclusion survives every race/replay fixture.
- Manifest comparison is identical.
- No protected value is present in scans.
- Rollback rehearsal preserves owner truth and recovery/Stop/data-rights access.
- Platform qualification proves no topology expansion, immutable promotion, fail-closed
  configuration, bounded overload, alert/runbook operation, migration/rollback ordering, and
  recovery integration.

### 6.9 CEW-WC-09 - Live Demo Provider and Deployment

**Depends on:** 08 and every Section 2.3 gate.

**Status:** **BLOCKED**.

**Outcome after authorization:** deploy the accepted exact image, configure the authorized
WhatsApp business sender and Demo recipient through protected references, and demonstrate the
complete live customer journey.

**Tasks after all gates close**

1. Resolve protected sender/recipient references only in the authorized secret store.
2. Configure the authorized provider account, webhook, signature secret, templates, callback, and
   bounded recipient allowlist.
3. Deploy the exact CEW-WC-08 image digest through the authorized pipeline.
4. Verify health, callback challenge/signature, outbound template, inbound reply, handoff,
   end-session, Stop, redaction, alerts, and rollback.
5. Run the Founder-approved live Trial/Hire lifecycle scenario.
6. Capture redacted evidence containing opaque identifiers and digests, never full phone identity.
7. Start `READY_INACTIVE`; record separate deployment, bounded-traffic, and activation decisions;
   verify automatic/manual deactivation at the approved expiry.
8. Prove capacity/backpressure, SLO/alert routing, provider-versus-owner truth separation, and
   post-rollback reconciliation during the approved window.

**Completion**

- Provider feasibility is evidenced, not assumed.
- Deployed digest equals qualified digest.
- Live Portal and WhatsApp journeys share one relationship/conversation/command/evidence history.
- Incident and rollback rehearsal pass.
- Activation remains off unless separately authorized.

## 7. Exact API Outcomes

| Operation | Required behavior |
|---|---|
| `POST /api/v1/employment/relationships` | Atomic admit/replay; exact disclosure and Trial/Hire; one `DISCOVERED` relationship, agent, conversation, workspace, focus, evidence |
| `GET/PUT /api/v1/identity/settings/workspace-layout` | Optimistic account preference; no authority effect |
| `GET/PUT .../workspace/preferences` | Per-relationship presentation default; lifecycle truth wins |
| `GET .../workspace/engagement-progress` | Evidence-aware owner composition; explicit unknown/unavailable; server-ranked action |
| `POST .../workspace/focus-resolutions` | Body-only token; integrity/type/expiry/binding/assurance/Stop/current-authority recheck and required single-use consumption |
| `POST .../channel-sessions/{channelSessionId}/end` | Idempotently end one session only; relationship remains active |

All operations use stable schema versions, correlation, explicit limits, deterministic errors, and
redacted telemetry. All mutation operations use idempotency and optimistic concurrency where state
can race. Every authenticated response is `Cache-Control: no-store`. Authorization precedes
existence, assurance, validation, conflict, expiry, and version detail: inaccessible and absent
resources share the normalized `404` family, while `403` and other detailed denials are returned only
after the caller is authorized to know the resource and denial class.

## 8. Data and Migration Contract

The controlling data architecture is CSA-CEW-001 Sections 10.5-10.12 and the accepted
`relationship-workspace-data-contract.md` and AE-01 relationship/data contracts. Implementation
must preserve their conceptual ownership without treating their illustrative physical structures as
authority to invent a competing store.

1. Persist only through the existing Identity settings, relationship Onboard, BP admission/
   idempotency, relationship workspace, Conversation Core, owner, and CE evidence boundaries.
   Impact analysis identifies each affected owner and existing persistence/migration surface.
2. Every mutable BP record is tenant scoped from trusted server context and protected by forced RLS
   for `USING` and `WITH CHECK`. Relationship/participant bindings participate in composite
   references, uniqueness, reads, writes, maintenance, reconciliation, and backup/restore checks.
   Paths, bodies, focus claims, and provider payloads never establish tenant authority.
3. Admission reserves the scoped idempotency key and canonical digest before side effects. The local
   mint/coordinator/outbox commit is transactional; cross-owner work is a recoverable saga with
   stable owner idempotency identities, durable receipts, and no success until all owner outcomes
   plus committed evidence are durable.
4. Every mutation persists canonical request digest, monotonic operation state, correlation,
   replayable result, and divergence conflict. Operational-key expiry never defeats canonical owner
   uniqueness. Crash-boundary and concurrent replay tests prove one logical effect.
5. Progress metadata carries the exact source-version vector and projection-contract version.
   Items expose source owner/subject/version/contract, produced/observed/confirmation/validity
   times, freshness, and evidence state/reference. Owner change, correction, revocation, Stop,
   validity expiry, erasure, or unsupported contract invalidates the cache; stale composition may
   not drive a consequential next action.
6. Focus references have a maximum 15-minute lifetime, are non-extendable, contain no protected
   payload, and are invalidated by membership, authority, Stop, source-version, correction,
   termination, or data-lifecycle changes. Only keyed fingerprints and bounded revocation metadata
   may persist; key-rotation overlap cannot exceed token lifetime.
7. Impact analysis records, for every preference, coordinator/idempotency record, projection/cache,
   focus lifecycle record, transcript, owner fact, and evidence reference: retention owner,
   duration, correction, export, erasure, hold override, purge process, and purge evidence. Missing
   policy blocks the owning component; implementers do not invent it.
8. Migration follows expand/backfill/verify/cutover/contract. Backfill is tenant-bounded,
   idempotent, restartable, observable, and quarantines invalid records. Any dual-read/write has one
   authority and divergence alarms. Destructive contract waits for old readers and rollback windows
   to retire under separate authorization.
9. Mixed-version tests prove old readers do not misread new states, unsupported future contracts
   become `UNAVAILABLE`, and rollback retains read/replay/reconcile/Stop/data-right operations.
10. Backup and point-in-time restore include BP coordinator/outbox state and separately protected
    immutable evidence while preserving encryption and tenant isolation. Projection caches may be
    rebuilt. Restore must not resurrect erased payload, expired focus authority, revoked bindings,
    or superseded truth.
11. A tenant-scoped, lease-safe reconciler resumes non-terminal work with original idempotency
    identities and detects orphan effects, missing outbox delivery, source-vector drift, purge
    failures, and evidence gaps. It quarantines irreconcilable state; it never manufactures success
    or evidence.
12. Rollback never deletes accepted owner writes or immutable evidence. A failed migration or
    failed restore blocks writes/activation and preserves the prior readable experience.
13. Component 08 must retain redacted evidence for atomicity/crash boundaries, divergent replay,
    reconciliation, invalidation/rebuild, RLS denial, retention/erasure/hold/purge,
    mixed-version migration/rollback, backup/restore, and accepted RPO/RTO rehearsal.

## 9. Security and Privacy Acceptance

The exact candidate must test:

1. cross-tenant, cross-participant, cross-relationship, stale membership, revoked link, and object
   enumeration denial;
2. open redirect, focus-token tamper/expiry/replay, idempotency mismatch, stale version, duplicate
   webhook, forged signature, oversized payload, unsupported media, and abuse/rate-limit behavior;
3. credential/token/secret/full-phone seeded redaction across transcript, URL, browser persistence,
   logs, traces, metrics, evidence, screenshots, and error detail;
4. distinct logout, end-session, switch, unlink, terminate, delete, and Stop effects; and
5. data-right export/correction/erasure/retention/legal-hold compatibility.

Any credential, token, protected payload, or full telephone identity found in a prohibited surface
is a release-blocking failure.

### 9.1 Mandatory security control matrix

Implementation impact analysis must produce a reviewable matrix, without secret values, that maps
each Portal, BP, Identity, WhatsApp callback, adapter, owner call, background job, data store,
telemetry sink, export and recovery path to:

1. validated customer proof and current actor-keyed membership derivation;
2. current tenant/relationship/participant/effective-role/object/purpose/version authorization and
   privacy-indistinguishable denial;
3. required assurance, mobile proof and typed acknowledgement, including Emergency Stop's
   independent fail-safe path and separately governed release;
4. cookie/session/CSRF and safe-return controls, or evidence that the path is non-browser and has no
   ambient cookie authority;
5. idempotency namespace/digest/retention, focus token type/lifetime/consumption/revocation, and
   rate/abuse limits;
6. exact WhatsApp raw-byte signature, freshness/deduplication, payload/media validation and
   quarantine controls where applicable;
7. allowlisted workload identity, audience, operation/purpose and delegated customer context;
8. secret/key owner and purpose separation, encryption in transit/at rest, rotation/revocation and
   fail-closed behavior;
9. telemetry allowlist, redaction point, cardinality bound, retention/access owner and seeded-canary
   evidence; and
10. rollback/recovery proof that revoked authority, secrets, sessions, links, tokens and bindings
    cannot return.

An absent owner, accepted policy, proof or enforceable test is `BLOCKED`, not an implementation
default.

### 9.2 Direct adversarial security qualification

Repository-owned deterministic tests must include:

1. forged/expired/wrong-issuer, algorithm or audience customer proofs; JWT tenant/role substitution;
   stale membership/role/link; actor, tenant, relationship, participant, object, session, purpose
   and version swapping; list/count/timing enumeration; and operator/service confused deputy;
2. CSRF absent/mismatch, hostile Origin/Fetch-Metadata, login CSRF, session fixation, stale
   assurance, account/tenant switch, logout/revocation, absolute/scheme-relative/encoded-host return
   attacks, safe-return replay/expiry, and proof that step-up never auto-executes a mutation;
3. focus raw-token absence from every URL/telemetry/evidence surface; entropy/type/key/tamper,
   actor/tenant/relationship/channel/subject/authority binding, expiry, single-use continuation,
   logout/switch/unlink/revocation/Stop/termination/deletion/correction invalidation, key rotation,
   concurrent replay, and no owner mutation on denial;
4. admission high-cardinality and divergent-key floods, same-key races, abandoned/in-flight
   quotas, limiter/cache/process/clock failure, timeout/unknown reconciliation, committed-key
   retention and proof that limiting cannot permit a second first mint;
5. WhatsApp missing/wrong signature, exact-raw-byte mutation and reserialization, stale/future
   accepted freshness proof beyond the five-minute window, duplicate event/message, account/phone substitution, oversized or
   unsupported encoding/type, decompression expansion, unknown sender and acknowledgement/dispatch
   races;
6. media extension/MIME/magic mismatch, active content, traversal filename/metadata, redirect and
   retrieval-network abuse, malware/safety/consent failure, quarantine isolation, size/count/timeout
   and unsupported-media denial;
7. unauthenticated/wrong-workload, wrong audience/operation/purpose, customer-context substitution,
   shared credential, callback/reconciler/migration/restore/export privilege crossover and original
   customer-proof failure;
8. unavailable/old/revoked/incorrect-purpose secret or key, rotation overlap boundary, encrypted
   store/backup/export inspection, restore under rotated keys, and fail-closed key dependency;
9. seeded credentials, cookies, authorization/CSRF headers, signatures, tokens, idempotency keys,
   safe returns, full phone/email, message/media, filename, URL/query and owner payload across
   request logs, errors, traces, metrics, analytics, transcript, evidence, export and screenshots;
10. Stop racing every admission/command/focus/handoff/end-session/provider delivery/reconciler path,
    Stop during dependency/limiter/session outage, restart persistence, ordinary-flow release
    denial, and exact distinct effects for logout, web-session revoke, end-session, switch, unlink,
    terminate, delete, Stop and Stop release; and
11. rollback/restore after every revocation and security-key transition, proving no authority,
    ingress, traffic, effect, credential or protected payload is resurrected.

Emergency Stop is excluded from ordinary rate limits. The Stop test harness may apply only controls
allowed by the accepted fail-safe Stop contract and must prove cessation is not delayed.

## 10. Docker-Only Validation Plan

Language, schema, generated-client, unit, integration, and browser tooling must run through
repository Docker runners. Host Python/Node results are non-authoritative.

### 10.1 Contract and BP selectors

```bash
docker compose --profile test-python run --rm test-runner-python pytest -q \
  tests/test_openapi_slice.py \
  tests/validation_control/test_spec_lint_scope.py \
  tests/business-platform/test_customer_engagement_admission.py \
  tests/business-platform/test_customer_engagement_preferences.py \
  tests/business-platform/test_customer_engagement_progress.py \
  tests/business-platform/test_customer_engagement_focus.py \
  tests/business-platform/test_customer_engagement_channel_session.py
```

### 10.2 Integration, security, privacy, and environment selectors

```bash
docker compose --profile test-python run --rm test-runner-python pytest -q \
  tests/integration/test_customer_engagement_workspace.py \
  tests/integration/test_customer_engagement_cross_channel.py \
  tests/security/test_customer_engagement_workspace_security.py \
  tests/privacy/test_customer_engagement_workspace_redaction.py \
  tests/environment/test_customer_engagement_same_image.py
```

### 10.3 Portal unit/component selector

```bash
docker compose --profile test-ts run --rm test-runner-ts \
  pnpm --dir web test -- --runInBand customer-engagement-workspace
```

### 10.4 Portal journey and accessibility selector

```bash
docker compose --profile test-ts run --rm test-runner-ts \
  pnpm --dir web exec playwright test \
  tests/e2e/customer-engagement-workspace.spec.ts \
  tests/e2e/customer-engagement-accessibility.spec.ts \
  tests/e2e/customer-engagement-cross-channel.spec.ts
```

### 10.5 Exact-image qualification

The implementation plan must bind repository-native image build and environment-shaped test
commands after impact analysis. Completion evidence must record:

1. one immutable image digest;
2. Demo-, UAT-, and Production-shaped configuration identifiers;
3. route/component/command/schema/lifecycle manifest digests;
4. default-off and enabled results; and
5. the exact CEW-FIT evidence location.

If any named test path does not yet exist, creating it is part of the owning component. Replacing an
oracle with a proxy requires Chief Solution Architect and Founder acceptance.

## 11. Canonical Requirement Index

| Requirement | Observable implementation obligation |
|---|---|
| WC121-R001 | Implementation starts only after exact package acceptance, Docker validation, impact analysis, pinned digests, and explicit current-session implementation authority. |
| WC121-R002 | Canonical BP incorporates the accepted additive contract and generated clients without a second facade, schema fork, or incompatible supported-client change. |
| WC121-R003 | Admission validates exact disclosure/admission/version and Trial/Hire intent and atomically creates or replays one `DISCOVERED` relationship, agent instance, conversation, workspace, focus, and evidence outcome. |
| WC121-R004 | Account layout and relationship workspace preferences use their accepted owners, optimistic concurrency, privacy policy, and have zero business-authority effect. |
| WC121-R005 | BP composes evidence-aware adaptive progress and reauthorizes opaque typed focus references; clients do not join owners, rank action, infer success, or mutate by navigation. |
| WC121-R006 | Portal provides expanded and compact conversation-first compositions with accessible hide/show/resize/restore and persistent Stop, lifecycle, identity, required-action, and recovery access. |
| WC121-R007 | Anonymous discovery, registration, login, stale-session recovery, and account switch preserve safe context without creating duplicate identity/employment state or leaking secrets into conversation. |
| WC121-R008 | Trial and Hire remain explicit, evidenced, idempotent, commercially distinct conversational journeys with consequential-action disclosure and reconciliation. |
| WC121-R009 | Induction, skills, goals, plans, schedules, budgets, and Decision Space are conversationally authored, visually verifiable, owner-versioned, conflict-aware, and never silently committed by a form. |
| WC121-R010 | Operations and performance separate delivery, processing, evidence, commercial, and outcome truth and lead with customer business outcomes. |
| WC121-R011 | WhatsApp presents the same lifecycle, professional identity, terminology, state meaning, evidence, commands, and next actions through the approved adapter and shared BP semantics. |
| WC121-R012 | Web logout, WhatsApp end-session, account switch, unlink, relationship termination, account deletion, and Stop invoke distinct owners and cannot trigger one another. |
| WC121-R013 | Emergency Stop remains independently reachable and cross-channel effective in every supported composition and lifecycle state. |
| WC121-R014 | Tenant/object authorization, assurance, idempotency, webhook verification, replay, limits, redaction, data rights, and protected-value exclusion pass direct security/privacy tests. |
| WC121-R015 | The complete experience passes WCAG 2.2 AA, keyboard, screen-reader, 200% zoom, 360px reflow, RTL, reduced motion, customer-language, one-action, and performance controls. |
| WC121-R016 | One immutable image provides identical routes, components, commands, schemas, and lifecycle behavior across Demo-, UAT-, and Production-shaped configuration; gates evaluate authority, not environment name. |
| WC121-R017 | Cross-channel change, race, retry, timeout, replay, and rollback preserve one canonical relationship, conversation, command effect, evidence conclusion, and recoverable owner truth. |
| WC121-R018 | Live provider configuration and Demo deployment remain blocked until same-number feasibility and every provider/cloud/deployment/traffic/activation gate are separately evidenced; protected identities remain runtime references only. |
| WC121-R019 | Persistence ownership, atomic saga/idempotency, projection provenance/invalidation, focus lifecycle, tenant/RLS, data lifecycle, mixed-version migration, recovery, reconciliation, and evidence satisfy Sections 8 and CSA-CEW-001 10.5-10.12. |
| WC121-R020 | The candidate-specific threat model and authentication, authorization/isolation, focus/safe-return/session/CSRF, idempotency-abuse, WhatsApp raw-byte/replay/media, workload, secret/encryption, telemetry, Stop-precedence, operation-separation, revocation, and rollback controls satisfy Section 9 and CSA-CEW-001 Section 11. |
| WC121-R021 | Existing-workload topology, closed-world configuration/secret/capability gates, health/readiness, SLO/alerts, capacity/backpressure, immutable promotion, migration/deployment/rollback, DR integration, activation, and live-provider evidence satisfy CSA-CEW-001 Sections 13.5-13.12. |

## 12. Requirement-to-Component Trace

| Component | Enterprise requirements |
|---|---|
| 01 | CEW-ER-001, 002, 027-029, 038, 043, 045; WC121-R019 persistence baseline |
| 02 | CEW-ER-003-009, 019, 022-024, 030-031, 035-036, 042 |
| 03 | CEW-ER-012-014, 037-041 |
| 04 | CEW-ER-013-019, 029, 036, 038-039, 045 |
| 05 | CEW-ER-015-016, 019, 025-026, 029 |
| 06 | CEW-ER-017-020, 023-026, 029, 036, 045 |
| 07 | CEW-ER-001-002, 010-012, 020, 027-031, 035, 041, 043-044 |
| 08 | CEW-ER-001-046; CEW-FIT-01-26; WC121-R019 recovery qualification; WC121-R021 platform qualification |
| 09 | CEW-ER-010-012, 020, 031-034, 046 after protected gates; WC121-R021 live platform evidence |

Every CEW-ER is owned by at least one component and is requalified integrally by Component 08.

## 13. Milestones and Evidence

Each component is one milestone:

1. commit only component-owned changes using the repository conventional format;
2. record exact changed paths, test commands/results, image/schema digests where applicable, known
   residual risk, and rollback;
3. update the required project checkpoint after the milestone commit;
4. do not start a dependent component while its prerequisite is failing or blocked; and
5. do not represent planned or emulator evidence as live acceptance.

Evidence root is `test-results/wc121/<component-or-fitness-id>/` or the repository-standard
equivalent selected by impact analysis. Evidence artifacts must be redacted and must not be
committed when repository policy treats them as ephemeral.

## 14. Rollback and Stop Conditions

### 14.1 Rollback

1. Revert presentation routing/configuration to the last accepted image.
2. Preserve backward-compatible API and prior generated clients during mixed-version rollback.
3. Disable new entry through owner-controlled configuration, not environment branching.
4. Keep read/reconcile/Stop/data-right operations available.
5. Reconcile uncertain admission, command, payment, evidence, and provider outcomes by canonical
   idempotency/correlation identity.
6. Never delete or claim reversal of committed owner/evidence/provider effects without that owner's
   accepted compensating operation.

### 14.2 Mandatory Stop

Stop the applicable component when:

1. an owner or source conflict is unresolved;
2. a required source digest differs from the accepted candidate;
3. implementation requires a prohibited root or a new deployable/store/facade;
4. canonical API compatibility cannot be preserved;
5. an oracle can only pass through client inference or success-shaped fallback;
6. protected data appears in a prohibited surface;
7. exact-image parity fails;
8. provider feasibility or any protected-action authority is absent; or
9. rollback cannot preserve owner truth, Stop, reconciliation, and data rights;
10. any identity, assurance, authorization, privacy-safe denial, CSRF/session/safe-return, webhook,
    abuse/media, workload, key/secret/encryption, telemetry, Stop/release, revocation, or rollback
    owner/control is absent, incompatible, or unproven; or
11. focus/safe-return/credential/signature/session/idempotency material reaches a URL or prohibited
    observability/evidence surface, raw-byte callback verification is not exact, Stop can lose a
    race, or rollback/restore can resurrect revoked authority; or
12. topology would add a deployable/ingress/store/queue, release/configuration/catalog digests do
    not bind, health/readiness performs effects, the capacity envelope or bounded backpressure is
    absent, SLO/alert/runbook ownership is unresolved, immutable promotion or migration ordering
    fails, rollback/DR cannot meet accepted objectives, or traffic/activation authority is absent.

## 15. Definition of Done

WC-121 is implementation-complete only when:

1. Components 01-08 pass their direct Docker-owned oracles on one exact candidate;
2. all `CEW-ER-001` through `CEW-ER-046` trace to implemented owner behavior;
3. all `CEW-FIT-01` through `CEW-FIT-26` pass with retained redacted evidence;
4. `WC121-R001` through `WC121-R017` and `WC121-R019` through `WC121-R021` pass their ledger completion rules;
5. Portal and WhatsApp demonstrate equivalent lifecycle outcomes with one canonical relationship
   and conversation;
6. security, privacy, accessibility, performance, operability, migration, recovery, and rollback
   gates pass;
7. same-image manifest and digest evidence passes across three environment-shaped configurations;
8. author review finds no critical or material bridge gap;
9. the PR uses the repository template and passes the repository precheck;
10. the Founder receives the completed PR for review and merge; and
11. no implementer claims `WC121-R018` or Component 09 complete while its provider/deployment gates
    remain blocked.

WC-121 may be completed for repository implementation with Component 09 explicitly `BLOCKED` if
the Founder accepts that bounded disposition. Live Demo acceptance remains incomplete until
Component 09 passes under separate authority.

## 16. Explicit Non-Authorization

Nothing in WC-121 authorizes:

1. source implementation before explicit current-session permission;
2. live Meta account or phone-number changes;
3. Azure or other cloud mutation;
4. deployment to Demo, UAT, or Production;
5. outbound or inbound external traffic;
6. capability activation;
7. PR approval; or
8. merge.

The Platform IT Expert must request and receive each applicable authority at the point of action.
