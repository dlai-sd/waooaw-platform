"""Execute one immutable validation-plan node without allowing a Compose build."""

# Implements: work-contracts/WC-104-end-to-end-docker-runner-supply.md §4.5
# Constitutional basis: C-023, C-059, C-071, C-080

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from validation_control.execution_contract import (  # noqa: E402
    UnchangedExecutionFailureError,
    assert_retry_allowed,
    binding_digest,
    clear_failure,
    evidence_is_current,
    execution_binding,
    orchestration_preflight,
    prepare_evidence,
    record_failure,
    safe_segment,
)


def select_plan_node(plan: dict[str, Any], gate_id: str) -> dict[str, Any]:
    if plan.get("schema") != "waooaw.validation-execution-plan/v1":
        raise ValueError("validation plan schema is not trusted")
    nodes = plan.get("nodes")
    if not isinstance(nodes, list):
        raise ValueError("validation plan nodes must be a list")
    matches = [node for node in nodes if isinstance(node, dict) and node.get("gate_id") == gate_id]
    if len(matches) != 1:
        raise ValueError(f"validation plan must contain exactly one {gate_id} node")
    node = matches[0]
    for field in ("runner_id", "compose_service", "profile", "command"):
        if not isinstance(node.get(field), str) or not node[field]:
            raise ValueError(f"validation plan node has invalid {field}")
    return node


def compose_command(node: dict[str, Any], git_common_dir: str | None = None) -> list[str]:
    environment = node.get("environment", [])
    if not isinstance(environment, list) or not all(isinstance(name, str) and name for name in environment):
        raise ValueError("validation plan node has invalid environment allowlist")
    command = [
        "docker",
        "compose",
        "--project-name",
        node["compose_project"],
        "--profile",
        node["profile"],
        "run",
        "--rm",
        "--pull",
        "never",
    ]
    for name in environment:
        command.extend(("-e", name))
    output_directory = node.get("output_directory")
    if not isinstance(output_directory, str) or not output_directory.startswith("test-results/wc109/runs/"):
        raise ValueError("validation plan node has invalid output directory")
    command.extend(("--volume", f"./{output_directory}:/workspace/test-results"))
    resources = node.get("resources")
    if not isinstance(resources, dict):
        raise ValueError("validation plan node resources must be a mapping")
    if resources.get("docker_socket") is True:
        command.extend(("--volume", "/var/run/docker.sock:/var/run/docker.sock"))
    if git_common_dir:
        command.extend(("--volume", f"{git_common_dir}:{git_common_dir}:ro"))
    command.extend(
        (
            node["compose_service"],
            "sh",
            "-lc",
            node["command"],
        )
    )
    return command


def execution_command(node: dict[str, Any], docker: str, git_common_dir: str | None = None) -> list[str]:
    if node.get("execution", "container") == "host":
        return ["sh", "-lc", node["command"]]
    command = compose_command(node, git_common_dir)
    command[0] = docker
    return command


def service_start_command(node: dict[str, Any], docker: str) -> list[str]:
    required_services = node.get("required_services", [])
    if not isinstance(required_services, list) or not all(isinstance(service, str) and service for service in required_services):
        raise ValueError("validation plan node has invalid required services")
    return [
        docker,
        "compose",
        "--project-name",
        node["compose_project"],
        "--profile",
        node["profile"],
        "up",
        "--detach",
        "--no-build",
        "--pull",
        "missing",
        "--wait",
        *required_services,
    ]


def cleanup_command(node: dict[str, Any], docker: str) -> list[str]:
    return [
        docker,
        "compose",
        "--project-name",
        node["compose_project"],
        "down",
        "--volumes",
        "--remove-orphans",
    ]


