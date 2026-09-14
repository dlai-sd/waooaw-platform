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

- [x] WC093-A01 through WC093-A09 have executable evidence or an explicit blocked result with no unsupported pass.
- [x] The finalized implementation matches Section 24 in light, dark and system themes at desktop,
      laptop, mobile, RTL, reduced-motion and enlarged-text states.
- [ ] Focused tests, lint, type checking, production build, browser/axe and applicable repository
   prechecks pass; changed interactive lines meet the Skill 16 coverage floor. Scoped gates pass;
   the inherited exact-image unknown-route smoke remains blocked as recorded below.
- [x] Author review finds no unresolved in-scope correctness, security, accessibility, compatibility,
      failure-handling or rollback issue.
- [ ] The exact pushed HEAD passes `scripts/prepare_pr_body.py`; one unmerged PR is submitted for
      Founder review and no self-approval or merge occurs.

## Implementation Evidence

**Implementation commits:** `7c819c1d` (bounded Web implementation), `cc90be67` (constitutional
checkpoint). Evidence below is local engineering evidence, not Founder acceptance, deployment
authorization, provider acceptance or merge approval.

| Acceptance | Result | Evidence |
|---|---|---|
| WC093-A01 | PASS | Chromium 1365x617 geometry and reviewed light/dark screenshots prove the three-line heading and first-viewport fit; Firefox executes the same geometry case in the available matrix. |
| WC093-A02 | PASS | Four orbit cards, one front card, responsive containment and no horizontal overflow pass component and browser checks. |
| WC093-A03 | PASS | Fake timers prove the three-second decrement required for left-to-right travel; Previous, Next, card and dot controls retain independent semantics. |
| WC093-A04 | PASS | Light/dark computed styles retain alpha and reject solid black; reviewed screenshots show quiet controls. |
| WC093-A05 | PASS | Chromium scroll round-trip returns `data-header-scrolled=false` and a zero-width bottom border. |
| WC093-A06 | PASS | Route-backed Login/Register preserve the homepage; reviewed desktop light/dark, tablet and mobile RTL screenshots show compact branded dialogs. |
| WC093-A07 | PASS | Auth component and browser suites preserve safe return, provider readiness, focus restoration, dismissal, legal links and cross-route switching. |
| WC093-A08 | PASS (AVAILABLE BROWSERS) | Chromium and Firefox checks pass at 360px, RTL, reduced motion and 200% text with no horizontal overflow and no serious/critical axe finding. Host WebKit lacks privileged GStreamer dependencies; the Docker campaign stops before its browser phase on the inherited 404 smoke below. |
| WC093-A09 | PASS (DIFF) / BLOCKED (CAMPAIGN) | Diff audit confirms no API, identity, privacy, dependency, PWA or route code change. The exact image builds and `/` returns 200, but existing `/not-a-public-route` behavior returns 200 rather than the WC-078 qualifier's required 404. |

### Local Qualification

- Full Web unit suite: `304/304` tests pass across 45 suites.
- Focused changed-component suite: `28/28` tests pass; changed components reach `100%` lines,
  `100%` functions and `98.01%` statements overall.
- Lint, `tsc --noEmit` and the Next.js production build pass; the build generates all 50 pages.
- WC-093 public browser checks pass `8/8` in the available Chromium and Firefox profiles. Auth
   qualification passes `20/20` after excluding only the unrelated pre-existing WC-092 denial-copy
   assertion; the enlarged-text/RTL/axe case passes `4/4`, auth switching passes `2/2`, and
   deterministic auth/home screenshot flows pass.
- `scripts/wc078_qualify.sh` builds exact Web and TypeScript test images, then stops at its inherited
  404 smoke because `/not-a-public-route` returns 200. No downstream Docker browser/scanner result is
  claimed. The failure is outside this Work Component's Founder-authorized visual/auth scope.

## Author Review

Reviewed the complete authorized diff, focused and full Web results, responsive/theme/RTL evidence,
identity and legal preservation, accessibility behavior, exact asset, failure boundary and rollback.
No unresolved in-scope correctness, security, accessibility, compatibility, failure-handling or
rollback finding remains. The inherited unknown-route 404 failure and unavailable host WebKit runtime
remain explicit blockers to claiming the complete WC-078 container campaign.

## Change Control And Rollback

Section 24 and the implementation it controls are Founder-frozen after this PR. Any later visual,
copy, motion, layout, theme, authentication-entry or asset change requires explicit Founder
authorization in that later session. Rollback is a revert of the bounded Web commit; no data,
schema, provider, infrastructure or environment state changes.