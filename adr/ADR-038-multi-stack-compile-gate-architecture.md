# ADR-038 — Multi-Stack Compile Gate Architecture

**Status:** Accepted
**Date:** 2026-08-01
**Author:** Enterprise Architect (INST-004) + Platform IT Expert (INST-010)
**Constitutional Basis:** C-082 (Build Validation), C-069 (Self-Improvement), C-077 (Dev Cost Ceiling), C-032 (Spec/Code Drift)
**Supersedes:** Implicit assumption in ADR-030 that compile gate = dotnet build only

---

## Context

ADR-030 defined the autonomous sprint code generation protocol with a 3-attempt retry loop and a compile gate at its centre. The compile gate as implemented covered:

- **.NET C#**: `dotnet build` (inside retry loop) + `dotnet_build` gate (outer)
- **Python**: `py_compile` syntax check only (inside retry loop); `ruff check` ran OUTSIDE the retry loop in `task_decomposer.run_compile_gate("ruff")` — no retry possible on ruff violations

This gap was revealed by WC-027 run 30686443609:
- **WC027-01bb** failed: `ANN201` (missing return type) — py_compile passed, ruff caught it after retry loop closed
- **WC027-02a** failed: `B017` (blind `pytest.raises(Exception)`) — same structural gap
- WC027-02b, WC027-02c skipped as downstream failures

Additionally, the platform now generates SQL migrations (`infrastructure/postgres/`), YAML Kubernetes manifests, Terraform infrastructure, and TypeScript Next.js files — none of which had any compile gate (inner or outer).

The SYSTEM slot injected into LLM prompts contained only C# forbidden patterns. Python tasks received zero ruff-specific constraints. The LLM had no knowledge of what gates its output would face.

---

## Decision

Three-layer defence architecture for every supported stack.

### Layer 0 — Pre-LLM Prevention (SYSTEM slot)

`context_builder._build_system()` now injects stack-specific constraints before the LLM writes a single character:

| Stack | Injected constant | Rules covered |
|---|---|---|
| Python | `_PYTHON_FORBIDDEN_PATTERNS` | ANN201, ANN001, B017, B006, F841, B018, ANN401, G004 |
| TypeScript | `_TYPESCRIPT_FORBIDDEN_PATTERNS` | no `any`, cookie-only JWT, Emergency Stop wiring, no console.log, server vs client components |
| Terraform | `_TERRAFORM_FORBIDDEN_PATTERNS` | Key Vault only (no hardcoded secrets), sensitive outputs, required outputs, pinned providers |

Additionally, a **Pipeline Self-Model** block is injected for ALL stacks: the LLM is told explicitly which 5 gates its output will face, in order, and how many retry attempts it has.

A **Violation History** block is injected from `sprint-context/lint-violations.json` (see Layer 2). Violations seen in prior runs appear as `⛔ [ANN201] seen in WC027-01bb` — the LLM knows not to repeat them.

### Layer 1 — Inside the 3-Attempt Retry Loop

`ResponseEvaluator._gate_compile()` dispatches by file extension AND stack:

| Stack | Inner gate | Pass condition |
|---|---|---|
| Python `.py` | `py_compile` (syntax) → `ruff check` (style) | Both exit 0 |
| .NET C# `.cs` | `dotnet build` | Exit 0 |
| TypeScript `.ts/.tsx` | `tsc --noEmit --strict` → `biome ci` (if configured) | Both exit 0 |
| SQL `.sql` | `sqlfluff lint --dialect postgres` | Exit 0 |
| YAML `.yaml/.yml` | `yamllint -d relaxed` | Exit 0 |
| Terraform `.tf` | `hcl2.load()` (python-hcl2) | No parse error |

When the inner gate fails, `GateResult.error_codes` is populated with extracted rule codes (`[A-Z]{1,3}\d{3,4}` pattern — covers multi-letter codes: ANN201, ANN001, UP007). `goal_executor._build_retry_context()` calls `sprint_retry_advisor.diagnose_build_error()` with the ruff output, which returns a **combined fix instruction covering all violations in that output** (not just the first).

### Layer 2 — Learning Cache + Outer Backstop

