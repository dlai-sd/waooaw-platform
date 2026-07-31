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

SAMPLE_WC_TABLE_SPLIT = textwrap.dedent("""
# WC-027 — Billing Engine: Markup & Bundle Engine (split tasks)

## Tasks

| Task ID | Scope | model_hint | Status |
|---|---|---|---|
| WC027-01a | SQLAlchemy models for MarkupRule, BundleItem | `reasoning` | 🔲 TODO |
| WC027-01b | FastAPI router for markup engine | `auto` | 🔲 TODO |
| WC027-02 | pytest tests for markup calculations | `auto` | 🔲 TODO |
""").strip()


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

    def test_split_task_ids_letter_suffix(self, tmp_path):
        """Regression: WC027-01a, WC027-01b must be parsed (not skipped)."""
        wc_file = tmp_path / "WC-027-markup-split.md"
        wc_file.write_text(SAMPLE_WC_TABLE_SPLIT)
        tasks = groom_sprint._parse_wc_tasks(wc_file, "WC027")
        ids = [t["task_id"] for t in tasks]
        assert ids == ["WC027-01a", "WC027-01b", "WC027-02"]

    def test_split_task_model_hints_correct(self, tmp_path):
        """Regression: model_hint must be read correctly for split tasks."""
        wc_file = tmp_path / "WC-027-markup-split.md"
        wc_file.write_text(SAMPLE_WC_TABLE_SPLIT)
        tasks = groom_sprint._parse_wc_tasks(wc_file, "WC027")
        assert tasks[0]["model_hint"] == "reasoning"
        assert tasks[1]["model_hint"] == "auto"

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
        runner.write_text('TASK_HANDLERS = {\n    "WC026-05": {"subtasks": [SubTaskDef(id="WC026-05a")]},\n}\n')
        monkeypatch.setattr(groom_sprint, "RUNNER_PATH", runner)
        assert groom_sprint._already_groomed("WC026-05") is True

    def test_returns_false_when_absent(self, tmp_path, monkeypatch):
        runner = tmp_path / "autonomous_sprint_runner.py"
        runner.write_text('TASK_HANDLERS = {\n    "WC026-05": {},\n}\n')
        monkeypatch.setattr(groom_sprint, "RUNNER_PATH", runner)
        assert groom_sprint._already_groomed("WC027-01") is False

    def test_detects_single_quote_key(self, tmp_path, monkeypatch):
        runner = tmp_path / "autonomous_sprint_runner.py"
        runner.write_text("TASK_HANDLERS = {\n    'WC027-01': {'subtasks': [SubTaskDef(id='WC027-01a')]},\n}\n")
        monkeypatch.setattr(groom_sprint, "RUNNER_PATH", runner)
        assert groom_sprint._already_groomed("WC027-01") is True

    def test_non_canonical_scaffold_id_returns_false_and_removes_entry(self, tmp_path, monkeypatch):
        runner = tmp_path / "autonomous_sprint_runner.py"
        # Entry exists with broken scaffold id — must match real multi-line format
        runner.write_text(
            'TASK_HANDLERS = {\n'
            '        "WC027-01a": {\n'
            '        "subtasks": [\n'
            '            SubTaskDef(id="WC027-01a-scaffold"),\n'
            '        ]\n'
            '    },\n'
            '    # ── GROOMER INJECTION POINT ──\n'
            '}\n'
        )
        monkeypatch.setattr(groom_sprint, "RUNNER_PATH", runner)
        result = groom_sprint._already_groomed("WC027-01a")
        assert result is False
        # Entry should be stripped so groomer re-injects on next call
        content = runner.read_text()
        assert '"WC027-01a":' not in content and "'WC027-01a':" not in content


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
        # Mark all tasks as already groomed with canonical scaffold ids
        runner.write_text(
            SAMPLE_RUNNER_WITH_ANCHOR
            + '\n    "WC026-01": {"subtasks": [SubTaskDef(id="WC026-01a")]},\n'
            + '    "WC026-02": {"subtasks": [SubTaskDef(id="WC026-02a")]},\n'
            + '    "WC026-03": {"subtasks": [SubTaskDef(id="WC026-03a")]},\n'
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


# ─────────────────────────────────────────────────────────────
# _validate_generated_entry — requires full 3-subtask chain
# ─────────────────────────────────────────────────────────────

class TestValidateRequiresFullChain:
    _base = textwrap.dedent("""\
        "WC027-01": {
            "subtasks": [
                SubTaskDef(id="WC027-01a", compile_gate="py_compile"),
                SubTaskDef(id="WC027-01b", depends_on=["WC027-01a"], compile_gate="ruff"),
                SubTaskDef(id="WC027-01c", depends_on=["WC027-01b"], compile_gate="ruff"),
            ]
        },""")

    def test_full_chain_passes(self):
        assert groom_sprint._validate_generated_entry(self._base, "WC027-01") is True

    def test_missing_polish_fails(self):
        code = self._base.replace('SubTaskDef(id="WC027-01b", depends_on=["WC027-01a"], compile_gate="ruff"),\n', "")
        assert groom_sprint._validate_generated_entry(code, "WC027-01") is False

    def test_missing_test_fails(self):
        code = self._base.replace('SubTaskDef(id="WC027-01c", depends_on=["WC027-01b"], compile_gate="ruff"),\n', "")
        assert groom_sprint._validate_generated_entry(code, "WC027-01") is False

    def test_scaffold_only_fails(self):
        code = textwrap.dedent("""\
            "WC027-01": {
                "subtasks": [
                    SubTaskDef(id="WC027-01a", compile_gate="py_compile"),
                ]
            },""")
        assert groom_sprint._validate_generated_entry(code, "WC027-01") is False


# ─────────────────────────────────────────────────────────────
# _generate_subtask_chain — integration with mocked _llm_call
# ─────────────────────────────────────────────────────────────

_SAMPLE_SCAFFOLD_LITERAL = textwrap.dedent("""\
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
            "work-contracts/WC-027-billing.md": "WC027-01",
        },
        constitutional_check="Implement MarkupRule model.",
        model_hint="auto",
        max_tokens=4000,
    )""")

_SAMPLE_TEST_LITERAL = textwrap.dedent("""\
    SubTaskDef(
        id="WC027-01c",
        description="Tests for MarkupRule SQLAlchemy models",
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
            "work-contracts/WC-027-billing.md": "WC027-01",
        },
        constitutional_check="TEST PASS",
        model_hint="reasoning",
        max_tokens=6000,
    )""")


class TestGenerateSubtaskChain:
    # Scope with explicit file path so _extract_scope_paths can return a deterministic result.
    _task = {"task_id": "WC027-01", "scope": "src/billing-engine/markup/models.py — SQLAlchemy models", "model_hint": "auto"}

    def _make_llm(self, responses: list) -> object:
        it = iter(responses)
        return lambda *a, **kw: next(it, None)

    def test_produces_all_three_subtask_ids(self, monkeypatch):
        monkeypatch.setattr(groom_sprint, "_llm_call", self._make_llm([_SAMPLE_SCAFFOLD_LITERAL, _SAMPLE_TEST_LITERAL]))
        result = groom_sprint._generate_subtask_chain(
            task=self._task, skeleton="", prior_subtask_id=None,
            sprint_prefix="WC027", wc_filename="WC-027-billing.md", api_key="x",
        )
        assert result is not None
        assert '"WC027-01a"' in result
        assert '"WC027-01b"' in result
        assert '"WC027-01c"' in result

    def test_result_passes_validation(self, monkeypatch):
        monkeypatch.setattr(groom_sprint, "_llm_call", self._make_llm([_SAMPLE_SCAFFOLD_LITERAL, _SAMPLE_TEST_LITERAL]))
        result = groom_sprint._generate_subtask_chain(
            task=self._task, skeleton="", prior_subtask_id=None,
            sprint_prefix="WC027", wc_filename="WC-027-billing.md", api_key="x",
        )
        assert groom_sprint._validate_generated_entry(result, "WC027-01") is True

    def test_result_is_valid_python(self, monkeypatch):
        monkeypatch.setattr(groom_sprint, "_llm_call", self._make_llm([_SAMPLE_SCAFFOLD_LITERAL, _SAMPLE_TEST_LITERAL]))
        result = groom_sprint._generate_subtask_chain(
            task=self._task, skeleton="", prior_subtask_id=None,
            sprint_prefix="WC027", wc_filename="WC-027-billing.md", api_key="x",
        )
        # ast.parse on the assembled entry must not raise
        import ast as _ast
        wrapper = "class SubTaskDef:\n    def __init__(self, **kw): pass\n_d = {" + result + "}"
        _ast.parse(wrapper)  # raises SyntaxError if invalid

    def test_returns_none_when_scaffold_llm_fails(self, monkeypatch):
        monkeypatch.setattr(groom_sprint, "_llm_call", self._make_llm([None]))
        result = groom_sprint._generate_subtask_chain(
            task=self._task, skeleton="", prior_subtask_id=None,
            sprint_prefix="WC027", wc_filename="WC-027.md", api_key="x",
        )
        assert result is None

    def test_returns_none_when_output_files_empty(self, monkeypatch):
        """When scope has no paths and LLM returns None, chain returns None (output_files empty)."""
        # Use a prose-only scope so _extract_scope_paths returns [] (fallback path)
        task_no_paths = {"task_id": "WC027-01", "scope": "Implement business logic", "model_hint": "auto"}
        monkeypatch.setattr(groom_sprint, "_llm_call", self._make_llm([None]))
        result = groom_sprint._generate_subtask_chain(
            task=task_no_paths, skeleton="", prior_subtask_id=None,
            sprint_prefix="WC027", wc_filename="WC-027.md", api_key="x",
        )
        assert result is None

    def test_impl_task_only_calls_llm_once(self, monkeypatch):
        """Impl task chain: scaffold prose LLM + polish (templated) + test (templated) = 1 LLM call."""
        call_count = [0]

        def counting_llm(*a, **kw):
            call_count[0] += 1
            return '{"description": "Implement models.", "constitutional_check": "ADR-036."}'

        monkeypatch.setattr(groom_sprint, "_llm_call", counting_llm)
        result = groom_sprint._generate_subtask_chain(
            task=self._task, skeleton="", prior_subtask_id=None,
            sprint_prefix="WC027", wc_filename="WC-027.md", api_key="x",
        )
        assert result is not None
        assert call_count[0] == 1, f"Impl task chain should make 1 LLM call, got {call_count[0]}"

    def test_prior_subtask_id_sets_depends_on(self, monkeypatch):
        monkeypatch.setattr(groom_sprint, "_llm_call", self._make_llm([_SAMPLE_SCAFFOLD_LITERAL, _SAMPLE_TEST_LITERAL]))
        result = groom_sprint._generate_subtask_chain(
            task=self._task, skeleton="", prior_subtask_id="WC027-00a",
            sprint_prefix="WC027", wc_filename="WC-027-billing.md", api_key="x",
        )
        # prior_subtask_id is used by _build_scaffold_subtaskdef directly; it must appear in depends_on
        assert result is not None
        assert '"WC027-01a"' in result
        assert 'depends_on=[\'WC027-00a\']' in result or 'depends_on=["WC027-00a"]' in result

    def test_scaffold_fenced_json_response_is_handled(self, monkeypatch):
        """Fenced JSON prose response from LLM is correctly parsed by _parse_prose_response."""
        fenced_json = '```json\n{"description": "Implement models.", "constitutional_check": "ADR-036."}\n```'
        monkeypatch.setattr(groom_sprint, "_llm_call", self._make_llm([fenced_json]))
        result = groom_sprint._generate_subtask_chain(
            task=self._task, skeleton="", prior_subtask_id=None,
            sprint_prefix="WC027", wc_filename="WC-027-billing.md", api_key="x",
        )
        assert result is not None
        assert '"WC027-01a"' in result
        assert '"WC027-01b"' in result

    def test_scaffold_non_json_response_falls_back(self, monkeypatch):
        """Non-JSON LLM prose response uses fallback description; chain still succeeds."""
        with_preamble = f"Here is some prose text without JSON structure."
        monkeypatch.setattr(groom_sprint, "_llm_call", self._make_llm([with_preamble]))
        result = groom_sprint._generate_subtask_chain(
            task=self._task, skeleton="", prior_subtask_id=None,
            sprint_prefix="WC027", wc_filename="WC-027-billing.md", api_key="x",
        )
        assert result is not None
        assert '"WC027-01a"' in result

    def test_prompt_contains_task_id_and_skeleton(self, monkeypatch):
        captured: list[str] = []

        def capture(prompt: str, system: str, api_key: str, max_tokens: int = 2048) -> str:
            captured.append(prompt)
            return _SAMPLE_SCAFFOLD_LITERAL

        monkeypatch.setattr(groom_sprint, "_llm_call", capture)
        groom_sprint._generate_subtask_chain(
            task=self._task, skeleton="SKELETON_CONTENT_HERE", prior_subtask_id=None,
            sprint_prefix="WC027", wc_filename="WC-027-billing.md", api_key="x",
        )
        scaffold_prompt = captured[0]
        assert "WC027-01" in scaffold_prompt
        # Prose-only LLM prompt includes skeleton content and output files
        assert "SKELETON_CONTENT_HERE" in scaffold_prompt
        assert "Output files" in scaffold_prompt

    def test_prior_subtask_id_appears_in_result_depends_on(self, monkeypatch):
        """prior_subtask_id must appear in scaffold depends_on (not in LLM prompt — used by builder)."""
        monkeypatch.setattr(groom_sprint, "_llm_call", self._make_llm([_SAMPLE_SCAFFOLD_LITERAL]))
        result = groom_sprint._generate_subtask_chain(
            task=self._task, skeleton="", prior_subtask_id="WC026-03a",
            sprint_prefix="WC027", wc_filename="WC-027.md", api_key="x",
        )
        assert result is not None
        # prior_subtask_id ends up in scaffold depends_on via _build_scaffold_subtaskdef
        assert "WC026-03a" in result


# ─────────────────────────────────────────────────────────────
# _strip_llm_fences
# ─────────────────────────────────────────────────────────────

class TestStripLlmFences:
    def test_strips_python_fence(self):
        raw = "```python\nSubTaskDef(\n    id='x',\n)\n```"
        assert groom_sprint._strip_llm_fences(raw) == "SubTaskDef(\n    id='x',\n)"

    def test_strips_plain_fence(self):
        raw = "```\nSubTaskDef(\n    id='x',\n)\n```"
        assert groom_sprint._strip_llm_fences(raw) == "SubTaskDef(\n    id='x',\n)"

    def test_no_fence_unchanged(self):
        raw = "SubTaskDef(\n    id='x',\n)"
        assert groom_sprint._strip_llm_fences(raw) == raw

    def test_strips_preamble_before_subtaskdef(self):
        raw = "Here is the generated literal:\nSubTaskDef(\n    id='x',\n)"
        assert groom_sprint._strip_llm_fences(raw).startswith("SubTaskDef(")

    def test_fence_plus_preamble(self):
        raw = "```python\nHere you go:\nSubTaskDef(\n    id='x',\n)\n```"
        result = groom_sprint._strip_llm_fences(raw)
        assert result.startswith("SubTaskDef(")

    def test_subtaskdef_at_start_not_stripped(self):
        raw = "SubTaskDef(\n    id='x',\n    description='test',\n)"
        assert groom_sprint._strip_llm_fences(raw) == raw

    # Option B regression: XML file-block envelope handling
    def test_strips_xml_file_envelope(self):
        """Regression: MagicLLM FORMAT gate requires <file path=...> wrapping."""
        raw = '<file path="scripts/autonomous_sprint_runner.py">\nSubTaskDef(\n    id=\'x\',\n)\n</file>'
        result = groom_sprint._strip_llm_fences(raw)
        assert result == "SubTaskDef(\n    id='x',\n)"
        assert "</file>" not in result

    def test_strips_xml_envelope_with_whitespace(self):
        raw = '<file path="scripts/autonomous_sprint_runner.py">\nSubTaskDef(\n    id=\'x\',\n)\n</file>\n'
        result = groom_sprint._strip_llm_fences(raw)
        assert result.startswith("SubTaskDef(")
        assert "</file>" not in result

    def test_no_xml_envelope_still_works(self):
        """Plain SubTaskDef (no XML wrapper) still parses correctly."""
        raw = "SubTaskDef(\n    id='x',\n    description='test',\n)"
        result = groom_sprint._strip_llm_fences(raw)
        assert result == raw

    def test_xml_envelope_preserves_full_subtaskdef_body(self):
        body = "SubTaskDef(\n    id='WC027-01a',\n    description='Implements markup engine',\n    type='llm',\n)"
        raw = f'<file path="scripts/autonomous_sprint_runner.py">\n{body}\n</file>'
        result = groom_sprint._strip_llm_fences(raw)
        assert result == body


# ─────────────────────────────────────────────────────────────
# _extract_output_files
# ─────────────────────────────────────────────────────────────

class TestExtractOutputFiles:
    def test_double_quoted_path(self):
        literal = 'output_files=["src/billing-engine/wallet/service.py"]'
        assert groom_sprint._extract_output_files(literal) == ["src/billing-engine/wallet/service.py"]

    def test_single_quoted_path(self):
        literal = "output_files=['src/billing-engine/wallet/service.py']"
        assert groom_sprint._extract_output_files(literal) == ["src/billing-engine/wallet/service.py"]

    def test_multiple_files(self):
        literal = 'output_files=["src/billing-engine/wallet/service.py", "src/billing-engine/wallet/repo.py"]'
        result = groom_sprint._extract_output_files(literal)
        assert len(result) == 2
        assert "src/billing-engine/wallet/service.py" in result

    def test_multiline_with_whitespace(self):
        literal = 'output_files=[\n    "src/billing-engine/wallet/service.py",\n]'
        assert groom_sprint._extract_output_files(literal) == ["src/billing-engine/wallet/service.py"]

    def test_excludes_test_files(self):
        literal = 'output_files=["tests/billing-engine/test_service.py"]'
        assert groom_sprint._extract_output_files(literal) == []

    def test_excludes_skeleton_files(self):
        literal = 'output_files=["src/billing-engine/skeleton/wbe_interfaces.py"]'
        assert groom_sprint._extract_output_files(literal) == []

    def test_impl_and_test_mixed(self):
        literal = 'output_files=["src/billing-engine/wallet/service.py", "tests/billing-engine/test_service.py"]'
        result = groom_sprint._extract_output_files(literal)
        assert result == ["src/billing-engine/wallet/service.py"]

    def test_returns_empty_when_no_output_files_key(self):
        literal = 'SubTaskDef(id="WC027-01a", compile_gate="py_compile")'
        assert groom_sprint._extract_output_files(literal) == []

    def test_returns_empty_for_empty_list(self):
        literal = 'output_files=[]'
        assert groom_sprint._extract_output_files(literal) == []


# ─────────────────────────────────────────────────────────────
# _indent_subtask
# ─────────────────────────────────────────────────────────────

class TestIndentSubtask:
    def test_all_lines_indented(self):
        literal = "SubTaskDef(\n    id='x',\n)"
        result = groom_sprint._indent_subtask(literal, 8)
        lines = result.splitlines()
        assert lines[0] == "        SubTaskDef("
        assert lines[1] == "            id='x',"
        assert lines[2] == "        )"

    def test_blank_lines_have_no_trailing_spaces(self):
        literal = "SubTaskDef(\n\n    id='x',\n)"
        result = groom_sprint._indent_subtask(literal, 8)
        for line in result.splitlines():
            assert line == line.rstrip() or line.strip()

    def test_default_8_spaces(self):
        assert groom_sprint._indent_subtask("SubTaskDef()").startswith("        SubTaskDef()")

    def test_custom_indent(self):
        result = groom_sprint._indent_subtask("SubTaskDef()", 4)
        assert result == "    SubTaskDef()"

    def test_assembled_entry_format(self):
        literal = "SubTaskDef(\n    id='WC027-01b',\n    compile_gate='ruff',\n)"
        result = groom_sprint._indent_subtask(literal, 8)
        # First line at 8 spaces, fields at 12 spaces — matches VALID_SUBTASKDEF_ENTRY format
        assert "        SubTaskDef(" in result
        assert "            id='WC027-01b'" in result


# ─────────────────────────────────────────────────────────────
# _extract_subtaskdef_id
# ─────────────────────────────────────────────────────────────

class TestExtractSubtaskdefId:
    def test_extracts_double_quoted_id(self):
        literal = 'SubTaskDef(\n    id="WC027-01a",\n    compile_gate="py_compile",\n)'
        assert groom_sprint._extract_subtaskdef_id(literal) == "WC027-01a"

    def test_extracts_single_quoted_id(self):
        literal = "SubTaskDef(\n    id='WC027-01a',\n    compile_gate='py_compile',\n)"
        assert groom_sprint._extract_subtaskdef_id(literal) == "WC027-01a"

    def test_returns_none_when_no_id(self):
        literal = 'SubTaskDef(\n    compile_gate="py_compile",\n)'
        assert groom_sprint._extract_subtaskdef_id(literal) is None

    def test_extracts_hyphenated_llm_invented_id(self):
        """Regression: LLM sometimes invents id='WC027-01a-scaffold' — must be extractable."""
        literal = 'SubTaskDef(\n    id="WC027-01a-scaffold",\n    compile_gate="py_compile",\n)'
        assert groom_sprint._extract_subtaskdef_id(literal) == "WC027-01a-scaffold"

    def test_extracts_first_id_only(self):
        """Only the first id= field is extracted (other uses of id= should not interfere)."""
        literal = 'SubTaskDef(\n    id="WC027-01a",\n    wc_task_id="WC027-01",\n)'
        assert groom_sprint._extract_subtaskdef_id(literal) == "WC027-01a"


# ─────────────────────────────────────────────────────────────
# _normalize_subtask_id
# ─────────────────────────────────────────────────────────────

class TestNormalizeSubtaskId:
    def test_canonical_id_unchanged(self):
        """If LLM already used the canonical id, no change."""
        literal = 'SubTaskDef(\n    id="WC027-01a",\n    compile_gate="py_compile",\n)'
        result = groom_sprint._normalize_subtask_id(literal, "WC027-01", "a")
        assert 'id="WC027-01a"' in result

    def test_scaffold_hyphen_suffix_normalised(self):
        """Regression: LLM used id='WC027-01a-scaffold' — must be normalised to 'WC027-01aa'."""
        literal = 'SubTaskDef(\n    id="WC027-01a-scaffold",\n    compile_gate="py_compile",\n)'
        result = groom_sprint._normalize_subtask_id(literal, "WC027-01a", "a")
        assert 'id="WC027-01aa"' in result
        assert 'scaffold' not in result

    def test_normalisation_does_not_touch_other_fields(self):
        """Only the id= field is rewritten; other fields are untouched."""
        literal = 'SubTaskDef(\n    id="WC027-01a-scaffold",\n    wc_task_id="WC027-01",\n    compile_gate="py_compile",\n)'
        result = groom_sprint._normalize_subtask_id(literal, "WC027-01a", "a")
        assert 'wc_task_id="WC027-01"' in result
        assert 'compile_gate="py_compile"' in result

    def test_split_task_id_double_letter_suffix(self):
        """task_id='WC027-01a', suffix='a' → canonical id='WC027-01aa' (double-letter)."""
        literal = 'SubTaskDef(\n    id="WC027-01a-models",\n    compile_gate="py_compile",\n)'
        result = groom_sprint._normalize_subtask_id(literal, "WC027-01a", "a")
        assert 'id="WC027-01aa"' in result


# ─────────────────────────────────────────────────────────────
# _generate_subtask_chain — scaffold id normalisation (regression)
# ─────────────────────────────────────────────────────────────

_SCAFFOLD_WITH_INVENTED_ID = textwrap.dedent("""\
    SubTaskDef(
        id="WC027-01a-scaffold",
        description="Implement SQLAlchemy models",
        type="llm",
        depends_on=[],
        compile_gate="py_compile",
        service_dir="src/billing-engine",
        wc_task_id="WC027-01a",
        stack="python",
        output_files=[
            "src/billing-engine/markup/models.py",
        ],
        inject_source_files=[
            "src/billing-engine/skeleton/wbe_interfaces.py",
        ],
        spec_sections={
            "work-contracts/WC-027-markup.md": "WC027-01a",
        },
        constitutional_check="Implement MarkupEngine models.",
        model_hint="reasoning",
        max_tokens=8000,
    )""")

_SAMPLE_TEST_FOR_SPLIT = textwrap.dedent("""\
    SubTaskDef(
        id="WC027-01ac",
        description="Tests for markup engine models",
        type="llm",
        depends_on=["WC027-01ab"],
        compile_gate="ruff",
        service_dir="src/billing-engine",
        wc_task_id="WC027-01a",
        stack="python",
        output_files=[
            "tests/billing-engine/test_models.py",
        ],
        inject_source_files=[
            "src/billing-engine/markup/models.py",
        ],
        spec_sections={
            "work-contracts/WC-027-markup.md": "WC027-01a",
        },
        constitutional_check="TEST PASS",
        model_hint="reasoning",
        max_tokens=6000,
    )""")


class TestGenerateSubtaskChainIdNormalisation:
    """Scaffold id is always canonical ({task_id}a) — deterministic from _build_scaffold_subtaskdef."""

    _split_task = {"task_id": "WC027-01a", "scope": "src/billing-engine/markup/models.py — SQLAlchemy models for markup engine", "model_hint": "reasoning"}

    def _make_llm(self, responses: list):
        it = iter(responses)
        return lambda *a, **kw: next(it, None)

    def test_scaffold_id_is_always_canonical(self, monkeypatch):
        """Scaffold id is always {task_id}a — produced by _build_scaffold_subtaskdef, not LLM."""
        monkeypatch.setattr(groom_sprint, "_llm_call", self._make_llm([
            '{"description": "Implement models.", "constitutional_check": "ADR-036."}'
        ]))
        result = groom_sprint._generate_subtask_chain(
            task=self._split_task, skeleton="", prior_subtask_id=None,
            sprint_prefix="WC027", wc_filename="WC-027-markup.md", api_key="x",
        )
        assert result is not None
        # Scaffold id must be WC027-01aa (task_id='WC027-01a' + suffix 'a')
        assert '"WC027-01aa"' in result

    def test_polish_depends_on_canonical_scaffold_id(self, monkeypatch):
        """Polish depends_on must reference the canonical scaffold id (WC027-01aa)."""
        monkeypatch.setattr(groom_sprint, "_llm_call", self._make_llm([
            '{"description": "Implement models.", "constitutional_check": "ADR-036."}'
        ]))
        result = groom_sprint._generate_subtask_chain(
            task=self._split_task, skeleton="", prior_subtask_id=None,
            sprint_prefix="WC027", wc_filename="WC-027-markup.md", api_key="x",
        )
        assert result is not None
        assert 'depends_on=["WC027-01aa"]' in result

    def test_full_chain_passes_validation(self, monkeypatch):
        """Generated entry must pass _validate_generated_entry."""
        monkeypatch.setattr(groom_sprint, "_llm_call", self._make_llm([
            '{"description": "Implement models.", "constitutional_check": "ADR-036."}'
        ]))
        result = groom_sprint._generate_subtask_chain(
            task=self._split_task, skeleton="", prior_subtask_id=None,
            sprint_prefix="WC027", wc_filename="WC-027-markup.md", api_key="x",
        )
        assert result is not None
        assert groom_sprint._validate_generated_entry(result, "WC027-01a") is True

    def test_canonical_id_in_chain_for_impl_task(self, monkeypatch):
        """Canonical a/b/c ids appear in chain output for impl task with explicit scope path."""
        monkeypatch.setattr(groom_sprint, "_llm_call", self._make_llm([
            '{"description": "Implement models.", "constitutional_check": "ADR-036."}'
        ]))
        task_with_path = {"task_id": "WC027-01", "scope": "src/billing-engine/markup/models.py — models", "model_hint": "auto"}
        result = groom_sprint._generate_subtask_chain(
            task=task_with_path, skeleton="", prior_subtask_id=None,
            sprint_prefix="WC027", wc_filename="WC-027-billing.md", api_key="x",
        )
        assert result is not None
        assert '"WC027-01a"' in result
        assert '"WC027-01b"' in result
        assert '"WC027-01c"' in result


# ─────────────────────────────────────────────────────────────
# Fix A regression: UP031 not in ruff gate blocklist
# ─────────────────────────────────────────────────────────────

class TestUP031NotBlockedByCompileGate:
    """Regression: UP031 (% string formatting in comprehensions) must not block the ruff gate.

    Root cause (run 30624494792): ruff --fix cannot auto-correct UP031 when the %
    format appears inside a list comprehension.  The fix: add UP031 to pyproject.toml
    ignore list so the strict gate never fails on it.
    """

    def test_pyproject_ignores_up031(self):
        """UP031 must be present in pyproject.toml [tool.ruff.lint] ignore list."""
        import re as _re
        pyproject = (
            __import__("pathlib").Path(__file__).parent.parent / "pyproject.toml"
        ).read_text()
        # Find the [tool.ruff.lint] section
        section_start = pyproject.find("[tool.ruff.lint]")
        assert section_start != -1, "[tool.ruff.lint] section not found in pyproject.toml"
        # Find the ignore list within that section
        section = pyproject[section_start:]
        ignore_start = section.find("ignore = [")
        assert ignore_start != -1, "ignore list not found in [tool.ruff.lint] section"
        ignore_end = section.find("]", ignore_start)
        ignore_block = section[ignore_start:ignore_end]
        assert "UP031" in ignore_block, (
            "UP031 must be in pyproject.toml ignore list — "
            "ruff cannot auto-fix % formatting in comprehensions (LLM-generated pattern)"
        )

    def test_ruff_gate_does_not_fail_on_percent_in_comprehension(self, tmp_path):
        """A file with % formatting in a list comprehension must pass the ruff compile gate."""
        import subprocess as _sp
        # Fully annotated to avoid ANN failures; the only potential UP031 issue
        # is the % formatting inside the comprehension.
        code = (
            'def f(items: list[tuple[int, str]]) -> list[str]:\n'
            '    return ["item %d: %s" % (i, s) for i, s in items]\n'
        )
        py_file = tmp_path / "test_up031.py"
        py_file.write_text(code)
        # Simulate the ruff gate: --fix first, then strict check
        _sp.run(
            ["python3", "-m", "ruff", "check", str(py_file), "--fix", "--unsafe-fixes", "--exit-zero"],
            capture_output=True, text=True, cwd=str(tmp_path),
        )
        result = _sp.run(
            ["python3", "-m", "ruff", "check", str(py_file)],
            capture_output=True, text=True,
            cwd=str(__import__("pathlib").Path(__file__).parent.parent),  # use project pyproject.toml
        )
        # With UP031 in ignore list, the gate must pass despite % formatting
        assert result.returncode == 0, (
            f"ruff gate failed on UP031 pattern. Output:\n{result.stdout + result.stderr}"
        )


# ─────────────────────────────────────────────────────────────
# Fix B: _is_test_task detection
# ─────────────────────────────────────────────────────────────

class TestIsTestTask:
    """Unit tests for _is_test_task helper.

    Root cause (run 30624494792): WC027-02 is a test task (output_files under
    tests/) but the groomer used service_dir='src/billing-engine'.  The file was
    written to the wrong location and the compile gate failed with FileNotFoundError.
    """

    def test_scope_with_tests_path_is_test_task(self):
        task = {"scope": "tests/billing-engine/test_markup.py — test: cost_floor reads bundle_profiles"}
        assert groom_sprint._is_test_task(task) is True

    def test_scope_with_src_path_is_not_test_task(self):
        task = {"scope": "src/billing-engine/markup/models.py — Pydantic: ThreadEntry, BundleProfile"}
        assert groom_sprint._is_test_task(task) is False

    def test_scope_with_mixed_src_and_tests_is_not_test_task(self):
        """When scope references both src/ and tests/ files, task is NOT a pure test task."""
        task = {"scope": "src/billing-engine/markup/engine.py — implement; tests/billing-engine/test_x.py — test"}
        assert groom_sprint._is_test_task(task) is False

    def test_scope_starting_with_tests_no_explicit_path(self):
        """Fallback: scope starts with 'tests/' even without a full path."""
        task = {"scope": "tests/billing-engine/test_x.py — cover happy path"}
        assert groom_sprint._is_test_task(task) is True

    def test_empty_scope_is_not_test_task(self):
        task = {"scope": ""}
        assert groom_sprint._is_test_task(task) is False

    def test_missing_scope_key_is_not_test_task(self):
        task = {}
        assert groom_sprint._is_test_task(task) is False

    def test_only_tests_paths_returns_true(self):
        """All detected file paths are under tests/ → True."""
        task = {"scope": "tests/billing-engine/test_markup.py, tests/billing-engine/test_router.py — full suite"}
        assert groom_sprint._is_test_task(task) is True


# ─────────────────────────────────────────────────────────────
# Fix B: _extract_output_files with include_tests=True
# ─────────────────────────────────────────────────────────────

class TestExtractOutputFilesIncludeTests:
    """Tests for the new include_tests parameter of _extract_output_files.

    When grooming a test task, the scaffold SubTaskDef declares output_files
    under tests/.  The default filter (include_tests=False) would return [] and
    cause the chain builder to abort.  include_tests=True includes those paths.
    """

    def test_default_excludes_tests_path(self):
        literal = 'output_files=["tests/billing-engine/test_markup.py"]'
        assert groom_sprint._extract_output_files(literal) == []

    def test_include_tests_returns_tests_path(self):
        literal = 'output_files=["tests/billing-engine/test_markup.py"]'
        result = groom_sprint._extract_output_files(literal, include_tests=True)
        assert result == ["tests/billing-engine/test_markup.py"]

    def test_include_tests_still_excludes_skeleton(self):
        literal = 'output_files=["tests/billing-engine/test_markup.py", "src/billing-engine/skeleton/wbe_interfaces.py"]'
        result = groom_sprint._extract_output_files(literal, include_tests=True)
        assert result == ["tests/billing-engine/test_markup.py"]

    def test_include_tests_false_does_not_include_tests_path(self):
        literal = 'output_files=["tests/billing-engine/test_markup.py"]'
        result = groom_sprint._extract_output_files(literal, include_tests=False)
        assert result == []

    def test_impl_files_returned_regardless_of_flag(self):
        """src/ files should be returned whether include_tests is True or False."""
        literal = 'output_files=["src/billing-engine/markup/models.py"]'
        assert groom_sprint._extract_output_files(literal, include_tests=True) == ["src/billing-engine/markup/models.py"]
        assert groom_sprint._extract_output_files(literal, include_tests=False) == ["src/billing-engine/markup/models.py"]


# ─────────────────────────────────────────────────────────────
# Fix B: _generate_pytest_run_subtaskdef
# ─────────────────────────────────────────────────────────────

class TestGeneratePytestRunSubtaskdef:
    """Tests for the fully-templated pytest run subtask generated for test tasks."""

    def test_id_is_task_c(self):
        result = groom_sprint._generate_pytest_run_subtaskdef(
            task_id="WC027-02",
            test_output_files=["tests/billing-engine/test_markup.py"],
            wc_filename="WC-027-wbe.md",
            stack="python",
        )
        assert '"WC027-02c"' in result

    def test_depends_on_polish_b(self):
        result = groom_sprint._generate_pytest_run_subtaskdef(
            task_id="WC027-02",
            test_output_files=["tests/billing-engine/test_markup.py"],
            wc_filename="WC-027-wbe.md",
            stack="python",
        )
        assert 'depends_on=["WC027-02b"]' in result

    def test_compile_gate_is_pytest(self):
        result = groom_sprint._generate_pytest_run_subtaskdef(
            task_id="WC027-02",
            test_output_files=["tests/billing-engine/test_markup.py"],
            wc_filename="WC-027-wbe.md",
            stack="python",
        )
        assert 'compile_gate="pytest"' in result

    def test_service_dir_is_test_directory(self):
        """service_dir for pytest run must be the tests/ directory, not src/."""
        result = groom_sprint._generate_pytest_run_subtaskdef(
            task_id="WC027-02",
            test_output_files=["tests/billing-engine/test_markup.py"],
            wc_filename="WC-027-wbe.md",
            stack="python",
        )
        assert 'service_dir="tests/billing-engine"' in result

    def test_no_llm_call_needed(self):
        """Fully templated — no api_key parameter needed."""
        result = groom_sprint._generate_pytest_run_subtaskdef(
            task_id="WC027-02",
            test_output_files=["tests/billing-engine/test_markup.py"],
            wc_filename="WC-027-wbe.md",
            stack="python",
        )
        assert result  # non-empty string without any network call

    def test_output_files_contains_test_file(self):
        result = groom_sprint._generate_pytest_run_subtaskdef(
            task_id="WC027-02",
            test_output_files=["tests/billing-engine/test_markup.py"],
            wc_filename="WC-027-wbe.md",
            stack="python",
        )
        assert '"tests/billing-engine/test_markup.py"' in result

    def test_custom_polish_id_used_in_depends_on(self):
        result = groom_sprint._generate_pytest_run_subtaskdef(
            task_id="WC027-02",
            test_output_files=["tests/billing-engine/test_markup.py"],
            wc_filename="WC-027-wbe.md",
            stack="python",
            polish_id="WC027-02b",
        )
        assert 'depends_on=["WC027-02b"]' in result


# ─────────────────────────────────────────────────────────────
# Fix B: _generate_subtask_chain for test tasks
# ─────────────────────────────────────────────────────────────

_SAMPLE_TEST_SCAFFOLD_LITERAL = textwrap.dedent("""\
    SubTaskDef(
        id="WC027-02a",
        description="Write pytest tests for BundleEngine cost_floor and derive_price",
        type="llm",
        depends_on=["WC027-01bc"],
        compile_gate="ruff",
        service_dir="",
        wc_task_id="WC027-02",
        stack="python",
        output_files=[
            "tests/billing-engine/test_markup.py",
        ],
        inject_source_files=[
            "src/billing-engine/markup/bundle_engine.py",
        ],
        spec_sections={
            "work-contracts/WC-027-wbe.md": "WC027-02",
        },
        constitutional_check="TEST SCAFFOLD",
        model_hint="reasoning",
        max_tokens=8000,
    )""")


class TestGenerateSubtaskChainTestTask:
    """Integration tests for test task handling in _generate_subtask_chain.

    Root cause (run 30624494792):
    1. service_dir='src/billing-engine' caused test file to be written to wrong location.
    2. Scaffold used implementation prompt → LLM generated engine.py, endpoints.py, models.py
       in addition to test_markup.py.
    3. _extract_output_files excluded the tests/ path → chain builder aborted.
    """

    _test_task = {
        "task_id": "WC027-02",
        "scope": "tests/billing-engine/test_markup.py — test: cost_floor reads bundle_profiles",
        "model_hint": "reasoning",
    }

    def _make_llm(self, responses: list) -> object:
        it = iter(responses)
        return lambda *a, **kw: next(it, None)

    def test_test_task_uses_empty_service_dir(self, monkeypatch):
        """service_dir must be '' for test tasks so tests/ paths resolve from repo root."""
        monkeypatch.setattr(groom_sprint, "_llm_call", self._make_llm([_SAMPLE_TEST_SCAFFOLD_LITERAL]))
        result = groom_sprint._generate_subtask_chain(
            task=self._test_task, skeleton="", prior_subtask_id="WC027-01bc",
            sprint_prefix="WC027", wc_filename="WC-027-wbe.md", api_key="x",
        )
        assert result is not None
        # service_dir must be "" (repo root) in all 3 subtasks for test task
        # The scaffold itself declares service_dir="" — check it propagates to polish
        assert 'service_dir=""' in result

    def test_test_task_scaffold_uses_test_prose_prompt(self, monkeypatch):
        """Test task scaffold is built deterministically — LLM is NOT called (no FORMAT_FAILURE risk)."""
        call_count = [0]

        def counting_llm(prompt: str, system: str, api_key: str, max_tokens: int = 2048) -> str:
            call_count[0] += 1
            return _SAMPLE_TEST_SCAFFOLD_LITERAL

        monkeypatch.setattr(groom_sprint, "_llm_call", counting_llm)
        result = groom_sprint._generate_subtask_chain(
            task=self._test_task, skeleton="", prior_subtask_id=None,
            sprint_prefix="WC027", wc_filename="WC-027-wbe.md", api_key="x",
        )
        assert result is not None, "chain must succeed"
        assert call_count[0] == 0, (
            "Test task scaffold must NOT call LLM — prose is built deterministically to avoid FORMAT_FAILURE"
        )

    def test_test_task_prompt_includes_scope_paths(self, monkeypatch):
        """Test task SubTaskDef output_files must contain the scope path (deterministic — no LLM)."""
        result = groom_sprint._generate_subtask_chain(
            task=self._test_task, skeleton="", prior_subtask_id=None,
            sprint_prefix="WC027", wc_filename="WC-027-wbe.md", api_key="x",
        )
        assert result is not None, "chain must succeed"
        # Scope path appears in the generated SubTaskDef output_files
        assert "tests/billing-engine/test_markup.py" in result

    def test_test_task_produces_pytest_run_as_c_subtask(self, monkeypatch):
        """c-subtask for a test task must use compile_gate='pytest', not LLM-generated tests."""
        monkeypatch.setattr(groom_sprint, "_llm_call", self._make_llm([_SAMPLE_TEST_SCAFFOLD_LITERAL]))
        result = groom_sprint._generate_subtask_chain(
            task=self._test_task, skeleton="", prior_subtask_id=None,
            sprint_prefix="WC027", wc_filename="WC-027-wbe.md", api_key="x",
        )
        assert result is not None
        assert '"WC027-02c"' in result
        assert 'compile_gate="pytest"' in result

    def test_test_task_only_calls_llm_once(self, monkeypatch):
        """Test task chain makes 0 LLM calls — all prose built deterministically to avoid FORMAT_FAILURE."""
        call_count = [0]

        def counting_llm(*a, **kw):
            call_count[0] += 1
            return _SAMPLE_TEST_SCAFFOLD_LITERAL

        monkeypatch.setattr(groom_sprint, "_llm_call", counting_llm)
        result = groom_sprint._generate_subtask_chain(
            task=self._test_task, skeleton="", prior_subtask_id=None,
            sprint_prefix="WC027", wc_filename="WC-027-wbe.md", api_key="x",
        )
        assert result is not None
        assert call_count[0] == 0, (
            f"Test task chain must make 0 LLM calls (deterministic prose), got {call_count[0]}"
        )

    def test_test_task_output_files_includes_tests_path(self, monkeypatch):
        """output_files for test task scaffold must include the tests/ path."""
        monkeypatch.setattr(groom_sprint, "_llm_call", self._make_llm([_SAMPLE_TEST_SCAFFOLD_LITERAL]))
        result = groom_sprint._generate_subtask_chain(
            task=self._test_task, skeleton="", prior_subtask_id=None,
            sprint_prefix="WC027", wc_filename="WC-027-wbe.md", api_key="x",
        )
        assert result is not None
        assert "tests/billing-engine/test_markup.py" in result

    def test_impl_task_still_uses_service_dir(self, monkeypatch):
        """Regression: impl tasks must still get service_dir from _SERVICE_MAP."""
        impl_task = {
            "task_id": "WC027-01",
            "scope": "src/billing-engine/markup/models.py — Pydantic models",
            "model_hint": "auto",
        }
        monkeypatch.setattr(groom_sprint, "_llm_call", self._make_llm([_SAMPLE_SCAFFOLD_LITERAL, _SAMPLE_TEST_LITERAL]))
        result = groom_sprint._generate_subtask_chain(
            task=impl_task, skeleton="", prior_subtask_id=None,
            sprint_prefix="WC027", wc_filename="WC-027-wbe.md", api_key="x",
        )
        assert result is not None
        # Impl task must use the service_dir from _SERVICE_MAP, not ""
        assert 'service_dir="src/billing-engine"' in result

    def test_test_task_validation_passes(self, monkeypatch):
        """Generated test task entry must pass _validate_generated_entry."""
        monkeypatch.setattr(groom_sprint, "_llm_call", self._make_llm([_SAMPLE_TEST_SCAFFOLD_LITERAL]))
        result = groom_sprint._generate_subtask_chain(
            task=self._test_task, skeleton="", prior_subtask_id=None,
            sprint_prefix="WC027", wc_filename="WC-027-wbe.md", api_key="x",
        )
        assert result is not None
        assert groom_sprint._validate_generated_entry(result, "WC027-02") is True


# ─────────────────────────────────────────────────────────────
# Structural refactor: deterministic path extraction
# ─────────────────────────────────────────────────────────────

class TestExtractScopePaths:
    """Verify _extract_scope_paths parses exact .py paths from WC scope strings.

    Root cause (run 30628288678): LLM invented 'billing_engine' (Python convention)
    instead of 'billing-engine' (ADR-016 hyphenated naming). Paths must come from
    the WC scope string directly, never from LLM re-derivation.
    """

    def test_hyphenated_service_dir_preserved(self):
        scope = "`tests/billing-engine/test_markup.py` — test: cost_floor reads"
        paths = groom_sprint._extract_scope_paths(scope)
        assert paths == ["tests/billing-engine/test_markup.py"]

    def test_underscore_would_not_appear(self):
        """The LLM hallucination was 'billing_engine'; confirm we parse 'billing-engine'."""
        scope = "`tests/billing-engine/test_markup.py` — test"
        paths = groom_sprint._extract_scope_paths(scope)
        assert all("billing_engine" not in p for p in paths)
        assert any("billing-engine" in p for p in paths)

    def test_multiple_src_paths(self):
        scope = "`src/billing-engine/markup/models.py` — Pydantic; `src/billing-engine/markup/bundle_engine.py` — BundleEngine"
        paths = groom_sprint._extract_scope_paths(scope)
        assert "src/billing-engine/markup/models.py" in paths
        assert "src/billing-engine/markup/bundle_engine.py" in paths
        assert len(paths) == 2

    def test_backticks_stripped(self):
        scope = "`src/billing-engine/markup/router.py` — FastAPI"
        paths = groom_sprint._extract_scope_paths(scope)
        assert paths == ["src/billing-engine/markup/router.py"]

    def test_skeleton_paths_excluded(self):
        scope = "see src/billing-engine/skeleton/wbe_interfaces.py for ABC definition"
        paths = groom_sprint._extract_scope_paths(scope)
        assert paths == []

    def test_no_paths_returns_empty(self):
        scope = "Implement ThreadCatalogService.list_threads() — see D-07 spec"
        paths = groom_sprint._extract_scope_paths(scope)
        assert paths == []

    def test_non_py_file_not_matched(self):
        scope = "Update src/billing-engine/migrations/001.sql — alter bundle_profiles"
        paths = groom_sprint._extract_scope_paths(scope)
        assert paths == []

    def test_mixed_src_and_tests_paths(self):
        scope = "src/billing-engine/markup/engine.py; tests/billing-engine/test_engine.py"
        paths = groom_sprint._extract_scope_paths(scope)
        assert "src/billing-engine/markup/engine.py" in paths
        assert "tests/billing-engine/test_engine.py" in paths

    def test_wc027_01a_real_scope(self):
        scope = (
            "`src/billing-engine/markup/models.py` — Pydantic: `ThreadEntry`, `BundleProfile`, "
            "`PriceConfig`; `src/billing-engine/markup/bundle_engine.py` — BundleEngine"
        )
        paths = groom_sprint._extract_scope_paths(scope)
        assert "src/billing-engine/markup/models.py" in paths
        assert "src/billing-engine/markup/bundle_engine.py" in paths

    def test_wc027_02_real_scope(self):
        """WC027-02 real scope must return hyphenated path — the root cause of run 30628288678."""
        scope = (
            "`tests/billing-engine/test_markup.py` — test: cost_floor reads "
            "`bundle_profiles.cost_floor_paise` (not recomputed)"
        )
        paths = groom_sprint._extract_scope_paths(scope)
        assert paths == ["tests/billing-engine/test_markup.py"]
        # Confirm the hallucinated underscore variant never appears
        assert "billing_engine" not in paths[0]


class TestDeriveServiceDir:
    """Verify _derive_service_dir returns correct service directory deterministically."""

    def test_src_billing_engine(self):
        paths = ["src/billing-engine/markup/models.py", "src/billing-engine/markup/bundle_engine.py"]
        assert groom_sprint._derive_service_dir(paths) == "src/billing-engine"

    def test_test_only_returns_empty(self):
        paths = ["tests/billing-engine/test_markup.py"]
        assert groom_sprint._derive_service_dir(paths) == ""

    def test_empty_list_returns_empty(self):
        assert groom_sprint._derive_service_dir([]) == ""

    def test_all_tests_returns_empty(self):
        paths = ["tests/billing-engine/test_a.py", "tests/billing-engine/test_b.py"]
        assert groom_sprint._derive_service_dir(paths) == ""

    def test_mixed_returns_src_service(self):
        """Mixed src+tests scope: service_dir from first src/ path."""
        paths = ["src/billing-engine/markup/engine.py", "tests/billing-engine/test_engine.py"]
        assert groom_sprint._derive_service_dir(paths) == "src/billing-engine"

    def test_different_service(self):
        paths = ["src/constitutional-engine/enforcer.py"]
        assert groom_sprint._derive_service_dir(paths) == "src/constitutional-engine"


class TestBuildScaffoldSubtaskdef:
    """Verify _build_scaffold_subtaskdef produces correct SubTaskDef literal."""

    def test_impl_task_uses_py_compile_gate(self):
        result = groom_sprint._build_scaffold_subtaskdef(
            task_id="WC027-01a", output_files=["src/billing-engine/markup/models.py"],
            service_dir="src/billing-engine", inject_source_files=["src/billing-engine/skeleton/wbe_interfaces.py"],
            description="Implement Pydantic models.", constitutional_check="ADR-036.",
            is_test=False, stack="python", wc_filename="WC-027.md",
            prior_subtask_id=None, model_hint="auto", max_tokens=4000,
        )
        assert 'compile_gate=\'py_compile\'' in result
        assert 'id=\'WC027-01aa\'' in result

    def test_test_task_uses_ruff_gate(self):
        result = groom_sprint._build_scaffold_subtaskdef(
            task_id="WC027-02", output_files=["tests/billing-engine/test_markup.py"],
            service_dir="", inject_source_files=["src/billing-engine/markup/models.py"],
            description="Write pytest tests for BundleEngine.", constitutional_check="C-059.",
            is_test=True, stack="python", wc_filename="WC-027.md",
            prior_subtask_id=None, model_hint="reasoning", max_tokens=8000,
        )
        assert 'compile_gate=\'ruff\'' in result
        assert 'id=\'WC027-02a\'' in result

    def test_hyphenated_path_preserved_exactly(self):
        """Key regression: billing-engine hyphen must survive in output_files."""
        result = groom_sprint._build_scaffold_subtaskdef(
            task_id="WC027-02", output_files=["tests/billing-engine/test_markup.py"],
            service_dir="", inject_source_files=[],
            description="Write pytest tests.", constitutional_check="C-059.",
            is_test=True, stack="python", wc_filename="WC-027.md",
            prior_subtask_id=None, model_hint="reasoning", max_tokens=8000,
        )
        assert "tests/billing-engine/test_markup.py" in result
        assert "billing_engine" not in result

    def test_prior_subtask_id_in_depends_on(self):
        result = groom_sprint._build_scaffold_subtaskdef(
            task_id="WC027-02", output_files=["tests/billing-engine/test_markup.py"],
            service_dir="", inject_source_files=[],
            description="Write pytest tests.", constitutional_check="C-059.",
            is_test=True, stack="python", wc_filename="WC-027.md",
            prior_subtask_id="WC027-01bc", model_hint="reasoning", max_tokens=8000,
        )
        assert "'WC027-01bc'" in result

    def test_no_prior_subtask_gives_empty_depends_on(self):
        result = groom_sprint._build_scaffold_subtaskdef(
            task_id="WC027-01a", output_files=["src/billing-engine/markup/models.py"],
            service_dir="src/billing-engine", inject_source_files=[],
            description="Implement models.", constitutional_check="ADR-036.",
            is_test=False, stack="python", wc_filename="WC-027.md",
            prior_subtask_id=None, model_hint="auto", max_tokens=4000,
        )
        assert "depends_on=[]" in result

    def test_description_with_quotes_safe(self):
        """repr() must safely handle quotes in description."""
        result = groom_sprint._build_scaffold_subtaskdef(
            task_id="WC027-01a", output_files=["src/billing-engine/markup/models.py"],
            service_dir="src/billing-engine", inject_source_files=[],
            description="Implement 'BundleEngine' for \"markup\".",
            constitutional_check="ADR-036.", is_test=False, stack="python",
            wc_filename="WC-027.md", prior_subtask_id=None, model_hint="auto", max_tokens=4000,
        )
        # Must still be ast-parseable
        import ast as _ast
        wrapper = "class SubTaskDef:\n    def __init__(self, **kw): pass\n_ = " + result
        _ast.parse(wrapper)

    def test_output_is_ast_parseable(self):
        result = groom_sprint._build_scaffold_subtaskdef(
            task_id="WC027-02", output_files=["tests/billing-engine/test_markup.py"],
            service_dir="", inject_source_files=["src/billing-engine/markup/models.py"],
            description="Write pytest tests for BundleEngine markup engine.",
            constitutional_check="TEST SCAFFOLD — write pytest to tests/billing-engine/.\nCover: C-059.",
            is_test=True, stack="python", wc_filename="WC-027.md",
            prior_subtask_id="WC027-01bc", model_hint="reasoning", max_tokens=8000,
        )
        import ast as _ast
        wrapper = "class SubTaskDef:\n    def __init__(self, **kw): pass\n_ = " + result
        _ast.parse(wrapper)


class TestAccumulatedImplFilesForTestTask:
    """Verify that test tasks receive accumulated impl files as inject_source_files."""

    _test_task = {
        "task_id": "WC027-02",
        "scope": "tests/billing-engine/test_markup.py — test: cost_floor",
        "model_hint": "reasoning",
    }

    def test_test_task_inject_includes_accumulated_impl(self, monkeypatch):
        """inject_source_files for test task must include all prior impl output files."""
        captured_prompts: list[str] = []

        def capture(prompt: str, system: str, api_key: str, max_tokens: int = 2048) -> str:
            captured_prompts.append(prompt)
            return '{"description": "Write tests.", "constitutional_check": "C-059."}'

        monkeypatch.setattr(groom_sprint, "_llm_call", capture)
        impl_files = [
            "src/billing-engine/markup/models.py",
            "src/billing-engine/markup/bundle_engine.py",
            "src/billing-engine/markup/router.py",
        ]
        result = groom_sprint._generate_subtask_chain(
            task=self._test_task, skeleton="", skeleton_files=[],
            prior_subtask_id=None, sprint_prefix="WC027",
            wc_filename="WC-027.md", api_key="x",
            accumulated_impl_files=impl_files,
        )
        assert result is not None
        # All accumulated impl files must appear in inject_source_files
        for f in impl_files:
            assert f in result

    def test_test_task_output_files_exact_hyphen(self, monkeypatch):
        """output_files must use hyphenated path from scope, not LLM-derived underscore."""
        monkeypatch.setattr(groom_sprint, "_llm_call",
            lambda *a, **kw: '{"description": "x", "constitutional_check": "y"}')
        result = groom_sprint._generate_subtask_chain(
            task=self._test_task, skeleton="", skeleton_files=[],
            prior_subtask_id=None, sprint_prefix="WC027",
            wc_filename="WC-027.md", api_key="x",
        )
        assert result is not None
        assert "tests/billing-engine/test_markup.py" in result
        assert "billing_engine" not in result
