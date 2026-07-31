r"""
Tests for bootstrap_sprint_sims.py — C-086 SIM stub auto-generator.

Regression coverage for two bug classes:
  BUG-1: _extract_wc_tasks regex WC\d{3}-\d{2} missed letter-suffix task IDs
          (WC027-01a, WC027-01b) -> fell back to "WC-NNN task" -> PENDING verdict
          Fixed: regex now WC\d{3}-\d{2}[a-z]?
  BUG-2: runner_integrity_check.py called run_runner_integrity_checks() with no
          namespace -> empty dict -> all symbols reported missing -> FAIL
          Fixed: script passes vars(autonomous_sprint_runner) to the probe
"""
from __future__ import annotations

import sys
import textwrap
from pathlib import Path

import pytest

# bootstrap_sprint_sims lives in scripts/ — add it to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

import bootstrap_sprint_sims as bss


# ── _extract_wc_tasks ──────────────────────────────────────────────────────

class TestExtractWcTasks:
    """BUG-1 regression: letter-suffix task IDs must be parsed."""

    def _make_wc(self, tmp_path: Path, rows: str) -> Path:
        wc = tmp_path / "WC027-test.md"
        wc.write_text(textwrap.dedent(f"""\
            # Work Contract
            ## Tasks
            | Task | Scope | model_hint | Status |
            |---|---|---|---|
            {rows}
        """))
        return wc

    def test_plain_task_ids_parsed(self, tmp_path):
        wc = self._make_wc(tmp_path, "| WC027-01 | `src/foo/models.py` — Pydantic models | auto | TODO |")
        tasks = bss._extract_wc_tasks(wc)
        assert "WC027-01" in tasks
        assert "models" in tasks["WC027-01"].lower()

    def test_letter_suffix_a_parsed(self, tmp_path):
        """Regression: WC027-01a was not matched before the fix."""
        wc = self._make_wc(tmp_path, "| WC027-01a | `src/foo/models.py` — Pydantic models | reasoning | TODO |")
        tasks = bss._extract_wc_tasks(wc)
        assert "WC027-01a" in tasks, "letter-suffix task IDs must be extracted"

    def test_letter_suffix_b_parsed(self, tmp_path):
        """Regression: WC027-01b was not matched before the fix."""
        wc = self._make_wc(tmp_path, "| WC027-01b | `src/foo/router.py` — FastAPI router | auto | TODO |")
        tasks = bss._extract_wc_tasks(wc)
        assert "WC027-01b" in tasks

    def test_mixed_plain_and_suffix_all_parsed(self, tmp_path):
        rows = "\n".join([
            "| WC027-01a | `markup/models.py` — Pydantic models | reasoning | TODO |",
            "| WC027-01b | `markup/router.py` — FastAPI router prefix /pricing | auto | TODO |",
            "| WC027-02  | `tests/test_markup.py` — unit tests | auto | TODO |",
        ])
        wc = self._make_wc(tmp_path, rows)
        tasks = bss._extract_wc_tasks(wc)
        assert set(tasks.keys()) == {"WC027-01a", "WC027-01b", "WC027-02"}

    def test_empty_wc_returns_empty_dict(self, tmp_path):
        wc = tmp_path / "WC027-empty.md"
        wc.write_text("# No task table here\n")
        assert bss._extract_wc_tasks(wc) == {}


# ── _classify_task ─────────────────────────────────────────────────────────

class TestClassifyTask:
    """Known-safe patterns must produce PASS; complex patterns must produce PENDING."""

    @pytest.mark.parametrize("scope,expected", [
        ("`markup/models.py` — Pydantic models", "PASS"),
        ("`markup/router.py` — FastAPI router prefix /pricing", "PASS"),
        ("`tests/test_markup.py` — unit tests ≥90% coverage", "PASS"),
        ("`wallet/cache.py` — Redis cache layer 30s TTL", "PASS"),
        ("`migrations/001_init.sql` — schema migration", "PASS"),
        ("`health_check.py` — /health endpoint", "PASS"),
        # letter-suffix scope previously fell back to "WC-027 task" → PENDING
        ("WC-027 task", "PENDING"),   # fallback scope before fix → must stay PENDING
    ])
    def test_classification(self, scope, expected):
        assert bss._classify_task(scope) == expected

    @pytest.mark.parametrize("scope", [
        "`payment/razorpay.py` — webhook handler",
        "`auth/jwt_middleware.py` — JWT validation",
        "`temporal/saga.py` — Temporal workflow",
        "`wallet/encryption.py` — secret key rotation",
    ])
    def test_sensitive_patterns_are_pending(self, scope):
        assert bss._classify_task(scope) == "PENDING"


