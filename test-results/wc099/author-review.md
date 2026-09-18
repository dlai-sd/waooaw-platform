# WC-099 Implementation Author Review

Status: **BLOCKED, NOT COMPLETE**

The implementation diff was reviewed against WC-099 Sections 5 through 14 and R-001 through R-023. It stays within the authorized Web, Business Platform, Demo readiness and Terraform surfaces. No API shape, schema migration, durable disclosure record, new service, identity model, relationship aggregate or conversation protocol was introduced.

## Verified Local Evidence

- Web unit/coverage: 63 suites, 381 tests passed; aggregate statements 90.01%, branches 79.9%.
- Business Platform: 793 tests passed in Docker with Testcontainers and the Docker socket mounted.
- Environment readiness: 20 tests passed in Docker; missing/short cursor key and canonical secret wiring are covered.
- WC-099 Playwright: 12 passed, 8 intentional project skips across Chromium, Firefox and WebKit. Required desktop widths, 360x800, 390x844, disclosure/no-handoff, RTL, dark theme, axe, focus containment/restoration, keyboard/pointer resize, Guide persistence, typography and Emergency Stop reachability are directly asserted.
- Lint, TypeScript and Next.js production build passed. No OpenAPI/generated-client drift check applies because no public contract changed.
- No migration or schema file changed.

## Findings

1. **Blocker: R-014 and R-020 cannot pass at this candidate.** Read-only Azure inspection shows active Demo Web revision `ca-demo-web--0000045` at image digest `sha256:10c380...`; Business Platform is `ca-demo-business-platform--0000040` at `sha256:8d5271...`. Neither contains the uncommitted implementation. Deployment mutation was not authorized, so an exact-candidate Demo journey was not executed.
2. **R-021 remains `FOUNDER-DEFERRED-NOT-APPLICABLE-TO-DEMO`.** It is mandatory before UAT or Production traffic.
3. **R-007 remains partial.** Local projection behavior is exercised, but the exact Trial and Hire no-refresh browser journey has not run against the integrated candidate.
4. **The pre-existing F1/WC-096 aggregate is not clean.** A serial Chromium run produced seven failures in public baseline/performance/routing and a duplicate transition-tree locator. The reviewed public screenshot was coherent and outside the WC-099 authenticated-shell boundary, so baselines were not rewritten and unrelated tests were not weakened.
5. **The first broad .NET run was invalid, not evidence.** It omitted `/var/run/docker.sock`, causing 107 Testcontainers failures. The corrected repository-standard Docker-on-worktree run passed 793/793 and supersedes it.

## Normative Review Disposition

- Identity/disclosure clauses: implemented locally; active-Demo proof pending.
- Stable shell/account/typography clauses: implemented and directly browser-tested locally.
- Compact/mobile and Guide workspace clauses: implemented and directly browser-tested locally.
- Data/persistence clauses: no new authority or schema; cursor rotation and presentation-state boundaries tested locally.
- Security/privacy/failure clauses: bounded telemetry fields, no token/PII/query logging, fail-closed key validation, focus behavior and no-handoff cancel are tested locally.
- Qualification/DoD clauses: not satisfied because exact-candidate Demo deployment/journey and a clean affected legacy browser aggregate are absent.
- Rollback/post-deployment clauses: repository changes remain independently deployable by Web, Business Platform and Demo configuration; no deployment or rollback was performed.

Author Review Result: **BLOCKED**. Do not label WC-099 complete, approve, merge, or promote to UAT/Production from this evidence.