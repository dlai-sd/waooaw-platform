# Platform IT Expert Frontend Skill Proposal Input

**Artifact type:** Enterprise Architecture Capability Gap Assessment
**Agent:** WAOOAW AI Agent — Platform IT Expert
**Candidate skill:** Next.js Conversational Experience Engineering
**Change type after approval:** `type:agent-update`, `update-type:new-skill`
**Status:** AWAITING PRODUCT OWNER REVIEW AND FOUNDER DECISION
**Produced by:** Enterprise Architect (INST-004), WC-034 Phase A
**Constitutional basis:** C-001, C-009, C-023, C-032, C-042, C-059, C-063, C-065, C-071, C-076, C-095, C-100; ADR-002, ADR-008, ADR-017, ADR-023

## Governance Boundary

This artifact is evidence for the Section 3.20 Product Owner review. It is not the Product Owner's SKILL_PROPOSAL, Founder approval, an agent-spec amendment, or implementation authorization.

The ratified Platform IT Expert remains at 15 skills. Section 15 Type 1 work may begin only after Product Owner review and an explicit Founder APPROVE decision. The new skill must then receive independent EA review; the author of the amended spec cannot issue that review under C-065.

## Gap Evidence

The current Skill 4 gives Next.js one line: strict TypeScript, no `any`, and ESLint. It does not define:

- App Router server/client ownership, route authorization, loading/error boundaries, or generated-client discipline;
- React conversation streaming, cancellation, reconciliation, idempotency, structured message parts, or partial-response behavior;
- responsive compact/intermediate/expanded composition, installed-PWA behavior, safe areas, mobile keyboards, or offline drafts;
- accessibility, focus lifecycle, live regions, reduced motion, multilingual font loading, Indic scripts, or RTL mirroring;
- constitutional status semantics separating transport delivery, professional processing, and Evidence First confirmation;
- visual regression, exact 360px, multi-browser Playwright, axe, privacy/cache, performance, or bundle acceptance;
- safe adoption boundaries for external frontend templates and AI SDKs.

WC-034 cannot be assigned responsibly to the current generic Code Implementation skill without delegating architecture choices to implementation, contrary to C-032.

## Product Owner Assessment Inputs

| Required question | EA evidence |
|---|---|
| Genuine new skill or prompt/training gap? | Genuine operational skill gap. The work is a repeatable engineering discipline with its own inputs, workflow, outputs, and acceptance evidence; one prompt cannot supply durable competence and gates. |
| Adjacent professional already covers it? | No. Solution Architecture owns component design and QA owns independent evidence; neither implements the frontend. Generic Skill 4 is too broad. |
| Customer segment | Indirectly every web/PWA customer and every professional relationship; directly all WAOOAW frontend implementation sprints. |
| Pricing impact | Internal development capability; no customer-facing skill price. Development-tool and dependency costs remain under C-077/C-067 controls. |
| Constitutional dependencies | Existing claims and ADRs are sufficient for the skill proposal. New APIs, voice providers, or model paths may require their own decisions later. |
| Regulatory considerations | DPDPA data minimization, consent, identity, accessibility, and secure session handling; skill does not itself authorize data collection. |
| Primary risk | Template copying or direct model access could bypass WAOOAW auth, service ownership, CE, evidence, privacy, and framework constraints. |
| Recommendation | APPROVE_FOR_SPEC, with no implementation authority and an explicit retroactive activation-gate audit. |

## Candidate Skill Contract

### Trigger

An approved Work Contract requires creation or modification of a Next.js customer, Founder, authentication, conversation, PWA, responsive, accessibility, localization, or browser acceptance surface.

### Required Inputs

- approved route, component, API-ownership, visual, security, privacy, and acceptance contracts;
- accepted framework and identity ADRs;
- generated OpenAPI clients or approved service-contract fixtures;
- explicit implementation authorization for the selected Work Contract;
- C-095 skeleton or approved no-new-component determination.

### Outputs

- strict TypeScript Next.js implementation within approved route and rendering boundaries;
- accessible, localized, responsive, theme-complete component behavior;
- generated-client integration with explicit pending, failure, conflict, and unknown states;
- Jest/Testing Library, Playwright, axe, visual, performance, privacy, and PWA evidence;
- dependency decision record for any library not already approved by the architecture package.

### Authorized Actions

- implement approved App Router layouts, routes, server components, and focused client interaction islands;
- implement typed conversation presentation, drafts, streams, cancellation, retries, and structured message parts against approved contracts;
- implement design tokens, semantic HTML, CSS, responsive/native-mobile behavior, themes, localization, RTL, accessibility, and PWA behavior;
- generate and consume approved API clients; add thin typed adapters that do not duplicate business rules;
- add component, contract, browser, accessibility, visual-regression, performance, and privacy tests;
- propose a dependency spike when an existing library may reduce verified complexity.

### Prohibited Actions

- invent endpoints, service schemas, lifecycle rules, authorization logic, constitutional semantics, or browser-owned business aggregates;
- call foundation-model providers directly from browser or Next.js routes unless a separately approved architecture explicitly assigns that ownership;
- copy template authentication, database, ORM, model-provider, deployment, or persistence architecture into WAOOAW;
- treat transport delivery as constitutional evidence or simulate service success after timeout/failure;
- store bearer/refresh tokens or authenticated response payloads in browser or service-worker caches;
- ship hardcoded colors, untranslated strings, inaccessible icon-only meaning, unbounded message history, or production fallback mocks;
- modify visual baselines in bulk without route-by-route reviewer evidence.

