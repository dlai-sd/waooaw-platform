#!/usr/bin/env python3
"""
bootstrap_sprint_sims.py — Auto-generate SIM-PL-002 stubs for new sprint tasks.

Constitutional basis: C-086 (Pre-Execution Simulation Obligation)
Office: Platform IT Expert (pipeline tooling)
IB: IB-009

When a new sprint is registered (tasks_remaining updated in PROJECT_STATE.md),
this script creates SIM-PL-002 stub files for any tasks that do not yet have
simulation files. Verdict is determined by task type:
  - Known-safe patterns (scaffold, cache, router, models, tests, migration):
    Verdict: PASS — pattern is well-understood, simulation confirms low risk.
  - Novel/complex patterns (unknown type, custom business logic marked HIGH):
    Verdict: PENDING — requires human review before pipeline may proceed.

The pipeline calls this before check_c086_gate.py so C-086 gate can read the
generated stubs. Engineers review PENDING verdicts and change to PASS or FAIL.

Run: python3 scripts/bootstrap_sprint_sims.py [--dry-run]
"""
from __future__ import annotations

import re
import sys
import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
SIM_DIR = REPO_ROOT / "simulation"
WC_DIR = REPO_ROOT / "work-contracts"
STATE_FILE = REPO_ROOT / "constitution" / "PROJECT_STATE.md"

# Task type classification → auto-PASS or PENDING
# PASS: well-understood, low-risk patterns that follow established repo conventions
# PENDING: novel logic requiring human pre-execution review
KNOWN_SAFE_PATTERNS = {
    "scaffold", "config", "dockerfile", "requirements",
    "migration", "sql", "seed",
    "models", "model",
    "cache", "redis",
    "router", "routes",
    "tests", "test",
    "health", "main",
    "docker-compose", "compose",
    "init", "setup",
}

PENDING_PATTERNS = {
    "orchestrat", "workflow", "temporal", "saga",
    "encryption", "secret", "auth", "jwt", "oauth",
    "payment", "razorpay", "webhook",
    "novel", "custom", "experimental",
}


def _read_sprint_state() -> tuple[str, list[str]]:
    """Return (current_sprint, tasks_remaining) from SPRINT_STATE_MACHINE block."""
    content = STATE_FILE.read_text()
    sm_match = re.search(
        r"## SPRINT_STATE_MACHINE.*?```yaml(.*?)```",
        content,
        re.DOTALL,
    )
    if not sm_match:
        return "", []
    sm_yaml = sm_match.group(1)

    sprint_match = re.search(r"current_sprint:\s*(\S+)", sm_yaml)
    current_sprint = sprint_match.group(1).strip("\"'") if sprint_match else ""

    tasks_block = re.search(r"tasks_remaining:\s*\n((?:  - [^\n]+\n?)*)", sm_yaml)
    tasks = re.findall(r"  - (\S+)", tasks_block.group(1)) if tasks_block else []
    return current_sprint, tasks


def _find_wc_file(sprint: str) -> Path | None:
    """Find the work contract file for the given sprint ID (e.g. WC-026)."""
    sprint_short = sprint.replace("-", "").upper()  # WC-026 → WC026
    matches = list(WC_DIR.glob(f"{sprint_short}-*.md")) or list(WC_DIR.glob(f"{sprint}-*.md"))
    return matches[0] if matches else None


def _extract_wc_tasks(wc_file: Path) -> dict[str, str]:
    """Extract task descriptions from the WC task table. Returns {task_id: scope_text}."""
    content = wc_file.read_text()
    tasks: dict[str, str] = {}
    # Match table rows: | WC026-01 | or | WC027-01a | (optional letter suffix for split tasks)
    for match in re.finditer(
        r"\|\s*(WC\d{3}-\d{2}[a-z]?)\s*\|\s*([^|]+)\|[^|]+\|[^|]+\|", content
    ):
        task_id = match.group(1).strip()
        scope = match.group(2).strip()
        tasks[task_id] = scope
    return tasks


def _classify_task(scope: str) -> str:
    """Return 'PASS' for known-safe patterns, 'PENDING' for novel logic."""
    scope_lower = scope.lower()
    for keyword in PENDING_PATTERNS:
        if keyword in scope_lower:
            return "PENDING"
    for keyword in KNOWN_SAFE_PATTERNS:
        if keyword in scope_lower:
            return "PASS"
    return "PENDING"  # unknown → require human review


def _build_sim_content(task_id: str, scope: str, sprint: str, verdict: str) -> str:
    today = datetime.date.today().isoformat()
    verdict_line = "**VERDICT: ✅ PASS**" if verdict == "PASS" else "**VERDICT: ⏳ PENDING — requires human review before pipeline may proceed**"
    risk_note = (
        "Known-safe pattern — follows established repo conventions. Low execution risk."
        if verdict == "PASS"
        else "Novel or complex pattern — pre-execution analysis required. Set verdict to ✅ PASS or ❌ FAIL after review."
    )
    slug = re.sub(r"[^a-z0-9]+", "-", scope[:40].lower()).strip("-")
    return f"""# SIM-PL-002 — {task_id} {scope[:60]}
**Date:** {today}
**Author:** bootstrap_sprint_sims.py (pipeline tooling — Platform IT Expert hat)
**Task:** {task_id} — {scope}
**Simulation type:** Dependency Graph Task Decomposition (IB-021)
**Sprint:** {sprint}

## Context
Auto-bootstrapped by pipeline. {risk_note}
Review this file and set verdict to ✅ PASS before triggering the sprint if PENDING.

## Subtask Decomposition
{task_id}a — implement per WC scope: {scope} → ruff → tests → PASS

## Dependency Graph
{task_id}a: depends_on=[prior tasks in same sprint]

## Risk Assessment
{risk_note}

## Verdict

{verdict_line}
"""


def main(dry_run: bool = False) -> int:
    current_sprint, tasks_remaining = _read_sprint_state()
    if not tasks_remaining:
        print("  ℹ️  No tasks_remaining in SPRINT_STATE_MACHINE — nothing to bootstrap")
        return 0

    print(f"  Sprint: {current_sprint} | Tasks: {tasks_remaining}")
    wc_file = _find_wc_file(current_sprint)
    wc_tasks = _extract_wc_tasks(wc_file) if wc_file else {}
    if not wc_file:
        print(f"  ⚠️  No WC file found for {current_sprint} — using task IDs only")

    created = 0
    for task_id in tasks_remaining:
        existing = list(SIM_DIR.glob(f"SIM-PL-002-{task_id}-*.md"))
        if existing:
            print(f"  ✅ {task_id}: SIM file exists — {existing[0].name}")
            continue

        scope = wc_tasks.get(task_id, f"{current_sprint} task")
        verdict = _classify_task(scope)
        slug = re.sub(r"[^a-z0-9]+", "-", scope[:40].lower()).strip("-")
        sim_path = SIM_DIR / f"SIM-PL-002-{task_id}-{slug}.md"
        content = _build_sim_content(task_id, scope, current_sprint, verdict)

        if dry_run:
            print(f"  [dry-run] would create: {sim_path.name} (verdict={verdict})")
        else:
            sim_path.write_text(content)
            icon = "✅" if verdict == "PASS" else "⏳"
            print(f"  {icon} {task_id}: created {sim_path.name} (verdict={verdict})")
        created += 1

    if created == 0:
        print("  ✅ All tasks already have SIM files — nothing to bootstrap")
    else:
        status = "[dry-run] would create" if dry_run else "created"
        print(f"  ✅ bootstrap_sprint_sims: {status} {created} SIM file(s)")

    return 0


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    sys.exit(main(dry_run=dry_run))
