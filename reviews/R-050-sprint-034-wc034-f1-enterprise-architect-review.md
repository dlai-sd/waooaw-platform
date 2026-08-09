# R-050 — WC-034 F1 Enterprise Architect Review

| Field | Value |
|---|---|
| `institution_id` | INST-004 |
| `work_contract` | WC-034 Phase B — F1 Experience Foundation |
| `pull_request_reviewed` | PR #246 |
| `record_id` | R-050 |
| `review_type` | Independent implementation review |
| `produced_at` | 2026-08-09 |
| Decision | **REJECT — CHANGES REQUIRED** |

## Scope and Independence

INST-004 independently reviewed PR #246 against WC-034, ADR-017, the hybrid application shell, visual-system contract, UI acceptance contract, and F1 implementation decomposition. This session did not author the implementation, does not review WC-057, does not authorize F2–F8 or deployment, and does not merge the pull request.

The implementation is structurally limited to F1 and preserves the approved Next.js App Router boundary. Server layouts separate public, customer, and Founder surfaces; the Founder layout checks an explicit server-session claim; runtime caching is configured network-only for navigation, API, and non-static requests; and deferred registration and Founder functions are represented honestly as unavailable. The findings below prevent F1 closure.

## Findings

### R050-01 — P0 — The eleven-locale control does not localize the application or load the required script fonts

`web/components/shell/ExperienceControls.tsx` persists a locale cookie and refreshes the route, while `web/lib/preferences.ts` changes only `lang` and `dir`. Shell, navigation, authentication, public, and system-state copy remains hardcoded in English. `web/app/layout.tsx` loads Noto Sans with only the Latin subset and Noto Nastaliq Urdu with the Arabic subset; it does not load the required Noto subsets for Hindi, Marathi, Tamil, Telugu, Kannada, Gujarati, Bengali, Malayalam, or Punjabi.

This fails C-042, the visual-system Typography and Script Contract, `CCT-UX-I18N-01`, and the F1 assignment of `CCT-UX-A11Y-01` through `CCT-UX-MOTION-01`. A locale selector that changes document metadata while customer commands remain English is not localized behavior.

**Required correction:** provide a typed translation source for all F1-owned copy, render translated labels for all eleven declared locales, load the active script's approved Noto subset, and add browser assertions for translated long labels, script rendering, clipping, direction, and 200% zoom. Alternatively, narrow the released locale list through an approved architecture/product amendment; implementation cannot silently reduce the contract.

### R050-02 — P0 — The reported 15/15 browser result does not cover the normative F1 acceptance matrix

`web/tests/e2e/accessibility.spec.ts` defines three scenarios that are repeated across five Playwright projects. It checks the public route, five unauthenticated state routes, and Urdu `lang`/`dir` metadata. It does not execute the required protected customer or Founder authorization paths, every F1 route at 360×800, long labels or 200% zoom, keyboard journeys, focus lifecycle beyond the first skip-link focus, serious axe findings, service-worker cache contents, visual screenshot baselines, or Core Web Vitals and payload budgets. No `toHaveScreenshot` or performance assertion exists under `web/`.

The 15 executions are browser/project multiplication, not evidence that the assigned acceptance IDs pass. Independent Docker execution also cannot reproduce the reported result: all 15 executions fail before launch because the constitutionally mandated test-runner contains no Chromium, Firefox, or WebKit binaries. GitHub currently reports no substantive CI quality check that independently supplies the missing evidence. This fails C-071/C-076 and the UI acceptance contract's release-blocking rules.

**Required correction:** make the repository-standard Docker runner install or provide the pinned Playwright browsers, declare the pnpm version used by the project, and implement and run the F1-assigned acceptance IDs with explicit test-to-ID traceability. At minimum include protected-route and Founder-denial tests, the complete F1 route/viewport matrix, keyboard/focus/RTL/script checks, zero critical plus disposition of serious axe findings, generated-worker cache inspection, route/state screenshots, and measured performance/payload assertions. Report scenario counts separately from browser-project executions.

