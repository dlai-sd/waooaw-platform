#!/usr/bin/env python3
"""Run catalog-selected prechecks against the exact staged Git tree."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from precheck_orchestrator import EVIDENCE_FILE_NAME, run_prechecks
from prepare_pr_body import (
    PRECHECK_GRAPH_VERSION,
    changed_files_digest,
    configuration_digest,
    precheck_nodes,
    runner_digest,
)


def git(*arguments: str, env: dict[str, str] | None = None) -> str:
    git_executable = shutil.which("git")
    if git_executable is None:
        raise ValueError("git executable is required for staged prechecks")
    completed = subprocess.run(  # noqa: S603
        [git_executable, *arguments],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )
    return completed.stdout.strip()


def staged_candidate() -> tuple[str, str, list[str]]:
    base = git("rev-parse", "HEAD")
    tree = git("write-tree")
    changed_files = git("diff", "--cached", "--name-only", "--diff-filter=ACMR").splitlines()
    if not changed_files:
        raise ValueError("staged prechecks require at least one staged file")
    identity = {
        **os.environ,
        "GIT_AUTHOR_NAME": "WAOOAW staged precheck",
        "GIT_AUTHOR_EMAIL": "staged-precheck@waooaw.invalid",
        "GIT_COMMITTER_NAME": "WAOOAW staged precheck",
        "GIT_COMMITTER_EMAIL": "staged-precheck@waooaw.invalid",
        "GIT_AUTHOR_DATE": git("show", "-s", "--format=%aI", base),
        "GIT_COMMITTER_DATE": git("show", "-s", "--format=%cI", base),
    }
    candidate = git("commit-tree", tree, "-p", base, "-m", "chore(validation): staged precheck", env=identity)
    return base, candidate, changed_files


def main() -> int:
    repository = Path(git("rev-parse", "--show-toplevel"))
    git_common_dir = Path(git("rev-parse", "--path-format=absolute", "--git-common-dir"))
    base, candidate, changed_files = staged_candidate()
    nodes = [
        node
        for node in precheck_nodes(repository, git_common_dir, base, candidate, changed_files)
        if node.name != "release_qualification"
    ]
    artifact_dir = repository / "test-results/wc109/precommit" / git("rev-parse", f"{candidate}^{{tree}}")
    evidence = run_prechecks(
        nodes,
        base_sha=base,
        head_sha=candidate,
        changed_file_digest=changed_files_digest(changed_files),
        graph_version=PRECHECK_GRAPH_VERSION,
        configuration_digest=configuration_digest(),
        runner_digest=runner_digest(nodes),
        artifact_dir=artifact_dir,
        reuse_evidence_paths=sorted(artifact_dir.parent.glob(f"*/{EVIDENCE_FILE_NAME}")),
    )
    print(
        json.dumps(
            {
                "schema": evidence["schema"],
                "commit_sha": evidence["commit_sha"],
                "passed": evidence["passed"],
                "executed_count": evidence["executed_count"],
                "reused_count": evidence["reused_count"],
                "expected_reuse_count": evidence["expected_reuse_count"],
                "reuse_candidate_count": evidence["reuse_candidate_count"],
                "first_causal_failure": evidence["first_causal_failure"],
                "manifest_path": str(artifact_dir / EVIDENCE_FILE_NAME),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if evidence.get("passed") is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
