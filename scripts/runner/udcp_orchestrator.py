# Implements: WC-036 — WC036-05
# constitutional_basis: ADR-039 §5, C-059, C-077, C-082
from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from runner.constants import REPO_ROOT
from runner.ptr_validation_gate import WorkspaceSymbolIndex
from runner.track1_scaffolder import Track1Scaffolder, Track1ScaffoldError
from runner.track2_polymorphic_engine import Track2PolymorphicEngine, Track2SpliceError
from runner.udcp_grooming_engine import UDCPGroomingEngine

# Filler marker pattern used in Track 1 scaffolds
_FILLER_START = "# [WAOOAW_LOGIC_FILLER_START]"
_FILLER_END = "# [WAOOAW_LOGIC_FILLER_END]"

# Track 2 LLM response marker
_FUNC_BLOCK_RE = re.compile(
    r"```python\s*((?:async\s+)?def\s.+?)```", re.DOTALL
)


@dataclass
class TaskResult:
    success: bool
    error_type: str | None = None
    error_snippet: str | None = None
    attempts: int = 1
    track: str = "UNKNOWN"
    files_written: list[str] = field(default_factory=list)
    dry_run: bool = False
    prompt_preview: str = ""  # populated in dry_run mode


class UDCPOrchestrator:
    """
    Main UDCP entry point called by task_executor.py for Python-stack tasks.

    Flow:
      grooming (LLM-free) → PTR gate → Track 1 scaffold OR Track 2 extract
      → logic-fill LLM → Track 1 file write OR Track 2 splice
      → compile gate → TaskResult

    Replaces direct full-file MagicLLM generation (ADR-039 supersedes ADR-030 §3).
    ADR-030 §1-2 (model selection, provider strategy) remain in force - the LLM is
    still called for the logic-fill step.
    """

    def __init__(
        self,
        skeleton_path: Path | None = None,
        sys_path_roots: list[str] | None = None,
        repo_root: Path | None = None,
        dry_run: bool = False,
        llm_fn: Callable[..., str | None] | None = None,
    ) -> None:
        self.repo_root = repo_root or REPO_ROOT
        self.dry_run = dry_run
        self._llm_fn = llm_fn
        self.groom = UDCPGroomingEngine(skeleton_path=skeleton_path, repo_root=self.repo_root)
        self.ptr = WorkspaceSymbolIndex(sys_path_roots=sys_path_roots, repo_root=self.repo_root)

    # ── Public API ────────────────────────────────────────────────────────────

    def execute_task(
        self,
        task_id: str,
        scope_text: str,
        sprint_id: str = "",
        model_hint: str = "reasoning",
        max_tokens: int = 8000,
    ) -> TaskResult:
        """
        Executes one WC task through the UDCP pipeline.
        Returns TaskResult — caller decides commit/flag_spec_gap based on success.
        """
        track = self.groom.detect_track(scope_text)

        if track == "GREENFIELD":
            return self._run_track1(task_id, scope_text, sprint_id, model_hint, max_tokens)
        elif track == "DIFFERENTIAL":
            return self._run_track2(task_id, scope_text, sprint_id, model_hint, max_tokens)
        else:
            # MIXED: scaffold new files (Track 1), then patch existing files (Track 2).
            r1 = self._run_track1(task_id, scope_text, sprint_id, model_hint, max_tokens, skip_existing=True)
            if not r1.success:
                return r1
            r2 = self._run_track2(task_id, scope_text, sprint_id, model_hint, max_tokens)
            # GROOMING_ERROR on Track 2 means no existing-file methods found — non-fatal for MIXED
            if not r2.success and r2.error_type != "GROOMING_ERROR":
                return r2
            return TaskResult(
                success=True, track="MIXED",
                files_written=r1.files_written + r2.files_written,
            )

    # ── Track 1: Greenfield ───────────────────────────────────────────────────

    def _run_track1(
        self,
        task_id: str,
        scope_text: str,
        sprint_id: str,
        model_hint: str,
        max_tokens: int,
        skip_existing: bool = False,
    ) -> TaskResult:
        # 1. Generate TIS
        try:
            tis = self.groom.generate_tis(task_id, scope_text, sprint_id)
        except Exception as exc:
            return TaskResult(
                success=False, error_type="GROOMING_ERROR",
                error_snippet=str(exc)[:300], track="GREENFIELD",
            )

        # 2. PTR gate — reject invented imports before scaffold
        self.ptr.index_workspace()
        ptr_errors = self.ptr.validate_tis(tis)
        if ptr_errors:
            return TaskResult(
                success=False, error_type="PTR_GATE_FAILURE",
                error_snippet="; ".join(ptr_errors[:5]), track="GREENFIELD",
            )

        # 3. Scaffold compilable stub files (skip existing files in MIXED-track)
        if skip_existing:
            tis["target_artifacts"] = [
                a for a in tis["target_artifacts"]
                if not (self.repo_root / a["file_path"]).is_file()
            ]
            if not tis["target_artifacts"]:
                return TaskResult(success=True, track="MIXED", files_written=[])

        try:
            scaffolder = Track1Scaffolder(tis, repo_root=self.repo_root)
            # 4. Dry-run: render in memory — no write, no disk mutation
            if self.dry_run:
                previews = scaffolder.scaffold_preview()
                preview_text = "\n".join(
                    f"=== {rp} ===\n{content}" for rp, content in previews.items()
                )
                return TaskResult(
                    success=True, track="GREENFIELD",
                    files_written=list(previews.keys()),
                    dry_run=True, prompt_preview=preview_text,
                )
            written_paths = scaffolder.scaffold_artifacts()
        except Track1ScaffoldError as exc:
            return TaskResult(
                success=False, error_type="SCAFFOLD_ERROR",
                error_snippet=str(exc)[:300], track="GREENFIELD",
            )

        # 4. Logic-fill LLM call for each scaffolded file
        filled_paths: list[str] = []
        for path in written_paths:
            result = self._fill_track1_logic(
                task_id, path, scope_text, model_hint, max_tokens
            )
            if not result.success:
                return result
            filled_paths.extend(result.files_written)

        return TaskResult(
            success=True, track="GREENFIELD",
            files_written=filled_paths,
        )

    def _fill_track1_logic(
        self,
        task_id: str,
        scaffold_path: Path,
        scope_text: str,
        model_hint: str,
        max_tokens: int,
    ) -> TaskResult:
        """Send scaffolded file to LLM and ask it to fill in LOGIC_FILLER sections."""
        _call_llm: Callable[..., str | None]
        if self._llm_fn is not None:
            _call_llm = self._llm_fn
            _parse = _parse_llm_files_local
        else:
            try:
                from runner.llm_codegen import call_llm_for_udcp, parse_llm_files
            except ImportError:
                return TaskResult(
                    success=False, error_type="IMPORT_ERROR",
                    error_snippet="call_llm_for_udcp not available", track="GREENFIELD",
                )
            _call_llm = call_llm_for_udcp
            _parse = parse_llm_files

        scaffold_content = scaffold_path.read_text(encoding="utf-8")
        rel_path = str(scaffold_path.relative_to(self.repo_root))

        prompt = (
            f"Fill in the logic sections of the Python scaffold below.\n\n"
            f"RULES:\n"
            f"- Replace every section between [WAOOAW_LOGIC_FILLER_START] and "
            f"[WAOOAW_LOGIC_FILLER_END] with working implementation\n"
            f"- Do NOT change any imports, function signatures, or class names\n"
            f"- Return the COMPLETE file — every line including all imports and class definitions\n"
            f"- No markdown code fences, no explanation — only the XML block below\n\n"
            f"Task context:\n{scope_text[:1500]}\n\n"
            f"Scaffold:\n{scaffold_content}\n\n"
            f"Respond with ONLY this format (the complete filled file):\n"
            f'<file path="{rel_path}">\n'
            f"...complete file content here...\n"
            f"</file>"
        )

        # 2-attempt retry: logic-only prompts are small but first attempt can timeout
        for attempt in range(1, 3):
            response = _call_llm(
                task_id=task_id,
                prompt=prompt,
                model_hint=model_hint,
                max_tokens=max_tokens,
                attempt=attempt,
            )
            if response:
                break

        if not response:
            return TaskResult(
                success=False, error_type="LLM_NO_RESPONSE",
                error_snippet="call_llm_via_magiclm returned None", track="GREENFIELD",
            )

        files = _parse(response)
        if not files:
            return TaskResult(
                success=False, error_type="NO_FILE_BLOCKS",
                error_snippet="LLM response contained no <file> blocks", track="GREENFIELD",
            )

        # Write and compile-gate the filled file
        for fpath, content in files.items():
            # Boundary check: reject paths outside ALLOWED_WRITE_ROOTS (C-065)
            from runner.constants import ALLOWED_WRITE_ROOTS
            if not any(fpath.startswith(root) for root in ALLOWED_WRITE_ROOTS):
                return TaskResult(
                    success=False, error_type="WRITE_BOUNDARY_VIOLATION",
                    error_snippet=f"LLM returned path outside write boundary: {fpath}",
                    track="GREENFIELD",
                )
            try:
                compile(content, fpath, "exec")
            except SyntaxError as exc:
                return TaskResult(
                    success=False, error_type="COMPILE_GATE_FAILURE",
                    error_snippet=f"{fpath}: {exc}", track="GREENFIELD",
                )
            (self.repo_root / fpath).write_text(content, encoding="utf-8")

        return TaskResult(
            success=True, track="GREENFIELD",
            files_written=list(files.keys()),
        )

    # ── Track 2: Differential ─────────────────────────────────────────────────

    def _run_track2(
        self,
        task_id: str,
        scope_text: str,
        sprint_id: str,
        model_hint: str,
        max_tokens: int,
    ) -> TaskResult:
        try:
            tmd = self.groom.generate_tmd(task_id, scope_text, sprint_id)
        except Exception as exc:
            return TaskResult(
                success=False, error_type="GROOMING_ERROR",
                error_snippet=str(exc)[:300], track="DIFFERENTIAL",
            )

        written: list[str] = []
        for artifact in tmd.get("impacted_artifacts", []):
            result = self._patch_artifact(
                task_id, artifact, scope_text, model_hint, max_tokens
            )
            if not result.success:
                return result
            written.extend(result.files_written)

        return TaskResult(success=True, track="DIFFERENTIAL", files_written=written)

    def _patch_artifact(
        self,
        task_id: str,
        artifact: dict[str, Any],
        scope_text: str,
        model_hint: str,
        max_tokens: int,
    ) -> TaskResult:
        fp = self.repo_root / artifact["file_path"]
        if not fp.is_file():
            return TaskResult(
                success=False, error_type="FILE_NOT_FOUND",
                error_snippet=f"Track 2 target not found: {artifact['file_path']}",
                track="DIFFERENTIAL",
            )

        engine = Track2PolymorphicEngine(fp)
        class_name: str | None = artifact.get("target_class")
        methods: list[str] = artifact.get("target_methods", [])

        if not methods:
            # No method target — ask LLM for module-level lines to append (e.g. router mount in main.py)
            return self._append_module_lines(task_id, fp, artifact["file_path"], scope_text, model_hint, max_tokens)

        written: list[str] = []
        for method_name in methods:
            result = self._patch_method(
                task_id, engine, method_name, class_name,
                scope_text, model_hint, max_tokens,
            )
            if not result.success:
                return result
            written.extend(result.files_written)
            engine._reload()  # reload after each splice

        return TaskResult(success=True, track="DIFFERENTIAL", files_written=written)

    def _append_module_lines(
        self,
        task_id: str,
        fp: Path,
        rel_path: str,
        scope_text: str,
        model_hint: str,
        max_tokens: int,
    ) -> TaskResult:
        """Module-level append mode: LLM returns lines to add at the end of the file (e.g. router mount)."""
        if self._llm_fn is not None:
            _call_llm: Callable[..., str | None] = self._llm_fn
        else:
            try:
                from runner.llm_codegen import call_llm_for_udcp
            except ImportError:
                return TaskResult(
                    success=False, error_type="IMPORT_ERROR",
                    error_snippet="call_llm_for_udcp not available", track="DIFFERENTIAL",
                )
            _call_llm = call_llm_for_udcp

        existing = fp.read_text(encoding="utf-8")
        prompt = (
            f"The file below needs new lines appended at the end.\n\n"
            f"Task: {scope_text[:1000]}\n\n"
            f"Current file content:\n{existing}\n\n"
            f"Return ONLY the new lines to append (imports + code). "
            f"No explanation. No file wrapper. Just the raw Python lines."
        )

        response = _call_llm(task_id=task_id, prompt=prompt, model_hint=model_hint,
                             max_tokens=1000, attempt=1)
        if not response:
            return TaskResult(success=False, error_type="LLM_NO_RESPONSE",
                              error_snippet="No response for module append", track="DIFFERENTIAL")

        # Strip code fences if present
        new_lines = re.sub(r"^```[a-z]*\n(.*)\n```$", r"\1", response.strip(), flags=re.DOTALL)
        updated = existing.rstrip() + "\n\n" + new_lines.strip() + "\n"
        try:
            compile(updated, rel_path, "exec")
        except SyntaxError as exc:
            return TaskResult(success=False, error_type="COMPILE_GATE_FAILURE",
                              error_snippet=f"{rel_path}: {exc}", track="DIFFERENTIAL")
        fp.write_text(updated, encoding="utf-8")
        return TaskResult(success=True, track="DIFFERENTIAL", files_written=[rel_path])

    def _patch_method(
        self,
        task_id: str,
        engine: Track2PolymorphicEngine,
        method_name: str,
        class_name: str | None,
        scope_text: str,
        model_hint: str,
        max_tokens: int,
    ) -> TaskResult:
        if self._llm_fn is not None:
            _call_llm: Callable[..., str | None] = self._llm_fn
        else:
            try:
                from runner.llm_codegen import call_llm_for_udcp
            except ImportError:
                return TaskResult(
                    success=False, error_type="IMPORT_ERROR",
                    error_snippet="call_llm_for_udcp not available", track="DIFFERENTIAL",
                )
            _call_llm = call_llm_for_udcp

        try:
            node_source = engine.extract_node_for_llm(method_name, class_name)
        except Track2SpliceError as exc:
            return TaskResult(
                success=False, error_type="EXTRACTION_ERROR",
                error_snippet=str(exc)[:300], track="DIFFERENTIAL",
            )

        target_label = f"{class_name}.{method_name}" if class_name else method_name
        prompt = (
            f"UDCP Track 2 — Method Logic Implementation\n\n"
            f"Implement the body of '{target_label}'. "
            f"Return ONLY the complete function definition "
            f"(the def line + body — no class wrapper, no imports, no decorators).\n\n"
            f"Task context:\n{scope_text[:2000]}\n\n"
            f"Current stub:\n```python\n{node_source}\n```\n\n"
            f"Return the filled function wrapped in triple backticks:\n"
            f"```python\n"
            f"def {method_name}(...):\n"
            f"    # your implementation\n"
            f"```"
        )

        response = _call_llm(
            task_id=task_id,
            prompt=prompt,
            model_hint=model_hint,
            max_tokens=max_tokens,
            attempt=1,
        )

        if not response:
            return TaskResult(
                success=False, error_type="LLM_NO_RESPONSE",
                error_snippet=f"No response for {target_label}", track="DIFFERENTIAL",
            )

        new_logic = _extract_function_block(response)
        if not new_logic:
            return TaskResult(
                success=False, error_type="NO_FUNCTION_BLOCK",
                error_snippet=f"Could not parse function block from LLM response for {target_label}",
                track="DIFFERENTIAL",
            )

        try:
            engine.splice_node_safely(method_name, new_logic, class_name)
        except Track2SpliceError as exc:
            return TaskResult(
                success=False, error_type="SPLICE_ERROR",
                error_snippet=str(exc)[:300], track="DIFFERENTIAL",
            )

        return TaskResult(
            success=True, track="DIFFERENTIAL",
            files_written=[str(engine.file_path.relative_to(self.repo_root))],
        )


