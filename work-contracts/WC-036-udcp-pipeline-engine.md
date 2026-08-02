# Work Contract 036 — UDCP: Universal Deterministic Code Pipeline Engine

**Office:** WAOOAW AI Agent — Platform IT Expert (INST-010)
**Sprint:** WC-036
**Backlog Item:** IB-009 — Foundation Implementation (Gate G5) — Pipeline Rebuild
**Sprint Track:** Track PIPELINE — Code Generation Infrastructure
**Gate:** G5 (pipeline prerequisite — blocks WC-027 through WC-034 execution)
**Reviewer:** Autonomous Sprint Reviewer (INST-010 PR Review hat)
**Constitutional Basis:** C-031 (ADR required), C-032 (Implementation may not create architecture), C-059 (Traceability), C-077 (Dev Cost Ceiling), C-082 (Build Validation)
**Authorization:** FA-039 required — Yogesh Khandge (Founder)

**Depends on:** ADR-039 (UDCP architectural spec — committed f50bc26)
**Blocks:** WC-027, WC-028, WC-029, WC-030, WC-031 — do NOT trigger any WBE sprint until WC-036 passes Definition of Done
**WC number assigned by:** Enterprise Architect (INST-004) — pipeline track, sequential after WC-035

---

## Sprint Goal

Implement the three UDCP engine files specified in ADR-039 + the rule-based Grooming Engine. On completion, the autonomous sprint runner uses Track 1 (Greenfield) or Track 2 (Differential) instead of the current full-file MagicLLM generation loop. WC-027 is the first sprint to execute on UDCP as a validation run.

---

## Tasks

| task_id | scope | model_hint | status | completed_at |
|---|---|---|---|---|
| WC036-01 | `scripts/runner/ptr_validation_gate.py` — `WorkspaceSymbolIndex` class: `index_workspace()`, `_resolve_module_string()` (sys_path_roots config), `_extract_exports()` (FunctionDef + ClassDef + Assign + ImportFrom re-exports), `validate_tis()` (module + symbol existence check); index rebuilt per-task call | `reasoning` | pending | — |
| WC036-02 | `scripts/runner/track1_scaffolder.py` — `Track1Scaffolder` class: `scaffold_artifacts()` with conditional `router = APIRouter()`, function stub generation (`[WAOOAW_LOGIC_FILLER_START]` / `[WAOOAW_LOGIC_FILLER_END]` markers), class/BaseModel stub generation (WC-EXT-01 §2 — field-level scaffold), `compile()` gate before file write | `reasoning` | pending | — |
| WC036-03 | `scripts/runner/track2_polymorphic_engine.py` — `Track2PolymorphicEngine` class: `find_target_node()` (class method + top-level function), `extract_node_for_llm()` (decorators stripped via `try/finally`), `splice_node_safely()` (signature invariant check, decorator coordinate fix, indentation separation, `compile()` gate before write) | `reasoning` | pending | — |
| WC036-04 | `scripts/runner/udcp_grooming_engine.py` — `UDCPGroomingEngine` class: `parse_wc_task_row(task_id, scope_text)` → TIS JSON or TMD JSON; `_detect_track(file_path)` (Track 1 if file absent, Track 2 if present); `_extract_imports_from_scope(scope_text, skeleton_path)` (regex + skeleton cross-reference — no LLM); `_extract_interfaces_from_scope(scope_text)` (FastAPI endpoint detection, class field detection); `generate_tis(task_id, scope_text, file_path)` → validated TIS dict; `generate_tmd(task_id, scope_text, file_path)` → TMD dict | `reasoning` | pending | — |
| WC036-05 | `scripts/runner/udcp_orchestrator.py` — `UDCPOrchestrator.execute_task(task_id, scope_text, output_files, skeleton_path, sys_path_roots)` → main entry point called by `task_executor.py`; orchestrates: grooming → PTR gate → Track 1 scaffold OR Track 2 extract → logic-fill LLM call (logic only, no structure) → Track 1 filler OR Track 2 splice → compile gate; returns `TaskResult`; replaces current MagicLLM full-file call for all python-stack tasks | `reasoning` | pending | — |
| WC036-06 | `tests/pipeline/test_udcp_engines.py` — unit tests: PTR gate validates correct imports, rejects invented symbols, resolves re-exports; Track 1 scaffolder produces compilable stubs for function + class interfaces, conditional APIRouter, compile gate blocks bad TIS; Track 2 engine extracts method without decorators, splices back with correct indentation, rejects signature mutation, handles top-level functions; grooming engine detects Track from file existence, extracts FastAPI endpoints, extracts Pydantic fields; orchestrator round-trip on WC027-01a scope (models.py + bundle_engine.py) | `auto` | pending | — |

