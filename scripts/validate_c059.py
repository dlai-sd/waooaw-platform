#!/usr/bin/env python3
"""Validate C-059 pull-request and commit traceability metadata."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

CONVENTIONAL_COMMIT = re.compile(
    r"^(feat|fix|constitutional|cct|chore|refactor|security|docs|agent)\([^)]+\):\s+.+"
)
BLOCKING_TRACE_TYPES = {"feat", "fix", "constitutional", "cct"}
TRACE_REFERENCE = re.compile(
    r"(?:IB:\s*IB-\d+|WC-\d+|FIX:\s*#?\d+|Constitutional:\s*(?:C|ADR|DP)-\d+)",
    re.IGNORECASE,
)
WORK_CONTRACT = re.compile(r"^Work Contract:\s*WC-\d+\s*$", re.IGNORECASE | re.MULTILINE)
CONSTITUTIONAL_BASIS = re.compile(
    r"^Constitutional Basis:\s*.*(?:C|ADR|DP)-\d+.*$",
    re.IGNORECASE | re.MULTILINE,
)


def normalize_markdown(value: str) -> str:
    return value.translate(str.maketrans("", "", "*_`"))


def validate_pr_body(body: str) -> list[str]:
    metadata = normalize_markdown(body)
    violations: list[str] = []
    if not WORK_CONTRACT.search(metadata):
        violations.append("PR_MISSING_WORK_CONTRACT: add `Work Contract: WC-<number>`")
    if not CONSTITUTIONAL_BASIS.search(metadata):
        violations.append(
            "PR_MISSING_CONSTITUTIONAL_BASIS: add "
            "`Constitutional Basis: C-<number> | ADR-<number> | DP-<number>`"
        )
    return violations


def validate_commit(subject: str, body: str) -> list[str]:
    if subject.startswith("Merge "):
        return []
    match = CONVENTIONAL_COMMIT.match(subject)
    if not match:
        return [f"COMMIT_FORMAT_INVALID: {subject}"]
    commit_type = match.group(1)
    if commit_type in BLOCKING_TRACE_TYPES and not TRACE_REFERENCE.search(f"{subject}\n{body}"):
        return [
            f"COMMIT_TRACE_MISSING: {subject} (add IB, WC, FIX, or Constitutional reference "
            "to subject or body)"
        ]
    return []


def read_commits(base: str, head: str) -> list[tuple[str, str]]:
    result = subprocess.run(  # noqa: S603
        ["git", "log", f"{base}..{head}", "--format=%s%x1f%b%x1e"],  # noqa: S607
        check=True,
        capture_output=True,
        text=True,
    )
    commits: list[tuple[str, str]] = []
    for record in result.stdout.split("\x1e"):
        record = record.strip("\r\n")
        if not record.strip("\r\n"):
            continue
        subject, separator, body = record.partition("\x1f")
        if not separator:
            raise ValueError("unexpected git log record")
        commits.append((subject.strip(), body.strip()))
    return commits


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pr-body-file", required=True, type=Path)
    parser.add_argument("--base", required=True)
    parser.add_argument("--head", required=True)
    arguments = parser.parse_args()
    violations = validate_pr_body(arguments.pr_body_file.read_text(encoding="utf-8"))
    try:
        for subject, body in read_commits(arguments.base, arguments.head):
            violations.extend(validate_commit(subject, body))
    except (subprocess.CalledProcessError, ValueError) as error:
        violations.append(f"COMMIT_HISTORY_UNREADABLE: {error}")
    if violations:
        print("C-059 validation failed:", file=sys.stderr)
        for violation in violations:
            print(f"- {violation}", file=sys.stderr)
        return 1
    print("C-059 validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())