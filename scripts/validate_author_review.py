#!/usr/bin/env python3
"""Validate mandatory author-review evidence against the current PR head."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

SECTION = re.compile(
    r"^## Author Review\s*$\n(?P<body>.*?)(?=^##\s|\Z)",
    re.IGNORECASE | re.MULTILINE | re.DOTALL,
)
REVIEWED_COMMIT = re.compile(
    r"^Reviewed Commit:\s*([0-9a-f]{40})\s*$",
    re.IGNORECASE | re.MULTILINE,
)
REVIEW_RESULT = re.compile(
    r"^Author Review Result:\s*PASS\s*$",
    re.IGNORECASE | re.MULTILINE,
)
REQUIRED_CHECKS = (
    "Reviewed the complete diff against the authorized scope",
    "Reviewed test and quality-gate results",
    "Reviewed security, constitutional, and rollback impact",
    "Resolved every finding or recorded no findings",
)


def normalize_markdown(value: str) -> str:
    return value.translate(str.maketrans("", "", "*_`"))


def validate_author_review(body: str, head_sha: str) -> list[str]:
    violations: list[str] = []
    normalized_head = head_sha.strip().lower()
    if re.fullmatch(r"[0-9a-f]{40}", normalized_head) is None:
        return ["AUTHOR_REVIEW_HEAD_INVALID: current PR head must be a full 40-character SHA"]

    match = SECTION.search(body)
    if match is None:
        return ["AUTHOR_REVIEW_MISSING: add the `## Author Review` section"]

    section = normalize_markdown(match.group("body"))
    for label in REQUIRED_CHECKS:
        if re.search(rf"^- \[[xX]\]\s+{re.escape(label)}\s*$", section, re.MULTILINE) is None:
            violations.append(f"AUTHOR_REVIEW_CHECK_MISSING: {label}")

    reviewed_commit = REVIEWED_COMMIT.search(section)
    if reviewed_commit is None:
        violations.append("AUTHOR_REVIEW_SHA_MISSING: add the full reviewed commit SHA")
    elif reviewed_commit.group(1).lower() != normalized_head:
        violations.append(
            "AUTHOR_REVIEW_STALE: reviewed commit "
            f"{reviewed_commit.group(1).lower()} does not match PR head {normalized_head}"
        )

    if REVIEW_RESULT.search(section) is None:
        violations.append("AUTHOR_REVIEW_NOT_PASS: set `Author Review Result: PASS`")
    return violations


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pr-body-file", required=True, type=Path)
    parser.add_argument("--head", required=True)
    arguments = parser.parse_args()

    violations = validate_author_review(
        arguments.pr_body_file.read_text(encoding="utf-8"),
        arguments.head,
    )
    if violations:
        print("Author review validation failed:", file=sys.stderr)
        for violation in violations:
            print(f"- {violation}", file=sys.stderr)
        return 1
    print("Author review validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
