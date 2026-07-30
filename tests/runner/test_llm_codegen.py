# Implements: tests/runner/test_llm_codegen.py
# constitutional_basis: C-076 (≥90% coverage), ADR-030 (code gen protocol), C-077 (cost ceiling)
"""Tests for runner/llm_codegen.py — parse_llm_files, write_llm_files, validate_written_files,
call_llm (mocked), prompt caching header."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

_scripts = str(Path(__file__).parent.parent.parent / "scripts")
if _scripts not in sys.path:
    sys.path.insert(0, _scripts)

from runner.llm_codegen import parse_llm_files, write_llm_files, validate_written_files


class TestParseLlmFiles:
    def test_parses_single_file_block(self):
        response = '<file path="src/billing-engine/models.py">x = 1</file>'
        files = parse_llm_files(response)
        assert "src/billing-engine/models.py" in files
        assert files["src/billing-engine/models.py"] == "x = 1"

    def test_parses_multiple_file_blocks(self):
        response = (
            '<file path="src/billing-engine/a.py">a = 1</file>'
            '<file path="tests/billing-engine/test_a.py">import a</file>'
        )
        files = parse_llm_files(response)
        assert len(files) == 2

    def test_rejects_constitution_path(self):
        response = '<file path="constitution/HACK.md">evil</file>'
        files = parse_llm_files(response)
        assert len(files) == 0

    def test_rejects_adr_path(self):
        response = '<file path="adr/ADR-999.md">evil</file>'
        files = parse_llm_files(response)
        assert len(files) == 0

    def test_accepts_src_path(self):
        response = '<file path="src/foo/bar.py">pass</file>'
        files = parse_llm_files(response)
        assert "src/foo/bar.py" in files

    def test_accepts_tests_path(self):
        response = '<file path="tests/foo/test_bar.py">pass</file>'
        files = parse_llm_files(response)
        assert "tests/foo/test_bar.py" in files

    def test_accepts_infrastructure_postgres(self):
        response = '<file path="infrastructure/postgres/init/12-foo.sql">SELECT 1;</file>'
        files = parse_llm_files(response)
        assert "infrastructure/postgres/init/12-foo.sql" in files

    def test_single_quotes_path(self):
        response = "<file path='src/svc/x.py'>pass</file>"
        files = parse_llm_files(response)
        assert "src/svc/x.py" in files

    def test_strips_leading_trailing_whitespace_from_content(self):
        response = '<file path="src/svc/x.py">\n  code\n</file>'
        files = parse_llm_files(response)
        assert files["src/svc/x.py"] == "code"

    def test_prints_design_question_warning(self, capsys):
        response = '<file path="src/svc/x.py">code\nDESIGN_QUESTION: what is X?</file>'
        parse_llm_files(response)
        captured = capsys.readouterr()
        assert "Design question" in captured.out

    def test_empty_response_returns_empty(self):
        assert parse_llm_files("") == {}

    def test_no_file_blocks_returns_empty(self):
        assert parse_llm_files("No file blocks here.") == {}


class TestWriteLlmFiles:
    def test_writes_file(self, tmp_path, monkeypatch):
        import runner.llm_codegen as lc
        monkeypatch.setattr(lc, "REPO_ROOT", tmp_path)
        files = {"src/svc/x.py": "x = 1\n"}
        written = write_llm_files(files)
        assert "src/svc/x.py" in written
        assert (tmp_path / "src" / "svc" / "x.py").read_text() == "x = 1\n"

    def test_creates_parent_dirs(self, tmp_path, monkeypatch):
        import runner.llm_codegen as lc
        monkeypatch.setattr(lc, "REPO_ROOT", tmp_path)
        write_llm_files({"src/a/b/c/d.py": "pass"})
        assert (tmp_path / "src" / "a" / "b" / "c" / "d.py").exists()

    def test_returns_list_of_written(self, tmp_path, monkeypatch):
        import runner.llm_codegen as lc
        monkeypatch.setattr(lc, "REPO_ROOT", tmp_path)
        written = write_llm_files({"src/s/x.py": "x", "tests/s/t.py": "t"})
        assert len(written) == 2

    def test_prints_written_path(self, tmp_path, monkeypatch, capsys):
        import runner.llm_codegen as lc
        monkeypatch.setattr(lc, "REPO_ROOT", tmp_path)
        write_llm_files({"src/s/y.py": "y"})
        out = capsys.readouterr().out
        assert "Written:" in out


class TestValidateWrittenFiles:
    def test_valid_python_ok(self, tmp_path, monkeypatch):
        import runner.llm_codegen as lc
        monkeypatch.setattr(lc, "REPO_ROOT", tmp_path)
        f = tmp_path / "src" / "svc" / "valid.py"
        f.parent.mkdir(parents=True)
        f.write_text("x = 1\n")
        ok, err = validate_written_files(["src/svc/valid.py"])
        assert ok
        assert err == ""

    def test_invalid_python_fails(self, tmp_path, monkeypatch):
        import runner.llm_codegen as lc
        monkeypatch.setattr(lc, "REPO_ROOT", tmp_path)
        f = tmp_path / "src" / "svc" / "bad.py"
        f.parent.mkdir(parents=True)
        f.write_text("def broken(\n")
        ok, err = validate_written_files(["src/svc/bad.py"])
        assert not ok
        assert "bad.py" in err

    def test_no_files_is_ok(self, tmp_path, monkeypatch):
        import runner.llm_codegen as lc
        monkeypatch.setattr(lc, "REPO_ROOT", tmp_path)
        ok, err = validate_written_files([])
        assert ok


class TestCallLlmPayload:
    """Tests that call_llm builds correct payload (unit — no real HTTP)."""

    def test_prompt_caching_header_sent(self, monkeypatch):
        """call_llm must send anthropic-beta: prompt-caching-2024-07-31."""
        import runner.llm_codegen as lc
        import urllib.request

        captured_headers = {}

        class FakeResp:
            def read(self):
                return json.dumps({
                    "content": [{"type": "text", "text": "<file path='src/x.py'>pass</file>"}],
                    "usage": {},
                    "stop_reason": "end_turn",
                }).encode()

            def __enter__(self): return self
            def __exit__(self, *a): pass

        def fake_urlopen(req, timeout=None):
            captured_headers.update(req.headers)
            return FakeResp()

        monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
        monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-test")

        result = lc.call_llm(
            "WC012-01", "Test task", "spec content",
            "check", model_hint="auto", max_tokens=100,
        )
        # Header keys are normalized by urllib (Title-Case)
        assert "Anthropic-beta" in captured_headers
        assert captured_headers["Anthropic-beta"] == "prompt-caching-2024-07-31"

    def test_system_prompt_is_cache_control_list(self, monkeypatch):
        """system must be a list with cache_control, not a plain string."""
        import runner.llm_codegen as lc
        import urllib.request

        captured_payload = {}

        class FakeResp:
            def read(self):
                return json.dumps({
                    "content": [{"type": "text", "text": "ok"}],
                    "usage": {}, "stop_reason": "end_turn",
                }).encode()

            def __enter__(self): return self
            def __exit__(self, *a): pass

        def fake_urlopen(req, timeout=None):
            import json as _json
            captured_payload.update(_json.loads(req.data))
            return FakeResp()

        monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
        monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-test")

        lc.call_llm("WC014-01", "desc", "spec", "check",
                    model_hint="auto", max_tokens=100)

        system = captured_payload.get("system")
        assert isinstance(system, list), "system must be a list for prompt caching"
        assert len(system) == 1
        assert system[0].get("cache_control") == {"type": "ephemeral"}

    def test_returns_none_when_no_api_key(self, monkeypatch):
        import runner.llm_codegen as lc
        monkeypatch.setenv("ANTHROPIC_API_KEY", "")
        result = lc.call_llm("WC012-01", "desc", "spec", "check")
        assert result is None

    def test_returns_none_for_model_hint_none(self, monkeypatch):
        import runner.llm_codegen as lc
        result = lc.call_llm("WC012-01", "desc", "spec", "check", model_hint="none")
        assert result is None

    def test_raises_runtime_error_on_429(self, monkeypatch):
        import runner.llm_codegen as lc
        import urllib.request
        import urllib.error

        def fake_urlopen(req, timeout=None):
            raise urllib.error.HTTPError(url="", code=429, msg="", hdrs=None,
                                         fp=__import__("io").BytesIO(b"rate limit"))

        monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

        with pytest.raises(RuntimeError, match="RATE_LIMIT"):
            lc.call_llm("WC012-01", "desc", "spec", "check",
                        model_hint="auto", max_tokens=100)

    def test_raises_runtime_error_on_timeout(self, monkeypatch):
        import runner.llm_codegen as lc
        import urllib.request

        def fake_urlopen(req, timeout=None):
            raise TimeoutError("timed out")

        monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

        with pytest.raises(RuntimeError, match="API_TIMEOUT"):
            lc.call_llm("WC012-01", "desc", "spec", "check",
                        model_hint="auto", max_tokens=100)
