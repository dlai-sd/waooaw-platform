"""
tests/test_groom_sprint.py — Unit tests for scripts/groom_sprint.py

Tests cover:
- _find_wc_file: locating WC files by sprint key
- _parse_wc_tasks: table-format and header-format WC files
- _already_groomed: sprint detection in TASK_HANDLERS
- _validate_generated_entry: syntax and structure validation
- _inject_task_handler: injection into runner file at anchor
- _inject_manifest_entry: injection into sprint_state at anchor
- _read_current_sprint: reading current sprint from PROJECT_STATE

Constitutional basis: C-086 (simulation before execution)
IB: IB-022 — groom_sprint.py
"""

from __future__ import annotations

import sys
import textwrap
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Add scripts/ to path so we can import groom_sprint
SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import groom_sprint


# ─────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────

SAMPLE_WC_TABLE = textwrap.dedent("""
# WC-027 — Billing Engine: Markup & Bundle Engine

## Tasks

| Task ID | Scope | model_hint | Status |
|---|---|---|---|
| WC027-01 | SQLAlchemy models for MarkupRule, BundleItem | `auto` | OPEN |
| WC027-02 | IMarkupEngine.derive_bundle_cost_floor() implementation | `reasoning` | OPEN |
| WC027-03 | Redis caching layer for markup lookups | `auto` | OPEN |
""").strip()

SAMPLE_WC_HEADERS = textwrap.dedent("""
# WC-027 — Billing Engine

### WC027-01 — SQLAlchemy Models

**Scope:** SQLAlchemy models for MarkupRule, BundleItem
**model_hint:** `auto`

### WC027-02 — IMarkupEngine Implementation

**Scope:** IMarkupEngine.derive_bundle_cost_floor() implementation
**model_hint:** `reasoning`
""").strip()

SAMPLE_RUNNER_WITH_ANCHOR = textwrap.dedent("""
TASK_HANDLERS = {
    "WC026-05": {
        "subtasks": []
    },
    # ── GROOMER INJECTION POINT — groom_sprint.py injects new sprint handlers here ──
    # ════════ WC-013 ════════
}
""")

SAMPLE_STATE_WITH_ANCHOR = textwrap.dedent("""
SPRINT_TASK_MANIFEST: dict[str, list[str]] = {
    "WC-025": ["WC025-01", "WC025-02"],
    "WC-026": ["WC026-01", "WC026-02"],
    # ── GROOMER MANIFEST INJECTION POINT — groom_sprint.py injects new sprint manifest here ──
}
""")

VALID_SUBTASKDEF_ENTRY = textwrap.dedent("""
"WC027-01": {
    "subtasks": [
        SubTaskDef(
            id="WC027-01a",
            description="Implement SQLAlchemy models for MarkupRule and BundleItem",
            type="llm",
            depends_on=[],
            compile_gate="py_compile",
            service_dir="src/billing-engine",
            wc_task_id="WC027-01",
            stack="python",
            output_files=[
                "src/billing-engine/models/markup.py",
            ],
            inject_source_files=[
                "src/billing-engine/skeleton/wbe_interfaces.py",
            ],
            spec_sections={
                "work-contracts/WC-027-markup.md": "WC027-01",
            },
            constitutional_check=(
                "Implement MarkupRule and BundleItem SQLAlchemy models.\\n"
                "DO NOT change signatures — implement bodies only (ADR-036).\\n"
                "Type annotations optional in scaffold — polish pass enforces ANN001."
            ),
            model_hint="auto",
            max_tokens=4000,
        ),
        SubTaskDef(
            id="WC027-01b",
            description="Add complete type annotations and fix ruff style (ANN001/ANN201 enforcement)",
            type="llm",
            depends_on=["WC027-01a"],
            compile_gate="ruff",
            service_dir="src/billing-engine",
            wc_task_id="WC027-01",
            stack="python",
            output_files=[
                "src/billing-engine/models/markup.py",
            ],
            inject_source_files=[
                "src/billing-engine/models/markup.py",
            ],
            spec_sections={
                "work-contracts/WC-027-markup.md": "WC027-01",
            },
            constitutional_check=(
                "POLISH PASS — type annotation enforcement only.\\n"
                "Add type annotations to ALL function parameters (ANN001).\\n"
                "DO NOT change function names, business logic, or structure."
            ),
            model_hint="auto",
            max_tokens=3000,
        ),
        SubTaskDef(
            id="WC027-01c",
            description="Write pytest tests for SQLAlchemy models",
            type="llm",
            depends_on=["WC027-01b"],
            compile_gate="ruff",
            service_dir="src/billing-engine",
            wc_task_id="WC027-01",
            stack="python",
            output_files=[
                "tests/billing-engine/test_markup.py",
            ],
            inject_source_files=[
                "src/billing-engine/models/markup.py",
            ],
            spec_sections={
                "work-contracts/WC-027-markup.md": "WC027-01",
            },
            constitutional_check=(
                "TEST PASS — write pytest tests against the provided implementation."
            ),
            model_hint="reasoning",
            max_tokens=6000,
        ),
    ]
},
""").strip()


