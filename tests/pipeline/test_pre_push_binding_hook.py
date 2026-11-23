import os
import stat
import subprocess
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
HOOK = ROOT / ".githooks" / "pre-push"
HEAD = "a" * 40
OTHER = "b" * 40
ZERO = "0" * 40


def run_hook(tmp_path: Path, stdin: str, listing: str | None, gh_exit: int = 0) -> subprocess.CompletedProcess[str]:
    # A stub gh stands in for the GitHub CLI: it prints the template output a real `gh pr list` would.
    stub = tmp_path / "gh"
    stub.write_text(f'#!/bin/sh\n[ {gh_exit} -eq 0 ] || exit {gh_exit}\nprintf %s "$STUB_LISTING"\n', encoding="utf-8")
    stub.chmod(stub.stat().st_mode | stat.S_IXUSR)
    environment = {"PATH": f"{tmp_path}:{os.environ['PATH']}", "STUB_LISTING": listing or ""}
    return subprocess.run(
        ["sh", str(HOOK)],
        input=stdin,
        capture_output=True,
        text=True,
        env=environment,
        check=False,
    )


def push_line(branch: str = "ib/1/example", sha: str = HEAD) -> str:
    return f"refs/heads/{branch} {sha} refs/heads/{branch} {ZERO}\n"


def test_push_is_allowed_when_the_open_pr_body_is_bound_to_the_pushed_head(tmp_path: Path) -> None:
    listing = f"622 ## Summary\n\n**Reviewed Commit:** {HEAD}\n**Author Review Result:** PASS\n"

    assert run_hook(tmp_path, push_line(), listing).returncode == 0


def test_push_is_refused_with_the_exact_binding_command_when_the_body_names_another_head(tmp_path: Path) -> None:
    listing = f"622 ## Summary\n\n**Reviewed Commit:** {OTHER}\n"

    result = run_hook(tmp_path, push_line(), listing)

    assert result.returncode == 1
    assert "PR #622 is not bound" in result.stderr
    assert "scripts/prepare_pr_body.sh" in result.stderr
    assert "--allow-unpushed-head --update-pr 622" in result.stderr


def test_push_is_refused_when_the_body_has_no_reviewed_commit(tmp_path: Path) -> None:
    assert run_hook(tmp_path, push_line(), "622 no evidence yet\n").returncode == 1


def test_push_without_an_open_pr_deletes_and_other_refs_and_gh_failures_are_not_blocked(tmp_path: Path) -> None:
    assert run_hook(tmp_path, push_line(), "").returncode == 0
    assert run_hook(tmp_path, push_line(sha=ZERO), f"622 **Reviewed Commit:** {OTHER}").returncode == 0
    assert run_hook(tmp_path, f"refs/tags/v1 {HEAD} refs/tags/v1 {ZERO}\n", f"622 **Reviewed Commit:** {OTHER}").returncode == 0
    failed = run_hook(tmp_path, push_line(), None, gh_exit=1)
    assert failed.returncode == 0
    assert "could not read the open PR" in failed.stderr


def test_the_binding_hook_is_executable_and_pinned_by_process_control() -> None:
    # Drift guard: removing or unpinning the hook changes process-control and fails this test.
    assert HOOK.stat().st_mode & stat.S_IXUSR
    manifest = yaml.safe_load((ROOT / "validation" / "process-control.yaml").read_text(encoding="utf-8"))
    handoff = manifest["required_controls"]["exact_head_handoff"]["sources"]
    assert ".githooks/pre-push" in handoff
    assert "tests/pipeline/test_pre_push_binding_hook.py" in handoff
    assert ".githooks/pre-push" in manifest["source_digests"]
