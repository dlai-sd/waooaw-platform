# Work Contract 034 — WAOOAW Hybrid Web Application Shell

**Goal:** GOAL-005 — Agent Employment Experience Program
**Backlog Item:** IB-014 — Customer Self-Service Portal
**Gate:** G5 CLEAR
**Architecture Office:** Enterprise Architect (INST-004)
**Implementation Office:** Platform IT Expert (INST-010)
**Architecture Reviewer:** Solution Architect (INST-005) + Product Owner (INST-011)
**Implementation Reviewer:** Enterprise Architect (INST-004) in an independent session
**Status:** PHASE B EXECUTION RELEASED — COMPONENT ENTRY GATES APPLY
**Authorization:** FA-031 authorized WC-034 Phase B implementation; FA-034 released execution on 2026-08-09 after FA-033 activated Platform IT Expert v1.2 Skill 16 and PR #244 merged. INST-010 may begin F1 and any later component whose local entry criteria pass.
**Constitutional Basis:** C-001, C-009, C-023, C-034, C-042, C-059, C-064, C-065, C-076; ADR-017

## Outcome

Define one coherent WAOOAW web application that preserves the existing public home-page direction and introduces a reusable authenticated application layout. The product remains a Next.js App Router PWA with hybrid server and client rendering; "hybrid SPA" does not authorize a client-only React application or a second frontend stack.

The architecture must make the transition from public discovery to authenticated employment feel continuous while preserving different navigation, density, and constitutional controls for public, customer, and Founder surfaces.

## Scope Boundary

### Phase A — Architecture and UI/UX Specification (INST-004)

Phase A defines the route topology, shell ownership, responsive layout, constitutional control placement, rendering boundaries, design-token migration, and acceptance contract. It may update architecture, UX specifications, this Work Contract, and review evidence. It must not modify `web/app/`, generate build output, or implement APIs.

### Phase B — Application Implementation (INST-010)

Phase B was authorized by FA-031 after Phase A received independent architecture review. FA-033 and merged PR #244 completed the Platform IT Expert Skill 16 Type 1 lifecycle; FA-034 releases execution. INST-010 may begin F1 and may select later components only when their service-contract and acceptance prerequisites pass. Phase B implements the approved shell, migrates the home page into Next.js, and places customer and Founder routes inside their approved layouts.

Founder admin capabilities remain part of WC-034, but they are not the application architecture. Markup Designer, Trial Budget Config, and Coupon Manager are feature routes nested inside the Founder surface after the shared shell exists.

## Required Surface Model

| Surface | Route group | Primary layout | Constitutional controls |
|---|---|---|---|
| Public | `(public)` | Brand navigation, responsive content canvas, footer; Concierge deferred from first release | Honest capability and limitation disclosure; no authenticated data |
| Customer | `(authenticated)` | Compact app header, desktop side navigation, mobile bottom navigation, relationship workspace | Persistent Emergency Stop; rights and lifecycle state; tenant-safe identity |
| Founder | `(founder)` | Customer shell primitives with denser administration navigation | `founder=true` authorization; no customer-facing discovery language |
| Shared system | global | Loading, empty, error, offline, forbidden, and not-found states | Fail-safe messaging; no fabricated success; correlation support |

The shell must use role-aware route composition rather than runtime CSS hiding. Unauthorized Founder routes redirect to `/403`. Public pages must not load authenticated application data. Customer and Founder navigation must remain usable at 360px without horizontal overflow.

## Architecture Tasks

| task_id | scope | model_hint | status | completed_at |
|---|---|---|---|---|
| WC034-01 | A01 — Inventory the static home, current Next.js routes, WC-057 provisional workspace, and UX vocabulary; record reuse, migration, and retirement decisions without changing source. | reasoning | done | 2026-08-08 — architecture prototype rejected and permanently deleted; `web/WAOOAWHome.html` approved by Founder as the inspiration source for logo, fonts, color themes, design language, and public-page migration |
| WC034-02 | A02 — Define route groups, layouts, navigation, responsive composition, role/claim and server/client boundaries, application states, and persistent constitutional controls. | reasoning | done | 2026-08-08 — shell, continuity boundary, failure semantics, privacy, and budgets published |
| WC034-03 | A03 — Map the approved home-page inspiration into shared tokens, typography, spacing, iconography, focus, motion, RTL, and accessibility rules; resolve vocabulary conflicts without replacing its visual character. | reasoning | done | 2026-08-08 — logo treatment, Noto Sans-led typography, blue/green/orange/navy themes, and trust-focused design language carried forward; constitutional constraints control adaptations |
| WC034-04 | A04 — Define public, customer, relationship, settings/profile, and Founder information architecture and groom the implementation components. | reasoning | done | 2026-08-08 — route families, navigation, relationship views, and F0–F8 decomposition published |
| WC034-05 | A05 — Define generated-client/API boundaries and route missing operations to their owning services; no UI-created BP/WBE endpoints. | reasoning | done | 2026-08-08 — INST-004 owner/gap matrix complete; INST-005 validation requested under A07 |
| WC034-06 | A06 — Define executable desktop, exact 360px, keyboard, RTL, reduced-motion, PWA, overflow, axe, privacy, performance, and coverage evidence. | reasoning | done | 2026-08-08 — component, contract, browser, axe, screenshot, and quality matrix published |
| WC034-07 | A07 — Submit the architecture package for independent INST-005 and INST-011 review and route unresolved product decisions. | reasoning | done | 2026-08-08 — PR #239 open; Solution Architect and Product Owner review requested |

