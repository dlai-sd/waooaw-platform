# WC-085 Partial Candidate Evidence

This is a PARTIAL implementation bundle, not the complete WC-085 final release bundle.
Application/configuration freeze: `14a28c18aa8774d8b2f956c475e2e60a245f4ddd`.
Subsequent changes add evidence and repair the mandatory lifecycle gate's PostgreSQL readiness probe.
Base: `79ec8065ad448cb418551034366091693b7b316c`. Office: INST-010.
The final draft PR records the pushed HEAD; these local results do not contain a candidate Demo
revision or immutable exact-six deployment tuple. No full story PASS or provider acceptance is claimed.

## Checks

All executable application/test/build/scanner work ran in Docker. No virtual environment was created.

| Command / Scope | Result |
|---|---|
| `pnpm test -- --runInBand --json --outputFile=/evidence/jest.json` | 41 suites, 229 tests PASS; `jest.json` |
| Auth Jest coverage, collecting AuthBoundary/AuthDialog/AuthJourney/safe-return | 10 suites, 44 tests PASS; 98.5% lines, 94% branches; each changed file exceeds 90% lines |
| `pnpm exec tsc --noEmit` and `pnpm lint` | PASS |
| Focused Playwright command in `browser-matrix.md` | 30/30 PASS, Chromium/Firefox/WebKit across five configured projects |
| `pytest tests/pipeline/test_wc085_google_deployment.py tests/pipeline/test_goal006_*.py tests/identity-foundation/test_identity_artifacts.py -q` | 513 PASS; final registered-origin assertion subsequently passed in the 8-test focused rerun |
| Ruff on new verifier/tests and changed Azure fixture; Bash syntax on three changed/new verification scripts | PASS |
| Terraform 1.9.8 Demo workload `init -backend=false`, `validate`, module `fmt -check` | PASS; no cloud state/provider plan/apply |
| `bash scripts/run_goal006_local_azure_verification.sh` | PASS; synthetic TLS Google redirect plus revision-bound evidence and unhealthy revision failure |
| `bash scripts/run_wc085_google_reconstruction.sh` | PASS twice; actual Terraform-rendered realm, pinned Keycloak, synthetic credentials, TLS Google redirect, new user's customer role and absence of founder role |
| `docker build -f web/Dockerfile -t wc085-web:14a28c18 .` | PASS; `web-build.log` |
| Syft v1.27.1 CycloneDX SBOM | Generated, `sbom.json` |
| Trivy 0.73.0 image scan, `--severity HIGH,CRITICAL --ignore-unfixed --exit-code 1` | PASS, zero matching vulnerabilities; `trivy.json`; not a claim of zero vulnerabilities of every severity |
| Gitleaks v8.28.0, redacted, candidate commit range | PASS, zero leaks; `gitleaks-diff.json` |
| actionlint 1.7.7 on changed deployment-verification workflow | PASS |
| Author diff and editor diagnostics | Checked scope, secret handling, default-role isolation, callback guard, rollback and no private browser endpoint; no diagnostics in checked changed files |
| Mandatory real-container lifecycle gate | Initial local-socket probes exhausted during PostgreSQL initialization; repaired to probe the TCP endpoint from the Docker network. Same pinned images and 503/200/503/200 assertions then PASS. Final pushed-HEAD result is bound in the prepared PR body. |

Web candidate image ID: `sha256:a9dc8fbc4d2575c29c9dbc21635d7b76d8e34635bee93905a10e96727635940d`.

## Test Images

| Image | Local Immutable Identity |
|---|---|
| pr408-test-runner-ts:latest | sha256:c59b212476b4da92ffd9dd502235afa4dc5a733d32ad1e03402bfb80cf426f3c |
| pr408-test-runner-python:latest | sha256:5a833b51dcbb5da88ac473b849ec32656cce0611d731fca361ab7abfe82f3866 |
| mcr.microsoft.com/playwright:v1.62.1-noble | sha256:dcc5531e97840b9b5e794f2814476b21571c5124a3fca2267d73041f56e7580e |
| hashicorp/terraform:1.9.8 | sha256:18f9986038bbaf02cf49db9c09261c778161c51dcc7fb7e355ae8938459428cd |
| Keycloak reconstruction | quay.io/keycloak/keycloak@sha256:82c5b7a110456dbd42b86ea572e728878549954cc8bd03cd65410d75328095d2 |

## Authority And Limits

- The Founder authorized WC-085 implementation and the additional Demo Google reconstruction work. Canonical deployment remains after review/merge; no cloud deployment was performed here.
- The reconstruction script is a test harness using stock Keycloak import, not a custom production importer. It creates no persistent database. Synthetic TLS material is temporary and removed on exit.
- Key Vault values never enter Terraform, source, images or evidence. A separate managed identity receives access to exactly the two Google secrets. Normal deployments retain the registered issuer/callback; a foundation-domain change fails the precondition and needs renewed callback approval.
- Google runtime enablement in this candidate is desired configuration, not accepted readiness. The generated `ReadinessEvidenceReference` names a redirect artifact, not a real-user journey. Legacy manifest parity, private API/UI checks and complete provider journeys remain a merge/activation blocker under SP-03/SP-06.
- Startup import assumes an empty disposable realm. It does not update an existing persistent realm. Persistence and a custom importer were explicitly excluded.
- Provider credential rotation resolves versionless references on fresh deployment; in-place retained pods may require restart. No promise of uninterrupted identity continuity is made for disposable Demo users.
- Rollback: revert auth slice independently; disable/revert Google desired configuration and provider projection together through the reviewed deployment path. Reverting the whole candidate restores the prior empty generated provider list. No real rollback test was performed.
- Known pre-existing output: Next.js CSS autoprefixer warning at the unrelated `align-items:end` rule and jsdom navigation console warnings in AcquisitionController tests. Both commands completed successfully.
- Missing acceptance includes S1 formal owner approvals; real Google/Facebook/email journeys; exact candidate Demo binding; complete zoom/loading/error/portal/browser matrices; public Chrome reproduction; Founder visual acceptance. See all 26 rows in `story-gates.md`.
- The canonical C-059/C-065 PR preparer must pass after final push. Its real-container lifecycle evidence is attached to the PR body separately and does not imply WC-085 completion.