# ── Helpers ───────────────────────────────────────────────────────────────────

def _parse_llm_files_local(response: str) -> dict[str, str]:
    """Minimal <file path="...">...</file> parser used when llm_codegen is not on sys.path."""
    from runner.constants import ALLOWED_WRITE_ROOTS
    # Strip surrounding code fence — Haiku sometimes wraps file blocks in ```python ... ```
    stripped = re.sub(r"^```[a-z]*\n(.*)\n```$", r"\1", response.strip(), flags=re.DOTALL)
    files: dict[str, str] = {}
    for m in re.finditer(r'<file\s+path=["\']([^"\']+)["\']>(.*?)</file>', stripped, re.DOTALL | re.IGNORECASE):
        path, content = m.group(1).strip(), m.group(2).strip()
        if any(path.startswith(r) for r in ALLOWED_WRITE_ROOTS):
            files[path] = content
    return files


def _extract_function_block(response: str) -> str | None:
    """Extract the first ```python ... ``` block containing a function definition."""
    match = _FUNC_BLOCK_RE.search(response)
    if match:
        return match.group(1).strip()
    # Fallback: look for bare 'def' line in response
    lines = response.splitlines()
    start = next(
        (i for i, ln in enumerate(lines) if re.match(r"(?:async\s+)?def\s+\w+", ln.strip())),
        None,
    )
    if start is None:
        return None
    return "\n".join(lines[start:]).strip()
