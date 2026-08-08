# Work Contract 034 — WAOOAW Hybrid Web Application Shell

**Goal:** GOAL-005 — Agent Employment Experience Program
**Backlog Item:** IB-014 — Customer Self-Service Portal
**Gate:** G5 CLEAR
**Architecture Office:** Enterprise Architect (INST-004)
**Implementation Office:** Platform IT Expert (INST-010)
**Architecture Reviewer:** Solution Architect (INST-005) + Product Owner (INST-011)
**Implementation Reviewer:** Enterprise Architect (INST-004) in an independent session
**Status:** ARCHITECTURE AMENDMENT AUTHORIZED — IMPLEMENTATION UNAUTHORIZED
**Authorization:** Founder selected the WC-034 scope amendment on 2026-08-08. This authorizes architecture and specification work only. A separate Founder Action is required before modifying application source.
**Constitutional Basis:** C-001, C-009, C-023, C-034, C-042, C-059, C-064, C-065, C-076; ADR-017

## Outcome

Define one coherent WAOOAW web application that preserves the existing public home-page direction and introduces a reusable authenticated application layout. The product remains a Next.js App Router PWA with hybrid server and client rendering; "hybrid SPA" does not authorize a client-only React application or a second frontend stack.

The architecture must make the transition from public discovery to authenticated employment feel continuous while preserving different navigation, density, and constitutional controls for public, customer, and Founder surfaces.

## Scope Boundary

### Phase A — Architecture and UI/UX Specification (INST-004)

Phase A defines the route topology, shell ownership, responsive layout, constitutional control placement, rendering boundaries, design-token migration, and acceptance contract. It may update architecture, UX specifications, this Work Contract, and review evidence. It must not modify `web/app/`, generate build output, or implement APIs.

### Phase B — Application Implementation (INST-010)

Phase B may begin only after Phase A receives independent architecture review and a separate Founder implementation authorization. It implements the approved shell, migrates the home page into Next.js, and places customer and Founder routes inside their approved layouts.

Founder admin capabilities remain part of WC-034, but they are not the application architecture. Markup Designer, Trial Budget Config, and Coupon Manager are feature routes nested inside the Founder surface after the shared shell exists.

## Required Surface Model

| Surface | Route group | Primary layout | Constitutional controls |
|---|---|---|---|
| Public | `(public)` | Brand navigation, responsive content canvas, footer, optional Concierge | Honest capability and limitation disclosure; no authenticated data |
| Customer | `(authenticated)` | Compact app header, desktop side navigation, mobile bottom navigation, relationship workspace | Persistent Emergency Stop; rights and lifecycle state; tenant-safe identity |
| Founder | `(founder)` | Customer shell primitives with denser administration navigation | `founder=true` authorization; no customer-facing discovery language |
| Shared system | global | Loading, empty, error, offline, forbidden, and not-found states | Fail-safe messaging; no fabricated success; correlation support |

The shell must use role-aware route composition rather than runtime CSS hiding. Unauthorized Founder routes redirect to `/403`. Public pages must not load authenticated application data. Customer and Founder navigation must remain usable at 360px without horizontal overflow.

## Architecture Tasks

| Task | Scope | Owner | Status |
|---|---|---|---|
| WC034-A01 | Inventory `web/WAOOAWHome.html`, the current Next.js root/authenticated routes, WC-057 provisional workspace, and approved UX vocabulary. Record reuse, migration, and retirement decisions without changing source. | INST-004 | pending |
| WC034-A02 | Produce the hybrid application-shell specification: route groups, nested layouts, navigation model, responsive breakpoints, role/claim boundaries, server/client component rules, loading/error/offline states, and persistent constitutional controls. | INST-004 | pending |
| WC034-A03 | Produce the visual-system contract that maps the home-page prototype into shared tokens, typography, spacing, iconography, focus, motion, RTL, and accessibility rules. Resolve conflicts between the prototype and approved constitutional UX vocabulary explicitly. | INST-004 | pending |
| WC034-A04 | Define page-level information architecture for public Home/Professionals/Blogs, customer Home/My Professionals/Relationship/Settings/Profile, and Founder administration. Activity evidence remains relationship-contextual rather than a generic top-level feed unless separately approved. | INST-004 | pending |
| WC034-A05 | Define generated-client and API-boundary rules. Identify missing OpenAPI operations as specification gaps; WC-034 implementation may not create undocumented BP or WBE endpoints. | INST-004 + INST-005 | pending |
| WC034-A06 | Define executable acceptance evidence: desktop and exact 360px layouts, keyboard navigation, RTL integrity, reduced motion, installability, no overflow, zero critical axe violations, and changed-line coverage at or above 90%. | INST-004 | pending |
| WC034-A07 | Submit the architecture package for independent INST-005 and INST-011 review. Record all unresolved product choices instead of embedding them in implementation tasks. | INST-004 | pending |

## Implementation Tasks — Gated

| Task | Scope | Owner | Status |
|---|---|---|---|
| WC034-I01 | Create approved route groups and shared layouts; migrate the public home page from static HTML into the approved Next.js public surface without maintaining two production home pages. | INST-010 | blocked — implementation authorization required |
| WC034-I02 | Implement customer navigation and shared application states around the WC-057 relationship workspace. Preserve the persistent honest Emergency Stop boundary. | INST-010 | blocked — implementation authorization required |
| WC034-I03 | Implement the Founder layout and Founder-only authorization boundary. | INST-010 | blocked — implementation authorization required |
| WC034-I04 | Implement Markup Designer, Trial Budget Config, and Coupon Manager only against approved OpenAPI operations and generated clients. Missing APIs return to their owning service Work Contract. | INST-010 | blocked — implementation authorization required |
| WC034-I05 | Add component, accessibility, route-authorization, responsive, RTL, PWA, and browser acceptance tests required by WC034-A06. | INST-010 | blocked — implementation authorization required |

## Required Inputs

| Input | Status |
|---|---|
| `web/WAOOAWHome.html` — existing public home-page template | present — design input, not automatically normative |
| `web/app/` — WC-057 provisional Next.js PWA and relationship workspace | present — implementation baseline |
| `architecture/reference/ux/constitutional-ux-vocabulary.md` | approved — normative vocabulary and public navigation input |
| `architecture/reference/ux/suresh-portal-walkthrough.md` | approved input with open items requiring reconciliation |
| `architecture/reference/api-specs/business-platform.openapi.yaml` | present — canonical BP API source |
| `architecture/reference/billing/customer-acquisition-spec.md` | present — Founder tooling and acquisition input |
| ADR-017 — Next.js 14 TypeScript PWA | accepted — framework boundary fixed |
| WC-057 — Employment Relationship foundation | merged to `main`; independent review evidence remains unresolved |
| WC-027 and WC-031 — WBE markup/trial/promotions contracts | required before Founder feature implementation |

## Architecture Definition of Done

- [ ] One reviewed application-shell specification defines all four surfaces and route ownership.
- [ ] Public-to-authenticated continuity is explicit; no duplicate production home-page implementation remains in the target state.
- [ ] Desktop, tablet, 360px mobile, RTL, keyboard, reduced-motion, offline, loading, empty, error, and forbidden behavior are specified.
- [ ] Emergency Stop placement and behavior remain consistent with C-001 and ADR-017.
- [ ] Every screen family maps to an approved capability and API owner; no UI-invented endpoint remains.
- [ ] Founder feature routes remain subordinate to the shared shell and are separately authorization-gated.
- [ ] INST-005 and INST-011 review the architecture package before implementation authorization is requested.

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
