"""WC-168 R011: the deployment waits for the previous Temporal copy to drain instead of racing its scale-down.

Fault injection runs the real script with a stub Azure CLI: drained after a few polls, never drained, and an Azure
failure that must never be read as "drained". The workflow test pins that the wait comes before the startup job runs.
"""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/wait_for_replicas_drained.sh"
WORKFLOW = ROOT / ".github/workflows/environment-deployment.yaml"

STUB_AZ = """#!/usr/bin/env bash
count_file="$STUB_DIR/count"
calls=$(cat "$STUB_DIR/calls" 2>/dev/null || echo 0)
echo $((calls + 1)) > "$STUB_DIR/calls"
case "$STUB_MODE" in
  fail) echo "az failed" >&2; exit 3 ;;
  garbage) echo "not-a-number"; exit 0 ;;
  never) echo 1 ;;
  drain) if [ "$calls" -ge 2 ]; then echo 0; else echo 1; fi ;;
esac
"""


def _run(tmp_path: Path, mode: str, max_seconds: int = 3) -> subprocess.CompletedProcess[str]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    az = bin_dir / "az"
    az.write_text(STUB_AZ, encoding="utf-8")
    az.chmod(0o755)
    env = {**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}", "STUB_DIR": str(tmp_path), "STUB_MODE": mode}
    return subprocess.run(
        ["bash", str(SCRIPT), "ca-demo-temporal", "rg", str(max_seconds), "1"],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_a_copy_that_scales_down_during_the_wait_lets_the_qualification_start(tmp_path: Path) -> None:
    done = _run(tmp_path, "drain", max_seconds=30)
    assert done.returncode == 0, done.stderr
    assert "has no running replica" in done.stdout


def test_a_copy_that_never_drains_is_refused_after_the_limit(tmp_path: Path) -> None:
    done = _run(tmp_path, "never", max_seconds=2)
    assert done.returncode == 1
    assert "refusing to start the startup qualification" in done.stderr


def test_an_azure_failure_or_unreadable_count_is_never_treated_as_drained(tmp_path: Path) -> None:
    failed = _run(tmp_path, "fail")
    assert failed.returncode != 0 and "has no running replica" not in failed.stdout
    other = tmp_path / "other"
    other.mkdir()
    garbage = _run(other, "garbage")
    assert garbage.returncode == 1 and "Could not read the replica count" in garbage.stderr


def test_the_workflow_waits_for_the_drain_before_it_starts_the_temporal_startup_job() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    step = workflow.split("- name: Qualify exact Temporal startup through PgBouncer", 1)[1]
    wait = step.index('scripts/wait_for_replicas_drained.sh "ca-${TARGET_ENVIRONMENT}-temporal"')
    start = step.index("az containerapp job start")
    assert wait < start


def test_a_deploy_that_keeps_the_database_stops_running_demo_before_the_temporal_gate() -> None:
    steps = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))["jobs"]["terraform"]["steps"]
    names = [step.get("name") for step in steps]
    quiesce = steps[names.index("Quiesce running Demo applications before migrations")]
    reset_only = steps[names.index("Quiesce Demo consumers before database reset")]
    # Exactly one of the two stops runs, so a running Demo can never reach the gate with Temporal still up.
    assert "outputs.reuse == 'true'" in quiesce["if"] and "outputs.reuse != 'true'" in reset_only["if"]
    assert "inputs.environment == 'demo'" in quiesce["if"] and "inputs.apply" in quiesce["if"]
    assert "--action Stop --component database-reset" in quiesce["run"]
    assert names.index("Quiesce running Demo applications before migrations") < names.index(
        "Resume PgBouncer before migration preflight"
    ) < names.index("Qualify exact Temporal startup through PgBouncer")



def test_every_retained_evidence_path_is_on_its_own_line() -> None:
    steps = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))["jobs"]["terraform"]["steps"]
    upload = next(step for step in steps if step.get("name") == "Upload plans and evidence")
    # A line holding two names is one pattern that matches nothing, so neither file would be retained.
    joined = [line for line in upload["with"]["path"].splitlines() if len(re.sub(r"\$\{\{.*?\}\}", "", line).split()) > 1]
    assert joined == []
    assert "wc143-database-chain-reuse.json" in upload["with"]["path"].split()
    assert "wc124-connection-budget.json" in upload["with"]["path"].split()
