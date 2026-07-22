# Work Contract 016 — IB-009 Sprint 016: Web Portal Skeleton

**Office:** WAOOAW AI Agent — Platform IT Expert (Office 10)
**Sprint:** 016
**Backlog Item:** IB-009 — Foundation Implementation (Gate G5)
**Sprint Track:** Track 6 — Web Portal (PMO §2.1 M7)
**Gate:** G5
**Reviewer:** WAOOAW AI Agent — QA
**Constitutional Basis:** C-001 (Emergency Stop always visible), C-009 (Rights visibility), C-059, C-065, C-071, C-076

**Depends on:** WC-013 complete (BP registration endpoint needed for portal sign-up)
**Parallel with:** WC-014, WC-015 (Web can be built in parallel once BP is live)
**Authorization:** Requires `platform_phase: IMPLEMENTATION`

---

## Sprint Goal

Produce a running Next.js 14 TypeScript PWA for the Web Portal that:
1. Landing page: `web/WAOOAWHome.html` promoted to Next.js App Router (already built as HTML)
2. Registration flow: form → POST `/api/customers` on BP → Keycloak session
3. WaooaW Concierge: 3-exchange conversation stub (no real LLM yet — canned responses)
4. Emergency Stop button: visible on every authenticated page, triggers WS to PR ≤250ms (C-001)
5. Unit test coverage ≥90% (C-076), Accessibility: 0 axe-core violations (C-071)

---

## Required Inputs

| Input | Location | Status |
|---|---|---|
| UX vocabulary | `architecture/reference/ux/constitutional-ux-vocabulary.md` | ✅ EXISTS |
| Portal walkthrough | `architecture/reference/ux/suresh-portal-walkthrough.md` | ✅ EXISTS |
| Landing page HTML | `web/WAOOAWHome.html` | ✅ EXISTS |
| Brand assets | `web/assets/` | ✅ EXISTS |
| biome.json | `web/biome.json` | ✅ EXISTS |
| ADR-008 (Keycloak) | `adr/ADR-008-keycloak-identity-broker.md` | ✅ EXISTS |
| ADR-017 (Next.js) | `adr/ADR-017-web-application-framework.md` | ✅ EXISTS |
| WC-013 (BP running) | `src/business-platform/` | ⏳ PENDING WC-013 |

**Readiness: BLOCKED** — WC-013 must complete first (registration calls BP API)

---

## Tasks

### WC016-01 — Next.js 14 App Router scaffold + landing page

**Scope:** Convert `web/WAOOAWHome.html` to Next.js App Router. Deploy to `web/` service in docker-compose.
**model_hint:** `reasoning`

### WC016-02 — Registration + Auth flow (Keycloak)

**Scope:** Auth modal (already HTML stub) → real Keycloak OAuth flow via `next-auth`. JWT stored in httpOnly cookie.
**model_hint:** `reasoning`
**Constitutional check:** C-009 (rights visibility before hire), ADR-008 (Keycloak as broker).

### WC016-03 — Emergency Stop button (C-001 constitutional requirement)

**Scope:** Persistent button on all authenticated pages. Triggers WebSocket to PR. ≤250ms latency.
**model_hint:** `reasoning`
**Constitutional check:** C-001 — MUST be reachable at all times. Keyboard accessible. No loading state.
**CCT gate:** CCT-HO-03 (UI Emergency Stop ≤250ms)

### WC016-04 — Accessibility audit + unit tests ≥90%

**Scope:** axe-core/playwright on all pages: 0 critical violations. Vitest unit tests.
**model_hint:** `auto`
**Constitutional check:** WCAG 2.1 AA (constitutional UX vocabulary mandate).

---

## Definition of Done

- [ ] `docker compose up web` → Next.js serves at localhost:3000
- [ ] Registration flow works end-to-end with local Keycloak
- [ ] Emergency Stop: ≤250ms P99 (CCT-HO-03 PASS)
- [ ] axe-core: 0 critical violations on all pages
- [ ] Unit tests: ≥90% coverage (C-076)
- [ ] Bundle size: home page JS < 200KB (UX vocabulary mandate)

**Status:** READY when WC-013 completes (parallel with WC-014/015)