### R050-03 — P1 — The public migration removes the approved discovery experience without recording migration or explicit content retirement

PR #246 deletes the 738-line Founder-approved `web/WAOOAWHome.html` and replaces it with a 19-line App Router page containing only a hero and safeguard strip. The approved source's professional discovery, journey, trust, and conversion content is neither migrated nor covered by a content-level retirement decision. WC-034 requires existing home-page content to be migrated or explicitly retired, and the visual contract requires recognizable continuity with the Founder-approved public design direction.

**Required correction:** migrate the F1-owned public discovery content into the App Router using the approved visual system, or record an explicit Product/Founder disposition for each omitted content family before deletion. Add public-page visual baselines demonstrating continuity at compact and expanded widths.

### R050-04 — P1 — The persistent Emergency Stop control is disabled by construction and lacks browser-level constitutional evidence

`web/components/shell/AppShell.tsx` renders `EmergencyStop` for every protected shell with `contractId={null}` and `activeSessionIds={[]}`. The component therefore always presents the disabled `No active work to stop` state. The unit test asserts this disabled state, while the browser suite never enters an authenticated professional route or proves visibility, keyboard reachability, 56×56 target size, or Stop placement at required widths. The existing relationship workspace also supplies null/empty Stop inputs, so direct relationship navigation does not disconfirm the issue.

F1 does not authorize a new Stop transport, but it does assign `CCT-UX-HO-01` and requires the existing constitutional control to remain persistently reachable. A permanently disabled shell control is insufficient evidence of that invariant.

**Required correction:** define the approved F1 boundary for deriving active Stop context without inventing F2–F8 data ownership, wire the existing control where context exists, retain an honest no-active-work state where it does not, and add authenticated browser evidence for every F1-owned professional surface at compact and expanded widths. Any missing context contract must be routed upstream rather than compensated for in browser code.

## Acceptance Disposition

| Area | Result | Evidence |
|---|---|---|
| F1 scope boundary | PASS | No registration, conversation transport, Founder operation, voice, attachment, continuity, new API, or deployment implementation introduced |
| Route/layout ownership | PARTIAL | Server layouts and explicit Founder claim exist; protected browser evidence is missing |
| Visual system | PARTIAL | Semantic tokens and WAOOAW logo are present; locale scripts and public-page continuity are incomplete |
| Privacy-safe PWA | PARTIAL | Runtime rules are structurally network-only outside static assets; generated-worker behavior is not covered by an executable acceptance test |
| Constitutional controls | FAIL | Persistent Stop is disabled by construction and `CCT-UX-HO-01` evidence is absent |
| Accessibility/localization | FAIL | Eleven locales are selectable but untranslated; required script, zoom, focus, and serious-axe evidence is absent |
| Responsive/visual/performance evidence | FAIL | Project viewports exist, but required route matrix, screenshots, Core Web Vitals, and payload assertions do not |
| Lint, coverage, and build | PASS WITH TOOLCHAIN NOTE | Docker test-runner: lint clean; Jest 29/29; 98.68% lines; production build 20/20 routes; 89.5 kB shared JS. Reproduction required manually pinning pnpm 9.15.9 because the project declares no package-manager version and Corepack otherwise selects pnpm 11, which is incompatible with the runner's Node 20. |
| Browser execution | FAIL — ENVIRONMENT/EVIDENCE | Docker test-runner: 15/15 executions failed before launch because Chromium, Firefox, and WebKit binaries are absent; GitHub exposes no substantive quality check that supplies independent browser evidence |

## Verdict

**REJECT — CHANGES REQUIRED.**

PR #246 must not merge or close WC-034 F1 until R050-01 through R050-04 are resolved and independently re-reviewed. This verdict does not authorize implementation beyond F1, does not authorize deployment, and does not alter the entry gates for F2–F8.
