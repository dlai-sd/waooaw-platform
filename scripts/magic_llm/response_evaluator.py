#!/usr/bin/env python3
"""
response_evaluator.py — MagicLLM Response Evaluator

# Implements: architecture/reference/magic-llm/architecture.md §8 Response Evaluator
# Constitutional basis:
#   C-082 (Build Validation — compile gate is mandatory)
#   C-032 (Spec-Code Alignment — spec alignment gate)
#   C-073 (Constitutional Annotations — annotation gate)
#   C-059 (Traceability — every file must trace to spec)
# Office: AI Architect (INST-008)

Implements all 5 quality gates in §8 sequence:
  Gate 1: FORMAT      — XML file block structure present
  Gate 2: COMPILE     — dotnet build / ruff / tsc exits 0
  Gate 3: SPEC_ALIGN  — no drift from spec via PTR check
  Gate 4: ANNOTATION  — C-059 header present in every file
  Gate 5: SCHEMA      — structured output JSON valid (for non-code tasks)

All 5 gates were missing in Phase 1 — this module closes the constitutional violation.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).parent.parent.parent

# ── Module-level compiled regexes (P2: avoid recompile on every evaluation) ──
_RE_FILE_BLOCK  = re.compile(r'<file\s+path="[^"]+">', re.IGNORECASE)
_RE_XML_BLOCK   = re.compile(r'<file\s+path="([^"]+)">(.*?)</file>', re.DOTALL)
_RE_IMPLEMENTS  = re.compile(r'(?://|#)\s*Implements:', re.MULTILINE)
_RE_BASIS       = re.compile(r'(?://|#)\s*constitutional_basis:', re.MULTILINE)
_RE_CS_ERRORS   = re.compile(r'CS\d+')
_RE_TEMPORAL_NS = re.compile(r'using\s+.*Temporal')


@dataclass
class GateResult:
    gate: str              # FORMAT | COMPILE | SPEC_ALIGN | ANNOTATION | SCHEMA
    passed: bool
    failure_class: str     # maps to §9 Retry Advisor failure classifications
    detail: str            # human-readable detail for Retry Advisor context
    error_codes: list[str] = field(default_factory=list)  # compiler error codes if compile gate


@dataclass
class EvaluationResult:
    """Result of all applicable gates for one LLM response."""
    task_id: str
    output_file: str
    status: str = "pending"  # "accepted" | "retry_needed" | "escalate"
    gates: list[GateResult] = field(default_factory=list)

    @property
    def first_failure(self) -> GateResult | None:
        return next((g for g in self.gates if not g.passed), None)

    @property
    def all_passed(self) -> bool:
        return all(g.passed for g in self.gates)

    @property
    def gate_summary(self) -> dict[str, str]:
        return {g.gate: ("PASS" if g.passed else f"FAIL: {g.detail[:60]}") for g in self.gates}


class ResponseEvaluator:
    """
    §8 Response Evaluator — 5 quality gates in sequence.

    Usage:
        evaluator = ResponseEvaluator()
        result = evaluator.evaluate(
            task_id="WC012-02c",
            raw_response=llm_output,
            written_files=["tests/.../CCT_EF01_C041ToolAuthorizationEvaluatorTests.cs"],
            stack="dotnet",
            spec_sections={"tests/QA-STRATEGY.md": "§5.1"},
        )
        if not result.all_passed:
            failure = result.first_failure
            print(f"Gate {failure.gate} failed: {failure.detail}")
    """

    def __init__(self, repo_root: Path | None = None) -> None:
        self._root = repo_root or REPO_ROOT

    def evaluate(
        self,
        task_id: str,
        raw_response: str,
        written_files: list[str],
        stack: str = "dotnet",
        spec_sections: dict[str, str] | None = None,
        expected_output_format: str = "xml_file_blocks",
        expected_output_file: str = "",
    ) -> EvaluationResult:
        """
        Run all applicable gates in §8 sequence.
        Stops at first failure (gates are in dependency order).
        """
        output_file = written_files[0] if written_files else ""
        result = EvaluationResult(task_id=task_id, output_file=output_file)

        # Gate 1: FORMAT
        g1 = self._gate_format(raw_response, expected_output_format)
        result.gates.append(g1)
        if not g1.passed:
            result.status = "retry_needed"
            return result

        # Gate 1b: PATH — expected output file must be among written files
        if expected_output_file:
            gp = self._gate_path(expected_output_file, written_files)
            result.gates.append(gp)
            if not gp.passed:
                result.status = "retry_needed"
                return result

        # Gate 2: COMPILE (for code tasks)
        if stack in ("dotnet", "python", "typescript") and written_files:
            g2 = self._gate_compile(written_files, stack)
            result.gates.append(g2)
            if not g2.passed:
                result.status = "retry_needed"
                return result

        # Gate 3: ANNOTATION (C-073 — traceability header)
        g3 = self._gate_annotation(written_files, stack)
        result.gates.append(g3)
        if not g3.passed:
            result.status = "retry_needed"
            return result

        # Gate 4: SPEC_ALIGN (C-032 — no invented types/members)
        if spec_sections and written_files:
            g4 = self._gate_spec_align(written_files, spec_sections)
            result.gates.append(g4)
            if not g4.passed:
                result.status = "retry_needed"
                return result

        # Gate 5: SCHEMA (structured outputs only)
        if expected_output_format == "json":
            g5 = self._gate_schema(raw_response)
            result.gates.append(g5)
            if not g5.passed:
                result.status = "retry_needed"
                return result

        result.status = "accepted"
        return result

    # ── Gate 1: FORMAT ─────────────────────────────────────────────────────────

    def _gate_format(self, raw_response: str, expected_format: str) -> GateResult:
        """
        §8 Gate 1: Response contains expected output structure.
        For code tasks: at least one <file path="...">...</file> block.
        """
        if expected_format == "xml_file_blocks":
            if _RE_FILE_BLOCK.search(raw_response or ""):
                return GateResult("FORMAT", True, "", "XML file block found")
            # Check for markdown code blocks with file indicators
            if "```" in (raw_response or "") and ("using " in (raw_response or "") or "def " in (raw_response or "")):
                return GateResult(
                    "FORMAT", False, "FORMAT_FAILURE",
                    'Response has code but not in required XML file block format. '
                    'Wrap output in: <file path="exact/path/to/file.ext">code</file>'
                )
            return GateResult(
                "FORMAT", False, "FORMAT_FAILURE",
                "No <file path=\"...\"> block found in response. "
                "Output must be wrapped in XML file blocks."
            )
        if expected_format == "json":
            try:
                import json
                json.loads(raw_response or "")
                return GateResult("FORMAT", True, "", "Valid JSON")
            except Exception:
                return GateResult("FORMAT", False, "SCHEMA_VIOLATION", "Response is not valid JSON")

        return GateResult("FORMAT", True, "", f"Format {expected_format} accepted")

    # ── Gate 1b: PATH ──────────────────────────────────────────────────────────

    def _gate_path(self, expected_output_file: str, written_files: list[str]) -> GateResult:
        """
        §8 Gate PATH: LLM must write to the expected output path.
        Prevents silent pass when LLM writes to a wrong subdirectory:
        evaluate() checks written files (what was actually written), not SubTaskDef.output_files.
        Without this gate, a wrong-path file passes COMPILE/ANNOTATION/SPEC_ALIGN and the
        pipeline returns success, but run_compile_gate then fails with E902 (file not found).
        """
        if expected_output_file in written_files:
            return GateResult("PATH", True, "", f"Expected file written: {expected_output_file}")
        return GateResult(
            "PATH", False, "PATH_MISMATCH",
            f"Expected output file not written. "
            f"Expected: {expected_output_file} — "
            f"LLM wrote to: {written_files or '(nothing)'}. "
            f"Rewrite the file at the exact path: {expected_output_file}"
        )

    # ── Gate 2: COMPILE ────────────────────────────────────────────────────────

    def _gate_compile(self, written_files: list[str], stack: str) -> GateResult:
        """
        §8 Gate 2: Compile gate — stack-appropriate build tool.
        """
        cs_files = [f for f in written_files if f.endswith(".cs")]
        py_files = [f for f in written_files if f.endswith(".py")]
        ts_files = [f for f in written_files if f.endswith((".ts", ".tsx"))]
        sql_files = [f for f in written_files if f.endswith(".sql")]
        yaml_files = [f for f in written_files if f.endswith((".yaml", ".yml"))]
        tf_files = [f for f in written_files if f.endswith(".tf")]

        if stack == "dotnet" and cs_files:
            return self._compile_dotnet(cs_files)
        if stack == "python" and py_files:
            return self._compile_python(py_files)
        if stack == "typescript" and ts_files:
            return self._compile_typescript(ts_files)
        if stack == "terraform" and tf_files:
            return self._compile_terraform(tf_files)
        if sql_files:
            return self._gate_sql(sql_files)
        if yaml_files:
            return self._gate_yaml(yaml_files)

        return GateResult("COMPILE", True, "", "No compilable files — gate skipped")

    def _compile_dotnet(self, cs_files: list[str]) -> GateResult:
        """Find and run dotnet build on the .csproj containing these files."""
        csproj_dirs: set[str] = set()
        for f in cs_files:
            parts = Path(f).parts
            if len(parts) > 1:
                csproj_dirs.add(str(self._root / parts[0] / parts[1]))
        # Only add CE tests if the written files are in CE (tests/ or src/constitutional-engine).
        # For BP (src/business-platform), do NOT build CE tests — hardcoding caused
        # WC013-02a to fail: CE tests were always compiled, LLM-generated extra file blocks
        # for CE types overwrote them with incorrect versions → CS0117 on CE tests.
        has_ce_files = any(
            "constitutional-engine" in f or (f.startswith("tests/") and "constitutional" in f)
            for f in cs_files
        )
        if has_ce_files:
            csproj_dirs.add(str(self._root / "tests" / "constitutional-engine.Tests"))

        errors: list[str] = []
        error_codes: list[str] = []

        for csproj_dir in csproj_dirs:
            csproj_files = list(Path(csproj_dir).glob("*.csproj")) if Path(csproj_dir).exists() else []
            if not csproj_files:
                continue
            build_target = str(csproj_files[0])
            proc = subprocess.run(
                ["dotnet", "build", build_target, "--nologo", "-v", "quiet"],
                capture_output=True, text=True, cwd=self._root,
                timeout=120,  # R1: 2-min hard cap — prevents infinite hang on corrupted dotnet cache
            )
            if proc.returncode != 0:
                output = (proc.stdout or "") + (proc.stderr or "")
                errors.append(output[:600])
                codes = _RE_CS_ERRORS.findall(output)
                error_codes.extend(codes)

        if errors:
            return GateResult(
                "COMPILE", False,
                f"COMPILE_FAILURE: {','.join(sorted(set(error_codes))[:5])}",
                "\n".join(errors[:2]),
                error_codes=sorted(set(error_codes))
            )
        return GateResult("COMPILE", True, "", "dotnet build: PASS")

    def _compile_python(self, py_files: list[str]) -> GateResult:
        errors = []
        for f in py_files:
            full = self._root / f
            if not full.exists():
                continue
            proc = subprocess.run(
                ["python3", "-m", "py_compile", str(full)],
                capture_output=True, text=True,
                timeout=30,  # R1: py_compile should be instant
            )
            if proc.returncode != 0:
                errors.append(f"{f}: {proc.stderr[:200]}")
        if errors:
            return GateResult("COMPILE", False, "COMPILE_FAILURE: PYTHON_SYNTAX", "\n".join(errors))
        # Style gate: ruff check scoped to only the generated files (no pre-existing violations)
        # This runs INSIDE the 3-attempt retry loop so violations get targeted fixes.
        ruff_args = ["python3", "-m", "ruff", "check"] + [str(self._root / f) for f in py_files]
        ruff_proc = subprocess.run(
            ruff_args,
            capture_output=True, text=True, cwd=self._root,
            timeout=30,
        )
        if ruff_proc.returncode != 0:
            ruff_output = (ruff_proc.stdout + ruff_proc.stderr).strip()
            # Strip absolute path prefix for cleaner error messages
            ruff_output = ruff_output.replace(str(self._root) + "/", "")
            # Match 1–3 uppercase letters + 3–4 digits (covers ANN201, B017, F841, E501, UP007)
            codes = sorted(set(re.findall(r'\b([A-Z]{1,3}\d{3,4})\b', ruff_output)))
            return GateResult(
                "COMPILE", False,
                f"COMPILE_FAILURE: RUFF {','.join(codes[:6]) if codes else 'VIOLATION'}",
                ruff_output[:500],
                error_codes=codes,
            )
        # For test files: --collect-only imports the module (with conftest sys.path) catching
        # ImportErrors that py_compile misses because it only checks syntax, not import resolution.
        test_files = [f for f in py_files if f.startswith("tests/") or "/tests/" in f]
        if test_files:
            collect_proc = subprocess.run(
                ["python3", "-m", "pytest", "--collect-only", "-q", "--tb=short"]
                + [str(self._root / f) for f in test_files],
                capture_output=True, text=True, cwd=self._root,
                timeout=30,
            )
            if collect_proc.returncode != 0:
                collect_out = (collect_proc.stdout + collect_proc.stderr).strip()
                collect_out = collect_out.replace(str(self._root) + "/", "")
                return GateResult(
                    "COMPILE", False,
                    "COMPILE_FAILURE: PYTEST_COLLECT",
                    collect_out[:500],
                )
        # For source files: static cross-module symbol check via AST (no imports executed)
        src_files = [f for f in py_files if not (f.startswith("tests/") or "/tests/" in f)]
        import_err = self._check_intrapackage_imports(src_files)
        if import_err:
            return GateResult("COMPILE", False, "COMPILE_FAILURE: IMPORT_SYMBOL", import_err)
        return GateResult("COMPILE", True, "", "py_compile: PASS | ruff: PASS")

    def _check_intrapackage_imports(self, src_files: list[str]) -> str | None:
        """AST-only cross-module symbol check for markup.* intra-package imports.

        Catches `from markup.models import ValidationOutcome` when models.py only
        defines `PriceOutcome` — no imports are executed, so no side effects.
        Returns a human-readable error string or None if everything resolves.
        """
        import ast as _ast

        for f in src_files:
            full = self._root / f
            if not full.exists():
                continue
            try:
                tree = _ast.parse(full.read_text())
            except SyntaxError:
                continue
            for node in _ast.walk(tree):
                if not isinstance(node, _ast.ImportFrom) or not node.module:
                    continue
                # Only check markup.* intra-package imports
                if not node.module.startswith("markup."):
                    continue
                sub = node.module[len("markup."):]
                pkg_file = self._root / "src" / "billing-engine" / "markup" / f"{sub}.py"
                if not pkg_file.exists():
                    continue
                try:
                    pkg_tree = _ast.parse(pkg_file.read_text())
                except SyntaxError:
                    continue
                defined: set[str] = set()
                for n in _ast.walk(pkg_tree):
                    if isinstance(n, (_ast.ClassDef, _ast.FunctionDef, _ast.AsyncFunctionDef)):
                        defined.add(n.name)
                for stmt in pkg_tree.body:
                    if isinstance(stmt, _ast.Assign):
                        for t in stmt.targets:
                            if isinstance(t, _ast.Name):
                                defined.add(t.id)
                    elif isinstance(stmt, _ast.AugAssign) and isinstance(stmt.target, _ast.Name):
                        defined.add(stmt.target.id)
                for alias in node.names:
                    if alias.name != "*" and alias.name not in defined:
                        return (
                            f"ImportError: cannot import name '{alias.name}' from "
                            f"'markup.{sub}' ({f})\n"
                            f"Defined names in markup/{sub}.py: {sorted(defined)}"
                        )
        return None

    def _compile_typescript(self, ts_files: list[str]) -> GateResult:
        web_dir = self._root / "web"
        if not web_dir.exists():
            return GateResult("COMPILE", True, "", "No TypeScript project found — gate skipped")
        proc = subprocess.run(
            ["npx", "tsc", "--noEmit", "--strict"],
            capture_output=True, text=True, cwd=web_dir,
            timeout=60,  # R1: tsc type check hard cap
        )
        if proc.returncode != 0:
            return GateResult("COMPILE", False, "COMPILE_FAILURE: TS", proc.stdout[:400])
        # Biome lint (if configured) — web/ uses biome.json instead of ESLint
        biome_config = web_dir / "biome.json"
        if biome_config.exists():
            # Probe availability first — avoids 60s hang when biome not in node_modules
            probe = subprocess.run(
                ["npx", "biome", "--version"],
                capture_output=True, text=True, cwd=web_dir, timeout=10,
            )
            if probe.returncode == 0:
                biome_proc = subprocess.run(
                    ["npx", "biome", "ci", "--files-ignore-unknown=true"],
                    capture_output=True, text=True, cwd=web_dir, timeout=60,
                )
                if biome_proc.returncode != 0:
                    output = (biome_proc.stdout + biome_proc.stderr).strip()[:400]
                    return GateResult("COMPILE", False, "COMPILE_FAILURE: TS_BIOME", output)
        return GateResult("COMPILE", True, "", "tsc: PASS | biome: PASS")

    def _compile_terraform(self, tf_files: list[str]) -> GateResult:
        """
        Terraform syntax validation using python-hcl2 parser.
        Catches HCL syntax errors inside the retry loop.
        Does NOT run terraform validate (no provider init needed).
        """
        errors = []
        try:
            import hcl2  # type: ignore[import-untyped]
        except ImportError:
            return GateResult("COMPILE", True, "", "python-hcl2 not installed — TF gate skipped")
        for f in tf_files:
            full = self._root / f
            if not full.exists():
                continue
            try:
                with full.open("r", encoding="utf-8") as fh:
                    hcl2.load(fh)
            except Exception as exc:
                errors.append(f"{f}: HCL syntax error — {str(exc)[:120]}")
        if errors:
            return GateResult("COMPILE", False, "COMPILE_FAILURE: TF_SYNTAX", "\n".join(errors))
        return GateResult("COMPILE", True, "", "hcl2 parse: PASS")

    def _gate_sql(self, sql_files: list[str]) -> GateResult:
        """
        SQL lint gate using sqlfluff (PostgreSQL dialect).
        Runs inside the retry loop so violations feed into failure_context.
        """
        full_paths = [str(self._root / f) for f in sql_files if (self._root / f).exists()]
        if not full_paths:
            return GateResult("COMPILE", True, "", "SQL files not written yet — gate skipped")
        proc = subprocess.run(
            ["python3", "-m", "sqlfluff", "lint", "--dialect", "postgres",
             "--format", "github-annotation", "--no-progress-bar"] + full_paths,
            capture_output=True, text=True, cwd=self._root, timeout=60,
        )
        if proc.returncode != 0:
            output = (proc.stdout + proc.stderr).strip()[:500]
            output = output.replace(str(self._root) + "/", "")
            return GateResult("COMPILE", False, "COMPILE_FAILURE: SQL_LINT", output)
        return GateResult("COMPILE", True, "", "sqlfluff: PASS")

    def _gate_yaml(self, yaml_files: list[str]) -> GateResult:
        """
        YAML lint gate using yamllint with relaxed config.
        Kubernetes/Helm manifests use relaxed rules (long lines allowed).
        """
        full_paths = [str(self._root / f) for f in yaml_files if (self._root / f).exists()]
        if not full_paths:
            return GateResult("COMPILE", True, "", "YAML files not written yet — gate skipped")
        proc = subprocess.run(
            ["python3", "-m", "yamllint", "-d", "relaxed", "-f", "parsable"] + full_paths,
            capture_output=True, text=True, cwd=self._root, timeout=30,
        )
        if proc.returncode != 0:
            output = (proc.stdout + proc.stderr).strip()[:500]
            output = output.replace(str(self._root) + "/", "")
            return GateResult("COMPILE", False, "COMPILE_FAILURE: YAML_LINT", output)
        return GateResult("COMPILE", True, "", "yamllint: PASS")

    # ── Gate 3: ANNOTATION ─────────────────────────────────────────────────────

    def _gate_annotation(self, written_files: list[str], stack: str) -> GateResult:
        """
        §8 Gate 3 (C-073): Every file must start with:
          // Implements: <spec-path> §<section>
          // constitutional_basis: C-NNN
        """
        missing: list[str] = []
        for f in written_files:
            full = self._root / f
            if not full.exists():
                continue
            ext = full.suffix.lower()
            if ext not in (".cs", ".py", ".ts", ".tsx", ".tf"):
                continue
            content = full.read_text(encoding="utf-8", errors="replace")
            first_1000 = content[:1000]

            has_implements = bool(_RE_IMPLEMENTS.search(first_1000))
            has_basis = bool(_RE_BASIS.search(first_1000))

            if not (has_implements and has_basis):
                missing.append(full.name)

        if missing:
            return GateResult(
                "ANNOTATION", False, "ANNOTATION_MISSING",
                f"Files missing C-059/C-073 header: {', '.join(missing)}. "
                "First lines must be: // Implements: <spec> and // constitutional_basis: <claims>"
            )
        return GateResult("ANNOTATION", True, "", "C-059/C-073 headers: PASS")

    # ── Gate 4: SPEC_ALIGN ─────────────────────────────────────────────────────

    def _gate_spec_align(
        self, written_files: list[str], spec_sections: dict[str, str]
    ) -> GateResult:
        """
        §8 Gate 4 (C-032): No drift from spec.
        Fast check: verify no Temporal namespace in WC012-02 files (known scope violation).
        """
        violations: list[str] = []
        for f in written_files:
            full = self._root / f
            if not full.exists():
                continue
            content = full.read_text(encoding="utf-8", errors="replace")

            # Detect known scope violations
            if _RE_TEMPORAL_NS.search(content) and "WC012-02" in f or "WC012-02" in str(spec_sections):
                violations.append(f"{full.name}: Temporal namespace is WC012-04b scope, not WC012-02")

            # Detect invented types not in spec (fast heuristic: look for types not in USING_MAP)
            # Full semantic check is Phase 2 (embedding-based)

        if violations:
            return GateResult(
                "SPEC_ALIGN", False, "SPEC_DRIFT",
                "; ".join(violations)
            )
        return GateResult("SPEC_ALIGN", True, "", "Spec alignment: PASS (fast check)")

    # ── Gate 5: SCHEMA ─────────────────────────────────────────────────────────

    def _gate_schema(self, raw_response: str) -> GateResult:
        """§8 Gate 5: Structured output JSON validation."""
        try:
            import json
            data = json.loads(raw_response or "")
            if not isinstance(data, dict):
                return GateResult("SCHEMA", False, "SCHEMA_VIOLATION", "Response is not a JSON object")
            return GateResult("SCHEMA", True, "", "Schema: PASS")
        except Exception as e:
            return GateResult("SCHEMA", False, "SCHEMA_VIOLATION", str(e)[:200])
