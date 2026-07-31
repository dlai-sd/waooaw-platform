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
    _task = {"task_id": "WC027-01", "scope": "SQLAlchemy models", "model_hint": "auto"}

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
        scaffold_no_files = 'SubTaskDef(\n    id="WC027-01a",\n    output_files=[],\n    compile_gate="py_compile",\n)'
        monkeypatch.setattr(groom_sprint, "_llm_call", self._make_llm([scaffold_no_files]))
        result = groom_sprint._generate_subtask_chain(
            task=self._task, skeleton="", prior_subtask_id=None,
            sprint_prefix="WC027", wc_filename="WC-027.md", api_key="x",
        )
        assert result is None

    def test_returns_none_when_test_llm_fails(self, monkeypatch):
        monkeypatch.setattr(groom_sprint, "_llm_call", self._make_llm([_SAMPLE_SCAFFOLD_LITERAL, None]))
        result = groom_sprint._generate_subtask_chain(
            task=self._task, skeleton="", prior_subtask_id=None,
            sprint_prefix="WC027", wc_filename="WC-027.md", api_key="x",
        )
        assert result is None

    def test_prior_subtask_id_sets_depends_on(self, monkeypatch):
        monkeypatch.setattr(groom_sprint, "_llm_call", self._make_llm([_SAMPLE_SCAFFOLD_LITERAL, _SAMPLE_TEST_LITERAL]))
        result = groom_sprint._generate_subtask_chain(
            task=self._task, skeleton="", prior_subtask_id="WC027-00a",
            sprint_prefix="WC027", wc_filename="WC-027-billing.md", api_key="x",
        )
        # The scaffold prompt gets the prior_subtask_id — it appears in the LLM prompt,
        # but here we verify it doesn't corrupt the assembled result
        assert result is not None
        assert '"WC027-01a"' in result

    def test_scaffold_fenced_response_is_handled(self, monkeypatch):
        fenced = f"```python\n{_SAMPLE_SCAFFOLD_LITERAL}\n```"
        monkeypatch.setattr(groom_sprint, "_llm_call", self._make_llm([fenced, _SAMPLE_TEST_LITERAL]))
        result = groom_sprint._generate_subtask_chain(
            task=self._task, skeleton="", prior_subtask_id=None,
            sprint_prefix="WC027", wc_filename="WC-027-billing.md", api_key="x",
        )
        assert result is not None
        assert '"WC027-01a"' in result
        assert '"WC027-01b"' in result

    def test_scaffold_preamble_text_is_stripped(self, monkeypatch):
        with_preamble = f"Here is the SubTaskDef literal:\n{_SAMPLE_SCAFFOLD_LITERAL}"
        monkeypatch.setattr(groom_sprint, "_llm_call", self._make_llm([with_preamble, _SAMPLE_TEST_LITERAL]))
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
            return [_SAMPLE_SCAFFOLD_LITERAL, _SAMPLE_TEST_LITERAL][len(captured) - 1]

        monkeypatch.setattr(groom_sprint, "_llm_call", capture)
        groom_sprint._generate_subtask_chain(
            task=self._task, skeleton="SKELETON_CONTENT_HERE", prior_subtask_id=None,
            sprint_prefix="WC027", wc_filename="WC-027-billing.md", api_key="x",
        )
        scaffold_prompt = captured[0]
        assert "WC027-01" in scaffold_prompt
        assert "py_compile" in scaffold_prompt
        assert "SKELETON_CONTENT_HERE" in scaffold_prompt

    def test_prompt_includes_prior_subtask_id(self, monkeypatch):
        captured: list[str] = []

        def capture(prompt: str, system: str, api_key: str, max_tokens: int = 2048) -> str:
            captured.append(prompt)
            return [_SAMPLE_SCAFFOLD_LITERAL, _SAMPLE_TEST_LITERAL][len(captured) - 1]

        monkeypatch.setattr(groom_sprint, "_llm_call", capture)
        groom_sprint._generate_subtask_chain(
            task=self._task, skeleton="", prior_subtask_id="WC026-03a",
            sprint_prefix="WC027", wc_filename="WC-027.md", api_key="x",
        )
        assert "WC026-03a" in captured[0]


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
    """Regression: scaffold id normalisation prevents downstream BLOCKED subtasks."""

    _split_task = {"task_id": "WC027-01a", "scope": "SQLAlchemy models for markup engine", "model_hint": "reasoning"}

    def _make_llm(self, responses: list):
        it = iter(responses)
        return lambda *a, **kw: next(it, None)

    def test_invented_scaffold_id_is_normalised(self, monkeypatch):
        """Regression: id='WC027-01a-scaffold' → 'WC027-01aa' after normalisation."""
        monkeypatch.setattr(groom_sprint, "_llm_call", self._make_llm([_SCAFFOLD_WITH_INVENTED_ID, _SAMPLE_TEST_FOR_SPLIT]))
        result = groom_sprint._generate_subtask_chain(
            task=self._split_task, skeleton="", prior_subtask_id=None,
            sprint_prefix="WC027", wc_filename="WC-027-markup.md", api_key="x",
        )
        assert result is not None
        # After normalisation scaffold id must be WC027-01aa
        assert '"WC027-01aa"' in result
        assert '"WC027-01a-scaffold"' not in result

    def test_polish_depends_on_canonical_scaffold_id(self, monkeypatch):
        """Polish depends_on must reference the canonical scaffold id (WC027-01aa)."""
        monkeypatch.setattr(groom_sprint, "_llm_call", self._make_llm([_SCAFFOLD_WITH_INVENTED_ID, _SAMPLE_TEST_FOR_SPLIT]))
        result = groom_sprint._generate_subtask_chain(
            task=self._split_task, skeleton="", prior_subtask_id=None,
            sprint_prefix="WC027", wc_filename="WC-027-markup.md", api_key="x",
        )
        assert result is not None
        # Polish depends_on must be the canonical scaffold id
        assert 'depends_on=["WC027-01aa"]' in result

    def test_full_chain_passes_validation_after_normalisation(self, monkeypatch):
        """Generated entry must pass _validate_generated_entry after id normalisation."""
        monkeypatch.setattr(groom_sprint, "_llm_call", self._make_llm([_SCAFFOLD_WITH_INVENTED_ID, _SAMPLE_TEST_FOR_SPLIT]))
        result = groom_sprint._generate_subtask_chain(
            task=self._split_task, skeleton="", prior_subtask_id=None,
            sprint_prefix="WC027", wc_filename="WC-027-markup.md", api_key="x",
        )
        assert result is not None
        assert groom_sprint._validate_generated_entry(result, "WC027-01a") is True

    def test_canonical_scaffold_id_passes_through_unchanged(self, monkeypatch):
        """When LLM already used the canonical id, no normalisation occurs."""
        monkeypatch.setattr(groom_sprint, "_llm_call", self._make_llm([_SAMPLE_SCAFFOLD_LITERAL, _SAMPLE_TEST_LITERAL]))
        result = groom_sprint._generate_subtask_chain(
            task={"task_id": "WC027-01", "scope": "SQLAlchemy models", "model_hint": "auto"},
            skeleton="", prior_subtask_id=None,
            sprint_prefix="WC027", wc_filename="WC-027-billing.md", api_key="x",
        )
        assert result is not None
        assert '"WC027-01a"' in result
        assert '"WC027-01b"' in result
        assert '"WC027-01c"' in result