## Architecture Package

| Artifact | Responsibility |
|---|---|
| `architecture/reference/ux/hybrid-application-shell.md` | Canonical experience, routes, rendering, navigation, API ownership, operational semantics, privacy, and budgets |
| `architecture/reference/ux/hybrid-visual-system-contract.md` | Static HTML review status, tokens, typography, responsive composition, component and motion rules |
| `architecture/reference/ux/hybrid-ui-acceptance-contract.md` | Executable component, browser, accessibility, RTL, privacy, PWA, performance, and visual evidence |
| `architecture/reference/ux/wc-034-implementation-decomposition.md` | WC-016 supersession and F0–F8 dependency-ordered implementation handoff |
| `architecture/reference/agents/platform-it-expert-nextjs-skill-proposal-input.md` | Evidence for Product Owner review of the required INST-010 frontend skill uplift |
| `architecture/reference/ux/wc-034-enterprise-architecture-assessment.md` | Formal readiness verdict, risks, resolutions, and remaining gates |
| `architecture/reference/components/identity-boundary.md` | Canonical F2 component, API, data, error, assurance, integration, acceptance mapping, and dependency gate contract |
| `architecture/reference/api-specs/business-platform.openapi.yaml` | Canonical public F2 registration, verification, completion, and account-linking operations for generated TypeScript clients |
| `architecture/reference/components/conversation-core.md` | Canonical F3 BP/PR ownership, data-shape, error, idempotency, privacy, tenant, reconciliation, acceptance, and dependency gate contract |
| `architecture/reference/api-specs/professional-runtime.openapi.yaml` | Canonical internal F3 professional execution, cancellation, and typed stream contract |

## Implementation Components — Gated

Detailed scope, dependencies, exclusions, and acceptance IDs are normative in `architecture/reference/ux/wc-034-implementation-decomposition.md`.

| Component | Scope | Owner | Status |
|---|---|---|---|
| F0 | Architecture and dependency closure | INST-004 + reviewing/owning offices | review complete — remaining API and Founder gates named |
| F1 | Experience foundation | INST-010 | complete — R-052 approved; PR #246 merged to `main` as `798c183` on 2026-08-09 |
| F2 | Identity and registration | INST-010 + identity/BP owners | R-055 contract remediation complete — FA-035 fixes Google/Facebook/Apple/email fallback and progressive mobile policy; implementation blocked by INST-004 ADR-008 amendment and independent re-review; Facebook activation blocked by FA-002/FA-018 and Apple by FA-019 |
| F3 | Conversation core | INST-010 + BP/PR owners | implementation in progress — WC034-08 BP ingress complete with Docker test and coverage evidence; GOA-GOAL-005-INST-010-02 and ACC-GOAL-005-INST-010-02 valid; deployment separately blocked |
| F4 | Relationship workspace | INST-010 + BP/WBE owners | blocked — Plan/Priority Work and Consumption projections plus implementation gates |
| F5 | Omnichannel continuity | INST-010 + WC-060 owners | blocked — WC-060 completion plus implementation gates |
| F6 | Voice interaction | INST-010 + Product/Security/Data/Solution owners | blocked — voice consent, retention, transcription, attachment, and API decisions |
| F7 | Founder administration | INST-010 + BP/WBE owners | blocked — canonical BP Founder facade and internal WBE management APIs plus implementation gates |
| F8 | Integrated acceptance and hardening | INST-010, independently reviewed | blocked — selected release components complete and authorized |

### F3 Autonomous Implementation Tasks

