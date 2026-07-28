#!/usr/bin/env python3
"""
task_decomposer.py — Dependency-Ordered Sub-Task Execution Engine

# Implements: architecture/reference/pipeline/dependency-graph-task-decomposition.md
#             architecture/reference/pipeline/wc-spec-reader.md (IB-022 Phase 2a)
# constitutional_basis:
#   C-084 (Step Dependency Ordering — sub-tasks execute in dependency order, halt on failure)
#   C-083 (Emit-Transport-Listen — signal emitted after each sub-task, branch context propagated)
#   C-086 (Pre-Execution Simulation Obligation — simulation must pass before first LLM call)
#   C-082 (Build Validation — compile gate between every sub-task)
#   C-059 (Traceability — every sub-task traces to its spec via wc_task_id)
#   C-032 (Implementation may not create architecture — decomposition authorized by sprint-task-decomposition.md)
# office: Platform IT Expert (Implementation hat)
# IB: IB-021 / WC-019, IB-022

Implements ADR-030 Amendment 1: sub-task decomposition replaces single-LLM-call
for multi-layer tasks.

Implements ADR-030 Amendment 2 (IB-022): SubTaskDef.wc_task_id links to PMO Work
Contract. _build_effective_check() assembles constitutional_check from:
  1. PMO WC spec (via WCSpecReader)
  2. output_files list
  3. prior task preservation (not_regenerate_from ∩ completed)
  4. STACK_BEHAVIORAL_RULES (EA-approved floor rules per stack)
  5. constitutional_check delta (task-specific override)
Backward compatible: SubTaskDef without wc_task_id uses constitutional_check only.
"""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

REPO_ROOT = Path(__file__).parent.parent


# ══════════════════════════════════════════════════════════════════════════════
# Stack Behavioral Rules (IB-022)
# EA-approved floor rules per technology stack.
# Changes to this dict require Enterprise Architect review (C-032).
# These rules apply to every LLM subtask on the given stack.
# ══════════════════════════════════════════════════════════════════════════════

STACK_BEHAVIORAL_RULES: dict[str, list[str]] = {
    "dotnet": [
        "⛔ FIRST LINE RULE: The FIRST line of every .cs file MUST be // (comment) or using (directive). NEVER ## or any markdown. CS1024 fires if you start with markdown.",
        "ActionParameters is JSON-encoded — use ctx.GetParameter(\"key\"), NEVER TryGetValue().",
        "TenantId comes from gRPC metadata: context.RequestHeaders.GetValue(\"x-tenant-id\") ?? \"\".",
        "All using directives MUST precede the namespace declaration (proto namespace collision risk).",
        "PROTO NAMESPACE: using Waooaw.ConstitutionalEngine.Grpc; on files referencing gRPC types.",
        "C-059 header required on every .cs file: // Implements: <spec> and // constitutional_basis: <claims>.",
        # ── Constitutional Error Handling Standards (C-082, C-059) ──────────────
        "ERROR HANDLING RULE 1: Never swallow exceptions silently. catch (Exception ex) MUST log: _logger.LogError(ex, 'Operation failed: {Context}', context) before returning/rethrowing.",
        "ERROR HANDLING RULE 2: Every public method that can fail must return a Result<T>/bool or throw — never return null to indicate failure.",
        "ERROR HANDLING RULE 3: gRPC methods must map exceptions to StatusCode: catch (Exception ex) { _logger.LogError(ex, ...); throw new RpcException(new Status(StatusCode.Internal, ex.Message)); }",
        "ERROR HANDLING RULE 4: Every subprocess/external call needs timeout: CancellationToken or TimeSpan.FromSeconds(N). Never block indefinitely.",
        "ERROR HANDLING RULE 5: C-059 compliance — every caught exception that is swallowed MUST write to constitutional.audit_records with error_type='SWALLOWED_EXCEPTION'.",
    ],
    "python": [
        "No synchronous DB calls from Temporal activities — use async/await throughout.",
        "Every FastAPI endpoint must call CE.ValidateAction before execution (C-023).",
        "PII must not appear in any log statement (C-063).",
        "C-059 header required: # Implements: <spec> and # constitutional_basis: <claims>.",
        # ── Constitutional Error Handling Standards ──────────────────────────────
        "ERROR HANDLING RULE 1: Never use bare 'except: pass' or 'except Exception: pass'. Always log: logger.error('Operation failed', exc_info=True, extra={'context': context})",
        "ERROR HANDLING RULE 2: Use specific exception types. 'except (ValueError, KeyError) as e:' not 'except Exception as e:'.",
        "ERROR HANDLING RULE 3: Every async function must handle CancelledError separately: except asyncio.CancelledError: raise — never swallow it.",
        "ERROR HANDLING RULE 4: All subprocess calls need timeout=N seconds. subprocess.TimeoutExpired must be caught and logged.",
        "ERROR HANDLING RULE 5: C-059 compliance — every exception caught and not re-raised must produce an evidence record.",
    ],
    "typescript": [
        "JWT stored in httpOnly cookie ONLY — never localStorage or sessionStorage.",
        "All API mutations require CE.ValidateAction call before execution (C-023).",
        "Emergency Stop button must be rendered on every authenticated page (C-001).",
        "C-059 header required: // Implements: <spec> and // constitutional_basis: <claims>.",
        # ── Constitutional Error Handling Standards ──────────────────────────────
        "ERROR HANDLING RULE 1: Never swallow errors in catch blocks. catch (e) { console.error(e); } is not acceptable — must use structured logging with context.",
        "ERROR HANDLING RULE 2: async functions must have try/catch or .catch() — unhandled promise rejections are a constitutional violation (no evidence record).",
        "ERROR HANDLING RULE 3: All fetch/API calls need AbortController with timeout. Never await fetch() without a timeout.",
    ],
    "terraform": [
        "All outputs must be named and described — they become PTR terraform_output entries.",
        "No secrets in Terraform state — use Azure Key Vault references (ADR-014).",
        "C-059 header required on every .tf file: # Implements: <spec> and # constitutional_basis: <claims>.",
    ],
    "mixed": [],  # No stack-specific rules — use constitutional_check delta
}


