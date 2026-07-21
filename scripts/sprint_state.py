#!/usr/bin/env python3
"""
sprint_state.py — SPRINT_STATE_MACHINE helper for autonomous-sprint.yaml
constitutional_basis: C-066 (Tier 2A Autonomous Sprint), C-059 (Traceability)
ib_item: IB-009
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

        # Clear next_sprint (next session's PMO will populate it)
        content = set_field(content, "next_sprint", '""')
        content = set_field(content, "next_sprint_ib_item", '""')

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


def main() -> None:
    parser = argparse.ArgumentParser(description="Sprint State Machine helper")
    sub = parser.add_subparsers(dest="command", required=True)

    # set command
    p_set = sub.add_parser("set", help="Update sprint state fields")
    p_set.add_argument("pairs", nargs="+", help="key value pairs")
    p_set.set_defaults(func=cmd_set)

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
