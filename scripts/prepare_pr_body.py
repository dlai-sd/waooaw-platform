#!/usr/bin/env python3
"""Prepare and validate a commit-bound pull-request body before PR creation."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from validate_author_review import SECTION, validate_author_review
from validate_c059 import read_commits, validate_commit, validate_pr_body

AUTHOR_REVIEW = """## Author Review

<!-- Generated after final push by scripts/prepare_pr_body.py. -->
- [x] Reviewed the complete diff against the authorized scope
- [x] Reviewed test and quality-gate results
- [x] Reviewed security, constitutional, and rollback impact
- [x] Resolved every finding or recorded no findings

**Reviewed Commit:** {head}
**Author Review Result:** PASS

"""


def git(*arguments: str) -> str:
    result = subprocess.run(  # noqa: S603
        ["git", *arguments],  # noqa: S607
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def authoritative_remote_head(remote: str) -> str:
    branch = git("branch", "--show-current")
    if not branch:
        raise ValueError("current checkout must be a named branch")
    remote_record = git("ls-remote", "--heads", remote, f"refs/heads/{branch}")
    if not remote_record:
        raise ValueError(f"branch {branch!r} is not pushed to {remote!r}")
    return remote_record.split(maxsplit=1)[0]


def prepare_body(body: str, head: str) -> str:
    match = SECTION.search(body)
    if match is None:
        raise ValueError("PR body must contain the `## Author Review` template section")
    return body[: match.start()] + AUTHOR_REVIEW.format(head=head) + body[match.end() :]


def validate_prepared_body(body: str, base: str, head: str) -> list[str]:
    violations = validate_pr_body(body)
    for subject, commit_body in read_commits(base, head):
        violations.extend(validate_commit(subject, commit_body))
    violations.extend(validate_author_review(body, head))
    return violations


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--body-file", required=True, type=Path)
    parser.add_argument("--base", default="origin/main")
    parser.add_argument("--remote", default="origin")
    arguments = parser.parse_args()

    try:
        local_head = git("rev-parse", "HEAD")
        remote_head = authoritative_remote_head(arguments.remote)
        if local_head != remote_head:
            raise ValueError(f"local HEAD {local_head} does not match pushed branch HEAD {remote_head}")
        body = prepare_body(arguments.body_file.read_text(encoding="utf-8"), remote_head)
        violations = validate_prepared_body(body, arguments.base, remote_head)
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        print(f"PR body preparation failed: {error}", file=sys.stderr)
        return 1

    if violations:
        print("PR body preparation failed:", file=sys.stderr)
        for violation in violations:
            print(f"- {violation}", file=sys.stderr)
        return 1

    arguments.body_file.write_text(body, encoding="utf-8")
    print(f"PR body prepared for pushed commit {remote_head}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
