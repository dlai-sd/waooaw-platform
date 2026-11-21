# CI Validation Speed Policy

**Status:** Standing policy, introduced by IB-139. Founder-directed: CI and pre-commit runs must not be slow because of avoidable repeated work, and agents must not invent a new approach each time.
**Applies to:** every office and agent that adds or changes tests, validation gates, pre-checks or the CI workflow.
**Authority:** this standard records decisions; it grants no deployment, merge or gate-waiver authority. Lowering a gate threshold or skipping a gate needs a Work Contract and Founder authorization.

## 1. Rules

| Rule | Detail |
|---|---|
| V1 | Cheap checks gate expensive ones. A node that runs a full test suite depends on the same component's format, lint and build check (`PRECHECK_DEPENDENCIES` in `scripts/prepare_pr_body.py`). Add the dependency when you add a test node. |
| V2 | A Postgres-backed Business Platform test never starts its own container. Use `new PostgreSqlBuilder(image)...Build()`: in the test project this resolves to `PooledPostgresBuilder` (`tests/business-platform.Tests/PooledPostgres.cs`), which leases an exclusive, reset cluster from a process-wide pool and gives each lease its own database and roles. |
| V3 | A test that must start a real container (for example init scripts mounted at start-up) names `Testcontainers.PostgreSql.PostgreSqlBuilder` explicitly. Keep these few. |
| V4 | A lease is exclusive. Never share one cluster between concurrently running tests, and never weaken the reset in `PostgresCluster.ReleaseAsync`: a cluster that cannot be proven clean is discarded, not reused. |
| V5 | Tests do not need durability. Pooled clusters use an in-memory data directory with `fsync` off. Do not do this for anything that is not a throwaway test database. |
| V6 | Reuse only evidence that is keyed by the exact inputs: gate id, input digest, runner image digest and graph version. Never reuse a result by branch name or by time. Gates marked `reusable: false` (for example dependency scans, whose result changes with the vulnerability database) always re-run. |
| V7 | The full suite and the coverage gate (90% line, 80% branch) stay authoritative on merge to `main` and on the nightly run. A faster path may select tests on a PR; it may not lower the thresholds. |

## 2. Where things live

| Concern | Location |
|---|---|
| Pre-check graph and dependencies | `scripts/prepare_pr_body.py`, `scripts/precheck_orchestrator.py` |
| Gate catalog, inputs, reuse flags | `validation/engineering-validation.yaml` |
| Pooled Postgres for tests | `tests/business-platform.Tests/PooledPostgres.cs`, `PooledPostgresAliases.cs`, `PooledPostgresIsolationTests.cs` |

## 3. Measured effect (IB-139)

| Item | Before | After |
|---|---|---|
| `ConversationReconciliationPostgresTests` (55 tests) | 227 s test time, 305 s wall | 38 s test time, 41 s wall |
| Full Business Platform gate with coverage | 11–13 min | 2 m 54 s |
| Format failure before the Business Platform tests | found after about 13 min | found in seconds |