# ─────────────────────────────────────────────────────────────
# _parse_wc_tasks: table format
# ─────────────────────────────────────────────────────────────

class TestParseWcTasksTableFormat:
    def test_parses_three_tasks(self, tmp_path):
        wc_file = tmp_path / "WC-027-markup.md"
        wc_file.write_text(SAMPLE_WC_TABLE)
        tasks = groom_sprint._parse_wc_tasks(wc_file, "WC027")
        assert len(tasks) == 3

    def test_task_ids_correct(self, tmp_path):
        wc_file = tmp_path / "WC-027-markup.md"
        wc_file.write_text(SAMPLE_WC_TABLE)
        tasks = groom_sprint._parse_wc_tasks(wc_file, "WC027")
        ids = [t["task_id"] for t in tasks]
        assert ids == ["WC027-01", "WC027-02", "WC027-03"]

    def test_model_hint_backtick_stripped(self, tmp_path):
        wc_file = tmp_path / "WC-027-markup.md"
        wc_file.write_text(SAMPLE_WC_TABLE)
        tasks = groom_sprint._parse_wc_tasks(wc_file, "WC027")
        assert tasks[0]["model_hint"] == "auto"
        assert tasks[1]["model_hint"] == "reasoning"

    def test_empty_file_returns_empty(self, tmp_path):
        wc_file = tmp_path / "WC-027-empty.md"
        wc_file.write_text("# WC-027\n\nNo tasks here.\n")
        tasks = groom_sprint._parse_wc_tasks(wc_file, "WC027")
        assert tasks == []

    def test_wrong_sprint_prefix_returns_empty(self, tmp_path):
        wc_file = tmp_path / "WC-027-markup.md"
        wc_file.write_text(SAMPLE_WC_TABLE)
        tasks = groom_sprint._parse_wc_tasks(wc_file, "WC028")
        assert tasks == []


# ─────────────────────────────────────────────────────────────
# _parse_wc_tasks: header format (fallback)
# ─────────────────────────────────────────────────────────────

class TestParseWcTasksHeaderFormat:
    def test_parses_two_tasks(self, tmp_path):
        wc_file = tmp_path / "WC-027-markup.md"
        wc_file.write_text(SAMPLE_WC_HEADERS)
        tasks = groom_sprint._parse_wc_tasks(wc_file, "WC027")
        assert len(tasks) == 2

    def test_model_hint_extracted(self, tmp_path):
        wc_file = tmp_path / "WC-027-markup.md"
        wc_file.write_text(SAMPLE_WC_HEADERS)
        tasks = groom_sprint._parse_wc_tasks(wc_file, "WC027")
        assert tasks[0]["model_hint"] == "auto"
        assert tasks[1]["model_hint"] == "reasoning"

    def test_scope_extracted(self, tmp_path):
        wc_file = tmp_path / "WC-027-markup.md"
        wc_file.write_text(SAMPLE_WC_HEADERS)
        tasks = groom_sprint._parse_wc_tasks(wc_file, "WC027")
        assert "MarkupRule" in tasks[0]["scope"]