`task_decomposer.run_compile_gate()` is the outer backstop after `GoalExecutor` succeeds. On gate failure:
- Violations are written to `sprint-context/lint-violations.json` (keyed by rule code, with `last_task` and `gate` fields)
- `context_builder` reads this file at next prompt build time and injects `VIOLATION HISTORY`

New outer gate types added:
- `run_compile_gate("sqlfluff", target_files=[...])` for SQL subtasks
- `run_compile_gate("yamllint", target_files=[...])` for YAML subtasks
- `run_compile_gate("terraform_validate", target_files=[...])` for Terraform subtasks

### Retry Advisor Extension

`sprint_retry_advisor._classify_ruff_violation()` added as a new classifier:
- Fires BEFORE CS-code scan (ruff codes never overlap CS codes)
- Matches: `ANN201`, `ANN001`, `B017`, `B006`, `F841`, `B018`, `G004`, `E501`
- Returns **combined fix instruction** for all violations present in one output
- Confidence: 0.95 (rule-based, zero LLM cost)

---

## Implementation Commits

| Commit | Layer | Change |
|---|---|---|
| `1f404ec` | 0+1+2 | P0 — `_PYTHON_FORBIDDEN_PATTERNS`, Pipeline Self-Model, ruff inside `_compile_python()`, `_classify_ruff_violation()` |
| `c050aec` | 1+2 | P1 — `_gate_sql()`, `_gate_yaml()`, `run_compile_gate(sqlfluff/yamllint)`, lint-violations.json |
| `f85eb0d` | 0+1 | P2 — `_TYPESCRIPT_FORBIDDEN_PATTERNS`, `_TERRAFORM_FORBIDDEN_PATTERNS`, biome check, `_compile_terraform()` |
| `4bec166` | doc | P3 — `office-runtime-professional.md` pipeline self-model documentation |
| `bf6fb6d` | fix | Post-review: regex `[A-Z]\d{3,4}` → `[A-Z]{1,3}\d{3,4}` (ANN codes were silently dropped); multi-violation combined fix; biome probe guard; `task_id` in learning cache |

---

## Stack Coverage After ADR-038

| Stack | Inner (retry loop) | Outer (task_decomposer) | Pre-LLM (SYSTEM) |
|---|---|---|---|
| .NET C# | dotnet build ✅ | dotnet_build ✅ | `_FORBIDDEN_PATTERNS` ✅ |
| Python | py_compile + ruff ✅ | ruff ✅ | `_PYTHON_FORBIDDEN_PATTERNS` ✅ |
| TypeScript | tsc + biome ✅ | none | `_TYPESCRIPT_FORBIDDEN_PATTERNS` ✅ |
| SQL | sqlfluff ✅ | sqlfluff ✅ | — |
| YAML | yamllint ✅ | yamllint ✅ | — |
| Terraform | hcl2 parse ✅ | terraform_validate ✅ | `_TERRAFORM_FORBIDDEN_PATTERNS` ✅ |

---

## Consequences

**Positive:**
- ANN201/ANN001/B017 violations (WC-027 root cause) now caught inside retry loop with targeted fix at attempt 2
- Combined fix instruction covers all violations in one response — 3 retries now handle up to 3 distinct violation types in a single subtask
- Learning cache self-improves: first occurrence writes to JSON; subsequent sprints see warning in SYSTEM slot
- SQL/YAML/Terraform tasks that previously had no validation now have both inner and outer gates
- LLM knows what gates it faces (Pipeline Self-Model) — reduces "I didn't know" failures

**Negative / Constraints:**
- `sqlfluff` and `yamllint` must be in `requirements-test.txt` (already added)
- `python-hcl2` must be in `requirements-test.txt` for Terraform gate (already added)
- `biome` must be installed in `web/node_modules` for the TypeScript biome gate to fire (gracefully skipped if not present — 10s probe guards against 60s hang)
- Ruff code extraction regex `[A-Z]{1,3}\d{3,4}` may extract strings from file paths or log messages that happen to match the pattern. The ruff classifier should not be called for non-Python stacks — this is enforced by the `if ruff_codes:` guard using a specific ruff-pattern regex before calling the classifier
