# ADR-037 — Sprint Environment Contract Validation

**Status:** Accepted
**Date:** 2026-08-01
**Author:** Enterprise Architect (INST-005)
**Constitutional Basis:** C-032 (Spec/Code Drift Prevention), C-086 (Pre-Execution Gate), C-077 (Development Cost Ceiling)
**Supersedes:** Nothing — new pipeline gate

---

## Context

The autonomous sprint pipeline spends LLM tokens before validating that the CI execution environment can run the generated code. This creates a class of failures that:

1. Are **not detectable by any LLM gate** — they are environment facts, not code quality issues
2. **Block the test-validation subtask** (WC-NNN-c) after scaffold (a) and annotation (b) have already succeeded
3. **Repeat on every retry** until a human manually identifies and adds the missing package
4. Represent a **C-032 violation**: `requirements-test.txt` is declared the authoritative dependency source but the CI workflow used a separate, incomplete, manually-maintained list

Observed instance: `psycopg2-binary` was in `requirements-test.txt` but absent from the hardcoded `pip install` line in `autonomous-sprint.yaml`. WC-027 required 5 sprint runs across multiple sessions before the gap was found, wasting approximately ₹28 in LLM costs and 4 hours of iteration time.

The root cause is structural: two independent sources of truth for CI dependencies, one of which was authoritative by declaration but ignored in practice.

---

## Decision

1. **Single source of truth**: The CI workflow installs dependencies exclusively from `requirements-test.txt`. No parallel hardcoded install list.

2. **Environment Contract Validator**: A new script `scripts/env_validator.py` runs as a dedicated CI step — after dependency installation, before the groomer, before the runner. It:
   - Parses all `import` and `from X import` statements in `tests/` using Python `ast`
   - Identifies non-stdlib modules
   - Attempts `python -c "import X"` for each via subprocess
   - On any failure: prints a `CRITICAL` gap report and exits 1
   - Exit 1 propagates to `gap_halt=true` in the workflow, which halts the sprint via the existing C-086 mechanism before a single LLM token is spent

3. **Gate position**: The validator runs before the groomer. If the environment is broken, there is no point grooming SubTaskDefs or running the sprint.

---

## Consequences

**Positive:**
- Any future `ModuleNotFoundError` is caught before the sprint starts — zero wasted LLM cost
- `requirements-test.txt` becomes genuinely authoritative (validated on every run)
- When a new WC introduces a new library, the gap is caught in the same run that adds it, not in a subsequent test subtask
- Deterministic, zero-LLM, runs in under 10 seconds

**Negative / Constraints:**
- If `requirements-test.txt` lists a package that fails to install on the CI runner (compilation error, missing system library), the sprint will halt. This is correct behaviour — the solution is to fix `requirements-test.txt`, not bypass the check.
- The validator checks importability at the top-level module name. Packages with install names that differ from import names (e.g. `psycopg2-binary` → `import psycopg2`) are handled correctly because we test the import name, not the package name.

---

## Alternatives Considered

**A — Only fix requirements-test.txt usage in CI** (Layer 1 only): Catches the current psycopg2 gap but does not prevent recurrence. The next new WC that introduces a new library will hit the same class of error.

**B — Static analysis only (no runtime check)**: Cross-referencing import names against package names is unreliable due to import-name ≠ package-name mismatches. Runtime `python -c "import X"` is definitive.

**C — Pre-populate imports in conftest with try/except**: Hides real dependency errors. Rejected.

---

## Constitutional Trace

| Principle | Application |
|---|---|
| C-032 Spec/Code Drift | `requirements-test.txt` is the spec; CI must use it without deviation |
| C-086 Pre-Execution Gate | Environment contract must be verified before LLM execution begins |
| C-077 Dev Cost Ceiling | Prevents LLM cost waste on environment failures that repeat every retry |
