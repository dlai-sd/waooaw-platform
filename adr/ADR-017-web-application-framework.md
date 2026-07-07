# ADR-017: Web Application Framework — Next.js with TypeScript

**Status:** Accepted
**Date:** 2026-07-07
**Roles Applied:** Enterprise Architect (frontend architecture) + Solution Architect (client integration)
**Constitutional Basis:** GENESIS Part 01 — Mobile Strategy (Phase 1: PWA; Phase 2: React Native); AD-009 (Observability by Default — client-side OTel tracing); C-001 (Emergency Stop architecturally guaranteed — requires mobile-accessible, reliable UI)

---

## Context

WAOOAW customers are dental clinic owners between patients, traders monitoring positions, beauty artists between clients. The customer interface must be:
1. **Mobile-first** — phone is the primary device
2. **Emergency Stop accessible** — always one tap away, regardless of connection quality
3. **Evidence-readable** — audit trail must be readable on small screens
4. **Approvable on the go** — approve/reject professional actions from phone without opening a laptop

Phase 1 (MVI): one codebase, no app store submission, immediately usable on any device.
Phase 2: native iOS and Android with shared API contracts.

---

## Decision

**Next.js 14 with TypeScript (strict mode) for Phase 1. React Native for Phase 2.**

The two phases share: API contracts (OpenAPI-generated TypeScript clients), component design system, and authentication model. The Phase 1 PWA investment is not throwaway — it becomes the web presence and the foundation for the React Native app.

### Phase 1 — Next.js PWA

**Why Next.js over alternatives:**
- **App Router + SSR**: Evidence ledger pages are server-rendered for fast initial load and SEO. Customer dashboards are server-side streamed. This is not achievable cleanly in a plain React SPA.
- **PWA support**: `next-pwa` plugin provides Service Worker, offline capability, and home screen installability with minimal configuration. No separate PWA build pipeline.
- **TypeScript first-class**: Next.js is authored in TypeScript. Full static analysis from framework to business logic.
- **OpenAPI client generation**: `openapi-generator-cli` generates typed TypeScript clients from `business-platform.openapi.yaml` — no manual API call code.
- **React Native sharing path**: React (web) → React Native (mobile) is the lowest-friction Phase 2 migration. Shared component logic, shared API client types, shared state management patterns.

**Emergency Stop UI mandate:**
The Emergency Stop button must be:
- Present on every authenticated screen (fixed position, cannot be scrolled away)
- Accessible with one tap on mobile
- Functional with poor connectivity (the WebSocket pre-connects at login; the button sends on the established connection, not via a new HTTP request)
- Visually unambiguous (red, labeled, no confirmation dialog for speed)

### Phase 2 — React Native

React Native selected for Phase 2 because:
- Shared TypeScript codebase with web (business logic, API clients, state management)
- Better camera access for beauty artist content workflows (camera roll, image editing)
- Native push notifications for Emergency Stop alerts
- Native vibration/haptics for trading alerts

---

## Toolchain

| Tool | Purpose |
|---|---|
| `Next.js 14` | Framework (App Router, SSR, PWA) |
| `TypeScript 5.x` (strict) | Type safety |
| `openapi-generator-cli` | TypeScript client from `business-platform.openapi.yaml` — never write API calls by hand |
| `ESLint` + `@typescript-eslint/recommended` | Code quality, no `any` types |
| `Prettier` | Code formatting (enforced in CI) |
| `Jest` + `@testing-library/react` | Unit + component tests |
| `Playwright` | E2E tests (acceptance scenario smoke tests) |
| `next-pwa` | Service Worker, offline support, installable PWA |
| OTel browser SDK | Client-side traces (correlation ID propagated from server) |

---

## Alternatives Considered

| Option | Reason Rejected |
|---|---|
| React SPA (Vite) | No SSR — evidence ledger pages require fast first render. No App Router. PWA requires separate setup. Phase 2 migration path is identical (React → React Native) so no advantage. |
| SvelteKit | Excellent DX but smaller ecosystem. Fewer Indian developers familiar with it. TypeScript support good but not as mature as Next.js. No React Native path for Phase 2 (would require full rewrite). |
| Remix | More complex than needed for MVI. SSR model is good but less battle-tested in India-based teams. No PWA story without significant additional configuration. |
| Flutter | Cross-platform (web + mobile) from one codebase. Rejected: Dart is a third language in the stack. TypeScript API client sharing is not possible. Emergency Stop WebSocket pattern requires custom implementation. |
| Native iOS + Android (Phase 1) | App store approval timelines (2–4 weeks for Apple) incompatible with MVI launch velocity. No value over PWA for MVI customer personas. |

---

## Consequences

**Benefits:**
- One codebase for web Phase 1 and a clear, low-friction path to React Native Phase 2
- TypeScript strict mode catches API contract mismatches at build time
- OpenAPI-generated clients mean REST API changes are immediately visible as type errors in the web build
- SSR evidence ledger pages are fast on mobile data (3G India conditions tested)

**Trade-offs:**
- Next.js App Router has a steeper learning curve than plain React
- PWA limitations on iOS (push notifications require iOS 16.4+; acceptable for MVI customer demographic)
- Two render environments (server + client) require care about what runs where — mitigated by Next.js conventions
