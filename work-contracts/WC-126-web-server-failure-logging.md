# Work Contract 126 - Safe Web Server Failure Logging

## Record Control

- Office: Platform IT Expert (INST-010).
- Assigned by: Founder, 2026-10-29, current conversation.
- Authority: Founder approved session implementation, testing, a new PR from main,
  and creation of the next numbered Work Contract.
- Baseline: origin/main at 05cb325c.
- Status: LOCALLY QUALIFIED - exact-head PR preparation and Founder review/merge pending.

## Authority And Scope

Standardize web server failure handling outside sign-in. Cover acquisition,
conversation, identity management, relationships, voice, alerts, offerability,
admin Key Vault, readiness, journey telemetry, Redis and portal projections.
Preserve successful responses, expected validation rejection, authorization,
cache policy and existing failure status semantics except invalid upstream
success-shaped fallbacks, which must fail explicitly.

No sign-in flow changes, Business Platform/.NET changes, new dependencies,
live Azure access, provider mutation, deployment, DNS, expenditure, approval
or merge are authorized. Do not disturb the existing dirty checkout.

## Inputs

- Founder acceptance criteria in the current conversation.
- Existing web routes, library error mappers, tests and Docker validation runner.
- Existing C-059 implementation traceability and C-063 data minimisation boundaries.
- Main has no shared `logServerFailure` or diagnostic-detail flag implementation;
  introduce the shared boundary rather than a parallel logger.

## Requirements And Definition Of Done

| ID | Requirement | Executable evidence |
|---|---|---|
| R1 | Every in-scope server catch logs through `logServerFailure`, directly or through an owning shared error mapper. Invalid-user-input-only rejection stays silent. | AST-based regression gate over server sources and focused migration tests. |
| R2 | Use stable, static event identifiers and a safe correlation ID. Never log raw request/response data, credentials, personal data or bare/minified error names as the only diagnostic. | Logger tests with hostile errors and metadata. |
| R3 | `WAOOAW_DIAGNOSTIC_DETAIL=true` enables bounded, redacted diagnostic detail; false/unset does not. Redaction remains active in both modes. | Both flag values, unset/invalid flag, cause/stack/redaction tests. |
| R4 | In-scope handled 5xx responses include the logged correlation ID; preserve response status and no-store behavior. | Error-mapper and representative route tests, including malformed upstream JSON. |
| R5 | No new silent catch or bare-error-name logging can pass the existing web test gate. Cover catch clauses and promise rejection handlers. | Guard self-tests and existing Jest CI discovery. |
| R6 | Validate the completed change in the existing Docker runner, perform author review, and submit an exact-head PR using the repository template and mandatory preparation gate. | Exact commands/results recorded below and in the PR. |

## Execution Chunks

1. R2-R3: shared server-only structured logger and safe correlation/response helpers.
2. R1/R4: migrate callers and upstream response parsing, preserving input rejection.
3. R5-R6: regression gate, focused tests, impacted Docker web qualification, author
   review and Founder-ready PR.

## Stops And Rollback

Stop for missing approved inputs, architectural ambiguity, conflicting user changes,
unavailable Docker validation, secret requirements, or two reproducible infrastructure
failures. Never weaken validation gates. Rollback is reverting this bounded PR;
there is no database migration or live configuration change.

## Validation And Delivery Evidence

All commands below ran in `waooaw-platform-test-runner-typescript:local`, using the
existing `/opt/waooaw-web/node_modules` dependency installation. No host dependency
installation, provider access or live Azure change occurred.

- `sh /workspace/scripts/validation_control/run_web_test_gate.sh`: PASS.
  TypeScript strict typecheck, ESLint (zero warnings), 107 Jest suites / 689 tests;
  the existing one suite / three skipped tests remain skipped. All configured
  component coverage thresholds pass (91.38% statement coverage).
- `jest --runInBand lib/server-failure.test.ts app/api/server-failure-boundaries.test.ts
  --coverage --collectCoverageFrom=lib/server-failure.ts
  --collectCoverageFrom=lib/server-failure-boundary.ts
  --coverageDirectory=/results/logger-coverage
  --coverageThreshold='{"global":{"lines":90,"branches":80,"functions":90,"statements":90}}'`:
  PASS, 33 tests; 98.71% lines, 98.82% statements, 87.12% branches, 100% functions.
- `biome lint --reporter=github . && biome format .` from `web`: PASS.
  Pre-existing warnings outside the changed failure-handling surfaces remain.
- `next build`: PASS with the existing Dockerfile build environment:
  `BUILD_STANDALONE=true`, `KEYCLOAK_ISSUER=https://build.invalid/realms/waooaw`,
  `KEYCLOAK_EXPECTED_ISSUER=https://build.invalid/realms/waooaw`,
  `WAOOAW_SERVER_SESSION_MODE=enforced`, `NEXT_TELEMETRY_DISABLED=1`.
  An initial build without the required pinned issuer failed closed; using the
  canonical Dockerfile configuration resolved the validation setup failure.
- `git diff --check`: PASS.

Author review repaired three coupled failure-path defects: network TypeErrors
misclassified as portal validation errors; upstream SyntaxErrors misclassified
as malformed user JSON; and an unreadable 5xx body suppressing the owning
mapper's canonical fallback. Regression tests cover these cases, concurrent
correlation isolation, successful SSE pass-through, malformed upstream success,
safe upstream-correlation links and silent malformed-user-input rejection.
The existing Jest gate automatically discovers the AST regression policy;
no separate CI selector or threshold change is required.

## Troubleshooting Contract

Server failure records are single-line JSON on stderr, collected by the existing
Azure container log path. Search `correlationId` from a 5xx JSON body or its
`X-Correlation-ID` header; the same identifier spans nested library failures
within that request. Records include a stable `web.*` event, allowlisted
error type/network code/reason/status, and valid active OTel identifiers.
Safe upstream correlation identifiers link downstream diagnostics without
copying upstream problem details.

`WAOOAW_DIAGNOSTIC_DETAIL=true` enables bounded bundle-file/line/column locations
and a bounded cause chain. False, unset and other values omit that detail.
Both modes redact arbitrary messages, names, source paths, URLs, credentials,
personal data, headers and request/response payloads. Safe exact-message
classification preserves known readiness/Redis/network reasons without
exposing arbitrary error text. This flag is read server-side at runtime;
this delivery does not change deployed environment settings.

Successful responses and SSE streams are passed through unchanged. Handled
5xx statuses, cache headers, retry hints and cookies are retained with a
web-owned correlation identifier. Uncaught server failures return a safe 503.
Malformed request JSON remains a silent 400, distinguished from logged
upstream JSON failures. The optional .NET review was not selected.

Local Docker proof is not Azure deployment acceptance. Founder review and merge
remain required; this Work Contract does not assert hosted-CI or deployment PASS.
