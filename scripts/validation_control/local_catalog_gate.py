#!/usr/bin/env python3
"""Resolve one local validation runner and execute its immutable catalog node."""

# Implements: work-contracts/WC-104-end-to-end-docker-runner-supply.md sections 4.3-4.5
# Constitutional basis: C-023, C-059, C-071, C-080

from __future__ import annotations

import argparse
import fcntl
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from validation_control.orchestrator import build_execution_plan  # noqa: E402
from validation_control.runner_supply import (  # noqa: E402
    create_context,
    load_supply_config,
    runner_specification,
    validate_supply_manifest,
)

SHA256 = re.compile(r"sha256:[0-9a-f]{64}")


def image_id(image: str, repository: Path) -> str | None:
    completed = subprocess.run(  # noqa: S603
        ["docker", "image", "inspect", image, "--format", "{{.Id}}"],
        cwd=repository,
        check=False,
        capture_output=True,
        text=True,
    )
    candidate = completed.stdout.strip()
    return candidate if completed.returncode == 0 and SHA256.fullmatch(candidate) else None


def trusted_runner(
    repository: Path,
    runner_id: str,
    specification: dict[str, Any],
) -> tuple[str, str] | None:
    manifest_path = repository / "test-results/wc104/runner-manifests" / f"{runner_id}.json"
    source_repository = os.environ.get("GITHUB_REPOSITORY", "")
    gh = shutil.which("gh")
    if not manifest_path.is_file() or not source_repository or gh is None:
        return None
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        image = validate_supply_manifest(manifest, specification)
    except (OSError, ValueError, json.JSONDecodeError):
        return None
    attestation = subprocess.run(  # noqa: S603
        [gh, "attestation", "verify", f"oci://{image}", "--repo", source_repository],
        cwd=repository,
        check=False,
        capture_output=True,
        text=True,
    )
    if attestation.returncode != 0:
        return None
    pull = subprocess.run(["docker", "pull", image], cwd=repository, check=False)  # noqa: S603
    resolved_id = image_id(image, repository)
    return (image, resolved_id) if pull.returncode == 0 and resolved_id is not None else None


def local_fallback_runner(
    repository: Path,
    runner_id: str,
    specification: dict[str, Any],
) -> tuple[str, str, int]:
    identity = specification["identity"]
    image = f"waooaw-validation-runner-{runner_id}:local-{identity.removeprefix('sha256:')}"
    evidence_root = repository / "test-results/wc104"
    lock_root = evidence_root / "local-runner-locks"
    lock_root.mkdir(parents=True, exist_ok=True)
    lock_path = lock_root / f"{runner_id}-{identity.removeprefix('sha256:')}.lock"
    with lock_path.open("w", encoding="utf-8") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        resolved_id = image_id(image, repository)
        build_count = 0
        if resolved_id is None:
            context = evidence_root / "local-contexts" / f"{runner_id}-{identity.removeprefix('sha256:')}"
            create_context(repository, context, specification)
            dockerfile = context / specification["dockerfile"]
            subprocess.run(  # noqa: S603
                [
                    "docker",
                    "buildx",
                    "build",
                    "--platform",
                    specification["identity_inputs"]["platform"],
                    "--load",
                    "--tag",
                    image,
                    "--file",
                    str(dockerfile),
                    str(context),
                ],
                cwd=repository,
                check=True,
            )
            resolved_id = image_id(image, repository)
            if resolved_id is None:
                raise ValueError(f"local runner build did not produce an immutable image ID: {runner_id}")
            build_count = 1
    return image, resolved_id, build_count


def write_local_evidence(
    repository: Path,
    runner_id: str,
    specification: dict[str, Any],
    image: str,
    resolved_id: str,
    build_count: int,
    trust_source: str,
) -> None:
    output = repository / "test-results/wc104/local-runner-manifests" / f"{runner_id}.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(
            {
                "schema": "waooaw.local-runner-consumer/v1",
                "runner_id": runner_id,
                "runner_identity": specification["identity"],
                "image": image,
                "image_id": resolved_id,
                "build_count": build_count,
                "trust_source": trust_source,
                "authority": "diagnostic-local-only",
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def execute_gate(
    repository: Path,
    gate_id: str,
    head_sha: str,
    base_sha: str,
    git_common_dir: Path,
) -> int:
    catalog = yaml.safe_load((repository / "validation/engineering-validation.yaml").read_text(encoding="utf-8"))
    if not isinstance(catalog, dict):
        raise ValueError("validation catalog root must be a mapping")
    plan = build_execution_plan(catalog, [gate_id], mode="qualification", head_sha=head_sha, run_id=f"local-{gate_id}")
    node = plan["nodes"][0]
    plan_path = repository / "test-results/wc104/local-plans" / f"{gate_id.replace(':', '-')}.json"
    plan_path.parent.mkdir(parents=True, exist_ok=True)
    plan_path.write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    environment = os.environ.copy()
    environment.update(
        {
            "BASE_SHA": base_sha,
            "HEAD_SHA": head_sha,
            "GIT_COMMON_DIR": str(git_common_dir),
            "REPOSITORY_ROOT": str(repository),
        }
    )
    command = [
        sys.executable,
        str(repository / "scripts/validation_control/catalog_execution.py"),
        "--plan",
        str(plan_path),
        "--gate",
        gate_id,
    ]
    if node.get("execution", "container") != "host":
        runner_id = node["runner_id"]
        supply = load_supply_config(repository / "validation/runner-supply.json")
        specification = runner_specification(supply, repository, runner_id)
        trusted = trusted_runner(repository, runner_id, specification)
        if trusted is None:
            image, resolved_id, build_count = local_fallback_runner(repository, runner_id, specification)
            trust_source = "local-identity-build"
        else:
            image, resolved_id = trusted
            build_count = 0
            trust_source = "trusted-attested-digest"
        write_local_evidence(
            repository,
            runner_id,
            specification,
            image,
            resolved_id,
            build_count,
            trust_source,
        )
        environment[f"WAOOAW_RUNNER_{runner_id.upper()}_IMAGE"] = image
        command.extend(("--image-id", resolved_id))
    completed = subprocess.run(  # noqa: S603
        command,
        cwd=repository,
        env=environment,
        check=False,
    )
    return completed.returncode


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gate", required=True)
    parser.add_argument("--head", required=True)
    parser.add_argument("--base", required=True)
    parser.add_argument("--git-common-dir", type=Path, required=True)
    arguments = parser.parse_args()
    repository = Path.cwd().resolve()
    return execute_gate(repository, arguments.gate, arguments.head, arguments.base, arguments.git_common_dir.resolve())


if __name__ == "__main__":
    raise SystemExit(main())