# ── full bootstrap produces correct verdicts for split tasks ───────────────

class TestBootstrapProducesPassForSplitTasks:
    """BUG-1 integration regression: WC027-01a/01b must auto-PASS, not PENDING."""

    def _make_state(self, tmp_path: Path, tasks: list[str]) -> Path:
        tasks_yaml = "\n".join(f"  - {t}" for t in tasks)
        state = tmp_path / "constitution" / "PROJECT_STATE.md"
        state.parent.mkdir(parents=True)
        # Format must match _read_sprint_state regex: ## SPRINT_STATE_MACHINE ... ```yaml ... ```
        state.write_text(
            "## SPRINT_STATE_MACHINE\n"
            "```yaml\n"
            "current_sprint: WC-027\n"
            "tasks_remaining:\n"
            f"{tasks_yaml}\n"
            "```\n"
        )
        return state

    def _make_wc(self, tmp_path: Path) -> Path:
        (tmp_path / "work-contracts").mkdir(parents=True, exist_ok=True)
        wc = tmp_path / "work-contracts" / "WC027-markup-engine.md"
        wc.write_text(textwrap.dedent("""\
            # WC-027
            ## Tasks
            | Task | Scope | model_hint | Status |
            |---|---|---|---|
            | WC027-01a | `markup/models.py` — Pydantic models | reasoning | TODO |
            | WC027-01b | `markup/router.py` — FastAPI router | auto | TODO |
            | WC027-02 | `tests/test_markup.py` — unit tests | auto | TODO |
        """))
        return wc

    def test_split_tasks_bootstrap_to_pass(self, tmp_path, monkeypatch):
        """Regression: before fix all three tasks bootstrapped to PENDING."""
        self._make_state(tmp_path, ["WC027-01a", "WC027-01b", "WC027-02"])
        self._make_wc(tmp_path)
        sim_dir = tmp_path / "simulation"
        sim_dir.mkdir()

        monkeypatch.setattr(bss, "STATE_FILE", tmp_path / "constitution" / "PROJECT_STATE.md")
        monkeypatch.setattr(bss, "WC_DIR", tmp_path / "work-contracts")
        monkeypatch.setattr(bss, "SIM_DIR", sim_dir)

        result = bss.main()
        assert result == 0

        created = list(sim_dir.glob("SIM-PL-002-*.md"))
        assert len(created) == 3

        for sim_file in created:
            content = sim_file.read_text()
            assert "VERDICT: ✅ PASS" in content, (
                f"{sim_file.name} must have PASS verdict — "
                "models/router/tests are known-safe patterns"
            )

    def test_fallback_scope_stays_pending(self, tmp_path, monkeypatch):
        """Tasks not found in WC file → fallback scope → PENDING (human review required)."""
        self._make_state(tmp_path, ["WC027-99"])
        (tmp_path / "work-contracts").mkdir(parents=True, exist_ok=True)
        (tmp_path / "work-contracts" / "WC027-empty.md").write_text("# No task table\n")
        sim_dir = tmp_path / "simulation"
        sim_dir.mkdir()

        monkeypatch.setattr(bss, "STATE_FILE", tmp_path / "constitution" / "PROJECT_STATE.md")
        monkeypatch.setattr(bss, "WC_DIR", tmp_path / "work-contracts")
        monkeypatch.setattr(bss, "SIM_DIR", sim_dir)

        bss.main()
        created = list(sim_dir.glob("SIM-PL-002-WC027-99-*.md"))
        assert len(created) == 1
        assert "PENDING" in created[0].read_text()


# ── runner_integrity_check.py end-to-end (BUG-2 regression) ───────────────

class TestRunnerIntegrityCheckScript:
    """BUG-2 regression: standalone script must pass its own probe end-to-end."""

    def test_main_returns_zero(self):
        """Regression: script called run_runner_integrity_checks() with empty
        namespace (no args) → all symbols missing → exit 1.
        Fix: passes vars(autonomous_sprint_runner) — must now return 0."""
        scripts_dir = Path(__file__).parent.parent.parent / "scripts"
        sys.path.insert(0, str(scripts_dir))
        try:
            import runner_integrity_check
            result = runner_integrity_check.main()
        finally:
            sys.path.remove(str(scripts_dir))
        assert result == 0, (
            "runner_integrity_check.main() must return 0 — "
            "ensure it passes vars(autonomous_sprint_runner) not empty dict"
        )
