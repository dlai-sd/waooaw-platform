# WC-138 - CI Validation Speed-Up

## Record Control

| Field | Value |
|---|---|
| Work Contract | WC-138 |
| Authoring office | Platform IT Expert (INST-010), under Founder assignment in the current conversation (lightweight record; the Founder may re-assign the number or office) |
| Initiative | IB-139 |
| Founder assignment | Current conversation: "we are getting slap on face each time we get on this path of coverage and pre check runs or ci merge workflow ... really need to tackle this"; "Yes start with ci speed-up work lane"; "use next available wc number in sequence" |
| Status | IMPLEMENTED - FOUNDER REVIEW PENDING. Evidence is in the PR body at the exact head |
| Baseline | `origin/main` `99cd8471` (WC-136 merged) |
| Related contracts | WC-100 pre-check orchestrator; WC-109 pre-check graph; WC-121 selective validation |
| Requirement ledger | [WC-138-requirements.yaml](./WC-138-requirements.yaml) |
| Standing policy | [CI-VALIDATION-SPEED-POLICY](../standards/CI-VALIDATION-SPEED-POLICY.md) - the rules every later agent follows |
| Constitutional basis | C-059, C-063 |

## Authority And Scope

### In scope

1. The Business Platform test node waits for the same component's format check, so a format failure is found in seconds.
2. Business Platform tests lease reset, pooled PostgreSQL clusters instead of starting one container per test.
3. A pre-check node starts as soon as its own dependencies pass.
4. The standing policy and its routing from the agent entry point.

### Out of scope (separate Work Contracts, each needs Founder authorization)

- Release Qualification Azure-lane parallelisation (`scripts/goal006_activation_readiness.py`) and per-lane runner pulls.
- Hosted-CI carry-forward of PR evidence to the merge commit, and candidate-image promotion instead of rebuild.
- Any lowering of coverage thresholds, gate removal or gate waiver.
- Deployment, approval and merge.

## Canonical Requirement Index

Each row is one normative obligation. The ledger `WC-138-requirements.yaml` binds to this file's complete SHA-256 digest; any edit of this file after the ledger is written requires a new digest.

| ID | Obligation |
|---|---|
| WC138-R001 | The Business Platform test pre-check does not start until the Business Platform format check passes |
| WC138-R002 | Business Platform PostgreSQL tests use leased, pooled clusters; a lease is exclusive and leaks no role, database or table to the next lease, and a cluster that cannot be proven clean is discarded |
| WC138-R003 | No test is lost: the Business Platform test list is identical to `origin/main` apart from the new isolation tests, and the coverage thresholds (90% line, 80% branch) are unchanged and met |
| WC138-R004 | A pre-check node starts when its own dependencies pass, never waiting for unrelated running nodes; a failed prerequisite still prevents its dependents from starting |
| WC138-R005 | The standing speed policy is published and routed from the agent entry point |

## Implementation Record

Evidence at the exact head (commands and results) is in the PR body. Measured: the 55-test reconciliation class 227 s to 38 s test time; the full Business Platform gate with coverage 11-13 min to 2 m 54 s, 3763 tests, line coverage 90.96%, branch coverage 82.15%. Not done by design: fast/container lane split, build-output cache and shared-input narrowing (Business Platform is about 3 minutes now; the gain does not justify the cache-invalidation risk).
