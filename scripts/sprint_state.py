#!/usr/bin/env python3
"""
sprint_state.py — SPRINT_STATE_MACHINE helper for autonomous-sprint.yaml

# Implements: architecture/reference/agents/platform-it-expert-agent.md (Sprint State Machine)
# constitutional_basis: C-059 (Traceability), C-066 Tier 2A (autonomous sprint cycle),
#                       C-070 (Constitutional DNA), C-073 (this annotation)
# ib_item: IB-009
# office: Platform IT Expert
spec: architecture/reference/agents/platform-it-expert-agent.md §Skill 8

Architecture: PROJECT_STATE.md is a 5-field Founder control panel (current_sprint,
branch, sprint_status, autonomous_halt, consecutive_failures). Task progress lives
in the work-contract file (WC-NNN.md) — the runner reads/writes only that file.

Commands:
  set <key> <value> [<key> <value> ...]   — update fields in SPRINT_STATE_MACHINE
  advance --current WC-NNN --ib IB-NNN   — mark current sprint DONE
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
    # Scope replacement to SPRINT_STATE_MACHINE block only — avoids clobbering session records
    sm_idx = content.find("## SPRINT_STATE_MACHINE")
    if sm_idx < 0:
        print(f"WARNING: ## SPRINT_STATE_MACHINE not found — skipping {key}", file=sys.stderr)
        return content
    prefix_part = content[:sm_idx]
    sm_part = content[sm_idx:]

    # Pattern: key: <value_part> <whitespace> # optional comment
    # Use [ \t]* (not \s*) to prevent consuming newlines and stripping the closing ``` fence
    pattern = re.compile(
        r'^(' + re.escape(key) + r':[ \t]*)([^\n#]*?)([ \t]*)(#[^\n]*)?$',
        re.MULTILINE,
    )

    def replacer(m: re.Match) -> str:
        pfx = m.group(1)          # "key: "
        padding = m.group(3) or "    "  # whitespace before comment
        comment = m.group(4) or ""   # "# optional comment"
        return f"{pfx}{value}{padding}{comment}".rstrip()

    new_sm_part, n = pattern.subn(replacer, sm_part)
    if n == 0:
        print(f"WARNING: key '{key}' not found in SPRINT_STATE_MACHINE — skipping", file=sys.stderr)
    return prefix_part + new_sm_part


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
    """
    Mark current sprint DONE. Task lists live in the WC file — not populated here.
    PMO activates the next sprint with: sprint_state.py set current_sprint WC-NNN ...
    """
    content = read_state_file()
    content = set_field(content, "sprint_status", "DONE")
    write_state_file(content)
    print(f"✓ Sprint {args.current} marked DONE — run 'set' to activate next sprint")

    backlog_file = REPO_ROOT / "constitution" / "INSTITUTIONAL_BACKLOG.md"
    if backlog_file.exists():
        backlog = backlog_file.read_text(encoding="utf-8")
        if "Status:** AUTHORIZED" in backlog and args.current in backlog:
            print(f"  (INSTITUTIONAL_BACKLOG.md: IB {args.ib} remains AUTHORIZED — full DONE on Gate passage)")


def cmd_generate_secrets_doc(args: argparse.Namespace) -> None:
    """Generate infrastructure/GITHUB-SECRETS.md stub — used by WC011-07."""
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    print(f"✓ Secrets doc stub target: {output}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Sprint State Machine helper")
    sub = parser.add_subparsers(dest="command", required=True)

    p_set = sub.add_parser("set", help="Update sprint state fields")
    p_set.add_argument("pairs", nargs="+", help="key value pairs")
    p_set.set_defaults(func=cmd_set)

    p_adv = sub.add_parser("advance", help="Mark sprint done")
    p_adv.add_argument("--current", required=True)
    p_adv.add_argument("--ib", required=True)
    p_adv.set_defaults(func=cmd_advance)

    p_sec = sub.add_parser("generate-secrets-doc", help="Generate GITHUB-SECRETS.md")
    p_sec.add_argument("--output", required=True)
    p_sec.set_defaults(func=cmd_generate_secrets_doc)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