# ── Sub-task definition ────────────────────────────────────────────────────────

@dataclass
class SubTaskDef:
    """
    Declares one unit of work within a sprint task.

    type='deterministic': template_fn() called — no LLM, guaranteed namespace.
    type='llm': execute_with_llm() called — Claude generates business logic.

    C-084: depends_on list enforced before execution begins.
    C-083: signal emitted after compile gate passes.

    IB-022: wc_task_id links to PMO Work Contract for constitutional requirements.
    constitutional_check is now a delta/override — primary content comes from WC spec.
    """
    id: str                                    # e.g. "WC012-03a"
    description: str
    type: str                                  # "deterministic" | "llm"
    depends_on: list[str] = field(default_factory=list)
    compile_gate: str = "dotnet_build"         # "dotnet_build" | "dotnet_test" | "ruff" | "tsc"
    service_dir: str = "src/constitutional-engine"  # target service dir for compile gate

    # For type="deterministic"
    template_fn: Optional[Callable[[], bool]] = None

    # For type="llm" — mirror of execute_with_llm() params
    spec_sections: dict[str, str] = field(default_factory=dict)
    model_hint: str = "reasoning"
    max_tokens: int = 10000

    # IB-022: WC-spec-driven constitutional check assembly
    wc_task_id: str = ""                       # "WC012-02" → auto-loads PMO spec
    output_files: list[str] = field(default_factory=list)  # files this subtask MUST produce
    not_regenerate_from: list[str] = field(default_factory=list)  # prior subtask IDs
    stack: str = "dotnet"                      # selects STACK_BEHAVIORAL_RULES entry
    inject_source_files: list[str] = field(default_factory=list)  # actual source to paste verbatim

    # DELTA: task-specific override / additions (primary if wc_task_id empty)
    constitutional_check: str = ""

    # Phase-gated generation (industry: Contract-First + Compile-Gated Development)
    # "skeleton" → signatures/stubs only, no logic, compile required
    # "logic"    → fill bodies only, signatures frozen from skeleton phase
    # "test"     → tests only, no source file changes
    # "full"     → legacy single-pass (default, backward compatible)
    generation_phase: str = "full"


# ── Effective constitutional check assembly (IB-022) ──────────────────────────

def _build_effective_check(st: SubTaskDef, completed: list[str]) -> str:
    """
    Assemble the effective constitutional_check for an LLM subtask.

    # Implements: architecture/reference/pipeline/wc-spec-reader.md §_build_effective_check()
    # constitutional_basis: C-059 (traceability), C-032 (spec before code), DP-009 (API First)

    Assembly order:
      1. PMO constitutional requirements (auto-loaded from WC spec)
      2. Output file list
      3. Prior task preservation (not_regenerate_from ∩ completed)
      4. Stack behavioral rules (EA-approved floor)
      5. Task-specific delta (constitutional_check field)

    Graceful: if WC spec not found, falls back to delta only. Never blocks execution.
    PTR type contracts are appended AFTER this output by execute_subtask_chain.
    """
    parts: list[str] = []

    # 1. PMO constitutional requirements
    if st.wc_task_id:
        try:
            from wc_spec_reader import get_task
            wc_spec = get_task(st.wc_task_id)
            if wc_spec:
                pmo_section = (
                    f"CONSTITUTIONAL REQUIREMENTS "
                    f"(PMO: {wc_spec.task_id} — {wc_spec.title}):\n"
                )
                if wc_spec.scope:
                    pmo_section += f"Scope: {wc_spec.scope}\n"
                if wc_spec.constitutional_check:
                    pmo_section += wc_spec.constitutional_check
                if wc_spec.cct_gate:
                    pmo_section += f"\nCCT gate: {wc_spec.cct_gate}"
                parts.append(pmo_section.strip())
        except Exception as _wc_err:
            print(f"  WCSpecReader: skipped ({_wc_err})")

    # 2. Output file boundaries
    if st.output_files:
        files_section = "Implement ONLY these files:\n" + "\n".join(
            f"  {f}" for f in st.output_files
        )
        parts.append(files_section)

    # 3. Prior task preservation
    preserved = [t for t in st.not_regenerate_from if t in completed]
    if preserved:
        parts.append(
            f"Do NOT regenerate files from prior subtasks: {', '.join(preserved)}"
        )

    # 4. Stack behavioral rules (EA floor)
    rules = STACK_BEHAVIORAL_RULES.get(st.stack, [])
    if rules:
        rules_section = "STACK RULES (non-negotiable):\n" + "\n".join(
            f"  {r}" for r in rules
        )
        parts.append(rules_section)

    # 5. Phase rules (Contract-First + Compile-Gated development)
    _PHASE_RULES: dict[str, str] = {
        "skeleton": (
            "PHASE: SKELETON ONLY.\n"
            "Generate class/interface/method SIGNATURES, properties, and empty bodies ONLY.\n"
            "⛔ NO business logic. ⛔ NO implementation in method bodies.\n"
            "⛔ NO conditional statements, calculations, or DB calls.\n"
            "Every method body = `throw new NotImplementedException();`\n"
            "Compile MUST pass. Signatures are FROZEN after this phase — do not change them in later phases."
        ),
        "logic": (
            "PHASE: LOGIC FILL ONLY.\n"
            "All files already exist on branch with FROZEN signatures from skeleton phase.\n"
            "Fill method bodies ONLY. ⛔ Do NOT change any signature.\n"
            "⛔ Do NOT add or remove methods, properties, or constructors.\n"
            "⛔ Do NOT change class/interface names or namespaces."
        ),
        "test": (
            "PHASE: TEST ONLY.\n"
            "Write tests for existing source files. ⛔ Do NOT modify any source file.\n"
            "AAA pattern. ≥90% coverage (C-076). All arguments positional — no mixing named+positional (CS1744)."
        ),
    }
    if st.generation_phase in _PHASE_RULES:
        parts.append(_PHASE_RULES[st.generation_phase])

    # 6. Task-specific delta
    if st.constitutional_check:
        parts.append(st.constitutional_check)

    return "\n\n".join(filter(None, parts))


