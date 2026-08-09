# R-051 — WC-034 F1 Enterprise Architect Re-review

| Field | Value |
|---|---|
| `institution_id` | INST-004 |
| `work_contract` | WC-034 Phase B — F1 Experience Foundation |
| `pull_request_reviewed` | PR #246 |
| `commits_reviewed` | `407745c`, `9227d22` |
| `prior_review` | R-050 |
| `record_id` | R-051 |
| `review_type` | Independent remediation re-review |
| `produced_at` | 2026-08-09 |
| Decision | **CHANGES REQUIRED** |

## Scope and Independence

INST-004 independently re-reviewed only WC-034 Phase B F1 and the remediation for R050-01 through R050-04. This review does not assess WC-057 or F2–F8, authorize deployment, or merge PR #246. The reviewer did not author commits `407745c` or `9227d22`.

## Finding Validation

| Prior finding | Result | Evidence |
|---|---|---|
| R050-01 — localization and fonts | **RESOLVED** | Typed catalogs cover all eleven declared locales; F1 routes consume request-localized messages; script-specific Noto font variables and locale selectors are present; catalog parity, script-family, RTL, and 200% reflow checks are included. |
| R050-02 — reproducible browser evidence | **PARTIAL — OPEN** | The pinned Docker runner, five Playwright projects, protected-route fixtures, axe checks, worker inspection, screenshots, and payload assertions materially improve reproducibility. The test labeled `UX-PERF-01` measures FCP only; it does not measure or assert the contract's required LCP, CLS, or INP thresholds. The normative performance acceptance ID therefore is not proven. |
| R050-03 — homepage content preservation | **RESOLVED** | The App Router home now restores the F1-owned journey, professional categories, trust journey, and constitutional promise, with compact and expanded reviewed baselines. One production `/` entry remains. |
| R050-04 — honest Emergency Stop context | **PARTIAL — OPEN** | `ProtectedAppShell` now accepts an explicit `StopContext` and preserves an honest disabled fallback. However, every production `ProtectedAppShell` call omits `stopContext`; only a unit fixture supplies active values. The browser suite proves visibility and size only for the disabled `No active work to stop` state and never proves an enabled, keyboard-operable Stop on an authenticated professional route. `CCT-UX-HO-01` remains unproven. |

## Open Findings

### R051-01 — P0 — UX-PERF-01 is asserted without its required measurements

`web/tests/e2e/f1-acceptance.spec.ts` records FCP, initial JavaScript, public payload, and loaded-font count. The WC-034 acceptance contract requires FCP, LCP, CLS, and INP thresholds for `UX-PERF-01`. No LCP, CLS, or INP observation or threshold assertion exists, so the test name overstates the evidence and the release-blocking performance gate remains incomplete.

**Required correction:** collect deterministic LCP, CLS, and INP evidence under the approved Chromium performance profile and assert the normative thresholds, or obtain an approved acceptance-contract amendment that narrows F1 performance evidence. Keep normalized profile skips distinct from failures and from passed measurements.

### R051-02 — P0 — Active Emergency Stop remains fixture-only

`ProtectedAppShell` has a sound optional context boundary, but neither the authenticated layout nor the Founder layout supplies it. Repository-wide usages show active `StopContext` only in `F1Shell.test.tsx`. The browser acceptance test signs in to `/home` and explicitly expects the Stop button to be disabled. It does not exercise an authenticated route with approved active contract/session context, and it does not prove enabled keyboard operation at compact and expanded widths.

This does not satisfy the R050-04 correction or `CCT-UX-HO-01`. Dependency injection without a production ownership path is not evidence that human override remains reachable when active work exists.

**Required correction:** connect the approved existing relationship/session context to the protected shell where that context already exists, without inventing F2–F8 ownership, and add authenticated browser evidence that the enabled Stop is visible, at least 56×56, keyboard operable, and unobscured at 360×800 and 1440×900. Preserve the honest disabled fallback when no active work exists.

## WC-034 F1 Acceptance Disposition

| Area | Result |
|---|---|
| F1 scope boundary and explicit deferrals | PASS |
| Route groups and server-owned authorization | PASS |
| Eleven-locale/script foundation | PASS |
| Public homepage migration and continuity | PASS |
| PWA static-only cache boundary | PASS |
| Responsive, visual, axe, and coverage evidence | PASS |
| UX-PERF-01 | FAIL — LCP, CLS, and INP evidence absent |
| CCT-UX-HO-01 | FAIL — enabled Stop remains fixture-only |

## Independent Validation

Executed through the constitutionally required Docker test runner on commit `9227d22`:

- Playwright/axe: 36 passed, 4 expected normalized-performance skips across five projects.
- Jest: 34 passed; 98.64% line coverage.
- Next.js lint: no warnings or errors.
- Production build and strict TypeScript: passed; 20/20 routes generated; public `/` at 89.7 kB First Load JS.
- `git diff --check`: passed.

These successful commands establish reproducibility of the checks that exist. They do not supply the omitted LCP/CLS/INP observations or an enabled production-path Stop scenario.

## Decision

**CHANGES REQUIRED.**

Commits `407745c` and `9227d22` resolve R050-01 and R050-03 but do not fully resolve R050-02 or R050-04. PR #246 must not merge or close WC-034 F1 until R051-01 and R051-02 are corrected and independently confirmed. This decision does not authorize F2–F8, deployment, or merge.
