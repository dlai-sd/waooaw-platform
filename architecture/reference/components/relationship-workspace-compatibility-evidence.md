# WC-034 F4 Relationship Workspace Executable Compatibility Evidence

## Amendment 5 Order 3 Acceptance Record

| Field | Value |
|---|---|
| institution_id | INST-010 |
| goal_id | GOAL-005 |
| acceptance_id | ACC-GOAL-005-INST-010-03 |
| authorization_id | GOA-GOAL-005-INST-010-03 |
| authorization_issued_at | 2026-08-11T02:43:06+00:00 |
| accepted_at | 2026-08-11T02:45:25+00:00 |
| acceptance_validity | VALID - accepted_at is strictly later than issuance |
| decision | ACCEPT |

## G-10 Contribution Record

| Attestation field | Value |
|---|---|
| institution_id | INST-010 |
| goal_id | GOAL-005 |
| record_id | CR-GOAL-005-INST-010-03 |
| record_type | Contribution Record |
| produced_at | 2026-08-11T02:45:25+00:00 |
| authorization_id | GOA-GOAL-005-INST-010-03 |
| acceptance_id | ACC-GOAL-005-INST-010-03 |
| contribution_scope | Additive repair of pre-existing unresolved BP component references plus Docker-only deterministic G-F4-10 executable compatibility evidence from canonical ancestry commit `9b126bd`; no production client or service implementation changes |
| fixed_inputs | BP 1.3.0 repaired hash `f5b2835d81ce665add57b32fdc6b0f3422b30b61fa137caebdce15638e8de94c`; compatibility spec `CR-GOAL-005-INST-005-09`; owner attestation `CR-GOAL-005-INST-005-13`; R-069 conditions 1-3 |
| authority_boundary | BP contract dependency closure, evidence tooling, focused tests, and temporary generated output under ignored paths. No src/web feature implementation, deployment, provider activation, or F5-F8 work. |

## Learning Record

| Field | Value |
|---|---|
| institution_id | INST-010 |
| goal_id | GOAL-005 |
| record_id | LR-GOAL-005-INST-010-01 |
| record_type | Learning Record |
| produced_at | 2026-08-11T02:45:25+00:00 |
| constitutional_discovery | no |
| evolution_triggered | no |
| improvement_signal | Deterministic OpenAPI slice extraction plus dual-run normalized hashing catches generator drift early and proves no-manual-patch compatibility before any implementation authority is exercised. |

## Run Evidence

### Commands Executed (Docker-only)

1. `docker run --rm -v "$PWD:/local" openapitools/openapi-generator-cli:v7.17.0 validate -i /local/architecture/reference/api-specs/business-platform.openapi.yaml`
2. `docker compose --profile test-python run --rm --no-deps test-runner-python python3 scripts/openapi_slice.py --input architecture/reference/api-specs/business-platform.openapi.yaml --output web/test-results/wc034-f4-evidence/relationship-workspace.slice.yaml --tag "Relationship Workspace"`
3. Two independent clean `typescript-fetch` generations with `supportsES6=true,typescriptThreePlus=true,useSingleRequestParameter=true,hideGenerationTimestamp=true`, `TZ=UTC`, and `LC_ALL=C.UTF-8`
4. `docker compose --profile test-python run --rm --no-deps test-runner-python python3 scripts/wc034_f4_compatibility_validation.py ...`
5. `docker compose --profile test run --rm --no-deps test-runner sh -lc 'cd /workspace/web && pnpm exec tsc --strict --noEmit --skipLibCheck false ... generated-run-a/index.ts generated-run-b/index.ts'`
6. `docker compose --profile test-python run --rm --no-deps test-runner-python python3 -m pytest tests/constitutional/test_wc034_f4_compatibility_contract.py -q --tb=short`

Generator identity was established before this resumed run with:

1. `docker pull openapitools/openapi-generator-cli:v7.17.0`
2. `docker image inspect openapitools/openapi-generator-cli:v7.17.0 --format '{{index .RepoDigests 0}}'`
3. `docker run --rm --user "$(id -u):$(id -g)" --volume "$PWD:/local" openapitools/openapi-generator-cli:v7.17.0 version`

### Captured Results

- `accepted_at`: `2026-08-11T02:45:25+00:00`
- Canonical commit ancestry check: `git merge-base --is-ancestor 9b126bd HEAD` => PASS
- Execution base commit: `fd115577d588cc0f5fc0aae61f53571e0f7f22a9`
- BP 1.3.0 repaired hash: `f5b2835d81ce665add57b32fdc6b0f3422b30b61fa137caebdce15638e8de94c`
- F4 dependency-closed slice hash: `d68c7fbb1d50ab15ac2e16ca4b4b50900e95ae803ba5e488a8cbd3a7bc791dda`
- Canonical OpenAPI Generator validation: PASS; two non-blocking pre-existing unused-model recommendations (`DecisionSpace`, `FormEmploymentContractRequest`)
- Generator version: `7.17.0`
- Generator image digest: `openapitools/openapi-generator-cli@sha256:868b97eb4e5080d2cdfd5b3eeaa4d52e4bbb7c56f14e234b08b0b0bc4f38a78f`
- Independent generated trees: 2
- Generated file inventory per tree: 112
- Normalized generated tree hash: `1b349f177ae630d3ca6cc8e79fb2233ec50181e080733f509fdccb79c6b7861a`
- Per-file inventory and hashes: identical; no post-generation source mutation
- Generated relationship operation inventory: exact 14/14
- TypeScript compiler: `5.9.3`
- Repository TypeScript configuration hash: `c7c0780404d447e5aa71ba6f9ced4a253e7d21c19837a5111b40df3b3e113018`
- Strict compile of both exact generated trees: PASS with zero diagnostics and `skipLibCheck=false`
- Forbidden public-surface scan: PASS with zero unwaived findings
- Fixture/schema outcome token matrix: PASS
- Focused constitutional contract suite: 16/16 PASS
- Compatibility manifest status: PASS

### Canonical Dependency Repair

The first canonical validation exposed twelve schema references introduced by historical BP route additions without corresponding component definitions. The repair adds those twelve transport schemas and five supporting enums from the existing authoritative SQL and ADR-022 contracts. It does not change F4 paths, operations, models, or semantics.

### Provenance And Limits

- `STATIC_SPEC`: canonical dependency closure, exact fourteen-operation inventory, security, idempotency, RFC 9457 mapping, and static forbidden-surface assertions are present.
- `GENERATED_COMPILE`: pinned dual-run generation, exact normalized hashes, generated inventory, no-manual-patch proof, and strict TypeScript compilation pass.
- `FIXTURE_BEHAVIOR`: deterministic contract token matrix passes; this is schema-level fixture evidence, not service execution.
- `LIVE_INTEGRATION`, `BROWSER`, `DEPLOYMENT`, and `CUSTOMER_PROOF`: absent and not claimed by G-F4-10.

### Artifact Paths

- `web/test-results/wc034-f4-evidence/relationship-workspace.slice.yaml`
- `web/test-results/wc034-f4-evidence/compatibility-manifest.json`
- `web/test-results/wc034-f4-evidence/generated-run-a/`
- `web/test-results/wc034-f4-evidence/generated-run-b/`
- `web/test-results/wc034-f4-evidence/logs/generator-pull.log`
- `web/test-results/wc034-f4-evidence/logs/generator-digest.log`