# ── Compile gates ──────────────────────────────────────────────────────────────

def run_compile_gate(gate_type: str, service_dir: str = "src/constitutional-engine") -> tuple[bool, str]:
    """
    Run the appropriate compile gate for the technology stack.
    C-082: build validation required after every sub-task.
    Returns (passed, error_output).
    """
    if gate_type == "dotnet_build":
        csproj_files = list((REPO_ROOT / service_dir).glob("*.csproj"))
        if not csproj_files:
            return False, f"No .csproj found in {service_dir}"
        result = subprocess.run(
            ["dotnet", "build", str(csproj_files[0]), "--nologo", "-v", "quiet"],
            capture_output=True, text=True, cwd=REPO_ROOT
        )
        return result.returncode == 0, result.stderr[:500] if result.returncode != 0 else ""

    if gate_type == "dotnet_test":
        test_csproj = list((REPO_ROOT / "tests").rglob("*.csproj"))
        if not test_csproj:
            return False, "No test .csproj found"
        result = subprocess.run(
            ["dotnet", "test", str(test_csproj[0]), "--nologo", "-v", "quiet", "--no-build"],
            capture_output=True, text=True, cwd=REPO_ROOT
        )
        return result.returncode == 0, result.stderr[:500] if result.returncode != 0 else ""

    if gate_type == "ruff":
        result = subprocess.run(
            ["python3", "-m", "ruff", "check", service_dir],
            capture_output=True, text=True, cwd=REPO_ROOT
        )
        return result.returncode == 0, result.stdout[:500]

    if gate_type == "pytest":
        result = subprocess.run(
            ["python3", "-m", "pytest", service_dir, "-q", "--tb=short"],
            capture_output=True, text=True, cwd=REPO_ROOT
        )
        return result.returncode == 0, result.stdout[-500:] if result.returncode != 0 else ""

    return False, f"Unknown gate_type: {gate_type}"


# ── Signal emission (C-083) ───────────────────────────────────────────────────

def emit_subtask_signal(task_id: str, subtask_id: str, result: str, monitor_signal: dict) -> None:
    """
    C-083 (Emit-Transport-Listen): emit sub-task completion signal.
    Written to monitor-signal.json before next sub-task begins.
    The next sub-task's branch context read AFTER this signal is emitted.
    """
    if "subtask_results" not in monitor_signal:
        monitor_signal["subtask_results"] = {}
    monitor_signal["subtask_results"][subtask_id] = {
        "result": result,  # "SUCCESS" | "FAIL" | "SKIPPED"
        "task_id": task_id,
    }


# ── File-by-file LLM generation (IB-023) ──────────────────────────────────────

def _filter_ptr_types_for_file(filename: str, all_types: dict) -> list[str]:
    """
    Heuristic: return PTR type names likely relevant to the given filename.
    Reduces prompt context by injecting only relevant types, not all 24.

    Rules (in priority order):
    1. Type name appears verbatim in filename → always include
    2. File is a test → include all types (tests reference many types)
    3. File is ConstitutionalEngineService → include proto + registry types
    4. File is an evaluator → include evaluation types only
    5. Fallback → return all type names (safe default)
    """
    fname = filename.lower()

    # Test files — include all types
    if "test" in fname or "spec" in fname:
        return list(all_types.keys())

    # Constitutional engine service — proto types + evaluator types
    if "service" in fname and "constitutional" in fname:
        return [t for t in all_types if
                any(k in t.lower() for k in ("validate", "record", "evidence", "emergency",
                                              "grant", "revoke", "evaluator", "evaluation",
                                              "validation", "decision", "budget"))]

    # Evaluator files — evaluation types only
    if "evaluator" in fname or "evaluators" in fname.split("/")[-2:]:
        return [t for t in all_types if
                any(k in t.lower() for k in ("evaluation", "evaluator", "verdict",
                                              "result", "claim", "context", "registry"))]

    # Name match — type name substring appears in filename
    matched = [t for t in all_types if t.lower() in fname or fname in t.lower()]
    if matched:
        return matched + [t for t in all_types if
                          any(k in t.lower() for k in ("evaluation", "evaluator"))]

    # Safe fallback — inject all
    return list(all_types.keys())


