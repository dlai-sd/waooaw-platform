"""C-059 PR and commit traceability contracts."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from scripts.validate_c059 import read_commit_message, read_commits, validate_commit, validate_pr_body

ROOT = Path(__file__).parents[2]


def test_actual_template_has_canonical_required_fields() -> None:
    template = (ROOT / ".github/pull_request_template.md").read_text(encoding="utf-8")
    completed = template.replace("WC-NNN", "WC-076", 1).replace("C-NNN | ADR-NNN | DP-NNN", "ADR-047", 1)
    assert validate_pr_body(completed) == []


def test_generated_markdown_body_passes() -> None:
    body = """## Summary
Fix bootstrap behavior.

**Work Contract:** WC-076
**Constitutional Basis:** ADR-047 | C-059
"""
    assert validate_pr_body(body) == []


def test_missing_fields_report_independently() -> None:
    assert validate_pr_body("## Summary\nMissing traceability") == [
        "PR_MISSING_WORK_CONTRACT: add `Work Contract: WC-<number>`",
        "PR_MISSING_CONSTITUTIONAL_BASIS: add `Constitutional Basis: C-<number> | ADR-<number> | DP-<number>`",
    ]


def test_placeholders_do_not_pass() -> None:
    assert len(validate_pr_body("Work Contract: WC-NNN\nConstitutional Basis: ADR-NNN")) == 2


def test_commit_trace_reference_may_be_in_subject_or_body() -> None:
    assert validate_commit("fix(infra): repair gate Constitutional: C-059", "") == []
    assert validate_commit("fix(infra): repair gate", "Constitutional: C-059") == []
    assert validate_commit("fix(cct): isolate WC-078 performance gate", "") == []
    assert validate_commit("fix(cct): isolate performance gate", "Work Contract: WC-078") == []


def test_blocking_commit_without_trace_fails() -> None:
    assert validate_commit("fix(infra): repair gate", "") == [
        "COMMIT_TRACE_MISSING: fix(infra): repair gate (add IB, WC, FIX, or Constitutional reference to subject or body)"
    ]


def test_commit_message_reader_ignores_git_comments(tmp_path: Path) -> None:
    message = tmp_path / "COMMIT_EDITMSG"
    message.write_text(
        "fix(validation): enforce trace before commit\n\nWork Contract: WC-109\n# staged files follow\n",
        encoding="utf-8",
    )

    assert read_commit_message(message) == (
        "fix(validation): enforce trace before commit",
        "Work Contract: WC-109",
    )


def test_repository_commit_hook_uses_containerized_c059_validator() -> None:
    hook = (ROOT / ".githooks/commit-msg").read_text(encoding="utf-8")
    installer = (ROOT / "scripts/install_git_hooks.sh").read_text(encoding="utf-8")

    assert "run_with_docker_socket.sh" in hook
    assert "scripts/validate_c059.py" in hook
    assert "--commit-message-file /tmp/commit-message" in hook
    assert 'git config core.hooksPath "$repository/.githooks"' in installer


def test_git_reader_preserves_empty_commit_body(monkeypatch: pytest.MonkeyPatch) -> None:
    output = "fix(ci): enforce reusable C-059 metadata contract Constitutional: C-059\x1f\n\x1e\n"
    monkeypatch.setattr(
        "scripts.validate_c059.subprocess.run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 0, output, ""),
    )
    commits = read_commits("base", "head")
    assert commits == [("fix(ci): enforce reusable C-059 metadata contract Constitutional: C-059", "")]
