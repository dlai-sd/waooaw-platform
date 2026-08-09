# WC-034 Hybrid Application Implementation Decomposition

**Document type:** Architecture Handoff — Proposed Implementation Components
**Office:** Enterprise Architect (INST-004)
**Work Contract:** WC-034 / WC034-A04 and WC034-A05
**Status:** REVIEW CANDIDATE — COMPONENTS GROOMED, IMPLEMENTATION UNAUTHORIZED
**Implementation owner:** Platform IT Expert (INST-010), after capability and authorization gates
**Review owners:** Solution Architect (INST-005) and Product Owner (INST-011)
**Constitutional basis:** C-001, C-009, C-023, C-032, C-034, C-042, C-059, C-063, C-065, C-071, C-076, C-095

## Purpose

WC-034 must not execute as one broad frontend sprint. This decomposition defines independently reviewable customer and platform slices, their prerequisites, and their acceptance boundaries. It does not assign Work Contract numbers, prioritize roadmap capacity, or authorize implementation; those decisions belong to Product Ownership and the Founder.

Every component consumes the shell, visual, and acceptance contracts. Missing service operations return to the owning service specification and Work Contract. They are not created inside a web component task.

## WC-016 Supersession

WC-016 is superseded for future web implementation planning by WC-034 and this decomposition. Its historical record remains unchanged.

| WC-016 assumption | Current controlling decision |
|---|---|
| Generic registration form posts to `/api/customers` | Channel-specific verified identity, deterministic account linking, and canonical identity/API contracts |
| Three-exchange canned Concierge | One durable relationship conversation; no production canned-success fallback |
| UI directly triggers a PR WebSocket Stop path | Existing dedicated constitutional Stop path remains authoritative and independently measured |
| Vitest unit suite | Existing web baseline uses Jest, Testing Library, Playwright, and axe |
| Static home promotion plus three features in one sprint | Dependency-ordered components with independent acceptance and API readiness gates |

No implementation task may cite WC-016 as authority where it conflicts with the WC-034 architecture package or GOAL-005 D-02 through D-06 contracts.

## Entry Gates Shared by All Components

1. WC-034 Phase A has APPROVED records from INST-005 and INST-011.
2. The Platform IT Expert frontend skill proposal has completed its required lifecycle and activation gate.
3. Founder has explicitly authorized the selected implementation Work Contract for the current session or autonomous run.
4. Required owner OpenAPI operations are approved and generated-client compatible.
5. The component has a C-095 architecture skeleton or an explicitly approved determination that no new platform component is introduced.
6. The acceptance IDs assigned to the component are present in its Work Contract.

## Component Sequence

```text
F0 Architecture Closure
  └─ F1 Experience Foundation
       ├─ F2 Identity and Registration
       ├─ F3 Conversation Core
       │    ├─ F4 Relationship Workspace
       │    └─ F5 Omnichannel Continuity (after WC-060)
       ├─ F6 Voice Interaction (after voice/privacy contract)
                └─ F7 Founder Administration (after WBE management APIs)

Every authorized release selection
     └─ F8 Integrated Acceptance and Hardening
```

F2 and the service-contract portion of F3 may be prepared in parallel after F1, but an authenticated end-to-end conversation cannot close until both pass. F5, F6, and F7 remain independently deferrable. F8 is not a feature after F7; it is the mandatory release gate for whichever components Product Ownership selects.

## F0 — Architecture and Dependency Closure

**Outcome:** Implementation receives no unresolved architecture decision.

**Scope:**

- obtain independent shell, visual, product, API-ownership, security-boundary, and acceptance review;
- carry the INST-005 decision that `@ai-sdk/react` is not an F3 architecture dependency and may not be introduced before the canonical stream contract is approved;
- close or route the canonical conversation, Plan/Needs your attention, Usage & budget, registration/linking, and Founder management API gaps;
- establish performance profiles and the supported browser matrix; retain attachments, voice, and cross-channel notification suppression as explicit deferrals unless their owning contracts are selected for the release;
- retire WC-016 as a future authority in the implementation Work Contract.

**Exit:** Every later component is READY, BLOCKED with named dependency, or explicitly DEFERRED. No decision is delegated to component code.

## F1 — Experience Foundation

**Customer slice:** Public discovery transitions into one coherent, installable, localized application shell without promising an unimplemented Concierge.

**Scope:**