def execute_file_by_file(
    task_id: str,
    output_files: list[str],
    effective_check: str,
    spec_sections: dict,
    model_hint: str,
    max_tokens: int,
    inject_source_files: list[str] | None = None,
    prior_output_files: list[str] | None = None,
    stack: str = "dotnet",
    goal_id: str = "",
) -> bool:
    """
    Generate LLM output one file at a time.

    # Implements: architecture/reference/magic-llm/architecture.md §7+§8
    #             architecture/reference/goal-orchestrator/component-contracts.md §2
    # constitutional_basis: C-032, C-059, C-065, C-073, C-082

    Execution path (in priority order):
      1. GoalExecutor (GO→MagicLLM): canonical path — GO in execution path (A7 fix)
      2. Inline MagicLLM (ContextBuilder + ResponseEvaluator): fallback if GO unavailable
      3. Ad-hoc assembly: last-resort fallback for infrastructure failures

    GoalExecutor uses:
      - §7.1 ContextBuilder (9-slot ordered context)
      - §8 ResponseEvaluator (5 gates)
      - CascadeHandler (not spec-gap issues on failure)
      - Frozen Artifact Registry
    """
    _scripts = str(REPO_ROOT / "scripts")
    if _scripts not in sys.path:
        sys.path.insert(0, _scripts)
    from autonomous_sprint_runner import execute_with_llm, write_llm_files, parse_llm_files, validate_written_files, call_llm_via_magiclm

    # ── FinOps Pattern 1: augment spec_sections from sprint RAG index ──────────
    # The index pre-computes semantically-relevant spec files with token-budget
    # awareness. Merge them in so GoalExecutor/ContextBuilder gets a richer
    # context than the hardcoded SubTaskDef spec_sections alone.
    # SubTaskDef entries take priority (more specific); index fills gaps.
    _index_path = REPO_ROOT / "sprint-context" / "index.json"
    if _index_path.exists():
        try:
            import json as _ijson
            _idx = _ijson.loads(_index_path.read_text(encoding="utf-8"))
            _idx_specs: dict[str, str] = {
                s["file"]: (
                    s.get("section", "full")
                    if "TOO_LARGE" not in s.get("section", "")
                    else "full"
                )
                for s in _idx.get("spec_sections", [])
                if s.get("file") and (REPO_ROOT / s["file"]).exists()
            }
            # SubTaskDef wins on overlap — index fills the gaps
            _augmented = {**_idx_specs, **spec_sections}
            if len(_augmented) > len(spec_sections):
                print(f"  FILE-BY-FILE: RAG index augmented spec_sections "
                      f"{len(spec_sections)} → {len(_augmented)} files "
                      f"(+{len(_augmented) - len(spec_sections)} from index)")
            spec_sections = _augmented
        except Exception as _idx_e:
            pass  # non-blocking — SubTaskDef spec_sections still used

    # ── Path 1: GoalExecutor (canonical — A7 fix) ──────────────────────────────
    effective_goal_id = goal_id or f"GOAL-{task_id.split('-')[0].upper()}"
    _go_available = False
    try:
        from goal_orchestrator.goal_executor import GoalExecutor
        _go_available = True
    except ImportError as _go_import_err:
        print(f"  FILE-BY-FILE: GoalExecutor not importable ({_go_import_err}) — using MagicLLM inline")

    if _go_available:
        try:
            executor = GoalExecutor(goal_id=effective_goal_id, repo_root=REPO_ROOT)
            print(f"  FILE-BY-FILE: using GoalExecutor (canonical GO path)")
            results = executor.execute_sprint_task(
                task_id=task_id,
                wc_number=task_id[2:5] if task_id.startswith("WC") else "012",
                output_files=output_files,
                spec_sections=spec_sections,
                constitutional_check=effective_check,
                stack=stack,
                model_hint=model_hint,
                max_tokens=max_tokens,
                completed_tasks=[],
            )
            # C-084 2.0: return True only if ALL files succeeded
            all_ok = all(r.status == "success" for r in results)
            for r in results:
                mark = "✅" if r.status == "success" else "❌"
                print(f"  {mark} FILE-BY-FILE: {Path(r.task.output_file).name} ({r.status}, {r.attempts} attempt(s))")
            if all_ok:
                return True
            # Partial success — identify failed files and log prominently
            failed = [r.task.output_file for r in results if r.status != "success"]
            print(f"  FILE-BY-FILE: GoalExecutor partial failure — {len(failed)} file(s) failed: {failed}")
            print(f"  FILE-BY-FILE: falling back to inline MagicLLM for failed files only")
            # Only regenerate files that GoalExecutor failed on
            output_files = failed
        except Exception as _go_runtime_err:
            print(f"  FILE-BY-FILE: ⚠️  GoalExecutor runtime error ({type(_go_runtime_err).__name__}: {_go_runtime_err})")
            print(f"  FILE-BY-FILE: falling back to inline MagicLLM")

    # ── Path 2: Inline MagicLLM (fallback) ────────────────────────────────────
    # Try to load MagicLLM components
    try:
        from magic_llm.context_builder import ContextBuilder
        from magic_llm.response_evaluator import ResponseEvaluator
        _cb = ContextBuilder(REPO_ROOT)
        _re_eval = ResponseEvaluator(REPO_ROOT)
        _use_magic = True
    except Exception as _import_err:
        print(f"  FILE-BY-FILE: MagicLLM unavailable ({_import_err}) — using ad-hoc assembly")
        _use_magic = False

    already_written: list[str] = []

    for output_file in output_files:
        file_name = Path(output_file).name
        print(f"\n  FILE-BY-FILE: generating {file_name}")

        if _use_magic:
            # ── §7.1 Ordered Context Assembly + §8 Response Evaluator with retry ──
            # E3: retry loop (was single attempt — all 3 attempts wasted)
            # E4: fresh ContextBuilder per attempt (reloads frozen registry)
            # E5: pre-compile self-review before write
            # E7: retry advisor on compile gate failure
            import os as _os
            api_key = _os.environ.get("ANTHROPIC_API_KEY", "")
            if not api_key:
                print(f"  WARN: no API key — falling back to ad-hoc path")
                _use_magic = False
            else:
                max_magic_attempts = 3
                magic_failure_context = ""
                magic_success = False

                for attempt in range(1, max_magic_attempts + 1):
                    # E4: fresh ContextBuilder per attempt — reloads frozen registry
                    try:
                        from magic_llm.context_builder import ContextBuilder as _CB
                        _cb_fresh = _CB(REPO_ROOT)
                    except Exception:
                        _cb_fresh = _cb  # fallback to outer instance

                    try:
                        # Build context with failure context from prior attempt
                        ctx = _cb_fresh.build(
                            task_id=f"{task_id}:{file_name}",
                            output_file=output_file,
                            spec_sections=spec_sections,
                            constitutional_check=(
                                effective_check +
                                (f"\n\nPREVIOUS ATTEMPT FAILED:\n{magic_failure_context}" if magic_failure_context else "")
                            ),
                            depends_on_tasks=[],
                            prior_output_files=prior_output_files or already_written,
                            stack=stack,
                        )
                        print(f"\n── {task_id}:{file_name} (attempt {attempt}/{max_magic_attempts}) ──")
                        print(f"  CONTEXT: {ctx.total_chars:,} chars ({len(ctx.blocks)} slots)")

                        response = call_llm_via_magiclm(
                            f"{task_id}:{file_name}",
                            f"Generate {file_name}",
                            ctx.full_prompt,
                            "",
                            model_hint,
                            min(max_tokens, 4000),
                            attempt=attempt,
                        )

                        if not response:
                            magic_failure_context = "LLM returned no response."
                            continue

                        files_parsed = parse_llm_files(response)
                        if not files_parsed:
                            magic_failure_context = "No <file> blocks in response — wrap output in <file path=\"...\">.</file>"
                            continue

                        # E5: pre-compile self-review before write
                        try:
                            from codegen_self_review import pre_compile_review
                            from ptr_assembler import get_assembler as _pga2
                            _um2 = _pga2().build_using_map()
                            files_parsed = pre_compile_review(files_parsed, api_key, _um2)
                            print(f"  PRE-REVIEW: self-review complete ({len(files_parsed)} file(s))")
                        except Exception as _pr_err:
                            pass  # non-blocking

                        written = write_llm_files(files_parsed)

                        # §8 Response Evaluator — 5 gates
                        eval_result = _re_eval.evaluate(
                            task_id=f"{task_id}:{file_name}",
                            raw_response=response,
                            written_files=written,
                            stack=stack,
                            spec_sections=spec_sections,
                        )
                        for gate in eval_result.gates:
                            status = "✅" if gate.passed else "❌"
                            print(f"  {status} Gate {gate.gate}: {gate.detail[:80]}")

                        if eval_result.all_passed:
                            already_written.append(output_file)
                            print(f"  FILE-BY-FILE: {file_name} ✅")
                            magic_success = True
                            break

                        # E7: retry advisor on compile failure
                        failure = eval_result.first_failure
                        if failure and failure.error_codes:
                            try:
                                import importlib.util as _ilu
                                _s = _ilu.spec_from_file_location("sprint_retry_advisor",
                                     str(REPO_ROOT / "scripts" / "sprint_retry_advisor.py"))
                                _m = _ilu.module_from_spec(_s); _s.loader.exec_module(_m)
                                diagnosis = _m.diagnose_build_error(
                                    f"{task_id}:{file_name}", failure.detail, written, []
                                )
                                if diagnosis.should_retry and diagnosis.confidence >= 0.3:
                                    magic_failure_context = (
                                        f"COMPILE FAILED ({','.join(failure.error_codes)}):\n"
                                        f"{failure.detail[:300]}\n\n"
                                        f"TARGETED FIX: {diagnosis.fix_instruction}"
                                    )
                                    print(f"  Retry Advisor: {diagnosis.error_type} (confidence={diagnosis.confidence:.0%})")
                                    continue
                            except Exception:
                                pass
                        magic_failure_context = f"Gate {failure.gate} failed: {failure.detail[:300]}"

                    except Exception as _magic_err:
                        print(f"  MagicLLM error on attempt {attempt}: {_magic_err}")
                        magic_failure_context = str(_magic_err)[:200]

                if magic_success:
                    continue
                if not magic_failure_context.startswith("LLM"):
                    print(f"  FILE-BY-FILE: {file_name} ❌ — exhausted {max_magic_attempts} attempts")
                    return False
                # If all failures were LLM/infra, fall through to ad-hoc
                print(f"  FILE-BY-FILE: MagicLLM exhausted — falling back to ad-hoc for {file_name}")
                _use_magic = False

        # ── Ad-hoc assembly fallback (pre-MagicLLM path, kept for resilience) ─
        # Collect all PTR types for selective injection
        all_ptr_types: dict = {}
        try:
            from platform_type_registry import load_ptr, build_ptr_prompt_block
            ptr = load_ptr()
            for task_entry in ptr.get("tasks", {}).values():
                all_ptr_types.update(task_entry.get("types", {}))
        except Exception:
            pass

        preservation = (
            f"\nFiles already written in this session (DO NOT regenerate):\n  "
            + "\n  ".join(already_written)
        ) if already_written else ""

        relevant_types = _filter_ptr_types_for_file(output_file, all_ptr_types)
        file_ptr_block = ""
        if all_ptr_types and relevant_types:
            try:
                file_ptr_block = build_ptr_prompt_block(relevant_types, ptr=ptr)
                print(f"  PTR: {len(relevant_types)}/{len(all_ptr_types)} types injected for {file_name}")
            except Exception:
                pass

        single_file_check = (
            f"Generate ONLY this ONE file: {output_file}\n"
            f"Do NOT generate any other file.{preservation}\n\n"
            f"{effective_check}"
            f"{file_ptr_block}"
        )

        # REQUIRED_USINGS injection
        try:
            from ptr_assembler import get_assembler as _pga
            _umap = _pga().build_using_map()
            if _umap:
                import re as _re2
                _scan_text = effective_check + file_ptr_block
                _mentioned = set(_re2.findall(r'\b([A-Z][a-zA-Z0-9]+)\b', _scan_text))
                _req = sorted({f"using {ns};" for cls, ns in _umap.items() if cls in _mentioned})
                if _req:
                    single_file_check += "\n\nREQUIRED USINGS:\n" + "\n".join(_req)
                    print(f"  REQUIRED_USINGS: {len(_req)} directives injected")
        except Exception:
            pass

        success = execute_with_llm(
            f"{task_id}:{file_name}",
            f"Generate {file_name}",
            spec_sections,
            single_file_check,
            model_hint,
            min(max_tokens, 4000),
        )

        if success:
            already_written.append(output_file)
            print(f"  FILE-BY-FILE: {file_name} ✅")
        else:
            print(f"  FILE-BY-FILE: {file_name} ❌ — halting subtask")
            return False

    print(f"  FILE-BY-FILE: all {len(output_files)} file(s) generated successfully")
    return True


