# SIM-QA-001 — Test Champion CI Campaign Qualification

**Date:** 2026-08-14
**Institution:** INST-015 — Quality Assurance and Test Engineering
**Environment:** Local Docker Compose `test-runner-python`; no virtual environment or host Python
**Target:** Current `goal/007/qa-test-champion` working tree / pending PR #291 evidence surface
**Recommendation:** BLOCK

## Campaign

1. Build the exact `test-runner-python` image used by CI.
2. Run Ruff, format check, strict mypy, and real repository-level service suites in Docker.
3. Generate branch-aware Coverage XML/JSON from source-owned paths.
4. Evaluate line and branch counters independently against C-076 floors.
5. Verify deterministic campaign synthesis returns PASS for success/skipped inputs and BLOCK for a
   failed/cancelled prerequisite.

## Raw Results

| Check | Result | Evidence |
|---|---|---|
| Docker test-runner build | PASS | Image built from `Dockerfile.test-runner-python` |
| Workflow YAML parse | PASS | Ruby YAML parser, aliases enabled |
| Campaign verdict function | PASS | success + skipped → PASS; failure → BLOCK |
| AI Runtime tests | PASS | 43 passed |
| AI Runtime line coverage | BLOCK | 56.31%; minimum 90% |
| AI Runtime branch coverage | BLOCK | 64.18%; minimum 80% |
| AI Runtime Ruff | BLOCK | 5 violations: unused import plus four modernization/type-style findings |
| Professional Runtime tests | BLOCK | 166 passed, 1 failed |
| Professional Runtime contract | BLOCK | generated OpenAPI 1.2.0 differs from canonical 1.3.0 |
| Professional Runtime line coverage | BLOCK | 84.43%; minimum 90% |
| Professional Runtime branch coverage | BLOCK | 73.81%; minimum 80% |
| Test Champion structure/tier invariants | PASS | 13 manifests, 8 prompts/seeds; CLASSIFICATION LOCAL; BREAKING FRONTIER |

Raw machine evidence is produced under `coverage/{service}/` and retained by CI for 90 days. Local
coverage files are generated artifacts and are not committed.

## Obligation Disposition

| Obligation | Disposition |
|---|---|
| C-023 Evidence First | PASS — recommendation follows executable evidence |
| C-065 separation | PASS — campaign recommends only; no approval/merge authority |
| C-076 90% line / 80% branch | BLOCK — both Python services below floor |
| C-080 Docker-only Python tests | PASS — all Python checks executed in Compose runner |
| C-099 consequence routing | PASS — failed deterministic prerequisites force BLOCK |

## Finding Set

- **P1-QA-001:** Python CI previously targeted nonexistent service-local `tests/unit` directories.
  Corrected to `tests/ai-runtime` and `tests/professional-runtime`.
- **P1-QA-002:** AI Runtime coverage is below both constitutional floors.
- **P1-QA-003:** Professional Runtime has canonical OpenAPI drift and is below both coverage floors.
- **P1-QA-004:** AI Runtime fails the repository Ruff policy.

INST-015 remains `CHARTERED — Stage W-2 CAPABILITY DEVELOPMENT`. This simulation proves that the
campaign detects and blocks real defects; it does not prove operational activation readiness.