# ─────────────────────────────────────────────────────────────
# _find_wc_file
# ─────────────────────────────────────────────────────────────

class TestFindWcFile:
    def test_finds_existing_wc_file(self, tmp_path, monkeypatch):
        wc_dir = tmp_path / "work-contracts"
        wc_dir.mkdir()
        (wc_dir / "WC-027-billing-markup.md").write_text("# WC-027")
        monkeypatch.setattr(groom_sprint, "REPO_ROOT", tmp_path)
        result = groom_sprint._find_wc_file("WC-027")
        assert result is not None
        assert result.name == "WC-027-billing-markup.md"

    def test_returns_none_when_absent(self, tmp_path, monkeypatch):
        wc_dir = tmp_path / "work-contracts"
        wc_dir.mkdir()
        monkeypatch.setattr(groom_sprint, "REPO_ROOT", tmp_path)
        result = groom_sprint._find_wc_file("WC-099")
        assert result is None

    def test_normalises_missing_dash(self, tmp_path, monkeypatch):
        wc_dir = tmp_path / "work-contracts"
        wc_dir.mkdir()
        (wc_dir / "WC-027-test.md").write_text("# WC-027")
        monkeypatch.setattr(groom_sprint, "REPO_ROOT", tmp_path)
        # WC027 without dash should still find WC-027-*.md
        result = groom_sprint._find_wc_file("WC027")
        assert result is not None


# ─────────────────────────────────────────────────────────────
# _already_groomed
# ─────────────────────────────────────────────────────────────

class TestAlreadyGroomed:
    def test_returns_true_when_task_id_in_runner(self, tmp_path, monkeypatch):
        runner = tmp_path / "autonomous_sprint_runner.py"
        runner.write_text('TASK_HANDLERS = {\n    "WC026-05": {},\n}\n')
        monkeypatch.setattr(groom_sprint, "RUNNER_PATH", runner)
        assert groom_sprint._already_groomed("WC026-05") is True

    def test_returns_false_when_absent(self, tmp_path, monkeypatch):
        runner = tmp_path / "autonomous_sprint_runner.py"
        runner.write_text('TASK_HANDLERS = {\n    "WC026-05": {},\n}\n')
        monkeypatch.setattr(groom_sprint, "RUNNER_PATH", runner)
        assert groom_sprint._already_groomed("WC027-01") is False

    def test_detects_single_quote_key(self, tmp_path, monkeypatch):
        runner = tmp_path / "autonomous_sprint_runner.py"
        runner.write_text("TASK_HANDLERS = {\n    'WC027-01': {},\n}\n")
        monkeypatch.setattr(groom_sprint, "RUNNER_PATH", runner)
        assert groom_sprint._already_groomed("WC027-01") is True


# ─────────────────────────────────────────────────────────────
# _validate_generated_entry
# ─────────────────────────────────────────────────────────────

class TestValidateGeneratedEntry:
    def test_valid_entry_passes(self):
        assert groom_sprint._validate_generated_entry(VALID_SUBTASKDEF_ENTRY, "WC027-01") is True

    def test_missing_task_id_fails(self):
        code = '"WRONG-ID": { "subtasks": [SubTaskDef(id="x")] }'
        assert groom_sprint._validate_generated_entry(code, "WC027-01") is False

    def test_missing_subtaskdef_fails(self):
        code = '"WC027-01": { "subtasks": [] }'
        assert groom_sprint._validate_generated_entry(code, "WC027-01") is False

    def test_syntax_error_fails(self):
        code = '"WC027-01": { SubTaskDef(id="x" }'  # missing closing paren
        assert groom_sprint._validate_generated_entry(code, "WC027-01") is False

    def test_single_quote_task_id_passes(self):
        code = VALID_SUBTASKDEF_ENTRY.replace('"WC027-01":', "'WC027-01':")
        assert groom_sprint._validate_generated_entry(code, "WC027-01") is True


