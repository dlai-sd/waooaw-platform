# Implements: tests/runner/test_system_prompts.py
# constitutional_basis: C-076 (≥90% coverage), C-059 (Traceability)
"""Tests for runner/system_prompts.py — _build_system_prompt, _TASK_STACK_MAP, get_branch_context."""
from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

_scripts = str(Path(__file__).parent.parent.parent / "scripts")
if _scripts not in sys.path:
    sys.path.insert(0, _scripts)

from runner.system_prompts import (
    CONSTITUTIONAL_SYSTEM_PROMPT,
    _BASE_SYSTEM_PROMPT,
    _STACK_EXPERTS,
    _TASK_STACK_MAP,
    _build_system_prompt,
    get_branch_context,
)


class TestBaseSystemPrompt:
    def test_contains_constitutional_obligations(self):
        assert "CONSTITUTIONAL OBLIGATIONS" in _BASE_SYSTEM_PROMPT

    def test_contains_c059(self):
        assert "C-059" in _BASE_SYSTEM_PROMPT

    def test_contains_c076(self):
        assert "C-076" in _BASE_SYSTEM_PROMPT

    def test_contains_forbidden_patterns(self):
        assert "FORBIDDEN PATTERNS" in _BASE_SYSTEM_PROMPT

    def test_contains_output_format(self):
        assert "OUTPUT FORMAT" in _BASE_SYSTEM_PROMPT

    def test_contains_extend_not_replace(self):
        assert "EXTEND-NOT-REPLACE" in _BASE_SYSTEM_PROMPT


class TestStackExperts:
    def test_has_dotnet_expert(self):
        assert "dotnet" in _STACK_EXPERTS

    def test_has_python_expert(self):
        assert "python" in _STACK_EXPERTS

    def test_has_terraform_expert(self):
        assert "terraform" in _STACK_EXPERTS

    def test_has_typescript_expert(self):
        assert "typescript" in _STACK_EXPERTS

    def test_dotnet_expert_mentions_csharp(self):
        assert "C# 12" in _STACK_EXPERTS["dotnet"]

    def test_python_expert_mentions_fastapi(self):
        assert "FastAPI" in _STACK_EXPERTS["python"]


class TestTaskStackMap:
    def test_wc012_is_dotnet(self):
        assert _TASK_STACK_MAP["WC012"] == "dotnet"

    def test_wc014_is_python(self):
        assert _TASK_STACK_MAP["WC014"] == "python"

    def test_wc016_is_terraform(self):
        assert _TASK_STACK_MAP["WC016"] == "terraform"

    def test_wc017_is_typescript(self):
        assert _TASK_STACK_MAP["WC017"] == "typescript"

    def test_wc025_is_python(self):
        assert _TASK_STACK_MAP["WC025"] == "python"

    def test_wc026_is_python(self):
        assert _TASK_STACK_MAP["WC026"] == "python"


class TestBuildSystemPrompt:
    def test_wc012_includes_dotnet_expert(self):
        prompt = _build_system_prompt("WC012-01")
        assert "C# 12" in prompt
        assert _BASE_SYSTEM_PROMPT in prompt

    def test_wc014_includes_python_expert(self):
        prompt = _build_system_prompt("WC014-01")
        assert "FastAPI" in prompt

    def test_wc016_includes_terraform_expert(self):
        prompt = _build_system_prompt("WC016-01")
        assert "Terraform" in prompt

    def test_wc017_includes_typescript_expert(self):
        prompt = _build_system_prompt("WC017-01")
        assert "TypeScript" in prompt

    def test_unknown_task_defaults_to_dotnet(self):
        prompt = _build_system_prompt("WC999-01")
        assert "C# 12" in prompt

    def test_returns_string(self):
        assert isinstance(_build_system_prompt("WC012-01"), str)


class TestConstitutionalSystemPromptAlias:
    def test_is_string(self):
        assert isinstance(CONSTITUTIONAL_SYSTEM_PROMPT, str)

    def test_contains_base(self):
        assert _BASE_SYSTEM_PROMPT in CONSTITUTIONAL_SYSTEM_PROMPT


class TestGetBranchContext:
    def test_returns_empty_on_git_failure(self, monkeypatch):
        def fake_run(cmd, check=True, capture=False):
            m = MagicMock()
            m.returncode = 1
            m.stdout = ""
            return m
        monkeypatch.setattr("runner.system_prompts.run", fake_run)
        result = get_branch_context()
        assert result == ""

    def test_returns_empty_when_no_code_files(self, monkeypatch):
        def fake_run(cmd, check=True, capture=False):
            m = MagicMock()
            m.returncode = 0
            m.stdout = "README.md\ndocs/foo.txt\n"  # no .cs/.py files
            return m
        monkeypatch.setattr("runner.system_prompts.run", fake_run)
        result = get_branch_context()
        assert result == ""

    def test_returns_context_block_when_files_present(self, tmp_path, monkeypatch):
        # Create a fake .py file
        src_dir = tmp_path / "src" / "billing-engine"
        src_dir.mkdir(parents=True)
        py_file = src_dir / "models.py"
        py_file.write_text("# Implements: test\npublic class Foo {}\n")

        def fake_run(cmd, check=True, capture=False):
            m = MagicMock()
            m.returncode = 0
            m.stdout = "src/billing-engine/models.py\n"
            return m

        import runner.system_prompts as sp_mod
        monkeypatch.setattr(sp_mod, "run", fake_run)
        monkeypatch.setattr(sp_mod, "REPO_ROOT", tmp_path)
        monkeypatch.delenv("SPRINT_TASK_ID", raising=False)

        result = get_branch_context()
        assert "BRANCH CONTEXT" in result

    def test_returns_empty_on_exception(self, monkeypatch):
        def fake_run(*args, **kwargs):
            raise RuntimeError("git not available")
        monkeypatch.setattr("runner.system_prompts.run", fake_run)
        result = get_branch_context()
        assert result == ""
