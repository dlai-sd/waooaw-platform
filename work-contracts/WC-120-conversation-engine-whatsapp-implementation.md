# WC-120 - Channel-Neutral Conversation And WhatsApp Implementation

## Record Control

| Field | Value |
|---|---|
| Work Contract ID | WC-120 |
| Authoring office | Chief Solution Architect (INST-005) |
| Assigned implementation office | Platform IT Expert (INST-010), only after the gates in this contract pass |
| Status | WORK CONTRACT RECORDED FOR FOUNDER REVIEW - ADR-051/052/053 FOUNDER-ACCEPTED; ADDITIVE SCOPE; IMPLEMENTATION GATES ACTIVE |
| Current-main baseline | `c2a1baf64cb3b2652ce29ed930ac4a60f14e73bb` |
| Source PR | PR #499, merged as `c2a1baf64cb3b2652ce29ed930ac4a60f14e73bb` |
| Candidate solution package | `architecture/reference/components/conversation-engine-whatsapp-solution-work-component.md`, version `1.0.0-candidate.1`, as delivered by PR #499 |
| Solution package Git blob | `224d8f43f2a46e810eb5b13aac35570b6f0ebcda` |
| Candidate channel-neutral API | `architecture/reference/api-specs/channel-neutral-conversation-business-platform.openapi.yaml`, as delivered by PR #499 |
| Candidate API Git blob | `77b7875a0d294be3aba21534bf33cd92c7527e15` |
| Controlling enterprise input | PR #498 reviewed head `65add4540698116b00be1ec72e6000333d05eac9`, merged as `4a4420af6ee132623d6b87eb3863d700e56c9b86` |
| Existing Conversation Core | `architecture/reference/components/conversation-core.md`, blob `1004255bbd01e3d10dd53a64a2b115ac059ad631` |
| Existing WC-114 / WC-115 | `work-contracts/WC-114-conversational-employment-solution-contract.md` blob `11ba639efa43d3288ba1eb39fd2e05308c42e6c0`; `work-contracts/WC-115-conversational-employment-implementation.md` blob `337fcef0a51a4c2ef2ff72423a7afc64969d8914` |
| Existing BP and employment APIs | `architecture/reference/api-specs/business-platform.openapi.yaml` blob `406153fec469a5bf6b5919000110a6af1dfa6a46`; `architecture/reference/api-specs/conversational-employment-business-platform.openapi.yaml` blob `bf7d3466c4113049f9f61200583811a25e454951` |
| Accepted specialist profile | `architecture/reference/api-specs/conversational-employment-specialist-profiles.yaml`, blob `9c7ccecd64791010f1ba15b69d9b8a128d466d66` |
| Prior single-pass reviews | R-146 Security blob `e7ba98253092b7283fc70422fcf5539aab006d5c`; R-147 Data blob `df8e78409c0cc7afc4177ab5f181971af46b3f2f` |
| Constitutional basis | C-039, C-059; CE-FIT-01 through CE-FIT-16; ADR-051, ADR-052, ADR-053 |

### Founder Authorization And Accepted Decisions

On 2026-10-12, the Founder explicitly directed that ADR-051, ADR-052, and ADR-053 are
approved and authorized, and directed that this decision be recorded in this Work Contract.
This is the acceptance evidence for this bounded scope. ADR-051 is accepted before ADR-052;
ADR-052's acceptance dependency is therefore satisfied. ADR-053 is accepted subject to the
accepted channel-neutral conversation and policy decisions in ADR-052.

This decision resolves the ADR-acceptance prerequisite recorded in CB-010. Any earlier
`Proposed - Founder review required` status captured in a prior snapshot is superseded for
this scope by the Founder decision recorded here. This records ADR acceptance only: it is
not approval of this Work Contract's implementation, current-session authority to write code,
or permission for provider, cloud, deployment, traffic, or activation actions.

The Founder separately authorized the authoring of this contract in the current conversation.
That authority is limited to recording and preparing the governed implementation package.

### Explicit Status Replacement

For the PR #499 solution package, this Work Contract replaces the former status
`DRAFT - IMPLEMENTATION HANDOFF BLOCKED` with:

> **FORMALLY RECORDED - ADR-051/052/053 FOUNDER-ACCEPTED; SPECIFICATION CLOSURE AND
> SEPARATE IMPLEMENTATION AUTHORIZATION REQUIRED**

This is the recorded status of the work component, not a claim that its source package was
rewritten or independently re-approved. ADR-051/052/053 acceptance supersedes the stale
"Proposed - Founder review required" labels in the PR #499 candidate for this governed scope.
WC-120 does not override source history or reviewer verdicts. Implementation remains gated:
the compatibility crosswalk, seven specification corrections, required specialist
contributions, Founder acceptance of this exact Work Contract, ledger validation, and
separate explicit current-session implementation authorization must all pass first.

## 1. Objective And Authority

WC-120 governs the additive WhatsApp transport and cross-channel continuity work described
by PR #499. It does not replace, fork, or create another Conversation Core, relationship
workspace, transcript, API owner, context/profile store, or employment protocol. Existing
BP Conversation Core and the Founder-accepted WC-114/WC-115 contracts remain authoritative
for their existing surfaces and behavior.

Source precedence is: Founder-authorized constitutional decisions and accepted ADRs; the
merged PR #498 enterprise architecture; the existing Conversation Core and WC-114/WC-115
contracts for already-owned behavior; then the PR #499 solution package and candidate API
only where they are compatible with those controlling inputs. WC-120 adds stricter
implementation gates and does not silently supersede any owner contract. A conflict,
duplicate operation, or missing compatibility mapping is a stop for Founder direction.
PR #499's 27 stories, candidate schemas, runbook, CE-FIT mapping, failure/recovery, and
rollback remain the intended delivery decomposition subject to this precedence and the
closure gates below; they are not authority to invent or replace a controlling surface.

