#!/usr/bin/env python3
"""Emit the exact-candidate WC-104 full-clean rollback plan."""

# Implements: work-contracts/WC-104-end-to-end-docker-runner-supply.md section 9
# Constitutional basis: C-023, C-059, C-065, C-071, C-080

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import yaml

from validation_control.qualification import build_wc104_rollback_manifest, render_manifest
from validation_control.local_catalog_gate import execute_gate, resolve_runner


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


def execute_rollback(
    repository: Path,
    catalog: dict[str, Any],
    *,
    candidate_sha: str,
    base_sha: str,
    git_common_dir: Path,
    runner_resolver: Callable[[Path, str], dict[str, Any]] = resolve_runner,
    gate_executor: Callable[[Path, str, str, str, Path], int] = execute_gate,
) -> dict[str, Any]:
    manifest = build_wc104_rollback_manifest(catalog, candidate_sha=candidate_sha)
    previous = {name: os.environ.get(name) for name in manifest["environment"]}
    runner_results: dict[str, Any] = {}
    gate_results: list[dict[str, Any]] = []
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
        for gate_id in manifest["required_gates"]:
            started = time.monotonic()
            returncode = gate_executor(repository, gate_id, candidate_sha, base_sha, git_common_dir)
            gate_results.append(
                {
                    "gate_id": gate_id,
                    "returncode": returncode,
                    "result": "PASS" if returncode == 0 else "FAIL",
                    "duration_seconds": round(time.monotonic() - started, 3),
                }
            )
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
    arguments.output.write_text(render_manifest(manifest), encoding="utf-8")
    print(render_manifest(manifest), end="")
    return 0 if manifest["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
