#!/usr/bin/env python3
"""Emit the exact-candidate WC-104 full-clean rollback plan."""

# Implements: work-contracts/WC-104-end-to-end-docker-runner-supply.md section 9
# Constitutional basis: C-023, C-059, C-065, C-071, C-080

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from validation_control.qualification import build_wc104_rollback_manifest, render_manifest
from validation_control.local_catalog_gate import execute_gate, resolve_runner


@dataclass(frozen=True)
class QualificationContext:
    changed_files: tuple[str, ...]
    pr_body: str
    base_branch: str
    pr_number: str
    repository_name: str


def git_head(repository: Path) -> str:
    git = shutil.which("git")
    if git is None:
        raise ValueError("git executable is required for rollback evidence")
    completed = subprocess.run(  # noqa: S603
        [git, "rev-parse", "HEAD"],
        cwd=repository,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def resolve_qualification_context(repository: Path, base_sha: str, candidate_sha: str) -> QualificationContext:
    git = shutil.which("git")
    gh = shutil.which("gh")
    if git is None or gh is None:
        raise ValueError("git and gh are required for rollback qualification context")
    changed = subprocess.run(  # noqa: S603
        [git, "diff", "--name-only", "--find-renames", f"{base_sha}...{candidate_sha}"],
        cwd=repository,
        check=True,
        capture_output=True,
        text=True,
    )
    pull_request = subprocess.run(  # noqa: S603
        [gh, "pr", "view", "--json", "baseRefName,body,headRefOid,number"],
        cwd=repository,
        check=True,
        capture_output=True,
        text=True,
    )
    pr = json.loads(pull_request.stdout)
    if pr.get("headRefOid") != candidate_sha:
        raise ValueError("rollback PR head does not match candidate HEAD")
    remote = subprocess.run(  # noqa: S603
        [git, "remote", "get-url", "origin"],
        cwd=repository,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    match = re.search(r"github\.com(?::|/)([^/]+/[^/]+?)(?:\.git)?$", remote)
    if match is None:
        raise ValueError("origin is not a supported GitHub repository URL")
    return QualificationContext(
        changed_files=tuple(path for path in changed.stdout.splitlines() if path),
        pr_body=str(pr["body"]),
        base_branch=str(pr["baseRefName"]),
        pr_number=str(pr["number"]),
        repository_name=match.group(1),
    )


def execute_rollback(
    repository: Path,
    catalog: dict[str, Any],
    *,
    candidate_sha: str,
    base_sha: str,
    git_common_dir: Path,
    qualification_context: QualificationContext | None = None,
    runner_resolver: Callable[[Path, str], dict[str, Any]] = resolve_runner,
    gate_executor: Callable[..., int] = execute_gate,
) -> dict[str, Any]:
    manifest = build_wc104_rollback_manifest(catalog, candidate_sha=candidate_sha)
    previous = {name: os.environ.get(name) for name in manifest["environment"]}
    runner_results: dict[str, Any] = {}
    gate_results: list[dict[str, Any]] = []
    if qualification_context is None:
        qualification_context = resolve_qualification_context(repository, base_sha, candidate_sha)
    try:
        os.environ.update(manifest["environment"])
        docker_config = Path(os.environ["DOCKER_CONFIG"])
        docker_config.mkdir(parents=True, exist_ok=True)
        docker_config.chmod(0o700)
        for runner_id in manifest["required_runners"]:
            resolution = runner_resolver(repository, runner_id)
            if resolution.get("build_count") != 1 or resolution.get("trust_source") != "local-identity-build":
                raise ValueError(f"rollback did not clean-build runner: {runner_id}")
            runner_results[runner_id] = resolution
        os.environ["WC104_FORCE_LOCAL_BUILD"] = "0"
        with tempfile.TemporaryDirectory(prefix="wc104-rollback-") as temporary_directory:
            pr_body_file = Path(temporary_directory) / "pr-body.md"
            pr_body_file.write_text(qualification_context.pr_body, encoding="utf-8")
            for gate_id in manifest["required_gates"]:
                started = time.monotonic()
                error: str | None = None
                try:
                    returncode = gate_executor(
                        repository,
                        gate_id,
                        candidate_sha,
                        base_sha,
                        git_common_dir,
                        changed_files=list(qualification_context.changed_files),
                        pr_body_file=pr_body_file,
                        base_branch=qualification_context.base_branch,
                        pr_number=qualification_context.pr_number,
                        repository_name=qualification_context.repository_name,
                    )
                except Exception as exception:
                    returncode = 1
                    error = f"{type(exception).__name__}: {exception}"
                result = {
                    "gate_id": gate_id,
                    "returncode": returncode,
                    "result": "PASS" if returncode == 0 else "FAIL",
                    "duration_seconds": round(time.monotonic() - started, 3),
                }
                if error is not None:
                    result["error"] = error
                gate_results.append(result)
    finally:
        for name, value in previous.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
    manifest["base_sha"] = base_sha
    manifest["runner_results"] = runner_results
    manifest["gate_results"] = gate_results
    manifest["passed"] = len(gate_results) == len(manifest["required_gates"]) and all(
        result["returncode"] == 0 for result in gate_results
    )
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", type=Path, default=Path.cwd())
    parser.add_argument("--base", required=True)
    parser.add_argument("--git-common-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    repository = arguments.repository.resolve()
    catalog = yaml.safe_load((repository / "validation/engineering-validation.yaml").read_text(encoding="utf-8"))
    if not isinstance(catalog, dict):
        raise ValueError("validation catalog root must be a mapping")
    manifest = execute_rollback(
        repository,
        catalog,
        candidate_sha=git_head(repository),
        base_sha=arguments.base,
        git_common_dir=arguments.git_common_dir.resolve(),
    )
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    temporary_output = arguments.output.with_suffix(arguments.output.suffix + ".tmp")
    temporary_output.write_text(render_manifest(manifest), encoding="utf-8")
    temporary_output.replace(arguments.output)
    print(render_manifest(manifest), end="")
    return 0 if manifest["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
