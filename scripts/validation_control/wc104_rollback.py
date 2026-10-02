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

from validation_control.evidence_controller import BLOCKED_DEFERRED_AMENDMENT, BLOCKED_DEFERRED_GATES
from validation_control.qualification import build_wc104_rollback_manifest, render_manifest
from validation_control.local_catalog_gate import execute_gate, required_service_identities, resolve_runner
from validation_control.orchestrator import build_execution_plan


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


def publish_rollback_checkpoint(
    path: Path,
    manifest: dict[str, Any],
    *,
    base_sha: str,
    runner_results: dict[str, Any],
    service_results: dict[str, Any],
    gate_results: list[dict[str, Any]],
    first_cause_gate: str | None,
) -> None:
    checkpoint = {
        **manifest,
        "base_sha": base_sha,
        "runner_results": runner_results,
        "service_results": service_results,
        "gate_results": gate_results,
        "first_cause_gate": first_cause_gate,
        "run_state": manifest.get("run_state", "FAILED" if first_cause_gate is not None else "IN_PROGRESS"),
        "passed": False,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + f".tmp-{os.getpid()}")
    try:
        temporary.write_text(render_manifest(checkpoint), encoding="utf-8")
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def execute_rollback(
    repository: Path,
    catalog: dict[str, Any],
    *,
    candidate_sha: str,
    base_sha: str,
    git_common_dir: Path,
    qualification_context: QualificationContext | None = None,
    checkpoint_path: Path | None = None,
    runner_resolver: Callable[[Path, str], dict[str, Any]] = resolve_runner,
    service_resolver: Callable[[Path, dict[str, Any]], dict[str, str]] = required_service_identities,
    gate_executor: Callable[..., int] = execute_gate,
) -> dict[str, Any]:
    manifest = build_wc104_rollback_manifest(catalog, candidate_sha=candidate_sha)
    previous = {name: os.environ.get(name) for name in manifest["environment"]}
    runner_results: dict[str, Any] = {}
    service_results: dict[str, Any] = {}
    gate_results: list[dict[str, Any]] = []
    first_cause_gate: str | None = None
    if qualification_context is None:
        qualification_context = resolve_qualification_context(repository, base_sha, candidate_sha)

    def checkpoint() -> None:
        if checkpoint_path is not None:
            publish_rollback_checkpoint(
                checkpoint_path,
                manifest,
                base_sha=base_sha,
                runner_results=runner_results,
                service_results=service_results,
                gate_results=gate_results,
                first_cause_gate=first_cause_gate,
            )

    plan = build_execution_plan(
        catalog,
        manifest["required_gates"],
        mode="qualification",
        head_sha=candidate_sha,
        run_id=f"rollback-preflight-{candidate_sha}",
    )
    for node in plan["nodes"]:
        if not node["required_services"] or node["gate_id"] in service_results:
            continue
        try:
            service_results[node["gate_id"]] = service_resolver(repository, node)
        except Exception as exception:
            first_cause_gate = f"preflight:{node['gate_id']}"
            error = f"{type(exception).__name__}: {exception}"
            for gate_id in manifest["required_gates"]:
                if gate_id in BLOCKED_DEFERRED_GATES:
                    gate_results.append(
                        {
                            "gate_id": gate_id,
                            "result": "BLOCKED",
                            "disposition": "BLOCKED-DEFERRED",
                            "disposition_proof": {
                                "founder_scope_amendment": BLOCKED_DEFERRED_AMENDMENT,
                                "release_blocking": True,
                            },
                            "duration_seconds": 0.0,
                        }
                    )
                else:
                    result = {
                        "gate_id": gate_id,
                        "result": "BLOCKED",
                        "disposition": "PREFLIGHT_BLOCKED",
                        "first_cause_gate": first_cause_gate,
                        "duration_seconds": 0.0,
                    }
                    if gate_id == node["gate_id"]:
                        result["error"] = error
                    gate_results.append(result)
            manifest.update(
                {
                    "base_sha": base_sha,
                    "runner_results": runner_results,
                    "service_results": service_results,
                    "gate_results": gate_results,
                    "first_cause_gate": first_cause_gate,
                    "execution_summary": {
                        "executed_gate_count": 0,
                        "suppressed_gate_count": len(manifest["required_gates"]) - len(BLOCKED_DEFERRED_GATES),
                        "deferred_gate_count": len(BLOCKED_DEFERRED_GATES),
                    },
                    "passed": False,
                    "run_state": "BLOCKED",
                }
            )
            checkpoint()
            return manifest

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
                if gate_id in BLOCKED_DEFERRED_GATES:
                    gate_results.append(
                        {
                            "gate_id": gate_id,
                            "result": "BLOCKED",
                            "disposition": "BLOCKED-DEFERRED",
                            "disposition_proof": {
                                "founder_scope_amendment": BLOCKED_DEFERRED_AMENDMENT,
                                "release_blocking": True,
                            },
                            "duration_seconds": round(time.monotonic() - started, 3),
                        }
                    )
                    checkpoint()
                    continue
                if first_cause_gate is not None:
                    gate_results.append(
                        {
                            "gate_id": gate_id,
                            "result": "BLOCKED",
                            "disposition": "SUPPRESSED_AFTER_FAILURE",
                            "first_cause_gate": first_cause_gate,
                            "duration_seconds": 0.0,
                        }
                    )
                    checkpoint()
                    continue
                error: str | None = None
                disposition: str | None = None
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
                except KeyboardInterrupt:
                    returncode = 1
                    error = "KeyboardInterrupt: operator cancellation"
                    disposition = "OPERATOR_CANCELLED"
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
                if disposition is not None:
                    result["result"] = "BLOCKED"
                    result["disposition"] = disposition
                gate_results.append(result)
                if result["result"] in {"FAIL", "BLOCKED"}:
                    first_cause_gate = gate_id
                checkpoint()
    finally:
        for name, value in previous.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
    manifest["base_sha"] = base_sha
    manifest["runner_results"] = runner_results
    manifest["service_results"] = service_results
    manifest["gate_results"] = gate_results
    manifest["first_cause_gate"] = first_cause_gate
    manifest["execution_summary"] = {
        "executed_gate_count": sum("returncode" in result for result in gate_results),
        "suppressed_gate_count": sum(result.get("disposition") == "SUPPRESSED_AFTER_FAILURE" for result in gate_results),
        "deferred_gate_count": sum(result.get("disposition") == "BLOCKED-DEFERRED" for result in gate_results),
    }
    manifest["passed"] = len(gate_results) == len(manifest["required_gates"]) and all(
        result["result"] == "PASS" or (result["result"] == "BLOCKED" and result.get("disposition") == "BLOCKED-DEFERRED")
        for result in gate_results
    )
    manifest["run_state"] = "PASSED" if manifest["passed"] else "FAILED"
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
        checkpoint_path=arguments.output,
    )
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    temporary_output = arguments.output.with_suffix(arguments.output.suffix + ".tmp")
    temporary_output.write_text(render_manifest(manifest), encoding="utf-8")
    temporary_output.replace(arguments.output)
    print(render_manifest(manifest), end="")
    return 0 if manifest["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