# ─────────────────────────────────────────────────────────────
# _inject_task_handler
# ─────────────────────────────────────────────────────────────

class TestInjectTaskHandler:
    def test_injects_before_anchor(self, tmp_path, monkeypatch):
        runner = tmp_path / "autonomous_sprint_runner.py"
        runner.write_text(SAMPLE_RUNNER_WITH_ANCHOR)
        monkeypatch.setattr(groom_sprint, "RUNNER_PATH", runner)

        code = '"WC027-01": {"subtasks": [SubTaskDef(id="WC027-01a")]}'
        result = groom_sprint._inject_task_handler(code)

        assert result is True
        content = runner.read_text()
        # Injected entry should appear before anchor
        anchor_pos = content.find(groom_sprint.RUNNER_ANCHOR)
        entry_pos = content.find("WC027-01")
        assert entry_pos < anchor_pos

    def test_fails_when_anchor_missing(self, tmp_path, monkeypatch):
        runner = tmp_path / "autonomous_sprint_runner.py"
        runner.write_text("TASK_HANDLERS = {}\n")
        monkeypatch.setattr(groom_sprint, "RUNNER_PATH", runner)

        result = groom_sprint._inject_task_handler('"WC027-01": {}')
        assert result is False

    def test_idempotent_anchor_preserved(self, tmp_path, monkeypatch):
        runner = tmp_path / "autonomous_sprint_runner.py"
        runner.write_text(SAMPLE_RUNNER_WITH_ANCHOR)
        monkeypatch.setattr(groom_sprint, "RUNNER_PATH", runner)

        code = '"WC027-01": {"subtasks": [SubTaskDef(id="WC027-01a")]}'
        groom_sprint._inject_task_handler(code)

        # Anchor must still be present after injection
        content = runner.read_text()
        assert groom_sprint.RUNNER_ANCHOR in content


# ─────────────────────────────────────────────────────────────
# _inject_manifest_entry
# ─────────────────────────────────────────────────────────────

class TestInjectManifestEntry:
    def test_injects_new_sprint(self, tmp_path, monkeypatch):
        state = tmp_path / "sprint_state.py"
        state.write_text(SAMPLE_STATE_WITH_ANCHOR)
        monkeypatch.setattr(groom_sprint, "STATE_PATH", state)

        result = groom_sprint._inject_manifest_entry("WC-027", ["WC027-01", "WC027-02"])

        assert result is True
        content = state.read_text()
        assert '"WC-027"' in content
        assert '"WC027-01"' in content

    def test_anchor_preserved_after_injection(self, tmp_path, monkeypatch):
        state = tmp_path / "sprint_state.py"
        state.write_text(SAMPLE_STATE_WITH_ANCHOR)
        monkeypatch.setattr(groom_sprint, "STATE_PATH", state)

        groom_sprint._inject_manifest_entry("WC-027", ["WC027-01"])

        content = state.read_text()
        assert groom_sprint.MANIFEST_ANCHOR in content

    def test_idempotent_when_sprint_already_present(self, tmp_path, monkeypatch):
        state = tmp_path / "sprint_state.py"
        state.write_text(SAMPLE_STATE_WITH_ANCHOR)
        monkeypatch.setattr(groom_sprint, "STATE_PATH", state)

        # Inject once
        groom_sprint._inject_manifest_entry("WC-027", ["WC027-01"])
        # Inject again — should not duplicate
        groom_sprint._inject_manifest_entry("WC-027", ["WC027-01"])

        content = state.read_text()
        assert content.count('"WC-027"') == 1

    def test_fails_when_anchor_missing(self, tmp_path, monkeypatch):
        state = tmp_path / "sprint_state.py"
        state.write_text("SPRINT_TASK_MANIFEST = {}\n")
        monkeypatch.setattr(groom_sprint, "STATE_PATH", state)

        result = groom_sprint._inject_manifest_entry("WC-027", ["WC027-01"])
        assert result is False