- route groups and server-owned authorization layouts;
- shared tokens, Noto font loading, light/dark/system themes, locale and direction bootstrap;
- public direct-browse, authentication, customer, Founder, and shared-system layout primitives;
- responsive navigation and stable compact/intermediate/expanded composition;
- PWA manifest and safe static shell caching;
- loading, empty, offline, forbidden, not-found, and global error primitives;
- migrate or retire the static home implementation so one production entry remains.

**Excludes:** Real registration, conversation transport, relationship data, Founder features, voice capture.

**Acceptance:** UX-SHELL-01, UX-SHELL-03, UX-SHELL-05, UX-RESP-01 through UX-RESP-06, CCT-UX-A11Y-01 through CCT-UX-MOTION-01, UX-PWA-01, UX-PWA-02, and UX-PERF-01 through UX-PERF-03 apply to F1 routes and shell states. UX-VIS-01 uses only F1-owned public, authentication, and shared-system baselines here; the complete cross-component screenshot matrix remains an F8 exit condition.

## F2 — Identity and Registration

**Customer slice:** A customer registers or signs in through an approved channel and resumes the correct account without duplication.

**Scope:**

- dedicated login, registration, verification, account-linking, and authentication-error routes;
- one Keycloak-brokered Google/Facebook/Apple/email-fallback experience;
- confirmed email at completion and progressive mobile verification before consequential actions;
- deterministic WhatsApp-to-web identity linking and duplicate resolution;
- progressive assurance and fresh step-up for high-risk actions;
- safe return target, session expiry, sign-out, and account-switch cleanup.

**Dependencies:** Identity/API contract for registration, verification, linking, and duplicate resolution; ADR-008; ADR-023.

**Excludes:** Creating an active Employment Relationship, accepting a contract, payment, or Stop release at insufficient assurance.

**Acceptance:** UX-SHELL-02, UX-SHELL-04, UX-AUTH-01 through UX-AUTH-06, UX-PRIV-01, UX-PWA-04.

**Contract status:** R-055 REMEDIATED — FA-035 fixes the unified provider experience and progressive-mobile policy. `architecture/reference/components/identity-boundary.md` and the 13 F2 operations in the canonical Business Platform OpenAPI define component, API, data, error, assurance, idempotency, retry, tenant, privacy, session, and generated-client boundaries. Implementation remains BLOCKED by that contract's gate table: the INST-004 ADR-008 amendment and independent INST-004 re-review are unresolved. Facebook activation additionally requires FA-002/FA-018 evidence; Apple activation requires FA-019 evidence.

## F3 — Conversation Core

**Customer slice:** A customer can resume, read, compose, send, stream, retry, and understand one durable professional conversation.

**Scope:**

- cursor-paginated timeline, unread boundary, date and channel separators;
- text composer, draft retention, explicit send, idempotency, retry, and reconciliation;
- typed streamed responses, cancellation, partial-response disclosure, and live-region behavior;
- message-delivery and professional-processing states;
- Action, Plan, Deliverable, and Decision card renderers against versioned schemas;
- persistent existing Emergency Stop control without changing its transport.

**Dependencies:** Canonical BP conversation OpenAPI operations and schemas for customer-facing reads and commands; an internal Professional Runtime execution/stream contract surfaced through the approved BP public stream boundary; no ordinary browser-to-PR connection and no direct model-provider calls. `@ai-sdk/react` is not an approved F3 dependency.

**Excludes:** First-release attachments, cross-channel checkpoint commit, voice capture, browser-owned plan aggregation, model dispatch.

**Acceptance:** UX-CONV-01 through UX-CONV-07, CCT-UX-HO-01 through CCT-UX-EF-02, UX-PWA-03, UX-RES-01.

## F4 — Relationship Workspace

**Customer slice:** The customer can understand and govern the professional relationship around the conversation.

**Scope:**

- configured professional switcher and relationship header;
- Plan, Work, Results, Usage & budget, and Rights & control routes and expanded context panel;
- goals, next work, deliverables, approvals, schedule, business outcomes, allowance, forecast, budget, rights, scope, authority, lifecycle, and evidence;
- global Needs your attention presentation using server-provided ordering only after the aggregate contract is approved;
- pause, resume, approval/rejection, scope-boundary confirmation, and evidence export only through approved service operations.

**Dependencies:** Owner-approved Plan/Needs your attention and Usage & budget projections; relationship, approval, evidence, goals, results, and billing generated clients. Needs your attention is omitted if its aggregate projection is not part of the selected release.

