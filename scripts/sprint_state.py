#!/usr/bin/env python3
"""
sprint_state.py — SPRINT_STATE_MACHINE helper for autonomous-sprint.yaml

# Implements: architecture/reference/agents/platform-it-expert-agent.md (Sprint State Machine)
# constitutional_basis: C-059 (Traceability), C-066 Tier 2A (autonomous sprint cycle),
#                       C-070 (Constitutional DNA), C-073 (this annotation)
# ib_item: IB-009
# office: Platform IT Expert
# amended: 2026-07-23 — EA review; SPRINT_TASK_MANIFEST added; cmd_advance populates tasks_remaining
spec: architecture/reference/agents/platform-it-expert-agent.md §Skill 8

Commands:
  set <key> <value> [<key> <value> ...]   — update fields in SPRINT_STATE_MACHINE
  advance --current WC-NNN --ib IB-NNN   — mark current sprint DONE, activate next
  generate-secrets-doc --output FILE      — generate GITHUB-SECRETS.md (stub)
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
STATE_FILE = REPO_ROOT / "constitution" / "PROJECT_STATE.md"

# Sprint → task list manifest. Reviewer and runner both reference this.
# When a sprint completes, the next sprint's tasks_remaining is populated from here.
SPRINT_TASK_MANIFEST: dict[str, list[str]] = {
    "WC-011": ["WC011-01", "WC011-02", "WC011-03", "WC011-04", "WC011-05", "WC011-07"],
    "WC-012": ["WC012-01", "WC012-02", "WC012-03", "WC012-04"],
    "WC-013": ["WC013-01", "WC013-02", "WC013-03", "WC013-04"],
    "WC-014": ["WC014-01", "WC014-02", "WC014-03", "WC014-04"],
    "WC-015": ["WC015-01", "WC015-02", "WC015-03", "WC015-04", "WC015-05"],
    "WC-016": ["WC016-01", "WC016-02", "WC016-03", "WC016-04"],
    "WC-017": ["WC017-01", "WC017-02", "WC017-03", "WC017-04"],
    "WC-018": ["WC018-01", "WC018-02", "WC018-03", "WC018-04", "WC018-05", "WC018-06", "WC018-07"],
}


def read_state_file() -> str:
    return STATE_FILE.read_text(encoding="utf-8")


def write_state_file(content: str) -> None:
    STATE_FILE.write_text(content, encoding="utf-8")


def set_field(content: str, key: str, value: str) -> str:
    """
    Update a scalar field inside the ```yaml block under ## SPRINT_STATE_MACHINE.
    Handles both populated and empty values. Preserves inline comments.
    """
    # Pattern: key: <value_part> <whitespace> # optional comment
    pattern = re.compile(
        r'^(' + re.escape(key) + r':\s*)([^\n#]*?)(\s*)(#[^\n]*)?$',
        re.MULTILINE,
    )

    def replacer(m: re.Match) -> str:
        prefix = m.group(1)          # "key: "
        padding = m.group(3) or "    "  # whitespace before comment
        comment = m.group(4) or ""   # "# optional comment"
        return f"{prefix}{value}{padding}{comment}".rstrip()

    new_content, n = pattern.subn(replacer, content)
    if n == 0:
        print(f"WARNING: key '{key}' not found in SPRINT_STATE_MACHINE — skipping", file=sys.stderr)
    return new_content


def set_list_field(content: str, key: str, items: list[str]) -> str:
    """
    Update a YAML list field inside the ```yaml block under ## SPRINT_STATE_MACHINE.
    Handles both inline (e.g. tasks_done: []) and block list formats.
    RC#2 fix: called after each successful task to advance tasks_done/tasks_remaining.
    """
    if not items:
        # Empty list — use inline format
        new_value = "[]"
        # Replace inline: tasks_done: [] OR tasks_done: [...]
        inline_pat = re.compile(
            r'^(' + re.escape(key) + r':\s*)(\[.*?\])(.*)$',
            re.MULTILINE,
        )
        new_content, n = inline_pat.subn(lambda m: f"{m.group(1)}{new_value}{m.group(3)}", content)
        if n > 0:
            return new_content
    # Non-empty: use block list format (indented "  - item")
    block_items = "\n".join(f"  - {item}" for item in items)
    new_block = f"{key}:\n{block_items}"
    # Replace existing block (multi-line) or inline form
    block_pat = re.compile(
        r'^' + re.escape(key) + r':[ ]*(?:\[.*?\]|(?:\n  - [^\n]+)+)',
        re.MULTILINE,
    )
    new_content, n = block_pat.subn(new_block, content)
    if n == 0:
        # Fallback: scalar replacement
        new_content = set_field(content, key, f"[{', '.join(items)}]")
    return new_content


def cmd_set(args: argparse.Namespace) -> None:
    if len(args.pairs) % 2 != 0:
        print("ERROR: 'set' requires pairs of key value", file=sys.stderr)
        sys.exit(1)

    content = read_state_file()
    for i in range(0, len(args.pairs), 2):
        key, value = args.pairs[i], args.pairs[i + 1]
        content = set_field(content, key, value)
        print(f"  set {key} = {value}")

    write_state_file(content)
    print(f"✓ PROJECT_STATE.md updated ({len(args.pairs)//2} field(s))")


def cmd_advance(args: argparse.Namespace) -> None:
    content = read_state_file()

    # Mark current sprint DONE
    content = set_field(content, "sprint_status", "DONE")
    content = set_field(content, "current_task", '""')
    content = set_field(content, "current_task_started_utc", '""')
    content = set_field(content, "blocker", '""')

    # Activate next sprint (swap current ↔ next)
    next_match = re.search(r'^next_sprint:\s*(\S+)', content, re.MULTILINE)
    next_ib_match = re.search(r'^next_sprint_ib_item:\s*(\S+)', content, re.MULTILINE)

    if next_match and next_match.group(1) not in ('""', "''", ""):
        next_sprint = next_match.group(1)
        next_ib = next_ib_match.group(1) if next_ib_match else args.ib

        # Set current sprint to next
        content = set_field(content, "current_sprint", next_sprint)
        content = set_field(content, "sprint_ib_item", next_ib)
        content = set_field(content, "sprint_status", "READY")
        content = set_field(content, "tasks_done", "[]")

        # Determine branch for next sprint
        ib_num = re.search(r'\d+', next_ib)
        slug = next_sprint.lower().replace("wc-", "sprint-")
        new_branch = f"ib/{ib_num.group() if ib_num else '009'}/{slug}"
        content = set_field(content, "branch", new_branch)

        # Populate tasks_remaining for next sprint from manifest
        next_tasks = SPRINT_TASK_MANIFEST.get(next_sprint, [])
        if next_tasks:
            # Build YAML list block
            task_lines = "\n".join(f"  - {t}" for t in next_tasks)
            # Replace tasks_remaining: ... (list block) with new list
            content = re.sub(
                r'tasks_remaining:.*?(?=\n\n|\ncurrent_task:)',
                f'tasks_remaining:\n{task_lines}',
                content, flags=re.DOTALL
            )
            print(f"  tasks_remaining populated for {next_sprint}: {next_tasks}")
        else:
            content = set_field(content, "tasks_remaining", "[]")
            print(f"  WARNING: No task manifest for {next_sprint} — tasks_remaining set to []")

        # Clear next_sprint (next session's PMO will populate it)
        content = set_field(content, "next_sprint", next_sprint.replace("WC-0", "WC-0").replace(
            next_sprint, f"WC-0{int(next_sprint.split('-')[1])+1:02d}"))
        content = set_field(content, "next_sprint_ib_item", next_ib)

        print(f"✓ Sprint advanced: {args.current} DONE → {next_sprint} READY")
    else:
        print(f"✓ Sprint {args.current} marked DONE. No next_sprint defined — awaiting PMO.")

    write_state_file(content)

    # Also update INSTITUTIONAL_BACKLOG if accessible
    backlog_file = REPO_ROOT / "constitution" / "INSTITUTIONAL_BACKLOG.md"
    if backlog_file.exists():
        backlog = backlog_file.read_text(encoding="utf-8")
        # Mark the sprint's IB item progress (heuristic — finds AUTHORIZED near sprint ref)
        if f"Status:** AUTHORIZED" in backlog and args.current in backlog:
            print(f"  (INSTITUTIONAL_BACKLOG.md: IB {args.ib} remains AUTHORIZED — full DONE on Gate passage)")
    # Note: advance-state job should commit PROJECT_STATE.md to the feature branch,
    # NOT push to main directly. The PR merge itself advances main.
    # Direct main push is forbidden by CODEOWNERS (C-065 — Author cannot merge own work).


def cmd_generate_secrets_doc(args: argparse.Namespace) -> None:
    """Generate infrastructure/GITHUB-SECRETS.md stub — used by WC011-07."""
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    # Actual content generated inline in autonomous-sprint.yaml task WC011-07
    print(f"✓ Secrets doc stub target: {output}")


def cmd_set_list(args: argparse.Namespace) -> None:
    """
    Update a YAML list field in SPRINT_STATE_MACHINE.
    RC#2 fix: records tasks_done and tasks_remaining after each successful task commit.
    """
    content = read_state_file()
    content = set_list_field(content, args.key, args.items)
    write_state_file(content)
    print(f"✓ {args.key} = {args.items or '[]'}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Sprint State Machine helper")
    sub = parser.add_subparsers(dest="command", required=True)

    # set command
    p_set = sub.add_parser("set", help="Update sprint state fields")
    p_set.add_argument("pairs", nargs="+", help="key value pairs")
    p_set.set_defaults(func=cmd_set)

    # set-list command — RC#2 fix: advance tasks_done/tasks_remaining per task success
    p_setlist = sub.add_parser("set-list", help="Update a YAML list field in sprint state")
    p_setlist.add_argument("key", help="Field name (e.g. tasks_done)")
    p_setlist.add_argument("items", nargs="*", help="List items (space-separated, empty = [])")
    p_setlist.set_defaults(func=cmd_set_list)

    # advance command
    p_adv = sub.add_parser("advance", help="Mark sprint done and activate next")
    p_adv.add_argument("--current", required=True)
    p_adv.add_argument("--ib", required=True)
    p_adv.set_defaults(func=cmd_advance)

    # generate-secrets-doc command
    p_sec = sub.add_parser("generate-secrets-doc", help="Generate GITHUB-SECRETS.md")
    p_sec.add_argument("--output", required=True)
    p_sec.set_defaults(func=cmd_generate_secrets_doc)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
