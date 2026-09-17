# WC-098 Qualification Evidence

**Qualified product commit:** `b9f738e153456f05fbd6e00e8525fcb8600c2d60`
**Baseline:** `c0d24a09`
**Environment:** local Docker on Ubuntu 24.04; no Python virtual environment
**Result:** LOCAL ENGINEERING PASS

## Requirement Evidence

| Requirement | Evidence | Result |
|---|---|---|
| WC098-D01 | Full Web tests cover dark default, legacy `system` fallback, dark/light controls and strict settings/onboard writes. | PASS |
| WC098-D02 | Registration component tests and BP adapter/PostgreSQL tests cover masked broker email, provider source and unverified-email verification. | PASS |
| WC098-D03 | Full BP suite includes production-shaped PostgreSQL HTTP registration journeys using one issuer-and-subject actor. | PASS |
| WC098-D04 | Component and Chromium tests show SMS optional and disabled while completion remains enabled. | PASS |
| WC098-D05 | Route/component tests preserve approved code/status/correlation ID, exclude detail, restart inaccessible registration and resend expired email challenge. | PASS |
| WC098-D06 | Identity API tests prove recovery on the bounded second projection attempt; provider component tests prove actionable retry after fail-closed fallback. | PASS |
| WC098-D07 | Chromium at 360x800 and 1440x900: one title, no horizontal overflow, truthful controls and zero serious/critical axe findings. | PASS |
| WC098-D08 | Docker Web/BP/OpenAPI/security and diff gates below. | PASS |
| WC098-D09 | Requires one exact Demo deployment, Azure correlation and Founder acceptance. No cloud mutation or deployment was authorized or performed. | NOT CLAIMED |

## Executable Qualification

| Gate | Result |
|---|---|
| Business Platform full Docker suite | 734 passed, 0 failed, 0 skipped; includes real PostgreSQL Testcontainers journeys. |
| Web full Docker suite | 58 suites, 361 tests passed; production Next.js build, ESLint with zero warnings and TypeScript `--noEmit` passed. |
| Focused registration suite | 73 route/component tests passed before full qualification. |
| Chromium acceptance | 8 passed across `chromium-compact-360` and `chromium-expanded`; WC098-D04/D07 passed in both projects. |
| OpenAPI generator validation | Valid; two existing unused-model recommendations. |
| Spectral 6.15.0 | 0 errors, 71 existing warnings. |
| Generated client | Regeneration produced only the expected removal of `SYSTEM` from two write enums; normalized generated client is committed. |
| Production dependency audit | `pnpm audit --prod --audit-level high`: no known vulnerabilities. |
| Production image scan | Trivy 0.67.2, fixed HIGH/CRITICAL: zero findings. |
| Diff hygiene | `git diff --check origin/main...HEAD`: pass at qualified product commit. No dependency manifest changed. |

The first full BP invocation incorrectly used `--no-restore` with an empty ephemeral NuGet cache and stopped before repository compilation with missing analyzer metadata. The canonical container command was rerun with restore enabled and passed all 734 tests.

## Immutable Artifacts

| Artifact | Identifier |
|---|---|
| Production Web image | `sha256:322636cc8d254f438460b8cd44015c844459e6effd9c3fceafe01c91d7412ce8`; configured user `waooaw` |
| 360x800 registration capture | `registration-chromium-compact-360.png`; SHA-256 `c28e895007e7365d6c5fa9b6c709b7a723295f9ec349c79475b4b7d6c8b4f9db` |
| 1440x900 registration capture | `registration-chromium-expanded.png`; SHA-256 `bfab530363c54250ec0dc1d40753cca2ff56507920ae3384a19f2e012d8c59a6` |

## Limits

This evidence proves local source, exact-image and fixture-browser behavior. It does not prove a Demo revision, real Google/Facebook account acceptance, SMS delivery, UAT, Production, customer traffic, Founder approval or merge. SMS vendor selection, India delivery budget, cloud mutation and deployment remain outside WC-098 authority.