# ── Generalized LLM subtask runner (used by both normal and skeleton→logic path) ─

def _run_llm_subtask(st: "SubTaskDef", completed: list[str], dry_run: bool) -> bool:
    """Run a single LLM subtask with full context assembly. Used by execute_subtask_chain."""
    _scripts = str(REPO_ROOT / "scripts")
    if _scripts not in sys.path:
        sys.path.insert(0, _scripts)
    from autonomous_sprint_runner import execute_with_llm

    spec_with_context = dict(st.spec_sections)
    effective_check = _build_effective_check(st, completed)

    if not st.output_files:
        try:
            from platform_type_registry import build_ptr_prompt_block, load_ptr
            ptr = load_ptr()
            if ptr:
                all_type_names = [
                    t for task_entry in ptr.get("tasks", {}).values()
                    for t in task_entry.get("types", {}).keys()
                ]
                ptr_block = build_ptr_prompt_block(all_type_names, ptr=ptr)
                if ptr_block:
                    effective_check = effective_check + ptr_block
        except Exception:
            pass

    if st.output_files:
        return execute_file_by_file(
            st.id, st.output_files, effective_check, spec_with_context,
            st.model_hint, st.max_tokens,
            stack=st.stack,
            prior_output_files=list(spec_with_context.keys()),  # spec keys hint at dependencies
        )
    else:
        return execute_with_llm(
            st.id, st.description, spec_with_context, effective_check,
            st.model_hint, st.max_tokens,
        )


