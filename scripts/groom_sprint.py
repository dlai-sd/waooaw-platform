#!/usr/bin/env python3
"""
groom_sprint.py — Sprint Sub-Task Groomer

# Implements: standards/AUTONOMOUS-PIPELINE-STANDARD.md §Grooming
# Constitutional basis:
#   C-059 (Traceability — every SubTaskDef.wc_task_id links to authoritative PMO spec)
#   C-066 Tier 2A (Autonomous Execution — groomer runs in preflight without human approval)
#   C-070 Third Instinct (Autonomous execution is the primary production path)
#   C-077 (FinOps — Haiku for code generation, never Frontier model)
#   ADR-036 (Blueprint-First — skeleton defines exact method names; LLM implements, never invents)
# office: Platform IT Expert (INST-010)
# spec: standards/AUTONOMOUS-PIPELINE-STANDARD.md §Grooming
# ib_item: IB-022

Blueprint-First Grooming Flow (ADR-036):

  WC file (task table: task_id, scope, model_hint)
    +  EA skeleton (src/{service}/skeleton/*.py — exact interface contracts)
    → Haiku LLM (maps scope → skeleton interfaces → SubTaskDef Python struct)
    → ast.parse validation (syntax gate)
    → inject into TASK_HANDLERS (autonomous_sprint_runner.py)
    → inject into SPRINT_TASK_MANIFEST (sprint_state.py)
    → ruff check (lint gate)
    → commit to main (PIPELINE SYNC picks up in execute job)

Design principle: Without skeleton grounding, the LLM invents class names and method
signatures (the error class ADR-036 was written to eliminate). With skeleton, SubTaskDef
generation is deterministic: skeleton provides exact types, signatures, and constitutional
anchors. Haiku does scope→interface mapping only.

Usage:
  python3 scripts/groom_sprint.py [--sprint WC-027] [--dry-run]
  Called from autonomous-sprint.yaml preflight job (after halt_check, before index_build).
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
RUNNER_PATH = REPO_ROOT / "scripts" / "autonomous_sprint_runner.py"
STATE_PATH  = REPO_ROOT / "scripts" / "sprint_state.py"
PROJECT_STATE = REPO_ROOT / "constitution" / "PROJECT_STATE.md"

# Injection anchors (must match strings added by this session)
RUNNER_ANCHOR  = "# ── GROOMER INJECTION POINT — groom_sprint.py injects new sprint handlers here ──"
MANIFEST_ANCHOR = "# ── GROOMER MANIFEST INJECTION POINT — groom_sprint.py injects new sprint manifest here ──"

# Maps sprint WC prefix → service skeleton directory
_SKELETON_MAP: dict[str, str] = {
    "WC025": "src/billing-engine/skeleton",
    "WC026": "src/billing-engine/skeleton",
    "WC027": "src/billing-engine/skeleton",
    "WC028": "src/billing-engine/skeleton",
    "WC029": "src/billing-engine/skeleton",
}

# Maps sprint WC prefix → (stack, service_dir)
_SERVICE_MAP: dict[str, tuple[str, str]] = {
    "WC025": ("python", "src/billing-engine"),
    "WC026": ("python", "src/billing-engine"),
    "WC027": ("python", "src/billing-engine"),
    "WC028": ("python", "src/billing-engine"),
    "WC029": ("python", "src/billing-engine"),
}


# ── Sprint resolution ──────────────────────────────────────────────────────────

def _read_current_sprint() -> str:
    """Read current_sprint from PROJECT_STATE.md SPRINT_STATE_MACHINE."""
    text = PROJECT_STATE.read_text()
    idx = text.find("## SPRINT_STATE_MACHINE")
    sm = text[idx:] if idx >= 0 else text
    m = re.search(r"current_sprint:\s*(\S+)", sm)
    return m.group(1).strip("'\"") if m else ""


# ── WC table parsing ───────────────────────────────────────────────────────────

def _find_wc_file(sprint_key: str) -> Path | None:
    """Find work-contracts/WC-NNN-*.md for the given sprint key (e.g. 'WC-027')."""
    digits = sprint_key.lstrip("WCwc-").lstrip("0") or "0"
    padded = digits.zfill(3)
    matches = list((REPO_ROOT / "work-contracts").glob(f"WC-{padded}-*.md"))
    return matches[0] if matches else None


def _parse_wc_tasks(wc_file: Path, sprint_prefix: str) -> list[dict]:
    """
    Parse WC tasks from the work contract file.
    Supports two formats:
      1. Markdown table rows: | WC027-01 | scope | model_hint | status |
      2. ### WC027-01 — Title headers with **Scope:**, **model_hint:** fields
    Returns list of dicts with: task_id, scope, model_hint, title
    """
    text = wc_file.read_text()
    tasks: list[dict] = []

    # Format 1: table rows
    table_row = re.compile(
        r"\|\s*(" + re.escape(sprint_prefix) + r"-\d{2})\s*\|"
        r"\s*([^|]+)\s*\|\s*(`?)(reasoning|auto|none)`?\s*\|"
    )
    for m in table_row.finditer(text):
        tasks.append({
            "task_id": m.group(1).strip(),
            "scope":      m.group(2).strip(),
            "model_hint": m.group(4).strip(),
            "title":      m.group(2).strip()[:80],
        })

    if tasks:
        return tasks

    # Format 2: ### WCxxx-NN — Title headers
    blocks = re.split(r"(?=###\s+" + re.escape(sprint_prefix) + r"-\d{2})", text)
    for block in blocks:
        m = re.match(r"###\s+(" + re.escape(sprint_prefix) + r"-\d{2})\s*[—-]?\s*(.+)", block)
        if not m:
            continue
        task_id = m.group(1)
        title   = m.group(2).strip()

        def _field(name: str) -> str:
            fm = re.search(r"\*\*" + re.escape(name) + r":\*\*\s*(.*?)(?=\n\*\*|\Z)", block, re.DOTALL)
            v = fm.group(1).strip() if fm else ""
            return re.sub(r"^`([^`]+)`$", r"\1", v)

        tasks.append({
            "task_id":    task_id,
            "scope":      _field("Scope") or title,
            "model_hint": _field("model_hint") or "auto",
            "title":      title,
        })

    return tasks


# ── Already-groomed detection ──────────────────────────────────────────────────

def _already_groomed(task_id: str) -> bool:
    """Return True if task_id already has an entry in TASK_HANDLERS."""
    content = RUNNER_PATH.read_text()
    return f'"{task_id}"' in content or f"'{task_id}'" in content


# ── Skeleton reading ───────────────────────────────────────────────────────────

def _read_skeleton(sprint_prefix: str) -> str:
    """Read all skeleton/*.py files for the service and return concatenated content."""
    skel_dir_rel = _SKELETON_MAP.get(sprint_prefix)
    if not skel_dir_rel:
        return ""
    skel_dir = REPO_ROOT / skel_dir_rel
    if not skel_dir.exists():
        return ""
    parts = []
    for f in sorted(skel_dir.glob("*.py")):
        parts.append(f"# === {f.name} ===\n" + f.read_text())
    return "\n".join(parts)


# ── LLM SubTaskDef generation ──────────────────────────────────────────────────

_SUBTASKDEF_TEMPLATE = '''
SubTaskDef(
    id="{subtask_id}",
    description="<one sentence: what this task implements>",
    type="llm",
    depends_on=[{depends_on}],
    compile_gate="ruff",
    service_dir="{service_dir}",
    wc_task_id="{task_id}",
    stack="{stack}",
    output_files=[
        {output_files}
    ],
    inject_source_files=[
        {inject_files}
    ],
    {not_regen_line}
    spec_sections={{
        "work-contracts/{wc_file_name}": "{task_id}",
    }},
    constitutional_check=(
        "<derived from skeleton: exact interface to implement, constitutional claims, SLA constraints>"
    ),
    model_hint="{model_hint}",
    max_tokens={max_tokens},
)
'''.strip()

_SYSTEM_PROMPT = """You are a Python code generator for the WAOOAW autonomous sprint pipeline.
You produce SubTaskDef struct literals that tell the autonomous runner what to implement.

CRITICAL RULES (ADR-036 Blueprint-First):
1. output_files MUST be derived from the scope text — choose existing service module structure
2. constitutional_check MUST reference skeleton interface method names EXACTLY as written
3. constitutional_check MUST include "DO NOT change signatures — implement only, no invention"
4. inject_source_files MUST include the skeleton file path for skeleton-backed tasks
5. model_hint MUST be exactly as specified in the WC table (reasoning/auto — never 'standard')
6. max_tokens: 8000 for reasoning tasks, 3000–5000 for auto tasks
7. depends_on: use the prior_subtask_id exactly as given, or [] for the first task
8. Output ONLY the SubTaskDef(...) literal — no imports, no assignments, no explanation
"""

def _generate_subtaskdef(
    task: dict,
    skeleton: str,
    prior_subtask_id: str | None,
    sprint_prefix: str,
    wc_filename: str,
    api_key: str,
) -> str | None:
    """
    Use Claude Haiku to generate a SubTaskDef Python literal grounded in the skeleton.
    Cost: ~$0.002 per call. Returns the SubTaskDef(...) string or None on failure.
    """
    import urllib.request

    stack, service_dir = _SERVICE_MAP.get(sprint_prefix, ("python", "src/billing-engine"))
    task_id = task["task_id"]
    subtask_id = task_id.lower().replace("-", "") + "a"  # e.g. WC027-01 → wc02701a... fix below
    # Proper format: WC027-01 → WC027-01a
    subtask_id = task_id + "a"
    depends_on_str = f'"{prior_subtask_id}"' if prior_subtask_id else ""
    model_hint = task.get("model_hint", "auto")
    if model_hint not in ("reasoning", "auto", "none"):
        model_hint = "auto"
    max_tokens = 8000 if model_hint == "reasoning" else 4000

    user_msg = f"""Generate a SubTaskDef literal for this WC task.

Task ID: {task_id}
Scope: {task['scope']}
model_hint: {model_hint}
Stack: {stack}
Service dir: {service_dir}
Prior subtask id (for depends_on): {prior_subtask_id or 'none — this is the first task'}
WC file name: {wc_filename}

EA SKELETON (the blueprint — method signatures are FROZEN):
{skeleton[:6000]}

Output format (fill ALL placeholders):
    "{task_id}": {{
        "subtasks": [
            SubTaskDef(
                id="{task_id}a",
                description="<one sentence>",
                type="llm",
                depends_on=[{depends_on_str}],
                compile_gate="ruff",
                service_dir="{service_dir}",
                wc_task_id="{task_id}",
                stack="{stack}",
                output_files=[
                    "<derive from scope — e.g. src/billing-engine/wallet/service.py>",
                ],
                inject_source_files=[
                    "{service_dir}/skeleton/wbe_interfaces.py",
                    "<other relevant existing files>",
                ],
                spec_sections={{
                    "work-contracts/{wc_filename}": "{task_id}",
                }},
                constitutional_check=(
                    "<skeleton interface to implement + DO NOT change signatures + C-xxx claims from skeleton annotations>"
                ),
                model_hint="{model_hint}",
                max_tokens={max_tokens},
            ),
        ]
    }},

Rules:
- output_files must be real Python module paths under {service_dir}/
- inject_source_files must start with the skeleton file above, then any prior-task output files
- constitutional_check must name the exact ABC class from skeleton that this task implements
- DO NOT include imports or module-level assignments — only the dict entry literal
"""

    body = json.dumps({
        "model": "claude-haiku-4-5",
        "max_tokens": 2048,
        "system": _SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": user_msg}],
    }).encode()

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=body,
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read())
        return data["content"][0]["text"].strip()
    except Exception as exc:
        print(f"  ⚠️  LLM call failed: {exc}")
        return None


# ── Validation ────────────────────────────────────────────────────────────────

def _validate_generated_entry(code: str, task_id: str) -> bool:
    """
    Validate the generated TASK_HANDLERS entry.
    1. Must contain the task_id as a dict key
    2. Must contain 'SubTaskDef(' literal
    3. Must be parseable as Python (wrapped in a minimal module context)
    """
    if f'"{task_id}"' not in code and f"'{task_id}'" not in code:
        print(f"  ❌ Validation: missing task_id key '{task_id}' in generated code")
        return False
    if "SubTaskDef(" not in code:
        print(f"  ❌ Validation: no SubTaskDef( in generated code")
        return False
    # Wrap in parseable context for ast.parse
    wrapper = f"""
from dataclasses import dataclass
from typing import Optional
@dataclass
class SubTaskDef:
    id: str = ""
    description: str = ""
    type: str = "llm"
    depends_on: list = None
    compile_gate: str = "ruff"
    service_dir: str = ""
    wc_task_id: str = ""
    stack: str = "python"
    output_files: list = None
    inject_source_files: list = None
    not_regenerate_from: list = None
    spec_sections: dict = None
    constitutional_check: str = ""
    model_hint: str = "auto"
    max_tokens: int = 4000

_entry = {{
{code}
}}
"""
    try:
        ast.parse(wrapper)
        return True
    except SyntaxError as e:
        print(f"  ❌ Syntax error in generated code: {e}")
        return False


# ── Injection ─────────────────────────────────────────────────────────────────

def _inject_task_handler(code: str) -> bool:
    """Inject the generated TASK_HANDLERS entry before the GROOMER INJECTION POINT anchor."""
    content = RUNNER_PATH.read_text()
    if RUNNER_ANCHOR not in content:
        print(f"  ❌ Injection anchor not found in {RUNNER_PATH.name}")
        return False
    # Indent the entry: it goes inside the TASK_HANDLERS dict (4-space indent)
    indented = "\n".join("    " + line if line.strip() else line for line in code.splitlines())
    new_content = content.replace(
        f"    {RUNNER_ANCHOR}",
        f"    {indented}\n    {RUNNER_ANCHOR}",
    )
    RUNNER_PATH.write_text(new_content)
    return True


def _inject_manifest_entry(sprint_key: str, task_ids: list[str]) -> bool:
    """Inject sprint manifest entry before the GROOMER MANIFEST INJECTION POINT anchor."""
    content = STATE_PATH.read_text()
    if MANIFEST_ANCHOR not in content:
        print(f"  ❌ Manifest anchor not found in {STATE_PATH.name}")
        return False
    # Check not already present
    if f'"{sprint_key}"' in content:
        print(f"  ℹ️  {sprint_key} already in SPRINT_TASK_MANIFEST — skipping")
        return True
    ids_str = ", ".join(f'"{t}"' for t in task_ids)
    entry = f'    "{sprint_key}": [{ids_str}],\n    '
    new_content = content.replace(f"    {MANIFEST_ANCHOR}", f"{entry}{MANIFEST_ANCHOR}")
    STATE_PATH.write_text(new_content)
    return True


# ── Lint gate ─────────────────────────────────────────────────────────────────

def _run_ruff(path: Path) -> bool:
    result = subprocess.run(
        ["python3", "-m", "ruff", "check", "--select", "E,F", "--ignore", "E501,F401,F811", str(path)],
        capture_output=True, text=True, cwd=REPO_ROOT
    )
    if result.returncode != 0:
        print(f"  ⚠️  ruff warnings (non-blocking):\n{result.stdout[:500]}")
    return True  # ruff warnings don't block grooming — syntax gate is the hard gate


# ── Git commit ────────────────────────────────────────────────────────────────

def _git_commit(sprint_key: str, dry_run: bool) -> None:
    if dry_run:
        print(f"  [dry-run] Would commit groomed SubTaskDefs for {sprint_key} to main")
        return
    for cmd in [
        ["git", "config", "user.email", "autonomy@waooaw.ai"],
        ["git", "config", "user.name", "WAOOAW Sprint Groomer"],
        ["git", "add", str(RUNNER_PATH), str(STATE_PATH)],
        ["git", "commit", "-m",
         f"chore(pr): groom {sprint_key} SubTaskDefs from skeleton (ADR-036, C-059)"],
        ["git", "push", "origin", "main"],
    ]:
        r = subprocess.run(cmd, capture_output=True, text=True, cwd=REPO_ROOT)
        if r.returncode != 0 and "nothing to commit" not in r.stdout + r.stderr:
            print(f"  ⚠️  git cmd failed: {' '.join(cmd)}\n  {r.stderr[:200]}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description="Groom sprint SubTaskDefs from WC + skeleton")
    parser.add_argument("--sprint", default="", help="Sprint key e.g. WC-027")
    parser.add_argument("--dry-run", action="store_true", help="Plan only, no file writes")
    args = parser.parse_args()

    sprint_key = args.sprint.strip() or _read_current_sprint()
    if not sprint_key:
        print("  ❌ Could not determine current sprint from PROJECT_STATE.md")
        return 1

    # Normalise: WC-027 → WC-027, WC027 → WC-027
    if "-" not in sprint_key:
        sprint_key = sprint_key[:2] + "-" + sprint_key[2:]
    sprint_prefix = sprint_key.replace("-", "")  # WC-027 → WC027

    print(f"\n── Sprint Groomer: {sprint_key} ──────────────────────────────────────")

    # 1. Find WC file
    wc_file = _find_wc_file(sprint_key)
    if not wc_file:
        print(f"  ℹ️  No WC file found for {sprint_key} — grooming skipped (not yet pushed)")
        return 0

    print(f"  WC file: {wc_file.name}")

    # 2. Parse tasks
    tasks = _parse_wc_tasks(wc_file, sprint_prefix)
    if not tasks:
        print(f"  ℹ️  No tasks parsed from {wc_file.name} — check table format")
        return 0

    print(f"  Tasks in WC: {[t['task_id'] for t in tasks]}")

    # 3. Filter to ungroomed tasks
    ungroomed = [t for t in tasks if not _already_groomed(t["task_id"])]
    if not ungroomed:
        print(f"  ✅ All {len(tasks)} tasks already groomed — nothing to do")
        return 0

    print(f"  Ungroomed tasks: {[t['task_id'] for t in ungroomed]}")

    # 4. Read skeleton
    skeleton = _read_skeleton(sprint_prefix)
    if not skeleton:
        print(f"  ⚠️  No skeleton found for {sprint_prefix} — grooming without blueprint")
        print(f"  EA must produce skeleton before grooming can be skeleton-grounded (ADR-036)")

    # 5. Get API key
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("  ❌ ANTHROPIC_API_KEY not set — cannot call LLM")
        return 1

    # 6. Build depends_on chain: start from last groomed task's subtask id
    # Find the last subtask id from already-groomed tasks in this sprint
    prior_subtask_id: str | None = None
    runner_content = RUNNER_PATH.read_text()
    for t in tasks:
        if _already_groomed(t["task_id"]):
            candidate = t["task_id"] + "a"
            if candidate in runner_content:
                prior_subtask_id = candidate

    groomed_count = 0
    groomed_task_ids = []

    for task in ungroomed:
        task_id = task["task_id"]
        print(f"\n  Grooming {task_id}: {task['scope'][:60]}...")

        # Generate SubTaskDef via Haiku
        generated = _generate_subtaskdef(
            task=task,
            skeleton=skeleton,
            prior_subtask_id=prior_subtask_id,
            sprint_prefix=sprint_prefix,
            wc_filename=wc_file.name,
            api_key=api_key,
        )
        if not generated:
            print(f"  ❌ {task_id}: LLM generation failed — skipping")
            continue

        # Validate
        if not _validate_generated_entry(generated, task_id):
            print(f"  ❌ {task_id}: validation failed — skipping")
            print(f"  Generated:\n{generated[:400]}")
            continue

        if args.dry_run:
            print(f"  [dry-run] Would inject {task_id}:\n{generated[:300]}...")
            groomed_task_ids.append(task_id)
            prior_subtask_id = task_id + "a"
            continue

        # Inject into TASK_HANDLERS
        if not _inject_task_handler(generated):
            print(f"  ❌ {task_id}: injection failed")
            continue

        groomed_count += 1
        groomed_task_ids.append(task_id)
        prior_subtask_id = task_id + "a"
        print(f"  ✅ {task_id}: injected into TASK_HANDLERS")

    # 7. Update SPRINT_TASK_MANIFEST with all tasks (groomed + already-groomed)
    all_task_ids = [t["task_id"] for t in tasks]
    if groomed_count > 0 and not args.dry_run:
        _inject_manifest_entry(sprint_key, all_task_ids)
        print(f"\n  ✅ SPRINT_TASK_MANIFEST updated: {sprint_key} → {all_task_ids}")

    # 8. Lint gate
    if groomed_count > 0 and not args.dry_run:
        _run_ruff(RUNNER_PATH)
        _run_ruff(STATE_PATH)

    # 9. Compile gate (syntax check)
    if groomed_count > 0 and not args.dry_run:
        for path in [RUNNER_PATH, STATE_PATH]:
            r = subprocess.run(
                ["python3", "-m", "py_compile", str(path)],
                capture_output=True, text=True
            )
            if r.returncode != 0:
                print(f"  ❌ Syntax error after injection in {path.name}: {r.stderr[:300]}")
                print(f"  CRITICAL: manual fix required — reverting is not possible in CI")
                return 1
        print(f"  ✅ Syntax check passed for runner and sprint_state")

    # 10. Commit to main
    if groomed_count > 0:
        _git_commit(sprint_key, args.dry_run)
        print(f"\n── Grooming complete: {groomed_count} task(s) groomed for {sprint_key} ──")
    else:
        print(f"\n── Grooming: no new tasks injected for {sprint_key} ──")

    return 0


if __name__ == "__main__":
    sys.exit(main())
