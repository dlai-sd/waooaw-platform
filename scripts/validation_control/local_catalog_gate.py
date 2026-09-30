#!/usr/bin/env python3
"""Resolve one local validation runner and execute its immutable catalog node."""

# Implements: work-contracts/WC-104-end-to-end-docker-runner-supply.md sections 4.3-4.5
# Constitutional basis: C-023, C-059, C-071, C-080

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import yaml

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from validation_control.orchestrator import build_execution_plan  # noqa: E402
from validation_control.execution_contract import orchestration_preflight  # noqa: E402
from validation_control.evidence_controller import (  # noqa: E402
    catalog_invocation_signature,
    publish_envelope,
    route_failure,
)
from validation_control.identity import evidence_manifest, test_execution_manifest  # noqa: E402
from validation_control.runner_supply import (  # noqa: E402
    create_context,
    load_supply_config,
    runner_specification,
    validate_supply_manifest,
)

SHA256 = re.compile(r"sha256:[0-9a-f]{64}")


def docker_executable() -> str:
    docker = shutil.which("docker")
    if docker is None:
        raise ValueError("docker executable is required for local runner supply")
    return docker


def docker_socket_group() -> str:
    socket = Path("/var/run/docker.sock")
    if not socket.exists():
        raise ValueError("Docker socket is required for local catalog execution")
    return str(socket.stat().st_gid)


def image_id(image: str, repository: Path) -> str | None:
    completed = subprocess.run(  # noqa: S603
        [docker_executable(), "image", "inspect", image, "--format", "{{.Id}}"],
        cwd=repository,
        check=False,
        capture_output=True,
        text=True,
    )
    candidate = completed.stdout.strip()
    return candidate if completed.returncode == 0 and SHA256.fullmatch(candidate) else None


def required_service_identities(repository: Path, node: dict[str, Any]) -> dict[str, str]:
    required_services = node.get("required_services", [])
    if not required_services:
        return {}
    completed = subprocess.run(  # noqa: S603
        [docker_executable(), "compose", "--profile", node["profile"], "config", "--format", "json"],
        cwd=repository,
        check=True,
        capture_output=True,
        text=True,
    )
    compose = json.loads(completed.stdout)
    services = compose.get("services")
    if not isinstance(services, dict):
        raise ValueError("rendered Compose services must be a mapping")
    identities: dict[str, str] = {}
    for service_name in required_services:
        service = services.get(service_name)
        image = service.get("image") if isinstance(service, dict) else None
        if not isinstance(image, str) or not image:
            raise ValueError(f"required service has no rendered image: {service_name}")
        resolved_id = image_id(image, repository)
        if resolved_id is None:
            raise ValueError(f"required service image is unavailable: {service_name}")
        identities[service_name] = resolved_id
    return identities


def trusted_runner(
    repository: Path,
    runner_id: str,
    specification: dict[str, Any],
) -> tuple[str, str, str] | None:
    if os.environ.get("WC104_DISABLE_REGISTRY_REUSE") == "1" or os.environ.get("WC104_FORCE_LOCAL_BUILD") == "1":
        return None
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
    pull = subprocess.run([docker_executable(), "pull", image], cwd=repository, check=False)  # noqa: S603
    resolved_id = image_id(image, repository)
    digest = image.rpartition("@")[2]
    return (image, resolved_id, digest) if pull.returncode == 0 and resolved_id is not None else None


