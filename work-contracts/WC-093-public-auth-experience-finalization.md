# WC-093 - Public And Authentication Experience Finalization

**Office:** Platform IT Expert (INST-010), Skills 2-7, 11 and 16
**Assigned by:** Founder instruction, 2026-09-14
**Status:** IMPLEMENTATION AUTHORIZED FOR CURRENT SESSION; FUTURE VISUAL CHANGE REQUIRES FOUNDER AUTHORIZATION
**Delivery unit:** One bounded Web Application PR
**Controlling specification:** `architecture/reference/ux/wc-078-visual-experience-implementation-plan.md` Section 24
**Preserved contracts:** WC-078 public acquisition behavior; WC-083 and WC-092 route-backed identity behavior
**Constitutional basis:** C-042, C-049, C-059, C-063, C-065, C-071, C-076 and C-095; ADR-017

## Authority And Scope

The Founder approved the disposable prototype reviewed in the 2026-09-14 working session and
authorized Platform IT Expert to create this Work Component, carry the approved presentation into
the existing Next.js Web Application source, add focused tests, collect proportional local evidence,
and submit one unmerged PR for Founder review.

Authorized changes are limited to:

1. finalize the public hero background, laptop-height fit, three-line expanded heading, and stable
   light/dark/system presentation;
2. replace the hero film-strip presentation with the approved four-professional orbit card
   presentation, including its scale, placement, left-to-right autoplay and quiet theme-aware controls;
3. use the approved WAOOAW logo asset in the public header and authentication entry presentation;
4. prevent a stale colored sticky-header edge after scrolling;
5. finalize Login and Register as compact, branded, theme-complete route-backed dialogs over the
   originating homepage while preserving direct routes, provider readiness, legal links, safe return,
   focus, dismissal and registration behavior;
6. add focused component/browser/accessibility tests and run the repository's applicable Web gates.

No new platform component is introduced. C-095 is satisfied by the existing Web Application under
ADR-017. Its source root is `web/`; duplicating Next.js code under repository-root `src/` would violate
the approved component boundary and is prohibited. This Work Component does not authorize identity,
API, provider, dependency, database, infrastructure, deployment, DNS, customer-traffic, Production,
approval or merge changes.

## Required Inputs

| Input | Required state | Session result |
|---|---|---|
| WC-078 public acquisition contract | Existing implemented Web boundary | PRESENT |
| WC-078 visual implementation plan Section 24 | Founder-approved WC-093 revision | PRESENT |
| WC-083/WC-092 authentication contracts | Route and identity behavior preserved | PRESENT |
| Founder-reviewed disposable prototype | Light/dark, desktop/mobile and interaction states accepted | PRESENT |
| Skill 16 and implementation authority | Active and explicit for this session | PRESENT |
| Provider/cloud/deployment authority | Separately required | ABSENT; EXCLUDED |

## Acceptance Matrix

| ID | Required behavior | Executable proof |
|---|---|---|
| WC093-A01 | Expanded hero heading renders in the approved three lines and the full hero fits common laptop heights | Chromium/Firefox/WebKit geometry and screenshots at 1365x617 and 1365x720 |
| WC093-A02 | Four approved professional cards orbit without overlap or horizontal overflow | Component tests and browser geometry |
| WC093-A03 | Autoplay moves left-to-right every three seconds; Previous/Next and dots remain semantic | Fake-timer component tests and browser transition check |
| WC093-A04 | Orbit controls are translucent and theme-aware, never solid black | Light/dark computed-style and screenshot checks |
| WC093-A05 | Sticky header returns to its top state without a persistent colored edge | Scroll round-trip browser and raster check |
| WC093-A06 | Login and Register retain the homepage and render compact branded dialogs in light/dark/system | Route-backed browser matrix and screenshots |
| WC093-A07 | Login/Register preserve providers, unavailable states, safe return, dismissal, focus, legal and cross-route links | Existing and focused auth tests |
| WC093-A08 | Exact 360px, 200% text, reduced motion, keyboard, RTL and supported-theme states do not clip or overlap | Playwright/axe acceptance matrix |
| WC093-A09 | No API, identity, privacy, dependency, PWA or public-route contract changes occur | Diff review, build and privacy/cache checks |

## Stops

Stop rather than proceed if implementation requires a new dependency, API or identity behavior;
provider/cloud/deployment mutation; removal or weakening of legal, accessibility, privacy, safe-return,
failure or reduced-motion behavior; unsupported claims; or code outside the existing Web component.
Do not infer Founder acceptance of implementation, deployment authorization, PR approval or merge.

## Definition Of Done

- [ ] WC093-A01 through WC093-A09 have executable evidence with no unsupported pass.
- [ ] The finalized implementation matches Section 24 in light, dark and system themes at desktop,
      laptop, mobile, RTL, reduced-motion and enlarged-text states.
- [ ] Focused tests, lint, type checking, production build, browser/axe and applicable repository
      prechecks pass; changed interactive lines meet the Skill 16 coverage floor.
- [ ] Author review finds no unresolved correctness, security, accessibility, compatibility,
      failure-handling or rollback issue.
- [ ] The exact pushed HEAD passes `scripts/prepare_pr_body.py`; one unmerged PR is submitted for
      Founder review and no self-approval or merge occurs.

## Change Control And Rollback

Section 24 and the implementation it controls are Founder-frozen after this PR. Any later visual,
copy, motion, layout, theme, authentication-entry or asset change requires explicit Founder
authorization in that later session. Rollback is a revert of the bounded Web commit; no data,
schema, provider, infrastructure or environment state changes.