The target is one reusable channel-neutral conversation capability and one environment-
isolated WhatsApp adapter. Business Platform remains the public facade and canonical
conversation owner; Professional Runtime owns execution and Emergency Stop; AI Runtime
owns bounded context assembly and provider-neutral reasoning; Constitutional Engine owns
authority decisions and evidence. Web, WhatsApp, and future Mobile use common conversation
semantics; channel state is delivery/session state only. No new deployable Conversation
Engine service is introduced.

Before the Platform IT Expert can return `READY_FOR_STRATEGIC_PLAN`, the Chief Solution
Architect must close the PR #499 specification findings, complete the existing-contract
crosswalk, and obtain the specialist contributions in §2.2. After this Work Contract is
Founder-accepted and separate current-session implementation authority is granted, the
Platform IT Expert may perform the impact analysis, plan, and dependency-ordered additive
implementation within the exact reconciled package. No implementation file, test, generated
artifact, migration, executable configuration, or build output may be written before that
explicit authorization.

### Exclusions

- No source-code, test-code, generated-code, migration, or build-artifact changes under
  the current contract-authoring authorization.
- No new deployable, parallel conversation history/profile, channel-owned authority, or
  client-supplied tenant, policy, or authorization.
- No Meta/provider login or mutation, number purchase, Azure or other cloud mutation,
  DNS change, deployment, external traffic, activation, or Production apply.
- No reuse or publication of complete telephone identities, credentials, tokens, keys,
  provider payloads, or customer content in repository files, fixtures, logs, evidence,
  or PR text.
- No change to the controlling enterprise architecture, unaccepted decision, owner
  boundary, or product policy; no new technology or provider choice without its required
  decision and authority.
- No PR approval, merge, or representation of Founder approval beyond the explicit
  decisions recorded in this contract.

## 2. Required Inputs And Preconditions

| Input | Required state |
|---|---|
| PR #498 enterprise package and exact reviewed head | Merged; use the pinned head and controlling artifacts named by the PR #499 solution package |
| PR #499 solution package and candidate API | Merged candidate; preserve its compatible decomposition, subject to the precedence, crosswalk, and specification-closure gates below |
| Existing Conversation Core and BP API | Reuse the pinned Core and public API; no parallel timeline, unread/read position, command, or transport authority |
| WC-114 and WC-115 | Merged contracts; preserve their existing BP facade, Conversation Core, relationship workspace, owner boundaries, accepted specialist profiles, default-off posture, and rollback rules |
| WC-114 employment API and specialist profile | Use the pinned BP OpenAPI and profile as compatibility inputs; do not weaken, copy inconsistently, or bypass their operation, assurance, data, AI, product, or Stop controls |
| R-146 and R-147 | Treat the pinned Security and Data reviews as one-pass input records; their original verdicts remain `CHANGES REQUIRED`, and PR #498 §27 records author repairs, not reviewer re-approval |
| ADR-051 - Conversational Employment Workspace and Employment Readiness Protocol | Founder-accepted in this contract on 2026-10-12 |
| ADR-052 - Channel-Neutral Conversation Context and Policy | Founder-accepted in this contract on 2026-10-12, after ADR-051 |
| ADR-053 - WhatsApp Environment Isolation and Transport Boundary | Founder-accepted in this contract on 2026-10-12 |
| Existing ADR-023 phone identity and ADR-031 Emergency Stop assumptions | Verify current accepted owner contracts and exact behavior during CSA-CEWA-001; any mismatch is a stop, not permission to redesign |
| PR #499 open review threads | All seven findings below must be closed by corrected specification and direct validation before implementation may start |
| This exact WC-120 revision | Founder acceptance required before implementation planning or execution |
| Requirement/evidence ledger | `work-contracts/WC-120-requirements.yaml` maps each canonical WC120-RNNN obligation below; its digest must match this exact contract revision and pass `scripts/validate_requirement_ledger.py` in the repository Docker test runner before implementation planning or execution |
| Current-session implementation authority | Explicit Founder confirmation required before any runnable or implementation artifact is written |
| Environment/provider authority | Separate, exact authority required for each provider, cloud, DNS, deployment, traffic, activation, and Production action; none is granted here |

### 2.1 Specification Closure Gate

At the time WC-120 was prepared, the following PR #499 review threads were unresolved.
They are binding correction and test requirements for the contract/API package, not optional
suggestions:

