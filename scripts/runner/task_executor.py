# Implements: scripts/runner/task_executor.py
# constitutional_basis: ADR-030, ADR-039, C-059, C-065, C-066, C-076, C-077, C-082, C-084
# ib_item: IB-020
"""
execute_with_llm() — 3-attempt retry loop with validation, symbol-level patching,
                     and Retry Advisor diagnostic escalation.
execute_with_udcp() — UDCP orchestrator entry point for Python-stack tasks (ADR-039).
flag_spec_gap()    — halt task and create GitHub Issue for EA/SA/Founder review.
"""
from __future__ import annotations

import importlib.util as _ilu
import os
import sys

from runner.constants import REPO_ROOT
from runner.git_ops import git, gh, record_evidence
from runner.llm_codegen import (
    call_llm_via_magiclm,
    parse_llm_files,
    validate_written_files,
    write_llm_files,
)
from runner.state import _INFRA_ERROR_TASKS, _MONITOR_SIGNAL
from runner.system_prompts import get_branch_context


def execute_with_llm(
    task_id: str,
    task_description: str,
    spec_sections: dict,
    constitutional_check: str,
    model_hint: str = "reasoning",
    max_tokens: int = 10000,
) -> bool:
    """
    Execute a code generation task using Claude (ADR-030 protocol).
    Implements the 3-attempt retry loop with validation.
    Returns True on success, False (with flag_spec_gap) on exhausted retries.

    constitutional_basis: ADR-030, C-059, C-076, C-077
    ib_item: IB-020
    """
    # Build spec content from sections
    spec_lines = [f"# Spec context for {task_id}"]
    for file_path, section in spec_sections.items():
        full_path = REPO_ROOT / file_path
        if full_path.is_file():
            content = full_path.read_text(encoding="utf-8", errors="replace")
            if section == "full" or len(content) < 6000:
                spec_lines.append(f"\n## {file_path}\n{content[:4000]}")
            else:
                spec_lines.append(f"\n## {file_path} (section: {section})\n[load section '{section}' from this file]")
    spec_content = "\n".join(spec_lines)

    # RAG: inject branch context — tell LLM what prior tasks already generated.
    branch_context = get_branch_context()
    if branch_context:
        spec_content = spec_content + branch_context
        print(f"  Branch context injected ({len(branch_context.splitlines())} lines) — EXTEND-NOT-REPLACE active")

    # Industry practice #6: cross-file namespace index (USING_MAP) — prevents CS0246.
    try:
        try:
            from scripts.ptr_assembler import get_assembler
        except ImportError:
            from ptr_assembler import get_assembler
        _asm = get_assembler()
        _using_map = _asm.build_using_map()
        if _using_map:
            spec_content = spec_content + "\n\n" + _asm.using_map_to_prompt_block(_using_map)
            print(f"  USING_MAP injected ({len(_using_map)} types) — CS0246 prevention active")
    except Exception as _ume:
        print(f"  WARN: USING_MAP build failed ({_ume}) — skipping")

    failure_context = ""
    infra_failures = 0
    max_attempts = 3
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")

    for attempt in range(1, max_attempts + 1):
        print(f"\n── {task_id} (attempt {attempt}/{max_attempts}) ──")

        prompt_with_context = spec_content
        if failure_context:
            prompt_with_context += f"\n\n# Previous attempt failed:\n{failure_context}\nFix the issues above."

        try:
            response = call_llm_via_magiclm(
                task_id, task_description, prompt_with_context,
                constitutional_check, model_hint, max_tokens,
                attempt=attempt,
            )
        except RuntimeError as infra_err:
            err_str = str(infra_err)
            infra_failures += 1
            if err_str.startswith("API_TIMEOUT"):
                print(f"  INFRA_TIMEOUT on attempt {attempt} — NOT a spec gap. Retrying in 30s.")
            elif err_str.startswith("RATE_LIMIT"):
                print(f"  RATE_LIMIT on attempt {attempt} — backing off 60s before retry.")
                import time; time.sleep(60)
            elif err_str.startswith("API_SERVER_ERROR"):
                print(f"  API_SERVER_ERROR on attempt {attempt} — retrying in 30s.")
            else:
                print(f"  INFRA_ERROR on attempt {attempt}: {err_str}")
            import time; time.sleep(30)
            continue

        if not response:
            print(f"  LLM call returned no response on attempt {attempt}")
            continue

        try:
            files = parse_llm_files(response)
            if not files:
                print(f"  No <file> blocks found in LLM response on attempt {attempt}")
                failure_context = "Response contained no <file path='...'> blocks. Generate file blocks."
                continue

            # ── Stage 1: Pre-compile self-review (before write) ───────────────
            if api_key and files:
                try:
                    _scripts = str(REPO_ROOT / "scripts")
                    if _scripts not in sys.path:
                        sys.path.insert(0, _scripts)
                    from codegen_self_review import pre_compile_review
                    try:
                        from ptr_assembler import get_assembler as _ga
                        _using_map = _ga().build_using_map()
                    except Exception:
                        _using_map = None
                    files = pre_compile_review(files, api_key, _using_map)
                    print(f"  PRE-REVIEW: self-review complete ({len(files)} file(s))")
                except Exception as _pre_err:
                    print(f"  PRE-REVIEW: skipped ({_pre_err})")

            written = write_llm_files(files, task_id=task_id)
            ok, build_error = validate_written_files(written)
        except Exception as parse_exc:
            failure_context = f"RUNNER_PIPELINE_BUG: {type(parse_exc).__name__}: {parse_exc}"
            print(f"  ❌ {failure_context}")
            _MONITOR_SIGNAL["task_results"][task_id] = {
                "result": "PIPELINE_BUG", "error_type": type(parse_exc).__name__,
                "build_error_snippet": str(parse_exc)[:200], "attempts": attempt, "spec_gap_issue": None,
            }
            break

        if ok:
            git(["add"] + written, check=False)
            diff = git(["diff", "--cached", "--quiet"], check=False)
            if diff.returncode != 0:
                git(["commit", "-m",
                     f"feat: {task_id} — {task_description}\n\n"
                     f"IB: IB-009\nConstitutional: C-059, C-073, C-076\nCCTs-added: per WC spec"])
            print(f"  ✅ {task_id} complete ({len(written)} files)")
            if attempt > 1 and failure_context.startswith("RETRY ADVISOR DIAGNOSIS:"):
                try:
                    _s = _ilu.spec_from_file_location("sprint_retry_advisor",
                         str(REPO_ROOT / "scripts" / "sprint_retry_advisor.py"))
                    _m = _ilu.module_from_spec(_s); _s.loader.exec_module(_m)
                    _m.record_successful_fix(
                        error_snippet=build_error[:200] if build_error else "",
                        fix_instruction=failure_context[failure_context.find("TARGETED FIX"):failure_context.find("TARGETED FIX")+400] if "TARGETED FIX" in failure_context else failure_context[:400],
                        error_type=failure_context.split("\n")[0].replace("RETRY ADVISOR DIAGNOSIS:", "").strip(),
                        task_id=task_id,
                    )
                    print(f"  LEARNING CACHE: fix recorded for future runs (C-069)")
                except Exception:
                    pass
            _MONITOR_SIGNAL["task_results"][task_id] = {
                "result": "SUCCESS", "error_type": None,
                "build_error_snippet": None, "attempts": attempt, "spec_gap_issue": None,
            }
            return True
        else:
            # ── Stage 2: Symbol-level patch (before full-file retry) ─────────
            if api_key and attempt < max_attempts:
                try:
                    from codegen_self_review import symbol_level_patch
                    patches = symbol_level_patch(build_error, api_key)
                    if patches:
                        print(f"  SYMBOL-PATCH: applying surgical fixes to {len(patches)} file(s)")
                        for patch_path, patch_content in patches.items():
                            full = REPO_ROOT / patch_path
                            full.write_text(patch_content, encoding="utf-8")
                        patch_written = list(patches.keys())
                        ok2, build_error2 = validate_written_files(patch_written)
                        if ok2:
                            print(f"  SYMBOL-PATCH: ✅ compile error resolved — skipping full retry")
                            git(["add"] + written + patch_written, check=False)
                            diff = git(["diff", "--cached", "--quiet"], check=False)
                            if diff.returncode != 0:
                                git(["commit", "-m",
                                     f"feat: {task_id} — {task_description} (symbol-patched)\n\n"
                                     f"IB: IB-009\nConstitutional: C-059, C-073, C-076\nCCTs-added: per WC spec"])
                            print(f"  ✅ {task_id} complete via symbol-patch ({len(written)} files)")
                            _MONITOR_SIGNAL["task_results"][task_id] = {
                                "result": "SUCCESS", "error_type": None,
                                "build_error_snippet": None, "attempts": attempt, "spec_gap_issue": None,
                            }
                            return True
                        else:
                            print(f"  SYMBOL-PATCH: patch did not fully resolve — falling through to advisor")
                            build_error = build_error2
                except Exception as _sp_err:
                    print(f"  SYMBOL-PATCH: skipped ({_sp_err})")

            # Layer 1: Sprint Retry Advisor — classify error before next attempt
            _spec_ra = _ilu.spec_from_file_location("sprint_retry_advisor",
                        str(REPO_ROOT / "scripts" / "sprint_retry_advisor.py"))
            _mod_ra = _ilu.module_from_spec(_spec_ra)
            sys.modules.setdefault("sprint_retry_advisor", _mod_ra)
            _spec_ra.loader.exec_module(_mod_ra)
            diagnose_build_error = _mod_ra.diagnose_build_error
            branch_cs_files = [
                str(p.relative_to(REPO_ROOT))
                for p in REPO_ROOT.glob("src/**/*.cs")
            ]
            diagnosis = diagnose_build_error(task_id, build_error, written, branch_cs_files)

            if diagnosis.confidence < 0.30 and not diagnosis.should_retry:
                print(f"  Retry Advisor: STOP_LOSS — confidence={diagnosis.confidence:.0%} < 30%; skipping remaining attempts")
                failure_context = (
                    f"RETRY ADVISOR: {diagnosis.error_type} — confidence below stop-loss threshold.\n"
                    f"{build_error[:200]}"
                )
                break

            if not diagnosis.should_retry:
                print(f"  Retry Advisor: {diagnosis.error_type} — skipping remaining attempts "
                      f"(confidence={diagnosis.confidence:.0%})")
                failure_context = (
                    f"RETRY ADVISOR: {diagnosis.error_type} — unrecoverable without spec fix.\n"
                    f"{build_error[:200]}"
                )
                break

            failure_context = (
                f"RETRY ADVISOR DIAGNOSIS: {diagnosis.error_type}\n"
                f"CONSTITUTIONAL BASIS: {diagnosis.constitutional_trace}\n"
                f"TARGETED FIX REQUIRED: {diagnosis.fix_instruction}\n\n"
                f"ORIGINAL BUILD ERROR (for reference):\n{build_error[:300]}"
            )
            print(f"  Retry Advisor: {diagnosis.error_type} — intelligent retry with fix context")

    # All attempts exhausted
    if failure_context.startswith("RUNNER_PIPELINE_BUG:"):
        print(f"  ⚠️  PIPELINE_BUG: {task_id} failed due to runner logic, not spec content.")
        return False

    if infra_failures == max_attempts:
        print(f"  ⚠️  INFRA_FAILURE: {task_id} — all {max_attempts} attempts were API failures (timeout/rate-limit).")
        print(f"  This is NOT a spec gap. No issue created. Next cron run will retry automatically.")
        _INFRA_ERROR_TASKS.append(task_id)
        _MONITOR_SIGNAL["task_results"][task_id] = {
            "result": "INFRA_ERROR", "error_type": "API_TIMEOUT",
            "build_error_snippet": None, "attempts": max_attempts, "spec_gap_issue": None,
        }
        return False
    elif infra_failures > 0:
        gap_desc = (f"{task_id} failed after {max_attempts} attempts ({infra_failures} API timeouts, "
                    f"{max_attempts - infra_failures} build failures). Last build error: {failure_context[:200]}")
    else:
        if failure_context.startswith("RETRY ADVISOR DIAGNOSIS:"):
            print(f"  ⚠️  BUILD_FAILURE: {task_id} exhausted {max_attempts} attempts with actionable diagnosis.")
            print("  Routing to cascade for autonomous recovery (not spec-gap issue).")
            _MONITOR_SIGNAL["task_results"][task_id] = {
                "result": "BUILD_FAILURE", "error_type": "RETRY_EXHAUSTED",
                "build_error_snippet": failure_context[:200], "attempts": max_attempts, "spec_gap_issue": None,
            }
            return False

        gap_desc = f"{task_id} failed validation after {max_attempts} LLM attempts. Last error: {failure_context[:300]}"

    flag_spec_gap(
        task_id=task_id,
        gap_description=gap_desc,
        affected_spec=list(spec_sections.keys())[0] if spec_sections else "unknown",
        constitutional_basis="C-059 (Traceability — implementation must match spec), C-076 (Coverage)"
    )
    return False