---

## Required Inputs

| Input | File |
|---|---|
| UDCP Spec V6 | `gemini-code-1785676144736.md` (V6 final specification) |
| ADR-039 | `adr/ADR-039-udcp-universal-deterministic-code-pipeline.md` |
| EA Skeleton | `src/billing-engine/skeleton/wbe_interfaces.py` |
| WC-027 (target sprint) | `work-contracts/WC-027-wbe-s3-markup-engine.md` (used as grooming engine test input) |
| Existing task executor | `scripts/runner/task_executor.py` (call-site for orchestrator integration) |
| Existing pipeline | `scripts/magic_llm/pipeline.py`, `scripts/runner/llm_codegen.py` (logic-fill LLM calls are retained — UDCP wraps them, does not replace the LLM call itself) |

---

## Definition of Done

- [ ] `python3 -m py_compile scripts/runner/ptr_validation_gate.py` → exit 0
- [ ] `python3 -m py_compile scripts/runner/track1_scaffolder.py` → exit 0
- [ ] `python3 -m py_compile scripts/runner/track2_polymorphic_engine.py` → exit 0
- [ ] `python3 -m py_compile scripts/runner/udcp_grooming_engine.py` → exit 0
- [ ] `python3 -m py_compile scripts/runner/udcp_orchestrator.py` → exit 0
- [ ] `pytest tests/pipeline/test_udcp_engines.py` → all tests pass, ≥90% coverage
- [ ] `ruff check scripts/runner/ptr_validation_gate.py scripts/runner/track1_scaffolder.py scripts/runner/track2_polymorphic_engine.py scripts/runner/udcp_grooming_engine.py scripts/runner/udcp_orchestrator.py` → clean
- [ ] Grooming engine produces valid TIS for WC027-01a scope (models.py + bundle_engine.py) — PTR gate approves it
- [ ] Track 1 scaffolder produces compilable `models.py` stub from WC027-01a TIS — `BundleEngine` stub + Pydantic model stubs present
- [ ] `task_executor.py` updated: calls `UDCPOrchestrator.execute_task()` for python-stack tasks instead of direct MagicLLM full-file call
- [ ] `autonomous_halt` remains `true` until this WC is merged — runner will not fire WBE sprints on old pipeline

---

## Implementation Constraints (from ADR-039 V6 spec)

- **PTR symbol index** must be rebuilt at start of every task pass — not once at sprint start
- **Track 1 scaffolder** must NOT emit `router = APIRouter()` unless at least one interface has a `router.` decorator
- **Track 1 scaffolder** must handle both `"type": "function"` and `"type": "class"` interfaces (Pydantic BaseModel stubs)
- **Track 2 `extract_node_for_llm()`** must use `try/finally` when temporarily nulling `decorator_list`
- **Track 2 `splice_node_safely()`**: decorator lines extracted verbatim from `source_lines` (already indented); `ast.unparse()` output indented separately — no double-indent
- **Grooming engine** is LLM-free — regex + skeleton cross-reference only
- **Logic-fill LLM prompt** receives only the content between `[WAOOAW_LOGIC_FILLER_START]` and `[WAOOAW_LOGIC_FILLER_END]` markers plus the docstring — no full file context
- **Wildcard re-exports** (`from x import *`) are not tracked by PTR — all WAOOAW modules must use explicit named exports (enforced by ruff F403)
- `astor` must NOT be added as a dependency — use `ast.unparse()` (stdlib Python 3.12)

---

## Notes

- The existing MagicLLM pipeline (`scripts/magic_llm/`) is NOT deleted in this WC. The orchestrator calls it for the logic-fill step. Only the full-file generation mode is replaced.
- WC035-03 context-pressure Sonnet upgrade gate (`context > 40k → Sonnet`) should be removed as part of `task_executor.py` integration — logic-only prompts will be ~3–8k chars, making the gate unnecessary.
- After WC-036 merges: set `autonomous_halt: false`, `sprint_status: READY`, `current_sprint: WC-027` — WC-027 becomes the first UDCP validation run.