**Excludes:** Browser-derived priority, direct ledger access, technical metrics as headline outcomes, unapproved lifecycle transitions.

**Acceptance:** UX-CONV-06 through UX-CONV-08, CCT-UX-BOUNDARY-01, CCT-UX-RIGHTS-01, CCT-UX-EF-01, UX-SHELL-06.

## F5 — Omnichannel Continuity

**Customer slice:** An authenticated customer moves between WhatsApp and web without changing the relationship or duplicating consequential outcomes.

**Scope:**

- channel provenance and continuation separators;
- BP-owned authenticated handoff preparation, activation, checkpoint commit/revert, and public outcome retrieval;
- PR-owned internal channel delivery/session processing behind the BP contract;
- checkpoint, acknowledgement, cursor, ordering, and duplicate-delivery handling;
- active-channel notification suppression and reconnect behavior.

**Hard dependency:** WC-060 complete and its adversarial CCTs passing.

**Excludes:** Any pre-WC-060 claim of committed handoff or exactly-once cross-channel action.

**Acceptance:** UX-CONV-03, UX-RES-02, UX-CONT-01 through UX-CONT-06, plus WC-060 handoff, replay, downgrade, takeover, and cross-tenant CCTs.

## F6 — Voice Interaction

**Customer slice:** A customer records, reviews, corrects, and sends a voice contribution in the selected language with informed handling of its transcript.

**Scope:**

- permission, recording, pause/cancel, duration, upload progress, retry, playback, and text fallback;
- transcription language, confidence, correction, consent, retention, and evidence-lineage presentation;
- safe keyboard/screen-reader alternative and stable composer dimensions.

**Dependencies:** Product, Security, Data, and Solution Architecture approval of codec/size, malware scanning, transcription, consent, retention, correction, and service contracts.

**Excludes:** Shipping a visually enabled recorder before upload/transcription/privacy ownership exists.

**Acceptance:** Dedicated voice matrix added to the acceptance contract before this component becomes READY; compact keyboard, offline, RTL, and accessibility scenarios are mandatory.

## F7 — Founder Administration

**Institutional slice:** An authorized Founder manages markup, trial budgets, and coupons through isolated, auditable administration routes.

**Scope:**

- Founder layout and server authorization boundary;
- Markup Designer, Trial Budget Config, and Coupon Manager;
- explicit confirmation, validation, immutable evidence reference, and conflict/error handling;
- no customer discovery language or customer navigation leakage.

**Dependencies:** Canonical BP Founder-management OpenAPI operations and generated web client; internal WBE management contracts invoked only by BP; Founder assurance contract; WC-027 and WC-031 outcomes.

**Excludes:** Direct database access, private undocumented URLs, CSS-hidden customer routes, or expanding Founder authority in the UI.

**Acceptance:** UX-SHELL-03, UX-SHELL-06, UX-CONTRACT-01, keyboard/RTL/responsive/axe matrix for every Founder route, owner-defined financial and authorization CCTs.

## F8 — Integrated Acceptance and Hardening

**Outcome:** The authorized release slice satisfies the complete executable acceptance contract and contains no hidden cross-component regression.

**Scope:**

- Chromium, Firefox, and WebKit browser matrix;
- exact 360×800, intermediate, and expanded projects;
- English/Urdu, light/dark, reduced-motion, offline/reconnect, and Stop-state screenshots;
- security/privacy inspection, generated-contract conformance, coverage, lint, build, and PWA checks;
- dependency and bundle review; no unused template packages or copied persistence/auth architecture;
- evidence package for independent implementation review.

**Exit:** All acceptance IDs assigned to the selected release components pass. Deferred components are unavailable honestly and do not leave nonfunctional controls.

## Proposed Work Contract Boundaries

Product Ownership should issue separate implementation Work Contracts for F1, F2, F3+F4, F5, F6, and F7 unless release sequencing or risk review requires a narrower split. Every implementation Work Contract that can produce a releasable increment includes the proportional F8 evidence gate for its selected components. F0 remains architecture closure under WC-034 Phase A.

F3 and F4 may share one Work Contract only after all required read and command contracts are approved. F5 must remain separate because WC-060 controls its security and replay semantics. F6 must remain separate because voice introduces new privacy, data, accessibility, and provider decisions. F7 remains independently releasable from customer conversation work but cannot bypass its proportional F8 gate.