def local_fallback_runner(
    repository: Path,
    runner_id: str,
    specification: dict[str, Any],
) -> tuple[str, str, str, int]:
    identity = specification["identity"]
    image = f"waooaw-validation-runner-{runner_id}:local-{identity.removeprefix('sha256:')}"
    evidence_root = repository / "test-results/wc104"
    lock_root = evidence_root / "local-runner-locks"
    lock_root.mkdir(parents=True, exist_ok=True)
    lock_path = lock_root / f"{runner_id}-{identity.removeprefix('sha256:')}.lock"
    with lock_path.open("w", encoding="utf-8") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        resolved_id = image_id(image, repository)
        manifest_path = evidence_root / "local-runner-manifests" / f"{runner_id}.json"
        if os.environ.get("WC104_FORCE_LOCAL_BUILD") != "1" and resolved_id is not None and manifest_path.is_file():
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            runner_digest = manifest.get("runner_digest")
            if (
                manifest.get("runner_identity") == identity
                and manifest.get("image") == image
                and manifest.get("image_id") == resolved_id
                and isinstance(runner_digest, str)
                and SHA256.fullmatch(runner_digest)
            ):
                return image, resolved_id, runner_digest, 0
        build_count = 0
        context = evidence_root / "local-contexts" / f"{runner_id}-{identity.removeprefix('sha256:')}"
        create_context(repository, context, specification)
        dockerfile = context / specification["dockerfile"]
        metadata_path = context / "build-metadata.json"
        subprocess.run(  # noqa: S603
            [
                docker_executable(),
                "buildx",
                "build",
                "--platform",
                specification["identity_inputs"]["platform"],
                "--load",
                "--metadata-file",
                str(metadata_path),
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
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        runner_digest = metadata.get("containerimage.digest")
        if resolved_id is None or not isinstance(runner_digest, str) or not SHA256.fullmatch(runner_digest):
            raise ValueError(f"local runner build did not produce immutable identities: {runner_id}")
        build_count = 1
        write_local_evidence(
            repository,
            runner_id,
            specification,
            image,
            resolved_id,
            runner_digest,
            build_count,
            "local-identity-build",
        )
    return image, resolved_id, runner_digest, build_count


def write_local_evidence(
    repository: Path,
    runner_id: str,
    specification: dict[str, Any],
    image: str,
    resolved_id: str,
    runner_digest: str,
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
                "runner_digest": runner_digest,
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


def resolve_runner(repository: Path, runner_id: str) -> dict[str, Any]:
    supply = load_supply_config(repository / "validation/runner-supply.json")
    specification = runner_specification(supply, repository, runner_id)
    trusted = trusted_runner(repository, runner_id, specification)
    if trusted is None:
        image, resolved_id, runner_digest, build_count = local_fallback_runner(repository, runner_id, specification)
        trust_source = "local-identity-build"
    else:
        image, resolved_id, runner_digest = trusted
        build_count = 0
        trust_source = "trusted-attested-digest"
        write_local_evidence(
            repository,
            runner_id,
            specification,
            image,
            resolved_id,
            runner_digest,
            build_count,
            trust_source,
        )
    return {
        "runner_id": runner_id,
        "runner_identity": specification["identity"],
        "image": image,
        "image_id": resolved_id,
        "runner_digest": runner_digest,
        "build_count": build_count,
        "trust_source": trust_source,
    }


def gate_execution_identity(repository: Path, gate_id: str, head_sha: str) -> dict[str, str]:
    catalog = yaml.safe_load((repository / "validation/engineering-validation.yaml").read_text(encoding="utf-8"))
    if not isinstance(catalog, dict):
        raise ValueError("validation catalog root must be a mapping")
    plan = build_execution_plan(catalog, [gate_id], mode="qualification", head_sha=head_sha, run_id=f"identity-{gate_id}")
    node = plan["nodes"][0]
    if node.get("runner_required", True):
        runner_digest = resolve_runner(repository, node["runner_id"])["runner_digest"]
    else:
        runner_digest = node.get("tool_digest")
        if not isinstance(runner_digest, str) or not SHA256.fullmatch(runner_digest):
            raise ValueError(f"host-only gate has no immutable tool digest: {gate_id}")
    environment = {name: os.environ.get(name) for name in node.get("environment", [])}
    service_identities = required_service_identities(repository, node)
    implementation = {key: value for key, value in node.items() if key not in {"runner_manifest"}}
    return {
        "catalog_version": str(plan["catalog_version"]),
        "gate_id": gate_id,
        "command_id": node["command_id"],
        "gate_implementation_digest": hashlib.sha256(
            json.dumps(implementation, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest(),
        "runner_digest": runner_digest,
        "environment_digest": hashlib.sha256(json.dumps(environment, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
        "service_digest": hashlib.sha256(
            json.dumps(service_identities, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest(),
    }


def write_commit_metadata(repository: Path, base_sha: str, head_sha: str, artifact_root: Path | None = None) -> None:
    evidence_root = (artifact_root if artifact_root is not None else repository / "test-results") / "wc104"
    for relative in ("metadata", "c059", "c065"):
        directory = evidence_root / relative
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "base-sha.txt").write_text(base_sha + "\n", encoding="utf-8")
        (directory / "head-sha.txt").write_text(head_sha + "\n", encoding="utf-8")


def write_pr_body(pr_body_file: Path | None, gate_id: str, artifact_root: Path) -> None:
    if gate_id not in {"constitutional-commit-gate", "author-review-gate"}:
        return
    if pr_body_file is None:
        raise ValueError(f"{gate_id} local execution requires --pr-body-file")
    if not pr_body_file.is_file():
        raise ValueError(f"PR body file does not exist: {pr_body_file}")
    destination = artifact_root / "wc104" / ("c059" if gate_id == "constitutional-commit-gate" else "c065")
    destination.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(pr_body_file, destination / "pr-body.md")


def write_authorization_context(
    gate_id: str,
    artifact_root: Path,
    base_branch: str | None,
    pr_number: str | None,
    repository_name: str | None,
) -> None:
    if gate_id != "authorization-tier-check":
        return
    values = {
        "base-branch.txt": base_branch,
        "pr-number.txt": pr_number,
        "repository.txt": repository_name,
    }
    missing = [name for name, value in values.items() if not value]
    if missing:
        raise ValueError("authorization-tier-check local execution requires explicit PR context")
    destination = artifact_root / "wc104/c066"
    destination.mkdir(parents=True, exist_ok=True)
    for name, value in values.items():
        assert value is not None
        (destination / name).write_text(value + "\n", encoding="utf-8")


def write_requirement_scope(repository: Path, changed_files: list[str], artifact_root: Path | None = None) -> None:
    if not changed_files:
        raise ValueError("requirement-ledger local execution requires --changed-file")
    normalized: set[str] = set()
    for changed_file in changed_files:
        path = Path(changed_file)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError(f"changed file must be repository-relative: {changed_file}")
        normalized.add(path.as_posix())
    output = (artifact_root if artifact_root is not None else repository / "test-results") / "wc102/changed-files.txt"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("".join(f"{path}\n" for path in sorted(normalized)), encoding="utf-8")


def execute_gate(
    repository: Path,
    gate_id: str,
    head_sha: str,
    base_sha: str,
    git_common_dir: Path,
    changed_files: list[str] | None = None,
    mode: str = "qualification",
    pr_body_file: Path | None = None,
    base_branch: str | None = None,
    pr_number: str | None = None,
    repository_name: str | None = None,
) -> int:
    if mode not in {"focused", "qualification"}:
        raise ValueError(f"unsupported local execution mode: {mode}")
    orchestration_preflight(repository)
    catalog = yaml.safe_load((repository / "validation/engineering-validation.yaml").read_text(encoding="utf-8"))
    if not isinstance(catalog, dict):
        raise ValueError("validation catalog root must be a mapping")
    run_id = f"local-{gate_id}-{os.getpid()}-{time.time_ns()}"
    plan = build_execution_plan(catalog, [gate_id], mode=mode, head_sha=head_sha, run_id=run_id)
    node = plan["nodes"][0]
    artifact_root = repository / node["output_directory"]
    service_identities = required_service_identities(repository, node)
    write_commit_metadata(repository, base_sha, head_sha, artifact_root)
    write_pr_body(pr_body_file, gate_id, artifact_root)
    write_authorization_context(gate_id, artifact_root, base_branch, pr_number, repository_name)
    if gate_id == "requirement-ledger":
        write_requirement_scope(repository, changed_files or [], artifact_root)
    plan_path = repository / "test-results/wc104/local-plans" / f"{gate_id.replace(':', '-')}.json"
    plan_path.parent.mkdir(parents=True, exist_ok=True)
    plan_path.write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    environment = os.environ.copy()
    environment.update(
        {
            "BASE_SHA": base_sha,
            "DOCKER_GID": docker_socket_group(),
            "GOAL006_EVIDENCE_DIR": str(repository / "test-results/wc104/goal006-local-azure-runtime"),
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
    resolution: dict[str, Any] | None = None
    if node.get("runner_required", True):
        runner_id = node["runner_id"]
        resolution = resolve_runner(repository, runner_id)
        environment[f"WAOOAW_RUNNER_{runner_id.upper()}_IMAGE"] = resolution["image"]
        command.extend(("--image-id", resolution["image_id"]))
    started_at = datetime.now(timezone.utc).isoformat()
    started_monotonic = time.monotonic()
    completed = subprocess.run(  # noqa: S603
        command,
        cwd=repository,
        env=environment,
        check=False,
    )
    duration_ms = round((time.monotonic() - started_monotonic) * 1000)
    record_path = repository / node["output_directory"] / "wc109-execution.json"
    record_path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "schema": "waooaw.wc109-tier2-execution/v1",
        "authority": "diagnostic-local-only",
        "catalog_controlled": True,
        "compose_project": node["compose_project"],
        "execution_namespace": plan["execution_namespace"],
        "base_sha": base_sha,
        "gate_id": gate_id,
        "head_sha": head_sha,
        "invocation_source": "catalog",
        "mode": mode,
        "output_directory": node["output_directory"],
        "product_image_build_events": len(node.get("product_image_builds", [])),
        "result": "PASS" if completed.returncode == 0 else "FAIL",
        "return_code": completed.returncode,
        "runner_build_events": resolution["build_count"] if resolution is not None else 0,
        "runner_digest": resolution["runner_digest"] if resolution is not None else node.get("tool_digest"),
        "service_identities": service_identities,
    }
    temporary = record_path.with_suffix(f".tmp-{os.getpid()}")
    temporary.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, record_path)
    runner_digest = record["runner_digest"]
    if not isinstance(runner_digest, str):
        raise ValueError("catalog execution has no runner digest for evidence binding")
    source_identity = "sha256:" + hashlib.sha256(head_sha.encode()).hexdigest()
    environment_identity = [
        {
            "name_digest": hashlib.sha256(name.encode()).hexdigest(),
            "value_digest": hashlib.sha256(str(environment.get(name)).encode()).hexdigest(),
        }
        for name in sorted(node.get("environment", []))
    ]
    execution_identity = test_execution_manifest(
        {
            "mounted_source_identity": source_identity,
            "runner_digest": runner_digest,
            "command_id": node["command_id"],
            "policy_version": str(plan["catalog_version"]),
            "environment": environment_identity,
            "service_identities": service_identities,
            "disposable_state_contract": {
                "compose_project": node["compose_project"],
                "output_directory": node["output_directory"],
            },
            "architecture": "amd64",
            "platform": "linux",
            "test_execution_schema_version": "v1",
        }
    )["digest"]
    evidence_identity = evidence_manifest(
        {
            "subject_identity": source_identity,
            "test_execution_identity": execution_identity,
            "runner_digest": runner_digest,
            "command_id": node["command_id"],
            "policy_version": str(plan["catalog_version"]),
            "environment": environment_identity,
            "evidence_schema_version": "v1",
            "trust_source": "local-diagnostic",
            "freshness": {"head_sha": head_sha, "policy": "executed-now"},
        }
    )["digest"]
    claim = {
        "namespace": plan["execution_namespace"],
        "gate_id": gate_id,
        "command_id": node["command_id"],
        "head_sha": head_sha,
    }
    control_key = os.urandom(32)
    routing_class = (
        "NONE"
        if completed.returncode == 0
        else (
            "RUNNER" if completed.returncode == 78 else "WORKFLOW" if completed.returncode == 124 else route_failure("assertion")
        )
    )
    envelope = {
        "schema": "waooaw.validation-evidence-envelope/v1",
        "base_sha": base_sha,
        "head_sha": head_sha,
        "identities": {
            "runner": runner_digest,
            "test_execution": execution_identity,
            "subject": source_identity,
            "evidence": evidence_identity,
        },
        "component": ",".join(node["components"]) if node["components"] else "cross-cutting",
        "gate_id": gate_id,
        "command_id": node["command_id"],
        "started_at": started_at,
        "duration_ms": duration_ms,
        "result": record["result"],
        "routing_class": routing_class,
        "first_cause": "none" if completed.returncode == 0 else f"exit-code:{completed.returncode}",
        "artifacts": [
            {
                "path": str(record_path.relative_to(repository)),
                "digest": "sha256:" + hashlib.sha256(record_path.read_bytes()).hexdigest(),
            }
        ],
        "disposition": "executed",
        "disposition_proof": {"execution_fresh": True},
        "invocation": {
            "source": "catalog",
            "namespace": plan["execution_namespace"],
            "signature": catalog_invocation_signature(claim, control_key),
        },
        "trust_source": "local-diagnostic",
    }
    publish_envelope(
        repository / node["output_directory"] / "evidence-envelope.json",
        envelope,
        control_key,
        required_trust_source="local-diagnostic",
        artifact_root=repository,
    )
    return completed.returncode


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gate", required=True)
    parser.add_argument("--head", required=True)
    parser.add_argument("--base", required=True)
    parser.add_argument("--git-common-dir", type=Path, required=True)
    parser.add_argument("--changed-file", action="append", default=[])
    parser.add_argument("--pr-body-file", type=Path)
    parser.add_argument("--base-branch")
    parser.add_argument("--pr-number")
    parser.add_argument("--repository")
    parser.add_argument("--mode", choices=("focused", "qualification"), default="qualification")
    arguments = parser.parse_args()
    repository = Path.cwd().resolve()
    return execute_gate(
        repository,
        arguments.gate,
        arguments.head,
        arguments.base,
        arguments.git_common_dir.resolve(),
        arguments.changed_file,
        arguments.mode,
        arguments.pr_body_file.resolve() if arguments.pr_body_file is not None else None,
        arguments.base_branch,
        arguments.pr_number,
        arguments.repository,
    )


if __name__ == "__main__":
    raise SystemExit(main())