def flag_spec_gap(
    task_id: str,
    gap_description: str,
    affected_spec: str,
    workaround: str = "",
    constitutional_basis: str = "",
) -> None:
    """
    HALT the current task and create a GitHub Issue for EA/SA/Founder review.

    The implementation agent CANNOT proceed with a workaround. A workaround is
    an architectural decision — it is outside the Implementation hat's authority (C-065).

    Constitutional basis:
      C-065: SDLC Separation — Implementation hat cannot make architectural decisions
      C-066: Tier 3 — Architectural/spec changes require EA office or Founder approval
      C-059: Traceability — every implementation must trace to a valid spec; gap = no trace
    """
    github_repo = os.environ.get("GITHUB_REPO", "")
    github_token = os.environ.get("GITHUB_TOKEN", "")

    workaround_note = (
        f"\n## Workaround Considered (NOT Applied)\n\n{workaround}\n\n"
        f"**This workaround was NOT implemented.** The agent does not have authority "
        f"to make architectural decisions (C-065, C-066 Tier 3).\n"
    ) if workaround else ""

    title = f"spec-gap [{task_id}]: {gap_description[:80]}"
    body = (
        f"## Spec Gap — Implementation Halted\n\n"
        f"**Discovered by:** Autonomous Sprint Agent (Platform IT Expert — Implementation hat)\n"
        f"**During task:** `{task_id}`\n"
        f"**Affected spec:** `{affected_spec}`\n"
        f"**Task status:** BLOCKED — will not retry until this issue is closed\n\n"
        f"## Gap Description\n\n{gap_description}\n\n"
        + workaround_note
        + f"## Required Action (EA/SA or Founder)\n\n"
        f"1. Review the gap described above\n"
        f"2. Update `{affected_spec}` with the correct design decision\n"
        f"3. Open a PR for the spec change (branch: `spec-fix/{task_id.lower()}-gap`)\n"
        f"4. Merge the spec PR\n"
        f"5. **Close this issue** — the next sprint run will detect the closure and retry `{task_id}`\n\n"
        f"The implementation agent will automatically retry `{task_id}` when this issue is closed.\n\n"
        + (f"## Constitutional Basis\n\n{constitutional_basis}\n\n" if constitutional_basis else "")
        + f"---\n_Auto-generated by `flag_spec_gap()` in `scripts/runner/task_executor.py`_"
    )

    if github_repo and github_token:
        result = gh([
            "issue", "create",
            "--repo", github_repo,
            "--title", title,
            "--body", body,
            "--label", "awaiting:founder-approval",
        ], check=False)
        if result.returncode == 0:
            issue_url = result.stdout.strip()
            issue_num = issue_url.split("/")[-1] if "/" in issue_url else "?"
            print(f"  🔴 SPEC GAP — task HALTED. Issue #{issue_num} created.")
            print(f"     Gap: {gap_description[:80]}")
            print(f"     Spec: {affected_spec}")
            print(f"     Fix the spec, close the issue, and the next sprint run retries.")
            record_evidence("spec_gap_halt", task=task_id, issue=issue_num, gap=gap_description[:100])
            _MONITOR_SIGNAL["task_results"][task_id] = {
                "result": "SPEC_GAP", "error_type": "BUILD_ERROR",
                "build_error_snippet": gap_description[:200],
                "attempts": 3, "spec_gap_issue": issue_num,
            }
            _MONITOR_SIGNAL["spec_gap_issues"].append(issue_num)
        else:
            print(f"  🔴 SPEC GAP — task HALTED (issue creation failed: {result.stderr[:100]})")
            print(f"     Gap: {gap_description}")
            record_evidence("spec_gap_halt_no_issue", task=task_id, gap=gap_description[:100])
    else:
        print(f"  🔴 SPEC GAP — task HALTED (no GitHub token for issue creation)")
        print(f"     Gap: {gap_description}")