def cleanup_execution(node: dict[str, Any], docker: str, environment: dict[str, str]) -> None:
    subprocess.run(  # noqa: S603
        cleanup_command(node, docker),
        check=False,
        env=environment,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def runner_environment(image_id: str, docker_socket: Path = Path("/var/run/docker.sock")) -> dict[str, str]:
    environment = os.environ.copy()
    environment["WAOOAW_TEST_RUNNER_IMAGE_ID"] = image_id
    if docker_socket.exists():
        environment["DOCKER_GID"] = str(docker_socket.stat().st_gid)
    return environment


def stage_input_directory(repository: Path, input_directory: Path, artifact_root: Path) -> Path:
    repository = repository.resolve()
    test_results = (repository / "test-results").resolve()
    source = (repository / input_directory).resolve()
    resolved_artifact_root = (repository / artifact_root).resolve()
    hosted_runs = (test_results / "wc109/runs").resolve()
    if source == test_results or not source.is_relative_to(test_results):
        raise ValueError("catalog input directory must be below test-results")
    if not source.is_dir():
        raise ValueError(f"catalog input directory does not exist: {input_directory}")
    if not resolved_artifact_root.is_relative_to(hosted_runs):
        raise ValueError("catalog artifact root must be below test-results/wc109/runs")

    target = resolved_artifact_root / source.relative_to(test_results)
    if target.exists():
        shutil.rmtree(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, target)
    return target


def run_execution_preflight(
    plan: dict[str, Any],
    node: dict[str, Any],
    image_id: str,
    docker: str,
    environment: dict[str, str],
    repository: Path,
    git_common_dir: str | None = None,
) -> int:
    namespace = plan.get("execution_namespace")
    if not isinstance(namespace, str) or not namespace:
        raise ValueError("validation plan execution namespace is required")
    binding = execution_binding(plan, node, image_id, repository)
    digest = binding_digest(binding)
    assert_retry_allowed(repository, node["gate_id"], digest)
    output_directory = node.get("output_directory")
    if not isinstance(output_directory, str):
        raise ValueError("validation plan node output directory is required")
    artifact_root = repository / output_directory
    proof, token = prepare_evidence(repository, namespace, node["gate_id"], digest, artifact_root)
    resources = node.get("resources")
    if not isinstance(resources, dict):
        raise ValueError("validation plan node resources must be a mapping")
    preflight_variables = {
        "WC106_DOCKER_SOCKET_REQUIRED": "1" if resources.get("docker_socket") is True else "0",
        "WC106_EVIDENCE_PATH": f"/workspace/test-results/{proof.relative_to(artifact_root)}",
        "WC106_EVIDENCE_TOKEN": token,
        "WC106_EXECUTION_NAMESPACE": safe_segment(namespace),
        "WC106_EXPECTED_UID": "1000",
        "WC106_GATE_ID": safe_segment(node["gate_id"]),
    }
    preflight_node = dict(node)
    preflight_node.pop("execution", None)
    preflight_node["command"] = "sh scripts/validation_control/run_execution_contract.sh"
    preflight_node["environment"] = [*node.get("environment", []), *preflight_variables]
    preflight_environment = {**environment, **preflight_variables}
    completed = subprocess.run(  # noqa: S603
        execution_command(preflight_node, docker, git_common_dir),
        check=False,
        env=preflight_environment,
    )
    if completed.returncode != 0:
        reason = f"exact-container-preflight:{completed.returncode}"
        record_failure(repository, node["gate_id"], digest, reason)
        print(f"WC-106 execution contract failed for {node['gate_id']}: {reason}")
        return 78
    if not evidence_is_current(proof, token):
        record_failure(repository, node["gate_id"], digest, "host-visible-evidence-missing")
        print(f"WC-106 execution contract failed for {node['gate_id']}: host cannot atomically publish {proof}")
        return 78
    clear_failure(repository, node["gate_id"])
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--gate", required=True)
    parser.add_argument("--image-id")
    parser.add_argument("--input-directory", action="append", default=[], type=Path)
    arguments = parser.parse_args()

    plan = json.loads(arguments.plan.read_text(encoding="utf-8"))
    if not isinstance(plan, dict):
        raise ValueError("validation plan root must be a mapping")
    node = select_plan_node(plan, arguments.gate)
    docker = shutil.which("docker")
    if docker is None:
        raise ValueError("runner verification tools are unavailable")
    git_common_dir = os.environ.get("GIT_COMMON_DIR")
    if node.get("execution", "container") == "host" and node.get("runner_required", True) is False:
        return subprocess.run(execution_command(node, docker, git_common_dir), check=False).returncode  # noqa: S603

    image_variable = f"WAOOAW_RUNNER_{node['runner_id'].upper()}_IMAGE"
    if not os.environ.get(image_variable):
        raise ValueError(f"{image_variable} is not set by the verified runner consumer")
    if arguments.image_id is None:
        raise ValueError("--image-id is required for runner-backed catalog execution")

    orchestration_preflight(Path.cwd())
    output_directory = node.get("output_directory")
    if not isinstance(output_directory, str):
        raise ValueError("validation plan node output directory is required")
    artifact_root = Path(output_directory)
    artifact_root.mkdir(parents=True, exist_ok=True)
    artifact_root.chmod(0o777)
    for input_directory in arguments.input_directory:
        stage_input_directory(Path.cwd(), input_directory, artifact_root)
    verifier = Path("scripts/verify_runner_image.sh").resolve()
    if not verifier.is_file():
        raise ValueError("runner verification tools are unavailable")
    verification = subprocess.run(  # noqa: S603
        [str(verifier), node["profile"], node["compose_service"], arguments.image_id],
        check=False,
    )
    if verification.returncode != 0:
        return verification.returncode
    environment = runner_environment(arguments.image_id)
    environment["COMPOSE_PROJECT_NAME"] = node["compose_project"]
    required_services = node.get("required_services", [])
    if required_services:
        service_start = subprocess.run(  # noqa: S603
            service_start_command(node, docker),
            check=False,
            env=environment,
        )
        if service_start.returncode != 0:
            cleanup_execution(node, docker, environment)
            print(f"validation service startup failed for {node['gate_id']}: {service_start.returncode}")
            return 78
    try:
        preflight_result = run_execution_preflight(
            plan,
            node,
            arguments.image_id,
            docker,
            environment,
            Path.cwd(),
            git_common_dir,
        )
    except UnchangedExecutionFailureError as error:
        print(f"WC-106 retry blocked: {error}")
        return 78
    if preflight_result != 0:
        cleanup_execution(node, docker, environment)
        return preflight_result
    try:
        try:
            return subprocess.run(  # noqa: S603
                execution_command(node, docker, git_common_dir),
                check=False,
                env=environment,
                timeout=node["resources"]["timeout_seconds"],
            ).returncode
        except subprocess.TimeoutExpired:
            print(f"validation gate timed out: {node['gate_id']}")
            return 124
    finally:
        cleanup_execution(node, docker, environment)


if __name__ == "__main__":
    raise SystemExit(main())