# ─────────────────────────────────────────────────────────────
# _read_current_sprint
# ─────────────────────────────────────────────────────────────

class TestReadCurrentSprint:
    def test_reads_sprint_from_state_machine(self, tmp_path, monkeypatch):
        ps = tmp_path / "PROJECT_STATE.md"
        ps.write_text(textwrap.dedent("""
        ## Some Section

        ## SPRINT_STATE_MACHINE

        ```yaml
        autonomous_halt: false
        current_sprint: WC-027
        sprint_status: IN_PROGRESS
        ```
        """))
        monkeypatch.setattr(groom_sprint, "PROJECT_STATE", ps)
        assert groom_sprint._read_current_sprint() == "WC-027"

    def test_returns_empty_when_missing(self, tmp_path, monkeypatch):
        ps = tmp_path / "PROJECT_STATE.md"
        ps.write_text("# PROJECT_STATE\n\nNo sprint state here.\n")
        monkeypatch.setattr(groom_sprint, "PROJECT_STATE", ps)
        assert groom_sprint._read_current_sprint() == ""


# ─────────────────────────────────────────────────────────────
# main() — dry-run integration smoke test
# ─────────────────────────────────────────────────────────────

class TestMainDryRun:
    def test_dry_run_skips_when_no_wc_file(self, tmp_path, monkeypatch, capsys):
        wc_dir = tmp_path / "work-contracts"
        wc_dir.mkdir()
        monkeypatch.setattr(groom_sprint, "REPO_ROOT", tmp_path)
        # Set up minimal runner + state files so path lookups don't fail
        runner = tmp_path / "scripts" / "autonomous_sprint_runner.py"
        runner.parent.mkdir(parents=True, exist_ok=True)
        runner.write_text(SAMPLE_RUNNER_WITH_ANCHOR)
        monkeypatch.setattr(groom_sprint, "RUNNER_PATH", runner)
        state = tmp_path / "scripts" / "sprint_state.py"
        state.write_text(SAMPLE_STATE_WITH_ANCHOR)
        monkeypatch.setattr(groom_sprint, "STATE_PATH", state)

        ret = groom_sprint.main.__wrapped__ if hasattr(groom_sprint.main, "__wrapped__") else groom_sprint.main
        with patch("sys.argv", ["groom_sprint.py", "--sprint", "WC-099", "--dry-run"]):
            exit_code = groom_sprint.main()

        assert exit_code == 0
        captured = capsys.readouterr()
        assert "grooming skipped" in captured.out

    def test_dry_run_skips_api_call_when_already_groomed(self, tmp_path, monkeypatch, capsys):
        wc_dir = tmp_path / "work-contracts"
        wc_dir.mkdir()
        (wc_dir / "WC-026-billing.md").write_text(SAMPLE_WC_TABLE.replace("WC027", "WC026"))
        monkeypatch.setattr(groom_sprint, "REPO_ROOT", tmp_path)

        runner = tmp_path / "scripts" / "autonomous_sprint_runner.py"
        runner.parent.mkdir(parents=True, exist_ok=True)
        # Mark all tasks as already groomed
        runner.write_text(
            SAMPLE_RUNNER_WITH_ANCHOR
            + '\n    "WC026-01": {},\n    "WC026-02": {},\n    "WC026-03": {},\n'
        )
        monkeypatch.setattr(groom_sprint, "RUNNER_PATH", runner)
        state = tmp_path / "scripts" / "sprint_state.py"
        state.write_text(SAMPLE_STATE_WITH_ANCHOR)
        monkeypatch.setattr(groom_sprint, "STATE_PATH", state)

        with patch("sys.argv", ["groom_sprint.py", "--sprint", "WC-026", "--dry-run"]):
            exit_code = groom_sprint.main()

        assert exit_code == 0
        captured = capsys.readouterr()
        assert "already groomed" in captured.out


# ─────────────────────────────────────────────────────────────
# Staged generation: _generate_polish_subtaskdef
# ─────────────────────────────────────────────────────────────