| Review thread | Required closure |
|---|---|
| [R-4248036961](https://github.com/dlai-sd/waooaw-platform/pull/499#discussion_r4248036961) | Declare the WhatsApp webhook wire media type as `application/json`; preserve exact raw bytes for signature verification before deserialization. |
| [R-4248037029](https://github.com/dlai-sd/waooaw-platform/pull/499#discussion_r4248037029) | Replace committed Demo/UAT telephone inputs with repository-safe suffix-only labels; ensure complete values are absent from current files and evidence. Any repository-history remediation must use an explicitly approved cleanup plan and must not silently rewrite shared history. |
| [R-4248037076](https://github.com/dlai-sd/waooaw-platform/pull/499#discussion_r4248037076) | Add the durable conversation read-position operation or a compatible successor; an event-stream cursor is not a substitute. |
| [R-4248037125](https://github.com/dlai-sd/waooaw-platform/pull/499#discussion_r4248037125) | Make registered command descriptors discoverable from interaction context or a typed command-catalog operation. |
| [R-4248037174](https://github.com/dlai-sd/waooaw-platform/pull/499#discussion_r4248037174) | Add an idempotent handoff-revert operation and request semantics that preserve the source binding. |
| [R-4248037216](https://github.com/dlai-sd/waooaw-platform/pull/499#discussion_r4248037216) | Constrain contribution variants so exactly one correctly typed, non-null payload is accepted for each discriminator. |
| [R-4248037259](https://github.com/dlai-sd/waooaw-platform/pull/499#discussion_r4248037259) | Replace free-form command parameters and command type with a closed, typed union of registered command schemas. |

The Chief Solution Architect records the corrected package revision and evidence that each
thread's observable predicate is covered. The implementing office must not infer or invent
these contracts in code. If any correction conflicts with the accepted enterprise package,
stop and return the conflict to the Founder rather than choosing an interpretation.

### 2.2 Existing-Contract Crosswalk And Specialist Review Gate

Before `CSA-CEWA-001` may return `READY_FOR_STRATEGIC_PLAN`, its evidence must map every
PR #499 candidate operation and schema to the existing BP Conversation Core and WC-114/WC-115
contracts, including canonical messages/order, durable read position, command discovery,
employment commands, channel binding/revert, identity/assurance, Stop, and generated-client
ownership. The crosswalk must identify reuse, compatible additive operations, and removed or
replaced candidate operations. A duplicate owner or incompatible wire contract is a stop;
the Platform IT Expert must not choose a successor or perform migration by inference.

This Work Contract requests one-pass, write-access review and bounded owner contribution from
the required offices listed in [WC-120 specialist review requests](../reviews/WC-120-specialist-review-requests.md):
Data Architect, Security Architect, Platform Architect, AI Architect, Product Owner, and Test
Champion. Each office must return a scoped disposition with exact finding IDs and contract
locations, or explicitly record no findings. The Chief Solution Architect repairs accepted
findings and updates the traceability ledger. A second review pass is not implied; material
owner-boundary changes or unresolved conflicts stop for Founder direction.

R-146 and R-147 were the one-pass Security and Data reviews of the PR #498 enterprise
architecture, not reviews of WC-120 or approval of downstream specialist contributions.
Their Section 27 author-remediation mapping is retained as input. Neither the historical
review verdict nor the existence of the remediation table is represented as post-repair
reviewer approval.

## 3. Permitted Surfaces And Delivery Components

### 3.1 Owner And Surface Boundaries

The Platform IT Expert may select only existing canonical surfaces directly owned by these
components, and must record the exact paths and consumers during CSA-CEWA-001:

| Owner | Bounded responsibility | Surface constraint |
|---|---|---|
| Business Platform (BP) | Public conversation facade, canonical conversation/message state, interaction context, policy projection, WhatsApp adapter boundary, delivery projection | Reuse the existing BP owners and contracts; no new Conversation Engine deployable or parallel history/profile |
| Professional Runtime (PR) | Professional execution, ordering, cancellation, reconciliation, and Emergency Stop behavior | Extend the existing runtime owner only; no channel-owned execution or reasoning |
| AI Runtime (AIR) | Bounded context assembly, research, analysis, provider-neutral reasoning | Consume server-resolved context and accepted references; no client prompt/policy authority or provider selection |
| Constitutional Engine (CE) | Authority validation, constitutional decisions, evidence | Preserve existing CE interfaces and fail-safe behavior |
| Phone Identity / WhatsApp adapter | Signed provider identity resolution and channel transport at the BP boundary | Preserve ADR-023 ownership; no tenant supplied by client and no shared environment identity |
| Web and future Mobile | Generated-client-backed presentation and shared API adoption | No direct PR/AIR calls, authority, or channel-specific conversation semantics |
| Data and persistence owners | Canonical persistence, ordering, outbox/inbox, migrations, RLS, retention, backup and restore | Existing owner and storage only; no new product or cross-owner writes |
| Deployment and operations | Environment configuration, secrets, telemetry, runbooks, recovery | Existing protected configuration only; provider/cloud changes require separate authority |
| Tests and evidence | Owner-local unit, contract, integration, security, migration, journey and qualification evidence | Repository-native paths discovered by impact analysis; do not invent a parallel test/evidence surface |

If an exact owner/path is absent, conflicts with a controlling contract, or would create a new
deployable or persistence owner, stop. Do not substitute a plausible path.

### 3.2 Delivery Components

| Component | Source stories | Required output and exit evidence |
|---|---|---|
| WC120-00 - Baseline, Authority, And Impact | CSA-CEWA-001 | Exact source and ADR digests, existing-owner/path inventory, compatibility and risk analysis, and a signed `READY_FOR_STRATEGIC_PLAN` or `BLOCKED` result |
| WC120-01 - Shared Conversation Foundation | CSA-CEWA-002 through CSA-CEWA-008 | Frozen shared API, canonical history/order/outbox, server-resolved context and policy, observation lineage, cross-channel binding, deterministic identity and assurance; contract and denial tests pass |
| WC120-02 - WhatsApp Ingress And Delivery | CSA-CEWA-009 through CSA-CEWA-014 | Signed ingress, atomic claim/dedup/replay, normalized inbound, idempotent outbound, consent/window/template eligibility, independent delivery dimensions; provider-emulator and replay tests pass |
| WC120-03 - Media, Stop, And Operations Signals | CSA-CEWA-015 through CSA-CEWA-017 | Quarantine/scan/retention/erasure, Emergency Stop, dead-letter/alert/telemetry boundaries; hostile privacy and stop/recovery tests pass |
| WC120-04 - Environment Readiness | CSA-CEWA-018 through CSA-CEWA-020 | Demo provisioning/teardown, UAT stable-ingress readiness, and Production-dark evidence; each environment remains separately authorized and isolated |
| WC120-05 - Client Adoption And Data Recovery | CSA-CEWA-021 through CSA-CEWA-023 | Web compatibility, future Mobile contract, expand/migrate/contract, backup, restore, rollback, and invariant evidence |
| WC120-06 - Qualification And Founder Handoff | CSA-CEWA-024 through CSA-CEWA-027 | Bidirectional CE-FIT qualification, exact-candidate Docker validation, rehearsed runbooks, author review, residual-risk package, and Founder authorization gate |

The source package's per-story inputs, affected-owner analysis, migration/compatibility,
failure/retry/idempotency behavior, rollout/rollback, targeted tests, acceptance criteria,
evidence, and dependencies remain normative for every story. The delivery groupings above do
not replace those story-level contracts.

## 4. Definition Of Done

WC-120 is complete only when all of the following are evidenced:

1. The controlling inputs are reconciled by the source precedence in §1; the PR #499 package
   and API are versioned only where compatible with the exact PR #498 head, existing Core,
   WC-114/WC-115, and Founder-accepted ADR-051/052/053.
2. Every normative obligation, compatibility crosswalk item, specialist contribution, and
   specification-closure finding has a stable WC120-RNNN requirement, owner, dependency,
   acceptance oracle, targeted test, evidence location, and failure/rollback behavior in
   the validated ledger.
3. The Platform IT Expert's impact analysis is `READY_FOR_STRATEGIC_PLAN`; it traces current
   behavior and exact owning paths without changing implementation.
4. The implementation plan freezes shared contracts before consumers, preserves the
   story dependencies below, defines compatibility windows and feature gates, and assigns
   the smallest repository-native tests to every story.
5. All 27 stories meet their source-package acceptance criteria. The
   `WC-120-fitness-evidence-matrix.yaml` contains CE-FIT-01 through CE-FIT-16, each mapped
   bidirectionally to stories, direct positive/boundary oracles, exact Test Champion-selected
   repository test selectors, candidate identity, and evidence location.
6. API/OpenAPI validation proves the specified 14 paths and schemas, resolves every local
   reference, and covers every correction in the Specification Closure Gate.
7. Data evolution follows expand -> migrate -> contract; migration, backup, restore, and
   rollback evidence passes before any destructive contraction or environment promotion.
   Recovery evidence records environment, injected fault, commands, watermark, accepted
   RPO/RTO and data-loss bounds, invariant/checksum oracle, and provider-egress denial.
8. Every story's targeted unit, contract, integration, static, security/privacy, migration,
   and compatibility checks pass before final Docker qualification.
9. Final Docker, image, and containerized end-to-end qualification runs once on the complete
   exact candidate after all targeted tests and implementation author review pass. An
   immutable `test-results/wc120/candidate-manifest.json` binds source commit, image digest,
   API/solution digests, schema and migration watermark, configuration/feature-flag versions,
   targeted tests, recovery, CE-FIT results, and final qualification. Any relevant change
   invalidates affected evidence and reruns impacted targeted tests plus final qualification.
10. The operational runbook is complete and rehearsed in an authorized non-production
    environment; environment isolation, teardown, recovery, privacy-safe telemetry, and
    Emergency Stop evidence pass.
11. The implementation author review records PASS against the exact 40-character candidate
    commit, with all findings resolved or the contract marked BLOCKED.
12. Founder handoff contains the candidate identity, verified evidence, open risks, rollback
    and recovery instructions, remaining authority decisions, and exact decisions requested.
    No deployment, provider action, traffic, activation, Production change, approval, or merge
    is inferred from completion.
13. The one-pass Data, Security, Platform, AI, Product, and Test Champion review requests
    have scoped dispositions, and the Chief Solution Architect's repairs are recorded without
    misrepresenting any office decision.
14. The Product Owner accepts the customer-state and accessibility matrix for each
    implementation-enabled journey. Unsupported locales/media, unresolved consent/template
    policy, or missing approved customer copy remain explicit stops.
13. The one-pass Data, Security, Platform, AI, Product, and Test Champion review requests
    have scoped dispositions, and the Chief Solution Architect's repairs are recorded without
    misrepresenting any office decision.

## 5. Ordered Stories And Dependencies

Story identifiers and acceptance detail are retained from Section 17 of the PR #499 solution
package. The dependency order below is normative; parallel work never permits a consumer to
code against an unstable contract.

| Story | Name | Depends on |
|---|---|---|
| CSA-CEWA-001 | Existing-State Discovery And Impact Analysis | ADR/authority gate; controls all implementation |
| CSA-CEWA-002 | Shared Channel-Neutral Conversation Contract | 001 |
| CSA-CEWA-003 | Canonical History, Sequencing, And Transactional Outbox | 002 |
| CSA-CEWA-004 | Interaction Context Resolver | 002, 003 |
| CSA-CEWA-005 | Layered Conversation Policy And Rendering | 004 |
| CSA-CEWA-006 | Context Observation, Profile, Summary Lineage | 003, 004 |
| CSA-CEWA-007 | Cross-Channel Continuity And Binding | 002, 003, 004 |
| CSA-CEWA-008 | Deterministic Identity Resolution And Assurance | 001, 003 |
| CSA-CEWA-009 | Signed WhatsApp Webhook Ingress | 008 and authorized environment configuration |
| CSA-CEWA-010 | Atomic Inbound Claim, Acknowledgement, Deduplication, And Replay | 003, 009 |
| CSA-CEWA-011 | Inbound Message Normalization | 010 |
| CSA-CEWA-012 | Outbound Queueing And Provider Transport | 002, 003, 008 |
| CSA-CEWA-013 | Service Window, Consent, And Template Eligibility | 010, 012 |
| CSA-CEWA-014 | Delivery Observations And Derived Projection | 010, 012 |
| CSA-CEWA-015 | Media Retrieval, Quarantine, Scan, Retention, And Erasure | 006, 008, 011 |
| CSA-CEWA-016 | WhatsApp Emergency Stop | 008, 010, ADR-031 conformance |
| CSA-CEWA-017 | Privacy-Safe Telemetry, Dead Letters, And Alerts | 001; integrate with applicable stories |
| CSA-CEWA-018 | Demo Provisioning, Activation, And Complete Teardown | 009-017 and separate Demo authority |
| CSA-CEWA-019 | UAT Stable Ingress And Activation | 018 lessons closed and separate UAT authority |
| CSA-CEWA-020 | Production Readiness And Dark Activation Gates | 019, 023, 024, 026 and separate Founder decisions |
| CSA-CEWA-021 | Web Regression And Shared-API Adoption | 002-007 |
| CSA-CEWA-022 | Future Mobile Compatibility Contract | 002 |
| CSA-CEWA-023 | Data Migration, Backup, Restore, And Rollback | 003, 006, 010, 014, 015 |
| CSA-CEWA-024 | End-To-End Acceptance And CE-FIT Qualification | 002-023 |
| CSA-CEWA-025 | Final Docker And Containerized End-To-End Validation | 024 and implementation author review PASS |
| CSA-CEWA-026 | Operational Handoff And Runbooks | 017-025 |
| CSA-CEWA-027 | Founder Handoff And Implementation Authorization Gate | Solution author review; no implementation |

Stories 018-020 describe readiness and evidence only unless their separate environment
authorities are granted. Their presence in the sequence is not authority to activate an
environment.

## 6. Canonical Requirement Index

Every normative implementation obligation is assigned one stable ID. These IDs are the
contract-to-ledger join key; the referenced PR #499 story remains authoritative for detailed
semantics and acceptance conditions.

| Requirement ID | Source | Observable outcome and acceptance oracle |
|---|---|---|
| WC120-R001 | Record Control; §2; CSA-CEWA-001 | Work starts only from the exact reviewed enterprise package, Founder-accepted ADRs, accepted WC-120, digest-valid ledger, and separate current-session authorization. |
| WC120-R002 | §1; CSA-CEWA-001 through CSA-CEWA-027 | BP, PR, AIR, CE, identity, data, Web, and operations retain their stated ownership; no new deployable, history/profile owner, client authority, or cross-owner write appears. |
| WC120-R003 | Solution §5; CSA-CEWA-002 | The shared candidate API preserves one channel-neutral conversation contract and its documented protocol, identity, authorization, limits, errors, retries, telemetry, and failure behavior. |
| WC120-R004 | Solution §6; CSA-CEWA-003 | Canonical message order, transaction boundaries, idempotency domains, and outbox behavior remain durable and prove no duplicate or reordered logical effect. |
| WC120-R005 | Solution §§8-9; CSA-CEWA-004/005 | Interaction context is server-resolved and versioned; policy layers and rendering remain bounded, with no client-supplied prompt or policy authority. |
| WC120-R006 | Solution §6.3; CSA-CEWA-006 | Context observations, profiles, summaries, and lineage preserve source/version, privacy, retention, and correction semantics. |
| WC120-R007 | Solution §4; CSA-CEWA-007 | Web-to-WhatsApp-to-Web continuity preserves relationship/conversation/message identity and sequence; denial, expiry, replay, or revert cannot grant authority. |
| WC120-R008 | Solution §7; CSA-CEWA-008 | Identity resolution is deterministic, environment- and recipient-bound, and fails closed for zero, multiple, stale, revoked, reassigned, or mismatched identities. |
| WC120-R009 | Solution §10.1; CSA-CEWA-009 | WhatsApp webhook declares `application/json`; exact raw bytes are authenticated before parsing, with signature, timestamp, app, recipient, and environment validation. |
| WC120-R010 | Solution §§10.1, 13; CSA-CEWA-010 | Inbound claim/acknowledgement is atomic, idempotent, deduplicated, replay-safe, and retryable without duplicate mutation. |
| WC120-R011 | Solution §§5, 10; CSA-CEWA-011 | Provider events are normalized into the accepted domain contract without trusting provider-controlled tenant, authority, or policy fields. |
| WC120-R012 | Solution §10.2; CSA-CEWA-012 | Outbound work is queued and dispatched under separate idempotency and provider boundaries; duplicate, timeout, crash, and unknown outcomes reconcile safely. |
| WC120-R013 | Solution §§10.2, 10.3; CSA-CEWA-013 | Consent, service-window, and template eligibility is checked against current state; ineligible sends fail closed without dispatch. |
| WC120-R014 | Solution §10; CSA-CEWA-014 | Delivery observations are immutable and project independent delivery dimensions; callbacks may not overwrite unrelated message state. |
| WC120-R015 | Solution §§10.3, 12; CSA-CEWA-015 | Media retrieval, quarantine, scanning, retention, legal hold, erasure, and cross-environment access obey the approved owner boundary. |
| WC120-R016 | Solution §§12-13; CSA-CEWA-016 | Emergency Stop fences new work, remains available through dependency failure, and prevents late results from regaining authority. |
| WC120-R017 | Solution §14; CSA-CEWA-017 | Telemetry, dead letters, and alerts expose only approved reason codes and operational signals; prohibited identity, secret, payload, and content leakage is zero. |
| WC120-R018 | Solution §§11, 15-16; CSA-CEWA-018 | Demo provisioning is isolated, default-off, auditable, and completely torn down; Demo activity cannot affect UAT or Production. |
| WC120-R019 | Solution §§11, 15; CSA-CEWA-019 | UAT readiness uses its stable ingress and exact isolated configuration; UAT activation remains separately authorized. |
| WC120-R020 | Solution §15; CSA-CEWA-020 | Production readiness is evidence-only and dark; no Production mutation, traffic, or activation occurs under WC-120. |
| WC120-R021 | Solution §4; CSA-CEWA-021 | Web adopts the shared generated-client contract while preserving existing behavior and rejecting invalid or stale responses safely. |
| WC120-R022 | Solution §4; CSA-CEWA-022 | Future Mobile compatibility is represented by the shared API contract without server semantic changes or channel-specific authority. |
| WC120-R023 | Solution §§6, 13; CSA-CEWA-023 | Expand/migrate/contract, migration watermark, backup, restore, rollback, and recovery invariants are tested before destructive contraction; evidence includes accepted per-environment RPO/RTO and data-loss bounds, injected fault, commands, invariant/checksum, watermark, and provider-egress denial. |
| WC120-R024 | Solution §§19-20; CSA-CEWA-024; WC-120-fitness-evidence-matrix.yaml | CE-FIT-01 through CE-FIT-16 map bidirectionally to stories, source oracles, exact Test Champion-selected test selectors, exact-candidate manifest, and evidence. |
| WC120-R025 | Solution §19.3; CSA-CEWA-025 | Final Docker/image/end-to-end qualification binds to an immutable candidate manifest covering source, image, API/solution, schema, migration, configuration, targeted tests, recovery, CE-FIT, and qualification digests. |
| WC120-R026 | Solution §§14-16, 22; CSA-CEWA-026 | Operational procedures cover alerting, dead letters, Stop, environment setup/teardown, recovery, rollback, privacy, and escalation; rehearsals produce retained evidence. |
| WC120-R027 | Solution §23; CSA-CEWA-027 | Founder receives the exact candidate, evidence, risks, rollback, and requested decisions; implementation, deployment, activation, PR approval, and merge remain distinct authorities. |
| WC120-R028 | PR #499 review `R-4248037029`; Solution §§11-12 | Complete telephone identities are absent from current files, fixtures, logs, evidence, and PR text; any shared-history cleanup follows a separate approved plan. |
| WC120-R029 | PR #499 review `R-4248037076`; enterprise §448 | A durable read-position mutation or compatible successor is present and advances participant state; an event-stream cursor alone does not pass. |
| WC120-R030 | PR #499 review `R-4248037125`; Solution §8 | Registered command descriptors and accepted typed payload references are discoverable from interaction context or a typed catalog operation. |
| WC120-R031 | PR #499 review `R-4248037174`; Solution §§4.1, 17 | Handoff revert is an idempotent operation preserving the source binding through retry, uncertainty, expiry, and denial. |
| WC120-R032 | PR #499 review `R-4248037216`; Solution §§5, 9 | Contribution discriminator variants require exactly one corresponding non-null payload and reject missing, mismatched, or simultaneous variants. |
| WC120-R033 | PR #499 review `R-4248037259`; Solution §5 | Command types and parameters form a closed typed union of registered command schemas; arbitrary keys and values are rejected by contract validation. |
| WC120-R034 | PR #499 package test evidence; candidate OpenAPI | OpenAPI validation proves 14 paths, 23 schemas, and resolution of all local references, with generated-client and producer/consumer fixtures passing. |
| WC120-R035 | Solution §§3, 18-19; all stories; WC-120-fitness-evidence-matrix.yaml | Each story and CE-FIT item has exact repository-native commands/test selectors, predicates, candidate binding, evidence references, and failure/rollback result frozen before implementation starts; the generic ledger validator alone is insufficient. |
| WC120-R036 | PR #498 §§4, 22; WC-114; WC-115-R005/R006 | WhatsApp remains an additive transport/session adapter over the existing BP Conversation Core and employment workspace; no second timeline, transcript, relationship, API owner, or authority is introduced. |
| WC120-R037 | Existing Core API; WC-114 BP API; PR #499 review R-4248037076/7125/7174 | Candidate operations are crosswalked to canonical read position, command discovery, employment operations, and handoff/revert contracts; only compatible additive operations remain. |
| WC120-R038 | ADR-023; WC-115 security profile and R102-R108; PR #498 §§12.7/13.6 | Phone identity, workload assertion, freshness, operation assurance, secret rotation/revocation, and Stop behavior reuse accepted owner profiles and cannot be weakened by channel or candidate API. |
| WC120-R039 | WC-115 data profile and R077-R084; PR #498 §15 and R-147 | Data ownership, transaction/order, tenant RLS, lineage, deduplication, retention/erasure, backup/restore, and migration are bound to accepted Data-owner controls before persistence work. |
| WC120-R040 | WC-115 AIR profile and R095-R101; PR #498 §§8, 14, 16, 21 | AIR receives minimized, server-resolved context and untrusted contribution content; provenance and degraded/unknown outcomes remain explicit, with no provider or authority choice delegated to the channel. |
| WC120-R041 | PR #498 §§13, 17-21, 23-24; Platform Architect contribution | Ingress, DNS/TLS, environment isolation, observability, recovery, teardown, and measurable WhatsApp SLOs have named owners and accepted targets; no infrastructure mutation is implied. |
| WC120-R042 | PR #498 §§17, 23-24, 26; WC-115 §7.4; WC-120-product-acceptance-matrix.yaml | Product-owned journeys specify customer-visible consent/service-window/template outcomes, approved copy, locale/readability/accessibility, voice correction/send consent, Stop reachability, and degraded states; pending choices block the affected journey. |
| WC120-R043 | PR #498 §27; R-146; R-147; §2.2 | Historical review findings, author repairs, and current office dispositions are represented separately; no author repair is labelled reviewer approval. |
| WC120-R044 | PR #498 §17; CE-FIT-01..16; Test Champion disposition | The fitness matrix has exactly one row per CE-FIT item, maps each to one or more stories, positive/boundary oracles, exact test selectors, immutable candidate binding, and a planned evidence location. |

## 7. Validation And Evidence

### 7.1 PR #499 Architecture-Package Evidence

PR #499 records the following passed plan-validation command and results; they validate the
architecture-only candidate and are not implementation evidence:

```text
PYTHONPATH=. pytest -q tests/test_openapi_slice.py tests/validation_control/test_spec_lint_scope.py
Unit tests: PASS (7/7)
Integration: N/A - architecture-only package
CE-FIT: PASS - CE-FIT-01 through CE-FIT-16 assigned to stories, components, tests, and evidence
OpenAPI: PASS - YAML parsed; 14 paths; 23 schemas; 133/133 local references resolved
Package structure: PASS - 27 stories x 23 mandatory fields; 24 runbook steps
Spec lint: PASS - scoped repository lint selected existing BP/PR specs plus the candidate
Diff check: PASS - git diff --check
YAML lint: PASS - relaxed profile (line-length warnings only)
```

### 7.2 Required Implementation Test Portfolio

For every story, the implementer records and runs the smallest exact repository-native
commands for the changed surfaces. The impact analysis and strategic plan must pin those
commands before implementation starts; they must not be guessed after code is written.

- .NET: filtered Business Platform / Constitutional Engine unit and integration tests.
- Python: exact Professional Runtime / AI Runtime test modules or node IDs.
- Web: exact Jest/Playwright projects or test names, plus type and lint checks.
- Contracts: OpenAPI lint/slice, generated-client build, and producer/consumer fixtures.
- Data: migration up/repeat/rollback compatibility, RLS, backfill, restore, and invariant queries.
- Security/privacy: signature verification, identity/assurance, secret authority, media isolation,
  Emergency Stop, environment isolation, and telemetry-leakage tests.
- Static/traceability: formatter, linter, type checker, dependency/spec trace gates, and the
  validated WC-120 requirement ledger.

At minimum, explicit predicates must prove: JSON webhook media type with raw-byte signature
verification; durable read-position advancement; authorized interaction-context command
discovery; idempotent handoff revert; exactly one correctly typed contribution payload;
closed typed command payloads; and absence of complete telephone identities from current
repository files, fixtures, logs, evidence, and PR text. The repository-history remediation
for already committed sensitive inputs requires a separately approved plan.

The behavioral portfolio in Section 19.2 of the solution package is mandatory: canonical
continuity; identity and authority denial with zero mutation; ingress signature, freshness,
atomic claim and replay; outbound idempotency and delivery projections; media/privacy;
Emergency Stop and recovery; and environment isolation. All CE-FIT-01 through CE-FIT-16
must map to direct acceptance oracles and evidence in
`work-contracts/WC-120-fitness-evidence-matrix.yaml`. The exact repository-native command and
test-node selectors are intentionally not guessed: the Test Champion must bind them to the
current owners during CSA-CEWA-001 before any implementation begins. A missing or stale
selector blocks `READY_FOR_STRATEGIC_PLAN`.

The existing `scripts/validate_requirement_ledger.py` checks ledger shape, IDs, required
fields, contract digest, and completion evidence; it does not prove CE-FIT completeness,
test executability, or candidate binding. A passing ledger-validator result is not evidence
that those obligations pass. The Test Champion must explicitly disposition the matrix and
its candidate/evidence bindings. Any automation enhancement to the validator is a separate
code change requiring its own authority; it is not implied by WC-120.

Customer-visible acceptance is separately captured in
`work-contracts/WC-120-product-acceptance-matrix.yaml`. Product owns approved copy, supported
locale/readability choices, consent journeys, and user-visible outcomes; BP enforces transport
eligibility, while Security/Data own their control decisions. Entries marked pending are
pre-implementation stops, not values for the Platform IT Expert to invent.

Run final Docker, image scans, and full containerized end-to-end validation only after all
stories, targeted tests, static checks, migration/restore/rollback checks, and implementation
author review pass. A broad suite does not replace per-story targeted evidence.

## 8. Rollback And Reversibility

The failure and rollback behavior in Sections 13 and 18 of the PR #499 solution package is
normative. Before implementation, the strategic plan must bind it to exact owner paths,
feature gates, schema versions, migration watermarks, backup/restore points, and tested
commands.

- Use additive expand -> migrate -> contract evolution; retain compatible readers and
  source behavior until the new path proves equivalence.
- Keep new behavior disabled or shadowed until its exact acceptance predicates pass.
- On failure, stop the affected path, preserve evidence, and return to the last compatible
  application behavior while retaining safe additive schema. Do not run destructive
  contraction as an ad hoc rollback.
- Story 023 must prove backup, restore, migration compatibility, and recovery consistency;
  record the environment, injected fault, exact backup/restore/rollback commands, schema and
  migration watermark, accepted numeric RPO/RTO and data-loss bounds, invariant/checksum
  oracle, provider-egress denial, and retained evidence for each environment.
- Stop and reconcile external provider operations independently. Application rollback does
  not reverse a sent message, provider registration, DNS mutation, or customer-visible effect.
- Demo teardown, UAT recovery, and Production-dark evidence are separate acceptance
  activities; none grants authority to mutate or activate that environment.

If rollback cannot preserve existing behavior or integrity, stop and request Founder
direction before proceeding.

## 9. Stops

Stop the affected story and report a blocker when:

- This exact Work Contract or its requirement ledger has not received the required Founder
  acceptance/validation, or current-session implementation authorization is absent.
- A required owning contract, owner, interface, security property, or accepted decision
  cannot be verified; ADR-023/ADR-031 assumptions fail; or the corrected package conflicts
  with the accepted enterprise architecture.
- Any of the seven PR #499 review findings remains unresolved or lacks its explicit test
  predicate.
- The crosswalk to Conversation Core or WC-114/WC-115 is missing, duplicate, incompatible,
  or would weaken an accepted owner contract.
- A required Data, Security, Platform, AI, Product, or Test Champion contribution is absent,
  ambiguous, or conflicts with an accepted profile; R-146/R-147 are inputs, not substitutes
  for downstream contribution or reviewer approval.
- A complete telephone identity, credential, token, key, provider payload, or customer
  content is found in a location prohibited by this contract.
- A migration is destructive or not demonstrably reversible; an acceptance oracle cannot
  be proved; the required owner or path does not exist; or preserving current behavior
  requires inventing architecture or policy.
- A provider, environment, DNS, deployment, Production, cost, retention, legal-hold, media,
  RPO/RTO, or activation decision lacks its own named authority.
- A test, security, privacy, CE-FIT, traceability, rollback, or exact-candidate gate fails.
- The CE-FIT matrix is incomplete, has no exact Test Champion-selected test command/node,
  is stale for the candidate, or lacks direct evidence binding.
- The Product acceptance matrix has unaccepted consent, locale/media, copy, accessibility,
  service-window/template, voice-correction, or degraded-state decisions for the affected
  journey.
- The candidate manifest, recovery limits, or provider-egress denial evidence is missing or
  does not match the tested source/configuration/image.

Do not resolve a stop by reducing a threshold, weakening a contract, changing a test, or
assuming approval.

## 10. Handoff Evidence

The implementation handoff package delivered to the Founder must include:

1. This accepted WC-120 revision and its validated `WC-120-requirements.yaml` ledger bound
   to the exact Work Contract SHA-256.
2. The completed Core/WC-114/WC-115 compatibility crosswalk and corrected, versioned
   solution package and API digest, closure evidence for all seven
   PR #499 review threads, and protected-configuration evidence without secret values.
3. Scoped dispositions and repair evidence for each required office, with R-146/R-147
   accurately identified as prior one-pass enterprise reviews and author-remediation
   records.
4. Platform IT Expert impact analysis and dependency-ordered strategic plan with exact
   paths, commands, owners, feature gates, compatibility window, and rollback.
5. Per-story targeted test evidence, producer/consumer contract evidence, migration /
   backup / restore / rollback evidence, and bidirectional CE-FIT-01..16 traceability.
6. The completed Product acceptance matrix, Test Champion-dispositioned CE-FIT matrix,
   immutable candidate manifest, and exact-candidate evidence references.
7. Privacy, signature, assurance, idempotency, replay, Emergency Stop, environment
   isolation, sensitive-data non-disclosure, and telemetry-leakage evidence.
8. Exact-candidate Docker/container qualification, image evidence, rehearsed runbooks,
   authorized teardown/recovery proof, and implementation author review bound to the
   exact 40-character commit.
9. A concise residual-risk and open-decision list, including each ungranted environment
   authority and any separate Founder decision required.

The handoff is complete only as an evidence package for Founder review. It does not authorize
deployment, provider mutation, activation, traffic, Production change, PR approval, or merge.

## 11. Author Review

The author must review this complete Work Contract against PR #498's merged architecture and
remediation record, PR #499's candidate package and seven review threads, the exact current
Conversation Core/WC-114/WC-115 inputs, Founder ADR approval, required specialist profiles,
and the Chief Solution Architect's handoff standard. Review coverage includes precedence,
additive scope, authority, cross-contract compatibility, office-review provenance, requirements,
sequencing, test oracles, sensitive-data handling, rollback, stops, and handoff evidence.

### 11.1 Findings And Repairs

| Finding | Repair | Result |
|---|---|---|
| PR #499 candidate could be read as superseding WC-114/WC-115 or creating parallel conversation authority. | Set explicit source precedence and require a path/operation/schema compatibility crosswalk against the existing Conversation Core, BP API, WC-114/WC-115, and accepted profile before implementation planning. | RESOLVED |
| Stale PR #499 status and ADR labels obscured the Founder decision and the remaining implementation gate. | Recorded the Work Contract status replacement and Founder approval of ADR-051/052/053; explicitly retained specification, office-contribution, exact-contract acceptance, and session-authorization gates. | RESOLVED |
| PR #498 R-146/R-147 could be misrepresented as downstream office approval. | Pinned their original `CHANGES REQUIRED` review records and PR #498 §27 author remediation; stated that neither is a post-repair reviewer approval or WC-120 review. | RESOLVED |
| WC-114/WC-115 specialist profiles were not explicitly carried into identity, data, AIR, or platform requirements. | Added WC120-R038 through WC120-R042, pinned the existing profile, and made specialist contributions a hard pre-implementation gate. | RESOLVED |
| The ledger's required-evidence details did not meet this contract's own Definition of Done. | Added planned evidence destinations and failure/rollback behavior to every ledger row through the shared defaults, and added traceable requirements for cross-contract reuse and office dispositions. | RESOLVED |

**Contract authoring result:** PASS - the additive boundary, source precedence, Founder ADR
decision, status replacement, review provenance, specialist gates, requirements, and evidence
ledger are explicitly recorded.
**Implementation readiness:** BLOCKED pending the compatibility crosswalk, closure of all
seven PR #499 specification findings, scoped specialist dispositions/repairs, Founder
acceptance of this exact Work Contract, successful ledger validation, and separate explicit
current-session implementation authorization.
