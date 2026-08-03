# Implements: scripts/runner/git_ops.py
# constitutional_basis: C-059 (Traceability — evidence logging), C-065 (SDLC Separation)
# ib_item: IB-009
"""
Shell command helpers: run(), git(), gh(), set_output(), record_evidence().

All subprocess calls in the runner go through run() so there is a single
chokepoint for cwd=REPO_ROOT enforcement and observability.
"""
from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timezone

from runner.constants import REPO_ROOT, EVIDENCE_LOG


def set_output(key: str, value: str) -> None:
    """Write a key=value pair to the GitHub Actions step output file."""
    github_output = os.environ.get("GITHUB_OUTPUT", "")
    if github_output:
        with open(github_output, "a") as f:
            f.write(f"{key}={value}\n")
    print(f"  OUTPUT {key}={value}")


def record_evidence(event: str, **kwargs) -> None:
    """Append a JSON evidence record to the bootstrap evidence log (C-059)."""
    EVIDENCE_LOG.parent.mkdir(exist_ok=True)
    record = {
        "event": event,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "run_id": os.environ.get("GITHUB_RUN_ID", "local"),
        "stub_mode": True,
        **kwargs,
    }
    with EVIDENCE_LOG.open("a") as f:
        f.write(json.dumps(record) + "\n")


def run(
    cmd: list[str],
    check: bool = True,
    capture: bool = False,
) -> subprocess.CompletedProcess:
    """Run a shell command with cwd=REPO_ROOT. Prints the command before running."""
    print(f"  $ {' '.join(cmd)}")
    return subprocess.run(
        cmd,
        check=check,
        capture_output=capture,
        text=True,
        cwd=REPO_ROOT,
    )


def git(args: list[str], check: bool = True) -> subprocess.CompletedProcess:
    """Thin wrapper: run git with given args."""
    # Local .git/config has commit.gpgsign=true (codespace). Override for container runs.
    in_container = os.environ.get("AUTONOMOUS_SPRINT_AGENT") == "true"
    prefix = ["-c", "commit.gpgsign=false"] if in_container and args and args[0] in ("commit", "merge") else []
    return run(["git"] + prefix + args, check=check)


def gh(args: list[str], check: bool = True) -> subprocess.CompletedProcess:
    """Thin wrapper: run gh CLI and capture output."""
    return run(["gh"] + args, check=check, capture=True)