| task_id | scope | model_hint | status | completed_at |
|---|---|---|---|---|
| WC034-08 | Implement the BP OpenAPI 1.2.0 conversation timeline, send, retry, read-position, cancellation, and resumable SSE operations with JWT tenant authority, UUID request-hash idempotency, privacy-safe RFC 9457 errors, and CE-confirmed Evidence First state. | reasoning | completed | 2026-08-10 |
| WC034-09 | Implement the PR OpenAPI 1.1.0 BP-authenticated execution, cancellation, and resumable SSE operations with typed internal events, Temporal execution state, Stop preservation, and no public or provider-facing ingress. | reasoning | in-progress | — |
| WC034-10 | Generate the F3 `typescript-fetch` client without manual patches and implement the server-only BP boundary plus durable conversation timeline, composer, retry, reconciliation, typed cards, stream, cancellation, offline, accessibility, and exact 360px behavior. | reasoning | pending | — |
| WC034-11 | Add BP, PR, and web unit/integration coverage for idempotency, tenant isolation, privacy-safe errors, cursor replay, reconnect, cancellation, Stop independence, Evidence First, versioned schemas, and generated-client conformance; affected services and changed interactive web code must each reach at least 90% line coverage. | auto | pending | — |
| WC034-12 | Execute Docker-only regression and constitutional suites plus browser acceptance for UX-CONV-01 through UX-CONV-07, CCT-UX-HO-01 through CCT-UX-HO-03, CCT-UX-EF-01 and CCT-UX-EF-02, UX-PWA-03, and UX-RES-01; publish evidence for independent INST-004 review without merging or deploying. | auto | pending | — |

## Required Inputs

| Input | Status |
|---|---|
| `web/WAOOAWHome.html` — existing public home-page template | Founder-approved 2026-08-08 — inspiration source for logo, fonts, color themes, design language, and public-page migration; constitutional UX vocabulary controls adaptations |
| `web/app/` — WC-057 provisional Next.js PWA and relationship workspace | present — implementation baseline |
| `architecture/reference/ux/constitutional-ux-vocabulary.md` | approved — normative vocabulary and public navigation input |
| `architecture/reference/ux/suresh-portal-walkthrough.md` | approved input with open items requiring reconciliation |
| `architecture/reference/api-specs/business-platform.openapi.yaml` | present — canonical BP API source |
| `architecture/reference/billing/customer-acquisition-spec.md` | present — Founder tooling and acquisition input |
| ADR-017 — Next.js 14 TypeScript PWA | accepted — framework boundary fixed |
| WC-057 — Employment Relationship foundation | merged to `main`; independent review evidence remains unresolved |
| WC-027 and WC-031 — WBE markup/trial/promotions contracts | required before Founder feature implementation |
| Platform IT Expert frontend skill lifecycle | complete — Platform IT Expert v1.2 Skill 16 active under FA-033; PR #244 merged |

## Architecture Definition of Done

- [x] One application-shell specification defines all four surfaces and route ownership; independent review remains pending.
- [x] Public-to-authenticated continuity is explicit; no duplicate production home-page implementation remains in the target state.
- [x] Desktop, tablet, 360px mobile, RTL, keyboard, reduced-motion, offline, loading, empty, error, and forbidden behavior are specified.
- [x] Emergency Stop placement and behavior remain consistent with C-001 and ADR-017.
- [x] Every screen family maps to an approved capability and API owner; missing contracts are blocked and owner-routed.
- [x] Founder feature routes remain subordinate to the shared shell and are separately authorization-gated.
- [x] INST-005 reviewed component, API, rendering, and continuity ownership — R-047 APPROVED.
- [x] INST-011 reviewed product information architecture, labels, release composition, deferred choices, and Skill 16 business case — R-048 APPROVED.

## Implementation Definition of Done

- [ ] The approved Next.js application shell is implemented with generated API clients and strict TypeScript.
- [ ] Public, customer, and Founder authorization boundaries pass route-level tests.
- [ ] Existing home-page content is migrated or explicitly retired; there is one production entry point.
- [ ] Exact 360px mobile and desktop Playwright projects pass with no horizontal overflow.
- [ ] Keyboard, RTL, reduced-motion, PWA manifest, and zero-critical-axe acceptance checks pass.
- [ ] Changed interactive code maintains at least 90% line coverage.
- [ ] VERSION, CHANGELOG, SPRINT-REGISTRY, and PROJECT_STATE close only after independent review.

## Explicit Exclusions

- No React/Vite SPA, React Native application, or second web framework.
- No WC-058 through WC-060 employment-journey implementation.
- No new BP/WBE endpoint implemented from a UI task without its owning specification and authorization.
- No Founder-admin implementation during Phase A.
- No claim that the WC-057 provisional UI is the approved final visual design.
- No amendment to the ratified Platform IT Expert specification before Product Owner review and Founder approval of the new-skill proposal.