### Always Ask or Escalate

- missing or contradictory OpenAPI operation, generated schema, route authorization rule, or service owner;
- new framework, state-management, component-system, AI SDK, persistence, telemetry, authentication, or PWA dependency;
- change to Emergency Stop path, latency, placement, or release behavior;
- voice consent, transcription, retention, provider, attachment, scanning, or notification decision;
- inability to meet 360px, RTL, accessibility, privacy, performance, or 90% coverage gates without changing architecture.

### Engineering Workflow

1. Map each Work Contract task to an approved route, capability, owner contract, and acceptance ID.
2. Verify the session and implementation authorization gates before touching application source.
3. Establish server/client ownership and generated-client boundary before component code.
4. Implement the smallest vertical customer behavior with pending, failure, and unknown states.
5. Run the narrowest component or browser check immediately after the first substantive edit.
6. Add compact/expanded, light/dark, English/Urdu, keyboard, reduced-motion, offline, and privacy evidence proportional to the slice.
7. Run lint, coverage, production build, multi-browser acceptance, axe, and screenshot review.
8. Submit for independent review; do not approve, merge, or deployment-confirm the same work.

### Technical Competencies

- Next.js 14 App Router, React 18, strict TypeScript, server/client boundaries, route groups, metadata, loading, error, and not-found behavior;
- browser stream consumption, typed event/message parts, cancellation, reconciliation, idempotency, cursor pagination, and stable rendering;
- HTML semantics, tokenized CSS, responsive constraints, safe areas, software keyboards, touch targets, themes, and installed-PWA behavior;
- WCAG 2.1 AA, keyboard operation, focus management, screen readers, live regions, reduced motion, zoom, contrast, and stable accessible names;
- Noto script loading, locale formatting, translation expansion, `dir` ownership, Urdu/Nastaliq, and RTL mirroring;
- Keycloak/NextAuth server sessions, assurance-aware UX, generated OpenAPI clients, cache/privacy boundaries, and C-100 origin discipline;
- Jest, Testing Library, Playwright Chromium/Firefox/WebKit, axe, screenshot diffs, exact 360px checks, coverage, production build, and bundle/performance inspection.

### Knowledge Sources

- WC-specific architecture and acceptance contracts;
- `architecture/reference/ux/constitutional-ux-vocabulary.md`;
- `architecture/reference/ux/hybrid-application-shell.md` and companion contracts;
- accepted ADR-002, ADR-008, ADR-017, and ADR-023 decisions;
- `tests/QA-STRATEGY.md` and repository web tooling;
- official documentation matching the repository-pinned Next.js, React, NextAuth, Jest, and Playwright versions.

External templates are comparative references, not knowledge authorities. Current template code must never override repository-pinned versions or approved WAOOAW boundaries.

### Business and Quality KPI

**Primary KPI:** percentage of authorized frontend slices accepted without architecture-gap rework or constitutional UI regression.

**Measures:**

- 100% task-to-route/API-owner/acceptance traceability;
- zero UI-invented endpoints or browser-owned authorization decisions;
- zero critical axe violations and zero inaccessible Emergency Stop paths;
- zero horizontal-overflow failures at exact 360px;
- zero RTL/Indic clipping regressions in the required matrix;
- at least 90% changed interactive line coverage;
- all required browser, build, privacy/cache, and screenshot gates passing.

## External Template and AI SDK Position

The official Vercel chatbot template is Apache-2.0 licensed and may inform interaction patterns. Its current stack differs from WAOOAW: Next.js 16, React 19, Auth.js 5 beta, AI SDK 7, Tailwind 4, Drizzle/Postgres, and Redis. It is not a compatible scaffold for the accepted Next.js 14/React 18 architecture.

The JQueryScript article is a secondary description of the Vercel template and adds no independent architectural authority.

`@ai-sdk/react` remains optional. A Solution Architect spike may recommend it only if it:

- consumes a WAOOAW-owned typed stream without direct provider calls;
- does not introduce template auth, persistence, ORM, or deployment assumptions;
- supports cancellation, structured parts, reconciliation, accessibility, and testability;
- fits the accepted framework versions and bundle budget;
- preserves AI Runtime, Professional Runtime, Constitutional Engine, and Evidence First ownership.

Otherwise, the existing platform stream contract should be consumed through a small WAOOAW-owned adapter.

## Post-Approval Type 1 Checklist

After Founder APPROVE, the assigned Business Architect and agent-spec author must:

1. Add Skill 16 with all required subsections to the Platform IT Expert specification.
2. Record why no customer-runtime prompt, MCP server, SQL table, or customer capability is introduced, or add each artifact if the approved design requires it.
3. Update the professional template/authorized actions and constitutional checklist.
4. Update README and any skill/capability registers that enumerate 15 skills.
5. Perform a retroactive full Activation Gate audit because the current internal-agent specification predates several mandatory sections.
6. Obtain an independent `CHANGE_TYPE=NEW_SKILL` EA review.
7. Record Founder approval in the agent specification and bump the minor version.

Until all seven steps pass, WC-034 implementation remains blocked even if the skill proposal is approved in principle.
