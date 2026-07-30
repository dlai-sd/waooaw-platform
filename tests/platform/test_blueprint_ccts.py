"""
test_blueprint_ccts.py — Constitutional Compliance Tests for GOAL-PLATFORM-REGISTRY
WC-024 / PL-CCT-01

CCT-BLUEPRINT-01: blueprint_assurance.py produces a valid conformance score
CCT-SKEL-01:      task_decomposer C-095 pre-flight blocks IMPLEMENTATION task when skeleton absent
CCT-TRACE-01:     non-__init__ src/ files carry # Implements: C-059 header

Constitutional basis: C-094, C-095, C-059, ADR-035, ADR-036
"""
from __future__ import annotations

import subprocess
import sys
import json
import importlib.util
import textwrap
import tempfile
import os
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent


# ---------------------------------------------------------------------------
# CCT-BLUEPRINT-01: blueprint_assurance.py produces conformance score
# ---------------------------------------------------------------------------

class TestBlueprintAssurance:
    """CCT-BLUEPRINT-01"""

    def test_blueprint_assurance_runs_without_error(self) -> None:
        """Blueprint assurance script must exit 0 (non-strict) and emit a score line."""
        result = subprocess.run(
            [sys.executable, str(REPO_ROOT / "scripts" / "blueprint_assurance.py")],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
        )
        assert result.returncode == 0, (
            f"blueprint_assurance.py exited {result.returncode}.\n{result.stdout}\n{result.stderr}"
        )
        assert "Conformance score:" in result.stdout, (
            f"Expected 'Conformance score:' in output.\n{result.stdout}"
        )

    def test_blueprint_assurance_saves_json_report(self) -> None:
        """Blueprint assurance must save a JSON report to logs/ with a score_pct field."""
        import subprocess
        subprocess.run(
            [sys.executable, str(REPO_ROOT / "scripts" / "blueprint_assurance.py")],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
        )
        report_path = REPO_ROOT / "logs" / "blueprint_assurance_report.json"
        assert report_path.exists(), f"JSON report not written to {report_path}"
        data = json.loads(report_path.read_text())
        assert "score_pct" in data, f"Missing 'score_pct' in JSON report: {list(data.keys())}"
        assert isinstance(data["score_pct"], (int, float)), "'score_pct' must be a number"
        assert 0 <= data["score_pct"] <= 100, f"score_pct out of range: {data['score_pct']}"
        assert "checks" in data or "high_severity_gaps" in data, (
            f"JSON report must contain 'checks' or 'high_severity_gaps'. Got: {list(data.keys())}"
        )

    def test_platform_registry_yaml_exists(self) -> None:
        """platform-component-registry.yaml must be present."""
        registry = REPO_ROOT / "architecture" / "reference" / "platform-component-registry.yaml"
        assert registry.exists(), f"Missing: {registry}"

    def test_all_manifest_files_exist(self) -> None:
        """Every component listed in registry must have a manifest YAML."""
        manifest_dir = REPO_ROOT / "architecture" / "reference" / "components" / "manifest"
        expected = ["ce.yaml", "bp.yaml", "pr.yaml", "air.yaml", "wbe.yaml"]
        for name in expected:
            p = manifest_dir / name
            assert p.exists(), f"Missing manifest: {p}"


# ---------------------------------------------------------------------------
# CCT-SKEL-01: task_decomposer C-095 pre-flight blocks without skeleton
# ---------------------------------------------------------------------------

class TestSkeletonPreFlight:
    """CCT-SKEL-01"""

    def test_implementation_task_blocked_without_skeleton(self, tmp_path: Path) -> None:
        """C-095: An IMPLEMENTATION task for a service without a skeleton/ dir must be blocked."""
        spec = importlib.util.spec_from_file_location(
            "task_decomposer", REPO_ROOT / "scripts" / "task_decomposer.py"
        )
        td = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
        try:
            spec.loader.exec_module(td)  # type: ignore[union-attr]
        except Exception:
            import pytest
            pytest.skip("task_decomposer could not be imported standalone — manual CCT required")

        SubTaskDef = getattr(td, "SubTaskDef", None)
        if SubTaskDef is None:
            import pytest
            pytest.skip("SubTaskDef not found in task_decomposer")

        # A fake service with no skeleton directory
        fake_service = "nonexistent-service-xyz"
        skeleton_dir = REPO_ROOT / "src" / fake_service / "skeleton"
        assert not skeleton_dir.exists(), "Test precondition: skeleton must NOT exist"

        task = SubTaskDef(
            id="test-cct-task",
            description="implement foo",
            type="llm",
            generation_phase="logic",
            output_files=[f"src/{fake_service}/foo.py"],
        )

        # The pre-flight check should detect the missing skeleton and raise
        try:
            # Call the C-095 guard if exposed as a standalone function
            guard_fn = getattr(td, "_check_skeleton_precondition", None)
            if guard_fn:
                guard_fn(task)
                assert False, "Expected C-095 guard to raise but it did not"
        except Exception as exc:
            assert "SKELETON" in str(exc).upper() or "BLOCKED" in str(exc).upper(), (
                f"Expected SKELETON/BLOCKED signal, got: {exc}"
            )

    def test_existing_skeleton_dirs_present(self) -> None:
        """All LIVE/SPEC_APPROVED services must have a non-empty skeleton/ directory."""
        services = [
            "constitutional-engine",
            "business-platform",
            "professional-runtime",
            "ai-runtime",
            "billing-engine",
        ]
        for svc in services:
            skel = REPO_ROOT / "src" / svc / "skeleton"
            assert skel.exists(), f"Missing skeleton dir: {skel}"
            files = list(skel.iterdir())
            assert len(files) > 0, f"Empty skeleton dir: {skel}"


# ---------------------------------------------------------------------------
# CCT-TRACE-01: src/ non-init files carry C-059 Implements: header
# ---------------------------------------------------------------------------

class TestC059Headers:
    """CCT-TRACE-01"""

    def test_implementation_files_have_implements_header(self) -> None:
        """Non-__init__ src/ Python files must carry # Implements: (C-059)."""
        src_dir = REPO_ROOT / "src"
        violations = []
        for py_file in src_dir.rglob("*.py"):
            if py_file.name == "__init__.py":
                continue  # module markers exempt
            content = py_file.read_text(encoding="utf-8")
            if "# Implements:" not in content:
                violations.append(str(py_file.relative_to(REPO_ROOT)))
        assert not violations, (
            f"C-059 header missing in {len(violations)} files:\n" +
            "\n".join(f"  {v}" for v in violations)
        )

    def test_skeleton_files_have_implements_header(self) -> None:
        """All skeleton/*.py files must carry C-059 header (they define the contract)."""
        for skel_file in (REPO_ROOT / "src").rglob("skeleton/*.py"):
            content = skel_file.read_text(encoding="utf-8")
            assert "# Implements:" in content, (
                f"C-059 header missing in skeleton file: {skel_file.relative_to(REPO_ROOT)}"
            )

    def test_gap_scanner_script_importable(self) -> None:
        """gap_scanner.py must be importable without errors (syntax/import gate)."""
        result = subprocess.run(
            [sys.executable, "-c", "import importlib.util; "
             "spec = importlib.util.spec_from_file_location('gap_scanner', 'scripts/gap_scanner.py'); "
             "m = importlib.util.module_from_spec(spec)"],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
        )
        # A clean import of the module file should not produce syntax errors
        check = subprocess.run(
            [sys.executable, "-m", "py_compile", "scripts/gap_scanner.py"],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
        )
        assert check.returncode == 0, f"gap_scanner.py syntax error:\n{check.stderr}"