class TestGeneratePolishSubtaskdef:
    def test_returns_subtaskdef_literal(self):
        result = groom_sprint._generate_polish_subtaskdef(
            task_id="WC027-02",
            scaffold_output_files=["src/billing-engine/wallet/service.py"],
            service_dir="src/billing-engine",
            wc_filename="WC-027-billing.md",
            stack="python",
        )
        assert 'id="WC027-02b"' in result
        assert 'depends_on=["WC027-02a"]' in result
        assert 'compile_gate="ruff"' in result
        assert 'model_hint="auto"' in result
        assert "POLISH PASS" in result
        assert "ANN001" in result

    def test_output_files_match_scaffold(self):
        files = ["src/billing-engine/wallet/service.py", "src/billing-engine/wallet/repo.py"]
        result = groom_sprint._generate_polish_subtaskdef(
            task_id="WC027-02",
            scaffold_output_files=files,
            service_dir="src/billing-engine",
            wc_filename="WC-027-billing.md",
            stack="python",
        )
        assert '"src/billing-engine/wallet/service.py",' in result
        assert '"src/billing-engine/wallet/repo.py",' in result

    def test_inject_source_files_match_scaffold(self):
        files = ["src/billing-engine/wallet/service.py"]
        result = groom_sprint._generate_polish_subtaskdef(
            task_id="WC027-01",
            scaffold_output_files=files,
            service_dir="src/billing-engine",
            wc_filename="WC-027-billing.md",
            stack="python",
        )
        # inject_source_files should be the scaffold output files
        assert '"src/billing-engine/wallet/service.py",' in result

    def test_no_llm_call_needed(self):
        """Polish subtask is fully templated — no API key required."""
        # Just calling it with no api_key param should succeed
        result = groom_sprint._generate_polish_subtaskdef(
            task_id="WC027-03",
            scaffold_output_files=["src/billing-engine/cache/redis.py"],
            service_dir="src/billing-engine",
            wc_filename="WC-027.md",
            stack="python",
        )
        assert result  # non-empty string returned without network call

    def test_wc_filename_in_spec_sections(self):
        result = groom_sprint._generate_polish_subtaskdef(
            task_id="WC027-02",
            scaffold_output_files=["src/billing-engine/wallet/service.py"],
            service_dir="src/billing-engine",
            wc_filename="WC-027-billing-engine.md",
            stack="python",
        )
        assert '"work-contracts/WC-027-billing-engine.md"' in result


# ─────────────────────────────────────────────────────────────
# Staged generation: _validate_generated_entry — 3-subtask chain
# ─────────────────────────────────────────────────────────────

class TestValidateGeneratedEntryThreeSubtasks:
    def test_valid_3subtask_entry_passes(self):
        """3-subtask chain entry should pass validation."""
        assert groom_sprint._validate_generated_entry(VALID_SUBTASKDEF_ENTRY, "WC027-01") is True

    def test_scaffold_uses_py_compile_gate(self):
        """VALID_SUBTASKDEF_ENTRY fixture should have py_compile for scaffold."""
        assert 'compile_gate="py_compile"' in VALID_SUBTASKDEF_ENTRY

    def test_polish_uses_ruff_gate(self):
        assert VALID_SUBTASKDEF_ENTRY.count('compile_gate="ruff"') >= 2  # polish + test

    def test_scaffold_subtask_id_has_a_suffix(self):
        assert '"WC027-01a"' in VALID_SUBTASKDEF_ENTRY

    def test_polish_subtask_id_has_b_suffix(self):
        assert '"WC027-01b"' in VALID_SUBTASKDEF_ENTRY

    def test_test_subtask_id_has_c_suffix(self):
        assert '"WC027-01c"' in VALID_SUBTASKDEF_ENTRY

    def test_depends_on_chain(self):
        assert 'depends_on=["WC027-01a"]' in VALID_SUBTASKDEF_ENTRY
        assert 'depends_on=["WC027-01b"]' in VALID_SUBTASKDEF_ENTRY
