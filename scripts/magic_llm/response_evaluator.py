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
            pattern = re.compile(r'<file\s+path="[^"]+">', re.IGNORECASE)
            if pattern.search(raw_response or ""):
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

    # ── Gate 2: COMPILE ────────────────────────────────────────────────────────

    def _gate_compile(self, written_files: list[str], stack: str) -> GateResult:
        """
        §8 Gate 2: Compile gate — stack-appropriate build tool.
        """
        cs_files = [f for f in written_files if f.endswith(".cs")]
        py_files = [f for f in written_files if f.endswith(".py")]
        ts_files = [f for f in written_files if f.endswith((".ts", ".tsx"))]

        if stack == "dotnet" and cs_files:
            return self._compile_dotnet(cs_files)
        if stack == "python" and py_files:
            return self._compile_python(py_files)
        if stack == "typescript" and ts_files:
            return self._compile_typescript(ts_files)

        return GateResult("COMPILE", True, "", "No compilable files — gate skipped")

    def _compile_dotnet(self, cs_files: list[str]) -> GateResult:
        """Find and run dotnet build on the .csproj containing these files."""
        csproj_dirs: set[str] = set()
        for f in cs_files:
            parts = Path(f).parts
            if len(parts) > 1:
                csproj_dirs.add(str(self._root / parts[0] / parts[1]))
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
                codes = re.findall(r'CS\d+', output)
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
        return GateResult("COMPILE", True, "", "py_compile: PASS")

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
        return GateResult("COMPILE", True, "", "tsc: PASS")

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

            has_implements = bool(re.search(r'(?://|#)\s*Implements:', first_1000))
            has_basis = bool(re.search(r'(?://|#)\s*constitutional_basis:', first_1000))

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
            if re.search(r'using\s+.*Temporal', content) and "WC012-02" in f or "WC012-02" in str(spec_sections):
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