def execute_with_udcp(
    task_id: str,
    scope_text: str,
    sprint_id: str = "",
    model_hint: str = "reasoning",
    max_tokens: int = 8000,
    required_output_files: list[str] | None = None,
    inject_source_files: list[str] | None = None,
) -> tuple[bool, list[str]]:
    """
    UDCP orchestrator entry point for Python-stack tasks (ADR-039).
    Returns (success, files_written) so callers can scope compile gates to actual output.

    constitutional_basis: ADR-039, C-059, C-077, C-082
    ib_item: IB-009
    """
    from runner.udcp_orchestrator import UDCPOrchestrator

    orchestrator = UDCPOrchestrator()
    result = orchestrator.execute_task(
        task_id=task_id,
        scope_text=scope_text,
        sprint_id=sprint_id,
        model_hint=model_hint,
        max_tokens=max_tokens,
        required_output_files=required_output_files,
        inject_source_files=inject_source_files,
    )

    if result.success:
        written = result.files_written
        if written:
            git(["add", *written], check=False)
            diff = git(["diff", "--cached", "--quiet"], check=False)
            if diff.returncode != 0:
                git(["commit", "-m",
                     f"feat: {task_id} — UDCP {result.track} track\n\n"
                     f"IB: IB-009\nConstitutional: C-059, C-073, C-076, ADR-039\n"
                     f"Files: {', '.join(written[:3])}"])
        print(f"  ✅ {task_id} complete via UDCP {result.track} ({len(written)} files)")
        # task_results entry is provisional — compile gate in execute_subtask_chain may override it
        _MONITOR_SIGNAL["task_results"][task_id] = {
            "result": "SUCCESS", "error_type": None,
            "build_error_snippet": None, "attempts": result.attempts, "spec_gap_issue": None,
        }
        return True, written

    print(f"  ❌ {task_id} UDCP failure: {result.error_type} — {result.error_snippet}")
    _MONITOR_SIGNAL["task_results"][task_id] = {
        "result": "UDCP_FAILURE", "error_type": result.error_type,
        "build_error_snippet": result.error_snippet, "attempts": result.attempts,
        "spec_gap_issue": None,
    }
    flag_spec_gap(
        task_id=task_id,
        gap_description=f"UDCP {result.error_type}: {result.error_snippet}",
        affected_spec=task_id,
        constitutional_basis="ADR-039 (UDCP pipeline), C-082 (Build Validation)",
    )
    return False, []