# ── Canary-file validation ─────────────────────────────────────────────────────

def run_canary_validation(
    task_id: str,
    output_files: list[str],
    effective_check: str,
    spec_sections: dict,
    model_hint: str,
    compile_gate: str,
    service_dir: str,
) -> tuple[bool, str]:
    """
    Industry Item 8: Canary-file validation.
    Generate and compile the FIRST (most representative) file in isolation.
    If it fails, do not waste tokens on remaining files in the batch.
    Returns (should_proceed, error_message).
    """
    if not output_files or len(output_files) < 2:
        return True, ""  # no value in canary for single file

    canary_file = output_files[0]
    print(f"  CANARY: validating {Path(canary_file).name} before batch generation")

    _scripts = str(REPO_ROOT / "scripts")
    if _scripts not in sys.path:
        sys.path.insert(0, _scripts)
    from autonomous_sprint_runner import execute_with_llm, validate_written_files

    canary_check = (
        f"Generate ONLY this ONE canary file: {canary_file}\n"
        f"Do NOT generate any other file.\n\n"
        f"{effective_check}"
    )

    success = execute_with_llm(
        f"{task_id}:canary:{Path(canary_file).name}",
        f"Canary: {Path(canary_file).name}",
        spec_sections,
        canary_check,
        model_hint,
        3000,  # tight budget for canary
    )

    if not success:
        return False, f"Canary file {canary_file} failed — stopping batch"

    gate_ok, gate_error = run_compile_gate(compile_gate, service_dir)
    if not gate_ok:
        return False, f"Canary compile failed: {gate_error[:200]}"

    print(f"  CANARY: ✅ {Path(canary_file).name} validates — proceeding with batch")
    return True, ""


# ── TaskDecomposer ─────────────────────────────────────────────────────────────

