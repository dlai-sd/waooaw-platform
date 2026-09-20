"""Execute one immutable validation-plan node without allowing a Compose build."""

# Implements: work-contracts/WC-104-end-to-end-docker-runner-supply.md §4.5
# Constitutional basis: C-023, C-059, C-071, C-080

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any


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
        "--profile",
        node["profile"],
        "run",
        "--rm",
        "--pull",
        "never",
    ]
    for name in environment:
        command.extend(("-e", name))
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


def runner_environment(image_id: str, docker_socket: Path = Path("/var/run/docker.sock")) -> dict[str, str]:
    environment = os.environ.copy()
    environment["WAOOAW_TEST_RUNNER_IMAGE_ID"] = image_id
    if docker_socket.exists():
        environment["DOCKER_GID"] = str(docker_socket.stat().st_gid)
    return environment


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--gate", required=True)
    parser.add_argument("--image-id")
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

    artifact_root = Path("test-results")
    artifact_root.mkdir(exist_ok=True)
    artifact_root.chmod(0o777)
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
    return subprocess.run(execution_command(node, docker, git_common_dir), check=False, env=environment).returncode  # noqa: S603


if __name__ == "__main__":
    raise SystemExit(main())
