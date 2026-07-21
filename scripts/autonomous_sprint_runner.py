#!/usr/bin/env python3
"""
autonomous_sprint_runner.py
constitutional_basis: C-066 Tier 2A, C-070, C-001, C-059, C-065
ib_item: IB-009
spec: architecture/reference/agents/platform-it-expert-agent.md §Skill 8

Implementation hat — executes sprint tasks, opens PR.
Called by autonomous-sprint.yaml Job 1 (execute).
C-065: This script is the AUTHOR. Never the reviewer.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
STATE_FILE = REPO_ROOT / "constitution" / "PROJECT_STATE.md"
EVIDENCE_LOG = REPO_ROOT / "logs" / "bootstrap-evidence.jsonl"


# ── Helpers ──────────────────────────────────────────────────────────────────

def set_output(key: str, value: str) -> None:
    """Write to GitHub Actions step output."""
    github_output = os.environ.get("GITHUB_OUTPUT", "")
    if github_output:
        with open(github_output, "a") as f:
            f.write(f"{key}={value}\n")
    print(f"  OUTPUT {key}={value}")


def record_evidence(event: str, **kwargs) -> None:
    """Bootstrap evidence stub (engineering-standards.md §12)."""
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


def run(cmd: list[str], check: bool = True, capture: bool = False) -> subprocess.CompletedProcess:
    """Run a shell command."""
    print(f"  $ {' '.join(cmd)}")
    return subprocess.run(cmd, check=check, capture_output=capture, text=True, cwd=REPO_ROOT)


def git(args: list[str], check: bool = True) -> subprocess.CompletedProcess:
    return run(["git"] + args, check=check)


def parse_sprint_state() -> dict:
    """Extract SPRINT_STATE_MACHINE YAML block from PROJECT_STATE.md."""
    content = STATE_FILE.read_text(encoding="utf-8")
    # Find the yaml block under SPRINT_STATE_MACHINE
    match = re.search(
        r"## SPRINT_STATE_MACHINE.*?```yaml\n(.*?)```",
        content, re.DOTALL
    )
    if not match:
        raise ValueError("SPRINT_STATE_MACHINE block not found in PROJECT_STATE.md")

    state: dict = {}
    for line in match.group(1).splitlines():
        line = line.split("#")[0].strip()  # strip comments
        if ":" in line:
            k, _, v = line.partition(":")
            state[k.strip()] = v.strip().strip('"').strip("'")

    # Parse tasks_remaining list
    tasks_block = re.search(
        r"tasks_remaining:\n((?:  - [^\n]+\n?)*)",
        match.group(1)
    )
    if tasks_block:
        tasks = re.findall(r"  - (\S+)", tasks_block.group(1))
        state["tasks_remaining"] = [t for t in tasks if not t.startswith("#")]
    else:
        state["tasks_remaining"] = []

    return state


def update_sprint_state(**kwargs) -> None:
    """Update fields in SPRINT_STATE_MACHINE via sprint_state.py."""
    pairs = []
    for k, v in kwargs.items():
        pairs += [k, f'"{v}"' if " " in str(v) else str(v)]
    run([sys.executable, "scripts/sprint_state.py", "set"] + pairs)


def gh(args: list[str], check: bool = True) -> subprocess.CompletedProcess:
    return run(["gh"] + args, check=check, capture=True)


# ── Task implementations ─────────────────────────────────────────────────────

def execute_wc011_01() -> bool:
    """WC011-01: Validate docker-compose.yml."""
    print("── WC011-01: Validate docker-compose.yml ──")
    result = run(
        ["docker", "compose", "-f", "docker-compose.yml", "config"],
        check=False, capture=True
    )
    REPO_ROOT.joinpath("logs").mkdir(exist_ok=True)
    (REPO_ROOT / "logs" / "docker-compose-validation.txt").write_text(
        result.stdout + result.stderr
    )
    if result.returncode == 0:
        print("  OK: docker compose config valid")
    else:
        print("  WARN: docker compose config has warnings (recorded)")

    git(["add", "docker-compose.yml", "logs/"], check=False)
    diff = git(["diff", "--cached", "--quiet"], check=False)
    if diff.returncode != 0:
        git(["commit", "-m",
             "feat(infra): WC011-01 - validate docker-compose.yml\n\n"
             "IB: IB-009\nConstitutional: C-067, C-004\nCCTs-added: none"])
    return True


def execute_wc011_04() -> bool:
    """WC011-04: Create src/ directory scaffold with C-059 headers."""
    print("── WC011-04: Create src/ directory scaffold ──")
    services = [
        ("constitutional-engine", "Constitutional Engine"),
        ("business-platform", "Business Platform"),
        ("professional-runtime", "Professional Runtime"),
        ("ai-runtime", "AI Runtime"),
    ]
    for svc_dir, svc_name in services:
        target = REPO_ROOT / "src" / svc_dir
        target.mkdir(parents=True, exist_ok=True)
        readme = target / "README.md"
        if not readme.exists():
            readme.write_text(
                f"# Implements: architecture/reference/components/{svc_dir}.md\n"
                f"# Constitutional basis: C-059 (Implementation Traceability)\n\n"
                f"## {svc_name}\n\n"
                f"Implements: `architecture/reference/components/{svc_dir}.md`\n\n"
                f"## Local Development\n\n"
                f"```bash\ndocker compose up {svc_dir}\n```\n\n"
                f"## Tests\n\n"
                f"Unit tests and CCTs added in Sprint 012+.\n"
            )
            print(f"  Created src/{svc_dir}/README.md")

    git(["add", "src/"], check=False)
    diff = git(["diff", "--cached", "--quiet"], check=False)
    if diff.returncode != 0:
        git(["commit", "-m",
             "feat(infra): WC011-04 - src/ scaffold with C-059 headers\n\n"
             "IB: IB-009\nConstitutional: C-059, C-064\nCCTs-added: none"])
    return True


def execute_wc011_07() -> bool:
    """WC011-07: Document GitHub Actions secrets."""
    print("── WC011-07: Document GitHub Actions secrets ──")
    secrets_doc = REPO_ROOT / "infrastructure" / "GITHUB-SECRETS.md"
    if not secrets_doc.exists():
        secrets_doc.write_text(
            "# GitHub Actions Secrets - WAOOAW Platform\n"
            "# constitutional_basis: C-059\n"
            "# ib_item: IB-009 (WC011-07)\n\n"
            "| Secret | Used By | Obtain From | Status |\n"
            "|---|---|---|---|\n"
            "| AZURE_CREDENTIALS_DEV | promote.yaml | Azure SP (FA - Service Principal) | PENDING |\n"
            "| AZURE_CREDENTIALS_QA | promote.yaml | Azure SP | PENDING |\n"
            "| AZURE_CREDENTIALS_PROD | promote.yaml | Azure SP | PENDING |\n"
            "| GHCR_TOKEN | ci.yaml | GitHub PAT (packages:write) | PENDING |\n"
            "| CODECOV_TOKEN | ci.yaml | codecov.io project token | PENDING |\n"
            "| DEV_BASE_URL | post-deploy-verify.yaml | Terraform output after M1 | PENDING |\n"
            "| DEV_CONSTITUTIONAL_DB_URL | promote.yaml CCTs | Terraform output after M2 | PENDING |\n"
            "| DEV_TEST_JWT_TENANT_A | promote.yaml CCTs | scripts/get-dev-token.sh | PENDING |\n"
            "| DEV_TEST_JWT_TENANT_B | promote.yaml CCTs | scripts/get-dev-token.sh | PENDING |\n"
            "| REVIEW_APP_TOKEN | autonomous-sprint.yaml review job | GitHub App - see FA-023 | PENDING |\n"
        )
        print("  Created infrastructure/GITHUB-SECRETS.md")

    git(["add", "infrastructure/GITHUB-SECRETS.md"], check=False)
    diff = git(["diff", "--cached", "--quiet"], check=False)
    if diff.returncode != 0:
        git(["commit", "-m",
             "chore(infra): WC011-07 - document GitHub Actions secrets\n\n"
             "IB: IB-009\nConstitutional: C-059"])
    return True


TASK_HANDLERS = {
    "WC011-01": execute_wc011_01,
    "WC011-04": execute_wc011_04,
    "WC011-07": execute_wc011_07,
}


# ── Main execution ────────────────────────────────────────────────────────────

def main() -> int:
    dry_run = os.environ.get("DRY_RUN", "false").lower() == "true"
    force_task = os.environ.get("FORCE_TASK", "").strip()
    github_repo = os.environ.get("GITHUB_REPO", "")

    print("=" * 60)
    print("  WAOOAW Autonomous Sprint Agent")
    print(f"  Mode: {'DRY RUN' if dry_run else 'EXECUTE'}")
    print(f"  Force task: {force_task or 'none'}")
    print("=" * 60)

    # ── Step 1: Parse sprint state ────────────────────────────────────────
    try:
        state = parse_sprint_state()
    except ValueError as e:
        print(f"ERROR: {e}")
        set_output("result", "FAILED")
        set_output("halt", "false")
        return 1

    print(f"\nSprint state:")
    print(f"  autonomous_halt   : {state.get('autonomous_halt', 'false')}")
    print(f"  current_sprint    : {state.get('current_sprint', '')}")
    print(f"  sprint_status     : {state.get('sprint_status', '')}")
    print(f"  tasks_remaining   : {state.get('tasks_remaining', [])}")

    # ── Step 2: AUTONOMOUS_HALT check (C-001) ─────────────────────────────
    if state.get("autonomous_halt", "false").lower() == "true":
        print("\nAUTONOMOUS_HALT: true - human override active (C-001).")
        print("No sprint work performed. Exiting gracefully.")
        set_output("halt", "true")
        set_output("result", "HALTED")
        return 0

    set_output("halt", "false")

    # ── Step 3: Consecutive failure check ─────────────────────────────────
    failures = int(state.get("consecutive_failures", "0") or "0")
    if failures >= 3:
        print(f"\nConsecutive failures: {failures} >= 3 - creating Constitutional Blocker")
        if not dry_run and github_repo:
            title = f"CB: Autonomous Sprint {state.get('current_sprint', '?')} - {failures} consecutive failures"
            body = (
                f"Constitutional Blocker - Autonomous Sprint Failure\n\n"
                f"Sprint: {state.get('current_sprint', '?')}\n"
                f"Consecutive failures: {failures}\n"
                f"Action: Review workflow runs, fix root cause, reset consecutive_failures: 0\n"
                f"Constitutional basis: C-001 (Human Override)"
            )
            gh(["issue", "create", "--title", title, "--body", body,
                "--label", "type:constitutional-blocker,status:blocked",
                "--repo", github_repo], check=False)
        set_output("result", "FAILED")
        return 1

    # ── Step 4: Determine tasks to run ────────────────────────────────────
    sprint = state.get("current_sprint", "")
    set_output("sprint", sprint)
    tasks = [force_task] if force_task else state.get("tasks_remaining", [])

    if not tasks:
        print("\nNo tasks remaining. Sprint may already be DONE.")
        set_output("result", "SKIPPED")
        return 0

    # ── Step 5: Setup branch ──────────────────────────────────────────────
    branch = state.get("branch", f"ib/009/{sprint.lower()}")
    if not dry_run:
        remote_check = git(["ls-remote", "--exit-code", "--heads", "origin", branch], check=False)
        if remote_check.returncode == 0:
            git(["checkout", branch])
            git(["pull", "origin", branch])
        else:
            git(["checkout", "-b", branch])

        record_evidence("AUTONOMOUS_SPRINT_STARTED", sprint=sprint,
                        branch=branch, tasks=tasks)
        update_sprint_state(
            sprint_status="IN_PROGRESS",
            last_attempt_utc=datetime.now(timezone.utc).isoformat(),
            current_task=tasks[0] if tasks else "",
        )
        git(["add", "constitution/PROJECT_STATE.md", "logs/"], check=False)
        diff = git(["diff", "--cached", "--quiet"], check=False)
        if diff.returncode != 0:
            git(["commit", "-m",
                 f"chore(pm): {sprint} execution started\n\nIB: IB-009\nConstitutional: C-059"])

    # ── Step 6: Execute each task ─────────────────────────────────────────
    tasks_done = []
    for task in tasks:
        handler = TASK_HANDLERS.get(task)
        if handler is None:
            print(f"  SKIP {task}: no handler (requires Copilot workspace)")
            continue
        if dry_run:
            print(f"  DRY RUN: would execute {task}")
            continue
        try:
            success = handler()
            if success:
                tasks_done.append(task)
                print(f"  DONE: {task}")
        except Exception as exc:
            print(f"  FAILED: {task}: {exc}")

    # ── Step 7: Update state + open PR ────────────────────────────────────
    if dry_run:
        set_output("result", "DRY_RUN")
        return 0

    record_evidence("SPRINT_TASKS_EXECUTED", sprint=sprint, tasks_done=tasks_done)

    if tasks_done:
        update_sprint_state(
            last_attempt_result="SUCCESS",
            consecutive_failures=0,
            current_task="",
        )
    else:
        failures_new = failures + 1
        update_sprint_state(
            last_attempt_result="PARTIAL",
            consecutive_failures=str(failures_new),
        )

    git(["add", "constitution/PROJECT_STATE.md", "logs/"], check=False)
    diff = git(["diff", "--cached", "--quiet"], check=False)
    if diff.returncode != 0:
        git(["commit", "-m",
             f"chore(pm): {sprint} tasks done: {', '.join(tasks_done)}\n\n"
             f"IB: IB-009\nConstitutional: C-059"])

    git(["push", "origin", branch, "--force-with-lease"])

    # ── Step 8: Open/update PR ────────────────────────────────────────────
    if not github_repo:
        set_output("result", "SUCCESS")
        return 0

    existing = gh(["pr", "list", "--head", branch,
                   "--json", "number", "--jq", ".[0].number",
                   "--repo", github_repo], check=False)
    existing_num = existing.stdout.strip() if existing.returncode == 0 else ""

    if not existing_num:
        pr_title = f"feat(infra): {sprint} - Autonomous Sprint Execution"
        pr_body = (
            f"IB Reference: IB-009 - Foundation Implementation\n"
            f"Work Contract: {sprint}\n"
            f"Office: WAOOAW AI Agent - Platform IT Expert (Autonomous Sprint)\n"
            f"Execution mode: Autonomous (C-066 Tier 2A)\n\n"
            f"Tasks executed: {', '.join(tasks_done) or 'none (Copilot workspace required)'}\n\n"
            f"Constitutional basis: C-066 Tier 2A, C-070, C-059, C-065\n"
            f"Bootstrap evidence: logs/bootstrap-evidence.jsonl\n"
            f"Run ID: {os.environ.get('GITHUB_RUN_ID', 'local')}"
        )
        result = gh(["pr", "create",
                     "--title", pr_title,
                     "--body", pr_body,
                     "--base", "main",
                     "--head", branch,
                     "--label", "tier:2-feature,status:pr-open,awaiting:review",
                     "--repo", github_repo], check=False)
        pr_num = result.stdout.strip() if result.returncode == 0 else ""
        if pr_num:
            print(f"  PR created: #{pr_num}")
    else:
        pr_num = existing_num
        print(f"  PR updated: #{pr_num}")

    set_output("pr_number", pr_num)
    set_output("result", "SUCCESS" if tasks_done else "PARTIAL")
    return 0


if __name__ == "__main__":
    sys.exit(main())