def execute_subtask_chain(
    task_id: str,
    subtasks: list[SubTaskDef],
    monitor_signal: dict,
    infra_error_tasks: list,
    dry_run: bool = False,
) -> bool:
    """
    Execute sub-tasks with C-084 2.0: continue past non-dependent failures.

    C-084 2.0 (industry: fair-attempt sweep):
      - Scaffold/deterministic failures → halt dependents (hard gate)
      - LLM subtask failures → mark FAILED, skip direct dependents, continue rest
      - At end: commit what succeeded, record failures for next-run retry
      - Next run: branch context shows completed work, retries only failed items

    C-083: emits signal after each sub-task, refreshes branch context.
    C-082: compile gate after every sub-task.
    """
    _scripts = str(REPO_ROOT / "scripts")
    if _scripts not in sys.path:
        sys.path.insert(0, _scripts)
    from autonomous_sprint_runner import execute_with_llm, get_branch_context, git

    completed: list[str] = []
    failed: list[str] = []      # C-084 2.0: track failures without halting chain
    all_written_files: list[str] = []

    print(f"\n── {task_id}: sub-task chain ({len(subtasks)} sub-tasks) ──")

    for st in subtasks:
        # ── C-084 2.0: dependency check — skip if dependency FAILED ───────────
        unmet_failed = [d for d in st.depends_on if d in failed]
        unmet_incomplete = [d for d in st.depends_on if d not in completed and d not in failed]

        if unmet_failed:
            # Dependency failed — skip this subtask (can't succeed without its inputs)
            print(f"  [{st.id}] SKIPPED — dependency failed: {unmet_failed}")
            emit_subtask_signal(task_id, st.id, "SKIPPED", monitor_signal)
            failed.append(st.id)  # mark as failed so its dependents also skip
            continue

        if unmet_incomplete:
            # Dependency not yet run (shouldn't happen in ordered list, but guard it)
            print(f"  [{st.id}] BLOCKED — unmet dependencies: {unmet_incomplete}")
            emit_subtask_signal(task_id, st.id, "SKIPPED", monitor_signal)
            failed.append(st.id)
            continue

        print(f"\n  ── [{st.id}] {st.description} ({st.type}) ──")

        if dry_run:
            print(f"  DRY RUN: would execute sub-task {st.id}")
            completed.append(st.id)
            continue

        # ── C-083: refresh branch context before LLM call ─────────────────────
        branch_context = get_branch_context()
        if branch_context:
            print(f"  Branch context refreshed ({len(branch_context.splitlines())} lines)")

        # ── Execute sub-task ───────────────────────────────────────────────────
        if st.type == "deterministic":
            if st.template_fn is None:
                print(f"  [{st.id}] ERROR: deterministic sub-task has no template_fn")
                emit_subtask_signal(task_id, st.id, "FAIL", monitor_signal)
                failed.append(st.id)
                continue
            print(f"  [{st.id}] Running deterministic template...")
            success = st.template_fn()

        elif st.type == "llm":
            # ── Industry Item 1: Generalized skeleton→logic two-pass executor ──
            # If generation_phase="skeleton", we run an automatic second "logic" pass
            # after the skeleton compiles. This is fully general — no per-task code.
            if st.generation_phase == "skeleton":
                print(f"  [{st.id}] PHASE 1/2: SKELETON (signatures + stubs only)...")
                skeleton_st = st
                success = _run_llm_subtask(skeleton_st, completed, dry_run)
                if not success:
                    print(f"  [{st.id}] SKELETON phase FAILED — marking failed, continuing chain")
                    emit_subtask_signal(task_id, st.id, "FAIL", monitor_signal)
                    failed.append(st.id)
                    continue
                # Compile gate between phases
                gate_ok, gate_error = run_compile_gate(st.compile_gate, st.service_dir)
                if not gate_ok:
                    print(f"  [{st.id}] SKELETON compile gate FAILED: {gate_error[:200]}")
                    emit_subtask_signal(task_id, st.id, "FAIL", monitor_signal)
                    failed.append(st.id)
                    continue
                print(f"  [{st.id}] SKELETON compile gate: ✅ PASS — signatures frozen")
                import copy
                logic_st = copy.copy(st)
                logic_st.generation_phase = "logic"
                print(f"  [{st.id}] PHASE 2/2: LOGIC FILL (method bodies only)...")
                success = _run_llm_subtask(logic_st, completed, dry_run)
                if success:
                    completed.append(st.id)
                    emit_subtask_signal(task_id, st.id, "SUCCESS", monitor_signal)
                    print(f"  [{st.id}] C-083 signal: SUBTASK_COMPLETE emitted")
                else:
                    print(f"  [{st.id}] LOGIC phase FAILED — marking failed, continuing chain")
                    emit_subtask_signal(task_id, st.id, "FAIL", monitor_signal)
                    failed.append(st.id)
                continue  # Skip standard execution below

            print(f"  [{st.id}] Calling LLM ({st.model_hint}, max={st.max_tokens} tokens)...")
            spec_with_context = dict(st.spec_sections)

            # IB-022: assemble constitutional_check from WC spec + stack rules + delta
            effective_check = _build_effective_check(st, completed)

            # C-085/DP-009: inject PTR type contracts (appended to effective_check)
            # Note: for file-by-file mode, PTR injection is done per-file with targeted types.
            # For batch mode (legacy), inject all types here.
            if not st.output_files:
                try:
                    from platform_type_registry import build_ptr_prompt_block, load_ptr
                    ptr = load_ptr()
                    if ptr:
                        all_type_names = [
                            t for task_entry in ptr.get("tasks", {}).values()
                            for t in task_entry.get("types", {}).keys()
                        ]
                        ptr_block = build_ptr_prompt_block(all_type_names, ptr=ptr)
                        if ptr_block:
                            effective_check = effective_check + ptr_block
                            print(f"  PTR: injected {len(all_type_names)} type(s) (batch mode)")
                except Exception as _ptr_err:
                    print(f"  PTR injection skipped: {_ptr_err}")

            # IB-023: file-by-file generation when output_files defined (industry best practice)
            if st.output_files:
                print(f"  [{st.id}] File-by-file mode: {len(st.output_files)} file(s)")
                # E1+E2 fix: pass stack + prior_output_files so ContextBuilder has frozen signatures
                # prior = all output files from already-completed subtasks in this chain
                prior_files = [
                    f for prev_st in subtasks
                    if prev_st.id in completed and hasattr(prev_st, 'output_files')
                    for f in (prev_st.output_files or [])
                ]
                success = execute_file_by_file(
                    st.id,
                    st.output_files,
                    effective_check,
                    spec_with_context,
                    st.model_hint,
                    st.max_tokens,
                    stack=st.stack,
                    prior_output_files=prior_files,
                )
            else:
                # Legacy batch mode — backward compat for subtasks without output_files
                from autonomous_sprint_runner import execute_with_llm
                success = execute_with_llm(
                    st.id,
                    st.description,
                    spec_with_context,
                    effective_check,
                    st.model_hint,
                    st.max_tokens,
                )
        else:
            print(f"  [{st.id}] ERROR: unknown type '{st.type}'")
            failed.append(st.id)
            continue

        if not success:
            print(f"  [{st.id}] FAILED — marking failed, continuing with non-dependents (C-084 2.0)")
            emit_subtask_signal(task_id, st.id, "FAIL", monitor_signal)
            failed.append(st.id)
            continue

        # ── C-082: compile gate ────────────────────────────────────────────────
        gate_ok, gate_error = run_compile_gate(st.compile_gate, st.service_dir)
        if not gate_ok:
            print(f"  [{st.id}] COMPILE GATE FAILED: {gate_error[:200]}")
            print(f"  C-084 2.0: marking failed, continuing non-dependent subtasks")
            emit_subtask_signal(task_id, st.id, "FAIL", monitor_signal)
            failed.append(st.id)
            continue

        print(f"  [{st.id}] Compile gate: ✅ PASS")

        # §7.6: Freeze artifact signatures immediately after compile gate PASS
        # Context Builder for next subtask will inject [FROZEN] block from registry
        if st.output_files:
            try:
                _scripts = str(REPO_ROOT / "scripts")
                if _scripts not in sys.path:
                    sys.path.insert(0, _scripts)
                from magic_llm.context_builder import ContextBuilder
                _cb = ContextBuilder(REPO_ROOT)
                frozen_count = _cb.freeze_artifacts_from_task(st.output_files, st.id)
                if frozen_count > 0:
                    print(f"  [{st.id}] Frozen {frozen_count} artifact signature(s) → registry updated")
                    # P0 Fix 1: commit frozen-artifacts.json to sprint branch
                    # Without this, frozen signatures are lost when runner workspace is discarded
                    frozen_path = REPO_ROOT / "sprint-context" / "frozen-artifacts.json"
                    if frozen_path.exists():
                        git(["add", str(frozen_path)], check=False)
                        diff = git(["diff", "--cached", "--quiet"], check=False)
                        if diff.returncode != 0:
                            git(["commit", "-m",
                                 f"chore(frozen): {st.id} artifact signatures committed\n\n"
                                 "Constitutional: C-085 (Idempotency — frozen signatures persist across runs)"],
                                check=False)
                            print(f"  [{st.id}] Frozen registry committed to sprint branch")
            except Exception as _freeze_err:
                print(f"  [{st.id}] WARN: artifact freeze failed ({_freeze_err}) — non-blocking")

        # C-083 Emit: extract compiled types → write to PTR for downstream subtasks.
        # Best-effort — never blocks sprint execution.
        try:
            from platform_type_registry import update_ptr_from_task
            src_files = [
                str(f.relative_to(REPO_ROOT))
                for f in (REPO_ROOT / "src").rglob("*")
                if f.is_file() and f.suffix in (".cs", ".proto", ".py", ".ts", ".tsx", ".tf")
            ]
            if src_files:
                update_ptr_from_task(st.id, src_files)
        except Exception as _ptr_err:
            print(f"  PTR update skipped: {_ptr_err}")

        # ── C-083: emit signal ─────────────────────────────────────────────────
        emit_subtask_signal(task_id, st.id, "SUCCESS", monitor_signal)
        completed.append(st.id)
        print(f"  [{st.id}] C-083 signal: SUBTASK_COMPLETE emitted")

    # All sub-tasks attempted — commit what succeeded
    if not dry_run and completed:
        git(["add", "src/", "tests/"], check=False)
        diff = git(["diff", "--cached", "--quiet"], check=False)
        if diff.returncode != 0:
            git(["commit", "-m",
                 f"feat: {task_id} — {subtasks[-1].description}\n\n"
                 f"IB: IB-009\nConstitutional: C-059, C-073, C-076, C-084\n"
                 f"Sub-tasks: {', '.join(completed)}"
                 + (f"\nFailed (retry next run): {', '.join(failed)}" if failed else "")])

    print(f"\n  ✅ {task_id}: {len(completed)}/{len(subtasks)} sub-tasks passed"
          + (f" | {len(failed)} failed (retry next run): {failed}" if failed else ""))
    return len(failed) == 0
    return len(completed) == len(subtasks)


def check_simulation_exists(task_id: str) -> tuple[bool, str]:
    """
    C-086: verify simulation with PASS verdict exists for this task/sub-task.
    Returns (exists, reason).
    """
    sim_dir = REPO_ROOT / "simulation"
    # Match case-insensitively: files are named SIM-PL-002-WC012-03-*.md (uppercase)
    patterns = [
        f"SIM-PL-002-{task_id}-*.md",          # exact case: SIM-PL-002-WC012-03-*.md
        f"SIM-PL-002-{task_id.lower()}-*.md",  # lowercase fallback
        f"SIM-PL-002-{task_id.lower().replace('-', '')}-*.md",  # no-hyphen fallback
    ]

    for pattern in patterns:
        matches = list(sim_dir.glob(pattern))
        if matches:
            content = matches[0].read_text(encoding="utf-8", errors="replace")
            if "Verdict: ✅ PASS" in content or "VERDICT: ✅ PASS" in content:
                return True, str(matches[0].name)

    return False, f"No SIM-PL-002 with PASS verdict found for {task_id}"
